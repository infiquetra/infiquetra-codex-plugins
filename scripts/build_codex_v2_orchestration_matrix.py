#!/usr/bin/env python3
"""Capture sanitized V2 rollout projections and derive the committed proof matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPTS = ROOT / "docs" / "validation" / "codex-v2-orchestration-receipts.json"
DEFAULT_MATRIX = ROOT / "docs" / "validation" / "codex-v2-orchestration-matrix.json"
MAX_ROLLOUT_BYTES = 8 * 1024 * 1024
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
MARKERS = (
    "V2_PROFILE_PARENT_ONLY_CONTEXT",
    "V2_PROFILE_CHILD_OK",
    "V2_NESTED_ROOT_OK",
    "V2_NESTED_PARENT_OK",
    "V2_NESTED_LEAF_OK",
    "V2_LIFECYCLE_ROOT_OK",
    "V2_LIFECYCLE_RESTORED",
    "V2_PROFILE_REVIEW_MAX_OK",
    "V2_PROFILE_REVIEW_HIGH_OK",
    "V2_PROFILE_WORK_HIGH_OK",
    "V2_PROFILE_TEST_MEDIUM_OK",
    "V2_PROFILE_SCAN_LOW_OK",
    "V2_PROFILE_MONITOR_LOW_OK",
    "V2_ULTRA_ROOT_OK",
    "V2_ULTRA_CHILD_REJECTION_OBSERVED",
    "V2_BOUNDED_VISIBLE",
    "V2_BOUNDED_CONTEXT_OK",
    "V2_TYPED_ROOT_OK",
    "V2_TYPED_RESULT_OK",
)
EXPECTED_PARENTS = {
    "nested_root": None,
    "nested_parent": "nested_root",
    "nested_leaf": "nested_parent",
    "lifecycle_root": None,
    "lifecycle_child": "lifecycle_root",
    "profile_read_root": None,
    "profile_review_max": "profile_read_root",
    "profile_review_high": "profile_read_root",
    "profile_scan_low": "profile_read_root",
    "profile_monitor_low": "profile_read_root",
    "profile_write_root": None,
    "profile_work_high": "profile_write_root",
    "profile_test_medium": "profile_write_root",
    "ultra_root": None,
    "ultra_request_root": None,
    "ultra_child": "ultra_request_root",
    "bounded_root": None,
    "bounded_child": "bounded_root",
    "typed_root": None,
    "typed_child": "typed_root",
    "no_history_root": None,
    "no_history_child": "no_history_root",
}
EXPECTED_PROFILES = {
    "review_max": ("gpt-5.6-sol", "max", "read-only"),
    "review_high": ("gpt-5.6-sol", "high", "read-only"),
    "work_high": ("gpt-5.6-sol", "high", "workspace-write"),
    "test_medium": ("gpt-5.6-terra", "medium", "workspace-write"),
    "scan_low": ("gpt-5.6-terra", "low", "read-only"),
    "monitor_low": ("gpt-5.6-terra", "low", "read-only"),
}
PROFILE_CASES = {
    "review_max": "profile_review_max",
    "review_high": "profile_review_high",
    "work_high": "profile_work_high",
    "test_medium": "profile_test_medium",
    "scan_low": "profile_scan_low",
    "monitor_low": "profile_monitor_low",
}
TYPED_RESULT = {
    "assignment_id": "v2-typed",
    "attempt_id": "a1",
    "agent_path": "/root/typed_result",
    "role_id": "dependency-scanner",
    "profile_id": "scan_low",
    "terminal_status": "completed",
    "summary": "V2_TYPED_RESULT_OK",
    "changed_paths": [],
    "no_change": True,
    "checks": [],
    "findings": [],
    "residual_risks": [],
}


class MatrixError(ValueError):
    """Raised when receipt projections or the derived matrix are incomplete or inconsistent."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_sha256(value: object) -> str:
    return _sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _read(path: Path, limit: int, where: str) -> bytes:
    try:
        metadata = path.stat()
        content = path.read_bytes()
    except OSError as exc:
        raise MatrixError(f"{where} is unreadable") from exc
    if not path.is_file() or path.is_symlink() or metadata.st_size > limit or len(content) != metadata.st_size:
        raise MatrixError(f"{where} must be one bounded regular file")
    return content


