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


def test_module_exposes_no_plugin_owned_retry_state() -> None:
    assert not hasattr(rb, "CircuitBreaker")
    assert not hasattr(rb, "CircuitOpenError")
    assert not hasattr(rb, "bridge_call")
