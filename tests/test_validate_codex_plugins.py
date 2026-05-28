"""Tests for repo validation."""

from pathlib import Path

from scripts.validate_codex_plugins import (
    EXPECTED_PLUGINS,
    validate_relative_file,
    validate_repository,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_current_repository_validates():
    assert validate_repository(REPO_ROOT) == []


def test_expected_plugin_set_includes_mvp():
    assert set(EXPECTED_PLUGINS) == {
        "blueprint-reviewer",
        "home-lab-ops",
        "python-toolkit",
        "sdlc-manager",
        "unifi",
        "test-suite",
    }


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
