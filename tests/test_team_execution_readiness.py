from __future__ import annotations

import importlib.util
import pytest
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "plugins" / "saga" / "scripts" / "team_execution_readiness.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("team_execution_readiness", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TER = _load()


def test_valid_team_structure_anchor_is_ready(tmp_path: Path) -> None:
    plan = tmp_path / "docs" / "plans" / "repair.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("# Plan\n\n## Team Structure\n\nroles\n", encoding="utf-8")

    result = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref="docs/plans/repair.md#team-structure",
        context="work",
    )

    assert result.status == "ready"
    assert result.resolved_ref == "docs/plans/repair.md#team-structure"


def test_markdown_without_anchor_can_resolve_team_structure(tmp_path: Path) -> None:
    plan = tmp_path / "docs" / "plans" / "repair.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("# Plan\n\n## Team Structure\n\nroles\n", encoding="utf-8")

    result = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref="docs/plans/repair.md",
        context="plan-ready",
    )

    assert result.status == "ready"
    assert result.resolved_ref == "docs/plans/repair.md#team-structure"


def test_empty_ref_is_draft_only(tmp_path: Path) -> None:
    draft = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref="",
        context="draft-plan",
    )
    blocked = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref="",
        context="work",
        plan_path="docs/plans/repair.md",
    )

    assert draft.status == "draft"
    assert blocked.status == "blocked"
    assert "docs/plans/repair.md#team-structure" in blocked.repair_hint


def test_invalid_ref_shapes_block(tmp_path: Path) -> None:
    plan = tmp_path / "docs" / "plans" / "repair.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("# Plan\n\n## Other\n", encoding="utf-8")

    missing = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref="docs/plans/missing.md",
        context="work",
    )
    no_team_structure = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref="docs/plans/repair.md#team-structure",
        context="work",
    )
    absolute = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref=str(plan),
        context="work",
    )

    assert missing.status == "blocked"
    assert no_team_structure.status == "blocked"
    assert absolute.status == "blocked"


def test_path_traversal_and_symlink_escape_block(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\n\n## Team Structure\n\nspoof\n", encoding="utf-8")

    traversal = TER.validate_team_execution_ready(
        repo,
        orchestration_mode="team-execution",
        orchestration_ref="../outside.md#team-structure",
        context="work",
    )
    assert traversal.status == "blocked"
    assert "escapes the repository" in traversal.reason

    link = repo / "linked.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable on this filesystem")
    symlink = TER.validate_team_execution_ready(
        repo,
        orchestration_mode="team-execution",
        orchestration_ref="linked.md#team-structure",
        context="work",
    )
    assert symlink.status == "blocked"
    assert "escapes the repository" in symlink.reason


def test_repo_local_state_root_must_be_protected(tmp_path: Path) -> None:
    state_root = tmp_path / ".codex" / "team-execution"
    state_root.mkdir(parents=True)
    unprotected = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref=".codex/team-execution/",
        context="work",
    )
    (tmp_path / ".gitignore").write_text(".codex/team-execution/\n", encoding="utf-8")
    protected = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref=".codex/team-execution/",
        context="work",
    )

    assert unprotected.status == "blocked"
    assert protected.status == "ready"


def test_repo_local_state_root_respects_gitignore_negation(tmp_path: Path) -> None:
    state_root = tmp_path / ".codex" / "team-execution"
    state_root.mkdir(parents=True)
    (tmp_path / ".gitignore").write_text(
        ".codex/\n!.codex/team-execution/\n",
        encoding="utf-8",
    )

    result = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref=".codex/team-execution/",
        context="work",
    )

    assert result.status == "blocked"
    assert "not git-ignored" in result.reason


def test_user_local_fallback_must_match_repo_and_exist(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    repo.mkdir()
    fallback = home / ".codex" / "team-execution" / "state" / "repo"
    fallback.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    result = TER.validate_team_execution_ready(
        repo,
        orchestration_mode="team-execution",
        orchestration_ref="~/.codex/team-execution/state/repo/",
        context="work",
    )

    assert result.status == "ready"


def test_non_team_execution_modes_do_not_touch_filesystem(tmp_path: Path) -> None:
    for mode in ("inline", "manual"):
        result = TER.validate_team_execution_ready(
            tmp_path / "does-not-exist",
            orchestration_mode=mode,
            orchestration_ref="",
            context="work",
        )
        assert result.status == "not-team-execution"
