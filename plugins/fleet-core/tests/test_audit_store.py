"""Tests for the fleet-core durable delegation audit store (#396, U1)."""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "plugins" / "fleet-core" / "scripts" / "fleet_commons" / "audit_store.py"


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def audit_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
    # Never resolve DEFAULT_AUDIT_STORE_ROOT against the real developer home directory (R5/KTD6).
    monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
    return _load_module(MODULE_PATH, "audit_store")


def _receipt(run_id: str = "run-1") -> dict[str, object]:
    return {
        "schema": "bridge_receipt.v1",
        "engine_id": "agy",
        "variant": "flash",
        "transport": "cli",
        "wall_time_s": 1.5,
        "bytes_produced": 42,
        "runner": {"pid": 123, "argv": ["agy"], "exit_code": 0},
        "run_id": run_id,
    }


def test_mirror_receipt_resolvable_by_run_id_alone(audit_store: ModuleType, tmp_path: Path) -> None:
    store = audit_store.Store.for_root(tmp_path / "audit-store")
    audit_store.mirror_receipt(store, "run-1", _receipt("run-1"))

    resolved = audit_store.resolve_receipt(store, "run-1")

    assert resolved is not None
    assert resolved["run_id"] == "run-1"


def test_mirror_result_resolvable_when_no_receipt(audit_store: ModuleType, tmp_path: Path) -> None:
    store = audit_store.Store.for_root(tmp_path / "audit-store")
    result_payload = {"status": "success", "agy_launched": False, "run_id": "run-2"}

    audit_store.mirror_result(store, "run-2", result_payload)

    assert audit_store.resolve_result(store, "run-2") == result_payload
    assert audit_store.resolve_receipt(store, "run-2") is None


def test_mirror_manifest_resolvable_by_id(audit_store: ModuleType, tmp_path: Path) -> None:
    store = audit_store.Store.for_root(tmp_path / "audit-store")
    manifest = {"execution_id": "exec-1", "disposition": "ran-as-requested"}

    audit_store.mirror_manifest(store, "exec-1", manifest)

    assert audit_store.resolve_manifest(store, "exec-1") == manifest


def test_manifest_mirror_overwrites_in_place(audit_store: ModuleType, tmp_path: Path) -> None:
    store = audit_store.Store.for_root(tmp_path / "audit-store")
    audit_store.mirror_manifest(store, "exec-1", {"disposition": "ran-as-requested"})

    audit_store.mirror_manifest(store, "exec-1", {"disposition": "rejected-offload"})

    assert audit_store.resolve_manifest(store, "exec-1") == {"disposition": "rejected-offload"}


def test_default_root_is_runtime_neutral_local_state(
    audit_store: ModuleType,
) -> None:
    store = audit_store.Store.for_root(None)

    assert (
        store.root
        == (Path.home() / ".local" / "state" / "infiquetra" / "delegation-audit").resolve()
    )
    assert ".claude" not in str(store.root)
    assert ".codex" not in str(store.root)


def test_run_id_path_traversal_rejected(audit_store: ModuleType, tmp_path: Path) -> None:
    store = audit_store.Store.for_root(tmp_path / "audit-store")

    with pytest.raises(audit_store.AuditStoreError):
        audit_store.mirror_receipt(store, "../../etc", _receipt())


def test_list_runs_reflects_every_mirrored_run(audit_store: ModuleType, tmp_path: Path) -> None:
    store = audit_store.Store.for_root(tmp_path / "audit-store")
    audit_store.mirror_result(store, "run-a", {"status": "success"})
    audit_store.mirror_manifest(store, "run-b", {"disposition": "ran-as-requested"})

    assert audit_store.list_runs(store) == ["run-a", "run-b"]


def test_list_runs_empty_store_returns_empty_list(audit_store: ModuleType, tmp_path: Path) -> None:
    store = audit_store.Store.for_root(tmp_path / "audit-store")

    assert audit_store.list_runs(store) == []


def test_resolve_receipt_missing_run_returns_none(audit_store: ModuleType, tmp_path: Path) -> None:
    store = audit_store.Store.for_root(tmp_path / "audit-store")

    assert audit_store.resolve_receipt(store, "never-existed") is None


