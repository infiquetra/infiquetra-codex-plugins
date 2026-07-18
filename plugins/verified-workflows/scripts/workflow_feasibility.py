#!/usr/bin/env python3
"""Review whether a Workflow Structure can satisfy its selected evidence contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import protocol_probe as probe
import workflow_dispatch as dispatch


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs" / "validation" / "codex-runtime-capability-snapshot.json"


class WorkflowFeasibilityError(ValueError):
    """Raised when a plan or capability projection cannot be reviewed safely."""


def _read_plan(path: Path) -> tuple[str, str]:
    try:
        content = dispatch._read_bounded(path, dispatch.MAX_PLAN_BYTES, "workflow plan")
    except dispatch.WorkflowDispatchError as exc:
        raise WorkflowFeasibilityError(str(exc)) from exc
    try:
        return content.decode("utf-8"), hashlib.sha256(content).hexdigest()
    except UnicodeDecodeError as exc:
        raise WorkflowFeasibilityError("workflow plan is not valid UTF-8") from exc


def _parse_workflow(text: str) -> dispatch.Workflow:
    try:
        return dispatch.parse_workflow_structure(text)
    except (dispatch.WorkflowDispatchError, dispatch.renderer.RoleRegistryError) as exc:
        raise WorkflowFeasibilityError(str(exc)) from exc


def _validate_capability_projection(snapshot: dict[str, Any]) -> None:
    """Reject malformed known fields and unsupported claims without closing unknown extensions."""

    collaboration = snapshot.get("collaboration")
    if collaboration is not None and not isinstance(collaboration, dict):
        raise WorkflowFeasibilityError("capability snapshot collaboration must be an object")
    if not isinstance(collaboration, dict):
        return
    spawn = collaboration.get("spawn")
    if spawn is not None and not isinstance(spawn, dict):
        raise WorkflowFeasibilityError("capability snapshot collaboration.spawn must be an object")
    if isinstance(spawn, dict) and "host_issued_child_attestation" in spawn:
        attestation = spawn["host_issued_child_attestation"]
        if not isinstance(attestation, bool):
            raise WorkflowFeasibilityError("host-issued child attestation must be a boolean")
        if attestation:
            raise WorkflowFeasibilityError("host-issued child attestation is unsupported by this reviewer")


def _agent_row(step: dispatch.WorkflowStep, capability: dict[str, Any]) -> dict[str, Any]:
    row = {
        "step_id": step.step_id,
        "role_kind": step.role_kind,
        "vehicle": step.vehicle,
        "independence": step.independence,
        "requested_execution_class": step.execution_class,
        "runtime_agent_name": step.runtime_agent_name,
        "spawn_surface": capability["spawn_surface"],
    }
    if step.independence == "required":
        return {
            **row,
            "disposition": "strict-child-unavailable",
            "required_amendment": "provide host-issued child attestation or remove the strict contract",
            "limitation": "the capability projection does not prove a host-attested child",
        }
    if step.vehicle == "inline":
        return {
            **row,
            "disposition": "gate-authoritative-root-inline",
            "required_amendment": None,
            "limitation": (
                "logical role is root-executed; child model, effort, sandbox, and permission "
                "boundary are not observed"
            ),
        }
    return {
        **row,
        "disposition": "advisory-child-only",
        "required_amendment": "change vehicle to inline for gate authority",
        "limitation": (
            "a native child may provide advisory evidence, but this capability projection does not "
            "prove host-issued child attestation"
        ),
    }


def review_workflow(
    *,
    plan: Path,
    snapshot_path: Path = DEFAULT_SNAPSHOT,
) -> dict[str, Any]:
    """Return a closed feasibility result without launching or configuring Codex."""

    plan_text, plan_sha256 = _read_plan(plan)
    workflow = _parse_workflow(plan_text)
    try:
        snapshot, snapshot_sha256 = probe._read_snapshot(snapshot_path)
    except probe.ProtocolProbeError as exc:
        raise WorkflowFeasibilityError(str(exc)) from exc
    _validate_capability_projection(snapshot)

    rows: list[dict[str, Any]] = []
    for step in workflow.steps:
        if step.role_kind == "root":
            rows.append(
                {
                    "step_id": step.step_id,
                    "role_kind": "root",
                    "vehicle": "root",
                    "disposition": "root-owned",
                    "required_amendment": None,
                    "limitation": "root owns authority and completion",
                }
            )
            continue
        if step.role_kind == "deterministic-validator":
            rows.append(
                {
                    "step_id": step.step_id,
                    "role_kind": "deterministic-validator",
                    "vehicle": "deterministic-tool",
                    "disposition": "deterministic-gate-capable",
                    "required_amendment": None,
                    "limitation": "deterministic evidence contains no model or child claim",
                }
            )
            continue
        capability = probe.probe_protocol(
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            independence=str(step.independence),
            role_kind="agent-lens",
        )
        rows.append(_agent_row(step, capability))

    dispositions = {row["disposition"] for row in rows}
    if "strict-child-unavailable" in dispositions:
        outcome = "strict-unavailable"
    elif "advisory-child-only" in dispositions:
        outcome = "requires-inline"
    else:
        outcome = "ready"
    findings = [
        row
        for row in rows
        if row["disposition"] in {"strict-child-unavailable", "advisory-child-only"}
    ]
    return {
        "schema_version": 1,
        "outcome": outcome,
        "plan_sha256": plan_sha256,
        "capability_snapshot_sha256": snapshot_sha256,
        "runtime_proof": False,
        "rows": rows,
        "findings": findings,
        "limitation": (
            "the capability snapshot describes requested configuration only; it does not prove an "
            "observed child model, effort, sandbox, permission boundary, or host-issued attestation"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = review_workflow(plan=args.plan, snapshot_path=args.snapshot)
    except (OSError, WorkflowFeasibilityError) as exc:
        print(f"workflow feasibility review failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["outcome"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
