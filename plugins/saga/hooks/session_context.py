#!/usr/bin/env python3
"""Non-mutating SessionStart context: only summarize contained local Saga state."""
from __future__ import annotations
import json
from pathlib import Path

root = Path.cwd() / ".codex" / "saga" / "state.json"
try:
    data = json.loads(root.read_text(encoding="utf-8"))
    sagas = data.get("sagas", {})
    latest = sorted(sagas.values(), key=lambda item: str(item.get("updated_at", "")), reverse=True)[:1]
    if latest:
        item = latest[0]
        print(f"Saga re-entry: {item.get('saga_id', 'unknown')} — {item.get('next_step', 'inspect latest tick')}")
except (OSError, ValueError, TypeError):
    pass
