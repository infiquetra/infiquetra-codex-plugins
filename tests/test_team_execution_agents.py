"""Tests for the team-execution Codex agent roster."""

from __future__ import annotations

import importlib.util
import re
import sys
import tomllib
from pathlib import Path

import pytest

from scripts.validate_codex_plugins import (
    TEAM_EXECUTION_AGENT_MARKER,
    TEAM_EXECUTION_AGENT_ROSTER,
    TEAM_EXECUTION_MODEL_HINTS,
    validate_repository,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_ROOT = REPO_ROOT / "plugins" / "team-execution" / "agents"
SYNC_SCRIPT = REPO_ROOT / "plugins" / "team-execution" / "scripts" / "sync_codex_agents.py"
SOURCE_MODEL_RE = re.compile(r'^# source_model = "(?P<model>[^"]+)"$', re.MULTILINE)
CODEX_MODEL_HINT_RE = re.compile(r'^# codex_model_hint = "(?P<model>[^"]+)"$', re.MULTILINE)


def load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_codex_agents", SYNC_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_team_execution_agent_roster_is_exact_and_parseable():
    agent_files = sorted(AGENTS_ROOT.glob("*.toml"))

    assert {path.stem for path in agent_files} == TEAM_EXECUTION_AGENT_ROSTER
    assert len(agent_files) == 25

    for path in agent_files:
        text = path.read_text(encoding="utf-8")
        payload = tomllib.loads(text)
        assert payload["name"] == path.stem
        assert isinstance(payload["description"], str) and payload["description"].strip()
        assert isinstance(payload["developer_instructions"], str)
        assert path.stem in payload["developer_instructions"]
        assert "model" not in payload


def test_team_execution_agent_lineage_maps_to_codex_effort_hints():
    for path in sorted(AGENTS_ROOT.glob("*.toml")):
        text = path.read_text(encoding="utf-8")
        payload = tomllib.loads(text)
        source_model = SOURCE_MODEL_RE.search(text)
        codex_hint = CODEX_MODEL_HINT_RE.search(text)

        assert TEAM_EXECUTION_AGENT_MARKER in text.splitlines()[:8]
        assert source_model is not None, path.name
        assert codex_hint is not None, path.name

        expected_hint, expected_effort = TEAM_EXECUTION_MODEL_HINTS[source_model["model"]]
        assert codex_hint["model"] == expected_hint
        assert payload["model_reasoning_effort"] == expected_effort


def test_team_execution_agent_validation_is_part_of_repo_validator():
    assert validate_repository(REPO_ROOT) == []


def test_team_execution_active_docs_do_not_reference_retired_display_setup():
    active_docs = [
        REPO_ROOT / "plugins" / "team-execution" / "README.md",
        REPO_ROOT / "plugins" / "team-execution" / "skills" / "team-execution" / "SKILL.md",
    ]

    retired_terms = (
        "validator-pane-behavior.md",
        "/team-setup",
        "agent-overflow",
        "tmux",
    )
    for path in active_docs:
        text = path.read_text(encoding="utf-8")
        for term in retired_terms:
            assert term not in text, f"{path.relative_to(REPO_ROOT)} references {term}"


def test_sync_codex_agents_installs_and_then_reports_unchanged(tmp_path):
    sync = load_sync_module()
    target_dir = tmp_path / "agents"

    actions = sync.plan_sync(AGENTS_ROOT, target_dir, remove_stale=False)
    assert len(actions) == len(TEAM_EXECUTION_AGENT_ROSTER)
    assert {action.action for action in actions} == {"install"}

    sync.apply_actions(actions)
    assert {path.stem for path in target_dir.glob("*.toml")} == TEAM_EXECUTION_AGENT_ROSTER

    actions = sync.plan_sync(AGENTS_ROOT, target_dir, remove_stale=False)
    assert {action.action for action in actions} == {"unchanged"}


def test_sync_codex_agents_refuses_unmanaged_conflict(tmp_path):
    sync = load_sync_module()
    target_dir = tmp_path / "agents"
    target_dir.mkdir()
    target = target_dir / "security-reviewer.toml"
    target.write_text('name = "local-security-reviewer"\n', encoding="utf-8")

    actions = sync.plan_sync(AGENTS_ROOT, target_dir, remove_stale=False)
    conflict = [action for action in actions if action.target == str(target)]

    assert len(conflict) == 1
    assert conflict[0].action == "conflict"
    with pytest.raises(SystemExit):
        sync.apply_actions(actions)
    assert target.read_text(encoding="utf-8") == 'name = "local-security-reviewer"\n'


def test_sync_codex_agents_removes_only_stale_managed_files(tmp_path):
    sync = load_sync_module()
    target_dir = tmp_path / "agents"
    target_dir.mkdir()
    managed_stale = target_dir / "retired-reviewer.toml"
    unmanaged_stale = target_dir / "local-reviewer.toml"
    managed_stale.write_text(
        f"{TEAM_EXECUTION_AGENT_MARKER}\nname = \"retired-reviewer\"\n",
        encoding="utf-8",
    )
    unmanaged_stale.write_text('name = "local-reviewer"\n', encoding="utf-8")

    actions = sync.plan_sync(AGENTS_ROOT, target_dir, remove_stale=True)
    remove_actions = [action for action in actions if action.action == "remove"]

    assert [Path(action.target).name for action in remove_actions] == ["retired-reviewer.toml"]
    sync.apply_actions(actions)
    assert not managed_stale.exists()
    assert unmanaged_stale.exists()
