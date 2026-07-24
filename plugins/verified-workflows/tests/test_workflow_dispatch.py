from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import workflow_dispatch as W  # noqa: E402


def assignment(
    assignment_id: str,
    *,
    depends: str = "-",
    parent: str = "root",
    role: str = "root implementer",
    profile: str = "root",
    model: str = "gpt-5.6-sol",
    effort: str = "max",
    context: str = "root",
    writes: str = "unit:U1",
    completion: str = "work completes",
    fallback: str = "none",
) -> list[str]:
    return [
        assignment_id,
        depends,
        parent,
        role,
        profile,
        model,
        effort,
        context,
        writes,
        completion,
        fallback,
    ]


def reviewer(*, depends: str = "implement", fallback: str = "review_max@terminal-failure") -> list[str]:
    return assignment(
        "review",
        depends=depends,
        parent="fresh-root:review",
        role="devils-advocate-reviewer",
        profile="review_high",
        effort="high",
        context="none",
        writes="none",
        completion="review score passes",
        fallback=fallback,
    )


def worker(
    worker_id: str = "test",
    *,
    depends: str = "implement",
    parent: str = "root",
    writes: str = "tests/test_feature.py",
    context: str = "turns:4",
    profile: str = "test_medium",
    model: str = "gpt-5.6-terra",
    effort: str = "medium",
    fallback: str = "work_high@terminal-failure",
    completion: str = "targeted tests pass",
) -> list[str]:
    return assignment(
        worker_id,
        depends=depends,
        parent=parent,
        role="scenario-tester",
        profile=profile,
        model=model,
        effort=effort,
        context=context,
        writes=writes,
        completion=completion,
        fallback=fallback,
    )


def check(
    check_id: str = "reviewer-assurance",
    *,
    owner: str = "root",
    after: str = "review",
    command: str = "reviewer result satisfies policy",
    blocking: str = "yes",
    failure: str = "stop",
) -> list[str]:
    return [check_id, owner, after, command, blocking, failure]


def external(action_id: str = "second-opinion", **overrides: str) -> list[str]:
    values = {
        "purpose": "advisory review",
        "provider": "claude",
        "model": "fable/xhigh",
        "egress": "docs/input.md",
        "context": "docs/input.md",
        "sensitivity": "internal",
        "cost": "metered",
        "writes-or-artifact": "artifact:review",
        "requiredness": "best-effort",
        "authority": "non-gating",
    }
    values.update(overrides)
    return [action_id, *(values[header] for header in W.EXTERNAL_ACTION_HEADERS[1:])]


def table(headers: tuple[str, ...], rows: list[list[str]]) -> str:
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *("| " + " | ".join(row) + " |" for row in rows),
        ]
    )


def plan(
    assignments: list[list[str]],
    *,
    checks: list[list[str]] | None = None,
    external_actions: list[list[str]] | None = None,
) -> str:
    external_text = (
        table(W.EXTERNAL_ACTION_HEADERS, external_actions)
        if external_actions
        else "`External actions: []` is the exact approved value."
    )
    return (
        "# Plan\n\n"
        "## Workflow Contract\n\n"
        + table(W.ASSIGNMENT_HEADERS, assignments)
        + "\n\n### Blocking Checks\n\n"
        + table(W.CHECK_HEADERS, checks or [check()])
        + "\n\n### External Actions\n\n"
        + external_text
        + "\n\n## Implementation Units\n"
    )


def compile_fixture(
    assignments: list[list[str]] | None = None,
    *,
    checks: list[list[str]] | None = None,
    external_actions: list[list[str]] | None = None,
    revision: str = "approved-revision",
) -> W.WorkflowContract:
    return W.compile_workflow_contract(
        plan(
            assignments or [assignment("implement"), reviewer(), worker()],
            checks=checks,
            external_actions=external_actions,
        ),
        plan_revision=revision,
    )


