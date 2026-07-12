"""Tests for derived external-action status projections."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import external_action_contract as contract  # noqa: E402
import external_action_status as status_module  # noqa: E402
import external_action_store as store_module  # noqa: E402


def prepared_store(tmp_path: Path) -> store_module.Store:
    store = store_module.Store(tmp_path / "action")
    request = contract.ActionRequest(
        saga_id="task-runtime",
        run_id="run-1",
        action_id="offload-1",
        stage="brainstorm",
        intent="offload",
        trigger="alternative approach",
        requiredness=contract.Requiredness.BEST_EFFORT,
        provider_constraints={"engine_id": "ollama-cloud"},
        context_scope=("docs/brainstorms/input.md",),
        sensitivity="internal",
        write_set=(),
        evidence_destination="docs/brainstorms/advisory.md",
        consumption_point="before scope synthesis",
        created_at="2026-07-12T00:00:00Z",
    )
    store_module.write_request(store, request)
    approval = contract.ActionApproval(
        action_id=request.action_id,
        approved_at="2026-07-12T00:01:00Z",
        operator="operator",
        route={"engine_id": "ollama-cloud", "variant": "qwen"},
        context_scope=request.context_scope,
        sensitivity=request.sensitivity,
        base_revision="b" * 40,
        write_set=(),
        cost_class="metered",
        egress={"policy": "networked", "host": "ollama.com"},
        request_sha256=request.request_sha256,
    )
    store_module.write_approval(store, approval)
    store_module.append_event(
        store, event_id="resolve-1", event="resolve", at="2026-07-12T00:02:00Z"
    )
    store_module.append_event(
        store, event_id="approve-1", event="approve", at="2026-07-12T00:03:00Z"
    )
    return store


def test_refresh_writes_json_and_markdown_from_history(tmp_path: Path) -> None:
    store = prepared_store(tmp_path)
    status = status_module.refresh(store)
    assert status["state"] == "approved"
    assert status["route"]["engine_id"] == "ollama-cloud"
    assert json.loads(store.status_json_path.read_text()) == status
    markdown = store.status_markdown_path.read_text()
    assert "External Action `offload-1`" in markdown
    assert "| State | approved |" in markdown
    assert status["approval_fingerprint"] in markdown


def test_projection_is_recoverable_after_deletion(tmp_path: Path) -> None:
    store = prepared_store(tmp_path)
    first = status_module.refresh(store)
    store.status_json_path.unlink()
    store.status_markdown_path.unlink()
    second = status_module.refresh(store)
    assert first == second


def test_terminal_states_remain_distinct(tmp_path: Path) -> None:
    store = prepared_store(tmp_path)
    store_module.append_event(
        store, event_id="claim-1", event="claim", at="2026-07-12T00:04:00Z"
    )
    store_module.append_event(
        store, event_id="launch-1", event="launch", at="2026-07-12T00:05:00Z"
    )
    store_module.append_event(
        store, event_id="timeout-1", event="timeout", at="2026-07-12T00:06:00Z"
    )
    assert status_module.refresh(store)["state"] == "timed-out"
