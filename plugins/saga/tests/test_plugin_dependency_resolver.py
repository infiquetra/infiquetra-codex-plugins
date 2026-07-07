"""Regression tests for Saga sibling plugin dependency resolution."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "plugin_dependency_resolver_under_test", SCRIPTS / "plugin_dependency_resolver.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RESOLVER = _load()


def _plugin_root(root: Path, name: str, *, version: str | None = None) -> Path:
    plugin = root / "plugins" / name if version is None else root / name / version
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        '{"name": "%s"}\n' % name, encoding="utf-8"
    )
    return plugin


def _required_file(plugin: Path, rel: str) -> Path:
    path = plugin / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# probe\n", encoding="utf-8")
    return path


def _marketplace(root: Path) -> Path:
    (root / ".agents" / "plugins").mkdir(parents=True)
    (root / ".agents" / "plugins" / "marketplace.json").write_text("{}\n", encoding="utf-8")
    return root


def test_source_checkout_sibling_resolves_required_file(tmp_path: Path) -> None:
    repo = _marketplace(tmp_path / "repo")
    saga = _plugin_root(repo, "saga")
    mission = _plugin_root(repo, "mission-control")
    expected = _required_file(mission, "config/sdlc-schema.json")
    script = saga / "scripts" / "outcome_board_sync.py"
    script.parent.mkdir(parents=True)
    script.write_text("# saga\n", encoding="utf-8")

    resolved = RESOLVER.resolve_plugin_file(
        "mission-control", "config/sdlc-schema.json", from_file=script
    )

    assert resolved == expected


def test_installed_cache_sibling_selects_highest_valid_version(tmp_path: Path) -> None:
    market = tmp_path / "codex" / "plugins" / "cache" / "infiquetra-codex-plugins"
    saga = market / "saga" / "0.64.0"
    (saga / ".codex-plugin").mkdir(parents=True)
    (saga / ".codex-plugin" / "plugin.json").write_text('{"name": "saga"}\n')
    script = saga / "scripts" / "board_progression.py"
    script.parent.mkdir(parents=True)
    script.write_text("# saga\n", encoding="utf-8")

    low = _plugin_root(market, "mission-control", version="2.1.0")
    high = _plugin_root(market, "mission-control", version="2.2.0")
    _required_file(low, "scripts/sdlc_manager.py")
    expected = _required_file(high, "scripts/sdlc_manager.py")

    resolved = RESOLVER.resolve_plugin_file(
        "mission-control", "scripts/sdlc_manager.py", from_file=script
    )

    assert resolved == expected


def test_codex_tmp_marketplace_source_resolves_for_cache_installed_consumer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    saga = codex_home / "plugins" / "cache" / "infiquetra-codex-plugins" / "saga" / "0.64.0"
    (saga / ".codex-plugin").mkdir(parents=True)
    (saga / ".codex-plugin" / "plugin.json").write_text('{"name": "saga"}\n')
    script = saga / "scripts" / "outcome_board_sync.py"
    script.parent.mkdir(parents=True)
    script.write_text("# saga\n", encoding="utf-8")

    marketplace = _marketplace(
        codex_home / ".tmp" / "marketplaces" / "infiquetra-codex-plugins"
    )
    mission = _plugin_root(marketplace, "mission-control")
    expected = _required_file(mission, "config/sdlc-schema.json")

    resolved = RESOLVER.resolve_plugin_file(
        "mission-control", "config/sdlc-schema.json", from_file=script
    )

    assert resolved == expected


def test_missing_dependency_fails_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "empty-codex-home"))
    script = tmp_path / "isolated" / "saga" / "scripts" / "outcome.py"
    script.parent.mkdir(parents=True)
    script.write_text("# saga\n", encoding="utf-8")

    with pytest.raises(RESOLVER.PluginResolutionError, match="mission-control"):
        RESOLVER.resolve_plugin_file(
            "mission-control", "config/sdlc-schema.json", from_file=script
        )
