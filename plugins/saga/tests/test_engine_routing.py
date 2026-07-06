"""Oracle tests for the Saga external-engine routing stack (registry/resolver/dispatch, U8).

Consolidated from the upstream registry/resolver/dispatch suites into one per-plugin test file,
adapted to the Codex per-plugin layout (``plugins/saga/{scripts,references}``). The routing code is
a direct port (stdlib + YAML); the host-agent-of-record label ``claude`` is kept as a lineage name
(matches the ported provenance manifest's ``FELL_BACK_TO_CLAUDE``).
"""

from __future__ import annotations

import importlib.util
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).parent.parent
SCRIPT_DIR = ROOT / "scripts"
SEED_REGISTRY = ROOT / "references" / "engine-registry.yaml"


def _load(name: str, path: Path) -> ModuleType:
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


REG = _load("engine_registry", SCRIPT_DIR / "engine_registry.py")
R = _load("engine_resolver", SCRIPT_DIR / "engine_resolver.py")
D = _load("engine_dispatch", SCRIPT_DIR / "engine_dispatch.py")


class _Sandbox:
    """Duck-typed stand-in for a Unit's declared containment.

    The Codex adapter does not port the #287 Sandbox spawn-site enforcement class (deferred), but
    ``engine_dispatch`` duck-types the sandbox via ``is_restrictive`` + ``mutation_policy`` only, so
    the halt-not-downgrade write-ceiling behavior is still exercisable with a minimal stub.
    """

    def __init__(self, mutation_policy: str) -> None:
        self.is_restrictive = True
        self.mutation_policy = mutation_policy


# Reuse the exact module objects engine_dispatch imported (a re-_load would mint distinct
# enum classes and break ``is`` identity checks).
MS = D.manifest_store
PM = D.pm
RL = D.run_ledger


