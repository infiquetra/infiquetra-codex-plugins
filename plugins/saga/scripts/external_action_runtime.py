#!/usr/bin/env python3
"""Provider-neutral prepare, approve, execute, adjudicate, and consume runtime."""

from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))

import external_action_contract as contract  # noqa: E402
import external_action_egress as egress  # noqa: E402
import external_action_policy as policy  # noqa: E402
import external_action_status as status_module  # noqa: E402
import external_action_store as store_module  # noqa: E402
import fleet_commons_shim  # noqa: E402
import reconcile  # noqa: E402

_receipt = fleet_commons_shim.load("bridge_receipt")


class RuntimeError(ValueError):
    """An action cannot proceed without violating approval or lifecycle truth."""


@dataclass(frozen=True, slots=True)
class Preview:
    store: store_module.Store
    request: contract.ActionRequest
    candidate_approval: contract.ActionApproval
    approval_fingerprint: str
    sanitized_payload: Any
    egress_detections: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    status: str
    evidence_ref: str | None = None
    detail: Mapping[str, Any] | None = None
    validated: bool = False
    artifact_sha256: str | None = None


LaunchReporter = Callable[[Mapping[str, Any] | None], None]
Executor = Callable[[contract.ActionRequest, contract.ActionApproval, LaunchReporter], ExecutionOutcome]


def prepare(
    *,
    repo_root: Path,
    saga_id: str,
    run_id: str,
    template: policy.ActionTemplate,
    route: Mapping[str, Any],
    cost_class: str,
    route_egress: Mapping[str, Any],
    base_revision: str,
    payload: Any,
    created_at: str,
    dirty_overlap: tuple[str, ...] = (),
    attempt: int = 1,
    predecessor_request_sha256: str | None = None,
) -> Preview:
    sanitized = egress.sanitize(payload)
    if sanitized.blocked:
        raise RuntimeError(f"outbound payload blocked: {', '.join(sanitized.detections)}")
    resolved_base = _resolve_base_revision(repo_root, base_revision)
    derived_overlap = _derive_dirty_overlap(
        repo_root, (*template.context_scope, *template.write_set)
    )
    if dirty_overlap and tuple(sorted(dirty_overlap)) != derived_overlap:
        raise RuntimeError("caller dirty-worktree overlap differs from repository state")
    request = contract.ActionRequest(
        saga_id=saga_id,
        run_id=run_id,
        action_id=template.action_id,
        stage="work" if template.action_id == "bounded-unit" else _stage_from_route(route),
        intent=template.intent,
        trigger=template.trigger,
        requiredness=template.requiredness,
        provider_constraints=template.provider_constraints,
        context_scope=template.context_scope,
        sensitivity=template.sensitivity,
        write_set=template.write_set,
        evidence_destination=template.evidence_destination,
        consumption_point=template.consumption_point,
        created_at=created_at,
        attempt=attempt,
        predecessor_request_sha256=predecessor_request_sha256,
    )
    frozen_payload = json.loads(contract.canonical_json(sanitized.payload))
    frozen_route = json.loads(contract.canonical_json(dict(route)))
    frozen_egress = json.loads(contract.canonical_json(dict(route_egress)))
    candidate = contract.ActionApproval(
        action_id=request.action_id,
        approved_at="preview",
        operator="preview",
        route=frozen_route,
        context_scope=request.context_scope,
        sensitivity=request.sensitivity,
        base_revision=resolved_base,
        write_set=request.write_set,
        cost_class=cost_class,
        egress=frozen_egress,
        request_sha256=request.request_sha256,
        payload=frozen_payload,
        payload_sha256=sanitized.payload_sha256 or contract.digest(frozen_payload),
        dirty_overlap=derived_overlap,
        dirty_overlap_sha256=contract.digest(list(derived_overlap)),
    )
    store = store_module.Store.for_action(
        saga_id=saga_id, run_id=run_id, action_id=request.action_id, repo_root=repo_root
    )
    store_module.write_request(store, request)
    store_module.append_event(
        store,
        event_id="resolve-1",
        event="resolve",
        at=created_at,
        detail={
            "approval_fingerprint": candidate.approval_fingerprint,
            "route": dict(route),
            "payload_sha256": sanitized.payload_sha256,
            "egress_detections": list(sanitized.detections),
            "dirty_overlap": list(derived_overlap),
        },
    )
    status_module.refresh(store)
    return Preview(
        store,
        request,
        candidate,
        candidate.approval_fingerprint,
        frozen_payload,
        sanitized.detections,
    )


