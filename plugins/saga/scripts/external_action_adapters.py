#!/usr/bin/env python3
"""Runtime-owned adapter factory for supervised CLI and generic HTTP providers."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine_bridge_http  # noqa: E402
import engine_dispatch  # noqa: E402
import engine_resolver  # noqa: E402
import external_action_runtime as runtime  # noqa: E402
import external_action_store as store_module  # noqa: E402
import fleet_commons_shim  # noqa: E402
import reconcile  # noqa: E402
from external_action_workspace import Workspace  # noqa: E402

_receipt = fleet_commons_shim.load("bridge_receipt")
_attestation = fleet_commons_shim.load("output_attestation")
Runner = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class CliConfig:
    engine_id: str
    executable: str
    receipt_emitter: str
    argv_builder: Callable[[dict[str, Any]], list[str]]
    variant: str = ""
    timeout_seconds: int = 900
    stdin_prompt: bool = True


def cli_runner(
    config: CliConfig,
    *,
    repo_root: Path,
    on_launch: runtime.LaunchReporter | None = None,
) -> Runner:
    def run(invocation: dict[str, Any]) -> dict[str, Any]:
        base = str(invocation.get("base_revision") or "HEAD")
        write_set = tuple(str(item) for item in invocation.get("write_set", []))
        workspace = Workspace.create(repo_root, base)
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
            )
            if on_launch is not None:
                on_launch(
                    {
                        "transport": "cli",
                        "pid": process.pid,
                        "process_group": process.pid,
                        "argv_sha256": hashlib.sha256(
                            json.dumps(argv, separators=(",", ":")).encode("utf-8")
                        ).hexdigest(),
                    }
                )
            try:
                stdin_text = str(invocation.get("task") or "") if config.stdin_prompt else None
                stdout, stderr = process.communicate(stdin_text, timeout=config.timeout_seconds)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, 9)
                process.communicate()
                return {"status": "timeout", "output": "provider timed out"}
            if process.returncode:
                return {"status": "error", "output": stderr.strip() or "provider failed"}
            patch, changed, escaped = workspace.capture_patch(write_set)
            if escaped:
                return {"status": "error", "output": "write-set escape", "changed_paths": list(changed)}
            output = stdout.strip()
            if patch:
                output = output + ("\n\n" if output else "") + patch
            if not output:
                return {"status": "error", "output": "provider produced no output"}
            elapsed = max(time.monotonic() - started, 0.0)
            receipt = _receipt.emit_receipt(
                engine_id=config.engine_id,
                variant=config.variant or str(invocation.get("variant") or ""),
                transport="cli",
                wall_time_s=elapsed,
                bytes_produced=len(output.encode("utf-8")),
                runner={
                    "pid": process.pid,
                    "argv": _receipt_argv(argv, str(invocation.get("task") or "")),
                    "exit_code": process.returncode,
                },
                receipt_emitter=config.receipt_emitter,
                run_id=f"cli:{config.engine_id}:{process.pid}",
                invocation_sha256=_receipt.digest_invocation(invocation),
                output_attestation=_attestation.emit_attestation(artifact="evidence", content=output),
            )
            return {"status": "ok", "output": output, "receipt": receipt, "changed_paths": list(changed)}
        finally:
            workspace.close()

    return run


def runner_for(
    engine_id: str,
    *,
    repo_root: Path,
    variant: str = "",
    on_launch: runtime.LaunchReporter | None = None,
) -> Runner:
    if engine_id == "agy":
        return cli_runner(
            CliConfig(
                engine_id="agy",
                executable="agy",
                receipt_emitter="agy-delegate",
                variant=variant,
                argv_builder=lambda invocation: [
                    "agy",
                    "--model",
                    str(invocation.get("model") or ""),
                    "--print-timeout",
                    "900s",
                    "--log-file",
                    os.devnull,
                    "--add-dir",
                    ".",
                    "--dangerously-skip-permissions" if invocation.get("write_set") else "--sandbox",
                    "--print",
                    str(invocation.get("task") or ""),
                ],
                stdin_prompt=False,
            ),
            repo_root=repo_root,
            on_launch=on_launch,
        )
    if engine_id == "claude-cli":
        return cli_runner(
            CliConfig(
                engine_id="claude-cli",
                executable="claude",
                receipt_emitter="claude-delegate",
                variant=variant,
                argv_builder=lambda invocation: [
                    "claude",
                    "--safe-mode",
                    "--tools",
                    "",
                    "--disable-slash-commands",
                    "--print",
                    "--model",
                    str(invocation.get("model") or ""),
                ],
            ),
            repo_root=repo_root,
            on_launch=on_launch,
        )
    http_runner = engine_bridge_http.runner()

    def run_http(invocation: dict[str, Any]) -> dict[str, Any]:
        if on_launch is not None:
            on_launch(
                {
                    "transport": "http",
                    "operation_id": _receipt.digest_invocation(invocation),
                }
            )
        return http_runner(invocation)

    return run_http


def executor_for_preview(
    preview: runtime.Preview,
    *,
    repo_root: Path,
) -> runtime.Executor:
    """Bind an approved preview to the shipped adapter and dispatch contracts."""
    snapshot = store_module.read_snapshot(preview.store)
    approval = snapshot.approval
    if approval is None:
        raise ValueError("executor binding requires a persisted approval")
    route = dict(approval.route)
    engine_id = str(route.get("engine_id") or "")
    variant = str(route.get("variant") or "")
    invocation = route.get("invocation")
    if not engine_id or not variant or not isinstance(invocation, dict):
        raise ValueError("approved route requires engine_id, variant, and invocation")
    payload = _payload_text(approval.payload)
    invocation = dict(invocation)
    invocation["base_revision"] = approval.base_revision
    invocation["write_set"] = list(approval.write_set)
    resolution = engine_resolver.Resolution(
        engine_id=engine_id,
        variant=variant,
        effort=str(invocation.get("effort") or route.get("effort") or "default"),
        recipe=str(invocation.get("recipe") or route.get("recipe") or "external action"),
        protocol=[str(item) for item in route.get("protocol", [])],
        payload=payload,
        write_capable=bool(invocation.get("write_capable", False)),
        fallback=None,
        halt=None,
        invocation=invocation,
        cost_class=approval.cost_class,
    )
    def executor(
        _request: Any,
        _approval: Any,
        launch: runtime.LaunchReporter,
    ) -> runtime.ExecutionOutcome:
        if _approval.approval_fingerprint != approval.approval_fingerprint:
            raise ValueError("executor approval changed after binding")
        provider_runner = runner_for(
            engine_id,
            repo_root=repo_root,
            variant=variant,
            on_launch=launch,
        )
        def typed_runner(invocation_payload: dict[str, Any]) -> dict[str, Any]:
            result = dict(provider_runner(invocation_payload))
            if (
                preview.request.intent in {"second-opinion", "divergence"}
                and result.get("status") == "ok"
            ):
                findings = _typed_findings(str(result.get("output") or ""))
                canonical_output = reconcile.render_source_findings(
                    reconcile.parse_source_findings(findings)
                )
                result["output"] = canonical_output
                result["findings"] = findings
                receipt = result.get("receipt")
                if isinstance(receipt, dict):
                    normalized_receipt = dict(receipt)
                    normalized_receipt["bytes_produced"] = len(canonical_output.encode("utf-8"))
                    normalized_receipt["output_attestation"] = _attestation.emit_attestation(
                        artifact="evidence",
                        content=canonical_output,
                    )
                    result["receipt"] = normalized_receipt
            return result

        evidence = engine_dispatch.dispatch(
            resolution,
            runner=typed_runner,
            write_set=list(approval.write_set),
            expected_identity=f"{engine_id}/{variant}",
            execution_id=preview.request.action_id,
            intent=preview.request.intent,
        )
        if not isinstance(evidence, engine_dispatch.AdvisoryEvidence):
            return runtime.ExecutionOutcome("unavailable", detail={"reason": "dispatch requeued"})
        if evidence.halt is not None or evidence.provenance.get("status") != "ok":
            return runtime.ExecutionOutcome(
                "unavailable",
                detail={"reason": evidence.halt or evidence.provenance.get("status")},
            )
        findings = [{"content": item.content} for item in evidence.source_findings]
        artifact = {
            "schema": "external_action_evidence.v1",
            "action_id": preview.request.action_id,
            "engine_id": evidence.engine_id,
            "variant": evidence.variant,
            "intent": evidence.intent,
            "evidence": evidence.evidence,
            "findings": findings,
            "evidence_digest": evidence.evidence_digest,
            "runner_receipt": evidence.runner_receipt,
        }
        artifact_path, artifact_sha256 = _write_evidence(preview.store.root, artifact)
        return runtime.ExecutionOutcome(
            "available",
            str(artifact_path),
            {
                "evidence": evidence.evidence,
                "findings": findings,
                "runner_receipt": evidence.runner_receipt,
                "artifact_sha256": artifact_sha256,
            },
            validated=True,
            artifact_sha256=artifact_sha256,
        )

    return executor


def _receipt_argv(argv: list[str], task: str) -> list[str]:
    """Keep durable receipts useful without persisting prompt content."""
    redacted = list(argv)
    if task:
        marker = f"<redacted:{hashlib.sha256(task.encode('utf-8')).hexdigest()}>"
        redacted = [marker if item == task else item for item in redacted]
    return redacted


def _payload_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _typed_findings(output: str) -> list[dict[str, str]]:
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        parsed = None
    raw = parsed.get("findings") if isinstance(parsed, dict) else None
    if isinstance(raw, list) and all(
        isinstance(item, dict) and set(item) == {"content"} and isinstance(item["content"], str)
        for item in raw
    ):
        return [{"content": item["content"]} for item in raw]
    return [{"content": output}]


def _write_evidence(root: Path, artifact: dict[str, Any]) -> tuple[Path, str]:
    payload = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    path = root / f"evidence-{digest}.json"
    if path.exists():
        if path.read_text(encoding="utf-8") != payload:
            raise ValueError("content-addressed evidence artifact differs")
        return path, digest
    fd, name = tempfile.mkstemp(prefix=".evidence-", suffix=".tmp", dir=root)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return path, digest
