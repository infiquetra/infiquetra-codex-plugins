#!/usr/bin/env python3
"""Discover recent Codex session JSONL files for a repo (Tier-2 fallback).

This is the discovery half of the ``/resume`` heavy-forensic Tier-2 path: a
slim, source-only port of CE ``ce-sessions``' ``discover-sessions.sh``. It is
used ONLY when there is no saga and no resolvable issue to anchor a deep
reconstruction on, so the engine falls back to mining prior local sessions.

Usage:
  python3 discover_sessions.py --repo <repo-folder> --days <N> \\
      [--projects-root <path>] [--exclude <session-id>]

It searches both legacy ``~/.codex/sessions/*<repo>*/*.jsonl`` paths and
current ``~/.codex/sessions/YYYY/MM/DD/*.jsonl`` paths within an mtime window,
drops ``--exclude``\\d session ids, and caps the deterministic recency order at
5. Current-layout repository identity comes only from a bounded first
``session_meta`` record.

Output is ``json.dumps`` of ``{"candidates": [{"path", "session_id", "mtime"}],
"count": N}`` — PATHS plus small metadata ONLY. It NEVER emits file bodies.
The extractor (``extract_session_skeleton.py``) is the only thing that reads a
transcript body, and it does so file-mediated.

MVP = recency ranking only. Keyword / branch relevance ranking (CE's
``extract-metadata.py``) is deliberately deferred — see QUEUED.
"""

from __future__ import annotations

import argparse
import json
import stat
import sys
import time
from pathlib import Path
from typing import TypedDict

MAX_CANDIDATES = 5
MAX_FIRST_RECORD_BYTES = 65_536
CURRENT_LAYOUT_GLOB = (
    "[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]/*.jsonl"
)


class Candidate(TypedDict):
    """A discovered session: PATH plus small metadata only, never a file body."""

    path: str
    session_id: str
    mtime: float


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Repository folder name to match")
    parser.add_argument("--days", type=int, required=True, help="mtime window in days")
    parser.add_argument(
        "--projects-root",
        default=str(Path.home() / ".codex" / "sessions"),
        help="Override the Codex projects root (default ~/.codex/sessions); for testing",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Session id or basename to drop (repeatable or comma-separated); e.g. the current session",
    )
    return parser.parse_args(argv)


def _excluded_ids(raw: list[str]) -> set[str]:
    """Normalize ``--exclude`` values (repeatable + comma-separated) to bare session ids."""
    ids: set[str] = set()
    for item in raw:
        for part in item.split(","):
            part = part.strip()
            if part:
                # Accept either a bare id or a *.jsonl basename/path.
                ids.add(Path(part).name.removesuffix(".jsonl"))
    return ids


def _current_candidate(jsonl: Path, repo: str, cutoff: float, exclude: set[str]) -> Candidate | None:
    """Read one bounded current-layout metadata record and return an eligible candidate."""
    try:
        file_stat = jsonl.stat()
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_mtime < cutoff:
            return None
        with jsonl.open("rb") as session_file:
            probe = session_file.read(MAX_FIRST_RECORD_BYTES + 1)
    except OSError:
        return None

    newline = probe.find(b"\n")
    if newline >= 0:
        if newline + 1 > MAX_FIRST_RECORD_BYTES:
            return None
        first_record = probe[:newline].removesuffix(b"\r")
    elif len(probe) <= MAX_FIRST_RECORD_BYTES:
        first_record = probe
    else:
        return None

    try:
        metadata = json.loads(first_record)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(metadata, dict) or metadata.get("type") != "session_meta":
        return None
    payload = metadata.get("payload")
    if not isinstance(payload, dict):
        return None
    session_id = payload.get("id")
    cwd = payload.get("cwd")
    if not isinstance(session_id, str) or not session_id or not isinstance(cwd, str):
        return None

    repo_components = {repo, f"{repo}-worktrees"}
    if repo_components.isdisjoint(Path(cwd).parts):
        return None
    if session_id in exclude or jsonl.stem in exclude:
        return None
    return {"path": str(jsonl), "session_id": session_id, "mtime": file_stat.st_mtime}


def discover(projects_root: Path, repo: str, days: int, exclude: set[str]) -> list[Candidate]:
    """Return both layouts in deterministic recency order, capped at 5."""
    if not projects_root.is_dir():
        return []

    cutoff = time.time() - days * 86400
    candidates: list[Candidate] = []
    for project_dir in projects_root.glob(f"*{repo}*"):
        if not project_dir.is_dir():
            continue
        for jsonl in project_dir.glob("*.jsonl"):
            try:
                mtime = jsonl.stat().st_mtime
            except OSError:
                continue
            if mtime < cutoff:
                continue
            session_id = jsonl.stem
            if session_id in exclude:
                continue
            candidates.append({"path": str(jsonl), "session_id": session_id, "mtime": mtime})

    for jsonl in projects_root.glob(CURRENT_LAYOUT_GLOB):
        candidate = _current_candidate(jsonl, repo, cutoff, exclude)
        if candidate is not None:
            candidates.append(candidate)

    candidates.sort(key=lambda c: (-c["mtime"], c["session_id"], c["path"]))
    return candidates[:MAX_CANDIDATES]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    candidates = discover(
        Path(args.projects_root).expanduser(),
        args.repo,
        args.days,
        _excluded_ids(args.exclude),
    )
    print(json.dumps({"candidates": candidates, "count": len(candidates)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
