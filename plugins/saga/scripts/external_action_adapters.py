#!/usr/bin/env python3
"""Runtime-owned adapter factory for supervised CLI and generic HTTP providers."""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine_bridge_http  # noqa: E402
import fleet_commons_shim  # noqa: E402
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
    timeout_seconds: int = 900


def cli_runner(config: CliConfig, *, repo_root: Path) -> Runner:
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
            )
            try:
                stdout, stderr = process.communicate(
                    str(invocation.get("task") or ""), timeout=config.timeout_seconds
                )
            except subprocess.TimeoutExpired:
                process.kill()
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
            elapsed = max(time.monotonic() - started, 0.0)
            receipt = _receipt.emit_receipt(
                engine_id=config.engine_id,
                variant=str(invocation.get("variant") or ""),
                transport="cli",
                wall_time_s=elapsed,
                bytes_produced=len(output.encode("utf-8")),
                runner={"pid": process.pid, "argv": argv, "exit_code": process.returncode},
                receipt_emitter=config.receipt_emitter,
                run_id=f"cli:{config.engine_id}:{process.pid}",
                invocation_sha256=_receipt.digest_invocation(invocation),
                output_attestation=_attestation.emit_attestation(artifact="evidence", content=output),
            )
            return {"status": "ok", "output": output, "receipt": receipt, "changed_paths": list(changed)}
        finally:
            workspace.close()

    return run


def runner_for(engine_id: str, *, repo_root: Path) -> Runner:
    if engine_id == "agy":
        return cli_runner(
            CliConfig(
                engine_id="agy",
                executable="agy",
                receipt_emitter="agy-delegate",
                argv_builder=lambda invocation: [
                    "agy", "delegate", "--mode", "patch" if invocation.get("write_set") else "no-write",
                    "--model", str(invocation.get("model") or ""),
                ],
            ),
            repo_root=repo_root,
        )
    if engine_id == "claude-cli":
        return cli_runner(
            CliConfig(
                engine_id="claude-cli",
                executable="claude",
                receipt_emitter="claude-delegate",
                argv_builder=lambda invocation: ["claude", "--print", "--model", str(invocation.get("model") or "")],
            ),
            repo_root=repo_root,
        )
    return engine_bridge_http.runner()