def _stage_from_route(route: Mapping[str, Any]) -> str:
    stage = route.get("stage")
    if not isinstance(stage, str) or stage not in contract.STAGES:
        raise RuntimeError("route must include a supported stage")
    return stage


def approve(preview: Preview, *, operator: str, approved_at: str) -> contract.ActionApproval:
    approval = contract.ActionApproval(
        action_id=preview.candidate_approval.action_id,
        approved_at=approved_at,
        operator=operator,
        route=preview.candidate_approval.route,
        context_scope=preview.candidate_approval.context_scope,
        sensitivity=preview.candidate_approval.sensitivity,
        base_revision=preview.candidate_approval.base_revision,
        write_set=preview.candidate_approval.write_set,
        cost_class=preview.candidate_approval.cost_class,
        egress=preview.candidate_approval.egress,
        request_sha256=preview.candidate_approval.request_sha256,
        payload=preview.candidate_approval.payload,
        payload_sha256=preview.candidate_approval.payload_sha256,
        dirty_overlap=preview.candidate_approval.dirty_overlap,
        dirty_overlap_sha256=preview.candidate_approval.dirty_overlap_sha256,
    )
    if approval.approval_fingerprint != preview.approval_fingerprint:
        raise RuntimeError("approval input changed after preview")
    store_module.write_approval(preview.store, approval)
    store_module.append_event(preview.store, event_id="approve-1", event="approve", at=approved_at)
    status_module.refresh(preview.store)
    return approval


