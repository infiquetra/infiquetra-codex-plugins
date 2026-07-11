"""Workflow intent, result, resolution, and normalized receipt records."""

from __future__ import annotations

from protected_store import (
    Any,
    DispatchReceiptError,
    GIT_OID,
    HEX64,
    MAX_RECEIPT_BYTES,
    MAX_SUBJECT_ANCESTRY,
    MAX_SUBJECT_BYTES,
    Mapping,
    Path,
    PurePosixPath,
    SECRET_KEY,
    SECRET_VALUE,
    _attempt,
    _canonical_bytes,
    _current_hook_bytes,
    _load_json_at,
    _open_existing_chain,
    _parse_record_reference,
    _parse_time,
    _persist_under,
    _runtime_id,
    _safe,
    _sha256,
    _timestamp_now,
    _validate_raw_event,
    dispatch,
    dt,
    hook_receipt,
    json,
    load_protected_record,
    math,
    os,
    persist_protected_record,
    re,
    stat,
)

from workspace_evidence import (
    _load_mutation_audit_record,
    _load_subject_record,
    _load_workflow_run_record,
    _load_workspace_snapshot_record,
    _subject_path,
)

def build_inline_receipt(
    plugin_data: Path,
    workflow: dispatch.Workflow,
    step_id: str,
    *,
    attempt: int,
    task_id: str,
    intent_ref: str,
    result_ref: str,
    root_verification_ref: str,
) -> dict[str, Any]:
    """Record a truthful preferred-independence inline fallback."""

    step = workflow.step(step_id)
    if step.role_kind != "agent-lens" or step.vehicle not in {"auto", "inline"}:
        raise DispatchReceiptError("planned step is not eligible for inline execution")
    if step.independence != "preferred":
        raise DispatchReceiptError("required independence cannot fall back inline")
    attempt = _attempt(attempt, "attempt")
    task_id = _safe(task_id, "task_id")
    intent, intent_bytes = _load_intent_record(
        plugin_data, intent_ref, workflow, step_id, attempt, task_id
    )
    result, result_bytes = _load_result_record(
        plugin_data,
        result_ref,
        workflow,
        step_id,
        attempt=attempt,
        task_id=task_id,
        intent_ref=intent_ref,
        vehicle="verified-workflow-inline",
        child_id=None,
    )
    root_verification, root_verification_bytes = _load_root_verification_record(
        plugin_data, root_verification_ref, result_ref=result_ref
    )
    return {
        "schema_version": 1,
        "vehicle": "verified-workflow-inline",
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
            "expected_model": step.expected_model,
            "expected_effort": step.expected_effort,
            "profile_sha256": step.profile_sha256,
            "runtime_selection_attested": False,
        },
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
            "result_recorded_at": result["recorded_at"],
            "root_verified_at": root_verification["recorded_at"],
        },
        "limitation": "logical role executed inline; separate child, model, effort, and sandbox were not observed",
    }


def _build_non_agent_receipt(
    plugin_data: Path,
    workflow: dispatch.Workflow,
    step_id: str,
    *,
    attempt: int,
    task_id: str,
    intent_ref: str,
    result_ref: str,
    root_verification_ref: str,
    vehicle: str,
) -> dict[str, Any]:
    step = workflow.step(step_id)
    expected_kind = "deterministic-validator" if vehicle == "deterministic-tool" else "root"
    if step.role_kind != expected_kind or step.vehicle != vehicle:
        raise DispatchReceiptError(f"planned step is not eligible for {vehicle}")
    attempt = _attempt(attempt, "attempt")
    task_id = _safe(task_id, "task_id")
    intent, intent_bytes = _load_intent_record(
        plugin_data, intent_ref, workflow, step_id, attempt, task_id
    )
    result, result_bytes = _load_result_record(
        plugin_data,
        result_ref,
        workflow,
        step_id,
        attempt=attempt,
        task_id=task_id,
        intent_ref=intent_ref,
        vehicle=vehicle,
        child_id=None,
    )
    root_verification, root_verification_bytes = _load_root_verification_record(
        plugin_data, root_verification_ref, result_ref=result_ref
    )
    execution: dict[str, Any]
    if vehicle == "deterministic-tool":
        command_output, _command_output_bytes = _load_command_output_record(
            plugin_data, result["execution"]["output_ref"]
        )
        execution = {
            "command": list(step.command),
            "command_implementation_sha256": step.command_implementation_sha256,
            "evidence_schema_sha256": step.evidence_schema_sha256,
            "cwd": "repo-root",
            "timeout_seconds": step.command_timeout_seconds,
            "output_limit_bytes": step.command_output_limit_bytes,
            "output_ref": result["execution"]["output_ref"],
            "output_sha256": command_output["combined_sha256"],
            "exit_code": result["execution"]["exit_code"],
            "model_fields_present": False,
        }
    else:
        execution = {"kind": "root", "model_fields_present": False}
    return {
        "schema_version": 1,
        "vehicle": vehicle,
        "workflow_sha256": workflow.sha256,
        "step_id": step_id,
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
            "independence": "n/a",
        },
        "execution": execution,
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
            "result_recorded_at": result["recorded_at"],
            "root_verified_at": root_verification["recorded_at"],
        },
    }


def build_deterministic_receipt(
    plugin_data: Path,
    workflow: dispatch.Workflow,
    step_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return _build_non_agent_receipt(
        plugin_data, workflow, step_id, vehicle="deterministic-tool", **kwargs
    )


def build_root_receipt(
    plugin_data: Path,
    workflow: dispatch.Workflow,
    step_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return _build_non_agent_receipt(
        plugin_data, workflow, step_id, vehicle="root", **kwargs
    )

def _validate_intent_resolution_refs(
    plugin_data: Path,
    references: tuple[str, ...],
    *,
    previous_result_ref: str,
    finding_refs: tuple[str, ...],
    subject_ref: str,
    intent_created_at: dt.datetime,
) -> None:
    if len(references) != len(set(references)):
        raise DispatchReceiptError("intent resolution references contain duplicates")
    resolution_findings: set[str] = set()
    for reference in references:
        _parse_record_reference(reference, "resolution")
        resolution, _resolution_bytes = _load_resolution_record(
            plugin_data,
            reference,
            result_ref=previous_result_ref,
        )
        finding_id = resolution["finding_id"]
        if finding_id not in finding_refs or finding_id in resolution_findings:
            raise DispatchReceiptError(
                "intent resolutions do not bind unique predecessor findings"
            )
        if _parse_time(
            resolution["recorded_at"], "resolution.recorded_at"
        ) > intent_created_at:
            raise DispatchReceiptError("intent predates a claimed finding resolution")
        if not _subject_descends_from(
            plugin_data,
            subject_ref,
            resolution["resolved_subject_ref"],
        ):
            raise DispatchReceiptError(
                "intent subject does not consume its finding resolution"
            )
        resolution_findings.add(finding_id)


def create_intent_record(
    plugin_data: Path,
    workflow: dispatch.Workflow,
    step_id: str,
    *,
    attempt: int,
    task_id: str,
    subject_ref: str,
    workspace_snapshot_ref: str,
    intent_kind: str = "run",
    previous_receipt_ref: str | None = None,
    finding_refs: list[str] | None = None,
    resolution_refs: list[str] | None = None,
    created_at: str,
    nonce: str,
) -> str:
    step = workflow.step(step_id)
    attempt = _attempt(attempt, "intent attempt")
    task_id = _safe(task_id, "task_id")
    _parse_time(created_at, "intent.created_at")
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise DispatchReceiptError("intent nonce is invalid")
    normalized_findings = tuple(
        _safe(value, "intent finding reference") for value in (finding_refs or [])
    )
    normalized_resolutions = tuple(resolution_refs or ())
    if any(not isinstance(value, str) for value in normalized_resolutions):
        raise DispatchReceiptError("intent resolution references are invalid")
    previous_output_subject_ref: str | None = None
    if len(normalized_findings) != len(set(normalized_findings)):
        raise DispatchReceiptError("intent finding references contain duplicates")
    if attempt == 1:
        if (
            intent_kind != "run"
            or previous_receipt_ref is not None
            or normalized_findings
            or normalized_resolutions
        ):
            raise DispatchReceiptError("initial intent cannot claim remediation history")
    else:
        if intent_kind not in {"follow-up", "revalidate"} or previous_receipt_ref is None:
            raise DispatchReceiptError("later intent requires a typed predecessor")
        previous_receipt, previous_result = validate_normalized_receipt(
            plugin_data, previous_receipt_ref, workflow
        )
        if (
            previous_receipt["step_id"] != step_id
            or previous_receipt["attempt"] != attempt - 1
        ):
            raise DispatchReceiptError("intent predecessor does not bind the prior attempt")
        previous_findings = tuple(
            finding["finding_id"]
            for finding in previous_result["evidence"].get("findings", [])
        )
        if intent_kind == "follow-up" and (
            not previous_findings or normalized_findings != previous_findings
        ):
            raise DispatchReceiptError(
                "follow-up intent must bind every prior unresolved finding"
            )
        if intent_kind == "revalidate" and (previous_findings or normalized_findings):
            raise DispatchReceiptError(
                "revalidation intent cannot discard unresolved findings"
            )
        if intent_kind == "revalidate" and normalized_resolutions:
            raise DispatchReceiptError(
                "revalidation intent cannot carry finding resolutions"
            )
        previous_output_subject_ref = previous_receipt["output_subject_ref"]
    subject, subject_bytes = _load_subject_record(plugin_data, subject_ref)
    workflow_run, workflow_run_bytes = _load_workflow_run_record(
        plugin_data,
        subject["workflow_run_ref"],
        workflow=workflow,
    )
    if previous_output_subject_ref is not None and not _subject_descends_from(
        plugin_data,
        subject_ref,
        previous_output_subject_ref,
    ):
        raise DispatchReceiptError(
            "later intent subject does not descend from the prior result"
        )
    if attempt > 1:
        _validate_intent_resolution_refs(
            plugin_data,
            normalized_resolutions,
            previous_result_ref=previous_receipt["result"]["result_ref"],
            finding_refs=normalized_findings,
            subject_ref=subject_ref,
            intent_created_at=_parse_time(created_at, "intent.created_at"),
        )
    workspace_snapshot, workspace_snapshot_bytes = _load_workspace_snapshot_record(
        plugin_data, workspace_snapshot_ref
    )
    if workspace_snapshot["repository_sha256"] != subject["repository_sha256"]:
        raise DispatchReceiptError("intent workspace snapshot belongs to another repository")
    if _parse_time(
        workspace_snapshot["created_at"], "workspace snapshot.created_at"
    ) >= _parse_time(created_at, "intent.created_at"):
        raise DispatchReceiptError("intent requires a strictly earlier before snapshot")
    if _parse_time(subject["created_at"], "subject.created_at") > _parse_time(
        created_at, "intent.created_at"
    ):
        raise DispatchReceiptError("intent predates its protected subject")
    workflow_run_sha256 = _sha256(workflow_run_bytes)
    if attempt > 1 and previous_receipt["workflow_run_sha256"] != workflow_run_sha256:
        raise DispatchReceiptError("later intent changes the workflow run identity")
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "intent",
            "workflow_sha256": workflow.sha256,
            "step_id": step_id,
            "attempt": attempt,
            "task_id": task_id,
            "subject_ref": subject_ref,
            "subject_sha256": _sha256(subject_bytes),
            "workspace_snapshot_ref": workspace_snapshot_ref,
            "workspace_snapshot_sha256": _sha256(workspace_snapshot_bytes),
            "workflow_run_sha256": workflow_run_sha256,
            "intent_kind": intent_kind,
            "previous_receipt_ref": previous_receipt_ref,
            "finding_refs": list(normalized_findings),
            "resolution_refs": list(normalized_resolutions),
            "step": step.to_jsonable(),
            "nonce": nonce,
            "created_at": created_at,
        },
    )
    _load_intent_record(plugin_data, reference, workflow, step_id, attempt, task_id)
    return reference


