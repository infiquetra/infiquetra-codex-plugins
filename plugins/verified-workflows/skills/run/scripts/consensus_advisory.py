#!/usr/bin/env python3
"""Consensus helper for non-scoring external advisory seats."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

GATED_SEAT = "gated"
ADVISORY_SEAT = "advisory"
SEATS = frozenset({GATED_SEAT, ADVISORY_SEAT})

PRESENT = "present"
ABSENT_STATUSES = frozenset({"absent", "halted", "failed", "unavailable"})
STATUSES = frozenset({PRESENT, *ABSENT_STATUSES})


@dataclass(frozen=True)
class Finding:
    """One normalized reviewer finding used by convergence reporting."""

    key: str
    summary: str
    severity: str = ""
    recommendation: str = ""

    def comparable(self) -> tuple[str, str, str]:
        """Return the fields whose mismatch means same-key divergence."""
        return (
            self.summary.strip(),
            self.severity.strip().lower(),
            self.recommendation.strip(),
        )


@dataclass(frozen=True)
class ReviewerResult:
    """One consensus-panel participant result."""

    name: str
    score: float | None
    seat: str = GATED_SEAT
    findings: tuple[Finding, ...] = ()
    dimension_scores: Mapping[str, float] = field(default_factory=dict)
    status: str = PRESENT


@dataclass(frozen=True)
class ConsensusResult:
    """Gate decision using only gated seats plus advisory reporting metadata."""

    accepted: bool
    gated_reviewers: tuple[str, ...]
    advisory_reviewers: tuple[str, ...]
    absent_advisory_reviewers: tuple[str, ...]
    blocking_reviewers: tuple[str, ...]
    rerun_reviewers: tuple[str, ...]


@dataclass(frozen=True)
class FindingConflict:
    """Same finding key, different Codex and external content."""

    key: str
    codex: Finding
    external: Finding


@dataclass(frozen=True)
class ConvergenceReport:
    """Codex-vs-external convergence buckets."""

    converged: tuple[str, ...]
    codex_only: tuple[Finding, ...]
    external_only: tuple[Finding, ...]
    conflicting: tuple[FindingConflict, ...]


def calculate_consensus(results: Iterable[ReviewerResult]) -> ConsensusResult:
    """Calculate Verified Workflows consensus while excluding advisory seats from gates."""
    gated_reviewers: list[str] = []
    advisory_reviewers: list[str] = []
    absent_advisory_reviewers: list[str] = []
    blocking_reviewers: list[str] = []
    rerun_reviewers: list[str] = []

    for result in results:
        _validate_result(result)
        if result.seat == ADVISORY_SEAT:
            if result.status in ABSENT_STATUSES:
                absent_advisory_reviewers.append(result.name)
            else:
                advisory_reviewers.append(result.name)
            continue

        if result.score is None:
            raise ValueError(f"gated reviewer {result.name!r} must provide a score")
        gated_reviewers.append(result.name)
        has_blocking_dimension = any(score < 7.0 for score in result.dimension_scores.values())
        if result.score < 7.0 or has_blocking_dimension:
            blocking_reviewers.append(result.name)
        if result.score < 9.0 or has_blocking_dimension:
            rerun_reviewers.append(result.name)

    if not gated_reviewers:
        raise ValueError("at least one gated reviewer result is required")

    accepted = not blocking_reviewers and not rerun_reviewers
    return ConsensusResult(
        accepted=accepted,
        gated_reviewers=tuple(gated_reviewers),
        advisory_reviewers=tuple(advisory_reviewers),
        absent_advisory_reviewers=tuple(absent_advisory_reviewers),
        blocking_reviewers=tuple(blocking_reviewers),
        rerun_reviewers=tuple(rerun_reviewers),
    )


def build_convergence_report(
    codex_findings: Iterable[Finding], external_findings: Iterable[Finding]
) -> ConvergenceReport:
    """Build a key-based convergence report between Codex and external findings."""
    codex_by_key = _unique_by_key(codex_findings, label="codex")
    external_by_key = _unique_by_key(external_findings, label="external")

    all_keys = sorted(set(codex_by_key) | set(external_by_key))
    converged: list[str] = []
    codex_only: list[Finding] = []
    external_only: list[Finding] = []
    conflicting: list[FindingConflict] = []

    for key in all_keys:
        codex = codex_by_key.get(key)
        external = external_by_key.get(key)
        if codex is None and external is not None:
            external_only.append(external)
        elif external is None and codex is not None:
            codex_only.append(codex)
        elif codex is not None and external is not None:
            if codex.comparable() == external.comparable():
                converged.append(key)
            else:
                conflicting.append(FindingConflict(key=key, codex=codex, external=external))

    return ConvergenceReport(
        converged=tuple(converged),
        codex_only=tuple(codex_only),
        external_only=tuple(external_only),
        conflicting=tuple(conflicting),
    )


def render_convergence_markdown(report: ConvergenceReport) -> str:
    """Render a compact operator-facing convergence report."""
    lines = [
        "## Codex vs External Convergence",
        "",
        "| Bucket | Count |",
        "| --- | ---: |",
        f"| Converged | {len(report.converged)} |",
        f"| Codex only | {len(report.codex_only)} |",
        f"| External only | {len(report.external_only)} |",
        f"| Conflicting | {len(report.conflicting)} |",
        "",
    ]
    lines.extend(_render_key_list("### Converged", report.converged))
    lines.extend(_render_finding_list("### Codex Only", report.codex_only))
    lines.extend(_render_finding_list("### External Only", report.external_only))
    lines.extend(_render_conflict_list(report.conflicting))
    return "\n".join(lines).rstrip() + "\n"


def _validate_result(result: ReviewerResult) -> None:
    if result.seat not in SEATS:
        raise ValueError(f"unknown reviewer seat {result.seat!r}; expected one of {sorted(SEATS)}")
    if result.status not in STATUSES:
        raise ValueError(
            f"unknown reviewer status {result.status!r}; expected one of {sorted(STATUSES)}"
        )
    if result.seat == GATED_SEAT and result.status != PRESENT:
        raise ValueError(f"gated reviewer {result.name!r} cannot be {result.status!r}")
    if (
        result.seat == ADVISORY_SEAT
        and result.score is not None
        and not 0.0 <= result.score <= 10.0
    ):
        raise ValueError(f"advisory reviewer {result.name!r} score must be 0..10 when present")
    if result.score is not None and not 0.0 <= result.score <= 10.0:
        raise ValueError(f"reviewer {result.name!r} score must be 0..10")
    for dimension, score in result.dimension_scores.items():
        if not 0.0 <= score <= 10.0:
            raise ValueError(
                f"reviewer {result.name!r} dimension {dimension!r} score must be 0..10"
            )


def _unique_by_key(findings: Iterable[Finding], *, label: str) -> dict[str, Finding]:
    by_key: dict[str, Finding] = {}
    for finding in findings:
        if not finding.key:
            raise ValueError(f"{label} finding key must be non-empty")
        if finding.key in by_key:
            raise ValueError(f"duplicate {label} finding key {finding.key!r}")
        by_key[finding.key] = finding
    return by_key


def _render_key_list(title: str, keys: tuple[str, ...]) -> list[str]:
    lines = [title, ""]
    lines.extend(f"- `{key}`" for key in keys)
    if not keys:
        lines.append("- none")
    lines.append("")
    return lines


def _render_finding_list(title: str, findings: tuple[Finding, ...]) -> list[str]:
    lines = [title, ""]
    lines.extend(f"- `{finding.key}`: {finding.summary}" for finding in findings)
    if not findings:
        lines.append("- none")
    lines.append("")
    return lines


def _render_conflict_list(conflicts: tuple[FindingConflict, ...]) -> list[str]:
    lines = ["### Conflicting", ""]
    for conflict in conflicts:
        lines.append(
            f"- `{conflict.key}`: Codex={conflict.codex.summary}; "
            f"external={conflict.external.summary}"
        )
    if not conflicts:
        lines.append("- none")
    lines.append("")
    return lines
