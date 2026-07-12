from __future__ import annotations

import hashlib
import json
import sys
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import external_action_policy as policy  # noqa: E402
import external_action_runtime as runtime  # noqa: E402
import external_action_store as store_module  # noqa: E402

_attestation = runtime.fleet_commons_shim.load("output_attestation")


def template() -> policy.ActionTemplate:
    return policy.ActionTemplate.from_mapping(
        {
            "action_id": "opinion-1",
            "intent": "second-opinion",
            "trigger": "review",
            "consumption_point": "before gate",
            "context_scope": ["docs/input.md"],
        }
    )


def preview(tmp_path: Path) -> runtime.Preview:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return runtime.prepare(
        repo_root=tmp_path,
        saga_id="task-runtime",
        run_id="run-1",
        template=template(),
        route={"stage": "work", "engine_id": "agy", "variant": "gemini"},
        cost_class="metered",
        route_egress={"policy": "networked", "host": "provider.example"},
        base_revision="a" * 40,
        payload={"prompt": "safe"},
        created_at="2026-07-12T00:00:00Z",
    )


def available(prepared: runtime.Preview, detail: dict | None = None) -> runtime.ExecutionOutcome:
    evidence = "fixture"
    route = dict(prepared.candidate_approval.route)
    receipt = runtime._receipt.emit_receipt(
        engine_id=str(route["engine_id"]),
        variant=str(route["variant"]),
        transport="cli",
        wall_time_s=0.0,
        bytes_produced=len(evidence.encode("utf-8")),
        runner={"pid": 1, "argv": ["fixture"], "exit_code": 0},
        receipt_emitter="agy-delegate",
        run_id="cli:fixture:1",
        invocation_sha256=runtime._receipt.digest_invocation({"fixture": True}),
        output_attestation=_attestation.emit_attestation(
            artifact="evidence", content=evidence
        ),
    )
    artifact = prepared.store.root / "evidence-fixture.json"
    artifact.write_text(
        json.dumps(
            {
                "schema": "external_action_evidence.v1",
                "action_id": prepared.request.action_id,
                "engine_id": route["engine_id"],
                "variant": route["variant"],
                "intent": prepared.request.intent,
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
    artifact_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
    return runtime.ExecutionOutcome(
        "available",
        str(artifact),
        detail or {"receipt_valid": True},
        validated=True,
        artifact_sha256=artifact_sha256,
    )


def test_prepare_approve_execute_adjudicate_consume(tmp_path: Path) -> None:
    prepared = preview(tmp_path)
    runtime.approve(prepared, operator="operator", approved_at="2026-07-12T00:01:00Z")

    def executor(request, approval, launch):
        launch()
        return available(prepared)

    outcome = runtime.execute(prepared.store, executor=executor, at="2026-07-12T00:02:00Z")
    assert outcome.status == "available"
    runtime.adjudicate(prepared.store, accepted=True, at="2026-07-12T00:03:00Z", detail={"verified": True})
    runtime.consume(prepared.store, at="2026-07-12T00:04:00Z", artifact_ref="docs/result.md")
    assert store_module.read_snapshot(prepared.store).state.value == "consumed"


def test_execute_requires_approval(tmp_path: Path) -> None:
    prepared = preview(tmp_path)
    with pytest.raises(runtime.RuntimeError, match="approved"):
        runtime.execute(prepared.store, executor=lambda *_: None, at="now")  # type: ignore[arg-type]


def test_no_launch_acknowledgement_is_unavailable(tmp_path: Path) -> None:
    prepared = preview(tmp_path)
    runtime.approve(prepared, operator="operator", approved_at="approved")
    outcome = runtime.execute(
        prepared.store,
        executor=lambda *_: runtime.ExecutionOutcome("available", "manifest://fake"),
        at="run",
    )
    assert outcome.status == "unavailable"


def test_launched_timeout_is_distinct(tmp_path: Path) -> None:
    prepared = preview(tmp_path)
    runtime.approve(prepared, operator="operator", approved_at="approved")

    def timeout(request, approval, launch):
        launch()
        raise TimeoutError

    assert runtime.execute(prepared.store, executor=timeout, at="run").status == "timed-out"


def test_interrupted_attempt_retries_with_fresh_identity(tmp_path: Path) -> None:
    prepared = preview(tmp_path)
    runtime.approve(prepared, operator="operator", approved_at="approved")

    def interrupted(_request, _approval, launch):
        launch()
        raise RuntimeError("process disconnected")

    assert runtime.execute(prepared.store, executor=interrupted, at="run").status == "invalid-evidence"
    retried = runtime.retry(
        prepared, repo_root=tmp_path, new_run_id="run-2", created_at="retry"
    )
    assert retried.request.attempt == 2
    assert retried.request.predecessor_request_sha256 == prepared.request.request_sha256
    assert retried.store.root != prepared.store.root
    with pytest.raises(runtime.RuntimeError, match="successor already exists"):
        runtime.retry(
            prepared, repo_root=tmp_path, new_run_id="run-3", created_at="retry-2"
        )


def test_launched_interruption_requires_termination_proof(tmp_path: Path) -> None:
    prepared = preview(tmp_path)
    runtime.approve(prepared, operator="operator", approved_at="approved")
    store_module.append_event(prepared.store, event_id="claim-1", event="claim", at="claim")
    store_module.append_event(prepared.store, event_id="launch-1", event="launch", at="launch")

    with pytest.raises(runtime.RuntimeError, match="termination proof"):
        runtime.interrupt(prepared.store, at="interrupt", rationale="lost coordinator")
    runtime.interrupt(
        prepared.store,
        at="interrupt",
        rationale="provider process group terminated",
        termination_proof={"terminated": True, "receipt_sha256": "a" * 64},
    )
    assert store_module.read_snapshot(prepared.store).state.value == "interrupted"


def test_unvalidated_available_evidence_is_rejected(tmp_path: Path) -> None:
    prepared = preview(tmp_path)
    runtime.approve(prepared, operator="operator", approved_at="approved")

    def spoofed(_request, _approval, launch):
        launch()
        return runtime.ExecutionOutcome("available", "arbitrary-ref")

    assert runtime.execute(prepared.store, executor=spoofed, at="run").status == "invalid-evidence"


def test_symbolic_head_is_resolved_before_approval(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "tracked.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    prepared = runtime.prepare(
        repo_root=tmp_path,
        saga_id="task-runtime-head",
        run_id="run-1",
        template=template(),
        route={"stage": "work", "engine_id": "agy", "variant": "gemini"},
        cost_class="metered",
        route_egress={},
        base_revision="HEAD",
        payload="safe",
        created_at="prepared",
    )
    assert prepared.candidate_approval.base_revision == subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_private_key_payload_is_blocked_before_store_creation(tmp_path: Path) -> None:
    with pytest.raises(runtime.RuntimeError, match="blocked"):
        runtime.prepare(
            repo_root=tmp_path,
            saga_id="task-runtime",
            run_id="run-1",
            template=template(),
            route={"stage": "work", "engine_id": "agy"},
            cost_class="metered",
            route_egress={"host": "provider"},
            base_revision="a" * 40,
            payload="-----BEGIN PRIVATE KEY-----\nabc",
            created_at="now",
        )
