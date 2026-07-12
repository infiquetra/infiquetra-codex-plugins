#!/usr/bin/env python3
"""Git-common-dir store for immutable external-action records and transitions."""

from __future__ import annotations

import fcntl
import json
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))

import external_action_contract as contract  # noqa: E402
import outcome_store  # noqa: E402


ACTION_NAMESPACE = "saga-external-actions"


class ActionStoreError(ValueError):
    """An action-store operation would violate immutability or transition truth."""


@dataclass(frozen=True, slots=True)
class Store:
    root: Path

    @classmethod
    def for_action(
        cls,
        *,
        saga_id: str,
        run_id: str,
        action_id: str,
        repo_root: Path,
        runner: Callable[..., Any] | None = None,
    ) -> Store:
        for name, value in (("saga_id", saga_id), ("run_id", run_id), ("action_id", action_id)):
            contract.require_id(value, field_name=name)
        common = outcome_store.resolve_common_dir(repo_root, runner=runner)
        return cls(common / ACTION_NAMESPACE / saga_id / run_id / action_id)

    @property
    def request_path(self) -> Path:
        return self.root / "request.json"

    @property
    def approval_path(self) -> Path:
        return self.root / "approval.json"

    @property
    def events_path(self) -> Path:
        return self.root / "events.jsonl"

    @property
    def status_json_path(self) -> Path:
        return self.root / "status.json"

    @property
    def status_markdown_path(self) -> Path:
        return self.root / "status.md"

    @property
    def lock_path(self) -> Path:
        return self.root / ".lock"

    def ensure(self) -> Store:
        self.root.mkdir(parents=True, exist_ok=True)
        return self


@dataclass(frozen=True, slots=True)
class Snapshot:
    request: contract.ActionRequest
    approval: contract.ActionApproval | None
    events: tuple[dict[str, Any], ...]
    state: contract.State


