"""Contract tests for fleet-core's lease-backed admission authority (#356)."""

from __future__ import annotations

import importlib.util
import inspect
import json
import multiprocessing
import os
import stat
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[3]
BROKER_PATH = ROOT / "plugins" / "fleet-core" / "scripts" / "fleet_commons" / "lease_broker.py"
POLICY_PATH = (
    ROOT / "plugins" / "fleet-core" / "scripts" / "fleet_commons" / "concurrency_policy.py"
)


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


B = _load(BROKER_PATH, "fleet_lease_broker_under_test")
P = _load(POLICY_PATH, "fleet_concurrency_policy_under_test")


@dataclass
class FakeRuntime:
    wall: datetime = datetime(2026, 7, 16, 12, tzinfo=UTC)
    monotonic: int = 1_000_000_000
    boot: str = "boot-a"
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

    def advance(self, seconds: int, *, wall_seconds: int | None = None) -> None:
        self.monotonic += seconds * 1_000_000_000
        self.wall += timedelta(seconds=seconds if wall_seconds is None else wall_seconds)


@pytest.fixture
def runtime() -> FakeRuntime:
    return FakeRuntime()


@pytest.fixture
def broker(tmp_path: Path, runtime: FakeRuntime) -> Any:
    return B.LeaseBroker(tmp_path / "authority", providers=runtime.providers())


def _limits(**overrides: int) -> Any:
    return P.AdmissionLimits(**overrides)


def _agent(
    broker: Any,
    *,
    owner: str = "owner",
    session: str = "session",
    limits: Any | None = None,
    resource: str | None = None,
    ttl: int = 300,
    tool: str | None = None,
    agent_type: str = "worker",
) -> Any:
    effective = _limits() if limits is None else limits
    return broker.acquire_agent(
        owner_id=owner,
        session_id=session,
        policy_sha256=effective.policy_sha256(),
        session_limit=effective.max_concurrent,
        aggregate_limit=effective.aggregate_max_concurrent,
        mutation="read-write",
        ttl_seconds=ttl,
        resource_ref=None if resource is None else {"logical_unit_id": resource},
        tool_use_id=tool,
        agent_type=agent_type,
    )


def _worktree_resource(root: Path, index: int = 1) -> dict[str, str]:
    return {
        "repo_root": str(root),
        "outcome_id": "356",
        "subplot_id": f"sub-{index}",
    }


def _raw_registry(broker: Any) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(broker.registry_path.read_text(encoding="utf-8")))


def test_boot_id_fallback_ignores_wall_jump_and_expires_on_reboot(
    tmp_path: Path,
    runtime: FakeRuntime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_read_text = B.Path.read_text
    original_run = B.subprocess.run
    boot = {"value": "darwin-utmpx:1781257565:89752"}

    def deny_linux_boot_id(path: Path, *args: Any, **kwargs: Any) -> str:
        if path == Path("/proc/sys/kernel/random/boot_id"):
            raise OSError("proc boot identity unavailable")
        return cast(str, original_read_text(path, *args, **kwargs))

    def deny_darwin_boot_time(command: list[str], *args: Any, **kwargs: Any) -> Any:
        if command == ["sysctl", "-n", "kern.boottime"]:
            raise OSError("sysctl boot identity unavailable")
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(B.Path, "read_text", deny_linux_boot_id)
    monkeypatch.setattr(B.subprocess, "run", deny_darwin_boot_time)
    monkeypatch.setattr(B.sys, "platform", "darwin")
    monkeypatch.setattr(B, "_darwin_utmpx_boot_id", lambda: boot["value"])
    providers = B.Providers(
        wall_now=lambda: runtime.wall,
        monotonic_ns=lambda: runtime.monotonic,
        boot_id=B._default_boot_id,
        uuid4=runtime.uuid4,
        process_identity=lambda _pid: "stable-process",
        process_exists=lambda _pid: True,
    )
    selected = B.LeaseBroker(tmp_path / "fallback-authority", providers=providers)

    lease = _agent(selected, resource="fallback-boot-id")
    runtime.advance(1, wall_seconds=3_600)
    renewed = selected.renew(lease.lease_id, owner_id=lease.owner_id, token=lease.token)

    assert renewed.boot_id == lease.boot_id
    assert selected.verify(lease.resource_ref, lease.token).lease_id == lease.lease_id

    boot["value"] = "darwin-utmpx:1784265600:1"
    runtime.advance(1)
    with pytest.raises(B.LeaseExpiredError, match="expired"):
        selected.renew(lease.lease_id, owner_id=lease.owner_id, token=lease.token)


@pytest.mark.skipif(sys.platform != "darwin", reason="Darwin utmpx contract")
def test_darwin_utmpx_boot_identity_is_stable_across_processes() -> None:
    program = (
        "import runpy; "
        f"module = runpy.run_path({str(BROKER_PATH)!r}); "
        "print(module['_darwin_utmpx_boot_id']())"
    )
    identities = [
        subprocess.run(
            [sys.executable, "-c", program],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        for _ in range(2)
    ]

    assert identities[0].startswith("darwin-utmpx:")
    assert identities[0] == identities[1]


def test_boot_id_fails_closed_when_every_os_identity_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        B.Path, "read_text", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError())
    )
    monkeypatch.setattr(
        B.subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError())
    )
    monkeypatch.setattr(B.sys, "platform", "darwin")
    monkeypatch.setattr(B, "_darwin_utmpx_boot_id", lambda: None)

    with pytest.raises(B.UnsafeAuthorityError, match="boot identity is unavailable"):
        B._default_boot_id()


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for child in value.values():
            keys.update(_all_keys(child))
        return keys
    if isinstance(value, list):
        nested_keys: set[str] = set()
        for child in value:
            nested_keys.update(_all_keys(child))
        return nested_keys
    return set()


