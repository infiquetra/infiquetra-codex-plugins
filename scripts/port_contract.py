#!/usr/bin/env python3
"""Create, validate, verify, and render staged Claude-to-Codex port contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = 1
RUNBOOK_VERSION = 5
SUPPORTED_RUNBOOK_VERSIONS = {3, 4, RUNBOOK_VERSION}
DEFAULT_MANIFEST = Path("docs/portability/ports/2026-07-29-codex-0146-native-harness.json")
DEFAULT_RENDER = Path(
    "docs/portability/classifications/2026-07-11-external-advisory-execution.md"
)
DEFAULT_RUNBOOK = Path("docs/portability/claude-to-codex-plugin-port-runbook.md")
DEFAULT_CAPABILITY = Path("docs/validation/codex-runtime-capability-snapshot.json")
DEFAULT_CAPABILITY_SCHEMA = Path("docs/validation/codex-runtime-capability-snapshot.schema.json")
DEFAULT_PLAN = Path(
    "docs/plans/2026-07-11-codex-external-advisory-execution-contract-plan.md"
)
DEFAULT_REVIEWS = (
    Path("docs/reviews/2026-07-11-codex-external-advisory-execution-contract-plan-review.md"),
)
DEFAULT_SOURCE_BASE = "38742ece89880a6b140be237edad6d3f13c97b54"
DEFAULT_SOURCE_TARGET = "675712b1d6a55ead11f3e971ed0e119354621bf2"
DEFAULT_CODEX_PLAN_BASE = "39f0a2f466cb6f58e203ce3e586a959ff853a342"
ACTIVE_PORT_ID = "external-advisory-execution-2026-07-11"
# Each Codex alignment round rotates this set to its own port and lets its predecessors go stale;
# the 0146 round did the same to the 0145-era ports, which still carry errors on main today. Only
# purpose-scoped ports archive a private snapshot, so only the alignment lineage rotates.
CURRENT_PORT_IDS = {
    "codex-0147-alignment-2026-08-08",
}
APPROVED_CODEX_EXECUTION_BASE = "d8f5d165ad0e859af9c7d7f1ba7461b00ec1ae95"
CODEX_EVIDENCE_REF = "refs/tags/evidence/external-advisory-execution-20260711"
EXPECTED_SOURCE_INVENTORY_SHA256 = "f6d67d4294f8658118cb90728f151c813e87e3fc684c786277fb8a2f07168db0"
EXPECTED_CODEX_INVENTORY_SHA256 = "e6182153e2b1e67522491863f485d325d0ae9fd1b6b14b8ea70e4ac0141e83ab"
DEFAULT_SOURCE_PATHS = (
    "plugins/saga/scripts/second_opinion.py",
    "plugins/agy/scripts/agy_delegate.py",
    "plugins/codex/scripts/codex_delegate.py",
    "tests/test_second_opinion.py",
    "tests/test_agy_delegate_contract.py",
    "tests/test_codex_delegate.py",
    "tests/test_codex_delegate_contract.py",
)
EXPECTED_SOURCE_COUNT = 3
EXPECTED_CODEX_COUNT = 7
VALID_STAGES = {"classification", "unit", "cutover"}
SOURCE_STATES = {"unclassified", "classified", "implemented", "verified"}
SOURCE_TREATMENTS = {None, "direct-port", "codex-adapt", "defer", "reject"}
CODEX_STATES = {"unclassified", "classified", "verified"}
CODEX_TREATMENTS = {None, "preserve", "reconcile", "superseded-by-plan"}
SURFACE_KINDS = {
    "agent",
    "changelog",
    "claude-manifest",
    "command",
    "config",
    "documentation",
    "fixture",
    "hook",
    "other",
    "reference",
    "script",
    "skill",
    "test",
}
HOST_PRIMITIVES = {"TeamCreate", "Workflow", "SendMessage", "ClaudeHook", "ClaudeAgent", "ClaudeCommand"}
EVIDENCE_KINDS = {
    "check",
    "review",
    "source-verification",
    "isolated-install",
    "fresh-session",
    "rollback",
    "cutover",
}
UNIT_IDS = {f"U{number}" for number in range(1, 15)}
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
SECRET_KEY_RE = re.compile(r"(?:^|_)(?:token|secret|credential|password|auth_json)(?:_|$)", re.I)
FORBIDDEN_SOURCE_DIRECT = {"claude-manifest", "command", "agent", "hook"}
MAX_GIT_OUTPUT = 16 * 1024 * 1024


class ContractError(RuntimeError):
    """Raised for invalid contract input or unsafe repository state."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _run_git(repo: Path, args: Sequence[str], *, allow_failure: bool = False) -> bytes:
    command = ["git", "-C", str(repo), *args]
    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except subprocess.TimeoutExpired as exc:
        raise ContractError(f"git command timed out: {' '.join(command[:4])}") from exc
    if len(result.stdout) > MAX_GIT_OUTPUT or len(result.stderr) > MAX_GIT_OUTPUT:
        raise ContractError("git command exceeded the 16 MiB output ceiling")
    if result.returncode and not allow_failure:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise ContractError(f"git command failed ({result.returncode}): {message}")
    return result.stdout


def resolve_ref(repo: Path, ref: str) -> str:
    value = _run_git(repo, ["rev-parse", "--verify", f"{ref}^{{commit}}"])
    resolved = value.decode().strip()
    if not HEX40_RE.fullmatch(resolved):
        raise ContractError(f"ref `{ref}` did not resolve to a full commit")
    return resolved


def optional_ref(repo: Path, ref: str) -> str | None:
    output = _run_git(repo, ["rev-parse", "--verify", f"{ref}^{{commit}}"], allow_failure=True)
    resolved = output.decode().strip()
    return resolved if HEX40_RE.fullmatch(resolved) else None


def is_ancestor(repo: Path, base: str, target: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", base, target],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    return result.returncode == 0


def parse_name_status_z(payload: bytes) -> list[dict[str, Any]]:
    if len(payload) > MAX_GIT_OUTPUT:
        raise ContractError("name-status payload exceeded the 16 MiB ceiling")
    if not payload:
        return []
    parts = payload.split(b"\0")
    if parts[-1] != b"":
        raise ContractError("name-status payload was not NUL terminated")
    parts.pop()
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(parts):
        status_text = parts[index].decode("utf-8", "surrogateescape")
        index += 1
        match = re.fullmatch(r"([AMDTC])|([RC])(\d{1,3})", status_text)
        if not match:
            raise ContractError(f"unsupported git name-status token `{status_text}`")
        change = match.group(1) or match.group(2)
        similarity = int(match.group(3)) if match.group(3) is not None else None
        if change in {"R", "C"}:
            if index + 1 >= len(parts):
                raise ContractError("rename/copy row is missing a path")
            old_path = parts[index].decode("utf-8", "surrogateescape")
            new_path = parts[index + 1].decode("utf-8", "surrogateescape")
            index += 2
        else:
            if index >= len(parts):
                raise ContractError("name-status row is missing a path")
            path = parts[index].decode("utf-8", "surrogateescape")
            index += 1
            old_path = path if change == "D" else None
            new_path = None if change == "D" else path
        rows.append(
            {
                "change": change,
                "old_path": old_path,
                "new_path": new_path,
                "similarity": similarity,
            }
        )
    return normalize_inventory(rows)


def normalize_inventory(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized = [
        {
            "change": row["change"],
            "old_path": row.get("old_path"),
            "new_path": row.get("new_path"),
            "similarity": row.get("similarity"),
        }
        for row in rows
    ]
    normalized.sort(key=lambda row: (row["old_path"] or "", row["new_path"] or "", row["change"]))
    seen: set[tuple[Any, ...]] = set()
    for row in normalized:
        key = (row["change"], row["old_path"], row["new_path"], row["similarity"])
        if key in seen:
            raise ContractError(f"duplicate inventory row: {key}")
        seen.add(key)
    return normalized


def inventory_digest(rows: Iterable[Mapping[str, Any]]) -> str:
    return sha256_bytes(canonical_json_bytes(normalize_inventory(rows)))


def git_inventory(repo: Path, base: str, target: str, pathspecs: Sequence[str] = ()) -> list[dict[str, Any]]:
    args = ["diff", "--name-status", "-z", "-M", f"{base}..{target}", "--", *pathspecs]
    return parse_name_status_z(_run_git(repo, args))


def git_tree_digest(repo: Path, commit: str, paths: Sequence[str]) -> str:
    """Hash exact tracked entries for a bounded path set at one commit."""
    normalized = sorted({validate_repo_path(path) for path in paths})
    if not normalized:
        raise ContractError("target_paths must contain at least one repository path")
    tree = _run_git(repo, ["ls-tree", "-r", "-z", "--full-tree", commit, "--", *normalized])
    if not tree:
        raise ContractError("target_paths do not resolve to tracked entries")
    return sha256_bytes(tree)


def row_id(prefix: str, row: Mapping[str, Any]) -> str:
    inventory_row = {
        "change": row.get("change"),
        "old_path": row.get("old_path"),
        "new_path": row.get("new_path"),
        "similarity": row.get("similarity"),
    }
    digest = sha256_bytes(canonical_json_bytes(inventory_row))[:16]
    return f"{prefix}-{digest}"


def source_surface(path: str) -> tuple[str, list[str]]:
    parts = PurePosixPath(path).parts
    name = parts[-1]
    primitives: list[str] = []
    if ".claude-plugin" in parts:
        return "claude-manifest", ["ClaudeCommand"] if name != "plugin.json" else []
    if "commands" in parts:
        return "command", ["ClaudeCommand"]
    if "agents" in parts:
        return "agent", ["ClaudeAgent"]
    if "hooks" in parts:
        return "hook", ["ClaudeHook"]
    if name == "CHANGELOG.md":
        return "changelog", primitives
    if name == "SKILL.md" or "skills" in parts and name.endswith(".md"):
        return "skill", primitives
    if name.endswith((".yaml", ".yml", ".json", ".toml")):
        return "config", primitives
    if path.startswith("tests/fixtures/"):
        return "fixture", primitives
    if path.startswith("tests/") or "/tests/" in path:
        return "test", primitives
    if "references" in parts:
        return "reference", primitives
    if name.endswith(".py"):
        return "script", primitives
    if name.endswith(".md"):
        return "documentation", primitives
    return "other", primitives


def _source_contract_row(row: Mapping[str, Any]) -> dict[str, Any]:
    path = str(row.get("new_path") or row.get("old_path"))
    surface, primitives = source_surface(path)
    return {
        "row_id": row_id("src", row),
        **dict(row),
        "surface_kind": surface,
        "host_primitives": primitives,
        "state": "unclassified",
        "treatment": None,
        "rationale": None,
        "units": [],
        "planned_targets": [],
        "planned_tests": [],
        "capability_refs": [],
        "codex_invariant_refs": [],
        "evidence_refs": [],
    }


def _codex_contract_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "row_id": row_id("codex", row),
        **dict(row),
        "state": "unclassified",
        "treatment": None,
        "invariant": None,
        "rationale": None,
        "units": [],
        "planned_targets": [],
        "planned_tests": [],
        "evidence_refs": [],
    }


def contained_file(root: Path, relative_path: str) -> Path:
    safe = validate_repo_path(relative_path)
    candidate = root / safe
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ContractError(f"artifact is missing: {safe}") from exc
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ContractError(f"artifact escapes the repository boundary: {safe}")
    return resolved


def _authority_entry(root: Path, path: Path) -> dict[str, str]:
    safe = validate_repo_path(path.as_posix())
    target = contained_file(root, safe)
    return {"path": safe, "sha256": sha256_file(target)}


def _source_topology_errors(value: Any, label: str = "source.topology") -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{label} must be an object"]
    expected_keys = {"left", "right", "common_base", "left_only_commits"}
    if set(value) != expected_keys:
        errors.append(
            f"{label} keys mismatch: missing={sorted(expected_keys - set(value))} "
            f"unexpected={sorted(set(value) - expected_keys)}"
        )
    for side_name in ("left", "right"):
        side = value.get(side_name)
        side_label = f"{label}.{side_name}"
        if not isinstance(side, dict):
            errors.append(f"{side_label} must be an object")
            continue
        side_keys = {"tag", "peeled_commit"}
        if set(side) != side_keys:
            errors.append(
                f"{side_label} keys mismatch: missing={sorted(side_keys - set(side))} "
                f"unexpected={sorted(set(side) - side_keys)}"
            )
        tag = side.get("tag")
        if (
            not isinstance(tag, str)
            or not tag.strip()
            or tag != tag.strip()
            or CONTROL_RE.search(tag)
        ):
            errors.append(f"{side_label}.tag must be a non-empty printable string")
        peeled_commit = side.get("peeled_commit")
        if not isinstance(peeled_commit, str) or not HEX40_RE.fullmatch(peeled_commit):
            errors.append(f"{side_label}.peeled_commit must be a full 40-character commit")
    common_base = value.get("common_base")
    if not isinstance(common_base, str) or not HEX40_RE.fullmatch(common_base):
        errors.append(f"{label}.common_base must be a full 40-character commit")
    left_only = value.get("left_only_commits")
    if not isinstance(left_only, list):
        errors.append(f"{label}.left_only_commits must be a list")
        return errors
    seen: set[str] = set()
    for index, row in enumerate(left_only):
        row_label = f"{label}.left_only_commits[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{row_label} must be an object")
            continue
        row_keys = {"commit", "disposition"}
        if set(row) != row_keys:
            errors.append(
                f"{row_label} keys mismatch: missing={sorted(row_keys - set(row))} "
                f"unexpected={sorted(set(row) - row_keys)}"
            )
        commit = row.get("commit")
        if not isinstance(commit, str) or not HEX40_RE.fullmatch(commit):
            errors.append(f"{row_label}.commit must be a full 40-character commit")
        elif commit in seen:
            errors.append(f"{row_label}.commit must be unique")
        else:
            seen.add(commit)
        disposition = row.get("disposition")
        if (
            not isinstance(disposition, str)
            or not disposition.strip()
            or CONTROL_RE.search(disposition)
        ):
            errors.append(f"{row_label}.disposition must be a non-empty printable string")
    return errors