def _policy_type(value: object, where: str) -> str:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict) and isinstance(value.get("type"), str):
        return str(value["type"])
    raise MatrixError(f"{where} is missing")


def _function_name(value: object) -> str:
    return value.rsplit(".", 1)[-1].rsplit("__", 1)[-1] if isinstance(value, str) else ""


def _parse_rollout(case: str, path: Path) -> tuple[dict[str, Any], str, str | None]:
    content = _read(path, MAX_ROLLOUT_BYTES, f"rollout {case}")
    meta: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    operations: set[str] = set()
    terminal_message: object = None
    for number, line in enumerate(content.splitlines(), 1):
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MatrixError(f"rollout {case} line {number} is invalid JSON") from exc
        if not isinstance(row, dict) or not isinstance(row.get("payload"), dict):
            continue
        payload = row["payload"]
        if row.get("type") == "session_meta":
            if meta is not None:
                raise MatrixError(f"rollout {case} repeats session_meta")
            meta = payload
        elif row.get("type") == "turn_context":
            context = payload
        elif row.get("type") == "response_item":
            name = _function_name(payload.get("name"))
            if name:
                operations.add(name)
        elif row.get("type") == "event_msg" and payload.get("type") == "task_complete":
            terminal_message = payload.get("last_agent_message")
    if meta is None or context is None:
        raise MatrixError(f"rollout {case} lacks session_meta or turn_context")
    session_id = meta.get("id")
    parent_id = meta.get("parent_thread_id")
    if not isinstance(session_id, str) or not session_id:
        raise MatrixError(f"rollout {case} lacks a session id")
    if parent_id is not None and not isinstance(parent_id, str):
        raise MatrixError(f"rollout {case} parent id is malformed")
    typed_result_valid = False
    if case == "typed_child" and isinstance(terminal_message, str):
        try:
            typed_result_valid = json.loads(terminal_message) == TYPED_RESULT
        except json.JSONDecodeError:
            typed_result_valid = False
    projection = {
        "case": case,
        "rollout_sha256": _sha256(content),
        "agent_path": meta.get("agent_path") or "/root",
        "agent_role": meta.get("agent_role") or "root",
        "model": context.get("model"),
        "reasoning_effort": context.get("effort"),
        "model_provider": meta.get("model_provider"),
        "approval_policy": context.get("approval_policy"),
        "permission_profile": _policy_type(
            context.get("permission_profile"), f"rollout {case} permission profile"
        ),
        "sandbox_mode": _policy_type(
            context.get("sandbox_policy"), f"rollout {case} sandbox policy"
        ),
        "multi_agent_version": context.get(
            "multi_agent_version", meta.get("multi_agent_version")
        ),
        "history_mode": meta.get("history_mode"),
        "terminal": terminal_message is not None,
        "operations": sorted(operations),
        "markers": {marker: marker.encode() in content for marker in MARKERS},
        "typed_result_valid": typed_result_valid,
    }
    return projection, session_id, parent_id


def _catalog_projection(path: Path) -> dict[str, str]:
    content = _read(path, 16 * 1024 * 1024, "native model cache")
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MatrixError("native model cache is invalid JSON") from exc
    rows = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise MatrixError("native model cache lacks models")
    versions = {
        row.get("slug"): row.get("multi_agent_version")
        for row in rows
        if isinstance(row, dict)
    }
    return {
        "source": "native-model-cache",
        "sha256": _sha256(content),
        "sol_multi_agent_version": str(versions.get("gpt-5.6-sol")),
        "terra_multi_agent_version": str(versions.get("gpt-5.6-terra")),
        "luna_multi_agent_version": str(versions.get("gpt-5.6-luna")),
    }


