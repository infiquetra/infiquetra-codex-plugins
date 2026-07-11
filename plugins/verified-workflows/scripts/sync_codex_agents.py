#!/usr/bin/env python3
"""Safely synchronize the five managed execution profiles into a Codex home."""

from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import render_codex_agents as renderer  # noqa: E402

MAX_PROFILE_BYTES = 1024 * 1024
MAX_PROFILE_SET_BYTES = 16 * 1024 * 1024
SAFE_NAME = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*\.toml$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TRANSACTION_SCHEMA_VERSION = 1
CHANGED_ACTIONS = frozenset(
    {"install", "update", "replace-legacy", "remove-stale", "remove-legacy"}
)
NONMUTATING_ACTIONS = frozenset({"unchanged", "preserve-stale", "conflict"})


class SyncError(RuntimeError):
    """Raised when profile planning, apply, readback, recovery, or rollback cannot be proved."""


@dataclass(frozen=True, slots=True)
class TargetSpec:
    path: Path
    kind: str
    real_profile: bool
    isolated_target: bool


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    name: str
    mode: int
    size: int
    sha256: str
    ownership: str
    device: int
    inode: int
    mtime_ns: int

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mode": self.mode,
            "size": self.size,
            "sha256": self.sha256,
            "ownership": self.ownership,
        }

    def identity(self) -> tuple[int, int, int, int]:
        return (self.device, self.inode, self.size, self.mtime_ns)


@dataclass(frozen=True, slots=True)
class TargetSnapshot:
    exists: bool
    sha256: str
    canonical_sha256: str
    legacy_sha256: str
    unrelated_sha256: str
    entries: tuple[InventoryEntry, ...]
    directory_device: int | None = None
    directory_inode: int | None = None

    def entry(self, name: str) -> InventoryEntry | None:
        return next((entry for entry in self.entries if entry.name == name), None)

    def counts(self) -> dict[str, int]:
        values = {"canonical": 0, "legacy": 0, "unmanaged": 0}
        for entry in self.entries:
            values[entry.ownership] += 1
        return values