def _normalize_source_topology(value: Any) -> dict[str, Any]:
    errors = _source_topology_errors(value)
    if errors:
        raise ContractError("; ".join(errors))
    return {
        "left": dict(value["left"]),
        "right": dict(value["right"]),
        "common_base": value["common_base"],
        "left_only_commits": [dict(row) for row in value["left_only_commits"]],
    }


def _verify_source_topology(source_repo: Path, topology: Mapping[str, Any]) -> dict[str, Any]:
    left = topology["left"]
    right = topology["right"]
    left_commit = resolve_ref(source_repo, str(left["tag"]))
    right_commit = resolve_ref(source_repo, str(right["tag"]))
    if left_commit != left["peeled_commit"]:
        raise ContractError(
            f"source topology left tag `{left['tag']}` peeled to {left_commit}, "
            f"not {left['peeled_commit']}"
        )
    if right_commit != right["peeled_commit"]:
        raise ContractError(
            f"source topology right tag `{right['tag']}` peeled to {right_commit}, "
            f"not {right['peeled_commit']}"
        )
    merge_base = _run_git(
        source_repo, ["merge-base", left_commit, right_commit]
    ).decode().strip()
    if not HEX40_RE.fullmatch(merge_base):
        raise ContractError("source topology merge base did not resolve to one full commit")
    if merge_base != topology["common_base"]:
        raise ContractError(
            f"source topology common base is {merge_base}, not {topology['common_base']}"
        )
    left_only_output = _run_git(
        source_repo,
        ["rev-list", "--left-only", f"{left_commit}...{right_commit}"],
    ).decode()
    left_only_commits = [line for line in left_only_output.splitlines() if line]
    if not all(HEX40_RE.fullmatch(commit) for commit in left_only_commits):
        raise ContractError("source topology left-only history contained an invalid commit")
    recorded_left_only = [str(row["commit"]) for row in topology["left_only_commits"]]
    if set(left_only_commits) != set(recorded_left_only):
        raise ContractError(
            "source topology left-only commits do not match the recorded dispositions"
        )
    return {
        "left_tag": left["tag"],
        "left_peeled_commit": left_commit,
        "right_tag": right["tag"],
        "right_peeled_commit": right_commit,
        "common_base": merge_base,
        "left_only_commits": left_only_commits,
    }


def build_manifest(
    root: Path,
    source_repo: Path,
    *,
    source_base: str,
    source_target: str,
    source_pathspecs: Sequence[str],
    codex_plan_base: str,
    codex_execution_base: str,
    runbook: Path,
    capability_snapshot: Path,
    capability_schema: Path,
    plan: Path,
    reviews: Sequence[Path],
    classification_path: Path,
    port_id: str = ACTIVE_PORT_ID,
    source_repository_id: str = "infiquetra/infiquetra-claude-plugins",
    codex_repository_id: str = "infiquetra/infiquetra-codex-plugins",
    codex_evidence_ref: str = CODEX_EVIDENCE_REF,
    version_policy: Sequence[Mapping[str, str]] | None = None,
    source_topology: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_base = resolve_ref(source_repo, source_base)
    source_target = resolve_ref(source_repo, source_target)
    codex_plan_base = resolve_ref(root, codex_plan_base)
    codex_execution_base = resolve_ref(root, codex_execution_base)
    normalized_topology: dict[str, Any] | None = None
    if source_topology is not None:
        normalized_topology = _normalize_source_topology(source_topology)
        if source_base != normalized_topology["common_base"]:
            raise ContractError("source base must equal source topology common base")
        if source_target != normalized_topology["right"]["peeled_commit"]:
            raise ContractError("source target must equal source topology right peeled commit")
        _verify_source_topology(source_repo, normalized_topology)
    if not is_ancestor(source_repo, source_base, source_target):
        raise ContractError("frozen source base is not an ancestor of the frozen target")
    if not is_ancestor(root, codex_plan_base, codex_execution_base):
        raise ContractError("Codex historical plan base is not an ancestor of the execution base")

    try:
        capability_schema_version = json.loads(
            contained_file(root, capability_snapshot.as_posix()).read_text(encoding="utf-8")
        ).get("schema_version")
    except (AttributeError, json.JSONDecodeError, OSError) as exc:
        raise ContractError("capability snapshot lacks a readable schema version") from exc
    if capability_schema_version not in {1, 2, 3}:
        raise ContractError("capability snapshot schema version is unsupported")

    source_rows = git_inventory(source_repo, source_base, source_target, source_pathspecs)
    codex_rows = git_inventory(root, codex_plan_base, codex_execution_base)
    source_head = resolve_ref(source_repo, "HEAD")

    if not port_id or CONTROL_RE.search(port_id):
        raise ContractError("port_id must be a non-empty printable string")
    if (
        not codex_evidence_ref.startswith("refs/tags/evidence/")
        or CONTROL_RE.search(codex_evidence_ref)
        or " " in codex_evidence_ref
    ):
        raise ContractError("codex evidence ref must be a safe evidence tag")
    default_version_policy: list[dict[str, str]] = [
        {
            "source_plugin": "fleet-core",
            "source_version": "0.8.4",
            "current_codex_identity": "fleet-core",
            "current_codex_version": "0.5.0",
            "target_codex_identity": "fleet-core",
            "target_codex_version": "0.8.4",
            "policy": "lineage-with-codex-adaptation",
            "release_unit": "U8",
        },
        {
            "source_plugin": "saga",
            "source_version": "0.75.17",
            "current_codex_identity": "saga",
            "current_codex_version": "0.65.0",
            "target_codex_identity": "saga",
            "target_codex_version": "0.75.17",
            "policy": "lineage-with-codex-adaptation",
            "release_unit": "U8",
        },
        {
            "source_plugin": "team-execution",
            "source_version": "2.14.3",
            "current_codex_identity": "team-execution",
            "current_codex_version": "2.3.0",
            "target_codex_identity": "verified-workflows",
            "target_codex_version": "1.0.0",
            "policy": "identity-migration-no-byte-parity",
            "release_unit": "U8",
        },
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "port_id": port_id,
        "authority": {
            "plan": _authority_entry(root, plan),
            "reviews": [_authority_entry(root, path) for path in reviews],
            "runbook": {**_authority_entry(root, runbook), "version": RUNBOOK_VERSION},
            "capability_snapshot": {
                **_authority_entry(root, capability_snapshot),
                "schema_version": capability_schema_version,
                "schema_path": _authority_entry(root, capability_schema)["path"],
                "schema_sha256": _authority_entry(root, capability_schema)["sha256"],
            },
            "classification_path": validate_repo_path(classification_path.as_posix()),
        },
        "source": {
            **({"topology": normalized_topology} if normalized_topology is not None else {}),
            "repository_id": source_repository_id,
            "base_ref": source_base,
            "target_ref": source_target,
            "observed_refs": {
                "head": source_head,
                "local_main": optional_ref(source_repo, "main"),
                "origin_main": optional_ref(source_repo, "origin/main"),
            },
            "target_reachable": is_ancestor(source_repo, source_target, source_head),
            "pathspecs": [validate_repo_path(path) for path in source_pathspecs],
            "expected_count": len(source_rows),
            "inventory_sha256": inventory_digest(source_rows),
            "rows": [_source_contract_row(row) for row in source_rows],
        },
        "codex": {
            "repository_id": codex_repository_id,
            "historical_plan_base": codex_plan_base,
            "execution_base": codex_execution_base,
            "evidence_ref": codex_evidence_ref,
            "observed_origin_main": optional_ref(root, "origin/main"),
            "expected_count": len(codex_rows),
            "inventory_sha256": inventory_digest(codex_rows),
            "rows": [_codex_contract_row(row) for row in codex_rows],
        },
        "version_policy": [dict(policy) for policy in (version_policy or default_version_policy)],
        "evidence": [],
        "release_evidence": {
            "review": None,
            "isolated_install": None,
            "fresh_session": None,
            "rollback": None,
            "cutover": None,
        },
        "refresh_changes": [],
    }


def validate_repo_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError("repository path must be a non-empty string")
    if CONTROL_RE.search(value) or "\\" in value or value.startswith("~"):
        raise ContractError(f"unsafe repository path `{value}`")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ContractError(f"repository path must be contained and relative: `{value}`")
    lowered = value.lower()
    if path.parts and path.parts[0] == ".git":
        raise ContractError(f"repository path must not enter .git: `{value}`")
    if ".codex/plugins/cache" in lowered or "/cache/" in lowered or lowered.startswith("cache/"):
        raise ContractError(f"installed cache must not be source: `{value}`")
    return path.as_posix()


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str, errors: list[str]) -> None:
    actual = set(value)
    if actual != expected:
        errors.append(f"{label} keys mismatch: missing={sorted(expected - actual)} unexpected={sorted(actual - expected)}")


