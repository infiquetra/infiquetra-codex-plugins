"""Tests outcome_reconcile — board<->saga drift detection + HITL resolution (#295, ported for U5).

``detect()`` is a pure classification over a REAL store's board-sync ledger (seeded with
outcome_board_sync-shaped records) plus injected fake board/issue readers — no live ``gh`` ever fires
(conftest ``_no_live_gh`` guard). Requirement traceability: R3 (plan U5); upstream KTD1-KTD7.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess  # nosec B404 — git init for the coordinator-lock test, fixed argv, no shell
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"


# Every script this module loads, kept so ``_pin_script_modules`` can re-pin them per test.
_LOADED: dict[str, ModuleType] = {}


def _load(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    _LOADED[name] = module
    return module


@pytest.fixture(autouse=True)
def _pin_script_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-pin ``sys.modules`` to THIS module's script instances for each of its tests.

    These scripts are executed by file path under bare module names, so another test module
    loading the same scripts rebinds ``sys.modules`` to a second generation while this
    module's captured globals keep pointing at the first.  A lazy sibling import inside a
    script would then resolve to the other generation, ``monkeypatch.setattr(MOD, ...)``
    would patch an orphan, and pytest's COLLECTION ORDER would silently decide the result.
    ``setitem`` restores the previous binding on teardown, so the per-file isolation that
    these modules already rely on is preserved -- this pins identity, it does not share it.
    """
    for _name, _module in _LOADED.items():
        monkeypatch.setitem(sys.modules, _name, _module)


SPEC_MOD = _load("outcome_spec")
STORE_MOD = _load("outcome_store")
_load("outcome_orchestrator")
_load("outcome_dispatcher")
_load("outcome_merge")
_load("outcome_worktrees")
_load("outcome_decompose")
OUTCOME = _load("outcome")
DISPATCH = sys.modules["outcome_dispatcher"]
REPORT = _load("outcome_report")
CERT_MOD = _load("reversibility_certificate")
SYNC_MOD = _load("outcome_board_sync")
RECON = _load("outcome_reconcile")


def _store(tmp_path: Path) -> Any:
    return STORE_MOD.Store(root=tmp_path / "store").ensure()


def _spec(nodes: list[dict[str, Any]]) -> Any:
    return SPEC_MOD.OutcomeSpec.from_dict({"outcome_id": "o", "objective": "Ship", "nodes": nodes})


def _leaf(sid: str, issue: str = "infiquetra/x#42", kind: str = "non-code") -> dict[str, Any]:
    return {"subplot_id": sid, "title": sid, "kind": kind, "github": {"issue": issue}}


_SEED_COUNTER = [0]


def _seed(
    store: Any,
    *,
    op_kind: str,
    repo: str = "infiquetra/x",
    number: int = 42,
    target_state: str = "",
    ts: float = 1.0,
    override: bool = False,
) -> None:
    """Write one board-sync ledger record directly (mirrors outcome_board_sync's own filenames)."""
    _SEED_COUNTER[0] += 1
    d = Path(store.root) / "board-sync"
    d.mkdir(parents=True, exist_ok=True)
    rec: dict[str, Any] = {
        "op_kind": op_kind,
        "repo": repo,
        "number": number,
        "ts": ts,
    }
    if override:
        rec["kind"] = "reconcile-override"
        rec["board_value"] = target_state
    elif op_kind != RECON._CLOSE_FAMILY:
        rec["target_state"] = target_state
    name = f"seed-{_SEED_COUNTER[0]}.json"
    (d / name).write_text(json.dumps(rec), encoding="utf-8")


def test_detect_empty_ledger_is_silent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    spec = _spec([_leaf("a")])
    records = RECON.detect(spec, store, board_reader=lambda ref: "Ready", issue_reader=lambda ref: {})
    assert records == []


def test_detect_silent_when_live_matches_asserted(tmp_path: Path) -> None:
    store = _store(tmp_path)
    spec = _spec([_leaf("a")])
    _seed(store, op_kind=RECON._STATUS_FAMILY, target_state="Ready", ts=1.0)
    records = RECON.detect(
        spec,
        store,
        board_reader=lambda ref: "Ready",
        issue_reader=lambda ref: {"state": "open", "state_reason": "unknown", "closed_by": ""},
    )
    assert records == []


