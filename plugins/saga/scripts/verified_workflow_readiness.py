#!/usr/bin/env python3
"""Canonical Verified Workflows readiness with explicit legacy provenance."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fleet_commons_shim  # noqa: E402

WORKFLOW_COMPAT = fleet_commons_shim.load("workflow_compat")


def _legacy() -> Any:
    path = Path(__file__).with_name("team_execution_readiness.py")
    spec = importlib.util.spec_from_file_location("saga_legacy_readiness", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_verified_workflow_ready(
    repo_root: Path,
    *,
    orchestration_mode: str,
    orchestration_ref: str,
    context: str,
    plan_path: str = "",
) -> Any:
    """Validate canonical evidence; accept legacy evidence only for an explicitly legacy mode."""

    legacy = _legacy()
    if context not in legacy.VALID_CONTEXTS:
        raise ValueError(f"unknown Verified Workflows readiness context {context!r}")
    try:
        parsed_mode = WORKFLOW_COMPAT.parse(WORKFLOW_COMPAT.SAGA_MODE, orchestration_mode)
    except WORKFLOW_COMPAT.WorkflowVocabularyError:
        return legacy.ReadinessResult(
            "not-team-execution",
            "orchestration mode is not verified-workflow",
            "no Verified Workflows receipt is required",
        )
    if parsed_mode.is_legacy:
        result = legacy.validate_team_execution_ready(
            repo_root,
            orchestration_mode=orchestration_mode,
            orchestration_ref=orchestration_ref,
            context=context,
            plan_path=plan_path,
        )
        if result.status == "ready":
            return legacy.ReadinessResult(
                "ready",
                f"legacy Team Execution evidence resolved: {result.reason}",
                "legacy evidence is read-only and cannot attest a new Verified Workflow run",
                result.resolved_ref,
            )
        return result

    provenance_conflict = _provenance_conflict(repo_root, legacy)
    if provenance_conflict is not None:
        return provenance_conflict

    ref = orchestration_ref.strip()
    if not ref:
        if context == "draft-plan":
            return legacy.ReadinessResult(
                "draft",
                "Verified Workflows receipt has not been materialized yet",
                "materialize Workflow Structure before marking the plan ready",
            )
        repo_state = repo_root / WORKFLOW_COMPAT.emit(WORKFLOW_COMPAT.REPO_STATE_ROOT)
        if repo_state.is_dir():
            return _resolve_repo_root(repo_root, repo_state, legacy)
        user_ref = f"{WORKFLOW_COMPAT.emit(WORKFLOW_COMPAT.USER_STATE_ROOT)}{repo_root.name}/"
        if Path(user_ref).expanduser().is_dir():
            return _resolve_user_root(repo_root, user_ref, legacy)
        legacy_repo = repo_root / WORKFLOW_COMPAT.legacy_values(WORKFLOW_COMPAT.REPO_STATE_ROOT)[0]
        legacy_user = Path(
            f"{WORKFLOW_COMPAT.legacy_values(WORKFLOW_COMPAT.USER_STATE_ROOT)[0]}{repo_root.name}/"
        ).expanduser()
        if legacy_repo.exists() or legacy_user.exists():
            return legacy.ReadinessResult(
                "blocked",
                "only legacy workflow state is available for a canonical run",
                "migrate evidence into one canonical Verified Workflows state root",
            )
        return legacy.ReadinessResult(
            "blocked",
            "missing orchestration_ref for executable Verified Workflows",
            _repair_hint(plan_path),
        )
    if ref.startswith("~/"):
        return _resolve_user_root(repo_root, ref, legacy)
    if Path(ref).is_absolute():
        return legacy.ReadinessResult(
            "blocked",
            "absolute orchestration_ref is not portable",
            "use a repository-relative artifact or the exact canonical user-state root",
        )
    path_text, separator, anchor = ref.partition("#")
    relative = Path(path_text.strip())
    if not path_text.strip() or ".." in relative.parts or "\\" in path_text:
        return legacy.ReadinessResult(
            "blocked",
            "orchestration_ref escapes the repository",
            "use a contained repository-relative Workflow Structure artifact",
        )
    candidate = repo_root / relative
    containment = _containment_error(repo_root, candidate, legacy)
    if containment is not None:
        return containment
    if candidate.is_dir():
        return _resolve_repo_root(repo_root, candidate, legacy)
    if not candidate.is_file():
        return legacy.ReadinessResult(
            "blocked", "orchestration_ref target does not exist", _repair_hint(plan_path)
        )
    if relative.suffix.lower() not in {".md", ".markdown"}:
        return legacy.ReadinessResult(
            "blocked",
            "file orchestration_ref is not a markdown Workflow Structure receipt",
            _repair_hint(plan_path),
        )
    canonical_anchor = WORKFLOW_COMPAT.emit(WORKFLOW_COMPAT.PLAN_ANCHOR).lstrip("#")
    legacy_anchor = WORKFLOW_COMPAT.legacy_values(WORKFLOW_COMPAT.PLAN_ANCHOR)[0].lstrip("#")
    normalized_anchor = legacy._normalize_anchor(anchor) if separator else canonical_anchor
    if normalized_anchor == legacy_anchor:
        return legacy.ReadinessResult(
            "blocked",
            "legacy Team Structure evidence cannot authorize a new Verified Workflow run",
            f"use {relative.as_posix()}#{canonical_anchor}",
        )
    if normalized_anchor != canonical_anchor:
        return legacy.ReadinessResult(
            "blocked",
            "orchestration_ref anchor is not #workflow-structure",
            f"use {relative.as_posix()}#{canonical_anchor}",
        )
    headings = legacy._markdown_heading_anchors(candidate.read_text(encoding="utf-8"))
    if canonical_anchor not in headings:
        return legacy.ReadinessResult(
            "blocked",
            "orchestration_ref anchor does not resolve to ## Workflow Structure",
            "materialize the canonical Workflow Structure in the referenced file",
        )
    return legacy.ReadinessResult(
        "ready",
        "Workflow Structure receipt resolved",
        "Verified Workflows may execute",
        f"{relative.as_posix()}#{canonical_anchor}",
    )


def _repair_hint(plan_path: str) -> str:
    if plan_path:
        return f"add or link ## Workflow Structure and use {plan_path}#workflow-structure"
    return "add or link a canonical ## Workflow Structure receipt"


def _provenance_conflict(repo_root: Path, legacy: Any) -> Any | None:
    canonical_roots = (
        repo_root / WORKFLOW_COMPAT.emit(WORKFLOW_COMPAT.REPO_STATE_ROOT),
        Path(
            f"{WORKFLOW_COMPAT.emit(WORKFLOW_COMPAT.USER_STATE_ROOT)}{repo_root.name}/"
        ).expanduser(),
    )
    legacy_roots = (
        repo_root / WORKFLOW_COMPAT.legacy_values(WORKFLOW_COMPAT.REPO_STATE_ROOT)[0],
        Path(
            f"{WORKFLOW_COMPAT.legacy_values(WORKFLOW_COMPAT.USER_STATE_ROOT)[0]}{repo_root.name}/"
        ).expanduser(),
    )
    if any(path.exists() for path in canonical_roots) and any(
        path.exists() for path in legacy_roots
    ):
        return legacy.ReadinessResult(
            "blocked",
            "canonical and legacy workflow state roots both exist across protected locations",
            "resolve the mixed-provenance conflict explicitly before execution",
        )
    pairs = (
        (
            repo_root / WORKFLOW_COMPAT.emit(WORKFLOW_COMPAT.REPO_CONFIG_FILE),
            repo_root / WORKFLOW_COMPAT.legacy_values(WORKFLOW_COMPAT.REPO_CONFIG_FILE)[0],
            "repository workflow config files",
        ),
    )
    for canonical, old, label in pairs:
        if canonical.exists() and old.exists():
            if label == "repository workflow config files":
                try:
                    if (
                        not canonical.is_symlink()
                        and not old.is_symlink()
                        and canonical.is_file()
                        and old.is_file()
                        and canonical.stat().st_size <= 64 * 1024
                        and old.stat().st_size <= 64 * 1024
                        and canonical.read_bytes() == old.read_bytes()
                    ):
                        continue
                except OSError:
                    pass
            return legacy.ReadinessResult(
                "blocked",
                f"canonical and legacy {label} both exist",
                "resolve the mixed-provenance conflict explicitly before execution",
            )
    return None


def _containment_error(repo_root: Path, candidate: Path, legacy: Any) -> Any | None:
    try:
        candidate.resolve().relative_to(repo_root.resolve())
    except (OSError, ValueError):
        return legacy.ReadinessResult(
            "blocked",
            "orchestration_ref escapes the repository",
            "use a contained repository-relative Workflow Structure artifact",
        )
    current = repo_root
    try:
        relative = candidate.relative_to(repo_root)
    except ValueError:
        return legacy.ReadinessResult(
            "blocked", "orchestration_ref escapes the repository", _repair_hint("")
        )
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return legacy.ReadinessResult(
                "blocked",
                "orchestration_ref contains a symlink",
                "use a regular contained repository artifact",
            )
    return None


def _resolve_repo_root(repo_root: Path, candidate: Path, legacy: Any) -> Any:
    relative = candidate.resolve().relative_to(repo_root.resolve()).as_posix().rstrip("/") + "/"
    try:
        parsed = WORKFLOW_COMPAT.parse_prefix(WORKFLOW_COMPAT.REPO_STATE_ROOT, relative)
    except WORKFLOW_COMPAT.WorkflowVocabularyError:
        return legacy.ReadinessResult(
            "blocked",
            "state root is not under .codex/verified-workflows",
            "use the protected canonical state root",
        )
    if parsed.is_legacy:
        return legacy.ReadinessResult(
            "blocked",
            "legacy state cannot authorize a new Verified Workflow run",
            "migrate evidence into the canonical protected state root",
        )
    legacy_root = repo_root / WORKFLOW_COMPAT.legacy_values(WORKFLOW_COMPAT.REPO_STATE_ROOT)[0]
    if legacy_root.exists():
        return legacy.ReadinessResult(
            "blocked",
            "canonical and legacy workflow state roots both exist",
            "resolve the mixed-root conflict explicitly before execution",
        )
    if not legacy._is_ignored(repo_root, WORKFLOW_COMPAT.emit(WORKFLOW_COMPAT.REPO_STATE_ROOT)):
        return legacy.ReadinessResult(
            "blocked",
            "repo-local Verified Workflows state root is not git-ignored",
            "ignore .codex/verified-workflows/ or use the canonical user-state root",
        )
    return legacy.ReadinessResult(
        "ready",
        "protected Verified Workflows state root resolved",
        "Verified Workflows may execute",
        relative,
    )


def _resolve_user_root(repo_root: Path, ref: str, legacy: Any) -> Any:
    canonical_prefix = WORKFLOW_COMPAT.emit(WORKFLOW_COMPAT.USER_STATE_ROOT)
    expected = f"{canonical_prefix}{repo_root.name}/"
    normalized = ref.rstrip("/") + "/"
    if normalized != expected:
        return legacy.ReadinessResult(
            "blocked", "user-local fallback does not match this repository", f"use {expected}"
        )
    candidate = Path(expected).expanduser()
    if not candidate.is_dir():
        return legacy.ReadinessResult(
            "blocked", "canonical user-state root does not exist", f"create {expected}"
        )
    try:
        root_metadata = candidate.stat()
    except OSError:
        return legacy.ReadinessResult(
            "blocked",
            "canonical user-state root could not be inspected",
            "repair the canonical user-state directory",
        )
    if root_metadata.st_uid != os.getuid() or root_metadata.st_mode & 0o022:
        return legacy.ReadinessResult(
            "blocked",
            "canonical user-state root is not owner-controlled",
            "use a current-user-owned directory without group/world write access",
        )
    home = Path.home()
    try:
        relative = candidate.relative_to(home)
    except ValueError:
        return legacy.ReadinessResult(
            "blocked", "canonical user-state root escapes the user home", f"use {expected}"
        )
    current = home
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return legacy.ReadinessResult(
                "blocked",
                "canonical user-state root contains a symlink",
                "use a regular canonical user-state directory",
            )
    identity = candidate / ".repo-identity.json"
    try:
        fd = os.open(identity, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return legacy.ReadinessResult(
            "blocked",
            "canonical user-state root lacks repository identity proof",
            "write the bounded .repo-identity.json marker for this repository",
        )
    try:
        metadata = os.fstat(fd)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_size > 4096
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o022
        ):
            raise ValueError("identity marker must be a bounded regular file")
        content = os.read(fd, metadata.st_size + 1)
    except (OSError, ValueError):
        return legacy.ReadinessResult(
            "blocked",
            "canonical user-state repository identity proof is invalid",
            "replace .repo-identity.json with a bounded regular marker",
        )
    finally:
        os.close(fd)
    try:
        marker = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        marker = None
    expected_marker = {
        "schema": "saga.workflow-repo-identity.v1",
        "repo_root_sha256": hashlib.sha256(repo_root.resolve().as_posix().encode()).hexdigest(),
    }
    if marker != expected_marker:
        return legacy.ReadinessResult(
            "blocked",
            "canonical user-state repository identity proof does not match",
            "regenerate .repo-identity.json for this resolved repository",
        )
    return legacy.ReadinessResult(
        "ready", "canonical user-state root resolved", "Verified Workflows may execute", expected
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--repo-root", default=".")
    validate.add_argument("--mode", required=True)
    validate.add_argument("--ref", default="")
    validate.add_argument("--context", required=True)
    validate.add_argument("--plan-path", default="")
    args = parser.parse_args(argv)
    result = validate_verified_workflow_ready(
        Path(args.repo_root).resolve(),
        orchestration_mode=args.mode,
        orchestration_ref=args.ref,
        context=args.context,
        plan_path=args.plan_path,
    )
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0 if result.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
