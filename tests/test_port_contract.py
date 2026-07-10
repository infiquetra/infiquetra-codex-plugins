"""Tests for the staged Claude-to-Codex port contract."""

from __future__ import annotations

import copy
import hashlib
import json
from argparse import Namespace
from pathlib import Path

from scripts import port_contract as contract


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / contract.DEFAULT_MANIFEST


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_current_manifest_passes_classification_gate() -> None:
    manifest = load_manifest()

    assert contract.validate_manifest(ROOT, manifest, stage="classification") == []


def test_frozen_source_and_codex_inventories_are_exhaustive() -> None:
    manifest = load_manifest()
    source = manifest["source"]
    codex = manifest["codex"]

    assert source["pathspecs"] == list(contract.DEFAULT_SOURCE_PATHS)
    assert source["base_ref"] == contract.DEFAULT_SOURCE_BASE
    assert source["target_ref"] == contract.DEFAULT_SOURCE_TARGET
    assert len(source["rows"]) == source["expected_count"] == 156
    assert contract.inventory_digest(source["rows"]) == source["inventory_sha256"]
    assert len({row["row_id"] for row in source["rows"]}) == 156
    assert all(row["state"] == "classified" for row in source["rows"])
    assert all(row["treatment"] in {"direct-port", "codex-adapt", "defer", "reject"} for row in source["rows"])

    assert codex["historical_plan_base"] == contract.DEFAULT_CODEX_PLAN_BASE
    assert codex["execution_base"] == "3f639109b06ed2634d5333a58fb200b06e36dbbe"
    assert len(codex["rows"]) == codex["expected_count"] == 35
    assert contract.inventory_digest(codex["rows"]) == codex["inventory_sha256"]
    assert all(row["treatment"] in {"preserve", "reconcile", "superseded-by-plan"} for row in codex["rows"])


def test_active_contract_rejects_shifted_identity_or_frozen_refs() -> None:
    manifest = load_manifest()
    manifest["port_id"] = "replacement-cycle"
    manifest["source"]["base_ref"] = "1" * 40
    manifest["source"]["target_ref"] = "2" * 40
    manifest["codex"]["historical_plan_base"] = "3" * 40
    manifest["codex"]["execution_base"] = "4" * 40

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("port_id must remain" in error for error in errors)
    assert any("source.base_ref changed" in error for error in errors)
    assert any("source.target_ref changed" in error for error in errors)
    assert any("historical plan base changed" in error for error in errors)
    assert any("execution base changed" in error for error in errors)


def test_self_consistent_removed_codex_row_still_fails_frozen_inventory() -> None:
    manifest = load_manifest()
    manifest["codex"]["rows"].pop()
    manifest["codex"]["expected_count"] = len(manifest["codex"]["rows"])
    manifest["codex"]["inventory_sha256"] = contract.inventory_digest(
        manifest["codex"]["rows"]
    )

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("must contain exactly" in error for error in errors)
    assert any("changed from the approved" in error for error in errors)
    assert any("do not match the recorded Git refs" in error for error in errors)


def test_row_identity_ignores_classification_fields() -> None:
    manifest = load_manifest()
    row = manifest["source"]["rows"][0]

    assert contract.row_id("src", row) == row["row_id"]


def test_name_status_parser_handles_rename_delete_and_unusual_names() -> None:
    rows = contract.parse_name_status_z(
        b"R087\0old name.py\0new\tname.py\0D\0gone.py\0A\0new file.py\0"
    )

    assert rows == [
        {"change": "A", "old_path": None, "new_path": "new file.py", "similarity": None},
        {"change": "D", "old_path": "gone.py", "new_path": None, "similarity": None},
        {"change": "R", "old_path": "old name.py", "new_path": "new\tname.py", "similarity": 87},
    ]


def test_name_status_parser_rejects_non_nul_terminated_input() -> None:
    try:
        contract.parse_name_status_z(b"M\0path.py")
    except contract.ContractError as exc:
        assert "NUL terminated" in str(exc)
    else:
        raise AssertionError("unterminated name-status input was accepted")


def test_classification_rejects_unknown_schema_keys() -> None:
    manifest = load_manifest()
    manifest["unexpected"] = True

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("manifest keys mismatch" in error and "unexpected" in error for error in errors)


def test_claude_only_surface_cannot_be_direct_port() -> None:
    manifest = load_manifest()
    row = next(row for row in manifest["source"]["rows"] if row["surface_kind"] == "command")
    row["treatment"] = "direct-port"

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("Claude-only surface/primitive cannot be direct-port" in error for error in errors)


def test_codex_adaptation_requires_targets_and_tests() -> None:
    manifest = load_manifest()
    row = next(row for row in manifest["source"]["rows"] if row["treatment"] == "codex-adapt")
    row["planned_targets"] = []
    row["planned_tests"] = []

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("codex-adapt requires planned targets and tests" in error for error in errors)


def test_contract_rejects_absolute_traversal_and_cache_paths() -> None:
    for unsafe in ("/tmp/file", "../file", ".codex/plugins/cache/plugin/file"):
        try:
            contract.validate_repo_path(unsafe)
        except contract.ContractError:
            pass
        else:
            raise AssertionError(f"unsafe path was accepted: {unsafe}")