def test_detect_status_drift(tmp_path: Path) -> None:
    store = _store(tmp_path)
    spec = _spec([_leaf("a")])
    _seed(store, op_kind=RECON._STATUS_FAMILY, target_state="Ready", ts=1.0)
    records = RECON.detect(
        spec,
        store,
        board_reader=lambda ref: "In Progress",
        issue_reader=lambda ref: {"state": "open", "state_reason": "unknown", "closed_by": ""},
    )
    drifts = [r for r in records if r["kind"] == "status-drift"]
    assert len(drifts) == 1
    assert drifts[0]["saga_value"] == "Ready"
    assert drifts[0]["board_value"] == "In Progress"


def test_detect_external_close_drift_for_code_leaf(tmp_path: Path) -> None:
    store = _store(tmp_path)
    spec = _spec([_leaf("a", kind="code")])
    _seed(store, op_kind=RECON._STATUS_FAMILY, target_state="Ready", ts=1.0)
    records = RECON.detect(
        spec,
        store,
        board_reader=lambda ref: "Ready",
        issue_reader=lambda ref: {"state": "closed", "state_reason": "completed", "closed_by": "bob"},
    )
    drifts = [r for r in records if r["kind"] == "external-close"]
    assert len(drifts) == 1
    assert drifts[0]["author"] == "bob"


def test_detect_external_close_sanctioned_for_non_code_leaf(tmp_path: Path) -> None:
    store = _store(tmp_path)
    spec = _spec([_leaf("a", kind="non-code")])
    _seed(store, op_kind=RECON._STATUS_FAMILY, target_state="Ready", ts=1.0)
    records = RECON.detect(
        spec,
        store,
        board_reader=lambda ref: "Ready",
        issue_reader=lambda ref: {"state": "closed", "state_reason": "completed", "closed_by": "bob"},
    )
    assert not [r for r in records if r["kind"] == "external-close"]


def test_detect_external_close_not_planned_is_drift_even_for_non_code(tmp_path: Path) -> None:
    store = _store(tmp_path)
    spec = _spec([_leaf("a", kind="non-code")])
    _seed(store, op_kind=RECON._STATUS_FAMILY, target_state="Ready", ts=1.0)
    records = RECON.detect(
        spec,
        store,
        board_reader=lambda ref: "Ready",
        issue_reader=lambda ref: {"state": "closed", "state_reason": "not_planned", "closed_by": "bob"},
    )
    assert [r for r in records if r["kind"] == "external-close"]


def test_detect_external_reopen_drift(tmp_path: Path) -> None:
    store = _store(tmp_path)
    spec = _spec([_leaf("a")])
    _seed(store, op_kind=RECON._CLOSE_FAMILY, ts=1.0)
    records = RECON.detect(
        spec,
        store,
        board_reader=lambda ref: "",
        issue_reader=lambda ref: {"state": "open", "state_reason": "unknown", "closed_by": ""},
    )
    reopens = [r for r in records if r["kind"] == "external-reopen"]
    assert len(reopens) == 1


def test_detect_unreadable_when_board_unreadable_but_asserted(tmp_path: Path) -> None:
    store = _store(tmp_path)
    spec = _spec([_leaf("a")])
    _seed(store, op_kind=RECON._STATUS_FAMILY, target_state="Ready", ts=1.0)
    records = RECON.detect(
        spec,
        store,
        board_reader=lambda ref: "",
        issue_reader=lambda ref: {"state": "open", "state_reason": "unknown", "closed_by": ""},
    )
    assert any(r["kind"] == "unreadable" and r["op_kind"] == RECON._STATUS_FAMILY for r in records)


