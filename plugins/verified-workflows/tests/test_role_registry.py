from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import yaml


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
RENDERER_PATH = PLUGIN_ROOT / "scripts" / "render_codex_agents.py"


def _load_renderer():
    name = "verified_workflows_u3_role_renderer"
    spec = importlib.util.spec_from_file_location(name, RENDERER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = _load_renderer()


def test_registry_preserves_exact_25_role_contracts() -> None:
    registry = R.load_role_registry()

    assert {role.role_id for role in registry.roles} == R.EXPECTED_ROLE_IDS
    assert len(registry.roles) == 25
    assert {role.kind for role in registry.roles} == {"agent-lens"}
    assert all(role.minimum_independence == "preferred" for role in registry.roles)
    assert sum(role.category == "reviewer" for role in registry.roles) == 10
    assert sum(role.category == "tester" for role in registry.roles) == 8
    assert sum(role.category == "scanner" for role in registry.roles) == 4
    assert sum(role.category == "monitor" for role in registry.roles) == 3

    for role in registry.roles:
        policy = R.CLASS_POLICY[role.category]
        assert role.default_class == policy["default"]
        assert role.allowed_classes == policy["allowed"]
        assert role.workspace_cap == policy["workspace"]
        assert role.external_cap == policy["external"]
        assert role.lens_sha256 is not None and len(role.lens_sha256) == 64
        assert role.output_schema in registry.evidence_schemas


def test_role_resolution_allows_only_declared_escalation_and_independence() -> None:
    registry = R.load_role_registry()
    reviewer = R.resolve_role(
        registry,
        "devils-advocate-reviewer",
        requested_class="review-max",
        requested_independence="required",
    )

    assert reviewer.selected_class == "review-max"
    assert reviewer.effective_independence == "required"
    with pytest.raises(R.RoleRegistryError, match="cannot use execution class"):
        R.resolve_role(registry, "devils-advocate-reviewer", requested_class="test-medium")

    required_role = replace(registry.role("security-reviewer"), minimum_independence="required")
    required_registry = replace(
        registry,
        roles=tuple(
            required_role if role.role_id == required_role.role_id else role
            for role in registry.roles
        ),
    )
    with pytest.raises(R.RoleRegistryError, match="cannot be lowered"):
        R.resolve_role(
            required_registry,
            "security-reviewer",
            requested_independence="preferred",
        )


def _synthetic_registry(tmp_path: Path) -> tuple[Path, Path, dict]:
    roles_dir = tmp_path / "roles"
    schemas_dir = tmp_path / "schemas"
    scripts_dir = tmp_path / "scripts"
    roles_dir.mkdir(parents=True)
    schemas_dir.mkdir()
    scripts_dir.mkdir()
    evidence = schemas_dir / "proof.json"
    evidence.write_text('{"type":"object"}\n', encoding="utf-8")
    implementation = scripts_dir / "check.py"
    implementation.write_text("raise SystemExit(0)\n", encoding="utf-8")
    payload = yaml.safe_load(R.DEFAULT_REGISTRY.read_text(encoding="utf-8"))
    payload["roles"] = [
        {
            "id": "bounded-validator",
            "kind": "deterministic-validator",
            "category": "scanner",
            "spec_version": 1,
            "description": "Run one contained validator and emit its closed evidence.",
            "selection": {"mode": "conditional", "signals": ["bounded proof"]},
            "command": {
                "argv": ["python3", "scripts/check.py", "--json"],
                "implementation": {
                    "path": "scripts/check.py",
                    "sha256": hashlib.sha256(implementation.read_bytes()).hexdigest(),
                },
                "cwd_scope": "repository",
                "timeout_seconds": 30,
                "output_limit_bytes": 65536,
                "network": "none",
                "workspace_writes": [],
            },
            "evidence_schema": {
                "path": "schemas/proof.json",
                "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
            },
            "output_schema": "scanner-evidence.v1",
            "source_behavior_sha256": "0" * 64,
        }
    ]
    registry_path = tmp_path / "role-registry.yaml"
    registry_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return registry_path, roles_dir, payload


def test_deterministic_validator_union_has_no_model_class_or_independence(tmp_path: Path) -> None:
    registry_path, roles_dir, _payload = _synthetic_registry(tmp_path)

    registry = R.load_role_registry(
        registry_path,
        roles_dir,
        expected_role_ids=None,
    )
    role = registry.roles[0]

    assert role.kind == "deterministic-validator"
    assert role.command == ("python3", "scripts/check.py", "--json")
    assert role.command_implementation_path == "scripts/check.py"
    assert role.command_implementation_sha256 == hashlib.sha256(
        (tmp_path / "scripts" / "check.py").read_bytes()
    ).hexdigest()
    assert role.default_class is None
    assert role.allowed_classes == ()
    assert role.minimum_independence is None
    assert R.resolve_role(registry, role.role_id).selected_class is None
    with pytest.raises(R.RoleRegistryError, match="do not accept class"):
        R.resolve_role(registry, role.role_id, requested_class="scan-low")


def test_deterministic_validator_rejects_mixed_agent_fields(tmp_path: Path) -> None:
    registry_path, roles_dir, payload = _synthetic_registry(tmp_path)
    payload["roles"][0]["default_class"] = "scan-low"
    registry_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(R.RoleRegistryError, match="fields must be exactly"):
        R.load_role_registry(registry_path, roles_dir, expected_role_ids=None)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (("spec_version", 2), "spec_version"),
        (("category", "unknown"), "category"),
    ],
)
def test_deterministic_validator_rejects_invalid_closed_contract(
    tmp_path: Path,
    mutation: tuple[str, object],
    match: str,
) -> None:
    registry_path, roles_dir, payload = _synthetic_registry(tmp_path)
    payload["roles"][0][mutation[0]] = mutation[1]
    registry_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(R.RoleRegistryError, match=match):
        R.load_role_registry(registry_path, roles_dir, expected_role_ids=None)


