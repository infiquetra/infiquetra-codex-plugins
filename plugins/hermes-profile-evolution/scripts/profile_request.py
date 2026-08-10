#!/usr/bin/env python3
"""Thin Codex adapter for Team Mimir custody and Hermes profile dialogue."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER_CONFORMANCE = PLUGIN_ROOT / "conformance/profile-change-classifier.v1.json"
COMMAND_CONFORMANCE = PLUGIN_ROOT / "conformance/profile-request-cli.v1.json"
PROFILE_EVOLUTION_OPT_IN = Path("profile-governance/conformance/profile-change-classifier.v1.json")
MAX_INPUT_BYTES = 32_768
MAX_PATHS = 128
MAX_PATH_BYTES = 512
# The producer's loopback transport allows 30 seconds. Leave enough room for
# process startup and error serialization so this adapter never preempts that
# bounded producer result.
COMMAND_TIMEOUT_SECONDS = 45
CLASSIFIER_TIMEOUT_SECONDS = 5
PROFILE_RE = re.compile(r"^[a-z][a-z0-9-]+$")
SECRET_RE = re.compile(
    r"(?i)(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?:api[_-]?key|password|secret|token)\s*[:=]\s*[\"']?[A-Za-z0-9+/=_-]{12,})"
)
ACTOR_FIELDS = {"actor_kind", "actor_id", "verification"}
ACTOR_FIELDS_WITH_SOURCE = ACTOR_FIELDS | {"source_event_digest"}
ACTOR_KINDS = {"operator", "harness", "profile", "external_agent"}
ACTOR_VERIFICATIONS = {"verified", "claimed"}
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")


class AdapterError(ValueError):
    """Input or producer behavior is incompatible with the adapter contract."""


def _load_contract(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdapterError("producer conformance contract is unavailable") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema_version", value.get("fixture_version")) != 1
    ):
        raise AdapterError("producer conformance contract is incompatible")
    return value


def _read_bounded_json() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise AdapterError("standard input exceeds the adapter limit")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError("standard input must contain one JSON object") from exc
    if not isinstance(value, dict):
        raise AdapterError("standard input must contain one JSON object")
    return value


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _command_contract() -> dict[str, Any]:
    value = _load_contract(COMMAND_CONFORMANCE)
    if set(value) != {
        "artifact",
        "cases",
        "contracts",
        "producer",
        "proposal_envelope",
        "schema_version",
    }:
        raise AdapterError("producer command conformance contract is incompatible")
    return value


def _limits() -> dict[str, Any]:
    limits = _command_contract().get("contracts", {}).get("limits")
    if not isinstance(limits, dict):
        raise AdapterError("producer command limits are unavailable")
    return limits


def _bounded_text(value: object, limit_name: str, *, label: str) -> str:
    limit = _limits().get(limit_name)
    if not isinstance(limit, dict):
        raise AdapterError(f"producer {label} limit is unavailable")
    minimum = limit.get("min_non_whitespace_characters", limit.get("min_characters"))
    maximum = limit.get("max_characters")
    if (
        not isinstance(value, str)
        or not isinstance(minimum, int)
        or not isinstance(maximum, int)
        or len(value) > maximum
        or len(value.strip()) < minimum
    ):
        raise AdapterError(f"{label} is missing or outside producer bounds")
    if SECRET_RE.search(value):
        raise AdapterError(f"{label} contains secret-bearing material")
    return value


def _reject_secret_strings(value: object, *, label: str) -> None:
    """Reject secret-shaped strings without returning or logging their contents."""

    if isinstance(value, str):
        if SECRET_RE.search(value):
            raise AdapterError(f"{label} contains secret-bearing material")
        return
    if isinstance(value, list):
        for item in value:
            _reject_secret_strings(item, label=label)
        return
    if isinstance(value, dict):
        for item in value.values():
            _reject_secret_strings(item, label=label)


def _validate_actor(value: object, *, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) not in (ACTOR_FIELDS, ACTOR_FIELDS_WITH_SOURCE):
        raise AdapterError(f"{label} fields do not match the closed producer schema")
    kind = value.get("actor_kind")
    actor_id = value.get("actor_id")
    verification = value.get("verification")
    actor_limit = _limits().get("delegation_actor_id")
    if not isinstance(actor_limit, dict):
        raise AdapterError("producer delegation actor limit is unavailable")
    minimum = actor_limit.get("min_characters")
    maximum = actor_limit.get("max_characters")
    if (
        kind not in ACTOR_KINDS
        or verification not in ACTOR_VERIFICATIONS
        or not isinstance(actor_id, str)
        or not isinstance(minimum, int)
        or not isinstance(maximum, int)
        or not minimum <= len(actor_id) <= maximum
    ):
        raise AdapterError(f"{label} is invalid")
    _reject_secret_strings(value, label=label)
    source_digest = value.get("source_event_digest")
    if source_digest is not None and (
        not isinstance(source_digest, str) or not DIGEST_RE.fullmatch(source_digest)
    ):
        raise AdapterError(f"{label} source event digest is invalid")
    if kind == "profile" and verification == "verified":
        raise AdapterError("direct proposals cannot claim verified profile identity")
    return {key: str(item) for key, item in value.items()}


def _validate_delegation_chain(value: object) -> list[dict[str, str]]:
    chain_limit = _limits().get("delegation_chain")
    if not isinstance(chain_limit, dict):
        raise AdapterError("producer delegation chain limit is unavailable")
    minimum = chain_limit.get("min_items")
    maximum = chain_limit.get("max_items")
    if (
        not isinstance(value, list)
        or not isinstance(minimum, int)
        or not isinstance(maximum, int)
        or not minimum <= len(value) <= maximum
    ):
        raise AdapterError("delegation chain is outside producer bounds")
    return [_validate_actor(hop, label="delegation hop") for hop in value]


def validate_target(value: object) -> str:
    target = _bounded_text(value, "profile_name", label="target")
    if not PROFILE_RE.fullmatch(target) or target in {"default", "custom"}:
        raise AdapterError("target must be a named Hermes profile")
    return target


def validate_paths(value: object) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > MAX_PATHS:
        raise AdapterError("paths must be a bounded non-empty list")
    paths: list[str] = []
    for item in value:
        if (
            not isinstance(item, str)
            or not item
            or len(item.encode("utf-8")) > MAX_PATH_BYTES
            or Path(item).is_absolute()
            or ".." in Path(item).parts
            or "\x00" in item
        ):
            raise AdapterError("paths must be safe repository-relative values")
        paths.append(Path(item).as_posix())
    if len(paths) != len(set(paths)):
        raise AdapterError("paths must be unique")
    return paths


def validate_references(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_PATHS:
        raise AdapterError("evidence references must be a bounded list")
    references: list[str] = []
    for item in value:
        if (
            not isinstance(item, str)
            or not item
            or len(item.encode("utf-8")) > MAX_PATH_BYTES
            or Path(item).is_absolute()
            or ".." in Path(item).parts
            or SECRET_RE.search(item)
        ):
            raise AdapterError("evidence references must be safe repository-relative values")
        references.append(Path(item).as_posix())
    if len(references) != len(set(references)):
        raise AdapterError("evidence references must be unique")
    return references


def resolve_team_mimir_root(cwd: str) -> Path:
    configured = os.environ.get("HERMES_TEAM_MIMIR_ROOT")
    candidates = [Path(configured)] if configured else [Path(cwd), *Path(cwd).parents]
    for candidate in candidates:
        root = candidate.resolve()
        if (
            (root / "profiles").is_dir()
            and (root / "constitution.md").is_file()
            and (root / "deploy/team_profiles.yml").is_file()
            and (root / PROFILE_EVOLUTION_OPT_IN).is_file()
        ):
            return root
    raise AdapterError("working directory is not a recognized Team Mimir repository")


def _classifier_contract_facts() -> tuple[set[str], set[str], set[tuple[str, str]]]:
    contract = _load_contract(CLASSIFIER_CONFORMANCE)
    cases = contract.get("cases")
    if set(contract) != {"cases", "classifier_schema_version", "fixture_version"} or not isinstance(
        cases, list
    ):
        raise AdapterError("producer classifier conformance contract is incompatible")
    report_keys: set[str] | None = None
    path_keys: set[str] | None = None
    pairs: set[tuple[str, str]] = set()
    for case in cases:
        expected = case.get("expected") if isinstance(case, dict) else None
        if not isinstance(expected, dict):
            raise AdapterError("producer classifier conformance case is incompatible")
        report_keys = report_keys or set(expected)
        if set(expected) != report_keys:
            raise AdapterError("producer classifier conformance report shape drifted")
        category, disposition = expected.get("category"), expected.get("disposition")
        if isinstance(category, str) and isinstance(disposition, str):
            pairs.add((category, disposition))
        verdicts = expected.get("paths")
        if not isinstance(verdicts, list) or not verdicts:
            raise AdapterError("producer classifier conformance path shape drifted")
        for verdict in verdicts:
            if not isinstance(verdict, dict):
                raise AdapterError("producer classifier conformance path shape drifted")
            path_keys = path_keys or set(verdict)
            if set(verdict) != path_keys:
                raise AdapterError("producer classifier conformance path shape drifted")
            category, disposition = verdict.get("category"), verdict.get("disposition")
            if isinstance(category, str) and isinstance(disposition, str):
                pairs.add((category, disposition))
    assert report_keys is not None and path_keys is not None
    return report_keys, path_keys, pairs


def validate_classifier_report(value: object, expected_paths: list[str]) -> dict[str, Any]:
    report_keys, path_keys, pairs = _classifier_contract_facts()
    if not isinstance(value, dict) or set(value) != report_keys or value.get("schema_version") != 1:
        raise AdapterError("ownership classifier returned an incompatible response")
    pair = (value.get("category"), value.get("disposition"))
    if pair not in pairs:
        raise AdapterError("ownership classifier returned an incompatible response")
    verdicts = value.get("paths")
    if not isinstance(verdicts, list) or len(verdicts) != len(expected_paths):
        raise AdapterError("ownership classifier returned an incompatible response")
    actual_paths: list[str] = []
    for verdict in verdicts:
        if not isinstance(verdict, dict) or set(verdict) != path_keys:
            raise AdapterError("ownership classifier returned an incompatible response")
        if (verdict.get("category"), verdict.get("disposition")) not in pairs:
            raise AdapterError("ownership classifier returned an incompatible response")
        if not all(isinstance(verdict.get(key), str) and verdict[key] for key in path_keys):
            raise AdapterError("ownership classifier returned an incompatible response")
        actual_paths.append(verdict["path"])
    if actual_paths != expected_paths:
        raise AdapterError("ownership classifier returned paths outside the request")
    if not all(isinstance(value.get(key), str) and value[key] for key in ("owner", "reason")):
        raise AdapterError("ownership classifier returned an incompatible response")
    return value


def classify_paths(paths: list[str], root: Path) -> dict[str, Any]:
    classifier = root / "scripts/classify_profile_change.py"
    if not classifier.is_file():
        raise AdapterError("ownership classifier is unavailable")
    try:
        result = subprocess.run(
            [sys.executable, str(classifier), "--root", str(root), "--schema-version", "1", *paths],
            cwd=root,
            capture_output=True,
            timeout=CLASSIFIER_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise AdapterError("ownership classifier did not complete") from exc
    if result.returncode != 0 or len(result.stdout) > MAX_INPUT_BYTES:
        raise AdapterError("ownership classifier did not complete")
    try:
        report = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError("ownership classifier returned an incompatible response") from exc
    return validate_classifier_report(report, paths)


def _run_hermes(
    arguments: list[str], payload: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["hermes", "profile-request", *arguments],
            input=payload,
            capture_output=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise AdapterError("Hermes profile-request service is unavailable") from exc


def _case(case_id: str) -> dict[str, Any]:
    for case in _command_contract().get("cases", []):
        if isinstance(case, dict) and case.get("case_id") == case_id:
            return case
    raise AdapterError(f"producer command case `{case_id}` is unavailable")


def _parse_json_sequence(raw: bytes) -> list[Any]:
    if len(raw) > MAX_INPUT_BYTES:
        raise AdapterError("Hermes profile-request returned oversized output")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AdapterError("Hermes profile-request returned unexpected output") from exc
    decoder = json.JSONDecoder()
    values: list[Any] = []
    index = 0
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index == len(text):
            break
        try:
            value, index = decoder.raw_decode(text, index)
        except json.JSONDecodeError as exc:
            raise AdapterError("Hermes profile-request returned unexpected output") from exc
        values.append(value)
    if not values:
        raise AdapterError("Hermes profile-request returned unexpected output")
    return values


def _project_shape(value: object, example: object) -> object:
    if isinstance(example, dict):
        if not isinstance(value, dict) or not set(example) <= set(value):
            raise AdapterError("Hermes profile-request returned unexpected output")
        return {key: _project_shape(value[key], child) for key, child in example.items()}
    if isinstance(example, list):
        if not isinstance(value, list) or len(value) != len(example):
            raise AdapterError("Hermes profile-request returned unexpected output")
        return [_project_shape(child, sample) for child, sample in zip(value, example, strict=True)]
    if isinstance(example, bool):
        matches = isinstance(value, bool)
    elif isinstance(example, int):
        matches = isinstance(value, int) and not isinstance(value, bool)
    else:
        matches = isinstance(value, type(example))
    if not matches:
        raise AdapterError("Hermes profile-request returned unexpected output")
    return value


def _validated_output(
    case_id: str,
    result: subprocess.CompletedProcess[bytes],
    *,
    target: str | None = None,
    proposal_id: str | None = None,
    revision_digest: str | None = None,
) -> list[Any]:
    if result.returncode != 0:
        raise AdapterError("Hermes profile-request did not complete")
    values = _parse_json_sequence(result.stdout)
    expected = _case(case_id).get("expected", {}).get("stdout_json")
    if not isinstance(expected, list):
        raise AdapterError("Hermes profile-request returned unexpected output")
    projected = _project_shape(values, expected)
    if not isinstance(projected, list):
        raise AdapterError("Hermes profile-request returned unexpected output")
    values = projected
    summary = values[-1]
    if target is not None and (not isinstance(summary, dict) or summary.get("target") != target):
        raise AdapterError("Hermes profile-request returned a mismatched target")
    if proposal_id is not None and (
        not isinstance(summary, dict) or summary.get("proposal_id") != proposal_id
    ):
        raise AdapterError("Hermes profile-request returned a mismatched proposal")
    if revision_digest is not None and (
        not isinstance(summary, dict) or summary.get("proposal_revision_digest") != revision_digest
    ):
        raise AdapterError("Hermes profile-request returned a mismatched revision")
    return values


def doctor(target: str) -> dict[str, Any]:
    result = _run_hermes(["doctor", "--target", validate_target(target)])
    values = _parse_json_sequence(result.stdout) if result.returncode == 0 else []
    required = _command_contract().get("contracts", {}).get("doctor_fields")
    if (
        len(values) != 1
        or not isinstance(required, list)
        or not isinstance(values[0], dict)
        or set(values[0]) != set(required)
        or values[0].get("target") != target
        or not all(values[0].get(key) is True for key in set(required) - {"target"})
    ):
        raise AdapterError("Hermes profile-request is unavailable or incompatible")
    return values[0]


def build_envelope(target: str, intent: str, evidence: list[str]) -> dict[str, Any]:
    target = validate_target(target)
    intent = _bounded_text(intent, "intent", label="intent")
    references = validate_references(evidence)
    hop = {"actor_kind": "harness", "actor_id": "codex", "verification": "claimed"}
    body = {
        "schema_version": 1,
        "target": target,
        "requester": hop,
        "delegation_chain": [hop],
        "intent": intent,
        "evidence_references": references,
    }
    revision = hashlib.sha256(_canonical(body)).hexdigest()
    envelope = {
        **body,
        "record_type": "proposal_envelope",
        "proposal_id": f"proposal-{revision[:16]}",
        "revision_digest": revision,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    fields = _command_contract().get("contracts", {}).get("proposal_fields")
    if not isinstance(fields, list) or set(envelope) != set(fields):
        raise AdapterError("producer proposal envelope contract is incompatible")
    return envelope


def validate_proposal(value: object) -> dict[str, Any]:
    _reject_secret_strings(value, label="proposal")
    fields = _command_contract().get("contracts", {}).get("proposal_fields")
    if not isinstance(value, dict) or not isinstance(fields, list) or set(value) != set(fields):
        raise AdapterError("proposal fields do not match the producer contract")
    if value.get("schema_version") != 1 or value.get("record_type") != "proposal_envelope":
        raise AdapterError("proposal schema version or record type is unsupported")
    validate_target(value.get("target"))
    _validate_actor(value.get("requester"), label="requester")
    _validate_delegation_chain(value.get("delegation_chain"))
    _bounded_text(value.get("intent"), "intent", label="intent")
    validate_references(value.get("evidence_references"))
    if len(_canonical(value)) > MAX_INPUT_BYTES:
        raise AdapterError("proposal exceeds the adapter limit")
    for field in ("proposal_id", "revision_digest", "created_at"):
        if not isinstance(value.get(field), str) or not value[field]:
            raise AdapterError(f"proposal {field} is invalid")
    if not DIGEST_RE.fullmatch(value["revision_digest"]):
        raise AdapterError("proposal revision digest is invalid")
    body = {
        key: value[key]
        for key in (
            "schema_version",
            "target",
            "requester",
            "delegation_chain",
            "intent",
            "evidence_references",
        )
    }
    if hashlib.sha256(_canonical(body)).hexdigest() != value["revision_digest"]:
        raise AdapterError("proposal revision digest is invalid")
    try:
        datetime.fromisoformat(value["created_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdapterError("proposal created_at is invalid") from exc
    return value


def suggest(target: str, request: dict[str, Any], *, cwd: str) -> dict[str, Any]:
    if set(request) != {"schema_version", "intent", "paths", "evidence_references"}:
        raise AdapterError("suggest request fields do not match the closed adapter schema")
    if request.get("schema_version") != 1:
        raise AdapterError("suggest request schema version is unsupported")
    paths = validate_paths(request.get("paths"))
    report = classify_paths(paths, resolve_team_mimir_root(cwd))
    if report["disposition"] == "normal_merge":
        return {"action": "ordinary_repository_edit", "classification": report}
    dialogue_verdicts = [
        verdict
        for verdict in report["paths"]
        if verdict["category"] == "profile_owned_behavior"
        and verdict["disposition"] == "target_request"
    ]
    dialogue_owners = {verdict["owner"] for verdict in dialogue_verdicts}
    unsupported_verdicts = [
        verdict
        for verdict in report["paths"]
        if verdict not in dialogue_verdicts and verdict["disposition"] != "normal_merge"
    ]
    if unsupported_verdicts or not dialogue_verdicts:
        return {"action": "non_dialogue_disposition", "classification": report}
    if len(dialogue_owners) != 1:
        raise AdapterError(
            "request names multiple profile owners; submit one separate request per target"
        )
    classified_target = validate_target(next(iter(dialogue_owners)))
    caller_target = validate_target(target)
    if caller_target != classified_target:
        raise AdapterError("caller target does not match the classified profile owner")
    envelope = build_envelope(
        classified_target, request.get("intent"), request.get("evidence_references")
    )
    doctor(classified_target)
    values = _validated_output(
        "suggest",
        _run_hermes(["suggest"], _canonical(envelope)),
        target=envelope["target"],
        proposal_id=envelope["proposal_id"],
        revision_digest=envelope["revision_digest"],
    )
    return {"action": "hermes_dialogue", "classification": report, "response": values}


def continue_dialogue(action: str, request: dict[str, Any]) -> dict[str, Any]:
    expected = {"schema_version", "proposal"}
    if action == "reply":
        expected.add("message")
    if set(request) != expected or request.get("schema_version") != 1:
        raise AdapterError(f"{action} request fields do not match the closed adapter schema")
    _reject_secret_strings(request, label=f"{action} request")
    proposal = validate_proposal(request.get("proposal"))
    target = validate_target(proposal.get("target"))
    doctor(target)
    arguments = [action]
    if action == "reply":
        arguments.extend(
            ["--message", _bounded_text(request.get("message"), "reply_message", label="reply")]
        )
    values = _validated_output(
        action,
        _run_hermes(arguments, _canonical(proposal)),
        target=target,
        proposal_id=proposal["proposal_id"],
        revision_digest=proposal["revision_digest"],
    )
    return {"action": "hermes_dialogue", "response": values}


def status(proposal_id: str, revision: str, target: str) -> list[Any]:
    target = validate_target(target)
    opaque = _limits().get("opaque_identifier", {})
    minimum, maximum = opaque.get("min_characters"), opaque.get("max_characters")
    if (
        not isinstance(minimum, int)
        or not isinstance(maximum, int)
        or not minimum <= len(proposal_id) <= maximum
        or not re.fullmatch(r"[a-f0-9]{64}", revision)
    ):
        raise AdapterError("status identifiers are invalid")
    return _validated_output(
        "status",
        _run_hermes(
            ["status", "--proposal-id", proposal_id, "--revision", revision, "--target", target]
        ),
        target=target,
        revision_digest=revision,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    suggest_parser = commands.add_parser("suggest")
    suggest_parser.add_argument("target")
    commands.add_parser("reply")
    commands.add_parser("resume")
    doctor_parser = commands.add_parser("doctor")
    doctor_parser.add_argument("target")
    status_parser = commands.add_parser("status")
    status_parser.add_argument("--proposal-id", required=True)
    status_parser.add_argument("--revision", required=True)
    status_parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "doctor":
            output: object = doctor(args.target)
        elif args.action == "status":
            output = status(args.proposal_id, args.revision, args.target)
        elif args.action == "suggest":
            output = suggest(args.target, _read_bounded_json(), cwd=os.getcwd())
        else:
            output = continue_dialogue(args.action, _read_bounded_json())
    except AdapterError as exc:
        print(f"[hermes-profile-evolution] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
