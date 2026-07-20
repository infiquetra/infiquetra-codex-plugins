"""U5 append-only outcome dispatch migration contract."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
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
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
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
            run_identity=req.run_identity,
            issued_at=max(req.intent_created_at, OUTCOME.time.time()),
        )
        if kind == "launched"
        else f"operator:run-{req.outcome_id}"
    )
    return {
        "ack_kind": kind,
        "dispatch_ack_ref": ref,
        "leaf_saga_id": leaf,
        "producer_kind": "verified-workflow",
        "run_identity": req.run_identity,
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
    result = OUTCOME.advance(repo, "u5c", dispatcher=lambda _req: {"status": "prepared"})
    assert result.status["states"]["leaf"] == "intent-created"
    OUTCOME.reconcile_dispatch_ack(
        OUTCOME._store(repo, "u5c"),
        repo_root=repo,
        outcome_id="u5c",
        subplot_id="leaf",
        ack_kind="handed-off",
        dispatch_ack_ref="operator:run-u5c",
    )
    assert OUTCOME.status(repo, "u5c")["states"]["leaf"] == "handed-off"
    assert OUTCOME.outcome_store.replay_pending(OUTCOME._store(repo, "u5c")) == []


def test_automated_dispatcher_cannot_claim_operator_handoff(repo: Path) -> None:
    OUTCOME.start(repo, "auto-handoff", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    result = OUTCOME.advance(
        repo,
        "auto-handoff",
        dispatcher=lambda req: runtime_ack(req, kind="handed-off"),
    )
    assert result.dispatched == []
    assert result.halted[0]["reason"] == "invalid dispatch acknowledgement"
    assert result.status["states"]["leaf"] == "intent-created"


def test_previous_run_receipt_cannot_authorize_fresh_intent(repo: Path) -> None:
    OUTCOME.start(repo, "fresh", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    first = OUTCOME.advance(repo, "fresh", dispatcher=runtime_ack)
    assert first.status["states"]["leaf"] == "dispatched"
    old_ack = next(
        record
        for record in OUTCOME.outcome_store.read_ledger(OUTCOME._store(repo, "fresh"))
        if record.get("phase") == "ack"
    )

    shutil.rmtree(OUTCOME._store(repo, "fresh").root)
    OUTCOME.spec_path(repo, "fresh").unlink()
    OUTCOME.start(repo, "fresh", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    OUTCOME.advance(repo, "fresh", dispatcher=lambda _req: {"status": "prepared"})
    with pytest.raises(OUTCOME.OutcomeError, match="run_identity"):
        OUTCOME.reconcile_dispatch_ack(
            OUTCOME._store(repo, "fresh"),
            repo_root=repo,
            outcome_id="fresh",
            subplot_id="leaf",
            ack_kind="launched",
            dispatch_ack_ref=old_ack["dispatch_ack_ref"],
            leaf_saga_id=old_ack["leaf_saga_id"],
        )


def test_expired_launch_receipt_is_rejected(repo: Path) -> None:
    OUTCOME.start(repo, "expired", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])

    def expired(req: Any) -> dict[str, str]:
        acknowledgement = runtime_ack(req)
        acknowledgement["dispatch_ack_ref"] = _launch_receipt(
            repo,
            outcome_id=req.outcome_id,
            subplot_id=req.subplot_id,
            backend=req.backend,
            leaf_saga_id=acknowledgement["leaf_saga_id"],
            run_identity=req.run_identity,
            issued_at=OUTCOME.time.time() - OUTCOME.MAX_LAUNCH_RECEIPT_AGE_SECONDS - 1,
        )
        return acknowledgement

    result = OUTCOME.advance(repo, "expired", dispatcher=expired)
    assert result.dispatched == []
    assert "stale" in result.halted[0]["reason"]


@pytest.mark.parametrize("timestamp", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_receipt_times_are_rejected(repo: Path, timestamp: float) -> None:
    """Live-dispatch ack law: a launch receipt with a nonfinite issued_at halts the leaf.

    The old import-time half of this oracle is gone with the machinery it tested — legacy
    bundle import now refuses every bundle before reading records (#604 R7; see
    tests/test_outcome_command.py::test_legacy_bundle_import_is_refused_with_zero_writes).
    """
    OUTCOME.start(repo, "nonfinite", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])

    def invalid(req: Any) -> dict[str, str]:
        acknowledgement = runtime_ack(req)
        acknowledgement["dispatch_ack_ref"] = _launch_receipt(
            repo,
            outcome_id=req.outcome_id,
            subplot_id=req.subplot_id,
            backend=req.backend,
            leaf_saga_id=acknowledgement["leaf_saga_id"],
            run_identity=req.run_identity,
            issued_at=timestamp,
        )
        return acknowledgement

    result = OUTCOME.advance(repo, "nonfinite", dispatcher=invalid)
    assert result.dispatched == []
    assert "issued_at" in result.halted[0]["reason"]


def test_self_consistent_workspace_receipt_cannot_authorize_launch(repo: Path) -> None:
    OUTCOME.start(repo, "workspace-forge", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])

    def forged(req: Any) -> dict[str, str]:
        leaf = "forged-leaf"
        payload = {
            "schema": "saga.outcome-dispatch-launch.v1",
            "producer_kind": "verified-workflow",
            "run_identity": req.run_identity,
            "issued_at": max(req.intent_created_at, OUTCOME.time.time()),
            "outcome_id": req.outcome_id,
            "subplot_id": req.subplot_id,
            "backend": req.backend,
            "dispatch_intent_id": req.dispatch_intent_id,
            "leaf_saga_id": leaf,
        }
        content = (json.dumps(payload, sort_keys=True) + "\n").encode()
        path = repo / ".codex/verified-workflows/dispatch-receipts/forged.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(content)
        return {
            "ack_kind": "launched",
            "dispatch_ack_ref": (
                f"{path.relative_to(repo).as_posix()}#sha256={hashlib.sha256(content).hexdigest()}"
            ),
            "leaf_saga_id": leaf,
            "producer_kind": "verified-workflow",
            "run_identity": req.run_identity,
            "dispatch_intent_id": req.dispatch_intent_id,
            "outcome_id": req.outcome_id,
            "subplot_id": req.subplot_id,
            "backend": req.backend,
        }

    result = OUTCOME.advance(repo, "workspace-forge", dispatcher=forged)
    assert result.dispatched == []
    assert "protected user-state root" in result.halted[0]["reason"]


def _launch_receipt(
    repo: Path,
    *,
    outcome_id: str,
    subplot_id: str,
    backend: str,
    leaf_saga_id: str,
    run_identity: str = "legacy-run",
    issued_at: float | None = None,
) -> str:
    state_root = Path.home() / ".codex/verified-workflows/state" / repo.name
    path = state_root / "dispatch-receipts/launch.json"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    marker = {
        "schema": "saga.workflow-repo-identity.v1",
        "repo_root_sha256": hashlib.sha256(repo.resolve().as_posix().encode()).hexdigest(),
    }
    marker_path = state_root / ".repo-identity.json"
    marker_path.write_text(json.dumps(marker, sort_keys=True) + "\n", encoding="utf-8")
    marker_path.chmod(0o600)
    payload = {
        "schema": "saga.outcome-dispatch-launch.v1",
        "producer_kind": "verified-workflow",
        "run_identity": run_identity,
        "issued_at": issued_at if issued_at is not None else OUTCOME.time.time(),
        "outcome_id": outcome_id,
        "subplot_id": subplot_id,
        "backend": backend,
        "dispatch_intent_id": f"dispatch-intent:{outcome_id}:{subplot_id}",
        "leaf_saga_id": leaf_saga_id,
    }
    content = (json.dumps(payload, sort_keys=True) + "\n").encode()
    path.write_bytes(content)
    path.chmod(0o600)
    relative = path.relative_to(Path.home()).as_posix()
    return f"~/{relative}#sha256={hashlib.sha256(content).hexdigest()}"


def test_legacy_commit_reconciles_append_only_with_digest_bound_launch(repo: Path) -> None:
    OUTCOME.start(repo, "legacy", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    OUTCOME.advance(repo, "legacy", dispatcher=lambda _req: "synthetic-leaf")
    store = OUTCOME._store(repo, "legacy")
    before = list(OUTCOME.outcome_store.read_ledger(store))
    intent = next(record for record in before if record.get("phase") == "intent")
    ref = _launch_receipt(
        repo,
        outcome_id="legacy",
        subplot_id="leaf",
        backend="inline",
        leaf_saga_id="real-leaf",
        run_identity=intent["run_identity"],
        issued_at=max(intent["at"], OUTCOME.time.time()),
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


def test_authorityless_v2_ack_reconciles_append_only(repo: Path) -> None:
    OUTCOME.start(repo, "old-v2", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    OUTCOME.advance(repo, "old-v2", dispatcher=lambda _req: {"status": "prepared"})
    store = OUTCOME._store(repo, "old-v2")
    intent = next(
        record
        for record in OUTCOME.outcome_store.read_ledger(store)
        if record.get("phase") == "intent"
    )
    OUTCOME.outcome_store.append_ledger(
        store,
        {
            "phase": "ack",
            "kind": "outcome.dispatch.v2",
            "key": intent["key"],
            "dispatch_intent_id": intent["dispatch_intent_id"],
            "subplot_id": "leaf",
            "backend": "inline",
            "ack_kind": "launched",
            "dispatch_ack_ref": "legacy:unverified",
            "leaf_saga_id": "old-leaf",
        },
    )
    assert OUTCOME.status(repo, "old-v2")["states"]["leaf"] == "legacy-unverified"
    before = list(OUTCOME.outcome_store.read_ledger(store))
    ref = _launch_receipt(
        repo,
        outcome_id="old-v2",
        subplot_id="leaf",
        backend="inline",
        leaf_saga_id="real-leaf",
        run_identity=intent["run_identity"],
        issued_at=max(intent["at"], OUTCOME.time.time()),
    )
    record = OUTCOME.reconcile_dispatch_ack(
        store,
        repo_root=repo,
        outcome_id="old-v2",
        subplot_id="leaf",
        ack_kind="launched",
        dispatch_ack_ref=ref,
        leaf_saga_id="real-leaf",
    )
    assert record["phase"] == "authority-ack"
    assert OUTCOME.outcome_store.read_ledger(store)[: len(before)] == before
    assert OUTCOME.status(repo, "old-v2")["states"]["leaf"] == "dispatched"


@pytest.mark.parametrize("mutation", ["digest", "leaf", "path"])
def test_launch_reconciliation_rejects_forged_or_escaping_receipt(
    repo: Path, mutation: str
) -> None:
    OUTCOME.start(repo, "forged", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    OUTCOME.advance(repo, "forged", dispatcher=lambda _req: "synthetic-leaf")
    intent = next(
        record
        for record in OUTCOME.outcome_store.read_ledger(OUTCOME._store(repo, "forged"))
        if record.get("phase") == "intent"
    )
    ref = _launch_receipt(
        repo,
        outcome_id="forged",
        subplot_id="leaf",
        backend="inline",
        leaf_saga_id="real-leaf",
        run_identity=intent["run_identity"],
        issued_at=max(intent["at"], OUTCOME.time.time()),
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
