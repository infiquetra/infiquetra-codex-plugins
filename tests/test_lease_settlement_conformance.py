"""Cross-runtime lease/settlement conformance matrix (#33 U4).

Drives identical neutral fixtures through the ported broker and settlement modules and pins the
resulting state digests. The pinned constants are the cross-runtime anchor: the source runtime
(infiquetra-claude-plugins at cf15a09f) runs byte-identical module code over the same fixtures, so
a digest drift on either side is a semantic fork of the shared substrate, never noise — both
scenarios are proven root-independent in-suite before the digest comparison.

Authority-negative oracles prove zero mutation: a fenced-out or duplicate writer changes nothing,
not even one byte of registry or ledger state.
"""

from __future__ import annotations

import hashlib
import importlib.util
import multiprocessing
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent
FLEET = ROOT / "plugins" / "fleet-core" / "scripts" / "fleet_commons"
SAGA = ROOT / "plugins" / "saga" / "scripts"

EXPECTED_BROKER_REGISTRY_SHA256 = "f60fd482bba4ed5744e4ad590595f9ab92654f66f6371e57350dbc88c75a4b9d"
EXPECTED_SETTLEMENT_LEDGER_SHA256 = (
    "34804e26ad77eb96eb877d0c5bf3432018c60d739c49f7891aa79e13803a963a"
)

DISPATCH_ID = "outcome:conform:frontier:aa11bb22"
IDEMPOTENCY_KEY = "outcome:conform:u1"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


B = _load(FLEET / "lease_broker.py", "conformance_fleet_lease_broker")
P = _load(FLEET / "concurrency_policy.py", "conformance_concurrency_policy")
if str(SAGA) not in sys.path:
    sys.path.insert(0, str(SAGA))
DS = _load(SAGA / "dispatch_settlement.py", "conformance_dispatch_settlement")


@dataclass
class FakeRuntime:
    wall: datetime = datetime(2026, 7, 19, 12, tzinfo=UTC)
    monotonic: int = 1_000_000_000
    boot: str = "boot-conform"
    next_uuid: int = 1
    processes: dict[int, tuple[bool, str | None]] = field(default_factory=dict)

    def uuid4(self) -> uuid.UUID:
        value = uuid.UUID(int=self.next_uuid)
        self.next_uuid += 1
        return value

    def providers(self) -> Any:
        return B.Providers(
            wall_now=lambda: self.wall,
            monotonic_ns=lambda: self.monotonic,
            boot_id=lambda: self.boot,
            uuid4=self.uuid4,
            process_identity=lambda pid: self.processes.get(pid, (False, None))[1],
            process_exists=lambda pid: self.processes.get(pid, (False, None))[0],
        )

    def advance(self, seconds: int) -> None:
        self.monotonic += seconds * 1_000_000_000
        self.wall += timedelta(seconds=seconds)


def _broker_scenario(root: Path) -> Any:
    """The neutral acquire -> renew -> release fixture; returns the broker for inspection."""

    runtime = FakeRuntime()
    broker = B.LeaseBroker(root, providers=runtime.providers())
    limits = P.AdmissionLimits()
    lease = broker.acquire_agent(
        owner_id="conform-owner",
        session_id="conform-session",
        policy_sha256=limits.policy_sha256(),
        session_limit=limits.max_concurrent,
        aggregate_limit=limits.aggregate_max_concurrent,
        mutation="read-write",
        ttl_seconds=300,
        resource_ref={"logical_unit_id": "conform-unit"},
        agent_type="conformance",
    )
    runtime.advance(10)
    broker.renew(lease.lease_id, owner_id="conform-owner", token=lease.token)
    runtime.advance(10)
    broker.release(lease.lease_id, owner_id="conform-owner", token=lease.token)
    return broker


def _spawn_fact() -> dict[str, Any]:
    return DS.spawn_fact(
        subplot_id="conform",
        at="2026-07-19T12:00:05Z",
        dispatch_id=DISPATCH_ID,
        unit_id="u1",
        attempt=1,
        idempotency_key=IDEMPOTENCY_KEY,
    )


def _ledger_scenario(path: Path, *, spawn: bool = True, settle: bool = True) -> Any:
    """The neutral manifest -> spawn (-> delivered settle) fixture; returns the ledger."""

    ledger = DS.run_ledger.RunLedger(path=path)
    DS.append_manifest(
        ledger,
        DS.manifest_fact(
            subplot_id="conform",
            at="2026-07-19T12:00:00Z",
            dispatch_id=DISPATCH_ID,
            site="outcome",
            units=[
                DS.UnitSpec(
                    unit_id="u1", idempotency_key=IDEMPOTENCY_KEY, deliverables=("artifact",)
                )
            ],
        ),
    )
    if not spawn:
        return ledger
    DS.append_spawn(ledger, _spawn_fact())
    if settle:
        DS.append_settlement(
            ledger,
            DS.settle_fact(
                subplot_id="conform",
                at="2026-07-19T12:00:10Z",
                dispatch_id=DISPATCH_ID,
                unit_id="u1",
                attempt=1,
                classification=DS.DELIVERED,
                reason="conformance fixture delivery",
                evidence_ref="conform-evidence-1",
                evidence_sha256="ab" * 32,
            ),
        )
    return ledger


