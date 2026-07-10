"""Tests for the shared 429 retry/backoff primitive (deterministic over injected seams)."""

from __future__ import annotations

import importlib.util
import os
import random
from pathlib import Path
from types import ModuleType

import pytest

_FLEET_CORE = Path(__file__).resolve().parents[1]
_SCRIPTS = _FLEET_CORE / "scripts"
os.environ["FLEET_COMMONS_ROOT"] = str(_FLEET_CORE)


def _load(name: str) -> ModuleType:
    path = _SCRIPTS / "fleet_commons" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"fc_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rb = _load("retry_backoff")


class _HttpError(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.status_code = status


def test_retries_429_then_succeeds() -> None:
    calls = {"n": 0}
    slept: list[float] = []

    def fn() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise _HttpError(429)
        return "ok"

    result = rb.retry_with_backoff(
        fn, max_attempts=5, sleep=slept.append, rng=random.Random(0)
    )
    assert result == "ok"
    assert calls["n"] == 3
    assert len(slept) == 2  # two backoffs before the successful third call


def test_non_429_propagates_immediately() -> None:
    calls = {"n": 0}

    def fn() -> None:
        calls["n"] += 1
        raise _HttpError(500)

    with pytest.raises(_HttpError):
        rb.retry_with_backoff(fn, max_attempts=5, sleep=lambda _s: None)
    assert calls["n"] == 1  # no retry on a non-retryable status


def test_exhausts_attempts_and_reraises() -> None:
    def fn() -> None:
        raise _HttpError(429)

    with pytest.raises(_HttpError):
        rb.retry_with_backoff(fn, max_attempts=3, sleep=lambda _s: None)


def test_retry_after_hint_overrides_computed_delay() -> None:
    slept: list[float] = []
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise _HttpError(429)
        return "ok"

    rb.retry_with_backoff(
        fn,
        max_attempts=3,
        sleep=slept.append,
        retry_after=lambda _exc: 7.0,
        rng=random.Random(0),
    )
    assert slept == [7.0]


def test_positive_retry_after_is_capped_at_max_delay() -> None:
    slept: list[float] = []
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise _HttpError(429)
        return "ok"

    assert rb.retry_with_backoff(
        fn,
        max_attempts=2,
        max_delay=5.0,
        retry_after=lambda _exc: 500.0,
        sleep=slept.append,
    ) == "ok"
    assert slept == [5.0]


@pytest.mark.parametrize("hint", [0.0, -10.0])
def test_nonpositive_retry_after_uses_computed_jitter(hint: float) -> None:
    slept: list[float] = []
    calls = {"n": 0}
    expected = rb._computed_delay(1, 2.0, 60.0, random.Random(7))

    def fn() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise _HttpError(429)
        return "ok"

    rb.retry_with_backoff(
        fn,
        max_attempts=2,
        base_delay=2.0,
        retry_after=lambda _exc: hint,
        sleep=slept.append,
        rng=random.Random(7),
    )
    assert slept == [expected]


def test_circuit_breaker_opens_then_half_opens() -> None:
    clock = {"t": 0.0}
    breaker = rb.CircuitBreaker(fail_threshold=2, cooldown=10.0, clock=lambda: clock["t"])
    breaker.on_failure()
    assert breaker.state == "CLOSED"
    breaker.on_failure()
    assert breaker.state == "OPEN"
    clock["t"] = 10.0
    assert breaker.state == "HALF_OPEN"
    breaker.on_success()
    assert breaker.state == "CLOSED"


def test_bridge_call_short_circuits_when_open() -> None:
    breaker = rb.CircuitBreaker(fail_threshold=1, cooldown=100.0, clock=lambda: 0.0)
    breaker.on_failure()  # trip it
    with pytest.raises(rb.CircuitOpenError):
        rb.bridge_call(lambda: "never", breaker=breaker, sleep=lambda _s: None)


def test_bridge_call_trips_breaker_on_rate_limit_but_not_on_bug() -> None:
    breaker = rb.CircuitBreaker(fail_threshold=1, cooldown=100.0, clock=lambda: 0.0)

    def bug() -> None:
        raise _HttpError(500)

    with pytest.raises(_HttpError):
        rb.bridge_call(bug, breaker=breaker, max_attempts=1, sleep=lambda _s: None)
    assert breaker.state == "CLOSED"  # correctness bug does not trip the rate-limit breaker

    def limited() -> None:
        raise _HttpError(429)

    with pytest.raises(_HttpError):
        rb.bridge_call(limited, breaker=breaker, max_attempts=1, sleep=lambda _s: None)
    assert breaker.state == "OPEN"
