#!/usr/bin/env python3
"""Closed data contract for Saga external actions."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Mapping


REQUEST_SCHEMA = "saga.external-action.request.v1"
APPROVAL_SCHEMA = "saga.external-action.approval.v1"
EVENT_SCHEMA = "saga.external-action.event.v1"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
STAGES = frozenset({"ideate", "brainstorm", "plan", "work", "doc-review", "code-review"})
INTENTS = frozenset({"offload", "second-opinion"})
SENSITIVITY = frozenset({"public", "internal", "sensitive"})


class ContractError(ValueError):
    """An external-action record violates the closed contract."""


class Requiredness(StrEnum):
    BEST_EFFORT = "best-effort"
    REQUIRED = "required-before-continue"


class State(StrEnum):
    REQUESTED = "requested"
    RESOLVED = "resolved"
    APPROVED = "approved"
    CLAIMED = "claimed"
    LAUNCHED = "launched"
    AVAILABLE = "available"
    ACCEPTED = "accepted"
    CONSUMED = "consumed"
    REJECTED = "rejected"
    NOT_LAUNCHED = "not-launched"
    UNAVAILABLE = "unavailable"
    TIMED_OUT = "timed-out"
    INTERRUPTED = "interrupted"
    CANCELED = "canceled"
    INVALID_EVIDENCE = "invalid-evidence"


TERMINAL_FAILURE_STATES = frozenset(
    {
        State.REJECTED,
        State.NOT_LAUNCHED,
        State.UNAVAILABLE,
        State.TIMED_OUT,
        State.INTERRUPTED,
        State.CANCELED,
        State.INVALID_EVIDENCE,
    }
)

TRANSITIONS: dict[State, dict[str, State]] = {
    State.REQUESTED: {"resolve": State.RESOLVED},
    State.RESOLVED: {
        "approve": State.APPROVED,
        "reject": State.REJECTED,
        "remove": State.NOT_LAUNCHED,
        "invalidate": State.RESOLVED,
    },
    State.APPROVED: {
        "claim": State.CLAIMED,
        "invalidate": State.RESOLVED,
        "cancel": State.CANCELED,
    },
    State.CLAIMED: {
        "launch": State.LAUNCHED,
        "unavailable": State.UNAVAILABLE,
        "not-launch": State.NOT_LAUNCHED,
        "interrupt": State.INTERRUPTED,
    },
    State.LAUNCHED: {
        "complete": State.AVAILABLE,
        "timeout": State.TIMED_OUT,
        "interrupt": State.INTERRUPTED,
        "cancel": State.CANCELED,
        "invalidate-evidence": State.INVALID_EVIDENCE,
    },
    State.AVAILABLE: {
        "accept": State.ACCEPTED,
        "reject": State.REJECTED,
        "invalidate-evidence": State.INVALID_EVIDENCE,
    },
    State.ACCEPTED: {"consume": State.CONSUMED},
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def require_id(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ContractError(f"{field_name} must match {ID_RE.pattern}")
    return value


def _string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field_name} must be a non-empty string")
    return value.strip()


def _required_str(data: Mapping[str, Any], field_name: str) -> str:
    return _string(data.get(field_name), field_name=field_name)


def _string_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ContractError(f"{field_name} must be a list of non-empty strings")
    normalized = tuple(item.strip() for item in value)
    if len(set(normalized)) != len(normalized):
        raise ContractError(f"{field_name} must not contain duplicates")
    return normalized


@dataclass(frozen=True, slots=True)
class ActionRequest:
    saga_id: str
    run_id: str
    action_id: str
    stage: str
    intent: str
    trigger: str
    requiredness: Requiredness
    provider_constraints: Mapping[str, Any]
    context_scope: tuple[str, ...]
    sensitivity: str
    write_set: tuple[str, ...]
    evidence_destination: str
    consumption_point: str
    created_at: str
    attempt: int = 1
    predecessor_request_sha256: str | None = None
    schema: str = field(default=REQUEST_SCHEMA, init=False)

    def __post_init__(self) -> None:
        require_id(self.saga_id, field_name="saga_id")
        require_id(self.run_id, field_name="run_id")
        require_id(self.action_id, field_name="action_id")
        if self.stage not in STAGES:
            raise ContractError(f"stage must be one of {sorted(STAGES)}")
        if self.intent not in INTENTS:
            raise ContractError(f"intent must be one of {sorted(INTENTS)}")
        _string(self.trigger, field_name="trigger")
        if not isinstance(self.provider_constraints, Mapping):
            raise ContractError("provider_constraints must be an object")
        if self.sensitivity not in SENSITIVITY:
            raise ContractError(f"sensitivity must be one of {sorted(SENSITIVITY)}")
        _string(self.evidence_destination, field_name="evidence_destination")
        _string(self.consumption_point, field_name="consumption_point")
        _string(self.created_at, field_name="created_at")
        if isinstance(self.attempt, bool) or not isinstance(self.attempt, int) or self.attempt < 1:
            raise ContractError("attempt must be a positive integer")
        if self.predecessor_request_sha256 is not None and not re.fullmatch(
            r"[0-9a-f]{64}", self.predecessor_request_sha256
        ):
            raise ContractError("predecessor_request_sha256 must be a SHA-256 digest")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ActionRequest:
        if data.get("schema") not in {None, REQUEST_SCHEMA}:
            raise ContractError("request schema is unsupported")
        return cls(
            saga_id=_required_str(data, "saga_id"),
            run_id=_required_str(data, "run_id"),
            action_id=_required_str(data, "action_id"),
            stage=_required_str(data, "stage"),
            intent=_required_str(data, "intent"),
            trigger=_required_str(data, "trigger"),
            requiredness=Requiredness(_required_str(data, "requiredness")),
            provider_constraints=dict(data.get("provider_constraints", {})),
            context_scope=_string_tuple(data.get("context_scope"), field_name="context_scope"),
            sensitivity=_required_str(data, "sensitivity"),
            write_set=_string_tuple(data.get("write_set"), field_name="write_set"),
            evidence_destination=_required_str(data, "evidence_destination"),
            consumption_point=_required_str(data, "consumption_point"),
            created_at=_required_str(data, "created_at"),
            attempt=data.get("attempt", 1),
            predecessor_request_sha256=data.get("predecessor_request_sha256"),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["requiredness"] = self.requiredness.value
        value["provider_constraints"] = dict(self.provider_constraints)
        value["context_scope"] = list(self.context_scope)
        value["write_set"] = list(self.write_set)
        return value

    @property
    def request_sha256(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ActionApproval:
    action_id: str
    approved_at: str
    operator: str
    route: Mapping[str, Any]
    context_scope: tuple[str, ...]
    sensitivity: str
    base_revision: str
    write_set: tuple[str, ...]
    cost_class: str
    egress: Mapping[str, Any]
    request_sha256: str
    payload: Any = None
    payload_sha256: str = field(default_factory=lambda: digest(None))
    dirty_overlap: tuple[str, ...] = ()
    dirty_overlap_sha256: str = field(default_factory=lambda: digest([]))
    schema: str = field(default=APPROVAL_SCHEMA, init=False)

    def __post_init__(self) -> None:
        require_id(self.action_id, field_name="action_id")
        _string(self.approved_at, field_name="approved_at")
        _string(self.operator, field_name="operator")
        if not isinstance(self.route, Mapping) or not self.route:
            raise ContractError("route must be a non-empty object")
        if self.sensitivity not in SENSITIVITY:
            raise ContractError(f"sensitivity must be one of {sorted(SENSITIVITY)}")
        if not re.fullmatch(r"[0-9a-f]{40}", self.base_revision):
            raise ContractError("base_revision must be a full commit SHA")
        _string(self.cost_class, field_name="cost_class")
        if not isinstance(self.egress, Mapping):
            raise ContractError("egress must be an object")
        if not re.fullmatch(r"[0-9a-f]{64}", self.request_sha256):
            raise ContractError("request_sha256 must be a SHA-256 digest")
        if self.payload_sha256 != digest(self.payload):
            raise ContractError("payload_sha256 does not match payload")
        if self.dirty_overlap_sha256 != digest(list(self.dirty_overlap)):
            raise ContractError("dirty_overlap_sha256 does not match dirty_overlap")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ActionApproval:
        if data.get("schema") not in {None, APPROVAL_SCHEMA}:
            raise ContractError("approval schema is unsupported")
        return cls(
            action_id=_required_str(data, "action_id"),
            approved_at=_required_str(data, "approved_at"),
            operator=_required_str(data, "operator"),
            route=dict(data.get("route", {})),
            context_scope=_string_tuple(data.get("context_scope"), field_name="context_scope"),
            sensitivity=_required_str(data, "sensitivity"),
            base_revision=_required_str(data, "base_revision"),
            write_set=_string_tuple(data.get("write_set"), field_name="write_set"),
            cost_class=_required_str(data, "cost_class"),
            egress=dict(data.get("egress", {})),
            request_sha256=_required_str(data, "request_sha256"),
            payload=data.get("payload"),
            payload_sha256=data.get("payload_sha256", digest(data.get("payload"))),
            dirty_overlap=_string_tuple(data.get("dirty_overlap"), field_name="dirty_overlap"),
            dirty_overlap_sha256=data.get(
                "dirty_overlap_sha256", digest(list(data.get("dirty_overlap", [])))
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["route"] = dict(self.route)
        value["context_scope"] = list(self.context_scope)
        value["write_set"] = list(self.write_set)
        value["egress"] = dict(self.egress)
        value["dirty_overlap"] = list(self.dirty_overlap)
        return value

    @property
    def approval_fingerprint(self) -> str:
        payload = self.to_dict()
        payload.pop("schema", None)
        payload.pop("approved_at", None)
        payload.pop("operator", None)
        return digest(payload)


def next_state(current: State, event: str, *, rationale: str | None = None) -> State:
    if event == "override-continue":
        if current not in TERMINAL_FAILURE_STATES:
            raise ContractError("override-continue is allowed only from a terminal failure")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ContractError("override-continue requires a rationale")
        return current
    try:
        return TRANSITIONS[current][event]
    except KeyError as exc:
        raise ContractError(f"event {event!r} is invalid from state {current.value!r}") from exc
