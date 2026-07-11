#!/usr/bin/env python3
"""Render Fleet Core's Codex execution classes from the canonical registry."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import fleet_commons_shim  # noqa: E402

_palette = fleet_commons_shim.load("tier_palette")
_resolver = fleet_commons_shim.load("tier_resolver")

TIER_TABLE_BEGIN = (
    "<!-- BEGIN GENERATED EXECUTION CLASS TABLE "
    "(rendered from models.json via render_tier_table.py; do not hand-edit) -->"
)
TIER_TABLE_END = "<!-- END GENERATED EXECUTION CLASS TABLE -->"


def _candidate(candidate: Any) -> str:
    effort = "strongest supported scalar" if candidate.effort == "strongest-supported" else candidate.effort
    return f"`{candidate.model}` / `{effort}`"


def render_rows(policies: tuple[Any, ...] | None = None) -> list[tuple[str, str, str, str, str]]:
    """Return class, purpose, boundary, preferred, and ordered-fallback cells."""
    selected = policies if policies is not None else _palette.execution_class_policies()
    rows: list[tuple[str, str, str, str, str]] = []
    for policy in selected:
        boundary = f"workspace={policy.workspace_boundary}; external={policy.external_boundary}"
        fallbacks = " -> ".join(_candidate(candidate) for candidate in policy.fallbacks)
        rows.append(
            (
                policy.name,
                policy.description,
                boundary,
                _candidate(policy.preferred),
                fallbacks,
            )
        )
    return rows


def render_table(policies: tuple[Any, ...] | None = None) -> str:
    lines = [
        "| Execution class | Purpose | Boundary | Preferred | Ordered fallback |",
        "|---|---|---|---|---|",
    ]
    for name, purpose, boundary, preferred, fallbacks in render_rows(policies):
        lines.append(f"| `{name}` | {purpose} | {boundary} | {preferred} | {fallbacks} |")
    return "\n".join(lines)


def render_block(policies: tuple[Any, ...] | None = None) -> str:
    return "\n".join((TIER_TABLE_BEGIN, render_table(policies), TIER_TABLE_END))


def render_resolved_table(snapshot: Any) -> str:
    """Render effective class selection while consuming exactly one supplied snapshot."""
    lines = [
        "| Execution class | Effective model | Requested effort | Effective effort | Catalog |",
        "|---|---|---|---|---|",
    ]
    for execution_class in _palette.EXECUTION_CLASSES:
        resolution = _resolver.resolve_execution_class(execution_class, snapshot)
        lines.append(
            f"| `{execution_class}` | `{resolution.effective_model}` | "
            f"`{resolution.requested_effort}` | `{resolution.effective_effort}` | "
            f"`{resolution.catalog_source}:{resolution.catalog_sha256[:12]}` |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    print(render_block())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
