from __future__ import annotations

import hashlib
import sys
import tomllib
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import render_codex_agents as renderer  # noqa: E402
import workflow_dispatch as W  # noqa: E402

RUN_SHA256 = "f" * 64


def profile_facts(execution_class: str) -> tuple[str, str, str]:
    content = (PLUGIN_ROOT / "agents" / f"{execution_class}.toml").read_bytes()
    payload = tomllib.loads(content.decode())
    return (
        hashlib.sha256(content).hexdigest(),
        payload["model"],
        payload["model_reasoning_effort"],
    )


def row(
    step_id: str,
    role_id: str = "security-reviewer",
    *,
    depends_on: str = "-",
    barrier: str = "-",
    independence: str = "preferred",
    execution_class: str = "review-high",
    vehicle: str = "auto",
    mutation: str = "none",
    required_evidence: str = "review-evidence",
    validator_required: bool | None = None,
    validator_disabled: bool | None = None,
) -> list[str]:
    if role_id == "root":
        return [
            step_id,
            depends_on,
            barrier,
            "root",
            "root",
            "n/a",
            "-",
            "root",
            mutation,
            required_evidence,
            "-",
            "-",
            "-",
            "-",
            "n/a",
            "n/a",
            "-",
        ]
    role = renderer.load_role_registry().role(role_id)
    digest, model, effort = profile_facts(execution_class)
    is_validator = role.output_schema != "review-evidence.v1"
    required_cell = (
        "true" if (validator_required is not False) else "false"
    ) if is_validator else "n/a"
    disabled_cell = (
        "true" if validator_disabled is True else "false"
    ) if is_validator else "n/a"
    return [
        step_id,
        depends_on,
        barrier,
        role_id,
        role.kind,
        independence,
        execution_class,
        vehicle,
        mutation,
        required_evidence,
        str(role.lens_sha256),
        digest,
        model,
        effort,
        required_cell,
        disabled_cell,
        (
            W._deterministic_contract_sha256(role)
            if role.kind == "deterministic-validator"
            else "-"
        ),
    ]


def plan(*rows: list[str]) -> str:
    header = "| " + " | ".join(W.HEADERS) + " |"
    separator = "| " + " | ".join("---" for _ in W.HEADERS) + " |"
    body = "\n".join("| " + " | ".join(values) + " |" for values in rows)
    return f"# Plan\n\n## Workflow Structure\n\n{header}\n{separator}\n{body}\n"


def state_payload(workflow: W.Workflow, **statuses: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "workflow_sha256": workflow.sha256,
        "workflow_run_sha256": RUN_SHA256,
        "steps": {
            step.step_id: {
                "status": statuses.get(step.step_id, "pending"),
                "cycle": 0 if statuses.get(step.step_id, "pending") == "pending" else 1,
                "result_ref": (
                    f"result:{step.step_id}"
                    if statuses.get(step.step_id) in {"passed", "needs-follow-up"}
                    else None
                ),
                "finding_refs": ["finding:p2"]
                if statuses.get(step.step_id) == "needs-follow-up"
                else [],
            }
            for step in workflow.steps
        },
    }


def scheduler_state(
    workflow: W.Workflow, *, cycle: int = 1, **statuses: str
) -> dict[str, W.StepState]:
    values = W._default_state(workflow)
    for step_id, status in statuses.items():
        values[step_id] = W.StepState(
            status=status,
            cycle=cycle,
            result_ref=f"normalized:scheduler-fixture:{step_id}",
            finding_refs=("finding-p2",) if status == "needs-follow-up" else (),
        )
    return values


