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
    "qa",
    "investigate",
    "retro",
    "resume",
    "handoff",
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
    assert manifest["version"] == "0.22.1"
    assert set(target["skills"]) == EXPECTED_SKILLS
    assert {path.parent.name for path in (PLUGIN_ROOT / "skills").glob("*/SKILL.md")} == EXPECTED_SKILLS
    assert not (PLUGIN_ROOT / ".claude-plugin").exists()
    assert not (PLUGIN_ROOT / "commands").exists()
    assert not (PLUGIN_ROOT / "agents").exists()


def test_active_saga_text_has_no_old_host_or_command_only_surface() -> None:
    forbidden = (
        ".claude",
        "AskUserQuestion",
        "cc-workflows-ultracode",
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


def test_operator_choice_documents_two_codex_backends() -> None:
    text = (PLUGIN_ROOT / "references/operator-choice.md").read_text(encoding="utf-8")

    assert "`inline`" in text
    assert "`team-execution`" in text
    assert "cc-workflows-ultracode" not in text
    assert "Codex Saga exposes exactly two execution choices" in text
