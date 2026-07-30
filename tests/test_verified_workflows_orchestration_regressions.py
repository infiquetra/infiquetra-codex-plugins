from __future__ import annotations

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
    assert "Root does not edit files" in skill
    assert "session_meta" in skill
    assert "turn_context" in skill
    assert "independent reviewer" in skill
    assert "one targeted recheck" in skill


def test_retired_v1_and_evidence_chain_surfaces_are_absent() -> None:
    for relative in (
        "hooks/hooks.json",
        "hooks/agent_receipt.py",
        "scripts/dispatch_receipt.py",
        "scripts/protected_store.py",
        "scripts/workspace_evidence.py",
        "scripts/workflow_records.py",
        "scripts/named_child_attestation.py",
        "scripts/raw_hook_maintenance.py",
    ):
        assert not (PLUGIN / relative).exists()


def test_active_guidance_and_runtime_have_no_v1_or_retired_chain_fallback() -> None:
    active_guidance = (
        ROOT / "README.md",
        ROOT / "plugins" / "fleet-core" / "README.md",
        PLUGIN / "README.md",
        PLUGIN / "skills" / "run" / "SKILL.md",
        PLUGIN / "skills" / "review-workflow" / "SKILL.md",
        ROOT / "plugins" / "saga" / "references" / "operator-choice.md",
    )
    forbidden_guidance = (
        "codex_v1_catalog.py",
        "exactly five managed",
        "five maintained profiles",
        "select stable MultiAgent V1",
        "generated full-catalog override",
        "multi_agent_v2=false",
    )
    for path in active_guidance:
        text = path.read_text()
        for token in forbidden_guidance:
            assert token not in text, f"{path}: active legacy guidance `{token}`"

    retired_modules = (
        "protected_store",
        "workspace_evidence",
        "dispatch_receipt",
        "named_child_attestation",
        "raw_hook_maintenance",
        "workflow_records",
    )
    for path in (PLUGIN / "scripts").glob("*.py"):
        text = path.read_text()
        for module in retired_modules:
            assert f"import {module}" not in text
            assert f"from {module}" not in text


def test_runtime_scripts_do_not_import_sibling_workflow_plugins() -> None:
    legacy_plugin_path = "plugins/" + "team-" + "execution"
    for path in (
        PLUGIN / "scripts" / "workflow_dispatch.py",
        PLUGIN / "scripts" / "gate_evaluator.py",
        PLUGIN / "scripts" / "protocol_probe.py",
        PLUGIN / "scripts" / "result_contract.py",
        PLUGIN / "scripts" / "run_record.py",
    ):
        text = path.read_text()
        assert "plugins.saga" not in text
        assert "plugins.team_execution" not in text
        assert legacy_plugin_path not in text
