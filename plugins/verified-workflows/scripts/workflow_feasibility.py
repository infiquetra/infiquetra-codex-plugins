#!/usr/bin/env python3
"""Review a Workflow Contract against the Codex V2 capability projection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import protocol_probe as probe
import workflow_dispatch as dispatch


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs" / "validation" / "codex-runtime-capability-snapshot.json"
REQUIRED_SPAWN_FIELDS = {
    "agent_type",
    "fork_turns",
    "message",
    "model",
    "reasoning_effort",
    "task_name",
}
REQUIRED_READBACK_FIELDS = {
    "agent_path",
    "agent_role",
    "model",
    "reasoning_effort",
    "model_provider",
    "approval_policy",
    "permission_profile",
    "sandbox_policy",
    "multi_agent_version",
}


class WorkflowFeasibilityError(ValueError):
    """Raised when a contract or capability projection cannot be reviewed safely."""


def _collaboration_projection(snapshot: dict[str, Any]) -> dict[str, Any]:
    collaboration = snapshot.get("collaboration")
    if not isinstance(collaboration, dict):
        raise WorkflowFeasibilityError("capability snapshot collaboration must be an object")
    spawn = collaboration.get("spawn")
    if not isinstance(spawn, dict):
        raise WorkflowFeasibilityError("capability snapshot collaboration.spawn must be an object")
    if spawn.get("available") is not True or spawn.get("contract_version") != "v2":
        raise WorkflowFeasibilityError("Codex V2 configured-agent spawning is not available")
    if spawn.get("tool_namespace") != "agents" or spawn.get("per_child_agent_type") is not True:
        raise WorkflowFeasibilityError("Codex V2 named profile selection is not source-confirmed")
    request_fields = spawn.get("request_fields")
    readback_fields = spawn.get("selection_readback_fields")
    if not isinstance(request_fields, list) or not REQUIRED_SPAWN_FIELDS <= set(request_fields):
        raise WorkflowFeasibilityError("Codex V2 spawn request fields are incomplete")
    if not isinstance(readback_fields, list) or not REQUIRED_READBACK_FIELDS <= set(readback_fields):
        raise WorkflowFeasibilityError("Codex V2 runtime readback fields are incomplete")
    if spawn.get("profile_selection_fork_turns") != ["none", "positive-integer"]:
        raise WorkflowFeasibilityError("Codex V2 bounded context projection drifted")
    context = collaboration.get("context")
    if not isinstance(context, dict) or context.get("child_permissions_inherit_parent_turn") is not True:
        raise WorkflowFeasibilityError("Codex V2 child permission inheritance is not declared")
    return spawn


def review_workflow(
    *,
    plan: Path,
    snapshot_path: Path = DEFAULT_SNAPSHOT,
    plan_revision: str | None = None,
) -> dict[str, Any]:
    """Return a read-only feasibility result; never launch or configure Codex."""

    try:
        contract = dispatch.compile_plan(plan, plan_revision=plan_revision)
    except dispatch.WorkflowDispatchError as exc:
        raise WorkflowFeasibilityError(str(exc)) from exc
    try:
        snapshot, snapshot_sha256 = probe._read_snapshot(snapshot_path)
    except probe.ProtocolProbeError as exc:
        raise WorkflowFeasibilityError(str(exc)) from exc
    spawn = _collaboration_projection(snapshot)

    rows: list[dict[str, Any]] = []
    for spec in contract.launch_specs:
        if spec.agent_type is None:
            disposition = "root-owned"
            limitation = "root execution has no child receipt"
        elif spec.parent.startswith("fresh-root:"):
            disposition = "fresh-review-root-required"
            limitation = "the separately started review-root identity must be validated at runtime"
        else:
            disposition = "v2-launch-ready"
            limitation = "requested configuration remains provisional until session_meta plus turn_context readback"
        rows.append(
            {
                "assignment_id": spec.assignment_id,
                "parent": spec.parent,
                "role": spec.role,
                "profile": spec.agent_type or "root",
                "model": spec.model,
                "effort": spec.reasoning_effort,
                "fork_turns": spec.fork_turns,
                "result_schema": spec.result_schema,
                "disposition": disposition,
                "limitation": limitation,
            }
        )

    return {
        "schema_version": 2,
        "outcome": "ready",
        "runtime_proof": False,
        "plan_revision": contract.plan_revision,
        "contract_sha256": contract.contract_sha256,
        "approval_binding_sha256": contract.approval_binding_sha256,
        "capability_snapshot_sha256": snapshot_sha256,
        "spawn_surface": spawn["tool_namespace"],
        "rows": rows,
        "external_actions": len(contract.external_actions),
        "findings": [],
        "limitation": (
            "this review proves compile-time compatibility only; exact profile, model, effort, provider, "
            "permission, path, and restoration remain runtime readback gates"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--plan-revision")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = review_workflow(
            plan=args.plan,
            snapshot_path=args.snapshot,
            plan_revision=args.plan_revision,
        )
    except (OSError, WorkflowFeasibilityError) as exc:
        print(f"workflow feasibility review failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