def _write_registry(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "engine-registry.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- registry loader (U1)


def _reg_dict() -> dict[str, Any]:
    return {
        "capabilities": list(REG.CAPABILITIES),
        "engines": [
            {
                "engine_id": "codex",
                "variant": "gpt-5.5-xhigh",
                "substrate": "external",
                "default_for_engine": True,
                "invocation": {
                    "via": "codex:codex-rescue",
                    "recipe": "codex -s read-only --effort xhigh",
                    "write_capable": False,
                },
                "context_window": 400000,
                "cost_speed_rank": 2,
                "model_identity": "gpt-5.5",
                "last_validated": "2026-06-27",
                "capability_profile": {
                    "code-generation": {
                        "rating": "STRONG",
                        "note": "structured-output fidelity, multi-file refactor",
                    },
                    "debug": {"rating": "STRONG", "note": "tool-orchestrated debugging"},
                },
                "prompting_protocol": [
                    "Run read-only when generating against the repo.",
                    "Return a unified diff plus assumptions.",
                ],
                "sources": [
                    {
                        "claim": "top composite reasoning",
                        "url": "https://example.invalid/codex",
                        "date": "2026-06-27",
                        "tag": "OFFICIAL",
                        "corroboration": "STRONG",
                    }
                ],
            },
            {
                "engine_id": "agy",
                "variant": "gemini-3.1-pro-high",
                "substrate": "in-repo",
                "default_for_engine": True,
                "invocation": {
                    "via": "agy:delegate",
                    "recipe": "agy delegate --mode no-write",
                    "write_capable": False,
                    "model": "Gemini 3.1 Pro (High)",
                },
                "context_window": 1000000,
                "cost_speed_rank": 1,
                "model_identity": "gemini-3.1-pro",
                "last_validated": "2026-06-20",
                "capability_profile": {
                    "code-generation": {
                        "rating": "STRONG",
                        "note": "same rating as codex, cheaper/faster tie-break wins",
                    },
                    "debug": {"rating": "MODERATE", "note": "useful second opinion"},
                },
                "prompting_protocol": [
                    "Use the no-write envelope for evidence-only work.",
                    "Return findings for host verification.",
                ],
                "sources": [
                    {
                        "claim": "large context review path",
                        "url": "https://example.invalid/agy",
                        "date": "2026-06-20",
                        "tag": "LOCAL",
                        "corroboration": "MODERATE",
                    }
                ],
            },
        ],
        "roles": {
            "cross-family-review-panel": {
                "members": ["codex/gpt-5.5-xhigh", "agy/gemini-3.1-pro-high"],
                "verdict": "advisory",
                "verifier": "claude",
            }
        },
    }


def test_happy_path_lookups_by_capability_engine_and_role(tmp_path: Path) -> None:
    registry = REG.Registry.load(_write_registry(tmp_path, _reg_dict()))

    assert registry.by_capability("debug").key == "codex/gpt-5.5-xhigh"
    assert registry.by_capability("code-generation").key == "agy/gemini-3.1-pro-high"
    assert registry.by_engine("codex").key == "codex/gpt-5.5-xhigh"
    assert registry.by_role("cross-family-review-panel").members == [
        "codex/gpt-5.5-xhigh",
        "agy/gemini-3.1-pro-high",
    ]


def test_ambiguous_engine_default_errors(tmp_path: Path) -> None:
    data = _reg_dict()
    data["engines"][0]["default_for_engine"] = False
    second_codex_variant = deepcopy(data["engines"][0])
    second_codex_variant["variant"] = "gpt-5.5-medium"
    second_codex_variant["cost_speed_rank"] = 3
    data["engines"].append(second_codex_variant)

    with pytest.raises(REG.RegistryError, match="ambiguous default"):
        REG.Registry.load(_write_registry(tmp_path, data))


def test_stale_true_when_last_validated_predates_revision_and_false_otherwise(
    tmp_path: Path,
) -> None:
    registry = REG.Registry.load(_write_registry(tmp_path, _reg_dict()))
    entry = registry.by_engine("codex")

    assert REG.Registry.stale(entry, {"gpt-5.5": "2026-06-28"})
    assert not REG.Registry.stale(entry, {"gpt-5.5": "2026-06-27"})
    assert not REG.Registry.stale(entry, {"gemini-3.1-pro": "2026-07-01"})


def test_unknown_capability_key_errors(tmp_path: Path) -> None:
    data = _reg_dict()
    data["engines"][0]["capability_profile"]["telepathy"] = {
        "rating": "STRONG",
        "note": "not in the closed vocabulary",
    }

    with pytest.raises(REG.RegistryError, match="telepathy"):
        REG.Registry.load(_write_registry(tmp_path, data))


def test_missing_sources_errors(tmp_path: Path) -> None:
    data = _reg_dict()
    del data["engines"][0]["sources"]

    with pytest.raises(REG.RegistryError, match="sources"):
        REG.Registry.load(_write_registry(tmp_path, data))


@pytest.mark.parametrize("value", [None, "fast"])
def test_missing_or_non_integer_cost_speed_rank_errors(tmp_path: Path, value: object) -> None:
    data = _reg_dict()
    if value is None:
        del data["engines"][0]["cost_speed_rank"]
    else:
        data["engines"][0]["cost_speed_rank"] = value

    with pytest.raises(REG.RegistryError, match="cost_speed_rank"):
        REG.Registry.load(_write_registry(tmp_path, data))


def test_role_member_referencing_non_existent_variant_errors(tmp_path: Path) -> None:
    data = _reg_dict()
    data["roles"]["cross-family-review-panel"]["members"] = ["codex/missing-variant"]

    with pytest.raises(REG.RegistryError, match="non-existent variant"):
        REG.Registry.load(_write_registry(tmp_path, data))


def test_shipped_seed_registry_loads_and_resolves() -> None:
    """The checked-in Codex seed registry validates and routes sanely (R3/R21)."""
    registry = REG.Registry.load(SEED_REGISTRY)

    assert len(registry.engines) >= 3
    # KTD9: a STRONG tie on adversarial-review resolves to the cheapest cost_speed_rank.
    assert registry.by_capability("adversarial-review").cost_speed_rank == 2
    for entry in registry.engines:
        assert entry.sources
        assert isinstance(entry.cost_speed_rank, int)
    panel = registry.by_role("cross-family-review-panel")
    assert panel.verdict == "advisory"
    assert panel.verifier == "claude"


# --------------------------------------------------------------------------- resolver (U2/U3)


def _res_dict() -> dict[str, Any]:
    return {
        "capabilities": list(REG.CAPABILITIES),
        "engines": [
            {
                "engine_id": "codex",
                "variant": "gpt-5.5-xhigh",
                "substrate": "external",
                "default_for_engine": True,
                "invocation": {
                    "via": "codex:codex-rescue",
                    "recipe": "codex -s read-only --effort xhigh",
                    "write_capable": False,
                },
                "context_window": 400000,
                "cost_speed_rank": 2,
                "model_identity": "gpt-5.5",
                "last_validated": "2026-06-27",
                "capability_profile": {
                    "code-generation": {
                        "rating": "STRONG",
                        "note": "structured-output fidelity, multi-file refactor",
                    },
                    "adversarial-review": {"rating": "STRONG", "note": "hardest reviewer tasks"},
                    "debug": {"rating": "STRONG", "note": "tool-orchestrated debugging"},
                    "long-form-writing": {"rating": "WEAK", "note": "route prose-heavy work out"},
                },
                "prompting_protocol": [
                    "Run read-only when generating against the repo.",
                    "Return a unified diff plus assumptions.",
                ],
                "sources": [
                    {
                        "claim": "top composite reasoning",
                        "url": "https://example.invalid/codex",
                        "date": "2026-06-27",
                        "tag": "OFFICIAL",
                        "corroboration": "STRONG",
                    }
                ],
            },
            {
                "engine_id": "agy",
                "variant": "gemini-3.1-pro-high",
                "substrate": "in-repo",
                "default_for_engine": True,
                "invocation": {
                    "via": "agy:delegate",
                    "recipe": "agy delegate --mode no-write",
                    "write_capable": False,
                    "model": "Gemini 3.1 Pro (High)",
                },
                "context_window": 1000000,
                "cost_speed_rank": 1,
                "model_identity": "gemini-3.1-pro",
                "last_validated": "2026-06-20",
                "capability_profile": {
                    "code-generation": {
                        "rating": "MODERATE",
                        "note": "useful second implementation opinion",
                    },
                    "adversarial-review": {"rating": "MODERATE", "note": "cross-family reviewer"},
                    "debug": {"rating": "MODERATE", "note": "useful second opinion"},
                },
                "prompting_protocol": [
                    "Use the no-write envelope for evidence-only work.",
                    "Return findings for host verification.",
                ],
                "sources": [
                    {
                        "claim": "large context review path",
                        "url": "https://example.invalid/agy",
                        "date": "2026-06-20",
                        "tag": "LOCAL",
                        "corroboration": "MODERATE",
                    }
                ],
            },
        ],
        "roles": {
            "cross-family-review-panel": {
                "members": ["codex/gpt-5.5-xhigh", "agy/gemini-3.1-pro-high"],
                "verdict": "advisory",
                "verifier": "claude",
            }
        },
    }


@pytest.fixture
def registry(tmp_path: Path) -> Any:
    return REG.Registry.load(_write_registry(tmp_path, _res_dict()))


@pytest.fixture
def engine_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        R,
        "preflight",
        lambda engine_id: {"available": True, "reason": f"{engine_id} available"},
    )


