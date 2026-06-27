#!/usr/bin/env python3
"""Sync team-execution Codex agent definitions into a Codex profile."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

MANAGED_MARKER = "# managed_by = \"infiquetra-codex-plugins/team-execution\""


@dataclass(frozen=True)
class Action:
    action: str
    source: str | None
    target: str
    reason: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "action": self.action,
            "source": self.source,
            "target": self.target,
            "reason": self.reason,
        }


def _is_managed(path: Path) -> bool:
    try:
        return MANAGED_MARKER in path.read_text(encoding="utf-8").splitlines()[:8]
    except OSError:
        return False


def plan_sync(source_dir: Path, target_dir: Path, *, remove_stale: bool) -> list[Action]:
    sources = {path.name: path for path in sorted(source_dir.glob("*.toml"))}
    actions: list[Action] = []

    for name, source in sources.items():
        target = target_dir / name
        if not target.exists():
            actions.append(Action("install", str(source), str(target), "missing target"))
            continue
        if not _is_managed(target):
            actions.append(Action("conflict", str(source), str(target), "unmanaged target exists"))
            continue
        if target.read_text(encoding="utf-8") == source.read_text(encoding="utf-8"):
            actions.append(Action("unchanged", str(source), str(target), "already current"))
        else:
            actions.append(Action("update", str(source), str(target), "managed target differs"))

    if remove_stale and target_dir.exists():
        for target in sorted(target_dir.glob("*.toml")):
            if target.name not in sources and _is_managed(target):
                actions.append(Action("remove", None, str(target), "stale managed target"))

    return actions


def apply_actions(actions: list[Action]) -> None:
    conflicts = [action for action in actions if action.action == "conflict"]
    if conflicts:
        names = ", ".join(Path(action.target).name for action in conflicts)
        raise SystemExit(f"refusing to overwrite unmanaged Codex agent(s): {names}")

    for action in actions:
        target = Path(action.target)
        if action.action in {"install", "update"}:
            assert action.source is not None
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(action.source, target)
        elif action.action == "remove":
            target.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "agents",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path.home() / ".codex" / "agents",
    )
    parser.add_argument("--remove-stale", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    actions = plan_sync(args.source_dir, args.target_dir, remove_stale=args.remove_stale)
    if args.apply:
        apply_actions(actions)

    payload = {
        "applied": args.apply,
        "source_dir": str(args.source_dir),
        "target_dir": str(args.target_dir),
        "actions": [action.to_dict() for action in actions],
    }
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
