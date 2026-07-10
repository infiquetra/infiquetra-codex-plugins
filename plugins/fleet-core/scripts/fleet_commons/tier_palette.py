#!/usr/bin/env python3
"""Canonical Fleet Core model, effort, and Codex execution-class policy.

``models.json`` contains two deliberately separate vocabularies:

* Claude-derived lineage tiers retained for existing Saga and Team Execution consumers; and
* Codex execution classes plus the scalar ``low..max`` effort ladder used by new profiles.

Ultra is catalog truth but is not a scalar effort and is never a leaf execution class. Logical
roles and allowed class transitions belong to Verified Workflows, not this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MODELS_REGISTRY_PATH = Path(__file__).resolve().parent / "models.json"
STRONGEST_SUPPORTED = "strongest-supported"


class TierPaletteError(ValueError):
    """Raised when the single policy registry is malformed."""


@dataclass(frozen=True)
class ModelCandidate:
    model: str
    effort: str


@dataclass(frozen=True)
class ExecutionClassPolicy:
    name: str
    description: str
    workspace_boundary: str
    external_boundary: str
    preferred: ModelCandidate
    fallbacks: tuple[ModelCandidate, ...]

    @property
    def candidates(self) -> tuple[ModelCandidate, ...]:
        return (self.preferred, *self.fallbacks)

    @property
    def requested_effort(self) -> str:
        return self.preferred.effort


@dataclass(frozen=True)
class RootOrchestrationPolicy:
    preferred_model: str
    fallback_models: tuple[str, ...]
    default_effort: str
    ultra_requires_explicit_selection: bool
    ultra_requires_independent_fanout: bool
    ultra_leaf_allowed: bool

    @property
    def models(self) -> tuple[str, ...]:
        return (self.preferred_model, *self.fallback_models)


def _load_registry(path: Path = MODELS_REGISTRY_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TierPaletteError(f"could not load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TierPaletteError(f"{path}: top level must be an object")
    if value.get("schema_version") != 2:
        raise TierPaletteError(f"{path}: schema_version must be 2")
    required = {
        "lineage_models",
        "lineage_efforts",
        "scalar_efforts",
        "execution_classes",
        "root_orchestration_profiles",
    }
    missing = required - set(value)
    if missing:
        raise TierPaletteError(f"{path}: missing registry sections {sorted(missing)}")
    allowed = {"schema_version", "_comment", *required}
    unexpected = set(value) - allowed
    if unexpected:
        raise TierPaletteError(f"{path}: unexpected registry sections {sorted(unexpected)}")
    return value


def _derive_ordered(rows: object, index_key: str, kind: str) -> tuple[str, ...]:
    if not isinstance(rows, dict) or not rows:
        raise TierPaletteError(f"{kind} registry must be a non-empty object")
    indexed: list[tuple[int, str]] = []
    seen: set[int] = set()
    for name, row in rows.items():
        if not isinstance(name, str) or not isinstance(row, dict):
            raise TierPaletteError(f"{kind} rows must map names to objects")
        index = row.get(index_key)
        if not isinstance(index, int) or isinstance(index, bool):
            raise TierPaletteError(f"{kind} {name!r} {index_key} must be an integer")
        if index in seen:
            raise TierPaletteError(f"{kind} {index_key} {index} is duplicated")
        seen.add(index)
        indexed.append((index, name))
    if seen != set(range(len(indexed))):
        raise TierPaletteError(
            f"{kind} {index_key} values {sorted(seen)} are not contiguous 0..{len(indexed) - 1}"
        )
    return tuple(name for _, name in sorted(indexed))


def _string(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TierPaletteError(f"{where} must be a non-empty string")
    return value


_REGISTRY = _load_registry()

# Compatibility vocabulary. These names are source-lineage identifiers, not active Codex model
# selection. U3/U6 migrate consumers onto EXECUTION_CLASSES/SCALAR_EFFORTS before cutover.
MODELS = _derive_ordered(_REGISTRY["lineage_models"], "rank", "lineage model")
EFFORTS = _derive_ordered(_REGISTRY["lineage_efforts"], "rung", "lineage effort")

# Authoritative Codex scalar ladder. Ultra is intentionally absent.
SCALAR_EFFORTS = _derive_ordered(_REGISTRY["scalar_efforts"], "rung", "scalar effort")
if SCALAR_EFFORTS != ("low", "medium", "high", "xhigh", "max"):
    raise TierPaletteError(
        "scalar_efforts must be exactly ('low', 'medium', 'high', 'xhigh', 'max')"
    )


def _derive_effort_ceilings() -> dict[str, str]:
    ceilings: dict[str, str] = {}
    for name, row in _REGISTRY["lineage_models"].items():
        ceiling = row.get("effort_ceiling")
        if ceiling not in EFFORTS:
            raise TierPaletteError(
                f"lineage model {name!r} effort_ceiling {ceiling!r} is not in {EFFORTS}"
            )
        ceilings[name] = ceiling
    return ceilings


def _derive_codex_mapping() -> dict[str, tuple[str, str]]:
    mapping: dict[str, tuple[str, str]] = {}
    for name, row in _REGISTRY["lineage_models"].items():
        model = _string(row.get("codex_model"), f"lineage model {name!r}.codex_model")
        effort = row.get("codex_effort")
        if effort not in EFFORTS:
            raise TierPaletteError(
                f"lineage model {name!r}.codex_effort {effort!r} is not in {EFFORTS}"
            )
        mapping[name] = (model, effort)
    return mapping


_EFFORT_CEILINGS = _derive_effort_ceilings()
_CODEX_MAPPING = _derive_codex_mapping()
CHEAP_MODELS = ("haiku",)
ENGINE_INTENTS = ("offload", "second-opinion")


def _candidate(value: object, where: str, requested_effort: str | None = None) -> ModelCandidate:
    if not isinstance(value, dict) or set(value) != {"model", "effort"}:
        raise TierPaletteError(f"{where} must contain exactly model and effort")
    model = _string(value.get("model"), f"{where}.model")
    effort = value.get("effort")
    if effort != STRONGEST_SUPPORTED and effort not in SCALAR_EFFORTS:
        raise TierPaletteError(
            f"{where}.effort {effort!r} must be scalar or {STRONGEST_SUPPORTED!r}"
        )
    if requested_effort is None and effort == STRONGEST_SUPPORTED:
        raise TierPaletteError(f"{where}: preferred effort cannot be {STRONGEST_SUPPORTED!r}")
    if requested_effort is not None and effort not in {requested_effort, STRONGEST_SUPPORTED}:
        raise TierPaletteError(
            f"{where}.effort must preserve class effort {requested_effort!r} or request strongest"
        )
    return ModelCandidate(model=model, effort=str(effort))


def _derive_execution_classes() -> tuple[ExecutionClassPolicy, ...]:
    rows = _REGISTRY["execution_classes"]
    ordered = _derive_ordered(rows, "order", "execution class")
    allowed_keys = {
        "order",
        "description",
        "workspace_boundary",
        "external_boundary",
        "preferred",
        "fallbacks",
    }
    policies: list[ExecutionClassPolicy] = []
    for name in ordered:
        row = rows[name]
        if set(row) != allowed_keys:
            raise TierPaletteError(
                f"execution class {name!r} keys must be exactly {sorted(allowed_keys)}"
            )
        preferred = _candidate(row["preferred"], f"execution class {name!r}.preferred")
        fallbacks_raw = row["fallbacks"]
        if not isinstance(fallbacks_raw, list) or not fallbacks_raw:
            raise TierPaletteError(f"execution class {name!r}.fallbacks must be non-empty")
        fallbacks = tuple(
            _candidate(
                value,
                f"execution class {name!r}.fallbacks[{index}]",
                preferred.effort,
            )
            for index, value in enumerate(fallbacks_raw)
        )
        candidates = (preferred, *fallbacks)
        if len({candidate.model for candidate in candidates}) != len(candidates):
            raise TierPaletteError(f"execution class {name!r} repeats a candidate model")
        policies.append(
            ExecutionClassPolicy(
                name=name,
                description=_string(row["description"], f"execution class {name!r}.description"),
                workspace_boundary=_string(
                    row["workspace_boundary"],
                    f"execution class {name!r}.workspace_boundary",
                ),
                external_boundary=_string(
                    row["external_boundary"],
                    f"execution class {name!r}.external_boundary",
                ),
                preferred=preferred,
                fallbacks=fallbacks,
            )
        )
    return tuple(policies)


_EXECUTION_CLASS_POLICIES = _derive_execution_classes()
EXECUTION_CLASSES = tuple(policy.name for policy in _EXECUTION_CLASS_POLICIES)
_EXECUTION_CLASS_BY_NAME = {policy.name: policy for policy in _EXECUTION_CLASS_POLICIES}


def _derive_root_policy() -> RootOrchestrationPolicy:
    profiles = _REGISTRY["root_orchestration_profiles"]
    if not isinstance(profiles, dict) or set(profiles) != {"root"}:
        raise TierPaletteError("root_orchestration_profiles must contain exactly 'root'")
    row = profiles["root"]
    allowed = {"preferred_model", "fallback_models", "default_effort", "ultra"}
    if not isinstance(row, dict) or set(row) != allowed:
        raise TierPaletteError(f"root orchestration keys must be exactly {sorted(allowed)}")
    fallback_models = row["fallback_models"]
    if not isinstance(fallback_models, list) or not fallback_models:
        raise TierPaletteError("root fallback_models must be a non-empty list")
    models = (
        _string(row["preferred_model"], "root.preferred_model"),
        *(_string(value, "root.fallback_models[]") for value in fallback_models),
    )
    if len(set(models)) != len(models):
        raise TierPaletteError("root orchestration repeats a model")
    default_effort = row["default_effort"]
    if default_effort not in SCALAR_EFFORTS:
        raise TierPaletteError("root.default_effort must be scalar")
    ultra = row["ultra"]
    ultra_keys = {
        "requires_explicit_selection",
        "requires_independent_fanout",
        "leaf_allowed",
    }
    if not isinstance(ultra, dict) or set(ultra) != ultra_keys:
        raise TierPaletteError(f"root.ultra keys must be exactly {sorted(ultra_keys)}")
    if not all(isinstance(ultra[key], bool) for key in ultra_keys):
        raise TierPaletteError("root.ultra flags must be booleans")
    if ultra["leaf_allowed"]:
        raise TierPaletteError("Ultra must never be allowed for leaf execution")
    return RootOrchestrationPolicy(
        preferred_model=models[0],
        fallback_models=tuple(models[1:]),
        default_effort=default_effort,
        ultra_requires_explicit_selection=ultra["requires_explicit_selection"],
        ultra_requires_independent_fanout=ultra["requires_independent_fanout"],
        ultra_leaf_allowed=ultra["leaf_allowed"],
    )


_ROOT_ORCHESTRATION_POLICY = _derive_root_policy()


def execution_class_policy(name: str) -> ExecutionClassPolicy:
    try:
        return _EXECUTION_CLASS_BY_NAME[name]
    except KeyError:
        raise ValueError(
            f"unknown execution class {name!r}; expected one of {EXECUTION_CLASSES}"
        ) from None


def execution_class_policies() -> tuple[ExecutionClassPolicy, ...]:
    return _EXECUTION_CLASS_POLICIES


def root_orchestration_policy() -> RootOrchestrationPolicy:
    return _ROOT_ORCHESTRATION_POLICY


def model_rank(model: str) -> int:
    try:
        return MODELS.index(model)
    except ValueError:
        raise ValueError(f"unknown lineage model {model!r}; expected one of {MODELS}") from None


def effort_rank(effort: str) -> int:
    try:
        return EFFORTS.index(effort)
    except ValueError:
        raise ValueError(f"unknown lineage effort {effort!r}; expected one of {EFFORTS}") from None


def scalar_effort_rank(effort: str) -> int:
    try:
        return SCALAR_EFFORTS.index(effort)
    except ValueError:
        raise ValueError(
            f"unknown scalar effort {effort!r}; expected one of {SCALAR_EFFORTS}"
        ) from None


def effort_ceiling(model: str) -> str:
    try:
        return _EFFORT_CEILINGS[model]
    except KeyError:
        raise ValueError(f"unknown lineage model {model!r}; expected one of {MODELS}") from None


def codex_model(model: str) -> str:
    try:
        return _CODEX_MAPPING[model][0]
    except KeyError:
        raise ValueError(f"unknown lineage model {model!r}; expected one of {MODELS}") from None


def codex_effort(model: str) -> str:
    try:
        return _CODEX_MAPPING[model][1]
    except KeyError:
        raise ValueError(f"unknown lineage model {model!r}; expected one of {MODELS}") from None


def codex_tier(model: str) -> tuple[str, str]:
    try:
        return _CODEX_MAPPING[model]
    except KeyError:
        raise ValueError(f"unknown lineage model {model!r}; expected one of {MODELS}") from None


_LADDERS: dict[str, tuple[str, ...]] = {"model": MODELS, "effort": EFFORTS}
_STRONGEST_FIRST: dict[str, bool] = {"model": True, "effort": False}


def _strength(kind: str, value: str) -> int:
    if kind not in _LADDERS:
        raise ValueError(f"unknown lineage ladder {kind!r}; expected 'model' or 'effort'")
    ladder = _LADDERS[kind]
    try:
        index = ladder.index(value)
    except ValueError:
        raise ValueError(f"unknown {kind} {value!r}; expected one of {ladder}") from None
    return len(ladder) - 1 - index if _STRONGEST_FIRST[kind] else index


def _from_strength(kind: str, strength: int) -> str:
    ladder = _LADDERS[kind]
    bounded = max(0, min(strength, len(ladder) - 1))
    index = len(ladder) - 1 - bounded if _STRONGEST_FIRST[kind] else bounded
    return ladder[index]


def escalate(kind: str, value: str, steps: int = 1, *, ceiling: str | None = None) -> str:
    strength = _strength(kind, value)
    top = len(_LADDERS[kind]) - 1
    if ceiling is not None:
        top = min(top, _strength(kind, ceiling))
    return _from_strength(kind, max(strength, min(strength + steps, top)))


def downgrade(kind: str, value: str, steps: int = 1, *, floor: str | None = None) -> str:
    strength = _strength(kind, value)
    bottom = max(0, _strength(kind, floor)) if floor is not None else 0
    return _from_strength(kind, min(strength, max(strength - steps, bottom)))


def clamp(
    kind: str,
    value: str,
    *,
    floor: str | None = None,
    ceiling: str | None = None,
) -> str:
    strength = _strength(kind, value)
    if floor is not None:
        strength = max(strength, _strength(kind, floor))
    if ceiling is not None:
        strength = min(strength, _strength(kind, ceiling))
    return _from_strength(kind, strength)


def stronger(kind: str, a: str, b: str) -> str:
    return a if _strength(kind, a) >= _strength(kind, b) else b


def strongest(kind: str, values: object) -> str:
    items = list(values)  # type: ignore[call-overload]
    if not items:
        raise ValueError("strongest() requires at least one value")
    best = items[0]
    for value in items[1:]:
        best = stronger(kind, best, value)
    return best


def supports_effort(model: str, effort: str) -> bool:
    return effort_rank(effort) <= effort_rank(effort_ceiling(model))


def clamp_effort_to_model(model: str, effort: str) -> tuple[str, str | None]:
    ceiling = effort_ceiling(model)
    if effort_rank(effort) > effort_rank(ceiling):
        return ceiling, f"effort {effort!r} exceeds {model!r} ceiling; clamped to {ceiling!r}"
    return effort, None
