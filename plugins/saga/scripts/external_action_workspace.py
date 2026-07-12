#!/usr/bin/env python3
"""Disposable, remote-stripped Git workspace for external CLI actions."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class WorkspaceError(RuntimeError):
    pass


@dataclass(slots=True)
class Workspace:
    root: Path
    checkout: Path
    base_revision: str

    @classmethod
    def create(cls, repo_root: Path, base_revision: str) -> Workspace:
        root = Path(tempfile.mkdtemp(prefix="saga-external-action-"))
        checkout = root / "worktree"
        try:
            _git(repo_root, "rev-parse", "--verify", f"{base_revision}^{{commit}}")
            _run(["git", "clone", "--local", "--no-hardlinks", "--no-checkout", str(repo_root), str(checkout)])
            for remote in _git(checkout, "remote").stdout.splitlines():
                if remote.strip():
                    _git(checkout, "remote", "remove", remote.strip())
            _git(checkout, "checkout", "--detach", base_revision)
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise
        return cls(root, checkout, base_revision)

    def capture_patch(self, write_set: tuple[str, ...]) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
        untracked = [line for line in _git(self.checkout, "ls-files", "--others", "--exclude-standard").stdout.splitlines() if line]
        if untracked:
            _git(self.checkout, "add", "--intent-to-add", "--", *untracked)
        patch = _git(self.checkout, "diff", "--binary", self.base_revision).stdout
        changed = tuple(sorted(set(line for line in _git(self.checkout, "diff", "--name-only", self.base_revision).stdout.splitlines() if line)))
        escaped = tuple(path for path in changed if not _allowed(path, write_set))
        return patch, changed, escaped

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def _allowed(path: str, write_set: tuple[str, ...]) -> bool:
    return any(path == allowed or path.startswith(allowed.rstrip("/") + "/") for allowed in write_set)


def _run(argv: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise WorkspaceError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return result


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=cwd)
