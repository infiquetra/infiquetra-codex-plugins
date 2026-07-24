"""Tests for the sanitized Codex 0.145.0 V2 capability snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from scripts.port_contract import canonical_json_bytes, validate_json_schema_instance


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "docs/validation/codex-runtime-capability-snapshot.json"
SCHEMA_PATH = ROOT / "docs/validation/codex-runtime-capability-snapshot.schema-r3.json"


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def test_snapshot_matches_closed_r3_schema() -> None:
    snapshot = load_snapshot()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert validate_json_schema_instance(snapshot, schema, label="snapshot") == []
    assert schema["additionalProperties"] is False
    assert set(snapshot) == set(schema["required"]) == set(schema["properties"])
    assert snapshot["schema_version"] == 2
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", snapshot["captured_at"])


def test_every_declared_object_schema_is_closed() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if value.get("type") == "object":
                assert value.get("additionalProperties") is False
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)


def test_refs_are_full_commits_and_frozen_target_is_reachable() -> None:
    refs = load_snapshot()["refs"]

    for group in refs.values():
        for key, value in group.items():
            if key == "target_reachable":
                continue
            assert re.fullmatch(r"[0-9a-f]{40}", value), (key, value)
    assert refs["claude"]["target_reachable"] is True
    assert refs["claude"]["source_base"] == "9470edca65b1db06d2f7562eeb2d5a9e48c34dec"
    assert refs["claude"]["source_target"] == "46fefb6f17f0c9d0d63858978536d3369ab57dfe"


def test_catalog_projection_reproduces_digest() -> None:
    catalog = load_snapshot()["catalog"]
    models = catalog["models"]

    assert len(models) == len({model["slug"] for model in models}) == 8
    assert hashlib.sha256(canonical_json_bytes(models)).hexdigest() == catalog["normalized_sha256"]
    by_slug = {model["slug"]: model for model in models}
    assert by_slug["gpt-5.6-sol"]["supported_efforts"][-1] == "ultra"
    assert by_slug["gpt-5.6-terra"]["supported_efforts"][-1] == "ultra"
    assert "ultra" not in by_slug["gpt-5.6-luna"]["supported_efforts"]


def test_active_host_and_v2_contract_are_separate_truths() -> None:
    snapshot = load_snapshot()
    runtime = snapshot["runtime"]

    assert runtime["codex_cli_version"] == "0.145.0"
    assert snapshot["features"]["multi_agent_v2"] == {"stage": "stable", "enabled": False}
    assert runtime["multi_agent_v2_config"]["enabled"] is True
    assert runtime["configured_max_threads"] == 6
    assert runtime["configured_max_threads_key"] == "max_threads"
    assert runtime["configured_v2_total_threads"] == 7
    assert runtime["configured_v2_total_threads_source"] == "agents-plus-root"
    assert runtime["host_total_slots"] is None


def test_spawn_contract_separates_request_response_and_runtime_readback() -> None:
    spawn = load_snapshot()["collaboration"]["spawn"]

    assert spawn["contract_version"] == "v2"
    assert spawn["tool_namespace"] == "agents"
    assert spawn["request_fields"] == [
        "agent_type",
        "fork_turns",
        "message",
        "model",
        "reasoning_effort",
        "service_tier",
        "task_name",
    ]
    assert spawn["response_fields"] == ["nickname", "task_name"]
    assert spawn["runtime_receipt_sources"] == ["session_meta", "turn_context"]
    assert spawn["selection_readback_fields"] == [
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
    assert spawn["per_child_sandbox"] is False
    assert load_snapshot()["collaboration"]["context"]["child_permissions_inherit_parent_turn"] is True


def test_v2_operation_inventory_and_remaining_proof_are_explicit() -> None:
    collaboration = load_snapshot()["collaboration"]
    statuses = {row["name"]: row["status"] for row in collaboration["required_capabilities"]}

    assert collaboration["operations"] == [
        "followup_task",
        "interrupt_agent",
        "list_agents",
        "send_message",
        "spawn_agent",
        "wait_agent",
    ]
    assert statuses["configured-agent-selection"] == "source-confirmed"
    assert statuses["nested-delegation"] == "pending-u8"
    assert statuses["typed-results"] == "pending-u4"
    assert statuses["luna-leaf"] == statuses["ultra-root-only"] == "pending-u8"


def test_hooks_are_not_runtime_authority() -> None:
    hooks = load_snapshot()["hook_capabilities"]

    assert hooks["plugin_hooks_supported"] is True
    assert hooks["runtime_authority"] is False


def test_snapshot_excludes_sensitive_and_host_specific_payloads() -> None:
    snapshot = load_snapshot()

    def keys(value: object) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            found.update(str(key).lower() for key in value)
            for child in value.values():
                found.update(keys(child))
        elif isinstance(value, list):
            for child in value:
                found.update(keys(child))
        return found

    present_keys = keys(snapshot)
    text = SNAPSHOT_PATH.read_text(encoding="utf-8").lower()
    for forbidden_key in (
        "base_instructions",
        "developer_instructions",
        "model_messages",
        "transcript_path",
        "prompt",
        "environment",
        "token",
        "secret",
    ):
        assert forbidden_key not in present_keys
    for forbidden_value in ("auth.json", "/users/", "bearer ", "sk-"):
        assert forbidden_value not in text
