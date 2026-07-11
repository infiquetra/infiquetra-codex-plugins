#!/usr/bin/env python3
"""Root-owned abandonment, prune planning, and verified raw-hook cleanup."""

from __future__ import annotations

from protected_store import (
    Any,
    Callable,
    DispatchReceiptError,
    HEX64,
    MAX_EVENT_AGE_SECONDS,
    Mapping,
    Path,
    _canonical_bytes,
    _hash_segment,
    _load_json_at,
    _open_existing_chain,
    _parse_time,
    _persist_under,
    _runtime_id,
    _sha256,
    _timestamp_now,
    _utc_now,
    _validate_raw_bytes,
    _validate_raw_event,
    dt,
    fcntl,
    hook_receipt,
    json,
    load_protected_record,
    os,
    persist_protected_record,
    re,
)
from workflow_records import _load_consumption_marker, load_normalized_by_identity

def create_raw_abandonment_record(
    plugin_data: Path,
    *,
    parent_session_id: str,
    child_id: str,
    turn_id: str,
    reason: str,
    recorded_at: str | None = None,
) -> str:
    parent_session_id = _runtime_id(parent_session_id, "parent_session_id")
    child_id = _runtime_id(child_id, "child_id")
    turn_id = _runtime_id(turn_id, "turn_id")
    if reason not in {"operator-confirmed", "host-terminal"}:
        raise DispatchReceiptError("raw abandonment reason is invalid")
    descriptors = _open_existing_chain(
        plugin_data,
        (
            "receipts",
            "v1",
            "raw",
            _hash_segment(parent_session_id),
            _hash_segment(child_id),
            _hash_segment(turn_id),
        ),
    )
    try:
        start, start_bytes = _load_json_at(
            descriptors[-1], "start.json", "abandoned start receipt"
        )
        try:
            _load_json_at(descriptors[-1], "stop.json", "unexpected stop receipt")
        except FileNotFoundError:
            pass
        else:
            raise DispatchReceiptError("a complete raw pair cannot be abandoned")
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    start = _validate_raw_event(
        start,
        "start",
        parent_session_id=parent_session_id,
        child_id=child_id,
        turn_id=turn_id,
    )
    _validate_raw_bytes(start, start_bytes, "abandoned start receipt")
    recorded_at = recorded_at or _timestamp_now()
    if _parse_time(recorded_at, "raw abandonment.recorded_at") < _parse_time(
        start["observed_at"], "start.observed_at"
    ):
        raise DispatchReceiptError("raw abandonment predates the start event")
    start_sha256 = _sha256(start_bytes)
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "raw-abandonment",
            "parent_session_id": parent_session_id,
            "child_id": child_id,
            "turn_id": turn_id,
            "start_sha256": start_sha256,
            "reason": reason,
            "recorded_by": "root",
            "recorded_at": recorded_at,
        },
    )
    _persist_under(
        plugin_data,
        ("receipts", "v1", "abandoned"),
        f"{start_sha256}.json",
        {"schema_version": 1, "start_sha256": start_sha256, "record_ref": reference},
    )
    _load_raw_abandonment(plugin_data, start, start_bytes)
    return reference


def _load_raw_abandonment(
    plugin_data: Path,
    start: Mapping[str, Any],
    start_bytes: bytes,
) -> dict[str, Any] | None:
    start_sha256 = _sha256(start_bytes)
    try:
        descriptors = _open_existing_chain(
            plugin_data, ("receipts", "v1", "abandoned")
        )
    except FileNotFoundError:
        return None
    try:
        try:
            index, index_bytes = _load_json_at(
                descriptors[-1], f"{start_sha256}.json", "raw abandonment index"
            )
        except FileNotFoundError:
            return None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if index_bytes != _canonical_bytes(index) or set(index) != {
        "schema_version",
        "start_sha256",
        "record_ref",
    } or index["schema_version"] != 1 or index["start_sha256"] != start_sha256:
        raise DispatchReceiptError("raw abandonment index is invalid")
    record, _record_bytes = load_protected_record(
        plugin_data, index["record_ref"], "raw-abandonment"
    )
    if set(record) != {
        "schema_version",
        "record_type",
        "parent_session_id",
        "child_id",
        "turn_id",
        "start_sha256",
        "reason",
        "recorded_by",
        "recorded_at",
    } or any(
        record[field] != start[source]
        for field, source in (
            ("parent_session_id", "parent_session_id"),
            ("child_id", "child_id"),
            ("turn_id", "turn_id"),
        )
    ) or record["start_sha256"] != start_sha256 or record["reason"] not in {
        "operator-confirmed",
        "host-terminal",
    } or record["recorded_by"] != "root":
        raise DispatchReceiptError("raw abandonment record is invalid")
    _parse_time(record["recorded_at"], "raw abandonment.recorded_at")
    return record


