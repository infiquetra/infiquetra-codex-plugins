"""U5 append-only outcome dispatch migration contract."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/saga/scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"u5_{name}", SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


OUTCOME = load("outcome")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    common = tmp_path / ".git"
    common.mkdir()
    monkeypatch.setattr(
        OUTCOME.outcome_store.subprocess,
        "run",
        lambda *_a, **_kw: SimpleNamespace(returncode=0, stdout=f"{common}\n", stderr=""),
    )
    return tmp_path


def runtime_ack(req: Any, *, kind: str = "launched") -> dict[str, str]:
    leaf = f"real-{req.outcome_id}-{req.subplot_id}" if kind == "launched" else ""
    ref = (
        _launch_receipt(
            req.repo_root,
            outcome_id=req.outcome_id,
            subplot_id=req.subplot_id,
            backend=req.backend,
            leaf_saga_id=leaf,
        )
        if kind == "launched"
        else f"operator:run-{req.outcome_id}"
    )
    return {
        "ack_kind": kind,
        "dispatch_ack_ref": ref,
        "leaf_saga_id": leaf,
        "producer_kind": "verified-workflow",
        "run_identity": f"run-{req.outcome_id}",
        "dispatch_intent_id": req.dispatch_intent_id,
        "outcome_id": req.outcome_id,
        "subplot_id": req.subplot_id,
        "backend": req.backend,
    }


def test_launch_ack_is_required_for_dispatched_state(repo: Path) -> None:
    OUTCOME.start(repo, "u5", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    pending = OUTCOME.advance(repo, "u5", dispatcher=lambda _req: "leaf-u5-leaf")
    assert pending.dispatched == []
    assert pending.status["states"]["leaf"] == "legacy-unverified"
    with pytest.raises(OUTCOME.OutcomeError, match="not dispatched"):
        OUTCOME.attend(repo, "u5", "leaf")

    OUTCOME.start(repo, "u5b", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    launched = OUTCOME.advance(repo, "u5b", dispatcher=runtime_ack)
    assert launched.dispatched == ["leaf"]
    assert launched.status["states"]["leaf"] == "dispatched"


@pytest.mark.parametrize("mutation", ["digest", "stale", "leaf", "run"])
def test_live_dispatch_rejects_unverified_launch_receipts(repo: Path, mutation: str) -> None:
    outcome_id = f"live-{mutation}"
    OUTCOME.start(repo, outcome_id, "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])

    request: dict[str, Any] = {}

    def forged(req: Any) -> dict[str, str]:
        request["value"] = req
        acknowledgement = runtime_ack(req)
        if mutation == "digest":
            acknowledgement["dispatch_ack_ref"] = (
                f"{acknowledgement['dispatch_ack_ref'].rsplit('=', 1)[0]}={'0' * 64}"
            )
        elif mutation == "stale":
            acknowledgement["dispatch_ack_ref"] = _launch_receipt(
                repo,
                outcome_id="previous-run",
                subplot_id=req.subplot_id,
                backend=req.backend,
                leaf_saga_id=acknowledgement["leaf_saga_id"],
            )
        elif mutation == "leaf":
            acknowledgement["leaf_saga_id"] = "forged-leaf"
        else:
            acknowledgement["run_identity"] = "run-forged"
        return acknowledgement

    rejected = OUTCOME.advance(repo, outcome_id, dispatcher=forged)
    assert rejected.dispatched == []
    assert (
        rejected.halted[0]["reason"].startswith("invalid dispatch launch receipt")
        or rejected.halted[0]["reason"]
        == "dispatch acknowledgement conflicts with its launch receipt"
    )
    assert rejected.status["states"]["leaf"] == "intent-created"

    retried = OUTCOME.advance(
        repo,
        outcome_id,
        dispatcher=lambda _req: pytest.fail("unacknowledged intent must not relaunch"),
    )
    assert retried.dispatched == []
    assert "already exists" in retried.halted[0]["reason"]

    valid = runtime_ack(request["value"])
    OUTCOME.reconcile_dispatch_ack(
        OUTCOME._store(repo, outcome_id),
        repo_root=repo,
        outcome_id=outcome_id,
        subplot_id="leaf",
        ack_kind="launched",
        dispatch_ack_ref=valid["dispatch_ack_ref"],
        leaf_saga_id=valid["leaf_saga_id"],
    )
    assert OUTCOME.status(repo, outcome_id)["states"]["leaf"] == "dispatched"


def test_manual_ack_settles_without_liveness(repo: Path) -> None:
    OUTCOME.start(repo, "u5c", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    result = OUTCOME.advance(
        repo, "u5c", dispatcher=lambda req: runtime_ack(req, kind="handed-off")
    )
    assert result.dispatched == []
    assert OUTCOME.status(repo, "u5c")["states"]["leaf"] == "handed-off"
    assert OUTCOME.outcome_store.replay_pending(OUTCOME._store(repo, "u5c")) == []


def _launch_receipt(
    repo: Path,
    *,
    outcome_id: str,
    subplot_id: str,
    backend: str,
    leaf_saga_id: str,
) -> str:
    path = repo / ".codex/verified-workflows/dispatch-receipts/launch.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "saga.outcome-dispatch-launch.v1",
        "producer_kind": "verified-workflow",
        "run_identity": f"run-{outcome_id}",
        "outcome_id": outcome_id,
        "subplot_id": subplot_id,
        "backend": backend,
        "dispatch_intent_id": f"dispatch-intent:{outcome_id}:{subplot_id}",
        "leaf_saga_id": leaf_saga_id,
    }
    content = (json.dumps(payload, sort_keys=True) + "\n").encode()
    path.write_bytes(content)
    return f"{path.relative_to(repo).as_posix()}#sha256={hashlib.sha256(content).hexdigest()}"


def test_legacy_commit_reconciles_append_only_with_digest_bound_launch(repo: Path) -> None:
    OUTCOME.start(repo, "legacy", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    OUTCOME.advance(repo, "legacy", dispatcher=lambda _req: "synthetic-leaf")
    store = OUTCOME._store(repo, "legacy")
    before = list(OUTCOME.outcome_store.read_ledger(store))
    ref = _launch_receipt(
        repo,
        outcome_id="legacy",
        subplot_id="leaf",
        backend="inline",
        leaf_saga_id="real-leaf",
    )
    record = OUTCOME.reconcile_dispatch_ack(
        store,
        repo_root=repo,
        outcome_id="legacy",
        subplot_id="leaf",
        ack_kind="launched",
        dispatch_ack_ref=ref,
        leaf_saga_id="real-leaf",
    )
    after = OUTCOME.outcome_store.read_ledger(store)
    assert after[: len(before)] == before
    assert record["receipt_sha256"] == ref.rsplit("=", 1)[1]
    assert OUTCOME.status(repo, "legacy")["states"]["leaf"] == "dispatched"
    assert OUTCOME.outcome_store.replay_pending(store) == []


@pytest.mark.parametrize("mutation", ["digest", "leaf", "path"])
def test_launch_reconciliation_rejects_forged_or_escaping_receipt(
    repo: Path, mutation: str
) -> None:
    OUTCOME.start(repo, "forged", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    OUTCOME.advance(repo, "forged", dispatcher=lambda _req: "synthetic-leaf")
    ref = _launch_receipt(
        repo,
        outcome_id="forged",
        subplot_id="leaf",
        backend="inline",
        leaf_saga_id="real-leaf",
    )
    leaf = "real-leaf"
    if mutation == "digest":
        ref = f"{ref.rsplit('=', 1)[0]}={'0' * 64}"
    elif mutation == "leaf":
        leaf = "wrong-leaf"
    else:
        ref = f"../launch.json#sha256={'0' * 64}"
    with pytest.raises(OUTCOME.OutcomeError):
        OUTCOME.reconcile_dispatch_ack(
            OUTCOME._store(repo, "forged"),
            repo_root=repo,
            outcome_id="forged",
            subplot_id="leaf",
            ack_kind="launched",
            dispatch_ack_ref=ref,
            leaf_saga_id=leaf,
        )


def test_concurrent_manual_reconciliation_appends_one_ack(repo: Path) -> None:
    OUTCOME.start(repo, "race", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    store = OUTCOME._store(repo, "race")
    OUTCOME.outcome_store.append_ledger(
        store,
        {
            "phase": "intent",
            "kind": "outcome.dispatch.v2",
            "key": "dispatch-intent:race:leaf",
            "dispatch_intent_id": "dispatch-intent:race:leaf",
            "subplot_id": "leaf",
            "backend": "manual",
        },
    )

    def reconcile(index: int) -> str:
        try:
            OUTCOME.reconcile_dispatch_ack(
                store,
                repo_root=repo,
                outcome_id="race",
                subplot_id="leaf",
                ack_kind="handed-off",
                dispatch_ack_ref=f"operator:race-{index}",
            )
            return "appended"
        except OUTCOME.OutcomeError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(reconcile, (1, 2))) == ["appended", "duplicate"]
    acknowledgements = [
        record
        for record in OUTCOME.outcome_store.read_ledger(store)
        if record.get("phase") == "ack"
    ]
    assert len(acknowledgements) == 1


def test_unacknowledged_launch_is_not_reinvoked_automatically(repo: Path) -> None:
    OUTCOME.start(repo, "replay", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    seen: list[str] = []
    launch: dict[str, str] = {}

    def launch_with_lost_ack(req: Any) -> dict[str, str]:
        seen.append(req.dispatch_intent_id)
        launch.update(runtime_ack(req))
        return {"ack_kind": "launched"}

    first = OUTCOME.advance(repo, "replay", dispatcher=launch_with_lost_ack)
    second = OUTCOME.advance(repo, "replay", dispatcher=launch_with_lost_ack)
    assert first.dispatched == [] and second.dispatched == []
    assert "already exists" in second.halted[0]["reason"]
    assert seen == ["dispatch-intent:replay:leaf"]

    OUTCOME.reconcile_dispatch_ack(
        OUTCOME._store(repo, "replay"),
        repo_root=repo,
        outcome_id="replay",
        subplot_id="leaf",
        ack_kind="launched",
        dispatch_ack_ref=launch["dispatch_ack_ref"],
        leaf_saga_id=launch["leaf_saga_id"],
    )
    assert OUTCOME.status(repo, "replay")["states"]["leaf"] == "dispatched"
    assert OUTCOME.outcome_store.replay_pending(OUTCOME._store(repo, "replay")) == []


def test_expired_dispatch_lease_has_one_local_reclaimer(repo: Path) -> None:
    store = OUTCOME._store(repo, "lease").ensure()
    assert OUTCOME.outcome_store.acquire_dispatch(store, "leaf", "old", 1, now=lambda: 0.0)
    barrier = threading.Barrier(2)

    def reclaim(holder: str) -> bool:
        barrier.wait()
        return OUTCOME.outcome_store.acquire_dispatch(store, "leaf", holder, 30, now=lambda: 10.0)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reclaim, ("one", "two")))
    assert sorted(results) == [False, True]
