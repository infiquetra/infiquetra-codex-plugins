"""Closed compatibility vocabulary for the Team Execution package migration.

Verified Workflows serializers write only the canonical values in this module.
Readers may accept the exact legacy aliases and can tell that an alias was used.
Unknown keys and values fail closed so compatibility cannot grow accidentally.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Mapping


class WorkflowVocabularyError(ValueError):
    """Raised when a compatibility key or value is outside the closed registry."""


@dataclass(frozen=True, slots=True)
class VocabularyEntry:
    """One canonical write value and the exact legacy values accepted by readers."""

    canonical: str
    legacy: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        values = (self.canonical, *self.legacy)
        if not self.canonical or any(not value for value in values):
            raise ValueError("workflow vocabulary values must be non-empty")
        if len(values) != len(set(values)):
            raise ValueError("workflow vocabulary values must be unique within an entry")


@dataclass(frozen=True, slots=True)
class ParsedVocabulary:
    """A normalized reader result with explicit legacy provenance."""

    key: str
    source: str
    canonical: str
    is_legacy: bool


class WorkflowVocabularyConflict(WorkflowVocabularyError):
    """Raised when canonical and legacy locations are both present."""


PLUGIN_ID: Final = "plugin.id"
DISPLAY_NAME: Final = "plugin.display-name"
RUN_SKILL: Final = "skill.run"
APPSEC_AUDIT_SKILL: Final = "skill.appsec-audit"
NAMESPACED_RUN_SKILL: Final = "skill.namespaced-run"
NAMESPACED_APPSEC_AUDIT_SKILL: Final = "skill.namespaced-appsec-audit"
SAGA_MODE: Final = "saga.workflow-mode"
PLAN_HEADING: Final = "plan.workflow-heading"
PLAN_ANCHOR: Final = "plan.workflow-anchor"
REPO_STATE_ROOT: Final = "state.repo-root"
USER_STATE_ROOT: Final = "state.user-root-prefix"
REPO_CONFIG_FILE: Final = "config.repo-file"
GIT_SNAPSHOT_PREFIX: Final = "git.snapshot-prefix"
SUBAGENT_VEHICLE: Final = "receipt.vehicle.subagent"
INLINE_VEHICLE: Final = "receipt.vehicle.inline"
PRODUCER_KIND: Final = "receipt.producer-kind"
EVIDENCE_REF: Final = "evidence.ref-key"
MANAGED_AGENT_MARKER: Final = "agent.managed-marker"


_ENTRIES = {
    PLUGIN_ID: VocabularyEntry("verified-workflows", ("team-execution",)),
    DISPLAY_NAME: VocabularyEntry("Verified Workflows", ("Team Execution",)),
    RUN_SKILL: VocabularyEntry("run", ("team-execution",)),
    APPSEC_AUDIT_SKILL: VocabularyEntry("appsec-audit"),
    NAMESPACED_RUN_SKILL: VocabularyEntry(
        "verified-workflows:run",
        ("team-execution:team-execution",),
    ),
    NAMESPACED_APPSEC_AUDIT_SKILL: VocabularyEntry(
        "verified-workflows:appsec-audit",
        ("team-execution:appsec-audit",),
    ),
    SAGA_MODE: VocabularyEntry("verified-workflow", ("team-execution",)),
    PLAN_HEADING: VocabularyEntry("## Workflow Structure", ("## Team Structure",)),
    PLAN_ANCHOR: VocabularyEntry("#workflow-structure", ("#team-structure",)),
    REPO_STATE_ROOT: VocabularyEntry(
        ".codex/verified-workflows/",
        (".codex/team-execution/",),
    ),
    USER_STATE_ROOT: VocabularyEntry(
        "~/.codex/verified-workflows/state/",
        ("~/.codex/team-execution/state/",),
    ),
    REPO_CONFIG_FILE: VocabularyEntry(
        ".verified-workflows.json",
        (".team-execution.json",),
    ),
    GIT_SNAPSHOT_PREFIX: VocabularyEntry(
        "refs/verified-workflows/snapshots/",
        ("refs/team-execution/snapshots/",),
    ),
    SUBAGENT_VEHICLE: VocabularyEntry(
        "verified-workflow-subagent",
        ("team-execution-delegated",),
    ),
    INLINE_VEHICLE: VocabularyEntry(
        "verified-workflow-inline",
        ("team-execution-serial",),
    ),
    PRODUCER_KIND: VocabularyEntry("verified-workflow", ("team-execution",)),
    EVIDENCE_REF: VocabularyEntry("verified_workflow_ref", ("team_execution_ref",)),
    MANAGED_AGENT_MARKER: VocabularyEntry(
        '# managed_by = "infiquetra-codex-plugins/verified-workflows"',
        ('# managed_by = "infiquetra-codex-plugins/team-execution"',),
    ),
}

REGISTRY: Final[Mapping[str, VocabularyEntry]] = MappingProxyType(_ENTRIES)


def entry(key: str) -> VocabularyEntry:
    """Return one registry entry or fail closed for an unknown category."""

    try:
        return REGISTRY[key]
    except KeyError as exc:
        raise WorkflowVocabularyError(f"unknown workflow vocabulary key: {key!r}") from exc


def parse(key: str, value: str) -> ParsedVocabulary:
    """Read a canonical or exact legacy value and retain its provenance."""

    if not isinstance(value, str) or not value:
        raise WorkflowVocabularyError(f"workflow vocabulary value for {key!r} must be non-empty")
    spec = entry(key)
    if value == spec.canonical:
        return ParsedVocabulary(key, value, spec.canonical, False)
    if value in spec.legacy:
        return ParsedVocabulary(key, value, spec.canonical, True)
    raise WorkflowVocabularyError(
        f"unsupported workflow vocabulary value for {key!r}: {value!r}"
    )


def emit(key: str, value: str | None = None) -> str:
    """Validate an optional input and always emit the canonical write value."""

    spec = entry(key)
    if value is not None:
        parse(key, value)
    return spec.canonical


def legacy_values(key: str) -> tuple[str, ...]:
    """Return the immutable, explicitly allowlisted reader aliases for ``key``."""

    return entry(key).legacy


def parse_prefix(key: str, value: str) -> ParsedVocabulary:
    """Normalize a path/ref prefix while preserving the suffix and legacy provenance.

    Registry prefixes end in ``/``. That boundary prevents lookalike values such as
    ``.codex/team-execution-old/`` from being accepted as legacy state.
    """

    if not isinstance(value, str) or not value:
        raise WorkflowVocabularyError(f"workflow vocabulary value for {key!r} must be non-empty")
    spec = entry(key)
    prefixes = ((spec.canonical, False), *((legacy, True) for legacy in spec.legacy))
    for prefix, is_legacy in prefixes:
        if not prefix.endswith("/"):
            raise WorkflowVocabularyError(f"workflow vocabulary key {key!r} is not a prefix")
        if value == prefix or value.startswith(prefix):
            suffix = value[len(prefix) :]
            if "\x00" in suffix or "\\" in suffix or ".." in suffix.split("/"):
                raise WorkflowVocabularyError(
                    f"unsafe workflow vocabulary suffix for {key!r}: {suffix!r}"
                )
            return ParsedVocabulary(
                key=key,
                source=value,
                canonical=f"{spec.canonical}{suffix}",
                is_legacy=is_legacy,
            )
    raise WorkflowVocabularyError(
        f"unsupported workflow vocabulary prefix for {key!r}: {value!r}"
    )


def emit_prefix(key: str, value: str | None = None) -> str:
    """Validate an optional path/ref and emit it under the canonical prefix."""

    spec = entry(key)
    if value is None:
        if not spec.canonical.endswith("/"):
            raise WorkflowVocabularyError(f"workflow vocabulary key {key!r} is not a prefix")
        return spec.canonical
    return parse_prefix(key, value).canonical


def select_present(key: str, values: tuple[str, ...]) -> ParsedVocabulary | None:
    """Select one exact identity location and reject mixed old/new state.

    Callers pass only locations that actually exist. Duplicate observations of the same
    identity are harmless; observing canonical and legacy identities together is a hard stop.
    """

    parsed = tuple(parse(key, value) for value in values)
    identities = {item.is_legacy for item in parsed}
    if len(identities) > 1:
        raise WorkflowVocabularyConflict(
            f"canonical and legacy workflow locations both exist for {key!r}"
        )
    return parsed[0] if parsed else None


def select_present_prefix(key: str, values: tuple[str, ...]) -> ParsedVocabulary | None:
    """Select one prefix identity and reject mixed canonical/legacy locations."""

    parsed = tuple(parse_prefix(key, value) for value in values)
    identities = {item.is_legacy for item in parsed}
    if len(identities) > 1:
        raise WorkflowVocabularyConflict(
            f"canonical and legacy workflow prefix locations both exist for {key!r}"
        )
    return parsed[0] if parsed else None
