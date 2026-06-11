#!/usr/bin/env python3
"""Discover and audit Infiquetra context-library implementation spec profiles."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CONTEXT_LIBRARY_SUFFIX = "-context-library"

PROFILE_STANDARDS = {
    "service-implementations": Path("platform-specs/06-service-implementations/README.md"),
    "feature-modules": Path("platform-specs/06-feature-modules/README.md"),
}

READY_MARKERS = {
    "service-implementations": (
        "Folder Contract",
        "Completeness Checklist",
        "Definition of Done",
        "Probe inputs",
    ),
    "feature-modules": (
        "Folder Contract",
        "Completeness Checklist",
        "Definition of Done",
    ),
}

SERVICE_REQUIRED_FILES = {
    "architecture": (
        "service-architecture.md",
        "multi-region.md",
        "security-architecture.md",
    ),
    "api": ("openapi.yaml", "endpoint-specifications.md", "authorization-table.md"),
    "models": ("domain-model.md", "dynamodb-schema.md"),
    "specifications": ("implementation-spec.md",),
    "operations": (
        "deployment-guide.md",
        "monitoring-guide.md",
        "failover-runbook.md",
        "troubleshooting-runbook.md",
    ),
}

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((?P<target>[^)]+)\)")


@dataclass(frozen=True)
class Profile:
    library: str
    profile: str
    standard_path: str
    target_root: str
    status: str
    reason: str


def is_context_library(path: Path) -> bool:
    return path.is_dir() and path.name.endswith(CONTEXT_LIBRARY_SUFFIX)


def context_library_candidates(start: Path, max_depth: int = 4) -> list[Path]:
    """Return nearby context-library repos, preferring the current repo when applicable."""
    start = start.resolve()
    candidates: dict[Path, None] = {}
    if is_context_library(start):
        candidates[start] = None

    for parent in [start, *start.parents[:max_depth]]:
        for child in parent.glob(f"*{CONTEXT_LIBRARY_SUFFIX}"):
            if is_context_library(child):
                candidates[child.resolve()] = None

    return sorted(candidates, key=lambda path: (path != start, path.name))


def profile_status(profile: str, standard: Path) -> tuple[str, str]:
    text = standard.read_text(encoding="utf-8")
    missing = [marker for marker in READY_MARKERS[profile] if marker not in text]
    if missing:
        return "profile-needed", f"standard exists but is missing markers: {', '.join(missing)}"
    return "ready", "standard contains required authoring markers"


def detect_profiles(library: Path) -> list[Profile]:
    profiles: list[Profile] = []
    for profile, rel_standard in PROFILE_STANDARDS.items():
        standard = library / rel_standard
        if not standard.is_file():
            continue
        status, reason = profile_status(profile, standard)
        profiles.append(
            Profile(
                library=library.name,
                profile=profile,
                standard_path=rel_standard.as_posix(),
                target_root=rel_standard.parent.as_posix(),
                status=status,
                reason=reason,
            )
        )
    return profiles


def discover(start: Path, explicit: Path | None = None) -> list[Profile]:
    libraries = [explicit.resolve()] if explicit else context_library_candidates(start)
    profiles: list[Profile] = []
    for library in libraries:
        if is_context_library(library):
            profiles.extend(detect_profiles(library))
    return profiles


def _markdown_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def context_boundary(root: Path) -> Path:
    """Return the containing context-library boundary for link checks."""
    for path in [root, *root.parents]:
        if (path / "platform-specs").is_dir():
            return path.resolve()
    return root.resolve()


def broken_relative_links(root: Path, boundary: Path | None = None) -> list[str]:
    broken: list[str] = []
    boundary = (boundary or context_boundary(root)).resolve()
    for path in _markdown_files(root):
        text = path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK_RE.finditer(text):
            raw_target = match.group("target").split("#", 1)[0].strip()
            if not raw_target or raw_target.startswith(("http://", "https://", "mailto:")):
                continue
            if raw_target.startswith("/"):
                broken.append(f"{path.relative_to(root)}: absolute link {raw_target}")
                continue
            target = (path.parent / raw_target).resolve()
            try:
                target.relative_to(boundary)
            except ValueError:
                broken.append(f"{path.relative_to(root)}: link escapes target {raw_target}")
                continue
            if not target.exists():
                broken.append(f"{path.relative_to(root)}: missing link target {raw_target}")
    return broken


def _openapi_version(openapi_path: Path) -> str | None:
    if not openapi_path.is_file():
        return None
    for line in openapi_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("openapi:"):
            return stripped.split(":", 1)[1].strip().strip("'\"")
    return None


def audit_service_implementation(target: Path) -> dict[str, Any]:
    target = target.resolve()
    boundary = context_boundary(target)
    missing_files: list[str] = []
    for folder, filenames in SERVICE_REQUIRED_FILES.items():
        for filename in filenames:
            rel = Path(folder) / filename
            if not (target / rel).is_file():
                missing_files.append(rel.as_posix())

    integrations = target / "integrations"
    if integrations.is_dir():
        has_integration_doc = any(path.is_file() for path in integrations.glob("*-integration-guide.md"))
        has_na_doc = (integrations / "README.md").is_file()
        if not has_integration_doc and not has_na_doc:
            missing_files.append("integrations/README.md or *-integration-guide.md")
    else:
        missing_files.append("integrations/")

    workflows = target / "workflows"
    if not workflows.is_dir() or not any(workflows.glob("*-workflow.md")):
        missing_files.append("workflows/*-workflow.md")

    scenarios = target / "scenarios"
    scenario_count = len(list(scenarios.glob("*-scenario.md"))) if scenarios.is_dir() else 0
    if scenario_count < 3:
        missing_files.append("scenarios/<at least 3>-scenario.md")

    diagrams_src = target / "architecture" / "diagrams" / "src"
    diagrams_generated = target / "architecture" / "diagrams" / "generated"
    if not diagrams_src.is_dir() or len(list(diagrams_src.glob("*.py"))) < 2:
        missing_files.append("architecture/diagrams/src/<at least 2>.py")
    if not diagrams_generated.is_dir() or len(list(diagrams_generated.glob("*.png"))) < 2:
        missing_files.append("architecture/diagrams/generated/<at least 2>.png")

    openapi_version = _openapi_version(target / "api" / "openapi.yaml")
    warnings: list[str] = []
    if openapi_version and not openapi_version.startswith("3.1"):
        warnings.append(f"api/openapi.yaml declares OpenAPI {openapi_version}, expected 3.1")

    broken_links = broken_relative_links(target, boundary) if target.is_dir() else [f"{target}: missing target"]

    return {
        "target": str(target),
        "profile": "service-implementations",
        "passed": not missing_files and not warnings and not broken_links,
        "missing": missing_files,
        "warnings": warnings,
        "broken_links": broken_links,
        "openapi_version": openapi_version,
        "mermaid_blocks": sum(
            path.read_text(encoding="utf-8").count("```mermaid") for path in _markdown_files(target)
        )
        if target.is_dir()
        else 0,
    }


def _profiles_payload(profiles: list[Profile]) -> list[dict[str, str]]:
    return [asdict(profile) for profile in profiles]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="discover context-library profiles")
    discover_parser.add_argument("--start", type=Path, default=Path.cwd())
    discover_parser.add_argument("--library", type=Path)

    audit_parser = subparsers.add_parser("audit", help="audit a service implementation target")
    audit_parser.add_argument("--target", type=Path, required=True)
    audit_parser.add_argument("--profile", choices=("service-implementations",), default="service-implementations")

    args = parser.parse_args()
    if args.command == "discover":
        print(json.dumps(_profiles_payload(discover(args.start, args.library)), indent=2, sort_keys=True))
        return 0
    if args.command == "audit":
        print(json.dumps(audit_service_implementation(args.target), indent=2, sort_keys=True))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
