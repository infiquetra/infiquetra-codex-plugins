from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).parents[1] / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import external_action  # noqa: E402
import external_action_lifecycle as lifecycle  # noqa: E402
import external_action_runtime as runtime  # noqa: E402
import external_action_store as store  # noqa: E402
import reconcile  # noqa: E402

_receipt = runtime.fleet_commons_shim.load("bridge_receipt")
_attestation = runtime.fleet_commons_shim.load("output_attestation")


def _available(preview: runtime.Preview, detail: dict[str, Any]) -> runtime.ExecutionOutcome:
    evidence = "fixture"
    route = dict(preview.candidate_approval.route)
    receipt = _receipt.emit_receipt(
        engine_id=str(route["engine_id"]),
        variant=str(route["variant"]),
        transport="cli",
        wall_time_s=0.0,
        bytes_produced=len(evidence),
        runner={"pid": 1, "argv": ["fixture"], "exit_code": 0},
        receipt_emitter="agy-delegate",
        run_id="cli:fixture:1",
        invocation_sha256=_receipt.digest_invocation({"fixture": True}),
        output_attestation=_attestation.emit_attestation(artifact="evidence", content=evidence),
    )
    artifact = preview.store.root / "evidence-fixture.json"
    artifact.write_text(
        json.dumps(
            {
                "schema": "external_action_evidence.v1",
                "action_id": preview.request.action_id,
                "engine_id": route["engine_id"],
                "variant": route["variant"],
                "intent": preview.request.intent,
                "evidence": evidence,
                "findings": detail.get("findings", []),
                "evidence_digest": reconcile.evidence_digest(evidence),
                "runner_receipt": receipt,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    artifact_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
    return runtime.ExecutionOutcome(
        "available",
        str(artifact),
        detail,
        validated=True,
        artifact_sha256=artifact_sha256,
    )

STAGE_ACTIONS = (
    ("ideate", 0),
    ("ideate", 1),
    ("brainstorm", 0),
    ("brainstorm", 1),
    ("plan", 0),
    ("plan", 1),
    ("work", 0),
    ("work", 1),
    ("doc-review", 0),
    ("code-review", 0),
)


def test_bundle_cli_exposes_editable_plan_actions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert external_action.main(["bundle", "--stage", "plan", "--repo-root", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["stage"] == "plan"
    assert [item["action_id"] for item in payload["actions"]] == [
        "bounded-research",
        "architecture-opinion",
    ]


@pytest.mark.parametrize(("stage", "action_index"), STAGE_ACTIONS)
def test_each_stage_round_trips_through_shared_runtime(
    tmp_path: Path, stage: str, action_index: int
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    bundle = lifecycle.inspect_bundle(stage, repo_root=tmp_path)
    action = bundle.actions[action_index]
    previews = lifecycle.prepare_bundle(
        bundle,
        repo_root=tmp_path,
        saga_id=f"task-{stage}",
        run_id="run-1",
        routes={action.action_id: {"stage": stage, "engine_id": "fixture", "variant": "review"}},
        payloads={action.action_id: {"prompt": "safe fixture"}},
        cost_classes={action.action_id: "free"},
        route_egress={action.action_id: {"policy": "networked", "host": "fixture.example"}},
        base_revision="a" * 40,
        created_at="2026-07-12T00:00:00Z",
        selected_action_ids=[action.action_id],
    )
    approval_view = lifecycle.approval_preview_payload(previews)
    assert approval_view[0]["route"]["engine_id"] == "fixture"
    assert approval_view[0]["cost_class"] == "free"
    assert "approval_fingerprint" in approval_view[0]
    assert "status_card" in approval_view[0]
    lifecycle.approve_bundle(previews, operator="operator", approved_at="approved")

    def executor(_request: Any, _approval: Any, launch: Any) -> runtime.ExecutionOutcome:
        launch()
        return _available(
            previews[0],
            {
                "evidence": "typed fixture",
                "findings": [{"content": "fixture concern"}],
            },
        )

    result = lifecycle.execute_bundle(
        previews, executors={action.action_id: executor}, at="executed"
    )
    assert result.paused_action_id is None
    assert len(result.status_cards) == 1
    preview = previews[0]
    outcome = result.outcomes[action.action_id]
    if action.intent == "offload":
        lifecycle.adjudicate_artifact(
            preview, accepted=True, at="adjudicated", detail={"verified": True}
        )
    else:
        source_id = reconcile.parse_source_findings(
            [{"content": "fixture concern"}]
        )[0].source_finding_id
        lifecycle.adjudicate_opinion(
            preview,
            outcome,
            decisions={
                source_id: {"status": "reconciled", "rationale": "verified locally"}
            },
            reconciliation_id=f"reconcile-{stage}",
            adjudicator_id="codex/root",
            at="adjudicated",
        )
    lifecycle.consume(preview, at="consumed", artifact_ref=f"docs/{stage}.md")
    assert store.read_snapshot(preview.store).state.value == "consumed"


def test_bundle_validates_all_routes_before_partial_prepare(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    bundle = lifecycle.inspect_bundle("plan", repo_root=tmp_path)
    routes = {
        bundle.actions[0].action_id: {"engine_id": "fixture", "variant": "ok"},
        bundle.actions[1].action_id: {"halt": "provider unavailable"},
    }
    with pytest.raises(lifecycle.LifecycleError, match="before dispatch"):
        lifecycle.prepare_bundle(
            bundle,
            repo_root=tmp_path,
            saga_id="task-plan",
            run_id="run-1",
            routes=routes,
            payloads={item.action_id: "safe" for item in bundle.actions},
            cost_classes={item.action_id: "free" for item in bundle.actions},
            route_egress={},
            base_revision="a" * 40,
            created_at="now",
        )
    assert not (tmp_path / ".git" / "saga" / "external-actions").exists()


def test_required_failure_pauses_before_later_actions(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    actions = [
        {
            "action_id": "required-one",
            "intent": "offload",
            "trigger": "fixture",
            "requiredness": "required-before-continue",
            "consumption_point": "fixture",
        },
        {
            "action_id": "later",
            "intent": "offload",
            "trigger": "fixture",
            "requiredness": "best-effort",
            "consumption_point": "fixture",
        },
    ]
    bundle = lifecycle.inspect_bundle("work", repo_root=tmp_path, explicit_actions=actions)
    previews = lifecycle.prepare_bundle(
        bundle,
        repo_root=tmp_path,
        saga_id="task-work",
        run_id="run-1",
        routes={item.action_id: {"engine_id": "fixture", "variant": "x"} for item in bundle.actions},
        payloads={item.action_id: "safe" for item in bundle.actions},
        cost_classes={item.action_id: "free" for item in bundle.actions},
        route_egress={},
        base_revision="a" * 40,
        created_at="now",
    )
    lifecycle.approve_bundle(previews, operator="operator", approved_at="approved")

    def unavailable(_request: Any, _approval: Any, launch: Any) -> runtime.ExecutionOutcome:
        launch()
        return runtime.ExecutionOutcome("unavailable", detail={"reason": "fixture"})

    result = lifecycle.execute_bundle(
        previews,
        executors={item.action_id: unavailable for item in bundle.actions},
        at="executed",
    )
    assert result.paused_action_id == "required-one"
    assert "later" not in result.outcomes


def test_best_effort_failure_continues_to_later_actions(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    actions = [
        {
            "action_id": action_id,
            "intent": "offload",
            "trigger": "fixture",
            "requiredness": "best-effort",
            "consumption_point": "fixture",
        }
        for action_id in ("first", "later")
    ]
    bundle = lifecycle.inspect_bundle("work", repo_root=tmp_path, explicit_actions=actions)
    previews = lifecycle.prepare_bundle(
        bundle,
        repo_root=tmp_path,
        saga_id="task-best-effort",
        run_id="run-1",
        routes={item.action_id: {"engine_id": "fixture", "variant": "x"} for item in bundle.actions},
        payloads={item.action_id: "safe" for item in bundle.actions},
        cost_classes={item.action_id: "free" for item in bundle.actions},
        route_egress={},
        base_revision="a" * 40,
        created_at="now",
    )
    lifecycle.approve_bundle(previews, operator="operator", approved_at="approved")

    def unavailable(_request: Any, _approval: Any, launch: Any) -> runtime.ExecutionOutcome:
        launch()
        return runtime.ExecutionOutcome("unavailable", detail={"reason": "fixture"})

    result = lifecycle.execute_bundle(
        previews,
        executors={item.action_id: unavailable for item in bundle.actions},
        at="executed",
    )
    assert result.paused_action_id is None
    assert set(result.outcomes) == {"first", "later"}


def test_opinion_requires_decision_for_every_typed_finding(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    bundle = lifecycle.inspect_bundle("code-review", repo_root=tmp_path)
    action = bundle.actions[0]
    preview = lifecycle.prepare_bundle(
        bundle,
        repo_root=tmp_path,
        saga_id="task-review",
        run_id="run-1",
        routes={action.action_id: {"engine_id": "fixture", "variant": "review"}},
        payloads={action.action_id: "safe"},
        cost_classes={action.action_id: "free"},
        route_egress={},
        base_revision="a" * 40,
        created_at="now",
    )[0]
    lifecycle.approve_bundle([preview], operator="operator", approved_at="approved")

    def executor(_request: Any, _approval: Any, launch: Any) -> runtime.ExecutionOutcome:
        launch()
        return _available(preview, {"findings": [{"content": "x"}]})

    outcome = lifecycle.execute_bundle(
        [preview], executors={action.action_id: executor}, at="executed"
    ).outcomes[action.action_id]
    with pytest.raises(lifecycle.LifecycleError, match="every source finding"):
        lifecycle.adjudicate_opinion(
            preview,
            outcome,
            decisions={},
            reconciliation_id="reconcile-review",
            adjudicator_id="codex/root",
            at="adjudicated",
        )
