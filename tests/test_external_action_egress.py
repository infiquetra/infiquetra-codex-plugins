from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import external_action_egress as egress  # noqa: E402


def test_redacts_nested_credentials_without_reporting_values() -> None:
    secret = "sk-abcdefghijklmnopqrstuvwxyz1234"
    result = egress.sanitize({"prompt": [f"API key={secret}", "safe"]})
    assert not result.blocked
    assert secret not in repr(result.payload)
    assert secret not in repr(result.detections)
    assert result.payload_sha256


def test_private_key_blocks_entire_payload() -> None:
    result = egress.sanitize("-----BEGIN PRIVATE KEY-----\nabc")
    assert result.blocked
    assert result.payload is None
    assert result.detections == ("private-key",)


def test_unsupported_objects_fail_closed() -> None:
    try:
        egress.sanitize(object())
    except TypeError as exc:
        assert "unsupported outbound payload type" in str(exc)
    else:
        raise AssertionError("unsupported payload was accepted")
