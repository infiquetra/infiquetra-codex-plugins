"""Cross-surface regressions for Team Execution orchestration readiness."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SAGA_SCRIPTS = ROOT / "plugins" / "saga" / "scripts"
TEAM_SCRIPTS = ROOT / "plugins" / "team-execution" / "scripts"
TEAM_GATE_VEHICLES = {"team-execution-delegated", "team-execution-serial"}


def _load(name: str, path: Path) -> ModuleType:
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TER = _load("team_execution_readiness_regression", SAGA_SCRIPTS / "team_execution_readiness.py")
PROBE = _load("team_execution_protocol_probe_regression", TEAM_SCRIPTS / "protocol_probe.py")
DISPATCHER = _load("outcome_dispatcher_regression", SAGA_SCRIPTS / "outcome_dispatcher.py")


def _team_execution_gate_satisfied(records: list[dict[str, Any]]) -> bool:
    return bool(records) and all(record.get("vehicle") in TEAM_GATE_VEHICLES for record in records)


def test_metadata_only_plan_ready_team_execution_is_blocked(tmp_path: Path) -> None:
    plan = tmp_path / "docs" / "plans" / "metadata-only.md"
    plan.parent.mkdir(parents=True)
    plan.write_text(
        "# Plan\n\nRecommended backend: team-execution\n\nNo receipt here.\n",
        encoding="utf-8",
    )

    result = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref="docs/plans/metadata-only.md",
        context="plan-ready",
    )

    assert result.status == "blocked"
    assert "Team Structure" in result.reason


def test_empty_ref_work_is_blocked_before_mutation(tmp_path: Path) -> None:
    result = TER.validate_team_execution_ready(
        tmp_path,
        orchestration_mode="team-execution",
        orchestration_ref="",
        context="work",
        plan_path="docs/plans/repair.md",
    )

    assert result.status == "blocked"
    assert "docs/plans/repair.md#team-structure" in result.repair_hint


def test_absent_subagents_are_serial_team_execution_not_inline(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(".codex/team-execution/\n", encoding="utf-8")

    payload = PROBE.probe_protocol(
        repo_root=tmp_path,
        subagents="absent",
        validators=[
            PROBE.ValidatorSpec(
                "smoke-tester",
                "tester",
                "required",
                "pytest",
                "present",
            )
        ],
    )

    assert payload["mode"] == "serial"
    assert payload["reviewer_artifacts"][0]["vehicle"] == "team-execution-serial"
    assert payload["validator_artifacts"][0]["vehicle"] == "team-execution-serial"


def test_generic_subagent_and_inline_assist_do_not_satisfy_team_execution_gates() -> None:
    records = [
        {"role": "devils-advocate-reviewer", "vehicle": "generic-subagent"},
        {"role": "security-reviewer", "vehicle": "inline-assist"},
    ]

    assert _team_execution_gate_satisfied(records) is False


def test_resume_instructions_cover_contradiction_and_stale_context_repair() -> None:
    body = (ROOT / "plugins" / "saga" / "skills" / "resume" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    for phrase in (
        "generic-subagent",
        "inline-assist",
        ".codex/plugins/cache/",
        "reread current repo skill files",
        "orchestration_downgrade",
    ):
        assert phrase in body


def test_outcome_team_execution_leaf_without_ref_halts() -> None:
    req = SimpleNamespace(
        outcome_id="ship-x",
        subplot_id="build",
        title="Build",
        backend="team-execution",
        repo_root=Path("."),
        orchestration_ref="",
    )

    result = DISPATCHER.dispatch(req)

    assert result["status"] == "halt"
    assert "missing orchestration_ref" in result["receipt"]["reason"]
