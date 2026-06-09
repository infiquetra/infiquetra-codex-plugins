#!/usr/bin/env python3
"""Render visual assets for the Saga family documentation package."""

from __future__ import annotations

import argparse
import html
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import wrap

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import build_saga_docs_facts

ASSET_ROOT = Path("docs/saga/visual-assets")
ATLAS_SVG = "saga-lifecycle-atlas.svg"
ATLAS_PNG = "saga-lifecycle-atlas.png"
ATLAS_PDF = "saga-lifecycle-atlas.pdf"
READINESS_SVG = "readiness-ladder.svg"
OWNERSHIP_SVG = "ownership-boundaries.svg"

INK = "#172033"
MUTED = "#5b6472"
LINE = "#cbd5e1"
PANEL = "#ffffff"
SOFT = "#f8fafc"
BLUE = "#2563eb"
TEAL = "#0f766e"
GREEN = "#16a34a"
AMBER = "#d97706"
RED = "#dc2626"
VIOLET = "#7c3aed"
SLATE = "#475569"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def text(x: int, y: int, value: str, size: int = 22, weight: int = 400, fill: str = INK) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Inter, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{esc(value)}</text>'
    )


def wrapped_text(
    x: int,
    y: int,
    value: str,
    *,
    width: int,
    line_height: int = 22,
    size: int = 18,
    weight: int = 400,
    fill: str = INK,
) -> str:
    lines: list[str] = []
    for part in value.split("\n"):
        lines.extend(wrap(part, width=width) or [""])

    tspans = []
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else line_height
        tspans.append(f'<tspan x="{x}" dy="{dy}">{esc(line)}</tspan>')
    return (
        f'<text x="{x}" y="{y}" font-family="Inter, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{"".join(tspans)}</text>'
    )


def rect(
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    fill: str = PANEL,
    stroke: str = LINE,
    radius: int = 8,
    stroke_width: int = 1,
) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )


def arrow(x1: int, y1: int, x2: int, y2: int, color: str = SLATE) -> str:
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{color}" stroke-width="3" marker-end="url(#arrowhead)"/>'
    )


def svg_shell(width: int, height: int, body: list[str]) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
            "<defs>",
            '<marker id="arrowhead" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">',
            f'<path d="M0,0 L0,6 L9,3 z" fill="{SLATE}"/>',
            "</marker>",
            '<filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">',
            '<feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#0f172a" flood-opacity="0.12"/>',
            "</filter>",
            "</defs>",
            f'<rect width="{width}" height="{height}" fill="{SOFT}"/>',
            *body,
            "</svg>",
            "",
        ]
    )


def atlas_card(
    x: int,
    y: int,
    *,
    title: str,
    color: str,
    intent: str,
    command: str,
    artifact: str,
    maturity: str,
    gate: str,
    owner: str,
) -> str:
    row_y = y + 154
    parts = [
        f'<g filter="url(#softShadow)">',
        rect(x, y, 176, 560, fill=PANEL, stroke="#dbe3ef", radius=10),
        f'<rect x="{x}" y="{y}" width="176" height="66" rx="10" fill="{color}"/>',
        f'<rect x="{x}" y="{y + 48}" width="176" height="18" fill="{color}"/>',
        text(x + 16, y + 42, title, size=21, weight=800, fill="#ffffff"),
        "</g>",
        wrapped_text(x + 16, y + 92, intent, width=17, size=15, line_height=18, fill=MUTED),
    ]
    rows = [
        ("Command", command),
        ("Artifact", artifact),
        ("Maturity", maturity),
        ("Gate", gate),
        ("Owner", owner),
    ]
    for label, value in rows:
        parts.extend(
            [
                text(x + 16, row_y, label.upper(), size=12, weight=800, fill=MUTED),
                wrapped_text(x + 16, row_y + 26, value, width=18, size=16, line_height=19, fill=INK),
                f'<line x1="{x + 16}" y1="{row_y + 66}" x2="{x + 160}" y2="{row_y + 66}" stroke="#e2e8f0"/>',
            ]
        )
        row_y += 76
    return "\n".join(parts)


