from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import workspace_audit as W  # noqa: E402


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.com")
    (repo / "README.md").write_text("initial\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-qm", "initial")
    return repo


def test_sequential_declared_write_passes(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    before = W.capture_workspace_audit(repo)
    target = repo / "src" / "feature.py"
    target.parent.mkdir()
    target.write_text("value = 1\n")
    after = W.capture_workspace_audit(repo)

    delta = W.validate_attempt_audit(before, after, declared_writes=["src"])
    assert delta.changed_paths == ("src/feature.py",)
    assert delta.attribution == "root-quiescent-sequential"


def test_out_of_scope_write_fails(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    before = W.capture_workspace_audit(repo)
    (repo / "outside.txt").write_text("bad\n")
    after = W.capture_workspace_audit(repo)
    with pytest.raises(W.WorkspaceAuditError, match="outside declared ownership"):
        W.validate_attempt_audit(before, after, declared_writes=["src"])


def test_git_index_divergence_fails(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    before = W.capture_workspace_audit(repo)
    (repo / "src.py").write_text("value = 1\n")
    git(repo, "add", "src.py")
    after = W.capture_workspace_audit(repo)
    with pytest.raises(W.WorkspaceAuditError, match="index"):
        W.validate_attempt_audit(before, after, declared_writes=["src.py"])


def test_preexisting_dirty_overlap_fails(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    (repo / "README.md").write_text("dirty\n")
    before = W.capture_workspace_audit(repo)
    (repo / "README.md").write_text("changed again\n")
    after = W.capture_workspace_audit(repo)
    with pytest.raises(W.WorkspaceAuditError, match="pre-existing dirty"):
        W.validate_attempt_audit(before, after, declared_writes=["README.md"])


def test_concurrent_write_requires_native_attribution(tmp_path: Path) -> None:
    repo = repository(tmp_path)
    before = W.capture_workspace_audit(repo)
    after = W.capture_workspace_audit(repo)
    with pytest.raises(W.WorkspaceAuditError, match="proven per-agent attribution"):
        W.validate_attempt_audit(
            before, after, declared_writes=["src"], concurrent_writable=True
        )
    delta = W.validate_attempt_audit(
        before,
        after,
        declared_writes=["src"],
        concurrent_writable=True,
        mutation_attribution="v2:/root/worker",
    )
    assert delta.attribution == "v2:/root/worker"
