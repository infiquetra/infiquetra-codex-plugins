from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def load_protocol_probe() -> ModuleType:
    script = Path(__file__).parents[1] / "scripts" / "protocol_probe.py"
    spec = importlib.util.spec_from_file_location("team_execution_protocol_probe", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

probe = load_protocol_probe()


def write_gitignore(repo_root: Path, text: str) -> None:
    (repo_root / ".gitignore").write_text(text, encoding="utf-8")


def test_serial_fallback_records_per_role_artifacts_and_limits(tmp_path: Path) -> None:
    write_gitignore(tmp_path, ".codex/team-execution/\n")

    payload = probe.probe_protocol(
        repo_root=tmp_path,
        subagents="absent",
        validators=[
            probe.ValidatorSpec(
                "security-scanner",
                "scanner",
                "required",
                "bandit",
                "present",
            )
        ],
    )

    assert payload["mode"] == "serial"
    assert payload["subagent_capability"] == "absent"
    assert payload["main_thread_final_verification"] is True
    assert payload["serial_consensus_limits"]
    assert {item["role"] for item in payload["reviewer_artifacts"]} == set(probe.BASE_REVIEWERS)
    assert {item["vehicle"] for item in payload["reviewer_artifacts"]} == {
        "team-execution-serial"
    }
    assert payload["validator_artifacts"][0]["role"] == "security-scanner"
    assert payload["validator_artifacts"][0]["execution_mode"] == "serial"
    assert payload["validator_artifacts"][0]["vehicle"] == "team-execution-serial"
    assert payload["state_root"]["location"] == "repo-local"


def test_delegated_mode_records_bounds_and_safety(tmp_path: Path) -> None:
    write_gitignore(tmp_path, ".codex/\n")

    payload = probe.probe_protocol(
        repo_root=tmp_path,
        subagents="present",
        validators=[
            probe.ValidatorSpec(
                "smoke-tester",
                "tester",
                "required",
                "pytest",
                "present",
            )
        ],
    )

    assert payload["mode"] == "delegated"
    assert payload["delegation_status"] == "delegated"
    assert payload["dispatch_bounds"]["max_parallel_reviewers"] == 3
    assert {item["vehicle"] for item in payload["reviewer_artifacts"]} == {
        "team-execution-delegated"
    }
    assert payload["validator_artifacts"][0]["vehicle"] == "team-execution-delegated"
    assert payload["delegation_safety"]["subagents_authorize_mutation"] is False
    assert payload["serial_consensus_limits"] == []


def test_backpressure_uses_serial_fallback_without_hiding_capability(tmp_path: Path) -> None:
    write_gitignore(tmp_path, ".codex/team-execution/\n")

    payload = probe.probe_protocol(
        repo_root=tmp_path,
        subagents="present",
        spawn_result="backpressure",
        validators=[
            probe.ValidatorSpec(
                "scenario-tester",
                "tester",
                "required",
                "pytest",
                "present",
            )
        ],
    )

    assert payload["subagent_capability"] == "present"
    assert payload["mode"] == "serial"
    assert payload["delegation_status"] == "backpressure-fallback"
    assert {item["vehicle"] for item in payload["reviewer_artifacts"]} == {
        "team-execution-serial"
    }
    assert payload["validator_artifacts"][0]["vehicle"] == "team-execution-serial"
    assert payload["serial_consensus_limits"]


def test_unignored_repo_local_state_uses_user_local_fallback(tmp_path: Path) -> None:
    write_gitignore(tmp_path, "__pycache__/\n")

    payload = probe.probe_protocol(repo_root=tmp_path, subagents="absent")

    assert payload["state_root"]["location"] == "user-local-fallback"
    assert payload["state_root"]["path"].startswith("~/.codex/team-execution/state/")
    assert "add .codex/team-execution/ to .gitignore" in payload["state_root"]["instruction"]


def test_gitignore_negation_uses_user_local_fallback(tmp_path: Path) -> None:
    write_gitignore(tmp_path, ".codex/\n!.codex/team-execution/\n")

    payload = probe.probe_protocol(repo_root=tmp_path, subagents="absent")

    assert payload["state_root"]["location"] == "user-local-fallback"


def test_required_validator_missing_tool_blocks_with_setup_guidance(tmp_path: Path) -> None:
    write_gitignore(tmp_path, ".codex/team-execution/\n")

    payload = probe.probe_protocol(
        repo_root=tmp_path,
        subagents="absent",
        validators=[
            probe.ValidatorSpec(
                "security-scanner",
                "scanner",
                "required",
                "semgrep",
                "missing",
            )
        ],
    )

    assert payload["result"] == "blocked"
    assert payload["validator_artifacts"][0]["status"] == "blocked"
    assert payload["blockers"][0]["tool"] == "semgrep"
    assert "install or configure" in payload["blockers"][0]["setup"]


def test_cli_emits_json_and_blocks_with_nonzero_status(tmp_path: Path) -> None:
    write_gitignore(tmp_path, ".codex/team-execution/\n")
    script = Path(__file__).parents[1] / "scripts" / "protocol_probe.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo-root",
            str(tmp_path),
            "--subagents",
            "absent",
            "--validator",
            "security-scanner:scanner:required:semgrep:missing",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["result"] == "blocked"


def test_vehicle_vocabulary_documents_non_gate_assistance() -> None:
    skill = (Path(__file__).parents[1] / "skills" / "team-execution" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    evidence = (
        Path(__file__).parents[1]
        / "skills"
        / "team-execution"
        / "references"
        / "validator-evidence-state.md"
    ).read_text(encoding="utf-8")

    for body in (skill, evidence):
        assert "team-execution-delegated" in body
        assert "team-execution-serial" in body
        assert "generic-subagent" in body
        assert "inline-assist" in body
    assert "do not satisfy" in skill
    assert "not validator evidence" in evidence