def test_detect_scope_ignores_issue_with_no_ledger_record(tmp_path: Path) -> None:
    store = _store(tmp_path)
    spec = _spec([_leaf("a", issue="infiquetra/x#99")])
    # Ledger records only issue #42, not #99 (the leaf's issue) — out of scope, never probed.
    _seed(store, op_kind=RECON._STATUS_FAMILY, number=42, target_state="Ready", ts=1.0)
    records = RECON.detect(
        spec,
        store,
        board_reader=lambda ref: (_ for _ in ()).throw(AssertionError("should never be called")),
        issue_reader=lambda ref: (_ for _ in ()).throw(AssertionError("should never be called")),
    )
    assert records == []


def test_asserted_value_tie_prefers_override_over_write() -> None:
    records = [
        {"op_kind": RECON._STATUS_FAMILY, "target_state": "Ready", "ts": 1.0},
        {"op_kind": RECON._STATUS_FAMILY, "kind": "reconcile-override", "board_value": "Active", "ts": 1.0},
    ]
    assert RECON._asserted_value(records, RECON._STATUS_FAMILY) == "Active"


def test_decide_defaults_to_none_without_policy() -> None:
    assert RECON.decide({"kind": "status-drift"}) is None


def test_decide_uses_injected_policy() -> None:
    assert RECON.decide({"kind": "status-drift"}, policy=lambda d: "hold") == "hold"


def test_apply_resolution_hold_records_nothing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    drift = {
        "kind": "status-drift",
        "repo": "infiquetra/x",
        "number": 42,
        "subplot_id": "a",
        "op_kind": RECON._STATUS_FAMILY,
        "saga_value": "Ready",
        "board_value": "Active",
        "drift_id": "abc123",
    }
    result = RECON.apply_resolution(drift, "hold", store=store, board_writer=lambda **kw: None)
    assert result == {"status": "held", "drift_id": "abc123"}


def test_apply_resolution_accept_board_records_override(tmp_path: Path) -> None:
    store = _store(tmp_path)
    drift = {
        "kind": "status-drift",
        "repo": "infiquetra/x",
        "number": 42,
        "subplot_id": "a",
        "op_kind": RECON._STATUS_FAMILY,
        "saga_value": "Ready",
        "board_value": "Active",
        "drift_id": "abc123",
    }
    result = RECON.apply_resolution(drift, "accept-board", store=store, board_writer=lambda **kw: None)
    assert result["status"] == "accepted"
    files = list((Path(store.root) / "board-sync").glob("override-accept-board-*.json"))
    assert len(files) == 1


def test_apply_resolution_re_assert_calls_board_writer(tmp_path: Path) -> None:
    store = _store(tmp_path)
    calls: list[dict[str, Any]] = []
    drift = {
        "kind": "status-drift",
        "repo": "infiquetra/x",
        "number": 42,
        "subplot_id": "a",
        "op_kind": RECON._STATUS_FAMILY,
        "saga_value": "Ready",
        "board_value": "Active",
        "drift_id": "abc123",
    }
    result = RECON.apply_resolution(
        drift, "re-assert", store=store, board_writer=lambda **kw: calls.append(kw)
    )
    assert result["status"] == "reasserted"
    assert len(calls) == 1
    assert calls[0]["payload"]["target_state"] == "Ready"


def test_apply_resolution_unknown_resolution_raises(tmp_path: Path) -> None:
    store = _store(tmp_path)
    drift = {
        "kind": "status-drift",
        "repo": "infiquetra/x",
        "number": 42,
        "subplot_id": "a",
        "op_kind": RECON._STATUS_FAMILY,
        "saga_value": "Ready",
        "board_value": "Active",
        "drift_id": "abc123",
    }
    try:
        RECON.apply_resolution(drift, "nonsense", store=store, board_writer=lambda **kw: None)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


# ---------------------------------------------------------------------------
# #45 U4 — the dispatcher transient/permanent split in the reconcile hot path
# (plan R7 / R7a / R7b). ``_reconcile_once`` lives in ``outcome.py`` (:1148), not in
# ``outcome_reconcile.py``; these tests live here because this module already loads the
# whole outcome script family through one loader.
# ---------------------------------------------------------------------------


HOLDER = "holder-u4"
LEASE_TTL = 900.0