@dataclass(frozen=True, slots=True)
class SyncAction:
    action: str
    name: str
    before_sha256: str | None
    after_sha256: str | None
    prior_ownership: str
    reason: str

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "relative_path": f"agents/{self.name}",
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "prior_ownership": self.prior_ownership,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class SyncPlan:
    bundle: renderer.RenderBundle
    target: TargetSpec
    pre_state: TargetSnapshot
    actions: tuple[SyncAction, ...]
    migrate_legacy: bool
    remove_stale: bool

    def conflicts(self) -> tuple[SyncAction, ...]:
        return tuple(action for action in self.actions if action.action == "conflict")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_digest(values: list[dict[str, Any]]) -> str:
    content = (json.dumps(values, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return _sha256(content)


def _safe_errno(exc: OSError) -> str:
    return f"errno {exc.errno if exc.errno is not None else 'unknown'}"


def _assert_no_symlink_components(path: Path) -> None:
    absolute = path if path.is_absolute() else path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise SyncError(f"target path component is unreadable ({_safe_errno(exc)})") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise SyncError("target path must not contain symlink components")


def resolve_target(
    explicit_target: Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    isolated_target: bool = False,
) -> TargetSpec:
    """Resolve a target and require an explicit sentinel for every isolated profile."""

    env = os.environ if environ is None else environ
    user_home = Path.home() if home is None else home
    default_target = (user_home / ".codex" / "agents").absolute()
    active_codex_target: Path | None = None
    if env.get("CODEX_HOME"):
        active_codex_home = Path(env["CODEX_HOME"])
        if not active_codex_home.is_absolute():
            raise SyncError("CODEX_HOME must be absolute for managed profile sync")
        active_codex_target = (active_codex_home / "agents").absolute()

    if explicit_target is not None:
        if not explicit_target.is_absolute():
            raise SyncError("--target-dir must be an absolute canonical path")
        raw = explicit_target.absolute()
        kind = "explicit"
    elif active_codex_target is not None:
        if isolated_target:
            raise SyncError("--isolated-target requires an explicit --target-dir")
        raw = active_codex_target
        kind = "codex-home"
    else:
        if isolated_target:
            raise SyncError("--isolated-target requires an explicit --target-dir")
        raw = default_target
        kind = "default-home"

    _assert_no_symlink_components(raw)
    canonical = raw.resolve(strict=False)
    if explicit_target is not None and canonical != raw:
        raise SyncError("--target-dir must be canonical and symlink-free")
    protected = {default_target.resolve(strict=False)}
    if active_codex_target is not None:
        protected.add(active_codex_target.resolve(strict=False))
    if isolated_target and canonical in protected:
        raise SyncError("the active Codex profile cannot be marked isolated")
    real_profile = not isolated_target
    return TargetSpec(
        path=canonical,
        kind=kind,
        real_profile=real_profile,
        isolated_target=isolated_target,
    )


def _transaction_dir(target: TargetSpec) -> Path:
    return target.path.parent / f".{target.path.name}.verified-workflows-transaction"


def _lock_path(target: TargetSpec) -> Path:
    return target.path.parent / _lock_name(target)


def _lock_name(target: TargetSpec) -> str:
    return f".{target.path.name}.verified-workflows.lock"


def _directory_flags() -> int:
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _open_directory_chain(path: Path) -> int:
    """Open an absolute directory one no-follow component at a time."""

    if not path.is_absolute():
        raise SyncError("internal target directory must be absolute")
    flags = _directory_flags()
    try:
        descriptor = os.open(path.anchor, flags)
    except OSError as exc:
        raise SyncError(f"target root is unreadable ({_safe_errno(exc)})") from exc
    try:
        for part in path.parts[1:]:
            try:
                child = os.open(part, flags, dir_fd=descriptor)
            except OSError as exc:
                raise SyncError(
                    f"target directory component is unreadable ({_safe_errno(exc)})"
                ) from exc
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _validate_owned_directory(descriptor: int, where: str) -> os.stat_result:
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
        raise SyncError(f"{where} must be a real directory owned by the current user")
    if metadata.st_mode & 0o022:
        raise SyncError(f"{where} must not be group/world writable")
    return metadata


def _open_parent(target: TargetSpec) -> int:
    descriptor = _open_directory_chain(target.path.parent)
    try:
        _validate_owned_directory(descriptor, "target parent")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_target_from_parent(
    target: TargetSpec,
    parent_fd: int,
    *,
    create: bool = False,
) -> tuple[int | None, bool]:
    flags = _directory_flags()
    try:
        descriptor = os.open(target.path.name, flags, dir_fd=parent_fd)
        created = False
    except FileNotFoundError:
        if not create:
            return None, False
        try:
            os.mkdir(target.path.name, 0o700, dir_fd=parent_fd)
            os.fsync(parent_fd)
            descriptor = os.open(target.path.name, flags, dir_fd=parent_fd)
        except OSError as exc:
            raise SyncError(f"target directory could not be created ({_safe_errno(exc)})") from exc
        created = True
    except OSError as exc:
        raise SyncError(f"target directory is unreadable ({_safe_errno(exc)})") from exc
    try:
        _validate_owned_directory(descriptor, "target")
        return descriptor, created
    except BaseException:
        os.close(descriptor)
        raise


def _assert_target_link(target: TargetSpec, parent_fd: int, target_fd: int) -> None:
    try:
        linked = os.stat(target.path.name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        raise SyncError(f"target directory link changed ({_safe_errno(exc)})") from exc
    opened = os.fstat(target_fd)
    if (
        not stat.S_ISDIR(linked.st_mode)
        or (linked.st_dev, linked.st_ino) != (opened.st_dev, opened.st_ino)
    ):
        raise SyncError("target directory link changed during the transaction")


def _read_regular_at(
    directory_fd: int,
    name: str,
    *,
    where: str,
    limit: int = MAX_PROFILE_BYTES,
) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as exc:
        raise SyncError(f"{where} is unreadable ({_safe_errno(exc)})") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise SyncError(f"{where} must be a regular file")
        if before.st_nlink != 1:
            raise SyncError(f"{where} must have link count one")
        if before.st_uid != os.getuid():
            raise SyncError(f"{where} must be owned by the current user")
        if before.st_mode & 0o022:
            raise SyncError(f"{where} must not be group/world writable")
        if before.st_size > limit:
            raise SyncError(f"{where} exceeds the byte ceiling")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        if len(content) > limit:
            raise SyncError(f"{where} exceeds the byte ceiling")
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ) or len(content) != after.st_size:
            raise SyncError(f"{where} changed while it was read")
        return content, after
    except OSError as exc:
        raise SyncError(f"{where} is unreadable ({_safe_errno(exc)})") from exc
    finally:
        os.close(descriptor)


def _read_regular_path(path: Path, *, where: str, limit: int) -> tuple[bytes, os.stat_result]:
    parent = _open_directory_chain(path.parent)
    try:
        return _read_regular_at(parent, path.name, where=where, limit=limit)
    finally:
        os.close(parent)


def _ownership(content: bytes) -> str:
    try:
        first_lines = content.decode("utf-8").splitlines()[:8]
    except UnicodeDecodeError:
        return "unmanaged"
    if renderer.MANAGED_MARKER in first_lines:
        return "canonical"
    if renderer.LEGACY_MARKER in first_lines:
        return "legacy"
    return "unmanaged"


def _empty_snapshot() -> TargetSnapshot:
    empty = _canonical_digest([])
    return TargetSnapshot(
        exists=False,
        sha256=empty,
        canonical_sha256=empty,
        legacy_sha256=empty,
        unrelated_sha256=empty,
        entries=(),
    )


def _snapshot_directory_fd(directory_fd: int) -> TargetSnapshot:
    metadata = _validate_owned_directory(directory_fd, "target")
    entries: list[InventoryEntry] = []
    total = 0
    try:
        names = sorted(os.listdir(directory_fd))
    except OSError as exc:
        raise SyncError(f"target directory is unreadable ({_safe_errno(exc)})") from exc
    for name in names:
        if name.startswith(".verified-workflows-"):
            raise SyncError("target contains an incomplete managed-profile control file")
        if Path(name).suffix == ".toml" and not SAFE_NAME.fullmatch(name):
            raise SyncError(f"unsafe Codex agent filename {name!r}")
        content, child = _read_regular_at(
            directory_fd,
            name,
            where=f"target entry {name}",
        )
        total += len(content)
        if total > MAX_PROFILE_SET_BYTES:
            raise SyncError("target profile inventory exceeds the 16 MiB ceiling")
        if Path(name).suffix == ".toml":
            try:
                tomllib.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
                raise SyncError(f"target entry {name} is invalid TOML") from exc
        entries.append(
            InventoryEntry(
                name=name,
                mode=stat.S_IMODE(child.st_mode),
                size=len(content),
                sha256=_sha256(content),
                ownership=_ownership(content),
                device=child.st_dev,
                inode=child.st_ino,
                mtime_ns=child.st_mtime_ns,
            )
        )
    rendered = [entry.to_jsonable() for entry in entries]

    def partition(ownership: str) -> str:
        return _canonical_digest(
            [entry.to_jsonable() for entry in entries if entry.ownership == ownership]
        )

    return TargetSnapshot(
        exists=True,
        sha256=_canonical_digest(rendered),
        canonical_sha256=partition("canonical"),
        legacy_sha256=partition("legacy"),
        unrelated_sha256=partition("unmanaged"),
        entries=tuple(entries),
        directory_device=metadata.st_dev,
        directory_inode=metadata.st_ino,
    )


def _transaction_exists(target: TargetSpec) -> bool:
    transaction = _transaction_dir(target)
    try:
        metadata = transaction.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise SyncError(f"transaction state is unreadable ({_safe_errno(exc)})") from exc
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
        raise SyncError("managed-profile transaction must be an owned real directory")
    if stat.S_IMODE(metadata.st_mode) != 0o700:
        raise SyncError("managed-profile transaction must have mode 0700")
    return True


def snapshot_target(target: TargetSpec, *, allow_transaction: bool = False) -> TargetSnapshot:
    """Return a closed digest inventory without following target or entry symlinks."""

    if _transaction_exists(target) and not allow_transaction:
        raise SyncError("an incomplete managed-profile transaction requires --recover")
    if not target.path.parent.exists():
        _assert_no_symlink_components(target.path.parent)
        return _empty_snapshot()
    parent_fd = _open_parent(target)
    try:
        target_fd, _created = _open_target_from_parent(target, parent_fd)
        if target_fd is None:
            return _empty_snapshot()
        try:
            _assert_target_link(target, parent_fd, target_fd)
            return _snapshot_directory_fd(target_fd)
        finally:
            os.close(target_fd)
    finally:
        os.close(parent_fd)


def _same_pre_state(first: TargetSnapshot, second: TargetSnapshot) -> bool:
    if first.exists != second.exists or first.sha256 != second.sha256:
        return False
    first_rows = {entry.name: entry.identity() for entry in first.entries}
    second_rows = {entry.name: entry.identity() for entry in second.entries}
    return first_rows == second_rows


def plan_sync(
    bundle: renderer.RenderBundle,
    target: TargetSpec,
    pre_state: TargetSnapshot,
    *,
    migrate_legacy: bool = False,
    remove_stale: bool = False,
) -> SyncPlan:
    """Plan five-profile reconciliation without mutating the target."""

    profiles = {profile.filename: profile for profile in bundle.profiles}
    if set(profiles) != {
        f"{name}.toml" for name in renderer.RUNTIME_AGENT_NAMES.values()
    }:
        raise SyncError("render bundle does not contain the exact five execution profiles")
    actions: list[SyncAction] = []
    for name, profile in profiles.items():
        current = pre_state.entry(name)
        if current is None:
            actions.append(
                SyncAction("install", name, None, profile.sha256, "absent", "missing target")
            )
        elif current.ownership == "unmanaged":
            actions.append(
                SyncAction(
                    "conflict",
                    name,
                    current.sha256,
                    profile.sha256,
                    "unmanaged",
                    "unmanaged target uses a managed profile name",
                )
            )
        elif current.ownership == "legacy" and not migrate_legacy:
            actions.append(
                SyncAction(
                    "conflict",
                    name,
                    current.sha256,
                    profile.sha256,
                    "legacy",
                    "legacy ownership requires explicit migration",
                )
            )
        elif current.sha256 == profile.sha256 and current.ownership == "canonical":
            actions.append(
                SyncAction(
                    "unchanged",
                    name,
                    current.sha256,
                    profile.sha256,
                    "canonical",
                    "already current",
                )
            )
        else:
            action = "replace-legacy" if current.ownership == "legacy" else "update"
            actions.append(
                SyncAction(
                    action,
                    name,
                    current.sha256,
                    profile.sha256,
                    current.ownership,
                    "managed target differs",
                )
            )
    for current in pre_state.entries:
        if current.name in profiles or current.ownership == "unmanaged":
            continue
        if current.ownership == "legacy" and not migrate_legacy:
            action = "conflict"
            reason = "legacy ownership requires explicit migration"
        elif current.ownership == "legacy":
            action = "remove-legacy"
            reason = "explicit migration removes a stale legacy profile"
        elif remove_stale:
            action = "remove-stale"
            reason = "explicit cleanup removes a stale canonical profile"
        else:
            action = "preserve-stale"
            reason = "stale canonical profile preserved without --remove-stale"
        actions.append(
            SyncAction(
                action,
                current.name,
                current.sha256,
                None if action.startswith("remove-") else current.sha256,
                current.ownership,
                reason,
            )
        )
    return SyncPlan(
        bundle=bundle,
        target=target,
        pre_state=pre_state,
        actions=tuple(actions),
        migrate_legacy=migrate_legacy,
        remove_stale=remove_stale,
    )


def _profile_actions(plan: SyncPlan) -> dict[str, str]:
    return {
        renderer.EXECUTION_CLASS_BY_AGENT_NAME[Path(action.name).stem]: action.action
        for action in plan.actions
        if Path(action.name).stem in renderer.EXECUTION_CLASS_BY_AGENT_NAME
    }


def _snapshot_receipt(snapshot: TargetSnapshot) -> dict[str, Any]:
    return {
        "exists": snapshot.exists,
        "sha256": snapshot.sha256,
        "canonical_sha256": snapshot.canonical_sha256,
        "legacy_sha256": snapshot.legacy_sha256,
        "unrelated_sha256": snapshot.unrelated_sha256,
        "counts": snapshot.counts(),
    }


def _receipt(
    plan: SyncPlan,
    *,
    operation: str,
    result: str,
    post_state: TargetSnapshot | None = None,
    rollback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rendered = renderer.bundle_receipt(
        plan.bundle,
        profile_actions=_profile_actions(plan),
    )
    changed = any(action.action in CHANGED_ACTIONS for action in plan.actions)
    receipt = {
        "schema_version": 1,
        "operation": operation,
        "mode": "real-profile" if plan.target.real_profile else "isolated-profile",
        "result": result,
        "claim": "profile-presence-is-configuration-not-runtime-proof",
        "target": {
            "kind": plan.target.kind,
            "relative_root": "agents/",
            "real_profile": plan.target.real_profile,
            "isolated_target": plan.target.isolated_target,
            "real_profile_mutated": (
                operation == "apply"
                and plan.target.real_profile
                and result == "verified"
                and changed
            ),
        },
        "catalog": rendered["catalog"],
        "registry": rendered["registry"],
        "roles": rendered["roles"],
        "profiles": rendered["profiles"],
        "pre_state": _snapshot_receipt(plan.pre_state),
        "actions": [action.to_jsonable() for action in plan.actions],
        "readback": None,
        "rollback": rollback
        or {
            "journaled": False,
            "attempted": False,
            "completed": False,
            "verified": False,
            "cleanup_pending": False,
        },
    }
    if post_state is not None:
        receipt["readback"] = {
            **_snapshot_receipt(post_state),
            "profile_sha256": {
                profile.execution_class: profile.sha256 for profile in plan.bundle.profiles
            },
            "verified": result == "verified",
        }
    return receipt


def dry_run(plan: SyncPlan) -> dict[str, Any]:
    """Return a sanitized plan without creating a target, lock, journal, or file."""

    result = "blocked" if plan.conflicts() else "planned"
    return _receipt(plan, operation="dry-run", result=result)


class _TargetLock:
    """Persistent inode lock; the lock file is never unlinked."""

    def __init__(self, target: TargetSpec) -> None:
        self.target = target
        self.fd: int | None = None

    def __enter__(self) -> _TargetLock:
        parent_fd = _open_parent(self.target)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            try:
                descriptor = os.open(_lock_name(self.target), flags, 0o600, dir_fd=parent_fd)
            except OSError as exc:
                raise SyncError(
                    f"managed-profile lock could not be opened ({_safe_errno(exc)})"
                ) from exc
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or metadata.st_uid != os.getuid()
                or metadata.st_mode & 0o022
            ):
                os.close(descriptor)
                raise SyncError(
                    "managed-profile lock must be an owned single-link non-writable regular file"
                )
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            locked = os.fstat(descriptor)
            if (locked.st_dev, locked.st_ino) != (metadata.st_dev, metadata.st_ino):
                os.close(descriptor)
                raise SyncError("managed-profile lock identity changed")
            self.fd = descriptor
            return self
        finally:
            os.close(parent_fd)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.fd is None:
            return
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        self.fd = None


def _write_owned(path: Path, content: bytes, *, mode: int = 0o600) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, mode)
    except OSError as exc:
        raise SyncError(f"transaction file could not be created ({_safe_errno(exc)})") from exc
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)


