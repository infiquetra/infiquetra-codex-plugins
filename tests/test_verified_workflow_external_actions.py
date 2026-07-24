from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SAGA_SCRIPTS = ROOT / "plugins" / "saga" / "scripts"
WORKFLOW_SCRIPTS = ROOT / "plugins" / "verified-workflows" / "scripts"
for path in (SAGA_SCRIPTS, WORKFLOW_SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import external_action_adapters as adapters  # noqa: E402
import external_action_lifecycle as lifecycle  # noqa: E402
import external_action_runtime as action_runtime  # noqa: E402
import external_action_status as status_module  # noqa: E402
import external_action_store as action_store  # noqa: E402
import run_record  # noqa: E402
import workflow_dispatch as dispatch  # noqa: E402


def _repo(path: Path) -> str:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "a.txt").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=path, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _fake_claude(path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = path / ".test-bin"
    bin_dir.mkdir()
    executable = bin_dir / "claude"
    executable.write_text(
        "#!/bin/sh\ncat >/dev/null\nprintf 'after\\n' > a.txt\nprintf 'bounded edit complete\\n'\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")


def test_approved_external_patch_is_imported_and_recorded_non_gating(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _repo(tmp_path)
    _fake_claude(tmp_path, monkeypatch)
    external = dispatch.ExternalAction(
        action_id="external-edit",
        purpose="edit the approved file",
        provider="claude-cli",
        model="opus",
        egress=("networked", "claude"),
        context=("a.txt",),
        sensitivity="internal",
        cost="metered",
        writes_or_artifact=("a.txt",),
        requiredness="required",
        authority="non-gating",
    )
    bundle = lifecycle.inspect_workflow_contract_actions(rows=[asdict(external)])
    preview = lifecycle.prepare_bundle(
        bundle,
        repo_root=tmp_path,
        saga_id="task-external-edit",
        run_id="run-1",
        routes={
            "external-edit": {
                "engine_id": "claude-cli",
                "variant": "opus",
                "protocol": ["Return evidence and a bounded patch only."],
                "invocation": {
                    "via": "claude:delegate",
                    "recipe": "contained fixture",
                    "write_capable": True,
                    "patch_capture": "bounded",
                    "shared_workspace_import": "root-only",
                    "model": "opus",
                    "effort": "high",
                },
            }
        },
        payloads={"external-edit": "edit a.txt"},
        cost_classes={"external-edit": "metered"},
        route_egress={"external-edit": {"policy": "networked", "host": "claude"}},
        base_revision=base,
        created_at="prepared",
    )[0]
    lifecycle.approve_bundle([preview], operator="operator", approved_at="approved")

    outcome = lifecycle.execute_bundle(
        [preview],
        executors={
            "external-edit": adapters.executor_for_preview(preview, repo_root=tmp_path)
        },
        at="executed",
    ).outcomes["external-edit"]
    imported = lifecycle.import_workspace_patch(preview, repo_root=tmp_path, at="imported")

    assert outcome.status == "available"
    receipt_argv = outcome.detail["runner_receipt"]["runner"]["argv"]
    assert "Read,Edit,Write,Glob,Grep" in receipt_argv
    assert receipt_argv[receipt_argv.index("--permission-mode") + 1] == "acceptEdits"
    assert imported.changed_paths == ("a.txt",)
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "after\n"
    projected = status_module.project(action_store.read_snapshot(preview.store))
    assert projected["authority"] == "non-gating"
    assert projected["root_import"] == "imported"
    assert projected["changed_paths"] == ["a.txt"]

    contract = dispatch.WorkflowContract(
        schema_version=1,
        plan_revision="plan-revision",
        contract_sha256="a" * 64,
        approval_binding_sha256="b" * 64,
        assignments=(),
        checks=(),
        external_actions=(external,),
        launch_specs=(),
    )
    record = run_record.new_run_record(
        repository_id="infiquetra/fixture",
        run_id="run-1",
        contract=contract,
    )
    record = run_record.record_external_action(
        record,
        action_id="external-edit",
        provider="claude-cli",
        model="opus",
        status=projected["state"],
        approval_fingerprint=projected["approval_fingerprint"],
        artifact_sha256=outcome.artifact_sha256,
        patch_sha256=projected["patch_sha256"],
        changed_paths=projected["changed_paths"],
        root_disposition=projected["root_import"],
    )
    assert record["external_actions"][0]["authority"] == "non-gating"
    assert record["root_decision"] is None


def test_caller_cannot_promote_response_only_registry_route(tmp_path: Path) -> None:
    _repo(tmp_path)
    external = dispatch.ExternalAction(
        "external-edit",
        "edit the approved file",
        "agy",
        "Gemini 3.5 Flash (High)",
        ("networked",),
        ("a.txt",),
        "internal",
        "metered",
        ("a.txt",),
        "required",
        "non-gating",
    )
    bundle = lifecycle.inspect_workflow_contract_actions(rows=[asdict(external)])
    preview = lifecycle.prepare_bundle(
        bundle,
        repo_root=tmp_path,
        saga_id="task-false-write",
        run_id="run-1",
        routes={
            "external-edit": {
                "engine_id": "agy",
                "variant": "gemini-3.5-flash-high",
                "invocation": {
                    "write_capable": True,
                    "patch_capture": "bounded",
                    "shared_workspace_import": "root-only",
                    "model": "Gemini 3.5 Flash (High)",
                },
            }
        },
        payloads={"external-edit": "edit a.txt"},
        cost_classes={"external-edit": "metered"},
        route_egress={"external-edit": {"policy": "networked"}},
        base_revision="HEAD",
        created_at="prepared",
    )[0]
    lifecycle.approve_bundle([preview], operator="operator", approved_at="approved")

    with pytest.raises(ValueError, match="differs from the canonical registry"):
        adapters.executor_for_preview(preview, repo_root=tmp_path)


def test_workflow_route_cannot_widen_external_egress(tmp_path: Path) -> None:
    _repo(tmp_path)
    external = dispatch.ExternalAction(
        "external-opinion",
        "review one file",
        "agy",
        "Gemini 3.5 Flash (High)",
        ("networked", "approved.example"),
        ("a.txt",),
        "internal",
        "metered",
        ("artifact:review",),
        "best-effort",
        "non-gating",
    )
    bundle = lifecycle.inspect_workflow_contract_actions(rows=[asdict(external)])

    with pytest.raises(action_runtime.RuntimeError, match="egress widens"):
        lifecycle.prepare_bundle(
            bundle,
            repo_root=tmp_path,
            saga_id="task-egress",
            run_id="run-1",
            routes={
                "external-opinion": {
                    "engine_id": "agy",
                    "variant": "gemini-3.5-flash-high",
                    "invocation": {
                        "write_capable": False,
                        "model": "Gemini 3.5 Flash (High)",
                    },
                }
            },
            payloads={"external-opinion": "review a.txt"},
            cost_classes={"external-opinion": "metered"},
            route_egress={
                "external-opinion": {"policy": "networked", "host": "widened.example"}
            },
            base_revision="HEAD",
            created_at="prepared",
        )