def _load_intent_record(
    plugin_data: Path,
    reference: str,
    workflow: dispatch.Workflow,
    step_id: str,
    attempt: int,
    task_id: str,
) -> tuple[dict[str, Any], bytes]:
    attempt = _attempt(attempt, "intent attempt")
    record, content = load_protected_record(plugin_data, reference, "intent")
    expected_fields = {
        "schema_version",
        "record_type",
        "workflow_sha256",
        "step_id",
        "attempt",
        "task_id",
        "subject_ref",
        "subject_sha256",
        "workspace_snapshot_ref",
        "workspace_snapshot_sha256",
        "workflow_run_sha256",
        "intent_kind",
        "previous_receipt_ref",
        "finding_refs",
        "resolution_refs",
        "step",
        "nonce",
        "created_at",
    }
    if set(record) != expected_fields:
        raise DispatchReceiptError("intent record fields are not closed")
    step = workflow.step(step_id)
    subject, subject_bytes = _load_subject_record(plugin_data, record.get("subject_ref"))
    workflow_run, workflow_run_bytes = _load_workflow_run_record(
        plugin_data,
        subject["workflow_run_ref"],
        workflow=workflow,
    )
    workspace_snapshot, workspace_snapshot_bytes = _load_workspace_snapshot_record(
        plugin_data, record.get("workspace_snapshot_ref")
    )
    expected_run_sha256 = _sha256(workflow_run_bytes)
    intent_kind = record["intent_kind"]
    previous_receipt_ref = record["previous_receipt_ref"]
    finding_refs = record["finding_refs"]
    resolution_refs = record["resolution_refs"]
    if not isinstance(finding_refs, list) or any(
        _safe(value, "intent finding reference") != value for value in finding_refs
    ):
        raise DispatchReceiptError("intent finding references are invalid")
    if len(finding_refs) != len(set(finding_refs)):
        raise DispatchReceiptError("intent finding references contain duplicates")
    if not isinstance(resolution_refs, list) or any(
        not isinstance(value, str) for value in resolution_refs
    ):
        raise DispatchReceiptError("intent resolution references are invalid")
    if attempt == 1:
        if (
            intent_kind != "run"
            or previous_receipt_ref is not None
            or finding_refs
            or resolution_refs
        ):
            raise DispatchReceiptError("initial intent history is invalid")
    else:
        if intent_kind not in {"follow-up", "revalidate"} or not isinstance(
            previous_receipt_ref, str
        ):
            raise DispatchReceiptError("later intent history is invalid")
        previous_receipt, previous_result = validate_normalized_receipt(
            plugin_data, previous_receipt_ref, workflow
        )
        previous_findings = [
            finding["finding_id"]
            for finding in previous_result["evidence"].get("findings", [])
        ]
        if (
            previous_receipt["step_id"] != step_id
            or previous_receipt["attempt"] != attempt - 1
            or (intent_kind == "follow-up" and finding_refs != previous_findings)
            or (intent_kind == "follow-up" and not finding_refs)
            or (intent_kind == "revalidate" and (finding_refs or previous_findings))
            or (intent_kind == "revalidate" and resolution_refs)
        ):
            raise DispatchReceiptError("intent remediation history is invalid")
        if not _subject_descends_from(
            plugin_data,
            record["subject_ref"],
            previous_receipt["output_subject_ref"],
        ):
            raise DispatchReceiptError(
                "intent subject does not descend from the prior result"
            )
        if previous_receipt["workflow_run_sha256"] != expected_run_sha256:
            raise DispatchReceiptError("intent changes the workflow run identity")
        _validate_intent_resolution_refs(
            plugin_data,
            tuple(resolution_refs),
            previous_result_ref=previous_receipt["result"]["result_ref"],
            finding_refs=tuple(finding_refs),
            subject_ref=record["subject_ref"],
            intent_created_at=_parse_time(record["created_at"], "intent.created_at"),
        )
    if (
        record["workflow_sha256"] != workflow.sha256
        or record["step_id"] != step_id
        or record["attempt"] != attempt
        or record["task_id"] != task_id
        or record["subject_sha256"] != _sha256(subject_bytes)
        or record["workspace_snapshot_sha256"] != _sha256(workspace_snapshot_bytes)
        or workspace_snapshot["repository_sha256"] != subject["repository_sha256"]
        or record["workflow_run_sha256"] != expected_run_sha256
        or record["step"] != step.to_jsonable()
        or not isinstance(record["nonce"], str)
        or not re.fullmatch(r"[0-9a-f]{32}", record["nonce"])
    ):
        raise DispatchReceiptError("intent record does not bind the planned step")
    intent_created_at = _parse_time(record["created_at"], "intent.created_at")
    if _parse_time(
        workspace_snapshot["created_at"], "workspace snapshot.created_at"
    ) >= intent_created_at:
        raise DispatchReceiptError("intent requires a strictly earlier before snapshot")
    if _parse_time(subject["created_at"], "subject.created_at") > intent_created_at:
        raise DispatchReceiptError("intent predates its protected subject")
    return record, content


def create_hook_trust_record(
    plugin_data: Path,
    *,
    codex_home: Path,
    installed_hooks_dir: Path,
    scope: str,
    observed_at: str | None = None,
) -> str:
    definition, handler = _current_hook_bytes()
    if (
        not codex_home.is_absolute()
        or not installed_hooks_dir.is_absolute()
        or scope not in {"isolated", "real"}
    ):
        raise DispatchReceiptError("hook trust readback is invalid")
    try:
        hook_receipt._assert_no_symlink_components(codex_home)
        hook_receipt._assert_no_symlink_components(installed_hooks_dir)
        resolved_home = codex_home.resolve(strict=True)
        resolved_hooks = installed_hooks_dir.resolve(strict=True)
        relative_hooks = resolved_hooks.relative_to(resolved_home).as_posix()
    except (hook_receipt.AgentReceiptError, FileNotFoundError, OSError, ValueError) as exc:
        raise DispatchReceiptError(
            "installed hooks must be contained in the declared Codex home"
        ) from exc
    relative_parts = PurePosixPath(relative_hooks).parts
    if (
        not stat.S_ISDIR(resolved_home.stat().st_mode)
        or resolved_home.stat().st_uid != os.getuid()
        or not stat.S_ISDIR(resolved_hooks.stat().st_mode)
        or resolved_hooks.stat().st_uid != os.getuid()
        or "plugins" not in relative_parts
        or "verified-workflows" not in relative_parts
        or not relative_parts
        or relative_parts[-1] != "hooks"
    ):
        raise DispatchReceiptError("installed hook location is not a Verified Workflows install")
    try:
        installed_definition = hook_receipt._read_regular(
            installed_hooks_dir / "hooks.json",
            "installed hook definition",
            MAX_RECEIPT_BYTES,
        )
        installed_handler = hook_receipt._read_regular(
            installed_hooks_dir / "agent_receipt.py",
            "installed hook handler",
            MAX_RECEIPT_BYTES,
        )
    except hook_receipt.AgentReceiptError as exc:
        raise DispatchReceiptError("installed hook readback is missing or unsafe") from exc
    if installed_definition != definition or installed_handler != handler:
        raise DispatchReceiptError("installed hook readback does not match current trusted bytes")
    trust_readback_sha256 = _sha256(
        _canonical_bytes(
            {
                "definition_sha256": _sha256(installed_definition),
                "handler_sha256": _sha256(installed_handler),
            }
        )
    )
    observed_at = observed_at or _timestamp_now()
    _parse_time(observed_at, "hook trust observed_at")
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "hook-trust",
            "trust_claim": "root-observed-installed-hook-readback",
            "scope": scope,
            "codex_home_sha256": _sha256(str(resolved_home).encode()),
            "installed_hooks_relative": relative_hooks,
            "definition_sha256": _sha256(definition),
            "handler_sha256": _sha256(handler),
            "trust_readback_sha256": trust_readback_sha256,
            "observed_at": observed_at,
        },
    )
    _load_hook_trust_record(plugin_data, reference)
    return reference


def _load_hook_trust_record(
    plugin_data: Path, reference: str
) -> tuple[dict[str, Any], bytes]:
    record, content = load_protected_record(plugin_data, reference, "hook-trust")
    if set(record) != {
        "schema_version",
        "record_type",
        "trust_claim",
        "scope",
        "codex_home_sha256",
        "installed_hooks_relative",
        "definition_sha256",
        "handler_sha256",
        "trust_readback_sha256",
        "observed_at",
    }:
        raise DispatchReceiptError("hook trust record fields are not closed")
    definition, handler = _current_hook_bytes()
    expected_readback_sha256 = _sha256(
        _canonical_bytes(
            {
                "definition_sha256": record["definition_sha256"],
                "handler_sha256": record["handler_sha256"],
            }
        )
    )
    installed_parts = PurePosixPath(
        _subject_path(record["installed_hooks_relative"])
    ).parts
    if (
        record["trust_claim"] != "root-observed-installed-hook-readback"
        or record["scope"] not in {"isolated", "real"}
        or not isinstance(record["codex_home_sha256"], str)
        or not HEX64.fullmatch(record["codex_home_sha256"])
        or "plugins" not in installed_parts
        or "verified-workflows" not in installed_parts
        or installed_parts[-1] != "hooks"
        or record["definition_sha256"] != _sha256(definition)
        or record["handler_sha256"] != _sha256(handler)
        or not isinstance(record["trust_readback_sha256"], str)
        or not HEX64.fullmatch(record["trust_readback_sha256"])
        or record["trust_readback_sha256"] != expected_readback_sha256
    ):
        raise DispatchReceiptError("hook trust record does not bind current trusted bytes")
    _parse_time(record["observed_at"], "hook trust observed_at")
    return record, content


def create_launch_record(
    plugin_data: Path,
    *,
    intent_ref: str,
    parent_session_id: str,
    turn_id: str,
    child_id: str,
    agent_type: str,
    hook_trust_ref: str,
    launched_at: str | None = None,
) -> str:
    _parse_record_reference(intent_ref, "intent")
    hook_trust, _hook_trust_bytes = _load_hook_trust_record(
        plugin_data,
        hook_trust_ref,
    )
    parent_session_id = _runtime_id(parent_session_id, "parent_session_id")
    turn_id = _runtime_id(turn_id, "turn_id")
    child_id = _runtime_id(child_id, "child_id")
    agent_type = _safe(agent_type, "agent_type")
    launched_at = launched_at or _timestamp_now()
    _parse_time(launched_at, "launch.launched_at")
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "native-launch",
            "intent_ref": intent_ref,
            "parent_session_id": parent_session_id,
            "turn_id": turn_id,
            "child_id": child_id,
            "agent_type": agent_type,
            "hook_trust_ref": hook_trust_ref,
            "codex_home_sha256": hook_trust["codex_home_sha256"],
            "ack_kind": "native-collaboration-launch",
            "recorded_by": "root",
            "launched_at": launched_at,
        },
    )
    return reference


def _validate_finding_list(value: object, where: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 1024:
        raise DispatchReceiptError(f"{where} must be a bounded list")
    findings: list[dict[str, Any]] = []
    finding_ids: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict) or set(raw) != {
            "finding_id",
            "severity",
            "category",
            "location",
            "impact",
            "fix",
            "validation",
            "resolved",
            "hard_stop",
        }:
            raise DispatchReceiptError(f"{where} finding fields are not closed")
        finding_id = _safe(raw["finding_id"], f"{where}.finding_id")
        category = _safe(raw["category"], f"{where}.category")
        if raw["severity"] not in {"P0", "P1", "P2", "P3"}:
            raise DispatchReceiptError(f"{where}.severity is invalid")
        if category not in dispatch.renderer.NESTED_TYPE_CONTRACTS["typed-finding"][
            "enum_fields"
        ]["category"]:
            raise DispatchReceiptError(f"{where}.category is invalid")
        if any(
            not isinstance(raw[field], str) or not raw[field].strip()
            for field in ("location", "impact", "fix", "validation")
        ):
            raise DispatchReceiptError(f"{where} finding detail is invalid")
        if raw["resolved"] is not False or not isinstance(raw["hard_stop"], bool):
            raise DispatchReceiptError(f"{where} finding booleans are invalid")
        if finding_id in finding_ids:
            raise DispatchReceiptError(f"{where} contains duplicate finding IDs")
        finding_ids.add(finding_id)
        findings.append(dict(raw))
    return findings


def _validate_json_structure(value: object, where: str, depth: int = 0) -> None:
    if depth > 8:
        raise DispatchReceiptError(f"{where} exceeds the nesting ceiling")
    if isinstance(value, dict):
        if len(value) > 128 or any(
            not isinstance(key, str)
            or not key
            or len(key) > 128
            or SECRET_KEY.search(key)
            for key in value
        ):
            raise DispatchReceiptError(f"{where} object shape is invalid")
        for key, child in value.items():
            _validate_json_structure(child, f"{where}.{key}", depth + 1)
    elif isinstance(value, list):
        if len(value) > 1024:
            raise DispatchReceiptError(f"{where} list exceeds the item ceiling")
        for index, child in enumerate(value):
            _validate_json_structure(child, f"{where}[{index}]", depth + 1)
    elif isinstance(value, str):
        if len(value) > 4096 or any(
            ord(character) < 32 and character not in "\n\t" for character in value
        ) or value.startswith(("/", "~", "file:")) or SECRET_VALUE.search(value):
            raise DispatchReceiptError(f"{where} string is invalid")
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise DispatchReceiptError(f"{where} number is non-finite")
    elif value is not None and not isinstance(value, (bool, int)):
        raise DispatchReceiptError(f"{where} contains an unsupported value")


def _load_root_evidence_reference(plugin_data: Path, reference: object) -> str:
    if not isinstance(reference, str):
        raise DispatchReceiptError("root evidence reference is invalid")
    parts = reference.split(":")
    allowed = {"subject", "workspace-snapshot", "mutation-audit", "command-output"}
    if len(parts) != 3 or parts[0] != "record" or parts[1] not in allowed:
        raise DispatchReceiptError("root evidence must reference a protected record")
    try:
        if parts[1] == "subject":
            _load_subject_record(plugin_data, reference)
        elif parts[1] == "workspace-snapshot":
            _load_workspace_snapshot_record(plugin_data, reference)
        elif parts[1] == "mutation-audit":
            _load_mutation_audit_record(plugin_data, reference)
        else:
            _load_command_output_record(plugin_data, reference)
    except (OSError, json.JSONDecodeError) as exc:
        raise DispatchReceiptError("root evidence protected record is unavailable") from exc
    return reference


def _load_prerequisite_reference(plugin_data: Path, reference: object) -> str:
    if not isinstance(reference, str):
        raise DispatchReceiptError("prerequisite evidence reference is invalid")
    _parse_record_reference(reference, "role-result")
    load_protected_record(plugin_data, reference, "role-result")
    return reference


def _derive_evidence_bindings(
    plugin_data: Path,
    step: dispatch.WorkflowStep,
    evidence: Mapping[str, Any],
    provided_evidence: tuple[str, ...],
    *,
    subject_ref: str,
) -> dict[str, str]:
    if tuple(step.required_evidence) != provided_evidence:
        raise DispatchReceiptError(
            "result evidence ids must exactly match the approved workflow row"
        )
    if step.output_schema == "root-evidence.v1":
        refs = evidence.get("evidence_refs")
        if not isinstance(refs, dict) or set(refs) != set(provided_evidence):
            raise DispatchReceiptError("root evidence bindings are invalid")
        bindings = dict(refs)
    elif step.output_schema == "review-evidence.v1":
        bindings = {evidence_id: subject_ref for evidence_id in provided_evidence}
    else:
        refs = evidence.get("evidence_refs")
        if (
            not isinstance(refs, list)
            or len(refs) != len(provided_evidence)
            or len(refs) != len(set(refs))
        ):
            raise DispatchReceiptError(
                "validator evidence refs must map one-to-one to required evidence ids"
            )
        bindings = dict(zip(provided_evidence, refs, strict=True))
    for evidence_id, reference in bindings.items():
        _safe(evidence_id, "evidence binding id")
        _load_root_evidence_reference(plugin_data, reference)
    return bindings


def _validate_test_cases(plugin_data: Path, value: object) -> bool:
    if not isinstance(value, list):
        return False
    case_ids: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict) or set(raw) != {
            "case_id",
            "status",
            "evidence_ref",
        }:
            return False
        try:
            case_id = _safe(raw["case_id"], "test case id")
            _load_root_evidence_reference(plugin_data, raw["evidence_ref"])
        except DispatchReceiptError:
            return False
        if (
            case_id in case_ids
            or raw["status"]
            not in {"pass", "warn", "hard-fail", "blocked", "skipped-by-config"}
        ):
            return False
        case_ids.add(case_id)
    return True


