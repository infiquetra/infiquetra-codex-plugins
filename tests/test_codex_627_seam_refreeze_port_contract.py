"""Gate the codex#45 re-freeze port contract (#627 seam) and the promoted COR3 defers.

U1 of `docs/plans/2026-07-25-codex-refreeze-627-seam-and-cor3-worktree-authority-plan.md`
writes no production code: its deliverable is a classified contract that passes
`validate --stage classification`, plus the promotion of three orphaned defers in the
predecessor contract (R4b). These are that unit's oracles.
"""

from __future__ import annotations

import copy
import json
import os
from argparse import Namespace
from pathlib import Path

import pytest

from scripts import port_contract

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/portability/ports/2026-07-25-codex-627-seam-refreeze.json"
CLASSIFICATION_PATH = (
    ROOT / "docs/portability/classifications/2026-07-25-codex-627-seam-refreeze.md"
)
PREDECESSOR_PATH = ROOT / "docs/portability/ports/2026-07-19-lease-safe-substrate.json"

# R4: the range chains exactly off the predecessor contract's frozen target, so there is no gap
# and no re-freeze of an already-frozen range.
SOURCE_BASE = "cf15a09f8ffe9bf7c6f1218b2c72a8143d60ab49"
SOURCE_TARGET = "b464d090fccb59d0ff862f273902f1653f1d8835"

SOURCE_PATHSPECS = [
    "plugins/saga/scripts/outcome_compat.py",
    "plugins/fleet-core/scripts/fleet_commons/audit_store.py",
    "plugins/fleet-core/scripts/fleet_commons/lease_broker.py",
    "plugins/saga/scripts/outcome.py",
    "plugins/saga/scripts/outcome_dispatcher.py",
]

# Unit map from the plan: U2 byte re-freeze, U3 broker refuse-mode, U4 dispatcher + reconcile.
EXPECTED_ROWS = {
    "plugins/saga/scripts/outcome_compat.py": ("direct-port", ["U2"]),
    "plugins/fleet-core/scripts/fleet_commons/audit_store.py": ("codex-adapt", ["U2"]),
    "plugins/fleet-core/scripts/fleet_commons/lease_broker.py": ("codex-adapt", ["U3"]),
    "plugins/saga/scripts/outcome_dispatcher.py": ("codex-adapt", ["U4"]),
    "plugins/saga/scripts/outcome.py": ("codex-adapt", ["U4"]),
}

# R4b: promoted in the predecessor contract, claiming a unit id free in *that* manifest.
PROMOTED_PREDECESSOR_ROWS = {
    "plugins/saga/scripts/outcome_worktrees.py",
    "tests/test_outcome_worktrees.py",
}
PROMOTED_UNIT = "U6"

SOURCE_REPO_ENV = "CODEX_PORT_SOURCE_REPO"
DEFAULT_SOURCE_REPO = ROOT.parent / "infiquetra-claude-plugins"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _predecessor() -> dict:
    return json.loads(PREDECESSOR_PATH.read_text(encoding="utf-8"))


def _source_repo() -> Path:
    candidate = Path(os.environ.get(SOURCE_REPO_ENV, str(DEFAULT_SOURCE_REPO)))
    if not (candidate / ".git").exists():
        pytest.skip(
            f"Claude source clone unavailable at {candidate}; "
            f"set {SOURCE_REPO_ENV} to run the frozen-source oracles"
        )
    return candidate


def test_classification_gate_passes_on_the_new_contract() -> None:
    """U1's completion condition: `validate --stage classification` exits 0, not 'files written'."""
    assert port_contract.validate_manifest(ROOT, _manifest(), stage="classification") == []


def test_classification_render_is_current() -> None:
    manifest = _manifest()
    assert manifest["authority"]["classification_path"] == str(
        CLASSIFICATION_PATH.relative_to(ROOT)
    )
    assert CLASSIFICATION_PATH.read_text(encoding="utf-8") == port_contract.render_manifest(
        manifest
    )


def test_frozen_range_chains_off_the_predecessor_target() -> None:
    source = _manifest()["source"]

    assert source["base_ref"] == SOURCE_BASE
    assert source["target_ref"] == SOURCE_TARGET
    assert _predecessor()["source"]["target_ref"] == SOURCE_BASE
    assert source["pathspecs"] == SOURCE_PATHSPECS


def test_expected_count_is_derived_from_rows_not_from_pathspecs() -> None:
    """`port_contract.build_manifest` sets expected_count = len(source_rows) from the
    base->target diff. The invariant is row-derived: the pathspec count is not an input to it,
    and five rows over five pathspecs here is a coincidence, not the rule."""
    source = _manifest()["source"]

    assert source["expected_count"] == len(source["rows"]) == 5

    # Deletion-mutation guard: a manifest whose row list moves must move expected_count with it,
    # and adding a pathspec that produced no row must not change it.
    drifted = copy.deepcopy(_manifest())
    drifted["source"]["rows"] = drifted["source"]["rows"][:-1]
    errors = port_contract.validate_manifest(ROOT, drifted, stage="classification")
    assert any("expected_count does not match rows" in error for error in errors), errors

    widened = copy.deepcopy(_manifest())
    widened["source"]["pathspecs"] = [
        *SOURCE_PATHSPECS,
        "plugins/saga/scripts/outcome_worktrees.py",
    ]
    assert widened["source"]["expected_count"] == len(widened["source"]["rows"]) == 5


