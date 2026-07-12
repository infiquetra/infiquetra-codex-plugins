#!/usr/bin/env python3
"""Provider-neutral prepare, approve, execute, adjudicate, and consume runtime."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
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


Executor = Callable[[contract.ActionRequest, contract.ActionApproval, Callable[[], None]], ExecutionOutcome]


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

    def acknowledge_launch() -> None:
        nonlocal launched
        if not launched:
            store_module.append_event(store, event_id="launch-1", event="launch", at=at)
            launched = True

    try:
        outcome = executor(snapshot.request, snapshot.approval, acknowledge_launch)
    except TimeoutError:
        event = "timeout" if launched else "unavailable"
        store_module.append_event(store, event_id="terminal-1", event=event, at=at)
        status_module.refresh(store)
        return ExecutionOutcome("timed-out" if launched else "unavailable")
    except Exception as exc:
        event = "invalidate-evidence" if launched else "unavailable"
        detail = {"error_type": type(exc).__name__}
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
        store_module.append_event(store, event_id="terminal-1", event="invalidate-evidence", at=at)
        status_module.refresh(store)
        return ExecutionOutcome("invalid-evidence", detail={"reason": "artifact digest mismatch"})
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
    proof = dict(termination_proof or {})
    if launched and (
        proof.get("terminated") is not True
        or not re.fullmatch(r"[0-9a-f]{64}", str(proof.get("receipt_sha256") or ""))
    ):
        raise RuntimeError("launched action interruption requires termination proof")
    store_module.append_event(
        store,
        event_id="interrupt-1",
        event="interrupt",
        at=at,
        rationale=rationale,
        detail={"launched": launched, "termination_proof": proof},
    )
    status_module.refresh(store)


def retry(
    preview: Preview, *, repo_root: Path, new_run_id: str, created_at: str
) -> Preview:
    """Create a fresh immutable attempt after an explicit terminal failure."""
    snapshot = store_module.read_snapshot(preview.store)
    if snapshot.state not in contract.TERMINAL_FAILURE_STATES:
        raise RuntimeError("retry requires a terminal failed or interrupted attempt")
    request = snapshot.request
    approval = snapshot.approval or preview.candidate_approval
    _claim_retry_successor(preview.store, request, new_run_id)
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
    retry_store = store_module.Store.for_action(
        saga_id=retry_request.saga_id,
        run_id=retry_request.run_id,
        action_id=retry_request.action_id,
        repo_root=repo_root,
    )
    store_module.write_request(retry_store, retry_request)
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
            "predecessor_request_sha256": request.request_sha256,
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
        return ()
    dirty: list[str] = []
    for record in process.stdout.split("\0"):
        if not record:
            continue
        path = record[3:].split(" -> ")[-1]
        if any(path == scope or path.startswith(scope.rstrip("/") + "/") for scope in scopes):
            dirty.append(path)
    return tuple(sorted(set(dirty)))


def _claim_retry_successor(
    store: store_module.Store, request: contract.ActionRequest, new_run_id: str
) -> None:
    lineage = store.root.parents[1] / ".lineage" / request.action_id
    lineage.mkdir(parents=True, exist_ok=True)
    os.chmod(lineage, 0o700)
    marker = lineage / f"{request.request_sha256}.json"
    payload = contract.canonical_json(
        {
            "predecessor_request_sha256": request.request_sha256,
            "successor_run_id": new_run_id,
            "successor_attempt": request.attempt + 1,
        }
    ) + "\n"
    try:
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("retry successor already exists for predecessor") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


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