def _validate_observations(plugin_data: Path, value: object) -> bool:
    if not isinstance(value, list):
        return False
    observation_ids: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict) or set(raw) != {
            "observation_id",
            "health_state",
            "evidence_ref",
        }:
            return False
        try:
            observation_id = _safe(raw["observation_id"], "observation id")
            _load_root_evidence_reference(plugin_data, raw["evidence_ref"])
        except DispatchReceiptError:
            return False
        if (
            observation_id in observation_ids
            or raw["health_state"]
            not in {"healthy", "degraded", "missing-signal", "not-applicable"}
        ):
            return False
        observation_ids.add(observation_id)
    return True


def _validate_time_window(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {"started_at", "ended_at"}:
        return False
    try:
        started = _parse_time(value["started_at"], "time window.started_at")
        ended = _parse_time(value["ended_at"], "time window.ended_at")
    except DispatchReceiptError:
        return False
    return started <= ended


def _review_dimension_ids(registry: Any, role_id: str) -> tuple[str, ...]:
    role = registry.role(role_id)
    if role.category != "reviewer" or role.lens_path is None:
        raise DispatchReceiptError("review role lacks a versioned lens")
    path = registry.path.parent.parent / role.lens_path
    try:
        content = hook_receipt._read_regular(
            path,
            f"review lens {role_id}",
            MAX_SUBJECT_BYTES,
        ).decode("utf-8")
    except (hook_receipt.AgentReceiptError, UnicodeDecodeError) as exc:
        raise DispatchReceiptError("review lens dimensions are unreadable") from exc
    try:
        mandate = content.split("## Your Review Mandate", 1)[1].split("\n---", 1)[0]
    except IndexError as exc:
        raise DispatchReceiptError("review lens lacks its dimension mandate") from exc
    names = re.findall(r"(?m)^\d+\. \*\*(.+?)\*\*", mandate)
    dimension_ids = tuple(
        re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") for name in names
    )
    if len(dimension_ids) != 5 or len(set(dimension_ids)) != 5 or any(
        not value or _safe(value, "review dimension id") != value
        for value in dimension_ids
    ):
        raise DispatchReceiptError("review lens dimension contract is invalid")
    return dimension_ids


def _validate_evidence(
    plugin_data: Path,
    step: dispatch.WorkflowStep,
    evidence: object,
    evidence_bindings: Mapping[str, str],
) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise DispatchReceiptError("result evidence must be an object")
    _validate_json_structure(evidence, "result evidence")
    if step.output_schema == "root-evidence.v1":
        if set(evidence) != {"evidence_refs", "findings"}:
            raise DispatchReceiptError("root evidence fields are not closed")
        refs = evidence["evidence_refs"]
        if not isinstance(refs, dict) or refs != evidence_bindings:
            raise DispatchReceiptError("root evidence references are invalid")
        for evidence_id, reference in refs.items():
            _safe(evidence_id, "root evidence id")
            _load_root_evidence_reference(plugin_data, reference)
        _validate_finding_list(evidence["findings"], "root evidence")
        return evidence
    registry = dispatch.renderer.load_role_registry()
    schema = registry.evidence_schemas.get(step.output_schema)
    if schema is None or set(evidence) != set(schema["required_fields"]):
        raise DispatchReceiptError("role result does not match its output schema fields")
    for field, field_type in schema["field_types"].items():
        value = evidence[field]
        valid = True
        if field_type == "role-id":
            valid = isinstance(value, str) and dispatch.renderer.ROLE_ID.fullmatch(value) is not None
        elif field_type == "sha256":
            valid = isinstance(value, str) and HEX64.fullmatch(value) is not None
        elif field_type == "integer":
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif field_type == "boolean":
            valid = isinstance(value, bool)
        elif field_type == "number[0,10]":
            valid = (
                not isinstance(value, bool)
                and isinstance(value, (int, float))
                and math.isfinite(float(value))
                and 0 <= float(value) <= 10
            )
        elif field_type.startswith("list["):
            valid = isinstance(value, list)
            if valid and field_type == "list[string]":
                valid = all(isinstance(item, str) and bool(item) for item in value)
            elif valid and field_type == "list[list[string]]":
                valid = all(
                    isinstance(item, list)
                    and bool(item)
                    and all(isinstance(child, str) and bool(child) for child in item)
                    for item in value
                )
            elif valid and field_type == "list[integer]":
                valid = all(
                    isinstance(item, int) and not isinstance(item, bool)
                    for item in value
                )
            elif valid and field_type == "list[evidence-ref]":
                try:
                    for item in value:
                        _load_root_evidence_reference(plugin_data, item)
                    valid = len(value) == len(set(value))
                except DispatchReceiptError:
                    valid = False
            elif valid and field_type == "list[prerequisite-ref]":
                try:
                    for item in value:
                        _load_prerequisite_reference(plugin_data, item)
                    valid = len(value) == len(set(value))
                except DispatchReceiptError:
                    valid = False
            elif valid and field_type == "list[test-case]":
                valid = _validate_test_cases(plugin_data, value)
            elif valid and field_type == "list[observation]":
                valid = _validate_observations(plugin_data, value)
            elif field_type not in {
                "list[typed-finding]",
                "list[scored-dimension]",
                "list[typed-exclusion]",
            }:
                valid = False
        elif field_type == "enum":
            valid = value in schema["enum_fields"].get(field, [])
        elif field_type == "evidence-ref":
            try:
                _load_root_evidence_reference(plugin_data, value)
            except DispatchReceiptError:
                valid = False
        elif field_type == "repo-relative-path":
            try:
                valid = _safe(value, f"role result field {field}") == value
            except DispatchReceiptError:
                valid = False
        elif field_type == "git-sha":
            valid = isinstance(value, str) and GIT_OID.fullmatch(value) is not None
        elif field_type == "time-window":
            valid = _validate_time_window(value)
        else:
            valid = isinstance(value, str) and bool(value)
        if not valid:
            raise DispatchReceiptError(f"role result field {field} has the wrong type")
    if evidence.get("role_id") != step.role_id:
        raise DispatchReceiptError("role result does not bind the planned role")
    if "role_digest" in evidence and evidence["role_digest"] != step.role_lens_sha256:
        raise DispatchReceiptError("role result does not bind the planned lens")
    if "findings" in evidence:
        _validate_finding_list(evidence["findings"], "role evidence")
    if "evidence_refs" in evidence and set(evidence["evidence_refs"]) != set(
        evidence_bindings.values()
    ):
        raise DispatchReceiptError(
            "role evidence refs do not match the required evidence bindings"
        )
    if step.output_schema == "deploy-observation.v1":
        derived_eligibility = bool(
            re.fullmatch(r"github\.com/infiquetra/[A-Za-z0-9._-]+", evidence["remote"])
            and evidence["environment"] in {"nonprod", "publish-nonprod"}
            and evidence["branch"] == evidence["default_branch"]
        )
        if evidence["eligibility"] is not derived_eligibility:
            raise DispatchReceiptError(
                "deploy eligibility contradicts the closed automation policy"
            )
    if step.output_schema == "review-evidence.v1":
        dimensions = evidence["dimensions"]
        exclusions = evidence["exclusions"]
        expected_dimension_ids = set(_review_dimension_ids(registry, step.role_id))
        if not dimensions or evidence["denominator"] != len(dimensions):
            raise DispatchReceiptError(
                "review denominator must equal the non-empty applicable dimension set"
            )
        dimension_ids: set[str] = set()
        scores: list[float] = []
        for dimension in dimensions:
            if not isinstance(dimension, dict) or set(dimension) != {
                "dimension_id",
                "score",
                "notes",
            }:
                raise DispatchReceiptError("review dimension fields are not closed")
            dimension_id = _safe(dimension["dimension_id"], "review dimension id")
            score = dimension["score"]
            if (
                dimension_id in dimension_ids
                or isinstance(score, bool)
                or not isinstance(score, (int, float))
                or not math.isfinite(float(score))
                or not 0 <= float(score) <= 10
                or not isinstance(dimension["notes"], str)
                or not dimension["notes"]
            ):
                raise DispatchReceiptError("review dimension is invalid")
            dimension_ids.add(dimension_id)
            scores.append(float(score))
        if not math.isclose(
            float(evidence["overall"]), sum(scores) / len(scores), abs_tol=1e-9
        ):
            raise DispatchReceiptError("review overall is not the applicable-dimension mean")
        exclusion_ids: set[str] = set()
        if not isinstance(exclusions, list):
            raise DispatchReceiptError("review exclusions must be a list")
        for exclusion in exclusions:
            if not isinstance(exclusion, dict) or set(exclusion) != {
                "dimension_id",
                "reason",
            }:
                raise DispatchReceiptError("review exclusion fields are not closed")
            dimension_id = _safe(exclusion["dimension_id"], "review exclusion id")
            if (
                dimension_id in dimension_ids
                or dimension_id in exclusion_ids
                or exclusion["reason"] != "static-non-applicable"
            ):
                raise DispatchReceiptError("review exclusion is invalid")
            exclusion_ids.add(dimension_id)
        if dimension_ids | exclusion_ids != expected_dimension_ids:
            raise DispatchReceiptError(
                "review evidence does not cover the selected lens dimensions"
            )
        unresolved = [finding for finding in evidence["findings"] if not finding["resolved"]]
        blocking = any(
            finding["severity"] in {"P0", "P1"}
            or finding["category"] == "security"
            or finding["hard_stop"]
            for finding in unresolved
        )
        if step.role_id == "security-reviewer":
            security_hard_stops = {
                dimension["dimension_id"]
                for dimension in dimensions
                if dimension["dimension_id"]
                in {"auth-authz", "secrets-management"}
                and float(dimension["score"]) < 5.0
            }
            has_typed_security_hard_stop = any(
                finding["category"] == "security" and finding["hard_stop"] is True
                for finding in unresolved
            )
            if security_hard_stops and not has_typed_security_hard_stop:
                raise DispatchReceiptError(
                    "security hard-stop scores require matching typed hard-stop findings"
                )
            blocking = blocking or bool(security_hard_stops)
        scores_accept = float(evidence["overall"]) >= 9.0 and all(
            score >= 7.0 for score in scores
        )
        expected_verdict = (
            "blocking"
            if blocking
            else "needs-revision"
            if unresolved or not scores_accept
            else "accept"
        )
        if evidence["verdict"] != expected_verdict:
            raise DispatchReceiptError("review verdict does not match typed findings")
    gate_status = evidence.get("gate_status")
    if gate_status is not None:
        command_records: list[dict[str, Any]] = []
        if step.output_schema in {"tester-evidence.v1", "scanner-evidence.v1"}:
            for reference in evidence["evidence_refs"]:
                if not reference.startswith("record:command-output:"):
                    raise DispatchReceiptError(
                        "tester and scanner evidence requires command-output records"
                    )
                record, _record_bytes = _load_command_output_record(
                    plugin_data, reference
                )
                command_records.append(record)
        if (
            step.role_kind == "agent-lens"
            and gate_status != "skipped-by-config"
            and "evidence_refs" in evidence
            and not evidence["evidence_refs"]
        ):
            raise DispatchReceiptError(
                "agent validator evidence requires a protected evidence record"
            )
        if step.validator_disabled is True and gate_status != "skipped-by-config":
            raise DispatchReceiptError("disabled validator evidence must be skipped")
        if step.validator_disabled is not True and gate_status == "skipped-by-config":
            raise DispatchReceiptError("enabled validator cannot be skipped by config")
        unresolved = [
            finding
            for finding in evidence.get("findings", [])
            if not finding["resolved"]
        ]
        if gate_status == "pass" and unresolved:
            raise DispatchReceiptError(
                "passing validator evidence cannot contain unresolved findings"
            )
        if gate_status == "pass" and (
            ("exit_code" in evidence and evidence["exit_code"] != 0)
            or (
                "exit_codes" in evidence
                and any(exit_code != 0 for exit_code in evidence["exit_codes"])
            )
        ):
            raise DispatchReceiptError(
                "passing validator evidence requires zero exit codes"
            )
        if step.output_schema == "scanner-evidence.v1":
            aligned = len(evidence["tools"]) == len(evidence["argv"]) == len(
                evidence["exit_codes"]
            )
            if evidence["required"] is not (step.validator_required is True):
                raise DispatchReceiptError(
                    "scanner required flag does not match the workflow policy"
                )
            if not aligned or (gate_status == "pass" and not evidence["tools"]):
                raise DispatchReceiptError(
                    "scanner tools, argv, and exit codes must be nonempty and aligned"
                )
            if (
                evidence["argv"] != [record["argv"] for record in command_records]
                or evidence["exit_codes"]
                != [record["exit_code"] for record in command_records]
                or evidence["tools"]
                != [PurePosixPath(record["argv"][0]).name for record in command_records]
            ):
                raise DispatchReceiptError(
                    "scanner claims do not derive from command-output records"
                )
            if (
                all(code == 0 for code in evidence["exit_codes"])
                and gate_status not in {"pass", "warn"}
            ) or (
                any(code != 0 for code in evidence["exit_codes"])
                and gate_status not in {"hard-fail", "blocked"}
            ):
                raise DispatchReceiptError(
                    "scanner gate status does not derive from command exit codes"
                )
        if step.output_schema == "tester-evidence.v1":
            case_statuses = [case["status"] for case in evidence["cases"]]
            consistent = {
                "pass": bool(case_statuses)
                and all(status == "pass" for status in case_statuses),
                "warn": "warn" in case_statuses
                and all(status in {"pass", "warn"} for status in case_statuses),
                "hard-fail": "hard-fail" in case_statuses
                and "blocked" not in case_statuses,
                "blocked": "blocked" in case_statuses,
                "skipped-by-config": not case_statuses
                or all(status == "skipped-by-config" for status in case_statuses),
            }[gate_status]
            if not consistent or (
                gate_status == "pass" and not evidence["declared_argv"]
            ):
                raise DispatchReceiptError(
                    "tester aggregate status contradicts its typed cases"
                )
            if len(command_records) != 1 or (
                evidence["declared_argv"] != command_records[0]["argv"]
                or evidence["exit_code"] != command_records[0]["exit_code"]
                or any(
                    case["evidence_ref"] != evidence["evidence_refs"][0]
                    for case in evidence["cases"]
                )
            ):
                raise DispatchReceiptError(
                    "tester claims do not derive from one command-output record"
                )
            if (
                evidence["exit_code"] == 0
                and gate_status not in {"pass", "warn"}
            ) or (
                evidence["exit_code"] != 0
                and gate_status not in {"hard-fail", "blocked"}
            ):
                raise DispatchReceiptError(
                    "tester gate status does not derive from the command exit code"
                )
        if step.output_schema == "monitor-evidence.v1":
            observation_states = [
                observation["health_state"] for observation in evidence["observations"]
            ]
            health_state = evidence["health_state"]
            health_consistent = {
                "healthy": bool(observation_states)
                and all(state == "healthy" for state in observation_states),
                "degraded": "degraded" in observation_states
                and "missing-signal" not in observation_states,
                "missing-signal": "missing-signal" in observation_states,
                "not-applicable": not observation_states
                or all(state == "not-applicable" for state in observation_states),
            }[health_state]
            status_consistent = {
                "healthy": gate_status == "pass",
                "degraded": gate_status == "warn",
                "missing-signal": gate_status in {"hard-fail", "blocked"},
                "not-applicable": gate_status in {"pass", "skipped-by-config"},
            }[health_state]
            if not health_consistent or not status_consistent:
                raise DispatchReceiptError(
                    "monitor aggregate state contradicts its typed observations"
                )
        if (
            step.output_schema == "deploy-observation.v1"
            and gate_status == "pass"
            and (
                evidence["eligibility"] is not True
                or evidence["run_status"] != "succeeded"
            )
        ):
            raise DispatchReceiptError(
                "passing deploy evidence requires an eligible successful run"
            )
        if step.output_schema in {"monitor-evidence.v1", "deploy-observation.v1"}:
            if step.validator_required is True:
                raise DispatchReceiptError(
                    "required monitor/deploy evidence awaits an authenticated observation adapter"
                )
            if gate_status != "warn":
                raise DispatchReceiptError(
                    "nonrequired monitor/deploy evidence is advisory and must warn"
                )
    return evidence


def _validate_contextual_evidence(
    plugin_data: Path,
    workflow: dispatch.Workflow,
    step: dispatch.WorkflowStep,
    evidence: Mapping[str, Any],
    intent_ref: str,
    intent: Mapping[str, Any],
    subject: Mapping[str, Any],
    mutation_audit_ref: str | None,
    mutation_audit: Mapping[str, Any] | None,
    result_recorded_at: dt.datetime,
    evidence_bindings: Mapping[str, str],
) -> None:
    intent_created_at = _parse_time(intent["created_at"], "intent.created_at")
    current_run_sha256 = subject["workflow_run_sha256"]
    current_repository_sha256 = subject["repository_sha256"]

    evidence_refs: list[str] = []
    evidence_refs.extend(evidence_bindings.values())
    root_refs = evidence.get("evidence_refs", [])
    if isinstance(root_refs, dict):
        evidence_refs.extend(root_refs.values())
    else:
        evidence_refs.extend(root_refs)
    evidence_refs.extend(
        case["evidence_ref"] for case in evidence.get("cases", [])
    )
    evidence_refs.extend(
        observation["evidence_ref"]
        for observation in evidence.get("observations", [])
    )
    for reference in set(evidence_refs):
        parts = reference.split(":")
        kind = parts[1]
        permits_pre_intent_record = False
        if kind == "subject":
            record, _record_bytes = _load_subject_record(plugin_data, reference)
            recorded_at = _parse_time(record["created_at"], "evidence subject.created_at")
            if (
                record["repository_sha256"] != current_repository_sha256
                or record["workflow_run_sha256"] != current_run_sha256
                or record["paths"] != subject["paths"]
                or not _subject_descends_from(
                    plugin_data, reference, intent["subject_ref"]
                )
            ):
                raise DispatchReceiptError("evidence subject belongs to another workflow run")
            permits_pre_intent_record = reference == intent["subject_ref"]
        elif kind == "workspace-snapshot":
            record, _record_bytes = _load_workspace_snapshot_record(
                plugin_data, reference
            )
            recorded_at = _parse_time(
                record["created_at"], "evidence workspace snapshot.created_at"
            )
            if record["repository_sha256"] != current_repository_sha256:
                raise DispatchReceiptError("evidence snapshot belongs to another repository")
            allowed_snapshot_refs = {intent["workspace_snapshot_ref"]}
            if mutation_audit is not None:
                allowed_snapshot_refs.add(mutation_audit["after_ref"])
            if reference not in allowed_snapshot_refs:
                raise DispatchReceiptError(
                    "evidence snapshot is not part of the current execution audit"
                )
            permits_pre_intent_record = reference == intent["workspace_snapshot_ref"]
        elif kind == "mutation-audit":
            record, _record_bytes = _load_mutation_audit_record(plugin_data, reference)
            recorded_at = _parse_time(
                record["recorded_at"], "evidence mutation audit.recorded_at"
            )
            if (
                record["repository_sha256"] != current_repository_sha256
                or record["before_ref"] != intent["workspace_snapshot_ref"]
                or reference != mutation_audit_ref
            ):
                raise DispatchReceiptError("evidence audit belongs to another execution")
        else:
            record, _record_bytes = _load_command_output_record(plugin_data, reference)
            recorded_at = _parse_time(
                record["recorded_at"], "evidence command output.recorded_at"
            )
            if (
                record["workflow_run_sha256"] != current_run_sha256
                or record["intent_ref"] != intent_ref
            ):
                raise DispatchReceiptError("command evidence belongs to another execution")
        if not (
            recorded_at <= result_recorded_at
            and (permits_pre_intent_record or intent_created_at <= recorded_at)
        ):
            raise DispatchReceiptError("protected evidence is stale for this execution")

    for reference in evidence.get("prerequisite_gate_refs", []):
        prerequisite, _prerequisite_bytes = load_protected_record(
            plugin_data, reference, "role-result"
        )
        dependency_id = prerequisite.get("step_id")
        if dependency_id not in step.depends_on:
            raise DispatchReceiptError(
                "prerequisite evidence is not from a declared dependency"
            )
        prerequisite_result, _result_bytes = _load_result_record(
            plugin_data,
            reference,
            workflow,
            dependency_id,
            attempt=prerequisite.get("attempt"),
            task_id=prerequisite.get("task_id"),
            intent_ref=prerequisite.get("intent_ref"),
            vehicle=prerequisite.get("vehicle"),
            child_id=prerequisite.get("child_id"),
        )
        prerequisite_intent, _prerequisite_intent_bytes = _load_intent_record(
            plugin_data,
            prerequisite_result["intent_ref"],
            workflow,
            dependency_id,
            prerequisite_result["attempt"],
            prerequisite_result["task_id"],
        )
        if (
            prerequisite_intent["workflow_run_sha256"] != current_run_sha256
            or _parse_time(
                prerequisite_result["recorded_at"], "prerequisite result.recorded_at"
            )
            > intent_created_at
            or not _subject_descends_from(
                plugin_data,
                intent["subject_ref"],
                prerequisite_result["output_subject_ref"],
            )
        ):
            raise DispatchReceiptError(
                "prerequisite evidence does not precede this same-run dependency"
            )

    if step.output_schema == "deploy-observation.v1":
        workflow_run, _workflow_run_bytes = _load_workflow_run_record(
            plugin_data, subject["workflow_run_ref"]
        )
        if evidence["commit_sha"] != workflow_run["head_revision"]:
            raise DispatchReceiptError(
                "deploy observation does not bind the workflow run commit"
            )
    if step.output_schema == "monitor-evidence.v1":
        started_at = _parse_time(
            evidence["time_window"]["started_at"], "monitor time window.started_at"
        )
        ended_at = _parse_time(
            evidence["time_window"]["ended_at"], "monitor time window.ended_at"
        )
        if not (
            started_at <= ended_at <= result_recorded_at
            and ended_at - started_at <= dt.timedelta(hours=24)
            and result_recorded_at - ended_at <= dt.timedelta(hours=1)
        ):
            raise DispatchReceiptError(
                "monitor time window is stale or outside the protected execution"
            )


def _validate_deterministic_tester_output(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "target",
        "expected",
        "actual",
        "cases",
        "gate_status",
    }:
        raise DispatchReceiptError("deterministic stdout fields are not closed")
    if any(
        not isinstance(value[field], str) or not value[field]
        for field in ("target", "expected", "actual")
    ) or value["gate_status"] not in dispatch.renderer.GATE_STATUSES:
        raise DispatchReceiptError("deterministic stdout scalar fields are invalid")
    cases = value["cases"]
    if not isinstance(cases, list) or len(cases) > 1024:
        raise DispatchReceiptError("deterministic stdout cases are invalid")
    case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"case_id", "status"}:
            raise DispatchReceiptError("deterministic stdout case fields are not closed")
        case_id = _safe(case["case_id"], "deterministic stdout case_id")
        if case_id in case_ids or case["status"] not in dispatch.renderer.GATE_STATUSES:
            raise DispatchReceiptError("deterministic stdout case is invalid")
        case_ids.add(case_id)
    return dict(value)


