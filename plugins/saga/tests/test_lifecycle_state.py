from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_script(name: str) -> ModuleType:
    script = Path(__file__).parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"saga_{name}", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lifecycle_state = load_script("lifecycle_state")


def test_codex_backend_choices_exclude_source_workflow_backend() -> None:
    result = lifecycle_state.recommend_execution_backend(broad_independent_fanout=True)

    assert result["recommended"] == "team-execution"
    assert result["alternatives"] == ["inline"]
    assert result["source_workflow_excluded"] is True
    assert "cc-workflows-ultracode" not in str(result)
    assert "source-workflow-fanout" in result["unsupported_source_backends"]


def test_inline_remains_default_for_low_risk_work() -> None:
    result = lifecycle_state.recommend_execution_backend()

    assert result["recommended"] == "inline"
    assert result["alternatives"] == ["team-execution"]


def test_destination_normalizes_nonprod_deploy_intent() -> None:
    assert lifecycle_state.normalize_destination("deploy") == "nonprod-deploy"
    assert lifecycle_state.destination_includes_deploy("nonprod") is True
