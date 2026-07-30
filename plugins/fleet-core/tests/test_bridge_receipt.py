"""External-engine receipt and output-attestation proof tests."""

from __future__ import annotations

import importlib.util
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


def test_invocation_digest_is_canonical_and_receipt_validates_shape() -> None:
    first = {"model": "m", "task": "review", "effort": "high"}
    second = {"effort": "high", "task": "review", "model": "m"}
    digest = receipt.digest_invocation(first)

    assert digest == receipt.digest_invocation(second)
    value = receipt.emit_receipt(
        engine_id="agy",
        variant="v",
        transport="cli",
        wall_time_s=0.1,
        bytes_produced=1,
        runner={"pid": 1, "argv": ["agy"], "exit_code": 0},
        invocation_sha256=digest,
    )
    assert receipt.validate_receipt(value) == []
    value["invocation_sha256"] = "A" * 64
    assert any("invocation_sha256" in error for error in receipt.validate_receipt(value))


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
