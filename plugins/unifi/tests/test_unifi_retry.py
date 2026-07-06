"""Shared 429 retry/backoff adoption in the unifi network and protect clients.

Both clients wrap their raw HTTP call in fleet-commons' ``retry_with_backoff`` instead of
surfacing a 429 to the operator on the first hit. This test drives each client's ``_request``
against a fake ``requests.request`` that returns 429 twice then 200, and asserts the retry
primitive is what absorbs the transient rate limit (call count == 3, no early exit).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).parent.parent


def _load_client(rel_path: str, module_name: str) -> ModuleType:
    path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Ensure the module's own sys.path insert (for its vendored fleet_commons_shim) resolves
    # against its own directory, not a previously-loaded sibling's.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _fake_response(status_code: int, json_body: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {"Retry-After": "0"}
    resp.content = b"{}" if json_body is None else b"non-empty"
    resp.json.return_value = json_body or {}
    return resp


@pytest.mark.parametrize(
    ("rel_path", "module_name", "client_cls"),
    [
        (
            "skills/unifi-network/scripts/unifi_network_client.py",
            "unifi_network_client_retry_test",
            "UnifiNetworkClient",
        ),
        (
            "skills/unifi-protect/scripts/unifi_protect_client.py",
            "unifi_protect_client_retry_test",
            "UnifiProtectClient",
        ),
    ],
)
def test_client_retries_transient_429_then_succeeds(
    rel_path: str, module_name: str, client_cls: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UNIFI_API_KEY", "test-key")
    module = _load_client(rel_path, module_name)

    responses = [
        _fake_response(429),
        _fake_response(429),
        _fake_response(200, {"ok": True}),
    ]
    with (
        patch.object(module.requests, "request") as mock_request,
        patch.object(module.time, "sleep", return_value=None),
    ):
        mock_request.side_effect = responses
        client = getattr(module, client_cls)(api_key="test-key", host="10.0.0.1")
        result = client._request("GET", "https://10.0.0.1/api/test")

    assert result == {"ok": True}
    assert mock_request.call_count == 3


@pytest.mark.parametrize(
    ("rel_path", "module_name", "client_cls"),
    [
        (
            "skills/unifi-network/scripts/unifi_network_client.py",
            "unifi_network_client_retry_exhaust_test",
            "UnifiNetworkClient",
        ),
        (
            "skills/unifi-protect/scripts/unifi_protect_client.py",
            "unifi_protect_client_retry_exhaust_test",
            "UnifiProtectClient",
        ),
    ],
)
def test_client_surfaces_typed_error_when_retries_exhausted(
    rel_path: str, module_name: str, client_cls: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UNIFI_API_KEY", "test-key")
    module = _load_client(rel_path, module_name)

    with (
        patch.object(module.requests, "request") as mock_request,
        patch.object(module.time, "sleep", return_value=None),
        patch("builtins.print"),
    ):
        mock_request.return_value = _fake_response(429)
        client = getattr(module, client_cls)(api_key="test-key", host="10.0.0.1")
        with pytest.raises(SystemExit) as excinfo:
            client._request("GET", "https://10.0.0.1/api/test")

    assert excinfo.value.code == 1
    assert mock_request.call_count == 3  # default max_attempts
