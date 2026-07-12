#!/usr/bin/env python3
"""Shared six-stage external-action lifecycle orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import external_action_policy as policy
import external_action_runtime as runtime
import external_action_status as status_module
import external_action_store as store_module
import reconcile


class LifecycleError(ValueError):
    """A stage bundle cannot progress without violating the action contract."""


@dataclass(frozen=True, slots=True)
class StageBundle:
    stage: str
    source: str
    actions: tuple[policy.ActionTemplate, ...]


@dataclass(frozen=True, slots=True)
class StageRun:
    outcomes: Mapping[str, runtime.ExecutionOutcome]
    paused_action_id: str | None
    status_cards: tuple[str, ...]


def inspect_bundle(
    stage: str,
    *,
    repo_root: Path,
    explicit_actions: Sequence[Mapping[str, Any]] | None = None,
) -> StageBundle:
    resolved = policy.resolve(stage, repo_root=repo_root, explicit_actions=explicit_actions)
    return StageBundle(stage=stage, source=resolved.source, actions=resolved.actions)


def bundle_payload(bundle: StageBundle) -> dict[str, Any]:
    return {
        "stage": bundle.stage,
        "source": bundle.source,
        "actions": [
            {
                "action_id": item.action_id,
                "intent": item.intent,
                "trigger": item.trigger,
                "requiredness": item.requiredness.value,
                "consumption_point": item.consumption_point,
                "provider_constraints": dict(item.provider_constraints),
                "context_scope": list(item.context_scope),
                "sensitivity": item.sensitivity,
                "write_set": list(item.write_set),
                "evidence_destination": item.evidence_destination,
            }
            for item in bundle.actions
        ],
    }


def prepare_bundle(
    bundle: StageBundle,
    *,
    repo_root: Path,
    saga_id: str,
    run_id: str,
    routes: Mapping[str, Mapping[str, Any]],
    payloads: Mapping[str, Any],
    cost_classes: Mapping[str, str],
    route_egress: Mapping[str, Mapping[str, Any]],
    base_revision: str,
    created_at: str,
    selected_action_ids: Sequence[str] | None = None,
    dirty_overlap: Mapping[str, tuple[str, ...]] | None = None,
) -> tuple[runtime.Preview, ...]:
    selected = set(selected_action_ids or (item.action_id for item in bundle.actions))
    actions = tuple(item for item in bundle.actions if item.action_id in selected)
    unknown = selected - {item.action_id for item in bundle.actions}
    if unknown:
        raise LifecycleError(f"unknown selected action(s): {', '.join(sorted(unknown))}")
    for item in actions:
        route = routes.get(item.action_id)
        if route is None:
            raise LifecycleError(f"missing route for action {item.action_id!r}")
        if route.get("halt"):
            raise LifecycleError(
                f"action bundle is unavailable before dispatch: {item.action_id}: {route['halt']}"
            )
        if item.action_id not in payloads or item.action_id not in cost_classes:
            raise LifecycleError(f"incomplete preparation inputs for action {item.action_id!r}")
    previews: list[runtime.Preview] = []
    for item in actions:
        route = dict(routes[item.action_id])
        route.setdefault("stage", bundle.stage)
        previews.append(
            runtime.prepare(
                repo_root=repo_root,
                saga_id=saga_id,
                run_id=run_id,
                template=item,
                route=route,
                cost_class=cost_classes[item.action_id],
                route_egress=route_egress.get(item.action_id, {}),
                base_revision=base_revision,
                payload=payloads[item.action_id],
                created_at=created_at,
                dirty_overlap=(dirty_overlap or {}).get(item.action_id, ()),
            )
        )
    return tuple(previews)


def approve_bundle(
    previews: Sequence[runtime.Preview],
    *,
    operator: str,
    approved_at: str,
) -> None:
    for preview in previews:
        runtime.approve(preview, operator=operator, approved_at=approved_at)


def approval_preview_payload(previews: Sequence[runtime.Preview]) -> list[dict[str, Any]]:
    """Render the immutable approval candidate and status before operator approval."""
    return [
        {
            "action_id": preview.request.action_id,
            "stage": preview.request.stage,
            "intent": preview.request.intent,
            "requiredness": preview.request.requiredness.value,
            "consumption_point": preview.request.consumption_point,
            "route": dict(preview.candidate_approval.route),
            "cost_class": preview.candidate_approval.cost_class,
            "egress": dict(preview.candidate_approval.egress),
            "context_scope": list(preview.candidate_approval.context_scope),
            "write_set": list(preview.candidate_approval.write_set),
            "base_revision": preview.candidate_approval.base_revision,
            "approval_fingerprint": preview.approval_fingerprint,
            "status_card": status_module.render(status_module.refresh(preview.store)),
        }
        for preview in previews
    ]


def status_cards(previews: Sequence[runtime.Preview]) -> tuple[str, ...]:
    return tuple(
        status_module.render(status_module.refresh(preview.store)) for preview in previews
    )


def execute_bundle(
    previews: Sequence[runtime.Preview],
    *,
    executors: Mapping[str, runtime.Executor],
    at: str,
) -> StageRun:
    missing = [
        preview.request.action_id
        for preview in previews
        if preview.request.action_id not in executors
    ]
    if missing:
        raise LifecycleError(f"missing executor for action {missing[0]!r}")
    not_approved = [
        preview.request.action_id
        for preview in previews
        if store_module.read_snapshot(preview.store).state.value != "approved"
    ]
    if not_approved:
        raise LifecycleError(f"action must be approved before execution: {not_approved[0]}")
    outcomes: dict[str, runtime.ExecutionOutcome] = {}
    paused: str | None = None
    for preview in previews:
        action_id = preview.request.action_id
        executor = executors[action_id]
        outcome = runtime.execute(preview.store, executor=executor, at=at)
        outcomes[action_id] = outcome
        if (
            outcome.status != "available"
            and preview.request.requiredness.value == "required-before-continue"
        ):
            paused = action_id
            break
    cards = status_cards(previews)
    return StageRun(outcomes=outcomes, paused_action_id=paused, status_cards=cards)


def load_action(
    *, repo_root: Path, saga_id: str, run_id: str, action_id: str
) -> runtime.Preview:
    return runtime.load_preview(
        repo_root=repo_root,
        saga_id=saga_id,
        run_id=run_id,
        action_id=action_id,
    )


def interrupt_action(
    preview: runtime.Preview,
    *,
    at: str,
    rationale: str,
    termination_proof: Mapping[str, Any] | None = None,
) -> None:
    runtime.interrupt(
        preview.store,
        at=at,
        rationale=rationale,
        termination_proof=termination_proof,
    )


def retry_action(
    preview: runtime.Preview,
    *,
    repo_root: Path,
    new_run_id: str,
    created_at: str,
) -> runtime.Preview:
    return runtime.retry(
        preview,
        repo_root=repo_root,
        new_run_id=new_run_id,
        created_at=created_at,
    )


def adjudicate_artifact(
    preview: runtime.Preview,
    *,
    accepted: bool,
    at: str,
    detail: Mapping[str, Any],
) -> None:
    if preview.request.intent != "offload":
        raise LifecycleError("artifact adjudication requires an offload action")
    runtime.adjudicate(preview.store, accepted=accepted, at=at, detail=detail)


def adjudicate_opinion(
    preview: runtime.Preview,
    outcome: runtime.ExecutionOutcome,
    *,
    decisions: Mapping[str, Mapping[str, str]],
    reconciliation_id: str,
    adjudicator_id: str,
    at: str,
) -> reconcile.ReconciliationResult:
    if preview.request.intent not in {"second-opinion", "divergence"}:
        raise LifecycleError("typed opinion adjudication requires an opinion action")
    detail = dict(outcome.detail or {})
    try:
        findings = reconcile.parse_source_findings(detail.get("findings"))
    except reconcile.ReconciliationError as exc:
        raise LifecycleError(f"typed opinion findings are malformed: {exc}") from exc
    expected = {item.source_finding_id for item in findings}
    if set(decisions) != expected:
        raise LifecycleError("typed adjudication must account for every source finding exactly once")
    items = tuple(
        reconcile.ReconciliationItem(
            source_finding_id=finding.source_finding_id,
            status=reconcile.ReconciliationStatus(decisions[finding.source_finding_id]["status"]),
            adjudicator_id=adjudicator_id,
            rationale=decisions[finding.source_finding_id]["rationale"],
        )
        for finding in findings
    )
    rendered = str(detail.get("evidence") or reconcile.render_source_findings(findings))
    result = reconcile.build_result(
        reconciliation_id=reconciliation_id,
        execution_id=preview.request.action_id,
        intent=preview.request.intent,
        adjudicator_id=adjudicator_id,
        evidence_digest=reconcile.evidence_digest(rendered),
        source_finding_ids=(item.source_finding_id for item in findings),
        items=items,
    )
    accepted = any(item.status.value in {"reconciled", "overridden"} for item in items)
    runtime.adjudicate(
        preview.store,
        accepted=accepted,
        at=at,
        detail={
            "reconciliation_id": result.reconciliation_id,
            "evidence_digest": result.evidence_digest,
            "items": [
                {
                    "source_finding_id": item.source_finding_id,
                    "status": item.status.value,
                    "adjudicator_id": item.adjudicator_id,
                    "rationale": item.rationale,
                }
                for item in result.items
            ],
        },
    )
    return result


def consume(preview: runtime.Preview, *, at: str, artifact_ref: str) -> None:
    runtime.consume(preview.store, at=at, artifact_ref=artifact_ref)