def _dispatch_spec(sid: str = "a") -> Any:
    """One ready `inline` leaf — no orchestration-ref validation, no degrade decision."""
    return SPEC_MOD.OutcomeSpec.from_dict(
        {
            "outcome_id": "o",
            "objective": "Ship",
            "nodes": [{"subplot_id": sid, "title": sid.upper(), "kind": "non-code"}],
        }
    )


def _reconcile(store: Any, spec: Any, dispatcher: Any, tmp_path: Path) -> Any:
    return OUTCOME._reconcile_once(
        tmp_path, spec, store, dispatcher, HOLDER, LEASE_TTL, lambda: 1000.0
    )


def _dispatch_records(store: Any) -> list[dict[str, Any]]:
    return [
        rec
        for rec in STORE_MOD.read_ledger(store)
        if rec.get("kind") == "dispatch" and rec.get("phase") == "halt"
    ]


class _LedgerSpy:
    """A dispatcher that snapshots the ledger at the instant of the call, then raises."""

    def __init__(self, error: BaseException) -> None:
        self.error = error
        self.snapshot: list[dict[str, Any]] | None = None
        self.calls = 0

    def __call__(self, request: Any) -> Any:
        self.calls += 1
        self.snapshot = list(STORE_MOD.read_ledger(request_store))
        raise self.error


request_store: Any = None  # bound per test; the spy reads the live store


def _release_spy(monkeypatch: Any) -> list[str]:
    """Record every lease name released, still delegating to the real release."""
    seen: list[str] = []
    original = STORE_MOD.release_lease

    def _spy(store: Any, name: str, holder: str) -> bool:
        seen.append(name)
        return original(store, name, holder)

    monkeypatch.setattr(STORE_MOD, "release_lease", _spy)
    return seen


