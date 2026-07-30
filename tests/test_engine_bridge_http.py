from __future__ import annotations

import io
import json
import socket
import sys
import urllib.error
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).parents[1] / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import engine_bridge_http as B  # noqa: E402


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.body = body
        self.status = status

    def read(self, *_args: object) -> bytes:
        return self.body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def invocation(*, operation: str = "chat") -> dict[str, Any]:
    return {
        "engine_id": "ollama-cloud",
        "variant": "gpt-oss-120b" if operation == "chat" else "nomic-embed-text",
        "base_url": "https://ollama.com/v1",
        "model": "gpt-oss:120b" if operation == "chat" else "nomic-embed-text",
        "operation": operation,
        "auth": {"mode": "bearer", "key_env": "OLLAMA_API_KEY"},
        "task": "bounded input",
    }


def capture(body: bytes) -> tuple[Any, dict[str, Any]]:
    seen: dict[str, Any] = {}

    def urlopen(request: Any, timeout: float) -> FakeResponse:
        seen.update(
            {
                "url": request.full_url,
                "headers": dict(request.header_items()),
                "body": json.loads(request.data),
                "timeout": timeout,
            }
        )
        return FakeResponse(body)

    return urlopen, seen


def test_chat_bridge_emits_bound_receipt_without_exposing_token() -> None:
    body = json.dumps(
        {
            "choices": [{"message": {"content": "answer"}}],
            "usage": {"total_tokens": 12},
        }
    ).encode()
    urlopen, seen = capture(body)
    payload = invocation()
    result = B.runner(urlopen=urlopen, getenv={"OLLAMA_API_KEY": "secret"}.get)(payload)

    assert result["status"] == "ok"
    assert seen["url"] == "https://ollama.com/v1/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer secret"
    assert result["receipt"]["invocation_sha256"] == B._bridge_receipt.digest_invocation(payload)
    assert B._bridge_receipt.validate_receipt(result["receipt"]) == []
    assert "secret" not in json.dumps(result)


def test_embedding_route_uses_embeddings_operation() -> None:
    body = json.dumps(
        {"data": [{"embedding": [0.1, 0.2, 0.3]}], "usage": {"total_tokens": 3}}
    ).encode()
    urlopen, seen = capture(body)
    result = B.runner(urlopen=urlopen, getenv={"OLLAMA_API_KEY": "secret"}.get)(
        invocation(operation="embedding")
    )

    assert result["status"] == "ok"
    assert result["output"] == "[0.1,0.2,0.3]"
    assert seen["url"] == "https://ollama.com/v1/embeddings"
    assert seen["body"]["input"] == "bounded input"


def test_missing_key_and_malformed_body_never_report_ok() -> None:
    urlopen, seen = capture(b"not-json")
    missing = B.runner(urlopen=urlopen, getenv=lambda _key: None)(invocation())
    assert missing["status"] == "error"
    assert seen == {}

    malformed = B.runner(urlopen=urlopen, getenv=lambda _key: "token")(invocation())
    assert malformed["status"] == "malformed"
    assert malformed["receipt"] is None


def test_http_error_closes_response_and_timeout_is_terminal() -> None:
    body = io.BytesIO()
    error = urllib.error.HTTPError(
        "https://ollama.com/v1/chat/completions",
        503,
        "unavailable",
        None,
        body,
    )

    def fail(*_args: object, **_kwargs: object) -> Any:
        raise error

    result = B.runner(urlopen=fail, getenv=lambda _key: "token")(invocation())
    assert result["status"] == "error"
    assert body.closed

    def timeout(*_args: object, **_kwargs: object) -> Any:
        raise TimeoutError

    result = B.runner(urlopen=timeout, getenv=lambda _key: "token")(invocation())
    assert result["status"] == "timeout"


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "::1", "fc00::1"])
def test_live_bridge_rejects_non_public_provider_resolution(address: str) -> None:
    result = B.runner(
        getenv=lambda _key: "token",
        resolver=lambda *_args, **_kwargs: [
            (
                socket.AF_INET6 if ":" in address else socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (address, 443),
            )
        ],
    )(invocation())
    assert result["status"] == "error"
    assert "non-public" in result["note"]


def test_timeout_bound_rejects_non_finite_or_huge_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        B.runner(timeout=float("inf"))
    with pytest.raises(ValueError, match="finite"):
        B.runner(timeout=10**1000)
