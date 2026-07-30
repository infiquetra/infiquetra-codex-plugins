#!/usr/bin/env python3
"""Thin one-shot Saga harness for advisory CLI and HTTP engines."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine_bridge_http  # noqa: E402
import engine_registry  # noqa: E402
import external_action_contract as contract  # noqa: E402
import external_action_egress as egress  # noqa: E402
import fleet_commons_shim  # noqa: E402
import reconcile  # noqa: E402
from external_action_workspace import Workspace, import_approved_patch  # noqa: E402

_receipt = fleet_commons_shim.load("bridge_receipt")
_attestation = fleet_commons_shim.load("output_attestation")

Runner = Callable[[dict[str, Any]], dict[str, Any]]
LaunchReporter = Callable[[dict[str, Any]], None]
DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "references" / "engine-registry.yaml"
CHILD_ENV_KEYS = ("HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE", "TERM")
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class CliConfig:
    engine_id: str
    receipt_emitter: str
    argv_builder: Callable[[dict[str, Any]], list[str]]
    timeout_seconds: int = 900
    stdin_prompt: bool = True


def _cli_config(engine_id: str) -> CliConfig:
    if engine_id == "agy":
        return CliConfig(
            engine_id="agy",
            receipt_emitter="agy-delegate",
            argv_builder=lambda invocation: [
                "agy",
                "--model",
                str(invocation["model"]),
                "--print-timeout",
                "900s",
                "--log-file",
                os.devnull,
                "--add-dir",
                ".",
                "--sandbox",
                "--print",
                str(invocation["task"]),
            ],
            stdin_prompt=False,
        )
    if engine_id == "claude-cli":
        return CliConfig(
            engine_id="claude-cli",
            receipt_emitter="claude-delegate",
            argv_builder=lambda invocation: [
                "claude",
                "--safe-mode",
                "--tools",
                (
                    "Read,Glob,Grep,Edit,Write"
                    if invocation.get("write_set")
                    else "Read,Glob,Grep"
                ),
                "--disable-slash-commands",
                "--print",
                "--model",
                str(invocation["model"]),
            ],
        )
    raise ValueError(f"unsupported CLI engine {engine_id!r}")


def cli_runner(
    config: CliConfig,
    *,
    repo_root: Path,
    variant: str,
    on_launch: LaunchReporter | None = None,
) -> Runner:
    """Return a supervised runner backed by a remote-stripped disposable checkout."""

    def run(invocation: dict[str, Any]) -> dict[str, Any]:
        write_set = tuple(str(item) for item in invocation.get("write_set", []))
        mode = str(invocation.get("mode") or "direct")
        if mode == "direct" and write_set:
            return {"status": "error", "output": "direct Saga external calls are read-only"}
        context_scope = tuple(str(item) for item in invocation.get("context_scope", []))
        workspace = Workspace.create(
            repo_root,
            str(invocation.get("base_revision") or "HEAD"),
            visible_paths=tuple(dict.fromkeys((*context_scope, *write_set))),
            required_paths=context_scope,
        )
        started = time.monotonic()
        try:
            argv = config.argv_builder(invocation)
            process = subprocess.Popen(
                argv,
                cwd=workspace.checkout,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
                env=_minimal_child_env(),
            )
            if on_launch is not None:
                try:
                    on_launch(
                        {
                            "transport": "cli",
                            "pid": process.pid,
                            "process_group": process.pid,
                        }
                    )
                except BaseException:
                    _kill_process_group(process)
                    process.communicate()
                    raise
            try:
                stdin_text = str(invocation["task"]) if config.stdin_prompt else None
                stdout, stderr = process.communicate(stdin_text, timeout=config.timeout_seconds)
            except subprocess.TimeoutExpired:
                _kill_process_group(process)
                process.communicate()
                return {"status": "timeout", "output": "provider timed out"}
            if process.returncode:
                return {"status": "error", "output": stderr.strip() or "provider failed"}
            patch, changed_paths, escaped = workspace.capture_patch(write_set)
            if escaped:
                return {
                    "status": "error",
                    "output": "provider changed paths outside the approved write set",
                }
            output = stdout.strip()
            if not output:
                return {"status": "error", "output": "provider produced no output"}
            receipt = _receipt.emit_receipt(
                engine_id=config.engine_id,
                variant=variant,
                transport="cli",
                wall_time_s=max(time.monotonic() - started, 0.0),
                bytes_produced=len(output.encode("utf-8")),
                runner={
                    "pid": process.pid,
                    "argv": _receipt_argv(argv, str(invocation["task"])),
                    "exit_code": process.returncode,
                },
                receipt_emitter=config.receipt_emitter,
                run_id=f"cli:{config.engine_id}:{process.pid}",
                invocation_sha256=_receipt.digest_invocation(invocation),
                output_attestation=_attestation.emit_attestation(
                    artifact="evidence",
                    content=output,
                ),
            )
            return {
                "status": "ok",
                "output": output,
                "receipt": receipt,
                "changed_paths": list(changed_paths),
                "patch": patch,
            }
        finally:
            workspace.close()

    return run


def runner_for(
    engine_id: str,
    *,
    repo_root: Path,
    variant: str = "",
    on_launch: LaunchReporter | None = None,
) -> Runner:
    """Keep the Claude/Agy delegate seam while sharing the one-shot harness."""

    if engine_id in {"agy", "claude-cli"}:
        return cli_runner(
            _cli_config(engine_id),
            repo_root=repo_root,
            variant=variant,
            on_launch=on_launch,
        )
    http_runner = engine_bridge_http.runner()

    def run_http(invocation: dict[str, Any]) -> dict[str, Any]:
        if invocation.get("write_set"):
            return {"status": "error", "output": "HTTP routes cannot produce workspace patches"}
        if on_launch is not None:
            on_launch(
                {
                    "transport": "http",
                    "operation_id": _receipt.digest_invocation(invocation),
                }
            )
        return http_runner(invocation)

    return run_http


def execute(
    request: contract.HarnessRequest,
    *,
    repo_root: Path,
    artifact_root: Path | None = None,
    runner: Runner | None = None,
    registry_path: Path = DEFAULT_REGISTRY,
) -> contract.HarnessResult:
    """Execute one request without lifecycle, retry, status-store, or promotion machinery."""

    registry = engine_registry.Registry.load(registry_path)
    sanitized = egress.sanitize(request.task)
    if sanitized.detections:
        return _failure(request, "task contains secret-like content", status="invalid-output")
    try:
        entry = registry.by_key(f"{request.engine_id}/{request.variant}")
    except engine_registry.RegistryError as exc:
        return _failure(request, f"route is unavailable: {exc}")
    if request.write_set and entry.transport != "cli":
        return _failure(request, "only contained CLI routes can return a patch")
    if request.write_set and artifact_root is None:
        return _failure(request, "verified-workflow writes require an artifact directory")

    invocation = dict(entry.invocation)
    invocation.update(
        {
            "engine_id": request.engine_id,
            "variant": request.variant,
            "task": request.task,
            "base_revision": request.base_revision,
            "context_scope": list(request.context_scope),
            "write_set": list(request.write_set),
            "mode": request.mode,
        }
    )
    active_runner = runner or runner_for(
        request.engine_id,
        repo_root=repo_root,
        variant=request.variant,
    )
    raw = active_runner(invocation)
    if not isinstance(raw, dict):
        return _failure(request, "provider result is not an object", status="invalid-output")
    status = raw.get("status")
    if status != "ok":
        mapped = "timed-out" if status == "timeout" else "unavailable"
        return _failure(request, str(raw.get("output") or status or "provider failed"), status=mapped)
    output = raw.get("output")
    receipt = raw.get("receipt")
    if not isinstance(output, str) or not output:
        return _failure(request, "provider output is empty or malformed", status="invalid-output")
    if not isinstance(receipt, dict):
        return _failure(request, "provider receipt is absent", status="invalid-output")
    receipt_errors = _receipt.validate_receipt(receipt)
    receipt_errors.extend(
        _validate_receipt_binding(
            receipt,
            invocation=invocation,
            output=output,
            engine_id=request.engine_id,
            variant=request.variant,
        )
    )
    if receipt_errors:
        return _failure(
            request,
            "provider proof is invalid: " + "; ".join(receipt_errors),
            status="invalid-output",
        )
    gatekeeper = _gatekeeper_key(output)
    if gatekeeper is not None:
        return _failure(
            request,
            f"advisory output contains forbidden gate field {gatekeeper!r}",
            status="invalid-output",
        )
    try:
        findings = _typed_findings(output)
        reconcile.parse_source_findings(findings)
    except (ValueError, reconcile.ReconciliationError) as exc:
        return _failure(request, f"provider findings are invalid: {exc}", status="invalid-output")

    patch = raw.get("patch", "")
    changed_raw = raw.get("changed_paths", [])
    if not isinstance(patch, str) or not isinstance(changed_raw, list):
        return _failure(request, "provider patch envelope is malformed", status="invalid-output")
    changed_paths = tuple(str(item) for item in changed_raw)
    if any(
        not any(path == allowed or path.startswith(f"{allowed.rstrip('/')}/") for allowed in request.write_set)
        for path in changed_paths
    ):
        return _failure(
            request,
            "provider changed paths outside the approved write set",
            status="invalid-output",
        )
    patch_ref: str | None = None
    patch_sha256: str | None = None
    if changed_paths:
        if not patch or artifact_root is None:
            return _failure(request, "changed paths lack a patch artifact", status="invalid-output")
        patch_path, patch_sha256 = _write_blob(
            artifact_root,
            prefix="patch",
            suffix=".diff",
            content=patch.encode("utf-8"),
        )
        patch_ref = str(patch_path)
    elif patch:
        return _failure(request, "patch has no changed paths", status="invalid-output")

    return contract.HarnessResult(
        request_id=request.request_id,
        engine_id=request.engine_id,
        variant=request.variant,
        status="available",
        evidence=output,
        findings=tuple(findings),
        receipt=receipt,
        changed_paths=changed_paths,
        patch_ref=patch_ref,
        patch_sha256=patch_sha256,
    )


def import_verified_workflow_patch(
    request: contract.HarnessRequest,
    result: contract.HarnessResult,
    *,
    repo_root: Path,
) -> Any:
    """Import an approved harness patch; callers must assign this to the Git operator."""

    if request.mode != "verified-workflow" or (
        result.request_id,
        result.engine_id,
        result.variant,
    ) != (
        request.request_id,
        request.engine_id,
        request.variant,
    ):
        raise ValueError("patch import requires one matching verified-workflow request/result pair")
    if (
        result.status != "available"
        or not result.patch_ref
        or not result.patch_sha256
        or not result.changed_paths
    ):
        raise ValueError("harness result has no importable patch")
    approval = SimpleNamespace(
        base_revision=request.base_revision,
        write_set=request.write_set,
        dirty_overlap=(),
    )
    return import_approved_patch(
        repo_root=repo_root,
        approval=approval,
        patch_path=Path(result.patch_ref),
        patch_sha256=result.patch_sha256,
        changed_paths=result.changed_paths,
    )


def _failure(
    request: contract.HarnessRequest,
    detail: str,
    *,
    status: str = "unavailable",
) -> contract.HarnessResult:
    return contract.HarnessResult(
        request_id=request.request_id,
        engine_id=request.engine_id,
        variant=request.variant,
        status=status,
        evidence="",
        findings=(),
        receipt=None,
        detail=detail,
    )


def _validate_receipt_binding(
    receipt: Mapping[str, Any],
    *,
    invocation: dict[str, Any],
    output: str,
    engine_id: str,
    variant: str,
) -> list[str]:
    errors: list[str] = []
    if receipt.get("engine_id") != engine_id or receipt.get("variant") != variant:
        errors.append("receipt route identity does not match the request")
    if receipt.get("invocation_sha256") != _receipt.digest_invocation(invocation):
        errors.append("receipt invocation digest does not match the request")
    attestation = receipt.get("output_attestation")
    if not isinstance(attestation, dict):
        errors.append("receipt lacks output attestation")
    else:
        errors.extend(
            _attestation.validate_attestation(
                attestation,
                expected_content=output,
                require_non_empty=True,
            )
        )
    return errors


def _gatekeeper_key(output: str) -> str | None:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return None
    stack: list[object] = [payload]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            for key, nested in value.items():
                if str(key).casefold() in contract.GATEKEEPER_KEYS:
                    return str(key)
                stack.append(nested)
        elif isinstance(value, list):
            stack.extend(value)
    return None


def _typed_findings(output: str) -> list[dict[str, str]]:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        payload = None
    raw = payload.get("findings") if isinstance(payload, dict) else None
    if isinstance(raw, list) and all(
        isinstance(item, dict)
        and set(item) == {"content"}
        and isinstance(item["content"], str)
        and item["content"]
        for item in raw
    ):
        return [{"content": item["content"]} for item in raw]
    return [{"content": output}]


def _minimal_child_env() -> dict[str, str]:
    """Expose process basics and file-backed provider login, never root secret variables."""

    return {key: os.environ[key] for key in CHILD_ENV_KEYS if os.environ.get(key)}


def _kill_process_group(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def _receipt_argv(argv: list[str], task: str) -> list[str]:
    marker = f"<redacted:{hashlib.sha256(task.encode('utf-8')).hexdigest()}>"
    return [marker if item == task else item for item in argv]


def _write_blob(
    root: Path,
    *,
    prefix: str,
    suffix: str,
    content: bytes,
) -> tuple[Path, str]:
    if not content or len(content) > MAX_ARTIFACT_BYTES:
        raise ValueError("harness artifact is empty or exceeds the size ceiling")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()
    destination = root / f"{prefix}-{digest}{suffix}"
    if destination.exists():
        if destination.read_bytes() != content:
            raise ValueError("content-addressed harness artifact differs")
        return destination, digest
    descriptor, name = tempfile.mkstemp(prefix=f".{prefix}-", suffix=".tmp", dir=root)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        os.chmod(destination, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return destination, digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        raw = json.loads(args.request.read_text(encoding="utf-8"))
        request = contract.HarnessRequest.from_dict(raw)
        result = execute(
            request,
            repo_root=args.repo_root,
            artifact_root=args.artifact_root,
        )
    except (OSError, json.JSONDecodeError, contract.ContractError, ValueError) as exc:
        print(f"Saga harness failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result.status == "available" else 1


if __name__ == "__main__":
    raise SystemExit(main())