def test_broker_registry_digest_is_root_independent_and_pinned(tmp_path: Path) -> None:
    first = _broker_scenario(tmp_path / "authority-a").registry_path.read_bytes()
    second = _broker_scenario(tmp_path / "deeper" / "authority-b").registry_path.read_bytes()

    assert first == second
    assert hashlib.sha256(first).hexdigest() == EXPECTED_BROKER_REGISTRY_SHA256


def test_settlement_ledger_digest_is_root_independent_and_pinned(tmp_path: Path) -> None:
    first = _ledger_scenario(tmp_path / "run-facts.jsonl").path.read_bytes()
    second = _ledger_scenario(tmp_path / "deeper" / "elsewhere.jsonl").path.read_bytes()

    assert first == second
    assert hashlib.sha256(first).hexdigest() == EXPECTED_SETTLEMENT_LEDGER_SHA256


def test_settlement_read_views_project_shared_attempt_identity(tmp_path: Path) -> None:
    open_ledger = _ledger_scenario(tmp_path / "open.jsonl", settle=False)
    positions = DS.open_positions(open_ledger)
    assert len(positions) == 1
    assert positions[0]["dispatch_id"] == DISPATCH_ID
    assert positions[0]["unit_id"] == "u1"
    assert positions[0]["attempt"] == 1
    assert positions[0]["idempotency_key"] == IDEMPOTENCY_KEY

    settled_ledger = _ledger_scenario(tmp_path / "settled.jsonl")
    assert DS.open_positions(settled_ledger) == []
    report = DS.settlement_report(settled_ledger, DISPATCH_ID)
    assert report.dispatch_id == DISPATCH_ID
    assert report.halt_required is False
    assert len(report.entries) == 1
    entry = report.entries[0]
    assert (entry.unit_id, entry.attempt, entry.classification) == ("u1", 1, DS.DELIVERED)
    assert entry.spawned is True and entry.settled is True


def test_fenced_out_release_and_renew_mutate_zero_registry_bytes(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    broker = B.LeaseBroker(tmp_path / "authority", providers=runtime.providers())
    limits = P.AdmissionLimits()
    lease = broker.acquire_agent(
        owner_id="conform-owner",
        session_id="conform-session",
        policy_sha256=limits.policy_sha256(),
        session_limit=limits.max_concurrent,
        aggregate_limit=limits.aggregate_max_concurrent,
        mutation="read-write",
        ttl_seconds=300,
        resource_ref={"logical_unit_id": "conform-unit"},
        agent_type="conformance",
    )
    before = broker.registry_path.read_bytes()

    with pytest.raises(B.LeaseBrokerError):
        broker.release(lease.lease_id, owner_id="intruder", token=lease.token)
    with pytest.raises(B.LeaseBrokerError):
        broker.renew(lease.lease_id, owner_id="intruder", token=lease.token)

    assert broker.registry_path.read_bytes() == before


def test_duplicate_spawn_replay_mutates_zero_ledger_bytes(tmp_path: Path) -> None:
    ledger = _ledger_scenario(tmp_path / "run-facts.jsonl", settle=False)
    before = ledger.path.read_bytes()

    with pytest.raises(DS.DispatchSettlementError):
        DS.append_spawn(ledger, _spawn_fact())

    assert ledger.path.read_bytes() == before


def test_conflicting_resettle_mutates_zero_ledger_bytes(tmp_path: Path) -> None:
    ledger = _ledger_scenario(tmp_path / "run-facts.jsonl")
    before = ledger.path.read_bytes()

    with pytest.raises(DS.DispatchSettlementError):
        DS.append_settlement(
            ledger,
            DS.settle_fact(
                subplot_id="conform",
                at="2026-07-19T12:00:20Z",
                dispatch_id=DISPATCH_ID,
                unit_id="u1",
                attempt=1,
                classification=DS.IDLE,
                reason="conflicting second settlement must be refused",
            ),
        )

    assert ledger.path.read_bytes() == before


def _race_spawn(path: Path, outcomes: Any) -> None:
    ledger = DS.run_ledger.RunLedger(path=path)
    try:
        DS.append_spawn(ledger, _spawn_fact())
        outcomes.put("appended")
    except DS.DispatchSettlementError:
        outcomes.put("refused")


def test_two_process_spawn_race_yields_exactly_one_position(tmp_path: Path) -> None:
    path = tmp_path / "run-facts.jsonl"
    ledger = _ledger_scenario(path, spawn=False, settle=False)

    context = multiprocessing.get_context("fork")
    outcomes = context.Queue()
    workers = [context.Process(target=_race_spawn, args=(path, outcomes)) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=30)
    results = sorted(outcomes.get(timeout=5) for _ in workers)

    assert results == ["appended", "refused"]
    positions = DS.open_positions(ledger)
    assert len(positions) == 1
    assert positions[0]["idempotency_key"] == IDEMPOTENCY_KEY
