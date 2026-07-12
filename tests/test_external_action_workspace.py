from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from external_action_workspace import Workspace  # noqa: E402


def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "a.txt").write_text("a\n")
    subprocess.run(["git", "add", "a.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=path, check=True)
    return path


def test_clone_removes_remotes_and_captures_in_scope_patch(tmp_path: Path) -> None:
    source = repo(tmp_path)
    workspace = Workspace.create(source, "HEAD")
    try:
        assert subprocess.run(["git", "remote"], cwd=workspace.checkout, text=True, capture_output=True).stdout == ""
        (workspace.checkout / "a.txt").write_text("changed\n")
        patch, changed, escaped = workspace.capture_patch(("a.txt",))
        assert changed == ("a.txt",)
        assert escaped == ()
        assert "changed" in patch
    finally:
        root = workspace.root
        workspace.close()
        assert not root.exists()


def test_write_set_escape_is_reported(tmp_path: Path) -> None:
    workspace = Workspace.create(repo(tmp_path), "HEAD")
    try:
        (workspace.checkout / "a.txt").write_text("changed\n")
        assert workspace.capture_patch(("other.txt",))[2] == ("a.txt",)
    finally:
        workspace.close()
