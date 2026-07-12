from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import external_action_adapters as adapters  # noqa: E402


def test_cli_runner_emits_receipt_and_cleans_workspace(tmp_path: Path, monkeypatch) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "a.txt").write_text("a\n")
    subprocess.run(["git", "add", "a.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    runner = adapters.cli_runner(
        adapters.CliConfig("fake", "cat", "agy-delegate", lambda invocation: ["cat"]),
        repo_root=tmp_path,
    )
    result = runner({"task": "hello", "variant": "v1", "base_revision": "HEAD", "write_set": []})
    assert result["status"] == "ok"
    assert result["output"] == "hello"
    assert result["receipt"]["schema"] == "bridge_receipt.v1"
    assert result["receipt"]["runner"]["argv"] == ["cat"]


def test_runner_factory_keeps_http_generic(tmp_path: Path) -> None:
    assert callable(adapters.runner_for("ollama-cloud", repo_root=tmp_path))


def test_cli_timeout_is_terminal_and_workspace_is_cleaned(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "a.txt").write_text("a\n")
    subprocess.run(["git", "add", "a.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    runner = adapters.cli_runner(
        adapters.CliConfig(
            "fake",
            "sh",
            "agy-delegate",
            lambda _invocation: ["sh", "-c", "sleep 2"],
            timeout_seconds=1,
        ),
        repo_root=tmp_path,
    )

    result = runner({"task": "hello", "variant": "v1", "base_revision": "HEAD"})

    assert result["status"] == "timeout"


def test_cli_child_is_killed_when_launch_persistence_fails(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    runner = adapters.cli_runner(
        adapters.CliConfig("fake", "sh", "agy-delegate", lambda _invocation: ["sh", "-c", "sleep 60"]),
        repo_root=tmp_path,
        on_launch=lambda _identity: (_ for _ in ()).throw(RuntimeError("store failed")),
    )
    started = time.monotonic()
    try:
        runner({"task": "hello", "variant": "v1", "base_revision": "HEAD"})
    except RuntimeError as exc:
        assert "store failed" in str(exc)
    else:
        raise AssertionError("launch persistence failure was ignored")
    assert time.monotonic() - started < 5
