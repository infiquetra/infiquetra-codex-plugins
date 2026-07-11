#!/usr/bin/env python3
"""Scaffold and safely apply an OpenAI-compatible HTTP engine registry row."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
import tempfile
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from yaml.nodes import MappingNode, ScalarNode

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine_registry import (  # noqa: E402
    CAPABILITIES,
    COST_CLASSES,
    LATENCY_CLASSES,
    RATINGS,
    Registry,
    RegistryError,
)
from engine_registry_conformance import check_registry  # noqa: E402

DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "references" / "engine-registry.yaml"
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]*$")
_ENV_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
_REQUIRED_FIELDS = frozenset(
    {
        "transport",
        "engine_id",
        "variant",
        "base_url",
        "model",
        "auth_key_env",
        "context_window",
        "cost_speed_rank",
        "cost_class",
        "cost_per_token",
        "latency_class",
        "model_identity",
        "last_validated",
        "capability_profile",
        "prompting_protocol",
        "sources",
    }
)
_OPTIONAL_FIELDS = frozenset({"budget_ceiling_usd"})
BeforeReplace = Callable[[], None]


class OnboardingError(ValueError):
    """A provider spec or registry apply operation is unsafe."""


@dataclass(frozen=True)
class OnboardingResult:
    """Validated row, rendered fragment, and write disposition."""

    engine_key: str
    row: dict[str, Any]
    fragment: str
    applied: bool


def onboard(
    spec_path: Path | str,
    registry_path: Path | str = DEFAULT_REGISTRY,
    *,
    apply: bool = False,
    expected_sha256: str | None = None,
    repo_root: Path | str = DEFAULT_REPO_ROOT,
    before_replace: BeforeReplace | None = None,
) -> OnboardingResult:
    """Validate a provider spec and optionally insert its row atomically."""
    destination = _contained_registry_path(registry_path, repo_root)
    try:
        source = destination.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise OnboardingError(f"{destination}: registry must be UTF-8") from exc
    source_hash = _sha256(source)
    if apply:
        if expected_sha256 is None:
            raise OnboardingError("--apply requires the expected pre-write SHA-256")
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise OnboardingError("expected pre-write SHA-256 must be 64 lowercase hex characters")
        if expected_sha256 != source_hash:
            raise OnboardingError(
                f"{destination}: expected pre-write SHA-256 does not match current registry"
            )
    raw_registry = _load_registry_mapping(source, destination)
    spec = _load_spec(spec_path)
    existing = _equivalent_existing_row(spec, raw_registry)
    if existing is not None:
        return OnboardingResult(
            engine_key=f"{existing['engine_id']}/{existing['variant']}",
            row=existing,
            fragment=render_row(existing),
            applied=False,
        )
    row = build_row(spec, raw_registry)
    candidate = deepcopy(raw_registry)
    engines = candidate.get("engines")
    if not isinstance(engines, list):
        raise OnboardingError(f"{destination}: registry engines must be a list")
    engines.append(row)
    _validate_candidate(candidate)

    fragment = render_row(row)
    rendered = _insert_before_roles(source, fragment, destination)
    _validate_rendered(rendered, destination)

    if apply:
        _atomic_replace_if_unchanged(
            destination,
            rendered,
            expected_hash=expected_sha256,
            before_replace=before_replace,
        )
        _validate_applied_readback(destination, rendered)

    return OnboardingResult(
        engine_key=f"{row['engine_id']}/{row['variant']}",
        row=row,
        fragment=fragment,
        applied=apply,
    )


def _contained_registry_path(path: Path | str, repo_root: Path | str) -> Path:
    """Resolve one regular, single-link registry file inside the declared repository root."""

    root = Path(repo_root).resolve(strict=True)
    candidate = Path(path)
    if candidate.is_symlink():
        raise OnboardingError(f"{candidate}: registry target must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as exc:
        raise OnboardingError(f"{candidate}: registry target escapes the declared repository root") from exc
    if not resolved.is_file():
        raise OnboardingError(f"{candidate}: registry target must be a regular file")
    if resolved.stat().st_nlink != 1:
        raise OnboardingError(f"{candidate}: registry target must have exactly one hard link")
    return resolved


def _equivalent_existing_row(
    spec: dict[str, Any], registry: dict[str, Any]
) -> dict[str, Any] | None:
    """Return an existing byte-equivalent logical row so repeated apply is a no-op."""

    _validate_spec(spec)
    engines = registry.get("engines")
    if not isinstance(engines, list):
        raise OnboardingError("registry engines must be a list")
    matches = [
        entry
        for entry in engines
        if isinstance(entry, dict)
        and entry.get("engine_id") == spec["engine_id"]
        and entry.get("variant") == spec["variant"]
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise OnboardingError("registry contains duplicate rows for the requested engine variant")
    without_existing = deepcopy(registry)
    without_existing["engines"] = [entry for entry in engines if entry is not matches[0]]
    expected = build_row(spec, without_existing)
    if matches[0] != expected:
        key = f"{spec['engine_id']}/{spec['variant']}"
        raise OnboardingError(f"registry already contains a different engine variant {key!r}")
    return dict(matches[0])


def build_row(spec: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    """Build one fail-closed HTTP row from a validated provider spec."""
    _validate_spec(spec)
    engine_id = str(spec["engine_id"])
    variant = str(spec["variant"])
    key = f"{engine_id}/{variant}"
    raw_engines = registry.get("engines")
    if not isinstance(raw_engines, list):
        raise OnboardingError("registry engines must be a list")
    if any(
        isinstance(entry, dict)
        and entry.get("engine_id") == engine_id
        and entry.get("variant") == variant
        for entry in raw_engines
    ):
        raise OnboardingError(f"registry already contains engine variant {key!r}")

    first_for_engine = not any(
        isinstance(entry, dict) and entry.get("engine_id") == engine_id for entry in raw_engines
    )
    base_url = str(spec["base_url"]).rstrip("/")
    model = str(spec["model"])
    row: dict[str, Any] = {
        "engine_id": engine_id,
        "variant": variant,
        "substrate": "external",
        "egress_policy": "networked",
        "trust_tier": "probation",
        "default_for_engine": first_for_engine,
        "transport": "http",
        "invocation": {
            "via": "engine-bridge-http",
            "recipe": f"POST {base_url}/chat/completions ({model})",
            "write_capable": False,
            "base_url": base_url,
            "model": model,
            "effort": "default",
            "auth": {"mode": "bearer", "key_env": str(spec["auth_key_env"])},
        },
        "context_window": int(spec["context_window"]),
        "cost_speed_rank": int(spec["cost_speed_rank"]),
        "cost_per_token": deepcopy(spec["cost_per_token"]),
        "cost_class": str(spec["cost_class"]),
        "latency_class": str(spec["latency_class"]),
        "model_identity": str(spec["model_identity"]),
        "last_validated": str(spec["last_validated"]),
        "receipt_emitter": "http-bridge",
        "capability_profile": deepcopy(spec["capability_profile"]),
        "prompting_protocol": list(spec["prompting_protocol"]),
        "sources": deepcopy(spec["sources"]),
    }
    if spec["cost_class"] == "metered":
        row["budget_ceiling_usd"] = float(spec["budget_ceiling_usd"])
    return row


def render_row(row: dict[str, Any]) -> str:
    """Render one registry-list item without serializing the surrounding authored YAML."""
    block = yaml.safe_dump({"engines": [row]}, sort_keys=False, allow_unicode=False)
    prefix = "engines:\n"
    if not block.startswith(prefix):
        raise OnboardingError("could not render provider row under engines")
    body = block[len(prefix) :]
    return "".join(f"  {line}" if line.strip() else line for line in body.splitlines(keepends=True))


def _load_spec(path: Path | str) -> dict[str, Any]:
    spec_path = Path(path)
    try:
        source = spec_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise OnboardingError(f"{spec_path}: provider spec must be UTF-8") from exc
    try:
        raw = json.loads(
            source,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise OnboardingError(f"{spec_path}: malformed JSON: {exc.msg}") from exc
    if not isinstance(raw, dict):
        raise OnboardingError(f"{spec_path}: provider spec must be a JSON object")
    return dict(raw)


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OnboardingError(f"provider spec has duplicate JSON field {key!r}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise OnboardingError(f"provider spec contains non-finite JSON number {value!r}")


def _validate_spec(spec: dict[str, Any]) -> None:
    unknown = sorted(set(spec) - _REQUIRED_FIELDS - _OPTIONAL_FIELDS)
    if unknown:
        raise OnboardingError(f"provider spec has unknown field(s): {', '.join(unknown)}")
    missing = sorted(_REQUIRED_FIELDS - set(spec))
    if missing:
        raise OnboardingError(f"provider spec missing required field(s): {', '.join(missing)}")

    if spec["transport"] != "http":
        raise OnboardingError(
            "provider spec transport must be 'http'; CLI providers need a real wrapper"
        )
    _require_identifier(spec["engine_id"], "engine_id")
    _require_identifier(spec["variant"], "variant")
    _require_string(spec["model"], "model")
    _require_string(spec["model_identity"], "model_identity")
    _validate_base_url(spec["base_url"])
    if not isinstance(spec["auth_key_env"], str) or not _ENV_PATTERN.fullmatch(
        spec["auth_key_env"]
    ):
        raise OnboardingError("auth_key_env must be an uppercase environment-variable name")
    _require_positive_int(spec["context_window"], "context_window")
    _require_non_negative_int(spec["cost_speed_rank"], "cost_speed_rank")
    if spec["cost_class"] not in COST_CLASSES:
        raise OnboardingError(f"cost_class must be one of {COST_CLASSES}")
    if spec["latency_class"] not in LATENCY_CLASSES:
        raise OnboardingError(f"latency_class must be one of {LATENCY_CLASSES}")
    try:
        date.fromisoformat(str(spec["last_validated"]))
    except ValueError as exc:
        raise OnboardingError("last_validated must be an ISO date") from exc

    costs = spec["cost_per_token"]
    if not isinstance(costs, dict) or set(costs) != {"input_usd", "output_usd"}:
        raise OnboardingError("cost_per_token must contain exactly input_usd and output_usd")
    for field in ("input_usd", "output_usd"):
        _require_non_negative_number(costs[field], f"cost_per_token.{field}")
    if spec["cost_class"] == "metered":
        if "budget_ceiling_usd" not in spec:
            raise OnboardingError("metered provider spec requires budget_ceiling_usd")
        _require_non_negative_number(spec["budget_ceiling_usd"], "budget_ceiling_usd")
    elif "budget_ceiling_usd" in spec:
        raise OnboardingError("free provider spec must omit budget_ceiling_usd")
    if spec["cost_class"] == "free" and any(float(costs[field]) != 0.0 for field in costs):
        raise OnboardingError("free provider spec requires zero cost_per_token values")

    _validate_capabilities(spec["capability_profile"])
    _validate_string_list(spec["prompting_protocol"], "prompting_protocol")
    _validate_sources(spec["sources"])


def _validate_base_url(value: Any) -> None:
    url = _require_string(value, "base_url")
    parsed = urlsplit(url)
    if (
        any(character.isspace() for character in url)
        or parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise OnboardingError(
            "base_url must be an absolute HTTPS URL without credentials, query, or fragment"
        )


def _validate_capabilities(value: Any) -> None:
    if not isinstance(value, dict) or not value:
        raise OnboardingError("capability_profile must be a non-empty object")
    for capability, raw_claim in value.items():
        if capability not in CAPABILITIES:
            raise OnboardingError(f"capability_profile has unknown capability {capability!r}")
        if capability == "embedding":
            raise OnboardingError(
                "capability_profile cannot advertise embedding; the v1 scaffolder targets "
                "OpenAI-compatible chat/completions"
            )
        if not isinstance(raw_claim, dict):
            raise OnboardingError(f"capability_profile.{capability} must be an object")
        rating = raw_claim.get("rating")
        if rating not in RATINGS:
            raise OnboardingError(
                f"capability_profile.{capability}.rating must be one of {RATINGS}"
            )
        _require_string(raw_claim.get("note"), f"capability_profile.{capability}.note")


def _validate_sources(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise OnboardingError("sources must be a non-empty array")
    fields = ("claim", "url", "date", "tag", "corroboration")
    for index, source in enumerate(value):
        if not isinstance(source, dict):
            raise OnboardingError(f"sources[{index}] must be an object")
        for field in fields:
            _require_string(source.get(field), f"sources[{index}].{field}")


def _validate_string_list(value: Any, field: str) -> None:
    if not isinstance(value, list) or not value:
        raise OnboardingError(f"{field} must be a non-empty array")
    for index, item in enumerate(value):
        _require_string(item, f"{field}[{index}]")


def _require_identifier(value: Any, field: str) -> str:
    text = _require_string(value, field)
    if not _ID_PATTERN.fullmatch(text):
        raise OnboardingError(f"{field} must use lowercase letters, digits, dots, or hyphens")
    return text


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OnboardingError(f"{field} must be a non-empty string")
    return value


def _require_positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise OnboardingError(f"{field} must be a positive integer")
    return value


def _require_non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OnboardingError(f"{field} must be a non-negative integer")
    return value


def _require_non_negative_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise OnboardingError(f"{field} must be a finite non-negative number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise OnboardingError(f"{field} must be a finite non-negative number") from exc
    if not math.isfinite(number) or number < 0:
        raise OnboardingError(f"{field} must be a finite non-negative number")
    return number


def _load_registry_mapping(source: str, path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(source)
    except yaml.YAMLError as exc:
        raise OnboardingError(f"{path}: malformed registry YAML") from exc
    if not isinstance(raw, dict):
        raise OnboardingError(f"{path}: registry must be a mapping")
    return dict(raw)


def _validate_candidate(candidate: dict[str, Any]) -> None:
    try:
        registry = Registry.from_dict(candidate)
    except RegistryError as exc:
        raise OnboardingError(f"candidate row failed registry validation: {exc}") from exc
    report = check_registry(registry)
    if not report.ok:
        details = "; ".join(
            f"{issue.engine_key} [{issue.check}]: {issue.reason}" for issue in report.issues
        )
        raise OnboardingError(f"candidate row failed registry conformance: {details}")


def _insert_before_roles(source: str, fragment: str, path: Path) -> str:
    try:
        document = yaml.compose(source)
    except yaml.YAMLError as exc:
        raise OnboardingError(f"{path}: malformed registry YAML") from exc
    if not isinstance(document, MappingNode):
        raise OnboardingError(f"{path}: registry root must be a mapping")
    for key_node, _value_node in document.value:
        if isinstance(key_node, ScalarNode) and key_node.value == "roles":
            index = key_node.start_mark.index
            separator = "" if fragment.endswith("\n\n") else "\n"
            return source[:index] + fragment + separator + source[index:]
    raise OnboardingError(f"{path}: registry needs a top-level roles mapping")


def _validate_rendered(rendered: str, path: Path) -> None:
    raw = _load_registry_mapping(rendered, path)
    _validate_candidate(raw)


def _atomic_replace_if_unchanged(
    path: Path,
    rendered: str,
    *,
    expected_hash: str,
    before_replace: BeforeReplace | None,
) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.chmod(temporary, mode)
        if before_replace is not None:
            before_replace()
        try:
            current = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise OnboardingError(
                f"{path}: registry changed to invalid UTF-8 during onboarding"
            ) from exc
        if _sha256(current) != expected_hash:
            raise OnboardingError(
                f"{path}: registry changed during onboarding; refusing to overwrite"
            )
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _validate_applied_readback(path: Path, expected: str) -> None:
    """Require exact bytes plus a conformant registry after the atomic replacement."""

    try:
        current = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise OnboardingError(f"{path}: applied registry readback is not UTF-8") from exc
    if _sha256(current) != _sha256(expected):
        raise OnboardingError(f"{path}: applied registry readback digest mismatch")
    _validate_candidate(_load_registry_mapping(current, path))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, help="provider JSON specification")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="engine registry YAML")
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT), help="containment root")
    parser.add_argument("--apply", action="store_true", help="insert the validated row atomically")
    parser.add_argument(
        "--expected-sha256",
        help="required with --apply; SHA-256 of the exact registry bytes before mutation",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = onboard(
            args.spec,
            args.registry,
            apply=args.apply,
            expected_sha256=args.expected_sha256,
            repo_root=args.repo_root,
        )
    except (OSError, OnboardingError, RegistryError) as exc:
        print(f"engine onboarding failed: {exc}", file=sys.stderr)
        return 1

    if result.applied:
        print(f"added probationary engine row {result.engine_key}")
    else:
        print(result.fragment, end="")
        print(f"validated probationary engine row {result.engine_key} (dry-run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
