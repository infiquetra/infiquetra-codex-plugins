"""Gate the codex#54 lease-registry forward-compatibility port contract.

`scripts/port_contract.py validate` is permanently pinned to the 2026-07-11 external-advisory
port — its `port_id`, refs, row counts, and digests. Per DECISIONS *2026-07-19: Lease-Safe
Substrate Ports Byte-Faithful, Gates Per-Port*, release gating therefore runs through a per-port
pytest contract rather than by unfreezing the shared CLI validator. This module is that gate for
`docs/portability/ports/2026-07-26-lease-registry-forward-compat.json`.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from scripts import port_contract

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/portability/ports/2026-07-26-lease-registry-forward-compat.json"
CLASSIFICATION_PATH = (
    ROOT / "docs/portability/classifications/2026-07-26-lease-registry-forward-compat.md"
)
VERSION_POLICY_PATH = (
    ROOT / "docs/portability/ports/2026-07-26-lease-registry-forward-compat-version-policy.json"
)

# `1648a21b` IS the claude#617 merge ("registry schema forward-compatibility"); `4eb2fe15` is its
# parent. The range is chosen, not convenient — see the two invariants pinned below.
SOURCE_BASE = "4eb2fe155bbb3c96606532f73e7fc1df4bc93c72"
SOURCE_TARGET = "1648a21b26115d2bc59ed45857af4b58545f2bee"
CLAUDE_ORIGIN_MAIN = "b464d090fccb59d0ff862f273902f1653f1d8835"

SOURCE_PATHSPECS = [
    "plugins/fleet-core/scripts/fleet_commons/lease_broker.py",
    "plugins/saga/scripts/lease_broker.py",
]

EXPECTED_ROWS = {
    "plugins/fleet-core/scripts/fleet_commons/lease_broker.py": (
        "codex-adapt",
        ["U1", "U2", "U3", "U4"],
    ),
    "plugins/saga/scripts/lease_broker.py": ("codex-adapt", ["U4"]),
}

# R10 excludes these as unrelated claude drift. The exclusion is enforced structurally by the
# frozen range: every one already exists at SOURCE_BASE, so none can land under a contract row.
EXCLUDED_DRIFT_SYMBOLS = [
    "_renew_batch_member",
    "_renew_live_batch_siblings",
    "record_child_terminal",
    "assert_write_target",
]

AUTHORITY = ROOT / "plugins/fleet-core/scripts/fleet_commons/lease_broker.py"
ADAPTER = ROOT / "plugins/saga/scripts/lease_broker.py"

def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _source_repo(port_source_oracle: Callable[[Path, str], Path]) -> Path:
    return port_source_oracle(ROOT, _manifest()["source"]["repository_id"])


def test_manifest_validates_at_the_classification_stage() -> None:
    errors = port_contract.validate_manifest(ROOT, _manifest(), stage="classification")

    assert errors == []


def test_frozen_range_and_pathspecs_are_exactly_the_617_payload() -> None:
    source = _manifest()["source"]

    assert source["base_ref"] == SOURCE_BASE
    assert source["target_ref"] == SOURCE_TARGET
    assert source["pathspecs"] == SOURCE_PATHSPECS
    assert source["repository_id"] == "infiquetra/infiquetra-claude-plugins"


def test_expected_count_and_inventory_digest_are_derived_not_hand_written(
    port_source_oracle: Callable[[Path, str], Path],
) -> None:
    """codex#45's P1 #5 was a file ported under zero contract rows while the CLI still exited 0.

    `validate --stage classification` checks the rows a contract HAS, not the ones it should have,
    so the only real guard is that the count and digest come from the base->target diff. Re-derive
    them here and require an exact match.
    """

    repo = _source_repo(port_source_oracle)
    source = _manifest()["source"]
    rows = port_contract.normalize_inventory(
        port_contract.git_inventory(repo, SOURCE_BASE, SOURCE_TARGET, SOURCE_PATHSPECS)
    )

    assert source["expected_count"] == len(rows)
    assert source["expected_count"] == len(source["rows"])
    assert source["inventory_sha256"] == port_contract.inventory_digest(rows)


def test_every_changed_source_path_has_a_row(
    port_source_oracle: Callable[[Path, str], Path],
) -> None:
    """The inverse of the P1 #5 failure: no path in the frozen diff may be missing a row."""

    repo = _source_repo(port_source_oracle)
    changed = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "diff",
            "--name-only",
            SOURCE_BASE,
            SOURCE_TARGET,
            "--",
            *SOURCE_PATHSPECS,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    row_paths = {row["new_path"] for row in _manifest()["source"]["rows"]}

    assert set(changed) == row_paths == set(SOURCE_PATHSPECS)