@pytest.mark.usefixtures("engine_available")
def test_capability_dispatch_returns_variant_protocol_and_payload(registry: Any) -> None:
    context = "Implement the bounded change."

    resolution = R.resolve(
        {
            "capability": "code-generation",
            "role_kind": "generator",
            "task_context": {"context": context},
        },
        mode="dispatch",
        registry=registry,
    )

    assert resolution.engine_id == "codex"
    assert resolution.variant == "gpt-5.5-xhigh"
    assert resolution.effort == "xhigh"
    assert resolution.recipe == "codex -s read-only --effort xhigh"
    assert resolution.protocol == [
        "Run read-only when generating against the repo.",
        "Return a unified diff plus assumptions.",
    ]
    assert resolution.payload == "\n".join(resolution.protocol) + "\n\n" + context
    assert resolution.write_capable is False
    assert resolution.fallback is None
    assert resolution.halt is None


@pytest.mark.usefixtures("engine_available")
def test_engine_advisory_returns_default_variant(registry: Any) -> None:
    resolution = R.resolve(
        {"engine": "codex", "role_kind": "advisory-reviewer"},
        mode="advisory",
        registry=registry,
    )

    assert resolution.engine_id == "codex"
    assert resolution.variant == "gpt-5.5-xhigh"
    assert resolution.payload == "\n".join(resolution.protocol)
    assert resolution.fallback is None
    assert resolution.halt is None


@pytest.mark.usefixtures("engine_available")
def test_payload_preserves_protocol_line_order_byte_for_byte(registry: Any) -> None:
    resolution = R.resolve(
        {
            "capability": "code-generation",
            "role_kind": "worker",
            "task_context": {"context": "Caller context."},
        },
        mode="dispatch",
        registry=registry,
    )

    expected_protocol_bytes = "\n".join(resolution.protocol).encode("utf-8")
    payload_prefix = resolution.payload.encode("utf-8").split(b"\n\n", 1)[0]
    assert payload_prefix == expected_protocol_bytes
    assert resolution.payload.splitlines()[: len(resolution.protocol)] == resolution.protocol


