"""Tests for the sanitized Codex runtime capability snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from scripts.port_contract import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "docs/validation/codex-runtime-capability-snapshot.json"
SCHEMA_PATH = ROOT / "docs/validation/codex-runtime-capability-snapshot.schema.json"


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def test_snapshot_top_level_matches_closed_schema() -> None:
    snapshot = load_snapshot()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["additionalProperties"] is False
    assert set(snapshot) == set(schema["required"]) == set(schema["properties"])
    assert snapshot["schema_version"] == 1
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


def test_catalog_projection_reproduces_digest() -> None:
    catalog = load_snapshot()["catalog"]
    models = catalog["models"]

    assert len(models) == len({model["slug"] for model in models}) == 8
    assert hashlib.sha256(canonical_json_bytes(models)).hexdigest() == catalog["normalized_sha256"]
    by_slug = {model["slug"]: model for model in models}
    assert by_slug["gpt-5.6-sol"]["supported_efforts"][-1] == "ultra"
    assert by_slug["gpt-5.6-terra"]["supported_efforts"][-1] == "ultra"
    assert "ultra" not in by_slug["gpt-5.6-luna"]["supported_efforts"]
    assert by_slug["gpt-5.3-codex-spark"]["supported_in_api"] is False
    assert by_slug["codex-auto-review"]["visibility"] == "hide"


def test_configured_effort_is_not_misreported_as_catalog_default() -> None:
    snapshot = load_snapshot()

    assert snapshot["configured_defaults"] == {
        "model": "gpt-5.6-sol",
        "model_reasoning_effort": "max",
    }
    sol = next(model for model in snapshot["catalog"]["models"] if model["slug"] == "gpt-5.6-sol")
    assert sol["default_effort"] == "low"


def test_host_capacity_is_distinct_from_configured_thread_ceiling() -> None:
    runtime = load_snapshot()["runtime"]

    assert runtime["configured_max_threads"] == 6
    assert runtime["configured_max_threads_source"] == "config"
    assert runtime["configured_max_depth_source"] == "config"
    assert runtime["host_total_slots"] == 4
    assert runtime["effective_total_slots"] == min(
        runtime["configured_max_threads"], runtime["host_total_slots"]
    )
    assert runtime["effective_max_children"] == runtime["effective_total_slots"] - 1


def test_spawn_contract_does_not_invent_per_child_selection_or_readback() -> None:
    spawn = load_snapshot()["collaboration"]["spawn"]

    assert spawn["request_fields"] == ["fork_turns", "message", "task_name"]
    assert spawn["selection_readback_fields"] == []
    assert spawn["per_child_agent_type"] is False
    assert spawn["per_child_model"] is False
    assert spawn["per_child_effort"] is False
    assert spawn["per_child_sandbox"] is False


def test_custom_agent_config_and_hook_attestation_are_separate() -> None:
    snapshot = load_snapshot()
    optional = snapshot["custom_agents"]["optional_config_fields"]
    hooks = snapshot["hook_capabilities"]

    for field in ("model", "model_reasoning_effort", "sandbox_mode"):
        assert field in optional
    assert hooks["observes_active_model"] is True
    assert hooks["observes_agent_type"] is True
    assert hooks["observes_reasoning_effort"] is False


def test_capability_dimensions_do_not_conflate_goal_hooks_or_subagents() -> None:
    dimensions = load_snapshot()["capability_dimensions"]
    workflow = {row["name"]: row["status"] for row in dimensions["workflow_modes"]}
    vehicles = {row["name"]: row["status"] for row in dimensions["step_vehicles"]}
    continuation = {row["name"]: row["status"] for row in dimensions["continuation"]}

    assert continuation["goal"] == "explicit-only"
    assert workflow["source-workflow"] == "unsupported"
    assert workflow["verified-workflow"] == "planned-unproved"
    assert vehicles["generic-subagent"] == "available"
    assert {"goal", "hooks", "fork"}.isdisjoint(vehicles)


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
    for forbidden_value in (
        "auth.json",
        "/users/",
        ".codex/plugins/cache",
        "bearer",
        "password",
    ):
        assert forbidden_value not in text
