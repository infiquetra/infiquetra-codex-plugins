#!/usr/bin/env python3
"""Resolve external-action templates with explicit, policy, legacy, and default precedence."""

from __future__ import annotations

import json
import hashlib
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine_offer  # noqa: E402
import external_action_contract as contract  # noqa: E402


POLICY_VERSION = 1
POLICY_PATH = Path(".codex") / "saga" / "external-action-policy.json"
DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "references" / "external-action-defaults.yaml"
WORKFLOW_ACTION_FIELDS = {
    "action_id",
    "purpose",
    "provider",
    "model",
    "egress",
    "context",
    "sensitivity",
    "cost",
    "writes_or_artifact",
    "requiredness",
    "authority",
}
SECRET_PATH_PARTS = frozenset(
    {".env", "secrets", "credentials", ".aws", ".ssh", ".gnupg", "private-keys"}
)


class PolicyError(ValueError):
    """Policy input is malformed or outside the closed schema."""


@dataclass(frozen=True, slots=True)
class ActionTemplate:
    action_id: str
    intent: str
    trigger: str
    requiredness: contract.Requiredness
    consumption_point: str
    provider_constraints: Mapping[str, Any]
    context_scope: tuple[str, ...]
    sensitivity: str
    write_set: tuple[str, ...]
    evidence_destination: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ActionTemplate:
        allowed = {
            "action_id", "intent", "trigger", "requiredness", "consumption_point",
            "provider_constraints", "context_scope", "sensitivity", "write_set",
            "evidence_destination",
        }
        unknown = set(value) - allowed
        if unknown:
            raise PolicyError(f"action template has unknown keys: {sorted(unknown)}")
        action_id = _required_text(value, "action_id")
        intent = _required_text(value, "intent")
        trigger = _required_text(value, "trigger")
        consumption = _required_text(value, "consumption_point")
        contract.require_id(action_id, field_name="action_id")
        if intent not in contract.INTENTS:
            raise PolicyError(f"intent must be one of {sorted(contract.INTENTS)}")
        requiredness = contract.Requiredness(value.get("requiredness", "best-effort"))
        constraints = value.get("provider_constraints", {})
        if not isinstance(constraints, Mapping):
            raise PolicyError("provider_constraints must be an object")
        context_scope = _strings(value.get("context_scope", ()), "context_scope")
        write_set = _strings(value.get("write_set", ()), "write_set")
        sensitivity = value.get("sensitivity", "internal")
        if sensitivity not in contract.SENSITIVITY:
            raise PolicyError(f"sensitivity must be one of {sorted(contract.SENSITIVITY)}")
        destination = value.get("evidence_destination", ".codex/saga/external-actions")
        if not isinstance(destination, str) or not destination.strip():
            raise PolicyError("evidence_destination must be a non-empty string")
        return cls(
            action_id=action_id,
            intent=intent,
            trigger=trigger.strip(),
            requiredness=requiredness,
            consumption_point=consumption.strip(),
            provider_constraints=dict(constraints),
            context_scope=context_scope,
            sensitivity=sensitivity,
            write_set=write_set,
            evidence_destination=destination.strip(),
        )


@dataclass(frozen=True, slots=True)
class ResolvedPolicy:
    source: str
    actions: tuple[ActionTemplate, ...]


def workflow_rows_to_templates(rows: Sequence[Mapping[str, Any]]) -> tuple[ActionTemplate, ...]:
    """Import the compiler's approved external rows into the existing Saga lifecycle."""

    templates: list[ActionTemplate] = []
    for index, row in enumerate(rows):
        if set(row) != WORKFLOW_ACTION_FIELDS:
            raise PolicyError(
                f"workflow external action {index} fields must be exactly {sorted(WORKFLOW_ACTION_FIELDS)}"
            )
        if row.get("authority") != contract.AUTHORITY:
            raise PolicyError("workflow external actions must have non-gating authority")
        requiredness = row.get("requiredness")
        if requiredness == "required":
            saga_requiredness = contract.Requiredness.REQUIRED.value
        elif requiredness == "best-effort":
            saga_requiredness = contract.Requiredness.BEST_EFFORT.value
        else:
            raise PolicyError("workflow external action requiredness is invalid")
        context_scope = _strings(row.get("context", ()), "context")
        writes_or_artifact = _strings(
            row.get("writes_or_artifact", ()), "writes_or_artifact"
        )
        write_set = tuple(item for item in writes_or_artifact if not item.startswith("artifact:"))
        for path in (*context_scope, *write_set):
            parts = Path(path).parts
            folded_parts = {part.casefold() for part in parts}
            if path == "." or path.startswith("/") or ".." in parts or ".git" in parts:
                raise PolicyError("workflow external paths must be contained repository paths")
            if SECRET_PATH_PARTS & folded_parts:
                raise PolicyError(f"workflow external path {path!r} is secret-bearing")
        provider = _required_text(row, "provider")
        model = _required_text(row, "model")
        purpose = _required_text(row, "purpose")
        egress = _strings(row.get("egress", ()), "egress")
        templates.append(
            ActionTemplate.from_mapping(
                {
                    "action_id": _required_text(row, "action_id"),
                    "intent": "offload" if write_set else "second-opinion",
                    "trigger": purpose,
                    "requiredness": saga_requiredness,
                    "consumption_point": "verified-workflow-run-record",
                    "provider_constraints": {
                        "provider": provider,
                        "model": model,
                        "egress": list(egress),
                        "cost": _required_text(row, "cost"),
                        "authority": contract.AUTHORITY,
                    },
                    "context_scope": list(context_scope),
                    "sensitivity": _required_text(row, "sensitivity"),
                    "write_set": list(write_set),
                    "evidence_destination": ".codex/saga/external-actions",
                }
            )
        )
    if len({item.action_id for item in templates}) != len(templates):
        raise PolicyError("workflow external actions contain duplicate IDs")
    return tuple(templates)