def test_valid_mixed_contract_compiles_to_root_owned_launch_specs() -> None:
    contract = compile_fixture(external_actions=[external()])

    assert contract.schema_version == 2
    assert len(contract.assignments) == 3
    assert len(contract.external_actions) == 1
    specs = {spec.assignment_id: spec for spec in contract.launch_specs}
    assert specs["implement"].agent_type is None
    assert specs["review"].agent_type == "review_high"
    assert specs["review"].fork_turns == "none"
    assert specs["test"].fork_turns == 4
    assert specs["test"].result_schema == "assignment-result.v1"
    assert specs["review"].reviewer_mandate_ids == (
        "assumption-validity",
        "edge-case-coverage",
        "failure-mode-analysis",
        "scope-creep-risk",
        "alternatives-considered",
    )
    assert specs["review"].registry_sha256 == contract.registry_sha256
    assert specs["review"].role_lens_sha256
    assert specs["review"].profile_sha256
    assert contract.authority_sha256
    assert contract.external_actions[0].authority == "non-gating"


def test_canonical_binding_ignores_row_and_unordered_list_order() -> None:
    first = compile_fixture(
        [assignment("implement"), worker(writes="tests/b.py,tests/a.py"), reviewer()],
        revision="same-revision",
    )
    second = compile_fixture(
        [reviewer(), worker(writes="tests/a.py,tests/b.py"), assignment("implement")],
        revision="same-revision",
    )

    assert first.contract_sha256 == second.contract_sha256
    assert first.approval_binding_sha256 == second.approval_binding_sha256


def test_material_edit_invalidates_approval_binding() -> None:
    approved = compile_fixture()
    changed_rows = [assignment("implement"), reviewer(), worker(completion="different result")]
    changed = compile_fixture(changed_rows)

    with pytest.raises(W.WorkflowDispatchError, match="approval binding is stale"):
        W.validate_approval_binding(
            changed,
            approved_plan_revision=approved.plan_revision,
            approved_contract_sha256=approved.contract_sha256,
            approved_binding_sha256=approved.approval_binding_sha256,
        )


def test_role_or_profile_authority_changes_invalidate_approval_binding(tmp_path: Path) -> None:
    approved = compile_fixture()
    changed_registry = tmp_path / "role-registry.yaml"
    changed_registry.write_bytes(W.renderer.DEFAULT_REGISTRY.read_bytes())
    changed_roles = tmp_path / "roles"
    changed_roles.mkdir()
    for source in W.renderer.DEFAULT_ROLES_DIR.iterdir():
        (changed_roles / source.name).write_bytes(source.read_bytes())
    target = changed_roles / "devils-advocate-reviewer.md"
    target.write_text(target.read_text().replace("Assumption Validity", "Assumption Soundness"))
    changed = W.compile_workflow_contract(
        plan([assignment("implement"), reviewer(), worker()]),
        plan_revision=approved.plan_revision,
        registry_path=changed_registry,
        roles_dir=changed_roles,
    )
    assert changed.contract_sha256 == approved.contract_sha256
    assert changed.authority_sha256 != approved.authority_sha256
    assert changed.approval_binding_sha256 != approved.approval_binding_sha256


def test_exact_approved_binding_passes() -> None:
    contract = compile_fixture()
    W.validate_approval_binding(
        contract,
        approved_plan_revision=contract.plan_revision,
        approved_contract_sha256=contract.contract_sha256,
        approved_binding_sha256=contract.approval_binding_sha256,
    )


def test_dependency_cycle_is_rejected() -> None:
    rows = [
        assignment("a", depends="b"),
        assignment("b", depends="a"),
        reviewer(depends="a"),
    ]
    with pytest.raises(W.WorkflowDispatchError, match="cycle"):
        compile_fixture(rows)


def test_duplicate_assignment_id_is_rejected() -> None:
    rows = [assignment("implement"), assignment("implement"), reviewer()]
    with pytest.raises(W.WorkflowDispatchError, match="duplicate assignment ids"):
        compile_fixture(rows)


def test_concurrent_overlapping_writes_are_rejected() -> None:
    rows = [
        assignment("implement"),
        worker("left", writes="src"),
        worker("right", writes="src/feature.py"),
        reviewer(),
    ]
    with pytest.raises(W.WorkflowDispatchError, match="overlap writes"):
        compile_fixture(rows)


def test_ordered_overlapping_writes_are_allowed() -> None:
    rows = [
        assignment("implement"),
        worker("left", writes="src"),
        worker("right", depends="left", writes="src/feature.py"),
        reviewer(depends="right"),
    ]
    assert compile_fixture(rows).contract_sha256


