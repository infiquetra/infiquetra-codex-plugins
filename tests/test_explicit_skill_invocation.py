from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def skill_dirs(plugin: str) -> list[Path]:
    return sorted(
        path
        for path in (ROOT / "plugins" / plugin / "skills").iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def test_saga_and_verified_workflow_skills_are_explicit_only() -> None:
    for plugin in ("saga", "verified-workflows"):
        for skill in skill_dirs(plugin):
            metadata = yaml.safe_load(
                (skill / "agents" / "openai.yaml").read_text(encoding="utf-8")
            )
            assert metadata["policy"]["allow_implicit_invocation"] is False, skill


def test_loop_does_not_route_bare_ad_hoc_requests() -> None:
    text = (ROOT / "plugins" / "saga" / "skills" / "loop" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "bare ad-hoc ask" not in text
