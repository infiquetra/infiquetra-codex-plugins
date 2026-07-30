#!/usr/bin/env python3
"""Reduce typed V2 results and deterministic checks into one root gate decision."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import result_contract
import workflow_dispatch as dispatch


MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_REMEDIATION_ROUNDS = 1
CHECK_STATUSES = {"pass", "warn", "failed", "blocked"}
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
AGENT_PATH_RE = re.compile(r"^/root(?:/[a-zA-Z0-9][a-zA-Z0-9_-]{0,127})+$")
ATTEMPT_AUTHORITY_FIELDS = {
    "attempt_id",
    "session_id",
    "agent_path",
    "parent_thread_id",
    "execution_root_id",
    "runtime_receipt_sha256",
    "registry_sha256",
    "role_lens_sha256",
    "profile_sha256",
}


class GateEvaluationError(ValueError):
    """Raised when gate input is malformed or attempts to bypass authority."""


def _check_outcome(value: object, check_id: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"status", "detail"}:
        raise GateEvaluationError(f"check {check_id} outcome fields are not closed")
    status = value.get("status")
    detail = value.get("detail")
    if status not in CHECK_STATUSES or not isinstance(detail, str) or not detail.strip():
        raise GateEvaluationError(f"check {check_id} outcome is invalid")
    return {"status": status, "detail": detail.strip()}


def _root_finding(value: object, index: int) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"finding", "verified", "source"}:
        raise GateEvaluationError(f"adopted root finding {index} fields are not closed")
    if value["verified"] is not True:
        raise GateEvaluationError(f"adopted root finding {index} is not independently verified")
    if not isinstance(value["source"], str) or not value["source"].strip():
        raise GateEvaluationError(f"adopted root finding {index}.source is invalid")
    try:
        finding = result_contract.validate_finding(
            value["finding"], where=f"adopted root finding {index}"
        )
    except result_contract.ResultContractError as exc:
        raise GateEvaluationError(str(exc)) from exc
    return {**finding, "source": value["source"].strip(), "authority": "root-adopted"}


def _validate_reviewer_result(
    result: Mapping[str, Any],
    assignment_id: str,
    *,
    expected_mandates: Sequence[str],
) -> list[str]:
    dimensions = result.get("dimensions")
    exclusions = result.get("exclusions")
    if not isinstance(dimensions, list) or not dimensions:
        raise GateEvaluationError(f"reviewer {assignment_id} has no applicable dimensions")
    if not isinstance(exclusions, list):
        raise GateEvaluationError(f"reviewer {assignment_id} exclusions are invalid")
    observed_mandates = [
        item.get("dimension_id")
        for item in [*dimensions, *exclusions]
        if isinstance(item, dict)
    ]
    if (
        len(observed_mandates) != len(dimensions) + len(exclusions)
        or len(observed_mandates) != len(set(observed_mandates))
        or set(observed_mandates) != set(expected_mandates)
    ):
        raise GateEvaluationError(
            f"reviewer {assignment_id} mandate roster does not match its approved role lens"
        )
    scores = [item.get("score") for item in dimensions if isinstance(item, dict)]
    if len(scores) != len(dimensions) or any(
        isinstance(score, bool) or not isinstance(score, (int, float)) for score in scores
    ):
        raise GateEvaluationError(f"reviewer {assignment_id} scores are invalid")
    denominator = result.get("denominator")
    overall = result.get("overall")
    expected = sum(float(score) for score in scores) / len(scores)
    if denominator != len(scores) or not isinstance(overall, (int, float)) or isinstance(overall, bool):
        raise GateEvaluationError(f"reviewer {assignment_id} arithmetic is invalid")
    if not math.isclose(float(overall), expected, abs_tol=1e-9):
        raise GateEvaluationError(f"reviewer {assignment_id} arithmetic is invalid")
    issues: list[str] = []
    if result.get("hard_stop") is True:
        issues.append(f"reviewer {assignment_id} declared a role hard stop")
    if result.get("verdict") != "accept":
        issues.append(f"reviewer {assignment_id} verdict is {result.get('verdict')!r}")
    return issues


def _attempt_authority(
    value: object,
    assignment_id: str,
    launch: dispatch.LaunchSpec,
) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != ATTEMPT_AUTHORITY_FIELDS:
        raise GateEvaluationError(
            f"attempt authority {assignment_id} fields are not closed"
        )
    normalized: dict[str, str] = {}
    for field in ATTEMPT_AUTHORITY_FIELDS:
        item = value.get(field)
        if not isinstance(item, str) or not item.strip():
            raise GateEvaluationError(f"attempt authority {assignment_id}.{field} is invalid")
        normalized[field] = item.strip()
    if AGENT_PATH_RE.fullmatch(normalized["agent_path"]) is None:
        raise GateEvaluationError(f"attempt authority {assignment_id}.agent_path is not canonical")
    for field in (
        "runtime_receipt_sha256",
        "registry_sha256",
        "role_lens_sha256",
        "profile_sha256",
    ):
        if HEX64_RE.fullmatch(normalized[field]) is None:
            raise GateEvaluationError(f"attempt authority {assignment_id}.{field} is invalid")
    expected = {
        "registry_sha256": launch.registry_sha256,
        "role_lens_sha256": launch.role_lens_sha256,
        "profile_sha256": launch.profile_sha256,
    }
    for field, expected_value in expected.items():
        if normalized[field] != expected_value:
            raise GateEvaluationError(
                f"attempt authority {assignment_id}.{field} does not match the approved launch"
            )
    return normalized


def _finding_issue(finding: Mapping[str, Any], *, revalidated: set[str]) -> str | None:
    finding_id = str(finding["finding_id"])
    if finding.get("resolved") is True:
        if finding_id not in revalidated:
            return f"finding {finding_id} is marked resolved without fresh focused revalidation"
        return None
    if finding["severity"] in {"P0", "P1"}:
        return f"unresolved {finding['severity']} finding {finding_id}"
    if finding["hard_stop"] is True:
        return f"unresolved role hard stop {finding_id}"
    if finding["scope_disposition"] == "approval-required":
        return f"finding {finding_id} requires operator approval before broader work"
    if finding["scope_disposition"] == "defer":
        return None
    return f"unresolved {finding['severity']} finding {finding_id}"


def evaluate_gate(
    contract: dispatch.WorkflowContract,
    *,
    results: Mapping[str, object],
    attempt_authorities: Mapping[str, object],
    check_outcomes: Mapping[str, object],
    implementation_root_identity: str,
    adopted_root_findings: Sequence[object] = (),
    remediation_round: int = 0,
    revalidated_finding_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Return pass, block, or escalate from closed root-orchestrated gate inputs."""

    if isinstance(remediation_round, bool) or not isinstance(remediation_round, int):
        raise GateEvaluationError("remediation_round must be an integer")
    if not 0 <= remediation_round <= MAX_REMEDIATION_ROUNDS:
        raise GateEvaluationError("more than one remediation round is forbidden")
    if not implementation_root_identity.strip():
        raise GateEvaluationError("implementation root identity is required")
    expected_children = {
        spec.assignment_id: spec for spec in contract.launch_specs if spec.agent_type is not None
    }
    if set(results) != set(expected_children):
        raise GateEvaluationError(
            "typed result set must exactly cover delegated assignments: "
            f"missing={sorted(set(expected_children) - set(results))} "
            f"unexpected={sorted(set(results) - set(expected_children))}"
        )
    if set(attempt_authorities) != set(expected_children):
        raise GateEvaluationError(
            "attempt authority set must exactly cover delegated assignments: "
            f"missing={sorted(set(expected_children) - set(attempt_authorities))} "
            f"unexpected={sorted(set(attempt_authorities) - set(expected_children))}"
        )

    authorities = {
        assignment_id: _attempt_authority(
            attempt_authorities[assignment_id], assignment_id, launch
        )
        for assignment_id, launch in expected_children.items()
    }
    assignments = {assignment.assignment_id: assignment for assignment in contract.assignments}
    for assignment_id, authority in authorities.items():
        assignment = assignments[assignment_id]
        if assignment.parent != "root":
            raise GateEvaluationError(
                f"assignment {assignment_id} is not a direct child of root"
            )
        expected_parent = implementation_root_identity
        expected_root = implementation_root_identity
        expected_path = f"/root/{assignment_id}"
        if authority["parent_thread_id"] != expected_parent:
            raise GateEvaluationError(
                f"attempt authority {assignment_id} parent thread does not match the approved graph"
            )
        if authority["execution_root_id"] != expected_root:
            raise GateEvaluationError(
                f"attempt authority {assignment_id} execution root does not match the approved graph"
            )
        if authority["agent_path"] != expected_path:
            raise GateEvaluationError(
                f"attempt authority {assignment_id} agent path does not match the approved graph"
            )

    issues: list[str] = []
    hard_stops: list[str] = []
    normalized_results: dict[str, dict[str, Any]] = {}
    for assignment_id, launch in expected_children.items():
        raw = results[assignment_id]
        if not isinstance(raw, dict):
            raise GateEvaluationError(f"result {assignment_id} must be a typed object")
        authority = authorities[assignment_id]
        try:
            normalized = result_contract.validate_result(
                raw,
                launch,
                expected_attempt_id=authority["attempt_id"],
                expected_agent_path=authority["agent_path"],
            )
        except result_contract.ResultContractError as exc:
            raise GateEvaluationError(str(exc)) from exc
        normalized_results[assignment_id] = normalized
        if normalized["terminal_status"] != "completed":
            issues.append(
                f"assignment {assignment_id} terminal status is {normalized['terminal_status']}"
            )
        if launch.result_schema == "reviewer-result.v1":
            issues.extend(
                _validate_reviewer_result(
                    normalized,
                    assignment_id,
                    expected_mandates=launch.reviewer_mandate_ids,
                )
            )

    independent_reviewers = [
        assignment
        for assignment in contract.assignments
        if assignment.is_independent_review
    ]
    if not independent_reviewers:
        hard_stops.append("no independent direct-sibling reviewer is selected")
    paths_seen: set[str] = set()
    implementation_paths = {
        authorities[assignment.assignment_id]["agent_path"]
        for assignment in contract.assignments
        if assignment.category in {"worker", "tester", "git-operator"}
    }
    for reviewer in independent_reviewers:
        reviewer_path = authorities[reviewer.assignment_id]["agent_path"]
        if reviewer_path in paths_seen or any(
            reviewer_path.startswith(f"{path}/") for path in implementation_paths
        ):
            hard_stops.append(f"reviewer {reviewer.assignment_id} is not independent")
        paths_seen.add(reviewer_path)

    expected_checks = {check.check_id: check for check in contract.checks}
    unexpected_checks = set(check_outcomes) - set(expected_checks)
    if unexpected_checks:
        raise GateEvaluationError(f"unexpected check outcomes {sorted(unexpected_checks)}")
    normalized_checks: dict[str, dict[str, str]] = {}
    for check_id, check in expected_checks.items():
        raw = check_outcomes.get(check_id)
        if raw is None:
            if check.blocking:
                hard_stops.append(f"blocking check {check_id} is missing")
            continue
        outcome = _check_outcome(raw, check_id)
        normalized_checks[check_id] = outcome
        if check.blocking and outcome["status"] != "pass":
            hard_stops.append(f"blocking check {check_id} is {outcome['status']}")

    revalidated = set(revalidated_finding_ids)
    all_findings: list[dict[str, Any]] = [
        finding
        for result in normalized_results.values()
        for finding in result["findings"]
    ]
    all_findings.extend(
        _root_finding(value, index) for index, value in enumerate(adopted_root_findings)
    )
    one_hop_findings = [
        finding for finding in all_findings if finding["scope_disposition"] == "one-hop"
    ]
    if len(one_hop_findings) > 1:
        hard_stops.append(
            "more than one unplanned one-hop finding requires operator approval"
        )
    approval_required = any(
        finding["scope_disposition"] == "approval-required"
        and finding.get("resolved") is not True
        for finding in all_findings
    ) or len(one_hop_findings) > 1
    for finding in all_findings:
        issue = _finding_issue(finding, revalidated=revalidated)
        if issue is not None:
            if (
                finding["severity"] in {"P0", "P1"}
                or finding["hard_stop"] is True
                or finding["scope_disposition"] == "approval-required"
            ):
                hard_stops.append(issue)
            else:
                issues.append(issue)

    if remediation_round > 0:
        focused = normalized_checks.get("focused")
        if focused is None or focused["status"] != "pass":
            hard_stops.append("fresh focused revalidation is required after remediation")

    blockers = sorted(set(hard_stops + issues))
    actionable_finding_remains = any(
        finding.get("resolved") is not True
        and finding["scope_disposition"] != "defer"
        for finding in all_findings
    )
    if approval_required:
        verdict = "escalate"
        next_round = None
    elif (
        blockers
        and remediation_round >= MAX_REMEDIATION_ROUNDS
        and actionable_finding_remains
    ):
        verdict = "escalate"
        next_round = None
    elif blockers:
        verdict = "block"
        next_round = remediation_round + 1
    else:
        verdict = "pass"
        next_round = None
    return {
        "schema_version": 3,
        "verdict": verdict,
        "contract_sha256": contract.contract_sha256,
        "authority_sha256": contract.authority_sha256,
        "approval_binding_sha256": contract.approval_binding_sha256,
        "remediation_round": remediation_round,
        "next_remediation_round": next_round,
        "blocking_reasons": blockers,
        "checks": normalized_checks,
        "reviewers": sorted(reviewer.assignment_id for reviewer in independent_reviewers),
        "finding_count": len(all_findings),
        "deviation_used": bool(one_hop_findings),
        "root_release": verdict == "pass",
    }


def _read_input(path: Path) -> dict[str, Any]:
    content = dispatch._read_bounded(path, MAX_INPUT_BYTES, "gate input")
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateEvaluationError("gate input is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise GateEvaluationError("gate input must be an object")
    expected = {
        "results",
        "attempt_authorities",
        "check_outcomes",
        "implementation_root_identity",
        "adopted_root_findings",
        "remediation_round",
        "revalidated_finding_ids",
    }
    if set(payload) != expected:
        raise GateEvaluationError(f"gate input fields must be exactly {sorted(expected)}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-revision", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        contract = dispatch.compile_plan(args.plan, plan_revision=args.plan_revision)
        payload = _read_input(args.input)
        result = evaluate_gate(contract, **payload)
    except (OSError, dispatch.WorkflowDispatchError, GateEvaluationError) as exc:
        print(f"workflow gate evaluation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
