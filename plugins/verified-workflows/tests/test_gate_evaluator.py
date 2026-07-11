from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
TESTS = Path(__file__).parent
for directory in (SCRIPTS, TESTS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import gate_evaluator as G  # noqa: E402
import test_dispatch_receipt as receipt_fixtures  # noqa: E402
import test_workflow_dispatch as workflow_fixtures  # noqa: E402
import workflow_dispatch as W  # noqa: E402

_REAL_EVALUATE_GATE = G.evaluate_gate


def evaluate_unit_gate(*args: object, **kwargs: object) -> dict[str, object]:
    """Exercise a deliberately partial workflow fixture without production selection."""

    kwargs.setdefault("enforce_selection_policy", False)
    return _REAL_EVALUATE_GATE(*args, **kwargs)  # type: ignore[arg-type]


def payload(
    workflow: W.Workflow,
    reference: str,
    data: Path,
    *,
    cycle: object = 1,
    subject_ref: str | None = None,
) -> dict[str, object]:
    if subject_ref is None:
        receipt, _content = receipt_fixtures.R.load_normalized_receipt(data, reference)
        subject_ref = receipt["output_subject_ref"]
    return {
        "schema_version": 1,
        "workflow_sha256": workflow.sha256,
        "cycle": cycle,
        "subject_ref": subject_ref,
        "steps": [{"step_id": "security", "receipt_ref": reference}],
        "advisory": [],
    }


def inline_security_receipt(
    data: Path,
    workflow: W.Workflow,
    chain: dict[str, str],
    *,
    attempt: int = 1,
) -> dict[str, object]:
    return receipt_fixtures.R.build_inline_receipt(
        data,
        workflow,
        "security",
        attempt=attempt,
        task_id="security-review",
        **chain,
    )


def persisted_inline_receipt(
    tmp_path: Path,
    *,
    findings: list[dict[str, object]] | None = None,
    overall: float = 9.5,
    attempt: int = 1,
    subject_path: str = "src/example.py",
) -> tuple[Path, W.Workflow, str, dict[str, object]]:
    data = receipt_fixtures.plugin_data(tmp_path)
    workflow = receipt_fixtures.workflow()
    reference: str | None = None
    receipt: dict[str, object] | None = None
    for current_attempt in range(1, attempt + 1):
        chain = receipt_fixtures.protected_chain(
            data,
            workflow,
            vehicle="verified-workflow-inline",
            findings=findings,
            overall=overall,
            attempt=current_attempt,
            subject_path=subject_path,
            previous_receipt_ref=reference,
        )
        receipt = inline_security_receipt(
            data,
            workflow,
            chain,
            attempt=current_attempt,
        )
        reference = receipt_fixtures.R.persist_normalized(data, receipt)
        receipt_fixtures.R.validate_normalized_receipt(data, reference, workflow)
    assert reference is not None and receipt is not None
    return data, workflow, reference, receipt


def evaluated(
    tmp_path: Path,
    *,
    findings: list[dict[str, object]] | None = None,
    overall: float = 9.5,
    attempt: int = 1,
    subject_path: str = "src/example.py",
) -> tuple[dict[str, object], Path, W.Workflow, str]:
    data, workflow, reference, _receipt = persisted_inline_receipt(
        tmp_path,
        findings=findings,
        overall=overall,
        attempt=attempt,
        subject_path=subject_path,
    )
    result = evaluate_unit_gate(
        payload(workflow, reference, data, cycle=attempt),
        workflow=workflow,
        plugin_data=data,
        workspace_root=data.parent / "workspace",
    )
    return result, data, workflow, reference


def root_receipt(
    data: Path,
    workflow: W.Workflow,
    step_id: str,
    subject_ref: str,
    *,
    minute: int,
    findings: list[dict[str, object]] | None = None,
    evidence_id: str = "root-proof",
    verified_at: str | None = None,
) -> str:
    prefix = f"2026-07-10T22:{minute:02d}:"
    before_ref = receipt_fixtures.workspace_snapshot(data, prefix + "00.000000Z")
    intent_ref = receipt_fixtures.R.create_intent_record(
        data,
        workflow,
        step_id,
        attempt=1,
        task_id=step_id,
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_ref,
        created_at=prefix + "00.100000Z",
        nonce=hashlib.sha256(step_id.encode()).hexdigest()[:32],
    )
    result_ref = receipt_fixtures.R.create_result_record(
        data,
        workflow,
        step_id,
        attempt=1,
        task_id=step_id,
        intent_ref=intent_ref,
        output_subject_ref=subject_ref,
        mutation_audit_ref=None,
        workspace_root=None,
        vehicle="root",
        child_id=None,
        provided_evidence=[evidence_id],
        evidence={
            "evidence_refs": {evidence_id: subject_ref},
            "findings": findings or [],
        },
        execution={"kind": "root"},
        recorded_at=prefix + "01.000000Z",
    )
    verification_ref = receipt_fixtures.R.create_root_verification_record(
        data,
        result_ref=result_ref,
        verifier_session_id="Session-1",
        verifier_turn_id=f"{step_id}-Turn",
        resolution_refs=[],
        recorded_at=verified_at or prefix + "02.000000Z",
    )
    receipt = receipt_fixtures.R.build_root_receipt(
        data,
        workflow,
        step_id,
        attempt=1,
        task_id=step_id,
        intent_ref=intent_ref,
        result_ref=result_ref,
        root_verification_ref=verification_ref,
    )
    return receipt_fixtures.R.persist_normalized(data, receipt)


def test_clean_protected_evidence_passes(tmp_path: Path) -> None:
    result, _data, _workflow, _reference = evaluated(tmp_path)

    assert result["verdict"] == "pass"
    assert result["numeric_scores_have_gate_authority"] is False


def test_root_accountability_child_receipt_cannot_satisfy_gate(tmp_path: Path) -> None:
    data, workflow, reference, _receipt = (
        receipt_fixtures.persisted_subagent_receipt(tmp_path)
    )

    result = evaluate_unit_gate(
        payload(workflow, reference, data),
        workflow=workflow,
        plugin_data=data,
        workspace_root=data.parent / "workspace",
    )

    assert result["verdict"] == "block"
    assert {
        "step_id": "security",
        "reason": (
            "native child evidence is root-accountability only; "
            "host-issued attestation is unavailable"
        ),
    } in result["hard_blockers"]


def test_gate_enforces_full_review_selection_by_default(tmp_path: Path) -> None:
    data = receipt_fixtures.plugin_data(tmp_path)
    workflow = receipt_fixtures.workflow()

    with pytest.raises(W.WorkflowDispatchError, match="required base reviewers"):
        _REAL_EVALUATE_GATE(
            {},
            workflow=workflow,
            plugin_data=data,
            workspace_root=receipt_fixtures.workspace_repo(data),
        )


def test_root_owned_parallel_barrier_dag_passes_end_to_end(tmp_path: Path) -> None:
    workflow = W.parse_workflow_structure(
        workflow_fixtures.plan(
            workflow_fixtures.row(
                "implement",
                "root",
                mutation="root-only",
                required_evidence="diff",
            ),
            workflow_fixtures.row(
                "security",
                depends_on="implement",
                barrier="verify",
            ),
            workflow_fixtures.row(
                "tests",
                "scenario-tester",
                depends_on="implement",
                barrier="verify",
                execution_class="test-medium",
                required_evidence="test-evidence",
            ),
            workflow_fixtures.row(
                "integrate",
                "root",
                depends_on="security,tests",
                mutation="root-only",
                required_evidence="root-check",
            ),
        )
    )
    data = receipt_fixtures.plugin_data(tmp_path)
    workspace = data.parent / "workspace"
    initial_subject_ref, _initial_digest = receipt_fixtures.protected_subject(
        data,
        active_workflow=workflow,
    )
    initial_snapshot_ref = receipt_fixtures.workspace_snapshot(
        data, "2026-07-10T21:59:59Z"
    )
    implement_intent_ref = receipt_fixtures.R.create_intent_record(
        data,
        workflow,
        "implement",
        attempt=1,
        task_id="implement",
        subject_ref=initial_subject_ref,
        workspace_snapshot_ref=initial_snapshot_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="a" * 32,
    )
    (workspace / "src" / "example.py").write_text("implemented\n")
    implemented_subject_ref = receipt_fixtures.R.create_subject_record(
        data,
        workspace_root=workspace,
        subject_paths=["src/example.py"],
        workflow_run_ref=receipt_fixtures.R._load_subject_record(
            data, initial_subject_ref
        )[0]["workflow_run_ref"],
        parent_refs=[initial_subject_ref],
        created_at="2026-07-10T22:00:01Z",
    )
    implemented_subject, _subject_bytes = receipt_fixtures.R._load_subject_record(
        data, implemented_subject_ref
    )
    implement_result_ref = receipt_fixtures.R.create_result_record(
        data,
        workflow,
        "implement",
        attempt=1,
        task_id="implement",
        intent_ref=implement_intent_ref,
        output_subject_ref=implemented_subject_ref,
        mutation_audit_ref=None,
        workspace_root=None,
        vehicle="root",
        child_id=None,
        provided_evidence=["diff"],
        evidence={
            "evidence_refs": {"diff": implemented_subject_ref},
            "findings": [],
        },
        execution={"kind": "root"},
        recorded_at="2026-07-10T22:00:02Z",
    )
    implement_verification_ref = receipt_fixtures.R.create_root_verification_record(
        data,
        result_ref=implement_result_ref,
        verifier_session_id="Session-1",
        verifier_turn_id="Implement-Turn",
        resolution_refs=[],
        recorded_at="2026-07-10T22:00:03Z",
    )
    implement_receipt = receipt_fixtures.R.build_root_receipt(
        data,
        workflow,
        "implement",
        attempt=1,
        task_id="implement",
        intent_ref=implement_intent_ref,
        result_ref=implement_result_ref,
        root_verification_ref=implement_verification_ref,
    )
    implement_ref = receipt_fixtures.R.persist_normalized(data, implement_receipt)

    def inline_receipt(step_id: str, *, tester: bool, offset: int) -> str:
        step = workflow.step(step_id)
        before_ref = receipt_fixtures.workspace_snapshot(
            data, f"2026-07-10T22:00:0{offset}Z"
        )
        intent_ref = receipt_fixtures.R.create_intent_record(
            data,
            workflow,
            step_id,
            attempt=1,
            task_id=step_id,
            subject_ref=implemented_subject_ref,
            workspace_snapshot_ref=before_ref,
            created_at=f"2026-07-10T22:00:0{offset}.100000Z",
            nonce=("b" if step_id == "security" else "c") * 32,
        )
        after_ref = receipt_fixtures.workspace_snapshot(
            data, f"2026-07-10T22:00:0{offset}.200000Z"
        )
        audit_ref = receipt_fixtures.R.create_mutation_audit_record(
            data,
            before_ref=before_ref,
            after_ref=after_ref,
            recorded_at=f"2026-07-10T22:00:0{offset}.300000Z",
        )
        if tester:
            output_dir = data.parent / "gate-command-output"
            output_dir.mkdir(exist_ok=True)
            stdout = output_dir / f"{step_id}-stdout.txt"
            stderr = output_dir / f"{step_id}-stderr.txt"
            stdout.write_text("completed\n")
            stderr.write_text("")
            stdout.chmod(0o600)
            stderr.chmod(0o600)
            command_ref = receipt_fixtures.R.create_command_output_record(
                data,
                workflow,
                step_id,
                attempt=1,
                task_id=step_id,
                intent_ref=intent_ref,
                stdout_file=stdout,
                stderr_file=stderr,
                exit_code=0,
                output_limit_bytes=64 * 1024,
                argv=["pytest", "-q"],
                recorded_at=f"2026-07-10T22:00:0{offset}.150000Z",
            )
            evidence = {
                "role_id": step.role_id,
                "role_digest": step.role_lens_sha256,
                "target": "workflow",
                "declared_argv": ["pytest", "-q"],
                "expected": "pass",
                "actual": "pass",
                "exit_code": 0,
                "evidence_refs": [command_ref],
                "cases": [
                    {
                        "case_id": "workflow-suite",
                        "status": "pass",
                        "evidence_ref": command_ref,
                    }
                ],
                "gate_status": "pass",
            }
        else:
            evidence = receipt_fixtures.review_evidence(
                step,
                input_digest=implemented_subject["content_sha256"],
            )
        result_ref = receipt_fixtures.R.create_result_record(
            data,
            workflow,
            step_id,
            attempt=1,
            task_id=step_id,
            intent_ref=intent_ref,
            output_subject_ref=implemented_subject_ref,
            mutation_audit_ref=audit_ref,
            workspace_root=workspace,
            vehicle="verified-workflow-inline",
            child_id=None,
            provided_evidence=["test-evidence" if tester else "review-evidence"],
            evidence=evidence,
            execution={
                "kind": "agent-lens",
                "execution_class": step.execution_class,
                "profile_sha256": step.profile_sha256,
            },
            recorded_at=f"2026-07-10T22:00:0{offset}.500000Z",
        )
        verification_ref = receipt_fixtures.R.create_root_verification_record(
            data,
            result_ref=result_ref,
            verifier_session_id="Session-1",
            verifier_turn_id=f"{step_id}-Turn",
            resolution_refs=[],
            recorded_at=f"2026-07-10T22:00:0{offset}.600000Z",
        )
        receipt = receipt_fixtures.R.build_inline_receipt(
            data,
            workflow,
            step_id,
            attempt=1,
            task_id=step_id,
            intent_ref=intent_ref,
            result_ref=result_ref,
            root_verification_ref=verification_ref,
        )
        return receipt_fixtures.R.persist_normalized(data, receipt)

    security_ref = inline_receipt("security", tester=False, offset=4)
    tests_ref = inline_receipt("tests", tester=True, offset=5)
    integrate_snapshot_ref = receipt_fixtures.workspace_snapshot(
        data, "2026-07-10T22:00:06.700000Z"
    )
    integrate_intent_ref = receipt_fixtures.R.create_intent_record(
        data,
        workflow,
        "integrate",
        attempt=1,
        task_id="integrate",
        subject_ref=implemented_subject_ref,
        workspace_snapshot_ref=integrate_snapshot_ref,
        created_at="2026-07-10T22:00:07Z",
        nonce="d" * 32,
    )
    integrate_result_ref = receipt_fixtures.R.create_result_record(
        data,
        workflow,
        "integrate",
        attempt=1,
        task_id="integrate",
        intent_ref=integrate_intent_ref,
        output_subject_ref=implemented_subject_ref,
        mutation_audit_ref=None,
        workspace_root=None,
        vehicle="root",
        child_id=None,
        provided_evidence=["root-check"],
        evidence={
            "evidence_refs": {"root-check": implemented_subject_ref},
            "findings": [],
        },
        execution={"kind": "root"},
        recorded_at="2026-07-10T22:00:08Z",
    )
    integrate_verification_ref = receipt_fixtures.R.create_root_verification_record(
        data,
        result_ref=integrate_result_ref,
        verifier_session_id="Session-1",
        verifier_turn_id="Integrate-Turn",
        resolution_refs=[],
        recorded_at="2026-07-10T22:00:09Z",
    )
    integrate_receipt = receipt_fixtures.R.build_root_receipt(
        data,
        workflow,
        "integrate",
        attempt=1,
        task_id="integrate",
        intent_ref=integrate_intent_ref,
        result_ref=integrate_result_ref,
        root_verification_ref=integrate_verification_ref,
    )
    integrate_ref = receipt_fixtures.R.persist_normalized(data, integrate_receipt)
    value = {
        "schema_version": 1,
        "workflow_sha256": workflow.sha256,
        "cycle": 1,
        "subject_ref": implemented_subject_ref,
        "steps": [
            {"step_id": "implement", "receipt_ref": implement_ref},
            {"step_id": "security", "receipt_ref": security_ref},
            {"step_id": "tests", "receipt_ref": tests_ref},
            {"step_id": "integrate", "receipt_ref": integrate_ref},
        ],
        "advisory": [],
    }

    result = evaluate_unit_gate(
        value,
        workflow=workflow,
        plugin_data=data,
        workspace_root=workspace,
    )

    assert result["verdict"] == "pass"
    assert result["subject_ref"] == implemented_subject_ref


def test_two_hop_dependency_ancestry_passes(tmp_path: Path) -> None:
    workflow = W.parse_workflow_structure(
        workflow_fixtures.plan(
            workflow_fixtures.row(
                "prepare",
                "root",
                mutation="root-only",
                required_evidence="root-proof",
            ),
            workflow_fixtures.row(
                "verify",
                "root",
                depends_on="prepare",
                mutation="root-only",
                required_evidence="root-proof",
            ),
            workflow_fixtures.row(
                "integrate",
                "root",
                depends_on="verify",
                mutation="root-only",
                required_evidence="root-proof",
            ),
        )
    )
    data = receipt_fixtures.plugin_data(tmp_path)
    subject_ref, _subject_digest = receipt_fixtures.protected_subject(
        data,
        active_workflow=workflow,
    )
    references = {
        "prepare": root_receipt(data, workflow, "prepare", subject_ref, minute=0),
        "verify": root_receipt(data, workflow, "verify", subject_ref, minute=10),
        "integrate": root_receipt(data, workflow, "integrate", subject_ref, minute=20),
    }
    value = {
        "schema_version": 1,
        "workflow_sha256": workflow.sha256,
        "cycle": 1,
        "subject_ref": subject_ref,
        "steps": [
            {"step_id": step_id, "receipt_ref": references[step_id]}
            for step_id in ("prepare", "verify", "integrate")
        ],
        "advisory": [],
    }

    result = evaluate_unit_gate(
        value,
        workflow=workflow,
        plugin_data=data,
        workspace_root=data.parent / "workspace",
    )

    assert result["verdict"] == "pass"


def test_maximum_step_and_evidence_ids_produce_a_loadable_receipt(
    tmp_path: Path,
) -> None:
    step_id = "s" * 64
    evidence_id = "e" * 128
    workflow = W.parse_workflow_structure(
        workflow_fixtures.plan(
            workflow_fixtures.row(
                step_id,
                "root",
                mutation="root-only",
                required_evidence=evidence_id,
            )
        )
    )
    data = receipt_fixtures.plugin_data(tmp_path)
    subject_ref, _subject_digest = receipt_fixtures.protected_subject(
        data,
        active_workflow=workflow,
    )
    reference = root_receipt(
        data,
        workflow,
        step_id,
        subject_ref,
        minute=0,
        evidence_id=evidence_id,
    )
    value = {
        "schema_version": 1,
        "workflow_sha256": workflow.sha256,
        "cycle": 1,
        "subject_ref": subject_ref,
        "steps": [{"step_id": step_id, "receipt_ref": reference}],
        "advisory": [],
    }

    assert receipt_fixtures.R.load_normalized_receipt(data, reference)[0][
        "step_id"
    ] == step_id
    assert evaluate_unit_gate(
        value,
        workflow=workflow,
        plugin_data=data,
        workspace_root=data.parent / "workspace",
    )["verdict"] == "pass"


def test_future_root_verification_is_rejected_at_the_gate(tmp_path: Path) -> None:
    workflow = W.parse_workflow_structure(
        workflow_fixtures.plan(
            workflow_fixtures.row(
                "integrate",
                "root",
                mutation="root-only",
                required_evidence="root-proof",
            )
        )
    )
    data = receipt_fixtures.plugin_data(tmp_path)
    subject_ref, _subject_digest = receipt_fixtures.protected_subject(
        data,
        active_workflow=workflow,
    )
    reference = root_receipt(
        data,
        workflow,
        "integrate",
        subject_ref,
        minute=0,
        verified_at="2099-01-01T00:00:00Z",
    )
    value = {
        "schema_version": 1,
        "workflow_sha256": workflow.sha256,
        "cycle": 1,
        "subject_ref": subject_ref,
        "steps": [{"step_id": "integrate", "receipt_ref": reference}],
        "advisory": [],
    }

    with pytest.raises(G.GateEvaluationError, match="in the future"):
        evaluate_unit_gate(
            value,
            workflow=workflow,
            plugin_data=data,
            workspace_root=data.parent / "workspace",
        )


def test_remediation_escalation_uses_the_finding_steps_attempt(tmp_path: Path) -> None:
    workflow = W.parse_workflow_structure(
        workflow_fixtures.plan(
            workflow_fixtures.row("security"),
            workflow_fixtures.row(
                "root-check",
                "root",
                mutation="root-only",
                required_evidence="root-proof",
            ),
        )
    )
    data = receipt_fixtures.plugin_data(tmp_path)
    security_ref: str | None = None
    security_receipt: dict[str, object] | None = None
    for attempt in range(1, 4):
        chain = receipt_fixtures.protected_chain(
            data,
            workflow,
            vehicle="verified-workflow-inline",
            attempt=attempt,
            previous_receipt_ref=security_ref,
        )
        security_receipt = inline_security_receipt(
            data,
            workflow,
            chain,
            attempt=attempt,
        )
        security_ref = receipt_fixtures.R.persist_normalized(data, security_receipt)
    assert security_ref is not None and security_receipt is not None
    subject_ref = str(security_receipt["output_subject_ref"])
    root_ref = root_receipt(
        data,
        workflow,
        "root-check",
        subject_ref,
        minute=30,
        findings=[receipt_fixtures.finding("P2")],
    )
    value = {
        "schema_version": 1,
        "workflow_sha256": workflow.sha256,
        "cycle": 3,
        "subject_ref": subject_ref,
        "steps": [
            {"step_id": "security", "receipt_ref": security_ref},
            {"step_id": "root-check", "receipt_ref": root_ref},
        ],
        "advisory": [],
    }

    result = evaluate_unit_gate(
        value,
        workflow=workflow,
        plugin_data=data,
        workspace_root=data.parent / "workspace",
    )

    assert result["verdict"] == "block"
    assert result["remediation"] == [
        {
            "step_id": "root-check",
            "reason": "unresolved P2 correctness finding finding-p2",
        }
    ]


def test_fabricated_reference_and_omitted_steps_fail_closed(tmp_path: Path) -> None:
    data = receipt_fixtures.plugin_data(tmp_path)
    workflow = receipt_fixtures.workflow()
    fake = (
        "normalized:"
        + workflow.sha256
        + ":"
        + "b" * 64
        + ":security:1:"
        + "a" * 64
    )
    with pytest.raises(G.GateEvaluationError, match="receipt is invalid"):
        evaluate_unit_gate(
            payload(
                workflow,
                fake,
                data,
                subject_ref=receipt_fixtures.protected_subject(data)[0],
            ),
            workflow=workflow,
            plugin_data=data,
            workspace_root=data.parent / "workspace",
        )

    two_steps = W.parse_workflow_structure(
        workflow_fixtures.plan(
            workflow_fixtures.row("security"),
            workflow_fixtures.row("clarity", "clarity-reviewer"),
        )
    )
    partial = payload(
        two_steps,
        fake,
        data,
        subject_ref=receipt_fixtures.protected_subject(
            data, active_workflow=two_steps
        )[0],
    )
    partial["workflow_sha256"] = two_steps.sha256
    with pytest.raises(G.GateEvaluationError, match="every workflow step"):
        evaluate_unit_gate(
            partial,
            workflow=two_steps,
            plugin_data=data,
            workspace_root=data.parent / "workspace",
        )


def test_high_score_cannot_override_p1_or_security(tmp_path: Path) -> None:
    findings = [
        receipt_fixtures.finding("P1"),
        {
            **receipt_fixtures.finding("P3"),
            "finding_id": "finding-security",
            "category": "security",
        },
    ]
    result, _data, _workflow, _reference = evaluated(
        tmp_path, findings=findings, overall=10.0
    )

    assert result["verdict"] == "block"
    assert len(result["hard_blockers"]) == 2


def test_resolution_cannot_suppress_current_finding_before_revalidation(
    tmp_path: Path,
) -> None:
    data = receipt_fixtures.plugin_data(tmp_path)
    workflow = receipt_fixtures.workflow()
    unresolved = receipt_fixtures.finding("P1")
    chain = receipt_fixtures.protected_chain(
        data,
        workflow,
        vehicle="verified-workflow-inline",
        findings=[unresolved],
    )
    result, _result_bytes = receipt_fixtures.R.load_protected_record(
        data, chain["result_ref"], "role-result"
    )
    original_subject_ref = result["output_subject_ref"]
    original_subject, _subject_bytes = receipt_fixtures.R._load_subject_record(
        data, original_subject_ref
    )
    subject_path = original_subject["paths"][0]
    target = data.parent / "workspace" / subject_path
    original_content = target.read_text()
    target.write_text("candidate remediation\n")
    resolved_subject_ref, _resolved_digest = receipt_fixtures.protected_subject(
        data,
        subject_path,
        parent_refs=[original_subject_ref],
        created_at="2026-07-10T22:00:03.250000Z",
    )
    resolution_ref = receipt_fixtures.R.create_resolution_record(
        data,
        result_ref=chain["result_ref"],
        finding_id=str(unresolved["finding_id"]),
        resolved_subject_ref=resolved_subject_ref,
        evidence_refs=[resolved_subject_ref],
        recorded_at="2026-07-10T22:00:03.500000Z",
    )
    chain["root_verification_ref"] = (
        receipt_fixtures.R.create_root_verification_record(
            data,
            result_ref=chain["result_ref"],
            verifier_session_id="Session-1",
            verifier_turn_id="Root-Turn-1",
            resolution_refs=[resolution_ref],
            recorded_at="2026-07-10T22:00:04.000000Z",
        )
    )
    target.write_text(original_content)
    receipt = inline_security_receipt(data, workflow, chain)
    reference = receipt_fixtures.R.persist_normalized(data, receipt)

    result = evaluate_unit_gate(
        payload(workflow, reference, data),
        workflow=workflow,
        plugin_data=data,
        workspace_root=data.parent / "workspace",
    )

    assert result["verdict"] == "block"
    assert result["hard_blockers"] == [
        {
            "step_id": "security",
            "reason": "unresolved P1 correctness finding finding-p1",
        }
    ]


def _resolved_follow_up(
    tmp_path: Path,
    *,
    resolution_recorded_at: str = "2026-07-10T22:00:03.500000Z",
) -> tuple[dict[str, object], Path, W.Workflow, str]:
    data = receipt_fixtures.plugin_data(tmp_path)
    workflow = receipt_fixtures.workflow()
    unresolved = receipt_fixtures.finding("P2")
    first_chain = receipt_fixtures.protected_chain(
        data,
        workflow,
        vehicle="verified-workflow-inline",
        findings=[unresolved],
    )
    first_result, _first_result_bytes = receipt_fixtures.R.load_protected_record(
        data,
        first_chain["result_ref"],
        "role-result",
    )
    finding_subject_ref = first_result["output_subject_ref"]
    finding_subject, _finding_subject_bytes = receipt_fixtures.R._load_subject_record(
        data,
        finding_subject_ref,
    )
    subject_path = finding_subject["paths"][0]
    first_receipt = inline_security_receipt(data, workflow, first_chain)
    first_ref = receipt_fixtures.R.persist_normalized(data, first_receipt)
    assert evaluate_unit_gate(
        payload(
            workflow,
            first_ref,
            data,
            subject_ref=finding_subject_ref,
        ),
        workflow=workflow,
        plugin_data=data,
        workspace_root=data.parent / "workspace",
    )["verdict"] == "block"

    (data.parent / "workspace" / subject_path).write_text("remediated\n")
    resolved_subject_ref, resolved_digest = receipt_fixtures.protected_subject(
        data,
        subject_path,
        parent_refs=[finding_subject_ref],
        created_at="2026-07-10T22:00:03.250000Z",
    )
    resolution_ref = receipt_fixtures.R.create_resolution_record(
        data,
        result_ref=first_chain["result_ref"],
        finding_id=str(unresolved["finding_id"]),
        resolved_subject_ref=resolved_subject_ref,
        evidence_refs=[resolved_subject_ref],
        recorded_at=resolution_recorded_at,
    )

    second_before_ref = receipt_fixtures.workspace_snapshot(
        data,
        "2026-07-10T22:09:59Z",
    )
    second_intent_ref = receipt_fixtures.R.create_intent_record(
        data,
        workflow,
        "security",
        attempt=2,
        task_id="security-review",
        subject_ref=resolved_subject_ref,
        workspace_snapshot_ref=second_before_ref,
        intent_kind="follow-up",
        previous_receipt_ref=first_ref,
        finding_refs=[str(unresolved["finding_id"])],
        resolution_refs=[resolution_ref],
        created_at="2026-07-10T22:10:00Z",
        nonce="9" * 32,
    )
    second_after_ref = receipt_fixtures.workspace_snapshot(
        data,
        "2026-07-10T22:10:01Z",
    )
    second_audit_ref = receipt_fixtures.R.create_mutation_audit_record(
        data,
        before_ref=second_before_ref,
        after_ref=second_after_ref,
        recorded_at="2026-07-10T22:10:01.500000Z",
    )
    step = workflow.step("security")
    second_result_ref = receipt_fixtures.R.create_result_record(
        data,
        workflow,
        "security",
        attempt=2,
        task_id="security-review",
        intent_ref=second_intent_ref,
        output_subject_ref=resolved_subject_ref,
        mutation_audit_ref=second_audit_ref,
        workspace_root=data.parent / "workspace",
        vehicle="verified-workflow-inline",
        child_id=None,
        provided_evidence=["review-evidence"],
        evidence=receipt_fixtures.review_evidence(
            step,
            input_digest=resolved_digest,
        ),
        execution={
            "kind": "agent-lens",
            "execution_class": step.execution_class,
            "profile_sha256": step.profile_sha256,
        },
        recorded_at="2026-07-10T22:10:02Z",
    )
    second_verification_ref = receipt_fixtures.R.create_root_verification_record(
        data,
        result_ref=second_result_ref,
        verifier_session_id="Session-1",
        verifier_turn_id="Revalidation-Turn",
        resolution_refs=[],
        recorded_at="2026-07-10T22:10:03Z",
    )
    second_receipt = receipt_fixtures.R.build_inline_receipt(
        data,
        workflow,
        "security",
        attempt=2,
        task_id="security-review",
        intent_ref=second_intent_ref,
        result_ref=second_result_ref,
        root_verification_ref=second_verification_ref,
    )
    second_ref = receipt_fixtures.R.persist_normalized(data, second_receipt)
    value = payload(
        workflow,
        second_ref,
        data,
        cycle=2,
        subject_ref=resolved_subject_ref,
    )
    return value, data, workflow, second_ref


def test_changed_resolution_follow_up_and_clean_revalidation_pass(
    tmp_path: Path,
) -> None:
    value, data, workflow, _reference = _resolved_follow_up(tmp_path)

    result = evaluate_unit_gate(
        value,
        workflow=workflow,
        plugin_data=data,
        workspace_root=data.parent / "workspace",
    )

    assert result["verdict"] == "pass"
    assert result["remediation"] == []


def test_resolution_recorded_after_retry_intent_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(
        receipt_fixtures.R.DispatchReceiptError,
        match="predates a claimed finding resolution",
    ):
        _resolved_follow_up(
            tmp_path,
            resolution_recorded_at="2026-07-10T22:10:00.500000Z",
        )


def test_low_score_is_advisory_without_typed_finding(tmp_path: Path) -> None:
    result, _data, _workflow, _reference = evaluated(tmp_path, overall=6.0)

    assert result["verdict"] == "pass"
    assert result["remediation"] == []
    assert result["warnings"] == [
        {"step_id": "security", "reason": "review score below 9.0"}
    ]


def test_high_overall_with_one_low_dimension_is_a_gate_warning(
    tmp_path: Path,
) -> None:
    data = receipt_fixtures.plugin_data(tmp_path)
    workflow = receipt_fixtures.workflow()
    step = workflow.step("security")
    subject_ref, subject_digest = receipt_fixtures.protected_subject(
        data,
        active_workflow=workflow,
    )
    before_ref = receipt_fixtures.workspace_snapshot(
        data,
        "2026-07-10T21:59:59Z",
    )
    intent_ref = receipt_fixtures.R.create_intent_record(
        data,
        workflow,
        "security",
        attempt=1,
        task_id="security-review",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="5" * 32,
    )
    after_ref = receipt_fixtures.workspace_snapshot(
        data,
        "2026-07-10T22:00:01Z",
    )
    audit_ref = receipt_fixtures.R.create_mutation_audit_record(
        data,
        before_ref=before_ref,
        after_ref=after_ref,
        recorded_at="2026-07-10T22:00:01.500000Z",
    )
    evidence = receipt_fixtures.review_evidence(
        step,
        overall=10.0,
        input_digest=subject_digest,
    )
    evidence["dimensions"][0]["score"] = 6.0
    evidence["overall"] = 9.2
    evidence["verdict"] = "needs-revision"
    result_ref = receipt_fixtures.R.create_result_record(
        data,
        workflow,
        "security",
        attempt=1,
        task_id="security-review",
        intent_ref=intent_ref,
        output_subject_ref=subject_ref,
        mutation_audit_ref=audit_ref,
        workspace_root=data.parent / "workspace",
        vehicle="verified-workflow-inline",
        child_id=None,
        provided_evidence=["review-evidence"],
        evidence=evidence,
        execution={
            "kind": "agent-lens",
            "execution_class": step.execution_class,
            "profile_sha256": step.profile_sha256,
        },
        recorded_at="2026-07-10T22:00:02Z",
    )
    verification_ref = receipt_fixtures.R.create_root_verification_record(
        data,
        result_ref=result_ref,
        verifier_session_id="Session-1",
        verifier_turn_id="Dimension-Turn",
        resolution_refs=[],
        recorded_at="2026-07-10T22:00:03Z",
    )
    receipt = receipt_fixtures.R.build_inline_receipt(
        data,
        workflow,
        "security",
        attempt=1,
        task_id="security-review",
        intent_ref=intent_ref,
        result_ref=result_ref,
        root_verification_ref=verification_ref,
    )
    reference = receipt_fixtures.R.persist_normalized(data, receipt)

    result = evaluate_unit_gate(
        payload(workflow, reference, data),
        workflow=workflow,
        plugin_data=data,
        workspace_root=data.parent / "workspace",
    )

    assert result["verdict"] == "pass"
    assert result["warnings"] == [
        {"step_id": "security", "reason": "review dimension score below 7.0"}
    ]


def test_remediable_finding_blocks_then_escalates_at_attempt_three(
    tmp_path: Path,
) -> None:
    finding = receipt_fixtures.finding("P2")
    first, _data, _workflow, _reference = evaluated(tmp_path / "first", findings=[finding])
    third, _data, _workflow, _reference = evaluated(
        tmp_path / "third", findings=[finding], attempt=3
    )
    hard_third, _data, _workflow, _reference = evaluated(
        tmp_path / "hard-third",
        findings=[receipt_fixtures.finding("P1")],
        attempt=3,
    )

    assert first["verdict"] == "block"
    assert third["verdict"] == "escalate"
    assert hard_third["verdict"] == "escalate"


def test_self_acceptance_is_machine_rejected(tmp_path: Path) -> None:
    data, workflow, reference, receipt = (
        receipt_fixtures.persisted_subagent_receipt(
            tmp_path,
            subject_path="plugins/verified-workflows/scripts/gate_evaluator.py",
        )
    )
    value = payload(
        workflow,
        reference,
        data,
        subject_ref=receipt["output_subject_ref"],
    )

    with pytest.raises(G.GateEvaluationError, match="cannot evaluate its own"):
        evaluate_unit_gate(
            value,
            workflow=workflow,
            plugin_data=data,
            workspace_root=data.parent / "workspace",
        )


def test_omitted_or_case_changed_self_path_in_git_baseline_is_rejected(
    tmp_path: Path,
) -> None:
    hidden = (
        tmp_path
        / "workspace"
        / "Plugins"
        / "verified-workflows"
        / "scripts"
        / "gate_evaluator.py"
    )
    hidden.parent.mkdir(parents=True)
    hidden.write_text("hidden self change\n")
    data, workflow, reference, receipt = (
        receipt_fixtures.persisted_subagent_receipt(tmp_path)
    )
    value = payload(
        workflow,
        reference,
        data,
        subject_ref=receipt["output_subject_ref"],
    )

    with pytest.raises(G.GateEvaluationError, match="cannot evaluate its own"):
        evaluate_unit_gate(
            value,
            workflow=workflow,
            plugin_data=data,
            workspace_root=data.parent / "workspace",
        )


def test_final_gate_rejects_ignored_changes_outside_authorized_scope(
    tmp_path: Path,
) -> None:
    data = receipt_fixtures.plugin_data(tmp_path)
    workspace = receipt_fixtures.workspace_repo(data)
    (workspace / ".gitignore").write_text("*.cache\n")
    receipt_fixtures.subprocess.run(
        ["git", "-C", str(workspace), "add", ".gitignore"],
        check=True,
    )
    receipt_fixtures.subprocess.run(
        ["git", "-C", str(workspace), "commit", "-qm", "add ignore fixture"],
        check=True,
    )
    workflow = receipt_fixtures.workflow()
    chain = receipt_fixtures.protected_chain(
        data,
        workflow,
        vehicle="verified-workflow-inline",
    )
    receipt = receipt_fixtures.R.build_inline_receipt(
        data,
        workflow,
        "security",
        attempt=1,
        task_id="security-review",
        **chain,
    )
    reference = receipt_fixtures.R.persist_normalized(data, receipt)
    (workspace / "outside.cache").write_text("changed after the final audit\n")

    with pytest.raises(G.GateEvaluationError, match="outside the authorized"):
        evaluate_unit_gate(
            payload(workflow, reference, data),
            workflow=workflow,
            plugin_data=data,
            workspace_root=workspace,
        )


def test_cycle_boolean_and_mismatched_attempt_reject(tmp_path: Path) -> None:
    _result, data, workflow, reference = evaluated(tmp_path)
    with pytest.raises(G.GateEvaluationError, match="cycle"):
        evaluate_unit_gate(
            payload(workflow, reference, data, cycle=True),
            workflow=workflow,
            plugin_data=data,
            workspace_root=data.parent / "workspace",
        )
    with pytest.raises(G.GateEvaluationError, match="newest receipt attempt"):
        evaluate_unit_gate(
            payload(workflow, reference, data, cycle=2),
            workflow=workflow,
            plugin_data=data,
            workspace_root=data.parent / "workspace",
        )


def test_advisory_seat_has_zero_gate_authority(tmp_path: Path) -> None:
    _result, data, workflow, reference = evaluated(tmp_path)
    value = payload(workflow, reference, data)
    value["advisory"] = [
        {
            "seat_type": "external-advisory",
            "gate_authority": "none",
            "evidence_ref": None,
        }
    ]
    assert evaluate_unit_gate(
        value,
        workflow=workflow,
        plugin_data=data,
        workspace_root=data.parent / "workspace",
    )["verdict"] == "pass"

    bad = copy.deepcopy(value)
    bad["advisory"][0]["gate_authority"] = "pass"  # type: ignore[index]
    with pytest.raises(G.GateEvaluationError, match="authority"):
        evaluate_unit_gate(
            bad,
            workflow=workflow,
            plugin_data=data,
            workspace_root=data.parent / "workspace",
        )


@pytest.mark.parametrize(
    "status,verdict",
    [("pass", "pass"), ("hard-fail", "block"), ("blocked", "block")],
)
def test_deterministic_validator_status_comes_from_protected_evidence(
    tmp_path: Path, status: str, verdict: str
) -> None:
    data, workflow, reference, _receipt = (
        receipt_fixtures.persisted_deterministic_receipt(tmp_path, status=status)
    )
    value = {
        "schema_version": 1,
        "workflow_sha256": workflow.sha256,
        "cycle": 1,
        "subject_ref": _receipt["output_subject_ref"],
        "steps": [{"step_id": "schema-check", "receipt_ref": reference}],
        "advisory": [],
    }

    assert evaluate_unit_gate(
        value,
        workflow=workflow,
        plugin_data=data,
        workspace_root=data.parent / "workspace",
    )["verdict"] == verdict
