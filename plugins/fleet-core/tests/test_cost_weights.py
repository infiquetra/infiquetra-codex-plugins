"""Ordinal cost-weight completeness and drift guards."""

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
    spec = importlib.util.spec_from_file_location(f"cost_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


weights = _load("cost_weights")


def test_cost_grid_is_complete_and_includes_max() -> None:
    table = weights.load_cost_weights()
    assert weights.EFFORTS[-1] == "max"
    assert set(table) == set(weights.MODELS)
    assert all(set(row) == set(weights.EFFORTS) for row in table.values())


def test_cost_weights_are_strictly_monotonic_on_both_axes() -> None:
    for model in weights.MODELS:
        for lower, higher in zip(weights.EFFORTS, weights.EFFORTS[1:], strict=False):
            assert weights.to_spend(model, higher) > weights.to_spend(model, lower)
    for effort in weights.EFFORTS:
        for stronger, weaker in zip(weights.MODELS, weights.MODELS[1:], strict=False):
            assert weights.to_spend(stronger, effort) > weights.to_spend(weaker, effort)


def test_returned_table_is_a_defensive_copy() -> None:
    table = weights.load_cost_weights()
    table[weights.MODELS[0]][weights.EFFORTS[0]] = -1
    assert weights.to_spend(weights.MODELS[0], weights.EFFORTS[0]) != -1


def test_missing_non_monotonic_and_off_palette_cells_fail_loud() -> None:
    missing = weights.load_cost_weights()
    del missing[weights.MODELS[-1]][weights.EFFORTS[-1]]
    with pytest.raises(weights.CostWeightsError, match="missing cell"):
        weights._validate_table(missing)

    flat = weights.load_cost_weights()
    flat[weights.MODELS[0]][weights.EFFORTS[1]] = flat[weights.MODELS[0]][weights.EFFORTS[0]]
    with pytest.raises(weights.CostWeightsError, match="non-monotonic effort"):
        weights._validate_table(flat)

    extra = weights.load_cost_weights()
    extra["gpt-5.6-sol"] = dict(extra[weights.MODELS[0]])
    with pytest.raises(weights.CostWeightsError, match="off-palette model"):
        weights._validate_table(extra)

    nonpositive = weights.load_cost_weights()
    nonpositive[weights.MODELS[-1]][weights.EFFORTS[0]] = 0
    with pytest.raises(weights.CostWeightsError, match="positive integer"):
        weights._validate_table(nonpositive)


@pytest.mark.parametrize("cell", [True, 1.5, "3"])
def test_non_integer_weight_is_rejected(tmp_path: Path, cell: object) -> None:
    path = tmp_path / "weights.json"
    path.write_text(json.dumps({"weights": {"fable": {"low": cell}}}), encoding="utf-8")
    with pytest.raises(weights.CostWeightsError, match="must be an int"):
        weights._load_table(path)


@pytest.mark.parametrize("cell", [0, -1])
def test_nonpositive_weight_is_rejected_at_load(tmp_path: Path, cell: int) -> None:
    path = tmp_path / "weights.json"
    path.write_text(json.dumps({"weights": {"fable": {"low": cell}}}), encoding="utf-8")
    with pytest.raises(weights.CostWeightsError, match="must be positive"):
        weights._load_table(path)


def test_unknown_model_effort_and_ultra_are_rejected() -> None:
    with pytest.raises(weights.CostWeightsError):
        weights.to_spend("gpt-5.6-sol", "high")
    with pytest.raises(weights.CostWeightsError):
        weights.to_spend("fable", "ultra")
