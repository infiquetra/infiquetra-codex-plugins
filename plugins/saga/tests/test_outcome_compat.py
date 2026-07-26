"""Tests for the frozen cross-runtime seam's handoff-store ancestor guard (#627/U2, codex#45 U2).

`outcome_compat.py` is the byte-frozen twin of Claude `outcome_compat.py` (KTD1/KTD3): the two
copies are identical except `RUNTIME_LABEL` (line 83). Per KTD7 this module ships with zero codex
test coverage today, so a green suite elsewhere is not evidence a re-freeze landed correctly — this
module (plus the byte-identity diff run separately) is the actual oracle.

Coverage here targets `_refuse_unsafe_handoff_ancestors` / `_handoff_store_halt` / `_ensure_private_dir`,
the surface R2's re-freeze changed: the home-scope early return is gone, every filesystem component
from the anchor down is walked with `lstat` (never `resolve` inside the walk), a symlink anywhere is
refused, and world-writable is refused unless also sticky (`S_ISVTX`).
"""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def outcome_compat() -> ModuleType:
    return _load("outcome_compat")


# --------------------------------------------------------------- RUNTIME_LABEL (the sole divergence)


def test_runtime_label_is_codex_not_claude(outcome_compat: ModuleType) -> None:
    """The re-freeze pulls Claude's bytes forward except this one line (R2) — a regression here
    would mean the copy silently kept Claude's own label."""
    assert outcome_compat.RUNTIME_LABEL == "codex"


# ------------------------------------------------------- universal fail-closed ancestor walk (R3)


def test_refuses_symlinked_component_above_any_home_scope(
    outcome_compat: ModuleType, tmp_path: Path
) -> None:
    """Pre-port, a symlinked ancestor outside the caller's home directory was never even
    inspected (`is_relative_to(home)` returned False and the walk exited early) — this is the
    exact exemption R3 removes. A symlink anywhere in the path must now be refused."""
    real = tmp_path / "real-target"
    real.mkdir(parents=True, mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(real)

    with pytest.raises(outcome_compat.CompatibilityHaltError) as excinfo:
        outcome_compat._refuse_unsafe_handoff_ancestors(link / "handoff")

    assert excinfo.value.code == "handoff-store-unsafe"
    assert "symlink" in excinfo.value.unsupported
    assert list(real.iterdir()) == []  # nothing was created through the link


def test_refuses_world_writable_non_sticky_component_above_any_home_scope(
    outcome_compat: ModuleType, tmp_path: Path
) -> None:
    """Pre-port this path was exempt purely because it sat outside home; the old guard never
    reached the mode check for it at all. Post-port there is no scope exemption left."""
    loose = tmp_path / "loose"
    loose.mkdir(parents=True)
    os.chmod(loose, 0o777)

    with pytest.raises(outcome_compat.CompatibilityHaltError) as excinfo:
        outcome_compat._refuse_unsafe_handoff_ancestors(loose / "handoff")

    assert excinfo.value.code == "handoff-store-unsafe"
    assert "world-writable" in excinfo.value.unsupported
    assert "not sticky" in excinfo.value.unsupported
    assert not (loose / "handoff").exists()


def test_accepts_world_writable_sticky_component_the_system_temp_shape(
    outcome_compat: ModuleType, tmp_path: Path
) -> None:
    """Characterization: the `/tmp` 1777 shape is the exemption, not a regression. This must pass
    both before and after the port — pre-port it passed because the path sat outside home and the
    walk never ran; post-port it passes because the sticky bit is explicitly exempted."""
    sticky = tmp_path / "tmp-shape"
    sticky.mkdir(parents=True)
    os.chmod(sticky, 0o777)
    os.chmod(sticky, stat.S_IMODE(sticky.stat().st_mode) | stat.S_ISVTX)
    assert stat.S_ISVTX & sticky.stat().st_mode

    outcome_compat._refuse_unsafe_handoff_ancestors(sticky / "handoff")  # must not raise


def test_accepts_group_writable_component_the_624_boundary_unchanged(
    outcome_compat: ModuleType, tmp_path: Path
) -> None:
    """The guard's scope is world-writable, not group-writable (#624) — unaffected by the R3
    re-freeze. Pins the boundary above any home scope so it cannot drift unnoticed."""
    shared = tmp_path / "shared"
    shared.mkdir(parents=True)
    os.chmod(shared, 0o770)

    outcome_compat._refuse_unsafe_handoff_ancestors(shared / "handoff")  # must not raise


def test_permission_error_on_a_component_raises_typed_halt(
    outcome_compat: ModuleType, tmp_path: Path
) -> None:
    """An ancestor this user cannot inspect fails as the typed `CompatibilityHaltError`, never a
    bare `PermissionError`."""
    if os.geteuid() == 0:
        pytest.skip("root can traverse any directory")
    blocked = tmp_path / "blocked"
    blocked.mkdir(parents=True)
    (blocked / "child").mkdir()
    os.chmod(blocked, 0o000)
    try:
        with pytest.raises(outcome_compat.CompatibilityHaltError) as excinfo:
            outcome_compat._refuse_unsafe_handoff_ancestors(blocked / "child" / "handoff")
        assert excinfo.value.code == "handoff-store-unsafe"
        assert "cannot inspect" in excinfo.value.unsupported
    finally:
        os.chmod(blocked, 0o700)


def test_file_not_found_short_circuits_cleanly(outcome_compat: ModuleType, tmp_path: Path) -> None:
    """Nothing existing from the first-missing component down is not a halt: the walk returns
    cleanly, matching `_ensure_private_dir`'s create-fresh-0o700 path."""
    target = tmp_path / "fresh" / "nested" / "handoff"

    outcome_compat._refuse_unsafe_handoff_ancestors(target)  # must not raise


# ------------------------------------------------------------------- _ensure_private_dir end to end


def test_ensure_private_dir_refuses_symlinked_ancestor_outside_home(
    outcome_compat: ModuleType, tmp_path: Path
) -> None:
    real = tmp_path / "real-target"
    real.mkdir(parents=True, mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(real)

    with pytest.raises(outcome_compat.CompatibilityHaltError, match="handoff-store-unsafe"):
        outcome_compat._ensure_private_dir(link / "handoff")


def test_ensure_private_dir_creates_fresh_subtree_mode_0700(
    outcome_compat: ModuleType, tmp_path: Path
) -> None:
    target = tmp_path / "fresh" / "handoff"

    outcome_compat._ensure_private_dir(target)

    for directory in (target, target.parent):
        assert stat.S_IMODE(directory.lstat().st_mode) == 0o700


def test_handoff_store_halt_next_action_names_nfs_and_fat_relocate_guidance(
    outcome_compat: ModuleType,
) -> None:
    """R3's `next_action` gains the NFS/SMB and FAT32/exFAT relocate guidance — pinned so the
    string cannot silently regress to the pre-port wording."""
    halt = outcome_compat._handoff_store_halt(
        unsupported="a handoff store ancestor that is a symlink"
    )

    assert "NFS/SMB" in halt.next_action
    assert "FAT32/exFAT" in halt.next_action
    assert "world-writable-and-sticky" in halt.supported
