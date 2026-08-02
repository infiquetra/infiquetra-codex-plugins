from __future__ import annotations

import hashlib
import importlib.util
import shutil
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
if str(PLUGIN_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import workflow_dispatch as W  # noqa: E402

FROZEN_SOURCE = Path(__file__).resolve().parent / "fixtures" / "frozen-source"


def _role_text(role_id: str) -> str:
    return (PLUGIN_ROOT / "roles" / f"{role_id}.md").read_text(encoding="utf-8")


def test_every_lens_is_versioned_digest_bound_and_has_a_result_contract() -> None:
    registry = R.load_role_registry()
    roles = tuple(role for role in registry.roles if role.kind == "agent-lens")

    assert len({role.source_behavior_sha256 for role in roles}) == 29
    for role in roles:
        text = _role_text(role.role_id)
        assert f"role_id: {role.role_id}" in text
        assert "role_kind: agent-lens" in text
        assert role.source_behavior_sha256 in text
        assert role.lens_sha256 is not None
        assert role.result_schema in registry.result_schemas
        assert registry.result_schemas[role.result_schema]


def test_three_frozen_registry_sources_are_exact_digest_bound_oracles() -> None:
    registry = R.load_role_registry()

    assert {path.name for path in FROZEN_SOURCE.iterdir()} == set(R.SOURCE_FILE_SHA256)
    for name, expected in R.SOURCE_FILE_SHA256.items():
        assert hashlib.sha256((FROZEN_SOURCE / name).read_bytes()).hexdigest() == expected
    assert registry.assurance_policy == R.ASSURANCE_POLICY
    assert registry.assurance_policy["required_independent_reviewers"] == 1
    assert registry.assurance_policy["additional_reviewer_selection"] == "risk-triggered"


def test_common_result_schema_and_reviewer_extension_reach_every_profile() -> None:
    registry = R.load_role_registry()
    assert registry.result_schemas == R.RESULT_SCHEMA_CONTRACTS
    assert registry.result_types == R.RESULT_TYPE_CONTRACTS
    assert registry.review_policy == R.REVIEW_POLICY

    bundle = R.render_bundle(registry, R.load_catalog_snapshot())
    for profile in bundle.profiles:
        instructions = tomllib.loads(profile.content.decode())["developer_instructions"]
        assert "compute defaults, not logical-role identity" in instructions
        assert "requested typed result" in instructions
        assert "Runtime identity and permissions come from Codex" in instructions
        assert "minimum_acceptance_average" not in instructions
        assert "sandbox_mode" not in tomllib.loads(profile.content.decode())
    assert registry.result_types["finding"]["scope_dispositions"] == [
        "planned",
        "one-hop",
        "defer",
        "approval-required",
    ]
    assert registry.review_policy["scores_are_advisory"] is True


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
            "proportional engineering review",
            "actual P0/P1",
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


def test_harness_integration_lens_preserves_its_specialized_behavior() -> None:
    text = _role_text("harness-integration-engineer")

    for marker in (
        "native harness",
        "adapter boundaries",
        "producer-owned contracts",
        "unsupported features",
        "adversarial compatibility checks",
        "release metadata",
    ):
        assert marker in text


def _harness_workflow_plan() -> str:
    return """# Plan

## Workflow Contract

| id | depends | role | profile | writes | completion | fallback |
| --- | --- | --- | --- | --- | --- | --- |
| integrate | - | harness-integration-engineer | work_high | src/adapter.py | adapter passes compatibility checks | none |
| review | integrate | devils-advocate-reviewer | review_high | none | reviewer result has no blocking finding | none |

### Blocking Checks

| id | owner | after | command-or-proof | blocking | failure |
| --- | --- | --- | --- | --- | --- |
| reviewer-assurance | review | review | reviewer result satisfies policy | yes | stop |

### External Actions

`External actions: []` is the exact approved value.

## Implementation Units
"""


def test_harness_lens_bytes_bind_compiler_authority_and_operator_approval(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "role-registry.yaml"
    registry_path.write_bytes(R.DEFAULT_REGISTRY.read_bytes())
    roles_dir = tmp_path / "roles"
    shutil.copytree(R.DEFAULT_ROLES_DIR, roles_dir)

    approved = W.compile_workflow_contract(
        _harness_workflow_plan(),
        plan_revision="approved-harness-role",
        registry_path=registry_path,
        roles_dir=roles_dir,
    )
    target = roles_dir / "harness-integration-engineer.md"
    target.write_text(
        target.read_text(encoding="utf-8").replace(
            "adapter boundaries", "adapter integration boundaries", 1
        ),
        encoding="utf-8",
    )
    changed = W.compile_workflow_contract(
        _harness_workflow_plan(),
        plan_revision="approved-harness-role",
        registry_path=registry_path,
        roles_dir=roles_dir,
    )

    approved_spec = next(
        spec for spec in approved.launch_specs if spec.assignment_id == "integrate"
    )
    changed_spec = next(spec for spec in changed.launch_specs if spec.assignment_id == "integrate")
    assert changed.contract_sha256 == approved.contract_sha256
    assert changed.registry_sha256 == approved.registry_sha256
    assert changed_spec.role_lens_sha256 != approved_spec.role_lens_sha256
    assert changed.authority_sha256 != approved.authority_sha256
    assert changed.approval_binding_sha256 != approved.approval_binding_sha256
