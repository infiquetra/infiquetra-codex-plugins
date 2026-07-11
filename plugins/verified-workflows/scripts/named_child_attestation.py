"""Join native child hook evidence to one planned logical-role result."""

from __future__ import annotations

from protected_store import (
    Any,
    Callable,
    DispatchReceiptError,
    MAX_EVENT_AGE_SECONDS,
    Path,
    _attempt,
    _canonical_bytes,
    _parse_time,
    _runtime_id,
    _safe,
    _sha256,
    _utc_now,
    _validate_raw_bytes,
    _validate_raw_event,
    dispatch,
    dt,
)

from workflow_records import (
    _load_hook_trust_record,
    _load_intent_record,
    _load_launch_record,
    _load_result_record,
    _load_root_verification_record,
)

def join_subagent_receipt(
    plugin_data: Path,
    workflow: dispatch.Workflow,
    step_id: str,
    *,
    attempt: int,
    task_id: str,
    parent_session_id: str,
    child_id: str,
    turn_id: str,
    intent_ref: str,
    hook_trust_ref: str,
    launch_ref: str,
    result_ref: str,
    root_verification_ref: str,
    start: object,
    stop: object,
    start_bytes: bytes,
    stop_bytes: bytes,
    now: Callable[[], dt.datetime] = _utc_now,
) -> dict[str, Any]:
    """Build a verified subagent receipt from one complete, matching evidence chain."""

    step = workflow.step(step_id)
    if step.role_kind != "agent-lens" or step.vehicle not in {"auto", "subagent"}:
        raise DispatchReceiptError("planned step is not eligible for subagent attestation")
    attempt = _attempt(attempt, "attempt")
    task_id = _safe(task_id, "task_id")
    parent_session_id = _runtime_id(parent_session_id, "parent_session_id")
    child_id = _runtime_id(child_id, "child_id")
    turn_id = _runtime_id(turn_id, "turn_id")
    intent, intent_bytes = _load_intent_record(
        plugin_data, intent_ref, workflow, step_id, attempt, task_id
    )
    hook_trust, hook_trust_bytes = _load_hook_trust_record(plugin_data, hook_trust_ref)
    launch, launch_bytes = _load_launch_record(
        plugin_data,
        launch_ref,
        intent_ref=intent_ref,
        parent_session_id=parent_session_id,
        turn_id=turn_id,
        child_id=child_id,
        agent_type=str(step.execution_class),
        hook_trust_ref=hook_trust_ref,
        codex_home_sha256=hook_trust["codex_home_sha256"],
    )
    result, result_bytes = _load_result_record(
        plugin_data,
        result_ref,
        workflow,
        step_id,
        attempt=attempt,
        task_id=task_id,
        intent_ref=intent_ref,
        vehicle="verified-workflow-subagent",
        child_id=child_id,
    )
    root_verification, root_verification_bytes = _load_root_verification_record(
        plugin_data, root_verification_ref, result_ref=result_ref
    )
    start = _validate_raw_event(
        start,
        "start",
        parent_session_id=parent_session_id,
        child_id=child_id,
        turn_id=turn_id,
    )
    stop = _validate_raw_event(
        stop,
        "stop",
        parent_session_id=parent_session_id,
        child_id=child_id,
        turn_id=turn_id,
    )
    _validate_raw_bytes(start, start_bytes, "start receipt")
    _validate_raw_bytes(stop, stop_bytes, "stop receipt")
    for field in (
        "parent_session_id",
        "turn_id",
        "child_id",
        "agent_type",
        "active_model",
        "permission_mode",
        "profile_sha256",
        "codex_home_sha256",
        "hook_definition_sha256",
        "hook_handler_sha256",
    ):
        if start[field] != stop[field]:
            raise DispatchReceiptError(f"start/stop {field} does not match")
    if start["agent_type"] != step.execution_class:
        raise DispatchReceiptError("hook agent_type does not match the planned execution class")
    if start["active_model"] != step.expected_model:
        raise DispatchReceiptError("hook model does not match the planned profile")
    if start["profile_sha256"] != step.profile_sha256:
        raise DispatchReceiptError("hook profile digest does not match the planned profile")
    if (
        start["hook_definition_sha256"] != hook_trust["definition_sha256"]
        or start["hook_handler_sha256"] != hook_trust["handler_sha256"]
        or start["codex_home_sha256"] != hook_trust["codex_home_sha256"]
    ):
        raise DispatchReceiptError("raw hook pair does not bind the trusted hook bytes")
    created = _parse_time(intent["created_at"], "intent.created_at")
    trusted = _parse_time(hook_trust["observed_at"], "hook trust observed_at")
    launched = _parse_time(launch["launched_at"], "launch.launched_at")
    started = _parse_time(start["observed_at"], "start.observed_at")
    stopped = _parse_time(stop["observed_at"], "stop.observed_at")
    recorded = _parse_time(result["recorded_at"], "result.recorded_at")
    verified = _parse_time(
        root_verification["recorded_at"], "root verification recorded_at"
    )
    effective_now = now()
    if not (
        created <= launched <= recorded
        and trusted <= started <= stopped <= recorded <= verified <= effective_now
    ):
        raise DispatchReceiptError("dispatch timestamps are reversed or in the future")
    if (effective_now - started).total_seconds() > MAX_EVENT_AGE_SECONDS:
        raise DispatchReceiptError("hook pair is stale")
    raw_pair_sha256 = _sha256(
        _canonical_bytes(
            {
                "start_sha256": _sha256(start_bytes),
                "stop_sha256": _sha256(stop_bytes),
            }
        )
    )
    return {
        "schema_version": 1,
        "vehicle": "verified-workflow-subagent",
        "workflow_sha256": workflow.sha256,
        "step_id": step.step_id,
        "attempt": attempt,
        "task_id": task_id,
        "intent_ref": intent_ref,
        "intent_sha256": _sha256(intent_bytes),
        "subject_ref": intent["subject_ref"],
        "subject_sha256": intent["subject_sha256"],
        "workflow_run_sha256": intent["workflow_run_sha256"],
        "workspace_snapshot_ref": intent["workspace_snapshot_ref"],
        "workspace_snapshot_sha256": intent["workspace_snapshot_sha256"],
        "mutation_audit_ref": result["mutation_audit_ref"],
        "output_subject_ref": result["output_subject_ref"],
        "output_subject_content_sha256": result["output_subject_content_sha256"],
        "role": {
            "role_id": step.role_id,
            "role_kind": step.role_kind,
            "role_lens_sha256": step.role_lens_sha256,
            "independence": step.independence,
        },
        "execution": {
            "execution_class": step.execution_class,
            "active_model": step.expected_model,
            "effort_evidence": "installed-profile-digest",
            "expected_effort": step.expected_effort,
            "profile_sha256": step.profile_sha256,
            "expected_profile_sandbox": step.expected_profile_sandbox,
            "observed_permission_mode": start["permission_mode"],
            "sandbox_enforcement_claim": "configured-not-observed",
            "permission_boundary": "requested-boundary-advisory",
        },
        "hook_trust": {
            "record_ref": hook_trust_ref,
            "record_sha256": _sha256(hook_trust_bytes),
            "definition_sha256": hook_trust["definition_sha256"],
            "handler_sha256": hook_trust["handler_sha256"],
            "codex_home_sha256": hook_trust["codex_home_sha256"],
            "trust_readback_sha256": hook_trust["trust_readback_sha256"],
        },
        "child": {
            "parent_session_id": parent_session_id,
            "turn_id": turn_id,
            "child_id": child_id,
            "launch_ref": launch_ref,
            "launch_sha256": _sha256(launch_bytes),
            "start_sha256": _sha256(start_bytes),
            "stop_sha256": _sha256(stop_bytes),
            "raw_pair_sha256": raw_pair_sha256,
        },
        "raw_events": {"start": start, "stop": stop},
        "result": {
            "result_ref": result_ref,
            "result_sha256": _sha256(result_bytes),
            "evidence_sha256": result["evidence_sha256"],
            "root_verification_ref": root_verification_ref,
            "root_verification_sha256": _sha256(root_verification_bytes),
            "root_verified": True,
        },
        "timestamps": {
            "intent_created_at": intent["created_at"],
            "hook_trusted_at": hook_trust["observed_at"],
            "launched_at": launch["launched_at"],
            "started_at": start["observed_at"],
            "stopped_at": stop["observed_at"],
            "result_recorded_at": result["recorded_at"],
            "root_verified_at": root_verification["recorded_at"],
        },
    }