def test_parallel_ready_set_and_barrier_join() -> None:
    workflow = W.parse_workflow_structure(
        plan(
            row("implement", "root", mutation="root-only", required_evidence="diff"),
            row("security", depends_on="implement", barrier="verify"),
            row(
                "tests",
                "scenario-tester",
                depends_on="implement",
                barrier="verify",
                execution_class="test-medium",
                mutation="none",
                required_evidence="test-evidence",
            ),
            row("integrate", "root", depends_on="security,tests", required_evidence="root-check"),
        )
    )

    first = W.emit_intents(
        workflow,
        W.load_dispatch_state(
            None, workflow, workflow_run_sha256=RUN_SHA256
        ),
        workflow_run_sha256=RUN_SHA256,
    )
    assert [item["step_id"] for item in first["intents"]] == ["implement"]
    assert first["intents"][0]["cycle"] == 1

    second_state = scheduler_state(workflow, implement="passed")
    second = W.emit_intents(
        workflow, second_state, workflow_run_sha256=RUN_SHA256
    )
    assert [item["step_id"] for item in second["intents"]] == ["security", "tests"]

    third_state = scheduler_state(
        workflow, implement="passed", security="passed", tests="passed"
    )
    assert [
        item["step_id"]
        for item in W.emit_intents(
            workflow, third_state, workflow_run_sha256=RUN_SHA256
        )["intents"]
    ] == [
        "integrate"
    ]


def test_selection_policy_requires_all_base_reviewers_and_a_required_validator() -> None:
    registry = renderer.load_role_registry()
    root_only = W.parse_workflow_structure(
        plan(row("implement", "root", mutation="root-only", required_evidence="diff"))
    )
    with pytest.raises(W.WorkflowDispatchError, match="required base reviewers"):
        W.validate_selection_policy(root_only, registry)

    reviewers_only = W.parse_workflow_structure(
        plan(
            row("architecture", "architecture-reviewer"),
            row("devils", "devils-advocate-reviewer"),
            row("security", "security-reviewer"),
        )
    )
    with pytest.raises(W.WorkflowDispatchError, match="required validator"):
        W.validate_selection_policy(reviewers_only, registry)

    full_review = W.parse_workflow_structure(
        plan(
            row("architecture", "architecture-reviewer"),
            row("devils", "devils-advocate-reviewer"),
            row("security", "security-reviewer"),
            row(
                "tests",
                "scenario-tester",
                execution_class="test-medium",
                required_evidence="tester-evidence",
                validator_required=True,
            ),
        )
    )
    selection = W.validate_selection_policy(full_review, registry)

    assert selection["review_mode"] == "full-review"
    assert selection["required_validator_step_ids"] == ["tests"]


def test_follow_up_preempts_new_work_and_is_selective() -> None:
    workflow = W.parse_workflow_structure(plan(row("security"), row("clarity", "clarity-reviewer")))
    state = scheduler_state(workflow, security="needs-follow-up")

    payload = W.emit_intents(workflow, state, workflow_run_sha256=RUN_SHA256)

    assert [(item["intent"], item["step_id"], item["cycle"]) for item in payload["intents"]] == [
        ("follow-up", "security", 2)
    ]
    assert payload["intents"][0]["previous_receipt_ref"] == state["security"].result_ref
    assert payload["intents"][0]["finding_refs"] == ["finding-p2"]


def test_follow_up_requires_interrupting_a_running_descendant() -> None:
    workflow = W.parse_workflow_structure(
        plan(
            row("security"),
            row("clarity", "clarity-reviewer", depends_on="security"),
        )
    )
    state = scheduler_state(workflow, security="needs-follow-up")
    state["clarity"] = W.StepState("running", 1, None, ())

    result = W.emit_intents(
        workflow,
        state,
        workflow_run_sha256=RUN_SHA256,
    )

    assert result["claim"] == "dispatch-state-update-required"
    assert result["intents"] == []
    assert result["invalidations"] == [
        {
            "step_id": "clarity",
            "from_status": "running",
            "to_status": "stale",
            "reason": "interrupt the running step before upstream remediation",
        }
    ]


