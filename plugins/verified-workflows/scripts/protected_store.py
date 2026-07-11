#!/usr/bin/env python3
"""Protected storage and shared receipt validation primitives."""

# ruff: noqa: F401 -- selected standard-library names support the compatibility facade.

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import re
import secrets
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

SCRIPTS_DIR = Path(__file__).resolve().parent
HOOKS_DIR = SCRIPTS_DIR.parent / "hooks"
for directory in (SCRIPTS_DIR, HOOKS_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import agent_receipt as hook_receipt  # noqa: E402
import workflow_dispatch as dispatch  # noqa: E402

RAW_FIELDS = {
    "schema_version",
    "event",
    "parent_session_id",
    "turn_id",
    "child_id",
    "agent_type",
    "active_model",
    "permission_mode",
    "codex_home_sha256",
    "profile_sha256",
    "hook_definition_sha256",
    "hook_handler_sha256",
    "observed_at",
}
MAX_RECEIPT_BYTES = 64 * 1024
MAX_PROTECTED_RECORD_BYTES = 2 * 1024 * 1024
MAX_EVENT_AGE_SECONDS = 24 * 60 * 60
MAX_SUBJECT_PATHS = 64
MAX_SUBJECT_FILES = 128
MAX_SUBJECT_PATH_BYTES = 16 * 1024
MAX_SUBJECT_ANCESTRY = 1024
MAX_SUBJECT_BYTES = 64 * 1024 * 1024
MAX_AUDIT_FILES = 250000
MAX_AUDIT_BYTES = 1024 * 1024 * 1024
HEX64 = re.compile(r"^[0-9a-f]{64}$")
GIT_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
SAFE_REF = re.compile(r"^[a-z0-9][a-z0-9._:/-]{0,127}$")
SAFE_RUNTIME_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
SECRET_KEY = re.compile(
    r"(?i)(token|secret|password|credential|authorization|api[_-]?key|auth_json)"
)
SECRET_VALUE = re.compile(
    r"(?i)(?:\bsk-[A-Za-z0-9_-]{8,}|\bgh[pousr]_[A-Za-z0-9]{8,}|"
    r"\bBearer\s+[A-Za-z0-9._~-]{8,}|\beyJ[A-Za-z0-9_-]{8,}\."
    r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|\bAKIA[0-9A-Z]{16}\b|"
    r"-----BEGIN(?: [A-Z0-9]+)* PRIVATE KEY-----|"
    r"\bBasic\s+[A-Za-z0-9+/=]{8,}|"
    r"[A-Za-z][A-Za-z0-9+.-]*://[^/\s:@]+:[^@\s/]+@|"
    r"\b(?:password|passwd|pwd|cookie|set-cookie)\s*[:=]\s*\S{4,})"
)
RECORD_KINDS = {
    "workflow-run",
    "intent",
    "hook-trust",
    "native-launch",
    "role-result",
    "root-verification",
    "resolution",
    "subject",
    "workspace-snapshot",
    "mutation-audit",
    "git-baseline",
    "command-output",
    "raw-abandonment",
}
LARGE_RECORD_KINDS = {"workflow-run", "subject", "git-baseline", "command-output"}


class DispatchReceiptError(RuntimeError):
    """Raised when an execution chain cannot support a truthful vehicle receipt."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _parse_time(value: object, where: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DispatchReceiptError(f"{where} must be a UTC timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DispatchReceiptError(f"{where} is invalid") from exc
    if parsed.tzinfo != dt.UTC:
        parsed = parsed.astimezone(dt.UTC)
    return parsed


def _safe(value: object, where: str) -> str:
    if (
        not isinstance(value, str)
        or not SAFE_REF.fullmatch(value)
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise DispatchReceiptError(f"{where} is invalid")
    return value


def _runtime_id(value: object, where: str) -> str:
    if not isinstance(value, str) or not SAFE_RUNTIME_ID.fullmatch(value):
        raise DispatchReceiptError(f"{where} is invalid")
    return value


def _attempt(value: object, where: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= dispatch.MAX_CYCLES
    ):
        raise DispatchReceiptError(f"{where} is outside the remediation-cycle range")
    return value


def _hash_segment(value: str) -> str:
    return _sha256(value.encode())


def _open_existing_chain(plugin_data: Path, parts: tuple[str, ...]) -> list[int]:
    try:
        root = hook_receipt._open_plugin_data(plugin_data)
    except hook_receipt.AgentReceiptError as exc:
        raise DispatchReceiptError("plugin data root is missing or unsafe") from exc
    descriptors = [root]
    current = root
    try:
        for part in parts:
            try:
                current = os.open(part, hook_receipt._directory_flags(), dir_fd=current)
            except FileNotFoundError:
                raise
            except OSError as exc:
                raise DispatchReceiptError("required protected receipt directory is missing") from exc
            hook_receipt._validate_directory(current, "protected receipt directory", private=True)
            descriptors.append(current)
        return descriptors
    except hook_receipt.AgentReceiptError as exc:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise DispatchReceiptError("protected receipt directory is unsafe") from exc
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _read_at_bounded(directory_fd: int, name: str, where: str, limit: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise DispatchReceiptError(f"{where} is missing or unsafe") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_uid != os.getuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_size > limit
        ):
            raise DispatchReceiptError(f"{where} has unsafe metadata")
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
            raise DispatchReceiptError(f"{where} changed while it was read")
        return content
    finally:
        os.close(descriptor)


def _load_json_at(
    directory_fd: int,
    name: str,
    where: str,
    limit: int = MAX_RECEIPT_BYTES,
) -> tuple[dict[str, Any], bytes]:
    try:
        content = _read_at_bounded(directory_fd, name, where, limit)
    except hook_receipt.AgentReceiptError as exc:
        raise DispatchReceiptError(f"{where} is missing or unsafe") from exc
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DispatchReceiptError(f"{where} is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise DispatchReceiptError(f"{where} must be an object")
    return payload, content


def load_raw_pair(
    plugin_data: Path,
    *,
    parent_session_id: str,
    child_id: str,
    turn_id: str,
) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    """Load one exact raw pair without accepting a path from hook data."""

    parts = (
        "receipts",
        "v1",
        "raw",
        _hash_segment(parent_session_id),
        _hash_segment(child_id),
        _hash_segment(turn_id),
    )
    descriptors = _open_existing_chain(plugin_data, parts)
    try:
        start, start_bytes = _load_json_at(descriptors[-1], "start.json", "start receipt")
        stop, stop_bytes = _load_json_at(descriptors[-1], "stop.json", "stop receipt")
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    return start, stop, start_bytes, stop_bytes


def _validate_raw_event(
    event: object,
    expected: str,
    *,
    parent_session_id: str,
    child_id: str,
    turn_id: str,
) -> dict[str, Any]:
    if not isinstance(event, dict) or set(event) != RAW_FIELDS:
        raise DispatchReceiptError(f"raw {expected} receipt fields are not closed")
    if event["schema_version"] != 1 or event["event"] != expected:
        raise DispatchReceiptError(f"raw {expected} receipt identity is invalid")
    bindings = {
        "parent_session_id": parent_session_id,
        "child_id": child_id,
        "turn_id": turn_id,
    }
    if any(event[field] != value for field, value in bindings.items()):
        raise DispatchReceiptError(f"raw {expected} receipt identity does not match the join")
    for field in ("parent_session_id", "child_id", "turn_id"):
        _runtime_id(event[field], f"raw {expected}.{field}")
    for field in ("agent_type", "active_model"):
        _safe(event[field], f"raw {expected}.{field}")
    if event["permission_mode"] not in hook_receipt.PERMISSION_MODES:
        raise DispatchReceiptError(f"raw {expected}.permission_mode is invalid")
    for field in (
        "codex_home_sha256",
        "profile_sha256",
        "hook_definition_sha256",
        "hook_handler_sha256",
    ):
        if not isinstance(event[field], str) or not HEX64.fullmatch(event[field]):
            raise DispatchReceiptError(f"raw {expected}.{field} is invalid")
    _parse_time(event["observed_at"], f"raw {expected}.observed_at")
    return event


def _validate_raw_bytes(event: Mapping[str, Any], content: bytes, where: str) -> None:
    if len(content) > hook_receipt.MAX_HOOK_BYTES:
        raise DispatchReceiptError(f"{where} exceeds the raw receipt byte ceiling")
    try:
        decoded = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DispatchReceiptError(f"{where} bytes are not valid JSON") from exc
    if decoded != event or content != _canonical_bytes(event):
        raise DispatchReceiptError(f"{where} bytes do not bind the normalized event")


def _persist_under(
    plugin_data: Path,
    parts: tuple[str, ...],
    name: str,
    payload: Mapping[str, Any],
    *,
    max_bytes: int = MAX_RECEIPT_BYTES,
) -> bytes:
    content = _canonical_bytes(payload)
    if len(content) > max_bytes:
        raise DispatchReceiptError("protected payload exceeds the byte ceiling")
    root = hook_receipt._open_plugin_data(plugin_data)
    descriptors = [root]
    try:
        current = root
        for part in parts:
            current = hook_receipt._open_private_child(current, part)
            descriptors.append(current)
        if max_bytes == MAX_RECEIPT_BYTES:
            hook_receipt._write_once(current, name, content)
        else:
            temporary = f".{name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
            lock_fd = os.open(
                ".receipt.lock",
                os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=current,
            )
            try:
                os.fchmod(lock_fd, 0o600)
                lock_metadata = os.fstat(lock_fd)
                if (
                    not stat.S_ISREG(lock_metadata.st_mode)
                    or lock_metadata.st_nlink != 1
                    or lock_metadata.st_uid != os.getuid()
                    or stat.S_IMODE(lock_metadata.st_mode) != 0o600
                ):
                    raise DispatchReceiptError(
                        "protected record lock has unsafe metadata"
                    )
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
                try:
                    existing = _read_at_bounded(
                        current, name, "protected record", max_bytes
                    )
                except FileNotFoundError:
                    existing = None
                if existing is not None:
                    if existing != content:
                        raise DispatchReceiptError(
                            "duplicate protected record conflicts with existing bytes"
                        )
                else:
                    descriptor = os.open(
                        temporary,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | getattr(os, "O_NOFOLLOW", 0),
                        0o600,
                        dir_fd=current,
                    )
                    try:
                        os.fchmod(descriptor, 0o600)
                        view = memoryview(content)
                        while view:
                            written = os.write(descriptor, view)
                            if written <= 0:
                                raise DispatchReceiptError(
                                    "protected record write made no progress"
                                )
                            view = view[written:]
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
                    os.rename(
                        temporary,
                        name,
                        src_dir_fd=current,
                        dst_dir_fd=current,
                    )
                    os.fsync(current)
            finally:
                try:
                    os.unlink(temporary, dir_fd=current)
                except FileNotFoundError:
                    pass
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
        if _read_at_bounded(current, name, "persisted record", max_bytes) != content:
            raise DispatchReceiptError("normalized receipt readback failed")
    except hook_receipt.AgentReceiptError as exc:
        raise DispatchReceiptError(str(exc)) from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    return content


def _timestamp_now() -> str:
    return _utc_now().isoformat(timespec="microseconds").replace("+00:00", "Z")


def _current_hook_bytes() -> tuple[bytes, bytes]:
    try:
        definition = hook_receipt._read_regular(
            HOOKS_DIR / "hooks.json", "hook definition", MAX_RECEIPT_BYTES
        )
        handler = hook_receipt._read_regular(
            HOOKS_DIR / "agent_receipt.py", "hook handler", MAX_RECEIPT_BYTES
        )
    except hook_receipt.AgentReceiptError as exc:
        raise DispatchReceiptError(str(exc)) from exc
    return definition, handler


def _record_reference(kind: str, digest: str) -> str:
    return f"record:{kind}:{digest}"


def _parse_record_reference(reference: str, expected_kind: str) -> str:
    if not isinstance(reference, str):
        raise DispatchReceiptError(f"{expected_kind} record reference is invalid")
    parts = reference.split(":")
    if (
        len(parts) != 3
        or parts[0] != "record"
        or parts[1] != expected_kind
        or not HEX64.fullmatch(parts[2])
    ):
        raise DispatchReceiptError(f"{expected_kind} record reference is invalid")
    return parts[2]


def persist_protected_record(plugin_data: Path, record: Mapping[str, Any]) -> str:
    """Persist one root-owned content-addressed evidence record."""

    kind = record.get("record_type")
    if (
        record.get("schema_version") != 1
        or not isinstance(kind, str)
        or kind not in RECORD_KINDS
    ):
        raise DispatchReceiptError("protected record envelope is invalid")
    content = _canonical_bytes(record)
    record_limit = (
        MAX_PROTECTED_RECORD_BYTES if kind in LARGE_RECORD_KINDS else MAX_RECEIPT_BYTES
    )
    if len(content) > record_limit:
        raise DispatchReceiptError("protected record exceeds the byte ceiling")
    digest = _sha256(content)
    _persist_under(
        plugin_data,
        ("records", "v1", kind),
        f"{digest}.json",
        record,
        max_bytes=record_limit,
    )
    return _record_reference(kind, digest)


def load_protected_record(
    plugin_data: Path,
    reference: str,
    expected_kind: str,
) -> tuple[dict[str, Any], bytes]:
    """Read one exact content-addressed record through protected directory descriptors."""

    digest = _parse_record_reference(reference, expected_kind)
    descriptors = _open_existing_chain(plugin_data, ("records", "v1", expected_kind))
    record_limit = (
        MAX_PROTECTED_RECORD_BYTES
        if expected_kind in LARGE_RECORD_KINDS
        else MAX_RECEIPT_BYTES
    )
    try:
        record, content = _load_json_at(
            descriptors[-1],
            f"{digest}.json",
            f"{expected_kind} record",
            record_limit,
        )
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if (
        content != _canonical_bytes(record)
        or _sha256(content) != digest
        or record.get("schema_version") != 1
        or record.get("record_type") != expected_kind
    ):
        raise DispatchReceiptError(f"{expected_kind} record digest or envelope is invalid")
    return record, content
