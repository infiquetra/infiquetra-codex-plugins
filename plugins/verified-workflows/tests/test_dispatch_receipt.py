from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

PLUGIN_ROOT = Path(__file__).parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
TESTS = Path(__file__).parent
for directory in (SCRIPTS, TESTS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import dispatch_receipt as R  # noqa: E402
import workspace_evidence as E  # noqa: E402
import test_workflow_dispatch as fixtures  # noqa: E402
import workflow_dispatch as W  # noqa: E402


def workflow(*, independence: str = "preferred", vehicle: str = "auto") -> W.Workflow:
    return W.parse_workflow_structure(
        fixtures.plan(
            fixtures.row("security", independence=independence, vehicle=vehicle)
        )
    )


def plugin_data(tmp_path: Path) -> Path:
    data = tmp_path / "plugin-data"
    data.mkdir(mode=0o700, parents=True)
    return data


def installed_hooks(data: Path) -> tuple[Path, Path]:
    codex_home = data.parent / "codex-home"
    hooks = codex_home / "plugins" / "verified-workflows" / "hooks"
    hooks.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name in ("hooks.json", "agent_receipt.py"):
        target = hooks / name
        target.write_bytes((PLUGIN_ROOT / "hooks" / name).read_bytes())
        target.chmod(0o600)
    return codex_home, hooks


def workspace_repo(data: Path) -> Path:
    workspace = data.parent / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    if not (workspace / ".git").exists():
        subprocess.run(["git", "init", "-q", str(workspace)], check=True)
        subprocess.run(
            ["git", "-C", str(workspace), "config", "user.name", "Fixture"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(workspace), "config", "user.email", "fixture@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(workspace), "commit", "--allow-empty", "-qm", "baseline"],
            check=True,
        )
    return workspace


def protected_subject(
    data: Path,
    relative: str = "src/example.py",
    *,
    active_workflow: W.Workflow | None = None,
    workflow_run_ref: str | None = None,
    parent_refs: list[str] | None = None,
    created_at: str = "2026-07-10T21:59:58Z",
) -> tuple[str, str]:
    workspace = workspace_repo(data)
    target = workspace / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text("subject fixture\n")
    if parent_refs:
        parent, _parent_bytes = R._load_subject_record(data, parent_refs[0])
        inherited_run_ref = parent["workflow_run_ref"]
        if workflow_run_ref is not None and workflow_run_ref != inherited_run_ref:
            raise AssertionError("fixture subject cannot change workflow run")
        workflow_run_ref = inherited_run_ref
    if workflow_run_ref is None:
        workflow_run_ref = R.create_workflow_run_record(
            data,
            active_workflow or workflow(),
            workspace_root=workspace,
            created_at="2026-07-10T21:59:57Z",
            nonce="0" * 32,
        )
    reference = R.create_subject_record(
        data,
        workspace_root=workspace,
        subject_paths=[relative],
        workflow_run_ref=workflow_run_ref,
        parent_refs=parent_refs,
        created_at=created_at,
    )
    record, _content = R._load_subject_record(data, reference)
    return reference, record["content_sha256"]


def workspace_snapshot(data: Path, created_at: str) -> str:
    return R.create_workspace_snapshot_record(
        data,
        workspace_root=data.parent / "workspace",
        created_at=created_at,
    )


def command_output(
    data: Path,
    active_workflow: W.Workflow,
    intent_ref: str,
    *,
    exit_code: int,
    status: str | None = None,
    recorded_at: str,
    payload: dict[str, object] | None = None,
    stderr_text: str | None = None,
) -> str:
    output_dir = data.parent / "command-output"
    output_dir.mkdir(exist_ok=True)
    stdout = output_dir / f"stdout-{exit_code}.txt"
    stderr = output_dir / f"stderr-{exit_code}.txt"
    status = status or ("pass" if exit_code == 0 else "hard-fail")
    intent, _intent_bytes = R.load_protected_record(data, intent_ref, "intent")
    stdout.write_text(
        json.dumps(
            payload
            or {
                "target": "schema",
                "expected": "valid",
                "actual": status,
                "cases": [{"case_id": intent["step_id"], "status": status}],
                "gate_status": status,
            },
            sort_keys=True,
        )
        + "\n"
    )
    stderr.write_text(
        stderr_text if stderr_text is not None else "" if exit_code == 0 else "failed\n"
    )
    stdout.chmod(0o600)
    stderr.chmod(0o600)
    return R.create_command_output_record(
        data,
        active_workflow,
        intent["step_id"],
        attempt=intent["attempt"],
        task_id=intent["task_id"],
        intent_ref=intent_ref,
        stdout_file=stdout,
        stderr_file=stderr,
        exit_code=exit_code,
        output_limit_bytes=active_workflow.step(intent["step_id"]).command_output_limit_bytes,
        recorded_at=recorded_at,
    )


def agent_command_output(
    data: Path,
    active_workflow: W.Workflow,
    step_id: str,
    *,
    argv: list[str],
    created_at: str,
    nonce: str,
) -> str:
    subject_ref, _subject_digest = protected_subject(
        data,
        f"src/{step_id}.py",
        active_workflow=active_workflow,
    )
    before_ref = workspace_snapshot(data, created_at)
    intent_time = (
        dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        + dt.timedelta(microseconds=1)
    ).isoformat(timespec="microseconds").replace("+00:00", "Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        step_id,
        attempt=1,
        task_id=step_id,
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_ref,
        created_at=intent_time,
        nonce=nonce,
    )
    output_dir = data.parent / "agent-command-output"
    output_dir.mkdir(exist_ok=True)
    stdout = output_dir / f"{step_id}-stdout.txt"
    stderr = output_dir / f"{step_id}-stderr.txt"
    stdout.write_text("completed\n")
    stderr.write_text("")
    stdout.chmod(0o600)
    stderr.chmod(0o600)
    output_time = (
        dt.datetime.fromisoformat(intent_time.replace("Z", "+00:00"))
        + dt.timedelta(microseconds=1)
    ).isoformat(timespec="microseconds").replace("+00:00", "Z")
    return R.create_command_output_record(
        data,
        active_workflow,
        step_id,
        attempt=1,
        task_id=step_id,
        intent_ref=intent_ref,
        stdout_file=stdout,
        stderr_file=stderr,
        exit_code=0,
        output_limit_bytes=64 * 1024,
        argv=argv,
        recorded_at=output_time,
    )


def finding(severity: str = "P2", *, resolved: bool = False) -> dict[str, object]:
    return {
        "finding_id": f"finding-{severity.lower()}",
        "severity": severity,
        "category": "correctness",
        "location": "src/example.py",
        "impact": "fixture impact",
        "fix": "apply the fixture correction",
        "validation": "rerun the fixture check",
        "resolved": resolved,
        "hard_stop": False,
    }


def deterministic_evidence(
    step: W.WorkflowStep,
    output_ref: str,
    payload: dict[str, object],
    *,
    exit_code: int,
) -> dict[str, object]:
    cases = payload["cases"]
    assert isinstance(cases, list)
    return {
        "role_id": step.role_id,
        "role_digest": step.role_lens_sha256,
        "target": payload["target"],
        "declared_argv": list(step.command),
        "expected": payload["expected"],
        "actual": payload["actual"],
        "exit_code": exit_code,
        "evidence_refs": [output_ref],
        "cases": [{**case, "evidence_ref": output_ref} for case in cases],
        "gate_status": payload["gate_status"],
    }


def review_evidence(
    step: W.WorkflowStep,
    *,
    findings: list[dict[str, object]] | None = None,
    overall: float = 9.5,
    input_digest: str = "9" * 64,
) -> dict[str, object]:
    values = findings or []
    dimension_ids = R._review_dimension_ids(
        W.renderer.load_role_registry(),
        step.role_id,
    )
    unresolved = [value for value in values if not value["resolved"]]
    blocking = any(
        value["severity"] in {"P0", "P1"}
        or value["category"] == "security"
        or value["hard_stop"]
        for value in unresolved
    )
    return {
        "role_id": step.role_id,
        "role_digest": step.role_lens_sha256,
        "input_digest": input_digest,
        "dimensions": [
            {
                "dimension_id": dimension_id,
                "score": overall,
                "notes": "fixture score",
            }
            for dimension_id in dimension_ids
        ],
        "denominator": len(dimension_ids),
        "overall": overall,
        "verdict": (
            "blocking"
            if blocking
            else "needs-revision"
            if unresolved or overall < 9.0
            else "accept"
        ),
        "findings": values,
        "exclusions": [],
    }


def raw(
    event: str,
    active_workflow: W.Workflow,
    **overrides: object,
) -> dict[str, object]:
    step = active_workflow.step("security")
    value: dict[str, object] = {
        "schema_version": 1,
        "event": event,
        "parent_session_id": "Session-1",
        "turn_id": "Turn-1",
        "child_id": "Child-1",
        "agent_type": "review_high",
        "active_model": step.expected_model,
        "permission_mode": "default",
        "codex_home_sha256": "0" * 64,
        "profile_sha256": step.profile_sha256,
        "hook_definition_sha256": hashlib.sha256(
            (PLUGIN_ROOT / "hooks" / "hooks.json").read_bytes()
        ).hexdigest(),
        "hook_handler_sha256": hashlib.sha256(
            (PLUGIN_ROOT / "hooks" / "agent_receipt.py").read_bytes()
        ).hexdigest(),
        "observed_at": (
            "2026-07-10T22:00:01.000000Z"
            if event == "start"
            else "2026-07-10T22:00:02.000000Z"
        ),
    }
    value.update(overrides)
    return value


def protected_chain(
    data: Path,
    active_workflow: W.Workflow,
    *,
    vehicle: str = "verified-workflow-subagent",
    findings: list[dict[str, object]] | None = None,
    overall: float = 9.5,
    attempt: int = 1,
    subject_path: str = "src/example.py",
    previous_receipt_ref: str | None = None,
    workflow_run_ref: str | None = None,
) -> dict[str, str]:
    step = active_workflow.step("security")
    minute = (attempt - 1) * 10
    prefix = f"2026-07-10T22:{minute:02d}:"
    if previous_receipt_ref is None:
        subject_ref, subject_digest = protected_subject(
            data,
            subject_path,
            active_workflow=active_workflow,
            workflow_run_ref=workflow_run_ref,
        )
    else:
        previous_receipt, _previous_bytes = R.load_normalized_receipt(
            data, previous_receipt_ref
        )
        subject_ref, subject_digest = protected_subject(
            data,
            subject_path,
            active_workflow=active_workflow,
            parent_refs=[previous_receipt["output_subject_ref"]],
        )
    before_snapshot_ref = workspace_snapshot(data, prefix + "00.000000Z")
    finding_ids = [str(value["finding_id"]) for value in (findings or [])]
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "security",
        attempt=attempt,
        task_id="security-review",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_snapshot_ref,
        intent_kind=(
            "run" if attempt == 1 else "follow-up" if finding_ids else "revalidate"
        ),
        previous_receipt_ref=previous_receipt_ref,
        finding_refs=finding_ids if attempt > 1 else [],
        created_at=prefix + "00.100000Z",
        nonce="1" * 32,
    )
    child_id = "Child-1" if vehicle == "verified-workflow-subagent" else None
    after_snapshot_ref = workspace_snapshot(data, prefix + "02Z")
    mutation_audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=before_snapshot_ref,
        after_ref=after_snapshot_ref,
        recorded_at=prefix + "02.500000Z",
    )
    result_ref = R.create_result_record(
        data,
        active_workflow,
        "security",
        attempt=attempt,
        task_id="security-review",
        intent_ref=intent_ref,
        output_subject_ref=subject_ref,
        mutation_audit_ref=mutation_audit_ref,
        workspace_root=data.parent / "workspace",
        vehicle=vehicle,
        child_id=child_id,
        provided_evidence=["review-evidence"],
        evidence=review_evidence(
            step,
            findings=findings,
            overall=overall,
            input_digest=subject_digest,
        ),
        execution={
            "kind": "agent-lens",
            "execution_class": step.execution_class,
            "profile_sha256": step.profile_sha256,
        },
        recorded_at=prefix + "03.000000Z",
    )
    verification_ref = R.create_root_verification_record(
        data,
        result_ref=result_ref,
        verifier_session_id="Session-1",
        verifier_turn_id="Root-Turn-1",
        resolution_refs=[],
        recorded_at=prefix + "04.000000Z",
    )
    values = {
        "intent_ref": intent_ref,
        "result_ref": result_ref,
        "root_verification_ref": verification_ref,
    }
    if vehicle == "verified-workflow-subagent":
        codex_home, hooks = installed_hooks(data)
        values["hook_trust_ref"] = R.create_hook_trust_record(
            data,
            codex_home=codex_home,
            installed_hooks_dir=hooks,
            scope="isolated",
            observed_at="2026-07-10T21:59:59.000000Z",
        )
        values["launch_ref"] = R.create_launch_record(
            data,
            intent_ref=intent_ref,
            parent_session_id="Session-1",
            turn_id="Turn-1",
            child_id="Child-1",
            agent_type="review_high",
            hook_trust_ref=values["hook_trust_ref"],
            launched_at=prefix + "00.500000Z",
        )
    return values


