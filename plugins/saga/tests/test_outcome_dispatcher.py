"""Tests outcome_dispatcher's typed lease-transient contract (#45 U4 — plan R6/KTD2/KTD3).

The dispatch seam classifies its lease faults into two categories and the reconcile arm in
``outcome.py`` branches on exactly one ``isinstance``:

* :class:`DispatcherLeaseTransientError` — a lease-LIFECYCLE transient (refuse-mode admission conflict
  on a live unexpired prior, a mid-flight renew loss, a lease that vanished before settlement). A later
  tick re-attempts once the holder releases.
* plain :class:`DispatcherError` — a PERMANENT fault (fleet-core shim/protocol skew, a fail-closed
  settlement release refusal, a malformed request). It aborts the tick loudly.

The classifier ``_lease_conflict_error_type`` resolves the conflict type through the SAME shim the
acquire used and **declines** to transient when that shim will not load — an unresolvable shim IS the
permanent fault, so guessing transient there would silently retry a broken install forever.

No live fleet-core is loaded: the shim is faked so these tests pin the classification contract, not
the broker.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace
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
    ``setitem`` restores the previous binding on teardown, so modules stay per-file isolated.
    """
    for _name, _module in _LOADED.items():
        monkeypatch.setitem(sys.modules, _name, _module)


_load("outcome_spec")
DISPATCH = _load("outcome_dispatcher")


class _FakeLeaseConflictError(Exception):
    """Stands in for fleet_commons.lease_broker.LeaseConflictError (refuse-mode admission)."""


class _FakeAdmissionLimits:
    max_concurrent = 3
    aggregate_max_concurrent = 6

    def policy_sha256(self) -> str:
        return "0" * 64


def _fake_shim_modules(*, conflict: Any = _FakeLeaseConflictError) -> dict[str, Any]:
    broker = SimpleNamespace(
        PROTOCOL_VERSION=2,
        DEFAULT_TTL_SECONDS=300,
        LeaseConflictError=conflict,
    )
    policy = SimpleNamespace(AdmissionLimits=_FakeAdmissionLimits)
    return {"lease_broker": broker, "concurrency_policy": policy}


@pytest.fixture
def shim(monkeypatch: pytest.MonkeyPatch):
    """Install a fake fleet-commons shim on the dispatcher's imported module object."""

    modules = _fake_shim_modules()

    def _load_shim(name: str) -> Any:
        return modules[name]

    monkeypatch.setattr(DISPATCH.fleet_commons_shim, "load", _load_shim)
    return modules


@dataclass
class _Req:
    outcome_id: str = "o"
    subplot_id: str = "a"
    title: str = "A"
    backend: str = "inline"
    repo_root: Path = field(default_factory=lambda: Path("."))
    dispatch_id: str = "d1"
    attempt: int = 1


class _Lease:
    lease_id = "lease-1"
    token = "tok"


class _Authority:
    """A minimal lease authority recording the acquire kwargs the dispatcher passes."""

    def __init__(
        self,
        *,
        acquire_error: BaseException | None = None,
        renew_error: BaseException | None = None,
        release_error: BaseException | None = None,
        released: bool = True,
    ) -> None:
        self.acquire_error = acquire_error
        self.renew_error = renew_error
        self.release_error = release_error
        self.released = released
        self.acquire_kwargs: dict[str, Any] = {}
        self.renewed = 0
        self.releases = 0

    def acquire_agent(self, **kwargs: Any) -> _Lease:
        self.acquire_kwargs = kwargs
        if self.acquire_error is not None:
            raise self.acquire_error
        return _Lease()

    def renew(self, lease_id: str, *, owner_id: str, token: str) -> bool:
        self.renewed += 1
        if self.renew_error is not None:
            raise self.renew_error
        return True

    def release(self, lease_id: str, *, owner_id: str, token: str) -> bool:
        self.releases += 1
        if self.release_error is not None:
            raise self.release_error
        return self.released


# ---------------------------------------------------------------------------
# The typed subclass + the shim-safe classifier
# ---------------------------------------------------------------------------


def test_transient_is_a_dispatcher_error_subclass() -> None:
    """Every existing ``except DispatcherError`` must keep catching the transient (KTD2)."""
    assert issubclass(DISPATCH.DispatcherLeaseTransientError, DISPATCH.DispatcherError)
    err = DISPATCH.DispatcherLeaseTransientError("x")
    assert isinstance(err, DISPATCH.DispatcherError)


def test_lease_conflict_error_type_resolves_through_the_shim(shim: dict[str, Any]) -> None:
    assert DISPATCH._lease_conflict_error_type() is _FakeLeaseConflictError


