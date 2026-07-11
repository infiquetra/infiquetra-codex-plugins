#!/usr/bin/env python3
"""Parse an approved Workflow Structure and emit root-owned dispatch intents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import render_codex_agents as renderer  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_HEADING = "## Workflow Structure"
HEADERS = (
    "step_id",
    "depends_on",
    "barrier",
    "role_id",
    "role_kind",
    "independence",
    "execution_class",
    "runtime_agent_name",
    "vehicle",
    "mutation",
    "required_evidence",
    "role_lens_sha256",
    "profile_sha256",
    "expected_model",
    "expected_effort",
    "validator_required",
    "validator_disabled",
    "deterministic_contract_sha256",
)
STEP_ID = re.compile(r"^(?=.{1,64}$)[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
EVIDENCE_ID = re.compile(r"^[a-z0-9][a-z0-9._:/-]{0,127}$")
RECEIPT_REF = re.compile(r"^[a-z0-9][a-z0-9._:/-]{0,511}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
VEHICLES = {"auto", "subagent", "inline", "deterministic-tool", "root"}
MUTATIONS = {"none", "declared-write", "root-only"}
STEP_STATUSES = {
    "pending",
    "running",
    "passed",
    "failed",
    "blocked",
    "needs-follow-up",
    "stale",
}
MAX_PLAN_BYTES = 1024 * 1024
MAX_STATE_BYTES = 1024 * 1024
MAX_STEPS = 128
MAX_CYCLES = 3


class WorkflowDispatchError(ValueError):
    """Raised when workflow structure or dispatch state is not closed and executable."""


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    step_id: str
    depends_on: tuple[str, ...]
    barrier: str | None
    role_id: str
    role_kind: str
    independence: str | None
    execution_class: str | None
    runtime_agent_name: str | None
    vehicle: str
    mutation: str
    required_evidence: tuple[str, ...]
    role_lens_sha256: str | None
    profile_sha256: str | None
    expected_model: str | None
    expected_effort: str | None
    validator_required: bool | None
    validator_disabled: bool | None
    expected_profile_sandbox: str | None
    output_schema: str
    command: tuple[str, ...]
    command_implementation_path: str | None
    command_implementation_sha256: str | None
    command_timeout_seconds: int | None
    command_output_limit_bytes: int | None
    evidence_schema_path: str | None
    evidence_schema_sha256: str | None
    deterministic_contract_sha256: str | None

    def to_jsonable(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["depends_on"] = list(self.depends_on)
        payload["required_evidence"] = list(self.required_evidence)
        payload["command"] = list(self.command)
        return payload


@dataclass(frozen=True, slots=True)
class Workflow:
    steps: tuple[WorkflowStep, ...]
    sha256: str

    def step(self, step_id: str) -> WorkflowStep:
        try:
            return next(step for step in self.steps if step.step_id == step_id)
        except StopIteration as exc:
            raise WorkflowDispatchError(f"unknown workflow step {step_id!r}") from exc


@dataclass(frozen=True, slots=True)
class StepState:
    status: str
    cycle: int
    result_ref: str | None
    finding_refs: tuple[str, ...]


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_sha256(payload: object) -> str:
    content = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return _sha256(content)


def _deterministic_contract_sha256(role: renderer.RoleSpec) -> str:
    if role.kind != "deterministic-validator":
        raise WorkflowDispatchError("only deterministic validators have command contracts")
    return _canonical_sha256(
        {
            "command": list(role.command or ()),
            "implementation_path": role.command_implementation_path,
            "implementation_sha256": role.command_implementation_sha256,
            "timeout_seconds": role.command_timeout_seconds,
            "output_limit_bytes": role.command_output_limit_bytes,
            "evidence_schema_path": role.evidence_schema_path,
            "evidence_schema_sha256": role.evidence_schema_sha256,
            "output_schema": role.output_schema,
        }
    )


def _read_bounded(path: Path, limit: int, where: str) -> bytes:
    try:
        return renderer._regular_single_link(path, where, limit)
    except renderer.RoleRegistryError as exc:
        raise WorkflowDispatchError(str(exc)) from exc


def _split_table_row(line: str) -> list[str]:
    if "\\|" in line:
        raise WorkflowDispatchError("Workflow Structure cells must not contain escaped pipes")
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        raise WorkflowDispatchError("Workflow Structure must use a pipe-delimited Markdown table")
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _extract_rows(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    headings = [index for index, line in enumerate(lines) if line.strip() == WORKFLOW_HEADING]
    if len(headings) != 1:
        raise WorkflowDispatchError("plan must contain exactly one `## Workflow Structure` heading")
    section: list[str] = []
    for line in lines[headings[0] + 1 :]:
        if line.startswith("## "):
            break
        if line.strip():
            section.append(line)
    if len(section) < 3:
        raise WorkflowDispatchError("Workflow Structure table is missing or empty")
    header = tuple(_split_table_row(section[0]))
    if header != HEADERS:
        raise WorkflowDispatchError(
            f"Workflow Structure headers must be exactly {list(HEADERS)}"
        )
    separator = _split_table_row(section[1])
    if len(separator) != len(HEADERS) or not all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in separator
    ):
        raise WorkflowDispatchError("Workflow Structure separator row is invalid")
    rows: list[dict[str, str]] = []
    for line in section[2:]:
        cells = _split_table_row(line)
        if len(cells) != len(HEADERS):
            raise WorkflowDispatchError("Workflow Structure row has the wrong column count")
        rows.append(dict(zip(HEADERS, cells, strict=True)))
    if not rows or len(rows) > MAX_STEPS:
        raise WorkflowDispatchError(f"Workflow Structure must contain 1-{MAX_STEPS} steps")
    return rows


def _optional(value: str) -> str | None:
    value = value.strip()
    return None if value in {"", "-"} else value


def _list_cell(value: str, where: str, pattern: re.Pattern[str]) -> tuple[str, ...]:
    raw = _optional(value)
    if raw is None:
        return ()
    values = tuple(item.strip() for item in raw.split(","))
    if any(
        not item
        or not pattern.fullmatch(item)
        or (pattern is EVIDENCE_ID and any(part in {"", ".", ".."} for part in item.split("/")))
        for item in values
    ):
        raise WorkflowDispatchError(f"{where} contains an invalid identifier")
    if len(values) != len(set(values)):
        raise WorkflowDispatchError(f"{where} contains duplicates")
    return values


def _load_profile(execution_class: str, agents_dir: Path) -> dict[str, str]:
    runtime_agent_name = renderer.RUNTIME_AGENT_NAMES[execution_class]
    path = agents_dir / f"{runtime_agent_name}.toml"
    try:
        content = renderer._regular_single_link(
            path, f"profile {execution_class}", 1024 * 1024
        )
    except renderer.RoleRegistryError as exc:
        raise WorkflowDispatchError(str(exc)) from exc
    try:
        payload = tomllib.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise WorkflowDispatchError(f"profile {execution_class} is invalid TOML") from exc
    expected = {
        "name",
        "description",
        "model",
        "model_reasoning_effort",
        "sandbox_mode",
        "developer_instructions",
        "nickname_candidates",
    }
    if set(payload) != expected:
        raise WorkflowDispatchError(f"profile {execution_class} fields are not closed")
    values = {
        "sha256": _sha256(content),
        "model": payload.get("model"),
        "effort": payload.get("model_reasoning_effort"),
        "sandbox": payload.get("sandbox_mode"),
        "runtime_agent_name": payload.get("name"),
    }
    if not all(isinstance(value, str) and value for value in values.values()):
        raise WorkflowDispatchError(f"profile {execution_class} identity fields are invalid")
    if values["runtime_agent_name"] != runtime_agent_name:
        raise WorkflowDispatchError(
            f"profile {execution_class} name does not match its runtime agent"
        )
    if renderer.MANAGED_MARKER not in content.decode("utf-8").splitlines()[:8]:
        raise WorkflowDispatchError(f"profile {execution_class} lacks the managed marker")
    return values


def _require_cell(actual: str | None, raw: str, where: str) -> None:
    expected = _optional(raw)
    if actual != expected:
        raise WorkflowDispatchError(f"{where} must bind {actual!r}, got {expected!r}")


def _validator_policy(
    row: Mapping[str, str], output_schema: str
) -> tuple[bool | None, bool | None]:
    has_gate_status = output_schema in {
        "scanner-evidence.v1",
        "tester-evidence.v1",
        "monitor-evidence.v1",
        "deploy-observation.v1",
    }
    required_raw = row["validator_required"]
    disabled_raw = row["validator_disabled"]
    if not has_gate_status:
        if required_raw != "n/a" or disabled_raw != "n/a":
            raise WorkflowDispatchError(
                "non-validator rows must use validator_required/disabled `n/a`"
            )
        return None, None
    if required_raw not in {"true", "false"} or disabled_raw not in {"true", "false"}:
        raise WorkflowDispatchError("validator policy cells must be true or false")
    required = required_raw == "true"
    disabled = disabled_raw == "true"
    if required and disabled:
        raise WorkflowDispatchError("a required validator cannot be disabled")
    return required, disabled


def _parse_root_step(row: Mapping[str, str]) -> WorkflowStep:
    if row["role_kind"] != "root":
        raise WorkflowDispatchError("root steps must declare role_kind `root`")
    if row["independence"] not in {"n/a", "-"}:
        raise WorkflowDispatchError("root steps must use independence `n/a`")
    if row["vehicle"] != "root":
        raise WorkflowDispatchError("root steps must use vehicle `root`")
    validator_required, validator_disabled = _validator_policy(
        row, "root-evidence.v1"
    )
    for field in (
        "execution_class",
        "runtime_agent_name",
        "role_lens_sha256",
        "profile_sha256",
        "expected_model",
        "expected_effort",
        "deterministic_contract_sha256",
    ):
        if _optional(row[field]) is not None:
            raise WorkflowDispatchError(f"root step {field} must be `-`")
    if row["mutation"] not in MUTATIONS:
        raise WorkflowDispatchError("root step mutation is invalid")
    return WorkflowStep(
        step_id=row["step_id"],
        depends_on=(),
        barrier=_optional(row["barrier"]),
        role_id="root",
        role_kind="root",
        independence=None,
        execution_class=None,
        runtime_agent_name=None,
        vehicle="root",
        mutation=row["mutation"],
        required_evidence=(),
        role_lens_sha256=None,
        profile_sha256=None,
        expected_model=None,
        expected_effort=None,
        validator_required=validator_required,
        validator_disabled=validator_disabled,
        expected_profile_sandbox=None,
        output_schema="root-evidence.v1",
        command=(),
        command_implementation_path=None,
        command_implementation_sha256=None,
        command_timeout_seconds=None,
        command_output_limit_bytes=None,
        evidence_schema_path=None,
        evidence_schema_sha256=None,
        deterministic_contract_sha256=None,
    )


def parse_workflow_structure(
    text: str,
    *,
    registry: renderer.RoleRegistry | None = None,
    agents_dir: Path | None = None,
) -> Workflow:
    """Parse and bind one exact Workflow Structure table to current role/profile bytes."""

    registry = registry or renderer.load_role_registry()
    agents_dir = agents_dir or renderer.DEFAULT_AGENTS_DIR
    parsed: list[WorkflowStep] = []
    seen: set[str] = set()
    for index, row in enumerate(_extract_rows(text), start=1):
        step_id = row["step_id"]
        if not STEP_ID.fullmatch(step_id) or step_id in seen:
            raise WorkflowDispatchError(f"workflow row {index} has an invalid or duplicate step_id")
        seen.add(step_id)
        depends_on = _list_cell(row["depends_on"], f"step {step_id}.depends_on", STEP_ID)
        barrier = _optional(row["barrier"])
        if barrier is not None and not STEP_ID.fullmatch(barrier):
            raise WorkflowDispatchError(f"step {step_id}.barrier is invalid")
        evidence = _list_cell(
            row["required_evidence"], f"step {step_id}.required_evidence", EVIDENCE_ID
        )
        role_id = row["role_id"]
        if role_id == "root":
            base = _parse_root_step(row)
            parsed.append(
                WorkflowStep(
                    step_id=base.step_id,
                    depends_on=depends_on,
                    barrier=base.barrier,
                    role_id=base.role_id,
                    role_kind=base.role_kind,
                    independence=base.independence,
                    execution_class=base.execution_class,
                    runtime_agent_name=base.runtime_agent_name,
                    vehicle=base.vehicle,
                    mutation=base.mutation,
                    required_evidence=evidence,
                    role_lens_sha256=base.role_lens_sha256,
                    profile_sha256=base.profile_sha256,
                    expected_model=base.expected_model,
                    expected_effort=base.expected_effort,
                    validator_required=base.validator_required,
                    validator_disabled=base.validator_disabled,
                    expected_profile_sandbox=base.expected_profile_sandbox,
                    output_schema=base.output_schema,
                    command=base.command,
                    command_implementation_path=base.command_implementation_path,
                    command_implementation_sha256=base.command_implementation_sha256,
                    command_timeout_seconds=base.command_timeout_seconds,
                    command_output_limit_bytes=base.command_output_limit_bytes,
                    evidence_schema_path=base.evidence_schema_path,
                    evidence_schema_sha256=base.evidence_schema_sha256,
                    deterministic_contract_sha256=base.deterministic_contract_sha256,
                )
            )
            continue
        try:
            role = registry.role(role_id)
        except renderer.RoleRegistryError as exc:
            raise WorkflowDispatchError(str(exc)) from exc
        vehicle = row["vehicle"]
        mutation = row["mutation"]
        if vehicle not in VEHICLES or mutation not in MUTATIONS:
            raise WorkflowDispatchError(f"step {step_id} has an invalid vehicle or mutation")
        if role.kind == "deterministic-validator":
            if row["role_kind"] != role.kind:
                raise WorkflowDispatchError("deterministic step role_kind is stale")
            validator_required, validator_disabled = _validator_policy(
                row, role.output_schema
            )
            if vehicle != "deterministic-tool":
                raise WorkflowDispatchError("deterministic validators require deterministic-tool")
            if mutation != "none":
                raise WorkflowDispatchError(
                    "deterministic validators are evidence-only and require mutation `none`"
                )
            if row["independence"] not in {"n/a", "-"}:
                raise WorkflowDispatchError("deterministic validators use independence `n/a`")
            for field in (
                "execution_class",
                "runtime_agent_name",
                "role_lens_sha256",
                "profile_sha256",
                "expected_model",
                "expected_effort",
            ):
                if _optional(row[field]) is not None:
                    raise WorkflowDispatchError(f"deterministic step {field} must be `-`")
            deterministic_contract_sha256 = _deterministic_contract_sha256(role)
            _require_cell(
                deterministic_contract_sha256,
                row["deterministic_contract_sha256"],
                f"step {step_id}.deterministic contract",
            )
            parsed.append(
                WorkflowStep(
                    step_id=step_id,
                    depends_on=depends_on,
                    barrier=barrier,
                    role_id=role_id,
                    role_kind=role.kind,
                    independence=None,
                    execution_class=None,
                    runtime_agent_name=None,
                    vehicle=vehicle,
                    mutation=mutation,
                    required_evidence=evidence,
                    role_lens_sha256=role.source_behavior_sha256,
                    profile_sha256=None,
                    expected_model=None,
                    expected_effort=None,
                    validator_required=validator_required,
                    validator_disabled=validator_disabled,
                    expected_profile_sandbox=None,
                    output_schema=role.output_schema,
                    command=role.command or (),
                    command_implementation_path=role.command_implementation_path,
                    command_implementation_sha256=role.command_implementation_sha256,
                    command_timeout_seconds=role.command_timeout_seconds,
                    command_output_limit_bytes=role.command_output_limit_bytes,
                    evidence_schema_path=role.evidence_schema_path,
                    evidence_schema_sha256=role.evidence_schema_sha256,
                    deterministic_contract_sha256=deterministic_contract_sha256,
                )
            )
            continue
        if row["role_kind"] != role.kind:
            raise WorkflowDispatchError("agent-lens step role_kind is stale")
        if _optional(row["deterministic_contract_sha256"]) is not None:
            raise WorkflowDispatchError(
                "agent-lens steps must not declare a deterministic contract"
            )
        independence = row["independence"]
        execution_class = row["execution_class"]
        try:
            resolution = renderer.resolve_role(
                registry,
                role_id,
                requested_class=execution_class,
                requested_independence=independence,
            )
        except renderer.RoleRegistryError as exc:
            raise WorkflowDispatchError(str(exc)) from exc
        if vehicle not in {"auto", "subagent", "inline"}:
            raise WorkflowDispatchError(f"agent-lens step {step_id} has an invalid vehicle")
        if resolution.effective_independence == "required" and vehicle == "inline":
            raise WorkflowDispatchError("required independence cannot use inline vehicle")
        if mutation != "none":
            raise WorkflowDispatchError(
                "agent-lens steps are evidence-only; workspace mutation remains root-owned"
            )
        profile = _load_profile(str(resolution.selected_class), agents_dir)
        runtime_agent_name = renderer.RUNTIME_AGENT_NAMES[str(resolution.selected_class)]
        validator_required, validator_disabled = _validator_policy(
            row, role.output_schema
        )
        _require_cell(role.lens_sha256, row["role_lens_sha256"], f"step {step_id}.role lens")
        _require_cell(profile["sha256"], row["profile_sha256"], f"step {step_id}.profile")
        _require_cell(profile["model"], row["expected_model"], f"step {step_id}.model")
        _require_cell(profile["effort"], row["expected_effort"], f"step {step_id}.effort")
        _require_cell(
            runtime_agent_name,
            row["runtime_agent_name"],
            f"step {step_id}.runtime agent",
        )
        parsed.append(
            WorkflowStep(
                step_id=step_id,
                depends_on=depends_on,
                barrier=barrier,
                role_id=role_id,
                role_kind=role.kind,
                independence=resolution.effective_independence,
                execution_class=resolution.selected_class,
                runtime_agent_name=runtime_agent_name,
                vehicle=vehicle,
                mutation=mutation,
                required_evidence=evidence,
                role_lens_sha256=role.lens_sha256,
                profile_sha256=profile["sha256"],
                expected_model=profile["model"],
                expected_effort=profile["effort"],
                validator_required=validator_required,
                validator_disabled=validator_disabled,
                expected_profile_sandbox=profile["sandbox"],
                output_schema=role.output_schema,
                command=(),
                command_implementation_path=None,
                command_implementation_sha256=None,
                command_timeout_seconds=None,
                command_output_limit_bytes=None,
                evidence_schema_path=None,
                evidence_schema_sha256=None,
                deterministic_contract_sha256=None,
            )
        )
    _validate_graph(parsed)
    serialized = [step.to_jsonable() for step in parsed]
    return Workflow(steps=tuple(parsed), sha256=_canonical_sha256(serialized))


def validate_selection_policy(
    workflow: Workflow,
    registry: renderer.RoleRegistry,
) -> dict[str, Any]:
    """Fail closed until a protected skip-review selector exists."""

    selected_role_ids = {step.role_id for step in workflow.steps}
    base_reviewers = tuple(registry.source_behavior_policy["base_reviewer_ids"])
    missing_reviewers = sorted(set(base_reviewers) - selected_role_ids)
    if missing_reviewers:
        raise WorkflowDispatchError(
            f"workflow omits required base reviewers {missing_reviewers}; "
            "skip-review is unavailable without a protected triage decision"
        )
    required_validator_steps = sorted(
        step.step_id
        for step in workflow.steps
        if step.validator_required is True and step.validator_disabled is not True
    )
    if not required_validator_steps:
        raise WorkflowDispatchError(
            "workflow must select at least one required validator"
        )
    return {
        "review_mode": "full-review",
        "base_reviewer_ids": list(base_reviewers),
        "selected_role_ids": sorted(selected_role_ids),
        "required_validator_step_ids": required_validator_steps,
        "policy_sha256": _canonical_sha256(registry.source_behavior_policy),
    }


def _validate_graph(steps: list[WorkflowStep]) -> None:
    ids = {step.step_id for step in steps}
    for step in steps:
        missing = set(step.depends_on) - ids
        if missing or step.step_id in step.depends_on:
            raise WorkflowDispatchError(
                f"step {step.step_id} has invalid dependencies {sorted(missing)}"
            )
    visiting: set[str] = set()
    visited: set[str] = set()
    by_id = {step.step_id: step for step in steps}

    def visit(step_id: str) -> None:
        if step_id in visiting:
            raise WorkflowDispatchError("Workflow Structure contains a dependency cycle")
        if step_id in visited:
            return
        visiting.add(step_id)
        for dependency in by_id[step_id].depends_on:
            visit(dependency)
        visiting.remove(step_id)
        visited.add(step_id)

    for step in steps:
        visit(step.step_id)
    cohorts: dict[str, set[str]] = {}
    for step in steps:
        if step.barrier:
            cohorts.setdefault(step.barrier, set()).add(step.step_id)
    for step in steps:
        for cohort in cohorts.values():
            overlap = set(step.depends_on) & cohort
            if overlap and overlap != cohort:
                raise WorkflowDispatchError(
                    f"step {step.step_id} must depend on every member of barrier cohort"
                )


def _default_state(workflow: Workflow) -> dict[str, StepState]:
    return {
        step.step_id: StepState("pending", 0, None, ())
        for step in workflow.steps
    }


def _validate_result_state(
    plugin_data: Path,
    workflow: Workflow,
    workflow_run_sha256: str,
    step_id: str,
    state: StepState,
) -> None:
    if state.result_ref is None:
        return
    try:
        import dispatch_receipt as receipts

        receipt, result = receipts.validate_normalized_receipt(
            plugin_data, state.result_ref, workflow
        )
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise WorkflowDispatchError(
            f"dispatch result for {step_id} is not protected verified evidence: {exc}"
        ) from exc
    if (
        receipt["step_id"] != step_id
        or receipt["attempt"] != state.cycle
        or receipt["workflow_run_sha256"] != workflow_run_sha256
    ):
        raise WorkflowDispatchError(
            f"dispatch result for {step_id} does not bind its step and cycle"
        )
    findings = result["evidence"].get("findings", [])
    unresolved = tuple(
        finding["finding_id"] for finding in findings if not finding["resolved"]
    )
    if state.status == "passed":
        if unresolved:
            raise WorkflowDispatchError(
                f"passed dispatch state for {step_id} has unresolved findings"
            )
        gate_status = result["evidence"].get("gate_status")
        planned = workflow.step(step_id)
        if (
            gate_status is not None
            and (
                gate_status in {"hard-fail", "blocked"}
                or (
                    planned.validator_disabled is True
                    and gate_status != "skipped-by-config"
                )
                or (
                    planned.validator_disabled is not True
                    and gate_status == "skipped-by-config"
                )
                or (
                    planned.validator_required is True
                    and planned.validator_disabled is not True
                    and gate_status != "pass"
                )
            )
        ):
            raise WorkflowDispatchError(
                f"passed dispatch state for {step_id} has a non-passing validator status"
            )
    elif state.status == "needs-follow-up":
        if unresolved != state.finding_refs:
            raise WorkflowDispatchError(
                f"follow-up dispatch state for {step_id} does not bind unresolved findings"
            )


def load_dispatch_state(
    payload: object,
    workflow: Workflow,
    *,
    workflow_run_sha256: str,
    plugin_data: Path | None = None,
) -> dict[str, StepState]:
    if not isinstance(workflow_run_sha256, str) or not SHA256.fullmatch(
        workflow_run_sha256
    ):
        raise WorkflowDispatchError("dispatch state workflow run digest is invalid")
    if payload is None:
        return _default_state(workflow)
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "workflow_sha256",
        "workflow_run_sha256",
        "steps",
    }:
        raise WorkflowDispatchError("dispatch state fields are not closed")
    if (
        payload["schema_version"] != 1
        or payload["workflow_sha256"] != workflow.sha256
        or payload["workflow_run_sha256"] != workflow_run_sha256
    ):
        raise WorkflowDispatchError("dispatch state does not bind this workflow")
    raw_steps = payload["steps"]
    if not isinstance(raw_steps, dict) or set(raw_steps) != {
        step.step_id for step in workflow.steps
    }:
        raise WorkflowDispatchError("dispatch state must cover every workflow step exactly")
    state: dict[str, StepState] = {}
    for step_id, raw in raw_steps.items():
        if not isinstance(raw, dict) or set(raw) != {
            "status",
            "cycle",
            "result_ref",
            "finding_refs",
        }:
            raise WorkflowDispatchError(f"dispatch state for {step_id} is not closed")
        status = raw["status"]
        cycle = raw["cycle"]
        result_ref = raw["result_ref"]
        finding_refs = raw["finding_refs"]
        if (
            status not in STEP_STATUSES
            or isinstance(cycle, bool)
            or not isinstance(cycle, int)
            or not 0 <= cycle <= MAX_CYCLES
        ):
            raise WorkflowDispatchError(f"dispatch state for {step_id} is invalid")
        if result_ref is not None and (
            not isinstance(result_ref, str)
            or not RECEIPT_REF.fullmatch(result_ref)
            or any(part in {"", ".", ".."} for part in result_ref.split("/"))
        ):
            raise WorkflowDispatchError(f"dispatch result_ref for {step_id} is invalid")
        if not isinstance(finding_refs, list):
            raise WorkflowDispatchError(f"dispatch finding_refs for {step_id} is invalid")
        normalized = tuple(finding_refs)
        if any(
            not isinstance(value, str)
            or not EVIDENCE_ID.fullmatch(value)
            or any(part in {"", ".", ".."} for part in value.split("/"))
            for value in normalized
        ):
            raise WorkflowDispatchError(f"dispatch finding_refs for {step_id} is invalid")
        if len(normalized) != len(set(normalized)):
            raise WorkflowDispatchError(f"dispatch finding_refs for {step_id} contains duplicates")
        if status == "pending" and (cycle != 0 or result_ref is not None or normalized):
            raise WorkflowDispatchError(f"pending dispatch state for {step_id} carries work evidence")
        if status == "running" and result_ref is not None:
            raise WorkflowDispatchError(f"running dispatch state for {step_id} carries a result")
        if status != "pending" and cycle == 0:
            raise WorkflowDispatchError(
                f"non-pending dispatch state for {step_id} requires an attempt"
            )
        if status == "passed" and (result_ref is None or normalized):
            raise WorkflowDispatchError(
                f"passed dispatch state for {step_id} requires a result and no findings"
            )
        if status == "needs-follow-up" and (result_ref is None or not normalized):
            raise WorkflowDispatchError(
                f"follow-up dispatch state for {step_id} requires a result and findings"
            )
        if status == "stale" and (result_ref is None or normalized):
            raise WorkflowDispatchError(
                f"stale dispatch state for {step_id} requires its prior result only"
            )
        step_state = StepState(status, cycle, result_ref, normalized)
        if result_ref is not None:
            if plugin_data is None:
                raise WorkflowDispatchError(
                    "dispatch result state requires the protected plugin data root"
                )
            _validate_result_state(
                plugin_data,
                workflow,
                workflow_run_sha256,
                step_id,
                step_state,
            )
        state[step_id] = step_state
    return state


def emit_intents(
    workflow: Workflow,
    state: Mapping[str, StepState],
    *,
    workflow_run_sha256: str,
) -> dict[str, Any]:
    """Emit deterministic ready/follow-up intents without starting a process or child."""

    if not isinstance(workflow_run_sha256, str) or not SHA256.fullmatch(
        workflow_run_sha256
    ):
        raise WorkflowDispatchError("dispatch workflow run digest is invalid")

    follow_ups = [
        step for step in workflow.steps if state[step.step_id].status == "needs-follow-up"
    ]
    intents: list[dict[str, Any]] = []
    escalations: list[dict[str, str]] = []
    follow_up_ids = {step.step_id for step in follow_ups}
    invalidated: set[str] = set()
    changed = True
    while changed:
        changed = False
        for step in workflow.steps:
            if step.step_id in follow_up_ids or step.step_id in invalidated:
                continue
            if any(
                dependency in follow_up_ids or dependency in invalidated
                for dependency in step.depends_on
            ) and state[step.step_id].status in {"passed", "running"}:
                invalidated.add(step.step_id)
                changed = True
    invalidations = [
        {
            "step_id": step_id,
            "from_status": state[step_id].status,
            "to_status": "stale",
            "reason": (
                "interrupt the running step before upstream remediation"
                if state[step_id].status == "running"
                else "an upstream dependency requires remediation"
            ),
        }
        for step_id in sorted(invalidated)
    ]
    if invalidations:
        return {
            "schema_version": 1,
            "claim": "dispatch-state-update-required",
            "workflow_sha256": workflow.sha256,
            "workflow_run_sha256": workflow_run_sha256,
            "intents": [],
            "invalidations": invalidations,
            "blocked": [],
            "escalations": [],
            "complete": False,
        }
    if follow_ups:
        for step in follow_ups:
            current = state[step.step_id]
            if current.cycle >= MAX_CYCLES:
                escalations.append(
                    {"step_id": step.step_id, "reason": "three-cycle remediation cap reached"}
                )
                continue
            target_cycle = current.cycle + 1
            if any(state[dependency].status != "passed" for dependency in step.depends_on):
                continue
            intents.append(
                {
                    "intent": "follow-up",
                    "cycle": target_cycle,
                    "previous_receipt_ref": current.result_ref,
                    "finding_refs": list(current.finding_refs),
                    **step.to_jsonable(),
                }
            )
    else:
        for step in workflow.steps:
            current = state[step.step_id]
            if current.status not in {"pending", "stale"}:
                continue
            dependency_states = [state[value].status for value in step.depends_on]
            if all(status == "passed" for status in dependency_states):
                target_cycle = 1 if current.status == "pending" else current.cycle + 1
                if target_cycle > MAX_CYCLES:
                    escalations.append(
                        {
                            "step_id": step.step_id,
                            "reason": "three-cycle remediation cap reached",
                        }
                    )
                    continue
                intents.append(
                    {
                        "intent": "revalidate" if current.status == "stale" else "run",
                        "cycle": target_cycle,
                        "previous_receipt_ref": (
                            current.result_ref if current.status == "stale" else None
                        ),
                        "finding_refs": [],
                        **step.to_jsonable(),
                    }
                )
    blocked = []
    for step in workflow.steps:
        if state[step.step_id].status != "pending":
            continue
        blockers = [
            dependency
            for dependency in step.depends_on
            if state[dependency].status in {"failed", "blocked"}
        ]
        if blockers:
            blocked.append({"step_id": step.step_id, "blocked_by": blockers})
    return {
        "schema_version": 1,
        "claim": "dispatch-intents-only",
        "workflow_sha256": workflow.sha256,
        "workflow_run_sha256": workflow_run_sha256,
        "intents": intents,
        "invalidations": [],
        "blocked": blocked,
        "escalations": escalations,
        "complete": all(state[step.step_id].status == "passed" for step in workflow.steps),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--agents-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=renderer.DEFAULT_REGISTRY)
    parser.add_argument("--roles-dir", type=Path, default=renderer.DEFAULT_ROLES_DIR)
    parser.add_argument("--workflow-run-ref", required=True)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--plugin-data", type=Path, required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        plan = _read_bounded(args.plan, MAX_PLAN_BYTES, "workflow plan").decode("utf-8")
        default_registry = (
            args.registry.resolve() == renderer.DEFAULT_REGISTRY.resolve()
            and args.roles_dir.resolve() == renderer.DEFAULT_ROLES_DIR.resolve()
        )
        registry = renderer.load_role_registry(
            args.registry,
            args.roles_dir,
            expected_role_ids=(renderer.EXPECTED_ROLE_IDS if default_registry else None),
        )
        workflow = parse_workflow_structure(
            plan,
            agents_dir=args.agents_dir,
            registry=registry,
        )
        validate_selection_policy(workflow, registry)
        if not args.plugin_data.is_absolute():
            raise WorkflowDispatchError("--plugin-data must be an absolute protected root")
        import dispatch_receipt as receipts

        _workflow_run, workflow_run_bytes = receipts._load_workflow_run_record(
            args.plugin_data,
            args.workflow_run_ref,
            workflow=workflow,
        )
        workflow_run_sha256 = hashlib.sha256(workflow_run_bytes).hexdigest()
        state_payload: object = None
        if args.state:
            state_payload = json.loads(
                _read_bounded(args.state, MAX_STATE_BYTES, "dispatch state")
            )
        state = load_dispatch_state(
            state_payload,
            workflow,
            workflow_run_sha256=workflow_run_sha256,
            plugin_data=args.plugin_data,
        )
        payload = emit_intents(
            workflow,
            state,
            workflow_run_sha256=workflow_run_sha256,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        WorkflowDispatchError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(f"verified workflow dispatch failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
