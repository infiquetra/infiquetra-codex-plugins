#!/usr/bin/env python3
"""Characterize or attest the Verified Workflows runtime boundary safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugins" / "verified-workflows"
PLUGIN_SCRIPTS = PLUGIN_ROOT / "scripts"
if str(PLUGIN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PLUGIN_SCRIPTS))

import render_codex_agents as renderer  # noqa: E402

DEFAULT_SNAPSHOT = REPO_ROOT / "docs" / "validation" / "codex-runtime-capability-snapshot.json"
PROJECT_AGENTS = REPO_ROOT / ".codex" / "agents"
MAX_BYTES = 4 * 1024 * 1024
SECRET_KEY = re.compile(r"(?i)(token|secret|password|credential|authorization|api[_-]?key|auth_json)")
SECRET_VALUE = re.compile(
    r"(?i)(?:\bsk-[A-Za-z0-9_-]{8,}|\bgh[pousr]_[A-Za-z0-9]{8,}|"
    r"\bBearer\s+[A-Za-z0-9._~-]{8,}|\beyJ[A-Za-z0-9_-]{8,}\."
    r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})"
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ROOT_TASK_REF = re.compile(r"^root-task:[0-9a-f]{64}$")


class RuntimeProofError(RuntimeError):
    """Raised when proof inputs could leak secrets or overstate runtime capability."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_regular(path: Path, where: str, limit: int = MAX_BYTES) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RuntimeProofError(f"{where} is unreadable") from exc
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size > limit
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
            or len(content) != metadata.st_size
            or (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_size,
                metadata.st_mtime_ns,
            )
            != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            )
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


def _assert_no_symlink_components(path: Path) -> None:
    if not path.is_absolute():
        raise RuntimeProofError("isolated CODEX_HOME must be absolute")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise RuntimeProofError("isolated CODEX_HOME is unreadable") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise RuntimeProofError("isolated CODEX_HOME must be symlink-free")


def _reject_default_profile_input(path: Path, where: str) -> None:
    default = (Path.home() / ".codex").resolve(strict=False)
    candidate = path.expanduser().resolve(strict=False)
    if candidate == default or default in candidate.parents:
        raise RuntimeProofError(f"{where} must not read from the default Codex profile tree")


def _validate_isolated_home(path: Path) -> bool:
    _assert_no_symlink_components(path)
    default = (Path.home() / ".codex").resolve(strict=False)
    candidate = path.resolve(strict=False)
    if candidate == default or candidate in default.parents or default in candidate.parents:
        raise RuntimeProofError("live proof refuses the default Codex profile tree")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        raise RuntimeProofError("live proof requires an existing isolated CODEX_HOME") from None
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_mode & 0o022
    ):
        raise RuntimeProofError("isolated CODEX_HOME must be a user-owned safe directory")
    auth_path = path / "auth.json"
    try:
        auth = auth_path.lstat()
    except FileNotFoundError:
        return False
    if (
        not stat.S_ISREG(auth.st_mode)
        or auth.st_nlink != 1
        or auth.st_uid != os.getuid()
        or auth.st_mode & 0o077
    ):
        raise RuntimeProofError("isolated authentication metadata is unsafe")
    return auth.st_size > 0


