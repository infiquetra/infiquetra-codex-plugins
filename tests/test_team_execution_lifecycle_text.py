"""Text regressions for Saga Verified Workflows lifecycle instructions."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SAGA_ROOT = REPO_ROOT / "plugins" / "saga"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_plan_requires_workflow_receipt_and_records_provenance() -> None:
    body = _read(SAGA_ROOT / "skills" / "plan" / "SKILL.md")

    assert "## Workflow Structure" in body
    assert "verified_workflow_readiness.py validate" in body
    assert "--context plan-ready" in body
    assert "--orchestration-ref" in body
    assert "--orchestration-recommended" in body
    assert "--orchestration-operator-choice" in body


def test_plan_section_contract_names_workflow_structure_receipt() -> None:
    body = _read(SAGA_ROOT / "skills" / "plan" / "references" / "plan-sections.md")

    assert "**Workflow Structure**" in body
    assert "selected workflow mode is `verified-workflow`" in body
    assert "## Workflow Structure" in body


def test_work_validates_receipt_before_phase_b_or_mutation() -> None:
    body = _read(SAGA_ROOT / "skills" / "work" / "SKILL.md")

    assert "verified_workflow_readiness.py validate" in body
    assert "--context work" in body
    assert "saving the work tick or mutating code" in body
    assert "Verified Workflows execution" in body
    assert "truthful inline execution" in body
    assert "orchestration_downgrade" in body


def test_work_execution_strategy_replaces_inline_fallback() -> None:
    body = _read(SAGA_ROOT / "skills" / "work" / "references" / "execution-strategy.md")
    lower = body.lower()

    assert "serial Verified Workflows" in body
    assert "orchestration_downgrade" in body
    assert "fall back to `inline`" not in lower
    assert "fall back to inline" not in lower


def test_resume_repairs_workflow_contradictions_before_reentry_tick() -> None:
    body = _read(SAGA_ROOT / "skills" / "resume" / "SKILL.md")

    assert "verified_workflow_readiness.py validate" in body
    assert "--context resume" in body
    for phrase in (
        "empty ref",
        "missing Workflow Structure",
        "generic-subagent",
        "inline prose",
        "stale instruction roots",
        "reread current repo skill files",
        "Before writing this tick",
    ):
        assert phrase in body
    assert "route back to `/loop`" in body
