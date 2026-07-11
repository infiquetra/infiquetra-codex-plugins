from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
PLUGIN = ROOT / "plugins" / "verified-workflows"


def test_run_skill_links_every_runtime_contract() -> None:
    skill = (PLUGIN / "skills" / "run" / "SKILL.md").read_text()
    for name in (
        "workflow-protocol.md",
        "gate-policy.md",
        "validator-evidence-state.md",
        "worker-manifest.md",
        "delegation-safety.md",
    ):
        assert f"references/{name}" in skill
        assert (PLUGIN / "skills" / "run" / "references" / name).is_file()
    assert "Python scripts parse, normalize, and evaluate state" in skill
    assert "they never spawn, steer, wait for, or impersonate" in skill
    assert "Peer messaging is optional and never required" in skill
    assert "cannot approve changes to their own implementation" in skill
    assert "--agents-dir <agents-dir>" in skill
    assert "content-addressed `intent` record" in skill
    assert "root-accountability chain" in skill
    assert "every workflow step exactly" in skill


def test_hook_receipts_cover_only_supported_events_and_use_plugin_paths() -> None:
    payload = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
    assert set(payload["hooks"]) == {"SubagentStart", "SubagentStop"}
    for groups in payload["hooks"].values():
        command = groups[0]["hooks"][0]["command"]
        assert "$PLUGIN_ROOT/hooks/agent_receipt.py" in command
        assert "/Users/" not in command


def test_runtime_scripts_do_not_import_sibling_workflow_plugins() -> None:
    legacy_plugin_path = "plugins/" + "team-" + "execution"
    for path in (
        PLUGIN / "scripts" / "workflow_dispatch.py",
        PLUGIN / "scripts" / "dispatch_receipt.py",
        PLUGIN / "scripts" / "gate_evaluator.py",
        PLUGIN / "scripts" / "protocol_probe.py",
        PLUGIN / "hooks" / "agent_receipt.py",
    ):
        text = path.read_text()
        assert "plugins.saga" not in text
        assert "plugins.team_execution" not in text
        assert legacy_plugin_path not in text
