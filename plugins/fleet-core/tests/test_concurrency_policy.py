"""Contract tests for the fleet-wide serialized admission limits value object (#356)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    ROOT / "plugins" / "fleet-core" / "scripts" / "fleet_commons" / "concurrency_policy.py"
)


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = _load(MODULE_PATH, "fleet_concurrency_policy_contract_under_test")


def test_defaults_are_the_fleet_serialized_limits() -> None:
    limits = P.AdmissionLimits()

    assert limits.to_dict() == {
        "max_concurrent": P.DEFAULT_MAX_CONCURRENT,
        "readonly_max_concurrent": P.DEFAULT_READONLY_MAX_CONCURRENT,
        "aggregate_max_concurrent": P.DEFAULT_AGGREGATE_MAX_CONCURRENT,
    }
    limits.validate()


def test_from_dict_round_trips_and_merges_partial_input_over_defaults() -> None:
    full = P.AdmissionLimits.from_dict(
        {"max_concurrent": 2, "readonly_max_concurrent": 3, "aggregate_max_concurrent": 5}
    )
    partial = P.AdmissionLimits.from_dict({"max_concurrent": 1})

    assert P.AdmissionLimits.from_dict(full.to_dict()) == full
    assert partial.readonly_max_concurrent == P.DEFAULT_READONLY_MAX_CONCURRENT
    assert partial.aggregate_max_concurrent == P.DEFAULT_AGGREGATE_MAX_CONCURRENT


def test_from_dict_rejects_unknown_fields() -> None:
    with pytest.raises(P.AdmissionPolicyError, match="unknown field"):
        P.AdmissionLimits.from_dict({"max_threads": 3})


@pytest.mark.parametrize("bad", [True, False, "3", 3.0, None])
def test_from_dict_rejects_non_integer_values(bad: object) -> None:
    with pytest.raises(P.AdmissionPolicyError, match="positive integer"):
        P.AdmissionLimits.from_dict({"max_concurrent": bad})


@pytest.mark.parametrize("value", [0, -1])
def test_validate_rejects_non_positive_limits(value: int) -> None:
    with pytest.raises(P.AdmissionPolicyError, match="positive integer"):
        P.AdmissionLimits(max_concurrent=value).validate()


def test_validate_rejects_inverted_orderings() -> None:
    with pytest.raises(P.AdmissionPolicyError, match="exceeds readonly_max_concurrent"):
        P.AdmissionLimits(max_concurrent=5, readonly_max_concurrent=4).validate()
    with pytest.raises(P.AdmissionPolicyError, match="exceeds aggregate_max_concurrent"):
        P.AdmissionLimits(readonly_max_concurrent=8, aggregate_max_concurrent=7).validate()


def test_policy_sha256_is_deterministic_and_value_sensitive() -> None:
    baseline = P.AdmissionLimits()
    changed = P.AdmissionLimits(max_concurrent=2)

    assert baseline.policy_sha256() == P.AdmissionLimits().policy_sha256()
    assert len(baseline.policy_sha256()) == 64
    assert baseline.policy_sha256() != changed.policy_sha256()
