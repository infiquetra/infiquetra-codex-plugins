#!/usr/bin/env python3
"""Repo-local Saga external-engine route overlay state."""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine_registry import CAPABILITIES

OVERLAY_VERSION = 1
OVERLAY_PATH = Path(".codex") / "saga" / "engine-overlay.json"


class EngineOverlayError(ValueError):
    """Raised when the repo-local engine overlay is malformed."""


@dataclass(frozen=True)
class EngineOverlay:
    """Validated local routes, pins, and deprecations for registry routing."""

    pins: Mapping[str, str] | None = None
    deprecated: frozenset[str] | set[str] | list[str] | tuple[str, ...] = frozenset()
    engines: Sequence[Mapping[str, Any]] = ()

    def __post_init__(self) -> None:
        pins = dict(self.pins or {})
        deprecated = frozenset(self.deprecated or ())
        engines = tuple(dict(row) for row in self.engines)
        for capability, engine_key in pins.items():
            _validate_capability(capability)
            _validate_engine_key(engine_key)
        for engine_key in deprecated:
            _validate_engine_key(engine_key)
        seen: set[str] = set()
        for row in engines:
            key = _engine_row_key(row)
            if key in seen:
                raise EngineOverlayError(f"duplicate overlay engine key {key!r}")
            seen.add(key)
        object.__setattr__(self, "pins", pins)
        object.__setattr__(self, "deprecated", deprecated)
        object.__setattr__(self, "engines", engines)

    def to_json(self) -> dict[str, object]:
        return {
            "version": OVERLAY_VERSION,
            "pins": dict(sorted(dict(self.pins or {}).items())),
            "deprecated": sorted(self.deprecated),
            "engines": [dict(row) for row in self.engines],
        }


def overlay_path(repo_root: Path | str) -> Path:
    root = Path(repo_root).resolve()
    path = root / OVERLAY_PATH
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(root) or path.is_symlink():
        raise EngineOverlayError("engine overlay path escapes the repository state root")
    return path


def load_overlay(repo_root: Path | str) -> EngineOverlay:
    """Load repo-local overlay state, returning an empty overlay when absent."""
    path = overlay_path(repo_root)
    if not path.exists():
        return EngineOverlay()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EngineOverlayError(f"{path}: malformed JSON: {exc.msg}") from exc
    except OSError as exc:
        raise EngineOverlayError(f"{path}: cannot read overlay: {exc}") from exc
    return overlay_from_json(raw, path=path)


def overlay_from_json(raw: Any, *, path: Path | None = None) -> EngineOverlay:
    where = str(path) if path is not None else "engine overlay"
    if not isinstance(raw, dict):
        raise EngineOverlayError(f"{where}: expected a JSON object")
    if raw.get("version") != OVERLAY_VERSION:
        raise EngineOverlayError(f"{where}: expected version {OVERLAY_VERSION}")
    unknown = set(raw) - {"version", "pins", "deprecated", "engines"}
    if unknown:
        raise EngineOverlayError(f"{where}: unknown field(s): {', '.join(sorted(unknown))}")

    raw_pins = raw.get("pins", {})
    if not isinstance(raw_pins, dict):
        raise EngineOverlayError(f"{where}: 'pins' must be an object")
    pins: dict[str, str] = {}
    for capability, engine_key in raw_pins.items():
        if not isinstance(capability, str):
            raise EngineOverlayError(f"{where}: pin capability {capability!r} must be a string")
        if not isinstance(engine_key, str):
            raise EngineOverlayError(f"{where}: pin for {capability!r} must be an engine key")
        _validate_capability(capability)
        _validate_engine_key(engine_key)
        pins[capability] = engine_key

    raw_deprecated = raw.get("deprecated", [])
    if not isinstance(raw_deprecated, list):
        raise EngineOverlayError(f"{where}: 'deprecated' must be a list")
    deprecated: list[str] = []
    seen: set[str] = set()
    for index, engine_key in enumerate(raw_deprecated):
        if not isinstance(engine_key, str):
            raise EngineOverlayError(f"{where}: deprecated[{index}] must be an engine key")
        _validate_engine_key(engine_key)
        if engine_key in seen:
            raise EngineOverlayError(f"{where}: duplicate deprecated engine key {engine_key!r}")
        seen.add(engine_key)
        deprecated.append(engine_key)

    raw_engines = raw.get("engines", [])
    if not isinstance(raw_engines, list):
        raise EngineOverlayError(f"{where}: 'engines' must be a list")
    engines: list[dict[str, Any]] = []
    for index, row in enumerate(raw_engines):
        if not isinstance(row, dict):
            raise EngineOverlayError(f"{where}: engines[{index}] must be an object")
        _engine_row_key(row)
        engines.append(dict(row))

    return EngineOverlay(pins=pins, deprecated=frozenset(deprecated), engines=engines)


