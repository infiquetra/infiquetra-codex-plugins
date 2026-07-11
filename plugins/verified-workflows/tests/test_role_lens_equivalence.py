from __future__ import annotations

import hashlib
import importlib.util
import tomllib
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
RENDERER_PATH = PLUGIN_ROOT / "scripts" / "render_codex_agents.py"


def _load_renderer():
    name = "verified_workflows_u3_equivalence_renderer"
    spec = importlib.util.spec_from_file_location(name, RENDERER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = _load_renderer()
FROZEN_SOURCE = Path(__file__).resolve().parent / "fixtures" / "frozen-source"


def _role_text(role_id: str) -> str:
    return (PLUGIN_ROOT / "roles" / f"{role_id}.md").read_text(encoding="utf-8")


def test_every_lens_is_versioned_digest_bound_and_has_an_output_contract() -> None:
    registry = R.load_role_registry()
    roles = tuple(role for role in registry.roles if role.kind == "agent-lens")

    assert len({role.source_behavior_sha256 for role in roles}) == 25
    for role in roles:
        text = _role_text(role.role_id)
        assert f"role_id: {role.role_id}" in text
        assert "role_kind: agent-lens" in text
        assert role.source_behavior_sha256 in text
        assert role.lens_sha256 is not None
        assert role.output_schema in registry.evidence_schemas
        assert registry.evidence_schemas[role.output_schema]


def test_three_frozen_registry_sources_are_exact_digest_bound_oracles() -> None:
    registry = R.load_role_registry()

    assert {path.name for path in FROZEN_SOURCE.iterdir()} == set(R.SOURCE_FILE_SHA256)
    for name, expected in R.SOURCE_FILE_SHA256.items():
        assert hashlib.sha256((FROZEN_SOURCE / name).read_bytes()).hexdigest() == expected
    assert registry.source_behavior_policy == R.SOURCE_BEHAVIOR_POLICY
    assert registry.source_behavior_policy["docs_only_requires_full_review"] is True
    assert registry.source_behavior_policy["triage_options"] == [
        "skip-review",
        "full-review",
        "devils-advocate-only",
    ]
    assert registry.source_behavior_policy["custom_reviewer_contract"] == (
        "user-supplied-versioned-agent-lens"
    )
    assert registry.source_behavior_policy["automation_requires_default_branch"] is True
    assert registry.source_behavior_policy["required_validator_absence"] == "blocked"
    assert all(
        row == {"unit": "U7", "active": False, "gate_authority": "none"}
        for row in registry.source_behavior_policy["advisory_deferrals"].values()
    )


def test_typed_evidence_schemas_and_shared_review_gate_reach_every_profile() -> None:
    registry = R.load_role_registry()
    assert registry.evidence_schemas == R.EVIDENCE_SCHEMA_CONTRACTS
    assert registry.review_policy == R.REVIEW_POLICY
    assert registry.evidence_schemas["deploy-observation.v1"]["required_fields"][-2:] == [
        "run_status",
        "gate_status",
    ]

    bundle = R.render_bundle(registry, R.load_catalog_snapshot())
    for profile in bundle.profiles:
        instructions = tomllib.loads(profile.content.decode())["developer_instructions"]
        assert "arithmetic-mean-of-applicable-dimensions" in instructions
        assert "minimum_acceptance_average" in instructions
        assert "review-evidence.v1" in instructions
        assert "scanner-evidence.v1" in instructions
        assert "tester-evidence.v1" in instructions
        assert "monitor-evidence.v1" in instructions
        assert "deploy-observation.v1" in instructions
        assert "hard-fail and blocked prevent completion" in instructions


def test_representative_reviewer_lenses_preserve_findings_exclusions_and_hard_rules() -> None:
    expected_markers = {
        "devils-advocate-reviewer": (
            "Assumption Validity",
            "Edge Case Coverage",
            "Failure Mode Analysis",
            "Scope Creep Risk",
            "Alternatives Considered",
            "NOT redesigning the solution",
            "Preserved Scoring Rubric",
        ),
        "security-reviewer": (
            "Auth & AuthZ",
            "Secrets Management",
            "Input Validation & Injection",
            "PII / Data Privacy",
            "Dependency & Supply Chain",
            "BLOCKING",
            "Preserved Scoring Rubric",
        ),
        "architecture-reviewer": (
            "Pattern Consistency",
            "Separation of Concerns",
            "Dependency Direction",
            "static-non-applicable",
            "avg of 4 applicable",
            "Architecture Gap Suggestions",
            "Preserved Scoring Rubric",
        ),
    }

    for role_id, markers in expected_markers.items():
        text = _role_text(role_id)
        for marker in markers:
            assert marker in text, f"{role_id} lost {marker!r}"


def test_representative_validator_lenses_preserve_evidence_and_stop_conditions() -> None:
    expected_markers = {
        "scenario-tester": (
            "Acceptance criteria",
            "full workflows",
            "Meaningful edge cases surfaced by reviewers",
            "hard-fail",
        ),
        "security-scanner": (
            "Secret-like values",
            "injection",
            "SSRF-style",
            "Record commands, exit codes",
            "mark the gate blocked",
        ),
        "runtime-monitor": (
            "Time window",
            "healthy",
            "degraded",
            "missing signal",
            "not applicable",
        ),
    }

    for role_id, markers in expected_markers.items():
        text = _role_text(role_id)
        for marker in markers:
            assert marker in text, f"{role_id} lost {marker!r}"


def test_deploy_observer_cannot_mutate_workflows() -> None:
    text = _role_text("deploy-watcher")

    assert "observe only" in text
    assert "root thread alone may initiate" in text
    assert "No workflow dispatch, approval, retry, cancellation" in text
    assert "No production, staging, force-push, branch deletion" in text
    assert "default-branch model" in text
    assert "separate typed validator gate status" in text


def test_ai_usefulness_lens_uses_codex_instruction_surfaces() -> None:
    text = _role_text("ai-usefulness-reviewer")

    assert "AGENTS.md" in text
    assert "Context Gap Questions" in text
    assert "Machine-Parseable Structure" in text
