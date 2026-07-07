"""Codex-native resolution ladder tests for fleet_commons_shim.

Exercises each rung of the Codex ladder (env override -> repo walk-up -> ~/.codex cache ->
fail-loud) and the loader's cache-keyed reload semantics. The Claude host rungs
(installed_plugins.json, CLAUDE_PLUGIN_ROOT cache-sibling) are deliberately absent — this test
also proves they are not silently emulated.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

_SHIM_PATH = Path(__file__).resolve().parents[1] / "scripts" / "fleet_commons_shim.py"
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _executable_code(path: Path) -> str:
    """Return the module's source with its docstring and comment lines stripped.

    Uses the AST to drop the module docstring, then drops full-line comments, so token checks
    below test executable code rather than explanatory prose.
    """
    import ast

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    # Blank out the module docstring's line span, if present.
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        doc = tree.body[0]
        start = (doc.lineno or 1) - 1
        end = doc.end_lineno or doc.lineno or 1
        for i in range(start, end):
            lines[i] = ""
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def _load_shim() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fleet_commons_shim_under_test", _SHIM_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def shim(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    # Neutralize ambient env so a developer's real CODEX_HOME / FLEET_COMMONS_ROOT can't leak in.
    monkeypatch.delenv("FLEET_COMMONS_ROOT", raising=False)
    monkeypatch.delenv("FLEET_COMMONS_DEBUG", raising=False)
    monkeypatch.setenv("CODEX_HOME", str(Path("/nonexistent-codex-home-for-tests")))
    return _load_shim()


def _make_fleet_root(base: Path, version: str = "0.5.0") -> Path:
    root = base / "plugins" / "fleet-core"
    (root / "scripts" / "fleet_commons").mkdir(parents=True)
    (root / ".codex-plugin").mkdir(parents=True)
    (root / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"name": "fleet-core", "version": version}), encoding="utf-8"
    )
    (root / "scripts" / "fleet_commons" / "probe.py").write_text(
        "VALUE = 'loaded'\n", encoding="utf-8"
    )
    return root


def test_env_override_wins(shim: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make_fleet_root(tmp_path)
    monkeypatch.setenv("FLEET_COMMONS_ROOT", str(root))
    resolved, rung = shim.resolve_root()
    assert resolved == root
    assert rung == 1


def test_env_override_invalid_raises(
    shim: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FLEET_COMMONS_ROOT", str(tmp_path / "not-a-root"))
    with pytest.raises(RuntimeError, match="FLEET_COMMONS_ROOT"):
        shim.resolve_root()


def test_repo_walk_up_finds_this_checkout(
    shim: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No env override -> the shim walks up from its own location and finds this repo's fleet-core,
    # keyed off the Codex repo marker .agents/plugins/marketplace.json.
    resolved, rung = shim.resolve_root()
    assert rung == 2
    assert resolved == _REPO_ROOT / "plugins" / "fleet-core"
    assert (_REPO_ROOT / ".agents" / "plugins" / "marketplace.json").is_file()


def test_codex_cache_rung_picks_highest_semver(
    shim: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Point CODEX_HOME at a fake cache with two versions; the highest semver valid root wins.
    codex_home = tmp_path / "codex"
    cache = codex_home / "plugins" / "cache" / "infiquetra-codex-plugins" / "fleet-core"
    low = cache / "0.4.0"
    high = cache / "0.10.0"
    for ver_dir in (low, high):
        (ver_dir / "scripts" / "fleet_commons").mkdir(parents=True)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    # Force walk-up to miss by pretending the shim lives outside any repo: patch __file__ parents
    # is awkward; instead delete the marker check by resolving from an isolated shim copy path.
    isolated = tmp_path / "isolated" / "scripts"
    isolated.mkdir(parents=True)
    shim_copy = isolated / "fleet_commons_shim.py"
    shim_copy.write_bytes(_SHIM_PATH.read_bytes())
    spec = importlib.util.spec_from_file_location("shim_isolated", shim_copy)
    assert spec is not None and spec.loader is not None
    isolated_shim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(isolated_shim)
    resolved, rung = isolated_shim.resolve_root()
    assert rung == 4
    assert resolved == high  # 0.10.0 > 0.4.0 by semver tuple, not string


def test_cache_installed_consumer_finds_codex_marketplace_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FLEET_COMMONS_ROOT", raising=False)
    codex_home = tmp_path / "codex"
    marketplace_fleet = (
        codex_home
        / ".tmp"
        / "marketplaces"
        / "infiquetra-codex-plugins"
        / "plugins"
        / "fleet-core"
    )
    (marketplace_fleet / "scripts" / "fleet_commons").mkdir(parents=True)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    cache_saga_scripts = (
        codex_home
        / "plugins"
        / "cache"
        / "infiquetra-codex-plugins"
        / "saga"
        / "0.64.0"
        / "scripts"
    )
    cache_saga_scripts.mkdir(parents=True)
    shim_copy = cache_saga_scripts / "fleet_commons_shim.py"
    shim_copy.write_bytes(_SHIM_PATH.read_bytes())
    spec = importlib.util.spec_from_file_location("shim_cache_consumer", shim_copy)
    assert spec is not None and spec.loader is not None
    cache_shim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache_shim)

    resolved, rung = cache_shim.resolve_root()

    assert rung == 3
    assert resolved == marketplace_fleet


def test_fail_loud_when_nothing_resolves(
    shim: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Isolated shim with no repo marker above it and an empty CODEX_HOME.
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "empty-codex"))
    isolated = tmp_path / "isolated" / "scripts"
    isolated.mkdir(parents=True)
    shim_copy = isolated / "fleet_commons_shim.py"
    shim_copy.write_bytes(_SHIM_PATH.read_bytes())
    spec = importlib.util.spec_from_file_location("shim_fail", shim_copy)
    assert spec is not None and spec.loader is not None
    isolated_shim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(isolated_shim)
    with pytest.raises(RuntimeError, match="could not resolve a fleet-core root"):
        isolated_shim.resolve_root()


def test_no_claude_rung_emulated(shim: ModuleType) -> None:
    # The Codex shim must not carry the Claude host rungs.
    assert set(shim.RUNG_NAMES.values()) == {
        "env-override",
        "repo-walk-up",
        "codex-marketplace-source",
        "codex-cache",
    }
    # No Claude-host functional rung: the registry file is never read and the Claude cache env
    # var is never consulted in actual code. (The module docstring may reference them as the
    # dropped rungs — so we scan executable code only, not the docstring/comments.)
    assert not hasattr(shim, "_rung_installed_plugins")
    code = _executable_code(_SHIM_PATH)
    assert "installed_plugins" not in code
    assert "CLAUDE_PLUGIN_ROOT" not in code
    assert ".claude" not in code


def test_load_returns_real_module_and_caches(
    shim: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _make_fleet_root(tmp_path)
    monkeypatch.setenv("FLEET_COMMONS_ROOT", str(root))
    mod_a = shim.load("probe")
    assert mod_a.VALUE == "loaded"
    mod_b = shim.load("probe")
    assert mod_a is mod_b  # same resolved root -> cached module object


def test_load_missing_module_raises(
    shim: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _make_fleet_root(tmp_path)
    monkeypatch.setenv("FLEET_COMMONS_ROOT", str(root))
    with pytest.raises(RuntimeError, match="not found"):
        shim.load("does_not_exist")


def test_resolved_version_reads_codex_plugin_manifest(
    shim: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _make_fleet_root(tmp_path, version="1.2.3")
    monkeypatch.setenv("FLEET_COMMONS_ROOT", str(root))
    assert shim.resolved_version() == "1.2.3"
