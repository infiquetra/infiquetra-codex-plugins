from __future__ import annotations

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


def test_external_cli_write_request_fails_closed(tmp_path: Path) -> None:
    base = _repo(tmp_path)
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

    with pytest.raises(ValueError, match="external CLI writes are disabled"):
        adapters.executor_for_preview(preview, repo_root=tmp_path)
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "before\n"


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
