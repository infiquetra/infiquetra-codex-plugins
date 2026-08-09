from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "build_codex_v2_orchestration_matrix.py"
SPEC = importlib.util.spec_from_file_location("build_codex_v2_orchestration_matrix", SCRIPT)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def receipts() -> dict:
    return json.loads(
        (ROOT / "docs" / "validation" / "codex-v2-orchestration-receipts.json").read_text()
    )


def test_committed_matrix_is_receipt_derived() -> None:
    matrix = json.loads(M.DEFAULT_MATRIX.read_text())
    payload = receipts()

    assert matrix["codex_cli_version"] == "0.145.0"
    assert (
        matrix["generated_from"]["receipt_set_sha256"]
        == payload["receipt_set_sha256"]
    )
    assert not any((ROOT / ".codex" / "agents").glob("*.toml"))


def test_the_observed_version_is_captured_rather_than_asserted_from_the_target() -> None:
    """KTD2: a target version and an observed version never share a field.

    The header records the version the receipt set was taken on. It is a literal, deliberately
    not read from `CODEX_TARGET_VERSION`: if the two were wired together, bumping the target
    would silently restamp evidence that was never retaken. A row reproved on a later version
    says so in `ROW_PROVENANCE` instead.
    """

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "u11_codex_target_version", ROOT / "scripts" / "codex_target_version.py"
    )
    assert spec is not None and spec.loader is not None
    target = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(target)

    matrix = json.loads(M.DEFAULT_MATRIX.read_text())
    assert matrix["codex_cli_version"] != target.CODEX_TARGET_VERSION
    assert "CODEX_TARGET_VERSION" not in SCRIPT.read_text(encoding="utf-8")

    reproved = M.ROW_PROVENANCE["luna_decision"]
    assert reproved["observed_on"] == target.CODEX_TARGET_VERSION
    assert reproved["observed_on"] != matrix["codex_cli_version"]


def test_dropped_receipt_fails_closed() -> None:
    payload = receipts()
    payload["receipts"] = payload["receipts"][:-1]
    payload["receipt_set_sha256"] = M._canonical_sha256(
        {"catalog": payload["catalog"], "receipts": payload["receipts"]}
    )
    with pytest.raises(M.MatrixError, match="exact required case set"):
        M.build_matrix(payload)


def test_fabricated_runtime_profile_fails_closed() -> None:
    payload = copy.deepcopy(receipts())
    row = next(item for item in payload["receipts"] if item["case"] == "profile_scan_low")
    row["model"] = "gpt-5.6-sol"
    payload["receipt_set_sha256"] = M._canonical_sha256(
        {"catalog": payload["catalog"], "receipts": payload["receipts"]}
    )
    with pytest.raises(M.MatrixError, match="profile_scan_low runtime tuple"):
        M.build_matrix(payload)


@pytest.mark.parametrize(
    ("case", "field", "value"),
    [
        ("nested_leaf", "model", "gpt-5.6-sol"),
        ("nested_parent", "sandbox_mode", "workspace-write"),
        ("lifecycle_child", "agent_role", "scan_low"),
        ("no_history_child", "model", "gpt-5.6-sol"),
        ("bounded_child", "reasoning_effort", "medium"),
        ("typed_child", "agent_role", "review_high"),
        ("ultra_root", "model", "gpt-5.6-terra"),
        ("ultra_child", "terminal", True),
    ],
)
def test_every_capability_receipt_field_is_fail_closed(
    case: str, field: str, value: object
) -> None:
    payload = copy.deepcopy(receipts())
    row = next(item for item in payload["receipts"] if item["case"] == case)
    row[field] = value
    payload["receipt_set_sha256"] = M._canonical_sha256(
        {"catalog": payload["catalog"], "receipts": payload["receipts"]}
    )
    with pytest.raises(M.MatrixError, match=f"receipt {case} runtime tuple"):
        M.build_matrix(payload)


@pytest.mark.parametrize(
    ("case", "marker", "expected"),
    [
        (case, marker, expected)
        for case, expectations in M.REQUIRED_CASE_MARKERS.items()
        for marker, expected in expectations.items()
    ],
)
def test_every_required_capability_marker_is_fail_closed(
    case: str, marker: str, expected: bool
) -> None:
    payload = copy.deepcopy(receipts())
    row = next(item for item in payload["receipts"] if item["case"] == case)
    row["markers"][marker] = not expected
    payload["receipt_set_sha256"] = M._canonical_sha256(
        {"catalog": payload["catalog"], "receipts": payload["receipts"]}
    )
    with pytest.raises(M.MatrixError, match=f"receipt {case} required markers"):
        M.build_matrix(payload)


def test_rollout_parser_projects_runtime_and_typed_result(tmp_path: Path) -> None:
    rows = [
        {
            "type": "session_meta",
            "payload": {
                "id": "child",
                "parent_thread_id": "root",
                "agent_path": "/root/typed_result",
                "agent_role": "scan_low",
                "model_provider": "openai",
                "multi_agent_version": "v2",
                "history_mode": "legacy",
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.6-terra",
                "effort": "low",
                "approval_policy": "never",
                "permission_profile": {"type": "managed"},
                "sandbox_policy": {"type": "read-only"},
                "multi_agent_version": "v2",
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "task_complete",
                "last_agent_message": json.dumps(M.TYPED_RESULT, separators=(",", ":")),
            },
        },
    ]
    path = tmp_path / "rollout.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    projection, session_id, parent_id = M._parse_rollout("typed_child", path)
    assert session_id == "child"
    assert parent_id == "root"
    assert projection["typed_result_valid"] is True
    assert projection["terminal"] is True
    assert projection["model"] == "gpt-5.6-terra"


def test_rollout_digest_tampering_fails_before_derivation() -> None:
    payload = receipts()
    payload["receipts"][0]["rollout_sha256"] = "not-a-digest"
    payload["receipt_set_sha256"] = M._canonical_sha256(
        {"catalog": payload["catalog"], "receipts": payload["receipts"]}
    )
    with pytest.raises(M.MatrixError, match="rollout digest"):
        M.build_matrix(payload)


def test_receipt_artifact_contains_no_session_ids_or_host_paths() -> None:
    source = M.DEFAULT_RECEIPTS.read_text()
    assert "/Users/" not in source
    assert "parent_thread_id" not in source
    assert '"session_id"' not in source