def capture_receipts(rollouts: Mapping[str, Path], catalog_path: Path) -> dict[str, Any]:
    if set(rollouts) != set(EXPECTED_PARENTS):
        raise MatrixError(
            "capture rollout cases are not closed: "
            f"missing={sorted(set(EXPECTED_PARENTS) - set(rollouts))} "
            f"unexpected={sorted(set(rollouts) - set(EXPECTED_PARENTS))}"
        )
    parsed = {case: _parse_rollout(case, path) for case, path in rollouts.items()}
    case_by_session = {session_id: case for case, (_row, session_id, _parent) in parsed.items()}
    if len(case_by_session) != len(parsed):
        raise MatrixError("capture rollouts repeat a session identity")
    receipts = []
    for case in sorted(parsed):
        projection, _session_id, parent_id = parsed[case]
        parent_case = case_by_session.get(parent_id) if parent_id else None
        if parent_id and parent_case is None:
            raise MatrixError(f"rollout {case} parent is outside the closed receipt set")
        projection["parent_case"] = parent_case
        receipts.append(projection)
    body = {"catalog": _catalog_projection(catalog_path), "receipts": receipts}
    return {
        "schema_version": 1,
        "claim": "sanitized-codex-v2-runtime-receipts",
        **body,
        "receipt_set_sha256": _canonical_sha256(body),
    }


def _closed_receipts(payload: object) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "claim",
        "catalog",
        "receipts",
        "receipt_set_sha256",
    }:
        raise MatrixError("receipt artifact fields are not closed")
    if payload["schema_version"] != 1 or payload["claim"] != "sanitized-codex-v2-runtime-receipts":
        raise MatrixError("receipt artifact identity is invalid")
    receipts = payload.get("receipts")
    catalog = payload.get("catalog")
    if not isinstance(receipts, list) or not isinstance(catalog, dict):
        raise MatrixError("receipt artifact body is invalid")
    body = {"catalog": catalog, "receipts": receipts}
    if payload.get("receipt_set_sha256") != _canonical_sha256(body):
        raise MatrixError("receipt set digest does not match its projections")
    by_case = {
        row.get("case"): row for row in receipts if isinstance(row, dict) and isinstance(row.get("case"), str)
    }
    if len(by_case) != len(receipts) or set(by_case) != set(EXPECTED_PARENTS):
        raise MatrixError("receipt artifact does not contain the exact required case set")
    for case, expected_parent in EXPECTED_PARENTS.items():
        row = by_case[case]
        if row.get("parent_case") != expected_parent:
            raise MatrixError(f"receipt {case} parent linkage is invalid")
        if not HEX64_RE.fullmatch(str(row.get("rollout_sha256"))):
            raise MatrixError(f"receipt {case} rollout digest is invalid")
        if row.get("multi_agent_version") != "v2" or row.get("model_provider") != "openai":
            raise MatrixError(f"receipt {case} does not attest the expected V2 provider")
        if row.get("approval_policy") != "never" or row.get("permission_profile") != "managed":
            raise MatrixError(f"receipt {case} does not attest the expected managed policy")
    expected_catalog = {
        "source": "native-model-cache",
        "sol_multi_agent_version": "v2",
        "terra_multi_agent_version": "v2",
        "luna_multi_agent_version": "v1",
    }
    if any(catalog.get(key) != value for key, value in expected_catalog.items()):
        raise MatrixError("receipt catalog does not attest the required V2 model boundary")
    if not HEX64_RE.fullmatch(str(catalog.get("sha256"))):
        raise MatrixError("receipt catalog digest is invalid")
    return payload, by_case


def _profile_hash(profile: str) -> str:
    path = ROOT / ".codex" / "agents" / f"{profile}.toml"
    return _sha256(_read(path, 1024 * 1024, f"project profile {profile}"))