def test_runtime_neutral_default_and_explicit_root_resolution(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    default = B.resolve_state_root(
        {"CLAUDE_PLUGIN_ROOT": "/claude", "PLUGIN_DATA": "/plugin-data"}, home=home
    )
    assert default == home / ".local/state/infiquetra/fleet-leases"
    assert ".claude" not in str(default)
    assert ".codex" not in str(default)

    explicit = tmp_path / "explicit"
    assert B.resolve_state_root({B.STATE_ENV: str(explicit)}, home=home) == explicit
    xdg = tmp_path / "xdg"
    assert B.resolve_state_root({B.XDG_STATE_ENV: str(xdg)}, home=home) == (
        xdg / "infiquetra/fleet-leases"
    )


@pytest.mark.parametrize("name", [B.STATE_ENV, B.XDG_STATE_ENV])
def test_relative_or_unsafe_configured_root_is_rejected(name: str) -> None:
    with pytest.raises(B.UnsafeAuthorityError, match="normalized absolute"):
        B.resolve_state_root({name: "relative/state"})
    with pytest.raises(B.UnsafeAuthorityError, match="normalized absolute"):
        B.resolve_state_root({name: "/tmp/../escaped"})


def test_inspect_is_read_only_and_root_identity_is_stable(tmp_path: Path) -> None:
    root = tmp_path / "authority"
    first = B.LeaseBroker(root)
    second = B.LeaseBroker(Path(str(root)))
    assert first.root_sha256 == second.root_sha256
    assert first.inspect() == {
        "exists": False,
        "root_sha256": first.root_sha256,
        "leases": [],
        "archived_resource_fences": {},
    }
    assert not root.exists()


def test_first_write_modes_and_no_committed_expiry_field(broker: Any) -> None:
    lease = _agent(broker, resource="unit-1")
    assert lease.token.fencing_sequence == 1
    assert stat.S_IMODE(broker.root.stat().st_mode) == 0o700
    assert stat.S_IMODE(broker.lock_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(broker.registry_path.stat().st_mode) == 0o600
    raw = _raw_registry(broker)
    assert raw["schema"] == B.SCHEMA
    assert not ({"status", "expired", "expires_at", "stale"} & _all_keys(raw))


def test_exact_legacy_v1_registry_shape_migrates_to_empty_session_admissions(
    broker: Any,
) -> None:
    lease = _agent(broker, resource="legacy")
    raw = _raw_registry(broker)
    del raw["session_admissions"]
    broker.registry_path.write_text(json.dumps(raw), encoding="utf-8")
    os.chmod(broker.registry_path, 0o600)

    assert broker.inspect()["leases"][0]["lease_id"] == lease.lease_id
    assert broker.release(lease.lease_id, token=lease.token) is True
    assert _raw_registry(broker)["session_admissions"] == {}


def test_exact_legacy_settlement_close_remains_readable_but_not_current_proof(
    broker: Any,
) -> None:
    lease = _agent(broker, resource="legacy-close")
    settlement = broker.prepare_agent_settlement(
        lease.lease_id,
        owner_id=lease.owner_id,
        token=lease.token,
        producer="saga",
        run_id="legacy-run",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )
    current_close = broker.commit_agent_settlement(
        settlement.settlement_id,
        owner_id=lease.owner_id,
        token=lease.token,
        write=lambda _lease: ["legacy-evidence"],
    )
    legacy_close = {
        key: value
        for key, value in current_close.items()
        if key
        not in {
            "settlement_id",
            "session_id",
            "policy_sha256",
            "protected_write_intent_sha256",
            "settlement_sha256",
            "receipt_sha256",
            "sha256",
        }
    }
    legacy_close["receipt_sha256"] = B._record_sha256(legacy_close)
    legacy_close["sha256"] = B._record_sha256(legacy_close)

    with pytest.raises(B.RegistryCorruptError, match="missing field"):
        B.validate_settlement_close(legacy_close)

    raw = _raw_registry(broker)
    digest = B.resource_sha256(lease.resource_ref)
    raw["resource_fences"][digest]["close_receipt"] = legacy_close
    broker.registry_path.write_text(json.dumps(raw), encoding="utf-8")
    os.chmod(broker.registry_path, 0o600)

    assert broker.classify_token(lease.resource_ref, lease.token) == "closed"
    assert broker.inspect()["resource_fences"][digest]["close_receipt"] == legacy_close
    with pytest.raises(B.LeaseClosedError, match="released"):
        broker.verify(lease.resource_ref, lease.token)


def test_session_and_minimum_live_aggregate_limits(broker: Any) -> None:
    session_two = _limits(max_concurrent=2, readonly_max_concurrent=4, aggregate_max_concurrent=5)
    first = _agent(broker, session="same", limits=session_two)
    second = _agent(broker, session="same", limits=session_two)
    with pytest.raises(B.CapacityExhaustedError) as captured:
        _agent(broker, session="same", limits=session_two)
    assert captured.value.earliest_expiry is not None

    aggregate_three = _limits(
        max_concurrent=3, readonly_max_concurrent=3, aggregate_max_concurrent=3
    )
    other = B.LeaseBroker(broker.root, providers=broker.providers)
    with pytest.raises(B.PolicyMismatchError):
        _agent(other, session="same", limits=aggregate_three)

    assert broker.release(first.lease_id, token=first.token)
    assert broker.release(second.lease_id, token=second.token)
    _agent(broker, owner="a", session="a", limits=aggregate_three)
    _agent(broker, owner="b", session="b", limits=aggregate_three)
    _agent(broker, owner="c", session="c", limits=aggregate_three)
    wider = _limits(max_concurrent=4, readonly_max_concurrent=4, aggregate_max_concurrent=7)
    with pytest.raises(B.CapacityExhaustedError, match="aggregate_limit=3"):
        _agent(broker, owner="d", session="d", limits=wider)


def test_session_can_rearm_with_new_policy_after_drain(broker: Any) -> None:
    original = _agent(broker)
    changed = _limits(max_concurrent=2, readonly_max_concurrent=4, aggregate_max_concurrent=6)
    with pytest.raises(B.PolicyMismatchError):
        _agent(broker, limits=changed)
    assert broker.release(original.lease_id, token=original.token)
    assert _agent(broker, limits=changed).policy_sha256 == changed.policy_sha256()


def test_session_admission_is_exact_live_snapshot_and_compact(broker: Any) -> None:
    limits = _limits(max_concurrent=2, readonly_max_concurrent=2, aggregate_max_concurrent=3)
    configured = broker.configure_session_admission(
        "session",
        policy_sha256=limits.policy_sha256(),
        session_limit=2,
        aggregate_limit=3,
        mutation="read-write",
    )
    assert broker.get_session_admission("session") == configured
    _agent(broker, limits=limits)
    for kwargs in (
        {
            "policy_sha256": "0" * 64,
            "session_limit": 2,
            "aggregate_limit": 3,
            "mutation": "read-write",
        },
        {
            "policy_sha256": limits.policy_sha256(),
            "session_limit": 1,
            "aggregate_limit": 3,
            "mutation": "read-write",
        },
        {
            "policy_sha256": limits.policy_sha256(),
            "session_limit": 2,
            "aggregate_limit": 2,
            "mutation": "read-write",
        },
        {
            "policy_sha256": limits.policy_sha256(),
            "session_limit": 2,
            "aggregate_limit": 3,
            "mutation": "none",
        },
    ):
        with pytest.raises(B.PolicyMismatchError):
            broker.configure_session_admission("session", **kwargs)
    with pytest.raises(B.PolicyMismatchError):
        _agent(
            broker,
            limits=_limits(max_concurrent=1, readonly_max_concurrent=1, aggregate_max_concurrent=3),
        )
    with pytest.raises(B.LeaseOwnershipError):
        broker.clear_session_admission("session")
    broker.release_session("session")
    assert broker.get_session_admission("session") is None


def test_orphan_session_admissions_expire_remain_visible_and_recover_capacity(
    broker: Any, runtime: FakeRuntime
) -> None:
    for index in range(B._MAX_SESSION_ADMISSIONS):
        broker.configure_session_admission(
            f"session-{index}",
            policy_sha256="a" * 64,
            session_limit=1,
            aggregate_limit=1,
            mutation="none",
        )

    inspected = broker.inspect()["session_admissions"]
    assert len(inspected) == B._MAX_SESSION_ADMISSIONS
    assert {item["derived_state"] for item in inspected.values()} == {"armed"}
    with pytest.raises(B.CapacityExhaustedError, match="registry is full"):
        broker.configure_session_admission(
            "overflow",
            policy_sha256="a" * 64,
            session_limit=1,
            aggregate_limit=1,
            mutation="none",
        )

    runtime.advance(B.DEFAULT_TTL_SECONDS)
    broker.configure_session_admission(
        "recovered",
        policy_sha256="a" * 64,
        session_limit=1,
        aggregate_limit=1,
        mutation="none",
    )
    assert set(broker.inspect()["session_admissions"]) == {"recovered"}

    runtime.advance(B.DEFAULT_TTL_SECONDS)
    broker.sweep()
    assert broker.inspect()["session_admissions"] == {}


def test_batch_reservation_is_atomic_and_claim_is_single_use(broker: Any) -> None:
    limits = _limits(max_concurrent=3, readonly_max_concurrent=3, aggregate_max_concurrent=3)
    batch = broker.reserve_batch(
        count=3,
        owner_id="driver",
        session_id="workflow",
        batch_id="batch-1",
        agent_type="*",
        policy_sha256=limits.policy_sha256(),
        session_limit=3,
        aggregate_limit=3,
        mutation="none",
    )
    assert len(batch) == 3
    with pytest.raises(B.CapacityExhaustedError):
        broker.reserve_batch(
            count=2,
            owner_id="other",
            session_id="other",
            batch_id="batch-2",
            agent_type="reviewer",
            policy_sha256=limits.policy_sha256(),
            session_limit=3,
            aggregate_limit=3,
            mutation="none",
        )
    assert len(broker.inspect()["leases"]) == 3

    broker.prepare_batch_call(
        session_id="workflow",
        batch_id="batch-1",
        agent_type="reviewer",
        tool_use_id="workflow-tool-1",
    )
    claimed = broker.claim(
        session_id="workflow",
        agent_type="reviewer",
        agent_id="agent-1",
        resource_ref={"logical_unit_id": "review-1"},
        batch_id="batch-1",
    )
    assert claimed.lease_id == batch[0].lease_id
    assert claimed.fencing_sequence > batch[-1].fencing_sequence
    assert broker.verify_agent("agent-1").lease_id == claimed.lease_id


def test_normal_reservation_requires_two_release_signals(broker: Any) -> None:
    provisional = _agent(broker, tool="tool-1", agent_type="worker")
    claimed = broker.claim(
        session_id="session",
        agent_type="worker",
        agent_id="child-1",
        resource_ref={"logical_unit_id": "unit-1"},
    )
    assert claimed.lease_id == provisional.lease_id
    assert broker.record_parent_completed("session", "tool-1") == ()
    assert broker.verify_agent("child-1").lease_id == claimed.lease_id
    assert broker.record_child_terminal("child-1") is True
    assert broker.classify_token(claimed.resource_ref, claimed.token) == "expired"
    assert broker.record_child_terminal("child-1") is False


def test_unclaimed_failed_parent_releases_reservation(broker: Any) -> None:
    provisional = _agent(broker, tool="tool-failed")
    assert broker.record_parent_completed("session", "tool-failed") == (provisional.lease_id,)
    assert broker.inspect()["leases"] == []


def test_parent_completion_is_scoped_to_its_session(broker: Any) -> None:
    first = _agent(broker, owner="one", session="one", tool="shared")
    second = _agent(broker, owner="two", session="two", tool="shared")
    assert broker.record_parent_completed("one", "shared") == (first.lease_id,)
    assert [item["lease_id"] for item in broker.inspect()["leases"]] == [second.lease_id]


def test_batch_settlement_and_terminal_session_release_are_atomic(broker: Any) -> None:
    limits = _limits(max_concurrent=3, readonly_max_concurrent=3, aggregate_max_concurrent=3)
    batch = broker.reserve_batch(
        count=2,
        owner_id="driver",
        session_id="workflow",
        batch_id="batch",
        agent_type="*",
        policy_sha256=limits.policy_sha256(),
        session_limit=3,
        aggregate_limit=3,
        mutation="none",
    )
    broker.prepare_batch_call(
        session_id="workflow", batch_id="batch", agent_type="worker", tool_use_id="tool"
    )
    claimed = broker.claim(
        session_id="workflow",
        batch_id="batch",
        agent_type="worker",
        agent_id="child",
        resource_ref={"logical_unit_id": "unit"},
    )
    assert broker.settle_batch("batch", owner_id="driver", session_id="workflow") == (
        batch[1].lease_id,
    )
    assert broker.inspect()["leases"]
    assert broker.record_parent_completed("workflow", "tool") == ()
    assert broker.record_child_terminal("child")
    assert broker.settle_batch("batch", owner_id="driver", session_id="workflow") == (
        claimed.lease_id,
    )

    _agent(broker, owner="root", session="terminal", tool="terminal-tool")
    active = broker.claim(
        session_id="terminal",
        agent_type="worker",
        agent_id="terminal-child",
        resource_ref={"logical_unit_id": "terminal-unit"},
    )
    with pytest.raises(B.LeaseOwnershipError):
        broker.release_session_if_terminal("terminal", terminal_agent_ids=[])
    assert broker.release_session_if_terminal(
        "terminal", terminal_agent_ids=["terminal-child"]
    ) == (active.lease_id,)

    _agent(broker, owner="root", session="persisted", tool="persisted-tool")
    persisted = broker.claim(
        session_id="persisted",
        agent_type="worker",
        agent_id="persisted-child",
        resource_ref={"logical_unit_id": "persisted-unit"},
    )
    assert broker.record_child_terminal("persisted-child")
    assert broker.release_session_if_terminal("persisted", terminal_agent_ids=[]) == (
        persisted.lease_id,
    )

    _agent(broker, owner="owner-release", session="owner-release", tool="owner-tool")
    owner_bound = broker.claim(
        session_id="owner-release",
        agent_type="worker",
        agent_id="owner-child",
        resource_ref={"logical_unit_id": "owner-unit"},
    )
    with pytest.raises(B.LeaseOwnershipError, match="non-terminal"):
        broker.release_owner("owner-release", session_id="owner-release")
    assert broker.record_child_terminal("owner-child")
    assert broker.release_owner("owner-release", session_id="owner-release") == (
        owner_bound.lease_id,
    )

    unbound = _agent(broker, owner="direct-owner", session="direct-session", resource="direct")
    with pytest.raises(B.LeaseOwnershipError, match="non-terminal"):
        broker.release_owner("direct-owner", session_id="direct-session")
    assert broker.release(unbound.lease_id, token=unbound.token)


def test_session_renewal_is_atomic_and_release_is_agent_pool_scoped(
    broker: Any, runtime: FakeRuntime, tmp_path: Path
) -> None:
    first = _agent(broker, owner="parent-a", session="team-session", resource="unit-a")
    second = _agent(broker, owner="parent-b", session="team-session", resource="unit-b")
    worktree = broker.acquire_worktree(
        owner_id="outcome-owner",
        session_id="team-session",
        resource_ref=_worktree_resource(tmp_path),
    )

    runtime.advance(30)
    renewed = broker.renew_session("team-session")
    assert {lease.lease_id for lease in renewed} == {first.lease_id, second.lease_id}
    assert all(lease.renewed_monotonic_ns == runtime.monotonic for lease in renewed)

    released = broker.release_session("team-session")
    assert set(released) == {first.lease_id, second.lease_id}
    assert [lease["lease_id"] for lease in broker.inspect()["leases"]] == [worktree.lease_id]
    assert broker.release_session("team-session") == ()


def test_session_renewal_refuses_expired_member_without_partial_write(
    broker: Any, runtime: FakeRuntime
) -> None:
    short = _agent(broker, session="team-session", resource="short", ttl=5)
    long = _agent(broker, session="team-session", resource="long", ttl=60)
    before = broker.registry_path.read_bytes()

    runtime.advance(6)
    with pytest.raises(B.LeaseExpiredError, match=short.lease_id):
        broker.renew_session("team-session")

    assert broker.registry_path.read_bytes() == before
    assert broker.verify(long.resource_ref, long.token).lease_id == long.lease_id


def test_monotonic_expiry_ignores_wall_jump_and_renew_prevents_expiry(
    broker: Any, runtime: FakeRuntime
) -> None:
    lease = _agent(broker, resource="unit", ttl=10)
    runtime.wall += timedelta(days=365)
    assert broker.classify_token(lease.resource_ref, lease.token) == "current"
    runtime.advance(9, wall_seconds=-365 * 24 * 60 * 60)
    renewed = broker.renew(lease.lease_id, token=lease.token)
    runtime.advance(9)
    assert broker.classify_token(renewed.resource_ref, renewed.token) == "current"
    runtime.advance(1)
    assert broker.classify_token(renewed.resource_ref, renewed.token) == "expired"
    with pytest.raises(B.LeaseExpiredError):
        broker.renew(lease.lease_id, token=lease.token)


def test_boot_change_invalidates_process_authority(broker: Any, runtime: FakeRuntime) -> None:
    lease = _agent(broker, resource="unit", ttl=999)
    runtime.boot = "boot-b"
    assert broker.classify_token(lease.resource_ref, lease.token) == "expired"


def test_resource_head_persists_and_token_states_are_distinct(
    broker: Any, runtime: FakeRuntime
) -> None:
    first = _agent(broker, resource="unit", ttl=5)
    assert broker.classify_token(first.resource_ref, first.token) == "current"
    runtime.advance(5)
    assert broker.classify_token(first.resource_ref, first.token) == "expired"

    retry = _agent(broker, resource="unit", ttl=30)
    assert retry.fencing_sequence > first.fencing_sequence
    assert broker.classify_token(first.resource_ref, first.token) == "superseded"
    assert broker.classify_token(retry.resource_ref, retry.token) == "current"
    assert broker.release(retry.lease_id, token=retry.token)
    assert broker.classify_token(retry.resource_ref, retry.token) == "expired"
    raw = _raw_registry(broker)
    assert next(iter(raw["resource_fences"].values()))["lease_id"] == retry.lease_id


def test_closed_resource_heads_are_archived_without_losing_exact_state(
    broker: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(B, "_MAX_CLOSED_FENCES", 4)
    issued = []
    for index in range(B._MAX_CLOSED_FENCES + 2):
        lease = _agent(broker, resource=f"unit-{index}")
        issued.append(lease)
        assert broker.release(lease.lease_id, token=lease.token)
    raw = _raw_registry(broker)
    assert len(raw["resource_fences"]) == B._MAX_CLOSED_FENCES
    assert len(list(broker.closed_fences_dir.glob("*.json"))) == 2
    assert broker.classify_token(issued[0].resource_ref, issued[0].token) == "expired"
    assert broker.classify_token(issued[-1].resource_ref, issued[-1].token) == "expired"
    archived_projection = broker.inspect()["archived_resource_fences"]
    assert len(archived_projection) == 2
    assert archived_projection[B.resource_sha256(issued[0].resource_ref)]["close_receipt"] is None

    worktrees = []
    for index in range(B._MAX_CLOSED_FENCES + 2):
        lease = broker.acquire_worktree(
            owner_id="worktree",
            session_id="worktree",
            resource_ref=_worktree_resource(tmp_path, index),
        )
        worktrees.append(lease)
        assert broker.release(lease.lease_id, token=lease.token)
    raw = _raw_registry(broker)
    assert len(raw["resource_fences"]) == B._MAX_CLOSED_FENCES
    assert (
        broker.classify_token(worktrees[0].resource_ref, worktrees[0].token, pool="worktree")
        == "expired"
    )
    assert (
        broker.classify_token(worktrees[-1].resource_ref, worktrees[-1].token, pool="worktree")
        == "expired"
    )
    archived = broker.closed_fences_dir / f"{B.resource_sha256(issued[0].resource_ref)}.json"
    assert archived.is_file()
    archived.chmod(0o644)
    with pytest.raises(B.UnsafeAuthorityError, match="closed fence"):
        broker.classify_token(issued[0].resource_ref, issued[0].token)


def test_retry_supersedes_at_full_capacity(broker: Any) -> None:
    limits = _limits(max_concurrent=1, readonly_max_concurrent=1, aggregate_max_concurrent=1)
    first = _agent(broker, limits=limits, resource="same")
    retry = _agent(broker, limits=limits, resource="same")
    assert broker.classify_token(first.resource_ref, first.token) == "superseded"
    assert broker.verify(retry.resource_ref, retry.token).lease_id == retry.lease_id
    assert len(broker.inspect()["leases"]) == 1


def test_recreated_store_has_new_epoch_and_old_token_is_not_current(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    root = tmp_path / "authority"
    first_broker = B.LeaseBroker(root, providers=runtime.providers())
    first = _agent(first_broker, resource="unit")
    first_epoch = first.token.broker_epoch
    first_broker.registry_path.unlink()
    second_broker = B.LeaseBroker(root, providers=runtime.providers())
    second = _agent(second_broker, resource="unit")
    assert second.token.broker_epoch != first_epoch
    assert second_broker.classify_token(first.resource_ref, first.token) == "superseded"


def test_write_fencing_and_missing_worktree_fail_loud(tmp_path: Path, runtime: FakeRuntime) -> None:
    root = tmp_path / "authority"
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    broker = B.LeaseBroker(root, providers=runtime.providers())
    limits = _limits()
    provisional = broker.acquire_agent(
        owner_id="owner",
        session_id="session",
        policy_sha256=limits.policy_sha256(),
        session_limit=limits.max_concurrent,
        aggregate_limit=limits.aggregate_max_concurrent,
        mutation="read-write",
        agent_type="worker",
    )
    claimed = broker.claim(
        session_id="session",
        agent_type="worker",
        agent_id="child",
        resource_ref={"logical_unit_id": "unit", "worktree_root": str(worktree)},
    )
    assert claimed.lease_id == provisional.lease_id
    assert broker.assert_write_target("child", worktree / "file.txt") == claimed
    with pytest.raises(B.MissingResourceError, match="outside leased worktree"):
        broker.assert_write_target("child", tmp_path / "elsewhere.txt")
    worktree.rmdir()
    with pytest.raises(B.MissingResourceError, match="worktree is missing"):
        broker.assert_write_target("child", "file.txt")


def test_worktree_sweep_requires_dead_owner_and_preserves_failed_reap(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    broker = B.LeaseBroker(tmp_path / "authority", providers=runtime.providers(), worktree_limit=4)
    runtime.processes[100] = (True, "start-a")
    live_owner = broker.acquire_worktree(
        owner_id="owner-live",
        session_id="session",
        resource_ref=_worktree_resource(tmp_path, 1),
        ttl_seconds=1,
        owner_pid=100,
        owner_process_start="start-a",
    )
    runtime.processes[200] = (False, None)
    dead_owner = broker.acquire_worktree(
        owner_id="owner-dead",
        session_id="session",
        resource_ref=_worktree_resource(tmp_path, 2),
        ttl_seconds=1,
        owner_pid=200,
        owner_process_start="start-b",
    )
    runtime.advance(1)
    failed = broker.sweep(worktree_reaper=lambda _resource: False)
    assert failed.retained[live_owner.lease_id] == "expired-live-owner"
    assert failed.retained[dead_owner.lease_id] == "reap-failed"
    assert len(broker.inspect()["leases"]) == 2

    reaped_resources: list[dict[str, str]] = []

    def _reap(resource: dict[str, str]) -> bool:
        reaped_resources.append(resource)
        return True

    passed = broker.sweep(
        worktree_reaper=_reap,
        terminal_lease_ids=[live_owner.lease_id],
    )
    assert set(passed.reaped_worktree_leases) == {live_owner.lease_id, dead_owner.lease_id}
    assert len(reaped_resources) == 2
    assert broker.inspect()["leases"] == []


def test_worktree_acquire_never_steals_and_exact_token_transfer_renews(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    broker = B.LeaseBroker(tmp_path / "authority", providers=runtime.providers())
    resource = _worktree_resource(tmp_path)
    original = broker.acquire_worktree(
        owner_id="first",
        session_id="session",
        resource_ref=resource,
        ttl_seconds=1,
        owner_pid=10,
        owner_process_start="first-start",
    )
    assert (
        broker.acquire_worktree(
            owner_id="first",
            session_id="session",
            resource_ref=resource,
            ttl_seconds=1,
            owner_pid=10,
            owner_process_start="first-start",
        )
        == original
    )
    before = broker.registry_path.read_bytes()
    with pytest.raises(B.LeaseOwnershipError):
        broker.acquire_worktree(
            owner_id="second", session_id="session", resource_ref=resource, owner_pid=20
        )
    assert broker.registry_path.read_bytes() == before
    runtime.advance(1)
    with pytest.raises(B.LeaseExpiredError):
        broker.acquire_worktree(
            owner_id="second", session_id="session", resource_ref=resource, owner_pid=20
        )
    transferred = broker.transfer_worktree(
        original.lease_id,
        token=original.token,
        owner_id="second",
        owner_pid=20,
        owner_process_start="second-start",
    )
    assert transferred.token == original.token
    assert transferred.owner_id == "second"
    assert broker.verify(resource, original.token, pool="worktree").owner_id == "second"


def test_worktree_transfer_cannot_race_a_destructive_sweep(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    broker = B.LeaseBroker(tmp_path / "authority", providers=runtime.providers())
    lease = broker.acquire_worktree(
        owner_id="first",
        session_id="session",
        resource_ref=_worktree_resource(tmp_path),
        ttl_seconds=1,
        owner_pid=10,
        owner_process_start="first-start",
    )
    runtime.advance(1)
    reaper_entered = threading.Event()
    allow_reaper_to_finish = threading.Event()
    transfer_finished = threading.Event()
    sweep_results: list[Any] = []
    transfer_results: list[Any] = []

    def reaper(_resource: dict[str, str]) -> bool:
        reaper_entered.set()
        assert allow_reaper_to_finish.wait(timeout=5)
        return False

    def run_sweep() -> None:
        sweep_results.append(broker.sweep(worktree_reaper=reaper))

    def run_transfer() -> None:
        try:
            transfer_results.append(
                broker.transfer_worktree(
                    lease.lease_id,
                    token=lease.token,
                    owner_id="second",
                    owner_pid=20,
                    owner_process_start="second-start",
                )
            )
        finally:
            transfer_finished.set()

    sweep_thread = threading.Thread(target=run_sweep)
    sweep_thread.start()
    assert reaper_entered.wait(timeout=5)
    transfer_thread = threading.Thread(target=run_transfer)
    transfer_thread.start()
    assert not transfer_finished.wait(timeout=0.1)
    allow_reaper_to_finish.set()
    sweep_thread.join(timeout=5)
    transfer_thread.join(timeout=5)
    assert not sweep_thread.is_alive()
    assert not transfer_thread.is_alive()
    assert sweep_results[0].retained[lease.lease_id] == "reap-failed"
    assert transfer_results[0].owner_id == "second"
    assert broker.inspect()["leases"][0]["owner_id"] == "second"


def test_wrong_owner_token_and_stale_token_refusals_leave_authority_unchanged(
    broker: Any, runtime: FakeRuntime, tmp_path: Path
) -> None:
    first = _agent(broker, owner="first", resource="unit")
    before = broker.registry_path.read_bytes()
    with pytest.raises(B.LeaseOwnershipError):
        broker.release(first.lease_id, owner_id="second", token=first.token)
    with pytest.raises(B.LeaseOwnershipError):
        broker.renew(first.lease_id, token=B.FencingToken(first.token.broker_epoch, 999))
    assert broker.registry_path.read_bytes() == before

    runtime.advance(1)
    replacement = _agent(broker, owner="replacement", resource="unit")
    before = broker.registry_path.read_bytes()
    with pytest.raises(B.LeaseOwnershipError):
        broker.release(replacement.lease_id, token=first.token)
    with pytest.raises(B.LeaseOwnershipError):
        broker.renew(replacement.lease_id, token=first.token)
    assert broker.registry_path.read_bytes() == before

    worktree = broker.acquire_worktree(
        owner_id="worktree", session_id="worktree", resource_ref=_worktree_resource(tmp_path)
    )
    before = broker.registry_path.read_bytes()
    with pytest.raises(B.LeaseSupersededError):
        broker.transfer_worktree(
            worktree.lease_id,
            token=B.FencingToken(worktree.token.broker_epoch, worktree.token.fencing_sequence + 1),
            owner_id="other",
        )
    assert broker.registry_path.read_bytes() == before


def test_parent_validation_and_child_grant_share_one_authority_transaction(broker: Any) -> None:
    limits = _limits(max_concurrent=3, readonly_max_concurrent=3, aggregate_max_concurrent=3)
    parent = broker.acquire_agent(
        owner_id="parent-owner",
        session_id="session",
        policy_sha256=limits.policy_sha256(),
        session_limit=limits.max_concurrent,
        aggregate_limit=limits.aggregate_max_concurrent,
        mutation="read-write",
        resource_ref={"logical_unit_id": "parent"},
        agent_id="parent-agent",
    )
    child = broker.acquire_agent(
        owner_id="child-owner",
        session_id="session",
        policy_sha256=limits.policy_sha256(),
        session_limit=limits.max_concurrent,
        aggregate_limit=limits.aggregate_max_concurrent,
        mutation="read-write",
        resource_ref={"logical_unit_id": "child"},
        parent_agent_id="parent-agent",
    )
    assert child.session_id == parent.session_id

    with pytest.raises(B.LeaseOwnershipError, match="different session"):
        broker.acquire_agent(
            owner_id="other-child",
            session_id="other-session",
            policy_sha256=limits.policy_sha256(),
            session_limit=limits.max_concurrent,
            aggregate_limit=limits.aggregate_max_concurrent,
            mutation="read-write",
            resource_ref={"logical_unit_id": "other-child"},
            parent_agent_id="parent-agent",
        )

    assert broker.release(parent.lease_id, token=parent.token)
    with pytest.raises(B.LeaseNotFoundError, match="current parent lease"):
        broker.acquire_agent(
            owner_id="stale-child",
            session_id="session",
            policy_sha256=limits.policy_sha256(),
            session_limit=limits.max_concurrent,
            aggregate_limit=limits.aggregate_max_concurrent,
            mutation="read-write",
            resource_ref={"logical_unit_id": "stale-child"},
            parent_agent_id="parent-agent",
        )
    assert broker.release(child.lease_id, token=child.token)


def test_legacy_agent_settlement_cannot_bypass_receipt_protocol(broker: Any) -> None:
    lease = _agent(broker, resource="settlement")
    with (
        pytest.raises(B.LeaseBrokerError, match="legacy agent_settlement is disabled"),
        broker.agent_settlement(lease.lease_id, owner_id=lease.owner_id, token=lease.token),
    ):
        raise AssertionError("legacy context body must never execute")
    assert broker.classify_token(lease.resource_ref, lease.token) == "current"


def _recovery_intent(
    settlement: Any,
    *,
    runtime: FakeRuntime,
    expected_phase: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": "settlement_recovery_intent.v1",
        "resource_ref": settlement.resource_ref,
        "token": settlement.token.to_dict(),
        "lease_id": settlement.lease_id,
        "generation": B.token_generation(settlement.token),
        "settlement_id": settlement.settlement_id,
        "session_id": settlement.session_id,
        "policy_sha256": settlement.policy_sha256,
        "expected_phase": expected_phase,
        "protected_write_intent_sha256": settlement.protected_write_intent_sha256,
        "recovery_owner_id": "root-adapter",
        "recovery_owner_pid": os.getpid(),
        "recovery_owner_process_start": "root-process",
        "recovery_owner_boot_id": runtime.boot,
        "recovery_owner_effective_uid": os.geteuid(),
    }
    payload["sha256"] = B._record_sha256(payload)
    return payload


def test_recovery_is_unavailable_from_ordinary_broker_instances(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    ordinary = B.LeaseBroker(tmp_path / "authority", providers=runtime.providers())

    assert not hasattr(ordinary, "recover_agent_settlement")
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        B.LeaseBroker(
            tmp_path / "other-authority",
            providers=runtime.providers(),
            recovery_owner_id="child-selected-owner",
        )
    with pytest.raises(B.LeaseOwnershipError, match="root-adapter-owned"):
        B.SettlementRecoveryCoordinator(
            object(),
            ordinary,
            recovery_owner_id="child-selected-owner",
            recovery_handlers={},
            recovery_capability=b"x" * 32,
        )


def test_root_recovery_replay_binds_full_settlement_and_lost_response_converges(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    runtime.processes[os.getpid()] = (True, "root-process")
    runtime.processes[42] = (False, None)
    broker = B.LeaseBroker(tmp_path / "authority", providers=runtime.providers())
    coordinator = B._open_settlement_recovery_coordinator(
        broker,
        recovery_owner_id="root-adapter",
    )
    with pytest.raises(B.LeaseOwnershipError, match="different root recovery capability"):
        B._open_settlement_recovery_coordinator(
            B.LeaseBroker(tmp_path / "authority", providers=runtime.providers()),
            recovery_owner_id="forged-child-adapter",
        )
    lease = _agent(broker, resource="recovery", owner="child", ttl=30)
    raw = _raw_registry(broker)
    raw["leases"][lease.lease_id]["owner_pid"] = 42
    raw["leases"][lease.lease_id]["owner_process_start"] = "dead-child"
    broker.registry_path.write_text(json.dumps(raw), encoding="utf-8")
    os.chmod(broker.registry_path, 0o600)
    settlement = broker.prepare_agent_settlement(
        lease.lease_id,
        token=lease.token,
        owner_id=lease.owner_id,
        producer="agy",
        run_id="run-recovery",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )

    def fail_after_write(_lease: Any) -> list[str]:
        raise RuntimeError("lost protected-write response")

    with pytest.raises(RuntimeError, match="lost protected-write response"):
        broker.commit_agent_settlement(
            settlement.settlement_id,
            owner_id=lease.owner_id,
            token=lease.token,
            write=fail_after_write,
        )

    replay_count = 0

    def replay(_lease: Any, retained: Any) -> Any:
        nonlocal replay_count
        replay_count += 1
        assert retained.settlement_sha256 == settlement.settlement_sha256
        return B.SettlementReplayResult(["recovered-output"], "c" * 64, "b" * 64)

    coordinator.register_recovery_handler(B.SettlementRecoveryHandler(settlement, replay))
    intent = _recovery_intent(settlement, runtime=runtime, expected_phase="ambiguous")
    first = coordinator.recover_agent_settlement(intent, action="commit")
    retry = coordinator.recover_agent_settlement(intent, action="commit")

    assert first == retry
    assert replay_count == 1
    assert first is not None
    assert first["settlement_sha256"] == settlement.settlement_sha256
    assert first["protected_write_intent_sha256"] == "c" * 64
    assert first["expected_output_sha256"] == "b" * 64


def test_recovery_rejects_replay_result_with_wrong_output_semantics(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    runtime.processes[os.getpid()] = (True, "root-process")
    runtime.processes[42] = (False, None)
    broker = B.LeaseBroker(tmp_path / "authority", providers=runtime.providers())
    coordinator = B._open_settlement_recovery_coordinator(
        broker,
        recovery_owner_id="root-adapter",
    )
    lease = _agent(broker, resource="wrong-replay", owner="child")
    raw = _raw_registry(broker)
    raw["leases"][lease.lease_id]["owner_pid"] = 42
    raw["leases"][lease.lease_id]["owner_process_start"] = "dead-child"
    broker.registry_path.write_text(json.dumps(raw), encoding="utf-8")
    os.chmod(broker.registry_path, 0o600)
    settlement = broker.prepare_agent_settlement(
        lease.lease_id,
        token=lease.token,
        owner_id=lease.owner_id,
        producer="agy",
        run_id="wrong-replay",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )
    coordinator.register_recovery_handler(
        B.SettlementRecoveryHandler(
            settlement,
            lambda _lease, _settlement: B.SettlementReplayResult(["wrong"], "c" * 64, "d" * 64),
        )
    )
    intent = _recovery_intent(settlement, runtime=runtime, expected_phase="prepared")

    with pytest.raises(B.LeaseOwnershipError, match="write/output semantics"):
        coordinator.recover_agent_settlement(intent, action="commit")
    assert next(iter(broker.inspect()["settlements"].values()))["phase"] == "ambiguous"


def test_write_fence_rejects_existing_and_nonexistent_symlink_escape(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    worktree = tmp_path / "worktree"
    outside = tmp_path / "outside"
    worktree.mkdir()
    outside.mkdir()
    broker = B.LeaseBroker(tmp_path / "authority", providers=runtime.providers())
    _agent(broker, tool="tool")
    broker.claim(
        session_id="session",
        agent_type="worker",
        agent_id="child",
        resource_ref={"logical_unit_id": "unit", "worktree_root": str(worktree)},
    )
    (worktree / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(B.MissingResourceError, match="outside leased worktree"):
        broker.assert_write_target("child", worktree / "escape" / "new.txt")


def test_expired_agents_release_capacity_on_sweep(broker: Any, runtime: FakeRuntime) -> None:
    lease = _agent(broker, ttl=1)
    limits = _limits()
    broker.configure_session_admission(
        "session",
        policy_sha256=limits.policy_sha256(),
        session_limit=limits.max_concurrent,
        aggregate_limit=limits.aggregate_max_concurrent,
        mutation="read-write",
    )
    runtime.advance(1)
    swept = broker.sweep()
    assert swept.released_agent_leases == (lease.lease_id,)
    assert broker.inspect()["leases"] == []
    assert broker.get_session_admission("session") is None


def test_swept_receiptless_head_remains_expired_not_closed(
    broker: Any, runtime: FakeRuntime
) -> None:
    lease = _agent(broker, resource="swept-head", ttl=1)
    runtime.advance(1)

    assert broker.sweep().released_agent_leases == (lease.lease_id,)
    assert broker.classify_token(lease.resource_ref, lease.token) == "expired"
    with pytest.raises(B.LeaseExpiredError, match="expired"):
        broker.verify(lease.resource_ref, lease.token)


def test_mismatched_live_head_is_corrupt_not_closed(broker: Any) -> None:
    first = _agent(broker, resource="first-head")
    second = _agent(broker, resource="second-head")
    registry_path = broker.root / B.REGISTRY_NAME
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    digest = B.resource_sha256(first.resource_ref)
    registry["resource_fences"][digest]["lease_id"] = second.lease_id
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    registry_path.chmod(0o600)

    with pytest.raises(B.RegistryCorruptError, match="does not bind"):
        broker.classify_token(first.resource_ref, first.token)


def test_cached_authority_rejects_root_identity_change(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    root = tmp_path / "authority"
    broker = B.LeaseBroker(root, providers=runtime.providers())
    first = _agent(broker, resource="before-swap")
    retained_root = tmp_path / "retained-authority"
    root.rename(retained_root)
    root.mkdir(mode=0o700)

    with pytest.raises(B.UnsafeAuthorityError, match="root changed identity"):
        _agent(broker, resource="after-swap")

    retained = B.LeaseBroker(retained_root, providers=runtime.providers()).inspect()
    assert {item["lease_id"] for item in retained["leases"]} == {first.lease_id}
    assert not (root / B.REGISTRY_NAME).exists()


@pytest.mark.parametrize("target", ["root", "lock", "registry"])
def test_symlinked_authority_nodes_are_rejected(
    tmp_path: Path, runtime: FakeRuntime, target: str
) -> None:
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    root = tmp_path / "authority"
    if target == "root":
        root.symlink_to(real, target_is_directory=True)
    else:
        root.mkdir(mode=0o700)
        destination = tmp_path / f"real-{target}"
        destination.write_text("{}", encoding="utf-8")
        os.chmod(destination, 0o600)
        name = B.LOCK_NAME if target == "lock" else B.REGISTRY_NAME
        (root / name).symlink_to(destination)
    broker = B.LeaseBroker(root, providers=runtime.providers())
    with pytest.raises(B.UnsafeAuthorityError, match="symlink"):
        _agent(broker)


def test_unsafe_mode_fails_closed_and_unknown_top_level_key_is_tolerated(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    # A bad file mode still fails closed; an additive unknown TOP-LEVEL key is now tolerated and
    # preserved rather than bricking the reader (#617 R1 — reverses the pre-#617 brick behavior).
    root = tmp_path / "authority"
    root.mkdir(mode=0o700)
    broker = B.LeaseBroker(root, providers=runtime.providers())
    lease = _agent(broker, resource="unit-tolerated")
    os.chmod(broker.registry_path, 0o644)
    with pytest.raises(B.UnsafeAuthorityError, match="mode must be 0600"):
        broker.inspect()
    os.chmod(broker.registry_path, 0o600)
    raw = _raw_registry(broker)
    raw["unexpected"] = {"future": True}
    broker.registry_path.write_text(json.dumps(raw), encoding="utf-8")
    os.chmod(broker.registry_path, 0o600)

    # Reads no longer raise, and a mutating write preserves the unknown key byte-faithfully.
    assert broker.inspect()["leases"][0]["lease_id"] == lease.lease_id
    assert broker.release(lease.lease_id, token=lease.token) is True
    assert _raw_registry(broker)["unexpected"] == {"future": True}


def _contention_worker(root: str, start: Any, output: Any, index: int) -> None:
    module = _load(BROKER_PATH, f"fleet_lease_broker_worker_{index}")
    policy = _load(POLICY_PATH, f"fleet_concurrency_policy_worker_{index}")
    broker = module.LeaseBroker(Path(root))
    limits = policy.AdmissionLimits(
        max_concurrent=3, readonly_max_concurrent=3, aggregate_max_concurrent=3
    )
    start.wait(10)
    try:
        lease = broker.acquire_agent(
            owner_id=f"owner-{index}",
            session_id=f"session-{index}",
            policy_sha256=limits.policy_sha256(),
            session_limit=3,
            aggregate_limit=3,
            mutation="read-write",
            ttl_seconds=60,
        )
        output.put(("granted", lease.lease_id))
    except module.CapacityExhaustedError:
        output.put(("refused", None))


def _same_session_worker(root: str, start: Any, output: Any, index: int) -> None:
    module = _load(BROKER_PATH, f"fleet_lease_broker_session_worker_{index}")
    policy = _load(POLICY_PATH, f"fleet_concurrency_policy_session_worker_{index}")
    broker = module.LeaseBroker(Path(root))
    limits = policy.AdmissionLimits(
        max_concurrent=2, readonly_max_concurrent=2, aggregate_max_concurrent=7
    )
    start.wait(10)
    try:
        lease = broker.acquire_agent(
            owner_id=f"owner-{index}",
            session_id="shared-session",
            policy_sha256=limits.policy_sha256(),
            session_limit=2,
            aggregate_limit=7,
            mutation="read-write",
            ttl_seconds=60,
        )
        output.put(("granted", lease.lease_id))
    except module.CapacityExhaustedError:
        output.put(("refused", None))


def _batch_contention_worker(root: str, start: Any, output: Any, index: int) -> None:
    module = _load(BROKER_PATH, f"fleet_lease_broker_batch_worker_{index}")
    policy = _load(POLICY_PATH, f"fleet_concurrency_policy_batch_worker_{index}")
    broker = module.LeaseBroker(Path(root))
    limits = policy.AdmissionLimits(
        max_concurrent=3, readonly_max_concurrent=3, aggregate_max_concurrent=3
    )
    start.wait(10)
    try:
        leases = broker.reserve_batch(
            count=2,
            owner_id=f"driver-{index}",
            session_id=f"workflow-{index}",
            batch_id=f"batch-{index}",
            agent_type="*",
            policy_sha256=limits.policy_sha256(),
            session_limit=3,
            aggregate_limit=3,
            mutation="none",
        )
        output.put(("granted", len(leases)))
    except module.CapacityExhaustedError:
        output.put(("refused", 0))


def test_fleet_cap_contention_across_processes(tmp_path: Path) -> None:
    authority = tmp_path / "authority"
    authority.mkdir(mode=0o700)
    context = multiprocessing.get_context("fork")
    start = context.Event()
    output = context.Queue()
    processes = [
        context.Process(target=_contention_worker, args=(str(authority), start, output, index))
        for index in range(8)
    ]
    for process in processes:
        process.start()
    start.set()
    results = [output.get(timeout=20) for _ in processes]
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    assert sum(result[0] == "granted" for result in results) == 3
    assert sum(result[0] == "refused" for result in results) == 5
    broker = B.LeaseBroker(authority)
    assert len(broker.inspect()["leases"]) == 3


def test_same_session_ceiling_is_enforced_across_processes(tmp_path: Path) -> None:
    authority = tmp_path / "authority"
    authority.mkdir(mode=0o700)
    context = multiprocessing.get_context("fork")
    start = context.Event()
    output = context.Queue()
    processes = [
        context.Process(target=_same_session_worker, args=(str(authority), start, output, index))
        for index in range(6)
    ]
    for process in processes:
        process.start()
    start.set()
    results = [output.get(timeout=20) for _ in processes]
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    assert sum(result[0] == "granted" for result in results) == 2
    assert sum(result[0] == "refused" for result in results) == 4


def test_batch_reservation_contention_is_all_or_nothing_across_processes(tmp_path: Path) -> None:
    authority = tmp_path / "authority"
    authority.mkdir(mode=0o700)
    context = multiprocessing.get_context("fork")
    start = context.Event()
    output = context.Queue()
    processes = [
        context.Process(
            target=_batch_contention_worker, args=(str(authority), start, output, index)
        )
        for index in range(2)
    ]
    for process in processes:
        process.start()
    start.set()
    results = [output.get(timeout=20) for _ in processes]
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    assert sorted(results) == [("granted", 2), ("refused", 0)]
    assert len(B.LeaseBroker(authority).inspect()["leases"]) == 2


# --- refuse-mode admission (#627 R5 / #637 liveness probe), ported from Claude b464d090 ---


def _refuse_acquire(
    broker: Any,
    *,
    owner: str,
    resource: str,
    limits: Any | None = None,
    ttl: int = 300,
    owner_pid: int | None = None,
    owner_process_start: str | None = None,
) -> Any:
    effective = _limits() if limits is None else limits
    return broker.acquire_agent(
        owner_id=owner,
        session_id="session",
        policy_sha256=effective.policy_sha256(),
        session_limit=effective.max_concurrent,
        aggregate_limit=effective.aggregate_max_concurrent,
        mutation="none",
        ttl_seconds=ttl,
        resource_ref={"logical_unit_id": resource},
        agent_type="worker",
        owner_pid=owner_pid,
        owner_process_start=owner_process_start,
        on_conflict="refuse",
    )


def test_refuse_mode_rejects_live_prior_and_leaves_registry_untouched(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    # Two brokers over one state dir model the cross-runtime dispatch seam (#627 R1/R2). A holds a
    # live lease on the shared digest; B's refuse-mode acquire must fail closed without mutating
    # A's authority -- no supersede, no registry byte change.
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    runtime.processes[4242] = (True, "start-4242")
    held = _refuse_acquire(broker_a, owner="runtime-a", resource="shared-leaf", owner_pid=4242)
    before = broker_a.registry_path.read_bytes()

    with pytest.raises(B.LeaseConflictError, match="runtime-a") as exc:
        _refuse_acquire(broker_b, owner="runtime-b", resource="shared-leaf")

    assert isinstance(exc.value, B.LeaseOwnershipError)  # broad handlers still catch it
    assert exc.value.holder_owner_id == "runtime-a"
    assert broker_a.registry_path.read_bytes() == before  # zero-mutation on refusal
    assert broker_a.verify(held.resource_ref, held.token).lease_id == held.lease_id


def test_refuse_mode_refuses_unknown_owner_pid_none(tmp_path: Path, runtime: FakeRuntime) -> None:
    # No owner_pid recorded -> _owner_state is "unknown" -> fail-closed refuse (R2). Only proof of
    # death admits; the absence of liveness evidence is never treated as death.
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    _refuse_acquire(broker_a, owner="runtime-a", resource="shared-leaf")  # owner_pid=None default
    before = broker_a.registry_path.read_bytes()

    with pytest.raises(B.LeaseConflictError, match="runtime-a") as exc:
        _refuse_acquire(broker_b, owner="runtime-b", resource="shared-leaf")

    assert exc.value.holder_owner_id == "runtime-a"
    assert broker_a.registry_path.read_bytes() == before


def test_refuse_mode_refuses_unreadable_owner_identity(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    # pid still alive but its process-start identity is now unreadable -> "unknown" -> refuse (R2).
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    runtime.processes[4242] = (True, "start-4242")
    _refuse_acquire(broker_a, owner="runtime-a", resource="shared-leaf", owner_pid=4242)
    runtime.processes[4242] = (True, None)  # alive, but identity unreadable
    before = broker_a.registry_path.read_bytes()

    with pytest.raises(B.LeaseConflictError, match="runtime-a"):
        _refuse_acquire(broker_b, owner="runtime-b", resource="shared-leaf")

    assert broker_a.registry_path.read_bytes() == before


def test_refuse_mode_refuses_same_owner_when_live(tmp_path: Path, runtime: FakeRuntime) -> None:
    # R3 / #627 KTD1: cross-runtime exclusion is the point -- a live holder refuses even when the
    # requester's owner_id matches (owner_id is deterministic per leaf, so this is the common case).
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    runtime.processes[4242] = (True, "start-4242")
    _refuse_acquire(broker_a, owner="runtime-a", resource="shared-leaf", owner_pid=4242)

    with pytest.raises(B.LeaseConflictError, match="runtime-a"):
        _refuse_acquire(broker_b, owner="runtime-a", resource="shared-leaf")


def test_refuse_mode_admits_crash_orphan_without_ttl_wait(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    # A SIGKILL skips the finally-release, so the orphaned lease is still unexpired (no TTL elapsed).
    # #637: refuse mode probes owner liveness -- a provably dead pid admits re-dispatch of the same
    # leaf immediately, matching supersede-mode behavior, instead of self-refusing for the full TTL.
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    runtime.processes[4242] = (True, "start-4242")
    held = _refuse_acquire(broker_a, owner="runtime-a", resource="shared-leaf", owner_pid=4242)
    runtime.processes[4242] = (False, None)  # holder crashed; pid gone, no time advanced

    reclaimed = _refuse_acquire(broker_b, owner="runtime-b", resource="shared-leaf")

    assert broker_b.verify(reclaimed.resource_ref, reclaimed.token).lease_id == reclaimed.lease_id
    assert len(broker_b.inspect()["leases"]) == 1  # dead prior superseded, not accumulated
    assert broker_b.classify_token(held.resource_ref, held.token) == "superseded"


@pytest.mark.parametrize("death_shape", ["crash-orphan", "stale-boot-id", "reused-pid"])
def test_refuse_mode_admits_every_death_shape_without_ttl_wait(
    tmp_path: Path, runtime: FakeRuntime, death_shape: str
) -> None:
    # All three shapes _owner_state calls dead must supersede with zero TTL elapsed: the pid is
    # gone, the machine rebooted, or the pid was recycled onto a different process start.
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    runtime.processes[4242] = (True, "start-4242")
    _refuse_acquire(broker_a, owner="runtime-a", resource="shared-leaf", owner_pid=4242)
    if death_shape == "crash-orphan":
        runtime.processes[4242] = (False, None)
    elif death_shape == "stale-boot-id":
        runtime.boot = "boot-b"
    else:
        runtime.processes[4242] = (True, "start-9999")  # pid recycled onto another process

    reclaimed = _refuse_acquire(broker_b, owner="runtime-b", resource="shared-leaf")

    assert broker_b.verify(reclaimed.resource_ref, reclaimed.token).lease_id == reclaimed.lease_id
    assert len(broker_b.inspect()["leases"]) == 1


def test_refuse_mode_reclaims_expired_prior(tmp_path: Path, runtime: FakeRuntime) -> None:
    # An expired prior is not a live conflict -- the TTL + boot-id check precedes the liveness probe,
    # so refuse mode reclaims exactly as supersede does (R1). This is the arm a one-part reading of
    # the guard (only _owner_state) silently drops: the owner pid here is provably LIVE.
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    runtime.processes[4242] = (True, "start-4242")
    _refuse_acquire(broker_a, owner="runtime-a", resource="shared-leaf", ttl=60, owner_pid=4242)
    runtime.advance(120)  # past the prior lease TTL -> _expired is True while the owner still lives

    reclaimed = _refuse_acquire(broker_b, owner="runtime-b", resource="shared-leaf")

    assert broker_b.verify(reclaimed.resource_ref, reclaimed.token).lease_id == reclaimed.lease_id
    assert len(broker_b.inspect()["leases"]) == 1


def test_refuse_mode_supersedes_when_fence_survives_but_lease_is_absent(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    # prior_lease is None: the released lease left its fence behind with no close receipt. There is
    # no holder to protect, so refuse mode falls through to supersede rather than refusing.
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    held = _refuse_acquire(broker_a, owner="runtime-a", resource="shared-leaf")
    assert broker_a.release(held.lease_id, token=held.token) is True
    digest = B.resource_sha256(held.resource_ref)
    fences = broker_a.inspect()["resource_fences"]
    assert digest in fences and fences[digest]["close_receipt"] is None
    assert not broker_a.inspect()["leases"]

    reclaimed = _refuse_acquire(broker_b, owner="runtime-b", resource="shared-leaf")

    assert broker_b.verify(reclaimed.resource_ref, reclaimed.token).lease_id == reclaimed.lease_id


def test_refuse_mode_stays_below_the_retained_settlement_precedence(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    # R5b precedence: a retained settlement raises LeaseOwnershipError -- NOT LeaseConflictError --
    # even under refuse mode against a live holder. The settlement gate must keep firing first.
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    runtime.processes[4242] = (True, "start-4242")
    held = _refuse_acquire(broker_a, owner="runtime-a", resource="shared-leaf", owner_pid=4242)
    broker_a.prepare_agent_settlement(
        held.lease_id,
        owner_id=held.owner_id,
        token=held.token,
        producer="saga",
        run_id="refuse-precedence",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )

    with pytest.raises(B.LeaseOwnershipError, match="retained settlement authority") as exc:
        _refuse_acquire(broker_b, owner="runtime-b", resource="shared-leaf")

    assert not isinstance(exc.value, B.LeaseConflictError)


def test_refuse_mode_stays_below_the_canonically_closed_precedence(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    # R5b precedence: a canonically closed resource whose lease is gone from the registry demands
    # acquire_successor with the predecessor receipt, ahead of any refuse-branch evaluation.
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    held = _refuse_acquire(broker_a, owner="runtime-a", resource="shared-leaf")
    settlement = broker_a.prepare_agent_settlement(
        held.lease_id,
        owner_id=held.owner_id,
        token=held.token,
        producer="saga",
        run_id="closed-precedence",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )
    broker_a.commit_agent_settlement(
        settlement.settlement_id,
        owner_id=held.owner_id,
        token=held.token,
        write=lambda _lease: ["evidence"],
    )

    with pytest.raises(B.LeaseOwnershipError, match="acquire_successor") as exc:
        _refuse_acquire(broker_b, owner="runtime-b", resource="shared-leaf")

    assert not isinstance(exc.value, B.LeaseConflictError)


def test_default_mode_still_supersedes_a_live_prior(tmp_path: Path, runtime: FakeRuntime) -> None:
    # Characterization: untouched callers pass no on_conflict and keep the #356 retry-supersede
    # design, including against a provably live holder. Must pass before AND after the port.
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    runtime.processes[4242] = (True, "start-4242")
    held = broker_a.acquire_agent(
        owner_id="runtime-a",
        session_id="session",
        policy_sha256=_limits().policy_sha256(),
        session_limit=_limits().max_concurrent,
        aggregate_limit=_limits().aggregate_max_concurrent,
        mutation="none",
        resource_ref={"logical_unit_id": "shared-leaf"},
        agent_type="worker",
        owner_pid=4242,
    )

    superseding = broker_b.acquire_agent(
        owner_id="runtime-b",
        session_id="session",
        policy_sha256=_limits().policy_sha256(),
        session_limit=_limits().max_concurrent,
        aggregate_limit=_limits().aggregate_max_concurrent,
        mutation="none",
        resource_ref={"logical_unit_id": "shared-leaf"},
        agent_type="worker",
    )

    assert broker_b.classify_token(held.resource_ref, held.token) == "superseded"
    assert broker_b.verify(superseding.resource_ref, superseding.token).lease_id
    assert len(broker_b.inspect()["leases"]) == 1


def test_explicit_supersede_matches_the_default_and_is_the_declared_default(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    # The parameter's default is "supersede", so every existing call site needs no edit, and passing
    # it explicitly reproduces the default path byte-for-byte in behavior.
    assert (
        inspect.signature(B.LeaseBroker.acquire_agent).parameters["on_conflict"].default
        == "supersede"
    )
    root = tmp_path / "authority"
    broker_a = B.LeaseBroker(root, providers=runtime.providers())
    broker_b = B.LeaseBroker(root, providers=runtime.providers())
    runtime.processes[4242] = (True, "start-4242")
    held = _refuse_acquire(broker_a, owner="runtime-a", resource="shared-leaf", owner_pid=4242)

    superseding = broker_b.acquire_agent(
        owner_id="runtime-b",
        session_id="session",
        policy_sha256=_limits().policy_sha256(),
        session_limit=_limits().max_concurrent,
        aggregate_limit=_limits().aggregate_max_concurrent,
        mutation="none",
        resource_ref={"logical_unit_id": "shared-leaf"},
        agent_type="worker",
        on_conflict="supersede",
    )

    assert broker_b.classify_token(held.resource_ref, held.token) == "superseded"
    assert broker_b.verify(superseding.resource_ref, superseding.token).lease_id
    assert len(broker_b.inspect()["leases"]) == 1


@pytest.mark.parametrize("value", ["explode", "", None, "Refuse", "SUPERSEDE"])
def test_acquire_agent_rejects_unknown_on_conflict(broker: Any, value: Any) -> None:
    # Closed-value check at the public boundary. None and "" must be rejected too: admitting either
    # would fail OPEN into supersede, the worst direction on a fail-closed admission path.
    with pytest.raises(B.LeaseBrokerError, match="on_conflict"):
        broker.acquire_agent(
            owner_id="owner",
            session_id="session",
            policy_sha256=_limits().policy_sha256(),
            session_limit=_limits().max_concurrent,
            aggregate_limit=_limits().aggregate_max_concurrent,
            mutation="none",
            resource_ref={"logical_unit_id": "x"},
            agent_type="worker",
            on_conflict=value,  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# U1 — tolerance primitives and capacity constants (#54, port of claude #617)
# ---------------------------------------------------------------------------

_U1_KEYS = frozenset({"alpha", "beta"})


def test_tolerant_mapping_splits_known_from_extras_disjointly() -> None:
    known, extras = B._tolerant_mapping({"alpha": 1, "beta": 2, "gamma": 3}, _U1_KEYS, "sample")

    assert known == {"alpha": 1, "beta": 2}
    assert extras == {"gamma": 3}
    # Disjointness is what makes the merge-last ``to_dict`` safe: a key in both would let an extra
    # silently overwrite a validated field.
    assert not (set(known) & set(extras))


def test_tolerant_mapping_keeps_the_strict_missing_field_error_verbatim() -> None:
    # R5: only *additive* keys are tolerated. A missing required key must still fail closed with
    # byte-identical wording, so existing operator runbooks and log greps keep working.
    with pytest.raises(B.RegistryCorruptError) as tolerant:
        B._tolerant_mapping({"alpha": 1}, _U1_KEYS, "sample")
    with pytest.raises(B.RegistryCorruptError) as strict:
        B._closed_mapping({"alpha": 1}, _U1_KEYS, "sample")

    assert str(tolerant.value) == "sample: missing field(s): beta"
    assert str(tolerant.value) == str(strict.value)


@pytest.mark.parametrize("value", [None, [], "alpha", 7, ()])
def test_tolerant_mapping_rejects_a_non_object(value: Any) -> None:
    with pytest.raises(B.RegistryCorruptError, match="sample must be an object"):
        B._tolerant_mapping(value, _U1_KEYS, "sample")


def test_extras_serialized_size_is_zero_for_empty_and_canonical_utf8_otherwise() -> None:
    assert B._extras_serialized_size({}) == 0

    extras = {"isolation": "worktree", "unicode": "é"}
    expected = len(B._canonical_json(extras).encode("utf-8"))

    assert B._extras_serialized_size(extras) == expected
    # ``_canonical_json`` sets ensure_ascii=True, so a non-ASCII value is counted as its escaped
    # form and the measurement is encoding-independent. Pin that: if canonicalization ever switches
    # to ensure_ascii=False, the same payload would suddenly measure smaller and the cap would
    # admit more than it was sized for.
    assert "\\u00e9" in B._canonical_json(extras)
    assert expected == len(B._canonical_json(extras))


def test_extras_serialized_size_measures_the_canonical_form_not_the_input() -> None:
    # Key order must not change the measurement, or the cap would be non-deterministic across
    # writers that emit the same fields in a different order.
    assert B._extras_serialized_size({"b": 1, "a": 2}) == B._extras_serialized_size(
        {"a": 2, "b": 1}
    )


def test_archived_fence_bound_is_a_strict_multiple_of_the_document_bound() -> None:
    # KTD4: archived sidecars bypass the document-total cap, so they carry their own larger bound.
    # A future edit that equalizes the two would silently remove the sidecar's headroom.
    assert B._MAX_EXTRAS_BYTES == 64 * 1024
    assert B._MAX_ARCHIVED_FENCE_BYTES == 4 * B._MAX_EXTRAS_BYTES
    assert B._MAX_ARCHIVED_FENCE_BYTES > B._MAX_EXTRAS_BYTES


# ---------------------------------------------------------------------------
# U2 — extras on the six record types (#54, port of claude #617)
# ---------------------------------------------------------------------------


def _persist_raw(broker: Any, raw: dict[str, Any]) -> None:
    """Write a hand-edited registry document back under the authority's 0600 requirement."""

    broker.registry_path.write_text(json.dumps(raw), encoding="utf-8")
    os.chmod(broker.registry_path, 0o600)


def _settled_fence_digest(broker: Any, *, resource: str) -> str:
    """Drive one lease through prepare + commit and return its resource digest."""

    lease = _agent(broker, resource=resource)
    settlement = broker.prepare_agent_settlement(
        lease.lease_id,
        owner_id=lease.owner_id,
        token=lease.token,
        producer="saga",
        run_id=f"run-{resource}",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )
    broker.commit_agent_settlement(
        settlement.settlement_id,
        owner_id=lease.owner_id,
        token=lease.token,
        write=lambda _lease: ["evidence"],
    )
    return cast(str, B.resource_sha256(lease.resource_ref))


@pytest.mark.parametrize("unknown_key", ["isolation", "field_no_runtime_has_yet"])
def test_lease_extras_round_trip_byte_identically(broker: Any, unknown_key: str) -> None:
    # R1/R2/R3. ``isolation`` is merely the first field to exercise the contract; the synthetic key
    # present in NEITHER runtime is the genericity proof. A reader that special-cased ``isolation``
    # would pass the first parameter and fail the second.
    lease = _agent(broker, resource="unit-extras")
    raw = _raw_registry(broker)
    raw["leases"][lease.lease_id][unknown_key] = {"nested": ["value", 1, None]}
    _persist_raw(broker, raw)

    assert broker.inspect()["leases"][0]["lease_id"] == lease.lease_id
    assert broker.renew(lease.lease_id, token=lease.token)
    assert _raw_registry(broker)["leases"][lease.lease_id][unknown_key] == {
        "nested": ["value", 1, None]
    }


def test_settlement_record_extras_round_trip(broker: Any) -> None:
    lease = _agent(broker, resource="unit-settlement-extras")
    settlement = broker.prepare_agent_settlement(
        lease.lease_id,
        owner_id=lease.owner_id,
        token=lease.token,
        producer="saga",
        run_id="run-settlement-extras",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )
    digest = B.resource_sha256(lease.resource_ref)
    raw = _raw_registry(broker)
    raw["settlements"][digest]["future_field"] = "preserved"
    _persist_raw(broker, raw)

    broker.inspect()
    broker.commit_agent_settlement(
        settlement.settlement_id,
        owner_id=lease.owner_id,
        token=lease.token,
        write=lambda _lease: ["evidence"],
    )
    # The settlement is consumed by the commit, so the surviving proof is that the tolerant read
    # accepted it at all — a strict read would have raised before the commit could run.
    assert digest not in _raw_registry(broker)["settlements"]


def test_resource_fence_extras_round_trip(broker: Any) -> None:
    lease = _agent(broker, resource="unit-fence-extras")
    digest = B.resource_sha256(lease.resource_ref)
    raw = _raw_registry(broker)
    raw["resource_fences"][digest]["future_field"] = {"kept": True}
    _persist_raw(broker, raw)

    assert broker.inspect()["leases"][0]["lease_id"] == lease.lease_id
    assert broker.renew(lease.lease_id, token=lease.token)
    assert _raw_registry(broker)["resource_fences"][digest]["future_field"] == {"kept": True}


def test_session_admission_extras_round_trip(broker: Any) -> None:
    limits = _limits()
    broker.configure_session_admission(
        "session",
        policy_sha256=limits.policy_sha256(),
        session_limit=limits.max_concurrent,
        aggregate_limit=limits.aggregate_max_concurrent,
        mutation="read-write",
    )
    lease = _agent(broker, resource="unit-admission-extras")
    raw = _raw_registry(broker)
    raw["session_admissions"]["session"]["future_field"] = 7
    _persist_raw(broker, raw)

    assert broker.get_session_admission("session") is not None
    assert broker.renew(lease.lease_id, token=lease.token)
    assert _raw_registry(broker)["session_admissions"]["session"]["future_field"] == 7


def test_closed_owner_admission_extras_round_trip(broker: Any) -> None:
    lease = _agent(broker, owner="closing-owner", resource="unit-owner-extras")
    broker.close_owner_admission(owner_id="closing-owner")
    raw = _raw_registry(broker)
    raw["closed_owner_admissions"]["closing-owner"]["future_field"] = "kept"
    _persist_raw(broker, raw)

    assert broker.inspect_owner_admission("closing-owner") is not None
    assert broker.release(lease.lease_id, token=lease.token) is True
    assert (
        _raw_registry(broker)["closed_owner_admissions"]["closing-owner"]["future_field"] == "kept"
    )


def test_registry_top_level_extras_round_trip(broker: Any) -> None:
    lease = _agent(broker, resource="unit-top-extras")
    raw = _raw_registry(broker)
    raw["future_top_level"] = {"schema": "someone-elses.v9"}
    _persist_raw(broker, raw)

    assert broker.inspect()["leases"][0]["lease_id"] == lease.lease_id
    assert broker.release(lease.lease_id, token=lease.token) is True
    assert _raw_registry(broker)["future_top_level"] == {"schema": "someone-elses.v9"}


def test_extras_free_document_is_byte_identical_across_a_read_write_cycle(broker: Any) -> None:
    # R8 golden pin. With no extras anywhere, ``result.update({})`` is a no-op and the serialized
    # document must be byte-for-byte what a pre-port broker produced.
    lease = _agent(broker, resource="unit-golden")
    broker.configure_session_admission(
        "session",
        policy_sha256=_limits().policy_sha256(),
        session_limit=_limits().max_concurrent,
        aggregate_limit=_limits().aggregate_max_concurrent,
        mutation="read-write",
    )
    before = broker.registry_path.read_bytes()

    parsed = B.Registry.from_dict(json.loads(before.decode("utf-8")))
    assert parsed.extras == {}
    assert all(item.extras == {} for item in parsed.leases.values())
    assert all(f.extras == {} for f in parsed.resource_fences.values())
    assert all(a.extras == {} for a in parsed.session_admissions.values())

    # Re-serializing the parsed document reproduces the on-disk bytes exactly.
    assert json.dumps(parsed.to_dict(), sort_keys=True) == json.dumps(
        json.loads(before.decode("utf-8")), sort_keys=True
    )
    assert broker.renew(lease.lease_id, token=lease.token)


@pytest.mark.parametrize(
    ("container", "key_of"),
    [
        ("leases", "lease"),
        ("resource_fences", "digest"),
        ("session_admissions", "session"),
        ("closed_owner_admissions", "owner"),
    ],
)
def test_missing_required_key_still_fails_closed_at_every_converted_site(
    broker: Any, container: str, key_of: str
) -> None:
    # R5. Tolerance is additive-only: dropping a REQUIRED key must still brick the read, or a
    # truncated document would parse as valid with silently-defaulted fields.
    lease = _agent(broker, owner="closing-owner", resource="unit-missing")
    broker.configure_session_admission(
        "session",
        policy_sha256=_limits().policy_sha256(),
        session_limit=_limits().max_concurrent,
        aggregate_limit=_limits().aggregate_max_concurrent,
        mutation="read-write",
    )
    broker.close_owner_admission(owner_id="closing-owner")
    raw = _raw_registry(broker)
    key = {
        "lease": lease.lease_id,
        "digest": B.resource_sha256(lease.resource_ref),
        "session": "session",
        "owner": "closing-owner",
    }[key_of]
    record = raw[container][key]
    record.pop(sorted(record)[0])
    _persist_raw(broker, raw)

    with pytest.raises(B.RegistryCorruptError, match="missing field"):
        broker.inspect()


def test_registry_missing_required_top_level_key_still_fails_closed(broker: Any) -> None:
    _agent(broker, resource="unit-missing-top")
    raw = _raw_registry(broker)
    del raw["next_fencing_sequence"]
    _persist_raw(broker, raw)

    with pytest.raises(B.RegistryCorruptError, match="missing field"):
        broker.inspect()


def test_strict_worktree_resource_ref_still_rejects_unknown_keys(tmp_path: Path) -> None:
    # R6, boundary 1 of 5 — hash-bound: an unknown byte here changes ``resource_sha256``.
    with pytest.raises(B.RegistryCorruptError, match="unknown field"):
        B.canonical_resource_ref("worktree", {**_worktree_resource(tmp_path), "surprise": True})


def test_strict_settlement_close_still_rejects_unknown_keys(broker: Any) -> None:
    # R6, boundary 2 of 5 — digest-covered commitment record.
    digest = _settled_fence_digest(broker, resource="unit-strict-close")
    raw = _raw_registry(broker)
    assert raw["resource_fences"][digest]["close_receipt"] is not None
    raw["resource_fences"][digest]["close_receipt"]["surprise"] = True
    _persist_raw(broker, raw)

    with pytest.raises(B.RegistryCorruptError, match="unknown field"):
        broker.inspect()


def test_strict_legacy_settlement_close_still_rejects_unknown_keys(broker: Any) -> None:
    # R6, boundary 3 of 5 — the legacy digest-covered close shape.
    digest = _settled_fence_digest(broker, resource="unit-strict-legacy")
    raw = _raw_registry(broker)
    current = raw["resource_fences"][digest]["close_receipt"]
    legacy = {
        key: value
        for key, value in current.items()
        if key
        not in {
            "settlement_id",
            "session_id",
            "policy_sha256",
            "protected_write_intent_sha256",
            "settlement_sha256",
            "receipt_sha256",
            "sha256",
        }
    }
    legacy["receipt_sha256"] = B._record_sha256(legacy)
    legacy["sha256"] = B._record_sha256(legacy)
    legacy["surprise"] = True
    raw["resource_fences"][digest]["close_receipt"] = legacy
    _persist_raw(broker, raw)

    with pytest.raises(B.RegistryCorruptError, match="unknown field"):
        broker.inspect()


def test_strict_settlement_recovery_intent_still_rejects_unknown_keys(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    # R6, boundary 4 of 5 — the recovery intent is a sha256-bound capability, not a container.
    runtime.processes[os.getpid()] = (True, "root-process")
    broker = B.LeaseBroker(tmp_path / "authority", providers=runtime.providers())
    coordinator = B._open_settlement_recovery_coordinator(broker, recovery_owner_id="root-adapter")
    lease = _agent(broker, resource="unit-strict-recovery")
    settlement = broker.prepare_agent_settlement(
        lease.lease_id,
        owner_id=lease.owner_id,
        token=lease.token,
        producer="saga",
        run_id="run-strict-recovery",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )
    intent = _recovery_intent(settlement, runtime=runtime, expected_phase="prepared")
    intent["surprise"] = True

    with pytest.raises(B.RegistryCorruptError, match="unknown field"):
        coordinator.recover_agent_settlement(intent, action="commit")


def test_strict_fencing_token_shape_is_pinned_at_every_embedding_site(
    tmp_path: Path, runtime: FakeRuntime
) -> None:
    # R6, boundary 5 of 5. ``FencingToken.from_dict`` reads with ``.get()`` and does NOT itself
    # reject unknown keys — the exact {broker_epoch, fencing_sequence} shape is pinned by an inline
    # check at each EMBEDDING site instead. An audit that only swept ``_closed_mapping`` call sites
    # would miss this boundary entirely, so assert it where it is actually enforced.
    assert B.FencingToken.from_dict(
        {"broker_epoch": str(uuid.UUID(int=1)), "fencing_sequence": 1, "surprise": True}
    ) == B.FencingToken(str(uuid.UUID(int=1)), 1)

    # Site 1 — the settlement record's embedded token.
    broker = B.LeaseBroker(tmp_path / "authority", providers=runtime.providers())
    lease = _agent(broker, resource="unit-token-shape")
    broker.prepare_agent_settlement(
        lease.lease_id,
        owner_id=lease.owner_id,
        token=lease.token,
        producer="saga",
        run_id="run-token-shape",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )
    digest = B.resource_sha256(lease.resource_ref)
    raw = _raw_registry(broker)
    raw["settlements"][digest]["token"]["surprise"] = True
    _persist_raw(broker, raw)
    with pytest.raises(B.RegistryCorruptError, match="closed token shape"):
        broker.inspect()

    # Site 2 — the recovery intent's embedded token.
    runtime.processes[os.getpid()] = (True, "root-process")
    clean = B.LeaseBroker(tmp_path / "authority-b", providers=runtime.providers())
    coordinator = B._open_settlement_recovery_coordinator(clean, recovery_owner_id="root-adapter")
    other = _agent(clean, resource="unit-token-shape-b")
    settlement = clean.prepare_agent_settlement(
        other.lease_id,
        owner_id=other.owner_id,
        token=other.token,
        producer="saga",
        run_id="run-token-shape-b",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )
    intent = _recovery_intent(settlement, runtime=runtime, expected_phase="prepared")
    intent["token"]["surprise"] = True
    intent["sha256"] = B._record_sha256(intent, "sha256")
    with pytest.raises(B.LeaseBrokerError, match="token shape is invalid"):
        coordinator.recover_agent_settlement(intent, action="commit")


def test_document_extras_over_capacity_fails_closed_and_just_under_loads(broker: Any) -> None:
    # R4/KTD5. Over-capacity must raise a typed error rather than truncate: a truncating reader
    # would silently drop a newer writer's fields and then write the loss back to disk.
    lease = _agent(broker, resource="unit-capacity")
    raw = _raw_registry(broker)
    raw["leases"][lease.lease_id]["bulk"] = "x" * (B._MAX_EXTRAS_BYTES - 64)
    _persist_raw(broker, raw)
    assert broker.inspect()["leases"][0]["lease_id"] == lease.lease_id

    raw = _raw_registry(broker)
    raw["leases"][lease.lease_id]["bulk"] = "x" * (B._MAX_EXTRAS_BYTES + 1)
    _persist_raw(broker, raw)
    with pytest.raises(B.RegistryCorruptError, match="bounded tolerance capacity"):
        broker.inspect()


def test_document_extras_capacity_is_summed_across_records_not_per_record(broker: Any) -> None:
    # The cap is a DOCUMENT total. Two records each individually under the bound must still trip it
    # together, or the limit would be trivially bypassed by spreading a payload across records.
    first = _agent(broker, resource="unit-capacity-a")
    second = _agent(broker, owner="owner-b", session="session-b", resource="unit-capacity-b")
    half = "x" * (B._MAX_EXTRAS_BYTES // 2)
    raw = _raw_registry(broker)
    raw["leases"][first.lease_id]["bulk"] = half
    raw["leases"][second.lease_id]["bulk"] = half
    _persist_raw(broker, raw)

    with pytest.raises(B.RegistryCorruptError, match="bounded tolerance capacity"):
        broker.inspect()


# ---------------------------------------------------------------------------
# U3 — settlement and archive commit path (#54, port of claude #617)
# ---------------------------------------------------------------------------


def _archive_head(broker: Any, digest: str) -> None:
    """Move one closed fence to its sidecar file.

    ``_compact_closed_fences`` only spills past ``_MAX_CLOSED_FENCES`` (128), so driving the
    archive writer directly is what makes these assertions unconditional instead of skipped.
    """

    registry = B.Registry.from_dict(_raw_registry(broker))
    broker._archive_closed_fence(digest, registry.resource_fences[digest])


def test_fence_extras_survive_the_settlement_close_into_the_archive(broker: Any) -> None:
    # R7 — the unit's most important test. Codex shipped the pre-#617 rebuild form, which drops
    # per-fence extras at exactly the commit that archives the fence. Assert by reading the
    # ARCHIVED record back off disk, never by inspecting the in-memory object: the in-memory value
    # can look right while the persisted one has already lost the field.
    lease = _agent(broker, resource="unit-archive-extras")
    digest = B.resource_sha256(lease.resource_ref)
    raw = _raw_registry(broker)
    raw["resource_fences"][digest]["carried_forward"] = {"by": "a newer writer"}
    _persist_raw(broker, raw)

    settlement = broker.prepare_agent_settlement(
        lease.lease_id,
        owner_id=lease.owner_id,
        token=lease.token,
        producer="saga",
        run_id="run-archive-extras",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )
    broker.commit_agent_settlement(
        settlement.settlement_id,
        owner_id=lease.owner_id,
        token=lease.token,
        write=lambda _lease: ["evidence"],
    )

    live = _raw_registry(broker)["resource_fences"][digest]
    assert live["close_receipt"] is not None
    assert live["carried_forward"] == {"by": "a newer writer"}

    # And once the fence moves to the sidecar archive, the field is still there — read back off
    # disk through the real archive reader, not from memory.
    _archive_head(broker, digest)
    reread = broker._read_archived_fence(digest)
    assert reread is not None
    assert reread.close_receipt is not None
    assert reread.extras == {"carried_forward": {"by": "a newer writer"}}


def test_archived_fence_over_the_per_record_bound_fails_closed(broker: Any) -> None:
    # KTD4. Sidecars bypass Registry.from_dict's document-total cap, so without the per-record
    # bound the archive would be an uncapped extras channel.
    digest = _settled_fence_digest(broker, resource="unit-archive-bound")
    _archive_head(broker, digest)
    path = broker.closed_fences_dir / f"{digest}.json"
    assert path.exists()

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["bulk"] = "x" * (B._MAX_EXTRAS_BYTES + 1)
    path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(path, 0o600)

    with pytest.raises(B.RegistryCorruptError, match="bounded tolerance capacity"):
        broker._read_archived_fence(digest)


def test_archived_fence_payload_read_is_bounded_and_not_single_read_truncated(
    broker: Any, tmp_path: Path
) -> None:
    # The pre-port reader took ONE os.read(fd, 65536), so a sidecar larger than 64 KiB was
    # silently truncated into a JSON parse error rather than read to EOF. Pin both halves:
    # a large-but-legal payload reads whole, and an over-bound one raises the size error.
    legal = tmp_path / "legal.json"
    legal.write_text(json.dumps({"pad": "y" * 100_000}), encoding="utf-8")
    fd = os.open(legal, os.O_RDONLY)
    try:
        payload = B.LeaseBroker._read_bounded_archived_fence_payload(fd)
    finally:
        os.close(fd)
    assert len(payload["pad"]) == 100_000

    oversized = tmp_path / "oversized.json"
    oversized.write_text(json.dumps({"pad": "y" * (B._MAX_ARCHIVED_FENCE_BYTES + 1)}), "utf-8")
    fd = os.open(oversized, os.O_RDONLY)
    try:
        with pytest.raises(B.RegistryCorruptError, match="bounded archive record size"):
            B.LeaseBroker._read_bounded_archived_fence_payload(fd)
    finally:
        os.close(fd)


def test_settlement_close_still_rejects_a_lost_head_cas(broker: Any) -> None:
    # The existing invariant must be unregressed by the replace() change: the CAS guard runs
    # BEFORE the in-place close, so a superseded head still refuses.
    lease = _agent(broker, resource="unit-cas")
    settlement = broker.prepare_agent_settlement(
        lease.lease_id,
        owner_id=lease.owner_id,
        token=lease.token,
        producer="saga",
        run_id="run-cas",
        expected_output_sha256="b" * 64,
        protected_write_intent_sha256="c" * 64,
    )
    digest = B.resource_sha256(lease.resource_ref)
    raw = _raw_registry(broker)
    raw["resource_fences"][digest]["fencing_sequence"] = 9999
    raw["settlements"].pop(digest, None)
    raw["next_fencing_sequence"] = 10000
    _persist_raw(broker, raw)

    with pytest.raises(B.LeaseBrokerError):
        broker.commit_agent_settlement(
            settlement.settlement_id,
            owner_id=lease.owner_id,
            token=lease.token,
            write=lambda _lease: ["evidence"],
        )


# ---------------------------------------------------------------------------
# U5 — the isolation non-port, pinned as a named guard (#54 KTD5)
# ---------------------------------------------------------------------------


def test_isolation_is_not_ported_ktd5() -> None:
    """R9: codex must not learn claude-specific lease semantics.

    Forward-compatibility is the contract; ``isolation`` (claude#616) is merely the first field to
    exercise it. A reader that special-cased it would defer the identical failure to the next field
    claude adds, so the exclusion is pinned by name rather than left to prose. Following the
    precedent in DECISIONS `2026-07-19: Cross-Runtime Parity Port` KTD6
    (`test_dispatcher_lease_seam_stays_dormant_ktd6`): teaching codex the field then requires
    deleting a named test with a written rationale, not silent drift.
    """

    authority = BROKER_PATH.read_text(encoding="utf-8")
    adapter = ROOT / "plugins" / "saga" / "scripts" / "lease_broker.py"

    assert "isolation" not in authority
    assert "isolation" not in adapter.read_text(encoding="utf-8")


def test_tolerance_names_no_runtime_specific_field() -> None:
    """The genericity claim, stated as an absence rather than inferred from a passing test.

    ``_tolerant_mapping`` partitions on set membership alone, so no field name can be privileged.
    """

    authority = BROKER_PATH.read_text(encoding="utf-8")

    for literal in ('"claude"', "'claude'", '"codex"', "'codex'", "RUNTIME_LABEL"):
        assert literal not in authority