def test_frozen_target_is_byte_equivalent_to_claude_origin_main_for_these_paths(
    port_source_oracle: Callable[[Path, str], Path],
) -> None:
    """The range is not stale: neither file has moved since the #617 merge."""

    repo = _source_repo(port_source_oracle)
    moved = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "diff",
            "--name-only",
            SOURCE_TARGET,
            CLAUDE_ORIGIN_MAIN,
            "--",
            *SOURCE_PATHSPECS,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()

    assert moved == []


def test_excluded_drift_predates_the_frozen_range(
    port_source_oracle: Callable[[Path, str], Path],
) -> None:
    """R10 is enforced by the range itself, not by reviewer discipline.

    Each excluded symbol already exists at SOURCE_BASE, so it is outside the diff the contract
    derives its rows from and cannot land under a row.
    """

    repo = _source_repo(port_source_oracle)
    before = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "show",
            f"{SOURCE_BASE}:plugins/fleet-core/scripts/fleet_commons/lease_broker.py",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    for symbol in EXCLUDED_DRIFT_SYMBOLS:
        assert symbol in before, f"{symbol} should predate the frozen range"


def test_rows_carry_the_expected_treatment_and_units() -> None:
    rows = {row["new_path"]: row for row in _manifest()["source"]["rows"]}

    assert set(rows) == set(EXPECTED_ROWS)
    for path, (treatment, units) in EXPECTED_ROWS.items():
        assert rows[path]["treatment"] == treatment
        assert rows[path]["units"] == units
        assert rows[path]["state"] == "verified"
        assert rows[path]["evidence_refs"], f"{path}: verified state requires evidence"


def test_no_codex_drift_rows_because_plan_and_execution_bases_match() -> None:
    codex = _manifest()["codex"]

    assert codex["historical_plan_base"] == codex["execution_base"]
    assert codex["expected_count"] == 0
    assert codex["rows"] == []


def test_r9_isolation_appears_in_neither_broker() -> None:
    """The acceptance criterion from the issue, gated at release rather than only in unit tests."""

    assert "isolation" not in AUTHORITY.read_text(encoding="utf-8")
    assert "isolation" not in ADAPTER.read_text(encoding="utf-8")


def test_version_policy_ships_one_release_unit_across_both_plugins() -> None:
    """KTD8: the adapter's CLI verbs are inert without the authority's methods, so they ship
    together rather than as split versions."""

    policy = json.loads(VERSION_POLICY_PATH.read_text(encoding="utf-8"))
    by_plugin = {entry["current_codex_identity"]: entry for entry in policy}

    assert set(by_plugin) == {"fleet-core", "saga"}
    assert {entry["release_unit"] for entry in policy} == {"U5"}
    assert by_plugin["fleet-core"]["target_codex_version"] == "0.13.0"
    assert by_plugin["saga"]["target_codex_version"] == "0.81.0"


def test_manifest_serializes_byte_exactly_under_the_shared_normal_form() -> None:
    """codex#45 hit a tool writeback that emitted 1-space indent and needed renormalizing.

    Pin the normal form so a reformat is a test failure rather than a silent diff.
    """

    raw = MANIFEST_PATH.read_bytes()
    expected = (
        json.dumps(json.loads(raw.decode("utf-8")), indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    assert raw == expected


def test_generated_classification_is_current() -> None:
    rendered = port_contract.render_manifest(_manifest())

    assert CLASSIFICATION_PATH.read_text(encoding="utf-8") == rendered