def test_contained_artifact_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (root / "link.txt").symlink_to(outside)

    try:
        contract.contained_file(root, "link.txt")
    except contract.ContractError as exc:
        assert "escapes" in str(exc)
    else:
        raise AssertionError("escaping symlink was accepted")


def test_runbook_digest_is_part_of_the_gate() -> None:
    manifest = load_manifest()
    manifest["authority"]["runbook"]["sha256"] = "0" * 64

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("authority.runbook digest is stale" in error for error in errors)


def test_capability_schema_digest_is_part_of_the_gate() -> None:
    manifest = load_manifest()
    manifest["authority"]["capability_snapshot"]["schema_sha256"] = "0" * 64

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("capability_snapshot.schema digest is stale" in error for error in errors)


def test_nested_capability_schema_is_closed() -> None:
    snapshot = json.loads(
        (ROOT / "docs/validation/codex-runtime-capability-snapshot.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (ROOT / "docs/validation/codex-runtime-capability-snapshot.schema.json").read_text(
            encoding="utf-8"
        )
    )
    snapshot["runtime"]["unexpected"] = True

    errors = contract.validate_json_schema_instance(snapshot, schema, label="snapshot")

    assert any("snapshot.runtime has unexpected keys" in error for error in errors)


def test_verified_state_without_evidence_is_rejected() -> None:
    manifest = load_manifest()
    row = manifest["source"]["rows"][0]
    row["state"] = "verified"

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("verified state requires evidence" in error for error in errors)


def test_failed_misattributed_and_malformed_evidence_is_rejected() -> None:
    manifest = load_manifest()
    row = next(row for row in manifest["source"]["rows"] if "U2" in row["units"])
    artifact = ROOT / "tests/test_port_contract.py"
    row["state"] = "verified"
    row["planned_targets"] = ["scripts/port_contract.py"]
    row["planned_tests"] = ["tests/test_port_contract.py"]
    row["evidence_refs"] = ["bad-evidence"]
    manifest["evidence"] = [
        {
            "evidence_id": "bad-evidence",
            "unit": "U9",
            "kind": "check",
            "artifact_path": "tests/test_port_contract.py",
            "artifact_sha256": contract.sha256_file(artifact),
            "argv": ["python3", "/tmp/check.py", "--token=secret"],
            "cwd": ".",
            "exit_code": 17,
            "recorded_at": "not-a-date",
            "repo_head": contract.APPROVED_CODEX_EXECUTION_BASE,
        }
    ]

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("unrelated unit" in error for error in errors)
    assert any("exit_code must be integer 0" in error for error in errors)
    assert any("timezone-aware" in error for error in errors)
    assert any("absolute or home-relative" in error for error in errors)
    assert any("secret-shaped" in error for error in errors)


def test_unit_gate_rejects_zero_claims() -> None:
    manifest = load_manifest()
    for row in [*manifest["source"]["rows"], *manifest["codex"]["rows"]]:
        row["units"] = [unit for unit in row["units"] if unit != "U2"]

    errors = contract.validate_manifest(ROOT, manifest, stage="unit", unit="U2")

    assert any("validation for U2 is vacuous" in error for error in errors)


def test_release_evidence_kind_must_match_release_slot() -> None:
    manifest = load_manifest()
    artifact = ROOT / "tests/test_port_contract.py"
    manifest["evidence"] = [
        {
            "evidence_id": "wrong-review-kind",
            "unit": "U8",
            "kind": "check",
            "artifact_path": "tests/test_port_contract.py",
            "artifact_sha256": contract.sha256_file(artifact),
            "argv": ["python3", "-m", "pytest", "tests/test_port_contract.py"],
            "cwd": ".",
            "exit_code": 0,
            "recorded_at": "2026-07-10T16:00:00Z",
            "repo_head": contract.APPROVED_CODEX_EXECUTION_BASE,
        }
    ]
    manifest["release_evidence"]["review"] = "wrong-review-kind"

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("release_evidence.review must reference `review` evidence" in error for error in errors)


def test_unit_and_cutover_stages_fail_before_their_evidence_exists() -> None:
    manifest = load_manifest()

    unit_errors = contract.validate_manifest(ROOT, manifest, stage="unit", unit="U2")
    cutover_errors = contract.validate_manifest(ROOT, manifest, stage="cutover")

    assert any("claimed by U2 but is not verified" in error for error in unit_errors)
    assert any("cutover requires" in error for error in cutover_errors)


def test_renderer_is_byte_current() -> None:
    manifest = load_manifest()
    output = ROOT / manifest["authority"]["classification_path"]

    assert output.read_text(encoding="utf-8") == contract.render_manifest(manifest)


def test_init_refuses_to_overwrite_existing_manifest() -> None:
    args = Namespace(manifest=str(contract.DEFAULT_MANIFEST))

    try:
        contract.command_init(args)
    except contract.ContractError as exc:
        assert "refuses to overwrite" in str(exc)
    else:
        raise AssertionError("init overwrote or accepted an existing contract")


def test_manifest_digest_changes_when_classification_changes() -> None:
    manifest = load_manifest()
    original = contract.canonical_json_bytes(manifest)
    modified = copy.deepcopy(manifest)
    modified["source"]["rows"][0]["rationale"] += " Changed."

    assert hashlib.sha256(original).hexdigest() != hashlib.sha256(
        contract.canonical_json_bytes(modified)
    ).hexdigest()
