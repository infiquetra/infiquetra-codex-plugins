from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "plugins" / "saga" / "scripts"
METRICS = ROOT / "plugins" / "saga" / "references" / "external-action-promotion-metrics.yaml"
sys.path.insert(0, str(SCRIPTS))

import external_action_lifecycle as lifecycle  # noqa: E402
import external_action_release_matrix as release_matrix  # noqa: E402
import external_action_runtime as runtime  # noqa: E402
import external_action_status as status  # noqa: E402
import external_action_store as store  # noqa: E402

R55_CASES = {
    "missing-credentials",
    "unavailable-provider",
    "timeout",
    "no-output",
    "invalid-receipt",
    "substituted-route",
    "secret-detection",
    "write-set-escape",
    "duplicate-resume",
    "operator-rejection",
}


def _preview(tmp_path: Path) -> Any:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    bundle = lifecycle.inspect_bundle("work", repo_root=tmp_path)
    action = bundle.actions[0]
    preview = lifecycle.prepare_bundle(
        bundle,
        repo_root=tmp_path,
        saga_id="task-release-matrix",
        run_id="run-1",
        routes={action.action_id: {"engine_id": "fixture", "variant": "artifact"}},
        payloads={action.action_id: "safe"},
        cost_classes={action.action_id: "free"},
        route_egress={},
        base_revision="a" * 40,
        created_at="prepared",
        selected_action_ids=[action.action_id],
    )[0]
    lifecycle.approve_bundle([preview], operator="operator", approved_at="approved")
    return preview


def _available(preview: Any) -> Any:
    def execute(_request: Any, _approval: Any, launch: Any) -> runtime.ExecutionOutcome:
        launch()
        artifact = preview.store.root / "evidence-fixture.json"
        artifact.write_text(json.dumps({"evidence": "fixture"}) + "\n", encoding="utf-8")
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        return runtime.ExecutionOutcome(
            "available",
            str(artifact),
            {"verified": True},
            validated=True,
            artifact_sha256=digest,
        )

    return execute


def test_promotion_metric_definitions_are_versioned_before_evidence() -> None:
    definitions = yaml.safe_load(METRICS.read_text(encoding="utf-8"))
    assert definitions["version"] == 1
    assert definitions["evidence_window"]["definition_version_frozen"] is True
    assert set(definitions) == {
        "version",
        "evidence_window",
        "qualifying_run",
        "major_rewrite",
        "provider_distribution",
        "integrity_failure",
        "containment_failure",
        "passing_rollback_drill",
    }
    assert "consumed" in " ".join(definitions["qualifying_run"]["required"])


def test_live_harness_is_fail_closed_without_attended_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert release_matrix.main([]) == 2
    assert "requires --attended" in capsys.readouterr().err


def test_release_assignments_cover_providers_stages_intents_and_requiredness() -> None:
    assignments = release_matrix.ASSIGNMENTS
    assert {item[0] for item in assignments} == {
        "ideate", "brainstorm", "plan", "work", "doc-review", "code-review"
    }
    assert {item[1] for item in assignments} == {"offload", "second-opinion"}
    assert {item[2].split("/", 1)[0] for item in assignments} == {
        "claude-cli", "agy", "ollama-cloud"
    }
    assert {item[3] for item in assignments} == {False, True}


def test_r55_matrix_is_closed_and_complete() -> None:
    assert R55_CASES == {
        "missing-credentials",
        "unavailable-provider",
        "timeout",
        "no-output",
        "invalid-receipt",
        "substituted-route",
        "secret-detection",
        "write-set-escape",
        "duplicate-resume",
        "operator-rejection",
    }


def test_operator_rejection_cannot_be_consumed(tmp_path: Path) -> None:
    preview = _preview(tmp_path)
    outcome = lifecycle.execute_bundle(
        [preview], executors={preview.request.action_id: _available(preview)}, at="executed"
    )
    assert outcome.outcomes[preview.request.action_id].status == "available"
    lifecycle.adjudicate_artifact(
        preview, accepted=False, at="rejected", detail={"rationale": "not useful"}
    )

    with pytest.raises(store.ActionStoreError, match="invalid from state"):
        lifecycle.consume(preview, at="consumed", artifact_ref="docs/should-not-exist.md")
    card = status.project(store.read_snapshot(preview.store))
    assert card["state"] == "rejected"
    assert card["adjudication"] == "reject"


def test_duplicate_resume_does_not_redispatch(tmp_path: Path) -> None:
    preview = _preview(tmp_path)
    calls = 0

    def counted(request: Any, approval: Any, launch: Any) -> runtime.ExecutionOutcome:
        nonlocal calls
        calls += 1
        return _available(preview)(request, approval, launch)

    lifecycle.execute_bundle(
        [preview], executors={preview.request.action_id: counted}, at="executed"
    )
    with pytest.raises(lifecycle.LifecycleError, match="approved before execution"):
        lifecycle.execute_bundle(
            [preview], executors={preview.request.action_id: counted}, at="resumed"
        )
    assert calls == 1


def test_proof_verifier_rejects_forged_content_hash() -> None:
    proof = {
        "schema_version": 1,
        "status": "passed",
        "providers": sorted({item[2] for item in release_matrix.ASSIGNMENTS}),
        "stages": [],
        "rollback_drill": {},
        "sanitization": {},
        "content_sha256": "0" * 64,
    }
    with pytest.raises(release_matrix.ReleaseMatrixError, match="content_sha256"):
        release_matrix.validate_proof(proof)


def test_rollback_drill_installs_reads_back_and_restores(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "plugins").mkdir(parents=True)
    source = ROOT / "plugins" / "saga"
    subprocess.run(["cp", "-R", str(source), str(repo / "plugins" / "saga")], check=True)

    proof = release_matrix._rollback_drill(repo, "a" * 40)

    assert proof["passed"] is True
    assert proof["candidate_installed"] is True
    assert proof["fresh_session_passed"] is True
    assert proof["restored"] is True