def _snapshot_projection(snapshot: dict[str, Any]) -> dict[str, Any]:
    runtime = snapshot.get("runtime")
    collaboration = snapshot.get("collaboration")
    hooks = snapshot.get("hook_capabilities")
    if not isinstance(runtime, dict) or not isinstance(collaboration, dict) or not isinstance(
        hooks, dict
    ):
        raise RuntimeProofError("capability snapshot lacks required closed sections")
    version = runtime.get("codex_cli_version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9A-Za-z.+-]{1,32}", version):
        raise RuntimeProofError("capability snapshot Codex version is invalid")
    spawn = collaboration.get("spawn")
    expected_spawn_fields = {
        "available",
        "tool_namespace",
        "hide_spawn_agent_metadata",
        "request_fields",
        "default_fork_turns",
        "profile_selection_fork_turns",
        "per_child_agent_type",
        "per_child_model",
        "per_child_effort",
        "per_child_sandbox",
        "selection_readback_fields",
    }
    if not isinstance(spawn, dict) or set(spawn) != expected_spawn_fields:
        raise RuntimeProofError("capability snapshot spawn schema is not closed")
    boolean_fields = {
        "available",
        "per_child_agent_type",
        "per_child_model",
        "per_child_effort",
        "per_child_sandbox",
    }
    if any(not isinstance(spawn[field], bool) for field in boolean_fields):
        raise RuntimeProofError("capability snapshot spawn booleans are invalid")
    request_fields = spawn["request_fields"]
    readback_fields = spawn["selection_readback_fields"]
    if spawn["tool_namespace"] != "agents" or spawn["hide_spawn_agent_metadata"] is not False:
        raise RuntimeProofError("capability snapshot named-profile bootstrap drifted")
    if request_fields != [
        "agent_type",
        "fork_turns",
        "message",
        "model",
        "reasoning_effort",
        "service_tier",
        "task_name",
    ]:
        raise RuntimeProofError("capability snapshot spawn request fields drifted")
    if spawn["default_fork_turns"] != "all" or spawn[
        "profile_selection_fork_turns"
    ] != ["none", "positive-integer"]:
        raise RuntimeProofError("capability snapshot profile-selection fork contract drifted")
    if not isinstance(readback_fields, list) or any(
        value not in {"agent_type", "model", "effort", "sandbox_mode"}
        for value in readback_fields
    ):
        raise RuntimeProofError("capability snapshot selection readback fields are invalid")
    expected_hook_fields = {
        "plugin_hooks_supported",
        "trust_required",
        "writable_data_environment",
        "subagent_event_allowlist",
        "observes_active_model",
        "observes_agent_type",
        "observes_reasoning_effort",
    }
    if set(hooks) != expected_hook_fields:
        raise RuntimeProofError("capability snapshot hook schema is not closed")
    if hooks["subagent_event_allowlist"] != ["SubagentStart", "SubagentStop"]:
        raise RuntimeProofError("capability snapshot hook events drifted")
    if hooks["writable_data_environment"] != "PLUGIN_DATA" or any(
        not isinstance(hooks[field], bool)
        for field in (
            "plugin_hooks_supported",
            "trust_required",
            "observes_active_model",
            "observes_agent_type",
            "observes_reasoning_effort",
        )
    ):
        raise RuntimeProofError("capability snapshot hook capabilities are invalid")
    return {"version": version, "spawn": spawn, "hooks": hooks}


def _contained_relative(root: Path, value: object, where: str) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith(("/", "~"))
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or not re.fullmatch(r"[A-Za-z0-9._/-]+", value)
    ):
        raise RuntimeProofError(f"{where} is not a safe relative path")
    candidate = root / value
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise RuntimeProofError(f"{where} escapes the isolated home") from exc
    return candidate


def _validate_installed_readback(
    codex_home: Path,
    install: object,
) -> None:
    if not isinstance(install, dict) or set(install) != {
        "plugin_root",
        "agents_root",
    }:
        raise RuntimeProofError("live envelope install fields are not closed")
    installed_plugin = _contained_relative(
        codex_home, install["plugin_root"], "installed plugin root"
    )
    installed_agents = _contained_relative(
        codex_home, install["agents_root"], "installed agents root"
    )
    for relative in (Path("hooks/hooks.json"), Path("hooks/agent_receipt.py")):
        if _read_regular(
            installed_plugin / relative, "installed hook readback"
        ) != _read_regular(PLUGIN_ROOT / relative, "source hook readback"):
            raise RuntimeProofError("installed hook bytes do not match the source package")
    for fact in _profile_facts():
        filename = f"{fact['runtime_agent_name']}.toml"
        if _read_regular(
            installed_agents / filename, "installed profile readback"
        ) != _read_regular(
            PLUGIN_ROOT / "agents" / filename, "source profile readback"
        ):
            raise RuntimeProofError("installed profile bytes do not match the source package")


def build_live_envelope(codex_home: Path, task_ref: str) -> dict[str, Any]:
    """Record root-mediated fresh-task fallback plus isolated installed-byte readback."""

    if not _validate_isolated_home(codex_home):
        raise RuntimeProofError(
            "live envelope production requires separately established isolated login metadata"
        )
    if not isinstance(task_ref, str) or ROOT_TASK_REF.fullmatch(task_ref) is None:
        raise RuntimeProofError("live envelope requires a protected root task reference")
    install = {
        "plugin_root": "plugins/verified-workflows",
        "agents_root": "agents",
    }
    _validate_installed_readback(codex_home, install)
    envelope = {
        "schema_version": 1,
        "claim": "root-accountability-fresh-session",
        "install": install,
        "fresh_task": {
            "spawn_surface": "generic",
            "outcome": "inline-only",
            "task_ref": task_ref,
        },
    }
    validate_sanitized_proof(envelope, "live_envelope")
    return envelope


