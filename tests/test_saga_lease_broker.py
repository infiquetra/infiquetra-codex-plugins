"""Contract tests for the saga-side lease broker adapter (#33 U3, ported from #356).

No source test exercises the adapter directly (verified at cf15a09f) — this suite is authored
for the Codex port: it pins the adapter's protocol gate, admission normalization, and the
worktree receipt round-trip against the U2-ported fleet-core authority.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "plugins" / "saga" / "scripts"


def _load(name: str, alias: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(alias, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


LB = _load("lease_broker", "saga_lease_broker_under_test")


def _selected(tmp_path: Path) -> Any:
    return LB.authority.LeaseBroker(tmp_path / "authority")


def test_protocol_gate_matches_ported_fleet_core() -> None:
    assert LB.REQUIRED_PROTOCOL_VERSION == 2
    assert LB.authority.PROTOCOL_VERSION == 2
    LB.ensure_protocol()


def test_protocol_skew_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(LB.authority, "PROTOCOL_VERSION", 1)
    with pytest.raises(LB.HookInputError, match="install/update fleet-core"):
        LB.ensure_protocol()


def test_admission_snapshot_defaults_mirror_fleet_policy() -> None:
    defaults = LB.concurrency_policy.AdmissionLimits()

    policy_sha256, session_limit, aggregate_limit, mutation = LB.admission_snapshot({})

    assert policy_sha256 == defaults.policy_sha256()
    assert session_limit == defaults.max_concurrent
    assert aggregate_limit == defaults.aggregate_max_concurrent
    assert mutation == "read-write"


def test_admission_snapshot_env_overrides_and_rejections() -> None:
    values = LB.admission_snapshot(
        {
            LB.SESSION_LIMIT_ENV: "2",
            LB.AGGREGATE_LIMIT_ENV: "5",
            LB.POLICY_SHA256_ENV: "f" * 64,
            LB.MUTATION_ENV: "none",
        }
    )
    assert values == ("f" * 64, 2, 5, "none")

    with pytest.raises(LB.HookInputError, match="must not exceed"):
        LB.admission_snapshot({LB.SESSION_LIMIT_ENV: "9", LB.AGGREGATE_LIMIT_ENV: "5"})
    with pytest.raises(LB.HookInputError, match="read-write or none"):
        LB.admission_snapshot({LB.MUTATION_ENV: "read-only"})
    for malformed in ("0", "03", "x", "-1"):
        with pytest.raises(LB.HookInputError, match="canonical positive integer"):
            LB.admission_snapshot({LB.SESSION_LIMIT_ENV: malformed})


def test_broker_resolves_state_root_from_environment(tmp_path: Path) -> None:
    state_root = tmp_path / "fleet-state"

    selected = LB.broker({LB.STATE_ENV: str(state_root)})

    assert selected.inspect()["leases"] == []
    assert selected.root == Path(str(state_root))
    assert ".claude" not in str(selected.root) and ".codex" not in str(selected.root)


def test_worktree_resource_is_canonical_and_stable(tmp_path: Path) -> None:
    first = LB.worktree_resource(tmp_path, "ship-x", "build")
    second = LB.worktree_resource(tmp_path, "ship-x", "build")

    assert first == second
    assert first["repo_root"] == str(tmp_path.resolve())
    assert first["outcome_id"] == "ship-x"
    assert first["subplot_id"] == "build"


def test_acquire_worktree_receipt_round_trip(tmp_path: Path) -> None:
    selected = _selected(tmp_path)
    lease = LB.acquire_outcome_worktree(
        repo_root=tmp_path / "repo",
        outcome_id="ship-x",
        subplot_id="build",
        owner_id="coordinator-1",
        session_id="outcome:ship-x",
        selected=selected,
    )

    receipt = LB.worktree_lease_receipt(lease, selected)
    assert set(receipt) == {"lease_id", "token", "root_sha256"}
    assert receipt["root_sha256"] == selected.root_sha256

    lease_id, token = LB.parse_worktree_lease_receipt(receipt, selected)
    assert lease_id == lease.lease_id
    assert token.to_dict() == lease.token.to_dict()


def test_parse_receipt_rejects_foreign_or_malformed_bindings(tmp_path: Path) -> None:
    selected = _selected(tmp_path)
    lease = LB.acquire_outcome_worktree(
        repo_root=tmp_path / "repo",
        outcome_id="ship-x",
        subplot_id="build",
        owner_id="coordinator-1",
        session_id="outcome:ship-x",
        selected=selected,
    )
    receipt = LB.worktree_lease_receipt(lease, selected)

    with pytest.raises(LB.HookInputError, match="exactly lease_id, token, and root_sha256"):
        LB.parse_worktree_lease_receipt({"lease_id": lease.lease_id}, selected)
    foreign = dict(receipt, root_sha256="0" * 64)
    with pytest.raises(LB.HookInputError, match="different authority root"):
        LB.parse_worktree_lease_receipt(foreign, selected)
    tampered = dict(receipt, token={"broker_epoch": "bad"})
    with pytest.raises(LB.HookInputError, match="token is invalid"):
        LB.parse_worktree_lease_receipt(tampered, selected)


def test_session_admission_requires_configuration_or_complete_environment(
    tmp_path: Path,
) -> None:
    selected = _selected(tmp_path)

    with pytest.raises(LB.HookInputError, match="lease preflight before spawning"):
        LB.session_admission_snapshot("session-a", {}, selected=selected)

    explicit = {
        LB.SESSION_LIMIT_ENV: "2",
        LB.AGGREGATE_LIMIT_ENV: "5",
        LB.POLICY_SHA256_ENV: "f" * 64,
        LB.MUTATION_ENV: "none",
    }
    armed = LB.session_admission_snapshot("session-a", explicit, selected=selected)
    assert armed == ("f" * 64, 2, 5, "none")

    pinned = LB.session_admission_snapshot("session-a", {}, selected=selected)
    assert pinned == armed

    drifted = dict(explicit, INFIQUETRA_FLEET_SESSION_LIMIT="1")
    with pytest.raises(LB.HookInputError, match="differs from its configured admission snapshot"):
        LB.session_admission_snapshot("session-a", drifted, selected=selected)
