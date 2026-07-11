"""Adversarial bridge lie-detector fixtures (#388)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "plugins" / "saga" / "scripts"


def _load(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = _load("engine_resolver")
D = _load("engine_dispatch")
PM = D.pm
BR = D._bridge_receipt
OA = D.fleet_commons_shim.load("output_attestation")
AUDIT = D.fleet_commons_shim.load("delegation_audit")
FIXTURES = ROOT / "tests" / "fixtures" / "delegation"


def _resolution() -> Any:
    return R.Resolution(
        engine_id="agy",
        variant="gemini-test",
        effort="high",
        recipe="recipe",
        protocol=["Run read-only."],
        payload="Run read-only.",
        write_capable=False,
        fallback=None,
        halt=None,
        invocation={"via": "agy:delegate", "model": "Gemini Test", "effort": "high"},
    )


def _invocation_digest() -> str:
    return BR.digest_invocation(D.build_agy_envelope(_resolution(), model=None))


def _manifest_for(receipt: dict[str, Any], output: str = "plausible delegated answer") -> Any:
    evidence = D.dispatch(
        _resolution(),
        runner=lambda _invocation: {"status": "ok", "output": output, "receipt": receipt},
    )
    return D.build_dispatch_manifest(
        evidence,
        execution_id="exec-lie",
        saga_ref="saga-1",
        created_at="2026-07-09T00:00:00Z",
    )


def test_host_fallback_without_signature_fails() -> None:
    receipt = BR.emit_receipt(
        engine_id="agy",
        variant="gemini-test",
        transport="cli",
        wall_time_s=0.01,
        bytes_produced=len("plausible delegated answer"),
        runner={"pid": 1, "argv": ["claude"], "exit_code": 0},
        invocation_sha256=_invocation_digest(),
    )

    manifest = _manifest_for(receipt)

    assert manifest.disposition is PM.Disposition.PROOF_INTEGRITY
    assert "missing receipt_emitter" in manifest.disposition_note


def test_zero_external_call_transcript_fails() -> None:
    receipt = BR.emit_receipt(
        engine_id="agy",
        variant="gemini-test",
        transport="cli",
        wall_time_s=0.01,
        bytes_produced=len("plausible delegated answer"),
        runner={"pid": 1, "argv": ["agy"], "exit_code": 0},
        receipt_emitter="agy-delegate",
        run_id="zero-call",
        invocation_sha256=_invocation_digest(),
        external_tokens=0,
        output_attestation=OA.emit_attestation(
            artifact="evidence",
            content="plausible delegated answer",
        ),
    )

    manifest = _manifest_for(receipt)

    assert manifest.disposition is PM.Disposition.PROOF_INTEGRITY
    assert "zero-external-token" in manifest.disposition_note


def test_inert_lineage_fixtures_distinguish_real_launch_from_host_clone() -> None:
    real = AUDIT.classify(FIXTURES / "real-codex.jsonl", "codex")
    clone = AUDIT.classify(FIXTURES / "claude-clone-codex.jsonl", "codex")
    empty = AUDIT.classify(FIXTURES / "empty.jsonl", "codex")

    assert real.classification == "real"
    assert clone.classification == "fallback_suspected"
    assert empty.classification == "fallback_suspected"