def test_non_transient_dispatcher_error_aborts_before_release_or_write(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """R7/R7a: a PERMANENT DispatcherError re-raises at the HEAD of the arm.

    The three claims that make this the load-bearing test — a version that only asserts the exception
    type passes against an implementation that releases and writes first:

    * nothing is appended BEYOND the pre-dispatch snapshot (no halt, no ack, no settlement). The
      ``outcome.dispatch.v2`` intent is required state appended before ``dispatch(request)``, so an
      empty-ledger assertion would be satisfiable only by deleting it;
    * ``release_lease`` is never called for the per-subplot lock;
    * the per-subplot ``dispatch-{sid}`` STORE lock is still held. (The 300 s broker dispatch lease is
      already released by ``make_dispatcher``'s own finally, so asserting IT is held would be false.)
    """
    global request_store
    store = _store(tmp_path)
    request_store = store
    spec = _dispatch_spec()
    seen = _release_spy(monkeypatch)
    spy = _LedgerSpy(DISPATCH.DispatcherError("fleet-core lease broker protocol skew"))

    with pytest.raises(DISPATCH.DispatcherError) as caught:
        _reconcile(store, spec, spy, tmp_path)

    assert not isinstance(caught.value, DISPATCH.DispatcherLeaseTransientError)
    assert spy.snapshot is not None
    # Nothing further than the pre-dispatch snapshot.
    assert STORE_MOD.read_ledger(store) == spy.snapshot
    assert _dispatch_records(store) == []
    # The lock was never released...
    assert "dispatch-a" not in seen
    # ...and is demonstrably still held by this tick.
    lease = STORE_MOD.read_lease(store, "dispatch-a")
    assert lease is not None and lease.holder == HOLDER


def test_non_transient_abort_leaves_the_intent_but_no_halt(tmp_path: Path) -> None:
    """The pre-dispatch intent is required state; the abort's contract is that nothing FURTHER lands."""
    global request_store
    store = _store(tmp_path)
    request_store = store
    spec = _dispatch_spec()
    spy = _LedgerSpy(DISPATCH.DispatcherError("malformed dispatch request"))

    with pytest.raises(DISPATCH.DispatcherError):
        _reconcile(store, spec, spy, tmp_path)

    records = STORE_MOD.read_ledger(store)
    intents = [
        r for r in records if r.get("kind") == "outcome.dispatch.v2" and r.get("phase") == "intent"
    ]
    assert len(intents) == 1
    assert not [r for r in records if r.get("phase") in {"halt", "ack", "authority-ack"}]
    assert STORE_MOD.reduce_dispatch_ledger(store)["a"].get("settled") is False


def test_transient_dispatcher_error_continues_the_tick(tmp_path: Path, monkeypatch: Any) -> None:
    """R7b: the transient subclass keeps halt-and-continue — the lock is RELEASED, the tick survives."""
    global request_store
    store = _store(tmp_path)
    request_store = store
    spec = _dispatch_spec()
    seen = _release_spy(monkeypatch)
    spy = _LedgerSpy(
        DISPATCH.DispatcherLeaseTransientError("outcome dispatch lease admission refused: held")
    )

    dispatched, halted, gated, degraded = _reconcile(store, spec, spy, tmp_path)

    assert dispatched == []
    assert gated == [] and degraded == []
    assert len(halted) == 1
    assert "dispatch-a" in seen
    assert STORE_MOD.read_lease(store, "dispatch-a") is None


def test_transient_path_appends_a_reducer_visible_halt(tmp_path: Path) -> None:
    """R7b/#628: spread-first / literal-last, so ``kind`` survives as ``dispatch`` for the reducer.

    A receipt-spread ``kind`` of ``halt`` would hide the record from every dispatch-family reducer arm,
    which is exactly the invisibility shape #628 named: an orphaned intent, a leaked store lock, and a
    silent re-dispatch with no operator page.
    """
    global request_store
    store = _store(tmp_path)
    request_store = store
    spec = _dispatch_spec()
    spy = _LedgerSpy(DISPATCH.DispatcherLeaseTransientError("lease admission refused"))

    _reconcile(store, spec, spy, tmp_path)

    records = _dispatch_records(store)
    assert len(records) == 1
    halt = records[0]
    assert halt["kind"] == "dispatch"  # literal-last wins over the receipt's own kind
    assert halt["receipt_kind"] == "halt"  # ...and the receipt's kind is preserved, not lost
    assert halt["phase"] == "halt"
    assert halt["key"] == "dispatch:a"
    # Paired to the same leaf the outcome.dispatch.v2 intent was opened for.
    intent = [
        r
        for r in STORE_MOD.read_ledger(store)
        if r.get("kind") == "outcome.dispatch.v2" and r.get("phase") == "intent"
    ][0]
    assert halt["subplot_id"] == intent["subplot_id"] == "a"
    assert "lease admission refused" in halt["reason"]


def test_transient_halt_is_visible_to_the_reducer_and_the_report(tmp_path: Path) -> None:
    global request_store
    store = _store(tmp_path)
    request_store = store
    spec = _dispatch_spec()
    spy = _LedgerSpy(DISPATCH.DispatcherLeaseTransientError("lease admission refused"))

    _reconcile(store, spec, spy, tmp_path)

    reduced = STORE_MOD.reduce_dispatch_ledger(store)["a"]
    assert reduced["halted"] is True
    # A refusal must NEVER settle the leaf — the reducer's ack arms settle, and a settled leaf is
    # permanently stranded as done.
    assert reduced["settled"] is False
    assert REPORT._halted_subplots(store) == {"a"}


def test_repeated_transient_appends_exactly_one_halt_record(tmp_path: Path) -> None:
    """Append-once on (phase, key): a second tick must not double-list the same refusal."""
    global request_store
    store = _store(tmp_path)
    request_store = store
    spec = _dispatch_spec()
    spy = _LedgerSpy(DISPATCH.DispatcherLeaseTransientError("lease admission refused"))

    first = _reconcile(store, spec, spy, tmp_path)
    second = _reconcile(store, spec, spy, tmp_path)

    assert len(first[1]) == 1 and len(second[1]) == 1
    assert len(_dispatch_records(store)) == 1
    assert STORE_MOD.read_lease(store, "dispatch-a") is None


def test_backend_halt_error_arm_is_unchanged(tmp_path: Path) -> None:
    """Characterization floor: the BackendHaltError sibling still halts-and-continues, untouched.

    This pins CURRENT codex behavior, including a drift this unit deliberately does NOT repair:
    codex's BackendHaltError arm appends literal-first / spread-LAST, so the receipt's own
    ``kind: "halt"`` clobbers the literal ``kind: "dispatch"`` and the record matches no
    ``reduce_dispatch_ledger`` arm. Upstream Claude (``outcome.py:1625-1633`` at b464d090) writes the
    same record spread-first / literal-last and IS reducer-visible. Repairing it changes what the
    board sync and the report see for every backend halt, which is outside U4's R6/R7 scope — the
    finding is reported, not silently widened into this unit.
    """
    global request_store
    store = _store(tmp_path)
    request_store = store
    spec = _dispatch_spec()
    receipt = DISPATCH.HaltReceipt(
        outcome_id="o", subplot_id="a", backend="inline", reason="no backend", available=("inline",)
    )
    spy = _LedgerSpy(DISPATCH.BackendHaltError(receipt))

    dispatched, halted, _gated, _degraded = _reconcile(store, spec, spy, tmp_path)

    assert dispatched == [] and len(halted) == 1
    assert STORE_MOD.read_lease(store, "dispatch-a") is None
    appended = [r for r in STORE_MOD.read_ledger(store) if r.get("phase") == "halt"]
    assert len(appended) == 1
    assert appended[0]["key"] == "dispatch:a"
    assert appended[0]["kind"] == "halt"  # the documented drift, pinned not fixed
    assert _dispatch_records(store) == []


def _git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for argv in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@t"],
        ["git", "config", "user.name", "t"],
        ["git", "commit", "-q", "--allow-empty", "-m", "init"],
    ):
        subprocess.run(argv, cwd=repo, check=True)  # noqa: S603,S607
    return repo


