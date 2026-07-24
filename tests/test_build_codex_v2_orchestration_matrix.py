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
    M.check_artifacts(M.DEFAULT_RECEIPTS, M.DEFAULT_MATRIX)


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
    with pytest.raises(M.MatrixError, match="profile receipt scan_low"):
        M.build_matrix(payload)


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