def _raw_leaf_actions(
    plugin_data: Path,
    leaf_fd: int,
    parts: tuple[str, str, str],
    *,
    cutoff: dt.datetime,
    visit_entry: Callable[[], None],
    consume_bytes: Callable[[int], None],
) -> dict[str, Any] | None:
    entries: list[os.DirEntry[str]] = []
    for entry in os.scandir(leaf_fd):
        visit_entry()
        entries.append(entry)
    names = {entry.name for entry in entries}
    allowed = {"start.json", "stop.json", ".receipt.lock"}
    temporary = {
        name
        for name in names
        if re.fullmatch(r"\.(?:start|stop)\.json\.\d+\.[0-9a-f]{16}\.tmp", name)
    }
    unexpected = names - allowed - temporary
    if unexpected:
        raise DispatchReceiptError("raw receipt directory contains unexpected entries")
    snapshots: dict[str, dict[str, Any]] = {}
    snapshot_names = (names & {"start.json", "stop.json", ".receipt.lock"}) | temporary
    for name in sorted(snapshot_names):
        metadata = os.stat(name, dir_fd=leaf_fd, follow_symlinks=False)
        consume_bytes(metadata.st_size)
        content = hook_receipt._read_at(leaf_fd, name)
        snapshots[name] = {
            "sha256": _sha256(content),
            "mtime_ns": metadata.st_mtime_ns,
            "size": len(content),
            "old": dt.datetime.fromtimestamp(metadata.st_mtime, tz=dt.UTC) <= cutoff,
            "content": content,
        }
    raw_names = names & {"start.json", "stop.json"}
    eligible_raw: set[str] = set()
    if raw_names == {"start.json", "stop.json"}:
        start = snapshots["start.json"]["content"]
        stop = snapshots["stop.json"]["content"]
        raw_digest = _sha256(
            _canonical_bytes(
                {"start_sha256": _sha256(start), "stop_sha256": _sha256(stop)}
            )
        )
        marker = _load_consumption_marker(plugin_data, raw_digest)
        if marker is not None:
            loaded = load_normalized_by_identity(
                plugin_data,
                marker["workflow_sha256"],
                marker["workflow_run_sha256"],
                marker["step_id"],
                marker["attempt"],
            )
            if loaded is None or loaded[1].split(":")[-1] != marker["normalized_sha256"]:
                raise DispatchReceiptError(
                    "consumed raw pair lacks its normalized receipt readback"
                )
            eligible_raw = set(raw_names)
    elif raw_names:
        # A start-only leaf can still belong to a live child. Age alone has no
        # authority; cleanup additionally requires a protected root abandonment.
        if raw_names == {"start.json"} and snapshots["start.json"]["old"]:
            try:
                start = json.loads(snapshots["start.json"]["content"])
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DispatchReceiptError("incomplete start receipt is malformed") from exc
            if not isinstance(start, dict):
                raise DispatchReceiptError("incomplete start receipt is malformed")
            start = _validate_raw_event(
                start,
                "start",
                parent_session_id=str(start.get("parent_session_id")),
                child_id=str(start.get("child_id")),
                turn_id=str(start.get("turn_id")),
            )
            if _parse_time(start["observed_at"], "start.observed_at") <= cutoff and (
                _load_raw_abandonment(
                    plugin_data, start, snapshots["start.json"]["content"]
                )
                is not None
            ):
                eligible_raw = {"start.json"}
        elif raw_names == {"stop.json"} and snapshots["stop.json"]["old"]:
            try:
                stop = json.loads(snapshots["stop.json"]["content"])
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DispatchReceiptError("incomplete stop receipt is malformed") from exc
            if not isinstance(stop, dict):
                raise DispatchReceiptError("incomplete stop receipt is malformed")
            stop = _validate_raw_event(
                stop,
                "stop",
                parent_session_id=str(stop.get("parent_session_id")),
                child_id=str(stop.get("child_id")),
                turn_id=str(stop.get("turn_id")),
            )
            if _parse_time(stop["observed_at"], "stop.observed_at") <= cutoff:
                eligible_raw = {"stop.json"}
    eligible_temp = {name for name in temporary if snapshots[name]["old"]}
    selected = sorted(eligible_raw | eligible_temp)
    cleanup_empty_leaf = names == {".receipt.lock"} and snapshots[
        ".receipt.lock"
    ]["old"]
    if not selected and not cleanup_empty_leaf:
        return None
    return {
        "leaf": "/".join(parts),
        "files": selected,
        "bytes": sum(snapshots[name]["size"] for name in selected),
        "entry_names": sorted(names),
        "snapshots": {
            name: {
                "sha256": snapshots[name]["sha256"],
                "mtime_ns": snapshots[name]["mtime_ns"],
            }
            for name in (
                [".receipt.lock"] if cleanup_empty_leaf else selected
            )
        },
    }


