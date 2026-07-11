"""Tests for the offline engine-registry conformance gate (#455)."""

from __future__ import annotations

import importlib.util
import os
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).parent.parent
SCRIPT_DIR = ROOT / "plugins" / "saga" / "scripts"
REGISTRY_PATH = ROOT / "plugins" / "saga" / "references" / "engine-registry.yaml"
SCRIPT = SCRIPT_DIR / "engine_registry_conformance.py"


def _load() -> ModuleType:
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location("engine_registry_conformance", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


C = _load()
OVERLAY = importlib.import_module("engine_overlay")
RESOLVER = importlib.import_module("engine_resolver")


def _registry_data() -> dict[str, Any]:
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _write_registry(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "engine-registry.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_shipped_registry_passes_offline_conformance() -> None:
    registry = C.Registry.load(REGISTRY_PATH)

    report = C.check_registry(registry)

    assert report.ok
    assert report.checked_rows == len(registry.engines)
    assert report.issues == ()


def test_shipped_registry_omits_native_codex_and_carries_model_effort() -> None:
    registry = C.Registry.load(REGISTRY_PATH)

    assert all(entry.engine_id != "codex" for entry in registry.engines)
    for entry in registry.engines:
        invocation = C.engine_dispatch._build_invocation(
            C.Resolution(
                engine_id=entry.engine_id,
                variant=entry.variant,
                effort=str(entry.invocation["effort"]),
                recipe=str(entry.invocation["recipe"]),
                protocol=list(entry.prompting_protocol),
                payload="probe",
                write_capable=False,
                fallback=None,
                halt=None,
                invocation=dict(entry.invocation),
            ),
            model=entry.invocation["model"],
        )
        assert invocation["model"] == entry.invocation["model"]
        assert invocation["effort"] == entry.invocation["effort"]


def test_signature_registry_exactly_covers_shipped_emitters() -> None:
    registry = C.Registry.load(REGISTRY_PATH)

    assert set(C.bridge_signatures.load_registry()) == {
        entry.receipt_emitter for entry in registry.engines
    }


def test_overlay_roundtrip_is_contained_and_owner_only(tmp_path: Path) -> None:
    overlay = OVERLAY.EngineOverlay(
        pins={"code-generation": "agy/gemini-3.5-flash-high"},
        deprecated={"deepseek/deepseek-chat"},
    )

    path = OVERLAY.save_overlay(tmp_path, overlay)

    assert path == tmp_path / ".codex" / "saga" / "engine-overlay.json"
    assert OVERLAY.load_overlay(tmp_path) == overlay
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_overlay_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / ".codex").symlink_to(outside, target_is_directory=True)

    with pytest.raises(OVERLAY.EngineOverlayError, match="escapes"):
        OVERLAY.load_overlay(tmp_path)


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda row: row["invocation"].update(
                {"via": "codex:delegate", "recipe": "codex exec --model gpt-5.6-sol"}
            ),
            "codex:delegate",
        ),
        (
            lambda row: row["invocation"].update(
                {"recipe": "external-cli --effort high"}
            ),
            "stale --effort",
        ),
        (lambda row: row["invocation"].pop("effort"), "effort"),
    ],
)
def test_cli_rows_reject_unenforceable_invocations(
    mutate: Any,
    match: str,
) -> None:
    data = _registry_data()
    row = data["engines"][0]
    mutate(row)

    with pytest.raises(C.RegistryError, match=match):
        C.Registry.from_dict(data)


@pytest.mark.parametrize("base_url", ["http://api.example.com", "https://127.0.0.1/v1"])
def test_http_rows_reject_unsafe_base_urls(base_url: str) -> None:
    data = _registry_data()
    row = next(entry for entry in data["engines"] if entry.get("transport") == "http")
    row["invocation"]["base_url"] = base_url

    with pytest.raises(C.RegistryError, match="base_url"):
        C.Registry.from_dict(data)


def test_registry_rejects_nonfinite_costs() -> None:
    data = _registry_data()
    data["engines"][0]["cost_per_token"]["input_usd"] = float("nan")

    with pytest.raises(C.RegistryError, match="finite"):
        C.Registry.from_dict(data)


def test_registry_rejects_oversized_integer_costs_without_overflow() -> None:
    data = _registry_data()
    data["engines"][0]["cost_per_token"]["input_usd"] = 10**1000

    with pytest.raises(C.RegistryError, match="finite"):
        C.Registry.from_dict(data)


def test_file_auth_preflight_rejects_partial_credentials() -> None:
    registry = C.Registry.load(REGISTRY_PATH)
    entry = registry.by_key("agy/gemini-3.5-flash-high")
    first = str(entry.auth["paths"][0])

    result = RESOLVER.preflight(
        entry.engine_id,
        entry=entry,
        which=lambda _cli: "/bin/agy",
        file_exists=lambda path: path == first,
    )

    assert result["available"] is False
    assert "one or more" in str(result["reason"])


