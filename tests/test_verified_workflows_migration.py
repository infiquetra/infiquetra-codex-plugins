from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

from scripts import build_legacy_workflow_inventory, materialize_verified_workflows
from scripts.validate_codex_plugins import (
    WORKFLOW_COMPAT,
    validate_repository,
    validate_saga_workflow_independence,
    validate_verified_workflows_canonical_surface,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = ROOT / "plugins" / "verified-workflows"
FIXTURE = ROOT / "docs" / "validation" / "saga-family-target-inventory.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
PORT_MANIFEST = ROOT / "docs" / "portability" / "ports" / "2026-07-10-saga-07517.json"
LEGACY_TOKEN_INVENTORY = (
    ROOT / "docs" / "validation" / "verified-workflows-legacy-token-inventory.json"
)


def _load_shim(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(
        item for item in path.rglob("*") if item.is_file() and "__pycache__" not in item.parts
    ):
        content = child.read_bytes()
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def test_current_marketplace_and_target_fixture_expose_exactly_one_workflow_identity_each() -> None:
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    active = {entry["name"] for entry in marketplace["plugins"]}
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    targets = {entry["name"]: entry for entry in fixture["plugins"]}

    assert active & {"team-execution", "verified-workflows"} == {"verified-workflows"}
    assert set(targets) & {"team-execution", "verified-workflows"} == {
        "verified-workflows"
    }
    target = targets["verified-workflows"]
    assert target["version"] == "1.0.1+codex.20260717220000"
    assert target["publication_status"] == "released"
    assert set(target["skills"]) == {"run", "appsec-audit", "select-agent"}
    assert fixture["unpublished_plugins"] == []
    assert fixture["legacy_readable_plugins"] == ["team-execution"]


def test_retired_source_is_absent_but_frozen_tree_remains_git_addressable() -> None:
    assert not (ROOT / "plugins" / "team-execution").exists()
    result = subprocess.run(
        ["git", "cat-file", "-e", "66b23ca83b6ce3b29871954c63a6554c39bfd72e^{tree}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


def test_legacy_token_inventory_is_exact_digest_bound_and_current() -> None:
    expected = build_legacy_workflow_inventory.dumps(
        build_legacy_workflow_inventory.build_inventory(ROOT)
    )
    assert LEGACY_TOKEN_INVENTORY.read_text(encoding="utf-8") == expected
    payload = json.loads(expected)
    entries = {entry["path"]: entry for entry in payload["entries"]}
    assert entries["plugins/saga/scripts/outcome.py"]["classification"] == "legacy-parser"
    assert entries[
        "docs/plans/2026-06-30-team-execution-saga-orchestration-repair-plan.md"
    ]["classification"] == "historical-evidence"
    for title_only_history in (
        "docs/reviews/2026-07-10-codex-plugin-model-execution-modernization-plan-doc-review-r2.md",
        "docs/reviews/2026-07-10-codex-plugin-model-execution-modernization-plan-doc-review.md",
        "docs/work-sessions/2026-07-01-discord-visual-identity-publisher-work.md",
        "docs/work-sessions/2026-07-10-codex-plugin-model-execution-modernization.md",
    ):
        assert entries[title_only_history]["classification"] == "historical-evidence"
        assert "Team Execution" in entries[title_only_history]["tokens"]
    assert entries["docs/engineering-journal/QUEUED.md"]["classification"] == (
        "mutable-engineering-journal"
    )
    assert sum(
        entry["classification"] == "historical-evidence" for entry in entries.values()
    ) == 46
    assert all(len(entry["sha256"]) == 64 for entry in entries.values())


def test_target_manifest_skills_and_u4_runtime_surfaces_are_complete() -> None:
    manifest = json.loads(
        (TARGET_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )

    assert manifest["name"] == "verified-workflows"
    assert manifest["version"] == "1.0.1+codex.20260717220000"
    assert manifest["author"]["name"] == "Infiquetra"
    assert manifest["skills"] == "./skills/"
    assert set(path.name for path in (TARGET_ROOT / "skills").iterdir() if path.is_dir()) == {
        "run",
        "appsec-audit",
        "select-agent",
    }
    for skill in ("run", "appsec-audit", "select-agent"):
        body = (TARGET_ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert f"name: {skill}" in body
        assert "TODO" not in body
    target_appsec = TARGET_ROOT / "skills" / "appsec-audit" / "SKILL.md"
    appsec_contract = target_appsec.read_text(encoding="utf-8")
    legacy_contract = subprocess.run(
        [
            "git",
            "show",
            "66b23ca83b6ce3b29871954c63a6554c39bfd72e:skills/appsec-audit/SKILL.md",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    target_body = appsec_contract.split("\n---\n", 1)[1]
    legacy_body = legacy_contract.split("\n---\n", 1)[1]
    assert target_body == legacy_body
    assert "when_to_use:" not in appsec_contract
    for trigger in (
        "accepts URLs",
        "fetches remote resources",
        "follows redirects",
        "parses user-controlled input",
        "network egress controls",
    ):
        assert trigger in appsec_contract.split("\n---\n", 1)[0]
    for marker in (
        "follows redirects",
        "user-controlled input",
        "SSRF Checklist",
        "metadata endpoints",
        "allowlists",
        "## Finding Format",
        "**Severity**",
        "**Evidence**",
        "**Impact**",
        "**Fix**",
        "**Validation**",
    ):
        assert marker in appsec_contract
    hooks = json.loads((TARGET_ROOT / "hooks" / "hooks.json").read_text())
    assert set(hooks["hooks"]) == {"SubagentStart", "SubagentStop"}
    assert (TARGET_ROOT / "hooks" / "agent_receipt.py").is_file()
    assert {
        "dispatch_receipt.py",
        "gate_evaluator.py",
        "named_child_attestation.py",
        "protocol_probe.py",
        "protected_store.py",
        "raw_hook_maintenance.py",
        "workflow_records.py",
        "workflow_dispatch.py",
        "workspace_evidence.py",
    } <= {path.name for path in (TARGET_ROOT / "scripts").glob("*.py")}
    assert {path.name for path in (TARGET_ROOT / "agents").glob("*.toml")} == {
        "review_max.toml",
        "review_high.toml",
        "test_medium.toml",
        "scan_low.toml",
        "monitor_low.toml",
    }
    assert (TARGET_ROOT / "config" / "role-registry.yaml").is_file()
    assert len(list((TARGET_ROOT / "roles").glob("*.md"))) == 25


def test_frozen_team_execution_rows_have_explicit_verified_workflows_targets() -> None:
    manifest = json.loads(PORT_MANIFEST.read_text(encoding="utf-8"))
    rows = [
        row
        for row in manifest["source"]["rows"]
        if (row.get("new_path") or row.get("old_path") or "").startswith(
            "plugins/team-execution/"
        )
    ]

    assert len(rows) == 10
    assert all(row["planned_targets"] for row in rows)
    assert all(
        all(target.startswith("plugins/verified-workflows/") for target in row["planned_targets"])
        for row in rows
    )
    identity = next(row for row in rows if row["row_id"] == "src-c75fe471946e3b4e")
    assert identity["units"] == ["U9"]
    assert identity["planned_targets"] == [
        "plugins/verified-workflows/.codex-plugin/plugin.json"
    ]


def test_target_operational_surfaces_emit_no_legacy_vocabulary_or_cross_plugin_imports() -> None:
    lineage_docs = {"README.md", "PORTABILITY.md", "CHANGELOG.md"}
    legacy_tokens = {
        value for entry in WORKFLOW_COMPAT.REGISTRY.values() for value in entry.legacy
    }
    for path in TARGET_ROOT.rglob("*"):
        if (
            not path.is_file()
            or path.name in lineage_docs
            or path.name == "fleet_commons_shim.py"
            or "__pycache__" in path.parts
            or "frozen-source" in path.parts
        ):
            continue
        text = path.read_text(encoding="utf-8")
        found = sorted(token for token in legacy_tokens if token in text)
        assert not found, f"{path}: {found}"
        if path.suffix == ".py":
            assert "plugins/team-execution" not in text
            assert "plugins/saga" not in text
            assert "team_execution" not in text


def test_saga_and_verified_workflows_load_shared_compat_without_cross_plugin_dependency(
    tmp_path,
    monkeypatch,
) -> None:
    layouts = {}
    for plugin in ("saga", "verified-workflows"):
        layout = tmp_path / plugin
        fleet_root = layout / "plugins" / "fleet-core"
        plugin_root = layout / "plugins" / plugin
        shutil.copytree(ROOT / "plugins" / "fleet-core", fleet_root)
        shutil.copytree(ROOT / "plugins" / plugin, plugin_root)
        layouts[plugin] = (fleet_root, plugin_root)
        assert not (layout / "plugins" / "team-execution").exists()
        sibling = "verified-workflows" if plugin == "saga" else "saga"
        assert not (layout / "plugins" / sibling).exists()

    saga_fleet, saga_root = layouts["saga"]
    monkeypatch.setenv("FLEET_COMMONS_ROOT", str(saga_fleet))
    saga_shim = _load_shim(saga_root / "scripts" / "fleet_commons_shim.py", "u9_saga_shim")
    assert saga_shim.load("workflow_compat").emit("plugin.id") == "verified-workflows"
    saga_errors: list[str] = []
    validate_saga_workflow_independence(saga_root.parents[1], saga_errors)
    assert saga_errors == []

    workflow_fleet, workflow_root = layouts["verified-workflows"]
    monkeypatch.setenv("FLEET_COMMONS_ROOT", str(workflow_fleet))
    workflow_shim = _load_shim(
        workflow_root / "scripts" / "fleet_commons_shim.py",
        "u9_verified_workflows_shim",
    )
    assert workflow_shim.load("workflow_compat").emit("plugin.id") == "verified-workflows"
    workflow_errors: list[str] = []
    validate_verified_workflows_canonical_surface(
        workflow_root.parents[1],
        workflow_errors,
    )
    assert workflow_errors == []


def test_source_materialization_can_run_twice_without_byte_drift(tmp_path) -> None:
    staged = tmp_path / "verified-workflows"

    first = materialize_verified_workflows.materialize(TARGET_ROOT, staged)
    second = materialize_verified_workflows.materialize(TARGET_ROOT, staged)

    assert first["created"] == first["file_count"]
    assert first["unchanged"] == 0
    assert second["created"] == 0
    assert second["unchanged"] == second["file_count"]
    assert first["tree_sha256"] == second["tree_sha256"]
    assert first["installed_or_profile_mutated"] is False
    assert _source_digest(staged) == _source_digest(TARGET_ROOT)

    manifest = staged / ".codex-plugin" / "plugin.json"
    manifest.write_text("{}\n", encoding="utf-8")
    with pytest.raises(materialize_verified_workflows.MaterializationError, match="drifted"):
        materialize_verified_workflows.materialize(TARGET_ROOT, staged)


def test_source_materialization_refuses_codex_home(tmp_path, monkeypatch) -> None:
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    with pytest.raises(materialize_verified_workflows.MaterializationError, match="CODEX_HOME"):
        materialize_verified_workflows.materialize(TARGET_ROOT, codex_home / "plugins" / "target")


def test_source_materialization_refuses_destination_symlink(tmp_path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "linked-parent"
    link.symlink_to(real, target_is_directory=True)

    with pytest.raises(
        materialize_verified_workflows.MaterializationError,
        match="destination must not be a symlink",
    ):
        materialize_verified_workflows.materialize(TARGET_ROOT, link)

    assert list(real.iterdir()) == []
    result = materialize_verified_workflows.materialize(TARGET_ROOT, link / "stage")
    assert result["created"] == result["file_count"]
    assert (real / "stage" / ".codex-plugin" / "plugin.json").is_file()


def test_source_materialization_refuses_maintained_repo_destination(
    tmp_path,
    monkeypatch,
) -> None:
    maintained_repo = tmp_path / "maintained-repo"
    maintained_repo.mkdir()
    monkeypatch.setattr(materialize_verified_workflows, "REPO_ROOT", maintained_repo)
    destination = maintained_repo / "plugins" / "verified-workflows-copy"

    with pytest.raises(
        materialize_verified_workflows.MaterializationError,
        match="maintained repository",
    ):
        materialize_verified_workflows.materialize(TARGET_ROOT, destination)

    assert not destination.exists()


def test_source_materialization_rejects_special_destination_file(tmp_path) -> None:
    staged = tmp_path / "stage"
    staged.mkdir()
    os.mkfifo(staged / "pipe")

    with pytest.raises(
        materialize_verified_workflows.MaterializationError,
        match="unmanaged paths",
    ):
        materialize_verified_workflows.materialize(TARGET_ROOT, staged)


def test_source_materialization_rejects_nondirectory_destination_root(tmp_path) -> None:
    regular = tmp_path / "regular"
    regular.write_text("occupied\n", encoding="utf-8")
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)

    for destination in (regular, fifo):
        with pytest.raises(
            materialize_verified_workflows.MaterializationError,
            match="destination must be a directory",
        ):
            materialize_verified_workflows.materialize(TARGET_ROOT, destination)


def test_read_only_validation_is_idempotent_and_does_not_mutate_source() -> None:
    before = _source_digest(TARGET_ROOT)
    historical_before = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()

    assert validate_repository(ROOT, mode="current") == []
    assert validate_repository(ROOT, mode="target-fixture") == []
    assert validate_repository(ROOT, mode="current") == []

    assert _source_digest(TARGET_ROOT) == before
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == historical_before
