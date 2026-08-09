"""Every place the superseded Luna conclusion was written down, and what was done with it.

A claim correction has two failure modes and they pull in opposite directions. Leaving a stale
operational claim in place is the obvious one. The less obvious one is over-correcting: editing a
dated record so that it says what we believe today, which destroys the evidence of what was believed
then. This module holds both ends -- current surfaces must not still assert the superseded claim,
and dated records must be byte-identical to what they said.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "docs" / "validation" / "codex-0147-negative-inventory.json"
INVENTORY = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

SUPERSEDED_CLAIM = "Luna is unavailable to MultiAgent V2"
DISPOSITIONS = frozenset({"updated", "superseded-note", "frozen"})


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# --- the inventory is complete and well formed ---------------------------------------------


def test_every_inventoried_location_has_a_recorded_disposition() -> None:
    claims = INVENTORY["superseded_claims"]
    assert claims, "the inventory records no superseded claims"
    for row in claims:
        assert row["disposition"] in DISPOSITIONS, row
        assert (ROOT / row["location"]).is_file(), row["location"]


def test_every_location_carrying_the_old_claim_is_inventoried() -> None:
    """A surface that still says it, and is not listed here, is the failure this test exists for."""

    inventoried = {row["location"] for row in INVENTORY["superseded_claims"]}
    searched = [
        "scripts/build_codex_v2_orchestration_matrix.py",
        "docs/validation/codex-v2-orchestration-matrix.json",
        "plugins/fleet-core/references/tier-palette.md",
        "plugins/verified-workflows/README.md",
        "plugins/verified-workflows/CHANGELOG.md",
        "docs/portability/matrix.md",
    ]
    for path in searched:
        assert path in inventoried, f"{path} carries a Luna claim but has no disposition"


def test_an_updated_row_states_what_replaced_the_claim() -> None:
    for row in INVENTORY["superseded_claims"]:
        if row["disposition"] == "updated":
            assert row.get("now"), row["location"]
            assert row["now"] != row.get("was")


def test_a_frozen_row_says_why_it_was_not_edited() -> None:
    for row in INVENTORY["superseded_claims"]:
        if row["disposition"] in {"frozen", "superseded-note"}:
            assert row.get("why"), row["location"]


# --- current surfaces no longer assert the superseded claim --------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "plugins/fleet-core/references/tier-palette.md",
        "plugins/verified-workflows/README.md",
    ],
)
def test_a_current_surface_no_longer_says_luna_is_unavailable(path: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    assert "only through MultiAgent V1" not in text
    assert "Luna remains V1" not in text
    assert SUPERSEDED_CLAIM not in text


def test_the_matrix_builder_no_longer_emits_the_superseded_reason() -> None:
    """The builder cannot currently run, but source that would emit a falsehood is still wrong."""

    text = (ROOT / "scripts" / "build_codex_v2_orchestration_matrix.py").read_text(encoding="utf-8")
    # The string survives only as an explicitly labelled `superseded_reason`, never as `reason`.
    assert f'"reason": "{SUPERSEDED_CLAIM}"' not in text
    assert f'"superseded_reason": "{SUPERSEDED_CLAIM}"' in text


def test_the_builder_records_per_row_provenance_rather_than_relabelling_the_header() -> None:
    """KTD2: reproving one row must not restamp evidence that was never retaken."""

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "u11_matrix_builder", ROOT / "scripts" / "build_codex_v2_orchestration_matrix.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    provenance = module.ROW_PROVENANCE
    assert provenance["luna_decision"]["observed_on"] == "0.147.0"
    assert (ROOT / provenance["luna_decision"]["evidence"]).is_file()


# --- dated records are byte-unchanged ------------------------------------------------------


def test_the_dated_changelog_line_is_byte_unchanged() -> None:
    row = next(
        r for r in INVENTORY["superseded_claims"]
        if r["location"] == "plugins/verified-workflows/CHANGELOG.md"
    )
    lines = (ROOT / row["location"]).read_text(encoding="utf-8").splitlines()
    assert row["line_text"] in lines


def test_the_dated_portability_note_is_byte_unchanged() -> None:
    row = next(
        r for r in INVENTORY["superseded_claims"]
        if r["location"] == "docs/portability/matrix.md"
    )
    text = (ROOT / row["location"]).read_text(encoding="utf-8")
    start = text.index("- 2026-07-29:")
    note = text[start : text.index("\n\n", start)]
    assert _sha256(note.encode("utf-8")) == row["dated_note_sha256"]
    assert row["line_text"] in note


def test_the_frozen_matrix_artifact_is_byte_unchanged() -> None:
    row = next(
        r for r in INVENTORY["superseded_claims"]
        if r["location"] == "docs/validation/codex-v2-orchestration-matrix.json"
    )
    assert _sha256((ROOT / row["location"]).read_bytes()) == row["sha256"]
    # It still carries the old wording, which is correct: it is evidence of a past run, and the
    # inventory is what routes a reader to what superseded it.
    matrix = json.loads((ROOT / row["location"]).read_text(encoding="utf-8"))
    assert matrix["luna_decision"]["reason"] == SUPERSEDED_CLAIM
    assert (ROOT / row["superseded_by"]).is_file()


def test_the_superseding_note_is_dated_and_sits_beside_the_record_it_supersedes() -> None:
    text = (ROOT / "docs" / "portability" / "matrix.md").read_text(encoding="utf-8")
    assert "- 2026-08-09: Codex 0.147 alignment supersedes" in text
    assert text.index("- 2026-08-09:") < text.index("- 2026-07-29:")


# --- the negative inventory ----------------------------------------------------------------


def test_every_no_change_row_carries_evidence() -> None:
    rows = INVENTORY["no_change"]
    expected = {
        "exec-full-auto-flag-removed",
        "mcp-2026-07-28-protocol-opt-in",
        "apps",
        "tool-registry-collision-policy",
        "symlink-handling-during-plugin-installation",
        "portable-agent-plugin-packaging",
    }
    assert {row["id"] for row in rows} == expected
    for row in rows:
        assert row["affects_this_repo"] is False, row["id"]
        assert row["evidence"], row["id"]
        assert all(isinstance(item, str) and item for item in row["evidence"]), row["id"]


def test_the_no_symlink_row_still_holds() -> None:
    """The one negative row cheap enough to re-derive on every run."""

    assert not list((ROOT / "plugins").rglob("*")) or not any(
        path.is_symlink() for path in (ROOT / "plugins").rglob("*")
    )


def test_no_plugin_manifest_declares_an_mcp_server_or_app() -> None:
    for manifest in sorted((ROOT / "plugins").glob("*/.codex-plugin/plugin.json")):
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        assert "mcp" not in payload, manifest
        assert "app" not in payload and "app_id" not in payload, manifest


def test_the_builder_is_recorded_as_unrunnable_with_its_reason() -> None:
    row = INVENTORY["builder_is_unrunnable"]
    assert not (ROOT / ".codex" / "agents").exists()
    assert "\\.codex/agents" in row["reason"] or ".codex/agents" in row["reason"]
    assert row["consequence"]


# --- the operator's routing decision --------------------------------------------------------


def test_the_implicit_routing_decision_is_recorded_as_reviewed() -> None:
    """Recorded so the next round finds a decision rather than an unexamined default."""

    decision = next(
        row for row in INVENTORY["operator_decisions"]
        if row["id"] == "implicit-skill-routing-reviewed"
    )
    assert decision["status"] == "reviewed-and-accepted"
    assert decision["reasoning_confirmed_current"]
    assert (ROOT / decision["evidence"]).is_file()