def join(
    data: Path,
    active_workflow: W.Workflow,
    chain: dict[str, str],
    attempt: int = 1,
    **overrides: object,
) -> dict[str, Any]:
    minute = (attempt - 1) * 10
    prefix = f"2026-07-10T22:{minute:02d}:"
    trust, _trust_bytes = R._load_hook_trust_record(data, chain["hook_trust_ref"])
    start = raw(
        "start",
        active_workflow,
        codex_home_sha256=trust["codex_home_sha256"],
        observed_at=prefix + "01.000000Z",
    )
    stop = raw(
        "stop",
        active_workflow,
        codex_home_sha256=trust["codex_home_sha256"],
        observed_at=prefix + "02.000000Z",
    )
    kwargs: dict[str, object] = {
        "attempt": attempt,
        "task_id": "security-review",
        "parent_session_id": "Session-1",
        "child_id": "Child-1",
        "turn_id": "Turn-1",
        **chain,
        "start": start,
        "stop": stop,
        "now": lambda: dt.datetime(
            2026, 7, 10, 22, minute, 5, tzinfo=dt.UTC
        ),
    }
    kwargs.update(overrides)
    kwargs.setdefault("start_bytes", R._canonical_bytes(kwargs["start"]))
    kwargs.setdefault("stop_bytes", R._canonical_bytes(kwargs["stop"]))
    return R.join_subagent_receipt(
        data, active_workflow, "security", **kwargs  # type: ignore[arg-type]
    )


def persisted_subagent_receipt(
    tmp_path: Path,
    *,
    findings: list[dict[str, object]] | None = None,
    overall: float = 9.5,
    attempt: int = 1,
    subject_path: str = "src/example.py",
) -> tuple[Path, W.Workflow, str, dict[str, Any]]:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    reference: str | None = None
    receipt: dict[str, Any] | None = None
    for current_attempt in range(1, attempt + 1):
        chain = protected_chain(
            data,
            active_workflow,
            findings=findings,
            overall=overall,
            attempt=current_attempt,
            subject_path=subject_path,
            previous_receipt_ref=reference,
        )
        receipt = join(data, active_workflow, chain, attempt=current_attempt)
        reference = R.persist_normalized(
            data, receipt, raw_pair_sha256=receipt["child"]["raw_pair_sha256"]
        )
        R.validate_normalized_receipt(data, reference, active_workflow)
    assert reference is not None and receipt is not None
    return data, active_workflow, reference, receipt


def deterministic_workflow(
    *,
    output_limit_bytes: int = 65536,
    validator_required: bool = True,
    validator_disabled: bool = False,
) -> W.Workflow:
    step = W.WorkflowStep(
        step_id="schema-check",
        depends_on=(),
        barrier=None,
        role_id="scenario-tester",
        role_kind="deterministic-validator",
        independence=None,
        execution_class=None,
        runtime_agent_name=None,
        vehicle="deterministic-tool",
        mutation="none",
        required_evidence=("tester-evidence",),
        role_lens_sha256="1" * 64,
        profile_sha256=None,
        expected_model=None,
        expected_effort=None,
        validator_required=validator_required,
        validator_disabled=validator_disabled,
        expected_profile_sandbox=None,
        output_schema="tester-evidence.v1",
        command=("python3", "tools/check_schema.py"),
        command_implementation_path="tools/check_schema.py",
        command_implementation_sha256="2" * 64,
        command_timeout_seconds=30,
        command_output_limit_bytes=output_limit_bytes,
        evidence_schema_path="schemas/tester-evidence.json",
        evidence_schema_sha256="3" * 64,
        deterministic_contract_sha256="4" * 64,
    )
    return W.Workflow(
        steps=(step,), sha256=W._canonical_sha256([step.to_jsonable()])
    )


def deploy_fixture(
    tmp_path: Path,
    *,
    validator_required: bool = True,
) -> tuple[Path, W.Workflow, dict[str, object]]:
    active_workflow = W.parse_workflow_structure(
        fixtures.plan(
            fixtures.row(
                "gate",
                "root",
                mutation="root-only",
                required_evidence="root-proof",
            ),
            fixtures.row(
                "deploy",
                "deploy-watcher",
                depends_on="gate",
                execution_class="monitor-low",
                required_evidence="deploy-evidence",
                validator_required=validator_required,
            ),
        )
    )
    data = plugin_data(tmp_path)
    subject_ref, _subject_digest = protected_subject(
        data,
        active_workflow=active_workflow,
    )
    gate_before_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    gate_intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "gate",
        attempt=1,
        task_id="gate",
        subject_ref=subject_ref,
        workspace_snapshot_ref=gate_before_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="6" * 32,
    )
    gate_result_ref = R.create_result_record(
        data,
        active_workflow,
        "gate",
        attempt=1,
        task_id="gate",
        intent_ref=gate_intent_ref,
        output_subject_ref=subject_ref,
        mutation_audit_ref=None,
        workspace_root=None,
        vehicle="root",
        child_id=None,
        provided_evidence=["root-proof"],
        evidence={"evidence_refs": {"root-proof": subject_ref}, "findings": []},
        execution={"kind": "root"},
        recorded_at="2026-07-10T22:00:01Z",
    )
    gate_verification_ref = R.create_root_verification_record(
        data,
        result_ref=gate_result_ref,
        verifier_session_id="Session-1",
        verifier_turn_id="Gate-Turn",
        resolution_refs=[],
        recorded_at="2026-07-10T22:00:02Z",
    )
    gate_receipt = R.build_root_receipt(
        data,
        active_workflow,
        "gate",
        attempt=1,
        task_id="gate",
        intent_ref=gate_intent_ref,
        result_ref=gate_result_ref,
        root_verification_ref=gate_verification_ref,
    )
    gate_receipt_ref = R.persist_normalized(data, gate_receipt)
    deploy_before_ref = workspace_snapshot(data, "2026-07-10T22:09:59Z")
    deploy_intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "deploy",
        attempt=1,
        task_id="deploy",
        subject_ref=subject_ref,
        workspace_snapshot_ref=deploy_before_ref,
        created_at="2026-07-10T22:10:00Z",
        nonce="7" * 32,
    )
    deploy_after_ref = workspace_snapshot(data, "2026-07-10T22:10:01Z")
    deploy_audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=deploy_before_ref,
        after_ref=deploy_after_ref,
        recorded_at="2026-07-10T22:10:01.500000Z",
    )
    subject, _subject_bytes = R._load_subject_record(data, subject_ref)
    workflow_run, _workflow_run_bytes = R._load_workflow_run_record(
        data,
        subject["workflow_run_ref"],
    )
    step = active_workflow.step("deploy")
    evidence = {
        "role_id": step.role_id,
        "role_digest": step.role_lens_sha256,
        "remote": "github.com/infiquetra/example",
        "workflow": "nonprod-deploy",
        "run_ref": "run-123",
        "commit_sha": workflow_run["head_revision"],
        "branch": "main",
        "default_branch": "main",
        "environment": "nonprod",
        "eligibility": True,
        "prerequisite_gate_refs": [gate_result_ref],
        "evidence_refs": [deploy_after_ref],
        "rollback_notes": "revert the nonprod deployment tag",
        "run_status": "succeeded",
        "gate_status": "pass" if validator_required else "warn",
    }
    return data, active_workflow, {
        "subject_ref": subject_ref,
        "gate_receipt_ref": gate_receipt_ref,
        "intent_ref": deploy_intent_ref,
        "audit_ref": deploy_audit_ref,
        "evidence": evidence,
        "execution": {
            "kind": "agent-lens",
            "execution_class": step.execution_class,
            "profile_sha256": step.profile_sha256,
        },
    }


def persisted_deterministic_receipt(
    tmp_path: Path, *, status: str = "pass"
) -> tuple[Path, W.Workflow, str, dict[str, Any]]:
    data = plugin_data(tmp_path)
    active_workflow = deterministic_workflow()
    step = active_workflow.step("schema-check")
    subject_ref, _subject_digest = protected_subject(
        data,
        "src/schema.py",
        active_workflow=active_workflow,
    )
    before_snapshot_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_snapshot_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="5" * 32,
    )
    output_ref = command_output(
        data,
        active_workflow,
        intent_ref,
        exit_code=0 if status == "pass" else 1,
        status=status,
        recorded_at="2026-07-10T22:00:00.500000Z",
    )
    after_snapshot_ref = workspace_snapshot(data, "2026-07-10T22:00:00.600000Z")
    mutation_audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=before_snapshot_ref,
        after_ref=after_snapshot_ref,
        recorded_at="2026-07-10T22:00:00.700000Z",
    )
    result_ref = R.create_result_record(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        intent_ref=intent_ref,
        output_subject_ref=subject_ref,
        mutation_audit_ref=mutation_audit_ref,
        workspace_root=data.parent / "workspace",
        vehicle="deterministic-tool",
        child_id=None,
        provided_evidence=["tester-evidence"],
        evidence={
            "role_id": step.role_id,
            "role_digest": step.role_lens_sha256,
            "target": "schema",
            "declared_argv": list(step.command),
            "expected": "valid",
            "actual": status,
            "exit_code": 0 if status == "pass" else 1,
            "evidence_refs": [output_ref],
            "cases": [
                {
                    "case_id": "schema-check",
                    "status": (
                        "pass"
                        if status == "pass"
                        else "blocked"
                        if status == "blocked"
                        else "hard-fail"
                    ),
                    "evidence_ref": output_ref,
                }
            ],
            "gate_status": status,
        },
        execution={
            "kind": "deterministic-validator",
            "argv": list(step.command),
            "implementation_sha256": step.command_implementation_sha256,
            "evidence_schema_sha256": step.evidence_schema_sha256,
            "cwd": "repo-root",
            "timeout_seconds": step.command_timeout_seconds,
            "output_limit_bytes": step.command_output_limit_bytes,
            "output_ref": output_ref,
            "exit_code": 0 if status == "pass" else 1,
        },
        recorded_at="2026-07-10T22:00:01Z",
    )
    verification_ref = R.create_root_verification_record(
        data,
        result_ref=result_ref,
        verifier_session_id="Session-1",
        verifier_turn_id="Turn-1",
        resolution_refs=[],
        recorded_at="2026-07-10T22:00:02Z",
    )
    receipt = R.build_deterministic_receipt(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        intent_ref=intent_ref,
        result_ref=result_ref,
        root_verification_ref=verification_ref,
    )
    reference = R.persist_normalized(data, receipt)
    R.validate_normalized_receipt(data, reference, active_workflow)
    return data, active_workflow, reference, receipt


