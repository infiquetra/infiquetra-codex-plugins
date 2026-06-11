from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_product_review() -> ModuleType:
    script = Path(__file__).parents[1] / "scripts" / "product_review.py"
    spec = importlib.util.spec_from_file_location("saga_product_review", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


product_review = load_product_review()


def test_revival_candidates_offer_near_misses_only() -> None:
    survivors = [{"title": "winner", "confidence": 80}]
    cut = [
        {"id": "R1", "title": "near", "confidence": 70, "status": "rejected"},
        {"id": "R2", "title": "far", "confidence": 20, "status": "rejected"},
        {"id": "R3", "title": "already revived", "confidence": 79, "status": "revived"},
    ]

    assert product_review.revival_candidates(survivors, cut, margin=15) == [
        {
            "id": "R1",
            "title": "near",
            "confidence": 70,
            "status": "rejected",
            "reason": None,
        }
    ]


def test_route_prototype_to_plan_with_experiment_ready() -> None:
    routed = product_review.route_idea(
        {
            "title": "Wizard-of-oz registration",
            "kind": "prototype",
            "metric": "operator completes flow",
            "threshold": "3 successful trials",
            "premise_holds": True,
        }
    )

    assert routed["command"] == "saga:plan"
    assert routed["maturity"] == "experiment-ready"
    assert routed["metric_actionable"] is True
    assert routed["issues"] == []


def test_route_flags_missing_threshold_and_parks_failed_premise() -> None:
    routed = product_review.route_all(
        [
            {"title": "thin metric", "kind": "full-build", "metric": "adoption", "threshold": ""},
            {"title": "dead premise", "kind": "prototype", "premise_holds": False},
        ]
    )

    assert routed["summary"]["full_builds"] == ["thin metric"]
    assert routed["summary"]["needs_threshold"] == ["thin metric"]
    assert routed["summary"]["parked"] == ["dead premise"]
    assert routed["routed"][0]["command"] == "saga:brainstorm"
    assert routed["routed"][1]["maturity"] == "deferred-context"
