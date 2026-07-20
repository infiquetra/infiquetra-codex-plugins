"""Ancestor hardening for the durable delegation audit store (#43, re-ported from #624 PA-1)."""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parent.parent
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
    # Never resolve DEFAULT_AUDIT_STORE_ROOT against the real developer home directory.
    monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
    return _load_module(MODULE_PATH, "audit_store")


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


def test_ensure_private_dir_exempts_paths_outside_home(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """Out-of-home roots (system temp style) keep working under loose ancestors."""
    outside = tmp_path / "outside-home"  # tmp_path is not under the monkeypatched home
    outside.mkdir()
    os.chmod(outside, 0o777)
    target = outside / "audit"
    audit_store._ensure_private_dir(target)
    assert stat.S_IMODE(target.lstat().st_mode) == 0o700


def test_ensure_private_dir_creates_fresh_below_home_path(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """The walk falls through at the first not-yet-existing component and creates the subtree
    0o700 — the DEFAULT_AUDIT_STORE_ROOT path on a machine that has never mirrored before."""
    home = Path.home()
    home.mkdir(parents=True, exist_ok=True)
    target = home / "fresh" / "audit"
    audit_store._ensure_private_dir(target)
    for directory in (target, target.parent):
        assert stat.S_IMODE(directory.lstat().st_mode) == 0o700


def test_ensure_private_dir_accepts_group_writable_ancestor_below_home(
    audit_store: ModuleType, tmp_path: Path
) -> None:
    """The guard's scope is world-writable, not group-writable — a shared-group ancestor stays
    usable. Pins the boundary so it cannot drift either way unnoticed."""
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
