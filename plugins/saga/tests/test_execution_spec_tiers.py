"""U3: execution_spec tier merge + validation routed through the fleet-core palette.

Covers the two load-bearing palette seams (KTD2/KTD3):

* ``segment_units`` merges member tiers upgrade-only via ``tier_palette.strongest`` —
  strongest model, highest effort, no raw index arithmetic.
* ``Tier.validate`` HALTs when an authored effort exceeds the model's real ceiling
  (haiku cannot run xhigh), instead of emitting an un-runnable dispatch.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"


def _load(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ES = _load("execution_spec")


def _unit(unit_id: str, model: str, effort: str, files: list[str]) -> "ES.Unit":
    return ES.Unit(
        unit_id=unit_id,
        label=unit_id,
        tier=ES.Tier(model=model, effort=effort),
        prompt="do the thing",
        files=files,
    )


def test_vocabulary_is_palette_derived() -> None:
    # MODELS strongest-first, EFFORTS weakest-first — sourced from models.json, not literals.
    assert ES.MODELS[0] == "fable"
    assert ES.MODELS[-1] == "haiku"
    assert ES.EFFORTS[0] == "low"
    assert ES.EFFORTS[-1] == "xhigh"
    assert "haiku" in ES._CHEAP_MODELS


def test_segment_merge_picks_strongest_model_and_effort() -> None:
    spec = ES.ExecutionSpec(
        name="merge-spec",
        description="",
        units=[
            _unit("a", "haiku", "low", ["plugins/foo/a.py"]),
            _unit("b", "sonnet", "high", ["plugins/foo/b.py"]),
        ],
        repo="",
    )
    segments = ES.segment_units(spec)
    assert len(segments) == 1
    # strongest model among {haiku, sonnet} is sonnet; highest effort among {low, high} is high.
    assert segments[0].tier.model == "sonnet"
    assert segments[0].tier.effort == "high"


def test_segment_merge_is_upgrade_only_across_three() -> None:
    spec = ES.ExecutionSpec(
        name="merge3",
        description="",
        units=[
            _unit("a", "haiku", "low", ["plugins/bar/a.py"]),
            _unit("b", "opus", "medium", ["plugins/bar/b.py"]),
            _unit("c", "sonnet", "high", ["plugins/bar/c.py"]),
        ],
        repo="",
    )
    segments = ES.segment_units(spec)
    assert len(segments) == 1
    assert segments[0].tier.model == "opus"  # strongest model present
    assert segments[0].tier.effort == "high"  # highest effort present


def test_tier_validate_halts_on_effort_over_ceiling() -> None:
    # haiku's ceiling is high; xhigh must fail loudly rather than clamp silently.
    tier = ES.Tier(model="haiku", effort="xhigh")
    with pytest.raises(ES.SpecError) as exc:
        tier.validate("unit x")
    assert "ceiling" in str(exc.value)


def test_tier_validate_accepts_effort_at_ceiling() -> None:
    ES.Tier(model="haiku", effort="high").validate("unit x")  # no raise
    ES.Tier(model="sonnet", effort="xhigh").validate("unit y")  # no raise


def test_spec_validate_rejects_over_ceiling_unit() -> None:
    spec = ES.ExecutionSpec(
        name="bad",
        description="",
        units=[_unit("a", "haiku", "xhigh", ["plugins/foo/a.py"])],
        repo="",
    )
    with pytest.raises(ES.SpecError):
        spec.validate()
