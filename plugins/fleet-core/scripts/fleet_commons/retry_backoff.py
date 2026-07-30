#!/usr/bin/env python3
"""Stateless shared 429 retry/backoff primitive.

Consumers load this module through their vendored ``fleet_commons_shim``:
``fleet_commons_shim.load("retry_backoff")``.

The module deliberately owns no cross-call retry or circuit-breaker state. It only
provides one bounded call helper for consumers such as the UniFi clients. Process
lifecycle, retries outside this one call, and recovery policy belong to the Codex
harness or the caller.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import Any


def _status_of(exc: BaseException) -> Any:
    """Best-effort HTTP status extraction from a raised error (``status_code`` or ``status``)."""
    return getattr(exc, "status_code", getattr(exc, "status", None))


def _computed_delay(
    attempt: int, base_delay: float, max_delay: float, rng: random.Random
) -> float:
    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
    return float(delay * (0.5 + rng.random() * 0.5))


def _retry_delay(
    *,
    attempt: int,
    base_delay: float,
    max_delay: float,
    hint: float | None,
    rng: random.Random,
) -> float:
    if hint is not None:
        hint_delay = float(hint)
        if hint_delay > 0:
            return min(max_delay, hint_delay)
    return _computed_delay(attempt, base_delay, max_delay, rng)


def retry_with_backoff(
    fn: Callable[[], Any],
    *,
    on_status: int = 429,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    is_retryable: Callable[[BaseException], bool] | None = None,
    retry_after: Callable[[BaseException], float | None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> Any:
    """Call ``fn()`` with jittered exponential backoff, retrying a rate-limit failure.

    ``is_retryable`` defaults to "the raised error carries ``on_status``" (429). A non-retryable error
    propagates immediately (no wasted retry). On the final attempt the last error re-raises. ``retry_after``
    may extract a server ``Retry-After`` hint (seconds) from the error to override the computed delay.

    Positive hints are capped at ``max_delay``. Zero or negative hints fall back to the computed
    delay so they cannot create a tight retry loop. The computed delay is jittered 50–100%.
    """
    _rng = rng if rng is not None else random.Random()  # nosec B311 - jitter, not security
    retryable = (
        is_retryable if is_retryable is not None else (lambda exc: _status_of(exc) == on_status)
    )

    attempt = 0
    while True:
        attempt += 1
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - re-raised below unless a retryable 429
            if attempt >= max_attempts or not retryable(exc):
                raise
            hint = retry_after(exc) if retry_after is not None else None
            delay = _retry_delay(
                attempt=attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                hint=hint,
                rng=_rng,
            )
            sleep(delay)
