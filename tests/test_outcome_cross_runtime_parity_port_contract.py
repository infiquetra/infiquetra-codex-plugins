"""Gate the outcome cross-runtime parity port contract (#34): #604 discovery/status/handoff."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import port_contract

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/portability/ports/2026-07-19-outcome-cross-runtime-parity.json"
CLASSIFICATION_PATH = (
    ROOT / "docs/portability/classifications/2026-07-19-outcome-cross-runtime-parity.md"
)
VERSION_POLICY_PATH = (
    ROOT / "docs/portability/ports/2026-07-19-outcome-cross-runtime-parity-version-policy.json"
)

SOURCE_BASE = "30bde209a5f56822366e0bb9005317798576338d"
SOURCE_TARGET = "97d2fb15dbed7ea210391e3fc293fb0de31dc95e"
CODEX_PLAN_BASE = "3723a8183e3ea9c372ad9f34fd18f4170c36d26f"
CODEX_EXECUTION_BASE = "3723a8183e3ea9c372ad9f34fd18f4170c36d26f"
SOURCE_INVENTORY_SHA256 = "b0bdb4758882fcc39e47c3f9c6554875ba0af49661e80f6c3f67a2935d6d2f3e"
CODEX_INVENTORY_SHA256 = "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"

# Frozen treatment per source row. Ported rows (direct-port/codex-adapt) must carry planned
# targets, tests, and units; reject rows must not claim any implementation surface.
SOURCE_TREATMENTS = {
    ".claude-plugin/marketplace.json": "reject",
    "docs/engineering-journal/LEARNINGS.md": "reject",
    "docs/evidence/issue-604/artifacts/2f16c54c3da662f9a45b0c9e27b1bd8498928a0ce2641a9265d1d9392c659eed.md": "reject",
    "docs/evidence/issue-604/artifacts/3b2503ad96f47855eca2e80fbe794a0208300281ca17f51d3d5af01d35c60f38.md": "reject",
    "docs/evidence/issue-604/artifacts/52124b8c55aa638a70d24839ee1562d4b221bd71ee36ea440543de8f6cea5c5e.md": "reject",
    "docs/evidence/issue-604/criteria-qa-85e67b15fd8785f7ab6b5e635673ef20edd332c7.json": "reject",
    "docs/evidence/issue-604/ledger.head": "reject",
    "docs/evidence/issue-604/ledger.jsonl": "reject",
    "docs/work-sessions/2026-07-18-issue-604-cross-runtime-contract.md": "reject",
    "plugins/saga/.claude-plugin/plugin.json": "codex-adapt",
    "plugins/saga/CHANGELOG.md": "codex-adapt",
    "plugins/saga/references/outcome-cross-runtime.md": "codex-adapt",
    "plugins/saga/scripts/outcome.py": "codex-adapt",
    "plugins/saga/scripts/outcome_compat.py": "codex-adapt",
    "plugins/saga/skills/outcome/SKILL.md": "codex-adapt",
    "tests/fixtures/outcome-cross-runtime/v1/canonical-status.json": "direct-port",
    "tests/fixtures/outcome-cross-runtime/v1/compatibility-halt.json": "direct-port",
    "tests/fixtures/outcome-cross-runtime/v1/discovery-envelope.json": "direct-port",
    "tests/fixtures/outcome-cross-runtime/v1/handoff-reference.json": "direct-port",
    "tests/fixtures/outcome-cross-runtime/v1/invalid/future-protocol-envelope.json": "direct-port",
    "tests/fixtures/outcome-cross-runtime/v1/invalid/unknown-field-envelope.json": "direct-port",
    "tests/test_liveness_consumer_conformance.py": "reject",
    "tests/test_outcome_command.py": "codex-adapt",
    "tests/test_outcome_cross_runtime_contract.py": "codex-adapt",
    "tests/test_saga_plugin.py": "reject",
}

U2_SOURCE_ROWS = {
    "tests/fixtures/outcome-cross-runtime/v1/canonical-status.json",
    "tests/fixtures/outcome-cross-runtime/v1/compatibility-halt.json",
    "tests/fixtures/outcome-cross-runtime/v1/discovery-envelope.json",
    "tests/fixtures/outcome-cross-runtime/v1/handoff-reference.json",
    "tests/fixtures/outcome-cross-runtime/v1/invalid/future-protocol-envelope.json",
    "tests/fixtures/outcome-cross-runtime/v1/invalid/unknown-field-envelope.json",
}

U4_SOURCE_ROWS = {
    "plugins/saga/scripts/outcome_compat.py",
    "tests/test_outcome_cross_runtime_contract.py",
}

U5_SOURCE_ROWS = {
    "plugins/saga/.claude-plugin/plugin.json",
    "plugins/saga/CHANGELOG.md",
    "plugins/saga/references/outcome-cross-runtime.md",
    "plugins/saga/scripts/outcome.py",
    "plugins/saga/skills/outcome/SKILL.md",
    "tests/test_outcome_command.py",
}


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def test_classification_freezes_exact_authority_and_inventories() -> None:
    manifest = _manifest()
    source = manifest["source"]
    codex = manifest["codex"]

    assert manifest["port_id"] == "outcome-cross-runtime-parity-2026-07-19"
    assert source["base_ref"] == SOURCE_BASE
    assert source["target_ref"] == SOURCE_TARGET
    assert set(source["pathspecs"]) == set(SOURCE_TREATMENTS)
    assert len(source["pathspecs"]) == len(SOURCE_TREATMENTS)
    assert source["expected_count"] == len(source["rows"]) == 25
    assert source["inventory_sha256"] == SOURCE_INVENTORY_SHA256
    assert port_contract.inventory_digest(source["rows"]) == source["inventory_sha256"]

    assert codex["historical_plan_base"] == CODEX_PLAN_BASE
    assert codex["execution_base"] == CODEX_EXECUTION_BASE
    assert codex["expected_count"] == len(codex["rows"]) == 0
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
        if expected_treatment in {"codex-adapt", "direct-port"}:
            assert row["planned_targets"], path
            assert row["planned_tests"], path
            assert row["units"], path
        else:
            assert row["units"] == [], path
            assert row["planned_targets"] == [], path
            assert row["planned_tests"] == [], path
        if row["host_primitives"]:
            assert expected_treatment in {"reject", "defer"}, path


def test_codex_preservation_drift_is_empty_by_construction() -> None:
    """The 2026-07-19 plan refresh re-grounded the plan at the execution base (3723a818),
    so plan-to-execution preservation drift is empty by construction, not by omission."""
    manifest = _manifest()
    assert manifest["codex"]["historical_plan_base"] == manifest["codex"]["execution_base"]
    assert manifest["codex"]["rows"] == []


def test_unit_row_sets_partition_the_ported_rows() -> None:
    ported = {
        path
        for path, treatment in SOURCE_TREATMENTS.items()
        if treatment in {"codex-adapt", "direct-port"}
    }
    unit_sets = [U2_SOURCE_ROWS, U4_SOURCE_ROWS, U5_SOURCE_ROWS]
    assert set().union(*unit_sets) == ported
    assert sum(len(unit_set) for unit_set in unit_sets) == len(ported)
    rows = {row["new_path"]: row for row in _manifest()["source"]["rows"]}
    for unit, unit_set in (("U2", U2_SOURCE_ROWS), ("U4", U4_SOURCE_ROWS), ("U5", U5_SOURCE_ROWS)):
        for path in unit_set:
            assert rows[path]["units"] == [unit], path


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
    expected_policy = [
        {
            "current_codex_identity": "saga",
            "current_codex_version": "0.76.0+codex.20260719174556",
            "policy": "lineage-with-codex-adaptation",
            "release_unit": "U5",
            "source_plugin": "saga",
            "source_version": "0.103.0",
            "target_codex_identity": "saga",
            "target_codex_version": "0.77.0",
        }
    ]
    assert _manifest()["version_policy"] == expected_policy
    assert json.loads(VERSION_POLICY_PATH.read_text(encoding="utf-8")) == expected_policy


def test_capability_snapshot_records_v1_contract_and_parity_refs() -> None:
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
    assert snapshot["refs"]["claude"]["source_base"] == SOURCE_BASE
    assert snapshot["refs"]["claude"]["source_target"] == SOURCE_TARGET
    assert snapshot["refs"]["codex"]["execution_base"] == CODEX_EXECUTION_BASE


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ({"available": False}, "must record v1 spawn availability"),
        (
            {"spawn_receipt_fields": ["agent_nickname", "agent_role"]},
            "must attest nickname, role, and depth",
        ),
        ({"per_child_sandbox": True}, "must not claim direct per-child sandbox override"),
        (
            {"named_profile_selection": "unproved"},
            "named-profile selection must be rollout-attested",
        ),
    ],
)
def test_capability_snapshot_validator_rejects_each_dishonest_v1_claim(
    tmp_path: Path, mutation: dict[str, Any], expected_error: str
) -> None:
    """Deletion-mutation guard: each v1 honesty assertion must individually reject a dishonest
    snapshot — the honest-artifact test alone cannot catch a deleted validator branch."""
    manifest = _manifest()
    capability = manifest["authority"]["capability_snapshot"]
    snapshot = json.loads((ROOT / capability["path"]).read_text(encoding="utf-8"))
    snapshot["collaboration"]["spawn"].update(mutation)
    (tmp_path / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
    (tmp_path / "schema.json").write_text(
        (ROOT / capability["schema_path"]).read_text(encoding="utf-8"), encoding="utf-8"
    )

    errors: list[str] = []
    port_contract._validate_capability_snapshot(
        tmp_path, {"path": "snapshot.json", "schema_path": "schema.json"}, errors
    )

    assert any(expected_error in error for error in errors), errors


def test_u2_fixture_rows_are_verified_with_current_evidence() -> None:
    _assert_unit_rows_verified("U2", U2_SOURCE_ROWS)


def test_u3_canonical_status_evidence_is_recorded() -> None:
    """U3 has no dedicated source row (status logic lives inside the U4-completing module);
    its acceptance evidence is still a required, digest-current manifest entry."""
    manifest = _manifest()
    entries = [entry for entry in manifest["evidence"] if entry["unit"] == "U3"]
    assert entries, "U3 evidence missing"
    for entry in entries:
        assert entry["kind"] in port_contract.EVIDENCE_KINDS
        assert entry["exit_code"] == 0
        assert _sha256(ROOT / entry["artifact_path"]) == entry["artifact_sha256"]


def test_u4_handoff_rows_are_verified_with_current_evidence() -> None:
    _assert_unit_rows_verified("U4", U4_SOURCE_ROWS)


def test_u5_release_rows_are_verified_with_current_evidence() -> None:
    _assert_unit_rows_verified("U5", U5_SOURCE_ROWS)


def test_release_version_pins_are_coherent() -> None:
    """Every surface pinning the saga release tells the same 0.77.0 story."""
    manifest_version = json.loads(
        (ROOT / "plugins/saga/.codex-plugin/plugin.json").read_text(encoding="utf-8")
    )["version"]
    assert manifest_version.split("+codex.")[0] == "0.77.0"
    inventory = json.loads(
        (ROOT / "docs/validation/saga-family-target-inventory.json").read_text(encoding="utf-8")
    )
    saga_rows = [entry["version"] for entry in inventory["plugins"] if entry.get("name") == "saga"]
    assert saga_rows == [manifest_version]
    changelog = (ROOT / "plugins/saga/CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 0.77.0 - 2026-07-20" in changelog


def test_dispatcher_lease_seam_stays_dormant_ktd6() -> None:
    """Operator decision 2026-07-19 (plan KTD6): this port must not activate the repository-wide
    dispatcher lease seam; `default_lease_authority` wiring belongs to cross-runtime-acceptance."""
    outcome_py = (ROOT / "plugins/saga/scripts/outcome.py").read_text(encoding="utf-8")
    assert "default_lease_authority" not in outcome_py


def test_release_surfaces_are_coherent_for_cutover() -> None:
    """Cutover gate (U5): drained refresh queue, floor-safe release versions, bound release evidence."""
    manifest = _manifest()
    assert manifest["refresh_changes"] == []

    for row in manifest["version_policy"]:
        plugin = row["target_codex_identity"]
        actual = json.loads(
            (ROOT / f"plugins/{plugin}/.codex-plugin/plugin.json").read_text(encoding="utf-8")
        )["version"]
        # The #34 atomic release is a historical fact: the changelog must record it, and the live
        # version may be newer but never behind it. Pinning the current version here would break on
        # the first legitimate release after #34 (release-event-guard-floor precedent,
        # infiquetra-claude-plugins#604).
        released = row["target_codex_version"]
        changelog = (ROOT / f"plugins/{plugin}/CHANGELOG.md").read_text(encoding="utf-8")
        assert f"## {released} " in changelog, (plugin, released)
        live = tuple(int(part) for part in actual.split("+codex.")[0].split("."))
        floor = tuple(int(part) for part in released.split("."))
        assert live >= floor, (plugin, actual)

    evidence = {entry["evidence_id"]: entry for entry in manifest["evidence"]}
    expected_kinds = {
        "review": "review",
        "isolated_install": "isolated-install",
        "fresh_session": "fresh-session",
        "rollback": "rollback",
        "cutover": "cutover",
    }
    for key, kind in expected_kinds.items():
        reference = manifest["release_evidence"][key]
        assert reference, key
        entry = evidence[reference]
        assert entry["kind"] == kind and entry["unit"] == "U5" and entry["exit_code"] == 0, key
        assert _sha256(ROOT / entry["artifact_path"]) == entry["artifact_sha256"], key
