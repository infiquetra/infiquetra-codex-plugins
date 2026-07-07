#!/usr/bin/env python3
"""Resolve sibling Codex plugin dependencies from source, marketplace, or cache layouts."""

from __future__ import annotations

import os
from pathlib import Path


class PluginResolutionError(RuntimeError):
    """A sibling plugin dependency could not be resolved from the Codex plugin environment."""


def _semver_key(name: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(part) for part in name.split("."))
    except ValueError:
        return None


def _codex_home() -> Path:
    override = os.environ.get("CODEX_HOME")
    return Path(override) if override else Path.home() / ".codex"


def _valid_root(root: Path, required_path: Path | None) -> bool:
    if not (root / ".codex-plugin" / "plugin.json").is_file():
        return False
    return required_path is None or (root / required_path).exists()


def _highest_version_root(versions_dir: Path, required_path: Path | None) -> Path | None:
    if not versions_dir.is_dir():
        return None
    candidates: list[tuple[tuple[int, ...], Path]] = []
    try:
        children = list(versions_dir.iterdir())
    except OSError:
        return None
    for child in children:
        if not child.is_dir():
            continue
        key = _semver_key(child.name)
        if key is not None and _valid_root(child, required_path):
            candidates.append((key, child))
    return sorted(candidates, reverse=True)[0][1] if candidates else None


def _source_or_marketplace_sibling(
    start_dir: Path, plugin_name: str, required_path: Path | None
) -> Path | None:
    for ancestor in (start_dir, *start_dir.parents):
        marker = ancestor / ".agents" / "plugins" / "marketplace.json"
        candidate = ancestor / "plugins" / plugin_name
        if marker.is_file() and _valid_root(candidate, required_path):
            return candidate
    return None


def _installed_sibling(
    start_dir: Path, plugin_name: str, required_path: Path | None
) -> Path | None:
    for ancestor in (start_dir, *start_dir.parents):
        if not (ancestor / ".codex-plugin" / "plugin.json").is_file():
            continue
        if ancestor.parent.name == "plugins":
            candidate = ancestor.parent / plugin_name
            if _valid_root(candidate, required_path):
                return candidate
            continue
        marketplace_root = ancestor.parent.parent
        root = _highest_version_root(marketplace_root / plugin_name, required_path)
        if root is not None:
            return root
    return None


def _codex_marketplace_source(plugin_name: str, required_path: Path | None) -> Path | None:
    home = _codex_home()
    marketplace_roots = [
        home / ".tmp" / "marketplaces",
        home / ".tmp" / "bundled-marketplaces",
    ]
    candidates: list[Path] = []
    for root in marketplace_roots:
        if not root.is_dir():
            continue
        try:
            candidates.extend(child / "plugins" / plugin_name for child in root.iterdir())
        except OSError:
            continue
    candidates.append(home / ".tmp" / "plugins" / "plugins" / plugin_name)
    for candidate in sorted(candidates):
        if _valid_root(candidate, required_path):
            return candidate
    return None


def _codex_cache(plugin_name: str, required_path: Path | None) -> Path | None:
    cache = _codex_home() / "plugins" / "cache"
    if not cache.is_dir():
        return None
    candidates: list[tuple[tuple[int, ...], Path]] = []
    try:
        marketplaces = list(cache.iterdir())
    except OSError:
        return None
    for marketplace in marketplaces:
        versions_dir = marketplace / plugin_name
        if not versions_dir.is_dir():
            continue
        try:
            children = list(versions_dir.iterdir())
        except OSError:
            continue
        for child in children:
            if not child.is_dir():
                continue
            key = _semver_key(child.name)
            if key is not None and _valid_root(child, required_path):
                candidates.append((key, child))
    return sorted(candidates, reverse=True)[0][1] if candidates else None


def resolve_plugin_root(
    plugin_name: str,
    *,
    from_file: str | Path,
    required_path: str | Path | None = None,
) -> Path:
    """Resolve a sibling plugin root for a script executing from a Codex plugin.

    Resolution order:
    1. source checkout or local marketplace sibling under ``plugins/<plugin_name>``;
    2. installed-cache sibling under the same marketplace cache root;
    3. local Codex marketplace source under ``CODEX_HOME/.tmp``;
    4. installed cache anywhere under ``CODEX_HOME/plugins/cache``.
    """
    source = Path(from_file).resolve()
    start_dir = source if source.is_dir() else source.parent
    req = Path(required_path) if required_path is not None else None

    for resolver in (
        _source_or_marketplace_sibling,
        _installed_sibling,
    ):
        if root := resolver(start_dir, plugin_name, req):
            return root
    if root := _codex_marketplace_source(plugin_name, req):
        return root
    if root := _codex_cache(plugin_name, req):
        return root

    detail = f" containing {req}" if req is not None else ""
    raise PluginResolutionError(
        f"could not resolve Codex plugin dependency {plugin_name!r}{detail} "
        f"from {source}; searched source/marketplace siblings, installed-cache siblings, "
        "CODEX_HOME/.tmp marketplaces, and CODEX_HOME/plugins/cache."
    )


def resolve_plugin_file(plugin_name: str, relative_path: str | Path, *, from_file: str | Path) -> Path:
    """Resolve ``relative_path`` within a sibling plugin dependency."""
    rel = Path(relative_path)
    return resolve_plugin_root(plugin_name, from_file=from_file, required_path=rel) / rel
