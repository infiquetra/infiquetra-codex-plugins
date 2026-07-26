"""Tests the worktree lease-authority subsystem ported into codex (#45 U5 — plan R8/KTD4).

Codex's ``outcome_worktrees`` carried the R15/R32 worktree lifecycle but none of the broker
**authority** mechanism: a reap could remove a worktree and drop its registry entry without ever
proving it held the exact fleet lease that owns the path. This module pins the ported subsystem:

* :func:`prevalidate_reap_authority` — a strict, **non-mutating** proof that runs BEFORE git, the
  registry, or the outcome spec is touched. Every refusal test here asserts on **ordering** (no
  ``ops.remove`` call, unchanged registry bytes), not merely that an exception was raised.
* :class:`ReapPreflight` / :func:`_reap_prevalidated` — the proof is carried into the mutation and
  re-checked, so a registry that changes in the TOCTOU window refuses rather than acting on stale
  authority.
* the authority-carrying ``reap_worktree`` / ``harvest_worktrees`` signatures, and the
  ``production_worktree_processor`` factory + ``main()`` wiring that construct and inject the
  authority for the ``advance`` and ``prune`` verbs.

The **compatibility floor** is explicit: an existing caller that passes no authority gets exactly
today's behavior. ``test_authority_free_reap_preserves_legacy_behavior`` is a characterization test
and passes both before and after the port.

A real ``fleet_commons.lease_broker.LeaseBroker`` is used (rooted in ``tmp_path`` with injected
clock/process providers) — the authority contract is the thing under test, so faking the broker
would prove nothing about it. Git is always faked.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import subprocess  # nosec B404 — git init for one CLI-wiring test, fixed argv, no shell
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
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


# Load in dependency order so every lazy ``import outcome`` / sibling import reuses these instances.
SPEC = _load("outcome_spec")
STORE = _load("outcome_store")
_load("outcome_orchestrator")
DISPATCH = _load("outcome_dispatcher")
_load("outcome_merge")
ENG = _load("outcome")
WT = _load("outcome_worktrees")
DECOMPOSE = _load("outcome_decompose")


# --------------------------------------------------------------------------- fixtures / fakes


def _store(tmp_path: Path) -> Any:
    return STORE.Store(root=tmp_path / "store").ensure()


def _spec(nodes: list[dict[str, Any]]) -> Any:
    return SPEC.OutcomeSpec.from_dict({"outcome_id": "o", "objective": "x", "nodes": nodes})


def _sub(sid: str, **kw: Any) -> dict[str, Any]:
    """A sub-outcome node dict (``child_spec_ref`` set so ``Node.is_outcome`` is True)."""
    return {"subplot_id": sid, "title": sid, "kind": "code", "child_spec_ref": f"child-{sid}", **kw}


def _dispatched(store: Any, sid: str) -> None:
    """A settled dispatch under codex's own ``outcome.dispatch.v2`` acknowledgement contract.

    Codex reduces dispatch through a typed v2 ledger (``_dispatch_records``), not Claude's v1
    ``kind: dispatch`` row — the mechanism is mirrored, the record shape is codex-native (KTD3).
    """
    STORE.append_ledger(
        store,
        {
            "phase": "ack",
            "kind": "outcome.dispatch.v2",
            "key": f"dispatch-intent:o:{sid}",
            "dispatch_intent_id": f"dispatch-intent:o:{sid}",
            "subplot_id": sid,
            "ack_kind": "launched",
            "receipt_authority": "owner-user-state-v1",
            "dispatch_ack_ref": f"test:{sid}",
            "leaf_saga_id": f"leaf-{sid}",
        },
    )


def _completed(store: Any, sid: str, state: str = "done") -> None:
    STORE.write_completion_event(
        store,
        STORE.CompletionEvent(subplot_id=sid, state=state, idempotency_key=f"k:{sid}:{state}"),
    )


class FakeWT:
    """A fake ``WorktreeOps`` over an in-memory path set that records every mutation attempt."""

    def __init__(self, *, remove_ok: bool = True) -> None:
        self.paths: set[str] = set()
        self.removed: list[str] = []
        self.added: list[str] = []
        self.remove_ok = remove_ok

    def _add(self, path: str, _branch: str) -> bool:
        self.added.append(path)
        self.paths.add(path)
        return True

    def _remove(self, path: str) -> bool:
        self.removed.append(path)
        if not self.remove_ok:
            return False
        self.paths.discard(path)
        return True

    def _exists(self, path: str) -> bool:
        return path in self.paths

    def ops(self) -> Any:
        return WT.WorktreeOps(
            add=self._add,
            remove=self._remove,
            exists=self._exists,
            list_paths=lambda: sorted(self.paths),
        )


@dataclass
class FakeLeaseRuntime:
    """Injected wall/monotonic/boot/process providers so lease expiry is deterministic."""

    wall: datetime = datetime(2026, 7, 25, 12, tzinfo=UTC)
    monotonic: int = 1_000_000_000
    boot: str = "boot-a"
    processes: dict[int, tuple[bool, str | None]] = field(default_factory=dict)

    def providers(self) -> Any:
        authority = WT.fleet_leases.authority
        return authority.Providers(
            wall_now=lambda: self.wall,
            monotonic_ns=lambda: self.monotonic,
            boot_id=lambda: self.boot,
            process_identity=lambda pid: self.processes.get(pid, (False, None))[1],
            process_exists=lambda pid: self.processes.get(pid, (False, None))[0],
        )

    def advance(self, seconds: int) -> None:
        self.monotonic += seconds * 1_000_000_000
        self.wall += timedelta(seconds=seconds)


def _broker(tmp_path: Path, runtime: FakeLeaseRuntime, *, worktree_limit: int = 4) -> Any:
    return WT.fleet_leases.authority.LeaseBroker(
        tmp_path / "authority",
        providers=runtime.providers(),
        worktree_limit=worktree_limit,
    )


def _leased(tmp_path: Path, *, ttl_seconds: int = 300) -> tuple[Any, Any, Any, FakeWT, Any]:
    """One provisioned, lease-bound sub-outcome worktree: (runtime, broker, store, ops-fake, spec)."""
    runtime = FakeLeaseRuntime()
    runtime.processes[os.getpid()] = (True, "coordinator-start")
    broker = _broker(tmp_path, runtime)
    spec = _spec([_sub("s1")])
    store = _store(tmp_path)
    fake = FakeWT()
    WT.ensure_worktree(
        tmp_path,
        spec,
        store,
        spec.nodes[0],
        fake.ops(),
        owner="coordinator",
        lease_authority=broker,
        lease_ttl_seconds=ttl_seconds,
    )
    return runtime, broker, store, fake, spec


# --------------------------------------------------------------------------- 1. compatibility floor


def test_authority_free_reap_preserves_legacy_behavior(tmp_path: Path) -> None:
    """CHARACTERIZATION (must pass before AND after the port): an authority-free reap is unchanged.

    Existing callers pass no authority. They must still get exactly today's three behaviors:
    a registered worktree is removed + deregistered and returns True; a second reap is a clean
    ``False`` no-op; a failed ``ops.remove`` returns False and RETAINS the entry (no silent leak).
    """
    spec = _spec([_sub("s1"), _sub("s2")])
    store = _store(tmp_path)
    fake = FakeWT()
    ops = fake.ops()
    WT.ensure_worktree(tmp_path, spec, store, spec.nodes[0], ops, owner="me")
    path = str(WT.worktree_path(tmp_path, "o", "s1"))

    assert WT.reap_worktree(store, "s1", ops) is True
    assert fake.removed == [path]
    assert "s1" not in WT.read_registry(store)
    assert WT.reap_worktree(store, "s1", ops) is False  # idempotent — nothing left to reap

    stuck = FakeWT(remove_ok=False)
    WT.ensure_worktree(tmp_path, spec, store, spec.nodes[1], stuck.ops(), owner="me")
    assert WT.reap_worktree(store, "s2", stuck.ops()) is False
    assert "s2" in WT.read_registry(store)  # retained so a later pass retries

    # Once the port lands, passing the authority explicitly as None is the identical path.
    if "lease_authority" in inspect.signature(WT.reap_worktree).parameters:
        assert WT.reap_worktree(store, "s2", FakeWT().ops(), lease_authority=None) is True
        assert WT.read_registry(store) == {}


# --------------------------------------------------------------------------- 2. classify_token refusal


def test_reap_refuses_when_classify_token_rejects_and_keeps_the_worktree(tmp_path: Path) -> None:
    """An authority whose token no longer classifies as live refuses and removes nothing."""
    _runtime, broker, store, fake, _spec_obj = _leased(tmp_path)
    entry = WT.read_registry(store)["s1"]
    lease_id, token = WT._lease_binding(entry, broker)
    path = str(WT.worktree_path(tmp_path, "o", "s1"))
    assert fake.paths == {path}

    # Drop the lease out from under the registry receipt: the token is no longer current/expired.
    assert broker.release(lease_id, token=token) is True

    with pytest.raises(WT.WorktreeAuthorityError):
        WT.reap_worktree(store, "s1", fake.ops(), lease_authority=broker)

    assert fake.removed == []  # never reached the mutation
    assert fake.paths == {path}
    assert "s1" in WT.read_registry(store)


# --------------------------------------------------------------------------- 3. preflight ordering


def test_prevalidate_refuses_before_any_filesystem_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ORDERING, not just the raise: the mutation phase is never entered on a refused preflight.

    Both phases are instrumented into one shared event log. A passing test therefore proves the
    refusal happened *before* ``_reap_prevalidated`` ran and before ``ops.remove`` was called —
    an assertion on the exception alone could not distinguish "refused first" from "refused after
    removing the worktree".
    """
    _runtime, broker, store, fake, _spec_obj = _leased(tmp_path)
    entry = WT.read_registry(store)["s1"]
    lease_id, token = WT._lease_binding(entry, broker)
    assert broker.release(lease_id, token=token) is True

    events: list[str] = []
    real_prevalidate = WT.prevalidate_reap_authority
    real_apply = WT._reap_prevalidated

    def spy_prevalidate(*args: Any, **kwargs: Any) -> Any:
        events.append("preflight")
        return real_prevalidate(*args, **kwargs)

    def spy_apply(*args: Any, **kwargs: Any) -> Any:
        events.append("mutate")
        return real_apply(*args, **kwargs)

    monkeypatch.setattr(WT, "prevalidate_reap_authority", spy_prevalidate)
    monkeypatch.setattr(WT, "_reap_prevalidated", spy_apply)

    registry_before = WT._registry_path(store).read_bytes()
    with pytest.raises(WT.WorktreeAuthorityError):
        WT.reap_worktree(store, "s1", fake.ops(), lease_authority=broker)

    assert events == ["preflight"]  # the mutation phase was never entered
    assert fake.removed == []
    assert WT._registry_path(store).read_bytes() == registry_before