def test_resolver_threads_registry_model_and_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = C.Registry.load(REGISTRY_PATH)
    monkeypatch.setattr(
        RESOLVER,
        "preflight",
        lambda *_args, **_kwargs: {"available": True, "reason": "fixture"},
    )

    resolution = RESOLVER.resolve(
        {
            "capability": "scaffold",
            "role_kind": "advisory-reviewer",
            "task_context": {"context": "review this"},
        },
        mode="advisory",
        registry=registry,
    )

    assert resolution.invocation is not None
    assert resolution.invocation["model"] == "Gemini 3.5 Flash (High)"
    assert resolution.invocation["effort"] == "high"
    assert resolution.effort == "high"


def test_unavailable_worker_falls_back_to_codex_root(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = C.Registry.load(REGISTRY_PATH)
    monkeypatch.setattr(
        RESOLVER,
        "preflight",
        lambda *_args, **_kwargs: {"available": False, "reason": "fixture unavailable"},
    )

    resolution = RESOLVER.resolve(
        {
            "capability": "scaffold",
            "role_kind": "worker",
            "task_context": {"context": "bounded task"},
        },
        mode="dispatch",
        registry=registry,
    )

    assert resolution.engine_id == "codex-root"
    assert resolution.variant == "inline"
    assert "Codex root" in str(resolution.fallback)


def test_unavailable_explicit_reviewer_halts(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = C.Registry.load(REGISTRY_PATH)
    monkeypatch.setattr(
        RESOLVER,
        "preflight",
        lambda *_args, **_kwargs: {"available": False, "reason": "fixture unavailable"},
    )

    resolution = RESOLVER.resolve(
        {
            "engine": "agy/gemini-3.5-flash-high",
            "role_kind": "advisory-reviewer",
        },
        mode="advisory",
        registry=registry,
    )

    assert resolution.halt is not None
    assert resolution.fallback is None


def test_schema_valid_dead_wired_row_fails_dispatch_invocation() -> None:
    data = _registry_data()
    row = data["engines"][-1]
    row["invocation"]["via"] = "missing-provider-bridge"
    registry = C.Registry.from_dict(data)

    report = C.check_registry(registry)

    assert not report.ok
    assert any(
        issue.engine_key == "deepseek/deepseek-chat"
        and issue.check == "dispatch-invocation"
        and "unsupported external engine" in issue.reason
        for issue in report.issues
    )


def test_unknown_receipt_emitter_fails_with_row_key() -> None:
    data = _registry_data()
    data["engines"][-1]["receipt_emitter"] = "missing-emitter"
    registry = C.Registry.from_dict(data)

    report = C.check_registry(registry)

    assert any(
        issue.engine_key == "deepseek/deepseek-chat"
        and issue.check == "receipt-emitter"
        and "missing-emitter" in issue.reason
        for issue in report.issues
    )


def test_independent_row_failures_are_reported_together() -> None:
    data = _registry_data()
    data["engines"][-1]["invocation"]["via"] = "missing-provider-bridge"
    data["engines"][-2]["receipt_emitter"] = "missing-emitter"
    registry = C.Registry.from_dict(data)

    report = C.check_registry(registry)

    failures = {(issue.engine_key, issue.check) for issue in report.issues}
    assert ("deepseek/deepseek-chat", "dispatch-invocation") in failures
    assert ("ollama-cloud/nomic-embed-text", "receipt-emitter") in failures


def test_advertised_capability_must_appear_in_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = C.Registry.load(REGISTRY_PATH)
    original = C.Registry.ranked_candidates

    def without_deepseek(self: Any, capability: str, **kwargs: Any) -> tuple[Any, ...]:
        return tuple(
            candidate
            for candidate in original(self, capability, **kwargs)
            if candidate.entry.key != "deepseek/deepseek-chat"
        )

    monkeypatch.setattr(C.Registry, "ranked_candidates", without_deepseek)

    report = C.check_registry(registry)

    assert any(
        issue.engine_key == "deepseek/deepseek-chat" and issue.check == "capability:code-generation"
        for issue in report.issues
    )


def test_checker_does_not_dispatch_or_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = C.Registry.load(REGISTRY_PATH)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("conformance must not dispatch or preflight")

    monkeypatch.setattr(C.engine_dispatch, "dispatch", forbidden)
    monkeypatch.setattr(sys.modules["engine_resolver"], "preflight", forbidden)

    assert C.check_registry(registry).ok


def test_cli_passes_live_registry_and_fails_broken_fixture(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert C.main(["--registry", str(REGISTRY_PATH)]) == 0
    assert "conformance ok" in capsys.readouterr().out

    broken = deepcopy(_registry_data())
    broken["engines"][-1]["invocation"]["via"] = "missing-provider-bridge"
    path = _write_registry(tmp_path, broken)

    assert C.main(["--registry", str(path)]) == 1
    err = capsys.readouterr().err
    assert "deepseek/deepseek-chat" in err
    assert "dispatch-invocation" in err

    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("engines: [", encoding="utf-8")
    assert C.main(["--registry", str(malformed)]) == 1
    assert "engine registry conformance failed" in capsys.readouterr().err