def create_command_output_record(
    plugin_data: Path,
    workflow: dispatch.Workflow,
    step_id: str,
    *,
    attempt: int,
    task_id: str,
    intent_ref: str,
    stdout_file: Path,
    stderr_file: Path,
    exit_code: int,
    output_limit_bytes: int,
    argv: list[str] | None = None,
    recorded_at: str | None = None,
) -> str:
    step = workflow.step(step_id)
    deterministic = step.vehicle == "deterministic-tool"
    if not deterministic and step.role_kind != "agent-lens":
        raise DispatchReceiptError(
            "command output requires a deterministic or agent-validator workflow step"
        )
    if deterministic:
        actual_argv = list(step.command)
        if argv is not None and argv != actual_argv:
            raise DispatchReceiptError("deterministic command argv is pinned by the plan")
    else:
        actual_argv = list(argv or [])
        if not actual_argv or any(
            not isinstance(value, str) or not value or "\x00" in value
            for value in actual_argv
        ):
            raise DispatchReceiptError("agent-validator command argv is invalid")
    attempt = _attempt(attempt, "command output attempt")
    task_id = _safe(task_id, "task_id")
    intent, intent_bytes = _load_intent_record(
        plugin_data,
        intent_ref,
        workflow,
        step_id,
        attempt,
        task_id,
    )
    if isinstance(exit_code, bool) or not isinstance(exit_code, int):
        raise DispatchReceiptError("command output exit code is invalid")
    if (
        isinstance(output_limit_bytes, bool)
        or not isinstance(output_limit_bytes, int)
        or not 1
        <= output_limit_bytes
        <= dispatch.renderer.MAX_DETERMINISTIC_OUTPUT_BYTES
    ):
        raise DispatchReceiptError("command output byte ceiling is invalid")
    try:
        stdout = hook_receipt._read_regular(
            stdout_file, "command stdout", MAX_SUBJECT_BYTES
        )
        stderr = hook_receipt._read_regular(
            stderr_file, "command stderr", MAX_SUBJECT_BYTES
        )
    except hook_receipt.AgentReceiptError as exc:
        raise DispatchReceiptError("command output files are missing or unsafe") from exc
    if len(stdout) + len(stderr) > output_limit_bytes:
        raise DispatchReceiptError("command output exceeds its declared byte ceiling")
    parsed_output: dict[str, Any] | None = None
    if deterministic:
        try:
            stdout_text = stdout.decode("utf-8")
            stdout_json = json.loads(stdout_text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DispatchReceiptError(
                "deterministic command stdout must be one UTF-8 JSON value"
            ) from exc
        _validate_json_structure(stdout_json, "command stdout")
        parsed_output = _validate_deterministic_tester_output(stdout_json)
    recorded_at = recorded_at or _timestamp_now()
    output_recorded_at = _parse_time(recorded_at, "command output.recorded_at")
    if output_recorded_at < _parse_time(intent["created_at"], "intent.created_at"):
        raise DispatchReceiptError("command output predates its execution intent")
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "command-output",
            "workflow_sha256": workflow.sha256,
            "workflow_run_sha256": intent["workflow_run_sha256"],
            "step_id": step_id,
            "attempt": attempt,
            "task_id": task_id,
            "intent_ref": intent_ref,
            "intent_sha256": _sha256(intent_bytes),
            "output_kind": (
                "deterministic-validator" if deterministic else "root-command"
            ),
            "argv": actual_argv,
            "implementation_sha256": (
                step.command_implementation_sha256 if deterministic else None
            ),
            "evidence_schema_sha256": (
                step.evidence_schema_sha256 if deterministic else None
            ),
            "cwd": "repo-root",
            "timeout_seconds": step.command_timeout_seconds if deterministic else None,
            "stdout_sha256": _sha256(stdout),
            "stdout_bytes": len(stdout),
            "stderr_sha256": _sha256(stderr),
            "stderr_bytes": len(stderr),
            "parsed_output": parsed_output,
            "combined_sha256": _sha256(
                _canonical_bytes(
                    {
                        "stdout_sha256": _sha256(stdout),
                        "stderr_sha256": _sha256(stderr),
                    }
                )
            ),
            "exit_code": exit_code,
            "output_limit_bytes": output_limit_bytes,
            "recorded_at": recorded_at,
        },
    )
    _load_command_output_record(plugin_data, reference, workflow=workflow)
    return reference


