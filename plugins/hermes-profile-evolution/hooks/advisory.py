#!/usr/bin/env python3
"""Advisory Codex guardrail for intercepted Team Mimir file edits."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from types import ModuleType

MAX_HOOK_INPUT_BYTES = 65_536
PATCH_PATH_RE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)


def _adapter() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts/profile_request.py"
    spec = importlib.util.spec_from_file_location("hermes_profile_request", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("adapter could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "systemMessage": reason,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                },
            },
            separators=(",", ":"),
        )
    )


def _paths(payload: dict[str, object]) -> list[str]:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        raise RuntimeError("supported edit has no tool input")
    file_path = tool_input.get("file_path")
    if isinstance(file_path, str) and file_path:
        return [file_path]
    command = tool_input.get("command")
    if isinstance(command, str):
        paths = PATCH_PATH_RE.findall(command)
        if paths:
            return paths
    raise RuntimeError("supported edit has no recognizable file path")


def _relative_paths(paths: list[str], root: Path, adapter: ModuleType) -> list[str]:
    relative: list[str] = []
    for raw in paths:
        candidate = Path(raw)
        if candidate.is_absolute():
            try:
                raw = candidate.resolve().relative_to(root).as_posix()
            except ValueError as exc:
                raise RuntimeError("edit path is outside the verified Team Mimir root") from exc
        relative.append(raw)
    return adapter.validate_paths(relative)


def _suggestion(report: dict[str, object]) -> str:
    target_owners = {
        verdict.get("owner")
        for verdict in report.get("paths", [])
        if isinstance(verdict, dict) and verdict.get("category") == "profile_owned_behavior"
    }
    target_owners.discard(None)
    if len(target_owners) == 1:
        target = next(iter(target_owners))
        return (
            "Use the hermes-profile-evolution skill to submit bounded JSON on standard input "
            f"for target `{target}`."
        )
    return "Split the request by named profile before starting Hermes dialogue."


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_HOOK_INPUT_BYTES + 1)
        if len(raw) > MAX_HOOK_INPUT_BYTES:
            raise RuntimeError("hook input exceeds the supported bound")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise RuntimeError("hook input must be a JSON object")
        if payload.get("hook_event_name") != "PreToolUse":
            return 0
        if payload.get("tool_name") not in {"apply_patch", "Edit", "Write"}:
            return 0
        cwd = payload.get("cwd")
        if not isinstance(cwd, str) or not cwd:
            raise RuntimeError("hook input lacks a working directory")
        adapter = _adapter()
        try:
            root = adapter.resolve_team_mimir_root(cwd)
        except adapter.AdapterError:
            if "HERMES_TEAM_MIMIR_ROOT" not in os.environ:
                return 0
            raise
        paths = _relative_paths(_paths(payload), root, adapter)
        report = adapter.classify_paths(paths, root)
    except Exception:
        _deny(
            "[hermes-profile-evolution] Profile custody could not be classified. "
            "This intercepted edit stopped without exposing its input."
        )
        return 0

    if report["disposition"] == "normal_merge":
        return 0
    _deny(
        "[hermes-profile-evolution] This intercepted edit stopped because Team Mimir classified "
        f"it as {report['category']} ({report['disposition']}). {_suggestion(report)} "
        "This trusted hook is an advisory guardrail for supported Codex tools; it cannot prevent "
        "same-user, root, shell, external-editor, disabled-hook, or untrusted-hook edits."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
