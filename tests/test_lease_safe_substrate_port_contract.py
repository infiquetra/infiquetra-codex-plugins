"""Gate the lease-safe substrate port contract (#33): #351 settlement, #356 broker, #355 guard."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import port_contract

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/portability/ports/2026-07-19-lease-safe-substrate.json"
CLASSIFICATION_PATH = ROOT / "docs/portability/classifications/2026-07-19-lease-safe-substrate.md"

SOURCE_BASE = "a6f3bcff0fe9df213e2d2947afca99d5e7516393"
SOURCE_TARGET = "cf15a09f8ffe9bf7c6f1218b2c72a8143d60ab49"
CODEX_PLAN_BASE = "739fb34e27f2e045e28cf5d420bbc2fc004115a0"
CODEX_EXECUTION_BASE = "19a3610e2db8d0f850fa18ecbbb8f16c74842ba4"
SOURCE_INVENTORY_SHA256 = "60d5875752cff31e9f9e1900bff4a942f319e21b2b13e8c4f29c829fc3080afa"
CODEX_INVENTORY_SHA256 = "656bf596f67e4e65baa97648e8fea2fc39dcd306c5d5b059cbdc4b3a628276f3"

# Frozen treatment per source row (KTD3: Claude host primitives are reject/defer, never
# direct-port). Adapted rows must carry planned targets and tests; defer/reject rows must not
# claim implementation units.
SOURCE_TREATMENTS = {
    ".claude-plugin/marketplace.json": "reject",
    "plugins/fleet-core/.claude-plugin/plugin.json": "codex-adapt",
    "plugins/fleet-core/CHANGELOG.md": "codex-adapt",
    "plugins/fleet-core/README.md": "defer",
    "plugins/fleet-core/scripts/fleet_commons/audit_store.py": "codex-adapt",
    "plugins/fleet-core/scripts/fleet_commons/concurrency_policy.py": "codex-adapt",
    "plugins/fleet-core/scripts/fleet_commons/lease_broker.py": "codex-adapt",
    "plugins/fleet-core/scripts/fleet_commons/orphan_evidence.py": "codex-adapt",
    "plugins/saga/.claude-plugin/plugin.json": "codex-adapt",
    "plugins/saga/CHANGELOG.md": "codex-adapt",
    "plugins/saga/README.md": "defer",
    "plugins/saga/hooks/hooks.json": "reject",
    "plugins/saga/hooks/lease_lifecycle_hook.py": "reject",
    "plugins/saga/hooks/lease_mutation_hook.py": "reject",
    "plugins/saga/scripts/concurrency_governor.py": "defer",
    "plugins/saga/scripts/dispatch_settlement.py": "codex-adapt",
    "plugins/saga/scripts/engine_dispatch.py": "defer",
    "plugins/saga/scripts/execution_spec.py": "defer",
    "plugins/saga/scripts/lease_broker.py": "codex-adapt",
    "plugins/saga/scripts/manifest_store.py": "defer",
    "plugins/saga/scripts/outcome.py": "defer",
    "plugins/saga/scripts/outcome_dispatcher.py": "codex-adapt",
    "plugins/saga/scripts/outcome_store.py": "codex-adapt",
    "plugins/saga/scripts/outcome_worktrees.py": "defer",
    "plugins/saga/scripts/reap_orphans.py": "defer",
    "plugins/saga/scripts/run_ledger.py": "codex-adapt",
    "plugins/saga/scripts/second_opinion.py": "defer",
    "plugins/saga/scripts/workflow_emitter.py": "reject",
    "tests/test_concurrency_conformance.py": "codex-adapt",
    "tests/test_delegation_tripwire.py": "defer",
    "tests/test_dispatch_settlement.py": "codex-adapt",
    "tests/test_fleet_lease_broker.py": "codex-adapt",
    "tests/test_manifest_store.py": "defer",
    "tests/test_orphan_fencing.py": "codex-adapt",
    "tests/test_outcome_dispatcher.py": "codex-adapt",
    "tests/test_outcome_worktrees.py": "defer",
    "tests/test_pulse_telemetry.py": "defer",
    "tests/test_reap_orphans.py": "defer",
    "tests/test_review_second_opinion.py": "defer",
    "tests/test_run_ledger.py": "codex-adapt",
    "tests/test_saga_engine_dispatch.py": "defer",
    "tests/test_saga_execution_spec.py": "defer",
    "tests/test_saga_hooks.py": "reject",
    "tests/test_saga_plugin.py": "defer",
    "tests/test_saga_workflow_emitter.py": "reject",
    "tests/test_work_second_opinion.py": "defer",
}

RECONCILED_CODEX_PATHS = {
    "plugins/fleet-core/.codex-plugin/plugin.json",
    "plugins/fleet-core/CHANGELOG.md",
}

U2_SOURCE_ROWS = {
    "plugins/fleet-core/scripts/fleet_commons/audit_store.py",
    "plugins/fleet-core/scripts/fleet_commons/concurrency_policy.py",
    "plugins/fleet-core/scripts/fleet_commons/lease_broker.py",
    "plugins/fleet-core/scripts/fleet_commons/orphan_evidence.py",
    "tests/test_fleet_lease_broker.py",
    "tests/test_orphan_fencing.py",
}

U3_SOURCE_ROWS = {
    "plugins/saga/scripts/dispatch_settlement.py",
    "plugins/saga/scripts/lease_broker.py",
    "plugins/saga/scripts/outcome_dispatcher.py",
    "plugins/saga/scripts/outcome_store.py",
    "plugins/saga/scripts/run_ledger.py",
    "tests/test_dispatch_settlement.py",
    "tests/test_outcome_dispatcher.py",
    "tests/test_run_ledger.py",
}


def _assert_unit_rows_verified(unit: str, row_paths: set[str]) -> None:
    manifest = _manifest()
    rows = {row["new_path"]: row for row in manifest["source"]["rows"]}
    evidence = {entry["evidence_id"]: entry for entry in manifest["evidence"]}

    for path in row_paths:
        row = rows[path]
        assert row["state"] == "verified", path
        assert row["evidence_refs"], path
        for ref in row["evidence_refs"]:
            entry = evidence[ref]
            assert entry["unit"] == unit
            assert entry["kind"] in port_contract.EVIDENCE_KINDS
            assert entry["exit_code"] == 0
            assert _sha256(ROOT / entry["artifact_path"]) == entry["artifact_sha256"]
        for target in row["planned_targets"]:
            assert (ROOT / target).is_file(), target
        for test_path in row["planned_tests"]:
            assert (ROOT / test_path).is_file(), test_path


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_classification_freezes_exact_authority_and_inventories() -> None:
    manifest = _manifest()
    source = manifest["source"]
    codex = manifest["codex"]

    assert manifest["port_id"] == "lease-safe-substrate-2026-07-19"
    assert source["base_ref"] == SOURCE_BASE
    assert source["target_ref"] == SOURCE_TARGET
    assert set(source["pathspecs"]) == set(SOURCE_TREATMENTS)
    assert len(source["pathspecs"]) == len(SOURCE_TREATMENTS)
    assert source["expected_count"] == len(source["rows"]) == 46
    assert source["inventory_sha256"] == SOURCE_INVENTORY_SHA256
    assert port_contract.inventory_digest(source["rows"]) == source["inventory_sha256"]

    assert codex["historical_plan_base"] == CODEX_PLAN_BASE
    assert codex["execution_base"] == CODEX_EXECUTION_BASE
    assert codex["expected_count"] == len(codex["rows"]) == 80
    assert codex["inventory_sha256"] == CODEX_INVENTORY_SHA256
    assert port_contract.inventory_digest(codex["rows"]) == codex["inventory_sha256"]


def test_classification_has_one_explicit_treatment_per_source_row() -> None:
    rows = {row["new_path"]: row for row in _manifest()["source"]["rows"]}

    assert set(rows) == set(SOURCE_TREATMENTS)
    for path, expected_treatment in SOURCE_TREATMENTS.items():
        row = rows[path]
        assert row["treatment"] == expected_treatment, path
        assert row["state"] in {"classified", "implemented", "verified"}, path
        assert row["rationale"], path
        if expected_treatment == "codex-adapt":
            assert row["planned_targets"], path
            assert row["planned_tests"], path
            assert row["units"], path
        else:
            assert row["units"] == [], path
            assert row["planned_targets"] == [], path
            assert row["planned_tests"] == [], path
        if row["host_primitives"]:
            assert expected_treatment in {"reject", "defer"}, path


def test_classification_codex_drift_rows_are_all_classified() -> None:
    rows = _manifest()["codex"]["rows"]

    assert len(rows) == 80
    reconciled = {row["new_path"] for row in rows if row["treatment"] == "reconcile"}
    assert reconciled == RECONCILED_CODEX_PATHS
    for row in rows:
        assert row["treatment"] in {"preserve", "reconcile"}, row["new_path"]
        assert row["state"] in {"classified", "verified"}, row["new_path"]
        assert row["invariant"], row["new_path"]
        assert row["rationale"], row["new_path"]
        if row["treatment"] == "reconcile":
            assert row["units"] == ["U5"], row["new_path"]
        else:
            assert row["units"] == [], row["new_path"]


def test_classification_authority_hashes_and_render_are_current() -> None:
    manifest = _manifest()
    authority = manifest["authority"]
    artifacts = [authority["plan"], *authority["reviews"], authority["runbook"]]

    for artifact in artifacts:
        assert _sha256(ROOT / artifact["path"]) == artifact["sha256"]
    capability = authority["capability_snapshot"]
    assert _sha256(ROOT / capability["path"]) == capability["sha256"]
    assert _sha256(ROOT / capability["schema_path"]) == capability["schema_sha256"]
    assert (
        capability["schema_path"]
        == "docs/validation/codex-runtime-capability-snapshot.schema-r2.json"
    )
    assert CLASSIFICATION_PATH.read_text(encoding="utf-8") == (
        port_contract.render_manifest(manifest)
    )


def test_classification_preserves_independent_codex_version_lineage() -> None:
    assert _manifest()["version_policy"] == [
        {
            "current_codex_identity": "fleet-core",
            "current_codex_version": "0.8.5+codex.20260717220000",
            "policy": "lineage-with-codex-adaptation",
            "release_unit": "U5",
            "source_plugin": "fleet-core",
            "source_version": "0.15.0",
            "target_codex_identity": "fleet-core",
            "target_codex_version": "0.9.0",
        },
        {
            "current_codex_identity": "saga",
            "current_codex_version": "0.75.17+codex.20260711160644",
            "policy": "lineage-with-codex-adaptation",
            "release_unit": "U5",
            "source_plugin": "saga",
            "source_version": "0.104.0",
            "target_codex_identity": "saga",
            "target_codex_version": "0.76.0",
        },
    ]


def test_capability_snapshot_records_retired_v2_as_v1_contract() -> None:
    """multi_agent_v2 was retired to v1 (operator decision, 2026-07-19); pin the honest truth."""
    manifest = _manifest()
    capability = manifest["authority"]["capability_snapshot"]
    snapshot = json.loads((ROOT / capability["path"]).read_text(encoding="utf-8"))
    schema = json.loads((ROOT / capability["schema_path"]).read_text(encoding="utf-8"))

    assert port_contract.validate_json_schema_instance(snapshot, schema, label="snapshot") == []
    errors: list[str] = []
    port_contract._validate_capability_snapshot(ROOT, capability, errors)
    assert errors == []

    spawn = snapshot["collaboration"]["spawn"]
    assert spawn["contract_version"] == "v1"
    assert spawn["named_profile_selection"] == "rollout-attested"
    assert {"agent_nickname", "agent_role", "depth"} <= set(spawn["spawn_receipt_fields"])
    assert spawn["per_child_sandbox"] is False
    assert snapshot["runtime"]["session_fact_source"] == "operator-session-rollouts"
    assert snapshot["refs"]["claude"]["source_target"] == SOURCE_TARGET
    assert snapshot["refs"]["codex"]["execution_base"] == CODEX_EXECUTION_BASE


def test_u2_substrate_rows_are_verified_with_current_evidence() -> None:
    _assert_unit_rows_verified("U2", U2_SOURCE_ROWS)


def test_u3_settlement_rows_are_verified_with_current_evidence() -> None:
    _assert_unit_rows_verified("U3", U3_SOURCE_ROWS)