def _prune_plan_sha256(
    *,
    older_than_seconds: int,
    max_entries: int,
    max_bytes: int,
    actions: list[dict[str, Any]],
) -> str:
    return _sha256(
        _canonical_bytes(
            {
                "schema_version": 1,
                "older_than_seconds": older_than_seconds,
                "max_entries": max_entries,
                "max_bytes": max_bytes,
                "actions": actions,
            }
        )
    )


def prune_raw_receipts(
    plugin_data: Path,
    *,
    older_than_seconds: int,
    apply: bool = False,
    expected_plan_sha256: str | None = None,
    max_entries: int = 1000,
    max_bytes: int = 64 * 1024 * 1024,
    now: Callable[[], dt.datetime] = _utc_now,
) -> dict[str, Any]:
    """Plan or apply bounded cleanup of stale incomplete or already-consumed raw receipts."""

    if (
        isinstance(older_than_seconds, bool)
        or not isinstance(older_than_seconds, int)
        or older_than_seconds < MAX_EVENT_AGE_SECONDS
        or isinstance(max_entries, bool)
        or not 1 <= max_entries <= 10000
        or isinstance(max_bytes, bool)
        or not 1 <= max_bytes <= 1024 * 1024 * 1024
    ):
        raise DispatchReceiptError("prune bounds are invalid")
    if apply and (
        not isinstance(expected_plan_sha256, str)
        or not HEX64.fullmatch(expected_plan_sha256)
    ):
        raise DispatchReceiptError("prune apply requires the exact dry-run plan digest")
    if not apply and expected_plan_sha256 is not None:
        raise DispatchReceiptError("prune dry-run cannot accept an apply plan digest")
    cutoff = now() - dt.timedelta(seconds=older_than_seconds)
    try:
        raw_chain = _open_existing_chain(plugin_data, ("receipts", "v1", "raw"))
    except FileNotFoundError:
        plan_sha256 = _prune_plan_sha256(
            older_than_seconds=older_than_seconds,
            max_entries=max_entries,
            max_bytes=max_bytes,
            actions=[],
        )
        if apply and expected_plan_sha256 != plan_sha256:
            raise DispatchReceiptError("prune plan changed after dry-run")
        return {
            "schema_version": 1,
            "claim": "raw-prune-plan",
            "apply": apply,
            "entries": [],
            "file_count": 0,
            "byte_count": 0,
            "plan_sha256": plan_sha256,
        }
    actions: list[dict[str, Any]] = []
    visited_entries = 0
    scanned_bytes = 0
    planned_bytes = 0

    def visit_entry() -> None:
        nonlocal visited_entries
        visited_entries += 1
        if visited_entries > max_entries:
            raise DispatchReceiptError("prune traversal exceeds the entry ceiling")

    def consume_bytes(size: int) -> None:
        nonlocal scanned_bytes
        if isinstance(size, bool) or size < 0:
            raise DispatchReceiptError("prune candidate size is invalid")
        scanned_bytes += size
        if scanned_bytes > max_bytes:
            raise DispatchReceiptError("prune traversal exceeds the byte ceiling")

    def entries(directory_fd: int) -> list[os.DirEntry[str]]:
        values: list[os.DirEntry[str]] = []
        for entry in os.scandir(directory_fd):
            visit_entry()
            values.append(entry)
        return sorted(values, key=lambda item: item.name)

    raw_fd = raw_chain[-1]
    try:
        for session_entry in entries(raw_fd):
            if not HEX64.fullmatch(session_entry.name) or not session_entry.is_dir(
                follow_symlinks=False
            ):
                raise DispatchReceiptError("raw session directory is unsafe")
            session_fd = os.open(
                session_entry.name, hook_receipt._directory_flags(), dir_fd=raw_fd
            )
            try:
                hook_receipt._validate_directory(session_fd, "raw session", private=True)
                for child_entry in entries(session_fd):
                    if not HEX64.fullmatch(child_entry.name) or not child_entry.is_dir(
                        follow_symlinks=False
                    ):
                        raise DispatchReceiptError("raw child directory is unsafe")
                    child_fd = os.open(
                        child_entry.name,
                        hook_receipt._directory_flags(),
                        dir_fd=session_fd,
                    )
                    try:
                        hook_receipt._validate_directory(child_fd, "raw child", private=True)
                        for turn_entry in entries(child_fd):
                            if not HEX64.fullmatch(turn_entry.name) or not turn_entry.is_dir(
                                follow_symlinks=False
                            ):
                                raise DispatchReceiptError("raw turn directory is unsafe")
                            turn_fd = os.open(
                                turn_entry.name,
                                hook_receipt._directory_flags(),
                                dir_fd=child_fd,
                            )
                            try:
                                hook_receipt._validate_directory(
                                    turn_fd, "raw turn", private=True
                                )
                                action = _raw_leaf_actions(
                                    plugin_data,
                                    turn_fd,
                                    (
                                        session_entry.name,
                                        child_entry.name,
                                        turn_entry.name,
                                    ),
                                    cutoff=cutoff,
                                    visit_entry=visit_entry,
                                    consume_bytes=consume_bytes,
                                )
                                if action is not None:
                                    actions.append(action)
                                    planned_bytes += action["bytes"]
                                    if planned_bytes > max_bytes:
                                        raise DispatchReceiptError(
                                            "prune plan exceeds the byte ceiling"
                                        )
                            finally:
                                os.close(turn_fd)
                    finally:
                        os.close(child_fd)
            finally:
                os.close(session_fd)
    finally:
        for descriptor in reversed(raw_chain):
            os.close(descriptor)
    file_count = sum(len(action["files"]) for action in actions)
    entry_count = file_count + sum(not action["files"] for action in actions)
    byte_count = sum(action["bytes"] for action in actions)
    if entry_count > max_entries or byte_count > max_bytes:
        raise DispatchReceiptError("prune plan exceeds the configured count or byte ceiling")
    plan_sha256 = _prune_plan_sha256(
        older_than_seconds=older_than_seconds,
        max_entries=max_entries,
        max_bytes=max_bytes,
        actions=actions,
    )
    if apply and expected_plan_sha256 != plan_sha256:
        raise DispatchReceiptError("prune plan changed after dry-run")
    if apply:
        for action in actions:
            parts = tuple(action["leaf"].split("/"))
            descriptors = _open_existing_chain(
                plugin_data, ("receipts", "v1", "raw", *parts)
            )
            leaf_fd = descriptors[-1]
            lock_fd = os.open(
                ".receipt.lock",
                os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=leaf_fd,
            )
            try:
                os.fchmod(lock_fd, 0o600)
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise DispatchReceiptError(
                        "prune candidate is active and cannot be locked"
                    ) from exc
                current_names = sorted(entry.name for entry in os.scandir(leaf_fd))
                if current_names != action["entry_names"]:
                    raise DispatchReceiptError("prune candidate set changed after planning")
                for name, expected in action["snapshots"].items():
                    content = hook_receipt._read_at(leaf_fd, name)
                    metadata = os.stat(name, dir_fd=leaf_fd, follow_symlinks=False)
                    if (
                        _sha256(content) != expected["sha256"]
                        or metadata.st_mtime_ns != expected["mtime_ns"]
                    ):
                        raise DispatchReceiptError("prune candidate changed after planning")
                for name in action["files"]:
                    os.unlink(name, dir_fd=leaf_fd)
                os.fsync(leaf_fd)
                remaining = {entry.name for entry in os.scandir(leaf_fd)}
                if remaining <= {".receipt.lock"}:
                    try:
                        os.unlink(".receipt.lock", dir_fd=leaf_fd)
                    except FileNotFoundError:
                        pass
                    os.rmdir(parts[-1], dir_fd=descriptors[-2])
                    if not list(os.scandir(descriptors[-2])):
                        os.rmdir(parts[-2], dir_fd=descriptors[-3])
                        if not list(os.scandir(descriptors[-3])):
                            os.rmdir(parts[-3], dir_fd=descriptors[-4])
            finally:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                finally:
                    os.close(lock_fd)
                for descriptor in reversed(descriptors):
                    os.close(descriptor)
    return {
        "schema_version": 1,
        "claim": "raw-prune-applied" if apply else "raw-prune-plan",
        "apply": apply,
        "entries": [
            {"leaf": action["leaf"], "files": action["files"], "bytes": action["bytes"]}
            for action in actions
        ],
        "file_count": file_count,
        "byte_count": byte_count,
        "plan_sha256": plan_sha256,
    }


