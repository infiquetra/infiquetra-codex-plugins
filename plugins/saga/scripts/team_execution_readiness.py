#!/usr/bin/env python3
"""Validate whether Saga Team Execution state is executable."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


ReadinessStatus = Literal["not-team-execution", "draft", "ready", "blocked"]

EXECUTABLE_CONTEXTS = {"plan-ready", "work", "resume", "outcome-dispatch", "qa-closeout"}
VALID_CONTEXTS = EXECUTABLE_CONTEXTS | {"draft-plan"}


@dataclass(frozen=True)
class ReadinessResult:
    status: ReadinessStatus
    reason: str
    repair_hint: str
    resolved_ref: str = ""

    @property
    def ready(self) -> bool:
        return self.status in {"not-team-execution", "draft", "ready"}

    def to_dict(self) -> dict[str, str | bool]:
        payload = asdict(self)
        payload["ready"] = self.ready
        return payload


def validate_team_execution_ready(
    repo_root: Path,
    *,
    orchestration_mode: str,
    orchestration_ref: str,
    context: str,
    plan_path: str = "",
) -> ReadinessResult:
    """Return whether ``team-execution`` state has a runnable receipt.

    Draft planning may carry Team Execution intent without a receipt. Any executable boundary must
    resolve the ref to a Team Structure section or protected Team Execution state root.
    """
    if context not in VALID_CONTEXTS:
        raise ValueError(f"unknown Team Execution readiness context {context!r}")
    if orchestration_mode != "team-execution":
        return ReadinessResult(
            "not-team-execution",
            "orchestration mode is not team-execution",
            "no Team Execution receipt is required",
        )

    ref = orchestration_ref.strip()
    if not ref:
        if context == "draft-plan":
            return ReadinessResult(
                "draft",
                "Team Execution receipt has not been materialized yet",
                "materialize Phase A before marking the plan ready or entering execution",
            )
        if context in EXECUTABLE_CONTEXTS:
            return ReadinessResult(
                "blocked",
                "missing orchestration_ref for executable Team Execution",
                _default_repair_hint(plan_path),
            )

    return _resolve_ref(Path(repo_root), ref, plan_path=plan_path)


def _default_repair_hint(plan_path: str) -> str:
    if plan_path:
        return f"add or link a ## Team Structure receipt and save --orchestration-ref {plan_path}#team-structure"
    return "add or link a ## Team Structure receipt before executable Team Execution"


def _resolve_ref(repo_root: Path, ref: str, *, plan_path: str = "") -> ReadinessResult:
    if ref.startswith("~/"):
        return _resolve_user_local_ref(repo_root, ref)
    if Path(ref).is_absolute():
        return ReadinessResult(
            "blocked",
            "absolute orchestration_ref is not portable",
            "use a repo-relative plan artifact or the explicit ~/.codex/team-execution fallback",
        )

    path_part, anchor = _split_ref(ref)
    path = repo_root / path_part
    if path.is_dir():
        return _resolve_repo_state_root(repo_root, path, path_part)
    if path.is_file():
        containment_error = _repo_relative_path_error(repo_root, path)
        if containment_error is not None:
            return containment_error
        return _resolve_markdown_ref(path, path_part, anchor)

    return ReadinessResult(
        "blocked",
        "orchestration_ref target does not exist",
        _default_repair_hint(plan_path),
    )


def _repo_relative_path_error(repo_root: Path, path: Path) -> ReadinessResult | None:
    try:
        path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return ReadinessResult(
            "blocked",
            "orchestration_ref escapes the repository",
            "use a repo-relative plan artifact or protected Team Execution evidence root",
        )
    return None


def _split_ref(ref: str) -> tuple[str, str]:
    path_part, sep, anchor = ref.partition("#")
    return path_part.strip(), anchor.strip() if sep else ""


def _resolve_markdown_ref(path: Path, rel_path: str, anchor: str) -> ReadinessResult:
    if path.suffix.lower() not in {".md", ".markdown"}:
        return ReadinessResult(
            "blocked",
            "file orchestration_ref is not a markdown Team Structure receipt",
            "point to a markdown plan/artifact with ## Team Structure or a protected evidence root",
        )
    headings = _markdown_heading_anchors(path.read_text(encoding="utf-8"))
    if anchor:
        normalized = _normalize_anchor(anchor)
        if normalized != "team-structure":
            return ReadinessResult(
                "blocked",
                "orchestration_ref anchor is not #team-structure",
                f"use {rel_path}#team-structure",
            )
        if "team-structure" not in headings:
            return ReadinessResult(
                "blocked",
                "orchestration_ref anchor does not resolve to ## Team Structure",
                "materialize Team Execution Phase A in the referenced markdown file",
            )
        return ReadinessResult(
            "ready",
            "Team Structure receipt resolved",
            "Team Execution may enter Phase B",
            f"{rel_path}#team-structure",
        )
    if "team-structure" in headings:
        return ReadinessResult(
            "ready",
            "Team Structure receipt resolved",
            "Team Execution may enter Phase B",
            f"{rel_path}#team-structure",
        )
    return ReadinessResult(
        "blocked",
        "markdown orchestration_ref lacks ## Team Structure",
        "materialize Team Execution Phase A in the referenced markdown file",
    )


def _markdown_heading_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            anchors.add(_normalize_anchor(match.group(1)))
    return anchors


def _normalize_anchor(value: str) -> str:
    text = value.strip().lower().replace("%20", " ")
    return "-".join(re.findall(r"[a-z0-9]+", text))


def _resolve_repo_state_root(repo_root: Path, path: Path, rel_path: str) -> ReadinessResult:
    try:
        relative = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return ReadinessResult(
            "blocked",
            "state root is outside the repository",
            "use a protected repo-local .codex/team-execution root or the user-local fallback",
        )
    normalized = relative.as_posix().rstrip("/") + "/"
    if not normalized.startswith(".codex/team-execution/"):
        return ReadinessResult(
            "blocked",
            "state root is not under .codex/team-execution",
            "use a protected Team Execution evidence root",
        )
    if not _is_ignored(repo_root, ".codex/team-execution/"):
        return ReadinessResult(
            "blocked",
            "repo-local Team Execution state root is not git-ignored",
            "add .codex/team-execution/ to .gitignore or use the user-local fallback",
        )
    return ReadinessResult(
        "ready",
        "protected Team Execution evidence root resolved",
        "Team Execution may enter Phase B",
        normalized,
    )


def _resolve_user_local_ref(repo_root: Path, ref: str) -> ReadinessResult:
    expected = f"~/.codex/team-execution/state/{repo_root.name}/"
    normalized = ref.rstrip("/") + "/"
    if normalized != expected:
        return ReadinessResult(
            "blocked",
            "user-local fallback does not match this repository",
            f"use {expected}",
        )
    if not Path(ref).expanduser().exists():
        return ReadinessResult(
            "blocked",
            "user-local Team Execution evidence root does not exist",
            f"create {expected} or point to a markdown Team Structure receipt",
        )
    return ReadinessResult(
        "ready",
        "user-local Team Execution evidence root resolved",
        "Team Execution may enter Phase B",
        expected,
    )


def _is_ignored(repo_root: Path, rel_path: str) -> bool:
    gitignore = repo_root / ".gitignore"
    if not gitignore.is_file():
        return False
    normalized = rel_path.strip("/")
    normalized_with_slash = f"{normalized}/"
    ignored = False
    for raw_line in gitignore.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        pattern = line[1:] if negated else line
        if _matches_ignore_pattern(pattern, normalized, normalized_with_slash):
            ignored = not negated
    return ignored


def _matches_ignore_pattern(pattern: str, normalized: str, normalized_with_slash: str) -> bool:
    cleaned = pattern.strip().lstrip("/").strip("/")
    if not cleaned:
        return False
    cleaned_with_slash = f"{cleaned}/"
    if cleaned in {normalized, ".codex"}:
        return True
    if normalized_with_slash.startswith(cleaned_with_slash):
        return True
    return fnmatch.fnmatch(normalized, cleaned) or fnmatch.fnmatch(normalized_with_slash, cleaned_with_slash)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="validate Team Execution readiness")
    validate.add_argument("--repo-root", type=Path, default=Path.cwd())
    validate.add_argument("--mode", required=True)
    validate.add_argument("--ref", default="")
    validate.add_argument("--context", choices=sorted(VALID_CONTEXTS), required=True)
    validate.add_argument("--plan-path", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = validate_team_execution_ready(
        args.repo_root,
        orchestration_mode=args.mode,
        orchestration_ref=args.ref,
        context=args.context,
        plan_path=args.plan_path,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 1 if result.status == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
