#!/usr/bin/env python3
"""Emit bounded, non-mutating SessionStart re-entry context."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

MAX_STATE_BYTES = 1024 * 1024
SAFE_SAGA_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def reentry_context(cwd: Path) -> str:
    """Return fixed re-entry syntax without interpolating free-form Saga state."""

    relative = Path(".codex") / "saga" / "state.json"
    current = cwd
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return ""
    try:
        if not current.is_file() or current.stat().st_size > MAX_STATE_BYTES:
            return ""
        data: Any = json.loads(current.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, TypeError):
        return ""
    if not isinstance(data, dict) or not isinstance(data.get("sagas"), dict):
        return ""
    candidates = [item for item in data["sagas"].values() if isinstance(item, dict)]
    latest = max(candidates, key=lambda item: str(item.get("updated_at", "")), default=None)
    if latest is None:
        return ""
    saga_id = str(latest.get("saga_id", ""))
    if SAFE_SAGA_ID.fullmatch(saga_id) is None:
        return ""
    return f"Saga re-entry available for `{saga_id}`. Use `saga:loop resume {saga_id}`."


def main() -> int:
    context = reentry_context(Path.cwd())
    if context:
        print(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
