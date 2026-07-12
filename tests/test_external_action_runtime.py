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
    artifact = prepared.store.root / "evidence-fixture.json"
    artifact.write_text(json.dumps({"evidence": "fixture"}) + "\n", encoding="utf-8")
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


def test_unvalidated_available_evidence_is_rejected(tmp_path: Path) -> None:
    prepared = preview(tmp_path)
    runtime.approve(prepared, operator="operator", approved_at="approved")

    def spoofed(_request, _approval, launch):
        launch()
        return runtime.ExecutionOutcome("available", "arbitrary-ref")

    assert runtime.execute(prepared.store, executor=spoofed, at="run").status == "invalid-evidence"


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
