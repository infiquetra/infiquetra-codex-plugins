from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).parents[1] / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from external_action_workspace import (  # noqa: E402
    Workspace,
    WorkspaceError,
    _contains_secret,
    import_approved_patch,
)


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


def test_external_git_mutation_is_rejected(tmp_path: Path) -> None:
    workspace = Workspace.create(repo(tmp_path), "HEAD")
    try:
        subprocess.run(
            ["git", "checkout", "-qb", "provider-branch"],
            cwd=workspace.checkout,
            check=True,
        )
        with pytest.raises(WorkspaceError, match="Git refs"):
            workspace.capture_patch(("a.txt",))
    finally:
        workspace.close()


def test_scoped_workspace_withholds_undeclared_history(tmp_path: Path) -> None:
    source = repo(tmp_path)
    (source / "undeclared.txt").write_text("withheld\n", encoding="utf-8")
    subprocess.run(["git", "add", "undeclared.txt"], cwd=source, check=True)
    subprocess.run(["git", "commit", "-qm", "add undeclared"], cwd=source, check=True)

    workspace = Workspace.create(
        source,
        "HEAD",
        visible_paths=("a.txt",),
        required_paths=("a.txt",),
    )
    try:
        assert (workspace.checkout / "a.txt").read_text(encoding="utf-8") == "a\n"
        assert not (workspace.checkout / "undeclared.txt").exists()
        history_probe = subprocess.run(
            ["git", "show", "HEAD:undeclared.txt"],
            cwd=workspace.checkout,
            text=True,
            capture_output=True,
            check=False,
        )
        assert history_probe.returncode != 0
    finally:
        workspace.close()


def test_scoped_workspace_rejects_nested_secret_paths(tmp_path: Path) -> None:
    source = repo(tmp_path)
    secret = source / "src" / "credentials"
    secret.mkdir(parents=True)
    (secret / "token.txt").write_text("secret\n", encoding="utf-8")
    subprocess.run(["git", "add", "src"], cwd=source, check=True)
    subprocess.run(["git", "commit", "-qm", "add secret fixture"], cwd=source, check=True)

    with pytest.raises(WorkspaceError, match="unsafe member"):
        Workspace.create(
            source,
            "HEAD",
            visible_paths=("src",),
            required_paths=("src",),
        )


@pytest.mark.parametrize(
    "content",
    [
        b"eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signaturevalue",
        b"xox" + b"b-1234567890-abcdefghijklmnop",
        b"ASIAABCDEFGHIJKLMNOP",
        b"Authorization: Bearer abcdefghijklmnop",
        b"password=correct-horse-battery-staple",
        b"\xff\xfe\x00binary",
    ],
)
def test_secret_content_detection_fails_closed(content: bytes) -> None:
    assert _contains_secret(content)


def test_root_import_applies_only_approval_bound_patch(tmp_path: Path) -> None:
    source = repo(tmp_path)
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    workspace = Workspace.create(source, base)
    try:
        (workspace.checkout / "a.txt").write_text("changed\n", encoding="utf-8")
        patch, changed, escaped = workspace.capture_patch(("a.txt",))
    finally:
        workspace.close()
    assert escaped == ()
    patch_path = tmp_path / "approved.diff"
    patch_path.write_text(patch, encoding="utf-8")
    import hashlib

    patch_sha256 = hashlib.sha256(patch_path.read_bytes()).hexdigest()
    approval = SimpleNamespace(
        base_revision=base,
        dirty_overlap=(),
        write_set=("a.txt",),
    )

    result = import_approved_patch(
        repo_root=source,
        approval=approval,
        patch_path=patch_path,
        patch_sha256=patch_sha256,
        changed_paths=changed,
    )

    assert result.changed_paths == ("a.txt",)
    assert result.authority == "root-import"
    assert (source / "a.txt").read_text(encoding="utf-8") == "changed\n"


def test_root_import_rejects_changed_base(tmp_path: Path) -> None:
    source = repo(tmp_path)
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    patch_path = tmp_path / "empty.diff"
    patch_path.write_text("", encoding="utf-8")
    subprocess.run(["git", "commit", "--allow-empty", "-qm", "advance"], cwd=source, check=True)

    with pytest.raises(WorkspaceError, match="base changed"):
        import_approved_patch(
            repo_root=source,
            approval=SimpleNamespace(
                base_revision=base,
                dirty_overlap=(),
                write_set=("a.txt",),
            ),
            patch_path=patch_path,
            patch_sha256=__import__("hashlib").sha256(b"").hexdigest(),
            changed_paths=("a.txt",),
        )
