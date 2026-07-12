#!/usr/bin/env python3
"""Compose validated repo-local provider rows with the canonical engine registry."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from engine_overlay import EngineOverlay, EngineOverlayError, load_overlay
from engine_registry import Registry, RegistryError


def canonical_mapping(path: Path | str) -> dict[str, Any]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RegistryError(f"registry must be a mapping: {path}")
    return dict(raw)


def compose_mapping(canonical: dict[str, Any], overlay: EngineOverlay) -> dict[str, Any]:
    composed = deepcopy(canonical)
    engines = composed.get("engines")
    if not isinstance(engines, list):
        raise RegistryError("registry engines must be a list")
    canonical_keys = {_row_key(row, source="canonical registry") for row in engines}
    overlay_keys: set[str] = set()
    for row in overlay.engines:
        key = _row_key(row, source="engine overlay")
        if key in canonical_keys:
            raise EngineOverlayError(f"engine key {key!r} exists in canonical registry and overlay")
        if key in overlay_keys:
            raise EngineOverlayError(f"duplicate overlay engine key {key!r}")
        overlay_keys.add(key)
        engines.append(deepcopy(dict(row)))
    Registry.from_dict(composed)
    return composed


def load_composed_registry(
    registry_path: Path | str,
    repo_root: Path | str,
) -> Registry:
    return Registry.from_dict(
        compose_mapping(canonical_mapping(registry_path), load_overlay(repo_root))
    )


def _row_key(row: Any, *, source: str) -> str:
    if not isinstance(row, dict):
        raise RegistryError(f"{source} engine rows must be objects")
    engine_id = row.get("engine_id")
    variant = row.get("variant")
    if not isinstance(engine_id, str) or not engine_id or not isinstance(variant, str) or not variant:
        raise RegistryError(f"{source} engine row requires engine_id and variant")
    return f"{engine_id}/{variant}"
