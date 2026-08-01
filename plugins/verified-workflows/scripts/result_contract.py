#!/usr/bin/env python3
"""Validate compact typed terminal results returned by Codex V2 assignments."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Mapping

import workflow_dispatch as dispatch


ATTEMPT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}-attempt-[1-9][0-9]*$")
COMMON_FIELDS = {
    "assignment_id",
    "attempt_id",
    "agent_path",
    "role_id",
    "profile_id",
    "terminal_status",
    "summary",
    "changed_paths",
    "no_change",
    "checks",
    "findings",
    "residual_risks",
}
REVIEWER_FIELDS = {
    "dimensions",
    "exclusions",
    "denominator",
    "overall",
    "verdict",
    "hard_stop",
}
TERMINAL_STATUSES = {"completed", "failed", "interrupted", "blocked"}
CHECK_STATUSES = {"pass", "warn", "failed", "blocked"}
SEVERITIES = {"P0", "P1", "P2", "P3"}
SCOPE_DISPOSITIONS = {"planned", "one-hop", "defer", "approval-required"}
FINDING_CATEGORIES = {
    "security",
    "correctness",
    "reliability",
    "operations",
    "maintainability",
    "documentation",
    "test-coverage",
    "performance",
    "compatibility",
}
UNDECLARED_WRITE_FINDING_PREFIX = "undeclared-write-"


class ResultContractError(ValueError):
    """Raised when terminal output does not match its approved assignment contract."""


def _closed(value: object, fields: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ResultContractError(f"{where} must be a typed object; a message is not completion")
    if set(value) != fields:
        raise ResultContractError(
            f"{where} fields must be exactly {sorted(fields)}; got {sorted(value)}"
        )
    return value


def _string(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResultContractError(f"{where} must be a non-empty string")
    return value.strip()


def _string_list(value: object, where: str, *, max_items: int = 1024) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > max_items:
        raise ResultContractError(f"{where} must be a bounded string list")
    values = tuple(_string(item, f"{where}[{index}]") for index, item in enumerate(value))
    if len(values) != len(set(values)):
        raise ResultContractError(f"{where} must not contain duplicates")
    return values


def _check(value: object, index: int) -> dict[str, Any]:
    item = _closed(value, {"check_id", "status", "detail"}, f"checks[{index}]")
    check_id = _string(item["check_id"], f"checks[{index}].check_id")
    status = item["status"]
    if status not in CHECK_STATUSES:
        raise ResultContractError(f"checks[{index}].status is invalid")
    detail = _string(item["detail"], f"checks[{index}].detail")
    return {"check_id": check_id, "status": status, "detail": detail}


def _finding(value: object, index: int) -> dict[str, Any]:
    fields = {
        "finding_id",
        "severity",
        "category",
        "location",
        "impact",
        "fix",
        "validation",
        "scope_disposition",
        "resolved",
        "hard_stop",
    }
    item = _closed(value, fields, f"findings[{index}]")
    normalized = {
        field: _string(item[field], f"findings[{index}].{field}")
        for field in ("finding_id", "location", "impact", "fix", "validation")
    }
    severity = item["severity"]
    category = item["category"]
    scope_disposition = item["scope_disposition"]
    if severity not in SEVERITIES:
        raise ResultContractError(f"findings[{index}].severity is invalid")
    if category not in FINDING_CATEGORIES:
        raise ResultContractError(f"findings[{index}].category is invalid")
    if scope_disposition not in SCOPE_DISPOSITIONS:
        raise ResultContractError(f"findings[{index}].scope_disposition is invalid")
    if not isinstance(item["resolved"], bool) or not isinstance(item["hard_stop"], bool):
        raise ResultContractError(f"findings[{index}] resolved and hard_stop must be booleans")
    if scope_disposition == "defer" and item["hard_stop"]:
        raise ResultContractError(
            f"findings[{index}] cannot combine scope_disposition=defer with hard_stop=true"
        )
    return {
        **normalized,
        "severity": severity,
        "category": category,
        "scope_disposition": scope_disposition,
        "resolved": item["resolved"],
        "hard_stop": item["hard_stop"],
    }


def _undeclared_write_finding_id(path: str) -> str:
    """Return one stable finding ID for an undeclared changed path."""

    slug = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")[:48].strip("-")
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
    return f"{UNDECLARED_WRITE_FINDING_PREFIX}{slug}-{digest}" if slug else (
        f"{UNDECLARED_WRITE_FINDING_PREFIX}{digest}"
    )


def _undeclared_write_finding(path: str, declared: tuple[str, ...], index: int) -> dict[str, Any]:
    """Synthesize the validator-owned finding for one out-of-scope changed path."""

    declared_text = ", ".join(declared) if declared else "none (the assignment declared no writes)"
    return _finding(
        {
            "finding_id": _undeclared_write_finding_id(path),
            "severity": "P2",
            "category": "operations",
            "location": path,
            "impact": (
                f"{path} was changed but sits outside the declared write set: {declared_text}"
            ),
            "fix": (
                f"either revert {path} or widen the assignment write set beyond {declared_text} "
                "with operator approval"
            ),
            "validation": (
                f"re-run the assignment and confirm changed paths stay inside {declared_text}"
            ),
            "scope_disposition": "one-hop",
            "resolved": False,
            "hard_stop": False,
        },
        index,
    )


def validate_finding(value: object, *, where: str = "finding") -> dict[str, Any]:
    """Validate one standalone typed finding for root adoption."""

    try:
        return _finding(value, 0)
    except ResultContractError as exc:
        raise ResultContractError(f"{where}: {exc}") from exc


def _reviewer_extension(payload: Mapping[str, Any]) -> dict[str, Any]:
    dimensions_raw = payload["dimensions"]
    exclusions_raw = payload["exclusions"]
    if not isinstance(dimensions_raw, list) or not dimensions_raw:
        raise ResultContractError("reviewer dimensions must be a non-empty list")
    if not isinstance(exclusions_raw, list):
        raise ResultContractError("reviewer exclusions must be a list")
    dimensions: list[dict[str, Any]] = []
    for index, value in enumerate(dimensions_raw):
        item = _closed(value, {"dimension_id", "score", "notes"}, f"dimensions[{index}]")
        score = item["score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 10:
            raise ResultContractError(f"dimensions[{index}].score must be a number from 0 to 10")
        dimensions.append(
            {
                "dimension_id": _string(item["dimension_id"], f"dimensions[{index}].dimension_id"),
                "score": float(score),
                "notes": _string(item["notes"], f"dimensions[{index}].notes"),
            }
        )
    exclusions: list[dict[str, str]] = []
    for index, value in enumerate(exclusions_raw):
        item = _closed(value, {"dimension_id", "reason"}, f"exclusions[{index}]")
        if item["reason"] != "static-non-applicable":
            raise ResultContractError(f"exclusions[{index}].reason is invalid")
        exclusions.append(
            {
                "dimension_id": _string(item["dimension_id"], f"exclusions[{index}].dimension_id"),
                "reason": "static-non-applicable",
            }
        )
    dimension_ids = [item["dimension_id"] for item in dimensions]
    exclusion_ids = [item["dimension_id"] for item in exclusions]
    if len(dimension_ids) != len(set(dimension_ids)) or len(exclusion_ids) != len(set(exclusion_ids)):
        raise ResultContractError("reviewer dimension and exclusion IDs must be unique")
    if set(dimension_ids) & set(exclusion_ids):
        raise ResultContractError("a reviewer dimension cannot also be excluded")
    denominator = payload["denominator"]
    if isinstance(denominator, bool) or not isinstance(denominator, int) or denominator != len(dimensions):
        raise ResultContractError("reviewer denominator must equal the applicable dimension count")
    overall = payload["overall"]
    expected = sum(item["score"] for item in dimensions) / denominator
    if isinstance(overall, bool) or not isinstance(overall, (int, float)) or not math.isclose(
        float(overall), expected, abs_tol=1e-9
    ):
        raise ResultContractError("reviewer overall must be the arithmetic mean")
    verdict = payload["verdict"]
    if verdict not in {"accept", "needs-revision", "blocking"}:
        raise ResultContractError("reviewer verdict is invalid")
    if not isinstance(payload["hard_stop"], bool):
        raise ResultContractError("reviewer hard_stop must be a boolean")
    return {
        "dimensions": dimensions,
        "exclusions": exclusions,
        "denominator": denominator,
        "overall": float(overall),
        "verdict": verdict,
        "hard_stop": payload["hard_stop"],
    }


def validate_result(
    value: object,
    launch: dispatch.LaunchSpec,
    *,
    expected_attempt_id: str,
    expected_agent_path: str,
) -> dict[str, Any]:
    """Return one normalized result after closed-schema and boundary validation."""

    reviewer = launch.result_schema == "reviewer-result.v1"
    fields = COMMON_FIELDS | (REVIEWER_FIELDS if reviewer else set())
    payload = _closed(value, fields, "terminal result")
    if ATTEMPT_ID_RE.fullmatch(expected_attempt_id) is None:
        raise ResultContractError("expected attempt ID is invalid")
    expected = {
        "assignment_id": launch.assignment_id,
        "attempt_id": expected_attempt_id,
        "agent_path": expected_agent_path,
        "role_id": launch.role,
        "profile_id": launch.agent_type or "root",
    }
    for field, expected_value in expected.items():
        if payload[field] != expected_value:
            raise ResultContractError(
                f"terminal result {field} mismatch: expected {expected_value!r}, got {payload[field]!r}"
            )
    terminal_status = payload["terminal_status"]
    if terminal_status not in TERMINAL_STATUSES:
        raise ResultContractError("terminal result status is invalid")
    changed_paths = tuple(
        sorted(
            dispatch._repo_path(item, "terminal result.changed_paths")
            for item in _string_list(payload["changed_paths"], "terminal result.changed_paths")
        )
    )
    no_change = payload["no_change"]
    if not isinstance(no_change, bool) or no_change != (not changed_paths):
        raise ResultContractError("no_change must be true exactly when changed_paths is empty")
    declared_writes = tuple(
        allowed for allowed in launch.writes if not allowed.startswith("unit:")
    )
    undeclared = [
        path
        for path in changed_paths
        if not any(
            path == allowed or path.startswith(f"{allowed}/") for allowed in declared_writes
        )
    ]
    checks_raw = payload["checks"]
    findings_raw = payload["findings"]
    if not isinstance(checks_raw, list) or not isinstance(findings_raw, list):
        raise ResultContractError("terminal result checks and findings must be lists")
    checks = [_check(item, index) for index, item in enumerate(checks_raw)]
    findings = [_finding(item, index) for index, item in enumerate(findings_raw)]
    agent_finding_count = len(findings)
    findings.extend(
        _undeclared_write_finding(path, declared_writes, agent_finding_count + offset)
        for offset, path in enumerate(undeclared)
    )
    residual_risks = list(
        _string_list(payload["residual_risks"], "terminal result.residual_risks", max_items=128)
    )
    normalized: dict[str, Any] = {
        **expected,
        "terminal_status": terminal_status,
        "summary": _string(payload["summary"], "terminal result.summary"),
        "changed_paths": list(changed_paths),
        "no_change": no_change,
        "checks": checks,
        "findings": findings,
        "residual_risks": residual_risks,
    }
    if reviewer:
        normalized.update(_reviewer_extension(payload))
    return normalized
