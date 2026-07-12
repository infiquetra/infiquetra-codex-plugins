from __future__ import annotations

import hashlib
import json
import shutil
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

_receipt = runtime.fleet_commons_shim.load("bridge_receipt")
_attestation = runtime.fleet_commons_shim.load("output_attestation")

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
                    "findings": [],
                    "evidence_digest": runtime.reconcile.evidence_digest(evidence),
                    "runner_receipt": receipt,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
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
    subprocess.run(
        ["cp", "-R", str(ROOT / "plugins" / "fleet-core"), str(repo / "plugins" / "fleet-core")],
        check=True,
    )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    proof = release_matrix._rollback_drill(repo, "a" * 40)

    assert proof["passed"] is True
    assert proof["candidate_installed"] is True
    assert proof["fresh_session_passed"] is True
    assert proof["restored"] is True
    assert len(proof["command_records"]) == 10
    release_matrix._validate_command_records(
        proof, repo_root=repo, source_head="a" * 40
    )
    evidence = repo / proof["command_records"][0]["record_ref"]
    evidence.write_text("{}\n", encoding="utf-8")
    with pytest.raises(release_matrix.ReleaseMatrixError, match="digest"):
        release_matrix._validate_command_records(
            proof, repo_root=repo, source_head="a" * 40
        )


