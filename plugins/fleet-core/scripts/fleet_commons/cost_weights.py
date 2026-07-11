#!/usr/bin/env python3
"""Validated ordinal cost weights for source-lineage economics.

Weights compare relative spend; they are never prices. The model axis remains the temporary
lineage vocabulary required by imported Saga economics, while the effort axis is Fleet Core's
authoritative scalar ``low..max`` ladder. Active Codex model choice comes from execution classes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import fleet_commons_shim  # noqa: E402

_tier_palette = fleet_commons_shim.load("tier_palette")
MODELS: tuple[str, ...] = _tier_palette.MODELS
EFFORTS: tuple[str, ...] = _tier_palette.SCALAR_EFFORTS

COST_WEIGHTS_PATH = Path(__file__).resolve().parent / "cost_weights.json"


class CostWeightsError(ValueError):
    """Raised when the ordinal table is malformed, incomplete, or non-monotonic."""


def _load_table(path: Path = COST_WEIGHTS_PATH) -> dict[str, dict[str, int]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CostWeightsError(f"could not load {path}: {exc}") from exc
    weights = raw.get("weights") if isinstance(raw, dict) else None
    if not isinstance(weights, dict):
        raise CostWeightsError(f"{path}: top-level 'weights' object is missing or not a map")
    table: dict[str, dict[str, int]] = {}
    for model, row in weights.items():
        if not isinstance(row, dict):
            raise CostWeightsError(f"cost weights for model {model!r} is not a map")
        cells: dict[str, int] = {}
        for effort, value in row.items():
            if not isinstance(value, int) or isinstance(value, bool):
                raise CostWeightsError(
                    f"cost weight for {model!r}/{effort!r} must be an int, got {value!r}"
                )
            if value <= 0:
                raise CostWeightsError(
                    f"cost weight for {model!r}/{effort!r} must be positive, got {value!r}"
                )
            cells[effort] = value
        table[model] = cells
    return table


def _validate_table(table: dict[str, dict[str, int]]) -> None:
    for model, row in table.items():
        if model not in MODELS:
            raise CostWeightsError(
                f"cost_weights.json has off-palette model {model!r}; expected one of {MODELS}"
            )
        for effort in row:
            if effort not in EFFORTS:
                raise CostWeightsError(
                    f"cost_weights.json has off-palette effort {effort!r} under model {model!r}; "
                    f"expected one of {EFFORTS}"
                )
            value = row[effort]
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise CostWeightsError(
                    f"cost weight for {model!r}/{effort!r} must be a positive integer"
                )
    for model in MODELS:
        if model not in table:
            raise CostWeightsError(f"cost_weights.json missing model {model!r}")
        for effort in EFFORTS:
            if effort not in table[model]:
                raise CostWeightsError(f"cost_weights.json missing cell {model!r}/{effort!r}")
    for model in MODELS:
        for weaker, stronger in zip(EFFORTS, EFFORTS[1:], strict=False):
            if table[model][stronger] <= table[model][weaker]:
                raise CostWeightsError(
                    f"cost_weights.json non-monotonic effort axis for {model!r}: "
                    f"{stronger!r} must exceed {weaker!r}"
                )
    for effort in EFFORTS:
        for stronger_model, weaker_model in zip(MODELS, MODELS[1:], strict=False):
            if table[weaker_model][effort] >= table[stronger_model][effort]:
                raise CostWeightsError(
                    f"cost_weights.json non-monotonic model axis at {effort!r}: "
                    f"{stronger_model!r} must exceed {weaker_model!r}"
                )


_WEIGHTS = _load_table()
_validate_table(_WEIGHTS)


def to_spend(model: str, effort: str) -> int:
    if model not in _WEIGHTS:
        raise CostWeightsError(f"unknown lineage model {model!r}; expected one of {MODELS}")
    if effort not in _WEIGHTS[model]:
        raise CostWeightsError(f"unknown scalar effort {effort!r}; expected one of {EFFORTS}")
    return _WEIGHTS[model][effort]


def load_cost_weights() -> dict[str, dict[str, int]]:
    return {model: dict(row) for model, row in _WEIGHTS.items()}
