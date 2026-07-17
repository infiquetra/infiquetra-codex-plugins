"""Contracts for the temporary Sol/Terra MultiAgent V1 compatibility path."""

from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIED = ROOT / "plugins" / "verified-workflows"
PROFILE_NAMES = ("review_max", "review_high", "test_medium", "scan_low", "monitor_low")


def test_project_config_selects_stable_multi_agent_without_v2_workaround() -> None:
    config = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))

    assert config["features"]["multi_agent"] is True
    assert config["features"]["multi_agent_v2"] is False
    assert not isinstance(config["features"]["multi_agent_v2"], dict)


def test_select_agent_skill_uses_exact_managed_profile_catalog() -> None:
    skill = (VERIFIED / "skills/select-agent/SKILL.md").read_text(encoding="utf-8")
    source_profiles = {path.stem for path in (VERIFIED / "agents").glob("*.toml")}

    assert source_profiles == set(PROFILE_NAMES)
    for name in PROFILE_NAMES:
        assert f"`{name}`" in skill
    assert "../../agents/" in skill
    assert "fork_context=false" in skill
    assert "`/agent` switches" in skill


def test_active_operator_guidance_uses_v1_catalog_override() -> None:
    paths = (
        VERIFIED / "README.md",
        VERIFIED / "skills/run/SKILL.md",
        ROOT / "plugins/saga/references/operator-choice.md",
        ROOT / "plugins/fleet-core/README.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "codex_v1_catalog.py" in text or "Fleet Core full-catalog override" in text
    assert "historical V2" in (VERIFIED / "README.md").read_text(encoding="utf-8")
