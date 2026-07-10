from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import MappingProxyType

import pytest


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "fleet_commons"
    / "workflow_compat.py"
)
_SPEC = importlib.util.spec_from_file_location("fleet_workflow_compat", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
workflow_compat = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = workflow_compat
_SPEC.loader.exec_module(workflow_compat)


EXPECTED_PAIRS = {
    workflow_compat.PLUGIN_ID: ("verified-workflows", "team-execution"),
    workflow_compat.DISPLAY_NAME: ("Verified Workflows", "Team Execution"),
    workflow_compat.RUN_SKILL: ("run", "team-execution"),
    workflow_compat.NAMESPACED_RUN_SKILL: (
        "verified-workflows:run",
        "team-execution:team-execution",
    ),
    workflow_compat.NAMESPACED_APPSEC_AUDIT_SKILL: (
        "verified-workflows:appsec-audit",
        "team-execution:appsec-audit",
    ),
    workflow_compat.SAGA_MODE: ("verified-workflow", "team-execution"),
    workflow_compat.PLAN_HEADING: ("## Workflow Structure", "## Team Structure"),
    workflow_compat.PLAN_ANCHOR: ("#workflow-structure", "#team-structure"),
    workflow_compat.REPO_STATE_ROOT: (
        ".codex/verified-workflows/",
        ".codex/team-execution/",
    ),
    workflow_compat.USER_STATE_ROOT: (
        "~/.codex/verified-workflows/state/",
        "~/.codex/team-execution/state/",
    ),
    workflow_compat.REPO_CONFIG_FILE: (".verified-workflows.json", ".team-execution.json"),
    workflow_compat.GIT_SNAPSHOT_PREFIX: (
        "refs/verified-workflows/snapshots/",
        "refs/team-execution/snapshots/",
    ),
    workflow_compat.SUBAGENT_VEHICLE: (
        "verified-workflow-subagent",
        "team-execution-delegated",
    ),
    workflow_compat.INLINE_VEHICLE: (
        "verified-workflow-inline",
        "team-execution-serial",
    ),
    workflow_compat.PRODUCER_KIND: ("verified-workflow", "team-execution"),
    workflow_compat.EVIDENCE_REF: ("verified_workflow_ref", "team_execution_ref"),
    workflow_compat.MANAGED_AGENT_MARKER: (
        '# managed_by = "infiquetra-codex-plugins/verified-workflows"',
        '# managed_by = "infiquetra-codex-plugins/team-execution"',
    ),
}


def test_registry_is_closed_and_has_exact_migration_pairs() -> None:
    assert isinstance(workflow_compat.REGISTRY, MappingProxyType)
    assert set(workflow_compat.REGISTRY) == {
        *EXPECTED_PAIRS,
        workflow_compat.APPSEC_AUDIT_SKILL,
    }
    assert workflow_compat.REGISTRY[workflow_compat.APPSEC_AUDIT_SKILL].canonical == (
        "appsec-audit"
    )
    assert workflow_compat.REGISTRY[workflow_compat.APPSEC_AUDIT_SKILL].legacy == ()

    for key, (canonical, legacy) in EXPECTED_PAIRS.items():
        assert workflow_compat.entry(key).canonical == canonical
        assert workflow_compat.legacy_values(key) == (legacy,)


@pytest.mark.parametrize(("key", "values"), EXPECTED_PAIRS.items())
def test_reader_accepts_canonical_and_legacy_with_provenance(
    key: str,
    values: tuple[str, str],
) -> None:
    canonical, legacy = values

    current = workflow_compat.parse(key, canonical)
    old = workflow_compat.parse(key, legacy)

    assert current.canonical == canonical
    assert current.source == canonical
    assert current.is_legacy is False
    assert old.canonical == canonical
    assert old.source == legacy
    assert old.is_legacy is True


@pytest.mark.parametrize(("key", "values"), EXPECTED_PAIRS.items())
def test_serializer_always_emits_canonical_value(
    key: str,
    values: tuple[str, str],
) -> None:
    canonical, legacy = values

    assert workflow_compat.emit(key) == canonical
    assert workflow_compat.emit(key, canonical) == canonical
    assert workflow_compat.emit(key, legacy) == canonical


def test_unknown_keys_values_and_cross_category_aliases_fail_closed() -> None:
    with pytest.raises(workflow_compat.WorkflowVocabularyError, match="unknown"):
        workflow_compat.entry("plugin.unknown")
    with pytest.raises(workflow_compat.WorkflowVocabularyError, match="unsupported"):
        workflow_compat.parse(workflow_compat.SAGA_MODE, "delegated")
    with pytest.raises(workflow_compat.WorkflowVocabularyError, match="unsupported"):
        workflow_compat.parse(workflow_compat.RUN_SKILL, "team-execution:team-execution")
    with pytest.raises(workflow_compat.WorkflowVocabularyError, match="non-empty"):
        workflow_compat.parse(workflow_compat.PLUGIN_ID, "")
    with pytest.raises(workflow_compat.WorkflowVocabularyError, match="unsupported"):
        workflow_compat.parse(workflow_compat.SUBAGENT_VEHICLE, "generic-subagent")
    with pytest.raises(workflow_compat.WorkflowVocabularyError, match="unsupported"):
        workflow_compat.parse(workflow_compat.INLINE_VEHICLE, "inline-assist")


def test_registry_cannot_be_mutated() -> None:
    with pytest.raises(TypeError):
        workflow_compat.REGISTRY["new"] = workflow_compat.VocabularyEntry("new")  # type: ignore[index]


@pytest.mark.parametrize(
    ("key", "canonical", "legacy"),
    (
        (
            workflow_compat.REPO_STATE_ROOT,
            ".codex/verified-workflows/run-1/receipt.json",
            ".codex/team-execution/run-1/receipt.json",
        ),
        (
            workflow_compat.USER_STATE_ROOT,
            "~/.codex/verified-workflows/state/repo/run-1.json",
            "~/.codex/team-execution/state/repo/run-1.json",
        ),
        (
            workflow_compat.GIT_SNAPSHOT_PREFIX,
            "refs/verified-workflows/snapshots/run-1",
            "refs/team-execution/snapshots/run-1",
        ),
    ),
)
def test_prefix_reader_preserves_suffix_and_writer_uses_canonical_prefix(
    key: str,
    canonical: str,
    legacy: str,
) -> None:
    assert workflow_compat.parse_prefix(key, canonical).is_legacy is False
    parsed = workflow_compat.parse_prefix(key, legacy)
    assert parsed.is_legacy is True
    assert parsed.canonical == canonical
    assert workflow_compat.emit_prefix(key, legacy) == canonical


def test_prefix_reader_is_boundary_safe() -> None:
    with pytest.raises(workflow_compat.WorkflowVocabularyError, match="unsupported"):
        workflow_compat.parse_prefix(
            workflow_compat.REPO_STATE_ROOT,
            ".codex/team-execution-old/run.json",
        )
    with pytest.raises(workflow_compat.WorkflowVocabularyError, match="unsafe"):
        workflow_compat.parse_prefix(
            workflow_compat.REPO_STATE_ROOT,
            ".codex/team-execution/../outside.json",
        )


def test_mixed_canonical_and_legacy_locations_are_a_hard_conflict() -> None:
    with pytest.raises(workflow_compat.WorkflowVocabularyConflict, match="both exist"):
        workflow_compat.select_present(
            workflow_compat.REPO_CONFIG_FILE,
            (".verified-workflows.json", ".team-execution.json"),
        )
    selected = workflow_compat.select_present(
        workflow_compat.REPO_CONFIG_FILE,
        (".team-execution.json",),
    )
    assert selected is not None and selected.is_legacy is True


def test_mixed_canonical_and_legacy_prefix_locations_are_a_hard_conflict() -> None:
    with pytest.raises(workflow_compat.WorkflowVocabularyConflict, match="both exist"):
        workflow_compat.select_present_prefix(
            workflow_compat.REPO_STATE_ROOT,
            (
                ".codex/verified-workflows/run-1/",
                ".codex/team-execution/run-1/",
            ),
        )