def _load_command_output_record(
    plugin_data: Path,
    reference: str,
    *,
    workflow: dispatch.Workflow | None = None,
) -> tuple[dict[str, Any], bytes]:
    record, content = load_protected_record(plugin_data, reference, "command-output")
    if set(record) != {
        "schema_version",
        "record_type",
        "workflow_sha256",
        "workflow_run_sha256",
        "step_id",
        "attempt",
        "task_id",
        "intent_ref",
        "intent_sha256",
        "output_kind",
        "argv",
        "implementation_sha256",
        "evidence_schema_sha256",
        "cwd",
        "timeout_seconds",
        "stdout_sha256",
        "stdout_bytes",
        "stderr_sha256",
        "stderr_bytes",
        "parsed_output",
        "combined_sha256",
        "exit_code",
        "output_limit_bytes",
        "recorded_at",
    }:
        raise DispatchReceiptError("command output fields are not closed")
    if (
        not isinstance(record["workflow_sha256"], str)
        or not HEX64.fullmatch(record["workflow_sha256"])
        or not isinstance(record["workflow_run_sha256"], str)
        or not HEX64.fullmatch(record["workflow_run_sha256"])
        or not isinstance(record["step_id"], str)
        or not dispatch.STEP_ID.fullmatch(record["step_id"])
        or isinstance(record["attempt"], bool)
        or not isinstance(record["attempt"], int)
        or not 1 <= record["attempt"] <= dispatch.MAX_CYCLES
        or _safe(record["task_id"], "command output task_id") != record["task_id"]
        or not isinstance(record["intent_ref"], str)
        or not isinstance(record["intent_sha256"], str)
        or not HEX64.fullmatch(record["intent_sha256"])
        or not isinstance(record["argv"], list)
        or not record["argv"]
        or any(not isinstance(value, str) or not value for value in record["argv"])
        or record["output_kind"]
        not in {"deterministic-validator", "root-command"}
        or record["cwd"] != "repo-root"
    ):
        raise DispatchReceiptError("command output execution identity is invalid")
    deterministic = record["output_kind"] == "deterministic-validator"
    if deterministic:
        if (
            not isinstance(record["implementation_sha256"], str)
            or not HEX64.fullmatch(record["implementation_sha256"])
            or not isinstance(record["evidence_schema_sha256"], str)
            or not HEX64.fullmatch(record["evidence_schema_sha256"])
            or isinstance(record["timeout_seconds"], bool)
            or not isinstance(record["timeout_seconds"], int)
            or not 1 <= record["timeout_seconds"] <= 3600
        ):
            raise DispatchReceiptError("deterministic command identity is invalid")
    elif any(
        record[field] is not None
        for field in (
            "implementation_sha256",
            "evidence_schema_sha256",
            "timeout_seconds",
            "parsed_output",
        )
    ):
        raise DispatchReceiptError("root command carries deterministic-only fields")
    if any(
        not isinstance(record[field], str) or not HEX64.fullmatch(record[field])
        for field in ("stdout_sha256", "stderr_sha256", "combined_sha256")
    ) or any(
        isinstance(record[field], bool)
        or not isinstance(record[field], int)
        or record[field] < 0
        for field in ("stdout_bytes", "stderr_bytes")
    ):
        raise DispatchReceiptError("command output digests or sizes are invalid")
    if deterministic:
        _validate_json_structure(record["parsed_output"], "command parsed output")
        _validate_deterministic_tester_output(record["parsed_output"])
    if isinstance(record["exit_code"], bool) or not isinstance(record["exit_code"], int):
        raise DispatchReceiptError("command output exit code is invalid")
    if (
        isinstance(record["output_limit_bytes"], bool)
        or not isinstance(record["output_limit_bytes"], int)
        or not 1
        <= record["output_limit_bytes"]
        <= dispatch.renderer.MAX_DETERMINISTIC_OUTPUT_BYTES
        or record["stdout_bytes"] + record["stderr_bytes"]
        > record["output_limit_bytes"]
    ):
        raise DispatchReceiptError("command output byte ceiling is invalid")
    expected_combined = _sha256(
        _canonical_bytes(
            {
                "stdout_sha256": record["stdout_sha256"],
                "stderr_sha256": record["stderr_sha256"],
            }
        )
    )
    if record["combined_sha256"] != expected_combined:
        raise DispatchReceiptError("command output combined digest is invalid")
    recorded_at = _parse_time(record["recorded_at"], "command output.recorded_at")
    if workflow is not None:
        intent, intent_bytes = _load_intent_record(
            plugin_data,
            record["intent_ref"],
            workflow,
            record["step_id"],
            record["attempt"],
            record["task_id"],
        )
        step = workflow.step(record["step_id"])
        common_invalid = (
            record["workflow_sha256"] != workflow.sha256
            or record["workflow_run_sha256"] != intent["workflow_run_sha256"]
            or record["intent_sha256"] != _sha256(intent_bytes)
            or recorded_at < _parse_time(intent["created_at"], "intent.created_at")
        )
        deterministic_invalid = deterministic and (
            step.vehicle != "deterministic-tool"
            or record["argv"] != list(step.command)
            or record["implementation_sha256"]
            != step.command_implementation_sha256
            or record["evidence_schema_sha256"] != step.evidence_schema_sha256
            or record["timeout_seconds"] != step.command_timeout_seconds
            or record["output_limit_bytes"] != step.command_output_limit_bytes
        )
        root_command_invalid = not deterministic and (
            step.role_kind != "agent-lens"
            or record["output_limit_bytes"]
            > dispatch.renderer.MAX_DETERMINISTIC_OUTPUT_BYTES
        )
        if common_invalid or deterministic_invalid or root_command_invalid:
            raise DispatchReceiptError(
                "command output does not bind its workflow execution intent"
            )
    return record, content


def _validated_execution(
    plugin_data: Path,
    workflow: dispatch.Workflow,
    step: dispatch.WorkflowStep,
    vehicle: str,
    execution: Mapping[str, Any],
    evidence: Mapping[str, Any],
    intent_ref: str,
    intent: Mapping[str, Any],
) -> dict[str, Any]:
    value = dict(execution)
    _validate_json_structure(value, "result execution")
    if vehicle in {"verified-workflow-subagent", "verified-workflow-inline"}:
        expected = {
            "kind": "agent-lens",
            "execution_class": step.execution_class,
            "profile_sha256": step.profile_sha256,
        }
    elif vehicle == "deterministic-tool":
        exit_code = value.get("exit_code")
        output_ref = value.get("output_ref")
        output, _output_bytes = _load_command_output_record(
            plugin_data,
            output_ref,
            workflow=workflow,
        )
        retained_output = _validate_deterministic_tester_output(
            output["parsed_output"]
        )
        expected = {
            "kind": "deterministic-validator",
            "argv": list(step.command),
            "implementation_sha256": step.command_implementation_sha256,
            "evidence_schema_sha256": step.evidence_schema_sha256,
            "cwd": "repo-root",
            "timeout_seconds": step.command_timeout_seconds,
            "output_limit_bytes": step.command_output_limit_bytes,
            "output_ref": output_ref,
            "exit_code": exit_code,
        }
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            raise DispatchReceiptError("deterministic result exit code is invalid")
        evidence_exit_code = evidence.get("exit_code")
        if evidence_exit_code is not None and evidence_exit_code != exit_code:
            raise DispatchReceiptError(
                "deterministic evidence exit code does not match execution"
            )
        evidence_argv = evidence.get("declared_argv")
        if evidence_argv is not None and evidence_argv != list(step.command):
            raise DispatchReceiptError(
                "deterministic evidence argv does not match the pinned command"
            )
        evidence_argvs = evidence.get("argv")
        if evidence_argvs is not None and evidence_argvs != [list(step.command)]:
            raise DispatchReceiptError(
                "deterministic evidence argv does not match the pinned command"
            )
        if evidence.get("gate_status") == "pass" and exit_code != 0:
            raise DispatchReceiptError(
                "deterministic passing evidence requires a zero exit code"
            )
        expected_evidence = {
            "role_id": step.role_id,
            "role_digest": step.role_lens_sha256,
            "target": retained_output["target"],
            "declared_argv": list(step.command),
            "expected": retained_output["expected"],
            "actual": retained_output["actual"],
            "exit_code": exit_code,
            "evidence_refs": [output_ref],
            "cases": [
                {**case, "evidence_ref": output_ref}
                for case in retained_output["cases"]
            ],
            "gate_status": retained_output["gate_status"],
        }
        if evidence != expected_evidence:
            raise DispatchReceiptError(
                "deterministic evidence contradicts retained command output"
            )
        if (
            output["exit_code"] != exit_code
            or output["output_limit_bytes"] != step.command_output_limit_bytes
            or output["intent_ref"] != intent_ref
            or output["workflow_run_sha256"] != intent["workflow_run_sha256"]
        ):
            raise DispatchReceiptError("deterministic output violates its execution contract")
    else:
        expected = {"kind": "root"}
    if value != expected:
        raise DispatchReceiptError("role result execution does not bind the planned vehicle")
    return value


def create_result_record(
    plugin_data: Path,
    workflow: dispatch.Workflow,
    step_id: str,
    *,
    attempt: int,
    task_id: str,
    intent_ref: str,
    output_subject_ref: str,
    mutation_audit_ref: str | None,
    workspace_root: Path | None,
    vehicle: str,
    child_id: str | None,
    provided_evidence: list[str],
    evidence: Mapping[str, Any],
    execution: Mapping[str, Any],
    recorded_at: str | None = None,
) -> str:
    attempt = _attempt(attempt, "result attempt")
    task_id = _safe(task_id, "task_id")
    intent, _intent_bytes = _load_intent_record(
        plugin_data, intent_ref, workflow, step_id, attempt, task_id
    )
    subject, _subject_bytes = _load_subject_record(plugin_data, intent["subject_ref"])
    output_subject, _output_subject_bytes = _load_subject_record(
        plugin_data, output_subject_ref
    )
    step = workflow.step(step_id)
    if (
        output_subject["repository_sha256"] != subject["repository_sha256"]
        or output_subject["paths"] != subject["paths"]
    ):
        raise DispatchReceiptError("result output subject changes the declared work scope")
    if step.mutation == "none" and output_subject_ref != intent["subject_ref"]:
        raise DispatchReceiptError("read-only result cannot change the protected subject")
    if (
        output_subject_ref != intent["subject_ref"]
        and intent["subject_ref"] not in output_subject["parent_refs"]
    ):
        raise DispatchReceiptError("result output subject does not descend from its input")
    mutation_audit: dict[str, Any] | None = None
    after_snapshot: dict[str, Any] | None = None
    audited_vehicle = vehicle in {
        "verified-workflow-subagent",
        "verified-workflow-inline",
        "deterministic-tool",
    }
    if audited_vehicle:
        if mutation_audit_ref is None:
            raise DispatchReceiptError("executed result requires a protected mutation audit")
        mutation_audit, _mutation_audit_bytes = _load_mutation_audit_record(
            plugin_data, mutation_audit_ref
        )
        if workspace_root is None:
            raise DispatchReceiptError("executed result requires the audited workspace root")
        after_snapshot, _after_snapshot_bytes = _load_workspace_snapshot_record(
            plugin_data,
            mutation_audit["after_ref"],
            workspace_root=workspace_root,
        )
        if (
            mutation_audit["before_ref"] != intent["workspace_snapshot_ref"]
            or mutation_audit["repository_sha256"] != subject["repository_sha256"]
            or (step.mutation == "none" and mutation_audit["mutation_observed"])
            or _parse_time(after_snapshot["created_at"], "workspace snapshot.created_at")
            < _parse_time(intent["created_at"], "intent.created_at")
        ):
            raise DispatchReceiptError("executed result mutation audit is invalid")
    elif mutation_audit_ref is not None or workspace_root is not None:
        raise DispatchReceiptError("root result cannot carry an execution mutation audit")
    if vehicle not in {
        "verified-workflow-subagent",
        "verified-workflow-inline",
        "deterministic-tool",
        "root",
    }:
        raise DispatchReceiptError("result vehicle is invalid")
    if child_id is not None:
        child_id = _runtime_id(child_id, "child_id")
    if vehicle == "verified-workflow-subagent" and child_id is None:
        raise DispatchReceiptError("subagent result requires a child identity")
    if vehicle != "verified-workflow-subagent" and child_id is not None:
        raise DispatchReceiptError("non-subagent result cannot claim a child identity")
    normalized_evidence = tuple(_safe(value, "provided evidence") for value in provided_evidence)
    if len(normalized_evidence) != len(set(normalized_evidence)):
        raise DispatchReceiptError("provided evidence contains duplicates")
    if tuple(step.required_evidence) != normalized_evidence:
        raise DispatchReceiptError("result is missing required workflow evidence")
    if not isinstance(evidence, Mapping) or not isinstance(execution, Mapping):
        raise DispatchReceiptError("result evidence and execution must be objects")
    evidence_bindings = _derive_evidence_bindings(
        plugin_data,
        step,
        evidence,
        normalized_evidence,
        subject_ref=intent["subject_ref"],
    )
    validated_evidence = _validate_evidence(
        plugin_data,
        step,
        dict(evidence),
        evidence_bindings,
    )
    if (
        step.output_schema == "review-evidence.v1"
        and validated_evidence["input_digest"] != subject["content_sha256"]
    ):
        raise DispatchReceiptError("review evidence does not bind the protected subject")
    execution_payload = _validated_execution(
        plugin_data,
        workflow,
        step,
        vehicle,
        execution,
        validated_evidence,
        intent_ref,
        intent,
    )
    recorded_at = recorded_at or _timestamp_now()
    result_recorded_at = _parse_time(recorded_at, "result.recorded_at")
    if result_recorded_at < _parse_time(intent["created_at"], "intent.created_at"):
        raise DispatchReceiptError("result predates its execution intent")
    _validate_contextual_evidence(
        plugin_data,
        workflow,
        step,
        validated_evidence,
        intent_ref,
        intent,
        subject,
        mutation_audit_ref,
        mutation_audit,
        result_recorded_at,
        evidence_bindings,
    )
    if mutation_audit is not None and _parse_time(
        mutation_audit["recorded_at"], "mutation audit.recorded_at"
    ) > result_recorded_at:
        raise DispatchReceiptError("result predates its mutation audit")
    if vehicle == "deterministic-tool":
        command_output, _command_output_bytes = _load_command_output_record(
            plugin_data,
            execution_payload["output_ref"],
            workflow=workflow,
        )
        if after_snapshot is None or _parse_time(
            command_output["recorded_at"], "command output.recorded_at"
        ) > _parse_time(after_snapshot["created_at"], "workspace snapshot.created_at"):
            raise DispatchReceiptError(
                "deterministic after snapshot predates command output"
            )
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "role-result",
            "intent_ref": intent_ref,
            "subject_ref": intent["subject_ref"],
            "subject_content_sha256": subject["content_sha256"],
            "output_subject_ref": output_subject_ref,
            "output_subject_content_sha256": output_subject["content_sha256"],
            "mutation_audit_ref": mutation_audit_ref,
            "workflow_sha256": workflow.sha256,
            "step_id": step_id,
            "attempt": attempt,
            "task_id": task_id,
            "vehicle": vehicle,
            "child_id": child_id,
            "role_id": step.role_id,
            "role_lens_sha256": step.role_lens_sha256,
            "output_schema": step.output_schema,
            "provided_evidence": evidence_bindings,
            "evidence_sha256": _sha256(_canonical_bytes(validated_evidence)),
            "evidence": validated_evidence,
            "execution": execution_payload,
            "recorded_at": recorded_at,
        },
    )
    _load_result_record(
        plugin_data,
        reference,
        workflow,
        step_id,
        attempt=attempt,
        task_id=task_id,
        intent_ref=intent_ref,
        vehicle=vehicle,
        child_id=child_id,
    )
    return reference