def save_overlay(
    repo_root: Path | str,
    overlay: EngineOverlay,
    *,
    expected_sha256: str | None = None,
    before_replace: Any | None = None,
) -> Path:
    """Persist overlay state through an atomic local file replace."""
    clean = EngineOverlay(
        pins=dict(overlay.pins or {}),
        deprecated=frozenset(overlay.deprecated),
        engines=overlay.engines,
    )
    path = overlay_path(repo_root)
    if expected_sha256 is not None and overlay_sha256(repo_root) != expected_sha256:
        raise EngineOverlayError("engine overlay digest changed before apply")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(clean.to_json(), indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if before_replace is not None:
            before_replace()
        if expected_sha256 is not None and overlay_sha256(repo_root) != expected_sha256:
            raise EngineOverlayError("engine overlay changed during apply")
        os.replace(tmp_path, path)
        os.chmod(path, 0o600)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return path


def pin_engine(overlay: EngineOverlay, capability: str, engine_key: str) -> EngineOverlay:
    _validate_capability(capability)
    _validate_engine_key(engine_key)
    pins = dict(overlay.pins or {})
    pins[capability] = engine_key
    return EngineOverlay(
        pins=pins, deprecated=frozenset(overlay.deprecated), engines=overlay.engines
    )


def deprecate_engine(overlay: EngineOverlay, engine_key: str) -> EngineOverlay:
    _validate_engine_key(engine_key)
    return EngineOverlay(
        pins=dict(overlay.pins or {}),
        deprecated=frozenset({*overlay.deprecated, engine_key}),
        engines=overlay.engines,
    )


def clear_pin(overlay: EngineOverlay, capability: str) -> EngineOverlay:
    _validate_capability(capability)
    pins = dict(overlay.pins or {})
    pins.pop(capability, None)
    return EngineOverlay(
        pins=pins, deprecated=frozenset(overlay.deprecated), engines=overlay.engines
    )


def clear_deprecated(overlay: EngineOverlay, engine_key: str) -> EngineOverlay:
    _validate_engine_key(engine_key)
    deprecated = set(overlay.deprecated)
    deprecated.discard(engine_key)
    return EngineOverlay(
        pins=dict(overlay.pins or {}),
        deprecated=frozenset(deprecated),
        engines=overlay.engines,
    )


def clear_all() -> EngineOverlay:
    return EngineOverlay()


def overlay_fingerprint(overlay: EngineOverlay | None) -> str:
    if overlay is None:
        return ""
    return json.dumps(overlay.to_json(), sort_keys=True, separators=(",", ":"))


def overlay_sha256(repo_root: Path | str) -> str:
    path = overlay_path(repo_root)
    payload = path.read_bytes() if path.exists() else b""
    return hashlib.sha256(payload).hexdigest()


def with_engine(overlay: EngineOverlay, row: Mapping[str, Any]) -> EngineOverlay:
    key = _engine_row_key(row)
    if any(_engine_row_key(existing) == key for existing in overlay.engines):
        raise EngineOverlayError(f"overlay already contains engine variant {key!r}")
    return EngineOverlay(
        pins=dict(overlay.pins or {}),
        deprecated=frozenset(overlay.deprecated),
        engines=(*overlay.engines, dict(row)),
    )


def without_engine(overlay: EngineOverlay, engine_key: str) -> EngineOverlay:
    _validate_engine_key(engine_key)
    return EngineOverlay(
        pins=dict(overlay.pins or {}),
        deprecated=frozenset(overlay.deprecated),
        engines=tuple(row for row in overlay.engines if _engine_row_key(row) != engine_key),
    )


def _validate_capability(capability: str) -> None:
    if capability not in CAPABILITIES:
        raise EngineOverlayError(f"unknown capability key {capability!r}")


def _validate_engine_key(engine_key: str) -> None:
    if not isinstance(engine_key, str) or engine_key.count("/") != 1:
        raise EngineOverlayError(f"engine key {engine_key!r} must be engine_id/variant")
    engine_id, variant = engine_key.split("/", 1)
    if not engine_id or not variant:
        raise EngineOverlayError(f"engine key {engine_key!r} must be engine_id/variant")


def _engine_row_key(row: Mapping[str, Any]) -> str:
    engine_id = row.get("engine_id")
    variant = row.get("variant")
    if not isinstance(engine_id, str) or not isinstance(variant, str):
        raise EngineOverlayError("overlay engine row requires string engine_id and variant")
    key = f"{engine_id}/{variant}"
    _validate_engine_key(key)
    return key
