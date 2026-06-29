#!/usr/bin/env python3
"""Infiquetra lifecycle destination and escalation helpers."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

ORCHESTRATION_TIERS = ("inline", "manual", "team-execution")
SOURCE_ONLY_ORCHESTRATION_TIERS = (
    "cc-workflows-ultracode",
    "workflow",
    "source-workflow-fanout",
    "fork",
    "goal",
    "hooks",
)

DESTINATION_ALIASES = {
    "plan": "plan-only",
    "plan only": "plan-only",
    "plan-only": "plan-only",
    "planning": "plan-only",
    "pr": "pr",
    "pull request": "pr",
    "pull-request": "pr",
    "merge": "merge",
    "merged": "merge",
    "nonprod": "nonprod-deploy",
    "nonprod deploy": "nonprod-deploy",
    "nonprod-deploy": "nonprod-deploy",
    "deploy": "nonprod-deploy",
}


def normalize_destination(value: str) -> str:
    """Normalize user-facing destination labels."""

    key = " ".join(value.strip().lower().replace("_", "-").split())
    key = key.replace("nonprod-deployment", "nonprod-deploy")
    if key in DESTINATION_ALIASES:
        return DESTINATION_ALIASES[key]
    raise ValueError("destination must be one of: plan-only, pr, merge, nonprod-deploy")


def destination_includes_deploy(destination: str) -> bool:
    """Return whether the selected destination needs deployment orchestration."""

    return normalize_destination(destination) == "nonprod-deploy"


def should_offer_team_execution(
    *,
    file_count: int,
    phase_count: int,
    has_security: bool,
    has_infra: bool,
    cross_repo: bool,
    deployment_sensitive: bool,
    has_code_surface: bool = True,
) -> bool:
    """Decide whether the loop should offer team-execution."""

    code_shaped = any(
        (
            file_count >= 8,
            phase_count >= 4,
            has_security,
            has_infra,
            deployment_sensitive,
        )
    )
    return (code_shaped and has_code_surface) or cross_repo


def should_prompt_for_issue(*, has_issue: bool, is_trivial: bool, user_declined: bool) -> bool:
    """Ask whether to file an SDLC issue for non-trivial ad-hoc work."""

    return not has_issue and not is_trivial and not user_declined


def requires_hard_test_gate(change_kinds: Sequence[str]) -> bool:
    """Return whether a change kind requires explicit tests before shipping."""

    risky = {"behavior", "security", "infra", "api", "deployment", "data"}
    return bool(risky.intersection(kind.lower() for kind in change_kinds))


def recommend_execution_backend(
    *,
    file_count: int = 0,
    phase_count: int = 0,
    has_security: bool = False,
    has_infra: bool = False,
    cross_repo: bool = False,
    deployment_sensitive: bool = False,
    needs_consensus: bool = False,
    broad_independent_fanout: bool = False,
    adversarial_confidence: bool = False,
    has_code_surface: bool = True,
    workflow_available: bool = True,
) -> dict[str, object]:
    """Recommend a Codex execution backend, mirroring operator-choice.md section 3.

    Codex exposes two Saga backends: ``inline`` and ``team-execution``. The
    source-only workflow backend is deliberately not reachable in this port.

    DELIBERATE DIVERGENCE from operator-choice section 3.1: that section frames
    the consensus signal as a **PLUS** on top of a size/risk trigger. Here a
    ``needs_consensus`` signal is **sufficient on its own** (``or
    needs_consensus``) — a small-but-contested job is a team-execution job even
    without a size/risk trigger, which is the more useful behavior for a real
    caller. This is intentional, not a transcription error.

    ``workflow_available`` is accepted for source compatibility but ignored:
    Codex never exposes the source-only workflow backend.
    """

    team = (
        should_offer_team_execution(
            file_count=file_count,
            phase_count=phase_count,
            has_security=has_security,
            has_infra=has_infra,
            cross_repo=cross_repo,
            deployment_sensitive=deployment_sensitive,
            has_code_surface=has_code_surface,
        )
        or needs_consensus
        or broad_independent_fanout
        or adversarial_confidence
    )

    if team:
        recommended = "team-execution"
        rationale = (
            "size, risk, consensus, fan-out, or adversarial-confidence signal -> "
            "team protocol fits"
        )
    else:
        recommended = "inline"
        rationale = "no escalation signal -> the agent does the work itself"

    reachable = ["inline", "team-execution"]
    alternatives = [backend for backend in reachable if backend != recommended]

    return {
        "recommended": recommended,
        "rationale": rationale,
        "alternatives": alternatives,
        "unsupported_source_backends": ["source-workflow-fanout"],
        "source_workflow_excluded": True,
    }


def _portable_fallback(fallback_mode: str) -> str:
    if fallback_mode in ORCHESTRATION_TIERS:
        return fallback_mode
    return "inline"


def recheck_orchestration_capability(
    *,
    orchestration_mode: str,
    workflow_available: bool = False,
    fallback_mode: str = "team-execution",
) -> dict[str, object]:
    """Recheck a stored orchestration tier against Codex capabilities."""

    resumed = orchestration_mode or "inline"
    if resumed in ORCHESTRATION_TIERS:
        return {
            "downgraded": False,
            "from": resumed,
            "to": resumed,
            "note": "",
            "workflow_available": workflow_available,
            "source_backend_excluded": False,
        }

    if resumed in SOURCE_ONLY_ORCHESTRATION_TIERS:
        target = _portable_fallback(fallback_mode)
        note = (
            f"{resumed} is a source-only backend in Codex; "
            f"degraded to {target}."
        )
        return {
            "downgraded": True,
            "from": resumed,
            "to": target,
            "note": note,
            "workflow_available": workflow_available,
            "source_backend_excluded": True,
        }

    return {
        "downgraded": True,
        "from": resumed,
        "to": "inline",
        "note": f"unknown orchestration mode {resumed!r}; using inline.",
        "workflow_available": workflow_available,
        "source_backend_excluded": False,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize = subparsers.add_parser("normalize", help="normalize a user-facing destination label")
    normalize.add_argument("destination")

    backend = subparsers.add_parser(
        "recommend-backend", help="recommend an execution backend as JSON"
    )
    backend.add_argument("--file-count", type=int, default=0)
    backend.add_argument("--phase-count", type=int, default=0)
    backend.add_argument("--has-security", action="store_true")
    backend.add_argument("--has-infra", action="store_true")
    backend.add_argument("--cross-repo", action="store_true")
    backend.add_argument("--deployment-sensitive", action="store_true")
    backend.add_argument("--needs-consensus", action="store_true")
    backend.add_argument("--broad-fanout", action="store_true")
    backend.add_argument("--adversarial-confidence", action="store_true")
    backend.add_argument("--no-code-surface", action="store_true")
    backend.add_argument("--no-workflow", action="store_true")

    recheck = subparsers.add_parser(
        "recheck-capability",
        help="recheck a stored orchestration mode against Codex capabilities",
    )
    recheck.add_argument("--orchestration-mode", default="inline")
    recheck.add_argument("--no-workflow", action="store_true")
    recheck.add_argument("--fallback-mode", default="team-execution")

    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "normalize":
        print(normalize_destination(args.destination))
        return 0
    if args.command == "recommend-backend":
        result = recommend_execution_backend(
            file_count=args.file_count,
            phase_count=args.phase_count,
            has_security=args.has_security,
            has_infra=args.has_infra,
            cross_repo=args.cross_repo,
            deployment_sensitive=args.deployment_sensitive,
            needs_consensus=args.needs_consensus,
            broad_independent_fanout=args.broad_fanout,
            adversarial_confidence=args.adversarial_confidence,
            has_code_surface=not args.no_code_surface,
            workflow_available=not args.no_workflow,
        )
        print(json.dumps(result))
        return 0
    if args.command == "recheck-capability":
        result = recheck_orchestration_capability(
            orchestration_mode=args.orchestration_mode,
            workflow_available=not args.no_workflow,
            fallback_mode=args.fallback_mode,
        )
        print(json.dumps(result))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