def test_stale_step_emits_contiguous_receipt_supported_revalidation() -> None:
    workflow = W.parse_workflow_structure(
        plan(
            row("security"),
            row("integrate", "root", depends_on="security"),
        )
    )
    state = scheduler_state(
        workflow,
        cycle=3,
        security="passed",
        integrate="stale",
    )
    state["integrate"] = W.StepState(
        status="stale",
        cycle=1,
        result_ref="normalized:scheduler-fixture:integrate",
        finding_refs=(),
    )

    payload = W.emit_intents(workflow, state, workflow_run_sha256=RUN_SHA256)

    assert payload["intents"] == [
        {
            "intent": "revalidate",
            "cycle": 2,
            "previous_receipt_ref": "normalized:scheduler-fixture:integrate",
            "finding_refs": [],
            **workflow.step("integrate").to_jsonable(),
        }
    ]


def test_cycle_cap_escalates_and_never_emits_run() -> None:
    workflow = W.parse_workflow_structure(plan(row("security")))
    state = scheduler_state(workflow, cycle=3, security="needs-follow-up")

    result = W.emit_intents(workflow, state, workflow_run_sha256=RUN_SHA256)

    assert result["intents"] == []
    assert result["escalations"] == [
        {"step_id": "security", "reason": "three-cycle remediation cap reached"}
    ]
    assert result["complete"] is False


def test_required_independence_rejects_inline() -> None:
    with pytest.raises(W.WorkflowDispatchError, match="required independence"):
        W.parse_workflow_structure(
            plan(row("security", independence="required", vehicle="inline"))
        )


def test_stale_role_or_profile_digest_fails_closed() -> None:
    values = row("security")
    values[10] = "0" * 64
    with pytest.raises(W.WorkflowDispatchError, match="role lens"):
        W.parse_workflow_structure(plan(values))


@pytest.mark.parametrize("status", ["passed", "needs-follow-up"])
def test_completed_state_requires_result_evidence(status: str) -> None:
    workflow = W.parse_workflow_structure(plan(row("security")))
    value = state_payload(workflow, security=status)
    value["steps"]["security"]["result_ref"] = None  # type: ignore[index]

    with pytest.raises(W.WorkflowDispatchError, match="requires a result"):
        W.load_dispatch_state(value, workflow, workflow_run_sha256=RUN_SHA256)


def test_disabled_validator_skipped_result_advances_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow = W.parse_workflow_structure(
        plan(
            row(
                "tests",
                "scenario-tester",
                validator_required=False,
                validator_disabled=True,
            )
        )
    )
    value = state_payload(workflow, tests="passed")
    import dispatch_receipt as receipts

    monkeypatch.setattr(
        receipts,
        "validate_normalized_receipt",
        lambda _plugin_data, _reference, _workflow: (
            {
                "step_id": "tests",
                "attempt": 1,
                "workflow_run_sha256": RUN_SHA256,
            },
            {"evidence": {"gate_status": "skipped-by-config"}},
        ),
    )

    state = W.load_dispatch_state(
        value,
        workflow,
        workflow_run_sha256=RUN_SHA256,
        plugin_data=tmp_path,
    )

    assert state["tests"].status == "passed"
    assert W.emit_intents(
        workflow,
        state,
        workflow_run_sha256=RUN_SHA256,
    )["complete"] is True


def test_cycle_booleans_and_zero_attempt_completed_state_are_rejected() -> None:
    workflow = W.parse_workflow_structure(plan(row("security")))
    value = state_payload(workflow, security="passed")
    value["steps"]["security"]["cycle"] = True  # type: ignore[index]
    with pytest.raises(W.WorkflowDispatchError, match="invalid"):
        W.load_dispatch_state(value, workflow, workflow_run_sha256=RUN_SHA256)

    value["steps"]["security"]["cycle"] = 0  # type: ignore[index]
    with pytest.raises(W.WorkflowDispatchError, match="requires an attempt"):
        W.load_dispatch_state(value, workflow, workflow_run_sha256=RUN_SHA256)

    values = row("security")
    values[11] = "0" * 64
    with pytest.raises(W.WorkflowDispatchError, match="profile"):
        W.parse_workflow_structure(plan(values))


