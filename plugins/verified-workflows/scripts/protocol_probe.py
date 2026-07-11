#!/usr/bin/env python3
"""Deterministic unit fixture for Verified Workflows capability degradation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs" / "validation" / "codex-runtime-capability-snapshot.json"
MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024


class ProtocolProbeError(ValueError):
    """Raised when fixture inputs do not describe a closed capability state."""


def _read_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    try:
        scripts_dir = PLUGIN_ROOT / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import render_codex_agents as renderer  # noqa: PLC0415

        content = renderer._regular_single_link(
            path, "capability snapshot", MAX_SNAPSHOT_BYTES
        )
    except renderer.RoleRegistryError as exc:
        raise ProtocolProbeError(str(exc)) from exc
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolProbeError("capability snapshot is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ProtocolProbeError("capability snapshot must be an object")
    return payload, hashlib.sha256(content).hexdigest()


def _snapshot_surface(snapshot: dict[str, Any]) -> str:
    collaboration_facts = snapshot.get("collaboration", {})
    if not isinstance(collaboration_facts, dict):
        return "absent"
    spawn = collaboration_facts.get("spawn", {})
    if not isinstance(spawn, dict) or spawn.get("available") is not True:
        return "absent"
    if spawn.get("per_child_agent_type") is True:
        return "named"
    return "generic"


def probe_protocol(
    *,
    snapshot: dict[str, Any],
    snapshot_sha256: str,
    spawn_surface: str | None = None,
    independence: str = "preferred",
    role_kind: str = "agent-lens",
    hook_pair: str = "absent",
    auth: str = "available",
) -> dict[str, Any]:
    """Characterize a fixture without running Codex or creating runtime evidence."""

    surface = spawn_surface or _snapshot_surface(snapshot)
    if surface not in {"named", "generic", "absent", "backpressure", "capacity-zero"}:
        raise ProtocolProbeError("spawn surface is invalid")
    if independence not in {"preferred", "required", "n/a"}:
        raise ProtocolProbeError("independence is invalid")
    if role_kind not in {"agent-lens", "deterministic-validator"}:
        raise ProtocolProbeError("role kind is invalid")
    if hook_pair not in {"present", "absent", "mismatch"}:
        raise ProtocolProbeError("hook pair state is invalid")
    if auth not in {"available", "unavailable"}:
        raise ProtocolProbeError("auth state is invalid")
    blockers: list[str] = []
    limitations: list[str] = []
    if auth == "unavailable":
        outcome = "auth-unavailable"
        blockers.append("isolated authentication is unavailable")
    elif role_kind == "deterministic-validator":
        if independence != "n/a":
            raise ProtocolProbeError("deterministic validators require n/a independence")
        outcome = "deterministic-tool-candidate"
        limitations.append("unit fixture does not execute the deterministic command")
    elif surface == "named" and hook_pair == "present":
        outcome = "attestation-candidate"
        limitations.append("unit fixture cannot prove a real child or live hook pair")
    elif independence == "required":
        outcome = "blocked"
        blockers.append("required independence lacks named-profile runtime proof")
    else:
        outcome = "inline-only"
        if surface == "generic":
            limitations.append("spawn surface cannot request or read back an agent type")
        elif surface in {"backpressure", "capacity-zero"}:
            limitations.append("child capacity is unavailable")
        else:
            limitations.append("native child spawn is unavailable")
        if hook_pair != "present":
            limitations.append("no matching start/stop receipt exists")
    return {
        "schema_version": 1,
        "claim": "unit-fixture-only",
        "runtime_proof": False,
        "snapshot_sha256": snapshot_sha256,
        "spawn_surface": surface,
        "role_kind": role_kind,
        "independence": independence,
        "hook_pair": hook_pair,
        "auth": auth,
        "outcome": outcome,
        "blockers": sorted(blockers),
        "limitations": sorted(limitations),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--spawn-surface",
        choices=("named", "generic", "absent", "backpressure", "capacity-zero"),
    )
    parser.add_argument("--independence", choices=("preferred", "required", "n/a"), default="preferred")
    parser.add_argument("--role-kind", choices=("agent-lens", "deterministic-validator"), default="agent-lens")
    parser.add_argument("--hook-pair", choices=("present", "absent", "mismatch"), default="absent")
    parser.add_argument("--auth", choices=("available", "unavailable"), default="available")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        snapshot, digest = _read_snapshot(args.snapshot)
        payload = probe_protocol(
            snapshot=snapshot,
            snapshot_sha256=digest,
            spawn_surface=args.spawn_surface,
            independence=args.independence,
            role_kind=args.role_kind,
            hook_pair=args.hook_pair,
            auth=args.auth,
        )
    except ProtocolProbeError as exc:
        print(f"verified workflow protocol probe failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
