"""Tests for immutable external-action records and append-only transitions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import external_action_contract as contract  # noqa: E402
import external_action_store as store_module  # noqa: E402


def request(**overrides: object) -> contract.ActionRequest:
    values: dict[str, object] = {
        "saga_id": "task-runtime",
        "run_id": "run-1",
        "action_id": "opinion-1",
        "stage": "work",
        "intent": "second-opinion",
        "trigger": "review architecture",
        "requiredness": contract.Requiredness.BEST_EFFORT,
        "provider_constraints": {"capability": "adversarial-review"},
        "context_scope": ("plugins/saga",),
        "sensitivity": "internal",
        "write_set": (),
        "evidence_destination": "docs/reviews/opinion.md",
        "consumption_point": "before code-review gate",
        "created_at": "2026-07-12T00:00:00Z",
    }
    values.update(overrides)
    return contract.ActionRequest(**values)  # type: ignore[arg-type]


def approval(req: contract.ActionRequest, **overrides: object) -> contract.ActionApproval:
    values: dict[str, object] = {
        "action_id": req.action_id,
        "approved_at": "2026-07-12T00:01:00Z",
        "operator": "operator",
        "route": {"engine_id": "agy", "variant": "gemini-pro"},
        "context_scope": req.context_scope,
        "sensitivity": req.sensitivity,
        "base_revision": "a" * 40,
        "write_set": req.write_set,
        "cost_class": "metered",
        "egress": {"policy": "networked", "host": "provider.example"},
        "request_sha256": req.request_sha256,
    }
    values.update(overrides)
    return contract.ActionApproval(**values)  # type: ignore[arg-type]


def action_store(tmp_path: Path) -> store_module.Store:
    return store_module.Store(tmp_path / "saga-external-actions" / "task" / "run" / "action")


def append(store: store_module.Store, event: str, sequence: int, **kwargs: object) -> dict:
    return store_module.append_event(
        store,
        event_id=f"event-{sequence}",
        event=event,
        at=f"2026-07-12T00:{sequence:02d}:00Z",
        **kwargs,  # type: ignore[arg-type]
    )


def test_request_and_approval_are_immutable_and_idempotent(tmp_path: Path) -> None:
    store = action_store(tmp_path)
    req = request()
    app = approval(req)
    assert store_module.write_request(store, req) == store.request_path
    assert store_module.write_request(store, req) == store.request_path
    assert store_module.write_approval(store, app) == store.approval_path
    assert store_module.write_approval(store, app) == store.approval_path
    with pytest.raises(store_module.ActionStoreError, match="immutable record differs"):
        store_module.write_request(store, request(trigger="different"))


def test_approval_must_bind_exact_request(tmp_path: Path) -> None:
    store = action_store(tmp_path)
    req = request()
    store_module.write_request(store, req)
    with pytest.raises(store_module.ActionStoreError, match="request_sha256"):
        store_module.write_approval(store, approval(req, request_sha256="0" * 64))


def test_happy_path_reconstructs_consumed_state(tmp_path: Path) -> None:
    store = action_store(tmp_path)
    req = request()
    store_module.write_request(store, req)
    store_module.write_approval(store, approval(req))
    for index, event in enumerate(
        ("resolve", "approve", "claim", "launch", "complete", "accept", "consume"), start=1
    ):
        append(store, event, index)
    snapshot = store_module.read_snapshot(store)
    assert snapshot.state == contract.State.CONSUMED
    assert len(snapshot.events) == 7
    assert snapshot.events[-1]["prev_hash"] == snapshot.events[-2]["this_hash"]


def test_invalid_transition_and_skipped_state_are_rejected(tmp_path: Path) -> None:
    store = action_store(tmp_path)
    store_module.write_request(store, request())
    with pytest.raises(store_module.ActionStoreError, match="invalid from state"):
        append(store, "claim", 1)


def test_event_id_is_idempotent_but_cannot_change(tmp_path: Path) -> None:
    store = action_store(tmp_path)
    store_module.write_request(store, request())
    first = append(store, "resolve", 1)
    again = append(store, "resolve", 1)
    assert first == again
    with pytest.raises(store_module.ActionStoreError, match="different content"):
        store_module.append_event(
            store,
            event_id="event-1",
            event="resolve",
            at="2026-07-12T00:99:00Z",
        )


def test_hash_mutation_is_detected(tmp_path: Path) -> None:
    store = action_store(tmp_path)
    store_module.write_request(store, request())
    append(store, "resolve", 1)
    record = json.loads(store.events_path.read_text().splitlines()[0])
    record["event"] = "reject"
    store.events_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(store_module.ActionStoreError, match="mutated"):
        store_module.read_snapshot(store)


def test_torn_tail_is_healed_by_next_append(tmp_path: Path) -> None:
    store = action_store(tmp_path)
    store_module.write_request(store, request())
    append(store, "resolve", 1)
    with store.events_path.open("a", encoding="utf-8") as handle:
        handle.write('{"schema":"torn"')
    append(store, "approve", 2)
    assert store_module.read_snapshot(store).state == contract.State.APPROVED
    assert store.events_path.read_bytes().endswith(b"\n")


def test_override_requires_terminal_failure_and_rationale(tmp_path: Path) -> None:
    store = action_store(tmp_path)
    store_module.write_request(store, request(requiredness=contract.Requiredness.REQUIRED))
    append(store, "resolve", 1)
    append(store, "approve", 2)
    append(store, "claim", 3)
    append(store, "unavailable", 4)
    with pytest.raises(store_module.ActionStoreError, match="requires a rationale"):
        append(store, "override-continue", 5)
    append(store, "override-continue", 5, rationale="continue with native Codex evidence")
    snapshot = store_module.read_snapshot(store)
    assert snapshot.state == contract.State.UNAVAILABLE
    assert snapshot.events[-1]["rationale"] == "continue with native Codex evidence"


def test_safe_ids_reject_path_traversal() -> None:
    with pytest.raises(contract.ContractError):
        request(action_id="../escape")