def _subject_descends_from(
    plugin_data: Path,
    descendant_ref: str,
    ancestor_ref: str,
) -> bool:
    pending = [descendant_ref]
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current == ancestor_ref:
            return True
        if current in visited:
            continue
        visited.add(current)
        subject, _subject_bytes = _load_subject_record(plugin_data, current)
        pending.extend(subject["parent_refs"])
        if len(visited) > MAX_SUBJECT_ANCESTRY:
            raise DispatchReceiptError("subject ancestry exceeds the traversal ceiling")
    return False


def _load_resolution_evidence(plugin_data: Path, reference: str) -> None:
    parts = reference.split(":") if isinstance(reference, str) else []
    allowed = {"subject", "mutation-audit", "workspace-snapshot", "role-result"}
    if len(parts) != 3 or parts[0] != "record" or parts[1] not in allowed:
        raise DispatchReceiptError("resolution evidence must be a protected record")
    load_protected_record(plugin_data, reference, parts[1])


def create_resolution_record(
    plugin_data: Path,
    *,
    result_ref: str,
    finding_id: str,
    resolved_subject_ref: str,
    evidence_refs: list[str],
    recorded_at: str | None = None,
) -> str:
    result, _result_bytes = load_protected_record(plugin_data, result_ref, "role-result")
    finding_id = _safe(finding_id, "resolution finding_id")
    findings = result.get("evidence", {}).get("findings", [])
    matches = [
        finding
        for finding in findings
        if isinstance(finding, dict) and finding.get("finding_id") == finding_id
    ]
    if len(matches) != 1 or matches[0].get("resolved") is not False:
        raise DispatchReceiptError("resolution does not bind one original unresolved finding")
    normalized_evidence = tuple(evidence_refs)
    if not normalized_evidence or len(normalized_evidence) != len(set(normalized_evidence)):
        raise DispatchReceiptError("resolution requires unique protected evidence references")
    for evidence_ref in normalized_evidence:
        _load_resolution_evidence(plugin_data, evidence_ref)
    finding_subject, _finding_subject_bytes = _load_subject_record(
        plugin_data, result.get("output_subject_ref")
    )
    resolved_subject, _resolved_subject_bytes = _load_subject_record(
        plugin_data, resolved_subject_ref
    )
    if (
        resolved_subject_ref not in normalized_evidence
        or resolved_subject_ref == result.get("output_subject_ref")
        or resolved_subject["content_sha256"] == finding_subject["content_sha256"]
        or resolved_subject["repository_sha256"]
        != finding_subject["repository_sha256"]
        or resolved_subject["paths"] != finding_subject["paths"]
        or not _subject_descends_from(
            plugin_data, resolved_subject_ref, result["output_subject_ref"]
        )
    ):
        raise DispatchReceiptError("resolution lacks a changed descendant subject")
    recorded_at = recorded_at or _timestamp_now()
    result_recorded_at = _parse_time(result.get("recorded_at"), "result.recorded_at")
    resolved_subject_created_at = _parse_time(
        resolved_subject["created_at"], "resolved subject.created_at"
    )
    resolution_recorded_at = _parse_time(recorded_at, "resolution.recorded_at")
    if not (
        result_recorded_at < resolved_subject_created_at <= resolution_recorded_at
    ):
        raise DispatchReceiptError(
            "resolution subject must be created after the finding and before resolution"
        )
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "resolution",
            "result_ref": result_ref,
            "finding_id": finding_id,
            "finding_subject_ref": result["output_subject_ref"],
            "finding_subject_content_sha256": finding_subject["content_sha256"],
            "resolved_subject_ref": resolved_subject_ref,
            "resolved_subject_content_sha256": resolved_subject["content_sha256"],
            "evidence_refs": list(normalized_evidence),
            "recorded_by": "root",
            "recorded_at": recorded_at,
        },
    )
    _load_resolution_record(plugin_data, reference, result_ref=result_ref)
    return reference


def _load_resolution_record(
    plugin_data: Path,
    reference: str,
    *,
    result_ref: str | None = None,
) -> tuple[dict[str, Any], bytes]:
    record, content = load_protected_record(plugin_data, reference, "resolution")
    if set(record) != {
        "schema_version",
        "record_type",
        "result_ref",
        "finding_id",
        "finding_subject_ref",
        "finding_subject_content_sha256",
        "resolved_subject_ref",
        "resolved_subject_content_sha256",
        "evidence_refs",
        "recorded_by",
        "recorded_at",
    }:
        raise DispatchReceiptError("resolution record fields are not closed")
    actual_result_ref = record.get("result_ref")
    if result_ref is not None and actual_result_ref != result_ref:
        raise DispatchReceiptError("resolution record belongs to a different result")
    result, _result_bytes = load_protected_record(
        plugin_data, actual_result_ref, "role-result"
    )
    finding_subject, _finding_subject_bytes = _load_subject_record(
        plugin_data, record["finding_subject_ref"]
    )
    resolved_subject, _resolved_subject_bytes = _load_subject_record(
        plugin_data, record["resolved_subject_ref"]
    )
    refs = record["evidence_refs"]
    findings = result.get("evidence", {}).get("findings", [])
    if (
        record["result_ref"] != actual_result_ref
        or record["recorded_by"] != "root"
        or record["finding_subject_ref"] != result.get("output_subject_ref")
        or record["finding_subject_content_sha256"]
        != finding_subject["content_sha256"]
        or record["resolved_subject_content_sha256"]
        != resolved_subject["content_sha256"]
        or record["resolved_subject_ref"] == record["finding_subject_ref"]
        or resolved_subject["content_sha256"] == finding_subject["content_sha256"]
        or resolved_subject["repository_sha256"]
        != finding_subject["repository_sha256"]
        or resolved_subject["paths"] != finding_subject["paths"]
        or not isinstance(refs, list)
        or not refs
        or len(refs) != len(set(refs))
        or record["resolved_subject_ref"] not in refs
        or sum(
            isinstance(finding, dict)
            and finding.get("finding_id") == record["finding_id"]
            and finding.get("resolved") is False
            for finding in findings
        )
        != 1
    ):
        raise DispatchReceiptError("resolution record does not bind its finding and subject")
    for evidence_ref in refs:
        _load_resolution_evidence(plugin_data, evidence_ref)
    if not _subject_descends_from(
        plugin_data, record["resolved_subject_ref"], record["finding_subject_ref"]
    ):
        raise DispatchReceiptError("resolution subject does not descend from the finding")
    resolution_recorded_at = _parse_time(
        record["recorded_at"], "resolution.recorded_at"
    )
    result_recorded_at = _parse_time(result.get("recorded_at"), "result.recorded_at")
    resolved_subject_created_at = _parse_time(
        resolved_subject["created_at"], "resolved subject.created_at"
    )
    if not (
        result_recorded_at < resolved_subject_created_at <= resolution_recorded_at
    ):
        raise DispatchReceiptError(
            "resolution subject must be created after the finding and before resolution"
        )
    return record, content


def create_root_verification_record(
    plugin_data: Path,
    *,
    result_ref: str,
    verifier_session_id: str,
    verifier_turn_id: str,
    resolution_refs: list[str],
    recorded_at: str | None = None,
) -> str:
    result, _content = load_protected_record(plugin_data, result_ref, "role-result")
    verifier_session_id = _runtime_id(verifier_session_id, "verifier_session_id")
    verifier_turn_id = _runtime_id(verifier_turn_id, "verifier_turn_id")
    normalized_refs = tuple(resolution_refs)
    if len(normalized_refs) != len(set(normalized_refs)):
        raise DispatchReceiptError("resolution references contain duplicates")
    resolutions = [
        _load_resolution_record(plugin_data, reference, result_ref=result_ref)[0]
        for reference in normalized_refs
    ]
    current_subject, _current_subject_bytes = _load_subject_record(
        plugin_data, result.get("output_subject_ref")
    )
    for resolution in resolutions:
        resolution_subject, _resolution_subject_bytes = _load_subject_record(
            plugin_data, resolution["resolved_subject_ref"]
        )
        if (
            resolution_subject["repository_sha256"]
            != current_subject["repository_sha256"]
            or resolution_subject["paths"] != current_subject["paths"]
        ):
            raise DispatchReceiptError("resolution belongs to another subject scope")
    if len({record["finding_id"] for record in resolutions}) != len(resolutions):
        raise DispatchReceiptError("resolution references duplicate a finding")
    recorded_at = recorded_at or _timestamp_now()
    result_recorded = _parse_time(result.get("recorded_at"), "result.recorded_at")
    verified_at = _parse_time(recorded_at, "root verification recorded_at")
    if verified_at < result_recorded:
        raise DispatchReceiptError("root verification predates the result")
    if any(
        verified_at < _parse_time(record["recorded_at"], "resolution.recorded_at")
        for record in resolutions
    ):
        raise DispatchReceiptError("root verification predates a resolution")
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "root-verification",
            "result_ref": result_ref,
            "verified": True,
            "verifier_session_id": verifier_session_id,
            "verifier_turn_id": verifier_turn_id,
            "resolution_refs": list(normalized_refs),
            "recorded_at": recorded_at,
        },
    )
    _load_root_verification_record(plugin_data, reference, result_ref=result_ref)
    return reference


def _load_launch_record(
    plugin_data: Path,
    reference: str,
    *,
    intent_ref: str,
    parent_session_id: str,
    turn_id: str,
    child_id: str,
    agent_type: str,
    hook_trust_ref: str,
    codex_home_sha256: str,
) -> tuple[dict[str, Any], bytes]:
    record, content = load_protected_record(plugin_data, reference, "native-launch")
    if set(record) != {
        "schema_version",
        "record_type",
        "intent_ref",
        "parent_session_id",
        "turn_id",
        "child_id",
        "agent_type",
        "hook_trust_ref",
        "codex_home_sha256",
        "ack_kind",
        "recorded_by",
        "launched_at",
    }:
        raise DispatchReceiptError("native launch record fields are not closed")
    expected = {
        "intent_ref": intent_ref,
        "parent_session_id": parent_session_id,
        "turn_id": turn_id,
        "child_id": child_id,
        "agent_type": agent_type,
        "hook_trust_ref": hook_trust_ref,
        "codex_home_sha256": codex_home_sha256,
    }
    if any(record[field] != value for field, value in expected.items()):
        raise DispatchReceiptError("native launch record does not bind the dispatch")
    if (
        record["ack_kind"] != "native-collaboration-launch"
        or record["recorded_by"] != "root"
    ):
        raise DispatchReceiptError("native launch acknowledgement identity is invalid")
    _parse_time(record["launched_at"], "launch.launched_at")
    return record, content


