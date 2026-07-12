#!/usr/bin/env python3
"""Operator CLI for reading durable external-action status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import external_action_lifecycle
import external_action_status
import external_action_store


def main(argv: list[str] | None = None) -> int:
    raw_args = sys.argv[1:] if argv is None else argv
    if raw_args and raw_args[0] == "probe":
        print(
            json.dumps(
                {
                    "schema": "saga.external-action.probe.v1",
                    "operations": [
                        name
                        for name in (
                            "prepare_bundle",
                            "approve_bundle",
                            "execute_bundle",
                            "load_action",
                            "interrupt_action",
                            "retry_action",
                            "adjudicate_artifact",
                            "adjudicate_opinion",
                            "consume",
                        )
                        if callable(getattr(external_action_lifecycle, name, None))
                    ],
                },
                sort_keys=True,
            )
        )
        return 0
    if raw_args and raw_args[0] == "bundle":
        bundle_parser = argparse.ArgumentParser(description="Inspect an editable stage action bundle")
        bundle_parser.add_argument("bundle")
        bundle_parser.add_argument("--repo-root", default=".")
        bundle_parser.add_argument("--stage", required=True)
        args = bundle_parser.parse_args(raw_args)
        bundle = external_action_lifecycle.inspect_bundle(
            args.stage,
            repo_root=Path(args.repo_root),
        )
        print(json.dumps(external_action_lifecycle.bundle_payload(bundle), indent=2, sort_keys=True))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--saga-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("command", choices=("status", "refresh"))
    args = parser.parse_args(raw_args)
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
