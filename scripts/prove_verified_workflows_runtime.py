#!/usr/bin/env python3
"""Prove the minimal Codex V2 runtime identity boundary with the active login."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugins" / "verified-workflows"
PLUGIN_SCRIPTS = PLUGIN_ROOT / "scripts"
if str(PLUGIN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PLUGIN_SCRIPTS))

import render_codex_agents as renderer  # noqa: E402

DEFAULT_SNAPSHOT = REPO_ROOT / "docs" / "validation" / "codex-runtime-capability-snapshot.json"
PROJECT_AGENTS = REPO_ROOT / ".codex" / "agents"
MAX_BYTES = 4 * 1024 * 1024
MAX_NEW_ROLLOUTS = 16
TERMINAL_MARKER = "V2_PROFILE_CHILD_OK"
ROOT_MARKER = "V2_PROFILE_ROOT_OK"
PARENT_ONLY_MARKER = "V2_PROFILE_PARENT_ONLY_CONTEXT"
TASK_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SECRET_KEY = re.compile(r"(?i)(token|secret|password|credential|authorization|api[_-]?key|auth_json)")
SECRET_VALUE = re.compile(
    r"(?i)(?:\bsk-[A-Za-z0-9_-]{8,}|\bgh[pousr]_[A-Za-z0-9]{8,}|"
    r"\bBearer\s+[A-Za-z0-9._~-]{8,}|\beyJ[A-Za-z0-9_-]{8,}\."
    r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})"
)


class RuntimeProofError(RuntimeError):
    """Raised when proof inputs are unsafe, incomplete, or contradict runtime truth."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_regular(path: Path, where: str, limit: int = MAX_BYTES) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RuntimeProofError(f"{where} is unreadable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > limit
        ):
            raise RuntimeProofError(f"{where} must be a bounded single-link regular file")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            len(content) > limit
            or len(content) != before.st_size
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise RuntimeProofError(f"{where} changed while it was read")
        return content
    finally:
        os.close(descriptor)


