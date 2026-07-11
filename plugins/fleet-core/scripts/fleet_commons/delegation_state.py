#!/usr/bin/env python3
"""Contained Codex delegation liveness marker with atomic, permission-safe writes.

The marker is advisory engine liveness state, not a hook guard and not workflow completion proof.
Readers fail open so corrupt local state cannot break an unrelated Codex turn.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import stat
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

DEFAULT_TTL_SECONDS = 4 * 60 * 60
DEFAULT_MARKER_RELATIVE_PATH = Path(".codex/saga/delegation/active.json")


@dataclass(frozen=True)
class DelegationEntry:
    engine: str
    session_id: str
    armed_at: float
    armed_by: str

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "session_id": self.session_id,
            "armed_at": self.armed_at,
            "armed_by": self.armed_by,
        }

    @classmethod
    def from_jsonable(cls, payload: dict[str, Any]) -> DelegationEntry | None:
        engine = payload.get("engine")
        session_id = payload.get("session_id")
        armed_at = payload.get("armed_at")
        armed_by = payload.get("armed_by")
        if not all(isinstance(value, str) and value for value in (engine, session_id, armed_by)):
            return None
        if isinstance(armed_at, bool) or not isinstance(armed_at, (int, float)):
            return None
        return cls(engine=engine, session_id=session_id, armed_at=float(armed_at), armed_by=armed_by)


def _validate_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value or any(ord(character) < 32 for character in value):
        raise ValueError(f"{field} must be a non-empty control-free string")


def _marker_path(root: Path | str | None = None) -> Path:
    base = (Path(root) if root is not None else Path.cwd()).resolve()
    candidate = base / DEFAULT_MARKER_RELATIVE_PATH
    resolved_parent = candidate.parent.resolve(strict=False)
    if not resolved_parent.is_relative_to(base):
        raise ValueError("delegation marker parent escapes the selected root")
    return resolved_parent / candidate.name


def _read_entries_raw(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("rb") as handle:
            raw = handle.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            return []
        payload = json.loads(raw)
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _live_entries(path: Path, *, now: float, ttl_seconds: float) -> list[DelegationEntry]:
    if ttl_seconds <= 0:
        return []
    live: list[DelegationEntry] = []
    for raw in _read_entries_raw(path):
        entry = DelegationEntry.from_jsonable(raw)
        if entry is not None and now - entry.armed_at <= ttl_seconds:
            live.append(entry)
    return live


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".active.", delete=False) as handle:
            temporary = Path(handle.name)
            os.fchmod(handle.fileno(), 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def _exclusive(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = path.with_suffix(".lock")
    flags = os.O_CREAT | os.O_RDWR | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("delegation lock must be one regular, unlinked file")
        if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
            raise ValueError("delegation lock must be owned by the current user")
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def arm(
    engine: str,
    session_id: str,
    armed_by: str,
    *,
    root: Path | str | None = None,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    now: float | None = None,
) -> DelegationEntry:
    for value, field in ((engine, "engine"), (session_id, "session_id"), (armed_by, "armed_by")):
        _validate_text(value, field)
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")
    path = _marker_path(root)
    effective_now = time.time() if now is None else now
    entry = DelegationEntry(engine, session_id, effective_now, armed_by)
    with _exclusive(path):
        surviving = [
            existing
            for existing in _live_entries(path, now=effective_now, ttl_seconds=ttl_seconds)
            if existing.session_id != session_id
        ]
        surviving.append(entry)
        _write_json(path, {"entries": [item.to_jsonable() for item in surviving]})
    return entry


def disarm(
    session_id: str,
    *,
    root: Path | str | None = None,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    now: float | None = None,
) -> bool:
    _validate_text(session_id, "session_id")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")
    path = _marker_path(root)
    effective_now = time.time() if now is None else now
    with _exclusive(path):
        live = _live_entries(path, now=effective_now, ttl_seconds=ttl_seconds)
        removed = any(entry.session_id == session_id for entry in live)
        surviving = [entry for entry in live if entry.session_id != session_id]
        if removed or path.exists():
            _write_json(path, {"entries": [item.to_jsonable() for item in surviving]})
    return removed


def active(
    session_id: str,
    *,
    root: Path | str | None = None,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    now: float | None = None,
) -> DelegationEntry | None:
    try:
        _validate_text(session_id, "session_id")
        path = _marker_path(root)
        effective_now = time.time() if now is None else now
        return next(
            (
                entry
                for entry in _live_entries(path, now=effective_now, ttl_seconds=ttl_seconds)
                if entry.session_id == session_id
            ),
            None,
        )
    except Exception:  # noqa: BLE001 - fail-open reader contract
        return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex delegation liveness marker")
    parser.add_argument("--root", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    arm_parser = subparsers.add_parser("arm")
    arm_parser.add_argument("--engine", required=True)
    arm_parser.add_argument("--session-id", required=True)
    arm_parser.add_argument("--armed-by", required=True)
    disarm_parser = subparsers.add_parser("disarm")
    disarm_parser.add_argument("--session-id", required=True)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--session-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "arm":
        payload = arm(args.engine, args.session_id, args.armed_by, root=args.root).to_jsonable()
    elif args.command == "disarm":
        payload = {"session_id": args.session_id, "removed": disarm(args.session_id, root=args.root)}
    else:
        entry = active(args.session_id, root=args.root)
        payload = {"session_id": args.session_id, "armed": entry is not None}
        if entry is not None:
            payload.update(entry.to_jsonable())
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
