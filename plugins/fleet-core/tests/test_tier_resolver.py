"""Tier palette + resolver tests, including the Codex dual-palette mapping (KTD3).

Loads the fleet_commons modules through the shim exactly as a consumer plugin would, with
FLEET_COMMONS_ROOT pinned to this checkout's fleet-core so resolution is deterministic.
"""

from __future__ import annotations

import importlib.util
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
resolver = _load("tier_resolver")


# --- palette vocabulary & ordering ------------------------------------------------------------


def test_models_strongest_first_and_efforts_weakest_first() -> None:
    assert palette.MODELS == ("fable", "opus", "sonnet", "haiku")
    assert palette.EFFORTS == ("low", "medium", "high", "xhigh")
    assert palette.model_rank("fable") == 0
    assert palette.effort_rank("low") == 0


def test_effort_ceiling_clamps_haiku() -> None:
    assert palette.effort_ceiling("haiku") == "high"
    assert not palette.supports_effort("haiku", "xhigh")
    clamped, note = palette.clamp_effort_to_model("haiku", "xhigh")
    assert clamped == "high"
    assert note is not None


def test_strongest_is_upgrade_only_merge() -> None:
    assert palette.strongest("model", ["haiku", "opus", "sonnet"]) == "opus"
    assert palette.strongest("effort", ["low", "high", "medium"]) == "high"


# --- Codex dual palette (KTD3) ----------------------------------------------------------------


def test_codex_mapping_matches_registry() -> None:
    assert palette.codex_tier("opus") == ("gpt-5.5", "high")
    assert palette.codex_tier("sonnet") == ("gpt-5.4", "medium")
    assert palette.codex_tier("haiku") == ("gpt-5.4-mini", "low")
    assert palette.codex_tier("fable") == ("gpt-5.5", "xhigh")


def test_codex_mapping_covers_every_model() -> None:
    for model in palette.MODELS:
        cm, ce = palette.codex_tier(model)
        assert isinstance(cm, str) and cm
        assert ce in palette.EFFORTS


def test_codex_accessors_reject_unknown_model() -> None:
    with pytest.raises(ValueError):
        palette.codex_model("gpt-5.5")  # a Codex model name is not a lineage tier


# --- resolver ---------------------------------------------------------------------------------


def test_resolve_reads_policy_defaults() -> None:
    r = resolver.resolve(None, "judgment")
    assert (r.model, r.effort) == ("opus", "high")
    assert r.needs_confirm is False


def test_resolve_role_tier_alias() -> None:
    r = resolver.resolve(None, "adversarial-review")
    assert r.model == "opus"


def test_resolve_expensive_tier_gates_confirm() -> None:
    assert resolver.resolve(None, "judgment", operator_override={"model": "fable"}).needs_confirm
    assert resolver.resolve(None, "judgment", operator_override={"effort": "xhigh"}).needs_confirm


def test_cheaper_fallback_weakens_model_then_effort() -> None:
    assert resolver.cheaper_fallback("opus", "high") == ("sonnet", "high")
    assert resolver.cheaper_fallback("haiku", "medium") == ("haiku", "low")
    assert resolver.cheaper_fallback("haiku", "low") == ("haiku", "low")  # floor no-op


def test_resolve_unknown_work_shape_raises() -> None:
    with pytest.raises(resolver.TierResolverError):
        resolver.resolve(None, "no-such-shape")
