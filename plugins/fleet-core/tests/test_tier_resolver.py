"""Legacy-lineage compatibility and Codex execution-class resolution tests."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

_FLEET_CORE = Path(__file__).resolve().parents[1]
_SCRIPTS = _FLEET_CORE / "scripts"
os.environ["FLEET_COMMONS_ROOT"] = str(_FLEET_CORE)
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _load(name: str) -> ModuleType:
    path = _SCRIPTS / "fleet_commons" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"fc_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


palette = _load("tier_palette")
catalog = _load("codex_model_catalog")
resolver = _load("tier_resolver")
effort_rider = _load("effort_rider")


def _row(
    slug: str,
    efforts: tuple[str, ...],
    *,
    visibility: str = "list",
    supported_in_api: bool = True,
) -> dict:
    return {
        "slug": slug,
        "default_reasoning_level": efforts[0],
        "supported_reasoning_levels": [{"effort": effort} for effort in efforts],
        "visibility": visibility,
        "supported_in_api": supported_in_api,
    }


def _snapshot(*rows: dict):
    return catalog.normalize_catalog({"models": list(rows)}, source="fixture")


@pytest.fixture
def full_snapshot():
    return _snapshot(
        _row("gpt-5.6-sol", ("low", "medium", "high", "xhigh", "max", "ultra")),
        _row("gpt-5.6-terra", ("low", "medium", "high", "xhigh", "max", "ultra")),
        _row("gpt-5.6-luna", ("low", "medium", "high", "xhigh", "max")),
        _row("gpt-5.5", ("low", "medium", "high", "xhigh")),
        _row("gpt-5.4-mini", ("low", "medium", "high", "xhigh")),
    )


def test_legacy_palette_remains_compatible_while_scalar_policy_adds_max() -> None:
    assert palette.MODELS == ("fable", "opus", "sonnet", "haiku")
    assert palette.EFFORTS == ("low", "medium", "high", "xhigh")
    assert palette.SCALAR_EFFORTS == ("low", "medium", "high", "xhigh", "max")
    assert "ultra" not in palette.SCALAR_EFFORTS
    assert palette.codex_tier("fable") == ("gpt-5.5", "xhigh")
    assert palette.codex_tier("opus") == ("gpt-5.5", "high")
    assert palette.codex_tier("sonnet") == ("gpt-5.4", "medium")
    assert palette.codex_tier("haiku") == ("gpt-5.4-mini", "low")


def test_legacy_ladder_and_work_shape_resolver_remain_available() -> None:
    assert palette.strongest("model", ["haiku", "opus", "sonnet"]) == "opus"
    assert palette.strongest("effort", ["low", "high", "medium"]) == "high"
    assert not palette.supports_effort("haiku", "xhigh")
    assert resolver.resolve(None, "judgment").model == "opus"
    assert resolver.resolve(None, "adversarial-review").model == "opus"


def test_registry_has_exact_five_classes_and_no_role_policy() -> None:
    assert palette.EXECUTION_CLASSES == (
        "review-max",
        "review-high",
        "test-medium",
        "scan-low",
        "monitor-low",
    )
    raw = json.loads(palette.MODELS_REGISTRY_PATH.read_text(encoding="utf-8"))
    forbidden = {"role", "logical_role", "default_role", "allowed_transitions"}
    for row in raw["execution_classes"].values():
        assert not (set(row) & forbidden)


def test_registry_rejects_top_level_role_policy(tmp_path: Path) -> None:
    raw = json.loads(palette.MODELS_REGISTRY_PATH.read_text(encoding="utf-8"))
    raw["roles"] = {"devils-advocate": {"default_class": "review-high"}}
    path = tmp_path / "models.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(palette.TierPaletteError, match="unexpected registry sections"):
        palette._load_registry(path)


def test_full_catalog_resolves_exact_five_classes(full_snapshot) -> None:
    expected = {
        "review-max": ("gpt-5.6-sol", "max"),
        "review-high": ("gpt-5.6-sol", "high"),
        "test-medium": ("gpt-5.6-terra", "medium"),
        "scan-low": ("gpt-5.6-luna", "low"),
        "monitor-low": ("gpt-5.6-luna", "low"),
    }
    for execution_class, pair in expected.items():
        result = resolver.resolve_execution_class(execution_class, full_snapshot)
        assert (result.effective_model, result.effective_effort) == pair
        assert result.catalog_sha256 == full_snapshot.normalized_sha256
        assert result.catalog_input_sha256 == full_snapshot.input_sha256
        assert result.clamped is False
        assert result.effective_effort != "ultra"


def test_scan_and_monitor_keep_distinct_permission_boundaries(full_snapshot) -> None:
    scan = resolver.resolve_execution_class("scan-low", full_snapshot)
    monitor = resolver.resolve_execution_class("monitor-low", full_snapshot)
    assert (scan.effective_model, scan.effective_effort) == (
        monitor.effective_model,
        monitor.effective_effort,
    )
    assert scan.external_boundary == "none"
    assert monitor.external_boundary == "allowlisted-read"


def test_absent_preferred_uses_ordered_same_effort_fallback() -> None:
    snapshot = _snapshot(
        _row("gpt-5.6-terra", ("low", "medium", "high", "xhigh", "max")),
        _row("gpt-5.5", ("low", "medium", "high", "xhigh")),
    )
    result = resolver.resolve_execution_class("review-high", snapshot)
    assert (result.effective_model, result.effective_effort) == ("gpt-5.6-terra", "high")
    assert result.candidate_index == 1
    assert result.fallback_reason is not None


def test_fallback_preserves_effort_before_preferred_model_is_clamped() -> None:
    snapshot = _snapshot(
        _row("gpt-5.6-sol", ("low", "medium", "high", "xhigh")),
        _row("gpt-5.6-terra", ("low", "medium", "high", "xhigh", "max")),
    )
    result = resolver.resolve_execution_class("review-max", snapshot)
    assert (result.effective_model, result.effective_effort) == ("gpt-5.6-terra", "max")
    assert result.clamped is False


def test_review_max_clamps_down_to_gpt55_strongest_scalar() -> None:
    snapshot = _snapshot(_row("gpt-5.5", ("low", "medium", "high", "xhigh")))
    result = resolver.resolve_execution_class("review-max", snapshot)
    assert (result.effective_model, result.effective_effort) == ("gpt-5.5", "xhigh")
    assert result.candidate_index == 2
    assert result.clamped is True
    assert "clamped downward" in str(result.fallback_reason)


def test_no_compatible_fallback_and_upward_clamp_fail_loud() -> None:
    snapshot = _snapshot(_row("gpt-5.6-luna", ("medium", "high")))
    with pytest.raises(resolver.TierResolverError, match="no compatible selectable model"):
        resolver.resolve_execution_class("scan-low", snapshot)


def test_hidden_or_api_unsupported_model_is_not_selectable() -> None:
    snapshot = _snapshot(
        _row("gpt-5.6-luna", ("low",), visibility="hide"),
        _row("gpt-5.6-terra", ("low",), supported_in_api=False),
        _row("gpt-5.4-mini", ("low",)),
    )
    result = resolver.resolve_execution_class("scan-low", snapshot)
    assert result.effective_model == "gpt-5.4-mini"


def test_unknown_class_and_leaf_ultra_policy_fail() -> None:
    with pytest.raises(resolver.TierResolverError, match="unknown execution class"):
        resolver.resolve_execution_class("devils-advocate", _snapshot(_row("gpt-5.6-sol", ("high",))))
    with pytest.raises(palette.TierPaletteError, match="preferred effort cannot"):
        palette._candidate(
            {"model": "gpt-5.6-sol", "effort": "strongest-supported"},
            "test",
        )
    with pytest.raises(palette.TierPaletteError, match="scalar"):
        palette._candidate({"model": "gpt-5.6-sol", "effort": "ultra"}, "test")


def test_root_ultra_requires_explicit_independent_fanout(full_snapshot) -> None:
    with pytest.raises(resolver.TierResolverError, match="explicit"):
        resolver.resolve_root_orchestration(full_snapshot, effort="ultra")
    with pytest.raises(resolver.TierResolverError, match="fan-out"):
        resolver.resolve_root_orchestration(full_snapshot, effort="ultra", explicit=True)
    result = resolver.resolve_root_orchestration(
        full_snapshot,
        effort="ultra",
        explicit=True,
        independent_fanout=True,
    )
    assert result.ultra is True
    assert result.effective_model == "gpt-5.6-sol"


def test_explicit_empty_root_effort_fails_instead_of_defaulting(full_snapshot) -> None:
    with pytest.raises(resolver.TierResolverError, match="unknown root effort"):
        resolver.resolve_root_orchestration(full_snapshot, effort="")


def test_max_rider_is_advisory_and_ultra_is_excluded() -> None:
    assert set(effort_rider.EFFORT_RIDER) == set(palette.SCALAR_EFFORTS)
    assert "ultra" not in effort_rider.EFFORT_RIDER
    prompt = effort_rider.inject_effort("BODY", "max", "agent")
    assert "EFFORT (max)" in prompt
    assert "BODY" in prompt
    drift = effort_rider.reconcile_effort("max", "agent", spawn_prompt="BODY")
    assert "rider-text" in str(drift)


def test_all_consumer_shims_load_the_new_catalog_and_palette() -> None:
    repo = _FLEET_CORE.parents[1]
    shim_paths = (
        repo / "plugins/saga/scripts/fleet_commons_shim.py",
        repo / "plugins/team-execution/scripts/fleet_commons_shim.py",
        repo / "plugins/mission-control/scripts/fleet_commons_shim.py",
        repo / "plugins/unifi/skills/unifi-network/scripts/fleet_commons_shim.py",
        repo / "plugins/unifi/skills/unifi-protect/scripts/fleet_commons_shim.py",
    )
    for index, path in enumerate(shim_paths):
        spec = importlib.util.spec_from_file_location(f"consumer_shim_{index}", path)
        assert spec is not None and spec.loader is not None
        shim = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(shim)
        assert shim.load("tier_palette").EXECUTION_CLASSES == palette.EXECUTION_CLASSES
        assert hasattr(shim.load("codex_model_catalog"), "read_catalog")
