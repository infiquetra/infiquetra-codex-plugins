"""Tests for sanitized live Codex capability capture."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import capture_codex_runtime_capabilities as capture


def result(payload: object, returncode: int = 0) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(
        args=["codex"],
        returncode=returncode,
        stdout=json.dumps(payload).encode(),
        stderr=b"failed" if returncode else b"",
    )


def raw_model(slug: str = "gpt-5.6-sol") -> dict:
    return {
        "slug": slug,
        "default_reasoning_level": "low",
        "supported_reasoning_levels": [
            {"effort": "low", "description": "not persisted"},
            {"effort": "max", "description": "not persisted"},
        ],
        "visibility": "list",
        "supported_in_api": True,
        "base_instructions": "must be dropped",
        "model_messages": {"secret": "must be dropped"},
        "unknown": "must be dropped",
    }


def test_normalizer_projects_only_allowlisted_model_fields() -> None:
    models = capture.normalize_catalog([raw_model()])

    assert models == [
        {
            "slug": "gpt-5.6-sol",
            "default_effort": "low",
            "supported_efforts": ["low", "max"],
            "visibility": "list",
            "supported_in_api": True,
        }
    ]
    assert "instructions" not in json.dumps(models).lower()


def test_capture_catalog_uses_bundled_only_after_refreshed_failure() -> None:
    calls: list[tuple[str, ...]] = []

    def run(argv):
        calls.append(tuple(argv))
        if "--bundled" not in argv:
            return result({}, returncode=1)
        return result([raw_model()])

    source, models = capture.capture_catalog(run)

    assert source == "bundled"
    assert models[0]["slug"] == "gpt-5.6-sol"
    assert calls == [
        ("codex", "debug", "models"),
        ("codex", "debug", "models", "--bundled"),
    ]


def test_capture_catalog_fails_after_two_invalid_results() -> None:
    with pytest.raises(capture.CaptureError):
        capture.capture_catalog(lambda argv: result({}, returncode=1))


def test_capture_catalog_rejects_oversized_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(capture, "MAX_GIT_OUTPUT", 8)

    with pytest.raises(capture.CaptureError, match="output ceiling"):
        capture.capture_catalog(lambda argv: result([raw_model()]))


def test_default_runner_translates_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=15)

    monkeypatch.setattr(subprocess, "run", timeout)

    with pytest.raises(capture.CaptureError, match="timed out"):
        capture._default_run(("codex", "debug", "models"))


def test_normalizer_rejects_duplicates_and_unknown_effort() -> None:
    with pytest.raises(capture.CaptureError, match="duplicate"):
        capture.normalize_catalog([raw_model(), raw_model()])
    malformed = raw_model()
    malformed["supported_reasoning_levels"] = [{"effort": "impossible"}]
    with pytest.raises(capture.CaptureError, match="malformed"):
        capture.normalize_catalog([malformed])


def test_feature_parser_selects_only_allowlisted_rows() -> None:
    text = """\
multi_agent stable true
hooks stable true
goals stable true
plugins stable true
memories experimental true
"""

    assert set(capture.parse_features(text)) == {"multi_agent", "hooks", "goals", "plugins"}


def test_config_reader_drops_unrelated_and_sensitive_fields(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'model = "gpt-5.6-sol"\nmodel_reasoning_effort = "max"\nsecret = "drop"\n'
        "[agents]\nmax_threads = 6\nmax_depth = 1\n",
        encoding="utf-8",
    )

    assert capture.read_config(config) == {
        "configured_defaults": {"model": "gpt-5.6-sol", "model_reasoning_effort": "max"},
        "configured_max_threads": 6,
        "configured_max_threads_source": "config",
        "configured_max_depth": 1,
        "configured_max_depth_source": "config",
    }


def test_config_reader_marks_absent_agent_limits_as_defaults(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('model = "m"\nmodel_reasoning_effort = "low"\n', encoding="utf-8")

    result = capture.read_config(config)

    assert result["configured_max_threads"] == 6
    assert result["configured_max_threads_source"] == "default"
    assert result["configured_max_depth"] == 1
    assert result["configured_max_depth_source"] == "default"


def test_compare_snapshot_checks_only_discoverable_projection() -> None:
    snapshot = {
        "runtime": {
            "codex_cli_version": "0.144.1",
            "configured_max_threads": 6,
            "configured_max_threads_source": "config",
            "configured_max_depth": 1,
            "configured_max_depth_source": "config",
            "host_total_slots": 4,
            "effective_total_slots": 4,
            "effective_max_children": 3,
            "effective_parent_permission_mode": {
                "sandbox_mode": "danger-full-access",
                "approval_policy": "never",
            },
        },
        "configured_defaults": {"model": "m", "model_reasoning_effort": "max"},
        "catalog": {"source": "refreshed", "normalized_sha256": "x", "models": []},
        "features": {"multi_agent": {"stage": "stable", "enabled": True}},
        "custom_agents": {
            "repo_managed_source_count": 25,
            "installed_custom_agent_count": 4,
            "installed_team_execution_managed_count": 0,
            "installed_verified_workflows_managed_count": 0,
        },
        "collaboration": {"spawn": {"available": True}},
        "hook_capabilities": {"observes_active_model": True},
    }
    projection = {
        "codex_cli_version": "0.144.1",
        "configured_max_threads": 6,
        "configured_max_threads_source": "config",
        "configured_max_depth": 1,
        "configured_max_depth_source": "config",
        "configured_defaults": snapshot["configured_defaults"],
        "catalog": snapshot["catalog"],
        "features": snapshot["features"],
        "custom_agent_counts": snapshot["custom_agents"],
    }
    session_facts = {
        "effective_parent_permission_mode": snapshot["runtime"][
            "effective_parent_permission_mode"
        ],
        "host_total_slots": 4,
        "collaboration": snapshot["collaboration"],
        "hook_capabilities": snapshot["hook_capabilities"],
    }

    assert capture.compare_snapshot(snapshot, projection, session_facts=session_facts) == []


def test_compare_snapshot_requires_explicit_session_facts() -> None:
    snapshot = {
        "runtime": {},
        "configured_defaults": {},
        "catalog": {},
        "features": {},
        "custom_agents": {},
    }
    projection = {
        "configured_defaults": {},
        "catalog": {},
        "features": {},
        "custom_agent_counts": {},
    }

    assert "explicit session facts" in " ".join(capture.compare_snapshot(snapshot, projection))
