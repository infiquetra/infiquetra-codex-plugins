#!/usr/bin/env python3
"""Bounded, immutable projection of ``codex debug models``.

The live command is attempted first and the bundled catalog once on any rejected result. Only
selection-relevant fields survive normalization; model instructions and unknown fields never enter
the snapshot. CI should inject fixture command results instead of reading mutable live state.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

COMMAND_TIMEOUT_SECONDS = 15.0
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
CATALOG_EFFORTS = frozenset({"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"})
CATALOG_VISIBILITIES = frozenset({"list", "hide"})
MODEL_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class CatalogError(RuntimeError):
    """Raised when neither Codex catalog source yields an accepted projection."""


class CatalogCommandError(CatalogError):
    """Raised for timeout, output-bound, or process failures."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True)
class CatalogModel:
    slug: str
    default_effort: str
    supported_efforts: tuple[str, ...]
    visibility: str
    supported_in_api: bool

    @property
    def selectable(self) -> bool:
        return self.visibility == "list" and self.supported_in_api

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "default_effort": self.default_effort,
            "supported_efforts": list(self.supported_efforts),
            "visibility": self.visibility,
            "supported_in_api": self.supported_in_api,
        }


@dataclass(frozen=True)
class CatalogSnapshot:
    source: Literal["refreshed", "bundled", "fixture"]
    normalized_sha256: str
    input_sha256: str
    models: tuple[CatalogModel, ...]

    def model(self, slug: str) -> CatalogModel | None:
        return next((model for model in self.models if model.slug == slug), None)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "normalized_sha256": self.normalized_sha256,
            "input_sha256": self.input_sha256,
            "models": [model.to_jsonable() for model in self.models],
        }


Run = Callable[[Sequence[str], float, int], CommandResult]


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.kill()
    process.wait()


def _run_bounded(
    argv: Sequence[str], timeout_seconds: float, max_output_bytes: int
) -> CommandResult:
    """Execute one argv-only command while enforcing a combined stdout/stderr byte ceiling."""
    if not argv or not all(isinstance(value, str) and value for value in argv):
        raise CatalogCommandError("catalog command argv must contain non-empty strings")
    process = subprocess.Popen(  # noqa: S603 - fixed argv supplied by read_catalog
        list(argv),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        env=os.environ.copy(),
    )
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    stdout_fd = process.stdout.fileno()
    stderr_fd = process.stderr.fileno()
    streams = {stdout_fd: bytearray(), stderr_fd: bytearray()}
    for stream in (process.stdout, process.stderr):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout_seconds
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _terminate(process)
                raise CatalogCommandError("catalog command timed out")
            events = selector.select(remaining)
            if not events:
                continue
            for key, _mask in events:
                stream = key.fileobj
                try:
                    chunk = os.read(stream.fileno(), 64 * 1024)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    continue
                streams[stream.fileno()].extend(chunk)
                if sum(len(value) for value in streams.values()) > max_output_bytes:
                    _terminate(process)
                    raise CatalogCommandError("catalog command exceeded the 16 MiB output ceiling")
        returncode = process.wait(timeout=max(0.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired as exc:
        _terminate(process)
        raise CatalogCommandError("catalog command timed out") from exc
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
    return CommandResult(
        returncode=returncode,
        stdout=bytes(streams[stdout_fd]),
        stderr=bytes(streams[stderr_fd]),
    )


def _models_list(payload: Any) -> list[Any]:
    rows = payload.get("models") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise CatalogError("model catalog must contain a non-empty models list")
    return rows


def normalize_catalog(
    payload: Any,
    *,
    source: Literal["refreshed", "bundled", "fixture"],
    input_bytes: bytes | None = None,
) -> CatalogSnapshot:
    """Return the closed, immutable selection projection for one parsed payload."""
    models: list[CatalogModel] = []
    seen_slugs: set[str] = set()
    for index, raw in enumerate(_models_list(payload)):
        if not isinstance(raw, dict):
            raise CatalogError(f"model row {index} must be an object")
        slug = raw.get("slug")
        default = raw.get("default_reasoning_level")
        levels = raw.get("supported_reasoning_levels")
        visibility = raw.get("visibility")
        supported_in_api = raw.get("supported_in_api")
        if not isinstance(slug, str) or not MODEL_SLUG_RE.fullmatch(slug) or slug in seen_slugs:
            raise CatalogError(f"model row {index} has a missing or duplicate slug")
        if default not in CATALOG_EFFORTS:
            raise CatalogError(f"model {slug!r} has an unsupported default effort")
        if not isinstance(levels, list) or not levels:
            raise CatalogError(f"model {slug!r} has no supported reasoning levels")
        efforts: list[str] = []
        for level in levels:
            if not isinstance(level, dict) or level.get("effort") not in CATALOG_EFFORTS:
                raise CatalogError(f"model {slug!r} has a malformed reasoning level")
            effort = level["effort"]
            if effort in efforts:
                raise CatalogError(f"model {slug!r} repeats effort {effort!r}")
            efforts.append(effort)
        if default not in efforts:
            raise CatalogError(f"model {slug!r} default effort is not in its supported levels")
        if visibility not in CATALOG_VISIBILITIES or not isinstance(supported_in_api, bool):
            raise CatalogError(f"model {slug!r} has malformed visibility/API support")
        seen_slugs.add(slug)
        models.append(
            CatalogModel(
                slug=slug,
                default_effort=default,
                supported_efforts=tuple(efforts),
                visibility=visibility,
                supported_in_api=supported_in_api,
            )
        )
    normalized = [model.to_jsonable() for model in models]
    accepted_input = input_bytes if input_bytes is not None else _canonical_json_bytes(payload)
    return CatalogSnapshot(
        source=source,
        normalized_sha256=hashlib.sha256(_canonical_json_bytes(normalized)).hexdigest(),
        input_sha256=hashlib.sha256(accepted_input).hexdigest(),
        models=tuple(models),
    )


def _parse_result(result: CommandResult, source: Literal["refreshed", "bundled"]) -> CatalogSnapshot:
    if len(result.stdout) + len(result.stderr) > MAX_OUTPUT_BYTES:
        raise CatalogCommandError(f"{source} catalog command exceeded the 16 MiB output ceiling")
    if result.returncode:
        raise CatalogCommandError(f"{source} catalog command failed with exit {result.returncode}")
    if not result.stdout:
        raise CatalogError(f"{source} catalog command returned empty output")
    try:
        payload = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CatalogError(f"{source} catalog command returned invalid JSON") from exc
    return normalize_catalog(payload, source=source, input_bytes=result.stdout)


def read_catalog(run: Run = _run_bounded) -> CatalogSnapshot:
    """Read refreshed then bundled catalog state exactly once each, returning the first accepted one."""
    failures: list[str] = []
    commands: tuple[tuple[Literal["refreshed", "bundled"], tuple[str, ...]], ...] = (
        ("refreshed", ("codex", "debug", "models")),
        ("bundled", ("codex", "debug", "models", "--bundled")),
    )
    for source, argv in commands:
        try:
            result = run(argv, COMMAND_TIMEOUT_SECONDS, MAX_OUTPUT_BYTES)
            return _parse_result(result, source)
        except (CatalogError, OSError) as exc:
            failures.append(f"{source}: {exc}")
    raise CatalogError("both Codex model catalog sources failed: " + "; ".join(failures))


capture_catalog = read_catalog
