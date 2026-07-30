#!/usr/bin/env python3
"""Maintain one concise, atomic Verified Workflow run record."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

import protocol_probe
import workflow_dispatch as dispatch


MAX_RECORD_BYTES = 1024 * 1024
RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
ATTEMPT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}-attempt-[1-9][0-9]*$")
FORBIDDEN_KEYS = {"events", "messages", "raw_output", "stdout", "stderr", "rollout"}
RECORD_FIELDS = {
    "schema_version",
    "repository_id",
    "run_id",
    "plan_revision",
    "contract_sha256",
    "approval_binding_sha256",
    "status",
    "remediation_round",
    "deviation_used",
    "attempts",
    "checks",
    "external_actions",
    "findings",
    "root_decision",
}
EXTERNAL_ACTION_FIELDS = {
    "action_id",
    "provider",
    "model",
    "status",
    "approval_fingerprint",
    "authority",
    "artifact_sha256",
    "patch_sha256",
    "changed_paths",
    "root_disposition",
}
ATTEMPT_FIELDS = {
    "assignment_id",
    "attempt_id",
    "agent_path",
    "role",
    "profile",
    "model",
    "effort",
    "provider",
    "permission",
    "status",
    "summary",
    "changed_paths",
    "checks",
    "findings",
    "residual_risks",
    "review",
    "prior_edit_disposition",
}


class RunRecordError(ValueError):
    """Raised when the bounded run record would lose identity or authority."""


def _marker(repo_root: Path) -> dict[str, str]:
    return {
        "schema": "saga.workflow-repo-identity.v1",
        "repo_root_sha256": hashlib.sha256(repo_root.resolve().as_posix().encode()).hexdigest(),
    }


def _assert_safe_directory(path: Path, where: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise RunRecordError(f"{where} is unavailable") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_mode & 0o022
        or path.is_symlink()
    ):
        raise RunRecordError(f"{where} must be an owner-controlled, non-symlink directory")


def initialize_user_state_root(repo_root: Path, *, state_parent: Path | None = None) -> Path:
    parent = state_parent or Path.home() / ".codex" / "verified-workflows" / "state"
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(parent, 0o700)
    _assert_safe_directory(parent, "Verified Workflows state parent")
    state_root = parent / repo_root.resolve().name
    state_root.mkdir(mode=0o700, exist_ok=True)
    os.chmod(state_root, 0o700)
    _assert_safe_directory(state_root, "Verified Workflows repository state root")
    marker_path = state_root / ".repo-identity.json"
    expected = json.dumps(_marker(repo_root), sort_keys=True, separators=(",", ":")).encode() + b"\n"
    if marker_path.exists():
        if marker_path.is_symlink() or marker_path.read_bytes() != expected:
            raise RunRecordError("repository identity marker does not match this repository")
    else:
        descriptor = os.open(marker_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, expected)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    os.chmod(marker_path, 0o600)
    return state_root


def validate_state_root(repo_root: Path, state_root: Path) -> None:
    _assert_safe_directory(state_root, "Verified Workflows repository state root")
    marker_path = state_root / ".repo-identity.json"
    try:
        metadata = marker_path.lstat()
        content = marker_path.read_bytes()
    except OSError as exc:
        raise RunRecordError("repository identity marker is unavailable") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_mode & 0o022
        or len(content) > 4096
    ):
        raise RunRecordError("repository identity marker is unsafe")
    try:
        marker = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunRecordError("repository identity marker is invalid JSON") from exc
    if marker != _marker(repo_root):
        raise RunRecordError("repository identity marker does not match this repository")


def probe_project_fallback(repo_root: Path) -> Path:
    state_root = repo_root.resolve() / ".codex" / "verified-workflows"
    state_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        check = subprocess.run(
            ["git", "check-ignore", "-q", ".codex/verified-workflows/"],
            cwd=repo_root,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RunRecordError("project fallback ignore probe failed") from exc
    if check.returncode != 0:
        raise RunRecordError("project fallback is not git-ignored")
    probe = state_root / ".write-probe"
    try:
        descriptor = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(descriptor, b"probe")
        os.fsync(descriptor)
        os.close(descriptor)
        probe.unlink()
    except OSError as exc:
        raise RunRecordError("project fallback is not safely writable") from exc
    return state_root


def new_run_record(
    *,
    repository_id: str,
    run_id: str,
    contract: dispatch.WorkflowContract,
) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise RunRecordError("run_id is invalid")
    if not repository_id or len(repository_id) > 256:
        raise RunRecordError("repository_id is invalid")
    return {
        "schema_version": 1,
        "repository_id": repository_id,
        "run_id": run_id,
        "plan_revision": contract.plan_revision,
        "contract_sha256": contract.contract_sha256,
        "approval_binding_sha256": contract.approval_binding_sha256,
        "status": "approved",
        "remediation_round": 0,
        "deviation_used": False,
        "attempts": [],
        "checks": [],
        "external_actions": [],
        "findings": [],
        "root_decision": None,
    }


def _validate_record(record: object) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != RECORD_FIELDS:
        raise RunRecordError("run record fields are not closed")
    if record.get("schema_version") != 1 or RUN_ID_RE.fullmatch(str(record.get("run_id"))) is None:
        raise RunRecordError("run record identity is invalid")
    if record.get("status") not in {"approved", "running", "blocked", "passed", "failed"}:
        raise RunRecordError("run record status is invalid")
    if (
        isinstance(record.get("remediation_round"), bool)
        or not isinstance(record.get("remediation_round"), int)
        or not 0 <= record["remediation_round"] <= 1
    ):
        raise RunRecordError("run record remediation_round must be 0 or 1")
    if not isinstance(record.get("deviation_used"), bool):
        raise RunRecordError("run record deviation_used must be a boolean")
    attempts = record.get("attempts")
    if not isinstance(attempts, list) or len(attempts) > 256:
        raise RunRecordError("run record attempts must be bounded")
    for attempt in attempts:
        if not isinstance(attempt, dict) or set(attempt) != ATTEMPT_FIELDS:
            raise RunRecordError("run record attempt fields are not closed")
    external_actions = record.get("external_actions")
    if not isinstance(external_actions, list) or len(external_actions) > 64:
        raise RunRecordError("run record external actions must be bounded")
    for action in external_actions:
        if not isinstance(action, dict) or set(action) != EXTERNAL_ACTION_FIELDS:
            raise RunRecordError("run record external action fields are not closed")
    stack: list[object] = [record]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            forbidden = FORBIDDEN_KEYS & {str(key).casefold() for key in value}
            if forbidden:
                raise RunRecordError(
                    f"run record may not copy forbidden fields {sorted(forbidden)}"
                )
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    return record


def start_attempt(
    record: Mapping[str, Any],
    launch: dispatch.LaunchSpec,
    receipt: protocol_probe.RuntimeReceipt,
    *,
    attempt_id: str,
    prior_edit_disposition: str | None = None,
) -> dict[str, Any]:
    if ATTEMPT_ID_RE.fullmatch(attempt_id) is None:
        raise RunRecordError("attempt_id is invalid")
    updated = copy.deepcopy(_validate_record(dict(record)))
    attempts: list[dict[str, Any]] = updated["attempts"]
    same_attempt = [item for item in attempts if item["attempt_id"] == attempt_id]
    if same_attempt:
        existing = same_attempt[0]
        if existing["assignment_id"] != launch.assignment_id or existing["agent_path"] != receipt.agent_path:
            raise RunRecordError("same-attempt restoration must preserve assignment and agent path")
        if existing["status"] != "running":
            raise RunRecordError("a terminal attempt identity cannot be reused")
        return updated
    if any(item["agent_path"] == receipt.agent_path for item in attempts):
        raise RunRecordError("retry, remediation, and revalidation require a fresh canonical agent path")
    previous = [item for item in attempts if item["assignment_id"] == launch.assignment_id]
    if previous and previous[-1]["changed_paths"] and prior_edit_disposition not in {"cleanup", "carry-forward"}:
        raise RunRecordError("partial edits must be classified before a retry")
    if prior_edit_disposition not in {None, "cleanup", "carry-forward"}:
        raise RunRecordError("prior edit disposition is invalid")
    attempts.append(
        {
            "assignment_id": launch.assignment_id,
            "attempt_id": attempt_id,
            "agent_path": receipt.agent_path,
            "role": launch.role,
            "profile": launch.agent_type or "root",
            "model": receipt.model,
            "effort": receipt.reasoning_effort,
            "provider": receipt.model_provider,
            "permission": receipt.permission_profile,
            "status": "running",
            "summary": "",
            "changed_paths": [],
            "checks": [],
            "findings": [],
            "residual_risks": [],
            "review": None,
            "prior_edit_disposition": prior_edit_disposition,
        }
    )
    updated["status"] = "running"
    return updated


def finish_attempt(record: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(_validate_record(dict(record)))
    matches = [item for item in updated["attempts"] if item["attempt_id"] == result.get("attempt_id")]
    if len(matches) != 1:
        raise RunRecordError("terminal result does not match one running attempt")
    attempt = matches[0]
    if attempt["status"] != "running" or attempt["assignment_id"] != result.get("assignment_id"):
        raise RunRecordError("terminal result cannot update this attempt")
    for field in ("agent_path", "role", "profile"):
        result_field = {"role": "role_id", "profile": "profile_id"}.get(field, field)
        if attempt[field] != result.get(result_field):
            raise RunRecordError(f"terminal result {result_field} drifted from launch")
    attempt.update(
        {
            "status": result["terminal_status"],
            "summary": result["summary"],
            "changed_paths": list(result["changed_paths"]),
            "checks": copy.deepcopy(result["checks"]),
            "findings": copy.deepcopy(result["findings"]),
            "residual_risks": list(result["residual_risks"]),
            "review": (
                {
                    field: copy.deepcopy(result[field])
                    for field in (
                        "dimensions",
                        "exclusions",
                        "denominator",
                        "overall",
                        "verdict",
                        "hard_stop",
                    )
                }
                if "dimensions" in result
                else None
            ),
        }
    )
    updated["findings"] = [
        finding for item in updated["attempts"] for finding in item["findings"]
    ]
    one_hop_count = sum(
        finding.get("scope_disposition") == "one-hop"
        for finding in updated["findings"]
    )
    if one_hop_count > 1:
        raise RunRecordError("only one one-hop deviation is allowed per run")
    updated["deviation_used"] = one_hop_count == 1
    return updated


def record_external_action(
    record: Mapping[str, Any],
    *,
    action_id: str,
    provider: str,
    model: str,
    status: str,
    approval_fingerprint: str,
    artifact_sha256: str | None,
    patch_sha256: str | None,
    changed_paths: list[str],
    root_disposition: str,
) -> dict[str, Any]:
    """Project one Saga external action into the same concise workflow record."""

    updated = copy.deepcopy(_validate_record(dict(record)))
    if RUN_ID_RE.fullmatch(action_id) is None:
        raise RunRecordError("external action_id is invalid")
    if not provider.strip() or not model.strip():
        raise RunRecordError("external action provider and model are required")
    if status not in {
        "available",
        "accepted",
        "consumed",
        "rejected",
        "not-launched",
        "unavailable",
        "timed-out",
        "interrupted",
        "canceled",
        "invalid-evidence",
    }:
        raise RunRecordError("external action status is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", approval_fingerprint):
        raise RunRecordError("external action approval fingerprint is invalid")
    for name, digest in (("artifact", artifact_sha256), ("patch", patch_sha256)):
        if digest is not None and re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise RunRecordError(f"external action {name} digest is invalid")
    if root_disposition not in {"pending", "adopted", "ignored", "imported", "rejected"}:
        raise RunRecordError("external action root disposition is invalid")
    if not isinstance(changed_paths, list) or any(
        not isinstance(path, str) or not path.strip() for path in changed_paths
    ):
        raise RunRecordError("external action changed paths are invalid")
    if len(set(changed_paths)) != len(changed_paths):
        raise RunRecordError("external action changed paths contain duplicates")
    entry = {
        "action_id": action_id,
        "provider": provider.strip(),
        "model": model.strip(),
        "status": status,
        "approval_fingerprint": approval_fingerprint,
        "authority": "non-gating",
        "artifact_sha256": artifact_sha256,
        "patch_sha256": patch_sha256,
        "changed_paths": sorted(changed_paths),
        "root_disposition": root_disposition,
    }
    actions = updated["external_actions"]
    existing = [index for index, item in enumerate(actions) if item["action_id"] == action_id]
    if existing:
        actions[existing[0]] = entry
    else:
        actions.append(entry)
    return updated


def write_run_record(repo_root: Path, state_root: Path, record: Mapping[str, Any]) -> Path:
    validate_state_root(repo_root, state_root)
    validated = _validate_record(dict(record))
    content = json.dumps(validated, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    if len(content) > MAX_RECORD_BYTES:
        raise RunRecordError("run record exceeds the bounded size ceiling")
    runs = state_root / "workflow-runs"
    runs.mkdir(mode=0o700, exist_ok=True)
    _assert_safe_directory(runs, "workflow run directory")
    destination = runs / f"{validated['run_id']}.json"
    descriptor, temporary_name = tempfile.mkstemp(prefix=".run-record-", dir=runs)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        os.write(descriptor, content)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, destination)
        directory_fd = os.open(runs, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return destination


def read_run_record(repo_root: Path, state_root: Path, run_id: str) -> dict[str, Any]:
    validate_state_root(repo_root, state_root)
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise RunRecordError("run_id is invalid")
    path = state_root / "workflow-runs" / f"{run_id}.json"
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise RunRecordError("run record is unavailable") from exc
    if len(content) > MAX_RECORD_BYTES or path.is_symlink():
        raise RunRecordError("run record is unsafe")
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunRecordError("run record is invalid JSON") from exc
    return _validate_record(payload)