def test_non_transient_abort_releases_the_coordinator_lock(tmp_path: Path) -> None:
    """R7a's THIRD claim: a permanent fault must abort loudly without WEDGING the coordinator.

    The other two R7a claims (re-raise before lease release, before ledger writes) are pinned by
    the tests above — but all of them call ``_reconcile_once`` directly, which never enters
    ``advance()`` and therefore cannot observe the coordinator lease at all. The outer
    ``try``/``finally`` that releases it (``outcome.py`` :1128-1129) was consequently unpinned.
    That is the expensive one to regress: the coordinator lease is what serializes ticks
    cross-process, so a permanent fault that escaped without releasing it would strand the whole
    outcome until the lease TTL expired, with every intervening tick silently no-opping.

    Asserting the lease record is gone is necessary but not sufficient — it would still pass if
    the lease were left in a state a *different* holder could not acquire. So the second half
    re-enters ``advance()`` under a different holder and asserts the tick actually RAN
    (``skipped_busy`` false, ``ticks`` >= 1); a still-held coordinator returns ``skipped_busy=True``
    with ``ticks=0`` before any work happens.

    Note what the second tick deliberately does NOT assert: that the dispatcher raises again. It
    does not run at all. The first tick already appended the pre-dispatch ``outcome.dispatch.v2``
    intent for ``a``, and the intent-dedup arm short-circuits every later tick before the dispatch
    call — so a re-raise assertion here would fail for a reason that has nothing to do with the
    coordinator lease.
    """
    repo = _git_repo(tmp_path)
    OUTCOME.start(repo, "o", "obj", nodes=[{"subplot_id": "a", "title": "A", "kind": "non-code"}])

    def _permanent(_request: Any) -> Any:
        raise DISPATCH.DispatcherError("fleet-core lease broker protocol skew")

    with pytest.raises(DISPATCH.DispatcherError):
        OUTCOME.advance(repo, "o", dispatcher=_permanent, holder="holder-loud-abort")

    store = OUTCOME._store(repo, "o")
    assert STORE_MOD.read_lease(store, STORE_MOD.COORDINATOR_LOCK) is None

    second = OUTCOME.advance(repo, "o", dispatcher=_permanent, holder="holder-second-tick")
    assert second.skipped_busy is False
    assert second.ticks >= 1
