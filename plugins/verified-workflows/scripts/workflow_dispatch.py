#!/usr/bin/env python3
"""Compile an approved Workflow Contract into root-owned Codex V2 launch specs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

import render_codex_agents as renderer


MAX_PLAN_BYTES = 2 * 1024 * 1024
ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
CONTEXT_RE = re.compile(r"^turns:([1-9][0-9]*)$")
FRESH_ROOT_RE = re.compile(r"^fresh-root:([a-z][a-z0-9-]{0,63})$")
FALLBACK_RE = re.compile(
    r"^(review_max|review_high|work_high|test_medium|scan_low|monitor_low)@([a-z0-9][a-z0-9-]{0,63})$"
)
ROOT_ROLE_RE = re.compile(r"^root(?: [a-z][a-z -]*)?$")
ROOT_EFFORTS = frozenset({"low", "medium", "high", "xhigh", "max", "ultra"})
GIT_WORD_RE = re.compile(r"(?:^|\s)(?:git|gh)\s+(?:add|commit|merge|push|tag|checkout|switch|reset|rebase)(?:\s|$)", re.I)

ASSIGNMENT_HEADERS = (
    "id",
    "depends",
    "parent",
    "role",
    "profile",
    "model",
    "effort",
    "context",
    "writes",
    "completion",
    "fallback",
)
CHECK_HEADERS = (
    "id",
    "owner",
    "after",
    "command-or-proof",
    "blocking",
    "failure",
)
EXTERNAL_ACTION_HEADERS = (
    "id",
    "purpose",
    "provider",
    "model",
    "egress",
    "context",
    "sensitivity",
    "cost",
    "writes-or-artifact",
    "requiredness",
    "authority",
)


class WorkflowDispatchError(ValueError):
    """Raised when a Workflow Contract cannot be compiled safely."""


@dataclass(frozen=True, slots=True)
class Fallback:
    profile: str
    condition: str


@dataclass(frozen=True, slots=True)
class Assignment:
    assignment_id: str
    depends: tuple[str, ...]
    parent: str
    role: str
    profile: str
    model: str
    effort: str
    context: str
    writes: tuple[str, ...]
    completion: str
    fallback: tuple[Fallback, ...]
    category: str
    result_schema: str

    @property
    def is_root(self) -> bool:
        return self.profile == "root"

    @property
    def is_independent_review(self) -> bool:
        return self.category == "reviewer" and self.parent == f"fresh-root:{self.assignment_id}"


@dataclass(frozen=True, slots=True)
class BlockingCheck:
    check_id: str
    owner: str
    after: tuple[str, ...]
    command_or_proof: str
    blocking: bool
    failure: str


@dataclass(frozen=True, slots=True)
class ExternalAction:
    action_id: str
    purpose: str
    provider: str
    model: str
    egress: tuple[str, ...]
    context: tuple[str, ...]
    sensitivity: str
    cost: str
    writes_or_artifact: tuple[str, ...]
    requiredness: str
    authority: str


@dataclass(frozen=True, slots=True)
class LaunchSpec:
    assignment_id: str
    depends: tuple[str, ...]
    parent: str
    role: str
    agent_type: str | None
    model: str
    reasoning_effort: str
    fork_turns: str | int | None
    writes: tuple[str, ...]
    completion: str
    fallback: tuple[Fallback, ...]
    result_schema: str


@dataclass(frozen=True, slots=True)
class WorkflowContract:
    schema_version: int
    plan_revision: str
    contract_sha256: str
    approval_binding_sha256: str
    assignments: tuple[Assignment, ...]
    checks: tuple[BlockingCheck, ...]
    external_actions: tuple[ExternalAction, ...]
    launch_specs: tuple[LaunchSpec, ...]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha256(payload: object) -> str:
    return _sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())


def _read_bounded(path: Path, limit: int = MAX_PLAN_BYTES, where: str = "workflow plan") -> bytes:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise WorkflowDispatchError(f"{where} is unreadable: {exc}") from exc
    if size > limit:
        raise WorkflowDispatchError(f"{where} exceeds the {limit}-byte ceiling")
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise WorkflowDispatchError(f"{where} is unreadable: {exc}") from exc
    if len(content) != size:
        raise WorkflowDispatchError(f"{where} changed while it was read")
    return content


def _clean_cell(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == "`":
        return value[1:-1].strip()
    return value


def _split_table_row(line: str) -> tuple[str, ...]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        raise WorkflowDispatchError("workflow tables must use leading and trailing pipes")
    return tuple(_clean_cell(cell) for cell in stripped[1:-1].split("|"))


def _heading_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"(?m)^###? {re.escape(heading)}\s*$")
    match = pattern.search(text)
    if match is None:
        raise WorkflowDispatchError(f"missing {heading!r} heading")
    start = match.end()
    next_heading = re.search(r"(?m)^#{1,3} \S", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def _first_table(section: str, headers: Sequence[str], where: str) -> list[dict[str, str]]:
    lines = section.splitlines()
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        actual_headers = _split_table_row(line)
        if actual_headers != tuple(headers):
            raise WorkflowDispatchError(
                f"{where} columns must be exactly {list(headers)}; got {list(actual_headers)}"
            )
        if index + 1 >= len(lines):
            raise WorkflowDispatchError(f"{where} table is missing its separator row")
        separator = _split_table_row(lines[index + 1])
        if len(separator) != len(headers) or any(
            re.fullmatch(r":?-{3,}:?", cell) is None for cell in separator
        ):
            raise WorkflowDispatchError(f"{where} table has an invalid separator row")
        rows: list[dict[str, str]] = []
        for row_line in lines[index + 2 :]:
            if not row_line.strip().startswith("|"):
                break
            cells = _split_table_row(row_line)
            if len(cells) != len(headers):
                raise WorkflowDispatchError(
                    f"{where} row has {len(cells)} cells; expected {len(headers)}"
                )
            rows.append(dict(zip(headers, cells, strict=True)))
        if not rows:
            raise WorkflowDispatchError(f"{where} table must contain at least one row")
        return rows
    raise WorkflowDispatchError(f"{where} table is missing")


def _list_cell(value: str, where: str, *, ordered: bool = False) -> tuple[str, ...]:
    if value in {"", "-", "none"}:
        return ()
    values = tuple(item.strip() for item in value.split(","))
    if any(not item for item in values):
        raise WorkflowDispatchError(f"{where} contains an empty item")
    if len(values) != len(set(values)):
        raise WorkflowDispatchError(f"{where} contains duplicate items")
    return values if ordered else tuple(sorted(values))


def _identifier(value: str, where: str) -> str:
    if ID_RE.fullmatch(value) is None:
        raise WorkflowDispatchError(f"{where} must match {ID_RE.pattern!r}; got {value!r}")
    return value


def _repo_path(value: str, where: str) -> str:
    if "\\" in value or value.startswith("/"):
        raise WorkflowDispatchError(f"{where} must be a canonical repository-relative path")
    path = PurePosixPath(value)
    if value in {"", ".", ".."} or any(part in {"", ".", ".."} for part in path.parts):
        raise WorkflowDispatchError(f"{where} must be a canonical repository-relative path")
    if ".git" in path.parts:
        raise WorkflowDispatchError(f"{where} may not target Git metadata")
    if str(path) != value:
        raise WorkflowDispatchError(f"{where} must be canonical; got {value!r}")
    return value


def _parse_fallbacks(value: str, where: str) -> tuple[Fallback, ...]:
    entries = _list_cell(value, where, ordered=True)
    parsed: list[Fallback] = []
    for entry in entries:
        match = FALLBACK_RE.fullmatch(entry)
        if match is None:
            raise WorkflowDispatchError(
                f"{where} entries must be profile@condition with an underscore profile ID"
            )
        parsed.append(Fallback(profile=match.group(1), condition=match.group(2)))
    return tuple(parsed)


def _parse_context(value: str, where: str, *, root: bool) -> str:
    if root:
        if value != "root":
            raise WorkflowDispatchError(f"{where} must be 'root' for a root assignment")
        return value
    if value == "none" or CONTEXT_RE.fullmatch(value):
        return value
    raise WorkflowDispatchError(f"{where} must be 'none' or turns:<positive-int>")


def _parse_assignment(
    row: Mapping[str, str],
    *,
    registry: renderer.RoleRegistry,
    catalog: Any,
) -> Assignment:
    assignment_id = _identifier(row["id"], "assignment id")
    depends = tuple(
        _identifier(item, f"assignment {assignment_id}.depends")
        for item in _list_cell(row["depends"], f"assignment {assignment_id}.depends")
    )
    parent = row["parent"]
    role = row["role"]
    profile = row["profile"]
    model = row["model"]
    effort = row["effort"]
    completion = row["completion"].strip()
    if not completion:
        raise WorkflowDispatchError(f"assignment {assignment_id}.completion must not be empty")

    is_root = profile == "root"
    if is_root:
        if parent != "root" or ROOT_ROLE_RE.fullmatch(role) is None:
            raise WorkflowDispatchError(
                f"root assignment {assignment_id} must use parent=root and a reserved root role"
            )
        if not model or effort not in ROOT_EFFORTS:
            raise WorkflowDispatchError(f"root assignment {assignment_id} has invalid model or effort")
        context = _parse_context(row["context"], f"assignment {assignment_id}.context", root=True)
        writes = _list_cell(row["writes"], f"assignment {assignment_id}.writes")
        for item in writes:
            if not item.startswith("unit:") and item != "none":
                _repo_path(item, f"assignment {assignment_id}.writes")
        fallback = _parse_fallbacks(row["fallback"], f"assignment {assignment_id}.fallback")
        if fallback:
            raise WorkflowDispatchError(f"root assignment {assignment_id} cannot declare a child fallback")
        return Assignment(
            assignment_id,
            depends,
            parent,
            role,
            profile,
            model,
            effort,
            context,
            writes,
            completion,
            (),
            "root",
            "root-result.v1",
        )

    if profile not in renderer.PROFILE_IDS:
        raise WorkflowDispatchError(
            f"assignment {assignment_id}.profile must be one of {list(renderer.PROFILE_IDS)}"
        )
    try:
        role_resolution = renderer.resolve_role(registry, role, requested_profile=profile)
        profile_resolution = renderer.resolve_profile(profile, catalog)
    except renderer.RoleRegistryError as exc:
        raise WorkflowDispatchError(str(exc)) from exc
    if (model, effort) != (profile_resolution.model, profile_resolution.effort):
        raise WorkflowDispatchError(
            f"assignment {assignment_id} profile {profile} requires "
            f"model={profile_resolution.model} effort={profile_resolution.effort}"
        )
    context = _parse_context(row["context"], f"assignment {assignment_id}.context", root=False)
    writes = tuple(
        _repo_path(item, f"assignment {assignment_id}.writes")
        for item in _list_cell(row["writes"], f"assignment {assignment_id}.writes")
    )
    if profile_resolution.workspace_boundary == "read-only" and writes:
        raise WorkflowDispatchError(f"read-only assignment {assignment_id} cannot declare writes")
    if GIT_WORD_RE.search(completion):
        raise WorkflowDispatchError(f"assignment {assignment_id} may not own a Git mutation")
    fallback = _parse_fallbacks(row["fallback"], f"assignment {assignment_id}.fallback")
    for candidate in fallback:
        if candidate.profile not in role_resolution.role.allowed_profiles:
            raise WorkflowDispatchError(
                f"assignment {assignment_id} fallback {candidate.profile} widens role {role!r}"
            )
        candidate_resolution = renderer.resolve_profile(candidate.profile, catalog)
        if (
            candidate_resolution.workspace_boundary != profile_resolution.workspace_boundary
            or candidate_resolution.external_boundary != profile_resolution.external_boundary
        ):
            raise WorkflowDispatchError(
                f"assignment {assignment_id} fallback {candidate.profile} widens its boundary"
            )
    return Assignment(
        assignment_id,
        depends,
        parent,
        role,
        profile,
        model,
        effort,
        context,
        writes,
        completion,
        fallback,
        role_resolution.role.category,
        role_resolution.role.result_schema,
    )


def _parse_check(row: Mapping[str, str]) -> BlockingCheck:
    check_id = _identifier(row["id"], "check id")
    owner = row["owner"].strip()
    command = row["command-or-proof"].strip()
    failure = row["failure"].strip()
    if not owner or not command or not failure:
        raise WorkflowDispatchError(f"check {check_id} owner, command-or-proof, and failure are required")
    blocking_raw = row["blocking"].casefold()
    if blocking_raw not in {"yes", "no"}:
        raise WorkflowDispatchError(f"check {check_id}.blocking must be yes or no")
    after = tuple(
        _identifier(item, f"check {check_id}.after")
        for item in _list_cell(row["after"], f"check {check_id}.after")
    )
    return BlockingCheck(check_id, owner, after, command, blocking_raw == "yes", failure)


def _parse_external(row: Mapping[str, str]) -> ExternalAction:
    action_id = _identifier(row["id"], "external action id")
    required = {
        key: row[key].strip()
        for key in ("purpose", "provider", "model", "egress", "sensitivity", "cost", "requiredness")
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise WorkflowDispatchError(f"external action {action_id} missing fields {missing}")
    if row["authority"] != "non-gating":
        raise WorkflowDispatchError(f"external action {action_id}.authority must be non-gating")
    if required["requiredness"] not in {"best-effort", "required"}:
        raise WorkflowDispatchError(
            f"external action {action_id}.requiredness must be best-effort or required"
        )
    egress = _list_cell(row["egress"], f"external action {action_id}.egress")
    if not egress:
        raise WorkflowDispatchError(f"external action {action_id}.egress must be explicit")
    context = tuple(
        _repo_path(item, f"external action {action_id}.context")
        for item in _list_cell(row["context"], f"external action {action_id}.context")
    )
    writes_or_artifact = _list_cell(
        row["writes-or-artifact"], f"external action {action_id}.writes-or-artifact"
    )
    if not writes_or_artifact:
        raise WorkflowDispatchError(
            f"external action {action_id}.writes-or-artifact must name an artifact or bounded paths"
        )
    for item in writes_or_artifact:
        if item.startswith("artifact:"):
            continue
        _repo_path(item, f"external action {action_id}.writes-or-artifact")
    return ExternalAction(
        action_id,
        required["purpose"],
        required["provider"],
        required["model"],
        egress,
        context,
        required["sensitivity"],
        required["cost"],
        writes_or_artifact,
        required["requiredness"],
        "non-gating",
    )


def _validate_unique(values: Iterable[str], where: str) -> None:
    items = list(values)
    duplicates = sorted({item for item in items if items.count(item) > 1})
    if duplicates:
        raise WorkflowDispatchError(f"duplicate {where}: {duplicates}")


def _dependency_closure(assignments: Sequence[Assignment]) -> dict[str, set[str]]:
    by_id = {assignment.assignment_id: assignment for assignment in assignments}
    for assignment in assignments:
        unknown = set(assignment.depends) - set(by_id)
        if unknown:
            raise WorkflowDispatchError(
                f"assignment {assignment.assignment_id} has unknown dependencies {sorted(unknown)}"
            )
        if assignment.assignment_id in assignment.depends:
            raise WorkflowDispatchError(f"assignment {assignment.assignment_id} depends on itself")
    visiting: set[str] = set()
    visited: set[str] = set()
    closure: dict[str, set[str]] = {}

    def visit(assignment_id: str) -> set[str]:
        if assignment_id in visiting:
            raise WorkflowDispatchError(f"assignment dependency cycle includes {assignment_id!r}")
        if assignment_id in visited:
            return closure[assignment_id]
        visiting.add(assignment_id)
        ancestors: set[str] = set()
        for dependency in by_id[assignment_id].depends:
            ancestors.add(dependency)
            ancestors.update(visit(dependency))
        visiting.remove(assignment_id)
        visited.add(assignment_id)
        closure[assignment_id] = ancestors
        return ancestors

    for assignment_id in by_id:
        visit(assignment_id)
    return closure


def _paths_overlap(left: str, right: str) -> bool:
    if left.startswith("unit:") or right.startswith("unit:"):
        return left == right
    left_path = PurePosixPath(left)
    right_path = PurePosixPath(right)
    return left_path == right_path or left_path in right_path.parents or right_path in left_path.parents


def _validate_graph(assignments: Sequence[Assignment], checks: Sequence[BlockingCheck]) -> None:
    _validate_unique((assignment.assignment_id for assignment in assignments), "assignment ids")
    _validate_unique((check.check_id for check in checks), "check ids")
    assignment_ids = {assignment.assignment_id for assignment in assignments}
    if assignment_ids & {check.check_id for check in checks}:
        raise WorkflowDispatchError("assignment and check ids share one global namespace")
    closure = _dependency_closure(assignments)

    for assignment in assignments:
        fresh = FRESH_ROOT_RE.fullmatch(assignment.parent)
        if assignment.parent != "root" and assignment.parent not in assignment_ids and fresh is None:
            raise WorkflowDispatchError(
                f"assignment {assignment.assignment_id}.parent is not root, an assignment, or fresh-root:<id>"
            )
        if assignment.parent in assignment_ids and assignment.parent not in closure[assignment.assignment_id]:
            raise WorkflowDispatchError(
                f"assignment {assignment.assignment_id} must depend on its declared parent {assignment.parent}"
            )
        if fresh is not None and (
            fresh.group(1) != assignment.assignment_id
            or assignment.category != "reviewer"
            or assignment.context != "none"
            or assignment.writes
        ):
            raise WorkflowDispatchError(
                f"fresh-root assignment {assignment.assignment_id} must be a same-id, read-only, no-history reviewer"
            )

    writable = [assignment for assignment in assignments if assignment.writes]
    for index, left in enumerate(writable):
        for right in writable[index + 1 :]:
            ordered = (
                left.assignment_id in closure[right.assignment_id]
                or right.assignment_id in closure[left.assignment_id]
            )
            if ordered:
                continue
            overlaps = [
                (left_path, right_path)
                for left_path in left.writes
                for right_path in right.writes
                if _paths_overlap(left_path, right_path)
            ]
            if overlaps:
                raise WorkflowDispatchError(
                    f"concurrent assignments {left.assignment_id} and {right.assignment_id} overlap writes {overlaps}"
                )

    for check in checks:
        unknown = set(check.after) - assignment_ids
        if unknown:
            raise WorkflowDispatchError(f"check {check.check_id} has unknown after assignments {sorted(unknown)}")
    if not any(check.blocking for check in checks):
        raise WorkflowDispatchError("workflow must declare at least one blocking check")
    reviewers = [assignment for assignment in assignments if assignment.category == "reviewer"]
    if not any(assignment.is_independent_review for assignment in reviewers):
        raise WorkflowDispatchError("workflow requires at least one fresh-root independent reviewer")
    if not any(
        check.blocking and "review" in f"{check.check_id} {check.command_or_proof}".casefold()
        for check in checks
    ):
        raise WorkflowDispatchError("workflow requires a blocking reviewer assurance check")


def _canonical_contract_payload(
    assignments: Sequence[Assignment],
    checks: Sequence[BlockingCheck],
    external_actions: Sequence[ExternalAction],
) -> dict[str, Any]:
    def assignment_row(value: Assignment) -> dict[str, Any]:
        row = asdict(value)
        row.pop("category")
        row.pop("result_schema")
        return row

    return {
        "schema_version": 1,
        "assignments": [assignment_row(value) for value in sorted(assignments, key=lambda item: item.assignment_id)],
        "checks": [asdict(value) for value in sorted(checks, key=lambda item: item.check_id)],
        "external_actions": [
            asdict(value) for value in sorted(external_actions, key=lambda item: item.action_id)
        ],
    }


def _launch_spec(assignment: Assignment) -> LaunchSpec:
    if assignment.is_root:
        return LaunchSpec(
            assignment.assignment_id,
            assignment.depends,
            assignment.parent,
            assignment.role,
            None,
            assignment.model,
            assignment.effort,
            None,
            assignment.writes,
            assignment.completion,
            assignment.fallback,
            assignment.result_schema,
        )
    fork_turns: str | int
    if assignment.context == "none":
        fork_turns = "none"
    else:
        match = CONTEXT_RE.fullmatch(assignment.context)
        if match is None:
            raise WorkflowDispatchError(f"assignment {assignment.assignment_id} context is invalid")
        fork_turns = int(match.group(1))
    return LaunchSpec(
        assignment.assignment_id,
        assignment.depends,
        assignment.parent,
        assignment.role,
        assignment.profile,
        assignment.model,
        assignment.effort,
        fork_turns,
        assignment.writes,
        assignment.completion,
        assignment.fallback,
        assignment.result_schema,
    )


def compile_workflow_contract(
    text: str,
    *,
    plan_revision: str,
    registry_path: Path = renderer.DEFAULT_REGISTRY,
    roles_dir: Path = renderer.DEFAULT_ROLES_DIR,
    catalog_snapshot_path: Path = renderer.DEFAULT_CATALOG_SNAPSHOT,
) -> WorkflowContract:
    """Compile and validate one approved three-table workflow contract."""

    if not plan_revision.strip():
        raise WorkflowDispatchError("plan revision must be explicit")
    try:
        registry = renderer.load_role_registry(registry_path, roles_dir)
        catalog = renderer.load_catalog_snapshot(catalog_snapshot_path)
    except renderer.RoleRegistryError as exc:
        raise WorkflowDispatchError(str(exc)) from exc

    contract_section = _heading_section(text, "Workflow Contract")
    assignment_rows = _first_table(
        contract_section, ASSIGNMENT_HEADERS, "workflow assignment"
    )
    check_rows = _first_table(
        _heading_section(text, "Blocking Checks"), CHECK_HEADERS, "blocking check"
    )
    external_section = _heading_section(text, "External Actions")
    if re.search(r"External actions:\s*\[\]", external_section, re.I):
        external_rows: list[dict[str, str]] = []
    else:
        external_rows = _first_table(
            external_section, EXTERNAL_ACTION_HEADERS, "external action"
        )

    assignments = tuple(
        _parse_assignment(row, registry=registry, catalog=catalog) for row in assignment_rows
    )
    checks = tuple(_parse_check(row) for row in check_rows)
    external_actions = tuple(_parse_external(row) for row in external_rows)
    _validate_unique((action.action_id for action in external_actions), "external action ids")
    _validate_graph(assignments, checks)

    canonical = _canonical_contract_payload(assignments, checks, external_actions)
    contract_sha256 = _canonical_sha256(canonical)
    approval_binding_sha256 = _canonical_sha256(
        {"plan_revision": plan_revision, "contract_sha256": contract_sha256}
    )
    return WorkflowContract(
        schema_version=1,
        plan_revision=plan_revision,
        contract_sha256=contract_sha256,
        approval_binding_sha256=approval_binding_sha256,
        assignments=assignments,
        checks=checks,
        external_actions=external_actions,
        launch_specs=tuple(_launch_spec(assignment) for assignment in assignments),
    )


def compile_plan(
    path: Path,
    *,
    plan_revision: str | None = None,
    registry_path: Path = renderer.DEFAULT_REGISTRY,
    roles_dir: Path = renderer.DEFAULT_ROLES_DIR,
    catalog_snapshot_path: Path = renderer.DEFAULT_CATALOG_SNAPSHOT,
) -> WorkflowContract:
    content = _read_bounded(path)
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WorkflowDispatchError("workflow plan is not valid UTF-8") from exc
    revision = plan_revision or _sha256(content)
    return compile_workflow_contract(
        text,
        plan_revision=revision,
        registry_path=registry_path,
        roles_dir=roles_dir,
        catalog_snapshot_path=catalog_snapshot_path,
    )


def validate_approval_binding(
    contract: WorkflowContract,
    *,
    approved_plan_revision: str,
    approved_contract_sha256: str,
    approved_binding_sha256: str,
) -> None:
    expected = (
        approved_plan_revision,
        approved_contract_sha256,
        approved_binding_sha256,
    )
    actual = (
        contract.plan_revision,
        contract.contract_sha256,
        contract.approval_binding_sha256,
    )
    if actual != expected:
        raise WorkflowDispatchError(
            "workflow approval binding is stale; re-preview and approve the material contract revision"
        )


def contract_payload(contract: WorkflowContract) -> dict[str, Any]:
    return asdict(contract)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-revision")
    parser.add_argument("--registry", type=Path, default=renderer.DEFAULT_REGISTRY)
    parser.add_argument("--roles-dir", type=Path, default=renderer.DEFAULT_ROLES_DIR)
    parser.add_argument("--catalog-snapshot", type=Path, default=renderer.DEFAULT_CATALOG_SNAPSHOT)
    parser.add_argument("--approved-plan-revision")
    parser.add_argument("--approved-contract-sha256")
    parser.add_argument("--approved-binding-sha256")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        contract = compile_plan(
            args.plan,
            plan_revision=args.plan_revision,
            registry_path=args.registry,
            roles_dir=args.roles_dir,
            catalog_snapshot_path=args.catalog_snapshot,
        )
        approvals = (
            args.approved_plan_revision,
            args.approved_contract_sha256,
            args.approved_binding_sha256,
        )
        if any(approvals):
            if not all(approvals):
                raise WorkflowDispatchError("all three approved binding fields are required together")
            validate_approval_binding(
                contract,
                approved_plan_revision=args.approved_plan_revision,
                approved_contract_sha256=args.approved_contract_sha256,
                approved_binding_sha256=args.approved_binding_sha256,
            )
    except (OSError, WorkflowDispatchError) as exc:
        print(f"workflow compilation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(contract_payload(contract), indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
