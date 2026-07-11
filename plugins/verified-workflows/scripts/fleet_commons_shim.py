#!/usr/bin/env python3
"""Fleet-commons resolution shim — how a Codex plugin finds fleet-core at run time.

Canonical copy: ``plugins/fleet-core/scripts/fleet_commons_shim.py``. Consumer plugins vendor a
byte-identical copy into their own ``scripts/`` (unifi vendors into each skill's ``scripts/``);
a repo drift-guard test (``tests/test_shim_drift.py``) compares every vendored copy to this
canonical file. Keep this file minimal and rarely-changing — it is bootstrap code, not a home
for logic.

Codex-native resolution ladder (first rung that succeeds wins; provenance is part of the return
value). This deliberately drops the two Claude-host rungs (the Claude installed-plugins registry
and the Claude-plugin-root cache-sibling scan): Codex does not maintain that registry, so
emulating it would be a silent dead rung. The divergence from upstream's byte-identical shim is
recorded in ``docs/portability/codex-saga-064-drift-classification.md``:

1. ``FLEET_COMMONS_ROOT`` env override — explicit, so an invalid value raises rather than falls
   through.
2. Repo-checkout walk-up from this file: an ancestor holding both
   ``.agents/plugins/marketplace.json`` (the Codex repo marker) and ``plugins/fleet-core/``.
3. Codex local marketplace source: ``$CODEX_HOME/.tmp/marketplaces/*/plugins/fleet-core`` or the
   equivalent bundled/curated marketplace source path. This supports library plugins that are
   available in the marketplace but not separately installed into the cache.
4. ``~/.codex`` plugin-cache layout: ``$CODEX_HOME/plugins/cache/<marketplace>/fleet-core/<highest
   semver>/`` (``CODEX_HOME`` defaults to ``~/.codex``). Any shape surprise is a rung miss, never
   a crash.
5. Fail loud with an actionable message.

Set ``FLEET_COMMONS_DEBUG=1`` to print ``fleet-commons: rung=<n> (<name>) root=<path>`` to
stderr on every successful resolve (subprocess-observable provenance).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

RUNG_NAMES = {
    1: "env-override",
    2: "repo-walk-up",
    3: "codex-marketplace-source",
    4: "codex-cache",
}

_FAIL_MESSAGE = (
    "fleet-commons: could not resolve a fleet-core root (tried FLEET_COMMONS_ROOT, repo walk-up "
    "for .agents/plugins/marketplace.json, CODEX_HOME/.tmp marketplace sources, and the ~/.codex "
    "plugin-cache layout). Fix: install the fleet-core plugin from the infiquetra-codex-plugins "
    "marketplace, refresh the local marketplace source, or set "
    "FLEET_COMMONS_ROOT to a checkout's plugins/fleet-core directory."
)


def _is_valid_root(root: Path) -> bool:
    return (root / "scripts" / "fleet_commons").is_dir()


def _semver_key(name: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(part) for part in name.split("."))
    except ValueError:
        return None


def _codex_home() -> Path:
    override = os.environ.get("CODEX_HOME")
    return Path(override) if override else Path.home() / ".codex"


def _rung_codex_cache() -> Path | None:
    cache = _codex_home() / "plugins" / "cache"
    if not cache.is_dir():
        return None
    candidates: list[tuple[tuple[int, ...], Path]] = []
    try:
        marketplaces = list(cache.iterdir())
    except OSError:
        return None
    for marketplace in marketplaces:
        versions_dir = marketplace / "fleet-core"
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
            if key is not None:
                candidates.append((key, child))
    for _, root in sorted(candidates, reverse=True):
        if _is_valid_root(root):
            return root
    return None


def _rung_codex_marketplace_source() -> Path | None:
    home = _codex_home()
    roots = [
        home / ".tmp" / "marketplaces",
        home / ".tmp" / "bundled-marketplaces",
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            candidates.extend(child / "plugins" / "fleet-core" for child in root.iterdir())
        except OSError:
            continue
    candidates.append(home / ".tmp" / "plugins" / "plugins" / "fleet-core")
    for candidate in sorted(candidates):
        if _is_valid_root(candidate):
            return candidate
    return None


def resolve_root() -> tuple[Path, int]:
    """Resolve the fleet-core root; returns ``(root, rung)`` or raises RuntimeError."""
    resolved: tuple[Path, int] | None = None
    override = os.environ.get("FLEET_COMMONS_ROOT")
    if override:
        root = Path(override)
        if not _is_valid_root(root):
            raise RuntimeError(
                f"fleet-commons: FLEET_COMMONS_ROOT={override!r} is not a fleet-core root "
                "(expected a directory containing scripts/fleet_commons/)."
            )
        resolved = (root, 1)
    if resolved is None:
        for ancestor in Path(__file__).resolve().parents:
            candidate = ancestor / "plugins" / "fleet-core"
            marketplace = ancestor / ".agents" / "plugins" / "marketplace.json"
            if marketplace.is_file() and _is_valid_root(candidate):
                resolved = (candidate, 2)
                break
    if resolved is None and (root := _rung_codex_marketplace_source()) is not None:
        resolved = (root, 3)
    if resolved is None and (root := _rung_codex_cache()) is not None:
        resolved = (root, 4)
    if resolved is None:
        raise RuntimeError(_FAIL_MESSAGE)
    if os.environ.get("FLEET_COMMONS_DEBUG") == "1":
        root, rung = resolved
        print(
            f"fleet-commons: rung={rung} ({RUNG_NAMES[rung]}) root={root}",
            file=sys.stderr,
        )
    return resolved


def resolved_version() -> str:
    """The resolved fleet-core's own version, for diagnostics; 'unknown' when unreadable."""
    import json

    root, _ = resolve_root()
    try:
        manifest = json.loads(
            (root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        return str(manifest["version"])
    except (OSError, ValueError, KeyError, TypeError):
        return "unknown"


def load(module: str) -> ModuleType:
    """Load ``<root>/scripts/fleet_commons/<module>.py``.

    Repeated loads against the same resolved root return the same module object; the cache is
    keyed by ``(module, root)`` so a changed resolution input (e.g. ``FLEET_COMMONS_ROOT``
    re-pointed mid-process, as tests do) re-loads instead of returning a stale module.
    """
    root, _ = resolve_root()
    cache_key = f"_fleet_commons_{module}@{root}"
    cached = sys.modules.get(cache_key)
    if cached is not None:
        return cached
    module_path = root / "scripts" / "fleet_commons" / f"{module}.py"
    if not module_path.is_file():
        raise RuntimeError(
            f"fleet-commons: module {module!r} not found at {module_path} "
            f"(fleet-core resolved to {root}, version {resolved_version()})."
        )
    spec = importlib.util.spec_from_file_location(cache_key, module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - importlib internal failure
        raise RuntimeError(f"fleet-commons: importlib could not load {module_path}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[cache_key] = loaded
    try:
        spec.loader.exec_module(loaded)
    except BaseException:
        sys.modules.pop(cache_key, None)
        raise
    return loaded
