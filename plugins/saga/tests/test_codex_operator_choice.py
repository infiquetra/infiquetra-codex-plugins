from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = ROOT / "plugins" / "saga"

EXPECTED_SKILLS = {
    "office-hours",
    "ideate",
    "product-review",
    "brainstorm",
    "spec",
    "implementation-spec",
    "strategy",
    "plan",
    "work",
    "outcome",
    "qa",
    "investigate",
    "retro",
    "resume",
    "handoff",
    "promote",
    "founder-review",
    "ceo-review",
    "doc-review",
    "code-review",
    "optimize",
    "loop",
}


def active_text_paths() -> list[Path]:
    paths = [PLUGIN_ROOT / "README.md"]
    paths.extend((PLUGIN_ROOT / "references").rglob("*.md"))
    paths.extend((PLUGIN_ROOT / "skills").rglob("*.md"))
    paths.extend((PLUGIN_ROOT / "scripts").rglob("*.py"))
    return sorted(path for path in paths if path.is_file())


def test_manifest_and_skill_inventory_match_target_fixture() -> None:
    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    fixture = json.loads(
        (ROOT / "docs/validation/saga-family-target-inventory.json").read_text(encoding="utf-8")
    )
    target = next(entry for entry in fixture["plugins"] if entry["name"] == "saga")

    assert manifest["name"] == "saga"
    assert manifest["version"] == "0.78.0+codex.20260720120109"
    assert set(target["skills"]) == EXPECTED_SKILLS
    assert {path.parent.name for path in (PLUGIN_ROOT / "skills").glob("*/SKILL.md")} == EXPECTED_SKILLS
    assert not (PLUGIN_ROOT / ".claude-plugin").exists()
    assert not (PLUGIN_ROOT / "commands").exists()
    assert not (PLUGIN_ROOT / "agents").exists()


def test_active_saga_text_has_no_old_host_or_command_only_surface() -> None:
    forbidden = (
        ".claude",
        "AskUserQuestion",
            ".claude-plugin",
        "suggested_command",
        "/issue --prepare",
        "exactly three backends",
    )

    offenders: dict[str, list[str]] = {}
    for path in active_text_paths():
        text = path.read_text(encoding="utf-8")
        hits = [pattern for pattern in forbidden if pattern in text]
        if hits:
            offenders[path.relative_to(ROOT).as_posix()] = hits

    assert offenders == {}


def test_operator_choice_documents_separate_codex_capability_dimensions() -> None:
    text = (PLUGIN_ROOT / "references/operator-choice.md").read_text(encoding="utf-8")

    for dimension in (
        "Lifecycle and state",
        "Continuation",
        "Workflow mode",
        "Step vehicle",
        "Role identity",
        "Execution-class control",
        "Hooks",
    ):
        assert dimension in text
    assert "exact V2 profile, model, effort" in text
    assert "bounded `fork_turns`" in text
    assert "session_meta" in text
    assert "turn_context" in text
    assert "child self-report" in text
    assert "Ultra is a root-only orchestration control" in text
    assert "Missing or mismatched readback fails visibly" in text