def _project_config() -> tuple[str, dict[str, Any]]:
    content = _read(ROOT / ".codex" / "config.toml", 1024 * 1024, "project Codex config")
    try:
        payload = tomllib.loads(content.decode())
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise MatrixError("project Codex config is invalid") from exc
    if payload.get("features", {}).get("multi_agent_v2") is not True:
        raise MatrixError("project Codex config does not enable MultiAgent V2")
    if payload.get("agents", {}).get("max_depth") != 2:
        raise MatrixError("project Codex config does not allow the proved nested depth")
    return _sha256(content), payload


def build_matrix(receipt_payload: object) -> dict[str, Any]:
    payload, rows = _closed_receipts(receipt_payload)
    config_sha256, _config = _project_config()
    profiles = []
    for profile in EXPECTED_PROFILES:
        model, effort, sandbox = EXPECTED_PROFILES[profile]
        row = rows[PROFILE_CASES[profile]]
        expected = (profile, model, effort, sandbox)
        actual = (
            row.get("agent_role"),
            row.get("model"),
            row.get("reasoning_effort"),
            row.get("sandbox_mode"),
        )
        if actual != expected or row.get("terminal") is not True:
            raise MatrixError(f"profile receipt {profile} does not match its runtime contract")
        profiles.append(
            {
                "profile": profile,
                "model": model,
                "effort": effort,
                "sandbox": sandbox,
                "permission": row["permission_profile"],
                "provider": row["model_provider"],
                "multi_agent_version": row["multi_agent_version"],
                "sha256": _profile_hash(profile),
                "rollout_sha256": row["rollout_sha256"],
            }
        )
    nested_parent = rows["nested_parent"]
    nested_leaf = rows["nested_leaf"]
    if (
        nested_parent.get("agent_path") != "/root/nested_parent"
        or nested_parent.get("agent_role") != "review_high"
        or nested_leaf.get("agent_path") != "/root/nested_parent/nested_leaf"
        or nested_leaf.get("agent_role") != "scan_low"
        or nested_leaf.get("terminal") is not True
    ):
        raise MatrixError("nested receipt chain is invalid")
    lifecycle_root = rows["lifecycle_root"]
    lifecycle_child = rows["lifecycle_child"]
    lifecycle_operations = [
        "spawn_agent",
        "send_message",
        "list_agents",
        "interrupt_agent",
        "followup_task",
        "wait_agent",
    ]
    if any(operation not in lifecycle_root.get("operations", []) for operation in lifecycle_operations):
        raise MatrixError("lifecycle root lacks one or more required operations")
    if (
        lifecycle_child.get("agent_path") != "/root/lifecycle"
        or lifecycle_child.get("markers", {}).get("V2_LIFECYCLE_RESTORED") is not True
        or lifecycle_child.get("terminal") is not True
    ):
        raise MatrixError("lifecycle child restoration is invalid")
    no_history = rows["no_history_child"]
    bounded = rows["bounded_child"]
    if no_history.get("markers", {}).get("V2_PROFILE_PARENT_ONLY_CONTEXT") is not False:
        raise MatrixError("no-history child contains the root-only marker")
    if bounded.get("markers", {}).get("V2_BOUNDED_VISIBLE") is not True:
        raise MatrixError("bounded-history child lacks the inherited marker")
    if rows["typed_child"].get("typed_result_valid") is not True:
        raise MatrixError("typed-result receipt does not contain the exact closed result")
    if (
        rows["ultra_root"].get("reasoning_effort") != "ultra"
        or rows["ultra_child"].get("agent_role") != "review_max"
        or rows["ultra_child"].get("reasoning_effort") != "max"
    ):
        raise MatrixError("Ultra receipts do not prove the root/child ceiling")
    return {
        "schema_version": 2,
        "claim": "codex-v2-orchestration-matrix",
        "capability_outcome": "supported",
        "codex_cli_version": "0.145.0",
        "authentication_mode": "current-codex-home-reused",
        "generated_from": {
            "receipt_artifact": "docs/validation/codex-v2-orchestration-receipts.json",
            "receipt_set_sha256": payload["receipt_set_sha256"],
            "builder_sha256": _sha256(Path(__file__).read_bytes()),
            "project_config_sha256": config_sha256,
        },
        "catalog": payload["catalog"],
        "luna_decision": {
            "outcome": "fallback-selected",
            "reason": "Luna is unavailable to MultiAgent V2",
            "scan_low_model": "gpt-5.6-terra",
            "monitor_low_model": "gpt-5.6-terra",
            "effort": "low",
        },
        "profiles": profiles,
        "context": {
            "no_history_child_excluded_root_only_marker": True,
            "bounded_history_child_observed_current_root_marker": True,
        },
        "nested_delegation": {
            "parent_path": nested_parent["agent_path"],
            "parent_profile": nested_parent["agent_role"],
            "leaf_path": nested_leaf["agent_path"],
            "leaf_profile": nested_leaf["agent_role"],
            "leaf_model": nested_leaf["model"],
            "leaf_effort": nested_leaf["reasoning_effort"],
            "terminal": nested_leaf["terminal"],
        },
        "typed_result": {
            "schema": "assignment-result.v1",
            "role": "dependency-scanner",
            "profile": "scan_low",
            "validated": True,
            "rollout_sha256": rows["typed_child"]["rollout_sha256"],
        },
        "lifecycle": {
            "canonical_path": lifecycle_child["agent_path"],
            "operations": lifecycle_operations,
            "restored_same_path": True,
            "terminal": lifecycle_child["terminal"],
        },
        "ultra": {
            "root_model": rows["ultra_root"]["model"],
            "root_effective_effort": rows["ultra_root"]["reasoning_effort"],
            "child_requested_effort": "ultra",
            "child_profile": rows["ultra_child"]["agent_role"],
            "child_effective_effort": rows["ultra_child"]["reasoning_effort"],
            "child_ultra_effective": False,
        },
        "limitations": [
            "Child permissions inherit the parent turn in Codex 0.145.0",
            "The pre-merge proof selects the unmodified native model cache while the user V1 catalog pointer remains installed for rollback",
            "Installed package and post-cutover configuration readback remain release-phase checks",
        ],
    }


