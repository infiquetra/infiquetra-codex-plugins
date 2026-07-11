"""Drift guards for Codex Saga backend choice language."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SAGA_ROOT = REPO_ROOT / "plugins" / "saga"
OPERATOR_CHOICE = SAGA_ROOT / "references" / "operator-choice.md"
HARNESS_DELTA = REPO_ROOT / "docs" / "portability" / "codex-saga-041-harness-delta.md"
OFFER_SURFACES = (
    SAGA_ROOT / "skills" / "plan" / "SKILL.md",
    SAGA_ROOT / "skills" / "work" / "SKILL.md",
    SAGA_ROOT / "skills" / "outcome" / "SKILL.md",
    SAGA_ROOT / "skills" / "code-review" / "SKILL.md",
    SAGA_ROOT / "skills" / "founder-review" / "SKILL.md",
    SAGA_ROOT / "skills" / "loop" / "SKILL.md",
    SAGA_ROOT / "skills" / "work" / "references" / "execution-strategy.md",
    SAGA_ROOT / "skills" / "loop" / "references" / "drive-and-resume.md",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_codex_operator_choice_separates_runtime_dimensions() -> None:
    body = _read(OPERATOR_CHOICE)
    for dimension in (
        "lifecycle and state",
        "continuation",
        "workflow mode",
        "step vehicle",
        "role identity",
        "execution-class control",
        "hooks",
    ):
        assert dimension in body


def test_operator_choice_requires_configured_named_child_selection_and_readback() -> None:
    body = _read(OPERATOR_CHOICE)

    assert "hide_spawn_agent_metadata=false" in body
    assert 'tool_namespace="agents"' in body
    assert "agent_type=<runtime_agent_name>" in body
    assert 'fork_turns="none"' in body
    assert "permission-homogeneous parent tasks" in body
    assert "host-issued child role/model/effort" in body
    assert "generic subagent output remains generic evidence" in body


def test_harness_delta_records_inactive_source_backends() -> None:
    body = _read(HARNESS_DELTA)
    for backend in ("workflow", "fork", "goal", "hooks"):
        assert backend in body
    assert "inactive" in body
    assert "degrade" in body or "degraded" in body


def test_offer_surfaces_do_not_advertise_source_workflow_as_active() -> None:
    forbidden_active_phrases = (
        "use workflow",
        "run workflow",
        "workflow backend is active",
        "cc-workflows-ultracode is active",
    )
    for path in OFFER_SURFACES:
        body = _read(path)
        for phrase in forbidden_active_phrases:
            assert phrase not in body, f"{path} advertises source Workflow as active"


def test_offer_surfaces_do_not_revert_to_two_backend_wording() -> None:
    forbidden_phrases = (
        "exactly two backends",
        "inline | team-execution",
        "team-execution` / `team-execution",
        "team-execution / team-execution",
    )
    for path in OFFER_SURFACES:
        body = _read(path)
        for phrase in forbidden_phrases:
            assert phrase not in body, f"{path} has stale backend wording: {phrase}"


def test_team_execution_unavailable_does_not_silently_fallback_inline() -> None:
    forbidden_phrases = (
        "fall back to `inline`",
        "fall back to inline",
        "fallback to inline",
    )
    for path in OFFER_SURFACES:
        body = _read(path)
        for phrase in forbidden_phrases:
            assert phrase not in body, f"{path} silently falls back from Team Execution to inline"


def test_recommend_backend_excludes_source_workflow() -> None:
    result = subprocess.run(
        [
            "python3",
            "plugins/saga/scripts/lifecycle_state.py",
            "recommend-backend",
            "--file-count",
            "20",
            "--phase-count",
            "7",
            "--broad-fanout",
            "--no-workflow",
        ],
        cwd=REPO_ROOT,
        text=True,
        check=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)
    assert payload["recommended"] == "team-execution"
    assert payload["alternatives"] == ["inline", "manual"]
    assert payload["source_workflow_excluded"] is True
    assert "source-workflow-fanout" in payload["unsupported_source_backends"]
