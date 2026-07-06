"""Tests outcome_reconcile — board<->saga drift detection + HITL resolution (#295, ported for U5).

``detect()`` is a pure classification over a REAL store's board-sync ledger (seeded with
outcome_board_sync-shaped records) plus injected fake board/issue readers — no live ``gh`` ever fires
(conftest ``_no_live_gh`` guard). Requirement traceability: R3 (plan U5); upstream KTD1-KTD7.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"


def _load(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SPEC_MOD = _load("outcome_spec")
STORE_MOD = _load("outcome_store")
_load("outcome_orchestrator")
_load("outcome_dispatcher")
_load("outcome_merge")
_load("outcome_worktrees")
_load("outcome_decompose")
_load("outcome")
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