def test_deterministic_validator_rejects_escaping_argument_and_digest_drift(
    tmp_path: Path,
) -> None:
    registry_path, roles_dir, payload = _synthetic_registry(tmp_path)
    payload["roles"][0]["command"]["argv"].append("../../outside")
    registry_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(R.RoleRegistryError, match="must not escape"):
        R.load_role_registry(registry_path, roles_dir, expected_role_ids=None)

    registry_path, roles_dir, payload = _synthetic_registry(tmp_path / "digest")
    payload["roles"][0]["command"]["implementation"]["sha256"] = "0" * 64
    registry_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(R.RoleRegistryError, match="implementation digest drifted"):
        R.load_role_registry(registry_path, roles_dir, expected_role_ids=None)


def test_registry_rejects_duplicate_keys_and_yaml_aliases(tmp_path: Path) -> None:
    registry_path, roles_dir, _payload = _synthetic_registry(tmp_path)
    duplicate = registry_path.read_text(encoding="utf-8") + "schema_version: 1\n"
    registry_path.write_text(duplicate, encoding="utf-8")
    with pytest.raises(R.RoleRegistryError, match="duplicate YAML key"):
        R.load_role_registry(registry_path, roles_dir, expected_role_ids=None)

    registry_path, roles_dir, _payload = _synthetic_registry(tmp_path / "alias")
    aliased = registry_path.read_text(encoding="utf-8").replace(
        "schema_version: 1", "schema_version: &version 1", 1
    )
    registry_path.write_text(aliased, encoding="utf-8")
    with pytest.raises(R.RoleRegistryError, match="aliases, anchors, or tags"):
        R.load_role_registry(registry_path, roles_dir, expected_role_ids=None)


def test_registry_rejects_nonstring_keys_and_closed_policy_drift(tmp_path: Path) -> None:
    registry_path, roles_dir, _payload = _synthetic_registry(tmp_path / "keys")
    registry_path.write_text(
        registry_path.read_text(encoding="utf-8") + "1: unexpected\n",
        encoding="utf-8",
    )
    with pytest.raises(R.RoleRegistryError, match="field names must be strings"):
        R.load_role_registry(registry_path, roles_dir, expected_role_ids=None)

    registry_path, roles_dir, payload = _synthetic_registry(tmp_path / "selection")
    payload["selection_config_keys"].pop()
    registry_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(R.RoleRegistryError, match="selection config keys drifted"):
        R.load_role_registry(registry_path, roles_dir, expected_role_ids=None)

    registry_path, roles_dir, payload = _synthetic_registry(tmp_path / "schema")
    payload["evidence_schemas"]["scanner-evidence.v1"]["required_fields"].pop()
    registry_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises(R.RoleRegistryError, match="field_types must cover"):
        R.load_role_registry(registry_path, roles_dir, expected_role_ids=None)


def test_role_output_schema_is_category_specific(tmp_path: Path) -> None:
    registry_path, roles_dir, payload = _synthetic_registry(tmp_path)
    payload["roles"][0]["output_schema"] = "tester-evidence.v1"
    registry_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(R.RoleRegistryError, match="invalid for category"):
        R.load_role_registry(registry_path, roles_dir, expected_role_ids=None)


def test_roles_directory_must_not_be_a_symlink(tmp_path: Path) -> None:
    real_roles = tmp_path / "real-roles"
    shutil.copytree(R.DEFAULT_ROLES_DIR, real_roles)
    linked_roles = tmp_path / "roles"
    linked_roles.symlink_to(real_roles, target_is_directory=True)

    with pytest.raises(R.RoleRegistryError, match="real directory"):
        R.load_role_registry(R.DEFAULT_REGISTRY, linked_roles)


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink"])
def test_role_lens_must_be_regular_single_link(tmp_path: Path, unsafe: str) -> None:
    copied = tmp_path / "plugin"
    (copied / "config").mkdir(parents=True)
    shutil.copy2(R.DEFAULT_REGISTRY, copied / "config" / "role-registry.yaml")
    shutil.copytree(R.DEFAULT_ROLES_DIR, copied / "roles")
    target = copied / "roles" / "security-reviewer.md"
    original = target.read_bytes()
    target.unlink()
    backing = copied / "backing.md"
    backing.write_bytes(original)
    if unsafe == "symlink":
        target.symlink_to(backing)
    else:
        os.link(backing, target)

    with pytest.raises(R.RoleRegistryError, match="regular, single-link"):
        R.load_role_registry(copied / "config" / "role-registry.yaml", copied / "roles")
