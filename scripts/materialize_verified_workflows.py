#!/usr/bin/env python3
"""Materialize the checked-in Verified Workflows package into an isolated staging path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "plugins" / "verified-workflows"


class MaterializationError(RuntimeError):
    """Raised when staging would overwrite drift or touch a managed Codex profile."""


def _source_files(source: Path) -> dict[Path, Path]:
    if not source.is_dir():
        raise MaterializationError(f"source package does not exist: {source}")
    symlinks = sorted(path for path in source.rglob("*") if path.is_symlink())
    if symlinks:
        raise MaterializationError(
            f"source package contains symlinks: {[path.relative_to(source) for path in symlinks]}"
        )
    return {
        path.relative_to(source): path
        for path in sorted(source.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def _tree_sha256(files: dict[Path, Path]) -> str:
    digest = hashlib.sha256()
    for rel, path in files.items():
        content = path.read_bytes()
        mode = stat.S_IMODE(path.stat().st_mode)
        digest.update(rel.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(f"{mode:o}".encode("ascii"))
        digest.update(b"\0")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _validate_destination(source: Path, destination: Path) -> None:
    if destination == source or destination.is_relative_to(source) or source.is_relative_to(destination):
        raise MaterializationError("destination must be independent from the maintained source")
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).resolve()
    if destination == codex_home or destination.is_relative_to(codex_home):
        raise MaterializationError("destination must not be inside CODEX_HOME")
    repo_root = REPO_ROOT.resolve()
    if destination == repo_root or destination.is_relative_to(repo_root):
        raise MaterializationError("destination must not be inside the maintained repository")


def _absolute_without_resolving(path: Path) -> Path:
    expanded = path.expanduser()
    return expanded if expanded.is_absolute() else Path.cwd() / expanded


def _reject_destination_symlink(path: Path) -> None:
    if path.is_symlink():
        raise MaterializationError("destination must not be a symlink")


def materialize(source: Path, destination: Path) -> dict[str, Any]:
    """Stage ``source`` exactly; a second identical call is a no-op."""

    raw_source = _absolute_without_resolving(source)
    if raw_source.is_symlink():
        raise MaterializationError("source package root must not be a symlink")
    source = raw_source.resolve()
    raw_destination = _absolute_without_resolving(destination)
    _reject_destination_symlink(raw_destination)
    destination = raw_destination.resolve()
    _validate_destination(source, destination)
    files = _source_files(source)
    expected_dirs = {Path(".")}
    for rel in files:
        expected_dirs.update(rel.parents)

    if destination.exists() and not destination.is_dir():
        raise MaterializationError("destination must be a directory")
    destination.mkdir(parents=True, exist_ok=True)
    extras = []
    for path in destination.rglob("*"):
        rel = path.relative_to(destination)
        if path.is_symlink():
            extras.append(rel.as_posix())
        elif path.is_file() and rel not in files:
            extras.append(rel.as_posix())
        elif path.is_dir() and rel not in expected_dirs:
            extras.append(rel.as_posix())
        elif not path.is_file() and not path.is_dir():
            extras.append(rel.as_posix())
    if extras:
        raise MaterializationError(f"destination contains unmanaged paths: {sorted(extras)}")

    created = 0
    unchanged = 0
    for rel, source_path in files.items():
        target = destination / rel
        if target.exists():
            if not target.is_file() or target.is_symlink():
                raise MaterializationError(f"destination path is not a regular file: {rel}")
            if target.read_bytes() != source_path.read_bytes():
                raise MaterializationError(f"destination file drifted: {rel}")
            if stat.S_IMODE(target.stat().st_mode) != stat.S_IMODE(source_path.stat().st_mode):
                raise MaterializationError(f"destination mode drifted: {rel}")
            unchanged += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
        created += 1
    return {
        "schema_version": 1,
        "file_count": len(files),
        "created": created,
        "unchanged": unchanged,
        "tree_sha256": _tree_sha256(files),
        "installed_or_profile_mutated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = materialize(args.source, args.destination)
    except MaterializationError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
