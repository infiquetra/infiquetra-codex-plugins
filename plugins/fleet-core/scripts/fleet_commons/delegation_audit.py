"""Codex-safe transcript classification and external-engine bundle corroboration.

This is an advisory proof primitive. It can detect a likely local fallback or disagreement between
signals, but it never grants Verified Workflows role authority.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

TRANSCRIPT_BYTE_CAP = 8 * 1024 * 1024
RESULT_BYTE_CAP = 1024 * 1024
LOCAL_MUTATION_TOOLS = frozenset({"apply_patch", "write_file", "edit_file"})

REAL = "real"
FALLBACK_SUSPECTED = "fallback_suspected"
DELEGATION_INTEGRITY = "delegation_integrity"


def _load_sibling(name: str) -> ModuleType:
    cache_key = f"_fleet_commons_{name}"
    if cache_key in sys.modules:
        return sys.modules[cache_key]
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(cache_key, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Fleet Core sibling module {name!r}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[cache_key] = module
    spec.loader.exec_module(module)
    return module


bridge_receipt = _load_sibling("bridge_receipt")


@dataclass(frozen=True)
class EngineConfig:
    name: str
    bundle_root: str
    launch_key: str
    receipt_file: str | None = None


ENGINE_CONFIGS: dict[str, EngineConfig] = {
    "codex": EngineConfig(
        name="codex",
        bundle_root=".codex/saga/engines/codex/runs",
        launch_key="codex_launched",
        receipt_file="bridge-receipt.json",
    )
}


class UnknownEngineError(ValueError):
    pass


def _engine_config(engine: str) -> EngineConfig:
    try:
        return ENGINE_CONFIGS[engine]
    except KeyError as exc:
        raise UnknownEngineError(
            f"unknown engine {engine!r}; expected one of {tuple(sorted(ENGINE_CONFIGS))}"
        ) from exc


@dataclass(frozen=True)
class AuditClassification:
    engine: str
    classification: str
    command_seen: bool
    local_mutation_tool_seen: bool
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "classification": self.classification,
            "command_seen": self.command_seen,
            "local_mutation_tool_seen": self.local_mutation_tool_seen,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class BundleCorroboration:
    engine: str
    launched: bool
    receipt_present: bool
    statuses: tuple[str, ...] = field(default_factory=tuple)
    run_dirs: tuple[str, ...] = field(default_factory=tuple)
    problems: tuple[str, ...] = field(default_factory=tuple)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "launched": self.launched,
            "receipt_present": self.receipt_present,
            "statuses": list(self.statuses),
            "run_dirs": list(self.run_dirs),
            "problems": list(self.problems),
        }


def _iter_capped_lines(path: Path, *, byte_cap: int = TRANSCRIPT_BYTE_CAP) -> Iterator[str]:
    remaining = byte_cap
    buffer = b""
    with path.open("rb") as handle:
        while remaining > 0:
            chunk = handle.read(min(64 * 1024, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            buffer += chunk
            lines = buffer.split(b"\n")
            buffer = lines.pop()
            for raw_line in lines:
                yield raw_line.decode("utf-8", errors="replace")
    if buffer:
        yield buffer.decode("utf-8", errors="replace")


def _event_tool_name(event: dict[str, Any]) -> str | None:
    for key in ("tool_name", "name"):
        value = event.get(key)
        if isinstance(value, str):
            return value
    message = event.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), list):
        for item in message["content"]:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                name = item.get("name")
                if isinstance(name, str):
                    return name
    return None


def _event_command(event: dict[str, Any]) -> str | None:
    for key in ("command", "cmd"):
        value = event.get(key)
        if isinstance(value, str):
            return value
    arguments = event.get("arguments") or event.get("input")
    if isinstance(arguments, dict) and isinstance(arguments.get("command"), str):
        return arguments["command"]
    message = event.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), list):
        for item in message["content"]:
            if not isinstance(item, dict) or item.get("type") != "tool_use":
                continue
            tool_input = item.get("input")
            if isinstance(tool_input, dict) and isinstance(tool_input.get("command"), str):
                return tool_input["command"]
    return None


def _looks_like_engine_command(command: str, engine: str) -> bool:
    lowered = command.lower()
    return (
        f"plugins/{engine}/scripts/{engine}_delegate.py" in lowered
        or f" --launch-{engine}" in lowered
        or lowered.startswith(f"{engine} ")
        or f" {engine} " in lowered
        or lowered.endswith(f"/{engine}")
        or f"/{engine} " in lowered
    )


def classify(transcript_path: Path | str, engine: str) -> AuditClassification:
    _engine_config(engine)
    evidence: list[str] = []
    command_seen = False
    local_mutation_tool_seen = False
    try:
        lines = _iter_capped_lines(Path(transcript_path))
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                evidence.append(f"line {line_number}: invalid json")
                continue
            if not isinstance(event, dict):
                continue
            tool_name = _event_tool_name(event)
            command = _event_command(event)
            if command and _looks_like_engine_command(command, engine):
                command_seen = True
                evidence.append(f"line {line_number}: {engine} command")
            if tool_name in LOCAL_MUTATION_TOOLS:
                local_mutation_tool_seen = True
                evidence.append(f"line {line_number}: local mutation tool {tool_name}")
    except OSError as exc:
        evidence.append(f"transcript unavailable: {type(exc).__name__}")
    classification = REAL if command_seen and not local_mutation_tool_seen else FALLBACK_SUSPECTED
    return AuditClassification(
        engine=engine,
        classification=classification,
        command_seen=command_seen,
        local_mutation_tool_seen=local_mutation_tool_seen,
        evidence=tuple(evidence),
    )


def _read_result(path: Path) -> Any:
    with path.open("rb") as handle:
        data = handle.read(RESULT_BYTE_CAP + 1)
    if len(data) > RESULT_BYTE_CAP:
        raise ValueError("result.json exceeds byte cap")
    return json.loads(data)


def _receipt_identity_errors(receipt: dict[str, Any], engine: str, run_name: str) -> list[str]:
    errors: list[str] = []
    if receipt.get("engine_id") != engine:
        errors.append("engine_id does not match the corroborated engine")
    if receipt.get("run_id") != run_name:
        errors.append("run_id is missing or does not match the containing run")
    return errors


def corroborate(
    engine: str, since_ts: float | None, *, root: Path | str | None = None
) -> BundleCorroboration:
    config = _engine_config(engine)
    base = (Path(root) if root is not None else Path.cwd()).resolve()
    bundle_root = base / config.bundle_root
    problems: list[str] = []
    run_dirs: list[str] = []
    statuses: list[str] = []
    matched_launch_receipt = False
    if not bundle_root.is_dir() or bundle_root.is_symlink():
        return BundleCorroboration(
            engine=engine,
            launched=False,
            receipt_present=False,
            problems=("bundle root not found or unsafe",),
        )
    try:
        entries = sorted(bundle_root.iterdir())
    except OSError as exc:
        return BundleCorroboration(
            engine=engine,
            launched=False,
            receipt_present=False,
            problems=(f"could not list bundle root: {type(exc).__name__}",),
        )
    for entry in entries:
        if entry.is_symlink() or not entry.is_dir():
            continue
        if since_ts is not None:
            try:
                if entry.stat().st_mtime < since_ts:
                    continue
            except OSError:
                problems.append(f"{entry.name}: unreadable run directory")
                continue
        try:
            payload = _read_result(entry / "result.json")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            problems.append(f"{entry.name}: missing/corrupt result.json ({type(exc).__name__})")
            continue
        if not isinstance(payload, dict):
            problems.append(f"{entry.name}: result.json is not an object")
            continue
        run_dirs.append(entry.name)
        status = payload.get("status")
        if isinstance(status, str):
            statuses.append(status)
        run_launched = payload.get(config.launch_key) is True
        run_receipt_valid = False
        if config.receipt_file is not None:
            receipt = entry / config.receipt_file
            if receipt.is_file() and not receipt.is_symlink():
                try:
                    receipt_payload = _read_result(receipt)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    problems.append(
                        f"{entry.name}: unreadable bridge receipt ({type(exc).__name__})"
                    )
                else:
                    if not isinstance(receipt_payload, dict):
                        problems.append(f"{entry.name}: bridge receipt is not an object")
                    else:
                        receipt_errors = [
                            *bridge_receipt.validate_receipt(receipt_payload),
                            *_receipt_identity_errors(receipt_payload, engine, entry.name),
                        ]
                        if receipt_errors:
                            problems.append(f"{entry.name}: bridge receipt failed validation")
                        else:
                            run_receipt_valid = True
        elif isinstance(payload.get("receipt"), dict):
            receipt_errors = [
                *bridge_receipt.validate_receipt(payload["receipt"]),
                *_receipt_identity_errors(payload["receipt"], engine, entry.name),
            ]
            if receipt_errors:
                problems.append(f"{entry.name}: embedded bridge receipt failed validation")
            else:
                run_receipt_valid = True
        if run_launched and run_receipt_valid:
            matched_launch_receipt = True
        elif run_launched or run_receipt_valid:
            problems.append(f"{entry.name}: launch and valid receipt were not joined in one run")
    return BundleCorroboration(
        engine=engine,
        launched=matched_launch_receipt,
        receipt_present=matched_launch_receipt,
        statuses=tuple(statuses),
        run_dirs=tuple(run_dirs),
        problems=tuple(problems),
    )


def reconcile(
    classification: AuditClassification,
    corroboration: BundleCorroboration,
    self_report: Any,
) -> str:
    if classification.engine != corroboration.engine:
        return DELEGATION_INTEGRITY
    if classification.classification == FALLBACK_SUSPECTED:
        return FALLBACK_SUSPECTED
    observer_says_launched = corroboration.launched and corroboration.receipt_present
    engine_says_ok = self_report in ("ok", "success", True) or (
        isinstance(self_report, str) and self_report.lower() in ("ok", "success", "real")
    )
    if engine_says_ok != observer_says_launched:
        return DELEGATION_INTEGRITY
    return REAL if observer_says_launched else FALLBACK_SUSPECTED
