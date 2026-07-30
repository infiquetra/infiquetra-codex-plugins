#!/usr/bin/env python3
"""Closed one-shot request/result contract for the Saga external harness."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
from typing import Any, Mapping


REQUEST_SCHEMA = "saga.harness.request.v1"
RESULT_SCHEMA = "saga.harness.result.v1"
AUTHORITY = "non-gating"
MODES = frozenset({"direct", "verified-workflow"})
STATUSES = frozenset({"available", "unavailable", "timed-out", "invalid-output"})
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
GATEKEEPER_KEYS = frozenset(
    {"adjudicated", "blocking", "gate_status", "hard_stop", "overall", "verdict"}
)


class ContractError(ValueError):
    """A Saga harness request or result violates its closed contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field_name} must be a non-empty string")
    return value.strip()


def _id(value: object, field_name: str) -> str:
    normalized = _string(value, field_name)
    if ID_RE.fullmatch(normalized) is None:
        raise ContractError(f"{field_name} must match {ID_RE.pattern}")
    return normalized


def _path(value: object, field_name: str) -> str:
    normalized = _string(value, field_name)
    path = PurePosixPath(normalized)
    if (
        normalized.startswith(("/", "~"))
        or "\\" in normalized
        or normalized in {".", ".."}
        or any(part in {"", ".", "..", ".git"} for part in path.parts)
        or path.as_posix() != normalized
    ):
        raise ContractError(f"{field_name} must be a safe repository-relative path")
    return normalized