def _load_live_envelope(path: Path, codex_home: Path) -> tuple[dict[str, Any], str]:
    _reject_default_profile_input(path, "live envelope")
    _validate_isolated_home(codex_home)
    envelope, digest = _load_json(path, "live envelope")
    if set(envelope) != {"schema_version", "claim", "install", "fresh_task"}:
        raise RuntimeProofError("live envelope fields are not closed")
    if (
        envelope["schema_version"] != 1
        or envelope["claim"] != "root-accountability-fresh-session"
    ):
        raise RuntimeProofError("live envelope identity is invalid")
    install = envelope["install"]
    _validate_installed_readback(codex_home, install)
    fresh_task = envelope["fresh_task"]
    if (
        not isinstance(fresh_task, dict)
        or set(fresh_task) != {"spawn_surface", "outcome", "task_ref"}
        or fresh_task["spawn_surface"] != "generic"
        or fresh_task["outcome"] != "inline-only"
        or not isinstance(fresh_task["task_ref"], str)
        or ROOT_TASK_REF.fullmatch(fresh_task["task_ref"]) is None
    ):
        raise RuntimeProofError("live envelope fresh task is invalid")
    validate_sanitized_proof(envelope, "live_envelope")
    return envelope, digest


def _profile_facts() -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    for execution_class, runtime_agent_name in renderer.RUNTIME_AGENT_NAMES.items():
        path = PLUGIN_ROOT / "agents" / f"{runtime_agent_name}.toml"
        content = _read_regular(path, "managed profile", 1024 * 1024)
        facts.append(
            {
                "execution_class": execution_class,
                "runtime_agent_name": runtime_agent_name,
                "sha256": _sha256(content),
            }
        )
    if len(facts) != 5:
        raise RuntimeProofError("managed profile source must contain exactly five profiles")
    return facts


