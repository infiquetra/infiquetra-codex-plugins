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

    assert result["recommended"] == "verified-workflow"
    assert result["alternatives"] == ["inline", "manual"]
    assert result["source_workflow_excluded"] is True
    assert "cc-workflows-ultracode" not in str(result)
    assert "source-workflow-fanout" in result["unsupported_source_backends"]


def test_inline_remains_default_for_low_risk_work() -> None:
    result = lifecycle_state.recommend_execution_backend()

    assert result["recommended"] == "inline"
    assert result["alternatives"] == ["manual", "verified-workflow"]


def test_manual_handoff_can_be_recommended() -> None:
    result = lifecycle_state.recommend_execution_backend(manual_handoff=True)

    assert result["recommended"] == "manual"
    assert result["alternatives"] == ["inline", "verified-workflow"]


def test_large_no_code_surface_stays_inline_without_coordination_signal() -> None:
    assert (
        lifecycle_state.should_offer_team_execution(
            file_count=12,
            phase_count=1,
            has_security=False,
            has_infra=False,
            cross_repo=False,
            deployment_sensitive=False,
            has_code_surface=False,
        )
        is False
    )

    result = lifecycle_state.recommend_execution_backend(
        file_count=12,
        has_code_surface=False,
    )

    assert result["recommended"] == "inline"


def test_cross_repo_and_adversarial_confidence_still_escalate() -> None:
    cross_repo = lifecycle_state.recommend_execution_backend(
        cross_repo=True,
        has_code_surface=False,
    )
    adversarial = lifecycle_state.recommend_execution_backend(adversarial_confidence=True)

    assert cross_repo["recommended"] == "verified-workflow"
    assert adversarial["recommended"] == "verified-workflow"


def test_destination_normalizes_nonprod_deploy_intent() -> None:
    assert lifecycle_state.normalize_destination("deploy") == "nonprod-deploy"
    assert lifecycle_state.destination_includes_deploy("nonprod") is True