def _paths(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ContractError(f"{field_name} must be a path list")
    result = tuple(_path(item, f"{field_name}[{index}]") for index, item in enumerate(value))
    if len(result) != len(set(result)):
        raise ContractError(f"{field_name} must not contain duplicates")
    return result


def _closed(data: Mapping[str, Any], expected: set[str], where: str) -> None:
    if set(data) != expected:
        raise ContractError(
            f"{where} fields must be exactly {sorted(expected)}; got {sorted(data)}"
        )


@dataclass(frozen=True, slots=True)
class HarnessRequest:
    request_id: str
    engine_id: str
    variant: str
    task: str
    base_revision: str
    context_scope: tuple[str, ...] = ()
    write_set: tuple[str, ...] = ()
    mode: str = "direct"
    authority: str = field(default=AUTHORITY, init=False)
    schema: str = field(default=REQUEST_SCHEMA, init=False)

    def __post_init__(self) -> None:
        _id(self.request_id, "request_id")
        _id(self.engine_id, "engine_id")
        _id(self.variant, "variant")
        _string(self.task, "task")
        _string(self.base_revision, "base_revision")
        _paths(self.context_scope, "context_scope")
        _paths(self.write_set, "write_set")
        if self.mode not in MODES:
            raise ContractError(f"mode must be one of {sorted(MODES)}")
        if self.mode == "direct" and self.write_set:
            raise ContractError("direct Saga external calls are read-only")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> HarnessRequest:
        expected = {
            "schema",
            "request_id",
            "engine_id",
            "variant",
            "task",
            "base_revision",
            "context_scope",
            "write_set",
            "mode",
            "authority",
        }
        _closed(data, expected, "harness request")
        if data.get("schema") != REQUEST_SCHEMA or data.get("authority") != AUTHORITY:
            raise ContractError("harness request schema or authority is invalid")
        return cls(
            request_id=_id(data.get("request_id"), "request_id"),
            engine_id=_id(data.get("engine_id"), "engine_id"),
            variant=_id(data.get("variant"), "variant"),
            task=_string(data.get("task"), "task"),
            base_revision=_string(data.get("base_revision"), "base_revision"),
            context_scope=_paths(data.get("context_scope"), "context_scope"),
            write_set=_paths(data.get("write_set"), "write_set"),
            mode=_string(data.get("mode"), "mode"),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["context_scope"] = list(self.context_scope)
        value["write_set"] = list(self.write_set)
        return value

    @property
    def request_sha256(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class HarnessResult:
    request_id: str
    engine_id: str
    variant: str
    status: str
    evidence: str
    findings: tuple[Mapping[str, str], ...]
    receipt: Mapping[str, Any] | None
    changed_paths: tuple[str, ...] = ()
    patch_ref: str | None = None
    patch_sha256: str | None = None
    detail: str = ""
    authority: str = field(default=AUTHORITY, init=False)
    schema: str = field(default=RESULT_SCHEMA, init=False)

    def __post_init__(self) -> None:
        _id(self.request_id, "request_id")
        _id(self.engine_id, "engine_id")
        _id(self.variant, "variant")
        if self.status not in STATUSES:
            raise ContractError(f"status must be one of {sorted(STATUSES)}")
        if not isinstance(self.evidence, str) or not isinstance(self.detail, str):
            raise ContractError("evidence and detail must be strings")
        _paths(self.changed_paths, "changed_paths")
        if not isinstance(self.findings, tuple) or any(
            not isinstance(item, Mapping)
            or set(item) != {"content"}
            or not isinstance(item.get("content"), str)
            or not item["content"]
            for item in self.findings
        ):
            raise ContractError("findings must contain only non-empty content objects")
        if self.receipt is not None and not isinstance(self.receipt, Mapping):
            raise ContractError("receipt must be an object or null")
        if (self.patch_ref is None) != (self.patch_sha256 is None):
            raise ContractError("patch_ref and patch_sha256 must be present together")
        if self.patch_ref is not None:
            _string(self.patch_ref, "patch_ref")
            if self.patch_sha256 is None or HEX64_RE.fullmatch(self.patch_sha256) is None:
                raise ContractError("patch_sha256 must be a SHA-256 digest")
        if self.status == "available" and not self.evidence:
            raise ContractError("available result requires non-empty evidence")
        if self.changed_paths and self.patch_ref is None:
            raise ContractError("changed paths require a patch artifact")
        if self.status != "available" and (
            self.changed_paths or self.patch_ref is not None or self.receipt is not None
        ):
            raise ContractError("non-available result cannot carry execution proof or a patch")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> HarnessResult:
        expected = {
            "schema",
            "request_id",
            "engine_id",
            "variant",
            "status",
            "evidence",
            "evidence_sha256",
            "findings",
            "receipt",
            "changed_paths",
            "patch_ref",
            "patch_sha256",
            "detail",
            "authority",
        }
        _closed(data, expected, "harness result")
        if data.get("schema") != RESULT_SCHEMA or data.get("authority") != AUTHORITY:
            raise ContractError("harness result schema or authority is invalid")
        evidence = data.get("evidence")
        if not isinstance(evidence, str):
            raise ContractError("evidence must be a string")
        evidence_sha256 = data.get("evidence_sha256")
        expected_digest = hashlib.sha256(evidence.encode("utf-8")).hexdigest()
        if evidence_sha256 != expected_digest:
            raise ContractError("evidence_sha256 does not match evidence")
        findings = data.get("findings")
        if not isinstance(findings, list):
            raise ContractError("findings must be a list")
        receipt = data.get("receipt")
        if receipt is not None and not isinstance(receipt, Mapping):
            raise ContractError("receipt must be an object or null")
        changed_paths = _paths(data.get("changed_paths"), "changed_paths")
        patch_ref = data.get("patch_ref")
        patch_sha256 = data.get("patch_sha256")
        detail = data.get("detail")
        if patch_ref is not None and not isinstance(patch_ref, str):
            raise ContractError("patch_ref must be a string or null")
        if patch_sha256 is not None and not isinstance(patch_sha256, str):
            raise ContractError("patch_sha256 must be a string or null")
        if not isinstance(detail, str):
            raise ContractError("detail must be a string")
        return cls(
            request_id=_id(data.get("request_id"), "request_id"),
            engine_id=_id(data.get("engine_id"), "engine_id"),
            variant=_id(data.get("variant"), "variant"),
            status=_string(data.get("status"), "status"),
            evidence=evidence,
            findings=tuple(findings),
            receipt=dict(receipt) if receipt is not None else None,
            changed_paths=changed_paths,
            patch_ref=patch_ref,
            patch_sha256=patch_sha256,
            detail=detail,
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["findings"] = [dict(item) for item in self.findings]
        value["receipt"] = dict(self.receipt) if self.receipt is not None else None
        value["changed_paths"] = list(self.changed_paths)
        value["evidence_sha256"] = hashlib.sha256(self.evidence.encode("utf-8")).hexdigest()
        return value
