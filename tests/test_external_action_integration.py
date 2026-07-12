from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import external_action_adapters as adapters  # noqa: E402
import external_action_lifecycle as lifecycle  # noqa: E402
import external_action_status as status_module  # noqa: E402
import external_action_store as store  # noqa: E402
import reconcile  # noqa: E402


def _repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "input.txt").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "input.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)


def _fake_agy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output: str = '{"findings":[{"content":"external fixture concern"}]}',
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "agy"
    executable.write_text(
        "#!/bin/sh\ncat <<'SAGA_OUTPUT'\n" + output + "\nSAGA_OUTPUT\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")


@pytest.mark.parametrize("action_index", [0, 1], ids=["offload", "second-opinion"])
def test_real_lifecycle_uses_shipped_cli_adapter_dispatch_and_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    action_index: int,
) -> None:
    _repo(tmp_path)
    _fake_agy(tmp_path, monkeypatch)
    bundle = lifecycle.inspect_bundle("work", repo_root=tmp_path)
    action = bundle.actions[action_index]
    preview = lifecycle.prepare_bundle(
        bundle,
        repo_root=tmp_path,
        saga_id="task-integration",
        run_id=f"run-{action_index}",
        routes={
            action.action_id: {
                "engine_id": "agy",
                "variant": "gemini-fixture",
                "protocol": ["Return advisory evidence only."],
                "invocation": {
                    "via": "agy:delegate",
                    "recipe": "agy fixture",
                    "write_capable": False,
                    "model": "gemini-fixture",
                    "effort": "medium",
                },
            }
        },
        payloads={action.action_id: "review the fixture"},
        cost_classes={action.action_id: "free"},
        route_egress={action.action_id: {"policy": "networked", "host": "agy"}},
        base_revision="HEAD",
        created_at="prepared",
        selected_action_ids=[action.action_id],
    )[0]
    lifecycle.approve_bundle([preview], operator="operator", approved_at="approved")

    result = lifecycle.execute_bundle(
        [preview],
        executors={
            action.action_id: adapters.executor_for_preview(preview, repo_root=tmp_path)
        },
        at="executed",
    )

    outcome = result.outcomes[action.action_id]
    assert outcome.status == "available", outcome.detail
    assert outcome.evidence_ref is not None
    artifact_path = Path(outcome.evidence_ref)
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["schema"] == "external_action_evidence.v1"
    assert artifact["runner_receipt"]["receipt_emitter"] == "agy-delegate"
    assert artifact["runner_receipt"]["runner"]["argv"][0] == "agy"
    assert "--print-timeout" in artifact["runner_receipt"]["runner"]["argv"]
    assert "--add-dir" in artifact["runner_receipt"]["runner"]["argv"]
    log_index = artifact["runner_receipt"]["runner"]["argv"].index("--log-file")
    assert artifact["runner_receipt"]["runner"]["argv"][log_index + 1] == os.devnull
    assert artifact_path.stat().st_mode & 0o777 == 0o600
    assert list(preview.store.root.glob("evidence-*.json")) == [artifact_path]
    status = status_module.project(store.read_snapshot(preview.store))
    assert status["resolved_provider"] == "agy"
    assert status["resolved_model"] == "gemini-fixture"
    assert status["adapter_class"] == "agy:delegate"
    assert status["launch_acknowledged"] is True
    assert status["receipt_validity"] == "valid", status["receipt_errors"]
    assert status["observed_usage"] is None

    if action.intent == "offload":
        lifecycle.adjudicate_artifact(
            preview, accepted=True, at="adjudicated", detail={"verified": True}
        )
    else:
        finding = reconcile.parse_source_findings(outcome.detail["findings"])[0]
        lifecycle.adjudicate_opinion(
            preview,
            outcome,
            decisions={
                finding.source_finding_id: {
                    "status": "reconciled",
                    "rationale": "verified against fixture",
                }
            },
            reconciliation_id="reconcile-integration",
            adjudicator_id="codex/root",
            at="adjudicated",
        )
    lifecycle.consume(preview, at="consumed", artifact_ref="docs/result.md")
    consumed = status_module.project(store.read_snapshot(preview.store))
    assert consumed["state"] == "consumed"
    assert consumed["adjudication"] == "accept"
    assert consumed["consumed_artifact"] == "docs/result.md"


def test_executor_rejects_incomplete_route_before_launch(tmp_path: Path) -> None:
    _repo(tmp_path)
    bundle = lifecycle.inspect_bundle("work", repo_root=tmp_path)
    action = bundle.actions[0]
    preview = lifecycle.prepare_bundle(
        bundle,
        repo_root=tmp_path,
        saga_id="task-invalid-route",
        run_id="run-1",
        routes={action.action_id: {"engine_id": "agy", "variant": "fixture"}},
        payloads={action.action_id: "safe"},
        cost_classes={action.action_id: "free"},
        route_egress={},
        base_revision="HEAD",
        created_at="prepared",
        selected_action_ids=[action.action_id],
    )[0]
    lifecycle.approve_bundle([preview], operator="operator", approved_at="approved")

    with pytest.raises(ValueError, match="requires engine_id, variant, and invocation"):
        adapters.executor_for_preview(preview, repo_root=tmp_path)


def test_no_output_becomes_invalid_evidence_without_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    _fake_agy(tmp_path, monkeypatch, output="")
    bundle = lifecycle.inspect_bundle("work", repo_root=tmp_path)
    action = bundle.actions[0]
    preview = lifecycle.prepare_bundle(
        bundle,
        repo_root=tmp_path,
        saga_id="task-no-output",
        run_id="run-1",
        routes={
            action.action_id: {
                "engine_id": "agy",
                "variant": "gemini-fixture",
                "invocation": {
                    "via": "agy:delegate",
                    "recipe": "agy fixture",
                    "write_capable": False,
                    "model": "gemini-fixture",
                    "effort": "medium",
                },
            }
        },
        payloads={action.action_id: "review the fixture"},
        cost_classes={action.action_id: "free"},
        route_egress={},
        base_revision="HEAD",
        created_at="prepared",
        selected_action_ids=[action.action_id],
    )[0]
    lifecycle.approve_bundle([preview], operator="operator", approved_at="approved")

    outcome = lifecycle.execute_bundle(
        [preview],
        executors={
            action.action_id: adapters.executor_for_preview(preview, repo_root=tmp_path)
        },
        at="executed",
    ).outcomes[action.action_id]

    assert outcome.status == "invalid-evidence"
    assert store.read_snapshot(preview.store).state.value == "invalid-evidence"
    assert list(preview.store.root.glob("evidence-*.json")) == []
