#!/usr/bin/env python3
"""Deterministic protocol probe for the team-execution Codex port."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


BASE_REVIEWERS = (
    "devils-advocate-reviewer",
    "security-reviewer",
    "architecture-reviewer",
)

SubagentCapability = Literal["present", "absent"]
SpawnResult = Literal["available", "backpressure"]
ValidatorRequirement = Literal["required", "optional"]
ToolStatus = Literal["present", "missing"]


@dataclass(frozen=True)
class ValidatorSpec:
    name: str
    group: str
    requirement: ValidatorRequirement
    tool: str
    tool_status: ToolStatus

    @property
    def required(self) -> bool:
        return self.requirement == "required"


def parse_validator_spec(raw: str) -> ValidatorSpec:
    parts = raw.split(":")
    if len(parts) != 5:
        raise argparse.ArgumentTypeError(
            "validator specs must be name:group:required|optional:tool:present|missing"
        )
    name, group, requirement, tool, tool_status = parts
    if requirement not in {"required", "optional"}:
        raise argparse.ArgumentTypeError("validator requirement must be required or optional")
    if tool_status not in {"present", "missing"}:
        raise argparse.ArgumentTypeError("validator tool status must be present or missing")
    return ValidatorSpec(
        name=name,
        group=group,
        requirement=requirement,
        tool=tool,
        tool_status=tool_status,
    )


def is_ignored(repo_root: Path, rel_path: str) -> bool:
    """Return true when a simple .gitignore rule protects rel_path."""
    gitignore = repo_root / ".gitignore"
    if not gitignore.is_file():
        return False

    normalized = rel_path.strip("/")
    normalized_with_slash = f"{normalized}/"
    for raw_line in gitignore.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        pattern = line.strip("/")
        if pattern in {normalized, normalized_with_slash, ".codex", ".codex/"}:
            return True
        if pattern.endswith("/") and normalized_with_slash.startswith(pattern):
            return True
    return False


def select_state_root(repo_root: Path) -> dict[str, str | bool]:
    rel_root = ".codex/team-execution/"
    if is_ignored(repo_root, rel_root):
        return {
            "location": "repo-local",
            "path": rel_root,
            "protected": True,
            "instruction": "repo-local state root is ignored",
        }
    return {
        "location": "user-local-fallback",
        "path": f"~/.codex/team-execution/state/{repo_root.name}/",
        "protected": True,
        "instruction": "add .codex/team-execution/ to .gitignore before using repo-local state",
    }


def reviewer_artifacts(mode: str) -> list[dict[str, str]]:
    return [
        {
            "role": reviewer,
            "artifact": f"reviewers/{reviewer}.json",
            "execution_mode": mode,
        }
        for reviewer in BASE_REVIEWERS
    ]


def validator_artifacts(
    validators: list[ValidatorSpec],
    mode: str,
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    artifacts: list[dict[str, object]] = []
    blockers: list[dict[str, str]] = []
    for validator in validators:
        if validator.tool_status == "missing" and validator.required:
            status = "blocked"
            blockers.append(
                {
                    "validator": validator.name,
                    "tool": validator.tool,
                    "setup": f"install or configure `{validator.tool}` before running {validator.name}",
                }
            )
        elif validator.tool_status == "missing":
            status = "warn"
        else:
            status = "pass"
        artifacts.append(
            {
                "role": validator.name,
                "group": validator.group,
                "required": validator.required,
                "tool": validator.tool,
                "tool_available": validator.tool_status == "present",
                "status": status,
                "artifact": f"validators/{validator.name}.json",
                "execution_mode": mode,
            }
        )
    return artifacts, blockers


def probe_protocol(
    *,
    repo_root: Path,
    subagents: SubagentCapability,
    spawn_result: SpawnResult = "available",
    validators: list[ValidatorSpec] | None = None,
) -> dict[str, object]:
    selected_validators = validators or []
    if subagents == "present" and spawn_result == "available":
        mode = "delegated"
        delegation_status = "delegated"
    elif subagents == "present":
        mode = "serial"
        delegation_status = "backpressure-fallback"
    else:
        mode = "serial"
        delegation_status = "subagents-unavailable"

    validator_records, blockers = validator_artifacts(selected_validators, mode)
    state_root = select_state_root(repo_root)
    result = "blocked" if blockers else "pass"

    payload: dict[str, object] = {
        "plugin": "team-execution",
        "subagent_capability": subagents,
        "spawn_result": spawn_result,
        "mode": mode,
        "delegation_status": delegation_status,
        "result": result,
        "state_root": state_root,
        "dispatch_bounds": {
            "max_parallel_reviewers": len(BASE_REVIEWERS) if mode == "delegated" else 1,
            "max_parallel_validators": 3 if mode == "delegated" else 1,
            "bounded_context_required": True,
        },
        "reviewer_artifacts": reviewer_artifacts(mode),
        "validator_artifacts": validator_records,
        "serial_consensus_limits": []
        if mode == "delegated"
        else [
            "reviewer and validator roles are simulated sequentially by the main thread",
            "serial consensus is usable for safety gates but is not independent delegated review",
        ],
        "delegation_safety": {
            "untrusted_context_delimited": True,
            "subagents_authorize_mutation": False,
            "main_thread_verifies_delegated_outputs": True,
            "sensitive_data_kept_main_thread": True,
        },
        "main_thread_final_verification": True,
        "blockers": blockers,
    }
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--subagents", choices=("present", "absent"), required=True)
    parser.add_argument(
        "--spawn-result",
        choices=("available", "backpressure"),
        default="available",
    )
    parser.add_argument(
        "--validator",
        action="append",
        default=[],
        type=parse_validator_spec,
        help="name:group:required|optional:tool:present|missing",
    )
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = probe_protocol(
        repo_root=args.repo_root,
        subagents=args.subagents,
        spawn_result=args.spawn_result,
        validators=args.validator,
    )
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    return 1 if payload["result"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
