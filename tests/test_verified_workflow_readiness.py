"""Canonical and legacy Verified Workflows readiness boundaries."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).parents[1] / "plugins/saga/scripts/verified_workflow_readiness.py"
spec = importlib.util.spec_from_file_location("u5_readiness", PATH)
assert spec and spec.loader
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def write_plan(root: Path, heading: str = "Workflow Structure") -> Path:
    plan = root / "docs/plans/x.md"
    plan.parent.mkdir(parents=True)
    plan.write_text(f"## {heading}\n", encoding="utf-8")
    return plan


def validate(root: Path, ref: str, *, mode: str = "verified-workflow") -> object:
    return M.validate_verified_workflow_ready(
        root,
        orchestration_mode=mode,
        orchestration_ref=ref,
        context="work",
    )


def test_canonical_workflow_ref_is_ready(tmp_path: Path) -> None:
    write_plan(tmp_path)
    result = validate(tmp_path, "docs/plans/x.md#workflow-structure")
    assert result.status == "ready"
    assert result.resolved_ref.endswith("#workflow-structure")


def test_legacy_ref_is_readable_only_in_explicit_legacy_mode(tmp_path: Path) -> None:
    write_plan(tmp_path, "Team Structure")
    ref = "docs/plans/x.md#team-structure"
    assert validate(tmp_path, ref).status == "blocked"
    legacy = validate(tmp_path, ref, mode="team-execution")
    assert legacy.status == "ready"
    assert "legacy" in legacy.reason.lower()


@pytest.mark.parametrize(
    "ref",
    [
        "/tmp/outside.md#workflow-structure",
        "../outside.md#workflow-structure",
        "docs/plans/x.md#team-structure",
    ],
)
def test_canonical_ref_rejects_absolute_traversal_and_legacy_anchor(
    tmp_path: Path, ref: str
) -> None:
    write_plan(tmp_path)
    assert validate(tmp_path, ref).status == "blocked"


def test_canonical_ref_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-workflow.md"
    outside.write_text("## Workflow Structure\n", encoding="utf-8")
    plan = tmp_path / "docs/plans/x.md"
    plan.parent.mkdir(parents=True)
    plan.symlink_to(outside)
    assert validate(tmp_path, "docs/plans/x.md#workflow-structure").status == "blocked"


def test_canonical_state_root_blocks_mixed_legacy_root(tmp_path: Path) -> None:
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(".codex/verified-workflows/\n", encoding="utf-8")
    canonical = tmp_path / ".codex/verified-workflows/run"
    legacy = tmp_path / ".codex/team-execution"
    canonical.mkdir(parents=True)
    legacy.mkdir(parents=True)
    result = validate(tmp_path, ".codex/verified-workflows/run/")
    assert result.status == "blocked"
    assert "both exist" in result.reason


@pytest.mark.parametrize("canonical_location", ["repo", "user"])
def test_cross_location_mixed_roots_are_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    canonical_location: str,
) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    if canonical_location == "repo":
        (tmp_path / ".codex/verified-workflows/run").mkdir(parents=True)
        (home / ".codex/team-execution/state" / tmp_path.name).mkdir(parents=True)
    else:
        (home / ".codex/verified-workflows/state" / tmp_path.name).mkdir(parents=True)
        (tmp_path / ".codex/team-execution/run").mkdir(parents=True)
    result = validate(tmp_path, "docs/plans/x.md#workflow-structure")
    assert result.status == "blocked"
    assert "across protected locations" in result.reason


@pytest.mark.parametrize("conflict", ["state", "config"])
def test_plan_ref_blocks_mixed_provenance_before_fast_path(tmp_path: Path, conflict: str) -> None:
    write_plan(tmp_path)
    if conflict == "state":
        (tmp_path / ".codex/verified-workflows").mkdir(parents=True)
        (tmp_path / ".codex/team-execution").mkdir(parents=True)
    else:
        (tmp_path / ".verified-workflows.json").write_text("{}\n", encoding="utf-8")
        (tmp_path / ".team-execution.json").write_text('{"legacy": true}\n', encoding="utf-8")
    result = validate(tmp_path, "docs/plans/x.md#workflow-structure")
    assert result.status == "blocked"
    assert "both exist" in result.reason


def test_identical_dual_config_is_deterministic_and_canonical(tmp_path: Path) -> None:
    write_plan(tmp_path)
    for name in (".verified-workflows.json", ".team-execution.json"):
        (tmp_path / name).write_text("{}\n", encoding="utf-8")
    assert validate(tmp_path, "docs/plans/x.md#workflow-structure").status == "ready"


def test_no_ref_falls_back_to_canonical_root_and_rejects_legacy_only(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(".codex/verified-workflows/\n", encoding="utf-8")
    canonical = tmp_path / ".codex/verified-workflows/run"
    canonical.mkdir(parents=True)
    assert validate(tmp_path, "").status == "ready"

    canonical.rmdir()
    canonical.parent.rmdir()
    (tmp_path / ".codex/team-execution/run").mkdir(parents=True)
    result = validate(tmp_path, "")
    assert result.status == "blocked"
    assert "only legacy" in result.reason


def test_user_state_root_rejects_symlink_and_requires_repo_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "workspace/repo"
    repo.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    state_parent = home / ".codex/verified-workflows/state"
    outside = tmp_path / "outside"
    outside.mkdir()
    state_parent.mkdir(parents=True)
    (state_parent / repo.name).symlink_to(outside, target_is_directory=True)
    ref = f"~/.codex/verified-workflows/state/{repo.name}/"
    result = validate(repo, ref)
    assert result.status == "blocked"
    assert "symlink" in result.reason

    (state_parent / repo.name).unlink()
    candidate = state_parent / repo.name
    candidate.mkdir()
    result = validate(repo, ref)
    assert result.status == "blocked"
    assert "identity proof" in result.reason

    marker = {
        "schema": "saga.workflow-repo-identity.v1",
        "repo_root_sha256": hashlib.sha256(repo.resolve().as_posix().encode()).hexdigest(),
    }
    (candidate / ".repo-identity.json").write_text(
        json.dumps(marker, sort_keys=True) + "\n", encoding="utf-8"
    )
    (candidate / ".repo-identity.json").chmod(0o600)
    assert validate(repo, ref).status == "ready"

    candidate.chmod(0o777)
    assert "owner-controlled" in validate(repo, ref).reason
    candidate.chmod(0o700)
    (candidate / ".repo-identity.json").chmod(0o666)
    assert "identity proof" in validate(repo, ref).reason
    (candidate / ".repo-identity.json").chmod(0o600)
    monkeypatch.setattr(M.os, "getuid", lambda: 2**31 - 1)
    assert "owner-controlled" in validate(repo, ref).reason