@pytest.mark.parametrize(
    "rows,match",
    [
        ((row("same"), row("same")), "duplicate"),
        ((row("one", depends_on="missing"),), "invalid dependencies"),
        ((row("one", depends_on="two"), row("two", depends_on="one")), "cycle"),
        (
            (
                row("one", barrier="join"),
                row("two", barrier="join"),
                row("after", "root", depends_on="one"),
            ),
            "every member",
        ),
    ],
)
def test_invalid_graphs_fail(rows: tuple[list[str], ...], match: str) -> None:
    with pytest.raises(W.WorkflowDispatchError, match=match):
        W.parse_workflow_structure(plan(*rows))


def test_dispatcher_contains_no_launch_or_collaboration_primitive() -> None:
    source = (SCRIPTS / "workflow_dispatch.py").read_text()
    assert "subprocess" not in source
    assert "spawn_agent" not in source
    assert "followup_task" not in source
    assert "collaboration." not in source


def test_synthetic_deterministic_role_emits_pinned_model_free_contract() -> None:
    base = renderer.load_role_registry()
    role = renderer.RoleSpec(
        role_id="schema-validator",
        kind="deterministic-validator",
        category="tester",
        spec_version=1,
        description="Validate schema deterministically",
        selection_mode="context",
        signals=(),
        minimum_independence=None,
        default_class=None,
        allowed_classes=(),
        workspace_cap="read-only",
        external_cap="none",
        output_schema="tester-evidence.v1",
        source_behavior_sha256="1" * 64,
        lens_path=None,
        lens_sha256=None,
        command=("python3", "tools/check_schema.py"),
        command_implementation_path="tools/check_schema.py",
        command_implementation_sha256="2" * 64,
        command_timeout_seconds=30,
        command_output_limit_bytes=65536,
        evidence_schema_path="schemas/tester-evidence.json",
        evidence_schema_sha256="3" * 64,
    )
    registry = renderer.RoleRegistry(
        path=base.path,
        sha256=base.sha256,
        schema_version=base.schema_version,
        role_spec_version=base.role_spec_version,
        source_behavior_policy=base.source_behavior_policy,
        review_policy=base.review_policy,
        evidence_schemas=base.evidence_schemas,
        nested_type_contracts=base.nested_type_contracts,
        roles=(role,),
    )
    values = [
        "schema-check",
        "-",
        "-",
        "schema-validator",
        "deterministic-validator",
        "n/a",
        "-",
        "deterministic-tool",
        "none",
        "tester-evidence",
        "-",
        "-",
        "-",
        "-",
        "true",
        "false",
        W._deterministic_contract_sha256(role),
    ]

    workflow = W.parse_workflow_structure(plan(values), registry=registry)
    step = workflow.step("schema-check")

    assert step.command == role.command
    assert step.command_implementation_sha256 == role.command_implementation_sha256
    assert step.evidence_schema_sha256 == role.evidence_schema_sha256
    assert step.execution_class is None
    assert step.expected_model is None

    values[8] = "root-only"
    with pytest.raises(W.WorkflowDispatchError, match="mutation `none`"):
        W.parse_workflow_structure(plan(values), registry=registry)

    values[8] = "none"
    values[16] = "0" * 64
    with pytest.raises(W.WorkflowDispatchError, match="deterministic contract"):
        W.parse_workflow_structure(plan(values), registry=registry)

    values[16] = W._deterministic_contract_sha256(role)
    values[4] = "agent-lens"
    with pytest.raises(W.WorkflowDispatchError, match="role_kind is stale"):
        W.parse_workflow_structure(plan(values), registry=registry)