def _load_json(path: Path, where: str) -> tuple[dict[str, Any], str]:
    content = _read_regular(path, where)
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeProofError(f"{where} is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeProofError(f"{where} must be an object")
    return payload, _sha256(content)


def _native_model_cache(
    codex_home: Path, required_models: Sequence[str]
) -> tuple[Path, dict[str, Any]]:
    path = codex_home / "models_cache.json"
    payload, digest = _load_json(path, "native Codex model cache")
    rows = payload.get("models")
    if not isinstance(rows, list):
        raise RuntimeProofError("native Codex model cache lacks model rows")
    versions: dict[str, str | None] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeProofError("native Codex model cache has a malformed row")
        slug = row.get("slug")
        version = row.get("multi_agent_version")
        if isinstance(slug, str):
            versions[slug] = version if isinstance(version, str) else None
    required = sorted(set(required_models))
    if any(versions.get(model) != "v2" for model in required):
        raise RuntimeProofError("required model is not V2 in the native Codex model cache")
    return path, {
        "source": "native-model-cache",
        "sha256": digest,
        "required_v2_models": required,
        "luna_multi_agent_version": versions.get("gpt-5.6-luna"),
    }


def _reject_default_profile_input(path: Path, where: str) -> None:
    default = (Path.home() / ".codex").resolve(strict=False)
    candidate = path.expanduser().resolve(strict=False)
    if candidate == default or default in candidate.parents:
        raise RuntimeProofError(f"{where} must not read from the default Codex profile tree")


def _snapshot_projection(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    runtime = snapshot.get("runtime")
    collaboration = snapshot.get("collaboration")
    if not isinstance(runtime, dict) or not isinstance(collaboration, dict):
        raise RuntimeProofError("capability snapshot lacks required closed sections")
    version = runtime.get("codex_cli_version")
    if version != "0.145.0":
        raise RuntimeProofError("capability snapshot must target Codex 0.145.0")
    spawn = collaboration.get("spawn")
    expected_spawn_fields = {
        "available",
        "contract_version",
        "tool_namespace",
        "hide_spawn_agent_metadata",
        "request_fields",
        "response_fields",
        "default_fork_turns",
        "profile_selection_fork_turns",
        "per_child_agent_type",
        "per_child_model",
        "per_child_effort",
        "per_child_sandbox",
        "runtime_receipt_sources",
        "selection_readback_fields",
    }
    if not isinstance(spawn, dict) or set(spawn) != expected_spawn_fields:
        raise RuntimeProofError("capability snapshot V2 spawn schema is not closed")
    if (
        spawn["available"] is not True
        or spawn["contract_version"] != "v2"
        or spawn["tool_namespace"] != "agents"
        or spawn["hide_spawn_agent_metadata"] is not False
    ):
        raise RuntimeProofError("capability snapshot V2 selection contract drifted")
    expected_requests = [
        "agent_type",
        "fork_turns",
        "message",
        "model",
        "reasoning_effort",
        "service_tier",
        "task_name",
    ]
    expected_readback = [
        "agent_path",
        "agent_role",
        "model",
        "reasoning_effort",
        "model_provider",
        "approval_policy",
        "permission_profile",
        "sandbox_policy",
        "multi_agent_version",
    ]
    if spawn["request_fields"] != expected_requests:
        raise RuntimeProofError("capability snapshot V2 request fields drifted")
    if spawn["response_fields"] != ["nickname", "task_name"]:
        raise RuntimeProofError("capability snapshot V2 response fields drifted")
    if spawn["runtime_receipt_sources"] != ["session_meta", "turn_context"]:
        raise RuntimeProofError("capability snapshot V2 receipt sources drifted")
    if spawn["selection_readback_fields"] != expected_readback:
        raise RuntimeProofError("capability snapshot V2 readback fields drifted")
    if spawn["default_fork_turns"] != "all" or spawn[
        "profile_selection_fork_turns"
    ] != ["none", "positive-integer"]:
        raise RuntimeProofError("capability snapshot V2 context contract drifted")
    for field in ("per_child_agent_type", "per_child_model", "per_child_effort"):
        if spawn[field] is not True:
            raise RuntimeProofError(f"capability snapshot must enable {field}")
    if spawn["per_child_sandbox"] is not False:
        raise RuntimeProofError("Codex 0.145.0 does not support per-child sandbox override")
    operations = collaboration.get("operations")
    if operations != [
        "followup_task",
        "interrupt_agent",
        "list_agents",
        "send_message",
        "spawn_agent",
        "wait_agent",
    ]:
        raise RuntimeProofError("capability snapshot V2 operation inventory drifted")
    return {"version": version, "spawn": spawn, "operations": operations}


def _task_name_from_tool(name: object) -> str | None:
    if not isinstance(name, str) or not name:
        return None
    normalized = name.rsplit(".", 1)[-1].rsplit("__", 1)[-1]
    return normalized if normalized in {
        "spawn_agent",
        "send_message",
        "followup_task",
        "wait_agent",
        "interrupt_agent",
        "list_agents",
    } else None


def parse_rollout_receipt(content: bytes) -> dict[str, Any]:
    """Project one rollout into the allowlisted V2 identity and permission receipt."""

    meta: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    terminal = False
    terminal_marker = False
    operations: set[str] = set()
    for number, raw_line in enumerate(content.splitlines(), 1):
        try:
            row = json.loads(raw_line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeProofError(f"rollout line {number} is invalid JSON") from exc
        if not isinstance(row, dict):
            raise RuntimeProofError(f"rollout line {number} must be an object")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if row.get("type") == "session_meta":
            if meta is not None:
                raise RuntimeProofError("rollout repeats session_meta")
            meta = payload
        elif row.get("type") == "turn_context":
            context = payload
        elif row.get("type") == "event_msg" and payload.get("type") == "task_complete":
            terminal = True
            terminal_marker = payload.get("last_agent_message") == TERMINAL_MARKER
        elif row.get("type") == "response_item":
            operation = _task_name_from_tool(payload.get("name"))
            if operation is not None:
                operations.add(operation)
    if meta is None or context is None:
        raise RuntimeProofError("rollout lacks session_meta or turn_context")
    source = meta.get("source")
    spawn = {}
    if isinstance(source, dict):
        subagent = source.get("subagent")
        if isinstance(subagent, dict) and isinstance(subagent.get("thread_spawn"), dict):
            spawn = subagent["thread_spawn"]
    sandbox = context.get("sandbox_policy")
    sandbox_mode = sandbox.get("type") if isinstance(sandbox, dict) else sandbox
    permission = context.get("permission_profile")
    permission_kind = permission.get("type") if isinstance(permission, dict) else None
    receipt = {
        "session_id": meta.get("id"),
        "parent_thread_id": meta.get("parent_thread_id"),
        "parent_thread_present": isinstance(meta.get("parent_thread_id"), str),
        "agent_path": meta.get("agent_path", spawn.get("agent_path")),
        "agent_role": meta.get("agent_role", spawn.get("agent_role")),
        "model": context.get("model"),
        "reasoning_effort": context.get("effort"),
        "model_provider": meta.get("model_provider"),
        "approval_policy": context.get("approval_policy"),
        "sandbox_mode": sandbox_mode,
        "permission_profile": permission_kind,
        "multi_agent_version": context.get(
            "multi_agent_version", meta.get("multi_agent_version")
        ),
        "history_mode": meta.get("history_mode"),
        "parent_context_marker_observed": PARENT_ONLY_MARKER.encode() in content,
        "terminal_status": "completed" if terminal else "incomplete",
        "terminal_marker_observed": terminal_marker,
        "operations_observed": sorted(operations),
    }
    validate_sanitized_proof(receipt, "runtime_receipt")
    return receipt


def validate_runtime_receipt(
    receipt: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    fields = (
        "agent_path",
        "agent_role",
        "model",
        "reasoning_effort",
        "model_provider",
        "approval_policy",
        "sandbox_mode",
        "permission_profile",
        "multi_agent_version",
    )
    for field in fields:
        if receipt.get(field) != expected.get(field):
            raise RuntimeProofError(f"runtime receipt {field} mismatch")
    if not isinstance(receipt.get("permission_profile"), str):
        raise RuntimeProofError("runtime receipt permission_profile is missing")
    if receipt.get("parent_thread_present") is not True:
        raise RuntimeProofError("runtime receipt lacks parent thread identity")
    if receipt.get("terminal_status") != "completed":
        raise RuntimeProofError("runtime receipt is not terminal")
    if receipt.get("terminal_marker_observed") is not True:
        raise RuntimeProofError("runtime receipt terminal result mismatch")
    if receipt.get("parent_context_marker_observed") is not False:
        raise RuntimeProofError("runtime receipt inherited root-only context")


def _profile_facts() -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    for profile_id, runtime_agent_name in renderer.RUNTIME_AGENT_NAMES.items():
        path = PLUGIN_ROOT / "agents" / f"{runtime_agent_name}.toml"
        content = _read_regular(path, "managed profile", 1024 * 1024)
        facts.append(
            {
                "profile_id": profile_id,
                "runtime_agent_name": runtime_agent_name,
                "sha256": _sha256(content),
            }
        )
    if not facts:
        raise RuntimeProofError("managed profile source is empty")
    return facts


def _project_agent_facts() -> dict[str, Any]:
    expected = {
        f"{runtime_name}.toml" for runtime_name in renderer.RUNTIME_AGENT_NAMES.values()
    }
    try:
        children = list(PROJECT_AGENTS.iterdir())
    except OSError as exc:
        raise RuntimeProofError("project agent discovery directory is unreadable") from exc
    actual = {child.name for child in children}
    if actual != expected:
        raise RuntimeProofError("project agent discovery inventory drifted")
    files: list[dict[str, str]] = []
    for filename in sorted(expected):
        project_content = _read_regular(
            PROJECT_AGENTS / filename, "project agent discovery profile", 1024 * 1024
        )
        source_content = _read_regular(
            PLUGIN_ROOT / "agents" / filename, "source agent profile", 1024 * 1024
        )
        if project_content != source_content:
            raise RuntimeProofError("project agent discovery bytes drifted")
        files.append({"filename": filename, "sha256": _sha256(project_content)})
    return {
        "location": ".codex/agents",
        "regular_files_only": True,
        "source_bytes_match": True,
        "files": files,
    }


def _project_profile_expectation(profile: str) -> dict[str, str]:
    if not TASK_NAME_RE.fullmatch(profile):
        raise RuntimeProofError("profile name is invalid")
    source = PLUGIN_ROOT / "agents" / f"{profile}.toml"
    installed = PROJECT_AGENTS / f"{profile}.toml"
    source_bytes = _read_regular(source, "source profile", 1024 * 1024)
    installed_bytes = _read_regular(installed, "project-discovered profile", 1024 * 1024)
    if source_bytes != installed_bytes:
        raise RuntimeProofError("project profile bytes do not match source")
    try:
        payload = tomllib.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeProofError("source profile is invalid TOML") from exc
    model = payload.get("model")
    effort = payload.get("model_reasoning_effort")
    sandbox = payload.get("sandbox_mode")
    if not all(isinstance(value, str) for value in (model, effort, sandbox)):
        raise RuntimeProofError("source profile lacks model, effort, or sandbox")
    return {
        "agent_role": profile,
        "model": model,
        "reasoning_effort": effort,
        "sandbox_mode": sandbox,
        "sha256": _sha256(source_bytes),
    }


def _rollout_paths(codex_home: Path) -> set[Path]:
    sessions = codex_home / "sessions"
    if not sessions.exists():
        return set()
    return set(sessions.glob("**/rollout-*.jsonl"))


def _thread_id_from_exec_output(stdout: bytes) -> str | None:
    for raw_line in stdout.splitlines():
        try:
            row = json.loads(raw_line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(row, dict) and row.get("type") == "thread.started":
            thread_id = row.get("thread_id")
            if isinstance(thread_id, str):
                return thread_id
    return None


def run_live_probe(
    *, profile: str = "review_high", task_name: str = "v2_profile_probe"
) -> dict[str, Any]:
    if not TASK_NAME_RE.fullmatch(task_name):
        raise RuntimeProofError("task name is invalid")
    expected_profile = _project_profile_expectation(profile)
    if expected_profile["sandbox_mode"] != "read-only":
        raise RuntimeProofError("the minimal V2 live probe requires a read-only profile")
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    if not codex_home.is_dir():
        raise RuntimeProofError("the active Codex home is unavailable")
    native_catalog_path, native_catalog = _native_model_cache(
        codex_home, ("gpt-5.6-sol", expected_profile["model"])
    )
    before = _rollout_paths(codex_home)
    prompt = (
        f"Retain this root-only marker and never include it in the child message: "
        f"{PARENT_ONLY_MARKER}. Use spawn_agent exactly once with task_name {task_name}, "
        f"agent_type {profile}, "
        f"fork_turns none, model {expected_profile['model']}, and reasoning_effort "
        f"{expected_profile['reasoning_effort']}. Ask the child to return exactly "
        f"{TERMINAL_MARKER} and do nothing else. Use list_agents and wait_agent until it "
        f"completes. Return exactly {ROOT_MARKER}."
    )
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    argv = [
        "codex",
        "exec",
        "--json",
        "--ignore-rules",
        "--strict-config",
        "-C",
        str(REPO_ROOT),
        "--sandbox",
        "read-only",
        "-m",
        "gpt-5.6-sol",
        "-c",
        'model_reasoning_effort="max"',
        "-c",
        f"model_catalog_json={json.dumps(str(native_catalog_path))}",
        prompt,
    ]
    try:
        result = subprocess.run(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=240,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeProofError("Codex V2 live probe timed out") from exc
    if len(result.stdout) > MAX_BYTES or len(result.stderr) > MAX_BYTES:
        raise RuntimeProofError("Codex V2 live probe exceeded the output ceiling")
    if result.returncode:
        raise RuntimeProofError(f"Codex V2 live probe failed with exit {result.returncode}")
    after = _rollout_paths(codex_home)
    created = sorted(after - before)
    if not created:
        raise RuntimeProofError("Codex V2 live probe produced no rollout receipts")
    if len(created) > MAX_NEW_ROLLOUTS:
        raise RuntimeProofError("Codex V2 live probe produced too many rollout receipts")
    parsed = []
    for path in created:
        content = _read_regular(path, "live rollout")
        parsed.append((parse_rollout_receipt(content), content))
    root_thread_id = _thread_id_from_exec_output(result.stdout)
    child_path = f"/root/{task_name}"
    children = [pair for pair in parsed if pair[0].get("agent_path") == child_path]
    if len(children) != 1:
        raise RuntimeProofError("Codex V2 live probe did not produce one canonical child")
    child, _child_content = children[0]
    roots = [
        receipt
        for receipt, _content in parsed
        if receipt.get("session_id") == root_thread_id
        or (
            receipt.get("parent_thread_id") is None
            and receipt.get("agent_path") in {None, "/root"}
        )
    ]
    if len(roots) != 1:
        raise RuntimeProofError("Codex V2 live probe did not identify one root receipt")
    root = roots[0]
    expected = {
        **expected_profile,
        "agent_path": child_path,
        "model_provider": root.get("model_provider"),
        "approval_policy": root.get("approval_policy"),
        "permission_profile": root.get("permission_profile"),
        "multi_agent_version": "v2",
    }
    validate_runtime_receipt(child, expected)
    if child.get("parent_thread_id") != root.get("session_id"):
        raise RuntimeProofError("Codex V2 child is not attached to the observed root")
    if root.get("multi_agent_version") != "v2":
        raise RuntimeProofError("Codex V2 root receipt reports a different backend")
    if root.get("model") != "gpt-5.6-sol" or root.get("reasoning_effort") != "max":
        raise RuntimeProofError("Codex V2 root model or reasoning effort drifted")
    if root.get("approval_policy") != "never":
        raise RuntimeProofError("Codex V2 root approval policy drifted")
    if root.get("sandbox_mode") != expected_profile["sandbox_mode"]:
        raise RuntimeProofError("Codex V2 root permission does not match the profile ceiling")
    root_ops = set(root.get("operations_observed", []))
    required_operations = {"spawn_agent", "list_agents", "wait_agent"}
    if not required_operations.issubset(root_ops):
        raise RuntimeProofError("Codex V2 root receipt lacks required probe operations")
    return {
        "catalog": native_catalog,
        "root": {
            key: root.get(key)
            for key in (
                "model",
                "reasoning_effort",
                "model_provider",
                "approval_policy",
                "sandbox_mode",
                "permission_profile",
                "multi_agent_version",
                "operations_observed",
            )
        },
        "child": {
            key: child.get(key)
            for key in (
                "agent_path",
                "agent_role",
                "model",
                "reasoning_effort",
                "model_provider",
                "approval_policy",
                "sandbox_mode",
                "permission_profile",
                "multi_agent_version",
                "history_mode",
                "parent_context_marker_observed",
                "terminal_status",
                "terminal_marker_observed",
            )
        },
        "profile_sha256": expected_profile["sha256"],
    }


def build_proof(
    *,
    snapshot: dict[str, Any],
    snapshot_sha256: str,
    live: bool,
    runtime_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    projection = _snapshot_projection(snapshot)
    if live and runtime_receipt is None:
        raise RuntimeProofError("authenticated live proof requires a runtime receipt")
    elif live:
        outcome = "supported"
        reason = "current-session Codex V2 rollout attests project profile and effective runtime fields"
    elif runtime_receipt is not None:
        raise RuntimeProofError("a runtime receipt requires --live")
    else:
        outcome = "diagnostic"
        reason = "source and configuration contract only; no live runtime receipt supplied"
    proof = {
        "schema_version": 2,
        "claim": "codex-v2-runtime-capability",
        "harness_sha256": _sha256(_read_regular(Path(__file__), "runtime proof harness")),
        "mode": "current-session-live" if runtime_receipt is not None else "dry-run",
        "capability_outcome": outcome,
        "reason": reason,
        "snapshot_sha256": snapshot_sha256,
        "codex_cli_version": projection["version"],
        "tool_namespace": projection["spawn"]["tool_namespace"],
        "spawn_request_fields": projection["spawn"]["request_fields"],
        "spawn_response_fields": projection["spawn"]["response_fields"],
        "runtime_readback_fields": projection["spawn"]["selection_readback_fields"],
        "operations": projection["operations"],
        "profiles": _profile_facts(),
        "project_discovery": _project_agent_facts(),
        "live_invocation_performed": runtime_receipt is not None,
        "runtime_receipt": runtime_receipt,
        "limitations": [
            "Codex 0.145.0 child permissions inherit the parent turn after profile loading",
            "this minimal probe covers one read-only child; the receipt-derived matrix covers the full operation set",
            "requested spawn fields are never accepted as runtime identity without session_meta and turn_context",
        ],
    }
    validate_sanitized_proof(proof)
    return proof


def validate_sanitized_proof(payload: object, path: str = "proof", depth: int = 0) -> None:
    if depth > 8:
        raise RuntimeProofError(f"{path} exceeds the proof nesting ceiling")
    if isinstance(payload, dict):
        if len(payload) > 64:
            raise RuntimeProofError(f"{path} exceeds the proof object ceiling")
        for key, value in payload.items():
            if not isinstance(key, str) or SECRET_KEY.search(key):
                raise RuntimeProofError(f"{path} contains a secret-shaped field")
            validate_sanitized_proof(value, f"{path}.{key}", depth + 1)
    elif isinstance(payload, list):
        if len(payload) > 128:
            raise RuntimeProofError(f"{path} exceeds the proof list ceiling")
        for index, value in enumerate(payload):
            validate_sanitized_proof(value, f"{path}[{index}]", depth + 1)
    elif isinstance(payload, str):
        if (
            payload.startswith(("/Users/", "~", "file:"))
            or SECRET_KEY.search(payload)
            or SECRET_VALUE.search(payload)
        ):
            raise RuntimeProofError(f"{path} contains a path or secret-shaped value")
        if len(payload) > 512:
            raise RuntimeProofError(f"{path} exceeds the proof string ceiling")
    elif isinstance(payload, float) and not math.isfinite(payload):
        raise RuntimeProofError(f"{path} contains a non-finite number")
    elif payload is not None and not isinstance(payload, (bool, int, float)):
        raise RuntimeProofError(f"{path} contains an unsupported value")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--profile", default="review_high")
    parser.add_argument("--task-name", default="v2_profile_probe")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        _reject_default_profile_input(args.snapshot, "capability snapshot")
        snapshot, digest = _load_json(args.snapshot, "capability snapshot")
        receipt = None
        if args.live:
            receipt = run_live_probe(
                profile=args.profile,
                task_name=args.task_name,
            )
        proof = build_proof(
            snapshot=snapshot,
            snapshot_sha256=digest,
            live=args.live,
            runtime_receipt=receipt,
        )
    except RuntimeProofError as exc:
        print(f"verified workflow runtime proof failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(proof, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
