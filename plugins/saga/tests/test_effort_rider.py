"""U3: effort cascade honoring — the fleet-core effort_rider seam + team_emitter clamp.

`effort` is a first-class, cascade-resolved field (#363). Two surfaces are exercised:

* ``fleet_commons.effort_rider`` (loaded through saga's vendored shim) — the one place that
  decides how a resolved effort is honored per spawn kind (agent rider vs real-knob
  pass-through) and reconciled post-run.
* ``team_emitter._resolved_tier_cell`` — the emitter honors the cascade-resolved effort by
  clamping it to the resident model's palette ceiling, surfacing the clamp rather than
  emitting an un-runnable tier.
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


if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fleet_commons_shim  # noqa: E402

TEAM_EMITTER = _load("team_emitter")
_EFFORT_RIDER = fleet_commons_shim.load("effort_rider")


def test_agent_path_prepends_rider() -> None:
    out = _EFFORT_RIDER.inject_effort("BODY", "high", "agent")
    assert out.endswith("BODY")
    assert out != "BODY"
    assert _EFFORT_RIDER.EFFORT_RIDER["high"] in out


def test_real_knob_paths_are_passthrough() -> None:
    # workflow and external-engine already carry effort as a real per-call knob; no rider.
    assert _EFFORT_RIDER.inject_effort("BODY", "high", "workflow") == "BODY"
    assert _EFFORT_RIDER.inject_effort("BODY", "high", "external-engine") == "BODY"


def test_unknown_effort_and_kind_raise() -> None:
    with pytest.raises(ValueError):
        _EFFORT_RIDER.inject_effort("BODY", "med", "agent")
    with pytest.raises(ValueError):
        _EFFORT_RIDER.inject_effort("BODY", "high", "teammate")


def test_reconcile_match_and_mismatch() -> None:
    assert (
        _EFFORT_RIDER.reconcile_effort("high", "workflow", manifest_effort="high") is None
    )
    drift = _EFFORT_RIDER.reconcile_effort("high", "workflow", manifest_effort="low")
    assert drift is not None and "tiering-drift" in drift


def test_emitter_cell_clamps_effort_over_ceiling() -> None:
    # haiku cannot run xhigh; the cell shows the clamped tier with a visible marker.
    cell = TEAM_EMITTER._resolved_tier_cell("haiku", "xhigh")
    assert cell.startswith("haiku/high")
    assert "clamped from xhigh" in cell


def test_emitter_cell_passthrough_when_within_ceiling() -> None:
    assert TEAM_EMITTER._resolved_tier_cell("sonnet", "xhigh") == "sonnet/xhigh"
    assert TEAM_EMITTER._resolved_tier_cell("haiku", "high") == "haiku/high"
