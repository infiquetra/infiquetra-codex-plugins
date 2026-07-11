#!/usr/bin/env python3
"""Codex-safe workflow-generation rules shared by Saga execution-spec emitters.

This module owns evidence-shape and intent-ordering rules only. It does not spawn children,
activate Claude Workflow, or grant external-engine output gate authority.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

ENGINE_INTENTS = ("offload", "second-opinion", "divergence")

JS_VERIFIER_PROMPT_HELPER = r'''function __verifierPrompt(basePrompt, unitResult) {
  var rendered;
  try {
    rendered = JSON.stringify(unitResult, null, 2);
  } catch (err) {
    rendered = String(unitResult);
  }
  var repoLine = (typeof REPO === "string")
    ? `PRIMARY REPO PATH: ${REPO}`
    : "PRIMARY REPO PATH: not declared by this workflow";
  return `${basePrompt}

VERIFIER VISIBILITY PROTOCOL:
${repoLine}
- Capture the primary checkout SHA with: git -C <primary repo path> rev-parse HEAD
- Inspect that checkout read-only. Never checkout, reset, clean, or mutate the primary tree.
- For uncommitted work, inspect git -C <primary repo path> status --short and diff output.
- Read named untracked output files directly from the primary checkout when needed.
- Return examined_sha as the SHA whose tracked content you inspected. If evidence is insufficient,
  return a structured refutation explaining the visibility gap; never return prose-only success.

UNIT RESULT INPUT (authoritative structured evidence):
${rendered}`;
}'''


def verifier_schema() -> dict[str, object]:
    """Closed required core for one independent verifier verdict."""

    return {
        "type": "object",
        "properties": {
            "refuted": {"type": "array"},
            "upheld": {"type": "array"},
            "verifier_identity": {"type": "string"},
            "fallback_depth": {"type": "integer", "minimum": 0},
            "examined_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
        },
        "required": [
            "refuted",
            "upheld",
            "verifier_identity",
            "fallback_depth",
            "examined_sha",
        ],
        "additionalProperties": True,
    }


def merge_engine_intents(intents: Iterable[str | None]) -> str | None:
    """Return the strongest declared external-engine intent without order dependence."""

    values = [value for value in intents if value is not None]
    if not values:
        return None
    invalid = sorted(set(values).difference(ENGINE_INTENTS))
    if invalid:
        raise ValueError(f"unknown engine intent(s): {invalid}")
    return max(values, key=ENGINE_INTENTS.index)


def external_engine_marker(
    *,
    engine: str | None,
    capability: str | None,
    intent: str | None,
) -> str | None:
    """Render a non-authoritative, deterministic selector marker for generated evidence."""

    if engine is not None and capability is not None:
        raise ValueError("engine and capability are mutually exclusive")
    if engine is None and capability is None:
        if intent is not None:
            raise ValueError("engine intent requires an engine or capability selector")
        return None
    selected_intent = intent or "offload"
    if selected_intent not in ENGINE_INTENTS:
        raise ValueError(f"unknown engine intent {selected_intent!r}")
    key, value = ("engine", engine) if engine is not None else ("capability", capability)
    return f"{key}={value} intent={selected_intent} authority=advisory-only"


def valid_verifier_verdict(value: object) -> bool:
    """Python mirror of the generated verifier completeness predicate."""

    if not isinstance(value, Mapping):
        return False
    return (
        isinstance(value.get("refuted"), list)
        and isinstance(value.get("upheld"), list)
        and isinstance(value.get("verifier_identity"), str)
        and bool(value["verifier_identity"])
        and isinstance(value.get("fallback_depth"), int)
        and not isinstance(value.get("fallback_depth"), bool)
        and value["fallback_depth"] >= 0
        and isinstance(value.get("examined_sha"), str)
        and len(value["examined_sha"]) == 40
        and all(char in "0123456789abcdef" for char in value["examined_sha"])
    )


def render_fallback_tier_marker(reporters: Iterable[Mapping[str, Any]]) -> str:
    """Name only verifier identities that actually used a fallback profile rung."""

    fragments: list[str] = []
    for reporter in reporters:
        depth = reporter.get("fallback_depth", 0)
        if isinstance(depth, bool) or not isinstance(depth, int) or depth <= 0:
            continue
        identity = reporter.get("verifier_identity") or "unknown-verifier"
        fragments.append(f"fallback tier {depth} ({identity})")
    return "" if not fragments else " — " + "; ".join(fragments)
