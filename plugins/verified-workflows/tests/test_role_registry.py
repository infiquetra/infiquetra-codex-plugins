from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
RENDERER_PATH = PLUGIN_ROOT / "scripts" / "render_codex_agents.py"


def _load_renderer():
    name = "verified_workflows_v2_role_renderer"
    spec = importlib.util.spec_from_file_location(name, RENDERER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = _load_renderer()


def _registry_payload() -> dict:
    return yaml.safe_load(R.DEFAULT_REGISTRY.read_text(encoding="utf-8"))


def _write_registry(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "role-registry.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_registry_preserves_exact_25_role_contracts() -> None:
    registry = R.load_role_registry()

    assert {role.role_id for role in registry.roles} == R.EXPECTED_ROLE_IDS
    assert len(registry.roles) == 25
    assert {role.kind for role in registry.roles} == {"agent-lens"}
    assert sum(role.category == "reviewer" for role in registry.roles) == 10
    assert sum(role.category == "tester" for role in registry.roles) == 8
    assert sum(role.category == "scanner" for role in registry.roles) == 4
    assert sum(role.category == "monitor" for role in registry.roles) == 3

    for role in registry.roles:
        policy = R.ROLE_PROFILE_POLICY[role.category]
        assert role.default_profile == policy["default"]
        assert role.allowed_profiles == policy["allowed"]
        assert role.workspace_cap == policy["workspace"]
        assert role.external_cap == policy["external"]
        assert role.minimum_independence == (
            "required" if role.category == "reviewer" else "preferred"
        )
        assert role.lens_sha256 is not None and len(role.lens_sha256) == 64
        assert role.result_schema in registry.result_schemas


def test_one_reviewer_is_required_and_additional_reviewers_are_risk_triggered() -> None:
    registry = R.load_role_registry()
    required = [role for role in registry.roles if role.selection_mode == "required"]

    assert registry.assurance_policy == R.ASSURANCE_POLICY
    assert [role.role_id for role in required] == ["devils-advocate-reviewer"]
    assert required[0].signals == ()
    assert all(
        role.selection_mode == "conditional" and role.signals
        for role in registry.roles
        if role.role_id != "devils-advocate-reviewer"
    )


def test_role_resolution_uses_only_underscore_profile_ids() -> None:
    registry = R.load_role_registry()

    reviewer = R.resolve_role(
        registry,
        "devils-advocate-reviewer",
        requested_profile="review_max",
    )
    worker = R.resolve_role(
        registry,
        "scenario-tester",
        requested_profile="work_high",
    )

    assert reviewer.selected_profile == "review_max"
    assert reviewer.effective_independence == "required"
    assert worker.selected_profile == "work_high"
    with pytest.raises(R.RoleRegistryError, match="cannot use profile"):
        R.resolve_role(
            registry,
            "devils-advocate-reviewer",
            requested_profile="work_high",
        )
    with pytest.raises(R.RoleRegistryError, match="cannot use profile"):
        R.resolve_role(
            registry,
            "security-scanner",
            requested_profile="test_medium",
        )
    with pytest.raises(R.RoleRegistryError, match="cannot use profile"):
        R.resolve_role(
            registry,
            "scenario-tester",
            requested_profile="test-medium",
        )


def test_result_contract_is_common_with_one_reviewer_extension() -> None:
    registry = R.load_role_registry()
    common = registry.result_schemas["assignment-result.v1"]
    reviewer = registry.result_schemas["reviewer-result.v1"]

    assert common["required_fields"] == [
        "assignment_id",
        "attempt_id",
        "agent_path",
        "role_id",
        "profile_id",
        "terminal_status",
        "summary",
        "changed_paths",
        "no_change",
        "checks",
        "findings",
        "residual_risks",
    ]
    assert reviewer["extends"] == "assignment-result.v1"
    assert reviewer["required_fields"] == [
        "dimensions",
        "exclusions",
        "denominator",
        "overall",
        "verdict",
        "hard_stop",
    ]
    serialized = yaml.safe_dump(
        {"schemas": registry.result_schemas, "types": registry.result_types}
    )
    assert "protected-evidence" not in serialized
    assert "workspace-snapshot" not in serialized


def test_registry_rejects_hyphenated_or_ultra_profile_ids(tmp_path: Path) -> None:
    payload = _registry_payload()
    payload["roles"][0]["default_profile"] = "review-high"
    hyphen_root = tmp_path / "hyphen"
    hyphen_root.mkdir()
    path = _write_registry(hyphen_root, payload)

    with pytest.raises(R.RoleRegistryError, match="profile transition"):
        R.load_role_registry(path, R.DEFAULT_ROLES_DIR)

    payload = _registry_payload()
    payload["roles"][0]["allowed_profiles"].append("ultra")
    ultra_root = tmp_path / "ultra"
    ultra_root.mkdir()
    path = _write_registry(ultra_root, payload)
    with pytest.raises(R.RoleRegistryError, match="profile transition"):
        R.load_role_registry(path, R.DEFAULT_ROLES_DIR)


def test_registry_rejects_duplicate_keys_and_yaml_aliases(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text(
        R.DEFAULT_REGISTRY.read_text(encoding="utf-8") + "schema_version: 1\n",
        encoding="utf-8",
    )
    with pytest.raises(R.RoleRegistryError, match="duplicate YAML key"):
        R.load_role_registry(duplicate, R.DEFAULT_ROLES_DIR)

    aliased = tmp_path / "aliased.yaml"
    aliased.write_text(
        R.DEFAULT_REGISTRY.read_text(encoding="utf-8").replace(
            "schema_version: 1", "schema_version: &version 1", 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(R.RoleRegistryError, match="aliases, anchors, or tags"):
        R.load_role_registry(aliased, R.DEFAULT_ROLES_DIR)


def test_registry_rejects_assurance_and_result_contract_drift(tmp_path: Path) -> None:
    payload = _registry_payload()
    payload["assurance_policy"]["required_independent_reviewers"] = 3
    root = tmp_path / "assurance"
    root.mkdir()
    path = _write_registry(root, payload)
    with pytest.raises(R.RoleRegistryError, match="assurance policy"):
        R.load_role_registry(path, R.DEFAULT_ROLES_DIR)

    payload = _registry_payload()
    payload["result_schemas"]["assignment-result.v1"]["required_fields"].pop()
    root = tmp_path / "result"
    root.mkdir()
    path = _write_registry(root, payload)
    with pytest.raises(R.RoleRegistryError, match="result schema"):
        R.load_role_registry(path, R.DEFAULT_ROLES_DIR)
