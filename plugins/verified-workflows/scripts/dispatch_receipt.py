#!/usr/bin/env python3
"""Compatibility CLI for Verified Workflows receipt modules."""

# ruff: noqa: F401 -- imported names are the compatibility API of this facade.

from __future__ import annotations

from protected_store import (
    Any,
    Callable,
    DispatchReceiptError,
    GIT_OID,
    HEX64,
    HOOKS_DIR,
    LARGE_RECORD_KINDS,
    MAX_AUDIT_BYTES,
    MAX_AUDIT_FILES,
    MAX_EVENT_AGE_SECONDS,
    MAX_PROTECTED_RECORD_BYTES,
    MAX_RECEIPT_BYTES,
    MAX_SUBJECT_ANCESTRY,
    MAX_SUBJECT_BYTES,
    MAX_SUBJECT_FILES,
    MAX_SUBJECT_PATHS,
    MAX_SUBJECT_PATH_BYTES,
    Mapping,
    Path,
    PurePosixPath,
    RAW_FIELDS,
    RECORD_KINDS,
    SAFE_REF,
    SAFE_RUNTIME_ID,
    SCRIPTS_DIR,
    SECRET_KEY,
    SECRET_VALUE,
    _attempt,
    _canonical_bytes,
    _current_hook_bytes,
    _hash_segment,
    _load_json_at,
    _open_existing_chain,
    _parse_record_reference,
    _parse_time,
    _persist_under,
    _read_at_bounded,
    _record_reference,
    _runtime_id,
    _safe,
    _sha256,
    _timestamp_now,
    _utc_now,
    _validate_raw_bytes,
    _validate_raw_event,
    argparse,
    dispatch,
    dt,
    fcntl,
    hashlib,
    hook_receipt,
    json,
    load_protected_record,
    load_raw_pair,
    math,
    os,
    persist_protected_record,
    re,
    secrets,
    stat,
    subprocess,
    sys,
)

from workspace_evidence import (
    _assert_plugin_data_outside_workspace,
    _create_git_baseline_record,
    _git_control_file_identity,
    _git_control_snapshot,
    _git_head_identity,
    _git_index_identity,
    _git_scope,
    _load_git_baseline_record,
    _load_mutation_audit_record,
    _load_subject_record,
    _load_workflow_run_record,
    _load_workspace_snapshot_record,
    _read_workspace_file,
    _read_workspace_file_at,
    _scope_covers,
    _scope_delta,
    _subject_path,
    _subject_snapshot,
    _valid_git_control_identity,
    _validate_git_entries,
    _workspace_snapshot,
    create_mutation_audit_record,
    create_subject_record,
    create_workflow_run_record,
    create_workspace_snapshot_record,
)

from workflow_records import (
    _build_non_agent_receipt,
    _derive_evidence_bindings,
    _load_command_output_record,
    _load_consumption_marker,
    _load_hook_trust_record,
    _load_intent_record,
    _load_launch_record,
    _load_prerequisite_reference,
    _load_resolution_evidence,
    _load_resolution_record,
    _load_result_record,
    _load_root_evidence_reference,
    _load_root_verification_record,
    _review_dimension_ids,
    _subject_descends_from,
    _validate_consumption_commit,
    _validate_contextual_evidence,
    _validate_deterministic_tester_output,
    _validate_evidence,
    _validate_finding_list,
    _validate_intent_resolution_refs,
    _validate_json_structure,
    _validate_observations,
    _validate_test_cases,
    _validate_time_window,
    _validated_execution,
    build_deterministic_receipt,
    build_inline_receipt,
    build_root_receipt,
    create_command_output_record,
    create_hook_trust_record,
    create_intent_record,
    create_launch_record,
    create_resolution_record,
    create_result_record,
    create_root_verification_record,
    load_normalized_by_identity,
    load_normalized_receipt,
    persist_normalized,
    recover_normalization_commit,
    validate_normalized_receipt,
)