def test_inventory_digest_recomputes_to_the_recorded_value() -> None:
    source = _manifest()["source"]

    assert port_contract.inventory_digest(source["rows"]) == source["inventory_sha256"]


def test_every_source_row_is_classified_with_its_planned_unit() -> None:
    rows = {row["new_path"]: row for row in _manifest()["source"]["rows"]}

    assert set(rows) == set(EXPECTED_ROWS)
    for path, (treatment, units) in EXPECTED_ROWS.items():
        row = rows[path]
        assert row["state"] == "classified", path
        assert row["treatment"] == treatment, path
        assert row["units"] == units, path
        assert row["rationale"].strip(), path
        assert row["planned_targets"], path
        assert row["planned_tests"], path


def test_no_row_is_left_unclassified() -> None:
    for row in _manifest()["source"]["rows"]:
        assert row["state"] != "unclassified", row["new_path"]
        assert row["treatment"] is not None, row["new_path"]
    for row in _manifest()["codex"]["rows"]:
        assert row["state"] != "unclassified", row["new_path"]
        assert row["treatment"] is not None, row["new_path"]


def test_every_planned_target_exists_in_the_codex_tree() -> None:
    """KTD6 trap guard: `lease_broker.py`, `outcome.py`, `outcome_compat.py`,
    `outcome_dispatcher.py`, and `outcome_worktrees.py` all exist at the same relative path in
    both repositories, so a planned target that names a Claude-only path would send an
    implementer into the wrong tree without any test noticing."""
    targets = {target for row in _manifest()["source"]["rows"] for target in row["planned_targets"]}
    targets |= {
        target
        for row in _predecessor()["source"]["rows"]
        if row["new_path"] in PROMOTED_PREDECESSOR_ROWS
        for target in row["planned_targets"]
        if row["surface_kind"] != "test"
    }

    assert targets
    for target in sorted(targets):
        assert (ROOT / target).is_file(), target


def test_planned_artifacts_not_yet_written_resolve_to_a_real_codex_directory() -> None:
    """U2 has landed (`plugins/saga/tests/test_outcome_compat.py` now exists); the modules U4 and
    U5 still create do not exist yet, so `is_file` cannot guard them. Their parent directory still
    must be a real Codex test root -- naming `tests/` where this repo uses `plugins/saga/tests/`
    (or vice versa) is the same wrong-tree mistake KTD6 warns about."""
    planned = {
        artifact
        for manifest in (_manifest(), _predecessor())
        for row in manifest["source"]["rows"]
        for artifact in [*row["planned_targets"], *row["planned_tests"]]
    }
    pending = sorted(artifact for artifact in planned if not (ROOT / artifact).is_file())

    assert pending == [
        "plugins/saga/tests/test_outcome_dispatcher.py",
        "plugins/saga/tests/test_outcome_worktrees.py",
    ]
    for artifact in pending:
        assert (ROOT / artifact).parent.is_dir(), artifact


def test_broker_row_targets_the_fleet_core_copy_not_the_saga_copy() -> None:
    """KTD6: only `plugins/fleet-core/scripts/fleet_commons/lease_broker.py` carries
    `_drop_superseded_resource_lease`; a port into the same-named saga copy is a silent no-op."""
    rows = {row["new_path"]: row for row in _manifest()["source"]["rows"]}
    row = rows["plugins/fleet-core/scripts/fleet_commons/lease_broker.py"]

    assert row["planned_targets"] == ["plugins/fleet-core/scripts/fleet_commons/lease_broker.py"]
    assert "plugins/saga/scripts/lease_broker.py" not in row["planned_targets"]


def test_promoted_defers_claim_a_unit_id_free_in_the_predecessor_manifest() -> None:
    """R4b: codex#34 closed on 2026-07-20 without treating these rows, so codex#45 discharges
    them in place. U2-U5 are already claimed in that manifest; the promotion must not reuse one."""
    predecessor = _predecessor()
    rows = {row["new_path"]: row for row in predecessor["source"]["rows"]}

    other_claims = {
        unit
        for section in ("source", "codex")
        for row in predecessor[section]["rows"]
        for unit in row["units"]
        if row["new_path"] not in PROMOTED_PREDECESSOR_ROWS
    }
    assert PROMOTED_UNIT in port_contract.UNIT_IDS
    assert PROMOTED_UNIT not in other_claims, other_claims

    for path in PROMOTED_PREDECESSOR_ROWS:
        row = rows[path]
        assert row["treatment"] == "codex-adapt", path
        assert row["state"] == "classified", path
        assert row["units"] == [PROMOTED_UNIT], path
        assert row["planned_targets"], path
        assert row["planned_tests"], path
        assert "#45" in row["rationale"], path
        assert "#34" in row["rationale"], path


