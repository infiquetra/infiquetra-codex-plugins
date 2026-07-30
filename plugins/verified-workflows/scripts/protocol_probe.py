#!/usr/bin/env python3
"""Validate Codex V2 session_meta plus turn_context runtime readback."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import render_codex_agents as renderer
import workflow_dispatch as dispatch


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs" / "validation" / "codex-runtime-capability-snapshot.json"
MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024
MAX_ROLLOUT_BYTES = 8 * 1024 * 1024
AGENT_PATH_RE = re.compile(r"^/root(?:/[a-zA-Z0-9][a-zA-Z0-9_-]{0,127})+$")
TASK_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")
GIT_INVOCATION_RE = re.compile(r"(?:^|[;&|()\s])(?:[^\s;&|()]+/)?git(?:\s|$)", re.I)


class ProtocolProbeError(ValueError):
    """Raised when runtime readback is missing, malformed, or mismatched."""


@dataclass(frozen=True, slots=True)
class RuntimeReceipt:
    session_id: str
    parent_thread_id: str
    agent_path: str
    agent_type: str
    model: str
    reasoning_effort: str
    model_provider: str
    approval_policy: str
    permission_profile: str
    sandbox_mode: str
    multi_agent_version: str
    terminal_observed: bool
    git_invocation_observed: bool
    child_paths: tuple[str, ...]
    source_events: tuple[str, ...]


def _read_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    try:
        content = renderer._regular_single_link(path, "capability snapshot", MAX_SNAPSHOT_BYTES)
    except renderer.RoleRegistryError as exc:
        raise ProtocolProbeError(str(exc)) from exc
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolProbeError("capability snapshot is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ProtocolProbeError("capability snapshot must be an object")
    return payload, hashlib.sha256(content).hexdigest()


def _object(value: object, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolProbeError(f"{where} must be an object")
    return value


def _required_string(value: object, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProtocolProbeError(f"{where} must be a non-empty string")
    return value


def _policy_type(value: object, where: str) -> str:
    if isinstance(value, str):
        return _required_string(value, where)
    payload = _object(value, where)
    return _required_string(payload.get("type"), f"{where}.type")


def _function_name(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.rsplit(".", 1)[-1].rsplit("__", 1)[-1]


def parse_runtime_receipt(content: bytes) -> RuntimeReceipt:
    """Project one Codex rollout into the closed V2 identity receipt."""

    if len(content) > MAX_ROLLOUT_BYTES:
        raise ProtocolProbeError("runtime rollout exceeds the bounded input ceiling")
    meta: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    terminal = False
    git_invocation = False
    child_task_names: set[str] = set()
    event_types: set[str] = set()
    for number, raw_line in enumerate(content.splitlines(), 1):
        try:
            row = json.loads(raw_line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProtocolProbeError(f"runtime rollout line {number} is invalid JSON") from exc
        row = _object(row, f"runtime rollout line {number}")
        row_type = row.get("type")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if isinstance(row_type, str):
            event_types.add(row_type)
        if row_type == "session_meta":
            if meta is not None:
                raise ProtocolProbeError("runtime rollout repeats session_meta")
            meta = payload
        elif row_type == "turn_context":
            context = payload
        elif row_type == "event_msg" and payload.get("type") == "task_complete":
            terminal = True
        elif row_type == "response_item":
            name = _function_name(payload.get("name"))
            arguments = payload.get("arguments", payload.get("input", {}))
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"cmd": arguments}
            if name in {"exec_command", "write_stdin"} and isinstance(arguments, dict):
                command = arguments.get("cmd", arguments.get("chars", ""))
                if isinstance(command, str) and GIT_INVOCATION_RE.search(command):
                    git_invocation = True
            if name == "spawn_agent" and isinstance(arguments, dict):
                task_name = arguments.get("task_name")
                if not isinstance(task_name, str) or TASK_NAME_RE.fullmatch(task_name) is None:
                    raise ProtocolProbeError(
                        "spawn_agent requires one canonical V2 arguments.task_name"
                    )
                child_task_names.add(task_name)
    if meta is None or context is None:
        raise ProtocolProbeError("runtime rollout requires both session_meta and turn_context")

    source = meta.get("source")
    spawn: dict[str, Any] = {}
    if isinstance(source, dict):
        subagent = source.get("subagent")
        if isinstance(subagent, dict) and isinstance(subagent.get("thread_spawn"), dict):
            spawn = subagent["thread_spawn"]
    agent_path = _required_string(
        meta.get("agent_path", spawn.get("agent_path")), "session_meta.agent_path"
    )
    return RuntimeReceipt(
        session_id=_required_string(meta.get("id"), "session_meta.id"),
        parent_thread_id=_required_string(
            meta.get("parent_thread_id"), "session_meta.parent_thread_id"
        ),
        agent_path=agent_path,
        agent_type=_required_string(
            meta.get("agent_role", spawn.get("agent_role")), "session_meta.agent_role"
        ),
        model=_required_string(context.get("model"), "turn_context.model"),
        reasoning_effort=_required_string(context.get("effort"), "turn_context.effort"),
        model_provider=_required_string(meta.get("model_provider"), "session_meta.model_provider"),
        approval_policy=_required_string(
            context.get("approval_policy"), "turn_context.approval_policy"
        ),
        permission_profile=_policy_type(
            context.get("permission_profile"), "turn_context.permission_profile"
        ),
        sandbox_mode=_policy_type(context.get("sandbox_policy"), "turn_context.sandbox_policy"),
        multi_agent_version=_required_string(
            context.get("multi_agent_version", meta.get("multi_agent_version")),
            "turn_context.multi_agent_version",
        ),
        terminal_observed=terminal,
        git_invocation_observed=git_invocation,
        child_paths=tuple(sorted(f"{agent_path}/{name}" for name in child_task_names)),
        source_events=tuple(sorted(event_types & {"session_meta", "turn_context"})),
    )


def _path_is_declared(path: str, declared: Sequence[str]) -> bool:
    return any(path == allowed or path.startswith(f"{allowed}/") for allowed in declared)


def validate_runtime_receipt(
    receipt: RuntimeReceipt,
    launch: dispatch.LaunchSpec,
    *,
    expected_agent_path: str,
    expected_provider: str,
    expected_permission_profile: str,
    expected_sandbox_mode: str,
    declared_descendant_paths: Sequence[str] = (),
    descendant_receipts: Sequence[RuntimeReceipt] = (),
) -> None:
    """Fail closed unless host-issued V2 readback matches the approved launch."""

    if launch.agent_type is None:
        raise ProtocolProbeError("root assignments do not accept child runtime receipts")
    expected = {
        "agent_path": expected_agent_path,
        "agent_type": launch.agent_type,
        "model": launch.expected_model,
        "reasoning_effort": launch.expected_reasoning_effort,
        "model_provider": expected_provider,
        "permission_profile": expected_permission_profile,
        "sandbox_mode": expected_sandbox_mode,
        "multi_agent_version": "v2",
    }
    actual = asdict(receipt)
    for field, value in expected.items():
        if actual[field] != value:
            raise ProtocolProbeError(
                f"runtime {field} mismatch: expected {value!r}, observed {actual[field]!r}"
            )
    if AGENT_PATH_RE.fullmatch(receipt.agent_path) is None:
        raise ProtocolProbeError("runtime agent_path is not canonical")
    if receipt.git_invocation_observed and launch.role != "git-integration-operator":
        raise ProtocolProbeError("worker runtime observed a prohibited Git invocation")
    undeclared = [
        path for path in receipt.child_paths if not _path_is_declared(path, declared_descendant_paths)
    ]
    if undeclared:
        raise ProtocolProbeError(f"runtime receipt contains undeclared descendant paths {undeclared}")
    receipt_by_path: dict[str, RuntimeReceipt] = {}
    for child in descendant_receipts:
        if child.agent_path in receipt_by_path:
            raise ProtocolProbeError(
                f"runtime descendant receipt repeats agent path {child.agent_path!r}"
            )
        receipt_by_path[child.agent_path] = child
    missing_receipts = sorted(set(receipt.child_paths) - set(receipt_by_path))
    extra_receipts = sorted(set(receipt_by_path) - set(receipt.child_paths))
    if missing_receipts or extra_receipts:
        raise ProtocolProbeError(
            "runtime descendant receipt set does not match observed V2 spawns: "
            f"missing={missing_receipts} unexpected={extra_receipts}"
        )
    for path, child in receipt_by_path.items():
        if child.parent_thread_id != receipt.session_id:
            raise ProtocolProbeError(
                f"runtime descendant {path!r} parent thread does not match its spawning session"
            )
        if AGENT_PATH_RE.fullmatch(child.agent_path) is None:
            raise ProtocolProbeError(f"runtime descendant {path!r} agent path is not canonical")
    if receipt.source_events != ("session_meta", "turn_context"):
        raise ProtocolProbeError("runtime receipt lacks both authoritative source events")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollout", type=Path, required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        content = dispatch._read_bounded(args.rollout, MAX_ROLLOUT_BYTES, "runtime rollout")
        receipt = parse_runtime_receipt(content)
    except (OSError, dispatch.WorkflowDispatchError, ProtocolProbeError) as exc:
        print(f"verified workflow runtime readback failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(asdict(receipt), indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