from named_child_attestation import (
    join_subagent_receipt,
)

from raw_hook_maintenance import (
    create_raw_abandonment_record,
    delete_raw_pair,
    prune_raw_receipts,
)
def _load_workflow(
    path: Path,
    agents_dir: Path | None = None,
    *,
    registry_path: Path = dispatch.renderer.DEFAULT_REGISTRY,
    roles_dir: Path = dispatch.renderer.DEFAULT_ROLES_DIR,
) -> dispatch.Workflow:
    try:
        content = dispatch._read_bounded(path, dispatch.MAX_PLAN_BYTES, "workflow plan")
        default_registry = (
            registry_path.resolve() == dispatch.renderer.DEFAULT_REGISTRY.resolve()
            and roles_dir.resolve() == dispatch.renderer.DEFAULT_ROLES_DIR.resolve()
        )
        registry = dispatch.renderer.load_role_registry(
            registry_path,
            roles_dir,
            expected_role_ids=(
                dispatch.renderer.EXPECTED_ROLE_IDS if default_registry else None
            ),
        )
        workflow = dispatch.parse_workflow_structure(
            content.decode("utf-8"),
            agents_dir=agents_dir,
            registry=registry,
        )
        return workflow
    except (
        UnicodeDecodeError,
        dispatch.WorkflowDispatchError,
        dispatch.renderer.RoleRegistryError,
    ) as exc:
        raise DispatchReceiptError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-data", type=Path)
    parser.add_argument("--agents-dir", type=Path)
    parser.add_argument("--registry", type=Path, default=dispatch.renderer.DEFAULT_REGISTRY)
    parser.add_argument("--roles-dir", type=Path, default=dispatch.renderer.DEFAULT_ROLES_DIR)
    parser.add_argument("--pretty", action="store_true")
    subparsers = parser.add_subparsers(dest="mode", required=True)
    workflow_run_parser = subparsers.add_parser("workflow-run")
    workflow_run_parser.add_argument("--plan", type=Path, required=True)
    workflow_run_parser.add_argument("--workspace-root", type=Path, required=True)
    subject_parser = subparsers.add_parser("subject")
    subject_parser.add_argument("--workspace-root", type=Path, required=True)
    subject_parser.add_argument("--path", action="append", required=True)
    subject_parser.add_argument("--workflow-run-ref", required=True)
    subject_parser.add_argument("--parent-ref", action="append", default=[])
    snapshot_parser = subparsers.add_parser("workspace-snapshot")
    snapshot_parser.add_argument("--workspace-root", type=Path, required=True)
    audit_parser = subparsers.add_parser("mutation-audit")
    audit_parser.add_argument("--before-ref", required=True)
    audit_parser.add_argument("--after-ref", required=True)
    command_output_parser = subparsers.add_parser("command-output")
    command_output_parser.add_argument("--plan", type=Path, required=True)
    command_output_parser.add_argument("--step-id", required=True)
    command_output_parser.add_argument("--attempt", type=int, required=True)
    command_output_parser.add_argument("--task-id", required=True)
    command_output_parser.add_argument("--intent-ref", required=True)
    command_output_parser.add_argument("--stdout-file", type=Path, required=True)
    command_output_parser.add_argument("--stderr-file", type=Path, required=True)
    command_output_parser.add_argument("--exit-code", type=int, required=True)
    command_output_parser.add_argument("--output-limit-bytes", type=int, required=True)
    command_output_parser.add_argument("--argv", action="append")
    abandon_parser = subparsers.add_parser("abandon")
    abandon_parser.add_argument("--parent-session-id", required=True)
    abandon_parser.add_argument("--child-id", required=True)
    abandon_parser.add_argument("--turn-id", required=True)
    abandon_parser.add_argument(
        "--reason", choices=("operator-confirmed", "host-terminal"), required=True
    )
    intent_parser = subparsers.add_parser("intent")
    intent_parser.add_argument("--plan", type=Path, required=True)
    intent_parser.add_argument("--step-id", required=True)
    intent_parser.add_argument("--attempt", type=int, required=True)
    intent_parser.add_argument("--task-id", required=True)
    intent_parser.add_argument("--subject-ref", required=True)
    intent_parser.add_argument("--workspace-snapshot-ref", required=True)
    intent_parser.add_argument(
        "--intent-kind", choices=("run", "follow-up", "revalidate"), default="run"
    )
    intent_parser.add_argument("--previous-receipt-ref")
    intent_parser.add_argument("--finding-ref", action="append", default=[])
    intent_parser.add_argument("--resolution-ref", action="append", default=[])
    intent_parser.add_argument("--created-at", required=True)
    intent_parser.add_argument("--nonce", required=True)
    trust_parser = subparsers.add_parser("hook-trust")
    trust_parser.add_argument("--codex-home", type=Path, required=True)
    trust_parser.add_argument("--installed-hooks-dir", type=Path, required=True)
    trust_parser.add_argument("--scope", choices=("isolated", "real"), required=True)
    launch_parser = subparsers.add_parser("launch")
    launch_parser.add_argument("--intent-ref", required=True)
    launch_parser.add_argument("--parent-session-id", required=True)
    launch_parser.add_argument("--turn-id", required=True)
    launch_parser.add_argument("--child-id", required=True)
    launch_parser.add_argument("--agent-type", required=True)
    launch_parser.add_argument("--hook-trust-ref", required=True)
    result_parser = subparsers.add_parser("result")
    result_parser.add_argument("--plan", type=Path, required=True)
    result_parser.add_argument("--step-id", required=True)
    result_parser.add_argument("--attempt", type=int, required=True)
    result_parser.add_argument("--task-id", required=True)
    result_parser.add_argument("--intent-ref", required=True)
    result_parser.add_argument("--output-subject-ref", required=True)
    result_parser.add_argument("--mutation-audit-ref")
    result_parser.add_argument("--workspace-root", type=Path)
    result_parser.add_argument(
        "--vehicle",
        choices=(
            "verified-workflow-subagent",
            "verified-workflow-inline",
            "deterministic-tool",
            "root",
        ),
        required=True,
    )
    result_parser.add_argument("--child-id")
    result_parser.add_argument("--provided-evidence", action="append", default=[])
    result_parser.add_argument("--evidence-file", type=Path, required=True)
    result_parser.add_argument("--execution-file", type=Path, required=True)
    resolution_parser = subparsers.add_parser("resolution")
    resolution_parser.add_argument("--result-ref", required=True)
    resolution_parser.add_argument("--finding-id", required=True)
    resolution_parser.add_argument("--resolved-subject-ref", required=True)
    resolution_parser.add_argument("--evidence-ref", action="append", required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--result-ref", required=True)
    verify_parser.add_argument("--verifier-session-id", required=True)
    verify_parser.add_argument("--verifier-turn-id", required=True)
    verify_parser.add_argument("--resolution-ref", action="append", default=[])
    prune_parser = subparsers.add_parser("prune")
    prune_parser.add_argument("--older-than-seconds", type=int, required=True)
    prune_parser.add_argument("--max-entries", type=int, default=1000)
    prune_parser.add_argument("--max-bytes", type=int, default=64 * 1024 * 1024)
    prune_parser.add_argument("--apply", action="store_true")
    prune_parser.add_argument("--expected-plan-sha256")
    for mode in ("join", "inline", "deterministic", "root"):
        mode_parser = subparsers.add_parser(mode)
        mode_parser.add_argument("--plan", type=Path, required=True)
        mode_parser.add_argument("--step-id", required=True)
        mode_parser.add_argument("--attempt", type=int, required=True)
        mode_parser.add_argument("--task-id", required=True)
        mode_parser.add_argument("--intent-ref", required=True)
        mode_parser.add_argument("--result-ref", required=True)
        mode_parser.add_argument("--root-verification-ref", required=True)
        if mode == "join":
            mode_parser.add_argument("--hook-trust-ref", required=True)
            mode_parser.add_argument("--parent-session-id", required=True)
            mode_parser.add_argument("--child-id", required=True)
            mode_parser.add_argument("--turn-id", required=True)
            mode_parser.add_argument("--launch-ref", required=True)
    for mode_parser in subparsers.choices.values():
        mode_parser.add_argument(
            "--plugin-data", type=Path, default=argparse.SUPPRESS
        )
        mode_parser.add_argument(
            "--agents-dir", type=Path, default=argparse.SUPPRESS
        )
        mode_parser.add_argument(
            "--pretty", action="store_true", default=argparse.SUPPRESS
        )
    args = parser.parse_args(argv)
    try:
        if hasattr(args, "workspace_root") and args.workspace_root is not None:
            args.workspace_root = args.workspace_root.resolve()
        plugin_data = args.plugin_data
        if plugin_data is None:
            raw = os.environ.get("PLUGIN_DATA")
            if not raw:
                raise DispatchReceiptError("PLUGIN_DATA or --plugin-data is required")
            plugin_data = Path(raw)
        if not plugin_data.is_absolute():
            raise DispatchReceiptError("plugin data path must be absolute")
        if args.mode in {
            "workflow-run",
            "command-output",
            "intent",
            "result",
            "join",
            "inline",
            "deterministic",
            "root",
        }:
            if args.agents_dir is None:
                raise DispatchReceiptError("--agents-dir is required for workflow-bound records")
        if args.mode == "workflow-run":
            workflow = _load_workflow(
                args.plan,
                args.agents_dir,
                registry_path=args.registry,
                roles_dir=args.roles_dir,
            )
            record_ref = create_workflow_run_record(
                plugin_data,
                workflow,
                workspace_root=args.workspace_root,
                created_at=_timestamp_now(),
                nonce=secrets.token_hex(16),
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        elif args.mode == "subject":
            record_ref = create_subject_record(
                plugin_data,
                workspace_root=args.workspace_root,
                subject_paths=args.path,
                workflow_run_ref=args.workflow_run_ref,
                parent_refs=args.parent_ref,
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        elif args.mode == "workspace-snapshot":
            record_ref = create_workspace_snapshot_record(
                plugin_data, workspace_root=args.workspace_root
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        elif args.mode == "mutation-audit":
            record_ref = create_mutation_audit_record(
                plugin_data,
                before_ref=args.before_ref,
                after_ref=args.after_ref,
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        elif args.mode == "command-output":
            workflow = _load_workflow(
                args.plan,
                args.agents_dir,
                registry_path=args.registry,
                roles_dir=args.roles_dir,
            )
            record_ref = create_command_output_record(
                plugin_data,
                workflow,
                args.step_id,
                attempt=args.attempt,
                task_id=args.task_id,
                intent_ref=args.intent_ref,
                stdout_file=args.stdout_file,
                stderr_file=args.stderr_file,
                exit_code=args.exit_code,
                output_limit_bytes=args.output_limit_bytes,
                argv=args.argv,
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        elif args.mode == "abandon":
            record_ref = create_raw_abandonment_record(
                plugin_data,
                parent_session_id=args.parent_session_id,
                child_id=args.child_id,
                turn_id=args.turn_id,
                reason=args.reason,
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        elif args.mode == "prune":
            output = prune_raw_receipts(
                plugin_data,
                older_than_seconds=args.older_than_seconds,
                apply=args.apply,
                expected_plan_sha256=args.expected_plan_sha256,
                max_entries=args.max_entries,
                max_bytes=args.max_bytes,
            )
        elif args.mode == "intent":
            workflow = _load_workflow(
                args.plan,
                args.agents_dir,
                registry_path=args.registry,
                roles_dir=args.roles_dir,
            )
            record_ref = create_intent_record(
                plugin_data,
                workflow,
                args.step_id,
                attempt=args.attempt,
                task_id=args.task_id,
                subject_ref=args.subject_ref,
                workspace_snapshot_ref=args.workspace_snapshot_ref,
                intent_kind=args.intent_kind,
                previous_receipt_ref=args.previous_receipt_ref,
                finding_refs=args.finding_ref,
                resolution_refs=args.resolution_ref,
                created_at=args.created_at,
                nonce=args.nonce,
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        elif args.mode == "hook-trust":
            record_ref = create_hook_trust_record(
                plugin_data,
                codex_home=args.codex_home,
                installed_hooks_dir=args.installed_hooks_dir,
                scope=args.scope,
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        elif args.mode == "launch":
            record_ref = create_launch_record(
                plugin_data,
                intent_ref=args.intent_ref,
                parent_session_id=args.parent_session_id,
                turn_id=args.turn_id,
                child_id=args.child_id,
                agent_type=args.agent_type,
                hook_trust_ref=args.hook_trust_ref,
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        elif args.mode == "result":
            workflow = _load_workflow(
                args.plan,
                args.agents_dir,
                registry_path=args.registry,
                roles_dir=args.roles_dir,
            )
            evidence = json.loads(
                dispatch._read_bounded(
                    args.evidence_file, MAX_RECEIPT_BYTES, "result evidence"
                )
            )
            execution = json.loads(
                dispatch._read_bounded(
                    args.execution_file, MAX_RECEIPT_BYTES, "result execution"
                )
            )
            record_ref = create_result_record(
                plugin_data,
                workflow,
                args.step_id,
                attempt=args.attempt,
                task_id=args.task_id,
                intent_ref=args.intent_ref,
                output_subject_ref=args.output_subject_ref,
                mutation_audit_ref=args.mutation_audit_ref,
                workspace_root=args.workspace_root,
                vehicle=args.vehicle,
                child_id=args.child_id,
                provided_evidence=args.provided_evidence,
                evidence=evidence,
                execution=execution,
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        elif args.mode == "resolution":
            record_ref = create_resolution_record(
                plugin_data,
                result_ref=args.result_ref,
                finding_id=args.finding_id,
                resolved_subject_ref=args.resolved_subject_ref,
                evidence_refs=args.evidence_ref,
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        elif args.mode == "verify":
            record_ref = create_root_verification_record(
                plugin_data,
                result_ref=args.result_ref,
                verifier_session_id=args.verifier_session_id,
                verifier_turn_id=args.verifier_turn_id,
                resolution_refs=args.resolution_ref,
            )
            output = {"schema_version": 1, "record_ref": record_ref}
        else:
            workflow = _load_workflow(
                args.plan,
                args.agents_dir,
                registry_path=args.registry,
                roles_dir=args.roles_dir,
            )
            requested_intent, _requested_intent_bytes = _load_intent_record(
                plugin_data,
                args.intent_ref,
                workflow,
                args.step_id,
                args.attempt,
                args.task_id,
            )
            existing = load_normalized_by_identity(
                plugin_data,
                workflow.sha256,
                requested_intent["workflow_run_sha256"],
                args.step_id,
                args.attempt,
            )
            if existing is not None:
                receipt, relative_ref = existing
                validate_normalized_receipt(
                    plugin_data,
                    relative_ref,
                    workflow,
                    require_consumption_commit=False,
                )
                expected_refs = {
                    "intent_ref": args.intent_ref,
                    "result_ref": args.result_ref,
                    "root_verification_ref": args.root_verification_ref,
                }
                if (
                    receipt["vehicle"]
                    != {
                        "join": "verified-workflow-subagent",
                        "inline": "verified-workflow-inline",
                        "deterministic": "deterministic-tool",
                        "root": "root",
                    }[args.mode]
                    or receipt["intent_ref"] != expected_refs["intent_ref"]
                    or receipt["task_id"] != args.task_id
                    or receipt["result"]["result_ref"] != expected_refs["result_ref"]
                    or receipt["result"]["root_verification_ref"]
                    != expected_refs["root_verification_ref"]
                ):
                    raise DispatchReceiptError(
                        "existing normalized receipt conflicts with the retry"
                    )
                if args.mode == "join" and (
                    receipt["hook_trust"]["record_ref"] != args.hook_trust_ref
                    or receipt["child"]["launch_ref"] != args.launch_ref
                    or receipt["child"]["parent_session_id"]
                    != args.parent_session_id
                    or receipt["child"]["turn_id"] != args.turn_id
                    or receipt["child"]["child_id"] != args.child_id
                ):
                    raise DispatchReceiptError(
                        "existing normalized child receipt conflicts with the retry"
                    )
                recover_normalization_commit(plugin_data, receipt)
                validate_normalized_receipt(plugin_data, relative_ref, workflow)
                raw_cleanup = "already-normalized"
                if args.mode == "join":
                    try:
                        delete_raw_pair(
                            plugin_data,
                            parent_session_id=args.parent_session_id,
                            child_id=args.child_id,
                            turn_id=args.turn_id,
                            start_sha256=receipt["child"]["start_sha256"],
                            stop_sha256=receipt["child"]["stop_sha256"],
                        )
                        raw_cleanup = "complete"
                    except FileNotFoundError:
                        raw_cleanup = "already-clean"
                    except (DispatchReceiptError, OSError):
                        raw_cleanup = "deferred"
            elif args.mode == "join":
                start, stop, start_bytes, stop_bytes = load_raw_pair(
                    plugin_data,
                    parent_session_id=args.parent_session_id,
                    child_id=args.child_id,
                    turn_id=args.turn_id,
                )
                receipt = join_subagent_receipt(
                    plugin_data,
                    workflow,
                    args.step_id,
                    attempt=args.attempt,
                    task_id=args.task_id,
                    parent_session_id=args.parent_session_id,
                    child_id=args.child_id,
                    turn_id=args.turn_id,
                    intent_ref=args.intent_ref,
                    hook_trust_ref=args.hook_trust_ref,
                    launch_ref=args.launch_ref,
                    result_ref=args.result_ref,
                    root_verification_ref=args.root_verification_ref,
                    start=start,
                    stop=stop,
                    start_bytes=start_bytes,
                    stop_bytes=stop_bytes,
                )
                raw_pair_sha = receipt["child"]["raw_pair_sha256"]
                relative_ref = persist_normalized(
                    plugin_data, receipt, raw_pair_sha256=raw_pair_sha
                )
                validate_normalized_receipt(plugin_data, relative_ref, workflow)
                raw_cleanup = "complete"
                try:
                    delete_raw_pair(
                        plugin_data,
                        parent_session_id=args.parent_session_id,
                        child_id=args.child_id,
                        turn_id=args.turn_id,
                        start_sha256=receipt["child"]["start_sha256"],
                        stop_sha256=receipt["child"]["stop_sha256"],
                    )
                except (DispatchReceiptError, OSError):
                    raw_cleanup = "deferred"
            else:
                builder = {
                    "inline": build_inline_receipt,
                    "deterministic": build_deterministic_receipt,
                    "root": build_root_receipt,
                }[args.mode]
                receipt = builder(
                    plugin_data,
                    workflow,
                    args.step_id,
                    attempt=args.attempt,
                    task_id=args.task_id,
                    intent_ref=args.intent_ref,
                    result_ref=args.result_ref,
                    root_verification_ref=args.root_verification_ref,
                )
                relative_ref = persist_normalized(plugin_data, receipt)
                validate_normalized_receipt(plugin_data, relative_ref, workflow)
                raw_cleanup = None
            output = {
                "schema_version": 1,
                "vehicle": receipt["vehicle"],
                "receipt_ref": relative_ref,
                "receipt_sha256": _sha256(_canonical_bytes(receipt)),
            }
            if args.mode == "join":
                output["raw_cleanup"] = raw_cleanup
    except (
        DispatchReceiptError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        print(f"verified workflow receipt failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
