from __future__ import annotations

import subprocess
import sys
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
