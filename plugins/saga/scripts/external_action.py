#!/usr/bin/env python3
"""Operator CLI for reading durable external-action status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import external_action_status
import external_action_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--saga-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("command", choices=("status", "refresh"))
    args = parser.parse_args(argv)
    store = external_action_store.Store.for_action(
        saga_id=args.saga_id,
        run_id=args.run_id,
        action_id=args.action_id,
        repo_root=Path(args.repo_root),
    )
    if args.command == "refresh":
        status = external_action_status.refresh(store)
    else:
        status = external_action_status.project(external_action_store.read_snapshot(store))
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