def _project_agent_facts() -> dict[str, Any]:
    """Prove project discovery files are regular and byte-identical to plugin source."""

    expected = {
        f"{runtime_name}.toml"
        for runtime_name in renderer.RUNTIME_AGENT_NAMES.values()
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
            PROJECT_AGENTS / filename,
            "project agent discovery profile",
            1024 * 1024,
        )
        source_content = _read_regular(
            PLUGIN_ROOT / "agents" / filename,
            "source agent profile",
            1024 * 1024,
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


def build_proof(
    *,
    snapshot: dict[str, Any],
    snapshot_sha256: str,
    live: bool,
    codex_home: Path | None,
    authenticated_isolated_home: bool,
    live_envelope: tuple[dict[str, Any], str] | None = None,
) -> dict[str, Any]:
    projection = _snapshot_projection(snapshot)
    spawn = projection["spawn"]
    hooks = projection["hooks"]
    if spawn.get("available") is not True:
        spawn_surface = "absent"
    elif spawn.get("per_child_agent_type") is True:
        spawn_surface = "named"
    else:
        spawn_surface = "generic"
    login_metadata_present: bool | None = None
    if live:
        if codex_home is None:
            raise RuntimeProofError("--live requires an explicit isolated --codex-home")
        login_metadata_present = _validate_isolated_home(codex_home)
        if login_metadata_present and not authenticated_isolated_home:
            raise RuntimeProofError(
                "isolated login metadata requires an explicit operator acknowledgement"
            )
    elif codex_home is not None or authenticated_isolated_home or live_envelope is not None:
        raise RuntimeProofError("isolated-home arguments require --live")
    if live and login_metadata_present is False:
        outcome = "auth-unavailable"
        reason = "isolated home has no separately established login"
        if live_envelope is not None:
            raise RuntimeProofError("auth-unavailable proof cannot consume a live envelope")
    elif live:
        if live_envelope is None:
            raise RuntimeProofError(
                "authenticated --live requires an isolated install readback envelope"
            )
        _envelope, _envelope_sha = live_envelope
        outcome = "inline-only"
        reason = (
            "isolated installed bytes were read back; no host-attested fresh task was performed"
        )
    elif spawn_surface != "named":
        outcome = "inline-only"
        reason = (
            "active collaboration spawn schema lacks agent_type and selection readback"
        )
    else:
        outcome = "diagnostic"
        reason = (
            "configured named-profile selection is available; tracked characterization carries "
            "no live child receipt"
        )
    hook_content = _read_regular(PLUGIN_ROOT / "hooks" / "hooks.json", "hook definition")
    hook_handler = _read_regular(
        PLUGIN_ROOT / "hooks" / "agent_receipt.py", "hook handler"
    )
    registry_content = _read_regular(
        PLUGIN_ROOT / "config" / "role-registry.yaml", "role registry"
    )
    envelope_sha256 = live_envelope[1] if live_envelope is not None else None
    proof = {
        "schema_version": 1,
        "claim": "runtime-capability-characterization",
        "harness_sha256": _sha256(_read_regular(Path(__file__), "runtime proof harness")),
        "mode": (
            "isolated-readback"
            if live_envelope is not None
            else "live-preflight"
            if live
            else "dry-run"
        ),
        "capability_outcome": outcome,
        "reason": reason,
        "snapshot_sha256": snapshot_sha256,
        "codex_cli_version": projection["version"],
        "spawn_surface": spawn_surface,
        "spawn_request_fields": spawn.get("request_fields", []),
        "hook_capabilities": {
            "events": hooks.get("subagent_event_allowlist", []),
            "observes_active_model": hooks.get("observes_active_model"),
            "observes_agent_type": hooks.get("observes_agent_type"),
            "observes_reasoning_effort": hooks.get("observes_reasoning_effort"),
            "trust_required": hooks.get("trust_required"),
            "trust_readback": "unobserved",
            "installed_bytes_readback": live_envelope is not None,
            "definition_sha256": _sha256(hook_content),
            "handler_sha256": _sha256(hook_handler),
        },
        "role_registry_sha256": _sha256(registry_content),
        "profiles": _profile_facts(),
        "project_discovery": _project_agent_facts(),
        "live_invocation_performed": False,
        "root_mediated_task_reported": False,
        "isolated_login_metadata_present": login_metadata_present,
        "live_envelope_sha256": envelope_sha256,
        "runtime_receipt_ref": None,
        "runtime_receipt_sha256": None,
        "limitations": [
            "project profile discovery is expected configuration, not runtime selection",
            "hook permission_mode is not effective sandbox_mode",
            "reasoning effort is expected from the exact profile digest, not observed by hooks",
            "profile-selected work requires agent_type with fork_turns none or a positive integer",
            "tracked characterization does not contain a live child turn_context receipt",
            "isolated readback proves bytes only; it does not prove hook trust or task execution",
        ],
    }
    validate_sanitized_proof(proof)
    return proof


def validate_sanitized_proof(
    payload: object, path: str = "proof", depth: int = 0
) -> None:
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
            payload.startswith(("/", "~", "file:"))
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--authenticated-isolated-home", action="store_true")
    parser.add_argument("--live-envelope", type=Path)
    parser.add_argument("--emit-live-envelope", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.emit_live_envelope:
            if (
                args.codex_home is None
                or args.live
                or args.live_envelope is not None
                or args.authenticated_isolated_home
            ):
                raise RuntimeProofError(
                    "envelope production requires only --codex-home"
                )
            output = build_live_envelope(args.codex_home)
            print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
            return 0
        _reject_default_profile_input(args.snapshot, "capability snapshot")
        if args.live_envelope is not None:
            _reject_default_profile_input(args.live_envelope, "live envelope")
        if args.codex_home is not None:
            _validate_isolated_home(args.codex_home)
        snapshot, digest = _load_json(args.snapshot, "capability snapshot")
        live_envelope = (
            _load_live_envelope(args.live_envelope, args.codex_home)
            if args.live_envelope and args.codex_home is not None
            else None
        )
        if args.live_envelope is not None and args.codex_home is None:
            raise RuntimeProofError("--live-envelope requires --codex-home")
        proof = build_proof(
            snapshot=snapshot,
            snapshot_sha256=digest,
            live=args.live,
            codex_home=args.codex_home,
            authenticated_isolated_home=args.authenticated_isolated_home,
            live_envelope=live_envelope,
        )
    except RuntimeProofError as exc:
        print(f"verified workflow runtime proof failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(proof, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
