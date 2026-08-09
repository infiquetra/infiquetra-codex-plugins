"""Tests for the staged Claude-to-Codex port contract."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from scripts import port_contract as contract


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT
    / "docs"
    / "portability"
    / "manifests"
    / "2026-07-11-external-advisory-execution.json"
)


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_current_contract_set_selects_the_codex_0147_alignment_cycle() -> None:
    assert contract.CURRENT_PORT_IDS == {"codex-0147-alignment-2026-08-08"}


def test_port_contract_accepts_evidence_units_through_u14() -> None:
    assert contract.UNIT_IDS == {f"U{number}" for number in range(1, 15)}


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
    assert len(source["rows"]) == source["expected_count"] == contract.EXPECTED_SOURCE_COUNT
    assert contract.inventory_digest(source["rows"]) == source["inventory_sha256"]
    assert len({row["row_id"] for row in source["rows"]}) == contract.EXPECTED_SOURCE_COUNT
    assert all(row["state"] in {"classified", "implemented", "verified"} for row in source["rows"])
    assert all(
        row["treatment"] in {"direct-port", "codex-adapt", "defer", "reject"}
        for row in source["rows"]
    )

    assert codex["historical_plan_base"] == contract.DEFAULT_CODEX_PLAN_BASE
    assert codex["execution_base"] == contract.APPROVED_CODEX_EXECUTION_BASE
    assert codex["evidence_ref"] == contract.CODEX_EVIDENCE_REF
    assert len(codex["rows"]) == codex["expected_count"] == contract.EXPECTED_CODEX_COUNT
    assert contract.inventory_digest(codex["rows"]) == codex["inventory_sha256"]
    assert all(row["treatment"] in {"preserve", "reconcile", "superseded-by-plan"} for row in codex["rows"])


def test_active_contract_rejects_shifted_identity_or_frozen_refs() -> None:
    manifest = load_manifest()
    manifest["port_id"] = "replacement-cycle"
    manifest["source"]["base_ref"] = "1" * 40
    manifest["source"]["target_ref"] = "2" * 40
    manifest["codex"]["historical_plan_base"] = "3" * 40
    manifest["codex"]["execution_base"] = "4" * 40
    manifest["codex"]["evidence_ref"] = "refs/tags/untrusted"

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("port_id must remain" in error for error in errors)
    assert any("source.base_ref changed" in error for error in errors)
    assert any("source.target_ref changed" in error for error in errors)
    assert any("historical plan base changed" in error for error in errors)
    assert any("execution base changed" in error for error in errors)
    assert any("codex.evidence_ref must remain" in error for error in errors)


def test_custom_contract_requires_a_safe_dedicated_evidence_tag() -> None:
    manifest = load_manifest()
    custom_plan = ROOT / "docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md"
    manifest["authority"]["plan"] = {
        "path": custom_plan.relative_to(ROOT).as_posix(),
        "sha256": contract.sha256_file(custom_plan),
    }
    manifest["codex"]["evidence_ref"] = "refs/heads/not-evidence"

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("codex.evidence_ref must be a safe evidence tag" in error for error in errors)


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


def test_source_row_construction_does_not_depend_on_manifest_authority() -> None:
    row = {
        "change": "M",
        "old_path": None,
        "new_path": "plugins/team-execution/references/reviewer-registry.md",
        "similarity": None,
    }

    result = contract._source_contract_row(row)

    assert result["surface_kind"] == "reference"
    assert result["state"] == "unclassified"
    assert result["capability_refs"] == []


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


def test_divergent_source_topology_is_closed_and_requires_dispositions() -> None:
    topology = {
        "left": {"tag": "rust-v0.146.1", "peeled_commit": "1" * 40},
        "right": {"tag": "rust-v0.147.0", "peeled_commit": "2" * 40},
        "common_base": "3" * 40,
        "left_only_commits": [
            {"commit": "4" * 40, "disposition": "Behavior is present on the right."}
        ],
    }

    assert contract._normalize_source_topology(topology) == topology

    topology["left_only_commits"][0].pop("disposition")
    errors = contract._source_topology_errors(topology)

    assert any("missing=['disposition']" in error for error in errors)
    assert any("disposition must be a non-empty printable string" in error for error in errors)


def test_init_parser_accepts_a_complete_divergent_source_topology() -> None:
    parser = contract.build_parser()
    args = parser.parse_args(
        [
            "init",
            "--source-repo",
            "/tmp/source",
            "--source-left-tag",
            "rust-v0.146.1",
            "--source-left-peeled-commit",
            "1" * 40,
            "--source-right-tag",
            "rust-v0.147.0",
            "--source-right-peeled-commit",
            "2" * 40,
            "--source-common-base",
            "3" * 40,
            "--source-left-only-commit",
            f"{'4' * 40}=Behavior is present on the right.",
        ]
    )

    assert contract._source_topology_from_args(args) == {
        "left": {"tag": "rust-v0.146.1", "peeled_commit": "1" * 40},
        "right": {"tag": "rust-v0.147.0", "peeled_commit": "2" * 40},
        "common_base": "3" * 40,
        "left_only_commits": [
            {"commit": "4" * 40, "disposition": "Behavior is present on the right."}
        ],
    }


def test_claude_only_surface_cannot_be_direct_port() -> None:
    manifest = load_manifest()
    row = manifest["source"]["rows"][0]
    row["surface_kind"] = "command"
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

    assert any("authority.runbook historical preimage" in error for error in errors)


def test_capability_schema_digest_is_part_of_the_gate() -> None:
    manifest = load_manifest()
    manifest["authority"]["capability_snapshot"]["schema_sha256"] = "0" * 64

    errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any(
        "capability_snapshot historical preimage" in error for error in errors
    )


def test_nested_capability_schema_is_closed() -> None:
    snapshot = json.loads(
        (ROOT / "docs/validation/codex-runtime-capability-snapshot.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (ROOT / "docs/validation/codex-runtime-capability-snapshot.schema-r3.json").read_text(
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
    row["evidence_refs"] = []

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


def test_evidence_can_bind_the_exact_current_target_tree() -> None:
    manifest = load_manifest()
    artifact = ROOT / "tests/test_port_contract.py"
    head = contract.resolve_ref(ROOT, contract.CODEX_EVIDENCE_REF)
    target_paths = ["AGENTS.md"]
    digest = contract.git_tree_digest(ROOT, head, target_paths)
    manifest["evidence"].append(
        {
            "evidence_id": "exact-tree-evidence",
            "unit": "U2",
            "kind": "check",
            "artifact_path": "tests/test_port_contract.py",
            "artifact_sha256": contract.sha256_file(artifact),
            "argv": ["python3", "-m", "pytest", "tests/test_port_contract.py"],
            "cwd": ".",
            "exit_code": 0,
            "recorded_at": "2026-07-11T12:00:00Z",
            "repo_head": head,
            "target_paths": target_paths,
            "target_tree_sha256": digest,
        }
    )
    errors = contract.validate_manifest(ROOT, manifest, stage="classification")
    assert not any("exact-tree-evidence" in error for error in errors)
    manifest["evidence"][-1]["target_tree_sha256"] = "0" * 64
    errors = contract.validate_manifest(ROOT, manifest, stage="classification")
    assert any("target_tree_sha256 is stale" in error for error in errors)


def test_evidence_commit_must_be_retained_by_durable_ref() -> None:
    manifest = load_manifest()
    repo_head = manifest["codex"]["execution_base"]
    evidence_head = contract.resolve_ref(ROOT, contract.CODEX_EVIDENCE_REF)
    artifact = ROOT / "tests/test_port_contract.py"
    manifest["evidence"].append(
        {
            "evidence_id": "retention-evidence",
            "unit": "U2",
            "kind": "check",
            "artifact_path": "tests/test_port_contract.py",
            "artifact_sha256": contract.sha256_file(artifact),
            "argv": ["python3", "-m", "pytest", "tests/test_port_contract.py"],
            "cwd": ".",
            "exit_code": 0,
            "recorded_at": "2026-07-12T01:20:00Z",
            "repo_head": repo_head,
        }
    )
    real_is_ancestor = contract.is_ancestor

    def fake_is_ancestor(repo: Path, base: str, target: str) -> bool:
        if base == repo_head and target == evidence_head:
            return False
        return real_is_ancestor(repo, base, target)

    with patch.object(contract, "is_ancestor", side_effect=fake_is_ancestor):
        errors = contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any("repo_head is not retained by codex.evidence_ref" in error for error in errors)


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


def test_historical_u2_unit_passes_but_retired_cutover_verifier_blocks_replay() -> None:
    manifest = load_manifest()

    unit_errors = contract.validate_manifest(ROOT, manifest, stage="unit", unit="U2")
    cutover_errors = contract.validate_manifest(ROOT, manifest, stage="cutover")

    assert unit_errors == []
    assert cutover_errors == ["cutover release-proof verifier or artifact is missing"]


def test_cutover_requires_exact_tagged_release_proof() -> None:
    manifest = load_manifest()
    failed = subprocess.CompletedProcess(
        args=["external_action_release_matrix.py"],
        returncode=1,
        stdout="",
        stderr="external action release proof invalid: evidence bundle missing\n",
    )
    with patch.object(contract.subprocess, "run", return_value=failed):
        errors = contract._validate_cutover_release_proof(ROOT, manifest)

    assert errors == ["cutover release-proof verifier or artifact is missing"]


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


def test_init_review_override_does_not_append_the_legacy_default() -> None:
    parser = contract.build_parser()

    args = parser.parse_args(
        [
            "init",
            "--source-repo",
            "../infiquetra-claude-plugins",
            "--review",
            "docs/reviews/current-review.md",
        ]
    )

    assert args.review == ["docs/reviews/current-review.md"]


def test_manifest_digest_changes_when_classification_changes() -> None:
    manifest = load_manifest()
    original = contract.canonical_json_bytes(manifest)
    modified = copy.deepcopy(manifest)
    modified["source"]["rows"][0]["rationale"] += " Changed."

    assert hashlib.sha256(original).hexdigest() != hashlib.sha256(
        contract.canonical_json_bytes(modified)
    ).hexdigest()