def _load_json(path: Path, where: str) -> dict[str, Any]:
    try:
        payload = json.loads(_read(path, 16 * 1024 * 1024, where))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MatrixError(f"{where} is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise MatrixError(f"{where} must be an object")
    return payload


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_artifacts(receipts_path: Path, matrix_path: Path) -> None:
    receipts = _load_json(receipts_path, "receipt artifact")
    expected = build_matrix(receipts)
    actual = _load_json(matrix_path, "matrix artifact")
    if actual != expected:
        raise MatrixError("matrix artifact is stale or differs from the receipt-derived projection")


def _rollout_args(values: Sequence[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        case, separator, raw_path = value.partition("=")
        if not separator or not case or not raw_path or case in result:
            raise MatrixError("--rollout must be a unique CASE=PATH value")
        result[case] = Path(raw_path).expanduser()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipts", type=Path, default=DEFAULT_RECEIPTS)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--rollout", action="append", default=[])
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.rollout:
            if not args.write or args.catalog is None:
                raise MatrixError("rollout capture requires --write and --catalog")
            receipts = capture_receipts(_rollout_args(args.rollout), args.catalog)
            _write_json(args.receipts, receipts)
            _write_json(args.matrix, build_matrix(receipts))
        elif args.write:
            receipts = _load_json(args.receipts, "receipt artifact")
            _write_json(args.matrix, build_matrix(receipts))
        if args.check:
            check_artifacts(args.receipts, args.matrix)
        if not args.write and not args.check:
            raise MatrixError("select --write, --check, or both")
    except (OSError, MatrixError) as exc:
        print(f"Codex V2 matrix failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
