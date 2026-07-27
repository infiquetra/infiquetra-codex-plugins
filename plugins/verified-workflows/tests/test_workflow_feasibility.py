from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
TESTS = Path(__file__).parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import workflow_feasibility as feasibility  # noqa: E402
from test_workflow_dispatch import assignment, plan, reviewer, worker  # noqa: E402

SNAPSHOT = Path(__file__).parents[3] / "docs/validation/codex-runtime-capability-snapshot.json"
REPOSITORY_PLAN = (
    Path(__file__).parents[3]
    / "docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md"
)


def write_plan(tmp_path: Path) -> Path:
    path = tmp_path / "plan.md"
    path.write_text(plan([assignment("implement"), reviewer(), worker()]), encoding="utf-8")
    return path


def test_v2_contract_is_compile_time_ready(tmp_path: Path) -> None:
    result = feasibility.review_workflow(
        plan=write_plan(tmp_path),
        snapshot_path=SNAPSHOT,
        plan_revision="approved-revision",
    )

    assert result["outcome"] == "ready"
    assert result["runtime_proof"] is False
    assert result["spawn_surface"] == "agents"
    rows = {row["assignment_id"]: row for row in result["rows"]}
    assert rows["implement"]["disposition"] == "v2-launch-ready"
    assert rows["review"]["disposition"] == "fresh-review-root-required"
    assert rows["test"]["disposition"] == "v2-launch-ready"
    assert result["contract_sha256"]
    assert result["approval_binding_sha256"]


def test_legacy_root_owned_repository_plan_requires_replanning() -> None:
    with pytest.raises(feasibility.WorkflowFeasibilityError, match="columns must be exactly"):
        feasibility.review_workflow(
            plan=REPOSITORY_PLAN,
            snapshot_path=SNAPSHOT,
            plan_revision="reviewed-plan",
        )


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda payload: payload.update({"collaboration": []}), "collaboration must be an object"),
        (
            lambda payload: payload["collaboration"].update({"spawn": []}),
            "collaboration.spawn must be an object",
        ),
        (
            lambda payload: payload["collaboration"]["spawn"].update({"contract_version": "v1"}),
            "Codex V2 configured-agent spawning is not available",
        ),
        (
            lambda payload: payload["collaboration"]["spawn"].update({"per_child_agent_type": False}),
            "named profile selection is not source-confirmed",
        ),
        (
            lambda payload: payload["collaboration"]["spawn"].update({"request_fields": []}),
            "spawn request fields are incomplete",
        ),
        (
            lambda payload: payload["collaboration"]["spawn"].update(
                {"selection_readback_fields": []}
            ),
            "runtime readback fields are incomplete",
        ),
    ],
)
def test_capability_projection_failures_are_actionable(
    tmp_path: Path, mutator: object, message: str
) -> None:
    payload = json.loads(SNAPSHOT.read_text())
    mutated = copy.deepcopy(payload)
    mutator(mutated)  # type: ignore[operator]
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps(mutated), encoding="utf-8")

    with pytest.raises(feasibility.WorkflowFeasibilityError, match=message):
        feasibility.review_workflow(plan=write_plan(tmp_path), snapshot_path=snapshot)


def test_cli_returns_two_for_invalid_contract(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    invalid = tmp_path / "invalid.md"
    invalid.write_text("# no contract\n", encoding="utf-8")
    assert feasibility.main(["--plan", str(invalid), "--snapshot", str(SNAPSHOT)]) == 2
    assert "missing 'Workflow Contract' heading" in capsys.readouterr().err
