"""External-engine receipt, attestation, audit, and liveness proof tests."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
from pathlib import Path
from types import ModuleType

import pytest

_COMMONS = Path(__file__).resolve().parents[1] / "scripts/fleet_commons"


def _load(name: str) -> ModuleType:
    path = _COMMONS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"proof_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


attestation = _load("output_attestation")
receipt = _load("bridge_receipt")
audit = _load("delegation_audit")
state = _load("delegation_state")

CLI_RUNNER = {"pid": 123, "argv": ["codex", "exec"], "exit_code": 0}
HTTP_RUNNER = {
    "url": "https://api.example.test/v1/responses",
    "status_code": 200,
    "model": "example-model",
}


@pytest.mark.parametrize("transport,runner", [("cli", CLI_RUNNER), ("http", HTTP_RUNNER)])
def test_valid_receipts_round_trip(transport: str, runner: dict) -> None:
    output = attestation.emit_attestation(artifact="result.md", content="evidence")
    value = receipt.emit_receipt(
        engine_id="engine",
        variant="variant-high",
        transport=transport,
        wall_time_s=1.25,
        bytes_produced=len(b"evidence"),
        runner=runner,
        receipt_emitter="fixture",
        run_id="run-1",
        external_tokens=42,
        output_attestation=output,
    )
    assert receipt.validate_receipt(value) == []
    assert value["runner"] == runner


def test_wrong_transport_shape_and_malformed_optional_attestation_fail() -> None:
    value = receipt.emit_receipt(
        engine_id="engine",
        variant="variant",
        transport="cli",
        wall_time_s=1,
        bytes_produced=1,
        runner=HTTP_RUNNER,
        output_attestation={"schema": "not-real"},
    )
    errors = receipt.validate_receipt(value)
    assert any("pid" in error for error in errors)
    assert any("looks like" in error for error in errors)
    assert any("output_attestation" in error for error in errors)


def test_complete_runner_with_other_transport_or_extra_fields_is_rejected() -> None:
    value = receipt.emit_receipt(
        engine_id="engine",
        variant="variant",
        transport="cli",
        wall_time_s=1,
        bytes_produced=1,
        runner={**CLI_RUNNER, "url": "https://example.test", "metadata": "extra"},
    )
    errors = receipt.validate_receipt(value)
    assert any("looks like" in error for error in errors)
    assert any("closed 'cli' schema" in error for error in errors)


@pytest.mark.parametrize(
    "runner",
    [
        {"pid": 1, "argv": ["codex", "--api-key=secret"], "exit_code": 0},
        {"pid": 1, "argv": ["codex", "--token", "secret"], "exit_code": 0},
        {"pid": 1, "argv": ["codex", "Bearer secret"], "exit_code": 0},
        {"pid": 1, "argv": ["codex\nunsafe"], "exit_code": 0},
    ],
)
def test_cli_receipt_rejects_secret_or_control_shaped_argv(runner: dict) -> None:
    value = receipt.emit_receipt(
        engine_id="engine",
        variant="variant",
        transport="cli",
        wall_time_s=1,
        bytes_produced=1,
        runner=runner,
    )
    assert receipt.validate_receipt(value)


@pytest.mark.parametrize(
    "url",
    [
        "https://user:password@example.test/v1",
        "https://example.test/v1?api_key=secret",
        "file:///tmp/result",
    ],
)
def test_http_receipt_rejects_secret_or_non_http_url(url: str) -> None:
    runner = {**HTTP_RUNNER, "url": url}
    value = receipt.emit_receipt(
        engine_id="engine",
        variant="variant",
        transport="http",
        wall_time_s=1,
        bytes_produced=1,
        runner=runner,
    )
    assert receipt.validate_receipt(value)


def test_receipt_rejects_secret_shaped_extra_keys_recursively() -> None:
    value = receipt.emit_receipt(
        engine_id="engine",
        variant="variant",
        transport="cli",
        wall_time_s=1,
        bytes_produced=1,
        runner={**CLI_RUNNER, "metadata": {"api_key": "redacted-but-forbidden"}},
    )
    assert any("secret-shaped key" in error for error in receipt.validate_receipt(value))
    value["runner"] = {**CLI_RUNNER, "api-key": "also-forbidden"}
    assert any("secret-shaped key" in error for error in receipt.validate_receipt(value))


def test_receipt_output_bytes_are_bound_to_attestation() -> None:
    output = attestation.emit_attestation(artifact="result", content="actual")
    value = receipt.emit_receipt(
        engine_id="engine",
        variant="variant",
        transport="cli",
        wall_time_s=1,
        bytes_produced=999,
        runner=CLI_RUNNER,
        output_attestation=output,
    )
    assert any("receipt-output-attestation-bytes-mismatch" in error for error in receipt.validate_receipt(value))


def test_receipt_validates_numeric_and_identity_types() -> None:
    value = receipt.emit_receipt(
        engine_id="",
        variant="variant",
        transport="cli",
        wall_time_s=-1,
        bytes_produced=True,
        runner={"pid": True, "argv": [], "exit_code": False},
        external_tokens=-1,
    )
    errors = receipt.validate_receipt(value)
    assert any("engine_id" in error for error in errors)
    assert any("wall_time_s" in error for error in errors)
    assert any("bytes_produced" in error for error in errors)
    assert any("external_tokens" in error for error in errors)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_receipt_rejects_nonfinite_numeric_evidence(value: float) -> None:
    receipt_value = receipt.emit_receipt(
        engine_id="engine",
        variant="variant",
        transport="cli",
        wall_time_s=value,
        bytes_produced=1,
        runner=CLI_RUNNER,
        external_tokens=value,
    )
    errors = receipt.validate_receipt(receipt_value)
    assert any("wall_time_s" in error for error in errors)
    assert any("external_tokens" in error for error in errors)


def test_receipt_validation_does_not_overflow_on_large_json_integer() -> None:
    large = 10**10000
    value = receipt.emit_receipt(
        engine_id="engine",
        variant="variant",
        transport="cli",
        wall_time_s=large,
        bytes_produced=1,
        runner=CLI_RUNNER,
        external_tokens=large,
    )
    assert receipt.validate_receipt(value) == []


def test_receipt_rejects_unknown_top_level_fields() -> None:
    value = receipt.emit_receipt(
        engine_id="engine",
        variant="variant",
        transport="cli",
        wall_time_s=1,
        bytes_produced=1,
        runner=CLI_RUNNER,
    )
    value["metadata"] = "Bearer should-not-be-persisted"
    assert any("closed schema" in error for error in receipt.validate_receipt(value))


def test_output_attestation_detects_empty_byte_and_hash_mismatch() -> None:
    empty = attestation.emit_attestation(artifact="result", content="")
    assert "proof-integrity: output-attestation-empty" in attestation.validate_attestation(
        empty, require_non_empty=True
    )
    value = attestation.emit_attestation(artifact="result", content="real")
    errors = attestation.validate_attestation(value, expected_content="different")
    assert any("bytes-mismatch" in error for error in errors)
    assert any("attestation-mismatch" in error for error in errors)


def test_output_attestation_rejects_bool_bytes_and_non_hex_digest() -> None:
    value = {
        "schema": attestation.SCHEMA_NAME,
        "artifact": "result",
        "bytes": True,
        "sha256": "z" * 64,
        "empty": False,
    }
    errors = attestation.validate_attestation(value)
    assert any("bytes" in error for error in errors)
    assert any("must be hex" in error for error in errors)


def test_output_attestation_rejects_nested_extra_fields() -> None:
    value = attestation.emit_attestation(artifact="result", content="result")
    value["metadata"] = "Bearer should-not-be-persisted"
    assert any("closed schema" in error for error in attestation.validate_attestation(value))
    receipt_value = receipt.emit_receipt(
        engine_id="engine",
        variant="variant",
        transport="cli",
        wall_time_s=1,
        bytes_produced=len(b"result"),
        runner=CLI_RUNNER,
        output_attestation=value,
    )
    assert any("closed schema" in error for error in receipt.validate_receipt(receipt_value))


@pytest.mark.parametrize("artifact", ["/tmp/result", "../result", "~/.secret", "bad\\path"])
def test_output_attestation_rejects_unsafe_artifact_reference(artifact: str) -> None:
    value = attestation.emit_attestation(artifact=artifact, content="result")
    assert any("safe relative" in error for error in attestation.validate_attestation(value))


def _write_transcript(path: Path, events: list[dict]) -> None:
    path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")


def test_delegation_audit_classifies_real_and_local_fallback(tmp_path: Path) -> None:
    real_path = tmp_path / "real.jsonl"
    _write_transcript(real_path, [{"tool_name": "exec_command", "command": "codex exec task"}])
    real = audit.classify(real_path, "codex")
    assert real.classification == audit.REAL
    assert real.command_seen is True

    fallback_path = tmp_path / "fallback.jsonl"
    _write_transcript(
        fallback_path,
        [
            {"tool_name": "exec_command", "command": "codex exec task"},
            {"tool_name": "apply_patch"},
        ],
    )
    fallback = audit.classify(fallback_path, "codex")
    assert fallback.classification == audit.FALLBACK_SUSPECTED
    assert fallback.local_mutation_tool_seen is True


def test_delegation_audit_corroborates_contained_relative_bundle(tmp_path: Path) -> None:
    run_dir = tmp_path / ".codex/saga/engines/codex/runs/run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "result.json").write_text(
        json.dumps({"status": "success", "codex_launched": True}), encoding="utf-8"
    )
    bridge_value = receipt.emit_receipt(
        engine_id="codex",
        variant="codex-medium",
        transport="cli",
        wall_time_s=1,
        bytes_produced=1,
        runner=CLI_RUNNER,
        run_id="run-1",
    )
    (run_dir / "bridge-receipt.json").write_text(json.dumps(bridge_value), encoding="utf-8")
    result = audit.corroborate("codex", since_ts=None, root=tmp_path)
    assert result.launched is True
    assert result.receipt_present is True
    assert result.run_dirs == ("run-1",)
    assert str(tmp_path) not in json.dumps(result.to_jsonable())


def test_delegation_audit_does_not_join_launch_and_receipt_across_runs(tmp_path: Path) -> None:
    root = tmp_path / ".codex/saga/engines/codex/runs"
    launched = root / "run-launched"
    receipt_only = root / "run-receipt"
    launched.mkdir(parents=True)
    receipt_only.mkdir()
    (launched / "result.json").write_text(
        json.dumps({"status": "partial", "codex_launched": True}), encoding="utf-8"
    )
    (receipt_only / "result.json").write_text(
        json.dumps({"status": "partial", "codex_launched": False}), encoding="utf-8"
    )
    bridge_value = receipt.emit_receipt(
        engine_id="codex",
        variant="codex-medium",
        transport="cli",
        wall_time_s=1,
        bytes_produced=1,
        runner=CLI_RUNNER,
        run_id="run-receipt",
    )
    (receipt_only / "bridge-receipt.json").write_text(
        json.dumps(bridge_value), encoding="utf-8"
    )
    result = audit.corroborate("codex", since_ts=None, root=tmp_path)
    assert result.launched is False
    assert result.receipt_present is False
    assert any("not joined" in problem for problem in result.problems)


def test_delegation_audit_rejects_invalid_receipt_on_launched_run(tmp_path: Path) -> None:
    run_dir = tmp_path / ".codex/saga/engines/codex/runs/run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "result.json").write_text(
        json.dumps({"status": "success", "codex_launched": True}), encoding="utf-8"
    )
    (run_dir / "bridge-receipt.json").write_text("{}", encoding="utf-8")
    result = audit.corroborate("codex", since_ts=None, root=tmp_path)
    assert result.launched is False
    assert any("failed validation" in problem for problem in result.problems)


@pytest.mark.parametrize(
    "engine_id,run_id",
    [
        ("different-engine", "run-1"),
        ("codex", "different-run"),
        ("codex", ""),
    ],
)
def test_delegation_audit_binds_receipt_engine_and_run_identity(
    tmp_path: Path, engine_id: str, run_id: str
) -> None:
    run_dir = tmp_path / ".codex/saga/engines/codex/runs/run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "result.json").write_text(
        json.dumps({"status": "success", "codex_launched": True}), encoding="utf-8"
    )
    bridge_value = receipt.emit_receipt(
        engine_id=engine_id,
        variant="codex-medium",
        transport="cli",
        wall_time_s=1,
        bytes_produced=1,
        runner=CLI_RUNNER,
        run_id=run_id,
    )
    (run_dir / "bridge-receipt.json").write_text(json.dumps(bridge_value), encoding="utf-8")
    result = audit.corroborate("codex", since_ts=None, root=tmp_path)
    assert result.launched is False
    assert any("failed validation" in problem for problem in result.problems)


def test_delegation_audit_disagreement_and_unknown_engine() -> None:
    classification = audit.AuditClassification("codex", audit.REAL, True, False)
    corroboration = audit.BundleCorroboration("codex", False, False)
    assert audit.reconcile(classification, corroboration, "ok") == audit.DELEGATION_INTEGRITY
    with pytest.raises(audit.UnknownEngineError):
        audit.classify("missing", "agy")


def test_delegation_state_round_trip_ttl_and_permissions(tmp_path: Path) -> None:
    entry = state.arm("codex", "session-1", "engine-dispatch", root=tmp_path, now=100.0)
    assert state.active("session-1", root=tmp_path, now=100.0) == entry
    marker = tmp_path / state.DEFAULT_MARKER_RELATIVE_PATH
    assert stat.S_IMODE(marker.stat().st_mode) == 0o600
    assert stat.S_IMODE(marker.parent.stat().st_mode) == 0o700
    assert state.active(
        "session-1",
        root=tmp_path,
        now=100.0 + state.DEFAULT_TTL_SECONDS + 1,
    ) is None
    assert state.disarm("session-1", root=tmp_path, now=100.0) is True
    assert state.active("session-1", root=tmp_path, now=100.0) is None


def test_delegation_state_is_session_isolated_and_latest_wins(tmp_path: Path) -> None:
    state.arm("codex", "session-a", "first", root=tmp_path, now=100.0)
    state.arm("codex", "session-b", "second", root=tmp_path, now=100.0)
    state.arm("codex", "session-a", "retry", root=tmp_path, now=200.0)
    entry = state.active("session-a", root=tmp_path, now=200.0)
    assert entry is not None and entry.armed_by == "retry"
    assert state.active("session-b", root=tmp_path, now=200.0) is not None


def test_delegation_state_reader_fails_open_and_writer_rejects_escape(tmp_path: Path) -> None:
    marker = tmp_path / state.DEFAULT_MARKER_RELATIVE_PATH
    marker.parent.mkdir(parents=True)
    marker.write_text("{not-json", encoding="utf-8")
    assert state.active("session", root=tmp_path) is None

    escape_root = tmp_path / "escape-root"
    outside = tmp_path / "outside"
    (escape_root / ".codex/saga").mkdir(parents=True)
    outside.mkdir()
    os.symlink(outside, escape_root / ".codex/saga/delegation")
    with pytest.raises(ValueError, match="escapes"):
        state.arm("codex", "session", "dispatcher", root=escape_root)
    assert state.active("session", root=escape_root) is None


def test_delegation_state_lock_rejects_symlink_without_chmodding_target(tmp_path: Path) -> None:
    marker = tmp_path / state.DEFAULT_MARKER_RELATIVE_PATH
    marker.parent.mkdir(parents=True)
    outside = tmp_path / "outside-lock-target"
    outside.write_text("do-not-touch", encoding="utf-8")
    outside.chmod(0o644)
    os.symlink(outside, marker.with_suffix(".lock"))
    with pytest.raises(OSError):
        state.arm("codex", "session", "dispatcher", root=tmp_path)
    assert stat.S_IMODE(outside.stat().st_mode) == 0o644