def test_long_form_writing_worker_no_fit_falls_back_not_halts(registry: Any) -> None:
    resolution = R.resolve(
        {
            "capability": "long-form-writing",
            "role_kind": "worker",
            "task_context": {"context": "Draft the decision entry."},
        },
        mode="dispatch",
        registry=registry,
    )

    # Worker/generator no-fit falls back to the host agent-of-record (serial), never halts.
    assert resolution.engine_id == "claude"
    assert resolution.fallback is not None
    assert "long-form-writing" in resolution.fallback
    assert "WEAK rating" in resolution.fallback
    assert resolution.halt is None


def test_panel_with_unavailable_member_halts_not_fallbacks(
    registry: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_preflight(engine_id: str) -> dict[str, bool | str]:
        if engine_id == "agy":
            return {"available": False, "reason": "agy is not installed"}
        return {"available": True, "reason": f"{engine_id} available"}

    monkeypatch.setattr(R, "preflight", fake_preflight)

    resolution = R.resolve(
        {
            "capability": "adversarial-review",
            "role_kind": "panel",
            "task_context": {
                "context": "Review the readiness packet.",
                "role": "cross-family-review-panel",
            },
        },
        mode="advisory",
        registry=registry,
    )

    assert resolution.fallback is None
    assert resolution.halt is not None
    assert "cross-family-review-panel" in resolution.halt
    assert "agy/gemini-3.1-pro-high" in resolution.halt


def test_named_unavailable_engine_halts_even_for_worker(
    registry: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        R,
        "preflight",
        lambda _engine_id: {"available": False, "reason": "codex is not installed"},
    )

    resolution = R.resolve(
        {"engine": "codex", "role_kind": "worker"},
        mode="dispatch",
        registry=registry,
    )

    assert resolution.fallback is None
    assert resolution.halt is not None
    assert "codex/gpt-5.5-xhigh" in resolution.halt
    assert "not installed" in resolution.halt


def test_task_token_estimate_exceeding_context_window_halts(registry: Any) -> None:
    resolution = R.resolve(
        {
            "engine": "codex",
            "role_kind": "worker",
            "task_context": {
                "context": "Small text; token estimate comes from the caller.",
                "token_estimate": 400001,
            },
        },
        mode="dispatch",
        registry=registry,
    )

    assert resolution.fallback is None
    assert resolution.halt is not None
    assert "token_estimate 400001" in resolution.halt
    assert "context_window 400000" in resolution.halt
    assert "truncate" in resolution.halt


def test_preflight_available_when_cli_and_config_present() -> None:
    result = R.preflight(
        "codex",
        which=lambda cli: f"/usr/bin/{cli}",
        config_exists=lambda engine_id: engine_id == "codex",
    )

    assert result["available"] is True
    assert "no live API call" in str(result["reason"])


def test_preflight_reports_not_configured_when_config_absent() -> None:
    result = R.preflight(
        "codex",
        which=lambda cli: f"/usr/bin/{cli}",
        config_exists=lambda _engine_id: False,
    )

    assert result["available"] is False
    assert "not configured" in str(result["reason"])


def test_preflight_reports_not_installed_when_cli_absent() -> None:
    result = R.preflight(
        "agy",
        which=lambda _cli: None,
        config_exists=lambda _engine_id: True,
    )

    assert result["available"] is False
    assert "not installed" in str(result["reason"])


@pytest.mark.usefixtures("engine_available")
def test_resolve_role_expands_to_per_member_advisory_resolutions(registry: Any) -> None:
    resolutions = R.resolve_role("cross-family-review-panel", registry=registry)
    members = registry.by_role("cross-family-review-panel").members

    assert len(resolutions) == len(members)
    assert [f"{r.engine_id}/{r.variant}" for r in resolutions] == members
    assert all(r.protocol for r in resolutions)
    assert R.panel_halt(resolutions) is None


def test_resolve_role_halts_panel_when_member_unavailable(
    registry: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_preflight(engine_id: str) -> dict[str, bool | str]:
        if engine_id == "agy":
            return {"available": False, "reason": "agy is not installed"}
        return {"available": True, "reason": f"{engine_id} available"}

    monkeypatch.setattr(R, "preflight", fake_preflight)

    resolutions = R.resolve_role("cross-family-review-panel", registry=registry)
    halt = R.panel_halt(resolutions)

    # R17: an unavailable panel member halts the panel; no host substitution.
    assert halt is not None
    assert "agy" in halt


# --------------------------------------------------------------------------- dispatch (U4/U5/#401)


def _resolution(
    *,
    engine_id: str = "codex",
    variant: str = "gpt-5.5-xhigh",
    payload: str = "Run read-only.\n\nReturn a unified diff.",
    halt: str | None = None,
) -> Any:
    return R.Resolution(
        engine_id=engine_id,
        variant=variant,
        effort="high",
        recipe="recipe",
        protocol=["Run read-only."],
        payload=payload,
        write_capable=False,
        fallback=None,
        halt=halt,
    )


def test_codex_invocation_preserves_payload_byte_for_byte_and_read_only() -> None:
    payload = "Run read-only.\n\nReturn the diff exactly.\nTrailing spaces:  "
    resolution = _resolution(payload=payload)

    invocation = D.build_codex_invocation(resolution)

    assert invocation == {
        "via": "codex:codex-rescue",
        "task": payload,
        "sandbox": "read-only",
    }
    assert invocation["task"].encode("utf-8") == payload.encode("utf-8")


def test_agy_envelope_is_no_write_and_forwards_model_verbatim() -> None:
    payload = "Use the no-write envelope.\n\nReturn evidence only."
    model = "  Gemini 3.1 Pro (High)  "
    resolution = _resolution(
        engine_id="agy",
        variant="gemini-3.1-pro-high",
        payload=payload,
    )

    envelope = D.build_agy_envelope(resolution, model=model)

    assert envelope["schema"] == "agy.delegation.v1"
    assert envelope["mode"] == "no-write"
    assert envelope["task"] == payload
    assert envelope["model"] == model


@pytest.mark.parametrize("status", ["timeout", "no-output", "error", "malformed", "clone-failed"])
def test_dispatch_failure_status_halts_with_downgrade_note_and_no_verdict(status: str) -> None:
    calls: list[dict[str, Any]] = []

    def runner(invocation: dict[str, Any]) -> dict[str, str]:
        calls.append(invocation)
        return {"status": status, "output": "wrapper failed"}

    evidence = D.dispatch(_resolution(), runner=runner)

    assert len(calls) == 1
    assert evidence.halt is not None
    assert evidence.evidence == ""
    assert evidence.provenance["status"] == status
    assert "note" in evidence.provenance
    assert "Downgraded external engine codex" in evidence.provenance["note"]
    assert status in evidence.provenance["note"]
    assert not hasattr(evidence, "gated_verdict")
    assert "gated_verdict" not in evidence.provenance


def test_dispatch_short_circuits_when_resolution_already_halted() -> None:
    called = False

    def runner(_invocation: dict[str, Any]) -> dict[str, str]:
        nonlocal called
        called = True
        raise AssertionError("runner must not be called for a halted resolution")

    evidence = D.dispatch(_resolution(halt="preflight halted"), runner=runner)

    assert called is False
    assert evidence.halt == "preflight halted"
    assert evidence.evidence == ""
    assert evidence.provenance["status"] == "halted"


def test_satisfy_gate_requires_host_verification() -> None:
    unverified = D.AdvisoryEvidence(
        engine_id="codex",
        variant="gpt-5.5-xhigh",
        evidence="external finding",
        provenance={"engine": "codex", "variant": "gpt-5.5-xhigh", "status": "ok"},
    )

    with pytest.raises(D.DispatchError):
        D.satisfy_gate(unverified)

    verified = D.AdvisoryEvidence(
        engine_id="codex",
        variant="gpt-5.5-xhigh",
        evidence="host verified external finding",
        provenance={"engine": "codex", "variant": "gpt-5.5-xhigh", "status": "ok"},
        verified_by_claude=True,
    )

    assert D.satisfy_gate(verified) is None


def test_dispatch_returns_advisory_evidence_without_tree_mutation_surface() -> None:
    payload = "Change plugins/saga/scripts/example.py.\n\nReturn the patch as evidence."

    def runner(invocation: dict[str, Any]) -> dict[str, str]:
        assert invocation["sandbox"] == "read-only"
        return {
            "status": "ok",
            "output": "diff --git a/example.py b/example.py\n+proposed evidence only",
        }

    evidence = D.dispatch(_resolution(payload=payload), runner=runner)

    assert isinstance(evidence, D.AdvisoryEvidence)
    assert evidence.evidence.startswith("diff --git")
    assert evidence.halt is None
    assert evidence.provenance == {
        "engine": "codex",
        "variant": "gpt-5.5-xhigh",
        "status": "ok",
    }
    assert not hasattr(evidence, "gated_verdict")


def _ok_runner(_invocation: dict[str, Any]) -> dict[str, str]:
    return {"status": "ok", "output": "external finding"}


def _store(tmp_path: Path) -> Any:
    return MS.Store(root=tmp_path / "saga-manifests" / "saga-1").ensure()


def test_dispatch_emits_manifest_with_attribution(tmp_path: Path) -> None:
    store = _store(tmp_path)
    evidence = D.dispatch(_resolution(), runner=_ok_runner)

    manifest = D.record_dispatch_manifest(
        store,
        evidence,
        execution_id="exec-1",
        saga_ref="saga-1",
        created_at="2026-07-01T00:00:00Z",
        effort="high",
        protocol="codex:codex-rescue",
    )

    assert manifest.attribution.kind is PM.ProducerKind.EXTERNAL_ENGINE
    assert manifest.attribution.identity == "codex/gpt-5.5-xhigh"
    assert manifest.attribution.effort == "high"
    assert manifest.attribution.protocol == "codex:codex-rescue"
    assert manifest.disposition is PM.Disposition.RAN_AS_REQUESTED

    persisted = MS.read_manifest(store, "exec-1")
    assert persisted is not None
    round_tripped = PM.Manifest.from_dict(persisted)
    assert round_tripped.attribution.identity == "codex/gpt-5.5-xhigh"
    assert round_tripped.schema == PM.SCHEMA_VERSION


def test_halted_dispatch_records_disposition_note(tmp_path: Path) -> None:
    store = _store(tmp_path)

    def failing_runner(_invocation: dict[str, Any]) -> dict[str, str]:
        return {"status": "timeout", "output": "wrapper timed out"}

    evidence = D.dispatch(_resolution(), runner=failing_runner)
    manifest = D.record_dispatch_manifest(
        store,
        evidence,
        execution_id="exec-halt",
        saga_ref="saga-1",
        created_at="2026-07-01T00:00:00Z",
    )

    assert manifest.disposition is PM.Disposition.FELL_BACK_TO_CLAUDE
    assert "Downgraded external engine codex" in manifest.disposition_note
    assert "timeout" in manifest.disposition_note

    persisted = MS.read_manifest(store, "exec-halt")
    assert persisted is not None
    assert persisted["disposition"] == "fell-back-to-claude"
    assert "Downgraded external engine codex" in persisted["disposition_note"]


def test_satisfy_gate_refuses_claimed_only_manifest(tmp_path: Path) -> None:
    store = _store(tmp_path)
    evidence = D.dispatch(_resolution(), runner=_ok_runner)
    claims = PM.ClaimProvenance(
        claims=(
            PM.Claim(
                text="all tests pass",
                claimed=PM.ClaimedStatus.VERIFIED,
                source_ref="tests/test_example.py",
            ),
        )
    )
    manifest = D.record_dispatch_manifest(
        store,
        evidence,
        execution_id="exec-claims",
        saga_ref="saga-1",
        created_at="2026-07-01T00:00:00Z",
        claim_provenance=claims,
    )

    verified = D.AdvisoryEvidence(
        engine_id=evidence.engine_id,
        variant=evidence.variant,
        evidence=evidence.evidence,
        provenance=evidence.provenance,
        verified_by_claude=True,
    )

    with pytest.raises(D.DispatchError):
        D.satisfy_gate(verified, manifest)

    adjudicated = D.adjudicate_manifest(
        store,
        "exec-claims",
        {
            ("all tests pass", "tests/test_example.py"): (
                PM.AdjudicatedStatus.VERIFIED,
                PM.Adjudication(
                    adjudicator="claude",
                    sources_read=("tests/test_example.py",),
                    decision="re-ran suite, all green",
                ),
            )
        },
    )
    assert D.satisfy_gate(verified, adjudicated) is None

    with pytest.raises(D.DispatchError):
        D.satisfy_gate(evidence, adjudicated)


def test_adjudicated_refuted_counts_as_parroting(tmp_path: Path) -> None:
    store = _store(tmp_path)
    evidence = D.dispatch(_resolution(), runner=_ok_runner)
    claims = PM.ClaimProvenance(
        claims=(
            PM.Claim(
                text="lint is clean",
                claimed=PM.ClaimedStatus.VERIFIED,
                source_ref="pyproject.toml",
            ),
        )
    )
    D.record_dispatch_manifest(
        store,
        evidence,
        execution_id="exec-parrot",
        saga_ref="saga-1",
        created_at="2026-07-01T00:00:00Z",
        claim_provenance=claims,
    )

    adjudicated = D.adjudicate_manifest(
        store,
        "exec-parrot",
        {
            ("lint is clean", "pyproject.toml"): (
                PM.AdjudicatedStatus.REFUTED,
                PM.Adjudication(adjudicator="claude", decision="ruff reported 3 errors"),
            )
        },
    )

    claim = adjudicated.claim_provenance.claims[0]
    assert claim.adjudicated is PM.AdjudicatedStatus.REFUTED
    assert claim.mismatch_reason is PM.MismatchReason.REFUTED
    assert PM.is_parroting(claim) is True
    assert PM.parroting_count(adjudicated) == 1

    persisted = MS.read_manifest(store, "exec-parrot")
    assert persisted is not None
    assert "verdict" not in persisted


def test_adjudicate_manifest_keys_same_text_claims_independently(tmp_path: Path) -> None:
    store = _store(tmp_path)
    evidence = D.dispatch(_resolution(), runner=_ok_runner)
    claims = PM.ClaimProvenance(
        claims=(
            PM.Claim(
                text="module is covered",
                claimed=PM.ClaimedStatus.VERIFIED,
                source_ref="tests/test_a.py",
            ),
            PM.Claim(
                text="module is covered",
                claimed=PM.ClaimedStatus.VERIFIED,
                source_ref="tests/test_b.py",
            ),
        )
    )
    D.record_dispatch_manifest(
        store,
        evidence,
        execution_id="exec-dup-text",
        saga_ref="saga-1",
        created_at="2026-07-01T00:00:00Z",
        claim_provenance=claims,
    )
    adjudicated = D.adjudicate_manifest(
        store,
        "exec-dup-text",
        {
            ("module is covered", "tests/test_a.py"): (
                PM.AdjudicatedStatus.VERIFIED,
                PM.Adjudication(adjudicator="claude", decision="ran test_a, green"),
            ),
            ("module is covered", "tests/test_b.py"): (
                PM.AdjudicatedStatus.REFUTED,
                PM.Adjudication(adjudicator="claude", decision="test_b does not exist"),
            ),
        },
    )
    by_source = {c.source_ref: c for c in adjudicated.claim_provenance.claims}
    assert by_source["tests/test_a.py"].adjudicated is PM.AdjudicatedStatus.VERIFIED
    assert by_source["tests/test_b.py"].adjudicated is PM.AdjudicatedStatus.REFUTED


def test_agy_sandboxed_mutate_lifts_to_patch_only_with_write_set() -> None:
    sb = _Sandbox("read-write")
    resolution = _resolution(engine_id="agy", variant="gemini-3.1-pro-high", payload="do it")
    envelope = D.build_agy_envelope(resolution, model="opus", sandbox=sb, write_set=["a.py", "b.py"])
    assert envelope["mode"] == "patch-only"
    assert envelope["write_set"] == ["a.py", "b.py"]
    assert envelope["apply_policy"] == "preserve-patch"
    assert envelope["task"].encode("utf-8") == b"do it"


def test_agy_read_only_sandbox_keeps_no_write_ceiling() -> None:
    sb = _Sandbox("read-only")
    resolution = _resolution(engine_id="agy", variant="v", payload="p")
    envelope = D.build_agy_envelope(resolution, model="opus", sandbox=sb, write_set=["x.py"])
    assert envelope["mode"] == "no-write"
    assert envelope["write_set"] == []


def test_agy_no_sandbox_dispatch_is_byte_identical_to_today() -> None:
    resolution = _resolution(engine_id="agy", variant="v", payload="p")
    assert D.build_agy_envelope(resolution, model="opus") == {
        "schema": "agy.delegation.v1",
        "role": "coder",
        "mode": "no-write",
        "task": "p",
        "model": "opus",
        "write_set": [],
        "apply_policy": "preserve-patch",
        "evidence": "summary",
        "verification": {"commands": [], "required": False, "run_scope": "none"},
        "provenance_required": True,
    }


def test_codex_sandboxed_mutate_enforce_halt() -> None:
    sb = _Sandbox("read-write")
    resolution = _resolution(engine_id="codex", payload="p")
    with pytest.raises(D.DispatchError, match="no write adapter"):
        D.build_codex_invocation(resolution, sandbox=sb)


def test_codex_no_sandbox_still_read_only() -> None:
    resolution = _resolution(engine_id="codex", payload="p")
    assert D.build_codex_invocation(resolution)["sandbox"] == "read-only"


def test_dispatch_codex_sandboxed_mutate_propagates_enforce_halt() -> None:
    sb = _Sandbox("read-write")
    with pytest.raises(D.DispatchError, match="no write adapter"):
        D.dispatch(_resolution(engine_id="codex"), runner=lambda inv: {"status": "ok"}, sandbox=sb)


def test_dispatch_agy_sandboxed_mutate_passes_patch_only_to_runner() -> None:
    sb = _Sandbox("read-write")
    seen: dict[str, Any] = {}

    def runner(inv: dict[str, Any]) -> dict[str, Any]:
        seen.update(inv)
        return {"status": "ok", "output": "diff"}

    evidence = D.dispatch(
        _resolution(engine_id="agy", variant="v"),
        runner=runner,
        model="opus",
        sandbox=sb,
        write_set=["a.py"],
    )
    assert seen["mode"] == "patch-only"
    assert seen["write_set"] == ["a.py"]
    assert evidence.evidence == "diff"


def test_manifest_records_declared_sandbox_attribution() -> None:
    evidence = D.AdvisoryEvidence(
        engine_id="agy", variant="v", evidence="out", provenance={"status": "ok"}
    )
    manifest = D.build_dispatch_manifest(
        evidence,
        execution_id="e1",
        saga_ref="s1",
        created_at="2026-07-02",
        sandbox="sandboxed-mutate",
    )
    assert manifest.to_dict()["attribution"]["sandbox"] == "sandboxed-mutate"


def test_manifest_absent_sandbox_emits_no_key_and_round_trips() -> None:
    evidence = D.AdvisoryEvidence(
        engine_id="agy", variant="v", evidence="out", provenance={"status": "ok"}
    )
    manifest = D.build_dispatch_manifest(
        evidence, execution_id="e1", saga_ref="s1", created_at="2026-07-02"
    )
    d = manifest.to_dict()
    assert "sandbox" not in d["attribution"]
    assert d["schema"] == PM.SCHEMA_VERSION
    assert PM.Manifest.from_dict(d).attribution.sandbox == ""


def _metric_runner(**metrics: Any):
    def runner(_invocation: Any) -> dict[str, Any]:
        return {"status": "ok", "output": "the diff", **metrics}

    return runner


def test_advisory_call_writes_one_engine_fact(tmp_path: Path) -> None:
    ledger = RL.RunLedger(path=tmp_path / "run-facts.jsonl")
    ev = D.dispatch(
        _resolution(engine_id="codex"),
        runner=_metric_runner(cost=0.02, latency_seconds=1.5, tokens=200),
        ledger=ledger,
        subplot_id="s1",
        at="2026-07-05T00:00:00Z",
    )
    facts = RL.read_facts(ledger)
    assert len(facts) == 1 and facts[0]["kind"] == "engine"
    assert facts[0]["engine"] == "codex"
    assert facts[0]["cost"] == 0.02 and facts[0]["latency_seconds"] == 1.5
    assert facts[0]["tokens"] == 200.0
    assert ev.evidence == "the diff"


def test_dispatch_without_ledger_writes_no_fact_and_is_unchanged(tmp_path: Path) -> None:
    ledger_path = tmp_path / "run-facts.jsonl"
    ev = D.dispatch(_resolution(engine_id="codex"), runner=_metric_runner(cost=0.02))
    assert ev.evidence == "the diff"
    assert not ledger_path.exists()


def test_agy_delegation_writes_engine_and_delegation_facts(tmp_path: Path) -> None:
    ledger = RL.RunLedger(path=tmp_path / "run-facts.jsonl")
    D.dispatch(
        _resolution(engine_id="agy", variant="gemini-3.1-pro-high"),
        runner=_metric_runner(cost=0.05, tokens=500),
        model="Gemini 3.1 Pro (High)",
        ledger=ledger,
        subplot_id="s1",
        at="t",
    )
    facts = RL.read_facts(ledger)
    assert [f["kind"] for f in facts] == ["engine", "delegation"]
    assert facts[1]["evidence"].startswith("sha256:")
    assert facts[1]["engine"] == "agy"
    assert RL.verify_chain(ledger).ok


def test_codex_advisory_writes_no_delegation_fact(tmp_path: Path) -> None:
    ledger = RL.RunLedger(path=tmp_path / "run-facts.jsonl")
    D.dispatch(
        _resolution(engine_id="codex"),
        runner=_metric_runner(),
        ledger=ledger,
        subplot_id="s1",
        at="t",
    )
    assert [f["kind"] for f in RL.read_facts(ledger)] == ["engine"]
