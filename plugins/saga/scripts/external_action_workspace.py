#!/usr/bin/env python3
"""Disposable, remote-stripped Git workspace for external CLI actions."""

from __future__ import annotations

import hashlib
import io
import re
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class WorkspaceError(RuntimeError):
    pass


MAX_PATCH_BYTES = 8 * 1024 * 1024
MAX_CONTEXT_ARCHIVE_BYTES = 64 * 1024 * 1024
SECRET_PATH_PARTS = frozenset(
    {".env", "secrets", "credentials", ".aws", ".ssh", ".gnupg", "private-keys"}
)
SECRET_CONTENT_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(rb"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    re.compile(rb"\bsk-proj-[A-Za-z0-9_-]{20,}\b"),
)


@dataclass(slots=True)
class Workspace:
    root: Path
    checkout: Path
    base_revision: str
    workspace_revision: str
    git_control_sha256: str

    @classmethod
    def create(
        cls,
        repo_root: Path,
        base_revision: str,
        *,
        visible_paths: tuple[str, ...] | None = None,
        required_paths: tuple[str, ...] = (),
    ) -> Workspace:
        root = Path(tempfile.mkdtemp(prefix="saga-external-action-"))
        checkout = root / "worktree"
        try:
            resolved_base = _git(
                repo_root, "rev-parse", "--verify", f"{base_revision}^{{commit}}"
            ).stdout.strip()
            if visible_paths is None:
                _run(
                    [
                        "git",
                        "clone",
                        "--local",
                        "--no-hardlinks",
                        "--no-checkout",
                        str(repo_root),
                        str(checkout),
                    ]
                )
                for remote in _git(checkout, "remote").stdout.splitlines():
                    if remote.strip():
                        _git(checkout, "remote", "remove", remote.strip())
                _git(checkout, "checkout", "--detach", resolved_base)
                workspace_revision = resolved_base
                _scan_checkout_for_secrets(checkout)
            else:
                workspace_revision = _create_scoped_checkout(
                    repo_root,
                    checkout,
                    source_revision=resolved_base,
                    visible_paths=visible_paths,
                    required_paths=required_paths,
                )
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise
        return cls(
            root,
            checkout,
            resolved_base,
            workspace_revision,
            _git_control_sha256(checkout),
        )

    def capture_patch(self, write_set: tuple[str, ...]) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
        if _git(self.checkout, "rev-parse", "HEAD").stdout.strip() != self.workspace_revision:
            raise WorkspaceError("external provider changed the contained workspace HEAD")
        if _git(self.checkout, "diff", "--cached", "--name-only").stdout.strip():
            raise WorkspaceError("external provider changed the contained workspace index")
        if _git_control_sha256(self.checkout) != self.git_control_sha256:
            raise WorkspaceError("external provider changed contained Git refs, config, or hooks")
        untracked = [line for line in _git(self.checkout, "ls-files", "--others", "--exclude-standard").stdout.splitlines() if line]
        if untracked:
            _git(self.checkout, "add", "--intent-to-add", "--", *untracked)
        patch = _git(self.checkout, "diff", "--binary", self.workspace_revision).stdout
        changed = tuple(sorted(set(line for line in _git(self.checkout, "diff", "--name-only", self.workspace_revision).stdout.splitlines() if line)))
        escaped = tuple(path for path in changed if not _allowed(path, write_set) or not _safe_path(path))
        if len(patch.encode("utf-8")) > MAX_PATCH_BYTES:
            raise WorkspaceError("external patch exceeds the bounded size ceiling")
        return patch, changed, escaped

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def _allowed(path: str, write_set: tuple[str, ...]) -> bool:
    return any(path == allowed or path.startswith(allowed.rstrip("/") + "/") for allowed in write_set)


def _safe_path(path: str) -> bool:
    parts = Path(path).parts
    return (
        bool(path)
        and path != "."
        and not path.startswith("/")
        and ".." not in parts
        and ".git" not in parts
        and not (SECRET_PATH_PARTS & {part.casefold() for part in parts})
    )


def _create_scoped_checkout(
    repo_root: Path,
    checkout: Path,
    *,
    source_revision: str,
    visible_paths: tuple[str, ...],
    required_paths: tuple[str, ...],
) -> str:
    visible = tuple(dict.fromkeys(visible_paths))
    required = set(required_paths)
    if any(not _safe_path(path) for path in visible):
        raise WorkspaceError("external context contains an unsafe path")
    existing: list[str] = []
    for path in visible:
        exists = _git_path_exists(repo_root, source_revision, path)
        if path in required and not exists:
            raise WorkspaceError(f"declared external context path is unavailable: {path}")
        if exists:
            existing.append(path)
    checkout.mkdir()
    if existing:
        archive = subprocess.run(
            ["git", "archive", "--format=tar", source_revision, "--", *existing],
            cwd=repo_root,
            capture_output=True,
            timeout=60,
            check=False,
        )
        if archive.returncode:
            raise WorkspaceError("cannot materialize declared external context")
        if len(archive.stdout) > MAX_CONTEXT_ARCHIVE_BYTES:
            raise WorkspaceError("declared external context exceeds the bounded size ceiling")
        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as payload:
            members = payload.getmembers()
            for member in members:
                if (
                    not _safe_path(member.name.rstrip("/"))
                    or not _visible_member(member.name.rstrip("/"), visible)
                    or member.issym()
                    or member.islnk()
                    or not (member.isfile() or member.isdir())
                ):
                    raise WorkspaceError("declared external context contains an unsafe member")
                if member.isfile():
                    handle = payload.extractfile(member)
                    if handle is None or _contains_secret(handle.read()):
                        raise WorkspaceError(
                            f"declared external context contains secret-like content: {member.name}"
                        )
            payload.extractall(checkout, members=members, filter="data")
    _git(checkout, "init", "-q")
    _git(checkout, "config", "user.email", "saga-external-action@invalid")
    _git(checkout, "config", "user.name", "Saga External Action")
    _git(checkout, "add", "-A")
    _git(checkout, "commit", "--allow-empty", "-qm", "scoped approved context")
    return _git(checkout, "rev-parse", "HEAD").stdout.strip()


