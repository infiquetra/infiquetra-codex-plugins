"""Tests for repo validation."""

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import validate_codex_plugins as validator
from scripts.validate_codex_plugins import (
    CURRENT_EXPECTED_PLUGINS,
    EXPECTED_PLUGINS,
    LEGACY_EXPECTED_PLUGINS,
    LEGACY_TEAM_EXECUTION_FILE_COUNT,
    LEGACY_TEAM_EXECUTION_TREE_SHA256,
    LEGACY_WORKFLOW_HISTORY_SENTINELS,
    LEGACY_WORKFLOW_INVENTORY,
    MODERNIZATION_CUTOVER_VERSIONS,
    REQUIRED_LEGACY_STATE_ROOTS,
    TARGET_EXPECTED_PLUGINS,
    compare_inventory,
    expected_legacy_workflow_classification,
    legacy_workflow_file_facts,
    validate_legacy_workflow_token_allowlist,
    validate_legacy_history_sentinels,
    validate_saga_workflow_independence,
    validate_verified_workflows_agents,
    validate_verified_workflows_canonical_surface,
    validate_verified_workflows_project_agents,
    validate_verified_workflows_runtime,
    workflow_registry_sha256,
    validate_relative_file,
    validate_repository,
    validate_port_contract,
    validate_target_fixture_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def make_verified_workflows_target(tmp_path: Path, filename: str, body: str) -> Path:
    target = tmp_path / "plugins" / "verified-workflows"
    target.mkdir(parents=True)
    (target / filename).write_text(body, encoding="utf-8")
    (target / "PORTABILITY.md").write_text(
        "This is a behavior adaptation, not an upstream byte-parity claim.\n",
        encoding="utf-8",
    )
    return target


def write_legacy_workflow_inventory(
    root: Path,
    classified_paths: dict[str, str],
) -> None:
    legacy_tokens = {
        value for entry in validator.WORKFLOW_COMPAT.REGISTRY.values() for value in entry.legacy
    }
    entries = []
    for raw_path, classification in sorted(classified_paths.items()):
        content = (root / raw_path).read_bytes()
        text = content.decode("utf-8")
        entries.append(
            {
                "path": raw_path,
                "classification": classification,
                "tokens": sorted(token for token in legacy_tokens if token in text),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    payload = {
        "schema_version": 1,
        "generated_by": "scripts/build_legacy_workflow_inventory.py",
        "workflow_registry_sha256": workflow_registry_sha256(),
        "legacy_team_execution_tree": {
            "file_count": LEGACY_TEAM_EXECUTION_FILE_COUNT,
            "sha256": LEGACY_TEAM_EXECUTION_TREE_SHA256,
        },
        "history_sentinels": validator.serialized_legacy_history_sentinels(),
        "historical_inventory_sha256": validator.legacy_historical_entries_sha256(entries),
        "entries": entries,
    }
    path = root / LEGACY_WORKFLOW_INVENTORY
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def copy_verified_workflows_runtime_target(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(
        REPO_ROOT / "plugins" / "verified-workflows",
        root / "plugins" / "verified-workflows",
    )
    shutil.copytree(
        REPO_ROOT / "plugins" / "fleet-core",
        root / "plugins" / "fleet-core",
    )
    (root / "scripts").mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / "scripts" / "prove_verified_workflows_runtime.py",
        root / "scripts" / "prove_verified_workflows_runtime.py",
    )
    shutil.copytree(REPO_ROOT / ".codex" / "agents", root / ".codex" / "agents")
    (root / "docs" / "validation").mkdir(parents=True)
    for name in (
        "codex-runtime-capability-snapshot.json",
        "verified-workflows-runtime-proof.json",
    ):
        shutil.copy2(
            REPO_ROOT / "docs" / "validation" / name,
            root / "docs" / "validation" / name,
        )
    return root


def test_current_repository_validates():
    assert validate_repository(REPO_ROOT) == []
    assert validate_repository(REPO_ROOT, mode="current") == []


def test_target_fixture_validates_without_active_cutover():
    assert validate_repository(REPO_ROOT, mode="target-fixture") == []


def test_cutover_validation_passes_after_u8_release_evidence():
    assert validate_repository(REPO_ROOT, mode="cutover") == []


def test_current_mode_rejects_pending_real_profile_cutover(monkeypatch):
    path = (
        REPO_ROOT
        / "docs"
        / "validation"
        / "codex-plugin-modernization-cutover.json"
    )
    pending = json.loads(path.read_text(encoding="utf-8"))
    pending["status"] = "isolated-gates-passed-real-profile-pending"
    pending["real_profile"] = {
        "apply_started": False,
        "applied": False,
        "fresh_session": "pending",
        "rollback_status": "not-needed",
        "installed_readback": None,
        "profile_readback": None,
    }
    monkeypatch.setattr(validator, "load_json", lambda _path, _errors: pending)
    errors: list[str] = []

    validator.validate_modernization_cutover_record(REPO_ROOT, path, "current", errors)

    assert any("real-profile cutover evidence is incomplete" in error for error in errors)


def test_modernization_cutover_versions_are_frozen_receipt_values():
    path = (
        REPO_ROOT
        / "docs"
        / "validation"
        / "codex-plugin-modernization-cutover.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["versions"] == MODERNIZATION_CUTOVER_VERSIONS
    assert MODERNIZATION_CUTOVER_VERSIONS["fleet-core"] != (
        TARGET_EXPECTED_PLUGINS["fleet-core"]["version"]
    )
    assert MODERNIZATION_CUTOVER_VERSIONS["verified-workflows"] != (
        TARGET_EXPECTED_PLUGINS["verified-workflows"]["version"]
    )


def test_current_and_target_fixture_run_classification_port_gate():
    errors: list[str] = []

    validate_port_contract(REPO_ROOT, "classification", errors)

    assert errors == []


def test_expected_plugin_set_is_current_post_cutover_inventory():
    assert set(EXPECTED_PLUGINS) == {
        "saga",
        "deploy",
        "mission-control",
        "verified-workflows",
        "discord-identity-assets",
        "home-lab-ops",
        "python-toolkit",
        "unifi",
        "test-suite",
        "fleet-core",
    }
    assert EXPECTED_PLUGINS is CURRENT_EXPECTED_PLUGINS
    assert EXPECTED_PLUGINS is TARGET_EXPECTED_PLUGINS


def test_legacy_plugin_set_remains_only_for_migration_checks():
    assert set(LEGACY_EXPECTED_PLUGINS) == {
        "blueprint-reviewer",
        "home-lab-ops",
        "python-toolkit",
        "sdlc-manager",
        "unifi",
        "test-suite",
    }
    assert {"blueprint-reviewer", "sdlc-manager"}.isdisjoint(EXPECTED_PLUGINS)


def test_target_plugin_set_describes_saga_family_cutover():
    assert set(TARGET_EXPECTED_PLUGINS) == {
        "saga",
        "deploy",
        "mission-control",
        "verified-workflows",
        "discord-identity-assets",
        "home-lab-ops",
        "python-toolkit",
        "unifi",
        "test-suite",
        "fleet-core",
    }
    assert {"plan", "work", "brainstorm"} <= set(TARGET_EXPECTED_PLUGINS["saga"]["skills"])
    assert TARGET_EXPECTED_PLUGINS["discord-identity-assets"]["skills"] == (
        "discord-identity-assets",
    )
    assert TARGET_EXPECTED_PLUGINS["verified-workflows"] == {
        "version": "1.0.3+codex.20260718134043",
        "skills": ("run", "review-workflow", "appsec-audit", "select-agent"),
    }
    assert "team-execution" not in TARGET_EXPECTED_PLUGINS
    assert {"blueprint-reviewer", "sdlc-manager"}.isdisjoint(TARGET_EXPECTED_PLUGINS)


def test_target_fixture_requires_namespace_proof():
    payload = {
        "plugins": [
            {
                "name": name,
                "version": spec["version"],
                "skills": list(spec["skills"]),
                "forbidden_active_dirs": (
                    [".claude-plugin", "commands"]
                    if name == "verified-workflows"
                    else [".claude-plugin", "commands", "agents"]
                ),
            }
            for name, spec in TARGET_EXPECTED_PLUGINS.items()
        ],
        "schema_version": "2.0",
        "removed_plugins": ["blueprint-reviewer", "sdlc-manager", "team-execution"],
        "unpublished_plugins": [],
        "legacy_readable_plugins": ["team-execution"],
        "required_namespace_proof": [
            "saga:plan",
            "saga:work",
            "verified-workflows:run",
            "verified-workflows:appsec-audit",
        ],
        "required_state_roots": [".codex/saga/", ".codex/verified-workflows/"],
        "legacy_readable_state_roots": [".codex/team-execution/"],
        "mutation_gate_plugins": ["deploy", "mission-control", "discord-identity-assets"],
    }
    errors: list[str] = []

    validate_target_fixture_payload(payload, REPO_ROOT / "fixture.json", errors)

    assert any("saga:brainstorm" in error for error in errors)


def test_target_fixture_requires_discord_identity_assets_mutation_gate():
    payload = {
        "plugins": [
            {
                "name": name,
                "version": spec["version"],
                "skills": list(spec["skills"]),
                "forbidden_active_dirs": (
                    [".claude-plugin", "commands"]
                    if name == "verified-workflows"
                    else [".claude-plugin", "commands", "agents"]
                ),
            }
            for name, spec in TARGET_EXPECTED_PLUGINS.items()
        ],
        "schema_version": "2.0",
        "removed_plugins": ["blueprint-reviewer", "sdlc-manager", "team-execution"],
        "unpublished_plugins": [],
        "legacy_readable_plugins": ["team-execution"],
        "required_namespace_proof": [
            "saga:plan",
            "saga:work",
            "saga:brainstorm",
            "verified-workflows:run",
            "verified-workflows:appsec-audit",
        ],
        "required_state_roots": [".codex/saga/", ".codex/verified-workflows/"],
        "legacy_readable_state_roots": [".codex/team-execution/"],
        "mutation_gate_plugins": ["deploy", "mission-control"],
    }
    errors: list[str] = []

    validate_target_fixture_payload(payload, REPO_ROOT / "fixture.json", errors)

    assert any("discord-identity-assets" in error for error in errors)


def test_target_fixture_rejects_duplicate_plugin_entries():
    payload = {
        "schema_version": "2.0",
        "plugins": [
            {
                "name": "verified-workflows",
                "version": "1.0.3+codex.20260718134043",
                "publication_status": "released",
                "skills": ["run", "review-workflow", "appsec-audit", "select-agent"],
                "forbidden_active_dirs": [".claude-plugin", "commands"],
            },
            {
                "name": "verified-workflows",
                "version": "1.0.3+codex.20260718134043",
                "publication_status": "released",
                "skills": ["run", "review-workflow", "appsec-audit", "select-agent"],
                "forbidden_active_dirs": [".claude-plugin", "commands"],
            },
        ],
    }
    errors: list[str] = []

    validate_target_fixture_payload(payload, REPO_ROOT / "fixture.json", errors)

    assert any("duplicate plugin entry `verified-workflows`" in error for error in errors)


def test_target_fixture_rejects_legacy_namespace_in_canonical_proof_set():
    payload = json.loads(
        (REPO_ROOT / "docs/validation/saga-family-target-inventory.json").read_text(
            encoding="utf-8"
        )
    )
    payload = copy.deepcopy(payload)
    payload["required_namespace_proof"].append("team-execution:team-execution")
    errors: list[str] = []

    validate_target_fixture_payload(payload, REPO_ROOT / "fixture.json", errors)

    assert any(
        "namespace proof skills mismatch" in error
        and "team-execution:team-execution" in error
        for error in errors
    )


def test_target_fixture_rejects_legacy_root_in_canonical_state_set():
    payload = json.loads(
        (REPO_ROOT / "docs/validation/saga-family-target-inventory.json").read_text(
            encoding="utf-8"
        )
    )
    payload = copy.deepcopy(payload)
    payload["required_state_roots"].append(".codex/team-execution/")
    errors: list[str] = []

    validate_target_fixture_payload(payload, REPO_ROOT / "fixture.json", errors)

    assert any(
        "canonical state roots mismatch" in error and ".codex/team-execution/" in error
        for error in errors
    )


def test_legacy_team_execution_tree_remains_git_addressable_after_cutover():
    result = subprocess.run(
        ["git", "cat-file", "-e", "66b23ca83b6ce3b29871954c63a6554c39bfd72e^{tree}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert REQUIRED_LEGACY_STATE_ROOTS == {".codex/team-execution/"}


def test_verified_workflows_rejects_from_plugins_import_saga(tmp_path):
    make_verified_workflows_target(tmp_path, "bad.py", "from plugins import saga\n")
    errors: list[str] = []

    validate_verified_workflows_canonical_surface(tmp_path, errors)

    assert any("directly imports another workflow plugin" in error for error in errors)


def test_verified_workflows_role_profiles_are_part_of_repo_validation() -> None:
    errors: list[str] = []

    validate_verified_workflows_agents(REPO_ROOT, errors)

    assert errors == []


def test_verified_workflows_project_agents_bind_generated_runtime_names() -> None:
    errors: list[str] = []
    profiles = [
        {"profile_id": profile_id, "runtime_agent_name": profile_id}
        for profile_id in (
            "review_max",
            "review_high",
            "work_high",
            "test_medium",
            "scan_low",
            "monitor_low",
        )
    ]

    validate_verified_workflows_project_agents(
        REPO_ROOT,
        {"profiles": profiles},
        errors,
    )

    assert errors == []


def test_verified_workflows_project_agents_reject_stale_profile_bytes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / ".codex" / "agents", root / ".codex" / "agents")
    (root / "plugins" / "verified-workflows").mkdir(parents=True)
    shutil.copytree(
        REPO_ROOT / "plugins" / "verified-workflows" / "agents",
        root / "plugins" / "verified-workflows" / "agents",
    )
    project_profile = root / ".codex" / "agents" / "review_high.toml"
    project_profile.write_bytes(project_profile.read_bytes() + b"\n# stale\n")
    errors: list[str] = []

    validate_verified_workflows_project_agents(
        root,
        {
            "profiles": [
                {
                    "profile_id": "review_high",
                    "runtime_agent_name": "review_high",
                }
            ]
        },
        errors,
    )

    assert any("project runtime agent bytes drifted" in error for error in errors)


def test_verified_workflows_runtime_surfaces_are_part_of_repo_validation() -> None:
    errors: list[str] = []

    validate_verified_workflows_runtime(REPO_ROOT, errors)

    assert errors == []


def test_verified_workflows_runtime_rejects_missing_hook(tmp_path: Path) -> None:
    root = copy_verified_workflows_runtime_target(tmp_path)
    (root / "plugins" / "verified-workflows" / "hooks" / "hooks.json").unlink()
    errors: list[str] = []

    validate_verified_workflows_runtime(root, errors)

    assert any("runtime surfaces missing" in error for error in errors)


def test_verified_workflows_runtime_rejects_open_hook_definition(tmp_path: Path) -> None:
    root = copy_verified_workflows_runtime_target(tmp_path)
    hook_path = root / "plugins" / "verified-workflows" / "hooks" / "hooks.json"
    payload = json.loads(hook_path.read_text())
    payload["extra"] = True
    hook_path.write_text(json.dumps(payload))
    errors: list[str] = []

    validate_verified_workflows_runtime(root, errors)

    assert any("top-level fields" in error for error in errors)


def test_verified_workflows_runtime_rejects_stale_proof(tmp_path: Path) -> None:
    root = copy_verified_workflows_runtime_target(tmp_path)
    proof_path = root / "docs" / "validation" / "verified-workflows-runtime-proof.json"
    payload = json.loads(proof_path.read_text())
    payload["reason"] = "stale"
    proof_path.write_text(json.dumps(payload))
    errors: list[str] = []

    validate_verified_workflows_runtime(root, errors)

    assert any("tracked runtime proof is stale" in error for error in errors)


def test_verified_workflows_validation_pins_fleet_core_to_supplied_root(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FLEET_COMMONS_ROOT", "/tmp/not-the-supplied-repository")
    errors: list[str] = []

    validate_verified_workflows_agents(REPO_ROOT, errors)

    assert errors == []


def test_verified_workflows_role_profile_validation_rejects_missing_role(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "plugins").mkdir(parents=True)
    shutil.copytree(
        REPO_ROOT / "plugins" / "verified-workflows",
        root / "plugins" / "verified-workflows",
    )
    shutil.copytree(REPO_ROOT / "plugins" / "fleet-core", root / "plugins" / "fleet-core")
    (root / ".agents" / "plugins").mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / ".agents" / "plugins" / "marketplace.json",
        root / ".agents" / "plugins" / "marketplace.json",
    )
    (root / "docs" / "validation").mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / "docs" / "validation" / "codex-runtime-capability-snapshot.json",
        root / "docs" / "validation" / "codex-runtime-capability-snapshot.json",
    )
    (root / "plugins" / "verified-workflows" / "roles" / "security-reviewer.md").unlink()
    errors: list[str] = []

    validate_verified_workflows_agents(root, errors)

    assert any("roster mismatch" in error or "role lens" in error for error in errors)


def test_verified_workflows_allows_standard_library_import(tmp_path):
    make_verified_workflows_target(
        tmp_path,
        "good.py",
        'from json import loads\nLABEL = "saga"\n',
    )
    errors: list[str] = []

    validate_verified_workflows_canonical_surface(tmp_path, errors)

    assert errors == []


def test_verified_workflows_rejects_dynamic_saga_import(tmp_path):
    make_verified_workflows_target(
        tmp_path,
        "bad.py",
        'from importlib import import_module\n'
        'import_module("plugins." + "sa" + "ga" + ".scripts.saga")\n',
    )
    errors: list[str] = []

    validate_verified_workflows_canonical_surface(tmp_path, errors)

    assert any("dynamic imports are not allowed" in error for error in errors)


@pytest.mark.parametrize(
    "body",
    (
        'import builtins\nname = "json"\nbuiltins.__import__(name)\n',
        'from builtins import __import__ as load\nname = "json"\nload(name)\n',
        'name = "json"\nexec("import " + name)\n',
    ),
)
def test_verified_workflows_rejects_dynamic_import_aliases(tmp_path, body):
    make_verified_workflows_target(tmp_path, "bad.py", body)
    errors: list[str] = []

    validate_verified_workflows_canonical_surface(tmp_path, errors)

    assert any("dynamic imports are not allowed" in error for error in errors)


def test_verified_workflows_allows_importlib_metadata(tmp_path):
    make_verified_workflows_target(
        tmp_path,
        "good.py",
        "from importlib.metadata import version\n",
    )
    errors: list[str] = []

    validate_verified_workflows_canonical_surface(tmp_path, errors)

    assert errors == []


def test_verified_workflows_rejects_source_symlink(tmp_path):
    target = make_verified_workflows_target(tmp_path, "good.py", "from json import loads\n")
    saga = tmp_path / "plugins" / "saga"
    saga.mkdir()
    (target / "saga-link").symlink_to(saga, target_is_directory=True)
    errors: list[str] = []

    validate_verified_workflows_canonical_surface(tmp_path, errors)

    assert any("canonical target source must not contain symlinks" in error for error in errors)


def test_saga_rejects_verified_workflows_source_dependency(tmp_path):
    script = tmp_path / "plugins" / "saga" / "scripts" / "bad.py"
    script.parent.mkdir(parents=True)
    script.write_text(
        'TARGET = "plugins/" + "verified-" + "workflows/scripts/run.py"\n',
        encoding="utf-8",
    )
    errors: list[str] = []

    validate_saga_workflow_independence(tmp_path, errors)

    assert any("Saga must not import Verified Workflows source" in error for error in errors)


def test_saga_allows_unrelated_workflow_prose(tmp_path):
    script = tmp_path / "plugins" / "saga" / "scripts" / "good.py"
    script.parent.mkdir(parents=True)
    script.write_text('MESSAGE = "verified-workflows is not installed"\n', encoding="utf-8")
    errors: list[str] = []

    validate_saga_workflow_independence(tmp_path, errors)

    assert errors == []


def test_saga_rejects_source_symlink_to_verified_workflows(tmp_path):
    saga = tmp_path / "plugins" / "saga"
    target = tmp_path / "plugins" / "verified-workflows" / "owned.py"
    saga.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    target.write_text("VALUE = 1\n", encoding="utf-8")
    (saga / "linked.py").symlink_to(target)
    errors: list[str] = []

    validate_saga_workflow_independence(tmp_path, errors)

    assert any("Saga source must not contain symlinks" in error for error in errors)


def test_verified_workflows_rejects_upstream_byte_parity_claim(tmp_path):
    target = make_verified_workflows_target(tmp_path, "good.py", "from json import loads\n")
    (target / "PORTABILITY.md").write_text(
        "This is a behavior adaptation, not an upstream byte-parity claim.\n"
        "This package claims upstream byte parity.\n",
        encoding="utf-8",
    )
    errors: list[str] = []

    validate_verified_workflows_canonical_surface(tmp_path, errors)

    assert any("must not claim upstream byte parity" in error for error in errors)


def test_legacy_workflow_tokens_require_an_explicit_path_classification(tmp_path):
    unallowlisted = tmp_path / "plugins" / "saga" / "scripts" / "new_serializer.py"
    unallowlisted.parent.mkdir(parents=True)
    unallowlisted.write_text('MODE = "team-execution"\n', encoding="utf-8")
    historical = tmp_path / "docs" / "plans" / "old.md"
    historical.parent.mkdir(parents=True)
    historical.write_text("Historical team-execution plan.\n", encoding="utf-8")
    write_legacy_workflow_inventory(
        tmp_path,
        {"docs/plans/old.md": "historical-evidence"},
    )
    errors: list[str] = []

    validate_legacy_workflow_token_allowlist(
        tmp_path,
        errors,
        enforce_history_sentinels=False,
    )

    assert any(
        "legacy workflow token path inventory mismatch" in error
        and "plugins/saga/scripts/new_serializer.py" in error
        for error in errors
    )
    assert (
        expected_legacy_workflow_classification(
            Path("plugins/saga/scripts/new_serializer.py")
        )
        is None
    )


def test_active_capability_capture_has_no_legacy_workflow_tokens():
    assert (
        "scripts/capture_codex_runtime_capabilities.py"
        not in legacy_workflow_file_facts(REPO_ROOT)
    )


def test_nested_codex_directory_is_not_hidden_from_legacy_scan(tmp_path):
    writer = tmp_path / "plugins" / "other" / ".codex" / "writer.py"
    writer.parent.mkdir(parents=True)
    writer.write_text('MODE = "team-execution"\n', encoding="utf-8")

    facts = legacy_workflow_file_facts(tmp_path)

    assert "plugins/other/.codex/writer.py" in facts


def test_cutover_allowlist_rejects_pre_cutover_active_marketplace(tmp_path):
    marketplace = tmp_path / ".agents" / "plugins" / "marketplace.json"
    marketplace.parent.mkdir(parents=True)
    marketplace.write_text('{"plugins": [{"name": "team-execution"}]}\n', encoding="utf-8")
    write_legacy_workflow_inventory(
        tmp_path,
        {".agents/plugins/marketplace.json": "temporary-active-marketplace"},
    )
    staged_errors: list[str] = []
    cutover_errors: list[str] = []

    validate_legacy_workflow_token_allowlist(
        tmp_path,
        staged_errors,
        enforce_history_sentinels=False,
    )
    validate_legacy_workflow_token_allowlist(
        tmp_path,
        cutover_errors,
        mode="cutover",
        enforce_history_sentinels=False,
    )

    assert staged_errors == []
    assert any("cutover-active surface" in error for error in cutover_errors)


def test_legacy_inventory_rejects_changes_to_known_saga_writer(tmp_path):
    writer = tmp_path / "plugins" / "saga" / "scripts" / "outcome.py"
    writer.parent.mkdir(parents=True)
    writer.write_text('MODE = "team-execution"\n', encoding="utf-8")
    write_legacy_workflow_inventory(
        tmp_path,
        {"plugins/saga/scripts/outcome.py": "legacy-parser"},
    )
    clean: list[str] = []
    validate_legacy_workflow_token_allowlist(
        tmp_path,
        clean,
        enforce_history_sentinels=False,
    )
    assert clean == []

    writer.write_text('MODE = "team-execution"\nWRITES_STATE = True\n', encoding="utf-8")
    errors: list[str] = []
    validate_legacy_workflow_token_allowlist(
        tmp_path,
        errors,
        enforce_history_sentinels=False,
    )

    assert any("legacy workflow content digest drifted" in error for error in errors)


def test_legacy_inventory_rejects_global_replacement_of_historical_doc(tmp_path):
    history = tmp_path / "docs" / "plans" / "old.md"
    history.parent.mkdir(parents=True)
    history.write_text("Historical team-execution decision.\n", encoding="utf-8")
    write_legacy_workflow_inventory(
        tmp_path,
        {"docs/plans/old.md": "historical-evidence"},
    )
    clean: list[str] = []
    validate_legacy_workflow_token_allowlist(
        tmp_path,
        clean,
        enforce_history_sentinels=False,
    )
    assert clean == []

    history.write_text("Historical verified-workflows decision.\n", encoding="utf-8")
    errors: list[str] = []
    validate_legacy_workflow_token_allowlist(
        tmp_path,
        errors,
        enforce_history_sentinels=False,
    )

    assert any("legacy workflow token path inventory mismatch" in error for error in errors)


def test_frozen_history_sentinels_survive_inventory_refresh(tmp_path):
    for raw_path in LEGACY_WORKFLOW_HISTORY_SENTINELS:
        source = REPO_ROOT / raw_path
        target = tmp_path / raw_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    clean: list[str] = []
    validate_legacy_history_sentinels(tmp_path, clean)
    assert clean == []

    target = tmp_path / next(iter(LEGACY_WORKFLOW_HISTORY_SENTINELS))
    target.write_text(
        target.read_text(encoding="utf-8").replace("team-execution", "verified-workflows"),
        encoding="utf-8",
    )
    errors: list[str] = []
    validate_legacy_history_sentinels(tmp_path, errors)

    assert any("historical workflow sentinel digest drifted" in error for error in errors)
    assert any("missing tokens" in error for error in errors)


def test_cutover_repository_validation_runs_canonical_target_gate(monkeypatch):
    called: list[Path] = []

    def record(root: Path, errors: list[str]) -> None:
        called.append(root)

    monkeypatch.setattr(validator, "validate_verified_workflows_canonical_surface", record)

    validator.validate_repository(REPO_ROOT, mode="cutover")

    assert called == [REPO_ROOT]


def test_compare_inventory_reports_missing_and_unexpected_items():
    errors: list[str] = []

    compare_inventory({"sdlc-manager"}, {"saga", "mission-control"}, "target", errors)

    assert errors == [
        "target mismatch: missing=['mission-control', 'saga'] unexpected=['sdlc-manager']"
    ]


def test_script_reference_rejects_traversal(tmp_path):
    plugin_root = tmp_path / "plugins" / "example"
    skill_dir = plugin_root / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    source = skill_dir / "SKILL.md"
    source.write_text("---\nname: demo\ndescription: demo\n---\n", encoding="utf-8")
    errors: list[str] = []

    validate_relative_file(skill_dir, plugin_root, "../outside.py", source, errors)

    assert errors
    assert "must stay inside package" in errors[0]


def test_script_reference_requires_existing_file(tmp_path):
    plugin_root = tmp_path / "plugins" / "example"
    skill_dir = plugin_root / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    source = skill_dir / "SKILL.md"
    source.write_text("---\nname: demo\ndescription: demo\n---\n", encoding="utf-8")
    errors: list[str] = []

    validate_relative_file(skill_dir, plugin_root, "./scripts/missing.py", source, errors)

    assert errors
    assert "points to missing file" in errors[0]