def test_command_evidence_rejects_replayed_run_even_when_rehashed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "plugins").mkdir(parents=True)
    subprocess.run(["cp", "-R", str(ROOT / "plugins" / "saga"), str(repo / "plugins" / "saga")], check=True)
    subprocess.run(["cp", "-R", str(ROOT / "plugins" / "fleet-core"), str(repo / "plugins" / "fleet-core")], check=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    proof = release_matrix._rollback_drill(repo, "a" * 40)
    item = proof["command_records"][0]
    path = repo / item["record_ref"]
    record = json.loads(path.read_text(encoding="utf-8"))
    record["release_run_id"] = "replayed-run"
    unhashed = dict(record)
    unhashed.pop("content_sha256")
    record["content_sha256"] = release_matrix._sha256_json(unhashed)
    content = json.dumps(record, indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8")
    item["record_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    with pytest.raises(release_matrix.ReleaseMatrixError, match="binding"):
        release_matrix._validate_command_records(
            proof, repo_root=repo, source_head="a" * 40
        )


def test_copied_action_record_rejects_semantic_artifact_replacement(tmp_path: Path) -> None:
    preview = _preview(tmp_path)
    lifecycle.execute_bundle(
        [preview], executors={preview.request.action_id: _available(preview)}, at="executed"
    )
    lifecycle.adjudicate_artifact(preview, accepted=True, at="accepted", detail={})
    lifecycle.consume(preview, at="consumed", artifact_ref="release-matrix://fixture")
    snapshot = store.read_snapshot(preview.store)
    record_root = tmp_path / "docs" / "validation" / "external-action-evidence" / "run" / "actions" / "fixture"
    record_root.parent.mkdir(parents=True)
    shutil.copytree(preview.store.root, record_root)
    complete = next(event for event in snapshot.events if event["event"] == "complete")
    detail = dict(complete["detail"])
    projected = status.project(snapshot, evidence_root=record_root)
    approval = snapshot.approval
    assert approval is not None
    observed = {
        "action_id": snapshot.request.action_id,
        "stage": snapshot.request.stage,
        "intent": snapshot.request.intent,
        "requiredness": snapshot.request.requiredness.value,
        "engine_key": f"{approval.route['engine_id']}/{approval.route['variant']}",
        "adapter_class": None,
        "state": projected["state"],
        "receipt_validity": projected["receipt_validity"],
        "request_sha256": snapshot.request.request_sha256,
        "approval_fingerprint": approval.approval_fingerprint,
        "event_chain_tip": snapshot.events[-1]["this_hash"],
        "receipt_sha256": release_matrix._sha256_json(detail["runner_receipt"]),
        "evidence_sha256": detail["artifact_sha256"],
        "evidence_digest": detail["evidence_digest"],
        "finding_count": detail["finding_count"],
        "status_card_sha256": hashlib.sha256(status.render(projected).encode("utf-8")).hexdigest(),
        "action_record_sha256": release_matrix._directory_digest(record_root),
    }
    release_matrix._validate_action_record(observed, record_root, repo_root=tmp_path)
    artifact = record_root / "evidence-fixture.json"
    replaced = json.loads(artifact.read_text(encoding="utf-8"))
    replaced["evidence"] = "replacement"
    replaced["evidence_digest"] = runtime.reconcile.evidence_digest("replacement")
    artifact.write_text(json.dumps(replaced, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(release_matrix.ReleaseMatrixError, match="semantics"):
        release_matrix._validate_action_record(observed, record_root, repo_root=tmp_path)


def test_stage_artifact_bindings_come_from_runtime_complete_event(tmp_path: Path) -> None:
    preview = _preview(tmp_path)
    execution = lifecycle.execute_bundle(
        [preview], executors={preview.request.action_id: _available(preview)}, at="executed"
    )
    outcome = execution.outcomes[preview.request.action_id]
    snapshot = store.read_snapshot(preview.store)
    complete = next(event for event in snapshot.events if event["event"] == "complete")
    detail = dict(complete["detail"])
    bindings = release_matrix._complete_artifact_bindings(snapshot.events)
    assert "evidence_digest" not in dict(outcome.detail or {})
    assert bindings == {
        "evidence_sha256": detail["artifact_sha256"],
        "evidence_digest": detail["evidence_digest"],
        "finding_count": detail["finding_count"],
    }


def test_expected_ref_must_contain_exact_proof_blob(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    proof_path = tmp_path / "proof.json"
    proof = {"source_head": ""}
    proof_path.write_text(json.dumps(proof) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "proof.json"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "proof"], cwd=tmp_path, check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    proof["source_head"] = head
    proof_path.write_text(json.dumps(proof) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "proof.json"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "bind proof"], cwd=tmp_path, check=True)
    subprocess.run(["git", "tag", "evidence"], cwd=tmp_path, check=True)
    release_matrix._validate_expected_ref(
        proof,
        repo_root=tmp_path,
        expected_ref="evidence",
        proof_path=proof_path,
    )
    with pytest.raises(release_matrix.ReleaseMatrixError, match="different"):
        release_matrix._validate_expected_ref(
            {**proof, "changed": True},
            repo_root=tmp_path,
            expected_ref="evidence",
            proof_path=proof_path,
        )


def test_expected_ref_requires_all_referenced_bundle_files(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "seed").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=tmp_path, check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True).stdout.strip()
    bundle = tmp_path / "docs" / "validation" / "external-action-evidence" / "run" / "actions" / "fixture"
    bundle.mkdir(parents=True)
    artifact = bundle / "evidence.json"
    artifact.write_text("{}\n", encoding="utf-8")
    proof = {"source_head": head, "stages": [{"action_record_ref": bundle.relative_to(tmp_path).as_posix()}]}
    proof_path = tmp_path / "proof.json"
    proof_path.write_text(json.dumps(proof) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "proof.json", str(bundle.relative_to(tmp_path))], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "bundle"], cwd=tmp_path, check=True)
    subprocess.run(["git", "tag", "complete"], cwd=tmp_path, check=True)
    (bundle / ".lock").touch()
    release_matrix._validate_expected_ref(proof, repo_root=tmp_path, expected_ref="complete", proof_path=proof_path)
    subprocess.run(["git", "rm", "-q", str(artifact.relative_to(tmp_path))], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "remove bundle"], cwd=tmp_path, check=True)
    subprocess.run(["git", "tag", "incomplete"], cwd=tmp_path, check=True)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("{}\n", encoding="utf-8")
    with pytest.raises(release_matrix.ReleaseMatrixError, match="bundled evidence"):
        release_matrix._validate_expected_ref(proof, repo_root=tmp_path, expected_ref="incomplete", proof_path=proof_path)
