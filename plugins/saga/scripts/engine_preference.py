#!/usr/bin/env python3
"""Explicit mutator for repo-local Saga external-engine preferences."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import engine_offer


def save_preference(
    repo_root: Path | str,
    stage: str,
    preference: engine_offer.Preference,
) -> Path:
    """Persist one stage preference through an atomic local file replace."""
    if stage not in engine_offer.STAGES:
        raise engine_offer.EngineOfferError(
            f"stage {stage!r} not in {engine_offer.STAGES}"
        )
    prefs = engine_offer.load_preferences(repo_root)
    prefs.stages[stage] = preference
    prefs_path = Path(repo_root) / engine_offer.PREFS_PATH
    prefs_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(prefs.to_json(), indent=2, sort_keys=True) + "\n"

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{prefs_path.name}.",
        suffix=".tmp",
        dir=str(prefs_path.parent),
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, prefs_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return prefs_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=engine_offer.STAGES)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--intent", required=True, choices=engine_offer.INTENTS)
    parser.add_argument("--model", choices=engine_offer.MODELS)
    parser.add_argument("--effort", choices=engine_offer.EFFORTS)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        preference = engine_offer.Preference(
            intent=args.intent,
            model=args.model,
            effort=args.effort,
        )
        path = save_preference(args.repo_root, args.stage, preference)
        print(json.dumps({"saved": str(path), "stage": args.stage, **preference.to_json()}))
        return 0
    except engine_offer.EngineOfferError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
