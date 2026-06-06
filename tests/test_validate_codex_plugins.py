"""Tests for repo validation."""

from pathlib import Path

from scripts.validate_codex_plugins import (
    CURRENT_EXPECTED_PLUGINS,
    EXPECTED_PLUGINS,
    TARGET_EXPECTED_PLUGINS,
    compare_inventory,
    validate_relative_file,
    validate_repository,
    validate_target_fixture_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_current_repository_validates():
    assert validate_repository(REPO_ROOT) == []
    assert validate_repository(REPO_ROOT, mode="current") == []


def test_target_fixture_validates_without_active_cutover():
    assert validate_repository(REPO_ROOT, mode="target-fixture") == []


def test_cutover_reports_old_inventory_before_u8():
    errors = validate_repository(REPO_ROOT, mode="cutover")

    assert errors
    assert any("marketplace inventory mismatch" in error for error in errors)
    assert any("plugin directory inventory mismatch" in error for error in errors)
    assert any("saga" in error and "missing" in error for error in errors)
    assert any("sdlc-manager" in error and "unexpected" in error for error in errors)


def test_expected_plugin_set_includes_mvp():
    assert set(EXPECTED_PLUGINS) == {
        "blueprint-reviewer",
        "home-lab-ops",
        "python-toolkit",
        "sdlc-manager",
        "unifi",
        "test-suite",
    }
    assert EXPECTED_PLUGINS is CURRENT_EXPECTED_PLUGINS


def test_target_plugin_set_describes_saga_family_cutover():
    assert set(TARGET_EXPECTED_PLUGINS) == {
        "saga",
        "deploy",
        "mission-control",
        "team-execution",
        "home-lab-ops",
        "python-toolkit",
        "unifi",
        "test-suite",
    }
    assert {"plan", "work", "brainstorm"} <= set(TARGET_EXPECTED_PLUGINS["saga"]["skills"])
    assert {"blueprint-reviewer", "sdlc-manager"}.isdisjoint(TARGET_EXPECTED_PLUGINS)


def test_target_fixture_requires_namespace_proof():
    payload = {
        "plugins": [
            {"name": name, "version": spec["version"], "skills": list(spec["skills"]), "forbidden_active_dirs": [".claude-plugin", "commands", "agents"]}
            for name, spec in TARGET_EXPECTED_PLUGINS.items()
        ],
        "removed_plugins": ["blueprint-reviewer", "sdlc-manager"],
        "required_namespace_proof": ["saga:plan", "saga:work"],
        "required_state_roots": [".codex/saga/", ".codex/team-execution/"],
        "mutation_gate_plugins": ["deploy", "mission-control"],
    }
    errors: list[str] = []

    validate_target_fixture_payload(payload, REPO_ROOT / "fixture.json", errors)

    assert any("saga:brainstorm" in error for error in errors)


def test_compare_inventory_reports_missing_and_unexpected_items():
    errors: list[str] = []

    compare_inventory({"sdlc-manager"}, {"saga", "mission-control"}, "target", errors)

    assert errors == [
        "target mismatch: missing=['mission-control', 'saga'] unexpected=['sdlc-manager']"
    ]


def test_script_reference_rejects_traversal(tmp_path):
    plugin_root = tmp_path / "plugins" / "example"
    skill_dir = plugin_root / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    source = skill_dir / "SKILL.md"
    source.write_text("---\nname: demo\ndescription: demo\n---\n", encoding="utf-8")
    errors: list[str] = []

    validate_relative_file(skill_dir, plugin_root, "../outside.py", source, errors)

    assert errors
    assert "must stay inside package" in errors[0]


def test_script_reference_requires_existing_file(tmp_path):
    plugin_root = tmp_path / "plugins" / "example"
    skill_dir = plugin_root / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    source = skill_dir / "SKILL.md"
    source.write_text("---\nname: demo\ndescription: demo\n---\n", encoding="utf-8")
    errors: list[str] = []

    validate_relative_file(skill_dir, plugin_root, "./scripts/missing.py", source, errors)

    assert errors
    assert "points to missing file" in errors[0]
