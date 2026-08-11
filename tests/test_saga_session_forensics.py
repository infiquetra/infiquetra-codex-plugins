"""Synthetic compatibility tests for Saga's last-resort session forensics."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT_ROOT = Path(__file__).parents[1] / "plugins/saga/scripts"
DISCOVERY_PATH = SCRIPT_ROOT / "discover_sessions.py"
EXTRACTOR_PATH = SCRIPT_ROOT / "extract_session_skeleton.py"


def _load_discovery() -> ModuleType:
    spec = importlib.util.spec_from_file_location("saga_discover_sessions", DISCOVERY_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DISCOVERY = _load_discovery()


def _session_meta(session_id: str, cwd: str, *, size: int | None = None) -> bytes:
    payload: dict[str, Any] = {
        "type": "session_meta",
        "payload": {"id": session_id, "cwd": cwd},
    }
    if size is None:
        return json.dumps(payload, separators=(",", ":")).encode() + b"\n"

    payload["payload"]["padding"] = ""
    encoded = json.dumps(payload, separators=(",", ":")).encode() + b"\n"
    padding_size = size - len(encoded)
    assert padding_size >= 0
    payload["payload"]["padding"] = "x" * padding_size
    encoded = json.dumps(payload, separators=(",", ":")).encode() + b"\n"
    assert len(encoded) == size
    return encoded


def _write_current(
    root: Path,
    filename: str,
    session_id: str,
    cwd: str,
    *,
    mtime: float,
    first_record_size: int | None = None,
) -> Path:
    path = root / "2026/08/10" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_session_meta(session_id, cwd, size=first_record_size))
    os.utime(path, (mtime, mtime))
    return path


def _write_legacy(root: Path, project: str, filename: str, *, mtime: float) -> Path:
    path = root / project / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("legacy body is not inspected by discovery\n", encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path


def _discover(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, Any]]:
    return DISCOVERY.discover(
        root,
        "infiquetra-codex-plugins",
        days=1,
        exclude=exclude or set(),
    )


def _extract(records: list[Any]) -> tuple[str, dict[str, Any]]:
    result = subprocess.run(
        [sys.executable, str(EXTRACTOR_PATH)],
        input="".join(json.dumps(record) + "\n" for record in records),
        text=True,
        capture_output=True,
        check=True,
    )
    lines = result.stdout.splitlines()
    return result.stdout, json.loads(lines[-1])


def test_discovers_current_session_by_exact_repository_component(tmp_path: Path) -> None:
    now = time.time()
    match = _write_current(
        tmp_path,
        "rollout-match.jsonl",
        "true-session-id",
        "/workspace/infiquetra-codex-plugins",
        mtime=now,
    )
    _write_current(
        tmp_path,
        "rollout-similar.jsonl",
        "similar-session-id",
        "/workspace/infiquetra-codex-plugins-other",
        mtime=now,
    )

    assert _discover(tmp_path) == [
        {"path": str(match), "session_id": "true-session-id", "mtime": now}
    ]


def test_discovers_current_session_under_conventional_worktree_parent(tmp_path: Path) -> None:
    now = time.time()
    match = _write_current(
        tmp_path,
        "rollout-worktree.jsonl",
        "worktree-session-id",
        "/workspace/infiquetra-codex-plugins-worktrees/issue-62-plan",
        mtime=now,
    )

    assert _discover(tmp_path) == [
        {"path": str(match), "session_id": "worktree-session-id", "mtime": now}
    ]


def test_current_metadata_accepts_64_kib_and_omits_invalid_candidates(tmp_path: Path) -> None:
    now = time.time()
    boundary = _write_current(
        tmp_path,
        "boundary.jsonl",
        "boundary-id",
        "/workspace/infiquetra-codex-plugins",
        mtime=now,
        first_record_size=65_536,
    )
    _write_current(
        tmp_path,
        "oversized.jsonl",
        "oversized-id",
        "/workspace/infiquetra-codex-plugins",
        mtime=now,
        first_record_size=65_537,
    )
    malformed = tmp_path / "2026/08/10/malformed.jsonl"
    malformed.write_text("{not json}\n", encoding="utf-8")
    wrong_type = tmp_path / "2026/08/10/wrong-type.jsonl"
    wrong_type.write_text('{"type":"response_item"}\n', encoding="utf-8")
    non_regular = tmp_path / "2026/08/10/non-regular.jsonl"
    non_regular.mkdir()
    unreadable = _write_current(
        tmp_path,
        "unreadable.jsonl",
        "unreadable-id",
        "/workspace/infiquetra-codex-plugins",
        mtime=now,
    )
    unreadable.chmod(0)

    try:
        assert _discover(tmp_path) == [
            {"path": str(boundary), "session_id": "boundary-id", "mtime": now}
        ]
    finally:
        unreadable.chmod(0o600)


def test_preserves_legacy_substring_discovery(tmp_path: Path) -> None:
    now = time.time()
    legacy = _write_legacy(
        tmp_path,
        "archive-infiquetra-codex-plugins-other",
        "legacy-id.jsonl",
        mtime=now,
    )

    assert _discover(tmp_path) == [
        {"path": str(legacy), "session_id": "legacy-id", "mtime": now}
    ]


def test_orders_mixed_layouts_before_cap_and_uses_both_exclusion_keys(tmp_path: Path) -> None:
    now = time.time()
    newer = _write_current(
        tmp_path,
        "zeta-new.jsonl",
        "zeta-new",
        "/workspace/infiquetra-codex-plugins",
        mtime=now,
    )
    alpha = _write_current(
        tmp_path,
        "alpha-file.jsonl",
        "alpha",
        "/workspace/infiquetra-codex-plugins",
        mtime=now - 10,
    )
    beta_a = _write_legacy(
        tmp_path,
        "a-infiquetra-codex-plugins",
        "beta.jsonl",
        mtime=now - 10,
    )
    beta_b = _write_legacy(
        tmp_path,
        "b-infiquetra-codex-plugins",
        "beta.jsonl",
        mtime=now - 10,
    )
    gamma = _write_current(
        tmp_path,
        "gamma-file.jsonl",
        "gamma",
        "/workspace/infiquetra-codex-plugins",
        mtime=now - 10,
    )
    _write_current(
        tmp_path,
        "excluded-by-id.jsonl",
        "current-session-id",
        "/workspace/infiquetra-codex-plugins",
        mtime=now + 20,
    )
    _write_current(
        tmp_path,
        "current-filename.jsonl",
        "different-true-id",
        "/workspace/infiquetra-codex-plugins",
        mtime=now + 10,
    )
    _write_legacy(
        tmp_path,
        "z-infiquetra-codex-plugins",
        "omega.jsonl",
        mtime=now - 10,
    )

    candidates = _discover(tmp_path, exclude={"current-session-id", "current-filename"})

    assert [candidate["path"] for candidate in candidates] == [
        str(newer),
        str(alpha),
        str(beta_a),
        str(beta_b),
        str(gamma),
    ]


def test_extracts_current_user_and_assistant_text_with_existing_bound(tmp_path: Path) -> None:
    del tmp_path
    output, meta = _extract(
        [
            {
                "type": "response_item",
                "timestamp": "2026-08-10T12:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "user message long enough to keep"}],
                },
            },
            {
                "type": "response_item",
                "timestamp": "2026-08-10T12:00:01Z",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "assistant response long enough to keep"}
                    ],
                },
            },
        ]
    )

    assert "[user] user message long enough to keep" in output
    assert "[assistant] assistant response long enough to keep" in output
    assert meta["user"] == 1
    assert meta["assistant"] == 1


def test_top_level_list_is_counted_as_unknown() -> None:
    output, meta = _extract([["not", "a", "record"]])

    assert output.splitlines() == [json.dumps(meta)]
    assert meta["unknown"] == 1


def test_top_level_string_is_counted_as_unknown() -> None:
    output, meta = _extract(["not a record"])

    assert output.splitlines() == [json.dumps(meta)]
    assert meta["unknown"] == 1


def test_current_expected_block_with_non_string_text_is_unknown() -> None:
    output, meta = _extract(
        [
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": None}],
                },
            }
        ]
    )

    assert output.splitlines() == [json.dumps(meta)]
    assert meta["unknown"] == 1
    assert meta["user"] == 0


def test_current_extraction_omits_private_roles_reasoning_and_tools() -> None:
    forbidden = {
        "developer-secret",
        "system-secret",
        "reasoning-secret",
        "tool-call-secret",
        "tool-result-secret",
    }
    output, meta = _extract(
        [
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "developer",
                    "content": [{"type": "input_text", "text": "developer-secret"}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "system",
                    "content": [{"type": "input_text", "text": "system-secret"}],
                },
            },
            {"type": "response_item", "payload": {"type": "reasoning", "text": "reasoning-secret"}},
            {
                "type": "response_item",
                "payload": {"type": "function_call", "arguments": "tool-call-secret"},
            },
            {
                "type": "response_item",
                "payload": {"type": "function_call_output", "output": "tool-result-secret"},
            },
        ]
    )

    assert forbidden.isdisjoint(output.split())
    assert meta["unknown"] == 5
    assert meta["user"] == 0
    assert meta["assistant"] == 0


def test_preserves_legacy_user_and_assistant_extraction() -> None:
    output, meta = _extract(
        [
            {
                "type": "user",
                "timestamp": "2026-08-10T12:00:00Z",
                "message": {"content": "legacy user message long enough to keep"},
            },
            {
                "type": "assistant",
                "timestamp": "2026-08-10T12:00:01Z",
                "message": {
                    "content": [
                        {"type": "text", "text": "legacy assistant response long enough to keep"}
                    ]
                },
            },
        ]
    )

    assert "[user] legacy user message long enough to keep" in output
    assert "[assistant] legacy assistant response long enough to keep" in output
    assert meta["user"] == 1
    assert meta["assistant"] == 1
