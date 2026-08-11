"""Contract tests for the canonical Claude-to-Codex port runbook."""

from __future__ import annotations

import re
from pathlib import Path

from scripts import port_contract


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs/portability/claude-to-codex-plugin-port-runbook.md"


REQUIRED_H2 = (
    "Contract Metadata",
    "Purpose And Contract Split",
    "Normative Language And Non-Goals",
    "Source Authority",
    "Capability Truth And Surface Selection",
    "Normative Claude-To-Codex Mapping",
    "Plugin Ownership Boundaries",
    "Roles, Execution Classes, And Workflow Ownership",
    "State, Trust, Authentication, And Mutation Boundaries",
    "Staged Port Workflow",
    "Versioning And Release Policy",
    "Validation, Isolated Installation, Fresh-Session Proof, And Rollback",
    "Worked Examples",
    "Stop Rules",
    "Required Artifacts And Historical References",
)

AUTHORITY_IDS = (
    "AUTH-VENDORED",
    "AUTH-CODEX-ADAPTER",
    "AUTH-CODEX-BORN",
    "AUTH-SHARED-POLICY",
    "AUTH-PACKAGE-MIGRATION",
    "AUTH-INSTALLED",
    "AUTH-HISTORICAL",
)

MAPPING_IDS = (
    "MAP-MANIFEST",
    "MAP-SKILL",
    "MAP-COMMAND",
    "MAP-SCRIPT-CONFIG",
    "MAP-AGENT",
    "MAP-DETERMINISTIC",
    "MAP-WORKFLOW",
    "MAP-MESSAGE",
    "MAP-HOOK",
    "MAP-STATE",
    "MAP-MCP",
    "MAP-APP",
    "MAP-TEST",
    "MAP-DOC",
    "MAP-CACHE",
    "MAP-METADATA",
)

STOP_IDS = (
    "STOP-AUTHORITY",
    "STOP-DIRTY-OVERLAP",
    "STOP-FROZEN-REF",
    "STOP-EXECUTION-BASE",
    "STOP-INVENTORY",
    "STOP-DIRECT-HOST-PRIMITIVE",
    "STOP-CAPABILITY",
    "STOP-HOOK",
    "STOP-ADAPTATION-EVIDENCE",
    "STOP-UNSAFE-DATA",
    "STOP-VERSION",
    "STOP-GATE",
    "STOP-INSTALL-PROOF",
    "STOP-FRESH-SESSION",
    "STOP-ROLLBACK",
    "STOP-DUAL-IDENTITY",
    "STOP-CREDENTIAL-COPY",
    "STOP-EXTERNAL-MUTATION",
    "STOP-UNPROVED-EXECUTION",
)


def test_runbook_has_exact_versioned_structure() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    headings = re.findall(r"^## (.+)$", text, re.MULTILINE)

    assert headings == list(REQUIRED_H2)
    assert "Status: canonical" in text
    assert "Runbook version: `6`" in text
    assert port_contract.RUNBOOK_VERSION == 6
    assert port_contract.SUPPORTED_RUNBOOK_VERSIONS == {3, 4, 5, 6}


def test_runbook_requires_native_v2_profiles_and_bounded_deviation() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    for required in (
        "native `collaboration` namespace",
        "without redundant model/effort overrides",
        "`agent_type`",
        "`fork_turns=none`",
        "full-history fork",
        "permission-homogeneous parent",
        "host-issued rollout context",
        "Bounded unplanned repair",
    ):
        assert required in text


def test_authority_mapping_and_stop_ids_are_unique() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    for identifier in (*AUTHORITY_IDS, *MAPPING_IDS, *STOP_IDS):
        assert text.count(f"`{identifier}`") == 1, identifier


def test_normative_mappings_keep_claude_host_surfaces_inactive() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    for required in (
        ".claude-plugin",
        ".codex-plugin/plugin.json",
        "active `commands/` directory",
        "agent-lens",
        "deterministic validator",
        "root-owned Verified Workflows DAG",
        "status or clarification",
        "fresh execution context",
        "`PLUGIN_DATA`",
        "MCP only for typed external actions",
        "Treat cache/profile state as installation evidence only",
    ):
        assert required in text


def test_runbook_names_all_canonical_owners_and_gates() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    for owner in ("`fleet-core`", "`saga`", "`verified-workflows`", "`mission-control`", "`deploy`"):
        assert owner in text
    for gate in ("classification", "unit", "cutover", "isolated", "fresh-session", "rollback"):
        assert gate in text.lower()
    assert "team-execution` is source input" in text


def test_worked_examples_cover_required_surface_types() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    examples = text.split("## Worked Examples", 1)[1].split("## Stop Rules", 1)[0]

    for term in ("Reviewer", "Scanner", "Workflow", "Hook", "Unsupported feature"):
        assert term in examples


def test_repo_entrypoints_make_runbook_mandatory() -> None:
    expected = "docs/portability/claude-to-codex-plugin-port-runbook.md"
    for path in (ROOT / "AGENTS.md", ROOT / "README.md"):
        text = path.read_text(encoding="utf-8")
        assert expected in text
        assert "mandatory" in text.lower()


def test_relative_markdown_links_resolve() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        if "://" in target or target.startswith("#"):
            continue
        assert (RUNBOOK.parent / target).resolve().exists(), target


def test_historical_recipe_is_marked_superseded() -> None:
    text = (ROOT / "docs/portability/provenance.md").read_text(encoding="utf-8").lower()

    assert "proof-port recipe" in text
    assert "superseded" in text
    assert "claude-to-codex-plugin-port-runbook.md" in text
