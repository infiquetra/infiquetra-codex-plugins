from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import external_action_adapters as A  # noqa: E402
import external_action_workspace as W  # noqa: E402


def test_cli_child_environment_drops_root_secret_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    monkeypatch.setenv("PATH", "/usr/bin")
    environment = A._minimal_child_env()
    assert environment["PATH"] == "/usr/bin"
    assert "AWS_SECRET_ACCESS_KEY" not in environment
    assert "ANTHROPIC_API_KEY" not in environment


def test_claude_cli_uses_read_only_tools_and_minimal_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    class FakeWorkspace:
        checkout = tmp_path

        def capture_patch(self, _write_set: tuple[str, ...]):
            return "", (), ()

        def close(self) -> None:
            return None

    class FakeProcess:
        pid = 4321
        returncode = 0

        def communicate(self, _stdin: str | None = None, timeout: int | None = None):
            assert timeout == 900
            return "review output", ""

        def poll(self) -> int:
            return 0

    def fake_popen(argv: list[str], **kwargs: object) -> FakeProcess:
        seen["argv"] = argv
        seen["env"] = kwargs["env"]
        return FakeProcess()

    monkeypatch.setattr(A.Workspace, "create", lambda *_args, **_kwargs: FakeWorkspace())
    monkeypatch.setattr(A.subprocess, "Popen", fake_popen)
    monkeypatch.setenv("AWS_SESSION_TOKEN", "must-not-leak")
    runner = A.runner_for("claude-cli", repo_root=tmp_path, variant="opus")
    result = runner(
        {
            "base_revision": "HEAD",
            "write_set": [],
            "context_scope": [],
            "model": "opus",
            "task": "review",
        }
    )
    assert result["status"] == "ok"
    assert "Read,Glob,Grep" in seen["argv"]
    assert "Edit" not in seen["argv"]
    assert "Write" not in seen["argv"]
    assert "--permission-mode" not in seen["argv"]
    assert "AWS_SESSION_TOKEN" not in seen["env"]


def test_scoped_context_rejects_secret_like_content(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    target = repo / "docs" / "input.txt"
    target.parent.mkdir()
    target.write_text("credential=AKIAABCDEFGHIJKLMNOP\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
    with pytest.raises(W.WorkspaceError, match="secret-like content"):
        W.Workspace.create(
            repo,
            "HEAD",
            visible_paths=("docs/input.txt",),
            required_paths=("docs/input.txt",),
        )


def test_adapter_source_contains_no_permission_bypass() -> None:
    source = (SCRIPTS / "external_action_adapters.py").read_text()
    assert "dangerously-skip-permissions" not in source
    assert "acceptEdits" not in source
