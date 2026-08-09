"""Tests for the sanitized Codex 0.147.0 V2 capability snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from scripts import port_contract, render_capability_schema
from scripts.codex_target_version import (
    CAPABILITY_SNAPSHOT_SCHEMA_VERSION,
    CODEX_TARGET_VERSION,
)


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "docs/validation/codex-runtime-capability-snapshot.json"
R3_SCHEMA_PATH = ROOT / "docs/validation/codex-runtime-capability-snapshot.schema-r3.json"
R4_SCHEMA_PATH = ROOT / "docs/validation/codex-runtime-capability-snapshot.schema-r4.json"
R3_MANIFEST_PATH = (
    ROOT / "docs/portability/ports/2026-07-29-codex-0146-native-harness.json"
)
ALIGNMENT_MANIFEST_PATH = (
    ROOT / "docs/portability/ports/2026-08-08-codex-0147-alignment.json"
)


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def test_snapshot_matches_closed_r4_schema() -> None:
    snapshot = load_snapshot()
    schema = json.loads(R4_SCHEMA_PATH.read_text(encoding="utf-8"))

    assert port_contract.validate_json_schema_instance(snapshot, schema, label="snapshot") == []
    assert schema["additionalProperties"] is False
    assert set(snapshot) == set(schema["required"]) == set(schema["properties"])
    assert snapshot["schema_version"] == CAPABILITY_SNAPSHOT_SCHEMA_VERSION
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", snapshot["captured_at"])


def test_r3_artifact_still_validates_against_unchanged_r3_schema() -> None:
    manifest = port_contract.load_manifest(R3_MANIFEST_PATH)
    capability = manifest["authority"]["capability_snapshot"]
    snapshot = json.loads(
        port_contract._historical_file_by_sha256(
            ROOT,
            capability["path"],
            capability["sha256"],
        )
    )
    schema = json.loads(
        port_contract._historical_file_by_sha256(
            ROOT,
            capability["schema_path"],
            capability["schema_sha256"],
        )
    )

    assert capability["schema_version"] == snapshot["schema_version"] == 2
    assert capability["schema_path"] == R3_SCHEMA_PATH.relative_to(ROOT).as_posix()
    assert schema["properties"]["runtime"]["properties"]["codex_cli_version"] == {
        "const": "0.146.0"
    }
    assert port_contract.validate_json_schema_instance(snapshot, schema, label="snapshot") == []


def test_r4_schema_matches_its_generator() -> None:
    assert R4_SCHEMA_PATH.read_text(encoding="utf-8") == render_capability_schema.dumps(
        render_capability_schema.build_schema()
    )


def test_port_contract_accepts_schema_version_three_and_rejects_four() -> None:
    manifest = port_contract.load_manifest(ALIGNMENT_MANIFEST_PATH)

    assert port_contract.validate_manifest(ROOT, manifest, stage="classification") == []

    manifest["authority"]["capability_snapshot"]["schema_version"] = 4
    errors = port_contract.validate_manifest(ROOT, manifest, stage="classification")

    assert "authority.capability_snapshot.schema_version must be 1, 2, or 3" in errors


def test_every_declared_r4_object_schema_is_closed() -> None:
    schema = json.loads(R4_SCHEMA_PATH.read_text(encoding="utf-8"))

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
    assert refs["claude"]["source_base"] == "95637f7056835fea66bdd0044414af480fc0fd74"
    assert refs["claude"]["source_target"] == "be6e8eac029b183056b7e4402879f15d2c85f61b"


def test_catalog_projection_reproduces_digest() -> None:
    catalog = load_snapshot()["catalog"]
    models = catalog["models"]

    assert len(models) == len({model["slug"] for model in models}) == 9
    assert (
        hashlib.sha256(port_contract.canonical_json_bytes(models)).hexdigest()
        == catalog["normalized_sha256"]
        == "7a8eaa7fc65492c2c0e0689304972eea17fec2ba4f39d06fa5d8a905f3e40868"
    )
    by_slug = {model["slug"]: model for model in models}
    assert by_slug["gpt-5.6-sol"]["supported_efforts"][-1] == "ultra"
    assert by_slug["gpt-5.6-terra"]["supported_efforts"][-1] == "ultra"
    assert "ultra" not in by_slug["gpt-5.6-luna"]["supported_efforts"]
    assert by_slug["gpt-5.6-sol"]["multi_agent_version"] == "v2"
    assert by_slug["gpt-5.6-terra"]["multi_agent_version"] == "v2"
    assert by_slug["gpt-5.6-luna"]["multi_agent_version"] == "v1"
    assert by_slug["gpt-5.6-sol-wm"]["visibility"] == "hide"
    assert by_slug["codex-auto-review"]["visibility"] == "hide"
    assert by_slug["gpt-5.6-luna"]["multi_agent_v2_override_filter"]["passes"] is True
    assert by_slug["gpt-5.6-luna"]["multi_agent_v2_collaboration"] == {
        "rule": "codex-0.147.0/collab-tools-enabled",
        "as_root": True,
        "as_child": False,
    }


def test_active_host_and_v2_contract_are_separate_truths() -> None:
    snapshot = load_snapshot()
    runtime = snapshot["runtime"]

    assert runtime["codex_cli_version"] == CODEX_TARGET_VERSION
    assert runtime["session_fact_source"] == render_capability_schema.SESSION_FACT_SOURCE
    assert snapshot["features"]["multi_agent_v2"] == {"stage": "stable", "enabled": True}
    assert runtime["multi_agent_v2_config"]["enabled"] is True
    assert runtime["configured_max_threads"] == 6
    assert runtime["configured_max_threads_key"] == "max_threads"
    assert runtime["configured_v2_total_threads"] == 7
    assert runtime["configured_v2_total_threads_source"] == "agents-plus-root"
    assert runtime["configured_max_depth"] == 1
    assert runtime["host_total_slots"] == 7
    assert runtime["effective_total_slots"] == 6
    assert runtime["effective_max_children"] == 5


def test_spawn_contract_separates_request_response_and_runtime_readback() -> None:
    spawn = load_snapshot()["collaboration"]["spawn"]

    assert spawn["contract_version"] == "v2"
    assert spawn["tool_namespace"] == "collaboration"
    assert spawn["request_fields"] == [
        "agent_type",
        "fork_turns",
        "message",
        "model",
        "reasoning_effort",
        "task_name",
    ]
    assert spawn["response_fields"] == ["agent_id", "nickname", "task_name"]
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


def test_v2_operation_inventory_and_live_matrix_status_are_explicit() -> None:
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
    assert statuses["configured-agent-selection"] == "supported"
    assert statuses["nested-delegation"] == "supported"
    assert statuses["typed-results"] == "supported"
    assert statuses["luna-leaf"] == "unavailable"
    assert statuses["ultra-root-only"] == "supported"


def test_v2_live_matrix_records_profiles_luna_decision_and_runtime_operations() -> None:
    matrix = json.loads(
        (ROOT / "docs/validation/codex-v2-orchestration-matrix.json").read_text()
    )

    assert matrix["capability_outcome"] == "supported"
    assert matrix["authentication_mode"] == "current-codex-home-reused"
    assert matrix["catalog"]["luna_multi_agent_version"] == "v1"
    assert matrix["luna_decision"]["outcome"] == "fallback-selected"
    assert [row["profile"] for row in matrix["profiles"]] == [
        "review_max",
        "review_high",
        "work_high",
        "test_medium",
        "scan_low",
        "monitor_low",
    ]
    assert all(row["multi_agent_version"] == "v2" for row in matrix["profiles"])
    assert matrix["nested_delegation"]["leaf_path"] == "/root/nested_parent/nested_leaf"
    assert matrix["lifecycle"]["operations"] == [
        "spawn_agent",
        "send_message",
        "list_agents",
        "interrupt_agent",
        "followup_task",
        "wait_agent",
    ]
    assert matrix["ultra"]["root_effective_effort"] == "ultra"
    assert matrix["ultra"]["child_ultra_effective"] is False


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
