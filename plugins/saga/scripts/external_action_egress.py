#!/usr/bin/env python3
"""Credential-safe outbound payload sanitizer for external actions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from external_action_contract import digest


PRIVATE_KEY = re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY(?: BLOCK)?-----")
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
CREDENTIAL_KEY = re.compile(
    r"(?i)^(?:api[_-]?key|access[_-]?token|auth[_-]?token|bearer[_-]?token|token|password|secret|client[_-]?secret|private[_-]?key|jwt)$"
)
PATTERNS = (
    ("bearer-token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}")),
    ("slack-token", re.compile(r"\bxox[a-zA-Z]-[A-Za-z0-9-]{8,}\b")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("github-token", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{16,}")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("assignment-secret", re.compile(r"(?i)\b(?:token|password|secret|api[_-]?key)\s*[:=]\s*[^\s,;]{8,}")),
)


@dataclass(frozen=True, slots=True)
class EgressResult:
    payload: Any | None
    detections: tuple[str, ...]
    blocked: bool
    payload_sha256: str | None


def sanitize(value: Any) -> EgressResult:
    detections: list[str] = []
    blocked = False

    def visit(item: Any) -> Any:
        nonlocal blocked
        if isinstance(item, str):
            if PRIVATE_KEY.search(item):
                detections.append("private-key")
                blocked = True
                return "<blocked:private-key>"
            if JWT.search(item):
                detections.append("jwt")
                blocked = True
                return "<blocked:jwt>"
            sanitized_text = item
            for name, pattern in PATTERNS:
                if pattern.search(sanitized_text):
                    detections.append(name)
                    sanitized_text = pattern.sub(f"<redacted:{name}>", sanitized_text)
            return sanitized_text
        if isinstance(item, list):
            return [visit(child) for child in item]
        if isinstance(item, tuple):
            return [visit(child) for child in item]
        if isinstance(item, dict):
            sanitized_mapping: dict[str, Any] = {}
            for key, child in item.items():
                name = str(key)
                if CREDENTIAL_KEY.fullmatch(name):
                    detections.append(f"credential-key:{name.lower()}")
                    blocked = True
                    sanitized_mapping[name] = "<blocked:credential>"
                else:
                    sanitized_mapping[name] = visit(child)
            return sanitized_mapping
        if item is None or isinstance(item, (bool, int, float)):
            return item
        raise TypeError(f"unsupported outbound payload type: {type(item).__name__}")

    sanitized = visit(value)
    unique = tuple(sorted(set(detections)))
    if blocked:
        return EgressResult(None, unique, True, None)
    return EgressResult(sanitized, unique, False, digest(sanitized))