def _strings(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise PolicyError(f"{field_name} must be a list of non-empty strings")
    result = tuple(item.strip() for item in value)
    if len(set(result)) != len(result):
        raise PolicyError(f"{field_name} must not contain duplicates")
    return result


def _required_text(value: Mapping[str, Any], field_name: str) -> str:
    item = value.get(field_name)
    if not isinstance(item, str) or not item.strip():
        raise PolicyError(f"{field_name} must be a non-empty string")
    return item.strip()


def _parse_document(raw: Any, *, source: str) -> dict[str, tuple[ActionTemplate, ...]]:
    if not isinstance(raw, Mapping) or set(raw) != {"version", "stages"} or raw.get("version") != POLICY_VERSION:
        raise PolicyError(f"{source}: expected closed version {POLICY_VERSION} policy")
    stages = raw.get("stages")
    if not isinstance(stages, Mapping):
        raise PolicyError(f"{source}: stages must be an object")
    parsed: dict[str, tuple[ActionTemplate, ...]] = {}
    for stage, actions in stages.items():
        if stage not in contract.STAGES:
            raise PolicyError(f"{source}: unsupported stage {stage!r}")
        if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes)):
            raise PolicyError(f"{source}: stage {stage!r} must contain a list")
        templates = tuple(ActionTemplate.from_mapping(action) for action in actions if isinstance(action, Mapping))
        if len(templates) != len(actions) or len({item.action_id for item in templates}) != len(templates):
            raise PolicyError(f"{source}: stage {stage!r} has invalid or duplicate actions")
        parsed[str(stage)] = templates
    return parsed


def load_defaults(path: Path = DEFAULTS_PATH) -> dict[str, tuple[ActionTemplate, ...]]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PolicyError(f"{path}: cannot load defaults: {exc}") from exc
    return _parse_document(raw, source=str(path))


def load_policy(repo_root: Path) -> dict[str, tuple[ActionTemplate, ...]]:
    path = repo_root / POLICY_PATH
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"{path}: cannot load policy: {exc}") from exc
    return _parse_document(raw, source=str(path))


def policy_sha256(repo_root: Path) -> str:
    path = repo_root / POLICY_PATH
    payload = path.read_bytes() if path.exists() else b""
    return hashlib.sha256(payload).hexdigest()


def save_policy(
    repo_root: Path,
    stages: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    expected_sha256: str,
) -> Path:
    """Persist a closed policy document with optimistic concurrency."""
    document: dict[str, Any] = {"version": POLICY_VERSION, "stages": dict(stages)}
    parsed = _parse_document(document, source="policy update")
    normalized = {
        "version": POLICY_VERSION,
        "stages": {
            stage: [_template_json(item) for item in actions]
            for stage, actions in sorted(parsed.items())
        },
    }
    if policy_sha256(repo_root) != expected_sha256:
        raise PolicyError("external-action policy digest changed before apply")
    path = repo_root / POLICY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(normalized, indent=2, sort_keys=True) + "\n"
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if policy_sha256(repo_root) != expected_sha256:
            raise PolicyError("external-action policy changed during apply")
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def _template_json(item: ActionTemplate) -> dict[str, Any]:
    return {
        "action_id": item.action_id,
        "intent": item.intent,
        "trigger": item.trigger,
        "requiredness": item.requiredness.value,
        "consumption_point": item.consumption_point,
        "provider_constraints": dict(item.provider_constraints),
        "context_scope": list(item.context_scope),
        "sensitivity": item.sensitivity,
        "write_set": list(item.write_set),
        "evidence_destination": item.evidence_destination,
    }


def resolve(
    stage: str,
    *,
    repo_root: Path,
    explicit_actions: Sequence[Mapping[str, Any]] | None = None,
    defaults_path: Path = DEFAULTS_PATH,
) -> ResolvedPolicy:
    if stage not in contract.STAGES:
        raise PolicyError(f"unsupported stage {stage!r}")
    if explicit_actions is not None:
        return ResolvedPolicy("explicit", tuple(ActionTemplate.from_mapping(item) for item in explicit_actions))
    policy = load_policy(repo_root)
    if stage in policy:
        return ResolvedPolicy("policy", policy[stage])
    legacy = engine_offer.load_preferences(repo_root).stages.get(stage)
    defaults = load_defaults(defaults_path)
    if legacy is not None:
        if legacy.intent == "none":
            return ResolvedPolicy("legacy", ())
        matches = tuple(item for item in defaults.get(stage, ()) if item.intent == legacy.intent)
        return ResolvedPolicy("legacy", matches)
    return ResolvedPolicy("default", defaults.get(stage, ()))