def _check_commit(value: Any, label: str, errors: list[str]) -> None:
    if value is not None and (not isinstance(value, str) or not HEX40_RE.fullmatch(value)):
        errors.append(f"{label} must be a full 40-character commit")


def _check_digest(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not HEX64_RE.fullmatch(value):
        errors.append(f"{label} must be a lowercase SHA-256")


def _scan_forbidden_keys(value: Any, label: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY_RE.search(key):
                errors.append(f"{label} contains forbidden secret-shaped key `{key}`")
            _scan_forbidden_keys(child, f"{label}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_forbidden_keys(child, f"{label}[{index}]", errors)


def _validate_artifact(root: Path, entry: Mapping[str, Any], label: str, errors: list[str]) -> None:
    _exact_keys(entry, {"path", "sha256"}, label, errors)
    path_value = entry.get("path")
    try:
        safe = validate_repo_path(path_value)
    except (ContractError, TypeError) as exc:
        errors.append(f"{label}: {exc}")
        return
    try:
        path = contained_file(root, safe)
    except ContractError as exc:
        errors.append(f"{label}: {exc}")
        return
    expected = entry.get("sha256")
    _check_digest(expected, f"{label}.sha256", errors)
    if isinstance(expected, str) and sha256_file(path) != expected:
        errors.append(f"{label} digest is stale: {safe}")


def _historical_file_by_sha256(root: Path, path: str, expected: str) -> bytes:
    """Recover a digest-bound historical authority file without changing its manifest."""

    commits = _run_git(root, ["log", "--all", "--format=%H", "--", path]).decode().splitlines()
    if len(commits) > 256:
        raise ContractError("historical authority search exceeded the commit ceiling")
    for commit in commits:
        if not HEX40_RE.fullmatch(commit):
            continue
        content = _run_git(root, ["show", f"{commit}:{path}"], allow_failure=True)
        if content and sha256_bytes(content) == expected:
            return content
    raise ContractError("digest-bound historical authority preimage is unavailable")


def _json_schema_ref(root_schema: Mapping[str, Any], reference: str) -> Mapping[str, Any]:
    if not reference.startswith("#/"):
        raise ContractError(f"unsupported JSON Schema reference `{reference}`")
    value: Any = root_schema
    for part in reference[2:].split("/"):
        if not isinstance(value, dict) or part not in value:
            raise ContractError(f"unresolved JSON Schema reference `{reference}`")
        value = value[part]
    if not isinstance(value, dict):
        raise ContractError(f"JSON Schema reference is not an object: `{reference}`")
    return value


def validate_json_schema_instance(
    value: Any,
    schema: Mapping[str, Any],
    *,
    root_schema: Mapping[str, Any] | None = None,
    label: str = "value",
) -> list[str]:
    """Validate the small draft-2020-12 subset used by the committed snapshot schema."""

    root_schema = root_schema or schema
    errors: list[str] = []
    if "$ref" in schema:
        try:
            target = _json_schema_ref(root_schema, str(schema["$ref"]))
        except ContractError as exc:
            return [f"{label}: {exc}"]
        return validate_json_schema_instance(value, target, root_schema=root_schema, label=label)
    if "const" in schema and value != schema["const"]:
        errors.append(f"{label} must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{label} must be one of {schema['enum']!r}")

    expected_type = schema.get("type")
    type_ok = True
    if expected_type == "object":
        type_ok = isinstance(value, dict)
    elif expected_type == "array":
        type_ok = isinstance(value, list)
    elif expected_type == "string":
        type_ok = isinstance(value, str)
    elif expected_type == "integer":
        type_ok = isinstance(value, int) and not isinstance(value, bool)
    elif expected_type == "boolean":
        type_ok = isinstance(value, bool)
    if not type_ok:
        return [f"{label} must be {expected_type}"]

    if isinstance(value, dict) and expected_type == "object":
        required = set(schema.get("required", []))
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            return [f"{label} schema properties must be an object"]
        missing = required - set(value)
        if missing:
            errors.append(f"{label} is missing required keys {sorted(missing)}")
        if schema.get("additionalProperties") is False:
            unexpected = set(value) - set(properties)
            if unexpected:
                errors.append(f"{label} has unexpected keys {sorted(unexpected)}")
        for key, child in value.items():
            child_schema = properties.get(key)
            if isinstance(child_schema, dict):
                errors.extend(
                    validate_json_schema_instance(
                        child,
                        child_schema,
                        root_schema=root_schema,
                        label=f"{label}.{key}",
                    )
                )
    elif isinstance(value, list) and expected_type == "array":
        minimum = schema.get("minItems")
        if isinstance(minimum, int) and len(value) < minimum:
            errors.append(f"{label} must contain at least {minimum} items")
        if schema.get("uniqueItems") is True:
            encoded = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{label} must contain unique items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, child in enumerate(value):
                errors.extend(
                    validate_json_schema_instance(
                        child,
                        item_schema,
                        root_schema=root_schema,
                        label=f"{label}[{index}]",
                    )
                )
    elif isinstance(value, str) and expected_type == "string":
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            errors.append(f"{label} does not match required pattern")
        if schema.get("format") == "date-time" and re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
        ) is None:
            errors.append(f"{label} must be an RFC3339 UTC timestamp")
    elif isinstance(value, int) and not isinstance(value, bool) and expected_type == "integer":
        minimum = schema.get("minimum")
        if isinstance(minimum, int) and value < minimum:
            errors.append(f"{label} must be at least {minimum}")
    return errors


def _validate_inventory_rows(rows: Any, label: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        errors.append(f"{label} must be a list")
        return []
    inventory: list[dict[str, Any]] = []
    row_ids: set[str] = set()
    for index, row in enumerate(rows):
        row_label = f"{label}[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{row_label} must be an object")
            continue
        row_id_value = row.get("row_id")
        if not isinstance(row_id_value, str) or row_id_value in row_ids:
            errors.append(f"{row_label}.row_id must be a unique string")
        else:
            row_ids.add(row_id_value)
        change = row.get("change")
        old_path = row.get("old_path")
        new_path = row.get("new_path")
        similarity = row.get("similarity")
        if change not in {"A", "M", "D", "R", "C", "T"}:
            errors.append(f"{row_label}.change is invalid")
        for key, path_value in (("old_path", old_path), ("new_path", new_path)):
            if path_value is not None:
                try:
                    validate_repo_path(path_value)
                except (ContractError, TypeError) as exc:
                    errors.append(f"{row_label}.{key}: {exc}")
        if similarity is not None and (not isinstance(similarity, int) or not 0 <= similarity <= 100):
            errors.append(f"{row_label}.similarity must be null or 0..100")
        inventory.append({"change": change, "old_path": old_path, "new_path": new_path, "similarity": similarity})
    return inventory


SOURCE_ROW_KEYS = {
    "row_id", "change", "old_path", "new_path", "similarity", "surface_kind", "host_primitives",
    "state", "treatment", "rationale", "units", "planned_targets", "planned_tests", "capability_refs",
    "codex_invariant_refs", "evidence_refs",
}
CODEX_ROW_KEYS = {
    "row_id", "change", "old_path", "new_path", "similarity", "state", "treatment", "invariant",
    "rationale", "units", "planned_targets", "planned_tests", "evidence_refs",
}


def _validate_string_list(value: Any, label: str, errors: list[str], *, paths: bool = False) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{label} must be a list of strings")
        return []
    if len(value) != len(set(value)):
        errors.append(f"{label} must not contain duplicates")
    if paths:
        for item in value:
            try:
                validate_repo_path(item)
            except ContractError as exc:
                errors.append(f"{label}: {exc}")
    return value


def _validate_evidence_argv(value: Any, label: str, errors: list[str]) -> list[str]:
    argv = _validate_string_list(value, label, errors)
    if not argv:
        errors.append(f"{label} must contain the executed command")
        return argv
    secret_arg = re.compile(r"(?i)(?:^|[-_])(token|password|secret|credential|bearer)(?:=|$)")
    for argument in argv:
        if CONTROL_RE.search(argument):
            errors.append(f"{label} contains a control character")
        if secret_arg.search(argument):
            errors.append(f"{label} contains a secret-shaped argument")
        if argument.startswith(("/", "~")) or re.search(r"(?:^|=)(?:/|~)", argument):
            errors.append(f"{label} contains an absolute or home-relative path")
        if "/" in argument:
            path = PurePosixPath(argument)
            lowered = argument.lower()
            if ".." in path.parts or ".codex/plugins/cache" in lowered or "/cache/" in lowered:
                errors.append(f"{label} contains an unsafe or cache path")
    return argv


def _valid_recorded_at(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _validate_source_rows(rows: list[dict[str, Any]], stage: str, errors: list[str]) -> None:
    for index, row in enumerate(rows):
        label = f"source.rows[{index}]"
        _exact_keys(row, SOURCE_ROW_KEYS, label, errors)
        if row.get("surface_kind") not in SURFACE_KINDS:
            errors.append(f"{label}.surface_kind is invalid")
        primitives = _validate_string_list(row.get("host_primitives"), f"{label}.host_primitives", errors)
        if set(primitives) - HOST_PRIMITIVES:
            errors.append(f"{label}.host_primitives contains unknown values")
        state = row.get("state")
        treatment = row.get("treatment")
        if state not in SOURCE_STATES:
            errors.append(f"{label}.state is invalid")
        if treatment not in SOURCE_TREATMENTS:
            errors.append(f"{label}.treatment is invalid")
        if stage in VALID_STAGES and (state == "unclassified" or treatment is None):
            errors.append(f"{label} is not classified")
        rationale = row.get("rationale")
        if treatment is not None and (not isinstance(rationale, str) or not rationale.strip()):
            errors.append(f"{label}.rationale is required")
        units = _validate_string_list(row.get("units"), f"{label}.units", errors)
        if set(units) - UNIT_IDS:
            errors.append(f"{label}.units contains an unknown U-ID")
        targets = _validate_string_list(row.get("planned_targets"), f"{label}.planned_targets", errors, paths=True)
        tests = _validate_string_list(row.get("planned_tests"), f"{label}.planned_tests", errors, paths=True)
        _validate_string_list(row.get("capability_refs"), f"{label}.capability_refs", errors)
        _validate_string_list(row.get("codex_invariant_refs"), f"{label}.codex_invariant_refs", errors)
        evidence_refs = _validate_string_list(row.get("evidence_refs"), f"{label}.evidence_refs", errors)
        if treatment == "direct-port" and (row.get("surface_kind") in FORBIDDEN_SOURCE_DIRECT or primitives):
            errors.append(f"{label}: Claude-only surface/primitive cannot be direct-port")
        if treatment in {"direct-port", "codex-adapt"} and (not targets or not tests):
            errors.append(f"{label}: {treatment} requires planned targets and tests")
        if treatment in {"defer", "reject"} and units:
            errors.append(f"{label}: deferred/rejected rows must not claim implementation units")
        if state == "verified" and not evidence_refs:
            errors.append(f"{label}: verified state requires evidence")


def _validate_codex_rows(rows: list[dict[str, Any]], stage: str, errors: list[str]) -> None:
    for index, row in enumerate(rows):
        label = f"codex.rows[{index}]"
        _exact_keys(row, CODEX_ROW_KEYS, label, errors)
        state = row.get("state")
        treatment = row.get("treatment")
        if state not in CODEX_STATES:
            errors.append(f"{label}.state is invalid")
        if treatment not in CODEX_TREATMENTS:
            errors.append(f"{label}.treatment is invalid")
        if stage in VALID_STAGES and (state == "unclassified" or treatment is None):
            errors.append(f"{label} is not classified")
        if treatment is not None:
            for key in ("invariant", "rationale"):
                if not isinstance(row.get(key), str) or not row[key].strip():
                    errors.append(f"{label}.{key} is required")
        units = _validate_string_list(row.get("units"), f"{label}.units", errors)
        if set(units) - UNIT_IDS:
            errors.append(f"{label}.units contains an unknown U-ID")
        _validate_string_list(row.get("planned_targets"), f"{label}.planned_targets", errors, paths=True)
        _validate_string_list(row.get("planned_tests"), f"{label}.planned_tests", errors, paths=True)
        evidence_refs = _validate_string_list(row.get("evidence_refs"), f"{label}.evidence_refs", errors)
        if state == "verified" and not evidence_refs:
            errors.append(f"{label}: verified state requires evidence")


def _validate_capability_snapshot(
    root: Path,
    entry: Mapping[str, Any],
    errors: list[str],
    *,
    snapshot_bytes: bytes | None = None,
    schema_bytes: bytes | None = None,
    enforce_current_contract: bool = True,
) -> None:
    try:
        path = contained_file(root, str(entry.get("path", "")))
        schema_path = contained_file(root, str(entry.get("schema_path", "")))
    except ContractError:
        return
    try:
        snapshot = json.loads(
            snapshot_bytes.decode("utf-8")
            if snapshot_bytes is not None
            else path.read_text(encoding="utf-8")
        )
        snapshot_schema = json.loads(
            schema_bytes.decode("utf-8")
            if schema_bytes is not None
            else schema_path.read_text(encoding="utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
        errors.append(f"capability snapshot/schema is unreadable: {exc}")
        return
    if not isinstance(snapshot_schema, dict):
        errors.append("capability snapshot schema must be an object")
        return
    errors.extend(
        f"capability snapshot schema: {error}"
        for error in validate_json_schema_instance(snapshot, snapshot_schema, label="snapshot")
    )
    expected_top = {
        "schema_version", "captured_at", "refs", "runtime", "configured_defaults", "catalog", "features",
        "custom_agents", "collaboration", "hook_capabilities", "capability_dimensions", "official_sources",
    }
    if isinstance(snapshot, dict):
        _exact_keys(snapshot, expected_top, "capability snapshot", errors)
    else:
        errors.append("capability snapshot must be an object")
        return
    models = snapshot.get("catalog", {}).get("models", [])
    include_multi_agent_version = bool(models) and all(
        isinstance(model, dict) and "multi_agent_version" in model for model in models
    )
    # Same presence-inference rule as above, so an r3 snapshot keeps reproducing its recorded
    # digest while an r4 one includes the two derived projections. This projection has to mirror
    # CatalogModel.to_jsonable exactly or the digest comparison below is a false negative.
    derived_projection_keys = ("multi_agent_v2_override_filter", "multi_agent_v2_collaboration")
    include_derived_projections = bool(models) and all(
        isinstance(model, dict) and all(key in model for key in derived_projection_keys)
        for model in models
    )
    projection = []
    for model in models:
        if not isinstance(model, dict):
            continue
        row = {
            "slug": model.get("slug"),
            "default_effort": model.get("default_effort"),
            "supported_efforts": model.get("supported_efforts"),
            "visibility": model.get("visibility"),
            "supported_in_api": model.get("supported_in_api"),
        }
        if include_multi_agent_version:
            row["multi_agent_version"] = model.get("multi_agent_version")
        if include_derived_projections:
            for key in derived_projection_keys:
                row[key] = model.get(key)
        projection.append(row)
    expected_digest = snapshot.get("catalog", {}).get("normalized_sha256")
    if sha256_bytes(canonical_json_bytes(projection)) != expected_digest:
        errors.append("capability snapshot catalog digest is stale")
    runtime = snapshot.get("runtime", {})
    if isinstance(runtime, dict):
        configured = runtime.get("configured_max_threads")
        host = runtime.get("host_total_slots")
        effective = runtime.get("effective_total_slots")
        children = runtime.get("effective_max_children")
        if all(isinstance(value, int) for value in (configured, host, effective, children)):
            if effective != min(configured, host) or children != effective - 1:
                errors.append("capability snapshot thread capacity arithmetic is inconsistent")
    if not enforce_current_contract:
        return
    spawn = snapshot.get("collaboration", {}).get("spawn", {})
    if isinstance(spawn, dict) and spawn.get("contract_version") == "v1":
        # MultiAgent V2 retired to v1 (operator decision, 2026-07-19): nickname/role spawn with
        # rollout-attested child receipts; no per-child sandbox override is claimable on v1.
        if spawn.get("available") is not True:
            errors.append("capability snapshot must record v1 spawn availability")
        receipt_fields = set(spawn.get("spawn_receipt_fields") or [])
        if not {"agent_nickname", "agent_role", "depth"}.issubset(receipt_fields):
            errors.append("capability snapshot v1 spawn receipts must attest nickname, role, and depth")
        if spawn.get("per_child_sandbox") is not False:
            errors.append("capability snapshot must not claim direct per-child sandbox override")
        if spawn.get("named_profile_selection") != "rollout-attested":
            errors.append("capability snapshot v1 named-profile selection must be rollout-attested")
    elif isinstance(spawn, dict) and spawn.get("contract_version") == "v2":
        if spawn.get("tool_namespace") != "collaboration":
            errors.append("capability snapshot spawn namespace must be `collaboration`")
        if spawn.get("hide_spawn_agent_metadata") is not False:
            errors.append("capability snapshot must expose named-profile metadata")
        if spawn.get("request_fields") != [
            "agent_type",
            "fork_turns",
            "message",
            "model",
            "reasoning_effort",
            "task_name",
        ]:
            errors.append("capability snapshot spawn fields do not match the live tool contract")
        if spawn.get("default_fork_turns") != "all" or spawn.get(
            "profile_selection_fork_turns"
        ) != ["none", "positive-integer"]:
            errors.append("capability snapshot profile-selection fork contract drifted")
        for field in ("per_child_agent_type", "per_child_model", "per_child_effort"):
            if spawn.get(field) is not True:
                errors.append(f"capability snapshot must claim configured `{field}`")
        if spawn.get("per_child_sandbox") is not False:
            errors.append("capability snapshot must not claim direct per-child sandbox override")
        if spawn.get("response_fields") != ["agent_id", "nickname", "task_name"]:
            errors.append("capability snapshot V2 spawn response fields drifted")
        if spawn.get("runtime_receipt_sources") != ["session_meta", "turn_context"]:
            errors.append("capability snapshot V2 runtime receipt sources drifted")
        if spawn.get("selection_readback_fields") != [
            "agent_path",
            "agent_role",
            "model",
            "reasoning_effort",
            "model_provider",
            "approval_policy",
            "permission_profile",
            "sandbox_policy",
            "multi_agent_version",
        ]:
            errors.append("capability snapshot child receipt fields drifted")
        context = snapshot.get("collaboration", {}).get("context", {})
        if not isinstance(context, dict) or context.get(
            "child_permissions_inherit_parent_turn"
        ) is not True:
            errors.append("capability snapshot must record V2 parent-turn permission inheritance")
    elif isinstance(spawn, dict) and spawn.get("contract_version") is None:
        if spawn.get("tool_namespace") != "agents":
            errors.append("capability snapshot spawn namespace must be `agents`")
        if spawn.get("selection_readback_fields") != [
            "agent_type",
            "effort",
            "model",
            "sandbox_mode",
        ]:
            errors.append("capability snapshot legacy child receipt fields drifted")
    elif isinstance(spawn, dict):
        errors.append("capability snapshot collaboration.spawn contract_version is unsupported")
    dimensions = snapshot.get("capability_dimensions", {})
    workflow_names = {row.get("name"): row.get("status") for row in dimensions.get("workflow_modes", []) if isinstance(row, dict)}
    if workflow_names.get("source-workflow") != "unsupported":
        errors.append("source Workflow must remain unsupported")
    leaf_names = {row.get("name") for row in dimensions.get("step_vehicles", []) if isinstance(row, dict)}
    if "goal" in leaf_names or "hooks" in leaf_names or "fork" in leaf_names:
        errors.append("Goal, hooks, and fork must not be leaf executors")


def validate_manifest(root: Path, manifest: Mapping[str, Any], stage: str = "classification", unit: str | None = None) -> list[str]:
    errors: list[str] = []
    authority_hint = manifest.get("authority")
    plan_hint = authority_hint.get("plan") if isinstance(authority_hint, dict) else None
    active_contract = (
        isinstance(plan_hint, dict)
        and plan_hint.get("path") == DEFAULT_PLAN.as_posix()
    )
    approved_evidence_base = APPROVED_CODEX_EXECUTION_BASE
    if stage not in VALID_STAGES:
        return [f"unknown port-contract stage `{stage}`"]
    if stage == "unit" and unit not in UNIT_IDS:
        return ["unit-stage validation requires --unit U1..U10"]
    top_keys = {
        "schema_version", "port_id", "authority", "source", "codex", "version_policy", "evidence",
        "release_evidence", "refresh_changes",
    }
    _exact_keys(manifest, top_keys, "manifest", errors)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    port_id = manifest.get("port_id")
    current_contract = port_id in CURRENT_PORT_IDS
    if not isinstance(port_id, str) or not port_id or CONTROL_RE.search(port_id):
        errors.append("port_id must be a non-empty printable string")
    if active_contract and port_id != ACTIVE_PORT_ID:
        errors.append(f"port_id must remain the active contract `{ACTIVE_PORT_ID}`")
    _scan_forbidden_keys(manifest, "manifest", errors)

    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority must be an object")
    else:
        _exact_keys(authority, {"plan", "reviews", "runbook", "capability_snapshot", "classification_path"}, "authority", errors)
        if isinstance(authority.get("plan"), dict):
            _validate_artifact(root, authority["plan"], "authority.plan", errors)
        reviews = authority.get("reviews")
        if not isinstance(reviews, list) or not reviews:
            errors.append("authority.reviews must be a non-empty list")
        else:
            for index, review in enumerate(reviews):
                if isinstance(review, dict):
                    _validate_artifact(root, review, f"authority.reviews[{index}]", errors)
                else:
                    errors.append(f"authority.reviews[{index}] must be an object")
        runbook = authority.get("runbook")
        if isinstance(runbook, dict):
            _exact_keys(runbook, {"path", "version", "sha256"}, "authority.runbook", errors)
            if runbook.get("version") not in SUPPORTED_RUNBOOK_VERSIONS:
                errors.append("authority.runbook.version is unsupported")
            if current_contract:
                _validate_artifact(
                    root,
                    {"path": runbook.get("path"), "sha256": runbook.get("sha256")},
                    "authority.runbook",
                    errors,
                )
            else:
                try:
                    runbook_path = validate_repo_path(str(runbook.get("path", "")))
                    runbook_digest = str(runbook.get("sha256", ""))
                    _check_digest(runbook_digest, "authority.runbook.sha256", errors)
                    _historical_file_by_sha256(root, runbook_path, runbook_digest)
                except ContractError as exc:
                    errors.append(f"authority.runbook historical preimage: {exc}")
        else:
            errors.append("authority.runbook must be an object")
        capability = authority.get("capability_snapshot")
        if isinstance(capability, dict):
            _exact_keys(
                capability,
                {"path", "schema_version", "sha256", "schema_path", "schema_sha256"},
                "authority.capability_snapshot",
                errors,
            )
            if capability.get("schema_version") not in {1, 2, 3}:
                errors.append("authority.capability_snapshot.schema_version must be 1, 2, or 3")
            historical_snapshot: bytes | None = None
            historical_schema: bytes | None = None
            if not current_contract:
                try:
                    snapshot_path = validate_repo_path(str(capability.get("path", "")))
                    schema_path = validate_repo_path(str(capability.get("schema_path", "")))
                    expected = str(capability.get("sha256", ""))
                    schema_expected = str(capability.get("schema_sha256", ""))
                    _check_digest(
                        expected, "authority.capability_snapshot.sha256", errors
                    )
                    _check_digest(
                        schema_expected,
                        "authority.capability_snapshot.schema_sha256",
                        errors,
                    )
                    historical_snapshot = _historical_file_by_sha256(
                        root, snapshot_path, expected
                    )
                    historical_schema = _historical_file_by_sha256(
                        root, schema_path, schema_expected
                    )
                except ContractError as exc:
                    errors.append(f"authority.capability_snapshot historical preimage: {exc}")
            else:
                _validate_artifact(root, {"path": capability.get("path"), "sha256": capability.get("sha256")}, "authority.capability_snapshot", errors)
                _validate_artifact(
                    root,
                    {
                        "path": capability.get("schema_path"),
                        "sha256": capability.get("schema_sha256"),
                    },
                    "authority.capability_snapshot.schema",
                    errors,
                )
            _validate_capability_snapshot(
                root,
                capability,
                errors,
                snapshot_bytes=historical_snapshot,
                schema_bytes=historical_schema,
                enforce_current_contract=current_contract,
            )
        else:
            errors.append("authority.capability_snapshot must be an object")
        try:
            validate_repo_path(authority.get("classification_path"))
        except (ContractError, TypeError) as exc:
            errors.append(f"authority.classification_path: {exc}")

    source = manifest.get("source")
    source_rows: list[dict[str, Any]] = []
    if not isinstance(source, dict):
        errors.append("source must be an object")
    else:
        source_keys = {
            "repository_id", "base_ref", "target_ref", "observed_refs", "target_reachable",
            "pathspecs", "expected_count", "inventory_sha256", "rows",
        }
        if "topology" in source:
            source_keys.add("topology")
        _exact_keys(source, source_keys, "source", errors)
        _check_commit(source.get("base_ref"), "source.base_ref", errors)
        _check_commit(source.get("target_ref"), "source.target_ref", errors)
        topology = source.get("topology")
        if "topology" in source:
            topology_errors = _source_topology_errors(topology)
            errors.extend(topology_errors)
            if not topology_errors:
                if source.get("base_ref") != topology["common_base"]:
                    errors.append("source.base_ref must equal source.topology.common_base")
                if source.get("target_ref") != topology["right"]["peeled_commit"]:
                    errors.append(
                        "source.target_ref must equal source.topology.right.peeled_commit"
                    )
        observed = source.get("observed_refs")
        if isinstance(observed, dict):
            _exact_keys(observed, {"head", "local_main", "origin_main"}, "source.observed_refs", errors)
            for key in ("head", "local_main", "origin_main"):
                _check_commit(observed.get(key), f"source.observed_refs.{key}", errors)
        else:
            errors.append("source.observed_refs must be an object")
        paths = _validate_string_list(source.get("pathspecs"), "source.pathspecs", errors, paths=True)
        if active_contract and tuple(paths) != DEFAULT_SOURCE_PATHS:
            errors.append("source.pathspecs changed from the four approved focused paths")
        if active_contract and source.get("base_ref") != DEFAULT_SOURCE_BASE:
            errors.append("source.base_ref changed from the approved frozen base")
        if active_contract and source.get("target_ref") != DEFAULT_SOURCE_TARGET:
            errors.append("source.target_ref changed from the approved frozen target")
        source_rows = source.get("rows") if isinstance(source.get("rows"), list) else []
        inventory = _validate_inventory_rows(source_rows, "source.rows", errors)
        if source.get("expected_count") != len(source_rows):
            errors.append("source.expected_count does not match rows")
        if active_contract and len(source_rows) != EXPECTED_SOURCE_COUNT:
            errors.append(f"focused source inventory must contain exactly {EXPECTED_SOURCE_COUNT} rows")
        expected_digest = source.get("inventory_sha256")
        _check_digest(expected_digest, "source.inventory_sha256", errors)
        if inventory_digest(inventory) != expected_digest:
            errors.append("source inventory digest is stale")
        if active_contract and expected_digest != EXPECTED_SOURCE_INVENTORY_SHA256:
            errors.append("source inventory digest changed from the approved frozen inventory")
        _validate_source_rows(source_rows, stage, errors)

    codex = manifest.get("codex")
    codex_evidence_head: str | None = None
    codex_rows: list[dict[str, Any]] = []
    if not isinstance(codex, dict):
        errors.append("codex must be an object")
    else:
        _exact_keys(codex, {"repository_id", "historical_plan_base", "execution_base", "evidence_ref", "observed_origin_main", "expected_count", "inventory_sha256", "rows"}, "codex", errors)
        _check_commit(codex.get("historical_plan_base"), "codex.historical_plan_base", errors)
        _check_commit(codex.get("execution_base"), "codex.execution_base", errors)
        _check_commit(codex.get("observed_origin_main"), "codex.observed_origin_main", errors)
        if active_contract and codex.get("historical_plan_base") != DEFAULT_CODEX_PLAN_BASE:
            errors.append("Codex historical plan base changed from the approved value")
        if active_contract and codex.get("execution_base") != APPROVED_CODEX_EXECUTION_BASE:
            errors.append("Codex execution base changed from the approved value")
        evidence_ref = codex.get("evidence_ref")
        if active_contract and evidence_ref != CODEX_EVIDENCE_REF:
            errors.append(f"codex.evidence_ref must remain `{CODEX_EVIDENCE_REF}`")
        elif active_contract:
            try:
                codex_evidence_head = resolve_ref(root, evidence_ref)
            except ContractError as exc:
                errors.append(f"codex.evidence_ref is unavailable: {exc}")
            else:
                if not is_ancestor(root, APPROVED_CODEX_EXECUTION_BASE, codex_evidence_head):
                    errors.append("codex.evidence_ref does not retain the approved execution base")
        elif (
            not isinstance(evidence_ref, str)
            or not evidence_ref.startswith("refs/tags/evidence/")
            or CONTROL_RE.search(evidence_ref)
            or " " in evidence_ref
        ):
            errors.append("codex.evidence_ref must be a safe evidence tag")
        codex_rows = codex.get("rows") if isinstance(codex.get("rows"), list) else []
        inventory = _validate_inventory_rows(codex_rows, "codex.rows", errors)
        if codex.get("expected_count") != len(codex_rows):
            errors.append("codex.expected_count does not match rows")
        if active_contract and len(codex_rows) != EXPECTED_CODEX_COUNT:
            errors.append(f"Codex drift inventory must contain exactly {EXPECTED_CODEX_COUNT} rows")
        expected_digest = codex.get("inventory_sha256")
        _check_digest(expected_digest, "codex.inventory_sha256", errors)
        if inventory_digest(inventory) != expected_digest:
            errors.append("Codex drift inventory digest is stale")
        if active_contract and expected_digest != EXPECTED_CODEX_INVENTORY_SHA256:
            errors.append("Codex drift digest changed from the approved execution-base inventory")
        try:
            actual_codex_inventory = git_inventory(
                root,
                str(codex.get("historical_plan_base")),
                str(codex.get("execution_base")),
            )
        except ContractError as exc:
            errors.append(f"Codex drift inventory could not be reproduced: {exc}")
        else:
            if actual_codex_inventory != normalize_inventory(codex_rows):
                errors.append("Codex drift rows do not match the recorded Git refs")
        _validate_codex_rows(codex_rows, stage, errors)
        if not active_contract and isinstance(codex.get("execution_base"), str):
            approved_evidence_base = codex["execution_base"]

    if isinstance(authority, dict) and isinstance(authority.get("capability_snapshot"), dict):
        capability_entry = authority["capability_snapshot"]
        try:
            snapshot_path_value = validate_repo_path(
                str(capability_entry.get("path", ""))
            )
            if not current_contract:
                snapshot_content = _historical_file_by_sha256(
                    root,
                    snapshot_path_value,
                    str(capability_entry.get("sha256", "")),
                )
                snapshot = json.loads(snapshot_content)
            else:
                snapshot_path = contained_file(root, snapshot_path_value)
                snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except (ContractError, OSError, json.JSONDecodeError):
            snapshot = None
        staged_topology = (
            isinstance(source, dict)
            and "topology" in source
            and not current_contract
        )
        if (
            isinstance(snapshot, dict)
            and isinstance(source, dict)
            and isinstance(codex, dict)
            and not staged_topology
        ):
            # A staged divergent refresh pins source authority in its topology while the next
            # unit re-baselines the capability snapshot. Once promoted into CURRENT_PORT_IDS,
            # exact snapshot-to-manifest reference binding applies again.
            snapshot_refs = snapshot.get("refs", {})
            snapshot_codex = snapshot_refs.get("codex", {})
            snapshot_claude = snapshot_refs.get("claude", {})
            ref_pairs = (
                (snapshot_codex.get("historical_plan_base"), codex.get("historical_plan_base"), "Codex historical plan base"),
                (snapshot_codex.get("execution_base"), codex.get("execution_base"), "Codex execution base"),
                (snapshot_claude.get("source_base"), source.get("base_ref"), "Claude source base"),
                (snapshot_claude.get("source_target"), source.get("target_ref"), "Claude source target"),
            )
            for snapshot_value, manifest_value, label in ref_pairs:
                if snapshot_value != manifest_value:
                    errors.append(f"capability snapshot {label} does not match the port contract")

    policies = manifest.get("version_policy")
    policy_keys = {"source_plugin", "source_version", "current_codex_identity", "current_codex_version", "target_codex_identity", "target_codex_version", "policy", "release_unit"}
    if not isinstance(policies, list) or not policies:
        errors.append("version_policy must be a non-empty list")
    else:
        for index, policy in enumerate(policies):
            if isinstance(policy, dict):
                _exact_keys(policy, policy_keys, f"version_policy[{index}]", errors)
            else:
                errors.append(f"version_policy[{index}] must be an object")

    evidence_entries = manifest.get("evidence")
    evidence_ids: set[str] = set()
    evidence_by_id: dict[str, dict[str, Any]] = {}
    evidence_keys = {"evidence_id", "unit", "kind", "artifact_path", "artifact_sha256", "argv", "cwd", "exit_code", "recorded_at", "repo_head"}
    evidence_optional_keys = {"target_paths", "target_tree_sha256"}
    if not isinstance(evidence_entries, list):
        errors.append("evidence must be a list")
        evidence_entries = []
    for index, entry in enumerate(evidence_entries):
        label = f"evidence[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        actual_keys = set(entry)
        missing_keys = evidence_keys - actual_keys
        unexpected_keys = actual_keys - evidence_keys - evidence_optional_keys
        if missing_keys or unexpected_keys:
            errors.append(
                f"{label} keys mismatch: missing={sorted(missing_keys)} "
                f"unexpected={sorted(unexpected_keys)}"
            )
        evidence_id = entry.get("evidence_id")
        if not isinstance(evidence_id, str) or evidence_id in evidence_ids:
            errors.append(f"{label}.evidence_id must be unique")
        else:
            evidence_ids.add(evidence_id)
            evidence_by_id[evidence_id] = entry
        if entry.get("unit") not in UNIT_IDS or entry.get("kind") not in EVIDENCE_KINDS:
            errors.append(f"{label} has an invalid unit or kind")
        try:
            artifact_path = validate_repo_path(entry.get("artifact_path"))
        except (ContractError, TypeError) as exc:
            errors.append(f"{label}.artifact_path: {exc}")
            continue
        try:
            artifact = contained_file(root, artifact_path)
        except ContractError as exc:
            errors.append(f"{label} artifact is missing or unsafe: {exc}")
        else:
            _check_digest(entry.get("artifact_sha256"), f"{label}.artifact_sha256", errors)
            if entry.get("artifact_sha256") != sha256_file(artifact):
                errors.append(f"{label} artifact digest is stale")
        _validate_evidence_argv(entry.get("argv"), f"{label}.argv", errors)
        if entry.get("cwd") != ".":
            errors.append(f"{label}.cwd must be `.`")
        exit_code = entry.get("exit_code")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool) or exit_code != 0:
            errors.append(f"{label}.exit_code must be integer 0")
        if not _valid_recorded_at(entry.get("recorded_at")):
            errors.append(f"{label}.recorded_at must be a timezone-aware ISO timestamp")
        _check_commit(entry.get("repo_head"), f"{label}.repo_head", errors)
        repo_head = entry.get("repo_head")
        if isinstance(repo_head, str) and HEX40_RE.fullmatch(repo_head):
            try:
                resolved_evidence_head = resolve_ref(root, repo_head)
            except ContractError as exc:
                errors.append(f"{label}.repo_head is not present in this repository: {exc}")
            else:
                if resolved_evidence_head != repo_head or not is_ancestor(
                    root, approved_evidence_base, repo_head
                ):
                    errors.append(f"{label}.repo_head is outside the approved execution history")
                if codex_evidence_head is not None and not is_ancestor(
                    root, repo_head, codex_evidence_head
                ):
                    errors.append(f"{label}.repo_head is not retained by codex.evidence_ref")
                target_paths = entry.get("target_paths")
                target_tree_sha256 = entry.get("target_tree_sha256")
                if (target_paths is None) != (target_tree_sha256 is None):
                    errors.append(
                        f"{label}.target_paths and target_tree_sha256 must be supplied together"
                    )
                elif target_paths is not None:
                    if not isinstance(target_paths, list) or not all(
                        isinstance(path, str) for path in target_paths
                    ):
                        errors.append(f"{label}.target_paths must be a list of repository paths")
                    else:
                        _check_digest(target_tree_sha256, f"{label}.target_tree_sha256", errors)
                        try:
                            reviewed_digest = git_tree_digest(root, repo_head, target_paths)
                            current_digest = git_tree_digest(root, "HEAD", target_paths)
                            unstaged = _run_git(root, ["diff", "--name-only", "--", *target_paths])
                            staged = _run_git(
                                root, ["diff", "--cached", "--name-only", "--", *target_paths]
                            )
                        except ContractError as exc:
                            errors.append(f"{label}.target_paths: {exc}")
                        else:
                            if reviewed_digest != target_tree_sha256:
                                errors.append(f"{label}.target_tree_sha256 is stale")
                            if current_digest != reviewed_digest or unstaged or staged:
                                errors.append(f"{label} reviewed target tree differs from current source")

    references: list[tuple[str, list[str], str]] = []
    for row in source_rows:
        references.extend(
            (row.get("row_id", "source"), row.get("units", []), ref)
            for ref in row.get("evidence_refs", [])
        )
    for row in codex_rows:
        references.extend(
            (row.get("row_id", "codex"), row.get("units", []), ref)
            for ref in row.get("evidence_refs", [])
        )
    for owner, owner_units, reference in references:
        if reference not in evidence_ids:
            errors.append(f"{owner} references unknown evidence `{reference}`")
        elif evidence_by_id[reference].get("unit") not in owner_units:
            errors.append(f"{owner} references evidence `{reference}` from an unrelated unit")
    if current_contract:
        for row in source_rows:
            if row.get("state") not in {"implemented", "verified"}:
                continue
            for artifact_path in [*row.get("planned_targets", []), *row.get("planned_tests", [])]:
                try:
                    contained_file(root, artifact_path)
                except ContractError as exc:
                    errors.append(f"{row.get('row_id')} advanced without a real artifact: {exc}")

    refresh_changes = manifest.get("refresh_changes")
    if not isinstance(refresh_changes, list):
        errors.append("refresh_changes must be a list")
    elif refresh_changes:
        errors.append("refresh_changes must be empty before classification can pass")

    if stage == "unit" and unit:
        claimed_source_rows = [
            row
            for row in source_rows
            if unit in row.get("units", [])
        ]
        if not claimed_source_rows:
            errors.append(f"unit-stage validation for {unit} is vacuous: no source rows claim that unit")
        for row in source_rows:
            if unit not in row.get("units", []) or row.get("treatment") in {"defer", "reject"}:
                continue
            if row.get("state") != "verified":
                errors.append(f"{row.get('row_id')} is claimed by {unit} but is not verified")
            if current_contract:
                for path in [*row.get("planned_targets", []), *row.get("planned_tests", [])]:
                    try:
                        contained_file(root, path)
                    except ContractError:
                        errors.append(f"{row.get('row_id')} planned artifact is missing or unsafe: {path}")
            matching_evidence = [
                reference
                for reference in row.get("evidence_refs", [])
                if evidence_by_id.get(reference, {}).get("unit") == unit
            ]
            if not matching_evidence:
                errors.append(f"{row.get('row_id')} has no {unit} evidence")
        for row in codex_rows:
            if unit not in row.get("units", []):
                continue
            if row.get("state") != "verified":
                errors.append(f"{row.get('row_id')} Codex invariant is not verified for {unit}")
            matching_evidence = [
                reference
                for reference in row.get("evidence_refs", [])
                if evidence_by_id.get(reference, {}).get("unit") == unit
            ]
            if not matching_evidence:
                errors.append(f"{row.get('row_id')} Codex invariant has no {unit} evidence")

    release = manifest.get("release_evidence")
    release_keys = {"review", "isolated_install", "fresh_session", "rollback", "cutover"}
    if not isinstance(release, dict):
        errors.append("release_evidence must be an object")
    else:
        _exact_keys(release, release_keys, "release_evidence", errors)
        for key, value in release.items():
            if value is not None and value not in evidence_ids:
                errors.append(f"release_evidence.{key} references unknown evidence `{value}`")
        expected_release_kinds = {
            "review": "review",
            "isolated_install": "isolated-install",
            "fresh_session": "fresh-session",
            "rollback": "rollback",
            "cutover": "cutover",
        }
        for key, expected_kind in expected_release_kinds.items():
            reference = release.get(key)
            if reference in evidence_by_id:
                if evidence_by_id[reference].get("kind") != expected_kind:
                    errors.append(
                        f"release_evidence.{key} must reference `{expected_kind}` evidence"
                    )
                if evidence_by_id[reference].get("unit") != "U8":
                    errors.append(f"release_evidence.{key} must reference U8 release evidence")
        if stage == "cutover" and any(release.get(key) is None for key in release_keys):
            errors.append("cutover requires review, isolated-install, fresh-session, rollback, and cutover evidence")

    if stage == "cutover":
        for row in source_rows:
            if row.get("treatment") in {"direct-port", "codex-adapt"} and row.get("state") != "verified":
                errors.append(f"{row.get('row_id')} is not verified for cutover")
        for row in codex_rows:
            if row.get("state") != "verified":
                errors.append(f"{row.get('row_id')} Codex invariant is not verified for cutover")
        if not errors:
            errors.extend(_validate_cutover_release_proof(root, manifest))

    if isinstance(authority, dict) and isinstance(authority.get("classification_path"), str):
        try:
            expected_render = render_manifest(manifest)
            render_path = root / authority["classification_path"]
            if not render_path.is_file() or render_path.read_text(encoding="utf-8") != expected_render:
                errors.append("generated classification is missing or stale")
        except (KeyError, TypeError, ContractError) as exc:
            errors.append(f"generated classification could not be rendered: {exc}")
    return errors


def _validate_cutover_release_proof(
    root: Path, manifest: Mapping[str, Any]
) -> list[str]:
    """Require the canonical evidence tag to retain the exact proof and preimages."""
    codex = manifest.get("codex")
    release = manifest.get("release_evidence")
    evidence = manifest.get("evidence")
    if not isinstance(codex, Mapping) or not isinstance(release, Mapping) or not isinstance(
        evidence, list
    ):
        return ["cutover release proof inputs are unavailable"]
    evidence_ref = codex.get("evidence_ref")
    cutover_id = release.get("cutover")
    cutover = next(
        (
            row
            for row in evidence
            if isinstance(row, Mapping) and row.get("evidence_id") == cutover_id
        ),
        None,
    )
    if (
        not isinstance(evidence_ref, str)
        or not evidence_ref.startswith("refs/tags/")
        or not isinstance(cutover, Mapping)
        or not isinstance(cutover.get("artifact_path"), str)
    ):
        return ["cutover requires a tagged release-proof artifact"]
    verifier = root / "plugins/saga/scripts/external_action_release_matrix.py"
    proof = root / str(cutover["artifact_path"])
    if not verifier.is_file() or not proof.is_file():
        return ["cutover release-proof verifier or artifact is missing"]
    process = subprocess.run(
        [
            sys.executable,
            str(verifier),
            "--repo-root",
            str(root),
            "--verify",
            "--output",
            str(proof),
            "--expected-ref",
            evidence_ref,
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode:
        detail = process.stderr.strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        return [f"cutover release proof is not retained by the evidence tag{suffix}"]
    return []


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"manifest is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"manifest is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError("manifest root must be an object")
    return value


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def write_json(path: Path, value: Any) -> None:
    write_atomic(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def render_manifest(manifest: Mapping[str, Any]) -> str:
    source = manifest["source"]
    codex = manifest["codex"]
    topology = source.get("topology")
    range_label = "Source range" if isinstance(topology, Mapping) else "Claude range"
    lines = [
        f"# Port Classification: {manifest['port_id']}",
        "",
        "This file is generated by `scripts/port_contract.py render`. Edit the JSON manifest, not this file.",
        "",
        "## Frozen Contract",
        "",
        f"- Port: `{manifest['port_id']}`",
        f"- {range_label}: `{source['base_ref']}..{source['target_ref']}`",
    ]
    if isinstance(topology, Mapping):
        lines.extend(
            [
                f"- Source left tag: `{topology['left']['tag']}` peeled to "
                f"`{topology['left']['peeled_commit']}`",
                f"- Source right tag: `{topology['right']['tag']}` peeled to "
                f"`{topology['right']['peeled_commit']}`",
                f"- Source common base: `{topology['common_base']}`",
            ]
        )
        for row in topology["left_only_commits"]:
            lines.append(
                f"- Source left-only commit: `{row['commit']}` — {row['disposition']}"
            )
    lines.extend(
        [
            f"- Claude focused rows: **{len(source['rows'])}** (`{source['inventory_sha256']}`)",
            f"- Codex execution preservation: `{codex['historical_plan_base']}..{codex['execution_base']}`",
            f"- Codex evidence retention: `{codex['evidence_ref']}`",
            f"- Codex drift rows: **{len(codex['rows'])}** (`{codex['inventory_sha256']}`)",
            f"- Runbook: `{manifest['authority']['runbook']['path']}` v{manifest['authority']['runbook']['version']} (`{manifest['authority']['runbook']['sha256']}`)",
            f"- Capability snapshot: `{manifest['authority']['capability_snapshot']['path']}` (`{manifest['authority']['capability_snapshot']['sha256']}`)",
            f"- Capability schema: `{manifest['authority']['capability_snapshot']['schema_path']}` (`{manifest['authority']['capability_snapshot']['schema_sha256']}`)",
            "",
            "## Source Rows",
            "",
            "| ID | Change | Source path | Surface | Treatment | State | Unit |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in source["rows"]:
        path = row.get("new_path") or row.get("old_path") or ""
        lines.append(
            f"| `{row['row_id']}` | `{row['change']}` | `{path}` | `{row['surface_kind']}` | "
            f"`{row.get('treatment') or 'unclassified'}` | `{row['state']}` | `{', '.join(row['units']) or '-'}` |"
        )
    lines.extend(
        [
            "",
            "## Codex Preservation Rows",
            "",
            "| ID | Change | Codex path | Treatment | State | Unit | Invariant |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in codex["rows"]:
        path = row.get("new_path") or row.get("old_path") or ""
        invariant = str(row.get("invariant") or "unclassified").replace("|", "\\|")
        lines.append(
            f"| `{row['row_id']}` | `{row['change']}` | `{path}` | `{row.get('treatment') or 'unclassified'}` | "
            f"`{row['state']}` | `{', '.join(row['units']) or '-'}` | {invariant} |"
        )
    lines.extend(["", "## Version Policy", "", "| Source | Current Codex | Target Codex | Policy |", "|---|---|---|---|"])
    for policy in manifest["version_policy"]:
        lines.append(
            f"| `{policy['source_plugin']} {policy['source_version']}` | "
            f"`{policy['current_codex_identity']} {policy['current_codex_version']}` | "
            f"`{policy['target_codex_identity']} {policy['target_codex_version']}` | `{policy['policy']}` |"
        )
    lines.append("")
    return "\n".join(lines)


def refresh_manifest(root: Path, source_repo: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    source = manifest["source"]
    codex = manifest["codex"]
    new_source = git_inventory(source_repo, source["base_ref"], source["target_ref"], source["pathspecs"])
    new_codex = git_inventory(root, codex["historical_plan_base"], codex["execution_base"])

    changes: list[dict[str, Any]] = []
    for label, current_rows, new_rows in (
        ("source", source["rows"], new_source),
        ("codex", codex["rows"], new_codex),
    ):
        current_by_id = {
            row_id("src" if label == "source" else "codex", row): row
            for row in current_rows
        }
        new_ids = {row_id("src" if label == "source" else "codex", row) for row in new_rows}
        for identifier in sorted(set(current_by_id) - new_ids):
            changes.append({"inventory": label, "kind": "removed", "row_id": identifier})
        for row in new_rows:
            identifier = row_id("src" if label == "source" else "codex", row)
            if identifier not in current_by_id:
                changes.append({"inventory": label, "kind": "added", "row_id": identifier})
    manifest["refresh_changes"] = changes
    source["observed_refs"] = {
        "head": resolve_ref(source_repo, "HEAD"),
        "local_main": optional_ref(source_repo, "main"),
        "origin_main": optional_ref(source_repo, "origin/main"),
    }
    source["target_reachable"] = is_ancestor(source_repo, source["target_ref"], source["observed_refs"]["head"])
    codex["observed_origin_main"] = optional_ref(root, "origin/main")
    return manifest


def verify_source(source_repo: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    source = manifest["source"]
    base = resolve_ref(source_repo, source["base_ref"])
    target = resolve_ref(source_repo, source["target_ref"])
    topology_observation: dict[str, Any] | None = None
    if "topology" in source:
        topology = _normalize_source_topology(source["topology"])
        if base != topology["common_base"]:
            raise ContractError("source base does not match the topology common base")
        if target != topology["right"]["peeled_commit"]:
            raise ContractError("source target does not match the topology right peeled commit")
        topology_observation = _verify_source_topology(source_repo, topology)
    if not is_ancestor(source_repo, base, target):
        raise ContractError("source base is not an ancestor of target")
    inventory = git_inventory(source_repo, base, target, source["pathspecs"])
    expected_inventory = normalize_inventory(source["rows"])
    if inventory != expected_inventory:
        raise ContractError("frozen source inventory does not match the manifest")
    digest = inventory_digest(inventory)
    if digest != source["inventory_sha256"]:
        raise ContractError("frozen source inventory digest does not match the manifest")
    head = resolve_ref(source_repo, "HEAD")
    result = {
        "verified": True,
        "base_ref": base,
        "target_ref": target,
        "row_count": len(inventory),
        "inventory_sha256": digest,
        "observed_head": head,
        "target_reachable_from_head": is_ancestor(source_repo, target, head),
        "upstream_ahead_is_drift_only": head != target,
    }
    if topology_observation is not None:
        result["topology"] = topology_observation
    return result


def _resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _manifest_path(root: Path, value: str | Path) -> Path:
    path = _resolve_path(root, value)
    if not path.resolve(strict=False).is_relative_to(root.resolve()):
        raise ContractError(f"manifest/output path escapes the repository: {path}")
    return path


def _source_topology_from_args(args: argparse.Namespace) -> dict[str, Any] | None:
    values = {
        "left_tag": getattr(args, "source_left_tag", None),
        "left_peeled_commit": getattr(args, "source_left_peeled_commit", None),
        "right_tag": getattr(args, "source_right_tag", None),
        "right_peeled_commit": getattr(args, "source_right_peeled_commit", None),
        "common_base": getattr(args, "source_common_base", None),
    }
    left_only_values = getattr(args, "source_left_only_commit", None)
    if not any(value is not None for value in values.values()) and left_only_values is None:
        return None
    missing = [name for name, value in values.items() if value is None]
    if missing:
        raise ContractError(
            f"source topology arguments are incomplete: missing {', '.join(sorted(missing))}"
        )
    left_only_commits: list[dict[str, str]] = []
    for raw_value in left_only_values or []:
        commit, separator, disposition = raw_value.partition("=")
        if not separator or not disposition.strip():
            raise ContractError(
                "--source-left-only-commit must use COMMIT=DISPOSITION"
            )
        left_only_commits.append(
            {"commit": commit, "disposition": disposition.strip()}
        )
    return _normalize_source_topology(
        {
            "left": {
                "tag": values["left_tag"],
                "peeled_commit": values["left_peeled_commit"],
            },
            "right": {
                "tag": values["right_tag"],
                "peeled_commit": values["right_peeled_commit"],
            },
            "common_base": values["common_base"],
            "left_only_commits": left_only_commits,
        }
    )


def command_init(args: argparse.Namespace) -> int:
    root = _repo_root()
    manifest_path = _manifest_path(root, args.manifest)
    if manifest_path.exists():
        raise ContractError(f"init refuses to overwrite existing manifest: {manifest_path.relative_to(root)}")
    source_repo = Path(args.source_repo).expanduser().resolve()
    execution_base = args.codex_execution_base or resolve_ref(root, "HEAD")
    version_policy = None
    if args.version_policy:
        raw_policy = json.loads(_manifest_path(root, args.version_policy).read_text(encoding="utf-8"))
        if not isinstance(raw_policy, list) or not all(isinstance(row, dict) for row in raw_policy):
            raise ContractError("--version-policy must contain a JSON array of objects")
        version_policy = raw_policy
    manifest = build_manifest(
        root,
        source_repo,
        source_base=args.source_base,
        source_target=args.source_target,
        source_pathspecs=args.source_pathspec or DEFAULT_SOURCE_PATHS,
        codex_plan_base=args.codex_plan_base,
        codex_execution_base=execution_base,
        runbook=Path(args.runbook),
        capability_snapshot=Path(args.capability_snapshot),
        capability_schema=Path(args.capability_schema),
        plan=Path(args.plan),
        reviews=[Path(path) for path in (args.review or [str(path) for path in DEFAULT_REVIEWS])],
        classification_path=Path(args.classification_path),
        port_id=args.port_id,
        source_repository_id=args.source_repository_id,
        codex_repository_id=args.codex_repository_id,
        codex_evidence_ref=args.codex_evidence_ref,
        version_policy=version_policy,
        source_topology=_source_topology_from_args(args),
    )
    write_json(manifest_path, manifest)
    print(f"initialized {manifest_path.relative_to(root)} with {len(manifest['source']['rows'])} source rows and {len(manifest['codex']['rows'])} Codex rows")
    return 0


def command_refresh(args: argparse.Namespace) -> int:
    root = _repo_root()
    manifest_path = _manifest_path(root, args.manifest)
    actual_digest = sha256_file(manifest_path)
    if actual_digest != args.expect_digest:
        raise ContractError(f"refresh digest mismatch: expected {args.expect_digest}, found {actual_digest}")
    manifest = refresh_manifest(root, Path(args.source_repo).expanduser().resolve(), load_manifest(manifest_path))
    encoded = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    if args.check:
        if encoded != manifest_path.read_bytes():
            raise ContractError("refresh would change the manifest")
    else:
        write_atomic(manifest_path, encoded)
    print(json.dumps({"refresh_changes": manifest["refresh_changes"]}, sort_keys=True))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    root = _repo_root()
    manifest_path = _manifest_path(root, args.manifest)
    errors = validate_manifest(root, load_manifest(manifest_path), stage=args.stage, unit=args.unit)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"port contract valid at `{args.stage}` stage")
    return 0


def command_verify_source(args: argparse.Namespace) -> int:
    root = _repo_root()
    result = verify_source(
        Path(args.source_repo).expanduser().resolve(),
        load_manifest(_manifest_path(root, args.manifest)),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def command_render(args: argparse.Namespace) -> int:
    root = _repo_root()
    manifest = load_manifest(_manifest_path(root, args.manifest))
    authority = manifest.get("authority", {})
    render_path = _manifest_path(root, authority.get("classification_path", args.output))
    rendered = render_manifest(manifest).encode()
    if args.check:
        if not render_path.is_file() or render_path.read_bytes() != rendered:
            raise ContractError(f"generated classification is stale: {render_path.relative_to(root)}")
    else:
        write_atomic(render_path, rendered)
    print(f"classification {'current' if args.check else 'rendered'}: {render_path.relative_to(root)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="initialize an unclassified contract")
    init.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    init.add_argument("--port-id", default=ACTIVE_PORT_ID)
    init.add_argument("--source-repo", required=True)
    init.add_argument("--source-repository-id", default="infiquetra/infiquetra-claude-plugins")
    init.add_argument("--source-base", default=DEFAULT_SOURCE_BASE)
    init.add_argument("--source-target", default=DEFAULT_SOURCE_TARGET)
    init.add_argument("--source-pathspec", action="append")
    init.add_argument("--source-left-tag")
    init.add_argument("--source-left-peeled-commit")
    init.add_argument("--source-right-tag")
    init.add_argument("--source-right-peeled-commit")
    init.add_argument("--source-common-base")
    init.add_argument(
        "--source-left-only-commit",
        action="append",
        metavar="COMMIT=DISPOSITION",
    )
    init.add_argument("--codex-plan-base", default=DEFAULT_CODEX_PLAN_BASE)
    init.add_argument("--codex-execution-base")
    init.add_argument("--runbook", default=str(DEFAULT_RUNBOOK))
    init.add_argument("--capability-snapshot", default=str(DEFAULT_CAPABILITY))
    init.add_argument("--capability-schema", default=str(DEFAULT_CAPABILITY_SCHEMA))
    init.add_argument("--codex-repository-id", default="infiquetra/infiquetra-codex-plugins")
    init.add_argument("--codex-evidence-ref", default=CODEX_EVIDENCE_REF)
    init.add_argument("--version-policy", help="repo-relative JSON array overriding version policy")
    init.add_argument("--plan", default=str(DEFAULT_PLAN))
    init.add_argument("--review", action="append")
    init.add_argument("--classification-path", default=str(DEFAULT_RENDER))
    init.set_defaults(func=command_init)

    refresh = subparsers.add_parser("refresh", help="refresh observations without moving frozen refs")
    refresh.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    refresh.add_argument("--source-repo", required=True)
    refresh.add_argument("--expect-digest", required=True)
    refresh.add_argument("--check", action="store_true")
    refresh.set_defaults(func=command_refresh)

    validate = subparsers.add_parser("validate", help="validate a staged contract")
    validate.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    validate.add_argument("--stage", choices=sorted(VALID_STAGES), required=True)
    validate.add_argument("--unit")
    validate.set_defaults(func=command_validate)

    verify = subparsers.add_parser("verify-source", help="verify the frozen source from a local checkout")
    verify.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    verify.add_argument("--source-repo", required=True)
    verify.set_defaults(func=command_verify_source)

    render = subparsers.add_parser("render", help="render the human classification")
    render.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    render.add_argument("--output", default=str(DEFAULT_RENDER))
    render.add_argument("--check", action="store_true")
    render.set_defaults(func=command_render)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except (ContractError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