def _load_result_record(
    plugin_data: Path,
    reference: str,
    workflow: dispatch.Workflow,
    step_id: str,
    *,
    attempt: int,
    task_id: str,
    intent_ref: str,
    vehicle: str,
    child_id: str | None,
) -> tuple[dict[str, Any], bytes]:
    record, content = load_protected_record(plugin_data, reference, "role-result")
    if set(record) != {
        "schema_version",
        "record_type",
        "intent_ref",
        "subject_ref",
        "subject_content_sha256",
        "output_subject_ref",
        "output_subject_content_sha256",
        "mutation_audit_ref",
        "workflow_sha256",
        "step_id",
        "attempt",
        "task_id",
        "vehicle",
        "child_id",
        "role_id",
        "role_lens_sha256",
        "output_schema",
        "provided_evidence",
        "evidence_sha256",
        "evidence",
        "execution",
        "recorded_at",
    }:
        raise DispatchReceiptError("role result record fields are not closed")
    step = workflow.step(step_id)
    intent, _intent_bytes = _load_intent_record(
        plugin_data, intent_ref, workflow, step_id, attempt, task_id
    )
    subject, _subject_bytes = _load_subject_record(plugin_data, intent["subject_ref"])
    output_subject, _output_subject_bytes = _load_subject_record(
        plugin_data, record.get("output_subject_ref")
    )
    mutation_audit: dict[str, Any] | None = None
    after_snapshot: dict[str, Any] | None = None
    if record.get("mutation_audit_ref") is not None:
        mutation_audit, _mutation_audit_bytes = _load_mutation_audit_record(
            plugin_data, record["mutation_audit_ref"]
        )
        after_snapshot, _after_snapshot_bytes = _load_workspace_snapshot_record(
            plugin_data, mutation_audit["after_ref"]
        )
    expected = {
        "intent_ref": intent_ref,
        "subject_ref": intent["subject_ref"],
        "subject_content_sha256": subject["content_sha256"],
        "output_subject_ref": record["output_subject_ref"],
        "output_subject_content_sha256": output_subject["content_sha256"],
        "mutation_audit_ref": record["mutation_audit_ref"],
        "workflow_sha256": workflow.sha256,
        "step_id": step_id,
        "attempt": attempt,
        "task_id": task_id,
        "vehicle": vehicle,
        "child_id": child_id,
        "role_id": step.role_id,
        "role_lens_sha256": step.role_lens_sha256,
        "output_schema": step.output_schema,
    }
    if any(record[field] != value for field, value in expected.items()):
        raise DispatchReceiptError("role result record does not bind the dispatch")
    if (
        output_subject["repository_sha256"] != subject["repository_sha256"]
        or output_subject["paths"] != subject["paths"]
        or (step.mutation == "none" and record["output_subject_ref"] != record["subject_ref"])
        or (
            record["output_subject_ref"] != record["subject_ref"]
            and record["subject_ref"] not in output_subject["parent_refs"]
        )
    ):
        raise DispatchReceiptError("role result output subject is invalid")
    if vehicle in {
        "verified-workflow-subagent",
        "verified-workflow-inline",
        "deterministic-tool",
    }:
        if (
            mutation_audit is None
            or mutation_audit["before_ref"] != intent["workspace_snapshot_ref"]
            or mutation_audit["repository_sha256"] != subject["repository_sha256"]
            or (step.mutation == "none" and mutation_audit["mutation_observed"])
        ):
            raise DispatchReceiptError("role result mutation audit is invalid")
    elif mutation_audit is not None:
        raise DispatchReceiptError("root result carries an execution mutation audit")
    provided = record["provided_evidence"]
    if not isinstance(provided, dict) or any(
        not isinstance(evidence_id, str)
        or _safe(evidence_id, "provided evidence") != evidence_id
        or not isinstance(reference, str)
        for evidence_id, reference in provided.items()
    ):
        raise DispatchReceiptError("role result provided evidence is invalid")
    if set(provided) != set(step.required_evidence):
        raise DispatchReceiptError("role result is missing or duplicates required evidence")
    for reference in provided.values():
        _load_root_evidence_reference(plugin_data, reference)
    evidence = _validate_evidence(
        plugin_data,
        step,
        record["evidence"],
        provided,
    )
    if (
        step.output_schema == "review-evidence.v1"
        and evidence["input_digest"] != subject["content_sha256"]
    ):
        raise DispatchReceiptError(
            "role result review evidence does not bind the protected subject"
        )
    if record["evidence_sha256"] != _sha256(_canonical_bytes(evidence)):
        raise DispatchReceiptError("role result evidence digest is invalid")
    execution = record["execution"]
    if not isinstance(execution, dict):
        raise DispatchReceiptError("role result execution binding is invalid")
    _validated_execution(
        plugin_data,
        workflow,
        step,
        vehicle,
        execution,
        evidence,
        intent_ref,
        intent,
    )
    result_recorded_at = _parse_time(record["recorded_at"], "result.recorded_at")
    if result_recorded_at < _parse_time(intent["created_at"], "intent.created_at"):
        raise DispatchReceiptError("role result predates its execution intent")
    _validate_contextual_evidence(
        plugin_data,
        workflow,
        step,
        evidence,
        intent_ref,
        intent,
        subject,
        record["mutation_audit_ref"],
        mutation_audit,
        result_recorded_at,
        provided,
    )
    if mutation_audit is not None and _parse_time(
        mutation_audit["recorded_at"], "mutation audit.recorded_at"
    ) > result_recorded_at:
        raise DispatchReceiptError("role result predates its mutation audit")
    if vehicle == "deterministic-tool":
        command_output, _command_output_bytes = _load_command_output_record(
            plugin_data,
            execution["output_ref"],
            workflow=workflow,
        )
        if after_snapshot is None or _parse_time(
            command_output["recorded_at"], "command output.recorded_at"
        ) > _parse_time(after_snapshot["created_at"], "workspace snapshot.created_at"):
            raise DispatchReceiptError(
                "role result deterministic audit predates command output"
            )
    return record, content


def _load_root_verification_record(
    plugin_data: Path,
    reference: str,
    *,
    result_ref: str,
) -> tuple[dict[str, Any], bytes]:
    record, content = load_protected_record(
        plugin_data, reference, "root-verification"
    )
    if set(record) != {
        "schema_version",
        "record_type",
        "result_ref",
        "verified",
        "verifier_session_id",
        "verifier_turn_id",
        "resolution_refs",
        "recorded_at",
    }:
        raise DispatchReceiptError("root verification record fields are not closed")
    if record["result_ref"] != result_ref or record["verified"] is not True:
        raise DispatchReceiptError("root verification does not bind the result")
    _runtime_id(record["verifier_session_id"], "verifier_session_id")
    _runtime_id(record["verifier_turn_id"], "verifier_turn_id")
    refs = record["resolution_refs"]
    if not isinstance(refs, list) or any(not isinstance(value, str) for value in refs):
        raise DispatchReceiptError("root verification resolution refs are invalid")
    if len(refs) != len(set(refs)):
        raise DispatchReceiptError("root verification resolution refs contain duplicates")
    resolutions = [
        _load_resolution_record(plugin_data, value, result_ref=result_ref)[0]
        for value in refs
    ]
    current_result, _current_result_bytes = load_protected_record(
        plugin_data, result_ref, "role-result"
    )
    current_subject, _current_subject_bytes = _load_subject_record(
        plugin_data, current_result.get("output_subject_ref")
    )
    for resolution in resolutions:
        resolution_subject, _resolution_subject_bytes = _load_subject_record(
            plugin_data, resolution["resolved_subject_ref"]
        )
        if (
            resolution_subject["repository_sha256"]
            != current_subject["repository_sha256"]
            or resolution_subject["paths"] != current_subject["paths"]
        ):
            raise DispatchReceiptError("root verification resolution changes subject scope")
    if len({value["finding_id"] for value in resolutions}) != len(resolutions):
        raise DispatchReceiptError("root verification duplicates a resolved finding")
    verified_at = _parse_time(record["recorded_at"], "root verification recorded_at")
    if verified_at < _parse_time(
        current_result.get("recorded_at"), "result.recorded_at"
    ):
        raise DispatchReceiptError("root verification predates its result")
    if any(
        verified_at < _parse_time(value["recorded_at"], "resolution.recorded_at")
        for value in resolutions
    ):
        raise DispatchReceiptError("root verification predates a resolution")
    return record, content


def persist_normalized(
    plugin_data: Path,
    receipt: Mapping[str, Any],
    *,
    raw_pair_sha256: str | None = None,
) -> str:
    """Persist a normalized receipt and optional one-intent raw-pair consumption marker."""

    workflow_sha = str(receipt["workflow_sha256"])
    workflow_run_sha = str(receipt["workflow_run_sha256"])
    step_id = str(receipt["step_id"])
    raw_attempt = receipt["attempt"]
    if (
        not HEX64.fullmatch(workflow_sha)
        or not HEX64.fullmatch(workflow_run_sha)
        or not dispatch.STEP_ID.fullmatch(step_id)
        or isinstance(raw_attempt, bool)
        or not isinstance(raw_attempt, int)
        or not 1 <= raw_attempt <= dispatch.MAX_CYCLES
    ):
        raise DispatchReceiptError("normalized receipt identity is invalid")
    attempt = raw_attempt
    name = f"attempt-{attempt}.json"
    content = _canonical_bytes(receipt)
    if len(content) > MAX_RECEIPT_BYTES:
        raise DispatchReceiptError("normalized receipt exceeds the byte ceiling")
    if raw_pair_sha256 is not None:
        if not HEX64.fullmatch(raw_pair_sha256):
            raise DispatchReceiptError("raw pair digest is invalid")
        marker = {
            "schema_version": 1,
            "state": "prepared",
            "raw_pair_sha256": raw_pair_sha256,
            "normalized_sha256": _sha256(content),
            "workflow_sha256": workflow_sha,
            "workflow_run_sha256": workflow_run_sha,
            "step_id": step_id,
            "attempt": attempt,
        }
        _persist_under(
            plugin_data,
            ("receipts", "v1", "consumed"),
            f"{raw_pair_sha256}.prepared.json",
            marker,
        )
    _persist_under(
        plugin_data,
        (
            "receipts",
            "v1",
            "normalized",
            workflow_sha,
            workflow_run_sha,
            step_id,
        ),
        name,
        receipt,
    )
    if raw_pair_sha256 is not None:
        committed = {**marker, "state": "committed"}
        _persist_under(
            plugin_data,
            ("receipts", "v1", "consumed"),
            f"{raw_pair_sha256}.committed.json",
            committed,
        )
    return (
        f"normalized:{workflow_sha}:{workflow_run_sha}:{step_id}:"
        f"{attempt}:{_sha256(content)}"
    )


def load_normalized_by_identity(
    plugin_data: Path,
    workflow_sha256: str,
    workflow_run_sha256: str,
    step_id: str,
    attempt: int,
) -> tuple[dict[str, Any], str] | None:
    """Load a normalized receipt by its closed identity for crash-safe retries."""

    if (
        not HEX64.fullmatch(workflow_sha256)
        or not HEX64.fullmatch(workflow_run_sha256)
        or not dispatch.STEP_ID.fullmatch(step_id)
        or isinstance(attempt, bool)
        or not isinstance(attempt, int)
        or not 1 <= attempt <= dispatch.MAX_CYCLES
    ):
        raise DispatchReceiptError("normalized receipt lookup identity is invalid")
    try:
        descriptors = _open_existing_chain(
            plugin_data,
            (
                "receipts",
                "v1",
                "normalized",
                workflow_sha256,
                workflow_run_sha256,
                step_id,
            ),
        )
    except FileNotFoundError:
        return None
    try:
        try:
            receipt, content = _load_json_at(
                descriptors[-1], f"attempt-{attempt}.json", "normalized receipt"
            )
        except FileNotFoundError:
            return None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if (
        content != _canonical_bytes(receipt)
        or receipt.get("schema_version") != 1
        or receipt.get("workflow_sha256") != workflow_sha256
        or receipt.get("workflow_run_sha256") != workflow_run_sha256
        or receipt.get("step_id") != step_id
        or receipt.get("attempt") != attempt
    ):
        raise DispatchReceiptError("normalized receipt readback is invalid")
    digest = _sha256(content)
    return receipt, (
        f"normalized:{workflow_sha256}:{workflow_run_sha256}:{step_id}:"
        f"{attempt}:{digest}"
    )


def load_normalized_receipt(
    plugin_data: Path,
    reference: str,
) -> tuple[dict[str, Any], bytes]:
    parts = reference.split(":")
    if len(parts) != 6 or parts[0] != "normalized" or not parts[4].isdigit():
        raise DispatchReceiptError("normalized receipt reference is invalid")
    loaded = load_normalized_by_identity(
        plugin_data, parts[1], parts[2], parts[3], int(parts[4])
    )
    if loaded is None:
        raise DispatchReceiptError("normalized receipt is missing")
    receipt, actual_ref = loaded
    if actual_ref != reference or not HEX64.fullmatch(parts[5]):
        raise DispatchReceiptError("normalized receipt digest does not match")
    return receipt, _canonical_bytes(receipt)


def _validate_consumption_commit(
    plugin_data: Path,
    raw_pair_sha256: str,
    normalized_sha256: str,
    workflow_sha256: str,
    workflow_run_sha256: str,
    step_id: str,
    attempt: int,
) -> None:
    descriptors = _open_existing_chain(plugin_data, ("receipts", "v1", "consumed"))
    try:
        marker, content = _load_json_at(
            descriptors[-1],
            f"{raw_pair_sha256}.committed.json",
            "consumption commit",
        )
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    expected = {
        "schema_version": 1,
        "state": "committed",
        "raw_pair_sha256": raw_pair_sha256,
        "normalized_sha256": normalized_sha256,
        "workflow_sha256": workflow_sha256,
        "workflow_run_sha256": workflow_run_sha256,
        "step_id": step_id,
        "attempt": attempt,
    }
    if marker != expected or content != _canonical_bytes(expected):
        raise DispatchReceiptError("raw-pair consumption commit is invalid")