def _json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_once(path: Path, payload: Mapping[str, Any]) -> Path:
    expected = _json_text(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != expected:
            raise ActionStoreError(f"immutable record differs: {path.name}")
        return path
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(expected)
        handle.flush()
        os.fsync(handle.fileno())
    return path


@contextmanager
def _locked(store: Store) -> Iterator[None]:
    store.ensure()
    with store.lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def write_request(store: Store, request: contract.ActionRequest) -> Path:
    return _write_once(store.ensure().request_path, request.to_dict())


def write_approval(store: Store, approval: contract.ActionApproval) -> Path:
    request = read_request(store)
    if request is None:
        raise ActionStoreError("request must exist before approval")
    if approval.action_id != request.action_id:
        raise ActionStoreError("approval action_id does not match request")
    if approval.request_sha256 != request.request_sha256:
        raise ActionStoreError("approval request_sha256 does not match request")
    payload = approval.to_dict()
    payload["approval_fingerprint"] = approval.approval_fingerprint
    return _write_once(store.approval_path, payload)


def _read_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise ActionStoreError(f"malformed JSON record: {path.name}") from exc
    if not isinstance(value, dict):
        raise ActionStoreError(f"JSON record must be an object: {path.name}")
    return value


def read_request(store: Store) -> contract.ActionRequest | None:
    value = _read_object(store.request_path)
    return None if value is None else contract.ActionRequest.from_dict(value)


def read_approval(store: Store) -> contract.ActionApproval | None:
    value = _read_object(store.approval_path)
    return None if value is None else contract.ActionApproval.from_dict(value)


def _heal_torn_tail(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return
    data = path.read_bytes()
    if data.endswith(b"\n"):
        return
    newline = data.rfind(b"\n")
    healed = data[: newline + 1] if newline >= 0 else b""
    with path.open("r+b") as handle:
        handle.truncate(0)
        handle.write(healed)
        handle.flush()
        os.fsync(handle.fileno())


def _event_hash(payload: Mapping[str, Any]) -> str:
    return contract.digest({key: value for key, value in payload.items() if key != "this_hash"})


def _read_events_unlocked(store: Store, *, heal_tail: bool) -> list[dict[str, Any]]:
    if heal_tail:
        _heal_torn_tail(store.events_path)
    try:
        lines = store.events_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    records: list[dict[str, Any]] = []
    expected_prev = ""
    state = contract.State.REQUESTED
    for index, line in enumerate(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ActionStoreError(f"event {index} is malformed") from exc
        if not isinstance(record, dict) or record.get("schema") != contract.EVENT_SCHEMA:
            raise ActionStoreError(f"event {index} has an invalid schema")
        if record.get("sequence") != index + 1:
            raise ActionStoreError(f"event {index} has a non-contiguous sequence")
        if record.get("prev_hash") != expected_prev:
            raise ActionStoreError(f"event {index} has a broken hash link")
        if record.get("this_hash") != _event_hash(record):
            raise ActionStoreError(f"event {index} was mutated")
        if record.get("from_state") != state.value:
            raise ActionStoreError(f"event {index} does not start from the current state")
        try:
            expected_state = contract.next_state(
                state, str(record.get("event")), rationale=record.get("rationale")
            )
        except contract.ContractError as exc:
            raise ActionStoreError(f"event {index} has an invalid transition: {exc}") from exc
        if record.get("to_state") != expected_state.value:
            raise ActionStoreError(f"event {index} has an invalid resulting state")
        state = expected_state
        expected_prev = str(record["this_hash"])
        records.append(record)
    return records


def append_event(
    store: Store,
    *,
    event_id: str,
    event: str,
    at: str,
    detail: Mapping[str, Any] | None = None,
    rationale: str | None = None,
) -> dict[str, Any]:
    contract.require_id(event_id, field_name="event_id")
    if not isinstance(at, str) or not at.strip():
        raise ActionStoreError("event at must be a non-empty string")
    with _locked(store):
        request = read_request(store)
        if request is None:
            raise ActionStoreError("request must exist before events")
        records = _read_events_unlocked(store, heal_tail=True)
        for existing in records:
            if existing["event_id"] == event_id:
                candidate = {
                    key: value
                    for key, value in existing.items()
                    if key not in {"sequence", "from_state", "to_state", "prev_hash", "this_hash"}
                }
                expected = {
                    "schema": contract.EVENT_SCHEMA,
                    "event_id": event_id,
                    "event": event,
                    "at": at,
                    "detail": dict(detail or {}),
                    "rationale": rationale,
                }
                if candidate != expected:
                    raise ActionStoreError("event_id already exists with different content")
                return existing
        state = (
            contract.State(records[-1]["to_state"])
            if records
            else contract.State.REQUESTED
        )
        try:
            target = contract.next_state(state, event, rationale=rationale)
        except contract.ContractError as exc:
            raise ActionStoreError(str(exc)) from exc
        new_record: dict[str, Any] = {
            "schema": contract.EVENT_SCHEMA,
            "event_id": event_id,
            "sequence": len(records) + 1,
            "event": event,
            "at": at,
            "from_state": state.value,
            "to_state": target.value,
            "detail": dict(detail or {}),
            "rationale": rationale,
            "prev_hash": records[-1]["this_hash"] if records else "",
        }
        new_record["this_hash"] = _event_hash(new_record)
        store.events_path.parent.mkdir(parents=True, exist_ok=True)
        with store.events_path.open("a", encoding="utf-8") as handle:
            handle.write(contract.canonical_json(new_record) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return new_record


def read_snapshot(store: Store) -> Snapshot:
    with _locked(store):
        request = read_request(store)
        if request is None:
            raise ActionStoreError("action request is missing")
        approval = read_approval(store)
        events = tuple(_read_events_unlocked(store, heal_tail=False))
    state = contract.State(events[-1]["to_state"]) if events else contract.State.REQUESTED
    return Snapshot(request=request, approval=approval, events=events, state=state)


def write_projection(store: Store, status: Mapping[str, Any], markdown: str) -> None:
    _atomic_write(store.status_json_path, _json_text(status))
    _atomic_write(store.status_markdown_path, markdown.rstrip() + "\n")