def _git_path_exists(repo_root: Path, revision: str, path: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}:{path}"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode not in {0, 1, 128}:
        raise WorkspaceError("cannot inspect declared external context")
    return result.returncode == 0


def _visible_member(path: str, visible: tuple[str, ...]) -> bool:
    return _allowed(path, visible) or any(
        item.startswith(path.rstrip("/") + "/") for item in visible
    )


def _contains_secret(content: bytes) -> bool:
    return any(pattern.search(content) is not None for pattern in SECRET_CONTENT_PATTERNS)


def _scan_checkout_for_secrets(checkout: Path) -> None:
    for path in sorted(checkout.rglob("*"), key=lambda item: item.as_posix()):
        if ".git" in path.relative_to(checkout).parts or not path.is_file():
            continue
        if path.stat().st_size > MAX_CONTEXT_ARCHIVE_BYTES:
            raise WorkspaceError("external context file exceeds the bounded size ceiling")
        if _contains_secret(path.read_bytes()):
            raise WorkspaceError(
                f"external context contains secret-like content: {path.relative_to(checkout)}"
            )


def _git_control_sha256(repo_root: Path) -> str:
    refs = _git(repo_root, "for-each-ref", "--format=%(refname)%00%(objectname)").stdout
    config = _git(repo_root, "config", "--local", "--null", "--list").stdout
    git_dir = Path(_git(repo_root, "rev-parse", "--absolute-git-dir").stdout.strip())
    hooks: list[str] = []
    hooks_dir = git_dir / "hooks"
    if hooks_dir.is_dir():
        for child in sorted(hooks_dir.iterdir(), key=lambda value: value.name):
            if child.is_file() and not child.name.endswith(".sample"):
                hooks.append(f"{child.name}:{hashlib.sha256(child.read_bytes()).hexdigest()}")
    payload = f"{refs}\0{config}\0{'|'.join(hooks)}".encode()
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class ImportResult:
    changed_paths: tuple[str, ...]
    patch_sha256: str
    base_revision: str
    authority: str = "root-import"


def import_approved_patch(
    *,
    repo_root: Path,
    approval: Any,
    patch_path: Path,
    patch_sha256: str,
    changed_paths: tuple[str, ...],
) -> ImportResult:
    """Apply one approval-bound contained patch into the shared workspace as root."""

    root = repo_root.resolve()
    artifact_root = patch_path.parent.resolve()
    resolved_patch = patch_path.resolve(strict=False)
    if patch_path.is_symlink() or resolved_patch.parent != artifact_root:
        raise WorkspaceError("external patch artifact must not be a symlink")
    try:
        patch = patch_path.read_bytes()
    except OSError as exc:
        raise WorkspaceError("external patch artifact is unavailable") from exc
    if len(patch) > MAX_PATCH_BYTES or hashlib.sha256(patch).hexdigest() != patch_sha256:
        raise WorkspaceError("external patch artifact digest or size is invalid")
    base = _git(root, "rev-parse", "HEAD").stdout.strip()
    if base != approval.base_revision:
        raise WorkspaceError("shared workspace base changed after approval")
    if approval.dirty_overlap:
        raise WorkspaceError("approved write paths overlap pre-existing dirty state")
    writes = tuple(str(item) for item in approval.write_set)
    expected = tuple(sorted(changed_paths))
    if not expected or any(not _safe_path(path) or not _allowed(path, writes) for path in expected):
        raise WorkspaceError("external patch changed paths exceed approved safe writes")
    dirty = _dirty_paths(root)
    overlap = tuple(
        sorted(path for path in dirty if any(_allowed(path, (allowed,)) or _allowed(allowed, (path,)) for allowed in writes))
    )
    if overlap:
        raise WorkspaceError(f"shared workspace dirty overlap changed after approval: {overlap}")
    numstat = _git(root, "apply", "--numstat", str(resolved_patch)).stdout
    patch_paths = tuple(sorted(line.rsplit("\t", 1)[-1] for line in numstat.splitlines() if line))
    if patch_paths != expected:
        raise WorkspaceError("external patch content does not match its audited changed paths")
    _git(root, "apply", "--check", "--binary", str(resolved_patch))
    _git(root, "apply", "--binary", str(resolved_patch))
    return ImportResult(expected, patch_sha256, base)


def _dirty_paths(repo_root: Path) -> tuple[str, ...]:
    tracked = _git(repo_root, "diff", "--name-only", "HEAD").stdout.splitlines()
    untracked = _git(repo_root, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    return tuple(sorted(set(path for path in (*tracked, *untracked) if path)))


def _run(argv: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise WorkspaceError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return result


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=cwd)