def test_complete_protected_chain_attests_model_not_effort_or_sandbox(
    tmp_path: Path,
) -> None:
    data, active_workflow, reference, receipt = persisted_subagent_receipt(tmp_path)

    assert receipt["vehicle"] == "verified-workflow-subagent"
    assert receipt["execution"]["active_model"] == "gpt-5.6-sol"
    assert receipt["execution"]["effort_evidence"] == "installed-profile-digest"
    assert receipt["execution"]["sandbox_enforcement_claim"] == "configured-not-observed"
    assert receipt["execution"]["permission_boundary"] == "requested-boundary-advisory"
    assert receipt["result"]["root_verified"] is True
    assert R.validate_normalized_receipt(data, reference, active_workflow)[0] == receipt


def test_fabricated_or_cross_bound_records_fail(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    chain = protected_chain(data, active_workflow)

    with pytest.raises(R.DispatchReceiptError, match="record reference"):
        join(data, active_workflow, {**chain, "launch_ref": "native-launch:" + "a" * 64})

    other = R.create_launch_record(
        data,
        intent_ref=chain["intent_ref"],
        parent_session_id="Session-1",
        turn_id="Turn-1",
        child_id="Other-Child",
        agent_type="review_high",
        hook_trust_ref=chain["hook_trust_ref"],
        launched_at="2026-07-10T22:00:00.500000Z",
    )
    with pytest.raises(R.DispatchReceiptError, match="does not bind"):
        join(data, active_workflow, {**chain, "launch_ref": other})


def test_launch_ack_may_follow_child_start_but_must_precede_result(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    chain = protected_chain(data, active_workflow)
    late_ack = R.create_launch_record(
        data,
        intent_ref=chain["intent_ref"],
        parent_session_id="Session-1",
        turn_id="Turn-1",
        child_id="Child-1",
        agent_type="review_high",
        hook_trust_ref=chain["hook_trust_ref"],
        launched_at="2026-07-10T22:00:01.500000Z",
    )
    receipt = join(data, active_workflow, {**chain, "launch_ref": late_ack})
    reference = R.persist_normalized(
        data,
        receipt,
        raw_pair_sha256=receipt["child"]["raw_pair_sha256"],
    )

    R.validate_normalized_receipt(data, reference, active_workflow)

    after_result = R.create_launch_record(
        data,
        intent_ref=chain["intent_ref"],
        parent_session_id="Session-1",
        turn_id="Turn-1",
        child_id="Child-1",
        agent_type="review_high",
        hook_trust_ref=chain["hook_trust_ref"],
        launched_at="2026-07-10T22:00:03.500000Z",
    )
    with pytest.raises(R.DispatchReceiptError, match="timestamps"):
        join(data, active_workflow, {**chain, "launch_ref": after_result})


def test_raw_pair_and_trusted_hook_bytes_must_match(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    chain = protected_chain(data, active_workflow)

    with pytest.raises(R.DispatchReceiptError, match="bytes do not bind"):
        join(
            data,
            active_workflow,
            chain,
            start_bytes=R._canonical_bytes(
                raw("start", active_workflow, child_id="Other-Child")
            ),
        )
    with pytest.raises(R.DispatchReceiptError, match="trusted hook bytes"):
        join(
            data,
            active_workflow,
            chain,
            start=raw("start", active_workflow, hook_handler_sha256="0" * 64),
            stop=raw("stop", active_workflow, hook_handler_sha256="0" * 64),
        )
    foreign_start = raw(
        "start",
        active_workflow,
        codex_home_sha256="f" * 64,
    )
    foreign_stop = raw(
        "stop",
        active_workflow,
        codex_home_sha256="f" * 64,
    )
    with pytest.raises(R.DispatchReceiptError, match="trusted hook bytes"):
        join(
            data,
            active_workflow,
            chain,
            start=foreign_start,
            stop=foreign_stop,
            start_bytes=R._canonical_bytes(foreign_start),
            stop_bytes=R._canonical_bytes(foreign_stop),
        )


def test_normalized_replay_rebinds_retained_hook_hashes_to_trust_record(
    tmp_path: Path,
) -> None:
    data, active_workflow, _reference, receipt = persisted_subagent_receipt(tmp_path)
    tampered = json.loads(json.dumps(receipt))
    tampered["raw_events"]["start"]["hook_handler_sha256"] = "0" * 64
    tampered["raw_events"]["stop"]["hook_handler_sha256"] = "0" * 64
    start_bytes = R._canonical_bytes(tampered["raw_events"]["start"])
    stop_bytes = R._canonical_bytes(tampered["raw_events"]["stop"])
    tampered["child"]["start_sha256"] = R._sha256(start_bytes)
    tampered["child"]["stop_sha256"] = R._sha256(stop_bytes)
    tampered["child"]["raw_pair_sha256"] = R._sha256(
        R._canonical_bytes(
            {
                "start_sha256": tampered["child"]["start_sha256"],
                "stop_sha256": tampered["child"]["stop_sha256"],
            }
        )
    )
    content = R._canonical_bytes(tampered)
    normalized_path = (
        data
        / "receipts"
        / "v1"
        / "normalized"
        / tampered["workflow_sha256"]
        / tampered["workflow_run_sha256"]
        / tampered["step_id"]
        / f"attempt-{tampered['attempt']}.json"
    )
    normalized_path.write_bytes(content)
    reference = (
        f"normalized:{tampered['workflow_sha256']}:"
        f"{tampered['workflow_run_sha256']}:{tampered['step_id']}:"
        f"{tampered['attempt']}:{R._sha256(content)}"
    )

    with pytest.raises(R.DispatchReceiptError, match="retained raw event evidence"):
        R.validate_normalized_receipt(data, reference, active_workflow)


def test_hook_readback_must_come_from_declared_codex_home(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    codex_home = data.parent / "codex-home"
    codex_home.mkdir(mode=0o700)

    with pytest.raises(R.DispatchReceiptError, match="contained"):
        R.create_hook_trust_record(
            data,
            codex_home=codex_home,
            installed_hooks_dir=PLUGIN_ROOT / "hooks",
            scope="isolated",
        )


def test_hook_trust_recomputes_the_derived_readback_digest(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    definition, handler = R._current_hook_bytes()
    forged_ref = R.persist_protected_record(
        data,
        {
            "schema_version": 1,
            "record_type": "hook-trust",
            "trust_claim": "root-observed-installed-hook-readback",
            "scope": "isolated",
            "codex_home_sha256": "1" * 64,
            "installed_hooks_relative": "plugins/verified-workflows/hooks",
            "definition_sha256": hashlib.sha256(definition).hexdigest(),
            "handler_sha256": hashlib.sha256(handler).hexdigest(),
            "trust_readback_sha256": "0" * 64,
            "observed_at": "2026-07-10T22:00:00Z",
        },
    )

    with pytest.raises(R.DispatchReceiptError, match="current trusted bytes"):
        R._load_hook_trust_record(data, forged_ref)


def test_result_schema_required_evidence_and_mutation_audit_fail_closed(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    step = active_workflow.step("security")
    subject_ref, subject_digest = protected_subject(data)
    before_snapshot_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "security",
        attempt=1,
        task_id="security-review",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_snapshot_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="2" * 32,
    )
    with pytest.raises(R.DispatchReceiptError, match="missing required"):
        after_snapshot_ref = workspace_snapshot(data, "2026-07-10T22:00:01Z")
        audit_ref = R.create_mutation_audit_record(
            data,
            before_ref=before_snapshot_ref,
            after_ref=after_snapshot_ref,
            recorded_at="2026-07-10T22:00:01.500000Z",
        )
        R.create_result_record(
            data,
            active_workflow,
            "security",
            attempt=1,
            task_id="security-review",
            intent_ref=intent_ref,
            output_subject_ref=subject_ref,
            mutation_audit_ref=audit_ref,
            workspace_root=data.parent / "workspace",
            vehicle="verified-workflow-inline",
            child_id=None,
            provided_evidence=[],
            evidence=review_evidence(step, input_digest=subject_digest),
            execution={
                "kind": "agent-lens",
                "execution_class": step.execution_class,
                "profile_sha256": step.profile_sha256,
            },
        )
    (data.parent / "workspace" / "src" / "example.py").write_text("changed\n")
    changed_subject_ref, _changed_digest = protected_subject(
        data, parent_refs=[subject_ref]
    )
    changed_snapshot_ref = workspace_snapshot(data, "2026-07-10T22:00:02Z")
    changed_audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=before_snapshot_ref,
        after_ref=changed_snapshot_ref,
        recorded_at="2026-07-10T22:00:02.500000Z",
    )
    with pytest.raises(R.DispatchReceiptError, match="read-only result"):
        R.create_result_record(
            data,
            active_workflow,
            "security",
            attempt=1,
            task_id="security-review",
            intent_ref=intent_ref,
            output_subject_ref=changed_subject_ref,
            mutation_audit_ref=changed_audit_ref,
            workspace_root=data.parent / "workspace",
            vehicle="verified-workflow-inline",
            child_id=None,
            provided_evidence=["review-evidence"],
            evidence=review_evidence(step, input_digest=subject_digest),
            execution={
                "kind": "agent-lens",
                "execution_class": step.execution_class,
                "profile_sha256": step.profile_sha256,
            },
        )


def test_review_input_digest_and_security_hard_stop_are_enforced(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    step = active_workflow.step("security")
    subject_ref, subject_digest = protected_subject(
        data,
        active_workflow=active_workflow,
    )
    before_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "security",
        attempt=1,
        task_id="security-review",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="3" * 32,
    )
    after_ref = workspace_snapshot(data, "2026-07-10T22:00:01Z")
    audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=before_ref,
        after_ref=after_ref,
        recorded_at="2026-07-10T22:00:01.500000Z",
    )
    wrong_digest = review_evidence(step, input_digest="0" * 64)
    with pytest.raises(R.DispatchReceiptError, match="protected subject"):
        R.create_result_record(
            data,
            active_workflow,
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
            evidence=wrong_digest,
            execution={
                "kind": "agent-lens",
                "execution_class": step.execution_class,
                "profile_sha256": step.profile_sha256,
            },
            recorded_at="2026-07-10T22:00:02Z",
        )

    partial_dimensions = review_evidence(step, input_digest=subject_digest)
    partial_dimensions["dimensions"] = partial_dimensions["dimensions"][:-1]
    partial_dimensions["denominator"] = len(partial_dimensions["dimensions"])
    with pytest.raises(R.DispatchReceiptError, match="selected lens dimensions"):
        R._validate_evidence(
            data,
            step,
            partial_dimensions,
            {"review-evidence": subject_ref},
        )
    invented_dimension = review_evidence(step, input_digest=subject_digest)
    invented_dimension["dimensions"][0]["dimension_id"] = "invented-dimension"
    with pytest.raises(R.DispatchReceiptError, match="selected lens dimensions"):
        R._validate_evidence(
            data,
            step,
            invented_dimension,
            {"review-evidence": subject_ref},
        )

    hard_score = review_evidence(step, input_digest=subject_digest)
    for dimension in hard_score["dimensions"]:
        if dimension["dimension_id"] == "auth-authz":
            dimension["score"] = 4.0
    hard_score["overall"] = sum(
        float(dimension["score"]) for dimension in hard_score["dimensions"]
    ) / len(hard_score["dimensions"])
    hard_score["verdict"] = "needs-revision"
    with pytest.raises(R.DispatchReceiptError, match="typed hard-stop"):
        R._validate_evidence(
            data,
            step,
            hard_score,
            {"review-evidence": subject_ref},
        )

    security_finding = {
        **finding("P2"),
        "finding_id": "auth-hard-stop",
        "category": "security",
        "hard_stop": True,
    }
    hard_score["findings"] = [security_finding]
    hard_score["verdict"] = "blocking"
    assert (
        R._validate_evidence(
            data,
            step,
            hard_score,
            {"review-evidence": subject_ref},
        )["verdict"]
        == "blocking"
    )


def test_nested_validator_aggregates_accept_exact_shapes_and_reject_contradictions(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    protected_subject(data)
    evidence_ref = workspace_snapshot(data, "2026-07-10T22:00:00Z")
    workflows = {
        "scanner": W.parse_workflow_structure(
            fixtures.plan(
                fixtures.row(
                    "scanner",
                    "security-scanner",
                    execution_class="scan-low",
                    required_evidence="scanner-evidence",
                )
            )
        ),
        "tester": W.parse_workflow_structure(
            fixtures.plan(
                fixtures.row(
                    "tester",
                    "scenario-tester",
                    execution_class="test-medium",
                    required_evidence="tester-evidence",
                )
            )
        ),
        "monitor": W.parse_workflow_structure(
            fixtures.plan(
                fixtures.row(
                    "monitor",
                    "runtime-monitor",
                    execution_class="monitor-low",
                    required_evidence="monitor-evidence",
                )
            )
        ),
    }
    scanner = workflows["scanner"].step("scanner")
    scanner_ref = agent_command_output(
        data,
        workflows["scanner"],
        "scanner",
        argv=["scanner", "--json"],
        created_at="2026-07-10T21:59:58.100000Z",
        nonce="a" * 32,
    )
    scanner_evidence = {
        "role_id": scanner.role_id,
        "role_digest": scanner.role_lens_sha256,
        "required": True,
        "tools": ["scanner"],
        "argv": [["scanner", "--json"]],
        "cwd": "repo-root",
        "exit_codes": [0],
        "evidence_refs": [scanner_ref],
        "findings": [],
        "gate_status": "pass",
        "missing_tool_guidance": [],
    }
    assert R._validate_evidence(
        data, scanner, scanner_evidence, {"scanner-evidence": scanner_ref}
    )["gate_status"] == "pass"
    with pytest.raises(R.DispatchReceiptError, match="aligned"):
        R._validate_evidence(
            data,
            scanner,
            {**scanner_evidence, "exit_codes": []},
            {"scanner-evidence": scanner_ref},
        )

    tester = workflows["tester"].step("tester")
    tester_ref = agent_command_output(
        data,
        workflows["tester"],
        "tester",
        argv=["pytest", "-q"],
        created_at="2026-07-10T21:59:58.200000Z",
        nonce="b" * 32,
    )
    tester_evidence = {
        "role_id": tester.role_id,
        "role_digest": tester.role_lens_sha256,
        "target": "workflow",
        "declared_argv": ["pytest", "-q"],
        "expected": "pass",
        "actual": "pass",
        "exit_code": 0,
        "evidence_refs": [tester_ref],
        "cases": [
            {"case_id": "suite", "status": "pass", "evidence_ref": tester_ref}
        ],
        "gate_status": "pass",
    }
    assert R._validate_evidence(
        data, tester, tester_evidence, {"tester-evidence": tester_ref}
    )["gate_status"] == "pass"
    bad_case = dict(tester_evidence)
    bad_case["cases"] = [
        {"case_id": "suite", "status": "hard-fail", "evidence_ref": tester_ref}
    ]
    with pytest.raises(R.DispatchReceiptError, match="aggregate status"):
        R._validate_evidence(
            data,
            tester,
            bad_case,
            {"tester-evidence": tester_ref},
        )

    monitor = workflows["monitor"].step("monitor")
    monitor_evidence = {
        "role_id": monitor.role_id,
        "role_digest": monitor.role_lens_sha256,
        "system": "fixture",
        "environment": "nonprod",
        "time_window": {
            "started_at": "2026-07-10T21:50:00Z",
            "ended_at": "2026-07-10T21:59:30Z",
        },
        "observations": [
            {
                "observation_id": "health",
                "health_state": "healthy",
                "evidence_ref": evidence_ref,
            }
        ],
        "evidence_refs": [evidence_ref],
        "health_state": "healthy",
        "gate_status": "pass",
    }
    with pytest.raises(R.DispatchReceiptError, match="authenticated observation adapter"):
        R._validate_evidence(
            data, monitor, monitor_evidence, {"monitor-evidence": evidence_ref}
        )
    with pytest.raises(R.DispatchReceiptError, match="aggregate state"):
        R._validate_evidence(
            data,
            monitor,
            {**monitor_evidence, "health_state": "degraded", "gate_status": "warn"},
            {"monitor-evidence": evidence_ref},
        )


def test_monitor_accepts_a_fresh_observation_window_that_predates_dispatch(
    tmp_path: Path,
) -> None:
    active_workflow = W.parse_workflow_structure(
        fixtures.plan(
            fixtures.row(
                "monitor",
                "runtime-monitor",
                execution_class="monitor-low",
                required_evidence="monitor-evidence",
                validator_required=False,
            )
        )
    )
    data = plugin_data(tmp_path)
    step = active_workflow.step("monitor")
    subject_ref, _subject_digest = protected_subject(
        data,
        active_workflow=active_workflow,
    )
    before_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "monitor",
        attempt=1,
        task_id="monitor",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="4" * 32,
    )
    after_ref = workspace_snapshot(data, "2026-07-10T22:00:01Z")
    audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=before_ref,
        after_ref=after_ref,
        recorded_at="2026-07-10T22:00:01.500000Z",
    )
    result_ref = R.create_result_record(
        data,
        active_workflow,
        "monitor",
        attempt=1,
        task_id="monitor",
        intent_ref=intent_ref,
        output_subject_ref=subject_ref,
        mutation_audit_ref=audit_ref,
        workspace_root=data.parent / "workspace",
        vehicle="verified-workflow-inline",
        child_id=None,
        provided_evidence=["monitor-evidence"],
        evidence={
            "role_id": step.role_id,
            "role_digest": step.role_lens_sha256,
            "system": "fixture",
            "environment": "nonprod",
            "time_window": {
                "started_at": "2026-07-10T21:50:00Z",
                "ended_at": "2026-07-10T21:59:30Z",
            },
            "observations": [
                {
                    "observation_id": "health",
                    "health_state": "degraded",
                    "evidence_ref": after_ref,
                }
            ],
            "evidence_refs": [after_ref],
            "health_state": "degraded",
            "gate_status": "warn",
        },
        execution={
            "kind": "agent-lens",
            "execution_class": step.execution_class,
            "profile_sha256": step.profile_sha256,
        },
        recorded_at="2026-07-10T22:00:02Z",
    )

    assert (
        R.load_protected_record(data, result_ref, "role-result")[0]["step_id"]
        == "monitor"
    )


def test_subject_readback_rejects_executable_bit_drift(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    original_ref, _original_digest = protected_subject(data)
    target = data.parent / "workspace" / "src" / "example.py"
    target.write_text("changed subject\n")
    changed_ref, _changed_digest = protected_subject(
        data,
        parent_refs=[original_ref],
    )
    target.chmod(0o755)

    with pytest.raises(R.DispatchReceiptError, match="subject Git change scope changed"):
        R._load_subject_record(
            data,
            changed_ref,
            workspace_root=data.parent / "workspace",
        )


def test_subject_paths_support_spaces_and_unicode_and_workspace_audits_hardlinks(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    subject_ref, _subject_digest = protected_subject(
        data,
        "docs/My Résumé.txt",
        active_workflow=active_workflow,
    )
    subject, _subject_bytes = R._load_subject_record(
        data,
        subject_ref,
        workspace_root=data.parent / "workspace",
    )
    source = data.parent / "workspace" / "docs" / "My Résumé.txt"
    hardlink = data.parent / "workspace" / "docs" / "Résumé copy.txt"
    os.link(source, hardlink)

    snapshot_ref = workspace_snapshot(data, "2026-07-10T22:00:00Z")
    snapshot, _snapshot_bytes = R._load_workspace_snapshot_record(
        data,
        snapshot_ref,
        workspace_root=data.parent / "workspace",
    )

    assert subject["paths"] == ["docs/My Résumé.txt"]
    assert snapshot["file_count"] >= 4


def test_workspace_snapshot_detects_same_content_hardlink_replacement(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    protected_subject(data)
    workspace = data.parent / "workspace"
    target = workspace / "src" / "example.py"
    before_ref = workspace_snapshot(data, "2026-07-10T22:00:00Z")
    before, _before_bytes = R._load_workspace_snapshot_record(data, before_ref)
    replacement = tmp_path / "same-content-replacement.py"
    replacement.write_bytes(target.read_bytes())
    target.unlink()
    os.link(replacement, target)
    after_ref = workspace_snapshot(data, "2026-07-10T22:00:01Z")
    after, _after_bytes = R._load_workspace_snapshot_record(data, after_ref)
    audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=before_ref,
        after_ref=after_ref,
        recorded_at="2026-07-10T22:00:02Z",
    )
    audit, _audit_bytes = R._load_mutation_audit_record(data, audit_ref)

    assert before["tree_sha256"] != after["tree_sha256"]
    assert audit["mutation_observed"] is True


def test_subject_record_supports_the_maximum_file_count(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    workspace = workspace_repo(data)
    bulk = workspace / "bulk"
    bulk.mkdir()
    for index in range(R.MAX_SUBJECT_FILES):
        name = f"{index:03d}-" + "x" * 180 + ".txt"
        (bulk / name).write_text(f"fixture {index}\n")
    subprocess.run(["git", "-C", str(workspace), "add", "bulk"], check=True)
    subprocess.run(
        ["git", "-C", str(workspace), "commit", "-qm", "add large fixture tree"],
        check=True,
    )
    run_ref = R.create_workflow_run_record(
        data,
        active_workflow,
        workspace_root=workspace,
        created_at="2026-07-10T21:59:57Z",
        nonce="e" * 32,
    )

    subject_ref = R.create_subject_record(
        data,
        workspace_root=workspace,
        subject_paths=["bulk"],
        workflow_run_ref=run_ref,
        created_at="2026-07-10T21:59:58Z",
    )
    subject, content = R._load_subject_record(
        data,
        subject_ref,
        workspace_root=workspace,
    )

    assert len(subject["files"]) == R.MAX_SUBJECT_FILES
    assert len(content) > 32 * 1024
    assert len(content) <= R.MAX_PROTECTED_RECORD_BYTES


@pytest.mark.parametrize("mutation", ["config", "index", "loose-object", "alternates"])
def test_workspace_audit_detects_git_control_mutation(
    tmp_path: Path,
    mutation: str,
) -> None:
    data = plugin_data(tmp_path)
    protected_subject(data)
    before_ref = workspace_snapshot(data, "2026-07-10T22:00:00Z")
    workspace = data.parent / "workspace"
    if mutation == "config":
        with (workspace / ".git" / "config").open("a", encoding="utf-8") as handle:
            handle.write("\n[fixture]\n\tchanged = true\n")
    elif mutation == "index":
        subprocess.run(
            ["git", "-C", str(workspace), "add", "src/example.py"],
            check=True,
        )
    elif mutation == "loose-object":
        subprocess.run(
            ["git", "-C", str(workspace), "hash-object", "-w", "--stdin"],
            input=b"unreferenced object\n",
            check=True,
            stdout=subprocess.PIPE,
        )
    else:
        info = workspace / ".git" / "objects" / "info"
        info.mkdir(exist_ok=True)
        (info / "alternates").write_text("../other-objects\n")
    after_ref = workspace_snapshot(data, "2026-07-10T22:00:01Z")

    audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=before_ref,
        after_ref=after_ref,
        recorded_at="2026-07-10T22:00:02Z",
    )

    audit, _audit_bytes = R._load_mutation_audit_record(data, audit_ref)
    assert audit["mutation_observed"] is True


def test_gate_authoritative_plugin_data_cannot_be_repo_local(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    protected_subject(data)
    workspace = data.parent / "workspace"
    repo_data = workspace / ".codex" / "verified-workflows"
    repo_data.mkdir(mode=0o700, parents=True)

    with pytest.raises(R.DispatchReceiptError, match="outside the repository"):
        R.create_workspace_snapshot_record(
            repo_data,
            workspace_root=workspace,
            created_at="2026-07-10T22:00:00Z",
        )


def test_git_object_metadata_summary_obeys_file_ceiling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = plugin_data(tmp_path)
    protected_subject(data)
    workspace = data.parent / "workspace"
    baseline = R._git_control_snapshot(workspace)["git_control_file_count"]
    fanout = workspace / ".git" / "objects" / "aa"
    fanout.mkdir(exist_ok=True)
    for index in range(3):
        (fanout / f"{index:038x}").write_bytes(b"object")
    monkeypatch.setattr(E, "MAX_AUDIT_FILES", baseline + 2)

    with pytest.raises(R.DispatchReceiptError, match="exceeds"):
        R._git_control_snapshot(workspace)


def test_git_control_symlink_fails_closed(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    protected_subject(data)
    workspace = data.parent / "workspace"
    config = workspace / ".git" / "config"
    target = tmp_path / "external-git-config"
    config.rename(target)
    config.symlink_to(target)

    with pytest.raises(R.DispatchReceiptError, match="must not be symlinks"):
        R._git_control_snapshot(workspace)


def test_inline_fallback_is_truthful_and_required_independence_blocks(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    preferred = workflow()
    chain = protected_chain(data, preferred, vehicle="verified-workflow-inline")
    receipt = R.build_inline_receipt(
        data,
        preferred,
        "security",
        attempt=1,
        task_id="security-review",
        **chain,
    )
    assert receipt["execution"]["runtime_selection_attested"] is False

    required = workflow(independence="required", vehicle="auto")
    required_data = plugin_data(tmp_path / "required")
    required_chain = protected_chain(
        required_data, required, vehicle="verified-workflow-inline"
    )
    with pytest.raises(R.DispatchReceiptError, match="required independence"):
        R.build_inline_receipt(
            required_data,
            required,
            "security",
            attempt=1,
            task_id="security-review",
            **required_chain,
        )


def test_normalization_transaction_blocks_replay_and_supports_retry(
    tmp_path: Path,
) -> None:
    data, active_workflow, reference, receipt = persisted_subagent_receipt(tmp_path)
    raw_digest = receipt["child"]["raw_pair_sha256"]

    assert R.persist_normalized(data, receipt, raw_pair_sha256=raw_digest) == reference
    replay = {**receipt, "attempt": 2, "task_id": "different-intent"}
    with pytest.raises(R.DispatchReceiptError, match="conflicts"):
        R.persist_normalized(data, replay, raw_pair_sha256=raw_digest)
    run_sha256 = receipt["workflow_run_sha256"]
    assert R.load_normalized_by_identity(
        data, active_workflow.sha256, run_sha256, "security", 1
    )
    assert (
        R.load_normalized_by_identity(
            data, active_workflow.sha256, run_sha256, "security", 2
        )
        is None
    )


def test_two_runs_of_one_workflow_keep_independent_receipt_namespaces(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    workspace = workspace_repo(data)
    target = workspace / "src" / "example.py"
    target.parent.mkdir(parents=True)
    target.write_text("subject fixture\n")
    run_refs = [
        R.create_workflow_run_record(
            data,
            active_workflow,
            workspace_root=workspace,
            created_at="2026-07-10T21:59:57Z",
            nonce=character * 32,
        )
        for character in ("1", "2")
    ]
    normalized_refs: list[str] = []
    run_digests: list[str] = []
    for run_ref in run_refs:
        chain = protected_chain(
            data,
            active_workflow,
            vehicle="verified-workflow-inline",
            workflow_run_ref=run_ref,
        )
        receipt = R.build_inline_receipt(
            data,
            active_workflow,
            "security",
            attempt=1,
            task_id="security-review",
            **chain,
        )
        normalized_refs.append(R.persist_normalized(data, receipt))
        run_digests.append(receipt["workflow_run_sha256"])

    assert len(set(run_digests)) == 2
    assert len(set(normalized_refs)) == 2
    for reference in normalized_refs:
        R.validate_normalized_receipt(data, reference, active_workflow)


def test_protected_evidence_cannot_be_substituted_from_another_run(
    tmp_path: Path,
) -> None:
    active_workflow = W.parse_workflow_structure(
        fixtures.plan(
            fixtures.row(
                "integrate",
                "root",
                mutation="root-only",
                required_evidence="diff",
            )
        )
    )
    data = plugin_data(tmp_path)
    first_subject_ref, _first_digest = protected_subject(
        data,
        "src/integrate.py",
        active_workflow=active_workflow,
    )
    second_run_ref = R.create_workflow_run_record(
        data,
        active_workflow,
        workspace_root=data.parent / "workspace",
        created_at="2026-07-10T21:59:57Z",
        nonce="f" * 32,
    )
    second_subject_ref, _second_digest = protected_subject(
        data,
        "src/integrate.py",
        active_workflow=active_workflow,
        workflow_run_ref=second_run_ref,
    )
    before_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "integrate",
        attempt=1,
        task_id="integrate",
        subject_ref=second_subject_ref,
        workspace_snapshot_ref=before_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="a" * 32,
    )

    with pytest.raises(R.DispatchReceiptError, match="another workflow run"):
        R.create_result_record(
            data,
            active_workflow,
            "integrate",
            attempt=1,
            task_id="integrate",
            intent_ref=intent_ref,
            output_subject_ref=second_subject_ref,
            mutation_audit_ref=None,
            workspace_root=None,
            vehicle="root",
            child_id=None,
            provided_evidence=["diff"],
            evidence={"evidence_refs": {"diff": first_subject_ref}, "findings": []},
            execution={"kind": "root"},
            recorded_at="2026-07-10T22:00:01Z",
        )


@pytest.mark.parametrize("mutation", ["stage", "same-commit-checkout", "git-config"])
def test_final_gate_git_policy_detects_root_git_control_mutation(
    tmp_path: Path,
    mutation: str,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    subject_ref, _subject_digest = protected_subject(
        data, active_workflow=active_workflow
    )
    subject, _subject_bytes = R._load_subject_record(data, subject_ref)
    workspace = data.parent / "workspace"
    if mutation == "stage":
        subprocess.run(
            ["git", "-C", str(workspace), "add", "src/example.py"],
            check=True,
        )
        expected = "Git index changed"
    elif mutation == "same-commit-checkout":
        subprocess.run(
            ["git", "-C", str(workspace), "branch", "same-commit"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(workspace), "checkout", "-q", "same-commit"],
            check=True,
        )
        expected = "Git HEAD controls changed"
    else:
        with (workspace / ".git" / "config").open("a", encoding="utf-8") as handle:
            handle.write("\n[fixture]\n\tchanged = true\n")
        expected = "Git controls changed"
    with pytest.raises(R.DispatchReceiptError, match=expected):
        R._load_workflow_run_record(
            data,
            subject["workflow_run_ref"],
            workflow=active_workflow,
            workspace_root=workspace,
            enforce_git_policy=True,
        )


def test_cycle_boolean_is_rejected(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    subject_ref, _subject_digest = protected_subject(data)
    before_snapshot_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    with pytest.raises(R.DispatchReceiptError, match="attempt"):
        R.create_intent_record(
            data,
            workflow(),
            "security",
            attempt=True,
            task_id="security-review",
            subject_ref=subject_ref,
            workspace_snapshot_ref=before_snapshot_ref,
            created_at="2026-07-10T22:00:00Z",
            nonce="f" * 32,
        )


def test_identical_intent_inputs_are_content_addressed_idempotently(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    subject_ref, _subject_digest = protected_subject(
        data,
        active_workflow=active_workflow,
    )
    before_snapshot_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    kwargs = {
        "attempt": 1,
        "task_id": "security-review",
        "subject_ref": subject_ref,
        "workspace_snapshot_ref": before_snapshot_ref,
        "created_at": "2026-07-10T22:00:00Z",
        "nonce": "8" * 32,
    }

    first = R.create_intent_record(
        data,
        active_workflow,
        "security",
        **kwargs,
    )
    second = R.create_intent_record(
        data,
        active_workflow,
        "security",
        **kwargs,
    )

    assert first == second


@pytest.mark.parametrize(
    "unresolved",
    [
        finding("P1"),
        {**finding("P2"), "finding_id": "finding-security", "category": "security"},
    ],
)
def test_dispatcher_hard_finding_follow_up_is_directly_persistable(
    tmp_path: Path,
    unresolved: dict[str, object],
) -> None:
    data, active_workflow, previous_ref, _receipt = persisted_subagent_receipt(
        tmp_path,
        findings=[unresolved],
    )
    state = {
        "security": W.StepState(
            status="needs-follow-up",
            cycle=1,
            result_ref=previous_ref,
            finding_refs=(str(unresolved["finding_id"]),),
        )
    }
    previous_receipt, _previous_bytes = R.load_normalized_receipt(data, previous_ref)
    emitted = W.emit_intents(
        active_workflow,
        state,
        workflow_run_sha256=previous_receipt["workflow_run_sha256"],
    )["intents"][0]
    subject_ref, _subject_digest = protected_subject(
        data,
        active_workflow=active_workflow,
        parent_refs=[previous_receipt["output_subject_ref"]],
    )
    before_snapshot_ref = workspace_snapshot(data, "2026-07-10T22:09:59Z")

    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        emitted["step_id"],
        attempt=emitted["cycle"],
        task_id="security-review",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_snapshot_ref,
        intent_kind=emitted["intent"],
        previous_receipt_ref=emitted["previous_receipt_ref"],
        finding_refs=emitted["finding_refs"],
        created_at="2026-07-10T22:10:00Z",
        nonce="7" * 32,
    )

    intent, _intent_bytes = R._load_intent_record(
        data,
        intent_ref,
        active_workflow,
        "security",
        2,
        "security-review",
    )
    assert intent["intent_kind"] == "follow-up"
    assert intent["previous_receipt_ref"] == previous_ref
    assert intent["finding_refs"] == [str(unresolved["finding_id"])]


def test_follow_up_subject_must_descend_from_prior_result(tmp_path: Path) -> None:
    unresolved = finding("P2")
    data, active_workflow, previous_ref, _receipt = persisted_subagent_receipt(
        tmp_path,
        findings=[unresolved],
    )
    previous_receipt, _previous_bytes = R.load_normalized_receipt(data, previous_ref)
    previous_subject, _previous_subject_bytes = R._load_subject_record(
        data, previous_receipt["output_subject_ref"]
    )
    disconnected_ref = R.create_subject_record(
        data,
        workspace_root=data.parent / "workspace",
        subject_paths=["src/example.py"],
        workflow_run_ref=previous_subject["workflow_run_ref"],
        created_at="2026-07-10T22:09:58Z",
    )
    before_snapshot_ref = workspace_snapshot(data, "2026-07-10T22:09:59Z")

    with pytest.raises(R.DispatchReceiptError, match="does not descend"):
        R.create_intent_record(
            data,
            active_workflow,
            "security",
            attempt=2,
            task_id="security-review",
            subject_ref=disconnected_ref,
            workspace_snapshot_ref=before_snapshot_ref,
            intent_kind="follow-up",
            previous_receipt_ref=previous_ref,
            finding_refs=[str(unresolved["finding_id"])],
            created_at="2026-07-10T22:10:00Z",
            nonce="e" * 32,
        )


def test_follow_up_cannot_splice_a_revised_execution_class(tmp_path: Path) -> None:
    unresolved = finding("P2")
    data, active_workflow, previous_ref, previous_receipt = persisted_subagent_receipt(
        tmp_path,
        findings=[unresolved],
    )
    revised_workflow = W.parse_workflow_structure(
        fixtures.plan(fixtures.row("security", execution_class="review-max"))
    )
    assert revised_workflow.sha256 != active_workflow.sha256
    before_snapshot_ref = workspace_snapshot(data, "2026-07-10T22:09:59Z")

    with pytest.raises(R.DispatchReceiptError, match="workflow"):
        R.create_intent_record(
            data,
            revised_workflow,
            "security",
            attempt=2,
            task_id="security-review",
            subject_ref=previous_receipt["output_subject_ref"],
            workspace_snapshot_ref=before_snapshot_ref,
            intent_kind="follow-up",
            previous_receipt_ref=previous_ref,
            finding_refs=[str(unresolved["finding_id"])],
            created_at="2026-07-10T22:10:00Z",
            nonce="0" * 32,
        )


def test_deterministic_receipt_is_pinned_and_model_free(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    active_workflow = deterministic_workflow()
    step = active_workflow.step("schema-check")
    subject_ref, _subject_digest = protected_subject(
        data,
        "src/schema.py",
        active_workflow=active_workflow,
    )
    before_snapshot_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_snapshot_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="4" * 32,
    )
    output_ref = command_output(
        data,
        active_workflow,
        intent_ref,
        exit_code=0,
        recorded_at="2026-07-10T22:00:00.500000Z",
    )
    after_snapshot_ref = workspace_snapshot(data, "2026-07-10T22:00:00.600000Z")
    mutation_audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=before_snapshot_ref,
        after_ref=after_snapshot_ref,
        recorded_at="2026-07-10T22:00:00.700000Z",
    )
    result_ref = R.create_result_record(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        intent_ref=intent_ref,
        output_subject_ref=subject_ref,
        mutation_audit_ref=mutation_audit_ref,
        workspace_root=data.parent / "workspace",
        vehicle="deterministic-tool",
        child_id=None,
        provided_evidence=["tester-evidence"],
        evidence={
            "role_id": step.role_id,
            "role_digest": step.role_lens_sha256,
            "target": "schema",
            "declared_argv": list(step.command),
            "expected": "valid",
            "actual": "pass",
            "exit_code": 0,
            "evidence_refs": [output_ref],
            "cases": [
                {
                    "case_id": "schema-check",
                    "status": "pass",
                    "evidence_ref": output_ref,
                }
            ],
            "gate_status": "pass",
        },
        execution={
            "kind": "deterministic-validator",
            "argv": list(step.command),
            "implementation_sha256": step.command_implementation_sha256,
            "evidence_schema_sha256": step.evidence_schema_sha256,
            "cwd": "repo-root",
            "timeout_seconds": step.command_timeout_seconds,
            "output_limit_bytes": step.command_output_limit_bytes,
            "output_ref": output_ref,
            "exit_code": 0,
        },
        recorded_at="2026-07-10T22:00:01Z",
    )
    verification_ref = R.create_root_verification_record(
        data,
        result_ref=result_ref,
        verifier_session_id="Session-1",
        verifier_turn_id="Turn-1",
        resolution_refs=[],
        recorded_at="2026-07-10T22:00:02Z",
    )
    receipt = R.build_deterministic_receipt(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        intent_ref=intent_ref,
        result_ref=result_ref,
        root_verification_ref=verification_ref,
    )
    reference = R.persist_normalized(data, receipt)

    assert receipt["execution"]["model_fields_present"] is False
    assert receipt["execution"]["command"] == list(step.command)
    R.validate_normalized_receipt(data, reference, active_workflow)


def test_required_deploy_observation_waits_for_authenticated_adapter(
    tmp_path: Path,
) -> None:
    data, active_workflow, context = deploy_fixture(tmp_path)
    with pytest.raises(R.DispatchReceiptError, match="authenticated observation adapter"):
        R.create_result_record(
            data,
            active_workflow,
            "deploy",
            attempt=1,
            task_id="deploy",
            intent_ref=str(context["intent_ref"]),
            output_subject_ref=str(context["subject_ref"]),
            mutation_audit_ref=str(context["audit_ref"]),
            workspace_root=data.parent / "workspace",
            vehicle="verified-workflow-inline",
            child_id=None,
            provided_evidence=["deploy-evidence"],
            evidence=context["evidence"],
            execution=context["execution"],
            recorded_at="2026-07-10T22:10:02Z",
        )


def test_optional_deploy_observation_consumes_protected_prerequisite_as_advisory(
    tmp_path: Path,
) -> None:
    data, active_workflow, context = deploy_fixture(
        tmp_path,
        validator_required=False,
    )
    result_ref = R.create_result_record(
        data,
        active_workflow,
        "deploy",
        attempt=1,
        task_id="deploy",
        intent_ref=str(context["intent_ref"]),
        output_subject_ref=str(context["subject_ref"]),
        mutation_audit_ref=str(context["audit_ref"]),
        workspace_root=data.parent / "workspace",
        vehicle="verified-workflow-inline",
        child_id=None,
        provided_evidence=["deploy-evidence"],
        evidence=context["evidence"],
        execution=context["execution"],
        recorded_at="2026-07-10T22:10:02Z",
    )

    result, _result_bytes = R.load_protected_record(data, result_ref, "role-result")
    assert result["evidence"]["gate_status"] == "warn"


@pytest.mark.parametrize(
    ("updates", "match"),
    [
        ({"remote": "evil.example/infiquetra/example"}, "eligibility"),
        ({"environment": "production"}, "eligibility"),
        ({"default_branch": "develop"}, "eligibility"),
        ({"commit_sha": "0" * 40}, "workflow run commit"),
    ],
)
def test_deploy_policy_rejects_ineligible_or_unrelated_runs(
    tmp_path: Path,
    updates: dict[str, object],
    match: str,
) -> None:
    data, active_workflow, context = deploy_fixture(
        tmp_path,
        validator_required=False,
    )
    evidence = {**context["evidence"], **updates}

    with pytest.raises(R.DispatchReceiptError, match=match):
        R.create_result_record(
            data,
            active_workflow,
            "deploy",
            attempt=1,
            task_id="deploy",
            intent_ref=str(context["intent_ref"]),
            output_subject_ref=str(context["subject_ref"]),
            mutation_audit_ref=str(context["audit_ref"]),
            workspace_root=data.parent / "workspace",
            vehicle="verified-workflow-inline",
            child_id=None,
            provided_evidence=["deploy-evidence"],
            evidence=evidence,
            execution=context["execution"],
            recorded_at="2026-07-10T22:10:02Z",
        )


def test_large_deterministic_stdout_retains_only_typed_projection_and_hashes(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = deterministic_workflow(
        output_limit_bytes=R.dispatch.renderer.MAX_DETERMINISTIC_OUTPUT_BYTES
    )
    subject_ref, _subject_digest = protected_subject(
        data,
        "src/schema.py",
        active_workflow=active_workflow,
    )
    before_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="a" * 32,
    )
    output_payload: dict[str, object] = {
        "target": "schema",
        "expected": "valid",
        "actual": "pass",
        "cases": [
            {
                "case_id": f"case-{index:04d}-" + "x" * 110,
                "status": "pass",
            }
            for index in range(1024)
        ],
        "gate_status": "pass",
    }

    output_ref = command_output(
        data,
        active_workflow,
        intent_ref,
        exit_code=0,
        payload=output_payload,
        recorded_at="2026-07-10T22:00:00.500000Z",
    )
    output, content = R._load_command_output_record(
        data,
        output_ref,
        workflow=active_workflow,
    )

    assert len(content) > R.MAX_RECEIPT_BYTES
    assert len(content) <= R.MAX_PROTECTED_RECORD_BYTES
    assert output["parsed_output"] == output_payload
    assert "stdout_text" not in output
    assert "stderr_text" not in output


def test_untrusted_stderr_is_hashed_but_never_retained(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = deterministic_workflow(
        output_limit_bytes=R.dispatch.renderer.MAX_DETERMINISTIC_OUTPUT_BYTES
    )
    subject_ref, _subject_digest = protected_subject(
        data,
        "src/schema.py",
        active_workflow=active_workflow,
    )
    before_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="1" * 32,
    )

    output_ref = command_output(
        data,
        active_workflow,
        intent_ref,
        exit_code=0,
        recorded_at="2026-07-10T22:00:00.500000Z",
        stderr_text="\x7f" * 500_000,
    )
    output, content = R._load_command_output_record(
        data,
        output_ref,
        workflow=active_workflow,
    )

    assert output["stderr_bytes"] == 500_000
    assert output["stderr_sha256"] == hashlib.sha256(b"\x7f" * 500_000).hexdigest()
    assert b"\x7f" not in content
    assert "stdout_text" not in output
    assert "stderr_text" not in output


@pytest.mark.parametrize(
    "secret_output",
    [
        "AKIAABCDEFGHIJKLMNOP",
        "-----BEGIN PRIVATE KEY-----",
        "Basic dXNlcjpwYXNzd29yZA==",
        "https://user:password@example.invalid/path",
    ],
)
def test_secret_shaped_command_streams_are_never_persisted(
    tmp_path: Path,
    secret_output: str,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = deterministic_workflow()
    subject_ref, _subject_digest = protected_subject(
        data,
        "src/schema.py",
        active_workflow=active_workflow,
    )
    before_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="2" * 32,
    )
    output_ref = command_output(
        data,
        active_workflow,
        intent_ref,
        exit_code=0,
        recorded_at="2026-07-10T22:00:00.500000Z",
        stderr_text=secret_output,
    )
    output, content = R._load_command_output_record(
        data,
        output_ref,
        workflow=active_workflow,
    )

    assert secret_output.encode() not in content
    assert output["stderr_sha256"] == hashlib.sha256(secret_output.encode()).hexdigest()
    assert "stderr_text" not in output


def test_deterministic_output_cannot_be_replayed_or_rewritten_as_evidence(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = deterministic_workflow()
    step = active_workflow.step("schema-check")
    first_subject_ref, _first_digest = protected_subject(
        data,
        "src/schema.py",
        active_workflow=active_workflow,
    )
    first_before_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    first_intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        subject_ref=first_subject_ref,
        workspace_snapshot_ref=first_before_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="b" * 32,
    )
    retained = {
        "target": "schema",
        "expected": "valid",
        "actual": "pass",
        "cases": [{"case_id": "schema-check", "status": "pass"}],
        "gate_status": "pass",
    }
    output_ref = command_output(
        data,
        active_workflow,
        first_intent_ref,
        exit_code=0,
        payload=retained,
        recorded_at="2026-07-10T22:00:00.500000Z",
    )
    first_after_ref = workspace_snapshot(data, "2026-07-10T22:00:00.600000Z")
    first_audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=first_before_ref,
        after_ref=first_after_ref,
        recorded_at="2026-07-10T22:00:00.700000Z",
    )
    invented = deterministic_evidence(step, output_ref, retained, exit_code=0)
    invented["actual"] = "invented-success"

    with pytest.raises(R.DispatchReceiptError, match="contradicts retained"):
        R.create_result_record(
            data,
            active_workflow,
            "schema-check",
            attempt=1,
            task_id="schema-check",
            intent_ref=first_intent_ref,
            output_subject_ref=first_subject_ref,
            mutation_audit_ref=first_audit_ref,
            workspace_root=data.parent / "workspace",
            vehicle="deterministic-tool",
            child_id=None,
            provided_evidence=["tester-evidence"],
            evidence=invented,
            execution={
                "kind": "deterministic-validator",
                "argv": list(step.command),
                "implementation_sha256": step.command_implementation_sha256,
                "evidence_schema_sha256": step.evidence_schema_sha256,
                "cwd": "repo-root",
                "timeout_seconds": step.command_timeout_seconds,
                "output_limit_bytes": step.command_output_limit_bytes,
                "output_ref": output_ref,
                "exit_code": 0,
            },
            recorded_at="2026-07-10T22:00:01Z",
        )

    second_run_ref = R.create_workflow_run_record(
        data,
        active_workflow,
        workspace_root=data.parent / "workspace",
        created_at="2026-07-10T21:59:57Z",
        nonce="c" * 32,
    )
    second_subject_ref, _second_digest = protected_subject(
        data,
        "src/schema.py",
        active_workflow=active_workflow,
        workflow_run_ref=second_run_ref,
    )
    second_before_ref = workspace_snapshot(data, "2026-07-10T22:09:59Z")
    second_intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        subject_ref=second_subject_ref,
        workspace_snapshot_ref=second_before_ref,
        created_at="2026-07-10T22:10:00Z",
        nonce="d" * 32,
    )
    second_after_ref = workspace_snapshot(data, "2026-07-10T22:10:00.600000Z")
    second_audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=second_before_ref,
        after_ref=second_after_ref,
        recorded_at="2026-07-10T22:10:00.700000Z",
    )

    with pytest.raises(R.DispatchReceiptError, match="execution contract"):
        R.create_result_record(
            data,
            active_workflow,
            "schema-check",
            attempt=1,
            task_id="schema-check",
            intent_ref=second_intent_ref,
            output_subject_ref=second_subject_ref,
            mutation_audit_ref=second_audit_ref,
            workspace_root=data.parent / "workspace",
            vehicle="deterministic-tool",
            child_id=None,
            provided_evidence=["tester-evidence"],
            evidence=deterministic_evidence(step, output_ref, retained, exit_code=0),
            execution={
                "kind": "deterministic-validator",
                "argv": list(step.command),
                "implementation_sha256": step.command_implementation_sha256,
                "evidence_schema_sha256": step.evidence_schema_sha256,
                "cwd": "repo-root",
                "timeout_seconds": step.command_timeout_seconds,
                "output_limit_bytes": step.command_output_limit_bytes,
                "output_ref": output_ref,
                "exit_code": 0,
            },
            recorded_at="2026-07-10T22:10:01Z",
        )


def test_custom_registry_validator_executes_real_command_end_to_end(
    tmp_path: Path,
) -> None:
    import test_role_registry as registry_fixtures

    data = plugin_data(tmp_path)
    workspace = workspace_repo(data)
    registry_path, roles_dir, registry_payload = (
        registry_fixtures._synthetic_registry(workspace)
    )
    expected_output = {
        "target": "schema",
        "expected": "valid",
        "actual": "pass",
        "cases": [{"case_id": "bounded-check", "status": "pass"}],
        "gate_status": "pass",
    }
    implementation = workspace / "scripts" / "check.py"
    implementation.write_text(
        f"print({(json.dumps(expected_output, sort_keys=True))!r})\n",
        encoding="utf-8",
    )
    registry_payload["roles"][0]["command"]["implementation"]["sha256"] = (
        hashlib.sha256(implementation.read_bytes()).hexdigest()
    )
    registry_path.write_text(
        yaml.safe_dump(registry_payload, sort_keys=False),
        encoding="utf-8",
    )
    custom_registry = W.renderer.load_role_registry(
        registry_path,
        roles_dir,
        expected_role_ids=None,
    )
    deterministic_contract_sha256 = W._deterministic_contract_sha256(
        custom_registry.role("bounded-validator")
    )
    subject_path = workspace / "src" / "schema.py"
    subject_path.parent.mkdir()
    subject_path.write_text("schema fixture\n")
    plan_path = workspace / "verified-plan.md"
    plan_path.write_text(
        fixtures.plan(
            [
                "bounded-check",
                "-",
                "-",
                "bounded-validator",
                "deterministic-validator",
                    "n/a",
                    "-",
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
                deterministic_contract_sha256,
            ]
        )
    )
    subprocess.run(["git", "-C", str(workspace), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(workspace), "commit", "-qm", "add validator fixture"],
        check=True,
    )
    active_workflow = R._load_workflow(
        plan_path,
        registry_path=registry_path,
        roles_dir=roles_dir,
    )
    step = active_workflow.step("bounded-check")
    subject_ref, _subject_digest = protected_subject(
        data,
        "src/schema.py",
        active_workflow=active_workflow,
    )
    before_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "bounded-check",
        attempt=1,
        task_id="bounded-check",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="8" * 32,
    )
    completed = subprocess.run(
        list(step.command),
        cwd=workspace,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=step.command_timeout_seconds,
        check=False,
    )
    command_dir = tmp_path / "real-command-output"
    command_dir.mkdir()
    stdout_file = command_dir / "stdout.json"
    stderr_file = command_dir / "stderr.txt"
    stdout_file.write_bytes(completed.stdout)
    stderr_file.write_bytes(completed.stderr)
    stdout_file.chmod(0o600)
    stderr_file.chmod(0o600)
    output_ref = R.create_command_output_record(
        data,
        active_workflow,
        "bounded-check",
        attempt=1,
        task_id="bounded-check",
        intent_ref=intent_ref,
        stdout_file=stdout_file,
        stderr_file=stderr_file,
        exit_code=completed.returncode,
        output_limit_bytes=step.command_output_limit_bytes,
        recorded_at="2026-07-10T22:00:00.500000Z",
    )
    after_ref = workspace_snapshot(data, "2026-07-10T22:00:01Z")
    audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=before_ref,
        after_ref=after_ref,
        recorded_at="2026-07-10T22:00:01.500000Z",
    )
    result_ref = R.create_result_record(
        data,
        active_workflow,
        "bounded-check",
        attempt=1,
        task_id="bounded-check",
        intent_ref=intent_ref,
        output_subject_ref=subject_ref,
        mutation_audit_ref=audit_ref,
        workspace_root=workspace,
        vehicle="deterministic-tool",
        child_id=None,
        provided_evidence=["tester-evidence"],
        evidence=deterministic_evidence(
            step,
            output_ref,
            expected_output,
            exit_code=completed.returncode,
        ),
        execution={
            "kind": "deterministic-validator",
            "argv": list(step.command),
            "implementation_sha256": step.command_implementation_sha256,
            "evidence_schema_sha256": step.evidence_schema_sha256,
            "cwd": "repo-root",
            "timeout_seconds": step.command_timeout_seconds,
            "output_limit_bytes": step.command_output_limit_bytes,
            "output_ref": output_ref,
            "exit_code": completed.returncode,
        },
        recorded_at="2026-07-10T22:00:02Z",
    )
    verification_ref = R.create_root_verification_record(
        data,
        result_ref=result_ref,
        verifier_session_id="Session-1",
        verifier_turn_id="Validator-Turn",
        resolution_refs=[],
        recorded_at="2026-07-10T22:00:03Z",
    )
    receipt = R.build_deterministic_receipt(
        data,
        active_workflow,
        "bounded-check",
        attempt=1,
        task_id="bounded-check",
        intent_ref=intent_ref,
        result_ref=result_ref,
        root_verification_ref=verification_ref,
    )
    reference = R.persist_normalized(data, receipt)
    import gate_evaluator as gate

    assert completed.returncode == 0
    assert gate.evaluate_gate(
        {
            "schema_version": 1,
            "workflow_sha256": active_workflow.sha256,
            "cycle": 1,
            "subject_ref": subject_ref,
            "steps": [{"step_id": "bounded-check", "receipt_ref": reference}],
            "advisory": [],
        },
        workflow=active_workflow,
        plugin_data=data,
        workspace_root=workspace,
        enforce_selection_policy=False,
    )["verdict"] == "pass"


@pytest.mark.parametrize("mutation", ["git-config", "ignored-file"])
def test_deterministic_validator_mutation_is_rejected(
    tmp_path: Path,
    mutation: str,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = deterministic_workflow()
    step = active_workflow.step("schema-check")
    workspace = workspace_repo(data)
    (workspace / "src").mkdir(exist_ok=True)
    (workspace / "src" / "schema.py").write_text("subject fixture\n")
    (workspace / ".gitignore").write_text("*.ignored\n")
    workflow_run_ref = R.create_workflow_run_record(
        data,
        active_workflow,
        workspace_root=workspace,
        created_at="2026-07-10T21:59:57Z",
        nonce="0" * 32,
    )
    subject_ref = R.create_subject_record(
        data,
        workspace_root=workspace,
        subject_paths=[".gitignore", "src/schema.py"],
        workflow_run_ref=workflow_run_ref,
        created_at="2026-07-10T21:59:58Z",
    )
    before_snapshot_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "schema-check",
        attempt=1,
        task_id="schema-check",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_snapshot_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="f" * 32,
    )
    if mutation == "git-config":
        with (workspace / ".git" / "config").open("a", encoding="utf-8") as handle:
            handle.write("\n[fixture]\n\tchanged = true\n")
    else:
        (workspace / "cache.ignored").write_text("changed\n")
    after_snapshot_ref = workspace_snapshot(data, "2026-07-10T22:00:00.500000Z")
    audit_ref = R.create_mutation_audit_record(
        data,
        before_ref=before_snapshot_ref,
        after_ref=after_snapshot_ref,
        recorded_at="2026-07-10T22:00:00.600000Z",
    )
    output_ref = command_output(
        data,
        active_workflow,
        intent_ref,
        exit_code=0,
        recorded_at="2026-07-10T22:00:00.700000Z",
    )

    with pytest.raises(R.DispatchReceiptError, match="mutation audit is invalid"):
        R.create_result_record(
            data,
            active_workflow,
            "schema-check",
            attempt=1,
            task_id="schema-check",
            intent_ref=intent_ref,
            output_subject_ref=subject_ref,
            mutation_audit_ref=audit_ref,
            workspace_root=workspace,
            vehicle="deterministic-tool",
            child_id=None,
            provided_evidence=["tester-evidence"],
            evidence={
                "role_id": step.role_id,
                "role_digest": step.role_lens_sha256,
                "target": "schema",
                "declared_argv": list(step.command),
                "expected": "valid",
                "actual": "pass",
                "exit_code": 0,
                "evidence_refs": [output_ref],
                "cases": [
                    {
                        "case_id": "schema-check",
                        "status": "pass",
                        "evidence_ref": output_ref,
                    }
                ],
                "gate_status": "pass",
            },
            execution={
                "kind": "deterministic-validator",
                "argv": list(step.command),
                "implementation_sha256": step.command_implementation_sha256,
                "evidence_schema_sha256": step.evidence_schema_sha256,
                "cwd": "repo-root",
                "timeout_seconds": step.command_timeout_seconds,
                "output_limit_bytes": step.command_output_limit_bytes,
                "output_ref": output_ref,
                "exit_code": 0,
            },
            recorded_at="2026-07-10T22:00:01Z",
        )


def test_stale_incomplete_raw_prune_is_bounded_dry_run_first(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    start = raw("start", active_workflow)
    R.hook_receipt.persist_event(start, data)
    leaf = (
        data
        / "receipts"
        / "v1"
        / "raw"
        / R._hash_segment("Session-1")
        / R._hash_segment("Child-1")
        / R._hash_segment("Turn-1")
    )
    old = dt.datetime(2026, 7, 10, 20, 0, tzinfo=dt.UTC).timestamp()
    os.utime(leaf / "start.json", (old, old))
    temporary = leaf / ".start.json.1234.0123456789abcdef.tmp"
    temporary.write_bytes(b"partial")
    temporary.chmod(0o600)
    os.utime(temporary, (old, old))

    def now() -> dt.datetime:
        return dt.datetime(2026, 7, 12, 23, 0, tzinfo=dt.UTC)

    with pytest.raises(R.DispatchReceiptError, match="entry ceiling"):
        R.prune_raw_receipts(
            data,
            older_than_seconds=R.MAX_EVENT_AGE_SECONDS,
            max_entries=4,
            now=now,
        )
    with pytest.raises(R.DispatchReceiptError, match="byte ceiling"):
        R.prune_raw_receipts(
            data,
            older_than_seconds=R.MAX_EVENT_AGE_SECONDS,
            max_bytes=1,
            now=now,
        )

    planned = R.prune_raw_receipts(
        data, older_than_seconds=R.MAX_EVENT_AGE_SECONDS, now=now
    )
    assert planned["apply"] is False
    assert planned["file_count"] == 1
    assert (leaf / "start.json").exists()

    applied = R.prune_raw_receipts(
        data,
        older_than_seconds=R.MAX_EVENT_AGE_SECONDS,
        apply=True,
        expected_plan_sha256=planned["plan_sha256"],
        now=now,
    )
    assert applied["claim"] == "raw-prune-applied"
    assert (leaf / "start.json").exists()
    assert not temporary.exists()
    R.create_raw_abandonment_record(
        data,
        parent_session_id="Session-1",
        child_id="Child-1",
        turn_id="Turn-1",
        reason="operator-confirmed",
        recorded_at="2026-07-12T22:00:00Z",
    )
    abandoned_plan = R.prune_raw_receipts(
        data, older_than_seconds=R.MAX_EVENT_AGE_SECONDS, now=now
    )
    assert abandoned_plan["file_count"] == 1
    assert R.prune_raw_receipts(
        data,
        older_than_seconds=R.MAX_EVENT_AGE_SECONDS,
        apply=True,
        expected_plan_sha256=abandoned_plan["plan_sha256"],
        now=now,
    )["file_count"] == 1
    assert not leaf.exists()


def test_stop_only_and_lock_only_raw_leaves_are_safely_prunable(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    R.hook_receipt.persist_event(raw("stop", active_workflow), data)
    raw_root = data / "receipts" / "v1" / "raw"
    stop_leaf = (
        raw_root
        / R._hash_segment("Session-1")
        / R._hash_segment("Child-1")
        / R._hash_segment("Turn-1")
    )
    old = dt.datetime(2026, 7, 10, 20, 0, tzinfo=dt.UTC).timestamp()
    os.utime(stop_leaf / "stop.json", (old, old))

    def now() -> dt.datetime:
        return dt.datetime(2026, 7, 12, 23, 0, tzinfo=dt.UTC)

    stop_plan = R.prune_raw_receipts(
        data, older_than_seconds=R.MAX_EVENT_AGE_SECONDS, now=now
    )
    assert stop_plan["entries"] == [
        {
            "leaf": "/".join(stop_leaf.parts[-3:]),
            "files": ["stop.json"],
            "bytes": (stop_leaf / "stop.json").stat().st_size,
        }
    ]
    R.prune_raw_receipts(
        data,
        older_than_seconds=R.MAX_EVENT_AGE_SECONDS,
        apply=True,
        expected_plan_sha256=stop_plan["plan_sha256"],
        now=now,
    )
    assert not stop_leaf.exists()

    lock_leaf = raw_root / ("a" * 64) / ("b" * 64) / ("c" * 64)
    lock_leaf.mkdir(mode=0o700, parents=True)
    for parent in (lock_leaf.parent.parent, lock_leaf.parent):
        parent.chmod(0o700)
    lock_path = lock_leaf / ".receipt.lock"
    lock_path.write_bytes(b"")
    lock_path.chmod(0o600)
    os.utime(lock_path, (old, old))
    lock_plan = R.prune_raw_receipts(
        data, older_than_seconds=R.MAX_EVENT_AGE_SECONDS, now=now
    )
    assert lock_plan["entries"] == [
        {"leaf": "/".join(lock_leaf.parts[-3:]), "files": [], "bytes": 0}
    ]
    with lock_path.open("rb+") as active_lock:
        fcntl.flock(active_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(R.DispatchReceiptError, match="active"):
            R.prune_raw_receipts(
                data,
                older_than_seconds=R.MAX_EVENT_AGE_SECONDS,
                apply=True,
                expected_plan_sha256=lock_plan["plan_sha256"],
                now=now,
            )
    R.prune_raw_receipts(
        data,
        older_than_seconds=R.MAX_EVENT_AGE_SECONDS,
        apply=True,
        expected_plan_sha256=lock_plan["plan_sha256"],
        now=now,
    )
    assert not lock_leaf.exists()


def test_root_receipt_requires_protected_result_and_verification(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    active_workflow = W.parse_workflow_structure(
        fixtures.plan(
            fixtures.row(
                "integrate",
                "root",
                mutation="root-only",
                required_evidence="diff",
            )
        )
    )
    subject_ref, _subject_digest = protected_subject(
        data,
        "src/integrate.py",
        active_workflow=active_workflow,
    )
    before_snapshot_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "integrate",
        attempt=1,
        task_id="integrate",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_snapshot_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="6" * 32,
    )
    result_ref = R.create_result_record(
        data,
        active_workflow,
        "integrate",
        attempt=1,
        task_id="integrate",
        intent_ref=intent_ref,
        output_subject_ref=subject_ref,
        mutation_audit_ref=None,
        workspace_root=None,
        vehicle="root",
        child_id=None,
        provided_evidence=["diff"],
        evidence={"evidence_refs": {"diff": subject_ref}, "findings": []},
        execution={"kind": "root"},
        recorded_at="2026-07-10T22:00:01Z",
    )
    with pytest.raises(R.DispatchReceiptError, match="predates the result"):
        R.create_root_verification_record(
            data,
            result_ref=result_ref,
            verifier_session_id="Session-1",
            verifier_turn_id="Backdated-Turn",
            resolution_refs=[],
            recorded_at="2026-07-10T22:00:00Z",
        )
    verification_ref = R.create_root_verification_record(
        data,
        result_ref=result_ref,
        verifier_session_id="Session-1",
        verifier_turn_id="Turn-1",
        resolution_refs=[],
        recorded_at="2026-07-10T22:00:02Z",
    )
    receipt = R.build_root_receipt(
        data,
        active_workflow,
        "integrate",
        attempt=1,
        task_id="integrate",
        intent_ref=intent_ref,
        result_ref=result_ref,
        root_verification_ref=verification_ref,
    )
    reference = R.persist_normalized(data, receipt)

    assert receipt["vehicle"] == "root"
    assert receipt["execution"]["model_fields_present"] is False
    R.validate_normalized_receipt(data, reference, active_workflow)


def test_root_verification_rejects_a_resolution_from_another_result(
    tmp_path: Path,
) -> None:
    data = plugin_data(tmp_path)
    active_workflow = workflow()
    step = active_workflow.step("security")
    unresolved = finding("P2")
    chain = protected_chain(data, active_workflow, findings=[unresolved])
    first_result, _first_result_bytes = R.load_protected_record(
        data,
        chain["result_ref"],
        "role-result",
    )
    subject_ref = first_result["output_subject_ref"]
    subject, _subject_bytes = R._load_subject_record(data, subject_ref)
    clean_result_ref = R.create_result_record(
        data,
        active_workflow,
        "security",
        attempt=1,
        task_id="security-review",
        intent_ref=chain["intent_ref"],
        output_subject_ref=subject_ref,
        mutation_audit_ref=first_result["mutation_audit_ref"],
        workspace_root=data.parent / "workspace",
        vehicle="verified-workflow-subagent",
        child_id="Child-1",
        provided_evidence=["review-evidence"],
        evidence=review_evidence(
            step,
            input_digest=subject["content_sha256"],
        ),
        execution={
            "kind": "agent-lens",
            "execution_class": step.execution_class,
            "profile_sha256": step.profile_sha256,
        },
        recorded_at="2026-07-10T22:00:03.100000Z",
    )
    subject_path = subject["paths"][0]
    (data.parent / "workspace" / subject_path).write_text("remediated\n")
    resolved_subject_ref, _resolved_digest = protected_subject(
        data,
        subject_path,
        parent_refs=[subject_ref],
        created_at="2026-07-10T22:00:03.250000Z",
    )
    resolution_ref = R.create_resolution_record(
        data,
        result_ref=chain["result_ref"],
        finding_id=str(unresolved["finding_id"]),
        resolved_subject_ref=resolved_subject_ref,
        evidence_refs=[resolved_subject_ref],
        recorded_at="2026-07-10T22:00:03.500000Z",
    )

    with pytest.raises(R.DispatchReceiptError, match="different result"):
        R.create_root_verification_record(
            data,
            result_ref=clean_result_ref,
            verifier_session_id="Session-1",
            verifier_turn_id="Cross-Result-Turn",
            resolution_refs=[resolution_ref],
            recorded_at="2026-07-10T22:00:04Z",
        )


def test_root_receipt_rejects_digest_shaped_unprotected_evidence(tmp_path: Path) -> None:
    data = plugin_data(tmp_path)
    active_workflow = W.parse_workflow_structure(
        fixtures.plan(
            fixtures.row(
                "integrate",
                "root",
                mutation="root-only",
                required_evidence="diff",
            )
        )
    )
    subject_ref, _subject_digest = protected_subject(
        data,
        "src/integrate.py",
        active_workflow=active_workflow,
    )
    before_snapshot_ref = workspace_snapshot(data, "2026-07-10T21:59:59Z")
    intent_ref = R.create_intent_record(
        data,
        active_workflow,
        "integrate",
        attempt=1,
        task_id="integrate",
        subject_ref=subject_ref,
        workspace_snapshot_ref=before_snapshot_ref,
        created_at="2026-07-10T22:00:00Z",
        nonce="8" * 32,
    )

    with pytest.raises(R.DispatchReceiptError, match="protected record"):
        R.create_result_record(
            data,
            active_workflow,
            "integrate",
            attempt=1,
            task_id="integrate",
            intent_ref=intent_ref,
            output_subject_ref=subject_ref,
            mutation_audit_ref=None,
            workspace_root=None,
            vehicle="root",
            child_id=None,
            provided_evidence=["diff"],
            evidence={"evidence_refs": {"diff": "record:subject:" + "a" * 64}, "findings": []},
            execution={"kind": "root"},
            recorded_at="2026-07-10T22:00:01Z",
        )
    malformed_ref = R.persist_protected_record(
        data,
        {
            "schema_version": 1,
            "record_type": "subject",
            "junk": True,
        },
    )
    with pytest.raises(R.DispatchReceiptError, match="subject record fields"):
        R.create_result_record(
            data,
            active_workflow,
            "integrate",
            attempt=1,
            task_id="integrate",
            intent_ref=intent_ref,
            output_subject_ref=subject_ref,
            mutation_audit_ref=None,
            workspace_root=None,
            vehicle="root",
            child_id=None,
            provided_evidence=["diff"],
            evidence={"evidence_refs": {"diff": malformed_ref}, "findings": []},
            execution={"kind": "root"},
            recorded_at="2026-07-10T22:00:01Z",
        )