def validate_normalized_receipt(
    plugin_data: Path,
    reference: str,
    workflow: dispatch.Workflow,
    *,
    require_consumption_commit: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate a normalized receipt and every protected record it references."""

    receipt, content = load_normalized_receipt(plugin_data, reference)
    common_fields = {
        "schema_version",
        "vehicle",
        "workflow_sha256",
        "step_id",
        "attempt",
        "task_id",
        "intent_ref",
        "intent_sha256",
        "subject_ref",
        "subject_sha256",
        "workflow_run_sha256",
        "workspace_snapshot_ref",
        "workspace_snapshot_sha256",
        "mutation_audit_ref",
        "output_subject_ref",
        "output_subject_content_sha256",
        "role",
        "execution",
        "result",
        "timestamps",
    }
    vehicle = receipt.get("vehicle")
    expected_fields = set(common_fields)
    if vehicle == "verified-workflow-subagent":
        expected_fields |= {"hook_trust", "child", "raw_events"}
    elif vehicle == "verified-workflow-inline":
        expected_fields.add("limitation")
    elif vehicle not in {"deterministic-tool", "root"}:
        raise DispatchReceiptError("normalized receipt vehicle is invalid")
    if set(receipt) != expected_fields:
        raise DispatchReceiptError("normalized receipt fields are not closed")
    if receipt["workflow_sha256"] != workflow.sha256:
        raise DispatchReceiptError("normalized receipt does not bind the workflow")
    step_id = receipt["step_id"]
    if not isinstance(step_id, str):
        raise DispatchReceiptError("normalized receipt step id is invalid")
    step = workflow.step(step_id)
    attempt = receipt["attempt"]
    if (
        isinstance(attempt, bool)
        or not isinstance(attempt, int)
        or not 1 <= attempt <= dispatch.MAX_CYCLES
    ):
        raise DispatchReceiptError("normalized receipt attempt is invalid")
    task_id = _safe(receipt["task_id"], "normalized receipt task_id")
    intent_ref = receipt["intent_ref"]
    intent, intent_bytes = _load_intent_record(
        plugin_data, intent_ref, workflow, step_id, attempt, task_id
    )
    if receipt["intent_sha256"] != _sha256(intent_bytes):
        raise DispatchReceiptError("normalized receipt intent digest is invalid")
    subject, subject_bytes = _load_subject_record(plugin_data, receipt["subject_ref"])
    output_subject, _output_subject_bytes = _load_subject_record(
        plugin_data, receipt["output_subject_ref"]
    )
    workspace_snapshot, workspace_snapshot_bytes = _load_workspace_snapshot_record(
        plugin_data, receipt["workspace_snapshot_ref"]
    )
    if (
        receipt["subject_ref"] != intent["subject_ref"]
        or receipt["subject_sha256"] != _sha256(subject_bytes)
        or receipt["subject_sha256"] != intent["subject_sha256"]
        or receipt["workflow_run_sha256"] != intent["workflow_run_sha256"]
        or receipt["workspace_snapshot_ref"] != intent["workspace_snapshot_ref"]
        or receipt["workspace_snapshot_sha256"] != _sha256(workspace_snapshot_bytes)
        or receipt["workspace_snapshot_sha256"]
        != intent["workspace_snapshot_sha256"]
        or workspace_snapshot["repository_sha256"] != subject["repository_sha256"]
        or receipt["output_subject_content_sha256"]
        != output_subject["content_sha256"]
        or output_subject["repository_sha256"] != subject["repository_sha256"]
        or output_subject["paths"] != subject["paths"]
    ):
        raise DispatchReceiptError("normalized receipt subject binding is invalid")
    role = receipt["role"]
    expected_role = {
        "role_id": step.role_id,
        "role_kind": step.role_kind,
        "role_lens_sha256": step.role_lens_sha256,
        "independence": step.independence if step.independence is not None else "n/a",
    }
    if role != expected_role:
        raise DispatchReceiptError("normalized receipt role binding is invalid")
    result_summary = receipt["result"]
    if not isinstance(result_summary, dict) or set(result_summary) != {
        "result_ref",
        "result_sha256",
        "evidence_sha256",
        "root_verification_ref",
        "root_verification_sha256",
        "root_verified",
    }:
        raise DispatchReceiptError("normalized receipt result summary is not closed")
    child_id: str | None = None
    if vehicle == "verified-workflow-subagent":
        child = receipt["child"]
        if not isinstance(child, dict) or set(child) != {
            "parent_session_id",
            "turn_id",
            "child_id",
            "launch_ref",
            "launch_sha256",
            "start_sha256",
            "stop_sha256",
            "raw_pair_sha256",
        }:
            raise DispatchReceiptError("normalized receipt child summary is not closed")
        child_id = _runtime_id(child["child_id"], "normalized child id")
        parent_session_id = _runtime_id(
            child["parent_session_id"], "normalized parent session id"
        )
        turn_id = _runtime_id(child["turn_id"], "normalized turn id")
        hook_trust = receipt["hook_trust"]
        if not isinstance(hook_trust, dict) or set(hook_trust) != {
            "record_ref",
            "record_sha256",
            "definition_sha256",
            "handler_sha256",
            "codex_home_sha256",
            "trust_readback_sha256",
        }:
            raise DispatchReceiptError("normalized hook trust summary is not closed")
        trust_record, trust_bytes = _load_hook_trust_record(
            plugin_data, hook_trust["record_ref"]
        )
        if (
            hook_trust["record_sha256"] != _sha256(trust_bytes)
            or hook_trust["definition_sha256"] != trust_record["definition_sha256"]
            or hook_trust["handler_sha256"] != trust_record["handler_sha256"]
            or hook_trust["codex_home_sha256"]
            != trust_record["codex_home_sha256"]
            or hook_trust["trust_readback_sha256"]
            != trust_record["trust_readback_sha256"]
        ):
            raise DispatchReceiptError("normalized hook trust summary is invalid")
        launch, launch_bytes = _load_launch_record(
            plugin_data,
            child["launch_ref"],
            intent_ref=intent_ref,
            parent_session_id=parent_session_id,
            turn_id=turn_id,
            child_id=child_id,
            agent_type=str(step.execution_class),
            hook_trust_ref=hook_trust["record_ref"],
            codex_home_sha256=hook_trust["codex_home_sha256"],
        )
        if child["launch_sha256"] != _sha256(launch_bytes):
            raise DispatchReceiptError("normalized launch digest is invalid")
        for digest_field in ("start_sha256", "stop_sha256", "raw_pair_sha256"):
            if not isinstance(child[digest_field], str) or not HEX64.fullmatch(
                child[digest_field]
            ):
                raise DispatchReceiptError("normalized raw receipt digest is invalid")
        raw_events = receipt["raw_events"]
        if not isinstance(raw_events, dict) or set(raw_events) != {"start", "stop"}:
            raise DispatchReceiptError("normalized raw event evidence is not closed")
        retained_start = _validate_raw_event(
            raw_events["start"],
            "start",
            parent_session_id=parent_session_id,
            child_id=child_id,
            turn_id=turn_id,
        )
        retained_stop = _validate_raw_event(
            raw_events["stop"],
            "stop",
            parent_session_id=parent_session_id,
            child_id=child_id,
            turn_id=turn_id,
        )
        retained_start_bytes = _canonical_bytes(retained_start)
        retained_stop_bytes = _canonical_bytes(retained_stop)
        retained_pair_sha256 = _sha256(
            _canonical_bytes(
                {
                    "start_sha256": _sha256(retained_start_bytes),
                    "stop_sha256": _sha256(retained_stop_bytes),
                }
            )
        )
        if (
            child["start_sha256"] != _sha256(retained_start_bytes)
            or child["stop_sha256"] != _sha256(retained_stop_bytes)
            or child["raw_pair_sha256"] != retained_pair_sha256
            or retained_start["agent_type"] != step.execution_class
            or retained_start["active_model"] != step.expected_model
            or retained_start["profile_sha256"] != step.profile_sha256
            or retained_start["codex_home_sha256"]
            != hook_trust["codex_home_sha256"]
            or retained_stop["agent_type"] != retained_start["agent_type"]
            or retained_stop["active_model"] != retained_start["active_model"]
            or retained_stop["profile_sha256"] != retained_start["profile_sha256"]
            or retained_stop["codex_home_sha256"]
            != retained_start["codex_home_sha256"]
            or retained_stop["permission_mode"] != retained_start["permission_mode"]
            or retained_start["permission_mode"]
            not in hook_receipt.RECEIPT_PERMISSION_MODES
            or retained_start["hook_definition_sha256"]
            != hook_trust["definition_sha256"]
            or retained_start["hook_handler_sha256"]
            != hook_trust["handler_sha256"]
            or retained_stop["hook_definition_sha256"]
            != retained_start["hook_definition_sha256"]
            or retained_stop["hook_handler_sha256"]
            != retained_start["hook_handler_sha256"]
        ):
            raise DispatchReceiptError("retained raw event evidence is invalid")
        if require_consumption_commit:
            _validate_consumption_commit(
                plugin_data,
                child["raw_pair_sha256"],
                _sha256(content),
                workflow.sha256,
                receipt["workflow_run_sha256"],
                step_id,
                attempt,
            )
    result, result_bytes = _load_result_record(
        plugin_data,
        result_summary["result_ref"],
        workflow,
        step_id,
        attempt=attempt,
        task_id=task_id,
        intent_ref=intent_ref,
        vehicle=vehicle,
        child_id=child_id,
    )
    root_verification, root_bytes = _load_root_verification_record(
        plugin_data,
        result_summary["root_verification_ref"],
        result_ref=result_summary["result_ref"],
    )
    if (
        result_summary["result_sha256"] != _sha256(result_bytes)
        or result["subject_ref"] != receipt["subject_ref"]
        or result["subject_content_sha256"] != subject["content_sha256"]
        or result["output_subject_ref"] != receipt["output_subject_ref"]
        or result["output_subject_content_sha256"]
        != receipt["output_subject_content_sha256"]
        or result["mutation_audit_ref"] != receipt["mutation_audit_ref"]
        or result_summary["evidence_sha256"] != result["evidence_sha256"]
        or result_summary["root_verification_sha256"] != _sha256(root_bytes)
        or result_summary["root_verified"] is not True
        or root_verification["verified"] is not True
    ):
        raise DispatchReceiptError("normalized result/root verification summary is invalid")
    timestamps = receipt["timestamps"]
    if not isinstance(timestamps, dict):
        raise DispatchReceiptError("normalized timestamp summary is invalid")
    expected_timestamps = {
        "intent_created_at": intent["created_at"],
        "result_recorded_at": result["recorded_at"],
        "root_verified_at": root_verification["recorded_at"],
    }
    if vehicle == "verified-workflow-subagent":
        expected_timestamps.update(
            {
                "hook_trusted_at": trust_record["observed_at"],
                "launched_at": launch["launched_at"],
                "started_at": retained_start["observed_at"],
                "stopped_at": retained_stop["observed_at"],
            }
        )
        expected_execution = {
            "execution_class": step.execution_class,
            "active_model": step.expected_model,
            "effort_evidence": "installed-profile-digest",
            "expected_effort": step.expected_effort,
            "profile_sha256": step.profile_sha256,
            "expected_profile_sandbox": step.expected_profile_sandbox,
            "observed_permission_mode": retained_start["permission_mode"],
            "sandbox_enforcement_claim": "configured-not-observed",
            "permission_boundary": "requested-boundary-advisory",
        }
        if expected_execution["observed_permission_mode"] not in hook_receipt.PERMISSION_MODES:
            raise DispatchReceiptError("normalized permission observation is invalid")
    elif vehicle == "verified-workflow-inline":
        expected_execution = {
            "execution_class": step.execution_class,
            "expected_model": step.expected_model,
            "expected_effort": step.expected_effort,
            "profile_sha256": step.profile_sha256,
            "runtime_selection_attested": False,
        }
        if receipt["limitation"] != (
            "logical role executed inline; separate child, model, effort, and sandbox "
            "were not observed"
        ):
            raise DispatchReceiptError("normalized inline limitation is invalid")
    elif vehicle == "deterministic-tool":
        command_output, _command_output_bytes = _load_command_output_record(
            plugin_data, result["execution"]["output_ref"]
        )
        expected_execution = {
            "command": list(step.command),
            "command_implementation_sha256": step.command_implementation_sha256,
            "evidence_schema_sha256": step.evidence_schema_sha256,
            "cwd": "repo-root",
            "timeout_seconds": step.command_timeout_seconds,
            "output_limit_bytes": step.command_output_limit_bytes,
            "output_ref": result["execution"]["output_ref"],
            "output_sha256": command_output["combined_sha256"],
            "exit_code": result["execution"]["exit_code"],
            "model_fields_present": False,
        }
    else:
        expected_execution = {"kind": "root", "model_fields_present": False}
    if receipt["execution"] != expected_execution:
        raise DispatchReceiptError("normalized execution summary is invalid")
    if timestamps != expected_timestamps:
        raise DispatchReceiptError("normalized timestamp summary does not bind the records")
    created_at = _parse_time(intent["created_at"], "intent.created_at")
    result_recorded_at = _parse_time(result["recorded_at"], "result.recorded_at")
    root_verified_at = _parse_time(
        root_verification["recorded_at"], "root verification.recorded_at"
    )
    if vehicle == "verified-workflow-subagent":
        launched_at = _parse_time(launch["launched_at"], "launch.launched_at")
        trusted_at = _parse_time(trust_record["observed_at"], "hook trust.observed_at")
        started_at = _parse_time(timestamps["started_at"], "timestamps.started_at")
        stopped_at = _parse_time(timestamps["stopped_at"], "timestamps.stopped_at")
        timestamps_valid = (
            created_at <= launched_at <= result_recorded_at
            and trusted_at
            <= started_at
            <= stopped_at
            <= result_recorded_at
            <= root_verified_at
        )
    else:
        timestamps_valid = created_at <= result_recorded_at <= root_verified_at
    if not timestamps_valid:
        raise DispatchReceiptError("normalized record timestamps are reversed")
    return receipt, result


def recover_normalization_commit(
    plugin_data: Path,
    receipt: Mapping[str, Any],
) -> None:
    """Complete a prepared transaction after normalized readback proves exact bytes."""

    if receipt.get("vehicle") != "verified-workflow-subagent":
        return
    raw_pair_sha256 = receipt["child"]["raw_pair_sha256"]
    content = _canonical_bytes(receipt)
    expected_prepared = {
        "schema_version": 1,
        "state": "prepared",
        "raw_pair_sha256": raw_pair_sha256,
        "normalized_sha256": _sha256(content),
        "workflow_sha256": receipt["workflow_sha256"],
        "workflow_run_sha256": receipt["workflow_run_sha256"],
        "step_id": receipt["step_id"],
        "attempt": receipt["attempt"],
    }
    descriptors = _open_existing_chain(plugin_data, ("receipts", "v1", "consumed"))
    try:
        prepared, prepared_bytes = _load_json_at(
            descriptors[-1],
            f"{raw_pair_sha256}.prepared.json",
            "consumption preparation",
        )
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if prepared != expected_prepared or prepared_bytes != _canonical_bytes(expected_prepared):
        raise DispatchReceiptError("normalization preparation does not bind the receipt")
    committed = {**expected_prepared, "state": "committed"}
    _persist_under(
        plugin_data,
        ("receipts", "v1", "consumed"),
        f"{raw_pair_sha256}.committed.json",
        committed,
    )


def _load_consumption_marker(
    plugin_data: Path, raw_pair_sha256: str
) -> dict[str, Any] | None:
    try:
        descriptors = _open_existing_chain(plugin_data, ("receipts", "v1", "consumed"))
    except FileNotFoundError:
        return None
    try:
        try:
            marker, content = _load_json_at(
                descriptors[-1],
                f"{raw_pair_sha256}.committed.json",
                "consumption commit",
            )
        except FileNotFoundError:
            return None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if (
        content != _canonical_bytes(marker)
        or set(marker)
        != {
            "schema_version",
            "state",
            "raw_pair_sha256",
            "normalized_sha256",
            "workflow_sha256",
            "workflow_run_sha256",
            "step_id",
            "attempt",
        }
        or marker["schema_version"] != 1
        or marker["state"] != "committed"
        or marker["raw_pair_sha256"] != raw_pair_sha256
        or not isinstance(marker["normalized_sha256"], str)
        or not HEX64.fullmatch(marker["normalized_sha256"])
        or not isinstance(marker["workflow_sha256"], str)
        or not HEX64.fullmatch(marker["workflow_sha256"])
        or not isinstance(marker["workflow_run_sha256"], str)
        or not HEX64.fullmatch(marker["workflow_run_sha256"])
        or not isinstance(marker["step_id"], str)
        or not dispatch.STEP_ID.fullmatch(marker["step_id"])
        or isinstance(marker["attempt"], bool)
        or not isinstance(marker["attempt"], int)
        or not 1 <= marker["attempt"] <= dispatch.MAX_CYCLES
    ):
        raise DispatchReceiptError("consumption commit is malformed")
    return marker
