#!/usr/bin/env python3
"""Build the exact U9 legacy-workflow token inventory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_codex_plugins import (  # noqa: E402
    LEGACY_TEAM_EXECUTION_FILE_COUNT,
    LEGACY_TEAM_EXECUTION_TREE_SHA256,
    LEGACY_WORKFLOW_INVENTORY,
    expected_legacy_workflow_classification,
    legacy_historical_entries_sha256,
    legacy_workflow_file_facts,
    serialized_legacy_history_sentinels,
    workflow_registry_sha256,
)


INVENTORY_PATH = LEGACY_WORKFLOW_INVENTORY


def build_inventory(root: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    unclassified: list[str] = []
    for raw_path, facts in legacy_workflow_file_facts(root).items():
        rel = Path(raw_path)
        classification = expected_legacy_workflow_classification(rel)
        if classification is None:
            unclassified.append(raw_path)
            continue
        entries.append(
            {
                "path": raw_path,
                "classification": classification,
                "tokens": facts["tokens"],
                "sha256": facts["sha256"],
            }
        )
    if unclassified:
        raise ValueError(f"unclassified legacy workflow token paths: {unclassified}")
    return {
        "schema_version": 1,
        "generated_by": "scripts/build_legacy_workflow_inventory.py",
        "workflow_registry_sha256": workflow_registry_sha256(),
        "legacy_team_execution_tree": {
            "file_count": LEGACY_TEAM_EXECUTION_FILE_COUNT,
            "sha256": LEGACY_TEAM_EXECUTION_TREE_SHA256,
        },
        "history_sentinels": serialized_legacy_history_sentinels(),
        "historical_inventory_sha256": legacy_historical_entries_sha256(entries),
        "entries": entries,
    }


def dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    if args.check and args.write:
        parser.error("--check and --write are mutually exclusive")
    root = args.repo_root.resolve()
    path = root / INVENTORY_PATH
    rendered = dumps(build_inventory(root))
    if args.check:
        if not path.is_file() or path.read_text(encoding="utf-8") != rendered:
            print(f"stale legacy workflow inventory: {path}", file=sys.stderr)
            return 1
        return 0
    if args.write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        print(f"wrote {path.relative_to(root)}")
        return 0
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
