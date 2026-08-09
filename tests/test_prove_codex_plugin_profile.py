from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def load_proof_script() -> ModuleType:
    script = ROOT / "scripts" / "prove_codex_plugin_profile.py"
    spec = importlib.util.spec_from_file_location("prove_codex_plugin_profile", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


proof_script = load_proof_script()


def test_generate_static_proof_contains_required_evidence(tmp_path: Path) -> None:
    proof = proof_script.generate_proof(
        repo_root=ROOT,
        proof_root=tmp_path,
        run_id="test-run",
        install_mode="static",
    )

    assert proof["default_profile_mutated"] is False
    assert proof["installed_plugins"] == list(proof_script.CURRENT_INSTALL_PLUGINS)
    upgrade = next(profile for profile in proof["profiles"] if profile["name"] == "upgrade-from-old")
    assert set(upgrade["seeded_inventory"]).isdisjoint(upgrade["replacement_inventory"])
    assert "team-execution" in upgrade["seeded_inventory"]
    assert upgrade["old_inventory_absent"] is True
    assert {item["skill"] for item in proof["namespace_proof"]} == {
        "saga:plan",
        "saga:work",
        "saga:brainstorm",
    }
    assert all(proof["old_skill_absence"].values())
    assert proof["flows"]["saga"]["source_workflow_excluded"] is True
    assert proof["flows"]["deploy"]["confirmation_required"] is True
    assert proof["flows"]["deploy"]["mutation_occurred"] is False
    assert proof["flows"]["mission_control"]["mutation_plan_present"] is True
    assert proof["flows"]["mission_control"]["confirmation_refused"] is True
    assert proof["flows"]["mission_control"]["mutation_occurred"] is False
    assert proof["flows"]["verified_workflows"]["outcome"] == "diagnostic"
    assert proof["flows"]["verified_workflows"]["runtime_proof"] is False
    assert proof["flows"]["verified_workflows"]["root_acceptance_required"] is True
    assert proof["state_proof"]["ignored"][".codex/saga/"] is True
    assert proof["state_proof"]["ignored"][".codex/verified-workflows/"] is True
    assert proof["state_proof"]["legacy_readable_roots"] == [".codex/team-execution/"]
    assert proof["state_proof"]["ignored"][".codex/proofs/"] is True


def test_rendered_markdown_redacts_local_profile_paths() -> None:
    proof = {
        "created_at": "2026-06-06T00:00:00+00:00",
        "run_id": "test-run",
        "profile_class": "isolated repo-local CODEX_HOME under ignored .codex/proofs",
        "default_profile_mutated": False,
        "marketplace": {"name": "infiquetra-saga-family-proof"},
        "installed_plugins": list(proof_script.CURRENT_INSTALL_PLUGINS),
        "codex_cli_install": {"mode": "static", "executed": False},
        "flows": {
            "saga": {"recommended": "verified-workflow", "source_workflow_excluded": True},
            "deploy": {"mutation_occurred": False, "confirmation_required": True},
            "mission_control": {
                "readiness_passed": True,
                "mutation_plan_present": True,
                "confirmation_refused": True,
            },
            "verified_workflows": {"outcome": "diagnostic", "runtime_proof": False},
        },
    }
    text = proof_script.render_markdown(proof)

    assert str(Path.home()) not in text
    assert ".codex/proofs/saga-family/<run-id>/" in text
    assert "saga:plan" in text
    assert "Default profile mutated: `false`" in text


def test_target_fixture_identity_is_read_only_and_released() -> None:
    before = (ROOT / ".agents" / "plugins" / "marketplace.json").read_bytes()

    proof = proof_script.target_fixture_identity(ROOT)

    assert proof["mode"] == "target-fixture"
    assert proof["workflow_plugin"] == "verified-workflows"
    assert proof["workflow_version"] == "3.1.0"
    assert proof["workflow_skills"] == ["appsec-audit", "review-workflow", "run"]
    assert proof["publication_status"] == "released"
    assert proof["legacy_workflow_marketplace_listed"] is False
    assert proof["target_workflow_marketplace_listed"] is True
    assert proof["installed_plugin_state"] == "unobserved-by-static-proof"
    assert proof["profile_state"] == "unobserved"
    assert proof["cache_state"] == "unobserved"
    assert "default_profile_mutated" not in proof
    assert (ROOT / ".agents" / "plugins" / "marketplace.json").read_bytes() == before