def test_prune_prevalidates_before_the_graph_mutation(tmp_path: Path) -> None:
    """``prune`` proves reap authority BEFORE it edits the spec — a refusal leaves the node in place."""
    _runtime, broker, store, fake, spec = _leased(tmp_path)
    entry = WT.read_registry(store)["s1"]
    lease_id, token = WT._lease_binding(entry, broker)
    assert broker.release(lease_id, token=token) is True
    revision_before = spec.spec_revision

    with pytest.raises(DECOMPOSE.DecomposeError, match="before graph mutation"):
        DECOMPOSE.prune(
            spec,
            store,
            "s1",
            worktree_ops=fake.ops(),
            lease_authority=broker,
        )

    assert [n.subplot_id for n in spec.nodes] == ["s1"]  # graph untouched
    assert spec.spec_revision == revision_before
    assert fake.removed == []
    assert "s1" in WT.read_registry(store)


def test_prune_refuses_a_lease_bound_worktree_without_authority(tmp_path: Path) -> None:
    """An authority-free prune of a lease-bound worktree refuses instead of stranding the lease."""
    _runtime, _broker, store, fake, spec = _leased(tmp_path)

    with pytest.raises(DECOMPOSE.DecomposeError, match="lease-bound"):
        DECOMPOSE.prune(spec, store, "s1", worktree_ops=fake.ops())

    assert [n.subplot_id for n in spec.nodes] == ["s1"]
    assert fake.removed == []
    assert "s1" in WT.read_registry(store)