def _fsync_dir(path: Path) -> None:
    try:
        descriptor = os.open(path, _directory_flags())
    except OSError as exc:
        raise SyncError(f"transaction directory is unreadable ({_safe_errno(exc)})") from exc
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_manifest(transaction: Path, manifest: dict[str, Any]) -> None:
    temporary = transaction / ".manifest.json.tmp"
    if temporary.exists() or temporary.is_symlink():
        content, _metadata = _read_regular_path(
            temporary,
            where="transaction manifest temporary",
            limit=MAX_PROFILE_BYTES,
        )
        if content:
            raise SyncError("nonempty transaction manifest temporary requires recovery")
        temporary.unlink()
    _write_owned(
        temporary,
        (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode(),
    )
    os.replace(temporary, transaction / "manifest.json")
    _fsync_dir(transaction)


def _manifest_action(action: SyncAction) -> dict[str, Any]:
    return {
        "action": action.action,
        "name": action.name,
        "before_sha256": action.before_sha256,
        "after_sha256": action.after_sha256,
    }


def _prepare_transaction(
    plan: SyncPlan,
    target_fd: int | None,
) -> tuple[Path, dict[str, Any]]:
    transaction = _transaction_dir(plan.target)
    if _transaction_exists(plan.target):
        raise SyncError("an incomplete managed-profile transaction requires --recover")
    prior: dict[str, dict[str, Any]] = {}
    for action in plan.actions:
        if action.action in NONMUTATING_ACTIONS:
            continue
        current = plan.pre_state.entry(action.name)
        prior[action.name] = {
            "present": current is not None,
            "sha256": current.sha256 if current is not None else None,
            "mode": current.mode if current is not None else None,
        }
    manifest = {
        "schema_version": TRANSACTION_SCHEMA_VERSION,
        "state": "preparing",
        "pre_state": _snapshot_receipt(plan.pre_state),
        "files": prior,
        "actions": [
            _manifest_action(action)
            for action in plan.actions
            if action.action not in NONMUTATING_ACTIONS
        ],
        "expected_profiles": {
            profile.filename: profile.sha256 for profile in plan.bundle.profiles
        },
        "post_state_sha256": None,
    }
    try:
        transaction.mkdir(mode=0o700)
        _write_manifest(transaction, manifest)
        stage = transaction / "stage"
        backup = transaction / "backup"
        removed = transaction / "removed"
        stage.mkdir(mode=0o700)
        backup.mkdir(mode=0o700)
        removed.mkdir(mode=0o700)
    except OSError as exc:
        raise SyncError(f"transaction could not be created ({_safe_errno(exc)})") from exc
    profiles = {profile.filename: profile for profile in plan.bundle.profiles}
    try:
        for name, profile in profiles.items():
            try:
                tomllib.loads(profile.content.decode("utf-8"))
            except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
                raise SyncError(f"generated profile {name} is invalid before staging") from exc
            _write_owned(stage / name, profile.content)
        for action in plan.actions:
            if action.action in NONMUTATING_ACTIONS:
                continue
            current = plan.pre_state.entry(action.name)
            if current is None:
                continue
            if target_fd is None:
                raise SyncError("planned pre-state disappeared before journaling")
            content, metadata = _read_regular_at(
                target_fd,
                action.name,
                where=f"pre-state {action.name}",
            )
            if (
                _sha256(content) != current.sha256
                or (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns)
                != current.identity()
            ):
                raise SyncError(f"pre-state {action.name} changed before journaling")
            _write_owned(backup / action.name, content, mode=stat.S_IMODE(metadata.st_mode))
        _fsync_dir(stage)
        _fsync_dir(backup)
        _fsync_dir(removed)
        _fsync_dir(transaction)
        manifest["state"] = "prepared"
        _write_manifest(transaction, manifest)
        return transaction, manifest
    except BaseException:
        try:
            _cleanup_transaction(transaction)
        except (OSError, SyncError):
            pass
        raise


def _recheck_action_target(
    plan: SyncPlan,
    target_fd: int,
    action: SyncAction,
) -> None:
    current = plan.pre_state.entry(action.name)
    if current is None:
        try:
            os.stat(action.name, dir_fd=target_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        except OSError as exc:
            raise SyncError(
                f"target {action.name} could not be rechecked ({_safe_errno(exc)})"
            ) from exc
        raise SyncError(f"target {action.name} appeared after pre-state capture")
    content, metadata = _read_regular_at(
        target_fd,
        action.name,
        where=f"target {action.name}",
    )
    if (
        _sha256(content) != current.sha256
        or (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns)
        != current.identity()
    ):
        raise SyncError(f"target {action.name} changed after pre-state capture")


def _move_and_validate_current(
    plan: SyncPlan,
    target_fd: int,
    removed_fd: int,
    action: SyncAction,
    index: int,
) -> str:
    """Move the current path first, then validate the exact inode now held in the journal."""

    expected = plan.pre_state.entry(action.name)
    if expected is None:
        raise SyncError(f"target {action.name} has no planned pre-state to move")
    removed_name = f"{index}-{action.name}"
    try:
        os.rename(
            action.name,
            removed_name,
            src_dir_fd=target_fd,
            dst_dir_fd=removed_fd,
        )
    except OSError as exc:
        raise SyncError(
            f"target {action.name} could not enter the journal ({_safe_errno(exc)})"
        ) from exc
    try:
        content, metadata = _read_regular_at(
            removed_fd,
            removed_name,
            where=f"journaled target {action.name}",
        )
    except SyncError as exc:
        try:
            os.link(
                removed_name,
                action.name,
                src_dir_fd=removed_fd,
                dst_dir_fd=target_fd,
                follow_symlinks=False,
            )
            os.unlink(removed_name, dir_fd=removed_fd)
        except OSError as restore_exc:
            raise SyncError(
                f"manual conflict: unsafe substituted target {action.name} is retained "
                "in the transaction"
            ) from restore_exc
        raise SyncError(f"target {action.name} changed at the mutation boundary") from exc
    matches = (
        _sha256(content) == expected.sha256
        and (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns)
        == expected.identity()
    )
    if matches:
        return removed_name
    try:
        os.link(
            removed_name,
            action.name,
            src_dir_fd=removed_fd,
            dst_dir_fd=target_fd,
            follow_symlinks=False,
        )
        os.unlink(removed_name, dir_fd=removed_fd)
    except OSError as exc:
        raise SyncError(
            f"target {action.name} changed at the mutation boundary; "
            "substituted bytes retained in the transaction"
        ) from exc
    raise SyncError(f"target {action.name} changed at the mutation boundary")


def _expected_canonical(plan: SyncPlan) -> dict[str, str]:
    expected = {profile.filename: profile.sha256 for profile in plan.bundle.profiles}
    for action in plan.actions:
        if action.action == "preserve-stale" and action.after_sha256 is not None:
            expected[action.name] = action.after_sha256
    return expected


def _verify_readback(plan: SyncPlan, target_fd: int) -> TargetSnapshot:
    post = _snapshot_directory_fd(target_fd)
    canonical = {
        entry.name: entry.sha256 for entry in post.entries if entry.ownership == "canonical"
    }
    legacy = [entry.name for entry in post.entries if entry.ownership == "legacy"]
    if canonical != _expected_canonical(plan) or legacy:
        raise SyncError(
            f"installed profile readback mismatch: canonical={sorted(canonical)} legacy={legacy}"
        )
    if post.unrelated_sha256 != plan.pre_state.unrelated_sha256:
        raise SyncError("unmanaged profile inventory changed during apply")
    return post


def _read_manifest(transaction: Path) -> dict[str, Any]:
    content, _metadata = _read_regular_path(
        transaction / "manifest.json",
        where="transaction manifest",
        limit=MAX_PROFILE_BYTES,
    )
    try:
        manifest = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SyncError("transaction manifest is invalid JSON") from exc
    if not isinstance(manifest, dict):
        raise SyncError("transaction manifest must be an object")
    required = {
        "schema_version",
        "state",
        "pre_state",
        "files",
        "actions",
        "expected_profiles",
        "post_state_sha256",
    }
    if set(manifest) != required:
        raise SyncError("transaction manifest fields are invalid")
    if manifest["schema_version"] != TRANSACTION_SCHEMA_VERSION:
        raise SyncError("transaction manifest schema is unsupported")
    if manifest["state"] not in {"preparing", "prepared", "applying", "committed"}:
        raise SyncError("transaction manifest state is invalid")
    if not isinstance(manifest["pre_state"], dict):
        raise SyncError("transaction manifest pre-state is invalid")
    if not isinstance(manifest["files"], dict) or not isinstance(manifest["actions"], list):
        raise SyncError("transaction manifest journal is invalid")
    if not isinstance(manifest["expected_profiles"], dict):
        raise SyncError("transaction manifest expected profiles are invalid")
    return manifest


def _safe_action_rows(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in manifest["actions"]:
        if not isinstance(row, dict) or set(row) != {
            "action",
            "name",
            "before_sha256",
            "after_sha256",
        }:
            raise SyncError("transaction action journal is invalid")
        name = row["name"]
        if not isinstance(name, str) or not SAFE_NAME.fullmatch(name) or name in result:
            raise SyncError("transaction action name is unsafe or duplicated")
        if row["action"] not in CHANGED_ACTIONS:
            raise SyncError("transaction action type is invalid")
        for key in ("before_sha256", "after_sha256"):
            value = row[key]
            if value is not None and (not isinstance(value, str) or not HEX64.fullmatch(value)):
                raise SyncError("transaction action digest is invalid")
        result[name] = row
    return result


def _safe_prior_rows(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    actions = _safe_action_rows(manifest)
    files = manifest["files"]
    if set(files) != set(actions):
        raise SyncError("transaction prior-state inventory does not match actions")
    result: dict[str, dict[str, Any]] = {}
    for name, row in files.items():
        if not isinstance(row, dict) or set(row) != {"present", "sha256", "mode"}:
            raise SyncError("transaction prior-state row is invalid")
        if not isinstance(row["present"], bool):
            raise SyncError("transaction prior-state presence is invalid")
        if row["present"]:
            if not isinstance(row["sha256"], str) or not HEX64.fullmatch(row["sha256"]):
                raise SyncError("transaction prior-state digest is invalid")
            if not isinstance(row["mode"], int) or row["mode"] & 0o022:
                raise SyncError("transaction prior-state mode is invalid")
        elif row["sha256"] is not None or row["mode"] is not None:
            raise SyncError("absent transaction prior-state must not contain file metadata")
        result[name] = row
    return result


def _current_entry_at(target_fd: int, name: str) -> tuple[bytes, os.stat_result] | None:
    try:
        os.stat(name, dir_fd=target_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SyncError(f"rollback target could not be inspected ({_safe_errno(exc)})") from exc
    return _read_regular_at(target_fd, name, where=f"rollback target {name}")


def _restore_journal(
    target_fd: int,
    transaction: Path,
    manifest: dict[str, Any],
    *,
    owned_identities: Mapping[str, tuple[int, int]] | None = None,
) -> tuple[list[str], bool]:
    backup = transaction / "backup"
    actions = _safe_action_rows(manifest)
    prior = _safe_prior_rows(manifest)
    errors: list[str] = []
    mutated = False
    backup_fd = _open_directory_chain(backup)
    try:
        for name in reversed(tuple(actions)):
            action = actions[name]
            state = prior[name]
            try:
                current = _current_entry_at(target_fd, name)
                current_owned = (
                    current is not None
                    and owned_identities is not None
                    and owned_identities.get(name)
                    == (current[1].st_dev, current[1].st_ino)
                )
                if state["present"]:
                    if current is not None and _sha256(current[0]) == state["sha256"]:
                        continue
                    allowed_current = action["after_sha256"]
                    if current is not None and not current_owned and (
                        allowed_current is None or _sha256(current[0]) != allowed_current
                    ):
                        raise SyncError("current bytes are not owned by this transaction")
                    backup_content, _backup_meta = _read_regular_at(
                        backup_fd,
                        name,
                        where=f"rollback backup {name}",
                    )
                    if _sha256(backup_content) != state["sha256"]:
                        raise SyncError("backup digest drifted")
                    os.replace(name, name, src_dir_fd=backup_fd, dst_dir_fd=target_fd)
                    mutated = True
                else:
                    if current is None:
                        continue
                    if not current_owned and (
                        action["after_sha256"] is None
                        or _sha256(current[0]) != action["after_sha256"]
                    ):
                        raise SyncError("current bytes are not owned by this transaction")
                    os.unlink(name, dir_fd=target_fd)
                    mutated = True
            except (OSError, SyncError) as exc:
                detail = _safe_errno(exc) if isinstance(exc, OSError) else str(exc)
                errors.append(f"{name}: {detail}")
    finally:
        os.close(backup_fd)
    try:
        os.fsync(target_fd)
    except OSError as exc:
        errors.append(f"target fsync failed: {_safe_errno(exc)}")
    return errors, mutated


def _cleanup_transaction(transaction: Path) -> None:
    """Remove a journal with its manifest last so partial cleanup stays recoverable."""

    try:
        metadata = transaction.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            raise SyncError("transaction cleanup target is not an owned 0700 directory")
        for directory_name in ("stage", "backup", "removed"):
            directory = transaction / directory_name
            if not directory.exists():
                continue
            directory_meta = directory.lstat()
            if (
                not stat.S_ISDIR(directory_meta.st_mode)
                or directory_meta.st_uid != os.getuid()
                or stat.S_IMODE(directory_meta.st_mode) != 0o700
            ):
                raise SyncError("transaction child is not an owned 0700 directory")
            for child in directory.iterdir():
                try:
                    content, _child_meta = _read_regular_path(
                        child,
                        where="transaction cleanup entry",
                        limit=MAX_PROFILE_BYTES,
                    )
                except SyncError as exc:
                    if directory_name == "removed":
                        raise SyncError(
                            "manual conflict: unsafe substituted entry is retained in the "
                            "transaction removed journal"
                        ) from exc
                    raise
                del content
                child.unlink()
            directory.rmdir()
        temporary = transaction / ".manifest.json.tmp"
        if temporary.exists() or temporary.is_symlink():
            _read_regular_path(
                temporary,
                where="transaction cleanup manifest temporary",
                limit=MAX_PROFILE_BYTES,
            )
            temporary.unlink()
        _fsync_dir(transaction)
        manifest = transaction / "manifest.json"
        if manifest.exists() or manifest.is_symlink():
            _read_regular_path(
                manifest,
                where="transaction cleanup manifest",
                limit=MAX_PROFILE_BYTES,
            )
            manifest.unlink()
        _fsync_dir(transaction)
        transaction.rmdir()
        _fsync_dir(transaction.parent)
    except OSError as exc:
        raise SyncError(f"transaction cleanup failed ({_safe_errno(exc)})") from exc


def _remove_created_target(target: TargetSpec, parent_fd: int, target_fd: int) -> None:
    _assert_target_link(target, parent_fd, target_fd)
    if os.listdir(target_fd):
        raise SyncError("new target directory is not empty after rollback")
    os.rmdir(target.path.name, dir_fd=parent_fd)
    os.fsync(parent_fd)


def _rollback_apply(
    plan: SyncPlan,
    transaction: Path,
    manifest: dict[str, Any],
    parent_fd: int,
    target_fd: int,
    *,
    created_target: bool,
    owned_identities: Mapping[str, tuple[int, int]],
) -> tuple[dict[str, Any], int | None]:
    errors, _mutated = _restore_journal(
        target_fd,
        transaction,
        manifest,
        owned_identities=owned_identities,
    )
    remaining_fd: int | None = target_fd
    if created_target and not errors:
        try:
            _remove_created_target(plan.target, parent_fd, target_fd)
            os.close(target_fd)
            remaining_fd = None
        except (OSError, SyncError) as exc:
            detail = _safe_errno(exc) if isinstance(exc, OSError) else str(exc)
            errors.append(detail)
    try:
        restored = snapshot_target(plan.target, allow_transaction=True)
        verified = (
            restored.exists == plan.pre_state.exists
            and restored.sha256 == plan.pre_state.sha256
        )
        if not verified:
            errors.append("restored target does not match the exact pre-state")
    except SyncError as exc:
        verified = False
        errors.append(str(exc))
    result = {
        "journaled": True,
        "attempted": True,
        "completed": not errors,
        "verified": verified and not errors,
        "cleanup_pending": False,
        "errors": errors,
    }
    if result["verified"]:
        try:
            _cleanup_transaction(transaction)
        except SyncError as exc:
            result["cleanup_pending"] = True
            result["errors"].append(str(exc))
    return result, remaining_fd


def _authorize_mutation(
    target: TargetSpec,
    pre_state_sha256: str,
    *,
    expected_pre_state_sha256: str | None,
    allow_real_profile: bool,
    destructive: bool,
) -> None:
    if expected_pre_state_sha256 is not None and not HEX64.fullmatch(
        expected_pre_state_sha256
    ):
        raise SyncError("expected pre-state digest must be 64 lowercase hex characters")
    if target.real_profile and (
        not allow_real_profile or expected_pre_state_sha256 is None
    ):
        raise SyncError(
            "real-profile mutation requires opt-in and an exact expected pre-state digest"
        )
    if destructive and expected_pre_state_sha256 is None:
        raise SyncError("destructive cleanup requires an exact expected pre-state digest")
    if (
        expected_pre_state_sha256 is not None
        and expected_pre_state_sha256 != pre_state_sha256
    ):
        raise SyncError("expected pre-state digest does not match the planned target")


def apply_sync(
    plan: SyncPlan,
    *,
    expected_pre_state_sha256: str | None = None,
    allow_real_profile: bool = False,
    fault_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Apply a journaled plan and prove exact readback or exact rollback."""

    if plan.conflicts():
        names = [action.name for action in plan.conflicts()]
        raise SyncError(f"unmanaged or legacy profile conflicts block apply: {names}")
    _authorize_mutation(
        plan.target,
        plan.pre_state.sha256,
        expected_pre_state_sha256=expected_pre_state_sha256,
        allow_real_profile=allow_real_profile,
        destructive=plan.migrate_legacy or plan.remove_stale,
    )
    with _TargetLock(plan.target):
        current = snapshot_target(plan.target)
        if not _same_pre_state(current, plan.pre_state):
            raise SyncError("target changed between plan and apply")
        parent_fd = _open_parent(plan.target)
        target_fd: int | None = None
        transaction: Path | None = None
        owned_identities: dict[str, tuple[int, int]] = {}
        try:
            target_fd, created_target = _open_target_from_parent(
                plan.target,
                parent_fd,
                create=False,
            )
            transaction, manifest = _prepare_transaction(
                plan,
                target_fd,
            )
            manifest["state"] = "applying"
            _write_manifest(transaction, manifest)
            if target_fd is None:
                target_fd, created_target = _open_target_from_parent(
                    plan.target,
                    parent_fd,
                    create=True,
                )
            assert target_fd is not None
            _assert_target_link(plan.target, parent_fd, target_fd)
            stage_fd = _open_directory_chain(transaction / "stage")
            removed_fd = _open_directory_chain(transaction / "removed")
            try:
                for index, action in enumerate(plan.actions):
                    if action.action in NONMUTATING_ACTIONS:
                        continue
                    _assert_target_link(plan.target, parent_fd, target_fd)
                    _recheck_action_target(plan, target_fd, action)
                    if action.action == "install":
                        try:
                            os.link(
                                action.name,
                                action.name,
                                src_dir_fd=stage_fd,
                                dst_dir_fd=target_fd,
                                follow_symlinks=False,
                            )
                            os.unlink(action.name, dir_fd=stage_fd)
                        except OSError as exc:
                            if exc.errno == errno.EEXIST:
                                raise SyncError(
                                    f"target {action.name} appeared at the install boundary"
                                ) from exc
                            raise
                    elif action.action in {"update", "replace-legacy"}:
                        _move_and_validate_current(
                            plan,
                            target_fd,
                            removed_fd,
                            action,
                            index,
                        )
                        try:
                            os.link(
                                action.name,
                                action.name,
                                src_dir_fd=stage_fd,
                                dst_dir_fd=target_fd,
                                follow_symlinks=False,
                            )
                            os.unlink(action.name, dir_fd=stage_fd)
                        except OSError as exc:
                            if exc.errno == errno.EEXIST:
                                raise SyncError(
                                    f"target {action.name} appeared at the update boundary"
                                ) from exc
                            raise
                    elif action.action in {"remove-stale", "remove-legacy"}:
                        _move_and_validate_current(
                            plan,
                            target_fd,
                            removed_fd,
                            action,
                            index,
                        )
                    else:  # pragma: no cover - plan_sync is closed
                        raise SyncError(f"unknown sync action {action.action!r}")
                    if action.action in {"install", "update", "replace-legacy"}:
                        installed = os.stat(
                            action.name,
                            dir_fd=target_fd,
                            follow_symlinks=False,
                        )
                        owned_identities[action.name] = (installed.st_dev, installed.st_ino)
                    if fault_hook is not None:
                        fault_hook(f"after:{action.name}")
            finally:
                os.close(stage_fd)
                os.close(removed_fd)
            os.fsync(target_fd)
            _fsync_dir(transaction)
            if fault_hook is not None:
                fault_hook("before-readback")
            _assert_target_link(plan.target, parent_fd, target_fd)
            post = _verify_readback(plan, target_fd)
        except BaseException as exc:
            if transaction is None or target_fd is None:
                if target_fd is not None:
                    os.close(target_fd)
                    target_fd = None
                if current.exists is False:
                    try:
                        orphan_fd, _created = _open_target_from_parent(
                            plan.target,
                            parent_fd,
                        )
                        if orphan_fd is not None:
                            try:
                                _remove_created_target(plan.target, parent_fd, orphan_fd)
                            finally:
                                os.close(orphan_fd)
                    except (OSError, SyncError):
                        pass
                raise
            rollback, target_fd = _rollback_apply(
                plan,
                transaction,
                manifest,
                parent_fd,
                target_fd,
                created_target=created_target,
                owned_identities=owned_identities,
            )
            if target_fd is not None:
                os.close(target_fd)
                target_fd = None
            if not rollback["verified"]:
                raise SyncError(
                    "managed-profile apply failed and rollback could not be proved; "
                    "manual conflict transaction retained"
                ) from exc
            if rollback["cleanup_pending"]:
                raise SyncError(
                    "managed-profile apply failed; exact pre-state restored; "
                    "manual conflict cleanup retained"
                ) from exc
            raise SyncError(
                f"managed-profile apply failed; exact pre-state restored: {type(exc).__name__}"
            ) from exc
        else:
            manifest["state"] = "committed"
            manifest["post_state_sha256"] = post.sha256
            _write_manifest(transaction, manifest)
            rollback = {
                "journaled": True,
                "attempted": False,
                "completed": False,
                "verified": False,
                "cleanup_pending": False,
            }
            try:
                _cleanup_transaction(transaction)
            except SyncError:
                rollback["cleanup_pending"] = True
            return _receipt(
                plan,
                operation="apply",
                result="verified",
                post_state=post,
                rollback=rollback,
            )
        finally:
            if target_fd is not None:
                os.close(target_fd)
            os.close(parent_fd)


def _recovery_receipt(
    target: TargetSpec,
    *,
    prior_state: str,
    pre_state: dict[str, Any],
    post_state: TargetSnapshot,
    mutated: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "operation": "recover",
        "mode": "real-profile" if target.real_profile else "isolated-profile",
        "result": "verified",
        "claim": "transaction-recovery-only",
        "target": {
            "kind": target.kind,
            "relative_root": "agents/",
            "real_profile": target.real_profile,
            "isolated_target": target.isolated_target,
            "real_profile_mutated": target.real_profile and mutated,
        },
        "prior_transaction_state": prior_state,
        "pre_state": pre_state,
        "readback": _snapshot_receipt(post_state),
    }


def recover_sync(
    target: TargetSpec,
    *,
    expected_pre_state_sha256: str | None = None,
    allow_real_profile: bool = False,
) -> dict[str, Any]:
    """Recover one prepared/applying transaction or clean one committed transaction."""

    with _TargetLock(target):
        if not _transaction_exists(target):
            raise SyncError("no managed-profile transaction requires recovery")
        transaction = _transaction_dir(target)
        contents = list(transaction.iterdir())
        bootstrap_residue = (
            not (transaction / "manifest.json").exists()
            and {child.name for child in contents} <= {".manifest.json.tmp"}
        )
        if bootstrap_residue:
            if expected_pre_state_sha256 is None:
                raise SyncError(
                    "bootstrap cleanup residue requires an expected pre-state digest"
                )
            _authorize_mutation(
                target,
                expected_pre_state_sha256,
                expected_pre_state_sha256=expected_pre_state_sha256,
                allow_real_profile=allow_real_profile,
                destructive=True,
            )
            current = snapshot_target(target, allow_transaction=True)
            if current.sha256 != expected_pre_state_sha256:
                raise SyncError("bootstrap cleanup target does not match the expected pre-state")
            _cleanup_transaction(transaction)
            return _recovery_receipt(
                target,
                prior_state="bootstrap-cleanup",
                pre_state={"exists": None, "sha256": expected_pre_state_sha256},
                post_state=current,
                mutated=False,
            )
        manifest = _read_manifest(transaction)
        pre_state = manifest["pre_state"]
        pre_sha = pre_state.get("sha256")
        pre_exists = pre_state.get("exists")
        if not isinstance(pre_sha, str) or not HEX64.fullmatch(pre_sha):
            raise SyncError("transaction pre-state digest is invalid")
        if not isinstance(pre_exists, bool):
            raise SyncError("transaction pre-state presence is invalid")
        _authorize_mutation(
            target,
            pre_sha,
            expected_pre_state_sha256=expected_pre_state_sha256,
            allow_real_profile=allow_real_profile,
            destructive=True,
        )
        state = manifest["state"]
        if state in {"preparing", "prepared"}:
            current = snapshot_target(target, allow_transaction=True)
            if current.exists != pre_exists or current.sha256 != pre_sha:
                raise SyncError("prepared transaction target no longer matches its pre-state")
            _cleanup_transaction(transaction)
            return _recovery_receipt(
                target,
                prior_state=state,
                pre_state=pre_state,
                post_state=current,
                mutated=False,
            )
        if state == "committed":
            current = snapshot_target(target, allow_transaction=True)
            post_sha = manifest["post_state_sha256"]
            if (
                not isinstance(post_sha, str)
                or not HEX64.fullmatch(post_sha)
                or current.sha256 != post_sha
            ):
                raise SyncError("committed transaction readback no longer matches")
            expected = manifest["expected_profiles"]
            if not all(
                isinstance(name, str)
                and SAFE_NAME.fullmatch(name)
                and isinstance(digest, str)
                and HEX64.fullmatch(digest)
                for name, digest in expected.items()
            ):
                raise SyncError("committed transaction profile inventory is invalid")
            installed = {
                entry.name: entry.sha256
                for entry in current.entries
                if entry.name in expected
            }
            if installed != expected:
                raise SyncError("committed transaction profile readback drifted")
            _cleanup_transaction(transaction)
            return _recovery_receipt(
                target,
                prior_state=state,
                pre_state=pre_state,
                post_state=current,
                mutated=False,
            )

        parent_fd = _open_parent(target)
        target_fd: int | None = None
        try:
            target_fd, _created = _open_target_from_parent(target, parent_fd)
            if target_fd is None:
                if pre_exists:
                    raise SyncError("applying transaction target is missing")
                current = snapshot_target(target, allow_transaction=True)
                if current.exists or current.sha256 != pre_sha:
                    raise SyncError("applying transaction target no longer matches its pre-state")
                _cleanup_transaction(transaction)
                return _recovery_receipt(
                    target,
                    prior_state=state,
                    pre_state=pre_state,
                    post_state=current,
                    mutated=False,
                )
            _assert_target_link(target, parent_fd, target_fd)
            errors, mutated = _restore_journal(target_fd, transaction, manifest)
            if errors:
                raise SyncError(
                    "transaction rollback could not be proved; manual conflict journal retained"
                )
            if not pre_exists:
                _remove_created_target(target, parent_fd, target_fd)
                mutated = True
                os.close(target_fd)
                target_fd = None
            current = snapshot_target(target, allow_transaction=True)
            if current.exists != pre_exists or current.sha256 != pre_sha:
                raise SyncError("recovered target does not match the exact pre-state")
            _cleanup_transaction(transaction)
            return _recovery_receipt(
                target,
                prior_state=state,
                pre_state=pre_state,
                post_state=current,
                mutated=mutated,
            )
        finally:
            if target_fd is not None:
                os.close(target_fd)
            os.close(parent_fd)


def build_plan(
    target: TargetSpec,
    *,
    catalog_snapshot: Path | None = None,
    migrate_legacy: bool = False,
    remove_stale: bool = False,
) -> SyncPlan:
    """Read one catalog snapshot, prove generated source, snapshot target, and plan."""

    registry = renderer.load_role_registry()
    if catalog_snapshot is None:
        catalog = renderer.CATALOG.read_catalog()
    else:
        catalog = renderer.load_catalog_snapshot(catalog_snapshot)
    bundle = renderer.render_bundle(registry, catalog)
    if catalog_snapshot is not None:
        renderer.check_generated(bundle)
    pre_state = snapshot_target(target)
    return plan_sync(
        bundle,
        target,
        pre_state,
        migrate_legacy=migrate_legacy,
        remove_stale=remove_stale,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-dir", type=Path)
    parser.add_argument("--isolated-target", action="store_true")
    parser.add_argument("--catalog-snapshot", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--recover", action="store_true")
    parser.add_argument("--migrate-legacy", action="store_true")
    parser.add_argument("--remove-stale", action="store_true")
    parser.add_argument("--allow-real-profile", action="store_true")
    parser.add_argument("--expected-pre-state-sha256")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        target = resolve_target(
            args.target_dir,
            isolated_target=args.isolated_target,
        )
        if args.recover:
            if args.migrate_legacy or args.remove_stale or args.catalog_snapshot is not None:
                raise SyncError("--recover does not accept planning or catalog options")
            payload = recover_sync(
                target,
                expected_pre_state_sha256=args.expected_pre_state_sha256,
                allow_real_profile=args.allow_real_profile,
            )
        else:
            plan = build_plan(
                target,
                catalog_snapshot=args.catalog_snapshot,
                migrate_legacy=args.migrate_legacy,
                remove_stale=args.remove_stale,
            )
            if args.apply:
                payload = apply_sync(
                    plan,
                    expected_pre_state_sha256=args.expected_pre_state_sha256,
                    allow_real_profile=args.allow_real_profile,
                )
            else:
                payload = dry_run(plan)
    except OSError as exc:
        print(
            f"verified-workflows profile sync failed: filesystem error ({_safe_errno(exc)})",
            file=sys.stderr,
        )
        return 1
    except (
        SyncError,
        renderer.RoleRegistryError,
        renderer.RESOLVER.TierResolverError,
        renderer.CATALOG.CatalogError,
    ) as exc:
        print(f"verified-workflows profile sync failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if payload["result"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