def test_predecessor_outcome_py_defer_is_re_justified_and_claims_no_unit() -> None:
    rows = {row["new_path"]: row for row in _predecessor()["source"]["rows"]}
    row = rows["plugins/saga/scripts/outcome.py"]

    assert row["treatment"] == "defer"
    assert row["units"] == []
    assert "2026-07-25" in row["rationale"]
    assert "2026-07-25-codex-627-seam-refreeze.json" in row["rationale"]


def test_promotion_left_the_frozen_predecessor_inventory_untouched() -> None:
    """A classification edit must not move the frozen inventory; if it did, `verify-source`
    would fail and the promotion would be a re-freeze in disguise."""
    source = _predecessor()["source"]

    assert port_contract.inventory_digest(source["rows"]) == source["inventory_sha256"]
    assert source["inventory_sha256"] == (
        "60d5875752cff31e9f9e1900bff4a942f319e21b2b13e8c4f29c829fc3080afa"
    )


def test_verify_source_passes_against_the_pinned_claude_clone() -> None:
    result = port_contract.verify_source(_source_repo(), _manifest())

    assert result["verified"] is True
    assert result["base_ref"] == SOURCE_BASE
    assert result["target_ref"] == SOURCE_TARGET
    assert result["row_count"] == 5
    assert result["inventory_sha256"] == _manifest()["source"]["inventory_sha256"]


def test_verify_source_still_passes_on_the_predecessor_after_promotion() -> None:
    result = port_contract.verify_source(_source_repo(), _predecessor())

    assert result["verified"] is True
    assert result["target_ref"] == SOURCE_BASE
    assert result["row_count"] == 46


def test_worktrees_row_cannot_be_re_derived_from_the_new_range() -> None:
    """R4b's structural premise: `outcome_worktrees.py` has zero changed lines across the frozen
    range, so a new contract yields no row for it and promotion is the only available treatment."""
    inventory = port_contract.git_inventory(
        _source_repo(),
        SOURCE_BASE,
        SOURCE_TARGET,
        ["plugins/saga/scripts/outcome_worktrees.py"],
    )

    assert inventory == []


def test_expected_count_matches_the_live_diff_row_count() -> None:
    source = _manifest()["source"]
    inventory = port_contract.git_inventory(
        _source_repo(), SOURCE_BASE, SOURCE_TARGET, source["pathspecs"]
    )

    assert len(inventory) == source["expected_count"]
    assert port_contract.normalize_inventory(inventory) == port_contract.normalize_inventory(
        source["rows"]
    )


def test_init_refuses_to_overwrite_the_existing_contract() -> None:
    args = Namespace(manifest=str(MANIFEST_PATH.relative_to(ROOT)))

    with pytest.raises(port_contract.ContractError) as excinfo:
        port_contract.command_init(args)

    assert "refuses to overwrite" in str(excinfo.value)


def test_codex_adapt_row_without_planned_tests_fails_validation() -> None:
    rows = copy.deepcopy(_manifest()["source"]["rows"])
    for row in rows:
        if row["treatment"] == "codex-adapt":
            row["planned_tests"] = []
            break
    else:  # pragma: no cover - the contract carries codex-adapt rows by construction
        raise AssertionError("no codex-adapt row to mutate")

    errors: list[str] = []
    port_contract._validate_source_rows(rows, "classification", errors)

    assert any("requires planned targets and tests" in error for error in errors), errors


def test_defer_row_claiming_a_unit_fails_validation() -> None:
    rows = copy.deepcopy(_predecessor()["source"]["rows"])
    for row in rows:
        if row["treatment"] == "defer":
            row["units"] = ["U7"]
            break
    else:  # pragma: no cover - the predecessor carries defer rows by construction
        raise AssertionError("no defer row to mutate")

    errors: list[str] = []
    port_contract._validate_source_rows(rows, "classification", errors)

    assert any(
        "deferred/rejected rows must not claim implementation units" in error for error in errors
    ), errors


def test_version_policy_records_both_moving_plugins_for_the_release_unit() -> None:
    policies = {row["target_codex_identity"]: row for row in _manifest()["version_policy"]}

    assert set(policies) == {"saga", "fleet-core"}
    for plugin, policy in policies.items():
        assert policy["release_unit"] == "U6", plugin
        assert policy["policy"] == "lineage-with-codex-adaptation", plugin
        installed = json.loads(
            (ROOT / f"plugins/{plugin}/.codex-plugin/plugin.json").read_text(encoding="utf-8")
        )["version"]
        assert policy["current_codex_version"] == installed, plugin
