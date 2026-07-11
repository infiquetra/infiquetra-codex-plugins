#!/usr/bin/env python3
"""Capture minimal prompt-free SubagentStart and SubagentStop receipts."""

from __future__ import annotations

import datetime as dt
import errno
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

MAX_HOOK_BYTES = 64 * 1024
MAX_PROFILE_BYTES = 1024 * 1024
PROFILE_TYPES = frozenset(
    {"review_max", "review_high", "test_medium", "scan_low", "monitor_low"}
)
EVENTS = {"SubagentStart": "start", "SubagentStop": "stop"}
PERMISSION_MODES = {"default", "acceptEdits", "plan", "dontAsk", "bypassPermissions"}
RECEIPT_PERMISSION_MODES = frozenset({"default", "plan"})
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
MANAGED_MARKER = '# managed_by = "infiquetra-codex-plugins/verified-workflows"'
COMMON_FIELDS = {
    "session_id",
    "transcript_path",
    "cwd",
    "hook_event_name",
    "model",
    "permission_mode",
    "turn_id",
    "agent_id",
    "agent_type",
}
STOP_FIELDS = {"agent_transcript_path", "stop_hook_active", "last_assistant_message"}
PLUGIN_ROOT = Path(__file__).resolve().parent.parent


class AgentReceiptError(RuntimeError):
    """Raised when a hook event cannot be captured without widening trust."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _safe_text(value: object, where: str) -> str:
    if not isinstance(value, str) or not SAFE_IDENTIFIER.fullmatch(value):
        raise AgentReceiptError(f"{where} is not a safe identifier")
    return value


def _assert_no_symlink_components(path: Path) -> None:
    if not path.is_absolute():
        raise AgentReceiptError("receipt paths must be absolute")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise AgentReceiptError(f"path component is unreadable (errno {exc.errno})") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise AgentReceiptError("receipt paths must not contain symlink components")


def _read_regular(path: Path, where: str, limit: int) -> bytes:
    if not path.is_absolute() or path.name in {"", ".", ".."}:
        raise AgentReceiptError(f"{where} path must be absolute")
    directory_flags = _directory_flags()
    directory_fd = os.open(path.anchor, directory_flags)
    try:
        for part in path.parts[1:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path.name, flags, dir_fd=directory_fd)
    except OSError as exc:
        os.close(directory_fd)
        raise AgentReceiptError(f"{where} is unreadable (errno {exc.errno})") from exc
    os.close(directory_fd)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_uid != os.getuid()
            or before.st_mode & 0o022
        ):
            raise AgentReceiptError(
                f"{where} must be a single-link, user-owned, non-writable regular file"
            )
        if before.st_size > limit:
            raise AgentReceiptError(f"{where} exceeds the byte ceiling")
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
        if len(content) > limit or len(content) != after.st_size:
            raise AgentReceiptError(f"{where} exceeds the byte ceiling or changed")
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise AgentReceiptError(f"{where} changed while it was read")
        return content
    finally:
        os.close(descriptor)


def _profile_receipt(agent_type: str, model: str, codex_home: Path) -> str:
    if not codex_home.is_absolute():
        raise AgentReceiptError("CODEX_HOME must be absolute")
    profile = codex_home / "agents" / f"{agent_type}.toml"
    try:
        profile.resolve(strict=False).relative_to((codex_home / "agents").resolve(strict=False))
    except ValueError as exc:
        raise AgentReceiptError("profile path escapes the Codex agents directory") from exc
    content = _read_regular(profile, "selected profile", MAX_PROFILE_BYTES)
    try:
        text = content.decode("utf-8")
        payload = tomllib.loads(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise AgentReceiptError("selected profile is invalid TOML") from exc
    if MANAGED_MARKER not in text.splitlines()[:8]:
        raise AgentReceiptError("selected profile does not carry the Verified Workflows marker")
    expected_fields = {
        "name",
        "description",
        "model",
        "model_reasoning_effort",
        "sandbox_mode",
        "developer_instructions",
        "nickname_candidates",
    }
    if set(payload) != expected_fields:
        raise AgentReceiptError("selected profile fields are not closed")
    if payload.get("name") != agent_type or payload.get("model") != model:
        raise AgentReceiptError("hook agent type/model does not match the installed profile")
    effort = payload.get("model_reasoning_effort")
    sandbox = payload.get("sandbox_mode")
    if not isinstance(effort, str) or not isinstance(sandbox, str):
        raise AgentReceiptError("selected profile effort/sandbox fields are invalid")
    return _sha256(content)


def _codex_home_sha256(codex_home: Path) -> str:
    _assert_no_symlink_components(codex_home)
    try:
        resolved = codex_home.resolve(strict=True)
        metadata = resolved.stat()
    except OSError as exc:
        raise AgentReceiptError("CODEX_HOME is missing or unreadable") from exc
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
        raise AgentReceiptError("CODEX_HOME must be a user-owned real directory")
    return _sha256(str(resolved).encode())


def _hook_identity() -> tuple[str, str]:
    definition = _read_regular(
        PLUGIN_ROOT / "hooks" / "hooks.json", "hook definition", MAX_PROFILE_BYTES
    )
    handler = _read_regular(Path(__file__), "hook handler", MAX_PROFILE_BYTES)
    return _sha256(definition), _sha256(handler)


def normalize_event(
    payload: object,
    *,
    codex_home: Path,
    now: Callable[[], str] = _utc_now,
) -> dict[str, Any]:
    """Reduce one official hook payload to the closed prompt-free receipt schema."""

    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise AgentReceiptError("hook input must be a JSON object")
    event = payload.get("hook_event_name")
    if event not in EVENTS:
        raise AgentReceiptError("hook event is not SubagentStart or SubagentStop")
    allowed = COMMON_FIELDS | (STOP_FIELDS if event == "SubagentStop" else set())
    unknown = set(payload) - allowed
    if unknown:
        raise AgentReceiptError(f"hook input contains unsupported fields {sorted(unknown)}")
    required = {
        "session_id",
        "transcript_path",
        "cwd",
        "hook_event_name",
        "model",
        "permission_mode",
        "turn_id",
        "agent_id",
        "agent_type",
    }
    missing = required - set(payload)
    if missing:
        raise AgentReceiptError(f"hook input is missing fields {sorted(missing)}")
    if payload["transcript_path"] is not None and not isinstance(
        payload["transcript_path"], str
    ):
        raise AgentReceiptError("transcript_path has the wrong scalar type")
    if not isinstance(payload["cwd"], str):
        raise AgentReceiptError("cwd has the wrong scalar type")
    if event == "SubagentStop":
        missing_stop = STOP_FIELDS - set(payload)
        if missing_stop:
            raise AgentReceiptError(f"stop hook input is missing fields {sorted(missing_stop)}")
        if payload["agent_transcript_path"] is not None and not isinstance(
            payload["agent_transcript_path"], str
        ):
            raise AgentReceiptError("agent_transcript_path has the wrong scalar type")
        if payload["last_assistant_message"] is not None and not isinstance(
            payload["last_assistant_message"], str
        ):
            raise AgentReceiptError("last_assistant_message has the wrong scalar type")
        if not isinstance(payload["stop_hook_active"], bool):
            raise AgentReceiptError("stop_hook_active has the wrong scalar type")
    session_id = _safe_text(payload["session_id"], "session_id")
    turn_id = _safe_text(payload["turn_id"], "turn_id")
    child_id = _safe_text(payload["agent_id"], "agent_id")
    agent_type = _safe_text(payload["agent_type"], "agent_type")
    model = _safe_text(payload["model"], "model")
    permission_mode = payload["permission_mode"]
    if agent_type not in PROFILE_TYPES:
        raise AgentReceiptError("agent_type is not a managed execution profile")
    if permission_mode not in PERMISSION_MODES:
        raise AgentReceiptError("permission_mode is not a current Codex value")
    if permission_mode not in RECEIPT_PERMISSION_MODES:
        raise AgentReceiptError(
            "permission_mode is too broad for workflow receipt evidence"
        )
    profile_sha256 = _profile_receipt(agent_type, model, codex_home)
    codex_home_sha256 = _codex_home_sha256(codex_home)
    hook_definition_sha256, hook_handler_sha256 = _hook_identity()
    return {
        "schema_version": 1,
        "event": EVENTS[str(event)],
        "parent_session_id": session_id,
        "turn_id": turn_id,
        "child_id": child_id,
        "agent_type": agent_type,
        "active_model": model,
        "permission_mode": permission_mode,
        "codex_home_sha256": codex_home_sha256,
        "profile_sha256": profile_sha256,
        "hook_definition_sha256": hook_definition_sha256,
        "hook_handler_sha256": hook_handler_sha256,
        "observed_at": now(),
    }


def _directory_flags() -> int:
    return os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)


def _validate_directory(descriptor: int, where: str, *, private: bool) -> None:
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
        raise AgentReceiptError(f"{where} must be a user-owned real directory")
    if metadata.st_mode & 0o022:
        raise AgentReceiptError(f"{where} must not be group/world writable")
    if private and stat.S_IMODE(metadata.st_mode) != 0o700:
        raise AgentReceiptError(f"{where} must have mode 0700")


def _open_plugin_data(plugin_data: Path) -> int:
    if not plugin_data.is_absolute():
        raise AgentReceiptError("PLUGIN_DATA must be absolute")
    descriptor = os.open(plugin_data.anchor, _directory_flags())
    try:
        parts = plugin_data.parts[1:]
        for index, part in enumerate(parts):
            try:
                next_fd = os.open(part, _directory_flags(), dir_fd=descriptor)
            except FileNotFoundError:
                if index != len(parts) - 1:
                    raise
                try:
                    os.mkdir(part, 0o700, dir_fd=descriptor)
                    os.fsync(descriptor)
                except FileExistsError:
                    pass
                next_fd = os.open(part, _directory_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_fd
    except OSError as exc:
        os.close(descriptor)
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise AgentReceiptError(
                "PLUGIN_DATA must not contain symlinks or non-directories"
            ) from exc
        raise AgentReceiptError(f"PLUGIN_DATA is unreadable (errno {exc.errno})") from exc
    try:
        _validate_directory(descriptor, "PLUGIN_DATA", private=False)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_private_child(parent_fd: int, name: str) -> int:
    _safe_text(name, "receipt directory name")
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except FileExistsError:
        pass
    except OSError as exc:
        raise AgentReceiptError(f"receipt directory cannot be created (errno {exc.errno})") from exc
    try:
        descriptor = os.open(name, _directory_flags(), dir_fd=parent_fd)
    except OSError as exc:
        raise AgentReceiptError(f"receipt directory is unreadable (errno {exc.errno})") from exc
    try:
        _validate_directory(descriptor, "receipt directory", private=True)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_at(directory_fd: int, name: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise AgentReceiptError(f"existing receipt is unreadable (errno {exc.errno})") from exc
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_size > MAX_HOOK_BYTES
        ):
            raise AgentReceiptError("existing receipt has unsafe metadata")
        chunks: list[bytes] = []
        remaining = MAX_HOOK_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            len(content) != metadata.st_size
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
            raise AgentReceiptError("existing receipt changed while it was read")
        return content
    finally:
        os.close(descriptor)


def _write_once(directory_fd: int, name: str, content: bytes) -> None:
    temporary = f".{name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    lock_name = ".receipt.lock"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    lock_flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    lock_fd = os.open(lock_name, lock_flags, 0o600, dir_fd=directory_fd)
    try:
        os.fchmod(lock_fd, 0o600)
        lock_metadata = os.fstat(lock_fd)
        if (
            not stat.S_ISREG(lock_metadata.st_mode)
            or lock_metadata.st_nlink != 1
            or lock_metadata.st_uid != os.getuid()
            or stat.S_IMODE(lock_metadata.st_mode) != 0o600
        ):
            raise AgentReceiptError("receipt lock has unsafe metadata")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            existing = _read_at(directory_fd, name)
        except FileNotFoundError:
            existing = None
        if existing is not None:
            if existing != content:
                raise AgentReceiptError("duplicate hook event conflicts with existing receipt")
            return
        descriptor = os.open(temporary, flags, 0o600, dir_fd=directory_fd)
        try:
            os.fchmod(descriptor, 0o600)
            view = memoryview(content)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise AgentReceiptError("receipt write made no progress")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.rename(
            temporary,
            name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        os.fsync(directory_fd)
    finally:
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def persist_event(receipt: Mapping[str, Any], plugin_data: Path) -> None:
    """Persist one raw event under a contained per-session/per-child directory."""

    content = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(content) > MAX_HOOK_BYTES:
        raise AgentReceiptError("normalized hook receipt exceeds the byte ceiling")
    root_fd = _open_plugin_data(plugin_data)
    descriptors = [root_fd]
    try:
        current = root_fd
        for part in (
            "receipts",
            "v1",
            "raw",
            _sha256(str(receipt["parent_session_id"]).encode()),
            _sha256(str(receipt["child_id"]).encode()),
            _sha256(str(receipt["turn_id"]).encode()),
        ):
            current = _open_private_child(current, part)
            descriptors.append(current)
        name = f"{receipt['event']}.json"
        try:
            _write_once(current, name, content)
        except AgentReceiptError as exc:
            try:
                existing = json.loads(_read_at(current, name))
            except (AgentReceiptError, UnicodeDecodeError, json.JSONDecodeError):
                raise exc
            expected_projection = {
                key: value for key, value in receipt.items() if key != "observed_at"
            }
            existing_projection = {
                key: value for key, value in existing.items() if key != "observed_at"
            }
            if existing_projection != expected_projection:
                raise exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _read_stdin() -> object:
    content = sys.stdin.buffer.read(MAX_HOOK_BYTES + 1)
    if len(content) > MAX_HOOK_BYTES:
        raise AgentReceiptError("hook input exceeds 64 KiB")
    try:
        return json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgentReceiptError("hook input is not valid UTF-8 JSON") from exc


def main() -> int:
    try:
        plugin_data_raw = os.environ.get("PLUGIN_DATA")
        if not plugin_data_raw:
            raise AgentReceiptError("PLUGIN_DATA is required")
        plugin_data = Path(plugin_data_raw)
        if not plugin_data.is_absolute():
            raise AgentReceiptError("PLUGIN_DATA must be absolute")
        codex_home_raw = os.environ.get("CODEX_HOME")
        codex_home = Path(codex_home_raw) if codex_home_raw else Path.home() / ".codex"
        if not codex_home.is_absolute():
            raise AgentReceiptError("CODEX_HOME must be absolute")
        receipt = normalize_event(_read_stdin(), codex_home=codex_home)
        persist_event(receipt, plugin_data)
    except (AgentReceiptError, OSError) as exc:
        print(f"verified workflow hook receipt failed: {exc}", file=sys.stderr)
        return 1
    if receipt["event"] == "stop":
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
