#!/usr/bin/env python3
"""Routing and revival helpers for saga:product-review."""

from __future__ import annotations

import argparse
import json
from typing import Any

DEFAULT_REVIVAL_MARGIN = 15

PROTOTYPE = "prototype"
FULL_BUILD = "full-build"

ROUTES = {
    PROTOTYPE: {"command": "saga:plan", "maturity": "experiment-ready"},
    FULL_BUILD: {"command": "saga:brainstorm", "maturity": "requirements-ready"},
}


def _confidence(idea: dict[str, Any]) -> int | None:
    raw = idea.get("confidence")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def revival_candidates(
    survivors: list[dict[str, Any]],
    cut: list[dict[str, Any]],
    margin: int = DEFAULT_REVIVAL_MARGIN,
) -> list[dict[str, Any]]:
    """Return close non-survivors worth offering for product review."""
    survivor_confidences = [
        confidence for confidence in (_confidence(idea) for idea in survivors) if confidence is not None
    ]
    floor = min(survivor_confidences) if survivor_confidences else None

    candidates: list[dict[str, Any]] = []
    for idea in cut:
        status = str(idea.get("status") or "rejected").lower()
        if status == "revived":
            continue

        confidence = _confidence(idea)
        if floor is not None and confidence is not None:
            close = confidence >= floor - margin
        else:
            close = status == "rejected"

        if close:
            candidates.append(
                {
                    "id": idea.get("id"),
                    "title": idea.get("title"),
                    "confidence": confidence,
                    "status": status,
                    "reason": idea.get("reason"),
                }
            )

    candidates.sort(key=lambda item: (item["confidence"] is not None, item["confidence"] or 0), reverse=True)
    return candidates


def metric_has_threshold(metric: str | None, threshold: str | None) -> bool:
    """A metric is actionable only when it has a concrete pass/fail threshold."""
    return bool((metric or "").strip()) and bool((threshold or "").strip())


def route_idea(idea: dict[str, Any]) -> dict[str, Any]:
    """Classify one reviewed idea's next Saga move."""
    title = idea.get("title")

    if idea.get("premise_holds") is False:
        return {
            "title": title,
            "kind": None,
            "move": "park",
            "command": None,
            "maturity": "deferred-context",
            "metric_actionable": False,
            "issues": ["premise check failed; park as deferred context"],
        }

    kind = str(idea.get("kind") or "").strip().lower()
    if kind not in (PROTOTYPE, FULL_BUILD):
        kind = PROTOTYPE if idea.get("cheap_to_test") else FULL_BUILD

    issues: list[str] = []
    metric_actionable = metric_has_threshold(idea.get("metric"), idea.get("threshold"))
    if not metric_actionable:
        issues.append("success metric is missing a concrete threshold")

    route = ROUTES[kind]
    return {
        "title": title,
        "kind": kind,
        "move": "route",
        "command": route["command"],
        "maturity": route["maturity"],
        "metric_actionable": metric_actionable,
        "issues": issues,
    }


def route_all(ideas: list[dict[str, Any]]) -> dict[str, Any]:
    """Route every reviewed idea and summarize the split."""
    routed = [route_idea(idea) for idea in ideas]
    return {
        "routed": routed,
        "summary": {
            "prototypes": [
                item["title"] for item in routed if item["move"] == "route" and item["kind"] == PROTOTYPE
            ],
            "full_builds": [
                item["title"] for item in routed if item["move"] == "route" and item["kind"] == FULL_BUILD
            ],
            "parked": [item["title"] for item in routed if item["move"] == "park"],
            "needs_threshold": [
                item["title"] for item in routed if item["move"] == "route" and not item["metric_actionable"]
            ],
        },
    }


def _load_json_list(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [item for item in loaded if isinstance(item, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    revival = subparsers.add_parser("revival", help="surface close non-survivors worth offering")
    revival.add_argument("--survivors", required=True, help="JSON array of survivor dictionaries")
    revival.add_argument("--cut", required=True, help="JSON array of non-survivor dictionaries")
    revival.add_argument("--margin", type=int, default=DEFAULT_REVIVAL_MARGIN)

    route = subparsers.add_parser("route", help="route reviewed ideas")
    route.add_argument("--ideas", required=True, help="JSON array of reviewed idea dictionaries")

    args = parser.parse_args()
    if args.command == "revival":
        output = revival_candidates(
            _load_json_list(args.survivors),
            _load_json_list(args.cut),
            margin=args.margin,
        )
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    if args.command == "route":
        print(json.dumps(route_all(_load_json_list(args.ideas)), indent=2, sort_keys=True))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