@pytest.mark.parametrize("context", ["root", "all", "turns:0", "turns:-1"])
def test_delegated_context_must_be_bounded_or_absent(context: str) -> None:
    with pytest.raises(W.WorkflowDispatchError, match="must be 'none' or turns"):
        compile_fixture([assignment("implement"), reviewer(), worker(context=context)])


def test_profile_model_effort_mismatch_is_rejected() -> None:
    rows = [assignment("implement"), reviewer(), worker(model="gpt-5.6-sol")]
    with pytest.raises(W.WorkflowDispatchError, match="requires model=gpt-5.6-terra"):
        compile_fixture(rows)


def test_child_ultra_is_rejected() -> None:
    rows = [
        assignment("implement"),
        reviewer(),
        worker(profile="review_high", model="gpt-5.6-sol", effort="ultra"),
    ]
    with pytest.raises(W.WorkflowDispatchError, match="cannot use profile|requires model"):
        compile_fixture(rows)


def test_widened_fallback_is_rejected() -> None:
    rows = [assignment("implement"), reviewer(), worker(fallback="review_max@ambiguity")]
    with pytest.raises(W.WorkflowDispatchError, match="widens role"):
        compile_fixture(rows)


def test_missing_independent_review_is_rejected() -> None:
    dependent_review = copy.deepcopy(reviewer())
    dependent_review[W.ASSIGNMENT_HEADERS.index("parent")] = "root"
    rows = [assignment("implement"), dependent_review, worker()]
    with pytest.raises(W.WorkflowDispatchError, match="fresh-root independent reviewer"):
        compile_fixture(rows)


def test_fresh_root_must_be_same_id_read_only_reviewer() -> None:
    bad_review = copy.deepcopy(reviewer())
    bad_review[W.ASSIGNMENT_HEADERS.index("parent")] = "fresh-root:someone-else"
    with pytest.raises(W.WorkflowDispatchError, match="same-id, read-only"):
        compile_fixture([assignment("implement"), bad_review, worker()])


def test_assignment_parent_must_be_declared_dependency() -> None:
    rows = [assignment("implement"), reviewer(), worker(parent="implement", depends="-")]
    with pytest.raises(W.WorkflowDispatchError, match="depend on its declared parent"):
        compile_fixture(rows)


def test_worker_git_mutation_is_rejected() -> None:
    rows = [assignment("implement"), reviewer(), worker(completion="git commit the change")]
    with pytest.raises(W.WorkflowDispatchError, match="may not own a Git mutation"):
        compile_fixture(rows)


def test_git_metadata_write_is_rejected() -> None:
    rows = [assignment("implement"), reviewer(), worker(writes=".git/config")]
    with pytest.raises(W.WorkflowDispatchError, match="Git metadata"):
        compile_fixture(rows)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"egress": "none"}, "egress must be explicit"),
        ({"authority": "gating"}, "authority must be non-gating"),
        ({"writes-or-artifact": "none"}, "must name an artifact"),
        ({"requiredness": "mandatory"}, "requiredness must be best-effort or required"),
    ],
)
def test_external_action_contract_is_closed(overrides: dict[str, str], message: str) -> None:
    with pytest.raises(W.WorkflowDispatchError, match=message):
        compile_fixture(external_actions=[external(**overrides)])


def test_table_columns_are_exact() -> None:
    text = plan([assignment("implement"), reviewer(), worker()]).replace(
        "| id | depends |", "| id | unexpected | depends |", 1
    )
    with pytest.raises(W.WorkflowDispatchError, match="columns must be exactly"):
        W.compile_workflow_contract(text, plan_revision="revision")


def test_repository_plan_compiles() -> None:
    repo_root = Path(__file__).parents[3]
    contract = W.compile_plan(
        repo_root / "docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md",
        plan_revision="reviewed-plan",
    )
    assert len(contract.assignments) == 12
    assert len(contract.checks) == 10
    assert contract.external_actions == ()


def test_cli_emits_compiled_contract(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "plan.md"
    path.write_text(plan([assignment("implement"), reviewer(), worker()]), encoding="utf-8")

    assert W.main(["--plan", str(path), "--plan-revision", "revision"]) == 0
    assert '"approval_binding_sha256"' in capsys.readouterr().out
