from __future__ import annotations

import sys
from pathlib import Path

import pytest

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


def test_slack_token_is_detected_and_redacted() -> None:
    token = "xox" + "b-1234567890-abcdefghijklmnop"
    result = egress.sanitize(f"authorization={token}")
    assert token not in str(result.payload)
    assert result.detections == ("slack-token",)


@pytest.mark.parametrize("prefix", ["ghp", "gho", "ghu", "ghs", "ghr", "github_pat"])
def test_complete_github_token_family_is_detected(prefix: str) -> None:
    token = f"{prefix}_abcdefghijklmnopqrstuv"
    result = egress.sanitize(token)
    assert token not in str(result.payload)
    assert result.detections == ("github-token",)


@pytest.mark.parametrize("key", ["DATABASE_PASSWORD", "db_password"])
def test_prefixed_credential_keys_block_mapping_and_assignment(key: str) -> None:
    secret = "correct-horse-battery-staple"
    mapping = egress.sanitize({key: secret})
    assignment = egress.sanitize(f"{key}={secret}")
    assert mapping.blocked
    assert secret not in repr(mapping)
    assert assignment.detections == ("assignment-secret",)
    assert secret not in str(assignment.payload)


def test_structured_credential_and_jwt_values_fail_closed_without_literals() -> None:
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signaturevalue"
    result = egress.sanitize({"api_key": "literal-secret", "nested": {"jwt": token}})
    assert result.blocked
    assert "literal-secret" not in repr(result)
    assert token not in repr(result)
    assert "credential-key:api_key" in result.detections


def test_unsupported_objects_fail_closed() -> None:
    try:
        egress.sanitize(object())
    except TypeError as exc:
        assert "unsupported outbound payload type" in str(exc)
    else:
        raise AssertionError("unsupported payload was accepted")
