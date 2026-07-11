#!/usr/bin/env python3
"""Evaluate Verified Workflows evidence with severity-first hard-failure precedence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import dispatch_receipt as receipts  # noqa: E402
import workflow_dispatch as dispatch  # noqa: E402

MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_STEPS = 128
MAX_FINDINGS = 1024
MAX_CYCLES = 3
MAX_FUTURE_SKEW = dt.timedelta(minutes=5)
SAFE_REF = re.compile(r"^[a-z0-9][a-z0-9._:/-]{0,127}$")
RECEIPT_REF = re.compile(r"^[a-z0-9][a-z0-9._:/-]{0,511}$")
SEVERITIES = {"P0", "P1", "P2", "P3"}
VEHICLES = {
    "verified-workflow-subagent",
    "verified-workflow-inline",
    "deterministic-tool",
    "root",
    "generic-subagent",
}
INDEPENDENCE = {"required", "preferred", "n/a"}
VALIDATOR_STATUSES = {
    "pass",
    "warn",
    "hard-fail",
    "blocked",
    "skipped-by-config",
    "not-applicable",
}
ADVISORY_SEATS = {"external-advisory", "external-second-opinion"}
SELF_PATHS = (
    "plugins/verified-workflows",
    "scripts/prove_verified_workflows_runtime.py",
    "scripts/validate_codex_plugins.py",
    "tests/test_prove_verified_workflows_runtime.py",
    "tests/test_validate_codex_plugins.py",
    "docs/portability/ports/2026-07-10-saga-07517.json",
)
SELF_PATHS_CASEFOLDED = tuple(value.rstrip("/").casefold() for value in SELF_PATHS)
SELF_PREFIXES_CASEFOLDED = (
    "tests/test_verified_workflows",
    "docs/validation/verified-workflows",
)


class GateEvaluationError(ValueError):
    """Raised when gate evidence is malformed, ambiguous, or untrusted."""


def _read_bounded(path: Path) -> object:
    try:
        content = dispatch._read_bounded(path, MAX_INPUT_BYTES, "gate input")
    except dispatch.WorkflowDispatchError as exc:
        raise GateEvaluationError(str(exc)) from exc
    try:
        return json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateEvaluationError("gate input is not valid UTF-8 JSON") from exc


def _closed(value: object, fields: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise GateEvaluationError(f"{where} fields are not closed")
    return value


def _safe_ref(value: object, where: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if (
        not isinstance(value, str)
        or not SAFE_REF.fullmatch(value)
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise GateEvaluationError(f"{where} is invalid")
    return value


def _receipt_ref(value: object, where: str) -> str:
    if not isinstance(value, str) or not RECEIPT_REF.fullmatch(value):
        raise GateEvaluationError(f"{where} is invalid")
    return value


def _finding(raw: object, step_id: str) -> dict[str, Any]:
    value = _closed(
        raw,
        {
            "finding_id",
            "severity",
            "category",
            "location",
            "impact",
            "fix",
            "validation",
            "resolved",
            "hard_stop",
        },
        f"finding for {step_id}",
    )
    _safe_ref(value["finding_id"], f"finding for {step_id}.finding_id")
    if value["severity"] not in SEVERITIES:
        raise GateEvaluationError(f"finding for {step_id}.severity is invalid")
    category = _safe_ref(value["category"], f"finding for {step_id}.category")
    if category not in dispatch.renderer.NESTED_TYPE_CONTRACTS[
        "typed-finding"
    ]["enum_fields"]["category"]:
        raise GateEvaluationError(f"finding for {step_id}.category is invalid")
    if any(
        not isinstance(value[field], str) or not value[field].strip()
        for field in ("location", "impact", "fix", "validation")
    ):
        raise GateEvaluationError(f"finding for {step_id} detail is invalid")
    if not isinstance(value["resolved"], bool) or not isinstance(value["hard_stop"], bool):
        raise GateEvaluationError(f"finding for {step_id} booleans are invalid")
    return {**value, "category": category}


def evaluate_gate(
    payload: object,
    *,
    workflow: dispatch.Workflow,
    plugin_data: Path,
    workspace_root: Path,
    registry: dispatch.renderer.RoleRegistry | None = None,
    enforce_selection_policy: bool = True,
) -> dict[str, Any]:
    """Evaluate the exact workflow from protected receipt/result records."""

    registry = registry or dispatch.renderer.load_role_registry()
    selection = (
        dispatch.validate_selection_policy(workflow, registry)
        if enforce_selection_policy
        else {
            "review_mode": "unit-fixture-partial",
            "base_reviewer_ids": [],
            "selected_role_ids": sorted({step.role_id for step in workflow.steps}),
            "required_validator_step_ids": [],
            "policy_sha256": dispatch._canonical_sha256(
                registry.source_behavior_policy
            ),
        }
    )
    root = _closed(
        payload,
        {
            "schema_version",
            "workflow_sha256",
            "cycle",
            "subject_ref",
            "steps",
            "advisory",
        },
        "gate input",
    )
    if root["schema_version"] != 1 or root["workflow_sha256"] != workflow.sha256:
        raise GateEvaluationError("gate input does not bind the workflow")
    cycle = root["cycle"]
    if (
        isinstance(cycle, bool)
        or not isinstance(cycle, int)
        or not 1 <= cycle <= MAX_CYCLES
    ):
        raise GateEvaluationError("cycle is outside the 1-3 remediation range")
    try:
        subject, _subject_bytes = receipts._load_subject_record(
            plugin_data,
            root["subject_ref"],
            workspace_root=workspace_root,
        )
    except (receipts.DispatchReceiptError, OSError) as exc:
        raise GateEvaluationError(f"protected subject is invalid: {exc}") from exc
    try:
        _workflow_run, workflow_run_bytes = receipts._load_workflow_run_record(
            plugin_data,
            subject["workflow_run_ref"],
            workflow=workflow,
            workspace_root=workspace_root,
            enforce_git_policy=True,
        )
    except (receipts.DispatchReceiptError, OSError) as exc:
        raise GateEvaluationError(f"protected workflow run is invalid: {exc}") from exc
    workflow_run_sha256 = receipts._sha256(workflow_run_bytes)
    subject_paths = subject["paths"]
    try:
        baseline, _baseline_bytes = receipts._load_git_baseline_record(
            plugin_data, subject["baseline_ref"]
        )
    except (receipts.DispatchReceiptError, OSError) as exc:
        raise GateEvaluationError(f"protected Git baseline is invalid: {exc}") from exc
    covered_paths = (
        list(subject_paths)
        + list(subject["delta_paths"])
        + [entry["path"] for entry in subject["files"]]
        + [entry["path"] for entry in baseline["entries"]]
    )
    for value in covered_paths:
        normalized = value.rstrip("/").casefold()
        if any(
            normalized == protected
            or normalized.startswith(protected + "/")
            for protected in SELF_PATHS_CASEFOLDED
        ) or any(normalized.startswith(prefix) for prefix in SELF_PREFIXES_CASEFOLDED):
            raise GateEvaluationError(
                "Verified Workflows cannot evaluate its own implementation"
            )
    raw_steps = root["steps"]
    advisory = root["advisory"]
    if not isinstance(raw_steps, list) or not 1 <= len(raw_steps) <= MAX_STEPS:
        raise GateEvaluationError("gate input must contain a bounded non-empty step list")
    if not isinstance(advisory, list) or len(advisory) > 32:
        raise GateEvaluationError("advisory seats must be a bounded list")
    gate_steps: dict[str, str] = {}
    for raw_step in raw_steps:
        value = _closed(raw_step, {"step_id", "receipt_ref"}, "gate step")
        step_id = _safe_ref(value["step_id"], "gate step.step_id")
        receipt_ref = _receipt_ref(value["receipt_ref"], "gate step.receipt_ref")
        if step_id in gate_steps:
            raise GateEvaluationError("gate input contains duplicate step ids")
        gate_steps[str(step_id)] = str(receipt_ref)
    expected_ids = {step.step_id for step in workflow.steps}
    if set(gate_steps) != expected_ids:
        raise GateEvaluationError("gate input must cover every workflow step exactly")
    hard_blockers: list[dict[str, str]] = []
    remediation: list[dict[str, str]] = []
    remediation_exhausted = False
    warnings: list[dict[str, str]] = []
    total_findings = 0
    normalized: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    resolution_records: dict[tuple[str, str], dict[str, Any]] = {}
    for planned in workflow.steps:
        try:
            receipt, result = receipts.validate_normalized_receipt(
                plugin_data, gate_steps[planned.step_id], workflow
            )
        except (receipts.DispatchReceiptError, OSError) as exc:
            raise GateEvaluationError(
                f"gate step {planned.step_id} receipt is invalid: {exc}"
            ) from exc
        if receipt["step_id"] != planned.step_id:
            raise GateEvaluationError("gate receipt is bound to the wrong step")
        if receipt["workflow_run_sha256"] != workflow_run_sha256:
            raise GateEvaluationError("gate receipt belongs to another workflow run")
        if receipts._parse_time(
            receipt["timestamps"]["root_verified_at"], "root verification timestamp"
        ) > receipts._utc_now() + MAX_FUTURE_SKEW:
            raise GateEvaluationError("gate receipt verification timestamp is in the future")
        try:
            input_subject, _input_subject_bytes = receipts._load_subject_record(
                plugin_data, receipt["subject_ref"]
            )
            output_subject, _output_subject_bytes = receipts._load_subject_record(
                plugin_data, receipt["output_subject_ref"]
            )
        except (receipts.DispatchReceiptError, OSError) as exc:
            raise GateEvaluationError(
                f"gate step {planned.step_id} subject transition is invalid: {exc}"
            ) from exc
        if any(
            candidate["repository_sha256"] != subject["repository_sha256"]
            or candidate["paths"] != subject["paths"]
            for candidate in (input_subject, output_subject)
        ):
            raise GateEvaluationError("gate receipt changes the protected subject scope")
        if receipt["attempt"] > cycle:
            raise GateEvaluationError("gate receipt attempt exceeds the gate cycle")
        normalized[planned.step_id] = receipt
        results[planned.step_id] = result
        try:
            verification, _verification_bytes = receipts._load_root_verification_record(
                plugin_data,
                receipt["result"]["root_verification_ref"],
                result_ref=receipt["result"]["result_ref"],
            )
            for reference in verification["resolution_refs"]:
                resolution, _resolution_bytes = receipts._load_resolution_record(
                    plugin_data, reference
                )
                resolution_records[
                    (resolution["result_ref"], resolution["finding_id"])
                ] = resolution
        except (receipts.DispatchReceiptError, OSError) as exc:
            raise GateEvaluationError(
                f"gate step {planned.step_id} resolution evidence is invalid: {exc}"
            ) from exc
        if (
            planned.independence == "required"
            and receipt["vehicle"] != "verified-workflow-subagent"
        ):
            hard_blockers.append(
                {
                    "step_id": planned.step_id,
                    "reason": "required independence lacks host-attested child",
                }
            )
        if receipt["vehicle"] == "verified-workflow-subagent":
            hard_blockers.append(
                {
                    "step_id": planned.step_id,
                    "reason": (
                        "native child evidence is root-accountability only; "
                        "host-issued attestation is unavailable"
                    ),
                }
            )
        evidence = result["evidence"]
        score = evidence.get("overall")
        dimension_scores = [
            float(dimension["score"])
            for dimension in evidence.get("dimensions", [])
        ]
        if score is not None and float(score) < 9:
            warnings.append(
                {"step_id": planned.step_id, "reason": "review score below 9.0"}
            )
        elif dimension_scores and min(dimension_scores) < 7:
            warnings.append(
                {
                    "step_id": planned.step_id,
                    "reason": "review dimension score below 7.0",
                }
            )
        findings = evidence.get("findings", [])
        total_findings += len(findings)
        if total_findings > MAX_FINDINGS:
            raise GateEvaluationError("gate input exceeds the finding ceiling")
        for raw_finding in findings:
            finding = _finding(raw_finding, planned.step_id)
            remediation_exhausted = (
                remediation_exhausted or receipt["attempt"] >= MAX_CYCLES
            )
            reason = (
                f"unresolved {finding['severity']} {finding['category']} finding "
                f"{finding['finding_id']}"
            )
            if (
                finding["severity"] in {"P0", "P1"}
                or finding["category"] == "security"
                or finding["hard_stop"]
            ):
                hard_blockers.append({"step_id": planned.step_id, "reason": reason})
            else:
                remediation.append({"step_id": planned.step_id, "reason": reason})
        status = evidence.get("gate_status")
        if status is not None:
            if status not in VALIDATOR_STATUSES:
                raise GateEvaluationError("validator status is invalid")
            required = planned.validator_required is True
            disabled = planned.validator_disabled is True
            if disabled and status != "skipped-by-config":
                raise GateEvaluationError("disabled validator did not report skipped-by-config")
            if not disabled and status == "skipped-by-config":
                raise GateEvaluationError("enabled validator cannot be skipped by config")
            if status in {"hard-fail", "blocked"}:
                hard_blockers.append(
                    {
                        "step_id": planned.step_id,
                        "reason": f"validator status is {status}",
                    }
                )
            elif required and status != "pass":
                hard_blockers.append(
                    {
                        "step_id": planned.step_id,
                        "reason": f"required validator status is {status}",
                    }
                )
            elif status == "warn":
                warnings.append(
                    {"step_id": planned.step_id, "reason": "validator warning"}
                )
    max_attempt = max(receipt["attempt"] for receipt in normalized.values())
    if max_attempt != cycle:
        raise GateEvaluationError("gate cycle must equal the newest receipt attempt")
    for planned in workflow.steps:
        chain: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
        cursor_receipt = normalized[planned.step_id]
        cursor_result = results[planned.step_id]
        while True:
            intent, _intent_bytes = receipts._load_intent_record(
                plugin_data,
                cursor_receipt["intent_ref"],
                workflow,
                planned.step_id,
                cursor_receipt["attempt"],
                cursor_receipt["task_id"],
            )
            chain.append((cursor_receipt, cursor_result, intent))
            verification, _verification_bytes = receipts._load_root_verification_record(
                plugin_data,
                cursor_receipt["result"]["root_verification_ref"],
                result_ref=cursor_receipt["result"]["result_ref"],
            )
            for reference in verification["resolution_refs"]:
                resolution, _resolution_bytes = receipts._load_resolution_record(
                    plugin_data, reference
                )
                resolution_records[
                    (resolution["result_ref"], resolution["finding_id"])
                ] = resolution
            previous_ref = intent["previous_receipt_ref"]
            if previous_ref is None:
                break
            cursor_receipt, cursor_result = receipts.validate_normalized_receipt(
                plugin_data, previous_ref, workflow
            )
            if cursor_receipt["workflow_run_sha256"] != workflow_run_sha256:
                raise GateEvaluationError(
                    f"gate step {planned.step_id} splices another workflow run"
                )
        chain.reverse()
        if [receipt["attempt"] for receipt, _result, _intent in chain] != list(
            range(1, normalized[planned.step_id]["attempt"] + 1)
        ):
            raise GateEvaluationError(
                f"gate step {planned.step_id} remediation history is incomplete"
            )
        for (prior_receipt, prior_result, _prior_intent), (
            _next_receipt,
            next_result,
            _next_intent,
        ) in zip(chain, chain[1:], strict=False):
            intent_resolutions: dict[str, dict[str, Any]] = {}
            for reference in _next_intent["resolution_refs"]:
                resolution, _resolution_bytes = receipts._load_resolution_record(
                    plugin_data,
                    reference,
                    result_ref=prior_receipt["result"]["result_ref"],
                )
                intent_resolutions[resolution["finding_id"]] = resolution
            if not receipts._subject_descends_from(
                plugin_data,
                _next_intent["subject_ref"],
                prior_receipt["output_subject_ref"],
            ):
                raise GateEvaluationError(
                    f"gate step {planned.step_id} remediation subject breaks ancestry"
                )
            prior_findings = {
                finding["finding_id"]: finding
                for finding in prior_result["evidence"].get("findings", [])
            }
            next_findings = {
                finding["finding_id"]: finding
                for finding in next_result["evidence"].get("findings", [])
            }
            for finding_id, prior_finding in prior_findings.items():
                if finding_id in next_findings:
                    if next_findings[finding_id] != prior_finding:
                        raise GateEvaluationError(
                            f"gate step {planned.step_id} mutated finding {finding_id}"
                        )
                else:
                    resolution = intent_resolutions.get(finding_id) or resolution_records.get(
                        (prior_receipt["result"]["result_ref"], finding_id)
                    )
                    if resolution is None:
                        raise GateEvaluationError(
                            f"gate step {planned.step_id} dropped unresolved finding {finding_id}"
                        )
                    if receipts._parse_time(
                        resolution["recorded_at"], "resolution.recorded_at"
                    ) > receipts._parse_time(
                        _next_intent["created_at"], "next intent.created_at"
                    ):
                        raise GateEvaluationError(
                            f"gate step {planned.step_id} resolution {finding_id} was recorded after its retry intent"
                        )
                    if not receipts._subject_descends_from(
                        plugin_data,
                        _next_intent["subject_ref"],
                        resolution["resolved_subject_ref"],
                    ) or not receipts._subject_descends_from(
                        plugin_data,
                        normalized[planned.step_id]["output_subject_ref"],
                        resolution["resolved_subject_ref"],
                    ):
                        raise GateEvaluationError(
                            f"gate step {planned.step_id} does not consume resolution {finding_id}"
                        )
    for planned in workflow.steps:
        downstream_created = receipts._parse_time(
            normalized[planned.step_id]["timestamps"]["intent_created_at"],
            "downstream intent timestamp",
        )
        for dependency in planned.depends_on:
            dependency_verified = receipts._parse_time(
                normalized[dependency]["timestamps"]["root_verified_at"],
                "dependency verification timestamp",
            )
            if downstream_created < dependency_verified:
                raise GateEvaluationError(
                    f"gate step {planned.step_id} predates dependency {dependency} verification"
                )
            if not receipts._subject_descends_from(
                plugin_data,
                normalized[planned.step_id]["subject_ref"],
                normalized[dependency]["output_subject_ref"],
            ):
                raise GateEvaluationError(
                    f"gate step {planned.step_id} does not consume dependency {dependency} output"
                )
            prerequisite_refs = results[planned.step_id]["evidence"].get(
                "prerequisite_gate_refs"
            )
            if (
                prerequisite_refs is not None
                and normalized[dependency]["result"]["result_ref"]
                not in prerequisite_refs
            ):
                raise GateEvaluationError(
                    f"gate step {planned.step_id} omits protected prerequisite {dependency}"
                )
    dependency_ids = {
        dependency for step in workflow.steps for dependency in step.depends_on
    }
    terminal_steps = [
        step for step in workflow.steps if step.step_id not in dependency_ids
    ]
    if any(
        normalized[step.step_id]["output_subject_ref"] != root["subject_ref"]
        for step in terminal_steps
    ):
        raise GateEvaluationError("terminal workflow evidence does not bind the current subject")
    for raw_seat in advisory:
        seat = _closed(
            raw_seat,
            {"seat_type", "gate_authority", "evidence_ref"},
            "advisory seat",
        )
        if seat["seat_type"] not in ADVISORY_SEATS or seat["gate_authority"] != "none":
            raise GateEvaluationError("advisory seat type or authority is invalid")
        _safe_ref(seat["evidence_ref"], "advisory seat.evidence_ref", nullable=True)
    hard_blockers.sort(key=lambda item: (item["step_id"], item["reason"]))
    remediation.sort(key=lambda item: (item["step_id"], item["reason"]))
    warnings.sort(key=lambda item: (item["step_id"], item["reason"]))
    if remediation_exhausted and (hard_blockers or remediation):
        verdict = "escalate"
    elif hard_blockers:
        verdict = "block"
    elif remediation:
        verdict = "block"
    else:
        verdict = "pass"
    return {
        "schema_version": 1,
        "workflow_sha256": workflow.sha256,
        "cycle": cycle,
        "subject_ref": root["subject_ref"],
        "subject_content_sha256": subject["content_sha256"],
        "subject_paths": subject_paths,
        "evidence_producer": "root-accountability",
        "verdict": verdict,
        "hard_blockers": hard_blockers,
        "remediation": remediation,
        "warnings": warnings,
        "advisory_gate_authority": "none",
        "numeric_scores_have_gate_authority": False,
        "selection": selection,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plugin-data", type=Path, required=True)
    parser.add_argument("--agents-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=dispatch.renderer.DEFAULT_REGISTRY)
    parser.add_argument("--roles-dir", type=Path, default=dispatch.renderer.DEFAULT_ROLES_DIR)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.plugin_data.is_absolute():
            raise GateEvaluationError("plugin data path must be absolute")
        plan = dispatch._read_bounded(
            args.plan, dispatch.MAX_PLAN_BYTES, "workflow plan"
        ).decode("utf-8")
        default_registry = (
            args.registry.resolve() == dispatch.renderer.DEFAULT_REGISTRY.resolve()
            and args.roles_dir.resolve() == dispatch.renderer.DEFAULT_ROLES_DIR.resolve()
        )
        registry = dispatch.renderer.load_role_registry(
            args.registry,
            args.roles_dir,
            expected_role_ids=(
                dispatch.renderer.EXPECTED_ROLE_IDS if default_registry else None
            ),
        )
        workflow = dispatch.parse_workflow_structure(
            plan,
            agents_dir=args.agents_dir,
            registry=registry,
        )
        payload = evaluate_gate(
            _read_bounded(args.input),
            workflow=workflow,
            plugin_data=args.plugin_data,
            workspace_root=args.workspace_root,
            registry=registry,
            enforce_selection_policy=True,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        dispatch.WorkflowDispatchError,
        dispatch.renderer.RoleRegistryError,
        receipts.DispatchReceiptError,
        GateEvaluationError,
        OSError,
    ) as exc:
        print(f"verified workflow gate failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if payload["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