def delete_raw_pair(
    plugin_data: Path,
    *,
    parent_session_id: str,
    child_id: str,
    turn_id: str,
    start_sha256: str,
    stop_sha256: str,
) -> None:
    if not HEX64.fullmatch(start_sha256) or not HEX64.fullmatch(stop_sha256):
        raise DispatchReceiptError("raw cleanup digests are invalid")
    parts = (
        "receipts",
        "v1",
        "raw",
        _hash_segment(parent_session_id),
        _hash_segment(child_id),
        _hash_segment(turn_id),
    )
    descriptors = _open_existing_chain(plugin_data, parts)
    lock_fd = os.open(
        ".receipt.lock",
        os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
        0o600,
        dir_fd=descriptors[-1],
    )
    try:
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        expected = {"start.json": start_sha256, "stop.json": stop_sha256}
        for name, digest in expected.items():
            content = hook_receipt._read_at(descriptors[-1], name)
            if _sha256(content) != digest:
                raise DispatchReceiptError("raw cleanup content changed after normalization")
        for name in expected:
            os.unlink(name, dir_fd=descriptors[-1])
        os.fsync(descriptors[-1])
        remaining = {entry.name for entry in os.scandir(descriptors[-1])}
        if remaining != {".receipt.lock"}:
            raise DispatchReceiptError("raw cleanup directory changed during normalization")
        os.unlink(".receipt.lock", dir_fd=descriptors[-1])
        os.rmdir(parts[-1], dir_fd=descriptors[-2])
        if not list(os.scandir(descriptors[-2])):
            os.rmdir(parts[-2], dir_fd=descriptors[-3])
            if not list(os.scandir(descriptors[-3])):
                os.rmdir(parts[-3], dir_fd=descriptors[-4])
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)
        for descriptor in reversed(descriptors):
            os.close(descriptor)


