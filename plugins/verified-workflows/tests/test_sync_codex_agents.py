from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SYNC_PATH = PLUGIN_ROOT / "scripts" / "sync_codex_agents.py"


def _load_sync():
    name = "verified_workflows_u3_profile_sync"
    spec = importlib.util.spec_from_file_location(name, SYNC_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


S = _load_sync()


def _target(path: Path) -> object:
    return S.resolve_target(path.resolve(), isolated_target=True)


def _plan(path: Path, *, migrate: bool = False, remove_stale: bool = False):
    return S.build_plan(
        _target(path),
        catalog_snapshot=S.renderer.DEFAULT_CATALOG_SNAPSHOT,
        migrate_legacy=migrate,
        remove_stale=remove_stale,
    )


def _agent_text(name: str, marker: str | None = None) -> str:
    prefix = f"{marker}\n" if marker else ""
    return (
        prefix
        + f'name = "{name}"\n'
        + 'description = "test profile"\n'
        + 'developer_instructions = "test"\n'
    )


def test_target_resolution_precedence_and_real_profile_detection(tmp_path: Path) -> None:
    explicit = (tmp_path / "explicit").resolve()
    codex_home = (tmp_path / "codex-home").resolve()
    home = (tmp_path / "home").resolve()

    selected = S.resolve_target(
        explicit,
        environ={"CODEX_HOME": str(codex_home)},
        home=home,
        isolated_target=True,
    )
    assert selected.path == explicit
    assert selected.kind == "explicit"
    assert selected.real_profile is False

    selected = S.resolve_target(None, environ={"CODEX_HOME": str(codex_home)}, home=home)
    assert selected.path == codex_home / "agents"
    assert selected.kind == "codex-home"
    assert selected.real_profile is True

    selected = S.resolve_target(None, environ={}, home=home)
    assert selected.path == home / ".codex" / "agents"
    assert selected.kind == "default-home"
    assert selected.real_profile is True

    with pytest.raises(S.SyncError, match="requires an explicit"):
        S.resolve_target(
            None,
            environ={"CODEX_HOME": str(codex_home)},
            home=home,
            isolated_target=True,
        )


def test_dry_run_is_read_only_and_reports_sanitized_plan(tmp_path: Path) -> None:
    target_path = tmp_path / "agents"
    plan = _plan(target_path)

    receipt = S.dry_run(plan)

    assert receipt["result"] == "planned"
    assert not target_path.exists()
    assert not S._lock_path(plan.target).exists()
    assert not S._transaction_dir(plan.target).exists()
    assert len(receipt["profiles"]) == 7
    assert len(receipt["roles"]) == 28
    assert {
        "sha256",
        "canonical_sha256",
        "legacy_sha256",
        "unrelated_sha256",
    } <= set(receipt["pre_state"])
    assert all(
        {
            "model",
            "effort",
            "default_profile",
            "result_schema",
        }
        <= set(role)
        for role in receipt["roles"]
    )
    assert all(
        {"allowed_profiles", "workspace_cap", "external_cap"}.isdisjoint(role)
        for role in receipt["roles"]
    )
    assert str(tmp_path) not in json.dumps(receipt)


def test_isolated_apply_installs_managed_profiles_and_is_idempotent(tmp_path: Path) -> None:
    target_path = tmp_path / "agents"
    first_plan = _plan(target_path)
    first = S.apply_sync(first_plan)

    assert first["result"] == "verified"
    assert first["target"]["real_profile_mutated"] is False
    assert {path.stem for path in target_path.glob("*.toml")} == set(
        S.renderer.RUNTIME_AGENT_NAMES.values()
    )
    assert first["readback"]["verified"] is True
    lock_inode = S._lock_path(first_plan.target).stat().st_ino

    second_plan = _plan(target_path)
    second = S.apply_sync(second_plan)
    assert {action["action"] for action in second["actions"]} == {"unchanged"}
    assert second["readback"]["sha256"] == first["readback"]["sha256"]
    assert S._lock_path(first_plan.target).stat().st_ino == lock_inode


def test_unmanaged_profiles_are_preserved_and_name_collisions_block(tmp_path: Path) -> None:
    target = tmp_path / "agents"
    target.mkdir()
    unrelated = target / "local-agent.toml"
    unrelated.write_text(_agent_text("local-agent"), encoding="utf-8")
    before = unrelated.read_bytes()

    plan = _plan(target)
    receipt = S.apply_sync(plan)
    assert unrelated.read_bytes() == before
    assert receipt["pre_state"]["unrelated_sha256"] == receipt["readback"][
        "unrelated_sha256"
    ]

    collision_target = tmp_path / "collision"
    collision_target.mkdir()
    (collision_target / "review_high.toml").write_text(
        _agent_text("local_review_high"), encoding="utf-8"
    )
    collision = _plan(collision_target)
    assert S.dry_run(collision)["result"] == "blocked"
    with pytest.raises(S.SyncError, match="conflicts block apply"):
        S.apply_sync(collision)


def test_stale_canonical_profile_requires_explicit_cleanup(tmp_path: Path) -> None:
    target = tmp_path / "agents"
    target.mkdir()
    stale = target / "obsolete-profile.toml"
    stale.write_text(
        _agent_text("obsolete-profile", S.renderer.MANAGED_MARKER), encoding="utf-8"
    )
    local = target / "local-agent.toml"
    local.write_text(_agent_text("local-agent"), encoding="utf-8")

    plan = _plan(target)
    assert any(action.action == "preserve-stale" for action in plan.actions)
    S.apply_sync(plan)

    assert stale.exists()
    assert local.exists()

    cleanup = _plan(target, remove_stale=True)
    with pytest.raises(S.SyncError, match="destructive cleanup requires"):
        S.apply_sync(cleanup)
    S.apply_sync(
        cleanup,
        expected_pre_state_sha256=cleanup.pre_state.sha256,
    )

    assert not stale.exists()
    assert local.exists()


def test_legacy_marker_requires_explicit_migration_and_digest(tmp_path: Path) -> None:
    target = tmp_path / "agents"
    target.mkdir()
    legacy = target / "old-role.toml"
    legacy.write_text(_agent_text("old-role", S.renderer.LEGACY_MARKER), encoding="utf-8")

    blocked = _plan(target)
    assert S.dry_run(blocked)["result"] == "blocked"
    with pytest.raises(S.SyncError, match="conflicts block apply"):
        S.apply_sync(blocked)

    migration = _plan(target, migrate=True)
    assert any(action.action == "remove-legacy" for action in migration.actions)
    with pytest.raises(S.SyncError, match="destructive cleanup requires"):
        S.apply_sync(migration)
    applied = S.apply_sync(
        migration,
        expected_pre_state_sha256=migration.pre_state.sha256,
    )
    assert applied["result"] == "verified"
    assert not legacy.exists()


def test_real_profile_apply_requires_both_opt_in_and_expected_digest(tmp_path: Path) -> None:
    target = S.resolve_target(None, environ={}, home=tmp_path)
    plan = S.build_plan(
        target,
        catalog_snapshot=S.renderer.DEFAULT_CATALOG_SNAPSHOT,
    )

    with pytest.raises(S.SyncError, match="real-profile mutation requires"):
        S.apply_sync(plan)
    with pytest.raises(S.SyncError, match="real-profile mutation requires"):
        S.apply_sync(plan, allow_real_profile=True)
    assert not target.path.exists()


def test_direct_target_symlink_is_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "agents"
    link.symlink_to(real, target_is_directory=True)

    with pytest.raises(S.SyncError, match="symlink components"):
        S.resolve_target(link.absolute())


@pytest.mark.parametrize("unsafe", ["hardlink", "fifo", "writable"])
def test_target_inventory_rejects_unsafe_files(tmp_path: Path, unsafe: str) -> None:
    target_path = tmp_path / "agents"
    target_path.mkdir()
    target = _target(target_path)
    profile = target_path / "local-agent.toml"
    if unsafe == "fifo":
        os.mkfifo(profile)
    else:
        profile.write_text(_agent_text("local-agent"), encoding="utf-8")
        if unsafe == "hardlink":
            os.link(profile, target_path / "second-agent.toml")
        else:
            profile.chmod(0o666)

    message = {
        "hardlink": "link count one",
        "fifo": "regular file",
        "writable": "group/world writable",
    }[unsafe]
    with pytest.raises(S.SyncError, match=message):
        S.snapshot_target(target)


def test_target_change_between_plan_and_apply_blocks_before_managed_write(tmp_path: Path) -> None:
    target = tmp_path / "agents"
    plan = _plan(target)
    target.mkdir()
    local = target / "local-agent.toml"
    local.write_text(_agent_text("local-agent"), encoding="utf-8")

    with pytest.raises(S.SyncError, match="changed between plan and apply"):
        S.apply_sync(plan)
    assert {path.name for path in target.iterdir()} == {"local-agent.toml"}


def test_wrong_expected_digest_and_incomplete_transaction_block(tmp_path: Path) -> None:
    target = tmp_path / "agents"
    plan = _plan(target)
    with pytest.raises(S.SyncError, match="does not match the planned target"):
        S.apply_sync(plan, expected_pre_state_sha256="0" * 64)
    assert not target.exists()

    transaction = S._transaction_dir(plan.target)
    transaction.mkdir(mode=0o700)
    with pytest.raises(S.SyncError, match="requires --recover"):
        _plan(target)


def test_injected_apply_failure_restores_exact_pre_state(tmp_path: Path) -> None:
    target = tmp_path / "agents"
    plan = _plan(target)

    def fail_after_first(stage: str) -> None:
        if stage.startswith("after:"):
            raise RuntimeError("injected replacement failure")

    with pytest.raises(S.SyncError, match="exact pre-state restored"):
        S.apply_sync(plan, fault_hook=fail_after_first)

    restored = S.snapshot_target(plan.target)
    assert restored.sha256 == plan.pre_state.sha256
    assert restored.exists is plan.pre_state.exists
    assert not target.exists()
    assert not S._transaction_dir(plan.target).exists()


def test_readback_mismatch_triggers_verified_rollback(tmp_path: Path) -> None:
    target = tmp_path / "agents"
    plan = _plan(target)

    def corrupt_before_readback(stage: str) -> None:
        if stage == "before-readback":
            with (target / "review_high.toml").open("ab") as handle:
                handle.write(b"# injected drift\n")

    with pytest.raises(S.SyncError, match="exact pre-state restored"):
        S.apply_sync(plan, fault_hook=corrupt_before_readback)

    restored = S.snapshot_target(plan.target)
    assert restored.sha256 == plan.pre_state.sha256
    assert restored.exists is plan.pre_state.exists
    assert not target.exists()
    assert not S._transaction_dir(plan.target).exists()


def test_custom_codex_home_is_real_and_cannot_bypass_mutation_gates(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / "custom-codex"
    codex_home.mkdir()
    target = S.resolve_target(
        None,
        environ={"CODEX_HOME": str(codex_home)},
        home=tmp_path / "other-home",
    )
    plan = S.build_plan(
        target,
        catalog_snapshot=S.renderer.DEFAULT_CATALOG_SNAPSHOT,
    )

    assert target.kind == "codex-home"
    assert target.real_profile is True
    with pytest.raises(S.SyncError, match="real-profile mutation requires"):
        S.apply_sync(plan)
    assert not target.path.exists()


def test_real_profile_receipt_reports_changes_not_verified_noops(tmp_path: Path) -> None:
    target_path = tmp_path / "agents"
    target = S.resolve_target(target_path.resolve())
    first_plan = S.build_plan(
        target,
        catalog_snapshot=S.renderer.DEFAULT_CATALOG_SNAPSHOT,
    )
    first = S.apply_sync(
        first_plan,
        expected_pre_state_sha256=first_plan.pre_state.sha256,
        allow_real_profile=True,
    )
    assert first["target"]["real_profile_mutated"] is True

    second_plan = S.build_plan(
        target,
        catalog_snapshot=S.renderer.DEFAULT_CATALOG_SNAPSHOT,
    )
    second = S.apply_sync(
        second_plan,
        expected_pre_state_sha256=second_plan.pre_state.sha256,
        allow_real_profile=True,
    )
    assert {action["action"] for action in second["actions"]} == {"unchanged"}
    assert second["target"]["real_profile_mutated"] is False


def test_raw_parent_symlink_and_writable_target_directory_are_rejected(
    tmp_path: Path,
) -> None:
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(S.SyncError, match="symlink components"):
        S.resolve_target(
            (linked_parent / "agents").absolute(),
            isolated_target=True,
        )

    writable = tmp_path / "writable-agents"
    writable.mkdir(mode=0o700)
    writable.chmod(0o777)
    with pytest.raises(S.SyncError, match="group/world writable"):
        S.snapshot_target(_target(writable))


def test_cli_failure_does_not_disclose_absolute_profile_path(tmp_path: Path) -> None:
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    environment = dict(os.environ)
    environment.pop("CODEX_HOME", None)

    result = subprocess.run(
        [
            sys.executable,
            str(SYNC_PATH),
            "--target-dir",
            str(linked_parent / "agents"),
            "--isolated-target",
            "--catalog-snapshot",
            str(S.renderer.DEFAULT_CATALOG_SNAPSHOT),
            "--dry-run",
        ],
        cwd=PLUGIN_ROOT.parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert str(tmp_path) not in result.stderr


def test_unsafe_lock_mode_is_rejected_and_lock_inode_is_persistent(tmp_path: Path) -> None:
    plan = _plan(tmp_path / "agents")
    lock = S._lock_path(plan.target)
    lock.write_text("not safe\n", encoding="utf-8")
    lock.chmod(0o666)

    with pytest.raises(S.SyncError, match="managed-profile lock must be"):
        S.apply_sync(plan)
    assert lock.exists()


def test_rollback_never_uses_or_deletes_unmanaged_scratch_names(tmp_path: Path) -> None:
    target = tmp_path / "agents"
    target.mkdir()
    scratch = target / ".review_high.toml.rollback"
    scratch.write_text("user-owned scratch\n", encoding="utf-8")
    before = scratch.read_bytes()

    S.apply_sync(_plan(target))

    assert scratch.read_bytes() == before


def test_default_build_plan_reads_live_catalog_exactly_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = S.renderer.load_catalog_snapshot()
    calls = 0

    def read_once():
        nonlocal calls
        calls += 1
        return snapshot

    monkeypatch.setattr(S.renderer.CATALOG, "read_catalog", read_once)
    plan = S.build_plan(_target(tmp_path / "agents"))

    assert calls == 1
    assert plan.bundle.catalog is snapshot


def test_applying_transaction_is_recovered_to_exact_absent_pre_state(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path / "agents")
    parent_fd = S._open_parent(plan.target)
    target_fd = None
    try:
        transaction, manifest = S._prepare_transaction(plan, None)
        manifest["state"] = "applying"
        S._write_manifest(transaction, manifest)
        target_fd, created = S._open_target_from_parent(
            plan.target,
            parent_fd,
            create=True,
        )
        assert target_fd is not None and created
        stage_fd = S._open_directory_chain(transaction / "stage")
        try:
            first = next(
                action for action in plan.actions if action.action == "install"
            )
            os.link(
                first.name,
                first.name,
                src_dir_fd=stage_fd,
                dst_dir_fd=target_fd,
                follow_symlinks=False,
            )
            os.unlink(first.name, dir_fd=stage_fd)
        finally:
            os.close(stage_fd)
    finally:
        if target_fd is not None:
            os.close(target_fd)
        os.close(parent_fd)

    with pytest.raises(S.SyncError, match="requires --recover"):
        S.snapshot_target(plan.target)
    receipt = S.recover_sync(
        plan.target,
        expected_pre_state_sha256=plan.pre_state.sha256,
    )

    assert receipt["prior_transaction_state"] == "applying"
    assert receipt["readback"]["exists"] is False
    assert not plan.target.path.exists()
    assert not S._transaction_dir(plan.target).exists()


def test_committed_cleanup_failure_is_recoverable_without_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _plan(tmp_path / "agents")
    cleanup = S._cleanup_transaction
    calls = 0

    def fail_first_cleanup(transaction: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise S.SyncError("injected committed cleanup failure")
        cleanup(transaction)

    monkeypatch.setattr(S, "_cleanup_transaction", fail_first_cleanup)
    applied = S.apply_sync(plan)
    assert applied["result"] == "verified"
    assert applied["rollback"]["cleanup_pending"] is True
    assert S._transaction_dir(plan.target).exists()

    recovered = S.recover_sync(
        plan.target,
        expected_pre_state_sha256=plan.pre_state.sha256,
    )
    assert recovered["prior_transaction_state"] == "committed"
    assert recovered["readback"]["exists"] is True
    assert not S._transaction_dir(plan.target).exists()


def test_preparing_transaction_with_partial_stage_is_recoverable(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path / "agents")
    transaction, manifest = S._prepare_transaction(plan, None)
    manifest["state"] = "preparing"
    S._write_manifest(transaction, manifest)
    staged = next((transaction / "stage").iterdir())
    staged.unlink()

    recovered = S.recover_sync(
        plan.target,
        expected_pre_state_sha256=plan.pre_state.sha256,
    )

    assert recovered["prior_transaction_state"] == "preparing"
    assert recovered["readback"]["exists"] is False
    assert not transaction.exists()


def test_applying_state_before_target_creation_recovers_without_mutation(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path / "agents")
    transaction, manifest = S._prepare_transaction(plan, None)
    manifest["state"] = "applying"
    S._write_manifest(transaction, manifest)

    recovered = S.recover_sync(
        plan.target,
        expected_pre_state_sha256=plan.pre_state.sha256,
    )

    assert recovered["prior_transaction_state"] == "applying"
    assert recovered["readback"]["exists"] is False
    assert not plan.target.path.exists()


def test_update_boundary_retains_concurrently_substituted_unmanaged_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "agents"
    target.mkdir()
    managed = target / "review_high.toml"
    managed.write_text(
        _agent_text("review_high", S.renderer.MANAGED_MARKER),
        encoding="utf-8",
    )
    plan = _plan(target)
    assert any(
        action.name == "review_high.toml" and action.action == "update"
        for action in plan.actions
    )
    substitute = _agent_text("user_review_high").encode()
    recheck = S._recheck_action_target

    def swap_after_recheck(plan_arg, target_fd, action):
        recheck(plan_arg, target_fd, action)
        if action.name == "review_high.toml":
            temporary = target / ".user-substitute"
            temporary.write_bytes(substitute)
            os.replace(temporary, managed)

    monkeypatch.setattr(S, "_recheck_action_target", swap_after_recheck)
    with pytest.raises(S.SyncError, match="rollback could not be proved"):
        S.apply_sync(plan)

    assert managed.read_bytes() == substitute
    assert S._transaction_dir(plan.target).exists()


def test_update_boundary_retains_special_node_substitution_as_manual_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "agents"
    target.mkdir()
    managed = target / "review_high.toml"
    managed.write_text(
        _agent_text("review_high", S.renderer.MANAGED_MARKER),
        encoding="utf-8",
    )
    plan = _plan(target)
    recheck = S._recheck_action_target

    def swap_fifo_after_recheck(plan_arg, target_fd, action):
        recheck(plan_arg, target_fd, action)
        if action.name == "review_high.toml":
            fifo = target / ".fifo-substitute"
            os.mkfifo(fifo)
            os.replace(fifo, managed)

    monkeypatch.setattr(S, "_recheck_action_target", swap_fifo_after_recheck)
    with pytest.raises(S.SyncError, match="manual conflict"):
        S.apply_sync(plan)

    transaction = S._transaction_dir(plan.target)
    retained = []
    if managed.exists() and stat.S_ISFIFO(managed.lstat().st_mode):
        retained.append(managed)
    removed = transaction / "removed"
    if removed.exists():
        retained.extend(
            child for child in removed.iterdir() if stat.S_ISFIFO(child.lstat().st_mode)
        )
    assert retained, "the concurrently substituted FIFO must remain recoverable"
    assert transaction.exists()


def test_created_target_removal_keeps_descriptor_owned_on_parent_fsync_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _target(tmp_path / "agents")
    parent_fd = S._open_parent(target)
    target_fd, created = S._open_target_from_parent(target, parent_fd, create=True)
    assert target_fd is not None and created
    fsync = S.os.fsync

    def fail_parent_fsync(descriptor: int) -> None:
        if descriptor == parent_fd:
            raise OSError("injected parent fsync failure")
        fsync(descriptor)

    monkeypatch.setattr(S.os, "fsync", fail_parent_fsync)
    try:
        with pytest.raises(OSError, match="injected parent fsync failure"):
            S._remove_created_target(target, parent_fd, target_fd)
        assert os.fstat(target_fd).st_ino > 0
    finally:
        os.close(target_fd)
        os.close(parent_fd)


def test_real_profile_applying_recovery_reports_restored_mutation(tmp_path: Path) -> None:
    target = S.resolve_target((tmp_path / "agents").resolve())
    plan = S.build_plan(
        target,
        catalog_snapshot=S.renderer.DEFAULT_CATALOG_SNAPSHOT,
    )
    transaction, manifest = S._prepare_transaction(plan, None)
    manifest["state"] = "applying"
    S._write_manifest(transaction, manifest)
    parent_fd = S._open_parent(target)
    target_fd = None
    try:
        target_fd, created = S._open_target_from_parent(target, parent_fd, create=True)
        assert target_fd is not None and created
        stage_fd = S._open_directory_chain(transaction / "stage")
        try:
            first = next(action for action in plan.actions if action.action == "install")
            os.link(
                first.name,
                first.name,
                src_dir_fd=stage_fd,
                dst_dir_fd=target_fd,
                follow_symlinks=False,
            )
            os.unlink(first.name, dir_fd=stage_fd)
        finally:
            os.close(stage_fd)
    finally:
        if target_fd is not None:
            os.close(target_fd)
        os.close(parent_fd)

    recovered = S.recover_sync(
        target,
        expected_pre_state_sha256=plan.pre_state.sha256,
        allow_real_profile=True,
    )

    assert recovered["target"]["real_profile"] is True
    assert recovered["target"]["real_profile_mutated"] is True
    assert recovered["readback"]["exists"] is False
