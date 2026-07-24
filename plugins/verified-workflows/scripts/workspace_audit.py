#!/usr/bin/env python3
"""Capture and compare the lightweight root-owned workspace and Git audit."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence

import workflow_dispatch as dispatch


MAX_GIT_OUTPUT_BYTES = 4 * 1024 * 1024
GIT_OPERATION_FILES = frozenset(
    {
        "BISECT_LOG",
        "BISECT_NAMES",
        "BISECT_START",
        "CHERRY_PICK_HEAD",
        "FETCH_HEAD",
        "MERGE_HEAD",
        "MERGE_MSG",
        "ORIG_HEAD",
        "REBASE_HEAD",
        "REVERT_HEAD",
        "SQUASH_MSG",
    }
)
GIT_OPERATION_DIRS = frozenset({"logs", "rebase-apply", "rebase-merge", "sequencer"})


class WorkspaceAuditError(ValueError):
    """Raised when workspace ownership or Git-control state is unsafe."""


@dataclass(frozen=True, slots=True)
class WorkspaceAudit:
    repo_root: str
    head: str
    branch: str
    index_sha256: str
    git_control_sha256: str
    status_sha256: str
    status_entries: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class WorkspaceDelta:
    changed_paths: tuple[str, ...]
    attribution: str
    git_control_unchanged: bool


def _run_git(repo_root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise WorkspaceAuditError(f"git {' '.join(args)} failed") from exc
    if len(completed.stdout) > MAX_GIT_OUTPUT_BYTES:
        raise WorkspaceAuditError(f"git {' '.join(args)} exceeded the output ceiling")
    return completed.stdout


def _hash_file(path: Path) -> str:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return hashlib.sha256(b"").hexdigest()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_GIT_OUTPUT_BYTES:
        raise WorkspaceAuditError(f"Git control file {path.name!r} is not a bounded regular file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _status_entries(content: bytes) -> tuple[tuple[str, str], ...]:
    records = content.split(b"\0")
    entries: list[tuple[str, str]] = []
    skip_original = False
    for record in records:
        if not record:
            continue
        if skip_original:
            skip_original = False
            continue
        text = record.decode("utf-8", "surrogateescape")
        kind = text[:1]
        try:
            if kind == "1":
                path = text.split(" ", 8)[8]
            elif kind == "2":
                path = text.split(" ", 9)[9]
                skip_original = True
            elif kind in {"?", "!"}:
                path = text[2:]
            elif kind == "u":
                path = text.split(" ", 10)[10]
            else:
                raise ValueError
        except (IndexError, ValueError) as exc:
            raise WorkspaceAuditError("git porcelain-v2 output is malformed") from exc
        normalized = dispatch._repo_path(path, "git status path")
        entries.append((normalized, hashlib.sha256(record).hexdigest()))
    return tuple(sorted(entries))


def _workspace_path_digest(repo_root: Path, relative: str) -> str:
    path = repo_root / relative
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return hashlib.sha256(b"missing").hexdigest()
    mode = stat.S_IMODE(metadata.st_mode)
    if stat.S_ISREG(metadata.st_mode):
        if metadata.st_size > MAX_GIT_OUTPUT_BYTES:
            raise WorkspaceAuditError(f"workspace path {relative!r} exceeds the audit ceiling")
        payload = b"file\0" + f"{mode:o}\0".encode() + path.read_bytes()
    elif stat.S_ISLNK(metadata.st_mode):
        payload = b"symlink\0" + os.readlink(path).encode("utf-8", "surrogateescape")
    elif stat.S_ISDIR(metadata.st_mode):
        rows: list[bytes] = []
        for child in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
            child_relative = child.relative_to(repo_root).as_posix()
            rows.append(
                child_relative.encode("utf-8", "surrogateescape")
                + b"\0"
                + _workspace_path_digest(repo_root, child_relative).encode()
            )
            if sum(map(len, rows)) > MAX_GIT_OUTPUT_BYTES:
                raise WorkspaceAuditError(
                    f"workspace directory {relative!r} exceeds the audit ceiling"
                )
        payload = b"directory\0" + b"\n".join(rows)
    else:
        raise WorkspaceAuditError(f"workspace path {relative!r} has an unsupported file type")
    return hashlib.sha256(payload).hexdigest()


def _content_bound_entries(
    repo_root: Path,
    status: bytes,
    ignored: bytes,
) -> tuple[tuple[str, str], ...]:
    records = dict(_status_entries(status))
    for raw_path in ignored.split(b"\0"):
        if not raw_path:
            continue
        path = dispatch._repo_path(
            raw_path.decode("utf-8", "surrogateescape"), "ignored workspace path"
        )
        records.setdefault(path, hashlib.sha256(b"ignored").hexdigest())
    return tuple(
        sorted(
            (
                path,
                hashlib.sha256(
                    f"{record_sha}\0{_workspace_path_digest(repo_root, path)}".encode()
                ).hexdigest(),
            )
            for path, record_sha in records.items()
        )
    )


def _git_operation_digest(git_dir: Path) -> str:
    rows: list[bytes] = []
    selected = [git_dir / name for name in sorted(GIT_OPERATION_FILES | GIT_OPERATION_DIRS)]
    for path in selected:
        if not path.exists() and not path.is_symlink():
            continue
        candidates = [path]
        if path.is_dir() and not path.is_symlink():
            candidates.extend(sorted(path.rglob("*"), key=lambda item: item.as_posix()))
        for candidate in candidates:
            relative = candidate.relative_to(git_dir).as_posix()
            metadata = candidate.lstat()
            if stat.S_ISDIR(metadata.st_mode):
                rows.append(f"dir\0{relative}".encode())
            elif stat.S_ISREG(metadata.st_mode):
                if metadata.st_size > MAX_GIT_OUTPUT_BYTES:
                    raise WorkspaceAuditError(
                        f"Git operation file {relative!r} exceeds the audit ceiling"
                    )
                rows.append(
                    f"file\0{relative}\0{stat.S_IMODE(metadata.st_mode):o}\0".encode()
                    + hashlib.sha256(candidate.read_bytes()).hexdigest().encode()
                )
            else:
                raise WorkspaceAuditError(
                    f"Git operation path {relative!r} must be a regular file or directory"
                )
            if sum(map(len, rows)) > MAX_GIT_OUTPUT_BYTES:
                raise WorkspaceAuditError("Git operation state exceeds the audit ceiling")
    return hashlib.sha256(b"\n".join(rows)).hexdigest()


def _control_digest(repo_root: Path) -> str:
    refs = _run_git(repo_root, "for-each-ref", "--format=%(refname)%00%(objectname)")
    config = _run_git(repo_root, "config", "--local", "--null", "--list")
    git_dir_raw = _run_git(repo_root, "rev-parse", "--absolute-git-dir").decode().strip()
    git_dir = Path(git_dir_raw)
    hooks = git_dir / "hooks"
    hook_rows: list[str] = []
    if hooks.is_dir() and not hooks.is_symlink():
        for child in sorted(hooks.iterdir(), key=lambda item: item.name):
            if child.name.endswith(".sample"):
                continue
            metadata = child.lstat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_GIT_OUTPUT_BYTES:
                raise WorkspaceAuditError("Git hooks must be bounded regular files")
            hook_rows.append(
                f"{child.name}:{stat.S_IMODE(metadata.st_mode):o}:{hashlib.sha256(child.read_bytes()).hexdigest()}"
            )
    operation_sha256 = _git_operation_digest(git_dir)
    payload = (
        b"refs\0"
        + refs
        + b"\0config\0"
        + config
        + b"\0hooks\0"
        + "\n".join(hook_rows).encode()
        + b"\0operations\0"
        + operation_sha256.encode()
    )
    if len(payload) > MAX_GIT_OUTPUT_BYTES:
        raise WorkspaceAuditError("Git control state exceeds the bounded input ceiling")
    return hashlib.sha256(payload).hexdigest()


def capture_workspace_audit(repo_root: Path) -> WorkspaceAudit:
    root = repo_root.resolve()
    if _run_git(root, "rev-parse", "--show-toplevel").decode().strip() != root.as_posix():
        raise WorkspaceAuditError("workspace audit must run at the Git worktree root")
    head = _run_git(root, "rev-parse", "HEAD").decode().strip()
    branch = _run_git(root, "symbolic-ref", "--short", "HEAD").decode().strip()
    index_path_raw = _run_git(root, "rev-parse", "--git-path", "index").decode().strip()
    index_path = Path(index_path_raw)
    if not index_path.is_absolute():
        index_path = root / index_path
    status = _run_git(root, "status", "--porcelain=v2", "-z", "--untracked-files=all")
    ignored = _run_git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "-z")
    entries = _content_bound_entries(root, status, ignored)
    return WorkspaceAudit(
        repo_root=root.as_posix(),
        head=head,
        branch=branch,
        index_sha256=_hash_file(index_path),
        git_control_sha256=_control_digest(root),
        status_sha256=hashlib.sha256(repr(entries).encode()).hexdigest(),
        status_entries=entries,
    )


def _overlaps(path: str, allowed: str) -> bool:
    left = PurePosixPath(path)
    right = PurePosixPath(allowed)
    return left == right or left in right.parents or right in left.parents


def validate_attempt_audit(
    before: WorkspaceAudit,
    after: WorkspaceAudit,
    *,
    declared_writes: Sequence[str],
    concurrent_writable: bool = False,
    mutation_attribution: str | None = None,
) -> WorkspaceDelta:
    if before.repo_root != after.repo_root:
        raise WorkspaceAuditError("workspace audits belong to different repositories")
    controls = (
        before.head == after.head
        and before.branch == after.branch
        and before.index_sha256 == after.index_sha256
        and before.git_control_sha256 == after.git_control_sha256
    )
    if not controls:
        raise WorkspaceAuditError("worker changed HEAD, branch, index, refs, config, or hooks")
    if concurrent_writable and not mutation_attribution:
        raise WorkspaceAuditError("concurrent writable attempts require proven per-agent attribution")
    allowed = tuple(
        dispatch._repo_path(path, "declared write")
        for path in declared_writes
        if not path.startswith("unit:")
    )
    before_entries = dict(before.status_entries)
    after_entries = dict(after.status_entries)
    dirty_overlap = sorted(
        path for path in before_entries if any(_overlaps(path, item) for item in allowed)
    )
    if dirty_overlap:
        raise WorkspaceAuditError(
            f"declared write paths overlap pre-existing dirty state {dirty_overlap}"
        )
    changed = tuple(
        sorted(
            path
            for path in set(before_entries) | set(after_entries)
            if before_entries.get(path) != after_entries.get(path)
        )
    )
    outside = [path for path in changed if not any(_overlaps(path, item) for item in allowed)]
    if outside:
        raise WorkspaceAuditError(f"worker changed paths outside declared ownership {outside}")
    return WorkspaceDelta(
        changed_paths=changed,
        attribution=mutation_attribution or "root-quiescent-sequential",
        git_control_unchanged=True,
    )
