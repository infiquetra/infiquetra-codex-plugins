"""Contract tests for the saga-side lease broker adapter (#33 U3, ported from #356).

No source test exercises the adapter directly (verified at cf15a09f) — this suite is authored
for the Codex port: it pins the adapter's protocol gate, admission normalization, and the
worktree receipt round-trip against the U2-ported fleet-core authority.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
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


# ---------------------------------------------------------------------------
# U4 — operator surface CLI harness (#54, port of claude #617)
#
# This module had NO CLI-invocation harness before this unit (zero references to main/argv/
# SystemExit/capsys); the helpers below are that harness, following tests/test_capability_degrade.py.
# ---------------------------------------------------------------------------


def _cli(
    monkeypatch: pytest.MonkeyPatch, state_root: Path, *argv: str
) -> tuple[int, dict[str, Any]]:
    """Run the adapter CLI against an isolated state root; return (exit_code, parsed stdout)."""

    monkeypatch.setenv(LB.STATE_ENV, str(state_root))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = LB.main(list(argv))
    printed = buffer.getvalue().strip()
    return code, (json.loads(printed) if printed else {})


def _seed_lease(state_root: Path) -> Any:
    """Create one live agent lease inside the CLI's own state root."""

    selected = LB.authority.LeaseBroker(environment={LB.STATE_ENV: str(state_root)})
    limits = LB.concurrency_policy.AdmissionLimits()
    return selected, selected.acquire_agent(
        owner_id="owner",
        session_id="session",
        policy_sha256=limits.policy_sha256(),
        session_limit=limits.max_concurrent,
        aggregate_limit=limits.aggregate_max_concurrent,
        mutation="read-write",
        resource_ref={"logical_unit_id": "cli-unit"},
        agent_type="worker",
    )


def _inject_unknown(selected: Any, lease_id: str, key: str, value: Any) -> None:
    raw = json.loads(selected.registry_path.read_text(encoding="utf-8"))
    raw["leases"][lease_id][key] = value
    selected.registry_path.write_text(json.dumps(raw), encoding="utf-8")
    os.chmod(selected.registry_path, 0o600)


def test_doctor_on_a_clean_registry_reports_valid_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_lease(tmp_path / "state")
    code, report = _cli(monkeypatch, tmp_path / "state", "doctor")

    assert code == 0
    assert report["status"] == "valid"
    assert report["extras"] == []
    assert report["extras_key_count"] == 0
    assert report["extras_bytes"] == 0


def test_doctor_reports_tolerated_unknowns_with_json_paths_and_exit_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected, lease = _seed_lease(tmp_path / "state")
    _inject_unknown(selected, lease.lease_id, "isolation", "worktree")
    code, report = _cli(monkeypatch, tmp_path / "state", "doctor")

    assert code == 3
    assert report["status"] == "tolerated-unknowns"
    assert report["extras"] == [{"path": f"$.leases.{lease.lease_id}", "keys": ["isolation"]}]
    assert report["extras_key_count"] == 1
    assert report["extras_bytes"] > 0


def test_doctor_reports_corrupt_as_data_with_exit_four_and_does_not_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected, lease = _seed_lease(tmp_path / "state")
    raw = json.loads(selected.registry_path.read_text(encoding="utf-8"))
    del raw["leases"][lease.lease_id]["ttl_seconds"]
    selected.registry_path.write_text(json.dumps(raw), encoding="utf-8")
    os.chmod(selected.registry_path, 0o600)

    # A diagnostic that aborts on the very state it exists to diagnose is useless; corrupt is
    # returned as data, never raised.
    code, report = _cli(monkeypatch, tmp_path / "state", "doctor")

    assert code == 4
    assert report["status"] == "corrupt"
    assert report["invariants"] == "failed"
    assert "missing field" in report["error"]


def test_an_unrecognized_doctor_status_maps_to_the_corrupt_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Fail-closed on the exit-code seam: a future status this mapping does not know must never
    # be reported to automation as clean.
    _seed_lease(tmp_path / "state")
    monkeypatch.setattr(
        LB.authority.LeaseBroker, "doctor", lambda self: {"status": "some-future-verdict"}
    )
    code, _report = _cli(monkeypatch, tmp_path / "state", "doctor")

    assert code == 4


def test_doctor_never_mutates_the_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    selected, lease = _seed_lease(tmp_path / "state")
    _inject_unknown(selected, lease.lease_id, "isolation", "worktree")
    before = selected.registry_path.read_bytes()

    _cli(monkeypatch, tmp_path / "state", "doctor")

    assert selected.registry_path.read_bytes() == before


def test_repair_without_the_explicit_flag_exits_nonzero_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected, lease = _seed_lease(tmp_path / "state")
    _inject_unknown(selected, lease.lease_id, "isolation", "worktree")
    before = selected.registry_path.read_bytes()

    monkeypatch.setenv(LB.STATE_ENV, str(tmp_path / "state"))
    with pytest.raises(SystemExit) as exc:
        LB.main(["repair"])

    assert exc.value.code != 0
    assert selected.registry_path.read_bytes() == before


def test_repair_strip_unknown_backs_up_then_clears_every_extras_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected, lease = _seed_lease(tmp_path / "state")
    _inject_unknown(selected, lease.lease_id, "isolation", "worktree")
    original = selected.registry_path.read_bytes()

    code, report = _cli(monkeypatch, tmp_path / "state", "repair", "--strip-unknown")

    assert code == 0
    assert report["status"] == "repaired"
    assert report["repaired"] is True
    assert report["stripped"] == [{"path": f"$.leases.{lease.lease_id}", "keys": ["isolation"]}]

    # The backup holds the pre-repair bytes, so the down-migration is reversible.
    backup = Path(report["backup"])
    assert backup.exists()
    assert backup.read_bytes() == original
    assert oct(backup.stat().st_mode & 0o777) == "0o600"

    # And the registry is now clean.
    follow_up_code, follow_up = _cli(monkeypatch, tmp_path / "state", "doctor")
    assert follow_up_code == 0
    assert follow_up["status"] == "valid"


def test_repair_on_a_clean_registry_is_an_explicit_no_op(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected, _lease = _seed_lease(tmp_path / "state")
    before = selected.registry_path.read_bytes()

    code, report = _cli(monkeypatch, tmp_path / "state", "repair", "--strip-unknown")

    assert code == 0
    assert report["status"] == "clean"
    assert report["repaired"] is False
    assert report["stripped"] == []
    assert selected.registry_path.read_bytes() == before


def test_repair_refuses_a_document_corrupt_beyond_unknown_field_stripping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected, lease = _seed_lease(tmp_path / "state")
    raw = json.loads(selected.registry_path.read_text(encoding="utf-8"))
    del raw["leases"][lease.lease_id]["ttl_seconds"]
    selected.registry_path.write_text(json.dumps(raw), encoding="utf-8")
    os.chmod(selected.registry_path, 0o600)
    before = selected.registry_path.read_bytes()

    code, report = _cli(monkeypatch, tmp_path / "state", "repair", "--strip-unknown")

    assert code == 0
    assert report["status"] == "refused"
    assert report["repaired"] is False
    assert selected.registry_path.read_bytes() == before
