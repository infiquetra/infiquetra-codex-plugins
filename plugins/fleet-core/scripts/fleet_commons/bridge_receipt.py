"""``bridge_receipt.v1``: transport-discriminated proof for external-engine execution.

This contract does not attest a Verified Workflows logical role, profile, or effective effort.
Runner evidence is deliberately secret-hostile: CLI arguments and HTTP URLs containing credential
shapes are rejected by validation.
"""

from __future__ import annotations

import importlib.util
import math
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import urlsplit


def _load_sibling(name: str) -> ModuleType:
    try:
        module = __import__(f"{__package__}.{name}", fromlist=[name]) if __package__ else None
    except ImportError:
        module = None
    if module is not None:
        return module
    cache_key = f"_fleet_commons_{name}"
    if cache_key in sys.modules:
        return sys.modules[cache_key]
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(cache_key, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Fleet Core sibling module {name!r}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[cache_key] = loaded
    spec.loader.exec_module(loaded)
    return loaded


output_attestation = _load_sibling("output_attestation")

SCHEMA_NAME = "bridge_receipt.v1"
SCHEMA_VERSIONS = (SCHEMA_NAME,)
TRANSPORT_CLI = "cli"
TRANSPORT_HTTP = "http"
TRANSPORTS = (TRANSPORT_CLI, TRANSPORT_HTTP)
COMMON_FIELDS = ("schema", "engine_id", "variant", "transport", "wall_time_s", "bytes_produced")
OPTIONAL_FIELDS = ("receipt_emitter", "run_id", "external_tokens", "output_attestation")
RECEIPT_FIELDS = frozenset({*COMMON_FIELDS, "runner", *OPTIONAL_FIELDS})
RUNNER_FIELDS: dict[str, tuple[str, ...]] = {
    TRANSPORT_CLI: ("pid", "argv", "exit_code"),
    TRANSPORT_HTTP: ("url", "status_code", "model"),
}
_SECRET_ARGUMENT = re.compile(
    r"(?i)(?:^|[-_])(token|password|passwd|secret|credential|api[-_]?key|bearer)(?:=|$)"
)
_SECRET_KEY = re.compile(
    r"(?i)(?:^|[-_])(token|password|passwd|secret|credential|api[-_]key|bearer|auth[-_]json)(?:[-_]|$)"
)


def _secret_shaped_key(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if isinstance(key, str) and _SECRET_KEY.search(key):
                return key
            found = _secret_shaped_key(nested)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _secret_shaped_key(nested)
            if found is not None:
                return found
    return None


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return True if isinstance(value, int) else math.isfinite(value)


def emit_receipt(
    *,
    engine_id: str,
    variant: str,
    transport: str,
    wall_time_s: float,
    bytes_produced: int,
    runner: dict[str, Any],
    receipt_emitter: str = "",
    run_id: str = "",
    external_tokens: int | float | None = None,
    output_attestation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if transport not in TRANSPORTS:
        raise ValueError(f"unknown transport {transport!r}; expected one of {TRANSPORTS}")
    receipt: dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "engine_id": engine_id,
        "variant": variant,
        "transport": transport,
        "wall_time_s": wall_time_s,
        "bytes_produced": bytes_produced,
        "runner": dict(runner),
    }
    if receipt_emitter:
        receipt["receipt_emitter"] = receipt_emitter
    if run_id:
        receipt["run_id"] = run_id
    if external_tokens is not None:
        receipt["external_tokens"] = external_tokens
    if output_attestation is not None:
        receipt["output_attestation"] = dict(output_attestation)
    return receipt


def _non_empty_string(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty string")
    elif any(ord(character) < 32 for character in value):
        errors.append(f"{field} must not contain control characters")


def _validate_cli_runner(runner: dict[str, Any], errors: list[str]) -> None:
    pid = runner.get("pid")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid < 0:
        errors.append("cli runner pid must be a non-negative integer")
    argv = runner.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
        errors.append("cli runner argv must be a non-empty list of strings")
    else:
        for argument in argv:
            if any(ord(character) < 32 for character in argument):
                errors.append("cli runner argv contains a control character")
            if _SECRET_ARGUMENT.search(argument) or "bearer " in argument.lower():
                errors.append("cli runner argv contains a secret-shaped argument")
    exit_code = runner.get("exit_code")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        errors.append("cli runner exit_code must be an integer")


def _validate_http_runner(runner: dict[str, Any], errors: list[str]) -> None:
    url = runner.get("url")
    if not isinstance(url, str):
        errors.append("http runner url must be a string")
    else:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            errors.append("http runner url must be an absolute http(s) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            errors.append("http runner url must not contain credentials, query, or fragment")
    status_code = runner.get("status_code")
    if isinstance(status_code, bool) or not isinstance(status_code, int):
        errors.append("http runner status_code must be an integer")
    _non_empty_string(runner.get("model"), "http runner model", errors)


def validate_receipt(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(receipt, dict):
        return [f"receipt must be a dict, got {type(receipt).__name__}"]
    secret_key = _secret_shaped_key(receipt)
    if secret_key is not None:
        errors.append(f"receipt contains secret-shaped key {secret_key!r}")
    unexpected_fields = set(receipt) - RECEIPT_FIELDS
    if unexpected_fields:
        errors.append(f"receipt has fields outside the closed schema: {sorted(unexpected_fields)}")
    schema = receipt.get("schema")
    if schema is None:
        errors.append("missing required field: schema")
    elif schema not in SCHEMA_VERSIONS:
        errors.append(f"unknown schema version: {schema!r} (expected one of {SCHEMA_VERSIONS})")
    for field in COMMON_FIELDS:
        if field != "schema" and field not in receipt:
            errors.append(f"missing required field: {field}")
    for field in ("engine_id", "variant"):
        if field in receipt:
            _non_empty_string(receipt[field], field, errors)
    wall_time = receipt.get("wall_time_s")
    if (
        not _is_finite_number(wall_time)
        or wall_time < 0
    ):
        errors.append("wall_time_s must be a non-negative number")
    bytes_produced = receipt.get("bytes_produced")
    if (
        isinstance(bytes_produced, bool)
        or not isinstance(bytes_produced, int)
        or bytes_produced < 0
    ):
        errors.append("bytes_produced must be a non-negative integer")
    transport = receipt.get("transport")
    if transport is not None and transport not in TRANSPORTS:
        errors.append(f"unknown transport: {transport!r} (expected one of {TRANSPORTS})")
    runner = receipt.get("runner")
    if "runner" not in receipt:
        errors.append("missing required field: runner")
    elif not isinstance(runner, dict):
        errors.append(f"runner must be a dict, got {type(runner).__name__}")
    elif transport in RUNNER_FIELDS:
        required = RUNNER_FIELDS[transport]
        missing = [field for field in required if field not in runner]
        for field in missing:
            errors.append(
                f"runner section missing required field for transport {transport!r}: {field}"
            )
        if transport == TRANSPORT_CLI:
            _validate_cli_runner(runner, errors)
        else:
            _validate_http_runner(runner, errors)
        other = TRANSPORT_HTTP if transport == TRANSPORT_CLI else TRANSPORT_CLI
        other_only = set(RUNNER_FIELDS[other]) - set(required)
        if other_only & set(runner):
            errors.append(f"runner section looks like {other!r} but transport is {transport!r}")
        unexpected = set(runner) - set(required)
        if unexpected:
            errors.append(
                f"runner section has fields outside the closed {transport!r} schema: "
                f"{sorted(unexpected)}"
            )
    for field in ("receipt_emitter", "run_id"):
        if field in receipt:
            _non_empty_string(receipt[field], field, errors)
    external_tokens = receipt.get("external_tokens")
    if external_tokens is not None and (
        not _is_finite_number(external_tokens)
        or external_tokens < 0
    ):
        errors.append("external_tokens must be a non-negative number when present")
    attestation = receipt.get("output_attestation")
    if attestation is not None:
        if not isinstance(attestation, dict):
            errors.append(f"output_attestation must be a dict, got {type(attestation).__name__}")
        else:
            errors.extend(output_attestation.validate_attestation(attestation))
            attested_bytes = attestation.get("bytes")
            if (
                isinstance(bytes_produced, int)
                and not isinstance(bytes_produced, bool)
                and isinstance(attested_bytes, int)
                and not isinstance(attested_bytes, bool)
                and bytes_produced != attested_bytes
            ):
                errors.append(
                    "proof-integrity: receipt-output-attestation-bytes-mismatch "
                    f"receipt={bytes_produced} attestation={attested_bytes}"
                )
    return errors