def render_atlas(facts: dict) -> str:
    steps = [
        {
            "title": "Frame",
            "color": BLUE,
            "intent": "A rough ask or fuzzy goal enters Saga.",
            "command": "saga:office-hours\nsaga:ideate",
            "artifact": "docs/ideation/",
            "maturity": "idea-ready",
            "gate": "advisory",
            "owner": "saga",
        },
        {
            "title": "Shape",
            "color": TEAL,
            "intent": "One promising direction becomes requirements.",
            "command": "saga:brainstorm\nsaga:spec",
            "artifact": "docs/brainstorms/\ndocs/specs/",
            "maturity": "requirements-ready",
            "gate": "advisory",
            "owner": "saga",
        },
        {
            "title": "Plan",
            "color": GREEN,
            "intent": "A buildable implementation path is chosen.",
            "command": "saga:plan",
            "artifact": "docs/plans/\n.codex/saga/",
            "maturity": "plan-ready",
            "gate": "review required",
            "owner": "saga",
        },
        {
            "title": "Review",
            "color": AMBER,
            "intent": "The plan is checked before execution.",
            "command": "saga:doc-review",
            "artifact": "docs/reviews/",
            "maturity": "plan-ready",
            "gate": "hard gate: no P0/P1",
            "owner": "saga",
        },
        {
            "title": "Build",
            "color": VIOLET,
            "intent": "Reviewed work is implemented to PR-ready.",
            "command": "saga:work",
            "artifact": "code, docs, tests\ndocs/work-sessions/",
            "maturity": "resume-ready",
            "gate": "commit and PR with confirmation",
            "owner": "saga",
        },
        {
            "title": "Prove",
            "color": RED,
            "intent": "Implementation evidence is challenged.",
            "command": "saga:code-review\nsaga:qa",
            "artifact": "docs/reviews/\nQA evidence",
            "maturity": "resume-ready",
            "gate": "quality gate",
            "owner": "saga + team-execution",
        },
        {
            "title": "Handoff",
            "color": SLATE,
            "intent": "Context leaves Saga for a mutation owner.",
            "command": "saga:handoff\nmission-control:*",
            "artifact": "handoff envelope\nissue draft",
            "maturity": "deferred-context",
            "gate": "receiver re-verifies",
            "owner": "mission-control",
        },
        {
            "title": "Operate",
            "color": "#0891b2",
            "intent": "Deployment or lessons are handled.",
            "command": "deploy:deploy\nsaga:retro",
            "artifact": "tags, release notes\njournal entries",
            "maturity": "done or resume-ready",
            "gate": "confirm mutation",
            "owner": "deploy + saga",
        },
    ]

    body = [
        text(70, 72, "Saga Family Lifecycle Atlas", size=40, weight=850),
        text(
            72,
            112,
            "Operator journey, command routing, durable artifacts, state maturity, gates, and plugin ownership",
            size=20,
            fill=MUTED,
        ),
        text(70, 152, f"Generated from {facts['generated_by']} and active Codex plugin manifests", size=15, fill=MUTED),
    ]

    start_x = 50
    gap = 18
    top = 180
    for index, step in enumerate(steps):
        x = start_x + index * (176 + gap)
        body.append(atlas_card(x, top, **step))
        if index < len(steps) - 1:
            body.append(arrow(x + 180, top + 280, x + 194, top + 280))

    body.extend(
        [
            rect(70, 800, 580, 112, fill="#ffffff", stroke="#dbe3ef", radius=10),
            text(95, 837, "Main Chain", size=20, weight=800),
            wrapped_text(95, 871, " -> ".join(facts["saga_routing"]["main_chain"]), width=72, size=17, line_height=22),
            rect(690, 800, 840, 112, fill="#ffffff", stroke="#dbe3ef", radius=10),
            text(715, 837, "Mutation Boundary", size=20, weight=800),
            wrapped_text(
                715,
                871,
                "Saga routes and records context. Mission Control mutates SDLC state, Team Execution owns review evidence, and Deploy owns tags.",
                width=96,
                size=17,
                line_height=22,
            ),
            text(70, 970, "Read left to right. A hard gate blocks the next step; an advisory step improves context without owning mutation.", size=17, fill=MUTED),
        ]
    )
    return svg_shell(1600, 1040, body)


def render_readiness_ladder(facts: dict) -> str:
    maturities = facts["state"]["readiness_maturities"]
    colors = [BLUE, TEAL, GREEN, VIOLET, SLATE]
    notes = {
        "idea-ready": "A direction exists and can be evaluated.",
        "requirements-ready": "The chosen idea has durable requirements.",
        "plan-ready": "The plan has passed readiness review.",
        "resume-ready": "Execution state can be resumed from artifacts.",
        "deferred-context": "Saga has handed context to another owner.",
    }
    body = [
        text(70, 72, "Saga Readiness Ladder", size=38, weight=850),
        text(72, 112, "Maturity is derived from lifecycle phase and artifact evidence; it is not stored as an independent source.", size=19, fill=MUTED),
    ]
    for index, maturity in enumerate(maturities):
        y = 170 + index * 102
        body.extend(
            [
                f'<circle cx="102" cy="{y + 34}" r="25" fill="{colors[index]}"/>',
                text(92, y + 43, str(index + 1), size=24, weight=800, fill="#ffffff"),
                rect(150, y, 860, 70, fill="#ffffff", stroke="#dbe3ef", radius=10),
                text(178, y + 31, maturity, size=22, weight=800, fill=colors[index]),
                wrapped_text(178, y + 57, notes[maturity], width=84, size=16, fill=MUTED),
            ]
        )
        if index < len(maturities) - 1:
            body.append(arrow(102, y + 62, 102, y + 96, colors[index]))

    body.extend(
        [
            rect(150, 650, 860, 70, fill="#fefce8", stroke="#facc15", radius=10),
            text(178, 682, "Operational rule", size=20, weight=800, fill=AMBER),
            wrapped_text(
                348,
                682,
                "When evidence and lifecycle phase disagree, the operator re-reads the durable artifact and updates the route before mutation.",
                width=76,
                size=16,
            ),
        ]
    )
    return svg_shell(1100, 760, body)


