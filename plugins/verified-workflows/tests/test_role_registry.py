from __future__ import annotations

import dataclasses
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


def test_registry_preserves_exact_role_contracts() -> None:
    registry = R.load_role_registry()

    assert {role.role_id for role in registry.roles} == R.EXPECTED_ROLE_IDS
    assert len(registry.roles) == 29
    assert {role.kind for role in registry.roles} == {"agent-lens"}
    assert sum(role.category == "reviewer" for role in registry.roles) == 10
    assert sum(role.category == "tester" for role in registry.roles) == 8
    assert sum(role.category == "scanner" for role in registry.roles) == 4
    assert sum(role.category == "monitor" for role in registry.roles) == 3

    spec_fields = {field.name for field in dataclasses.fields(R.RoleSpec)}
    assert "allowed_profiles" not in spec_fields
    assert "workspace_cap" not in spec_fields
    assert "external_cap" not in spec_fields

    for role in registry.roles:
        assert role.default_profile in R.PROFILE_IDS
        assert not hasattr(role, "workspace_cap")
        assert not hasattr(role, "external_cap")
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
            "scenario-tester",
            requested_profile="test-medium",
        )


def test_any_managed_profile_may_be_requested_for_any_role() -> None:
    registry = R.load_role_registry()

    git_operator = R.resolve_role(
        registry,
        "git-integration-operator",
        requested_profile="work_high",
    )
    scanner = R.resolve_role(
        registry,
        "security-scanner",
        requested_profile="test_medium",
    )
    reviewer = R.resolve_role(
        registry,
        "devils-advocate-reviewer",
        requested_profile="work_high",
    )

    assert git_operator.selected_profile == "work_high"
    assert scanner.selected_profile == "test_medium"
    assert reviewer.selected_profile == "work_high"
    assert reviewer.effective_independence == "required"


def test_role_resolution_without_a_request_falls_back_to_the_default_profile() -> None:
    registry = R.load_role_registry()

    for role in registry.roles:
        resolution = R.resolve_role(registry, role.role_id)
        assert resolution.selected_profile == role.default_profile

    assert R.resolve_role(registry, "git-integration-operator").selected_profile == "work_medium"


def test_harness_integration_role_defaults_to_work_high_without_adding_a_profile() -> None:
    registry = R.load_role_registry()
    role = registry.role("harness-integration-engineer")
    resolution = R.resolve_role(registry, role.role_id)

    assert role.category == "worker"
    assert role.result_schema == "assignment-result.v1"
    assert resolution.selected_profile == "work_high"
    assert R.PROFILE_IDS == (
        "review_max",
        "review_high",
        "work_medium",
        "work_high",
        "test_medium",
        "scan_low",
        "monitor_low",
    )


def test_registry_rejects_a_role_carrying_a_stale_boundaries_block(tmp_path: Path) -> None:
    payload = _registry_payload()
    payload["roles"][0]["boundaries"] = {
        "workspace_cap": "declared-write",
        "external_cap": "none",
        "external_mutation": "forbidden",
        "profile_may_not_widen_role": True,
    }
    stale_root = tmp_path / "boundaries"
    stale_root.mkdir()
    path = _write_registry(stale_root, payload)

    with pytest.raises(R.RoleRegistryError, match=r"role \S+ fields must be exactly"):
        R.load_role_registry(path, R.DEFAULT_ROLES_DIR)


def test_registry_rejects_a_role_carrying_a_stale_allowed_profiles_key(
    tmp_path: Path,
) -> None:
    payload = _registry_payload()
    payload["roles"][0]["allowed_profiles"] = ["work_medium", "work_high"]
    stale_root = tmp_path / "allowed"
    stale_root.mkdir()
    path = _write_registry(stale_root, payload)

    with pytest.raises(R.RoleRegistryError, match=r"role \S+ fields must be exactly"):
        R.load_role_registry(path, R.DEFAULT_ROLES_DIR)


def test_registry_rejects_independence_that_disagrees_with_the_category(
    tmp_path: Path,
) -> None:
    payload = _registry_payload()
    reviewer_row = next(row for row in payload["roles"] if row["category"] == "reviewer")
    reviewer_row["minimum_independence"] = "preferred"
    root = tmp_path / "independence"
    root.mkdir()
    path = _write_registry(root, payload)

    with pytest.raises(R.RoleRegistryError, match="minimum_independence must be"):
        R.load_role_registry(path, R.DEFAULT_ROLES_DIR)


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

    with pytest.raises(R.RoleRegistryError, match="default_profile is not a managed profile"):
        R.load_role_registry(path, R.DEFAULT_ROLES_DIR)

    registry = R.load_role_registry()
    for outside in ("ultra", "root", "review-high"):
        with pytest.raises(R.RoleRegistryError, match="cannot use profile"):
            R.resolve_role(
                registry,
                "implementation-worker",
                requested_profile=outside,
            )


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


def test_bundle_receipt_drops_the_removed_capability_keys() -> None:
    bundle = R.render_bundle(R.load_role_registry(), R.load_catalog_snapshot())
    receipt = R.bundle_receipt(bundle)

    assert len(receipt["roles"]) == 29
    assert len(receipt["profiles"]) == 7
    removed = {"allowed_profiles", "workspace_cap", "external_cap"}
    for role in receipt["roles"]:
        assert removed.isdisjoint(role)
        assert role["default_profile"] in R.PROFILE_IDS
        assert role["selected_profile"] in R.PROFILE_IDS
    assert removed.isdisjoint(set().union(*(set(p) for p in receipt["profiles"])))
