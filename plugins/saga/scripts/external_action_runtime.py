#!/usr/bin/env python3
"""Provider-neutral prepare, approve, execute, adjudicate, and consume runtime."""

from __future__ import annotations

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
) -> Preview:
    sanitized = egress.sanitize(payload)
    if sanitized.blocked:
        raise RuntimeError(f"outbound payload blocked: {', '.join(sanitized.detections)}")
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
    )
    candidate = contract.ActionApproval(
        action_id=request.action_id,
        approved_at="preview",
        operator="preview",
        route=dict(route),
        context_scope=request.context_scope,
        sensitivity=request.sensitivity,
        base_revision=base_revision,
        write_set=request.write_set,
        cost_class=cost_class,
        egress=dict(route_egress),
        request_sha256=request.request_sha256,
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
            "dirty_overlap": list(dirty_overlap),
        },
    )
    status_module.refresh(store)
    return Preview(store, request, candidate, candidate.approval_fingerprint, sanitized.payload, sanitized.detections)


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
        store_module.append_event(
            store, event_id="terminal-1", event=event, at=at, detail={"error_type": type(exc).__name__}
        )
        status_module.refresh(store)
        return ExecutionOutcome("invalid-evidence" if launched else "unavailable")
    if not launched:
        store_module.append_event(store, event_id="terminal-1", event="unavailable", at=at)
        status_module.refresh(store)
        return ExecutionOutcome("unavailable")
    if outcome.status != "available" or not outcome.evidence_ref:
        store_module.append_event(store, event_id="terminal-1", event="invalidate-evidence", at=at)
        status_module.refresh(store)
        return ExecutionOutcome("invalid-evidence", detail=outcome.detail)
    store_module.append_event(
        store,
        event_id="complete-1",
        event="complete",
        at=at,
        detail={"evidence_ref": outcome.evidence_ref, **dict(outcome.detail or {})},
    )
    status_module.refresh(store)
    return outcome


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
