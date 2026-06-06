from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace


def load_saga() -> ModuleType:
    script = Path(__file__).parents[1] / "scripts" / "saga.py"
    spec = importlib.util.spec_from_file_location("saga_state_engine", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


saga = load_saga()


def quiet_git_runner(*_args: object, **_kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(returncode=1, stdout="", stderr="")


def test_saga_state_uses_codex_root(tmp_path: Path) -> None:
    assert saga.STATE_DIR == Path(".codex/saga")
    assert saga.ORCHESTRATION_MODES == ("inline", "team-execution")

    result = saga.save(
        tmp_path,
        saga.Saga(
            saga_id="task-codex-port",
            kind="task",
            id="codex-port",
            lifecycle_phase="plan",
            orchestration_mode="team-execution",
            summary="Codex port state test",
        ),
        now=datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC),
        runner=quiet_git_runner,
    )

    envelope_path = Path(result["envelope_path"])
    state_path = Path(result["state_path"])
    assert envelope_path.is_file()
    assert state_path.is_file()
    assert ".codex/saga" in envelope_path.as_posix()
    assert ".claude" not in envelope_path.as_posix()

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["active_saga_id"] == "task-codex-port"
    assert state["sagas"]["task-codex-port"]["orchestration_mode"] == "team-execution"


def test_cli_rejects_source_only_backend(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "saga.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "save",
            "--kind",
            "task",
            "--id",
            "bad-backend",
            "--orchestration-mode",
            "cc-workflows-ultracode",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "invalid choice" in result.stderr