# --------------------------------------------------------------------------- 4. processor + main() wiring


def _fake_git_runner(live: set[str]) -> Any:
    """A ``git`` runner standing in for the real adapter, backed by a canonical live-path set."""

    class _Result:
        def __init__(self, returncode: int, stdout: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def run(argv: list[str], **_kwargs: Any) -> Any:
        assert argv[0] == "git" and argv[1] == "worktree"
        verb = argv[2]
        if verb == "list":
            return _Result(0, "".join(f"worktree {p}\n" for p in sorted(live)))
        if verb == "add":
            live.add(os.path.realpath(argv[-1]))
            return _Result(0)
        if verb == "remove":
            live.discard(os.path.realpath(argv[-1]))
            return _Result(0)
        raise AssertionError(f"unexpected git worktree verb: {verb}")

    return run


def test_production_worktree_processor_threads_authority_into_the_reap_path(
    tmp_path: Path,
) -> None:
    """The ported factory resolves an authority and carries it through provision -> reap."""
    runtime = FakeLeaseRuntime()
    runtime.processes[os.getpid()] = (True, "coordinator-start")
    broker = _broker(tmp_path, runtime)
    spec = _spec([_sub("s1")])
    store = _store(tmp_path)
    _dispatched(store, "s1")
    live: set[str] = set()

    processor = ENG.production_worktree_processor(
        tmp_path,
        runner=_fake_git_runner(live),
        owner="coordinator",
        lease_authority=broker,
    )
    first = processor(spec, store)
    assert first["provisioned"] == ["s1"]
    assert "lease_root_sha256" in first  # the lease reconcile leg ran
    entry = WT.read_registry(store)["s1"]
    assert "lease" in entry  # provisioning armed the broker authority
    assert len(broker.inspect()["leases"]) == 1

    _completed(store, "s1", "done")
    second = processor(spec, store)
    assert second["reaped"] == ["s1"]
    assert broker.inspect()["leases"] == []  # the terminal reap released the exact lease
    assert WT.read_registry(store) == {}


def test_production_worktree_processor_resolves_the_default_broker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no explicit authority the factory resolves the canonical broker and injects THAT."""
    runtime = FakeLeaseRuntime()
    broker = _broker(tmp_path, runtime)
    monkeypatch.setattr(WT.fleet_leases, "broker", lambda *a, **k: broker)
    seen: list[Any] = []

    def record_reconcile(
        _root: Any, _spec: Any, _store: Any, _ops: Any, authority: Any, **_kw: Any
    ) -> dict[str, Any]:
        seen.append(authority)
        return {}

    monkeypatch.setattr(WT, "reconcile_worktree_leases", record_reconcile)
    monkeypatch.setattr(WT, "harvest_worktrees", lambda *a, **k: {})
    monkeypatch.setattr(WT, "provision_pending", lambda *a, **k: {})

    processor = ENG.production_worktree_processor(tmp_path, runner=_fake_git_runner(set()))
    processor(_spec([_sub("s1")]), _store(tmp_path))
    assert seen == [broker]


def test_main_advance_wires_an_authority_carrying_worktree_processor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``main() advance`` hands ``advance`` a processor that reaches the reap path with authority."""
    runtime = FakeLeaseRuntime()
    broker = _broker(tmp_path, runtime)
    captured: dict[str, Any] = {}
    seen: list[Any] = []

    monkeypatch.setattr(WT.fleet_leases, "broker", lambda *a, **k: broker)
    monkeypatch.setattr(DISPATCH, "default_lease_authority", lambda *a, **k: broker)
    monkeypatch.setattr(DISPATCH, "resolve_available", lambda *a, **k: {})
    monkeypatch.setattr(DISPATCH, "make_dispatcher", lambda *a, **k: None)

    def record_reconcile(
        _root: Any, _spec: Any, _store: Any, _ops: Any, authority: Any, **_kw: Any
    ) -> dict[str, Any]:
        seen.append(authority)
        return {}

    monkeypatch.setattr(WT, "reconcile_worktree_leases", record_reconcile)
    monkeypatch.setattr(WT, "harvest_worktrees", lambda *a, **k: {})
    monkeypatch.setattr(WT, "provision_pending", lambda *a, **k: {})

    class _Result:
        def to_dict(self) -> dict[str, Any]:
            return {}

    def fake_advance(*_args: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return _Result()

    monkeypatch.setattr(ENG, "advance", fake_advance)
    assert ENG.main(["--repo-root", str(tmp_path), "advance", "o"]) == 0

    processor = captured["worktree_processor"]
    assert processor is not None
    processor(_spec([_sub("s1")]), _store(tmp_path))
    assert seen == [broker]  # the wired processor carries the resolved authority


def test_main_prune_wires_the_default_lease_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``main() prune`` passes the canonical authority into the decompose prune seam."""
    runtime = FakeLeaseRuntime()
    broker = _broker(tmp_path, runtime)
    captured: dict[str, Any] = {}

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S603,S607
    ENG.start(tmp_path, "o", "objective")
    monkeypatch.setattr(DISPATCH, "default_lease_authority", lambda *a, **k: broker)

    def fake_prune(*_args: Any, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {"pruned": "s1"}

    monkeypatch.setattr(DECOMPOSE, "prune", fake_prune)
    assert ENG.main(["--repo-root", str(tmp_path), "prune", "o", "s1"]) == 0
    assert captured["lease_authority"] is broker


# --------------------------------------------------------------------------- 5. release_authority=False


def test_release_authority_false_retains_the_lease_across_a_successful_reap(
    tmp_path: Path,
) -> None:
    """A reap that is explicitly told not to release leaves the broker lease standing."""
    _runtime, broker, store, fake, _spec_obj = _leased(tmp_path)
    lease_id = WT.read_registry(store)["s1"]["lease"]["lease_id"]

    assert (
        WT.reap_worktree(store, "s1", fake.ops(), lease_authority=broker, release_authority=False)
        is True
    )
    assert WT.read_registry(store) == {}
    assert [lease["lease_id"] for lease in broker.inspect()["leases"]] == [lease_id]


# --------------------------------------------------------------------------- 6. no lease binding


def test_entry_without_a_lease_binding_degrades_to_the_documented_path(tmp_path: Path) -> None:
    """A legacy unleased entry reaps normally under an authority — no raise, no release attempt."""
    runtime = FakeLeaseRuntime()
    broker = _broker(tmp_path, runtime)
    spec = _spec([_sub("s1")])
    store = _store(tmp_path)
    fake = FakeWT()
    WT.ensure_worktree(tmp_path, spec, store, spec.nodes[0], fake.ops(), owner="legacy")
    assert "lease" not in WT.read_registry(store)["s1"]

    preflight = WT.prevalidate_reap_authority(store, "s1", broker)
    assert preflight is not None and preflight.lease_id == "" and preflight.token is None
    assert WT.reap_worktree(store, "s1", fake.ops(), lease_authority=broker) is True
    assert WT.read_registry(store) == {}
    assert broker.inspect()["leases"] == []


# --------------------------------------------------------------------------- 7. second-reap idempotency


def test_second_reap_under_authority_is_a_clean_no_op(tmp_path: Path) -> None:
    """Calling ``reap_worktree`` twice is idempotent: no raise, no double release, no second remove."""
    _runtime, broker, store, fake, _spec_obj = _leased(tmp_path)

    assert WT.reap_worktree(store, "s1", fake.ops(), lease_authority=broker) is True
    removed_after_first = list(fake.removed)
    assert broker.inspect()["leases"] == []

    assert WT.reap_worktree(store, "s1", fake.ops(), lease_authority=broker) is False
    assert fake.removed == removed_after_first  # no second removal attempt
    assert broker.inspect()["leases"] == []  # and no second release
    assert WT.read_registry(store) == {}


# --------------------------------------------------------------------------- 8. malformed receipt


@pytest.mark.parametrize(
    "receipt",
    [None, {"lease_id": "only-an-id"}, {"lease_id": "x", "token": {}, "root_sha256": "0" * 64}],
    ids=["null", "missing-fields", "foreign-root"],
)
def test_malformed_receipt_refuses_at_preflight_before_removal(
    tmp_path: Path, receipt: Any
) -> None:
    """A null or structurally invalid receipt refuses at preflight — never proceeds on partial data."""
    _runtime, broker, store, fake, _spec_obj = _leased(tmp_path)
    entry = dict(WT.read_registry(store)["s1"])
    entry["lease"] = receipt
    WT.register(store, "s1", entry)
    registry_before = WT._registry_path(store).read_bytes()

    with pytest.raises(WT.WorktreeAuthorityError):
        WT.reap_worktree(store, "s1", fake.ops(), lease_authority=broker)

    assert fake.removed == []
    assert WT._registry_path(store).read_bytes() == registry_before


def test_malformed_registry_refuses_without_repair(tmp_path: Path) -> None:
    """Strict reads surface a corrupt registry instead of quarantining/rewriting it."""
    store = _store(tmp_path)
    registry = WT._registry_path(store)
    registry.write_text("{broken\n", encoding="utf-8")

    with pytest.raises(WT.WorktreeError, match="without repair"):
        WT.read_registry_strict(store)

    assert registry.read_text(encoding="utf-8") == "{broken\n"
    assert list(store.quarantine_dir.iterdir()) == []


# --------------------------------------------------------------------------- 9. TOCTOU


def test_registry_mutated_after_preflight_refuses_the_stale_prevalidation(tmp_path: Path) -> None:
    """The TOCTOU window the preflight exists to close: a changed registry refuses the stale proof.

    A happy-path sequence proves nothing here — the entry must be mutated **between** the
    prevalidation and the mutation, which is exactly what a concurrent coordinator does.
    """
    _runtime, broker, store, fake, _spec_obj = _leased(tmp_path)
    preflight = WT.prevalidate_reap_authority(store, "s1", broker)
    assert preflight is not None and preflight.lease_id

    mutated = dict(WT.read_registry(store)["s1"])
    mutated["owner"] = "a-different-coordinator"
    WT.register(store, "s1", mutated)

    with pytest.raises(WT.WorktreeAuthorityError, match="changed after authority prevalidation"):
        WT._reap_prevalidated(
            store,
            "s1",
            fake.ops(),
            preflight,
            lease_authority=broker,
            release_authority=True,
            deregister_entry=True,
        )

    assert fake.removed == []
    assert "s1" in WT.read_registry(store)
    assert len(broker.inspect()["leases"]) == 1


# --------------------------------------------------------------------------- 10. removal failure


def test_removal_failure_leaves_the_lease_unreleased_and_is_surfaced(tmp_path: Path) -> None:
    """A stuck worktree keeps BOTH its registry entry and its broker authority, and reports failure."""
    runtime = FakeLeaseRuntime()
    runtime.processes[os.getpid()] = (True, "coordinator-start")
    broker = _broker(tmp_path, runtime)
    spec = _spec([_sub("s1")])
    store = _store(tmp_path)
    stuck = FakeWT(remove_ok=False)
    stuck.paths.add(str(WT.worktree_path(tmp_path, "o", "s1")))
    WT.register(
        store,
        "s1",
        {
            "path": str(WT.worktree_path(tmp_path, "o", "s1")),
            "branch": "saga-outcome-o-s1",
            "owner": "coordinator",
            "repo_root": str(tmp_path.resolve()),
            "outcome_id": "o",
        },
    )
    lease = WT._arm_worktree(
        tmp_path, spec, "s1", owner="coordinator", selected=broker, ttl_seconds=300
    )
    entry = dict(WT.read_registry(store)["s1"])
    entry["lease"] = WT.fleet_leases.worktree_lease_receipt(lease, broker)
    WT.register(store, "s1", entry)

    assert WT.reap_worktree(store, "s1", stuck.ops(), lease_authority=broker) is False
    assert stuck.removed  # removal WAS attempted
    assert "s1" in WT.read_registry(store)  # entry retained — never a silent leak
    assert len(broker.inspect()["leases"]) == 1  # authority NOT released for a live worktree

    _completed(store, "s1", "done")
    result = WT.harvest_worktrees(spec, store, stuck.ops(), lease_authority=broker)
    assert result["reap_failed"] == ["s1"]  # surfaced to the caller, not swallowed
    assert result["reaped"] == []


# --------------------------------------------------------------------------- 11. release failure


def test_authority_release_failure_is_surfaced_and_not_marked_successful(tmp_path: Path) -> None:
    """A release that fails does not mark the reap successful and retains the registry entry."""
    _runtime, broker, store, fake, spec = _leased(tmp_path)

    class _RefusingRelease:
        """The real broker for every proof, with only ``release`` failing."""

        def __init__(self, inner: Any, *, raises: bool) -> None:
            self._inner = inner
            self._raises = raises
            self.release_calls = 0

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

        def release(self, *_args: Any, **_kwargs: Any) -> bool:
            self.release_calls += 1
            if self._raises:
                raise WT.fleet_leases.authority.LeaseBrokerError("release refused")
            return False

    for raises in (True, False):
        refusing = _RefusingRelease(broker, raises=raises)
        assert WT.reap_worktree(store, "s1", fake.ops(), lease_authority=refusing) is False
        assert refusing.release_calls == 1
        assert "s1" in WT.read_registry(store)  # entry retained for a later pass

    _completed(store, "s1", "done")
    refusing = _RefusingRelease(broker, raises=True)
    result = WT.harvest_worktrees(spec, store, fake.ops(), lease_authority=refusing)
    assert result["reap_failed"] == ["s1"]
    assert result["reaped"] == []


# --------------------------------------------------------------------------- read-only settlement view


def test_stale_worktree_debits_are_read_only(tmp_path: Path) -> None:
    """``reconcile --leaks`` consumes a projection that must not deregister, reap, or write."""
    store = _store(tmp_path)
    path = str(WT.worktree_path(tmp_path, "o", "s1"))
    WT.register(store, "s1", {"path": path, "branch": "saga-outcome-o-s1"})
    registry_before = WT._registry_path(store).read_bytes()

    debits = WT.stale_worktree_debits(store, FakeWT().ops(), outcome_id="o")

    assert debits == [
        {"dispatch_id": "outcome:o:worktrees", "unit_id": "s1", "attempt": 1, "worktree": path}
    ]
    assert WT._registry_path(store).read_bytes() == registry_before
    assert list(store.quarantine_dir.iterdir()) == []


def test_reconcile_adopts_a_legacy_live_entry_under_a_lease(tmp_path: Path) -> None:
    """A pre-authority registry entry that is still live is adopted under a broker lease."""
    runtime = FakeLeaseRuntime()
    runtime.processes[os.getpid()] = (True, "coordinator-start")
    broker = _broker(tmp_path, runtime)
    spec = _spec([_sub("s1")])
    store = _store(tmp_path)
    fake = FakeWT()
    WT.ensure_worktree(tmp_path, spec, store, spec.nodes[0], fake.ops(), owner="legacy")

    result = WT.reconcile_worktree_leases(
        tmp_path,
        spec,
        store,
        fake.ops(),
        broker,
        owner="coordinator",
        store_resolver=lambda _outcome_id, _repo_root: store,
    )

    assert result["lease_adopted"] == ["s1"]
    assert "lease" in WT.read_registry(store)["s1"]
    assert len(broker.inspect()["leases"]) == 1
    assert result["lease_root_sha256"] == broker.root_sha256


def test_authority_free_harvest_still_reaps_terminals(tmp_path: Path) -> None:
    """CHARACTERIZATION: harvest with no authority keeps its pre-port reap/removed/cascade shape."""
    spec = _spec([_sub("s1"), _sub("s2", depends_on=["s1"])])
    store = _store(tmp_path)
    fake = FakeWT()
    WT.ensure_worktree(tmp_path, spec, store, spec.nodes[0], fake.ops(), owner="me")
    _completed(store, "s1", "done")

    result = WT.harvest_worktrees(spec, store, fake.ops())
    assert result["reaped"] == ["s1"]
    assert result["removed"] == []
    assert WT.read_registry(store) == {}


def test_cli_describes_policy(capsys: Any) -> None:
    assert WT.main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["worktree_cap"] == WT.WORKTREE_CAP
    assert payload["removed_terminal"] == WT.WORKTREE_REMOVED_STATE
