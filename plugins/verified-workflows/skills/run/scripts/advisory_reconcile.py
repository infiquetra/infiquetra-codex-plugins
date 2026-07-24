#!/usr/bin/env python3
"""Build a bounded, non-authoritative external-advisory convergence record."""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import consensus_advisory as consensus

MAX_FINDINGS_PER_SIDE = 256
MAX_TEXT_BYTES = 4096
SCHEMA_VERSION = "verified-workflows.advisory.v1"


class AdvisoryReconcileError(ValueError):
    """Advisory input is malformed, oversized, or attempts to claim authority."""


def _bounded_findings(
    findings: Iterable[consensus.Finding], *, side: str
) -> tuple[consensus.Finding, ...]:
    values = tuple(findings)
    if len(values) > MAX_FINDINGS_PER_SIDE:
        raise AdvisoryReconcileError(f"{side} findings exceed {MAX_FINDINGS_PER_SIDE}")
    for finding in values:
        if not finding.key or any(part in {"", ".", ".."} for part in finding.key.split("/")):
            raise AdvisoryReconcileError(f"{side} finding key is invalid")
        for field in (finding.summary, finding.severity, finding.recommendation):
            if len(field.encode("utf-8")) > MAX_TEXT_BYTES:
                raise AdvisoryReconcileError(f"{side} finding text exceeds {MAX_TEXT_BYTES} bytes")
    return values


def build_advisory_record(
    codex_findings: Iterable[consensus.Finding],
    external_findings: Iterable[consensus.Finding],
    *,
    source_evidence_ref: str | None,
) -> dict[str, Any]:
    """Return structural convergence only; raw finding text never enters gate arithmetic."""

    codex = _bounded_findings(codex_findings, side="codex")
    external = _bounded_findings(external_findings, side="external")
    report = consensus.build_convergence_report(codex, external)
    rendered = consensus.render_convergence_markdown(report)
    projection = {
        "converged": list(report.converged),
        "codex_only": [finding.key for finding in report.codex_only],
        "external_only": [finding.key for finding in report.external_only],
        "conflicting": [conflict.key for conflict in report.conflicting],
    }
    return {
        "schema_version": 1,
        "record_type": "advisory",
        "advisory_schema": SCHEMA_VERSION,
        "seat_type": "external-second-opinion",
        "gate_authority": "none",
        "source_evidence_ref": source_evidence_ref,
        "projection": projection,
        "rendered_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
    }


def canonical_bytes(record: dict[str, Any]) -> bytes:
    """Canonical bytes suitable for the root-owned concise run record."""

    return (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
