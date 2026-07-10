#!/usr/bin/env python3
"""Capture the safe, locally discoverable portion of Codex runtime capability truth."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    from scripts.port_contract import MAX_GIT_OUTPUT, canonical_json_bytes, sha256_bytes
except ImportError:
    from port_contract import MAX_GIT_OUTPUT, canonical_json_bytes, sha256_bytes


SELECTED_FEATURES = ("multi_agent", "hooks", "goals", "plugins")
EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
TEAM_EXECUTION_MARKER = '# managed_by = "infiquetra-codex-plugins/team-execution"'
VERIFIED_WORKFLOWS_MARKER = '# managed_by = "infiquetra-codex-plugins/verified-workflows"'
Run = Callable[[Sequence[str]], subprocess.CompletedProcess[bytes]]


class CaptureError(RuntimeError):
    """Raised when the safe capability projection cannot be captured."""


def _default_run(argv: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            list(argv),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired as exc:
        raise CaptureError(f"command timed out: {' '.join(argv)}") from exc


def normalize_catalog(payload: Any) -> list[dict[str, Any]]:
    raw_models = payload.get("models") if isinstance(payload, dict) else payload
    if not isinstance(raw_models, list) or not raw_models:
        raise CaptureError("model catalog must contain a non-empty models list")
    models: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_models):
        if not isinstance(raw, dict):
            raise CaptureError(f"model row {index} must be an object")
        slug = raw.get("slug")
        default = raw.get("default_reasoning_level")
        levels = raw.get("supported_reasoning_levels")
        visibility = raw.get("visibility")
        supported_in_api = raw.get("supported_in_api")
        if not isinstance(slug, str) or not slug or slug in seen:
            raise CaptureError(f"model row {index} has a missing or duplicate slug")
        if default not in EFFORTS:
            raise CaptureError(f"model `{slug}` has an unsupported default effort")
        if not isinstance(levels, list) or not levels:
            raise CaptureError(f"model `{slug}` has no supported reasoning levels")
        efforts: list[str] = []
        for level in levels:
            if not isinstance(level, dict) or level.get("effort") not in EFFORTS:
                raise CaptureError(f"model `{slug}` has a malformed reasoning level")
            effort = level["effort"]
            if effort in efforts:
                raise CaptureError(f"model `{slug}` repeats effort `{effort}`")
            efforts.append(effort)
        if visibility not in {"list", "hide"} or not isinstance(supported_in_api, bool):
            raise CaptureError(f"model `{slug}` has malformed visibility/API support")
        seen.add(slug)
        models.append(
            {
                "slug": slug,
                "default_effort": default,
                "supported_efforts": efforts,
                "visibility": visibility,
                "supported_in_api": supported_in_api,
            }
        )
    return models


def _parse_catalog_result(result: subprocess.CompletedProcess[bytes], label: str) -> list[dict[str, Any]]:
    if len(result.stdout) > MAX_GIT_OUTPUT or len(result.stderr) > MAX_GIT_OUTPUT:
        raise CaptureError(f"{label} catalog command exceeded the 16 MiB output ceiling")
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise CaptureError(f"{label} catalog command failed ({result.returncode}): {detail}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CaptureError(f"{label} catalog command returned invalid JSON") from exc
    return normalize_catalog(payload)


def capture_catalog(run: Run = _default_run) -> tuple[str, list[dict[str, Any]]]:
    failures: list[str] = []
    for source, argv in (
        ("refreshed", ("codex", "debug", "models")),
        ("bundled", ("codex", "debug", "models", "--bundled")),
    ):
        try:
            return source, _parse_catalog_result(run(argv), source)
        except CaptureError as exc:
            failures.append(str(exc))
    raise CaptureError("; ".join(failures))


def parse_features(text: str) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[0] not in SELECTED_FEATURES:
            continue
        enabled_text = parts[-1]
        stage = " ".join(parts[1:-1])
        if enabled_text not in {"true", "false"}:
            raise CaptureError(f"feature `{parts[0]}` has an invalid enabled value")
        selected[parts[0]] = {"stage": stage, "enabled": enabled_text == "true"}
    missing = set(SELECTED_FEATURES) - set(selected)
    if missing:
        raise CaptureError(f"feature output is missing {sorted(missing)}")
    return {name: selected[name] for name in SELECTED_FEATURES}


def _run_text(argv: Sequence[str], run: Run) -> str:
    result = run(argv)
    if len(result.stdout) > MAX_GIT_OUTPUT or len(result.stderr) > MAX_GIT_OUTPUT:
        raise CaptureError(f"command exceeded output ceiling: {' '.join(argv)}")
    if result.returncode:
        raise CaptureError(f"command failed ({result.returncode}): {' '.join(argv)}")
    return result.stdout.decode("utf-8", "strict").strip()


def read_config(path: Path) -> dict[str, Any]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise CaptureError("Codex config could not be read") from exc
    agents = payload.get("agents", {})
    if not isinstance(agents, dict):
        raise CaptureError("Codex config `[agents]` must be a table")
    max_threads_configured = isinstance(agents, dict) and "max_threads" in agents
    max_depth_configured = isinstance(agents, dict) and "max_depth" in agents
    return {
        "configured_defaults": {
            "model": payload.get("model"),
            "model_reasoning_effort": payload.get("model_reasoning_effort"),
        },
        "configured_max_threads": agents.get("max_threads", 6),
        "configured_max_threads_source": "config" if max_threads_configured else "default",
        "configured_max_depth": agents.get("max_depth", 1),
        "configured_max_depth_source": "config" if max_depth_configured else "default",
    }


def count_custom_agents(codex_home: Path, repo_root: Path) -> dict[str, int]:
    installed = sorted((codex_home / "agents").glob("*.toml"))

    def marker_count(marker: str) -> int:
        count = 0
        for path in installed:
            try:
                if marker in path.read_text(encoding="utf-8"):
                    count += 1
            except OSError as exc:
                raise CaptureError("installed custom-agent file could not be read") from exc
        return count

    return {
        "repo_managed_source_count": len(
            list((repo_root / "plugins" / "team-execution" / "agents").glob("*.toml"))
        ),
        "installed_custom_agent_count": len(installed),
        "installed_team_execution_managed_count": marker_count(TEAM_EXECUTION_MARKER),
        "installed_verified_workflows_managed_count": marker_count(VERIFIED_WORKFLOWS_MARKER),
    }


def capture_projection(
    *,
    codex_home: Path,
    repo_root: Path | None = None,
    run: Run = _default_run,
) -> dict[str, Any]:
    repo_root = repo_root or Path(__file__).resolve().parent.parent
    source, models = capture_catalog(run)
    version_text = _run_text(("codex", "--version"), run)
    if not version_text.startswith("codex-cli "):
        raise CaptureError("unexpected `codex --version` output")
    features = parse_features(_run_text(("codex", "features", "list"), run))
    config = read_config(codex_home / "config.toml")
    return {
        "codex_cli_version": version_text.removeprefix("codex-cli "),
        **config,
        "catalog": {
            "source": source,
            "normalized_sha256": sha256_bytes(canonical_json_bytes(models)),
            "models": models,
        },
        "features": features,
        "custom_agent_counts": count_custom_agents(codex_home, repo_root),
    }


def compare_snapshot(
    snapshot: Mapping[str, Any],
    projection: Mapping[str, Any],
    *,
    session_facts: Mapping[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if snapshot.get("runtime", {}).get("codex_cli_version") != projection.get("codex_cli_version"):
        errors.append("Codex CLI version differs from the committed snapshot")
    if snapshot.get("configured_defaults") != projection.get("configured_defaults"):
        errors.append("configured model/effort differs from the committed snapshot")
    runtime = snapshot.get("runtime", {})
    for field in (
        "configured_max_threads",
        "configured_max_threads_source",
        "configured_max_depth",
        "configured_max_depth_source",
    ):
        if runtime.get(field) != projection.get(field):
            errors.append(f"{field} differs from the committed snapshot")
    if snapshot.get("catalog") != projection.get("catalog"):
        errors.append("normalized model catalog differs from the committed snapshot")
    if snapshot.get("features") != projection.get("features"):
        errors.append("selected feature state differs from the committed snapshot")
    snapshot_counts = {
        key: value
        for key, value in snapshot.get("custom_agents", {}).items()
        if key.endswith("_count")
    }
    if snapshot_counts != projection.get("custom_agent_counts"):
        errors.append("custom-agent counts differ from the committed snapshot")
    if session_facts is None:
        errors.append("explicit session facts are required for a full capability check")
        return errors
    expected_session_keys = {
        "effective_parent_permission_mode",
        "host_total_slots",
        "collaboration",
        "hook_capabilities",
    }
    if set(session_facts) != expected_session_keys:
        errors.append("session facts keys do not match the allowlisted tool-contract schema")
        return errors
    if runtime.get("effective_parent_permission_mode") != session_facts.get(
        "effective_parent_permission_mode"
    ):
        errors.append("effective parent permission mode differs from the committed snapshot")
    host_total_slots = session_facts.get("host_total_slots")
    if runtime.get("host_total_slots") != host_total_slots:
        errors.append("host slot capacity differs from the committed snapshot")
    configured_threads = projection.get("configured_max_threads")
    if isinstance(host_total_slots, int) and isinstance(configured_threads, int):
        effective_total = min(host_total_slots, configured_threads)
        if runtime.get("effective_total_slots") != effective_total:
            errors.append("effective total slot count differs from session/config truth")
        if runtime.get("effective_max_children") != effective_total - 1:
            errors.append("effective child capacity differs from session/config truth")
    if snapshot.get("collaboration") != session_facts.get("collaboration"):
        errors.append("collaboration tool schema differs from the committed snapshot")
    if snapshot.get("hook_capabilities") != session_facts.get("hook_capabilities"):
        errors.append("hook capability facts differ from the committed snapshot")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path("docs/validation/codex-runtime-capability-snapshot.json"),
    )
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--check", action="store_true", help="compare live discoverable fields to the snapshot")
    parser.add_argument("--json", action="store_true", help="print the sanitized discoverable projection")
    parser.add_argument(
        "--session-facts-json",
        help="allowlisted JSON copied from the active session tool contract; required with --check",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.check and not args.json:
        args.check = True
    try:
        projection = capture_projection(codex_home=args.codex_home)
        if args.json:
            print(json.dumps(projection, indent=2, sort_keys=True))
        if args.check:
            snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
            session_facts = (
                json.loads(args.session_facts_json) if args.session_facts_json is not None else None
            )
            if session_facts is not None and not isinstance(session_facts, dict):
                raise CaptureError("--session-facts-json must decode to an object")
            errors = compare_snapshot(snapshot, projection, session_facts=session_facts)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print("Codex capability projection and explicit session facts match the committed snapshot")
        return 0
    except (CaptureError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