def execute(store: store_module.Store, *, executor: Executor, at: str) -> ExecutionOutcome:
    snapshot = store_module.read_snapshot(store)
    if snapshot.state != contract.State.APPROVED or snapshot.approval is None:
        raise RuntimeError("action must be approved before execution")
    approval = snapshot.approval
    if approval.request_sha256 != snapshot.request.request_sha256:
        raise RuntimeError("persisted approval does not bind the request")
    resolved = next(
        (event for event in snapshot.events if event.get("event") == "resolve"), None
    )
    detail = dict(resolved.get("detail", {})) if isinstance(resolved, Mapping) else {}
    if detail.get("approval_fingerprint") != approval.approval_fingerprint:
        raise RuntimeError("persisted approval fingerprint differs from resolution")
    if detail.get("payload_sha256") != approval.payload_sha256:
        raise RuntimeError("persisted approval does not bind the outbound payload")
    if tuple(detail.get("dirty_overlap", [])) != approval.dirty_overlap:
        raise RuntimeError("persisted approval does not bind dirty-worktree overlap")
    if store.repo_root is not None:
        current_overlap = _derive_dirty_overlap(
            store.repo_root,
            (*snapshot.request.context_scope, *snapshot.request.write_set),
        )
        if current_overlap != approval.dirty_overlap:
            raise RuntimeError("dirty-worktree overlap changed after approval")
    store_module.append_event(store, event_id="claim-1", event="claim", at=at)
    launched = False

    def acknowledge_launch(identity: Mapping[str, Any] | None = None) -> None:
        nonlocal launched
        if not launched:
            store_module.append_event(
                store,
                event_id="launch-1",
                event="launch",
                at=at,
                detail={"identity": _normalize_launch_identity(identity)},
            )
            launched = True

    try:
        outcome = executor(snapshot.request, snapshot.approval, acknowledge_launch)
    except TimeoutError:
        event = "timeout" if launched else "unavailable"
        if launched:
            _record_returned_termination(store, at=at, disposition="executor-timeout")
        store_module.append_event(store, event_id="terminal-1", event=event, at=at)
        status_module.refresh(store)
        return ExecutionOutcome("timed-out" if launched else "unavailable")
    except Exception as exc:
        event = "invalidate-evidence" if launched else "unavailable"
        detail = {"error_type": type(exc).__name__}
        if launched:
            _record_returned_termination(store, at=at, disposition="executor-error")
        store_module.append_event(
            store, event_id="terminal-1", event=event, at=at, detail=detail
        )
        status_module.refresh(store)
        return ExecutionOutcome(
            "invalid-evidence" if launched else "unavailable",
            detail=detail,
        )
    if not launched:
        store_module.append_event(store, event_id="terminal-1", event="unavailable", at=at)
        status_module.refresh(store)
        return ExecutionOutcome("unavailable")
    if outcome.status != "available" or not outcome.evidence_ref:
        _record_returned_termination(store, at=at, disposition="executor-returned")
        store_module.append_event(store, event_id="terminal-1", event="invalidate-evidence", at=at)
        status_module.refresh(store)
        return ExecutionOutcome("invalid-evidence", detail=outcome.detail)
    evidence_path = Path(outcome.evidence_ref).resolve(strict=False)
    evidence_root = store.root.resolve()
    if (
        not evidence_path.is_relative_to(evidence_root)
        or not evidence_path.is_file()
    ):
        store_module.append_event(store, event_id="terminal-1", event="invalidate-evidence", at=at)
        status_module.refresh(store)
        return ExecutionOutcome("invalid-evidence", detail={"reason": "unbound evidence artifact"})
    try:
        artifact, artifact_sha256 = _validate_evidence_artifact(
            snapshot, approval, evidence_path
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        store_module.append_event(store, event_id="terminal-1", event="invalidate-evidence", at=at)
        status_module.refresh(store)
        return ExecutionOutcome(
            "invalid-evidence", detail={"reason": f"invalid evidence artifact: {exc}"}
        )
    if outcome.artifact_sha256 and outcome.artifact_sha256 != artifact_sha256:
        _record_returned_termination(store, at=at, disposition="executor-returned")
        store_module.append_event(store, event_id="terminal-1", event="invalidate-evidence", at=at)
        status_module.refresh(store)
        return ExecutionOutcome("invalid-evidence", detail={"reason": "artifact digest mismatch"})
    _record_returned_termination(store, at=at, disposition="executor-completed")
    store_module.append_event(
        store,
        event_id="complete-1",
        event="complete",
        at=at,
        detail={
            "evidence_ref": outcome.evidence_ref,
            "artifact_sha256": artifact_sha256,
            "evidence_digest": artifact["evidence_digest"],
            "finding_count": len(artifact["findings"]),
            "runner_receipt": artifact["runner_receipt"],
        },
    )
    status_module.refresh(store)
    return outcome


def interrupt(
    store: store_module.Store,
    *,
    at: str,
    rationale: str,
    termination_proof: Mapping[str, Any] | None = None,
) -> None:
    """Resolve an uncertain claimed/launched action without redispatching it."""
    snapshot = store_module.read_snapshot(store)
    if snapshot.state not in {contract.State.CLAIMED, contract.State.LAUNCHED}:
        raise RuntimeError("only claimed or launched actions can be interrupted")
    launched = snapshot.state == contract.State.LAUNCHED
    if termination_proof is not None:
        raise RuntimeError("caller-supplied termination proof is not accepted")
    receipt: dict[str, Any] | None = None
    if launched:
        receipt = _terminate_launched_action(store, at=at)
    store_module.append_event(
        store,
        event_id="interrupt-1",
        event="interrupt",
        at=at,
        rationale=rationale,
        detail={
            "launched": launched,
            "termination_receipt_sha256": (
                receipt.get("receipt_sha256") if receipt is not None else None
            ),
        },
    )
    status_module.refresh(store)


def retry(
    preview: Preview, *, repo_root: Path, new_run_id: str, created_at: str
) -> Preview:
    """Create a fresh immutable attempt after an explicit terminal failure."""
    snapshot = store_module.read_snapshot(preview.store)
    if snapshot.state not in contract.TERMINAL_FAILURE_STATES:
        raise RuntimeError("retry requires a terminal failed or interrupted attempt")
    approval = snapshot.approval or preview.candidate_approval
    if any(event.get("event") == "launch" for event in snapshot.events):
        _validated_termination_receipt(preview.store, snapshot)
    return _prepare_retry_successor(
        preview,
        repo_root=repo_root,
        new_run_id=new_run_id,
        created_at=created_at,
        approval=approval,
    )


def _prepare_retry_successor(
    preview: Preview,
    *,
    repo_root: Path,
    new_run_id: str,
    created_at: str,
    approval: contract.ActionApproval,
) -> Preview:
    request = preview.request
    contract.require_id(new_run_id, field_name="new_run_id")
    with _lineage_lock(preview.store, request):
        marker = _retry_marker(preview.store, request)
        marker_value = _read_json(marker)
        existing = _find_retry_successor(preview.store, request)
        if marker_value is not None:
            recorded_run = str(marker_value.get("successor_run_id") or "")
            if recorded_run != new_run_id:
                raise RuntimeError("retry successor already exists for predecessor")
        if existing is not None:
            existing_store, existing_request = existing
            if existing_request.run_id != new_run_id:
                raise RuntimeError("retry successor already exists for predecessor")
            retry_preview = _complete_retry_preview(
                existing_store,
                existing_request,
                approval,
                created_at=existing_request.created_at,
            )
            _write_retry_marker(marker, request, existing_request.run_id)
            return retry_preview
        retry_request = contract.ActionRequest(
        saga_id=request.saga_id,
        run_id=new_run_id,
        action_id=request.action_id,
        stage=request.stage,
        intent=request.intent,
        trigger=request.trigger,
        requiredness=request.requiredness,
        provider_constraints=request.provider_constraints,
        context_scope=request.context_scope,
        sensitivity=request.sensitivity,
        write_set=request.write_set,
        evidence_destination=request.evidence_destination,
        consumption_point=request.consumption_point,
        created_at=created_at,
        attempt=request.attempt + 1,
        predecessor_request_sha256=request.request_sha256,
        )
        retry_store = store_module.Store.for_action(
            saga_id=retry_request.saga_id,
            run_id=retry_request.run_id,
            action_id=retry_request.action_id,
            repo_root=repo_root,
        )
        store_module.write_request(retry_store, retry_request)
        retry_preview = _complete_retry_preview(
            retry_store,
            retry_request,
            approval,
            created_at=created_at,
        )
        _write_retry_marker(marker, request, new_run_id)
        return retry_preview


def _complete_retry_preview(
    retry_store: store_module.Store,
    retry_request: contract.ActionRequest,
    approval: contract.ActionApproval,
    *,
    created_at: str,
) -> Preview:
    candidate = contract.ActionApproval(
        action_id=retry_request.action_id,
        approved_at="preview",
        operator="preview",
        route=approval.route,
        context_scope=approval.context_scope,
        sensitivity=approval.sensitivity,
        base_revision=approval.base_revision,
        write_set=approval.write_set,
        cost_class=approval.cost_class,
        egress=approval.egress,
        request_sha256=retry_request.request_sha256,
        payload=approval.payload,
        payload_sha256=approval.payload_sha256,
        dirty_overlap=approval.dirty_overlap,
        dirty_overlap_sha256=approval.dirty_overlap_sha256,
    )
    store_module.append_event(
        retry_store,
        event_id="resolve-1",
        event="resolve",
        at=created_at,
        detail={
            "approval_fingerprint": candidate.approval_fingerprint,
            "route": dict(candidate.route),
            "payload_sha256": candidate.payload_sha256,
            "egress_detections": [],
            "dirty_overlap": list(candidate.dirty_overlap),
                "predecessor_request_sha256": retry_request.predecessor_request_sha256,
        },
    )
    status_module.refresh(retry_store)
    return Preview(
        retry_store,
        retry_request,
        candidate,
        candidate.approval_fingerprint,
        candidate.payload,
        (),
    )


def load_preview(
    *, repo_root: Path, saga_id: str, run_id: str, action_id: str
) -> Preview:
    """Reload a durable action for fresh-process recovery and retry."""
    store = store_module.Store.for_action(
        saga_id=saga_id, run_id=run_id, action_id=action_id, repo_root=repo_root
    )
    snapshot = store_module.read_snapshot(store)
    if snapshot.approval is None:
        raise RuntimeError("durable recovery requires a persisted approval")
    approval = snapshot.approval
    return Preview(
        store,
        snapshot.request,
        approval,
        approval.approval_fingerprint,
        approval.payload,
        (),
    )


def _resolve_base_revision(repo_root: Path, value: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", value):
        return value
    process = subprocess.run(
        ["git", "rev-parse", "--verify", f"{value}^{{commit}}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    resolved = process.stdout.strip()
    if process.returncode or not re.fullmatch(r"[0-9a-f]{40}", resolved):
        raise RuntimeError("base_revision must resolve to a full commit SHA")
    return resolved


def _derive_dirty_overlap(repo_root: Path, scopes: tuple[str, ...]) -> tuple[str, ...]:
    if not scopes:
        return ()
    process = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode:
        raise RuntimeError("cannot inspect dirty-worktree overlap")
    dirty: list[str] = []
    records = process.stdout.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4:
            raise RuntimeError("git status returned a malformed porcelain record")
        paths = [record[3:]]
        if "R" in record[:2] or "C" in record[:2]:
            if index >= len(records) or not records[index]:
                raise RuntimeError("git status returned an incomplete rename record")
            paths.append(records[index])
            index += 1
        for path in paths:
            if any(path == scope or path.startswith(scope.rstrip("/") + "/") for scope in scopes):
                dirty.append(path)
    return tuple(sorted(set(dirty)))


def _normalize_launch_identity(identity: Mapping[str, Any] | None) -> dict[str, Any]:
    value = dict(identity or {"transport": "in-process"})
    transport = value.get("transport")
    if transport not in {"cli", "http", "in-process"}:
        raise RuntimeError("launch identity transport is invalid")
    if transport == "cli":
        if any(
            isinstance(value.get(field), bool)
            or not isinstance(value.get(field), int)
            or value[field] < 1
            for field in ("pid", "process_group")
        ):
            raise RuntimeError("CLI launch identity requires positive pid and process_group")
        if not re.fullmatch(r"[0-9a-f]{64}", str(value.get("argv_sha256") or "")):
            raise RuntimeError("CLI launch identity requires argv_sha256")
    if transport == "http" and not isinstance(value.get("operation_id"), str):
        raise RuntimeError("HTTP launch identity requires operation_id")
    return value


def _launch_event(snapshot: store_module.Snapshot) -> dict[str, Any]:
    launches = [event for event in snapshot.events if event.get("event") == "launch"]
    if len(launches) != 1:
        raise RuntimeError("launched action must have exactly one launch event")
    return launches[0]


def _process_group_alive(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _termination_payload(
    snapshot: store_module.Snapshot,
    launch_event: Mapping[str, Any],
    *,
    at: str,
    disposition: str,
) -> dict[str, Any]:
    identity = _normalize_launch_identity(dict(launch_event.get("detail", {})).get("identity"))
    payload = {
        "schema": "saga.external-action.termination.v1",
        "request_sha256": snapshot.request.request_sha256,
        "action_id": snapshot.request.action_id,
        "run_id": snapshot.request.run_id,
        "launch_event_sha256": launch_event["this_hash"],
        "launch_identity": identity,
        "terminated": True,
        "terminated_at": at,
        "disposition": disposition,
    }
    payload["receipt_sha256"] = contract.digest(payload)
    return payload


def _record_returned_termination(store: store_module.Store, *, at: str, disposition: str) -> None:
    snapshot = store_module.read_snapshot(store)
    launch_event = _launch_event(snapshot)
    identity = _normalize_launch_identity(dict(launch_event.get("detail", {})).get("identity"))
    if identity["transport"] == "cli" and _process_group_alive(identity["process_group"]):
        return
    store_module.write_termination(
        store,
        _termination_payload(snapshot, launch_event, at=at, disposition=disposition),
    )


def _terminate_launched_action(store: store_module.Store, *, at: str) -> dict[str, Any]:
    snapshot = store_module.read_snapshot(store)
    launch_event = _launch_event(snapshot)
    identity = _normalize_launch_identity(dict(launch_event.get("detail", {})).get("identity"))
    if identity["transport"] != "cli":
        raise RuntimeError("launched action has no supervised termination path")
    process_group = identity["process_group"]
    if _process_group_alive(process_group):
        os.killpg(process_group, signal.SIGKILL)
        for _ in range(100):
            try:
                os.waitpid(identity["pid"], os.WNOHANG)
            except ChildProcessError:
                pass
            if not _process_group_alive(process_group):
                break
            time.sleep(0.01)
    if _process_group_alive(process_group):
        raise RuntimeError("provider process group termination could not be confirmed")
    receipt = _termination_payload(
        snapshot,
        launch_event,
        at=at,
        disposition="runtime-kill-confirmed",
    )
    store_module.write_termination(store, receipt)
    return receipt


def _validated_termination_receipt(
    store: store_module.Store, snapshot: store_module.Snapshot
) -> dict[str, Any]:
    receipt = store_module.read_termination(store)
    if receipt is None:
        raise RuntimeError("retry requires a runtime termination receipt")
    launch_event = _launch_event(snapshot)
    required = {
        "schema",
        "request_sha256",
        "action_id",
        "run_id",
        "launch_event_sha256",
        "launch_identity",
        "terminated",
        "terminated_at",
        "disposition",
        "receipt_sha256",
    }
    if set(receipt) != required:
        raise RuntimeError("termination receipt fields are not closed")
    claimed = dict(receipt)
    claimed_hash = claimed.pop("receipt_sha256")
    expected_identity = _normalize_launch_identity(
        dict(launch_event.get("detail", {})).get("identity")
    )
    if (
        claimed_hash != contract.digest(claimed)
        or receipt.get("schema") != "saga.external-action.termination.v1"
        or receipt.get("request_sha256") != snapshot.request.request_sha256
        or receipt.get("action_id") != snapshot.request.action_id
        or receipt.get("run_id") != snapshot.request.run_id
        or receipt.get("launch_event_sha256") != launch_event.get("this_hash")
        or receipt.get("launch_identity") != expected_identity
        or receipt.get("terminated") is not True
    ):
        raise RuntimeError("termination receipt is not bound to the launched attempt")
    return receipt


def _retry_marker(store: store_module.Store, request: contract.ActionRequest) -> Path:
    return store.root.parents[1] / ".lineage" / request.action_id / f"{request.request_sha256}.json"


@contextmanager
def _lineage_lock(store: store_module.Store, request: contract.ActionRequest):
    lineage = _retry_marker(store, request).parent
    lineage.mkdir(parents=True, exist_ok=True)
    os.chmod(lineage, 0o700)
    lock = lineage / ".lock"
    with lock.open("a+", encoding="utf-8") as handle:
        os.chmod(lock, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(value, dict):
        raise RuntimeError("retry lineage marker is malformed")
    return value


def _write_retry_marker(
    marker: Path, request: contract.ActionRequest, new_run_id: str
) -> None:
    payload = contract.canonical_json(
        {
            "predecessor_request_sha256": request.request_sha256,
            "successor_run_id": new_run_id,
            "successor_attempt": request.attempt + 1,
        }
    ) + "\n"
    if marker.exists():
        if marker.read_text(encoding="utf-8") != payload:
            raise RuntimeError("retry successor already exists for predecessor")
        return
    descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _find_retry_successor(
    store: store_module.Store, request: contract.ActionRequest
) -> tuple[store_module.Store, contract.ActionRequest] | None:
    saga_root = store.root.parents[1]
    matches: list[tuple[store_module.Store, contract.ActionRequest]] = []
    for request_path in saga_root.glob(f"*/{request.action_id}/request.json"):
        candidate_store = store_module.Store(request_path.parent, store.repo_root)
        candidate = store_module.read_request(candidate_store)
        if candidate is None or candidate.predecessor_request_sha256 != request.request_sha256:
            continue
        matches.append((candidate_store, candidate))
    if len(matches) > 1:
        raise RuntimeError("multiple retry successors exist for predecessor")
    return matches[0] if matches else None


def _validate_evidence_artifact(
    snapshot: store_module.Snapshot,
    approval: contract.ActionApproval,
    path: Path,
) -> tuple[dict[str, Any], str]:
    content = path.read_bytes()
    artifact = json.loads(content)
    required = {
        "schema",
        "action_id",
        "engine_id",
        "variant",
        "intent",
        "evidence",
        "findings",
        "evidence_digest",
        "runner_receipt",
    }
    if not isinstance(artifact, dict) or set(artifact) != required:
        raise ValueError("evidence artifact fields are not closed")
    route = dict(approval.route)
    expected = {
        "schema": "external_action_evidence.v1",
        "action_id": snapshot.request.action_id,
        "engine_id": route.get("engine_id"),
        "variant": route.get("variant"),
        "intent": snapshot.request.intent,
    }
    for field, value in expected.items():
        if artifact.get(field) != value:
            raise ValueError(f"evidence artifact {field} is not approval-bound")
    evidence = artifact.get("evidence")
    if not isinstance(evidence, str) or artifact.get("evidence_digest") != reconcile.evidence_digest(evidence):
        raise ValueError("evidence digest is invalid")
    if not isinstance(artifact.get("findings"), list):
        raise ValueError("evidence findings must be a list")
    receipt = artifact.get("runner_receipt")
    if not isinstance(receipt, dict):
        raise ValueError("runner receipt is missing")
    problems = list(_receipt.validate_receipt(receipt))
    if problems:
        raise ValueError(f"runner receipt is invalid: {problems[0]}")
    if receipt.get("engine_id") != expected["engine_id"] or receipt.get("variant") != expected["variant"]:
        raise ValueError("runner receipt identity is not approval-bound")
    return artifact, hashlib.sha256(content).hexdigest()


def adjudicate(store: store_module.Store, *, accepted: bool, at: str, detail: Mapping[str, Any]) -> None:
    store_module.append_event(
        store,
        event_id="adjudicate-1",
        event="accept" if accepted else "reject",
        at=at,
        detail=dict(detail),
    )
    status_module.refresh(store)


def consume(store: store_module.Store, *, at: str, artifact_ref: str) -> None:
    store_module.append_event(
        store,
        event_id="consume-1",
        event="consume",
        at=at,
        detail={"artifact_ref": artifact_ref},
    )
    status_module.refresh(store)
