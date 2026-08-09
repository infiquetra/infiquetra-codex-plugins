#!/usr/bin/env python3
"""Prove the minimal Codex V2 runtime identity boundary with the active login."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import stat
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugins" / "verified-workflows"
PLUGIN_SCRIPTS = PLUGIN_ROOT / "scripts"


class RuntimeProofError(RuntimeError):
    """Raised when proof inputs are unsafe, incomplete, or contradict runtime truth."""


def _reject_external_fleet_commons_root() -> None:
    """Refuse an out-of-repository Fleet Core before anything imports the renderer.

    This ran inside ``harness_sha256`` in an earlier draft, which was far too late to matter:
    cross-review supplied an external ``codex_model_catalog`` module that executed at import time
    and deleted ``FLEET_COMMONS_ROOT`` from the environment, after which the digest computed over
    the repository's own files and passed unchanged. A guard that the code it guards against can
    run before is not a guard, so it runs at module scope, above the imports.

    Refusing is the right response rather than hashing the external location: hashing whatever a
    caller points at would silently widen the approved instrument to cover code no one reviewed,
    which is the opposite of what a frozen harness digest is for.
    """

    external_fleet = os.environ.get("FLEET_COMMONS_ROOT")
    if not external_fleet:
        return
    resolved = Path(external_fleet).expanduser().resolve()
    if resolved != (REPO_ROOT / "plugins" / "fleet-core").resolve():
        raise RuntimeProofError(
            "FLEET_COMMONS_ROOT points outside this repository, so the renderer would load "
            "code the harness digest does not cover; unset it before producing a receipt"
        )


_reject_external_fleet_commons_root()


def _load_pinned(name: str, path: Path) -> Any:
    """Import a harness module from ITS PATH, never from ``sys.path`` resolution.

    Name-based import cannot be trusted to load the file the harness digest covers. The previous
    draft guarded `sys.path` conditionally -- ``if str(PLUGIN_SCRIPTS) not in sys.path`` -- so
    when ``PYTHONPATH`` already contained the repository directory somewhere later in the list,
    the insertion was skipped and an external directory earlier in the list won. Cross-review
    executed a foreign ``render_codex_agents`` that way while ``harness_sha256()`` went on
    returning the frozen digest, because the digest reads files from disk and the interpreter had
    loaded something else.

    Loading by path removes the question. Whatever ``sys.path`` says, the module object here is
    built from the bytes at ``path`` -- which are the bytes the digest covers.
    """

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeProofError(f"harness module {name} is not loadable from {path.name}")
    module = importlib.util.module_from_spec(spec)
    # Registered before execution so a module importing itself by name resolves to this object
    # rather than triggering a second, path-unchecked import.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# `fleet_commons_shim` resolves its own siblings relative to this directory, so the directory
# still belongs on the path; the load above is what decides which file each module comes from.
if str(PLUGIN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PLUGIN_SCRIPTS))

# The shim FIRST. `render_codex_agents` imports `fleet_commons_shim` by name at its own import
# time, so path-loading the renderer first still let an external shim win the name race -- the
# renderer was loaded from the right file and then pulled in the wrong dependency. Registering the
# shim in `sys.modules` from its path beforehand means the renderer's own import resolves to it.
_load_pinned("fleet_commons_shim", PLUGIN_SCRIPTS / "fleet_commons_shim.py")
renderer = _load_pinned("render_codex_agents", PLUGIN_SCRIPTS / "render_codex_agents.py")
profile_sync = _load_pinned("sync_codex_agents", PLUGIN_SCRIPTS / "sync_codex_agents.py")

_SCRIPTS = REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

CODEX_TARGET_VERSION = _load_pinned(
    "codex_target_version", _SCRIPTS / "codex_target_version.py"
).CODEX_TARGET_VERSION
_pin_module = _load_pinned("proof_harness_pin", _SCRIPTS / "proof_harness_pin.py")
HARNESS_FILES = _pin_module.HARNESS_FILES
PROOF_CASES = _pin_module.PROOF_CASES
RUNTIME_PROOF_HARNESS_SHA256 = _load_pinned(
    "proof_harness_sha256", _SCRIPTS / "proof_harness_sha256.py"
).RUNTIME_PROOF_HARNESS_SHA256

DEFAULT_SNAPSHOT = REPO_ROOT / "docs" / "validation" / "codex-runtime-capability-snapshot.json"
MAX_BYTES = 4 * 1024 * 1024
MAX_NEW_ROLLOUTS = 16
TERMINAL_MARKER = "V2_PROFILE_CHILD_OK"
ROOT_MARKER = "V2_PROFILE_ROOT_OK"
PARENT_ONLY_MARKER = "V2_PROFILE_PARENT_ONLY_CONTEXT"
TASK_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
CODEX_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
SECRET_KEY = re.compile(r"(?i)(token|secret|password|credential|authorization|api[_-]?key|auth_json)")
SECRET_VALUE = re.compile(
    r"(?i)(?:\bsk-[A-Za-z0-9_-]{8,}|\bgh[pousr]_[A-Za-z0-9]{8,}|"
    r"\bBearer\s+[A-Za-z0-9._~-]{8,}|\beyJ[A-Za-z0-9_-]{8,}\."
    r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})"
)


def harness_sha256() -> str:
    """Composite digest over every file that can change what a receipt says.

    Each file contributes its repository-relative path as well as its bytes, so moving a harness
    file is a change rather than a no-op. The value is compared against the frozen pin in
    ``proof_harness_pin`` before any receipt is accepted.
    """

    # Checked again here, not only at import. The import-time call is what actually protects the
    # renderer; this one catches an environment mutated after import, which is cheap to refuse.
    _reject_external_fleet_commons_root()
    digest = hashlib.sha256()
    for relative in HARNESS_FILES:
        path = REPO_ROOT / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_read_regular(path, f"harness file {relative}"))
        digest.update(b"\0")
    return digest.hexdigest()


def validate_harness_identity(payload: Mapping[str, Any], where: str) -> None:
    """Refuse a receipt or proof that carries no harness digest, or one that is not the pin."""

    observed = payload.get("harness_sha256")
    if not isinstance(observed, str) or not observed:
        raise RuntimeProofError(f"{where} carries no harness digest")
    if observed != RUNTIME_PROOF_HARNESS_SHA256:
        raise RuntimeProofError(
            f"{where} harness digest {observed[:12]} is not the frozen "
            f"{RUNTIME_PROOF_HARNESS_SHA256[:12]}; rerun the affected proofs"
        )


RECEIPT_REQUIRED_FIELDS = (
    "case_id",
    "harness_sha256",
    "codex_cli_version_observed",
    "agent_path",
    "agent_role",
    "model",
    "reasoning_effort",
    "model_provider",
    "approval_policy",
    "sandbox_mode",
    "permission_profile",
    "multi_agent_version",
    "parent_thread_present",
    "terminal_status",
    "terminal_marker_observed",
    "parent_context_marker_observed",
    "operations_observed",
)


def validate_receipt_identity(payload: object, where: str) -> None:
    """Refuse anything that is not one parsed rollout receipt this harness produced.

    Shape, then values, then the three harness-stamped identities. Presence alone was not
    enough: a dictionary carrying every required key set to ``None`` satisfied the field list
    while asserting nothing, so "has the keys" was standing in for "says something".
    """

    if not isinstance(payload, Mapping):
        raise RuntimeProofError(f"{where} is not a receipt object")
    missing = [field for field in RECEIPT_REQUIRED_FIELDS if field not in payload]
    if missing:
        raise RuntimeProofError(f"{where} is missing receipt fields {missing}")
    empty = [
        field
        for field in RECEIPT_REQUIRED_FIELDS
        if payload.get(field) is None or payload.get(field) == ""
    ]
    if empty:
        raise RuntimeProofError(f"{where} carries empty receipt fields {empty}")
    for field in ("parent_thread_present", "terminal_marker_observed"):
        if not isinstance(payload.get(field), bool):
            raise RuntimeProofError(f"{where} field {field} must be a boolean")
    if not isinstance(payload.get("operations_observed"), list):
        raise RuntimeProofError(f"{where} field operations_observed must be a list")
    validate_harness_identity(payload, where)
    validate_case_identity(payload, where)
    observed = payload.get("codex_cli_version_observed")
    if not isinstance(observed, str) or not CODEX_VERSION_RE.fullmatch(observed):
        raise RuntimeProofError(f"{where} records no observed Codex version")


LIVE_PROJECTION_REQUIRED_FIELDS = (
    "case_id",
    "harness_sha256",
    "codex_cli_version_observed",
    "catalog",
    "root",
    "child",
    "profile_sha256",
    # The digests of the two rollout receipts this probe parsed. A rollout is the one artefact
    # only a real turn produces, so these are what separate "agrees with configuration" from
    # "a turn happened".
    "root_rollout_sha256",
    "child_rollout_sha256",
)
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
SANDBOX_MODES = frozenset({"read-only", "workspace-write", "danger-full-access"})
# Every field the published projection carries, with the kind of value it must hold. Presence
# checking is what let a fabricated projection through: `{"fabricated": true}` is a non-empty
# mapping with no null values, so it satisfied every check the previous draft made.
LIVE_ROOT_FIELDS: dict[str, str] = {
    "model": "text",
    "reasoning_effort": "text",
    "model_provider": "text",
    "approval_policy": "text",
    "sandbox_mode": "text",
    "permission_profile": "nullable-text",
    "multi_agent_version": "text",
    "operations_observed": "text-list",
}
LIVE_CHILD_FIELDS: dict[str, str] = {
    "agent_path": "text",
    "agent_role": "text",
    "model": "text",
    "reasoning_effort": "text",
    "model_provider": "text",
    "approval_policy": "text",
    "sandbox_mode": "text",
    "permission_profile": "nullable-text",
    "multi_agent_version": "text",
    "history_mode": "text",
    "parent_context_marker_observed": "flag",
    "terminal_status": "text",
    "terminal_marker_observed": "flag",
}
LIVE_CATALOG_FIELDS: dict[str, str] = {
    "source": "text",
    "sha256": "digest",
    "required_v2_models": "text-list",
    "luna_multi_agent_version": "nullable-text",
}
REQUIRED_ROOT_OPERATIONS = frozenset({"spawn_agent", "list_agents", "wait_agent"})
APPROVAL_POLICIES = frozenset({"never", "on-request", "on-failure", "untrusted"})
HISTORY_MODES = frozenset({"none", "legacy", "compact", "all"})


def _snapshot_document() -> dict[str, Any]:
    payload, _digest = _load_json(DEFAULT_SNAPSHOT, "capability snapshot")
    return payload


def known_collaboration_operations() -> frozenset[str]:
    """Operations the committed snapshot records, so an invented one cannot pass."""

    collaboration = _snapshot_document().get("collaboration")
    operations = collaboration.get("operations") if isinstance(collaboration, dict) else None
    if not isinstance(operations, list) or not operations:
        raise RuntimeProofError("capability snapshot records no collaboration operations")
    return frozenset(name for name in operations if isinstance(name, str) and name)


def known_model_providers() -> frozenset[str]:
    """Providers the rendered profiles actually name, plus the built-in Codex default."""

    providers = {"openai"}
    for path in sorted((PLUGIN_ROOT / "agents").glob("*.toml")):
        payload = tomllib.loads(_read_regular(path, "source profile", 1024 * 1024).decode("utf-8"))
        provider = payload.get("model_provider")
        if isinstance(provider, str) and provider:
            providers.add(provider)
    return frozenset(providers)


def _validate_closed_block(
    payload: Mapping[str, Any], fields: Mapping[str, str], where: str
) -> None:
    """Refuse a block whose keys are not exactly ``fields``, or whose values are the wrong kind.

    A closed key set is what makes fabrication hard: an invented block cannot pass by carrying
    an extra key, and cannot pass by omitting a real one either.
    """

    observed = set(payload)
    expected = set(fields)
    if observed != expected:
        extra = sorted(observed - expected)
        missing = sorted(expected - observed)
        raise RuntimeProofError(
            f"{where} keys do not match the published projection "
            f"(unexpected {extra}, missing {missing})"
        )
    for key, kind in fields.items():
        value = payload[key]
        if kind == "flag":
            if not isinstance(value, bool):
                raise RuntimeProofError(f"{where}.{key} must be a boolean")
        elif kind == "digest":
            if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
                raise RuntimeProofError(f"{where}.{key} must be a sha256 digest")
        elif kind == "text-list":
            if not isinstance(value, list) or not value:
                raise RuntimeProofError(f"{where}.{key} must be a non-empty list")
            if any(not isinstance(entry, str) or not entry for entry in value):
                raise RuntimeProofError(f"{where}.{key} must hold non-empty strings")
        elif kind == "nullable-text":
            if value is not None and (not isinstance(value, str) or not value):
                raise RuntimeProofError(f"{where}.{key} must be a non-empty string or null")
        elif not isinstance(value, str) or not value:
            raise RuntimeProofError(f"{where}.{key} must be a non-empty string")


def validate_live_projection(payload: object, where: str) -> None:
    """Refuse anything that is not the projection ``run_live_probe`` publishes.

    The published projection and one parsed rollout receipt are different objects that were both
    being called "the receipt". Validating the published shape against the parsed shape rejected
    every honest proof while accepting fabricated ones, which is the worst way round.

    Beyond shape, this binds the projection to bytes on disk. The child names a source profile,
    and the profile digest it publishes must be the digest of THAT profile's real bytes, with the
    model and effort to match. A fabricated projection therefore cannot claim ``supported``
    without the operator already holding a profile that says what it claims -- at which point it
    is not a fabrication.
    """

    if not isinstance(payload, Mapping):
        raise RuntimeProofError(f"{where} is not a live projection object")
    observed_fields = set(payload)
    expected_fields = set(LIVE_PROJECTION_REQUIRED_FIELDS)
    if observed_fields != expected_fields:
        extra = sorted(observed_fields - expected_fields)
        missing = sorted(expected_fields - observed_fields)
        raise RuntimeProofError(
            f"{where} keys do not match the published projection "
            f"(unexpected {extra}, missing {missing})"
        )
    for side, fields in (("root", LIVE_ROOT_FIELDS), ("child", LIVE_CHILD_FIELDS)):
        block = payload[side]
        if not isinstance(block, Mapping):
            raise RuntimeProofError(f"{where} carries no {side} identity")
        _validate_closed_block(block, fields, f"{where}.{side}")
        if block["multi_agent_version"] != "v2":
            raise RuntimeProofError(f"{where}.{side} does not report the V2 backend")
        if block["sandbox_mode"] not in SANDBOX_MODES:
            raise RuntimeProofError(f"{where}.{side}.sandbox_mode is not a Codex sandbox mode")
    catalog = payload["catalog"]
    if not isinstance(catalog, Mapping):
        raise RuntimeProofError(f"{where} carries no catalog identity")
    _validate_closed_block(catalog, LIVE_CATALOG_FIELDS, f"{where}.catalog")
    if catalog["source"] != "native-model-cache":
        raise RuntimeProofError(f"{where}.catalog does not name the native Codex model cache")
    # Bound to bytes, like the profile digest beside it. A shape-checked digest is a claim about
    # a catalog rather than a catalog: cross-review published an invented one and was believed.
    # The only caller is `run_live_probe` in this same invocation, so the cache it measured
    # seconds ago is the cache read here; a disagreement means the catalog proved against is gone.
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    # `_native_model_cache`, not `_load_json`. The plain reader accepts any JSON object, so an
    # empty `{}` cache whose real digest was published satisfied the binding while proving
    # nothing; this reader requires the named models to be present AND marked v2.
    _cache_path, live_catalog = _native_model_cache(codex_home, catalog["required_v2_models"])
    if catalog["sha256"] != live_catalog["sha256"]:
        raise RuntimeProofError(
            f"{where}.catalog.sha256 is not the digest of the model cache this run measured"
        )

    # The two rollout digests are recorded so a reader can tie the record back to the
    # receipts it was built from. They are not a gate: a local file proves nothing about
    # whether Codex ran, as the test fixture that writes two of them demonstrates.
    if payload["root_rollout_sha256"] == payload["child_rollout_sha256"]:
        raise RuntimeProofError(f"{where} names one rollout receipt as both root and child")
    for digest_field in ("profile_sha256", "root_rollout_sha256", "child_rollout_sha256"):
        value = payload[digest_field]
        if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
            raise RuntimeProofError(f"{where}.{digest_field} must be a sha256 digest")
    profile_sha256 = payload["profile_sha256"]

    root = payload["root"]
    child = payload["child"]
    # `issubset`, not `<`. The proper-subset form was backwards and inverted the whole check:
    # `["not_a_codex_operation"]` is not a proper subset of the required three, so the comparison
    # was false and an arbitrary operation list passed. Cross-review reached `supported` through
    # exactly this line.
    observed_operations = set(root["operations_observed"])
    if not REQUIRED_ROOT_OPERATIONS.issubset(observed_operations):
        missing = sorted(REQUIRED_ROOT_OPERATIONS - observed_operations)
        raise RuntimeProofError(
            f"{where}.root did not observe the required probe operations {missing}"
        )
    unknown_operations = sorted(observed_operations - known_collaboration_operations())
    if unknown_operations:
        raise RuntimeProofError(
            f"{where}.root reports operations Codex does not define: {unknown_operations}"
        )
    agent_path = child["agent_path"]
    if not agent_path.startswith("/root/") or agent_path == "/root/":
        raise RuntimeProofError(f"{where}.child.agent_path is not a spawned child path")

    # Type checks alone left every outcome field free. A projection could report an unfinished
    # child that never returned the contract marker and still be published as `supported`.
    if child["terminal_status"] != "completed":
        raise RuntimeProofError(f"{where}.child did not reach a completed terminal status")
    if child["terminal_marker_observed"] is not True:
        raise RuntimeProofError(f"{where}.child never returned the terminal contract marker")
    if child["parent_context_marker_observed"] is not False:
        raise RuntimeProofError(
            f"{where}.child observed the root-only marker, so its history was not bounded"
        )
    for side, block in (("root", root), ("child", child)):
        if block["approval_policy"] not in APPROVAL_POLICIES:
            raise RuntimeProofError(f"{where}.{side}.approval_policy is not a Codex policy")
        if block["model_provider"] not in known_model_providers():
            raise RuntimeProofError(
                f"{where}.{side}.model_provider is not a provider this repository configures"
            )
    if child["history_mode"] not in HISTORY_MODES:
        raise RuntimeProofError(f"{where}.child.history_mode is not a Codex history mode")

    # The binding. `agent_role` names a source profile; the published digest, model and effort
    # must be that profile's own. Cross-review reached `capability_outcome = supported` with
    # arbitrary values here, which is the strongest claim this script can make.
    expected_profile = _source_profile_expectation(child["agent_role"])
    if profile_sha256 != expected_profile["sha256"]:
        raise RuntimeProofError(
            f"{where}.profile_sha256 is not the digest of source profile "
            f"{child['agent_role']!r}"
        )
    for field in ("model", "reasoning_effort"):
        if child[field] != expected_profile[field]:
            raise RuntimeProofError(
                f"{where}.child.{field} disagrees with source profile {child['agent_role']!r}"
            )
    if child["model"] not in catalog["required_v2_models"]:
        raise RuntimeProofError(f"{where}.child.model is absent from the proven V2 catalog")
    if root["model"] not in catalog["required_v2_models"]:
        raise RuntimeProofError(f"{where}.root.model is absent from the proven V2 catalog")

    validate_harness_identity(payload, where)
    validate_case_identity(payload, where)
    observed = payload.get("codex_cli_version_observed")
    if not isinstance(observed, str) or not CODEX_VERSION_RE.fullmatch(observed):
        raise RuntimeProofError(f"{where} records no observed Codex version")


def validate_case_identity(payload: Mapping[str, Any], where: str) -> None:
    """Refuse a receipt that declares no case, or one this harness does not define."""

    case_id = payload.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise RuntimeProofError(f"{where} declares no proof case")
    if case_id not in PROOF_CASES:
        raise RuntimeProofError(
            f"{where} declares unknown proof case {case_id!r}; "
            f"expected one of {sorted(PROOF_CASES)}"
        )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_regular(path: Path, where: str, limit: int = MAX_BYTES) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RuntimeProofError(f"{where} is unreadable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > limit
        ):
            raise RuntimeProofError(f"{where} must be a bounded single-link regular file")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            len(content) > limit
            or len(content) != before.st_size
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise RuntimeProofError(f"{where} changed while it was read")
        return content
    finally:
        os.close(descriptor)


def _load_json(path: Path, where: str) -> tuple[dict[str, Any], str]:
    content = _read_regular(path, where)
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeProofError(f"{where} is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeProofError(f"{where} must be an object")
    return payload, _sha256(content)


def _native_model_cache(
    codex_home: Path, required_models: Sequence[str]
) -> tuple[Path, dict[str, Any]]:
    path = codex_home / "models_cache.json"
    payload, digest = _load_json(path, "native Codex model cache")
    rows = payload.get("models")
    if not isinstance(rows, list):
        raise RuntimeProofError("native Codex model cache lacks model rows")
    versions: dict[str, str | None] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeProofError("native Codex model cache has a malformed row")
        slug = row.get("slug")
        version = row.get("multi_agent_version")
        if isinstance(slug, str):
            versions[slug] = version if isinstance(version, str) else None
    required = sorted(set(required_models))
    if any(versions.get(model) != "v2" for model in required):
        raise RuntimeProofError("required model is not V2 in the native Codex model cache")
    return path, {
        "source": "native-model-cache",
        "sha256": digest,
        "required_v2_models": required,
        "luna_multi_agent_version": versions.get("gpt-5.6-luna"),
    }


def _reject_default_profile_input(path: Path, where: str) -> None:
    default = (Path.home() / ".codex").resolve(strict=False)
    candidate = path.expanduser().resolve(strict=False)
    if candidate == default or default in candidate.parents:
        raise RuntimeProofError(f"{where} must not read from the default Codex profile tree")


def _snapshot_projection(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    runtime = snapshot.get("runtime")
    collaboration = snapshot.get("collaboration")
    if not isinstance(runtime, dict) or not isinstance(collaboration, dict):
        raise RuntimeProofError("capability snapshot lacks required closed sections")
    version = runtime.get("codex_cli_version")
    if version != CODEX_TARGET_VERSION:
        raise RuntimeProofError(
            f"capability snapshot must target Codex {CODEX_TARGET_VERSION}, not {version!r}"
        )
    spawn = collaboration.get("spawn")
    expected_spawn_fields = {
        "available",
        "contract_version",
        "tool_namespace",
        "hide_spawn_agent_metadata",
        "request_fields",
        "response_fields",
        "default_fork_turns",
        "profile_selection_fork_turns",
        "per_child_agent_type",
        "per_child_model",
        "per_child_effort",
        "per_child_sandbox",
        "runtime_receipt_sources",
        "selection_readback_fields",
    }
    if not isinstance(spawn, dict) or set(spawn) != expected_spawn_fields:
        raise RuntimeProofError("capability snapshot V2 spawn schema is not closed")
    if (
        spawn["available"] is not True
        or spawn["contract_version"] != "v2"
        or spawn["tool_namespace"] != "collaboration"
        or spawn["hide_spawn_agent_metadata"] is not False
    ):
        raise RuntimeProofError("capability snapshot V2 selection contract drifted")
    expected_requests = [
        "agent_type",
        "fork_turns",
        "message",
        "model",
        "reasoning_effort",
        "task_name",
    ]
    expected_readback = [
        "agent_path",
        "agent_role",
        "model",
        "reasoning_effort",
        "model_provider",
        "approval_policy",
        "permission_profile",
        "sandbox_policy",
        "multi_agent_version",
    ]
    if spawn["request_fields"] != expected_requests:
        raise RuntimeProofError("capability snapshot V2 request fields drifted")
    if spawn["response_fields"] != ["agent_id", "nickname", "task_name"]:
        raise RuntimeProofError("capability snapshot V2 response fields drifted")
    if spawn["runtime_receipt_sources"] != ["session_meta", "turn_context"]:
        raise RuntimeProofError("capability snapshot V2 receipt sources drifted")
    if spawn["selection_readback_fields"] != expected_readback:
        raise RuntimeProofError("capability snapshot V2 readback fields drifted")
    if spawn["default_fork_turns"] != "all" or spawn[
        "profile_selection_fork_turns"
    ] != ["none", "positive-integer"]:
        raise RuntimeProofError("capability snapshot V2 context contract drifted")
    for field in ("per_child_agent_type", "per_child_model", "per_child_effort"):
        if spawn[field] is not True:
            raise RuntimeProofError(f"capability snapshot must enable {field}")
    if spawn["per_child_sandbox"] is not False:
        raise RuntimeProofError(
            f"Codex {CODEX_TARGET_VERSION} does not support per-child sandbox override"
        )
    operations = collaboration.get("operations")
    if operations != [
        "followup_task",
        "interrupt_agent",
        "list_agents",
        "send_message",
        "spawn_agent",
        "wait_agent",
    ]:
        raise RuntimeProofError("capability snapshot V2 operation inventory drifted")
    return {"version": version, "spawn": spawn, "operations": operations}


def _task_name_from_tool(name: object) -> str | None:
    if not isinstance(name, str) or not name:
        return None
    normalized = name.rsplit(".", 1)[-1].rsplit("__", 1)[-1]
    return normalized if normalized in {
        "spawn_agent",
        "send_message",
        "followup_task",
        "wait_agent",
        "interrupt_agent",
        "list_agents",
    } else None


def parse_rollout_receipt(
    content: bytes, *, case_id: str, codex_cli_version_observed: str
) -> dict[str, Any]:
    """Project one rollout into the allowlisted V2 identity and permission receipt.

    Three fields are stamped by the harness rather than read from the rollout, because the
    transcript knows none of them: which claim this receipt is evidence for, which instrument
    produced it, and which Codex build was observed. The observed version is a caller-supplied
    observation on purpose — KTD2 forbids a target version standing in for one.
    """

    if case_id not in PROOF_CASES:
        raise RuntimeProofError(f"unknown proof case {case_id!r}")
    if not CODEX_VERSION_RE.fullmatch(codex_cli_version_observed):
        raise RuntimeProofError(
            f"observed Codex version {codex_cli_version_observed!r} is not a version string"
        )

    meta: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    terminal = False
    terminal_marker = False
    operations: set[str] = set()
    for number, raw_line in enumerate(content.splitlines(), 1):
        try:
            row = json.loads(raw_line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeProofError(f"rollout line {number} is invalid JSON") from exc
        if not isinstance(row, dict):
            raise RuntimeProofError(f"rollout line {number} must be an object")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if row.get("type") == "session_meta":
            if meta is not None:
                raise RuntimeProofError("rollout repeats session_meta")
            meta = payload
        elif row.get("type") == "turn_context":
            context = payload
        elif row.get("type") == "event_msg" and payload.get("type") == "task_complete":
            terminal = True
            terminal_marker = payload.get("last_agent_message") == TERMINAL_MARKER
        elif row.get("type") == "response_item":
            operation = _task_name_from_tool(payload.get("name"))
            if operation is not None:
                operations.add(operation)
    if meta is None or context is None:
        raise RuntimeProofError("rollout lacks session_meta or turn_context")
    source = meta.get("source")
    spawn = {}
    if isinstance(source, dict):
        subagent = source.get("subagent")
        if isinstance(subagent, dict) and isinstance(subagent.get("thread_spawn"), dict):
            spawn = subagent["thread_spawn"]
    sandbox = context.get("sandbox_policy")
    sandbox_mode = sandbox.get("type") if isinstance(sandbox, dict) else sandbox
    permission = context.get("permission_profile")
    permission_kind = permission.get("type") if isinstance(permission, dict) else None
    receipt = {
        "case_id": case_id,
        "harness_sha256": harness_sha256(),
        "codex_cli_version_observed": codex_cli_version_observed,
        "session_id": meta.get("id"),
        "parent_thread_id": meta.get("parent_thread_id"),
        "parent_thread_present": isinstance(meta.get("parent_thread_id"), str),
        "agent_path": meta.get("agent_path", spawn.get("agent_path")),
        "agent_role": meta.get("agent_role", spawn.get("agent_role")),
        "model": context.get("model"),
        "reasoning_effort": context.get("effort"),
        "model_provider": meta.get("model_provider"),
        "approval_policy": context.get("approval_policy"),
        "sandbox_mode": sandbox_mode,
        "permission_profile": permission_kind,
        "multi_agent_version": context.get(
            "multi_agent_version", meta.get("multi_agent_version")
        ),
        "history_mode": meta.get("history_mode"),
        "parent_context_marker_observed": PARENT_ONLY_MARKER.encode() in content,
        "terminal_status": "completed" if terminal else "incomplete",
        "terminal_marker_observed": terminal_marker,
        "operations_observed": sorted(operations),
    }
    validate_sanitized_proof(receipt, "runtime_receipt")
    return receipt


def validate_runtime_receipt(
    receipt: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    validate_receipt_identity(receipt, "runtime receipt")
    fields = (
        "agent_path",
        "agent_role",
        "model",
        "reasoning_effort",
        "model_provider",
        "approval_policy",
        "sandbox_mode",
        "permission_profile",
        "multi_agent_version",
    )
    for field in fields:
        if receipt.get(field) != expected.get(field):
            raise RuntimeProofError(f"runtime receipt {field} mismatch")
    if not isinstance(receipt.get("permission_profile"), str):
        raise RuntimeProofError("runtime receipt permission_profile is missing")
    if receipt.get("parent_thread_present") is not True:
        raise RuntimeProofError("runtime receipt lacks parent thread identity")
    if receipt.get("terminal_status") != "completed":
        raise RuntimeProofError("runtime receipt is not terminal")
    if receipt.get("terminal_marker_observed") is not True:
        raise RuntimeProofError("runtime receipt terminal result mismatch")
    if receipt.get("parent_context_marker_observed") is not False:
        raise RuntimeProofError("runtime receipt inherited root-only context")


def _profile_facts() -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    for profile_id, runtime_agent_name in renderer.RUNTIME_AGENT_NAMES.items():
        path = PLUGIN_ROOT / "agents" / f"{runtime_agent_name}.toml"
        content = _read_regular(path, "managed profile", 1024 * 1024)
        facts.append(
            {
                "profile_id": profile_id,
                "runtime_agent_name": runtime_agent_name,
                "sha256": _sha256(content),
            }
        )
    if not facts:
        raise RuntimeProofError("managed profile source is empty")
    return facts


def _source_agent_facts() -> dict[str, Any]:
    expected = {
        f"{runtime_name}.toml" for runtime_name in renderer.RUNTIME_AGENT_NAMES.values()
    }
    try:
        children = list((PLUGIN_ROOT / "agents").iterdir())
    except OSError as exc:
        raise RuntimeProofError("source agent directory is unreadable") from exc
    actual = {child.name for child in children}
    if actual != expected:
        raise RuntimeProofError("source agent inventory drifted")
    files: list[dict[str, str]] = []
    for filename in sorted(expected):
        source_content = _read_regular(
            PLUGIN_ROOT / "agents" / filename, "source agent profile", 1024 * 1024
        )
        files.append({"filename": filename, "sha256": _sha256(source_content)})
    return {
        "location": "plugins/verified-workflows/agents",
        "regular_files_only": True,
        "files": files,
    }


def _source_profile_expectation(profile: str) -> dict[str, str]:
    if not TASK_NAME_RE.fullmatch(profile):
        raise RuntimeProofError("profile name is invalid")
    source = PLUGIN_ROOT / "agents" / f"{profile}.toml"
    source_bytes = _read_regular(source, "source profile", 1024 * 1024)
    try:
        payload = tomllib.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeProofError("source profile is invalid TOML") from exc
    model = payload.get("model")
    effort = payload.get("model_reasoning_effort")
    if not all(isinstance(value, str) for value in (model, effort)):
        raise RuntimeProofError("source profile lacks model or effort")
    if "sandbox_mode" in payload:
        raise RuntimeProofError("source profile duplicates inherited sandbox policy")
    return {
        "agent_role": profile,
        "model": model,
        "reasoning_effort": effort,
        "sandbox_mode": "read-only",
        "sha256": _sha256(source_bytes),
    }


def _rollout_paths(codex_home: Path) -> set[Path]:
    sessions = codex_home / "sessions"
    if not sessions.exists():
        return set()
    return set(sessions.glob("**/rollout-*.jsonl"))


def _thread_id_from_exec_output(stdout: bytes) -> str | None:
    for raw_line in stdout.splitlines():
        try:
            row = json.loads(raw_line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(row, dict) and row.get("type") == "thread.started":
            thread_id = row.get("thread_id")
            if isinstance(thread_id, str):
                return thread_id
    return None


def observed_codex_cli_version() -> str:
    """Read the installed binary's own version. Never the target version (KTD2)."""

    try:
        result = subprocess.run(
            ["codex", "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeProofError(f"could not observe the installed Codex version: {exc}") from exc
    if result.returncode:
        raise RuntimeProofError("the installed Codex binary did not report a version")
    text = result.stdout.decode("utf-8", "replace").strip()
    match = re.search(r"\d+\.\d+\.\d+", text)
    if match is None:
        raise RuntimeProofError(f"unparsed Codex version output {text[:64]!r}")
    return match.group(0)


def run_live_probe(
    *,
    profile: str = "review_high",
    task_name: str = "v2_profile_probe",
    case_id: str = "profile-identity",
) -> dict[str, Any]:
    if not TASK_NAME_RE.fullmatch(task_name):
        raise RuntimeProofError("task name is invalid")
    if case_id not in PROOF_CASES:
        raise RuntimeProofError(f"unknown proof case {case_id!r}")
    codex_cli_version = observed_codex_cli_version()
    expected_profile = _source_profile_expectation(profile)
    if expected_profile["sandbox_mode"] != "read-only":
        raise RuntimeProofError("the minimal V2 live probe requires a read-only profile")
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    if not codex_home.is_dir():
        raise RuntimeProofError("the active Codex home is unavailable")
    native_catalog_path, native_catalog = _native_model_cache(
        codex_home, ("gpt-5.6-sol", expected_profile["model"])
    )
    before = _rollout_paths(codex_home)
    prompt = (
        f"Retain this root-only marker and never include it in the child message: "
        f"{PARENT_ONLY_MARKER}. Use spawn_agent exactly once with task_name {task_name}, "
        f"agent_type {profile}, fork_turns none, model {expected_profile['model']}, and "
        f"reasoning_effort {expected_profile['reasoning_effort']}. Ask the child to return "
        f"exactly {TERMINAL_MARKER} and do nothing else. Use list_agents and wait_agent until "
        f"it completes. Return exactly {ROOT_MARKER}."
    )
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    with tempfile.TemporaryDirectory(prefix="verified-workflows-canary-") as raw_workspace:
        # macOS exposes its temporary root through /var, a symlink to /private/var.
        # Normalize it before applying the isolated-target symlink guard.
        workspace = Path(raw_workspace).resolve()
        agents_dir = workspace / ".codex" / "agents"
        agents_dir.parent.mkdir(mode=0o700)
        target = profile_sync.resolve_target(agents_dir, isolated_target=True)
        plan = profile_sync.build_plan(
            target,
            catalog_snapshot=DEFAULT_SNAPSHOT,
        )
        profile_sync.apply_sync(plan)
        argv = [
            "codex",
            "exec",
            "--json",
            "--ignore-rules",
            "--strict-config",
            "--skip-git-repo-check",
            "-C",
            str(workspace),
            "--sandbox",
            "read-only",
            "-m",
            "gpt-5.6-sol",
            "-c",
            'model_reasoning_effort="max"',
            "-c",
            "features.multi_agent=true",
            "-c",
            "features.multi_agent_v2=true",
            "-c",
            "agents.max_depth=2",
            "-c",
            f"model_catalog_json={json.dumps(str(native_catalog_path))}",
            prompt,
        ]
        try:
            result = subprocess.run(
                argv,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=240,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeProofError("Codex V2 live probe timed out") from exc
    if len(result.stdout) > MAX_BYTES or len(result.stderr) > MAX_BYTES:
        raise RuntimeProofError("Codex V2 live probe exceeded the output ceiling")
    if result.returncode:
        raise RuntimeProofError(f"Codex V2 live probe failed with exit {result.returncode}")
    after = _rollout_paths(codex_home)
    created = sorted(after - before)
    if not created:
        raise RuntimeProofError("Codex V2 live probe produced no rollout receipts")
    if len(created) > MAX_NEW_ROLLOUTS:
        raise RuntimeProofError("Codex V2 live probe produced too many rollout receipts")
    parsed = []
    for path in created:
        content = _read_regular(path, "live rollout")
        parsed.append(
            (
                parse_rollout_receipt(
                    content,
                    case_id=case_id,
                    codex_cli_version_observed=codex_cli_version,
                ),
                content,
            )
        )
    root_thread_id = _thread_id_from_exec_output(result.stdout)
    child_path = f"/root/{task_name}"
    children = [pair for pair in parsed if pair[0].get("agent_path") == child_path]
    if len(children) != 1:
        raise RuntimeProofError("Codex V2 live probe did not produce one canonical child")
    child, child_content = children[0]
    child_rollout_sha256 = _sha256(child_content)
    roots = [
        pair
        for pair in parsed
        if pair[0].get("session_id") == root_thread_id
        or (
            pair[0].get("parent_thread_id") is None
            and pair[0].get("agent_path") in {None, "/root"}
        )
    ]
    if len(roots) != 1:
        raise RuntimeProofError("Codex V2 live probe did not identify one root receipt")
    root, root_content = roots[0]
    root_rollout_sha256 = _sha256(root_content)
    expected = {
        **expected_profile,
        "agent_path": child_path,
        "model_provider": root.get("model_provider"),
        "approval_policy": root.get("approval_policy"),
        "permission_profile": root.get("permission_profile"),
        "multi_agent_version": "v2",
    }
    validate_runtime_receipt(child, expected)
    if child.get("parent_thread_id") != root.get("session_id"):
        raise RuntimeProofError("Codex V2 child is not attached to the observed root")
    if root.get("multi_agent_version") != "v2":
        raise RuntimeProofError("Codex V2 root receipt reports a different backend")
    if root.get("model") != "gpt-5.6-sol" or root.get("reasoning_effort") != "max":
        raise RuntimeProofError("Codex V2 root model or reasoning effort drifted")
    if root.get("approval_policy") != "never":
        raise RuntimeProofError("Codex V2 root approval policy drifted")
    if root.get("sandbox_mode") != expected_profile["sandbox_mode"]:
        raise RuntimeProofError("Codex V2 root permission does not match the profile ceiling")
    root_ops = set(root.get("operations_observed", []))
    required_operations = {"spawn_agent", "list_agents", "wait_agent"}
    if not required_operations.issubset(root_ops):
        raise RuntimeProofError("Codex V2 root receipt lacks required probe operations")
    # Both sides are validated, and they must agree. Validating only the child left the root's
    # digest, case and version unchecked, so a root parsed under a different instrument would
    # travel into the same proof unnoticed.
    for side, receipt in (("root", root), ("child", child)):
        validate_receipt_identity(receipt, f"live probe {side} receipt")
    disagreement = [
        field
        for field in ("case_id", "harness_sha256", "codex_cli_version_observed")
        if root[field] != child[field]
    ]
    if disagreement:
        raise RuntimeProofError(
            f"live probe root and child receipts disagree on {disagreement}"
        )
    return {
        # The three harness-stamped identities travel with the published projection. The parser
        # adds them and the projection used to drop them, so the proof promised a case, a
        # harness and an observed version that no reader could actually find in it.
        "case_id": child["case_id"],
        "harness_sha256": child["harness_sha256"],
        "codex_cli_version_observed": child["codex_cli_version_observed"],
        "catalog": native_catalog,
        "root": {
            key: root.get(key)
            for key in (
                "model",
                "reasoning_effort",
                "model_provider",
                "approval_policy",
                "sandbox_mode",
                "permission_profile",
                "multi_agent_version",
                "operations_observed",
            )
        },
        "child": {
            key: child.get(key)
            for key in (
                "agent_path",
                "agent_role",
                "model",
                "reasoning_effort",
                "model_provider",
                "approval_policy",
                "sandbox_mode",
                "permission_profile",
                "multi_agent_version",
                "history_mode",
                "parent_context_marker_observed",
                "terminal_status",
                "terminal_marker_observed",
            )
        },
        "profile_sha256": expected_profile["sha256"],
        "root_rollout_sha256": root_rollout_sha256,
        "child_rollout_sha256": child_rollout_sha256,
    }


LUNA_CANARY = REPO_ROOT / "docs" / "validation" / "codex-0147-luna-canary.json"
CANARY_VERDICTS = renderer.CANARY_VERDICTS


def validate_luna_canary(payload: Mapping[str, Any], where: str = "luna canary") -> None:
    """Refuse a canary receipt that claims more than it measured.

    The adjudication itself lives in the renderer, because the renderer is what acts on the
    verdict: a receipt this function accepted but the promotion gate rejected, or the reverse,
    would be two policies for one question -- the exact defect this round exists to remove. What
    stays here is the part the renderer has no reason to care about: a receipt published as
    evidence must also carry the observations it was read from.
    """

    if "observations" not in payload:
        raise RuntimeProofError(f"{where} is missing observations")
    try:
        renderer.parse_luna_canary_receipt(
            dict(payload),
            sha256=_sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()),
        )
    except renderer.RoleRegistryError as exc:
        raise RuntimeProofError(f"{where}: {exc}") from exc


PERMISSION_INHERITANCE = (
    REPO_ROOT / "docs" / "validation" / "codex-0147-permission-inheritance.json"
)
PERMISSION_CASES = frozenset(
    case for case in PROOF_CASES if case.startswith("turn-permission-")
)


def validate_permission_inheritance(
    payload: Mapping[str, Any], where: str = "permission inheritance"
) -> None:
    """Refuse a permission receipt with a missing row, a widening child, or borrowed authority.

    Any mismatch blocks source-ready, and a mismatch is never remediated by falling back to a
    different model (KTD6): a permission that did not hold is a fact about the runtime, not a
    reason to try a different one.
    """

    cases = payload.get("cases")
    if not isinstance(cases, Mapping):
        raise RuntimeProofError(f"{where} records no cases")
    observed_cases = set(cases)
    missing = sorted(PERMISSION_CASES - observed_cases)
    extra = sorted(observed_cases - PERMISSION_CASES)
    if missing:
        raise RuntimeProofError(f"{where} is missing matrix rows {missing}")
    if extra:
        raise RuntimeProofError(f"{where} records rows the harness does not define: {extra}")

    for case, record in cases.items():
        if not isinstance(record, Mapping):
            raise RuntimeProofError(f"{where} row {case!r} is not an object")
        expected, observed = record.get("expected"), record.get("observed")
        if not isinstance(expected, Mapping) or not isinstance(observed, Mapping):
            raise RuntimeProofError(f"{where} row {case!r} carries no expected/observed pair")
        if expected != observed:
            raise RuntimeProofError(
                f"{where} row {case!r} did not match its expected tuple; this blocks source-ready"
            )
        if record.get("matches") is not True:
            raise RuntimeProofError(f"{where} row {case!r} is not recorded as matching")

        # No widening, checked from the tuple rather than trusted from the summary.
        root_sandbox = observed.get("root_sandbox")
        child_sandbox = observed.get("child_sandbox")
        if root_sandbox == "read-only" and child_sandbox != "read-only":
            raise RuntimeProofError(
                f"{where} row {case!r} shows a child widening beyond a read-only parent; "
                f"this blocks source-ready"
            )

        # `auto_review` is a runtime approval reviewer and is never operator authority (R11).
        reviewers = record.get("approvals_reviewer")
        if not isinstance(reviewers, Mapping):
            raise RuntimeProofError(f"{where} row {case!r} records no approvals reviewer")
        for side, value in reviewers.items():
            if value == "auto_review":
                raise RuntimeProofError(
                    f"{where} row {case!r} records auto_review as the {side} reviewer; "
                    f"runtime approval is never operator approval"
                )


SKILL_RESOURCES = REPO_ROOT / "docs" / "validation" / "codex-0147-skill-resources.json"
SKILL_CASES = frozenset(case for case in PROOF_CASES if case.startswith("skill-"))
SKILL_STATUSES = frozenset({"proven", "blocked"})


def validate_skill_resources(payload: Mapping[str, Any], where: str = "skill resources") -> None:
    """Refuse a skill receipt that conflates the two mechanisms or overstates what it proved.

    Treating a host-installed reference as executor-backed is a repeat finding in this repository,
    so the mechanism is recorded per case and cross-checked against the mechanism block. A case
    cannot be `proven` while its mechanism is not.
    """

    mechanisms = payload.get("mechanisms")
    cases = payload.get("cases")
    if not isinstance(mechanisms, Mapping) or not isinstance(cases, Mapping):
        raise RuntimeProofError(f"{where} records no mechanisms or no cases")

    missing = sorted(SKILL_CASES - set(cases))
    extra = sorted(set(cases) - SKILL_CASES)
    if missing:
        raise RuntimeProofError(f"{where} is missing skill rows {missing}")
    if extra:
        raise RuntimeProofError(f"{where} records rows the harness does not define: {extra}")

    for name, block in mechanisms.items():
        if not isinstance(block, Mapping) or not isinstance(block.get("proven"), bool):
            raise RuntimeProofError(f"{where} mechanism {name!r} does not declare `proven`")
        if not block["proven"] and not block.get("reasons"):
            raise RuntimeProofError(
                f"{where} mechanism {name!r} is unproven with no reasons; an absent proof must "
                f"say what stopped it, or it reads as an oversight later"
            )

    for case, record in cases.items():
        if not isinstance(record, Mapping):
            raise RuntimeProofError(f"{where} row {case!r} is not an object")
        status, mechanism = record.get("status"), record.get("mechanism")
        if status not in SKILL_STATUSES:
            raise RuntimeProofError(
                f"{where} row {case!r} carries status {status!r}; expected one of "
                f"{sorted(SKILL_STATUSES)}"
            )
        if mechanism not in mechanisms:
            raise RuntimeProofError(f"{where} row {case!r} names unknown mechanism {mechanism!r}")
        # The conflation guard: a row cannot be proven through a mechanism that was not.
        if status == "proven" and not mechanisms[mechanism]["proven"]:
            raise RuntimeProofError(
                f"{where} row {case!r} is proven through {mechanism!r}, which this receipt "
                f"records as unproven"
            )
        # And an executor row may not borrow the host mechanism's proof.
        if case.startswith("skill-executor-") and mechanism != "executor-backed":
            raise RuntimeProofError(
                f"{where} row {case!r} is an executor row recorded against {mechanism!r}; "
                f"host-installed and executor-backed are different mechanisms"
            )


DISCOVERY_ROUTING = REPO_ROOT / "docs" / "validation" / "codex-0147-discovery-routing.json"
# The scopes Codex 0.147 defines. Pinned here so a receipt cannot quietly invent one, and so a
# scope added upstream shows up as a refusal rather than as silence.
SKILL_SCOPES = frozenset({"user", "repo", "system", "admin"})


def validate_discovery_routing(
    payload: Mapping[str, Any], where: str = "discovery routing"
) -> None:
    """Refuse a discovery receipt that reports a skill as run, or hides an unresolved skill.

    Two conflations are worth refusing by construction. A skill being listed is not a skill being
    executed, and a receipt that blurs them turns "the catalog offered this" into "this works".
    And a per-plugin row claiming everything resolved while still naming unresolved skills is the
    same overclaim in a smaller space.
    """

    for field in ("claim", "codex_cli_version_observed", "criteria", "isolated_discovery",
                  "scopes", "removal", "context_injection", "agent_profiles"):
        if field not in payload:
            raise RuntimeProofError(f"{where} is missing {field}")
    observed = payload["codex_cli_version_observed"]
    if not isinstance(observed, str) or not CODEX_VERSION_RE.fullmatch(observed):
        raise RuntimeProofError(f"{where} records no observed Codex version")

    criteria = payload["criteria"]
    if not isinstance(criteria, Mapping) or not criteria:
        raise RuntimeProofError(f"{where} declares no criteria")
    for name, entry in criteria.items():
        if not isinstance(entry, Mapping) or not isinstance(entry.get("measured"), bool):
            raise RuntimeProofError(f"{where} criterion {name!r} does not declare `measured`")
        if not entry["measured"] and not entry.get("reason"):
            raise RuntimeProofError(f"{where} criterion {name!r} is unmeasured with no reason")
    # Execution is the one thing an offline round cannot show. Recording it as measured would be
    # the offered-versus-executed conflation this receipt exists to keep straight.
    if criteria.get("skill-execution", {}).get("measured"):
        raise RuntimeProofError(
            f"{where} claims skill execution was measured; listing a skill is not running one"
        )

    discovery = payload["isolated_discovery"]
    if not isinstance(discovery, Mapping):
        raise RuntimeProofError(f"{where} records no isolated discovery")
    if discovery.get("listing_errors"):
        raise RuntimeProofError(
            f"{where} records listing errors: {discovery['listing_errors']}"
        )
    per_plugin = discovery.get("per_plugin")
    if not isinstance(per_plugin, Mapping) or not per_plugin:
        raise RuntimeProofError(f"{where} assesses no plugins")
    for plugin, row in per_plugin.items():
        if not isinstance(row, Mapping):
            raise RuntimeProofError(f"{where} plugin {plugin!r} is not an object")
        for field in ("skills_in_source", "skills_resolved", "all_resolved", "unresolved"):
            if field not in row:
                raise RuntimeProofError(f"{where} plugin {plugin!r} is missing {field}")
        if row["all_resolved"] and row["unresolved"]:
            raise RuntimeProofError(
                f"{where} plugin {plugin!r} claims everything resolved while naming "
                f"{row['unresolved']} as unresolved"
            )
        if row["all_resolved"] and row["skills_resolved"] != row["skills_in_source"]:
            raise RuntimeProofError(
                f"{where} plugin {plugin!r} claims everything resolved but resolved "
                f"{row['skills_resolved']} of {row['skills_in_source']}"
            )

    scopes = payload["scopes"]
    observed_scopes = set(scopes.get("observed_counts") or {})
    unknown = sorted(observed_scopes - SKILL_SCOPES)
    if unknown:
        raise RuntimeProofError(f"{where} reports scopes Codex 0.147 does not define: {unknown}")
    if not observed_scopes:
        raise RuntimeProofError(f"{where} observed no scope at all")

    injection = payload["context_injection"]
    canaries = injection.get("canaries")
    if not isinstance(canaries, Mapping) or len(canaries) < 2:
        raise RuntimeProofError(
            f"{where} needs at least two injection canaries; one absent marker on its own "
            f"cannot distinguish a withheld skill from a request that carried none"
        )
    if not any(row.get("injected") for row in canaries.values()):
        raise RuntimeProofError(
            f"{where} records no injected canary, so the absent ones are a null result"
        )

    profiles = payload["agent_profiles"]
    if profiles.get("separate_synchronisation_still_required") is not True:
        raise RuntimeProofError(
            f"{where} does not record that custom agent profiles still need their own sync"
        )


def build_proof(
    *,
    snapshot: dict[str, Any],
    snapshot_sha256: str,
    live: bool,
    runtime_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    projection = _snapshot_projection(snapshot)
    if live and runtime_receipt is None:
        raise RuntimeProofError("authenticated live proof requires a runtime receipt")
    elif live:
        # A non-null object is not evidence. Without this, any dictionary at all promoted a
        # proof to "supported" with live_invocation_performed true, which is the strongest
        # claim this script can make and the easiest to fabricate by accident.
        validate_live_projection(runtime_receipt, "live proof projection")
        outcome = "supported"
        reason = "current-session Codex V2 rollout attests isolated source profile and effective runtime fields"
    elif runtime_receipt is not None:
        raise RuntimeProofError("a runtime receipt requires --live")
    else:
        outcome = "diagnostic"
        reason = "source and configuration contract only; no live runtime receipt supplied"
    proof = {
        "schema_version": 2,
        "claim": "codex-v2-runtime-capability",
        "harness_sha256": harness_sha256(),
        "mode": "current-session-live" if runtime_receipt is not None else "dry-run",
        "capability_outcome": outcome,
        "reason": reason,
        "snapshot_sha256": snapshot_sha256,
        "codex_cli_version": projection["version"],
        "tool_namespace": projection["spawn"]["tool_namespace"],
        "spawn_request_fields": projection["spawn"]["request_fields"],
        "spawn_response_fields": projection["spawn"]["response_fields"],
        "runtime_readback_fields": projection["spawn"]["selection_readback_fields"],
        "operations": projection["operations"],
        "profiles": _profile_facts(),
        "source_profiles": _source_agent_facts(),
        "live_invocation_performed": runtime_receipt is not None,
        "runtime_receipt": runtime_receipt,
        "limitations": [
            f"Codex {CODEX_TARGET_VERSION} child permissions inherit the parent turn "
            "after profile loading",
            "this candidate canary covers one disposable read-only child",
            "requested spawn fields are never accepted as runtime identity without session_meta and turn_context",
        ],
    }
    validate_sanitized_proof(proof)
    validate_harness_identity(proof, "proof")
    return proof


def validate_sanitized_proof(payload: object, path: str = "proof", depth: int = 0) -> None:
    if depth > 8:
        raise RuntimeProofError(f"{path} exceeds the proof nesting ceiling")
    if isinstance(payload, dict):
        if len(payload) > 64:
            raise RuntimeProofError(f"{path} exceeds the proof object ceiling")
        for key, value in payload.items():
            if not isinstance(key, str) or SECRET_KEY.search(key):
                raise RuntimeProofError(f"{path} contains a secret-shaped field")
            validate_sanitized_proof(value, f"{path}.{key}", depth + 1)
    elif isinstance(payload, list):
        if len(payload) > 128:
            raise RuntimeProofError(f"{path} exceeds the proof list ceiling")
        for index, value in enumerate(payload):
            validate_sanitized_proof(value, f"{path}[{index}]", depth + 1)
    elif isinstance(payload, str):
        if (
            payload.startswith(("/Users/", "~", "file:"))
            or SECRET_KEY.search(payload)
            or SECRET_VALUE.search(payload)
        ):
            raise RuntimeProofError(f"{path} contains a path or secret-shaped value")
        if len(payload) > 512:
            raise RuntimeProofError(f"{path} exceeds the proof string ceiling")
    elif isinstance(payload, float) and not math.isfinite(payload):
        raise RuntimeProofError(f"{path} contains a non-finite number")
    elif payload is not None and not isinstance(payload, (bool, int, float)):
        raise RuntimeProofError(f"{path} contains an unsupported value")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--profile", default="review_high")
    parser.add_argument("--task-name", default="v2_profile_probe")
    parser.add_argument(
        "--case-id",
        default="profile-identity",
        choices=sorted(PROOF_CASES),
        help="which behavioural claim a live receipt is evidence for",
    )
    parser.add_argument(
        "--print-harness-sha256",
        action="store_true",
        help="print the composite harness digest and exit; use it to rotate the frozen pin",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    if args.print_harness_sha256:
        try:
            print(harness_sha256())
        except RuntimeProofError as exc:
            print(f"verified workflow runtime proof failed: {exc}", file=sys.stderr)
            return 1
        return 0
    try:
        _reject_default_profile_input(args.snapshot, "capability snapshot")
        snapshot, digest = _load_json(args.snapshot, "capability snapshot")
        receipt = None
        if args.live:
            receipt = run_live_probe(
                profile=args.profile,
                task_name=args.task_name,
                case_id=args.case_id,
            )
        proof = build_proof(
            snapshot=snapshot,
            snapshot_sha256=digest,
            live=args.live,
            runtime_receipt=receipt,
        )
    except RuntimeProofError as exc:
        print(f"verified workflow runtime proof failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(proof, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
