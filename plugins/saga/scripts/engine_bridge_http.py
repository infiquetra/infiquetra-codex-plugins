#!/usr/bin/env python3
"""Generic OpenAI-compatible HTTP bridge for external-engine dispatch (#387, plan U5, KTD10/R7).

Any registry row declaring ``transport: http`` dispatches through this one bridge -- there is zero
per-provider branching here. Every provider difference (base URL, model id, bearer auth env var)
lives entirely in the registry row's ``invocation`` data, which reaches the bridge through the
invocation dict :func:`engine_dispatch._build_invocation` builds. Ollama Cloud and DeepSeek are the
first two rows; a new OpenAI-compatible provider is a registry row, never a code change.

The bridge is a :data:`Runner` -- the same ``dict -> dict`` seam :func:`engine_dispatch.dispatch`
already consumes (KTD10). :func:`runner` returns the live urllib-backed runner; unit tests inject a
``FakeHttpRunner`` instead so the suite needs no live network. A run returns
``{status, output, tokens, latency_seconds, receipt}`` where ``receipt`` is a schema-valid
``bridge_receipt.v1`` (HTTP shape: ``runner={url, status_code, model}``).

SECRET LIFECYCLE (plan risk "secret leakage", R7). The bearer token is resolved from the row's
``auth.key_env`` **name** exactly once, at request-build time, inside :func:`_invoke` -- and only
into the outgoing ``Authorization`` header. It is never written to the invocation dict (which flows
into run-ledger telemetry), the receipt, the returned result, evidence, or any log/exception line.
The env var *name* may appear (e.g. in a "key absent" failure note); the value never does.
"""

from __future__ import annotations

import json
import http.client
import ipaddress
import math
import socket
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fleet_commons_shim  # noqa: E402  (after the sys.path shim, by design)

_bridge_receipt = fleet_commons_shim.load("bridge_receipt")
_output_attestation = fleet_commons_shim.load("output_attestation")

Runner = Callable[[dict[str, Any]], dict[str, Any]]
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MIN_TIMEOUT_SECONDS = 1.0
MAX_TIMEOUT_SECONDS = 120.0

# The bridge's own vocabulary of non-ok terminal statuses, a subset of
# ``engine_dispatch.FAILURE_STATUSES`` -- an HTTP error / timeout / malformed body maps here and is
# NEVER reported as ``ok`` (plan U5: "HTTP error/timeout/malformed never fabricate ok").
STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_TIMEOUT = "timeout"
STATUS_MALFORMED = "malformed"