def test_lease_conflict_error_type_declines_when_the_shim_will_not_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A shim that will not load IS the permanent fault — decline, never assume transient."""

    def _boom(name: str) -> Any:
        raise RuntimeError("fleet-core is not installed")

    monkeypatch.setattr(DISPATCH.fleet_commons_shim, "load", _boom)
    assert DISPATCH._lease_conflict_error_type() is None


def test_lease_conflict_error_type_declines_a_non_type_attribute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modules = _fake_shim_modules(conflict="not-a-class")
    monkeypatch.setattr(DISPATCH.fleet_commons_shim, "load", lambda name: modules[name])
    assert DISPATCH._lease_conflict_error_type() is None


def test_lease_conflict_error_type_declines_a_missing_attribute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker = SimpleNamespace(PROTOCOL_VERSION=2, DEFAULT_TTL_SECONDS=300)
    monkeypatch.setattr(DISPATCH.fleet_commons_shim, "load", lambda name: broker)
    assert DISPATCH._lease_conflict_error_type() is None


# ---------------------------------------------------------------------------
# Admission-site classification
# ---------------------------------------------------------------------------


def test_admission_requests_refuse_mode(shim: dict[str, Any]) -> None:
    """The seam opts in to refuse-mode admission — without it there is no typed conflict to classify."""
    authority = _Authority()
    dispatcher = DISPATCH.make_dispatcher(lease_authority=authority)
    dispatcher(_Req())
    assert authority.acquire_kwargs.get("on_conflict") == "refuse"


def test_refuse_mode_admission_conflict_is_transient(shim: dict[str, Any]) -> None:
    authority = _Authority(acquire_error=_FakeLeaseConflictError("held by a live peer"))
    dispatcher = DISPATCH.make_dispatcher(lease_authority=authority)
    with pytest.raises(DISPATCH.DispatcherLeaseTransientError) as caught:
        dispatcher(_Req())
    assert "lease admission refused" in str(caught.value)


def test_non_conflict_admission_failure_stays_permanent(shim: dict[str, Any]) -> None:
    authority = _Authority(acquire_error=RuntimeError("protocol skew"))
    dispatcher = DISPATCH.make_dispatcher(lease_authority=authority)
    with pytest.raises(DISPATCH.DispatcherError) as caught:
        dispatcher(_Req())
    assert not isinstance(caught.value, DISPATCH.DispatcherLeaseTransientError)


def test_admission_conflict_with_an_unloadable_shim_stays_permanent(
    monkeypatch: pytest.MonkeyPatch, shim: dict[str, Any]
) -> None:
    """Classification declines to transient when the conflict type cannot be resolved."""
    monkeypatch.setattr(DISPATCH, "_lease_conflict_error_type", lambda: None)
    authority = _Authority(acquire_error=_FakeLeaseConflictError("held"))
    dispatcher = DISPATCH.make_dispatcher(lease_authority=authority)
    with pytest.raises(DISPATCH.DispatcherError) as caught:
        dispatcher(_Req())
    assert not isinstance(caught.value, DISPATCH.DispatcherLeaseTransientError)


# ---------------------------------------------------------------------------
# Mid-flight and settlement lease faults
# ---------------------------------------------------------------------------


def test_renew_failure_is_transient(shim: dict[str, Any]) -> None:
    authority = _Authority(renew_error=RuntimeError("expired"))
    dispatcher = DISPATCH.make_dispatcher(lease_authority=authority)
    with pytest.raises(DISPATCH.DispatcherLeaseTransientError) as caught:
        dispatcher(_Req())
    assert "expired before settlement" in str(caught.value)


def test_release_refusal_stays_permanent(shim: dict[str, Any]) -> None:
    """A broker that actively REFUSED the release is a fail-closed integrity fault, not a transient."""
    authority = _Authority(release_error=RuntimeError("wrong token"))
    dispatcher = DISPATCH.make_dispatcher(lease_authority=authority)
    with pytest.raises(DISPATCH.DispatcherError) as caught:
        dispatcher(_Req())
    assert not isinstance(caught.value, DISPATCH.DispatcherLeaseTransientError)
    assert "settlement refused" in str(caught.value)


def test_vanished_lease_at_release_is_transient(shim: dict[str, Any]) -> None:
    authority = _Authority(released=False)
    dispatcher = DISPATCH.make_dispatcher(lease_authority=authority)
    with pytest.raises(DISPATCH.DispatcherLeaseTransientError) as caught:
        dispatcher(_Req())
    assert "disappeared before authoritative settlement" in str(caught.value)


def test_no_authority_preserves_the_injected_compatibility_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``lease_authority=None`` takes no lease and never touches the shim (characterization)."""

    def _boom(name: str) -> Any:  # pragma: no cover - must never be reached
        raise AssertionError("the lease-free path must not load fleet-core")

    monkeypatch.setattr(DISPATCH.fleet_commons_shim, "load", _boom)
    dispatcher = DISPATCH.make_dispatcher()
    assert dispatcher(_Req())["status"] == "prepared"
