"""U3: effort cascade honoring through the fleet-core effort_rider seam.

`effort` is a first-class, cascade-resolved field (#363). Two surfaces are exercised:

* ``fleet_commons.effort_rider`` (loaded through saga's vendored shim) — the one place that
  decides how a resolved effort is honored per spawn kind (agent rider vs real-knob
  pass-through) and reconciled post-run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fleet_commons_shim  # noqa: E402

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