# Injection seams (typed so ``FakeHttpRunner`` and tests can substitute without live network).
UrlOpen = Callable[..., Any]
GetEnv = Callable[[str], str | None]
Clock = Callable[[], float]
Resolver = Callable[..., list[tuple[Any, ...]]]


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep reviewed provider routes from redirecting into another trust boundary."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        return None


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a prevalidated address without changing TLS's provider identity.

    ``HTTPSConnection`` normally resolves ``host`` inside ``connect``.  That leaves a DNS
    rebinding window between our public-address check and the eventual dial.  This connection
    receives an already-validated numeric address, while retaining the original provider hostname
    for both SNI and certificate hostname verification.
    """

    def __init__(
        self,
        *args: Any,
        pinned_address: str,
        tls_hostname: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._pinned_address = pinned_address
        self._tls_hostname = tls_hostname

    def connect(self) -> None:
        # A numeric address is deliberate: socket.create_connection therefore cannot perform a
        # second hostname lookup after the bridge has accepted the resolver's answer.
        self.sock = socket.create_connection(
            (self._pinned_address, self.port), self.timeout, self.source_address
        )
        if self._tunnel_host:
            self._tunnel()
        assert self._context is not None
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self._tls_hostname)


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    """urllib HTTPS handler whose transport connection is pinned to one validated address."""

    def __init__(self, *, provider_host: str, pinned_address: str) -> None:
        super().__init__()
        self._provider_host = provider_host
        self._pinned_address = pinned_address

    def https_open(self, req: urllib.request.Request) -> Any:
        def _connection(host: str, **kwargs: Any) -> _PinnedHTTPSConnection:
            return _PinnedHTTPSConnection(
                host,
                pinned_address=self._pinned_address,
                tls_hostname=self._provider_host,
                **kwargs,
            )

        return self.do_open(_connection, req)


def _pinned_urlopen(provider_host: str, addresses: tuple[str, ...]) -> UrlOpen:
    """Build one direct, no-redirect opener pinned to the checked resolver result."""

    # Resolver order is retained for a conventional preferred-address policy.  The important
    # boundary is that this is a numeric member of ``addresses``, never a hostname re-resolution.
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirectHandler(),
        _PinnedHTTPSHandler(provider_host=provider_host, pinned_address=addresses[0]),
    ).open


def runner(
    *,
    urlopen: UrlOpen | None = None,
    getenv: GetEnv | None = None,
    clock: Clock = time.monotonic,
    timeout: float = 120.0,
    resolver: Resolver | None = None,
) -> Runner:
    """Return the live urllib-backed :data:`Runner` for HTTP-transport dispatch.

    ``urlopen`` / ``getenv`` / ``clock`` are injection seams: tests pass fakes so no live network or
    real environment is touched. ``getenv`` defaults to ``os.environ.get`` (imported lazily so the
    default binds at call time, keeping the seam honest for tests that monkeypatch the environment).
    """
    live_urlopen = urlopen is None
    urlopen_factory: Callable[[str, tuple[str, ...]], UrlOpen] | None = None
    if live_urlopen:
        # Build the opener only after _invoke has validated a single DNS answer set.  This avoids
        # urllib's default hostname lookup during the later TCP connect.
        urlopen_factory = _pinned_urlopen
    if resolver is None and live_urlopen:
        resolver = socket.getaddrinfo
    if getenv is None:
        import os

        getenv = os.environ.get

    if isinstance(timeout, bool) or not isinstance(timeout, int | float):
        raise ValueError("HTTP bridge timeout must be a finite number")
    try:
        timeout_number = float(timeout)
    except OverflowError as exc:
        raise ValueError("HTTP bridge timeout must be a finite number") from exc
    if not math.isfinite(timeout_number):
        raise ValueError("HTTP bridge timeout must be a finite number")
    bounded_timeout = min(max(timeout_number, MIN_TIMEOUT_SECONDS), MAX_TIMEOUT_SECONDS)

    def _run(invocation: dict[str, Any]) -> dict[str, Any]:
        return _invoke(
            invocation,
            urlopen=urlopen,
            getenv=getenv,
            clock=clock,
            timeout=bounded_timeout,
            resolver=resolver,
            urlopen_factory=urlopen_factory,
        )

    return _run


def _invoke(
    invocation: dict[str, Any],
    *,
    urlopen: UrlOpen | None,
    getenv: GetEnv,
    clock: Clock,
    timeout: float,
    resolver: Resolver | None,
    urlopen_factory: Callable[[str, tuple[str, ...]], UrlOpen] | None,
) -> dict[str, Any]:
    """Build and send one chat/completions request; return the Runner-contract result.

    Row-driven: ``base_url``, ``model``, and ``auth`` come from the invocation dict, never from
    provider-specific code. The bearer token (when ``auth.mode == "bearer"``) is resolved here and
    only here, into the request headers -- see this module's SECRET LIFECYCLE note.
    """
    base_url = str(invocation.get("base_url") or "")
    model = str(invocation.get("model") or "")
    task = invocation.get("task")
    engine_id = str(invocation.get("engine_id") or "")
    variant = str(invocation.get("variant") or "")
    auth = invocation.get("auth") or {}

    url_error = _base_url_error(base_url)
    if url_error:
        return _failure(STATUS_ERROR, url_error)
    if not model or not isinstance(task, str):
        return _failure(STATUS_ERROR, "http invocation missing base_url, model, or task payload")
    validated_addresses: tuple[str, ...] | None = None
    if resolver is not None:
        validated_addresses, resolution_error = _validated_public_addresses(base_url, resolver)
        if resolution_error:
            return _failure(STATUS_ERROR, resolution_error)

    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": task}]}).encode(
        "utf-8"
    )
    headers = {"Content-Type": "application/json"}

    # --- SECRET BOUNDARY: token exists only inside this block and the headers dict it feeds. ---
    if auth.get("mode") == "bearer":
        key_env = str(auth.get("key_env") or "")
        token = getenv(key_env) if key_env else None
        if not token:
            # Name the env var, never a value (there is none to leak here anyway).
            return _failure(STATUS_ERROR, f"bearer key env {key_env!r} is absent")
        headers["Authorization"] = f"Bearer {token}"
    # --- END SECRET BOUNDARY: `token`/`headers` are never returned, logged, or receipted. ---

    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    started = clock()
    try:
        active_urlopen = urlopen
        if urlopen_factory is not None:
            assert validated_addresses is not None
            provider_host = urlsplit(base_url).hostname
            assert provider_host is not None
            active_urlopen = urlopen_factory(provider_host, validated_addresses)
        assert active_urlopen is not None
        with active_urlopen(request, timeout=timeout) as response:
            status_code = int(getattr(response, "status", 0) or getattr(response, "code", 0) or 0)
            try:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            except TypeError:
                # Small injected test doubles may implement only ``read()``; the live HTTP response
                # always accepts the byte bound.
                raw = response.read()
    except urllib.error.HTTPError as exc:
        # A non-2xx response: real network round-trip happened, but no usable output. The
        # exception itself holds the live response handle (the with-block above never entered),
        # so close it or every 4xx/5xx leaks a socket until GC.
        exc.close()
        return _failure(STATUS_ERROR, f"http {exc.code} from {url}")
    except TimeoutError:
        return _failure(STATUS_TIMEOUT, f"request to {url} timed out")
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return _failure(STATUS_TIMEOUT, f"request to {url} timed out")
        return _failure(STATUS_ERROR, f"http request to {url} failed: {reason}")

    if status_code < 200 or status_code >= 300:
        return _failure(STATUS_ERROR, f"http {status_code} from {url}")
    if len(raw) > MAX_RESPONSE_BYTES:
        return _failure(STATUS_MALFORMED, f"response body from {url} exceeded 4 MiB")

    latency = max(clock() - started, 0.0)

    output = _extract_output(raw)
    if output is None:
        return _failure(STATUS_MALFORMED, f"malformed response body from {url}")

    tokens = _extract_tokens(raw)
    receipt = _bridge_receipt.emit_receipt(
        engine_id=engine_id,
        variant=variant,
        transport="http",
        wall_time_s=latency,
        bytes_produced=len(output.encode("utf-8")),
        runner={"url": url, "status_code": status_code, "model": model},
        receipt_emitter="http-bridge",
        run_id=f"http:{engine_id}:{variant}:{started:.9f}",
        invocation_sha256=_bridge_receipt.digest_invocation(invocation),
        external_tokens=tokens,
        output_attestation=_output_attestation.emit_attestation(
            artifact="evidence",
            content=output,
        ),
    )
    return {
        "status": STATUS_OK,
        "output": output,
        "tokens": tokens,
        "latency_seconds": latency,
        "receipt": receipt,
    }


def _extract_output(raw: bytes) -> str | None:
    """Pull ``choices[0].message.content`` from an OpenAI chat/completions body, or ``None``."""
    try:
        parsed = json.loads(raw.decode("utf-8"))
        content = parsed["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError, UnicodeDecodeError):
        return None
    if not isinstance(content, str):
        return None
    return content


def _extract_tokens(raw: bytes) -> float:
    """Best-effort ``usage.total_tokens`` (telemetry only); ``0.0`` when absent/non-numeric."""
    try:
        parsed = json.loads(raw.decode("utf-8"))
        total = parsed["usage"]["total_tokens"]
    except (ValueError, KeyError, IndexError, TypeError, UnicodeDecodeError):
        return 0.0
    if isinstance(total, bool) or not isinstance(total, (int, float)) or total < 0:
        return 0.0
    try:
        number = float(total)
    except OverflowError:
        return 0.0
    return number if math.isfinite(number) else 0.0


def _base_url_error(base_url: str) -> str | None:
    """Reject URLs that can cross the reviewed public-provider boundary."""

    if not base_url:
        return "http invocation missing base_url, model, or task payload"
    try:
        parts = urlsplit(base_url)
        _port = parts.port
    except ValueError:
        return "http invocation base_url is invalid"
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
    ):
        return "http invocation base_url must be a credential-free HTTPS provider root"
    host = parts.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        return "http invocation base_url cannot target a local host"
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return None
    if not address.is_global:
        return "http invocation base_url cannot target a non-public address"
    return None


def _validated_public_addresses(
    base_url: str, resolver: Resolver
) -> tuple[tuple[str, ...] | None, str | None]:
    """Resolve once, returning only public numeric addresses safe for the eventual TCP dial."""
    parts = urlsplit(base_url)
    host = parts.hostname
    assert host is not None
    try:
        answers = resolver(host, parts.port or 443, type=socket.SOCK_STREAM)
    except OSError:
        return None, "http invocation provider hostname could not be resolved"
    addresses: list[str] = []
    seen: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for answer in answers:
        try:
            sockaddr = answer[4]
            address = ipaddress.ip_address(sockaddr[0])
        except (IndexError, TypeError, ValueError):
            return None, "http invocation provider hostname resolution was malformed"
        if address not in seen:
            seen.add(address)
            addresses.append(str(address))
    if not addresses:
        return None, "http invocation provider hostname resolved to no addresses"
    if any(not ipaddress.ip_address(address).is_global for address in addresses):
        return None, "http invocation provider hostname resolved to a non-public address"
    return tuple(addresses), None


def _resolved_host_error(base_url: str, resolver: Resolver) -> str | None:
    """Compatibility wrapper for callers that only need validation, not the pinned address set."""
    _addresses, error = _validated_public_addresses(base_url, resolver)
    return error


def _failure(status: str, note: str) -> dict[str, Any]:
    """A non-ok Runner result. No receipt is emitted -- there is nothing to prove ran (R7/#383).

    ``note`` may name an env var but never carries a secret value (SECRET LIFECYCLE).
    """
    return {
        "status": status,
        "output": "",
        "tokens": 0.0,
        "latency_seconds": 0.0,
        "receipt": None,
        "note": note,
    }