def test_resolve_corrupt_json_returns_none_never_raises(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    store = audit_store.Store.for_root(tmp_path / "audit-store")
    path = store.receipt_path("run-corrupt")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")

    assert audit_store.resolve_receipt(store, "run-corrupt") is None


def test_write_once_draft_then_resolve(audit_store: ModuleType, tmp_path: Path) -> None:
    store = audit_store.Store.for_root(tmp_path / "audit-store")

    audit_store.write_once_draft(store, "run-1", "--- a/foo\n+++ b/foo\n")

    assert audit_store.resolve_draft(store, "run-1") == "--- a/foo\n+++ b/foo\n"


def test_resolve_draft_missing_returns_none(audit_store: ModuleType, tmp_path: Path) -> None:
    store = audit_store.Store.for_root(tmp_path / "audit-store")

    assert audit_store.resolve_draft(store, "never-existed") is None


def test_mirrored_files_are_not_world_or_group_readable(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """Mirrored evidence (receipts, result payloads, manifests, raw drafts) lands mode 0600 —
    matching manifest_store.py's precedent for the identical manifest.json content this store
    also mirrors, not the unrestricted default a bare write_text/os.replace would leave."""
    store = audit_store.Store.for_root(tmp_path / "audit-store")
    audit_store.mirror_receipt(store, "run-1", _receipt("run-1"))
    audit_store.write_once_draft(store, "run-1", "raw pre-fix output")

    for path in (store.receipt_path("run-1"), store.draft_path("run-1")):
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == 0o600, f"{path} is mode {oct(mode)}, expected 0o600"


def test_resolve_receipt_valid_json_non_dict_returns_none(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """A mirrored file that parses as valid JSON but isn't an object (e.g. a bare list) degrades
    to None rather than being treated as a receipt/result/manifest dict."""
    store = audit_store.Store.for_root(tmp_path / "audit-store")
    path = store.receipt_path("run-list")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[1, 2, 3]", encoding="utf-8")

    assert audit_store.resolve_receipt(store, "run-list") is None


# ------------------------------------------------------------------- ancestor hardening (#43/#624)


def test_ensure_private_dir_refuses_symlinked_ancestor_below_home(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """A symlinked component below home is refused before any mkdir traverses it."""
    home = Path.home()  # the fixture monkeypatches HOME to tmp_path/"fake-home"
    real = home / "real-target"
    real.mkdir(parents=True, mode=0o700)
    link = home / "link"
    link.symlink_to(real)
    with pytest.raises(audit_store.AuditStoreError, match="symlink"):
        audit_store._ensure_private_dir(link / "audit")
    assert list(real.iterdir()) == []  # nothing was created through the link


def test_ensure_private_dir_refuses_world_writable_ancestor_below_home(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """An existing world-writable directory below home is refused, no fallback."""
    home = Path.home()
    loose = home / "loose"
    loose.mkdir(parents=True)
    os.chmod(loose, 0o777)
    with pytest.raises(audit_store.AuditStoreError, match="world-writable"):
        audit_store._ensure_private_dir(loose / "audit")
    assert not (loose / "audit").exists()


def test_ensure_private_dir_refuses_world_writable_non_sticky_ancestor_outside_home(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """R3/KTD2: the pre-port guard exempted everything outside home outright (the
    `is_relative_to(home)` early return), so a loose world-writable ancestor out there was
    silently accepted. Post-port there is no scope exemption left -- only the sticky bit
    (S_ISVTX) exempts a world-writable component, wherever it sits."""
    outside = tmp_path / "outside-home"  # tmp_path is not under the monkeypatched home
    outside.mkdir()
    os.chmod(outside, 0o777)
    target = outside / "audit"
    with pytest.raises(audit_store.AuditStoreError, match="world-writable"):
        audit_store._ensure_private_dir(target)
    assert not target.exists()


def test_ensure_private_dir_refuses_symlinked_ancestor_outside_home(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """R3: the walk has no home-scope exemption -- a symlinked component outside home, which the
    pre-port guard never even inspected, is refused exactly like one below home."""
    outside = tmp_path / "outside-home"
    real = outside / "real-target"
    real.mkdir(parents=True, mode=0o700)
    link = outside / "link"
    link.symlink_to(real)
    with pytest.raises(audit_store.AuditStoreError, match="symlink"):
        audit_store._ensure_private_dir(link / "audit")
    assert list(real.iterdir()) == []  # nothing was created through the link


def test_ensure_private_dir_accepts_world_writable_sticky_ancestor_outside_home(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """Characterization, must pass before and after: the `/tmp` 1777 shape (world-writable AND
    sticky) outside home is the intended exemption, not a regression. Pre-port it passed because
    the walk never ran outside home at all; post-port it passes because S_ISVTX is explicitly
    exempted."""
    outside = tmp_path / "outside-home"
    sticky = outside / "tmp-shape"
    sticky.mkdir(parents=True)
    os.chmod(sticky, 0o777)
    os.chmod(sticky, stat.S_IMODE(sticky.stat().st_mode) | stat.S_ISVTX)
    target = sticky / "audit"
    audit_store._ensure_private_dir(target)
    assert stat.S_IMODE(target.lstat().st_mode) == 0o700


def test_ensure_private_dir_accepts_group_writable_ancestor_outside_home(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """The guard's scope is world-writable, not group-writable (#624) -- unaffected by R3 and
    unaffected by home scope. Extends the below-home pin to the newly-universal outside-home
    case."""
    outside = tmp_path / "outside-home"
    shared = outside / "shared"
    shared.mkdir(parents=True)
    os.chmod(shared, 0o770)
    target = shared / "audit"
    audit_store._ensure_private_dir(target)
    assert stat.S_IMODE(target.lstat().st_mode) == 0o700


def test_ensure_private_dir_creates_fresh_outside_home_path(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """FileNotFoundError short-circuits cleanly outside home too: pre-port this path never
    reached the walk (home-scope exemption); post-port it reaches the walk and the first missing
    component's FileNotFoundError still short-circuits to a clean 0o700 create."""
    outside = tmp_path / "outside-home"
    outside.mkdir()
    target = outside / "fresh" / "audit"
    audit_store._ensure_private_dir(target)
    for directory in (target, target.parent):
        assert stat.S_IMODE(directory.lstat().st_mode) == 0o700


def test_ensure_private_dir_creates_fresh_below_home_path(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """Scope guard, not a change detector: the walk falls through at the first not-yet-existing
    component and creates the subtree 0o700 — the DEFAULT_AUDIT_STORE_ROOT path on a machine
    that has never mirrored before."""
    home = Path.home()
    home.mkdir(parents=True, exist_ok=True)
    target = home / "fresh" / "audit"
    audit_store._ensure_private_dir(target)
    for directory in (target, target.parent):
        assert stat.S_IMODE(directory.lstat().st_mode) == 0o700


def test_ensure_private_dir_accepts_group_writable_ancestor_below_home(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """Scope guard, not a change detector: the guard's scope is world-writable, not
    group-writable — a shared-group ancestor stays usable. Pins the boundary so it cannot drift
    either way unnoticed."""
    home = Path.home()
    shared = home / "shared"
    shared.mkdir(parents=True)
    os.chmod(shared, 0o770)
    target = shared / "audit"
    audit_store._ensure_private_dir(target)
    assert stat.S_IMODE(target.lstat().st_mode) == 0o700


def test_ensure_private_dir_refuses_uninspectable_ancestor_below_home(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """An ancestor this user cannot stat fails typed, not as a raw PermissionError."""
    if os.geteuid() == 0:  # root bypasses the permission check the test depends on
        pytest.skip("root can traverse any directory")
    home = Path.home()
    blocked = home / "blocked"
    blocked.mkdir(parents=True)
    (blocked / "child").mkdir()
    os.chmod(blocked, 0o000)
    try:
        with pytest.raises(audit_store.AuditStoreError, match="not inspectable"):
            audit_store._ensure_private_dir(blocked / "child" / "audit")
    finally:
        os.chmod(blocked, 0o700)  # restore so tmp_path teardown can clean up
