"""Tests for safe external-engine provider onboarding (#455)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT_DIR = ROOT / "plugins" / "saga" / "scripts"
REGISTRY_PATH = ROOT / "plugins" / "saga" / "references" / "engine-registry.yaml"
SCRIPT = SCRIPT_DIR / "engine_onboarding.py"
WRAPPER = ROOT / "tools" / "add-engine.sh"


def _load() -> ModuleType:
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location("engine_onboarding", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ONBOARDING = _load()
CONFORMANCE = importlib.import_module("engine_registry_conformance")
OVERLAY = importlib.import_module("engine_overlay")
REGISTRY_OVERLAY = importlib.import_module("engine_registry_overlay")
DISPATCH = importlib.import_module("engine_dispatch")
RESOLVER = importlib.import_module("engine_resolver")
FLEET_COMMONS = importlib.import_module("fleet_commons_shim")
BRIDGE_RECEIPT = FLEET_COMMONS.load("bridge_receipt")
OUTPUT_ATTESTATION = FLEET_COMMONS.load("output_attestation")


def _spec() -> dict[str, Any]:
    return {
        "transport": "http",
        "engine_id": "fixture-http",
        "variant": "fixture-chat",
        "base_url": "https://api.example.com/v1",
        "model": "fixture-chat",
        "auth_key_env": "FIXTURE_API_KEY",
        "context_window": 32768,
        "cost_speed_rank": 99,
        "cost_class": "metered",
        "cost_per_token": {"input_usd": 0.000001, "output_usd": 0.000002},
        "budget_ceiling_usd": 5.0,
        "latency_class": "standard",
        "model_identity": "fixture-chat",
        "last_validated": "2026-07-09",
        "capability_profile": {
            "code-generation": {
                "rating": "MODERATE",
                "note": "fixture provider onboarding proof",
            }
        },
        "prompting_protocol": ["Return advisory evidence only."],
        "sources": [
            {
                "claim": "OpenAI-compatible endpoint and model id",
                "url": "https://api.example.com/docs",
                "date": "2026-07-09",
                "tag": "OFFICIAL",
                "corroboration": "STRONG",
            }
        ],
    }


def _write_spec(tmp_path: Path, data: dict[str, Any] | None = None) -> Path:
    path = tmp_path / "provider.json"
    path.write_text(json.dumps(_spec() if data is None else data), encoding="utf-8")
    return path


def _copy_registry(tmp_path: Path) -> Path:
    path = tmp_path / "engine-registry.yaml"
    path.write_text(REGISTRY_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def _onboard(
    spec: Path,
    registry: Path,
    *,
    apply: bool = False,
    before_replace: Any | None = None,
) -> Any:
    expected = OVERLAY.overlay_sha256(registry.parent) if apply else None
    return ONBOARDING.onboard(
        spec,
        registry,
        apply=apply,
        expected_sha256=expected,
        repo_root=registry.parent,
        before_replace=before_replace,
        smoke_runner=lambda _invocation: {
            "status": "ok",
            "output": "SAGA_PROVIDER_SMOKE_OK",
            "external_tokens": 1,
        },
        getenv=lambda _name: "fixture-secret",
    )


def test_dry_run_builds_probationary_generic_http_row_without_writing(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)
    registry = _copy_registry(tmp_path)
    before = registry.read_text(encoding="utf-8")

    result = _onboard(spec, registry)

    assert not result.applied
    assert result.engine_key == "fixture-http/fixture-chat"
    assert result.row["trust_tier"] == "probation"
    assert result.row["invocation"]["via"] == "engine-bridge-http"
    assert result.row["invocation"]["write_capable"] is False
    assert result.row["receipt_emitter"] == "http-bridge"
    assert registry.read_text(encoding="utf-8") == before


def test_apply_writes_only_overlay_and_composed_registry_loads(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)
    registry = _copy_registry(tmp_path)
    before = registry.read_text(encoding="utf-8")

    result = _onboard(spec, registry, apply=True)

    assert result.applied
    assert registry.read_text(encoding="utf-8") == before
    loaded = REGISTRY_OVERLAY.load_composed_registry(registry, tmp_path)
    entry = loaded.by_key("fixture-http/fixture-chat")
    assert entry.trust_tier == "probation"
    assert entry.default_for_engine is True


def test_free_provider_omits_budget_ceiling_and_requires_zero_prices(tmp_path: Path) -> None:
    data = _spec()
    data["cost_class"] = "free"
    data["cost_per_token"] = {"input_usd": 0.0, "output_usd": 0.0}
    data.pop("budget_ceiling_usd")

    result = _onboard(_write_spec(tmp_path, data), _copy_registry(tmp_path))

    assert result.row["cost_class"] == "free"
    assert "budget_ceiling_usd" not in result.row


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda data: data.pop("capability_profile"), "capability_profile"),
        (lambda data: data.__setitem__("capability_profile", {}), "capability_profile"),
        (lambda data: data.__setitem__("sources", []), "sources"),
        (lambda data: data.pop("auth_key_env"), "auth_key_env"),
        (lambda data: data.pop("model"), "model"),
        (lambda data: data["cost_per_token"].pop("output_usd"), "cost_per_token"),
        (lambda data: data.__setitem__("base_url", "http://user:pass@example.com?q=1"), "base_url"),
    ],
)
def test_invalid_spec_names_field_and_writes_nothing(
    tmp_path: Path,
    mutate: Any,
    message: str,
) -> None:
    data = _spec()
    mutate(data)
    spec = _write_spec(tmp_path, data)
    registry = _copy_registry(tmp_path)
    before = registry.read_bytes()

    with pytest.raises(ONBOARDING.OnboardingError, match=message):
        _onboard(spec, registry, apply=True)

    assert registry.read_bytes() == before


def test_cli_transport_is_rejected_without_a_real_wrapper(tmp_path: Path) -> None:
    data = _spec()
    data["transport"] = "cli"
    spec = _write_spec(tmp_path, data)
    registry = _copy_registry(tmp_path)

    with pytest.raises(ONBOARDING.OnboardingError, match="CLI providers need a real wrapper"):
        _onboard(spec, registry)


def test_embedding_capability_is_rejected_by_chat_completions_scaffolder(tmp_path: Path) -> None:
    data = _spec()
    data["capability_profile"] = {
        "embedding": {"rating": "STRONG", "note": "not a chat capability"}
    }

    with pytest.raises(ONBOARDING.OnboardingError, match="chat/completions"):
        _onboard(_write_spec(tmp_path, data), _copy_registry(tmp_path))


def test_duplicate_or_non_finite_json_value_is_rejected(tmp_path: Path) -> None:
    registry = _copy_registry(tmp_path)
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        json.dumps(_spec()).replace(
            '"engine_id": "fixture-http"',
            '"engine_id": "reviewed-safe", "engine_id": "fixture-http"',
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ONBOARDING.OnboardingError, match="duplicate JSON field 'engine_id'"):
        _onboard(duplicate, registry)

    non_finite = _spec()
    non_finite["cost_per_token"]["input_usd"] = float("inf")
    with pytest.raises(ONBOARDING.OnboardingError, match="non-finite JSON number"):
        _onboard(_write_spec(tmp_path, non_finite), registry)


def test_second_apply_is_idempotent_and_preserves_first_result(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)
    registry = _copy_registry(tmp_path)
    _onboard(spec, registry, apply=True)
    after_first = registry.read_bytes()

    repeated = _onboard(spec, registry, apply=True)

    assert repeated.applied is False
    assert registry.read_bytes() == after_first


def test_concurrent_registry_edit_aborts_without_overwriting_it(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)
    registry = _copy_registry(tmp_path)

    def concurrent_edit() -> None:
        OVERLAY.save_overlay(
            tmp_path,
            OVERLAY.EngineOverlay(
                pins={"code-generation": "agy/gemini-3.5-flash-high"}
            ),
        )

    with pytest.raises(ONBOARDING.OnboardingError, match="overlay changed during apply"):
        _onboard(spec, registry, apply=True, before_replace=concurrent_edit)

    assert OVERLAY.load_overlay(tmp_path).pins == {
        "code-generation": "agy/gemini-3.5-flash-high"
    }
    assert "fixture-http" not in registry.read_text(encoding="utf-8")


def test_conformance_failure_prevents_apply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _write_spec(tmp_path)
    registry = _copy_registry(tmp_path)
    before = registry.read_bytes()
    issue = CONFORMANCE.ConformanceIssue(
        "fixture-http/fixture-chat",
        "dispatch-invocation",
        "dead wired",
    )
    monkeypatch.setattr(
        ONBOARDING,
        "check_registry",
        lambda _registry: CONFORMANCE.ConformanceReport(1, (issue,)),
    )

    with pytest.raises(ONBOARDING.OnboardingError, match="dead wired"):
        _onboard(spec, registry, apply=True)

    assert registry.read_bytes() == before


def test_cli_main_reports_success_and_invalid_utf8_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = _copy_registry(tmp_path)
    common = ["--registry", str(registry), "--repo-root", str(tmp_path)]
    assert ONBOARDING.main(["--spec", str(_write_spec(tmp_path)), *common]) == 0
    assert "validated probationary engine row" in capsys.readouterr().out

    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"\xff")
    assert ONBOARDING.main(["--spec", str(invalid), *common]) == 1
    assert "provider spec must be UTF-8" in capsys.readouterr().err


def test_apply_requires_current_digest_and_contained_regular_target(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)
    registry = _copy_registry(tmp_path)
    before = registry.read_bytes()

    with pytest.raises(ONBOARDING.OnboardingError, match="expected overlay SHA-256"):
        ONBOARDING.onboard(spec, registry, apply=True, repo_root=tmp_path)
    with pytest.raises(ONBOARDING.OnboardingError, match="does not match"):
        ONBOARDING.onboard(
            spec,
            registry,
            apply=True,
            expected_sha256="0" * 64,
            repo_root=tmp_path,
        )

    outside = tmp_path.parent / f"{tmp_path.name}-outside-registry.yaml"
    outside.write_bytes(before)
    try:
        with pytest.raises(ONBOARDING.OnboardingError, match="escapes"):
            ONBOARDING.onboard(spec, outside, repo_root=tmp_path)
    finally:
        outside.unlink()

    link = tmp_path / "registry-link.yaml"
    link.symlink_to(registry)
    with pytest.raises(ONBOARDING.OnboardingError, match="symlink"):
        ONBOARDING.onboard(spec, link, repo_root=tmp_path)
    assert registry.read_bytes() == before


def test_apply_rejects_unresolved_secret_and_failed_smoke(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)
    registry = _copy_registry(tmp_path)
    expected = OVERLAY.overlay_sha256(tmp_path)

    with pytest.raises(ONBOARDING.OnboardingError, match="secret reference"):
        ONBOARDING.onboard(
            spec,
            registry,
            apply=True,
            expected_sha256=expected,
            repo_root=tmp_path,
            getenv=lambda _name: None,
        )
    with pytest.raises(ONBOARDING.OnboardingError, match="provider smoke failed"):
        ONBOARDING.onboard(
            spec,
            registry,
            apply=True,
            expected_sha256=expected,
            repo_root=tmp_path,
            getenv=lambda _name: "fixture-secret",
            smoke_runner=lambda _invocation: {"status": "error", "note": "fixture failure"},
        )
    assert not (tmp_path / ".codex" / "saga" / "engine-overlay.json").exists()


def test_onboarded_overlay_row_dispatches_through_generic_http_contract(
    tmp_path: Path,
) -> None:
    spec = _write_spec(tmp_path)
    registry = _copy_registry(tmp_path)
    _onboard(spec, registry, apply=True)
    entry = REGISTRY_OVERLAY.load_composed_registry(registry, tmp_path).by_key(
        "fixture-http/fixture-chat"
    )
    resolution = RESOLVER.Resolution(
        engine_id=entry.engine_id,
        variant=entry.variant,
        effort=str(entry.invocation["effort"]),
        recipe=str(entry.invocation["recipe"]),
        protocol=list(entry.prompting_protocol),
        payload="review this fixture",
        write_capable=False,
        fallback=None,
        halt=None,
        invocation=dict(entry.invocation),
    )

    def runner(invocation: dict[str, Any]) -> dict[str, Any]:
        output = "fixture advisory"
        receipt = BRIDGE_RECEIPT.emit_receipt(
            engine_id=entry.engine_id,
            variant=entry.variant,
            transport="http",
            wall_time_s=0.01,
            bytes_produced=len(output.encode("utf-8")),
            runner={
                "url": str(invocation["base_url"]).rstrip("/") + "/chat/completions",
                "status_code": 200,
                "model": invocation["model"],
            },
            receipt_emitter="http-bridge",
            run_id="fixture-http:1",
            invocation_sha256=BRIDGE_RECEIPT.digest_invocation(invocation),
            external_tokens=3.0,
            output_attestation=OUTPUT_ATTESTATION.emit_attestation(
                artifact="evidence", content=output
            ),
        )
        return {
            "status": "ok",
            "output": output,
            "tokens": 3.0,
            "latency_seconds": 0.01,
            "receipt": receipt,
        }

    evidence = DISPATCH.dispatch(resolution, runner=runner)

    assert evidence.evidence == "fixture advisory"
    assert evidence.runner_receipt["receipt_emitter"] == "http-bridge"