def render_ownership_boundaries(facts: dict) -> str:
    owners = [
        ("saga", BLUE),
        ("mission-control", TEAL),
        ("team-execution", VIOLET),
        ("deploy", GREEN),
    ]
    body = [
        text(58, 72, "Saga Family Ownership Boundaries", size=36, weight=850),
        text(60, 112, "Each plugin owns one mutation or evidence domain. Handoffs transfer context, not authority.", size=19, fill=MUTED),
    ]
    for index, (plugin, color) in enumerate(owners):
        x = 50 + index * 290
        boundary = facts["owner_boundaries"][plugin]
        body.extend(
            [
                rect(x, 165, 250, 470, fill="#ffffff", stroke="#dbe3ef", radius=10),
                f'<rect x="{x}" y="165" width="250" height="64" rx="10" fill="{color}"/>',
                f'<rect x="{x}" y="211" width="250" height="18" fill="{color}"/>',
                text(x + 20, 206, plugin, size=22, weight=850, fill="#ffffff"),
                text(x + 20, 266, "OWNS", size=13, weight=850, fill=MUTED),
                wrapped_text(x + 20, 298, boundary["owns"], width=28, size=16, line_height=20),
                f'<line x1="{x + 20}" y1="432" x2="{x + 230}" y2="432" stroke="#e2e8f0"/>',
                text(x + 20, 470, "DOES NOT OWN", size=13, weight=850, fill=MUTED),
                wrapped_text(x + 20, 502, boundary["does_not_own"], width=28, size=16, line_height=20),
            ]
        )
    body.extend(
        [
            rect(205, 670, 790, 82, fill="#ffffff", stroke="#dbe3ef", radius=10),
            text(230, 705, "Handoff rule", size=20, weight=850),
            wrapped_text(
                365,
                705,
                "A receiver re-reads and re-verifies the handoff payload before mutating its own domain.",
                width=82,
                size=17,
            ),
        ]
    )
    return svg_shell(1200, 790, body)


def render_svg_assets(facts: dict) -> dict[str, str]:
    return {
        ATLAS_SVG: render_atlas(facts),
        READINESS_SVG: render_readiness_ladder(facts),
        OWNERSHIP_SVG: render_ownership_boundaries(facts),
    }


def export_atlas(repo_root: Path, atlas_svg: Path) -> None:
    converter = shutil.which("rsvg-convert")
    if converter is None:
        raise RuntimeError("rsvg-convert is required to export Saga atlas PNG/PDF")

    output_png = repo_root / ASSET_ROOT / ATLAS_PNG
    output_pdf = repo_root / ASSET_ROOT / ATLAS_PDF
    subprocess.run([converter, "-f", "png", "-o", str(output_png), str(atlas_svg)], check=True)
    subprocess.run([converter, "-f", "pdf", "-o", str(output_pdf), str(atlas_svg)], check=True)


def write_assets(repo_root: Path) -> int:
    facts = build_saga_docs_facts.build_facts(repo_root)
    output_dir = repo_root / ASSET_ROOT
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, content in render_svg_assets(facts).items():
        (output_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {(ASSET_ROOT / name).as_posix()}")

    export_atlas(repo_root, output_dir / ATLAS_SVG)
    print(f"wrote {(ASSET_ROOT / ATLAS_PNG).as_posix()}")
    print(f"wrote {(ASSET_ROOT / ATLAS_PDF).as_posix()}")
    return 0


def check_assets(repo_root: Path) -> int:
    facts = build_saga_docs_facts.build_facts(repo_root)
    output_dir = repo_root / ASSET_ROOT
    stale: list[str] = []

    for name, expected in render_svg_assets(facts).items():
        path = output_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            stale.append((ASSET_ROOT / name).as_posix())

    for name in (ATLAS_PNG, ATLAS_PDF):
        path = output_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            stale.append((ASSET_ROOT / name).as_posix())

    if stale:
        print("stale or missing Saga visual assets:", file=sys.stderr)
        for path in stale:
            print(f"  {path}", file=sys.stderr)
        print("run: python3 scripts/render_saga_docs_assets.py", file=sys.stderr)
        return 1

    converter = shutil.which("rsvg-convert")
    if converter is not None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_svg = Path(temp_dir) / ATLAS_SVG
            temp_svg.write_text((output_dir / ATLAS_SVG).read_text(encoding="utf-8"), encoding="utf-8")
            subprocess.run([converter, "-f", "png", "-o", str(Path(temp_dir) / ATLAS_PNG), str(temp_svg)], check=True)
            subprocess.run([converter, "-f", "pdf", "-o", str(Path(temp_dir) / ATLAS_PDF), str(temp_svg)], check=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if rendered assets are missing or stale")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    if args.check:
        return check_assets(repo_root)
    return write_assets(repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
