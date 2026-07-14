"""Drift guards for mission-control prompts, references, and release metadata."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = ROOT / "plugins" / "mission-control"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_sdlc_manager_metadata_and_marketplace_entry_match() -> None:
    plugin_json = json.loads(_read(PLUGIN_ROOT / ".codex-plugin" / "plugin.json"))
    fixture = json.loads(_read(ROOT / "docs/validation/saga-family-target-inventory.json"))
    entry = next(p for p in fixture["plugins"] if p["name"] == "mission-control")

    assert plugin_json["name"] == "mission-control"
    assert plugin_json["version"] == "2.4.1"
    assert entry["version"] == plugin_json["version"]
    assert sorted(entry["skills"]) == [
        "board",
        "flow",
        "issues",
        "labels",
        "metrics",
        "milestones",
        "rollout",
    ]
    assert not (PLUGIN_ROOT / ".claude-plugin").exists()
    assert not (PLUGIN_ROOT / "commands").exists()
    assert not (PLUGIN_ROOT / "agents").exists()
    assert "CAMPPS" in plugin_json["description"]
    assert "campps" in plugin_json["keywords"]
    assert "Mount Olympus" not in json.dumps(plugin_json)
    assert "mount-olympus" not in json.dumps(plugin_json)


def test_flow_catalog_description_leads_with_assign_mimir() -> None:
    frontmatter = _read(PLUGIN_ROOT / "skills" / "flow" / "SKILL.md").split(
        "when_to_use:", maxsplit=1
    )[0]

    assert "Assign covered issues to Team Mimir" in frontmatter[:180]


def test_issue_type_reference_uses_current_template_labels() -> None:
    issue_types = _read(PLUGIN_ROOT / "skills/issues/references/issue-types.md")

    assert "`capability`, `hermes-task`, `needs-plan`" in issue_types
    assert "`enhancement`, `hermes-task`, `needs-plan`" in issue_types
    assert "`defect`, `hermes-task`, `needs-plan`" in issue_types
    assert "Do not create an Objective issue" in issue_types
    assert "`objective`, `hermes-not-actionable`" not in issue_types
    assert "`exploration`, `research`, `hermes-not-actionable`" in issue_types
    assert "`context-update`, `documentation`, `hermes-not-actionable`" in issue_types
    assert "`capability`, `needs-analysis` (auto-applied by template)" not in issue_types
    assert "`enhancement`, `needs-analysis` (auto-applied by template)" not in issue_types
    assert "`defect`, `needs-triage` (auto-applied by template)" not in issue_types
    assert "`objective:{short-name}`" not in issue_types
    assert "`initiative:{name}`" not in issue_types


def test_issue_skill_honors_hermes_actionability_contract() -> None:
    skill = _read(PLUGIN_ROOT / "skills/issues/SKILL.md")

    assert "Actionable issue types are `capability`, `enhancement`, and `defect`" in skill
    assert "`exploration` and `context-update` are context-only types" in skill
    assert "capability/enhancement/defect/exploration/context-update" not in skill
    assert "hermes-task`, `needs-plan`" in skill
    assert "needs-analysis" not in skill
    assert "issue prepare" in skill
    assert "issue approve" in skill
    assert "issue create-prepared" in skill
    assert "Asgard prepared drafts start in `Shaping`" in skill
    assert "CAMPPS board work tracks `Idea -> Committed -> In Progress -> Done -> Parked`" in skill


def test_flow_skill_uses_project_fields_and_current_actionable_labels() -> None:
    flow = _read(PLUGIN_ROOT / "skills/flow/SKILL.md")

    assert "Set Initiative or Objective on a card (project FIELDS, not labels)" in flow
    assert "initiative/objective labels" not in flow
    assert "needs-analysis" not in flow
    assert "flow assign-mimir" in flow
    assert "never creates policy" in flow


def test_assign_mimir_guidance_is_aligned_across_active_surfaces() -> None:
    flow = _read(PLUGIN_ROOT / "skills/flow/SKILL.md")
    issues = _read(PLUGIN_ROOT / "skills/issues/SKILL.md")
    readme = _read(PLUGIN_ROOT / "README.md")

    for text in (flow, issues, readme):
        assert "flow assign-mimir" in text
    assert "alternate credentials" in flow
    assert "never admits a repository" in issues


def test_field_first_hierarchy_guidance_is_consistent() -> None:
    issue_skill = _read(PLUGIN_ROOT / "skills/issues/SKILL.md")
    flow_skill = _read(PLUGIN_ROOT / "skills/flow/SKILL.md")
    milestone_skill = _read(PLUGIN_ROOT / "skills/milestones/SKILL.md")
    rollout_hierarchy = _read(PLUGIN_ROOT / "skills/rollout/references/work-hierarchy.md")

    assert "5-type issue" in issue_skill
    assert "Objective is an `Objective` project-field option" in issue_skill
    assert "flow unlink-sub-issue" in flow_skill
    assert "Create the Objective issue" not in milestone_skill
    assert "Capability issue (top-level)" in rollout_hierarchy
    assert "Objective issue + project field option" not in rollout_hierarchy


def test_label_docs_mark_legacy_auto_label_rules_as_fallback() -> None:
    skill = _read(PLUGIN_ROOT / "skills/labels/SKILL.md")
    reference = _read(PLUGIN_ROOT / "skills/labels/references/labels-reference.md")

    assert "legacy fallback behavior" in skill
    assert "legacy fallback labels" in skill
    assert "legacy fallback labels" in reference
    assert "legacy fallback rules" in reference
    assert "Current capability,\nenhancement, and defect templates apply `needs-plan`" in reference


def test_prepared_issue_guidance_routes_natural_language_creation() -> None:
    skill = _read(PLUGIN_ROOT / "skills/issues/SKILL.md")
    readme = _read(PLUGIN_ROOT / "README.md")

    for text in (skill, readme):
        assert "issue prepare" in text
        assert "issue create-prepared" in text

    assert "mission-control:issues" in skill
    assert "Use `mission-control:issues`" in skill
    assert "--from" in skill
    assert "--maturity" in skill
    assert "prepared issue" in skill.lower()
    assert "Codex Skills" in readme
    assert "Create a CAMPPS issue from this text" in skill
    assert "Create an Asgard issue from these notes" in skill
    assert "Create an issue from the brainstorm" in skill
    assert "--team asgard --project campps" in skill
    assert "handoff_maturity" in skill
    assert "If team or project is ambiguous, ask" in skill
    assert "Never auto-move a prepared issue to `Ready`" in skill
    assert "Create an Olympus issue from this text" not in skill
    assert "/loop <issue>" not in skill


def test_active_topology_uses_campps_and_retired_olympus_history() -> None:
    schema = json.loads(_read(PLUGIN_ROOT / "config/sdlc-schema.json"))
    roles = schema["work_hierarchy"]["roles"]

    assert schema["schema_version"] == "2026-06-17"
    assert roles["objective"]["project_view_group_by"] == "Objective"
    assert roles["outcome"]["required_by_default"] is False
    assert roles["capability"]["default_parent_role"] is None
    assert roles["capability"]["allowed_parent_roles"] == ["outcome"]
    assert schema["teams"]["asgard"]["status"] == "active"
    assert schema["teams"]["olympus"]["status"] == "retired_historical"
    assert schema["teams"]["olympus"]["board"] is None
    assert schema["boards"]["campps"]["status"] == "active"
    assert schema["workflows"]["campps_initiative"]["statuses"] == [
        "Idea",
        "Committed",
        "In Progress",
        "Done",
        "Parked",
    ]
    assert "Transfer Target" in schema["fields"]["asgard"]
    assert "Promotion Target" not in schema["fields"]["asgard"]
    assert "cross_team_transfer_rule" in schema["team_routing"]
    assert "asgard_to_olympus_rule" not in schema["team_routing"]
    assert schema["team_routing"]["target_team_values"] == [
        "Asgard",
        "CAMPPS",
        "Jeff",
        "External/Deferred",
    ]

    active_surfaces = [
        PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
        PLUGIN_ROOT / "README.md",
        PLUGIN_ROOT / "config/sdlc-schema.json",
        PLUGIN_ROOT / "scripts/sdlc_manager.py",
        PLUGIN_ROOT / "skills/board/SKILL.md",
        PLUGIN_ROOT / "skills/flow/SKILL.md",
        PLUGIN_ROOT / "skills/issues/SKILL.md",
        PLUGIN_ROOT / "skills/metrics/SKILL.md",
    ]
    stale_phrases = [
        "asgard_to_olympus",
        "Promotion Target",
        "Promotion gaps",
        "Olympus promotion gaps",
        "Asgard Seeds Olympus",
        "seed Olympus",
        "promote to Olympus",
        "mount-olympus --",
    ]

    for path in active_surfaces:
        text = _read(path)
        for phrase in stale_phrases:
            assert phrase not in text, f"{path.relative_to(ROOT)} contains stale phrase {phrase!r}"
