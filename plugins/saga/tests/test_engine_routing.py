from __future__ import annotations

import sys
from pathlib import Path
import pytest

SCRIPT_DIR = Path(__file__).parents[1] / "scripts"
REFERENCES = Path(__file__).parents[1] / "references"
sys.path.insert(0, str(SCRIPT_DIR))

import engine_registry as REG  # noqa: E402
import engine_resolver as R  # noqa: E402


@pytest.fixture
def registry() -> REG.Registry:
    return REG.Registry.load(REFERENCES / "engine-registry.yaml")


@pytest.fixture
def available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        R,
        "preflight",
        lambda engine_id, **_kwargs: {
            "available": True,
            "reason": f"{engine_id} available",
        },
    )


def test_shipped_registry_exposes_only_the_six_supported_routes(
    registry: REG.Registry,
) -> None:
    assert {entry.key for entry in registry.engines} == {
        "claude-cli/opus",
        "agy/gemini-3.5-flash-high",
        "agy/gemini-3.1-pro-high",
        "ollama-cloud/gpt-oss-120b",
        "ollama-cloud/nomic-embed-text",
        "deepseek/deepseek-chat",
    }
    assert registry.by_role("cross-family-review-panel").verdict == "advisory"


@pytest.mark.usefixtures("available")
def test_capability_resolution_preserves_registry_model_and_protocol(
    registry: REG.Registry,
) -> None:
    resolution = R.resolve(
        {
            "capability": "code-generation",
            "role_kind": "generator",
            "task_context": {"context": "Implement the bounded change."},
        },
        mode="dispatch",
        registry=registry,
    )
    assert (resolution.engine_id, resolution.variant) == ("claude-cli", "opus")
    assert resolution.payload.endswith("Implement the bounded change.")
    assert resolution.invocation == registry.by_key("claude-cli/opus").invocation


@pytest.mark.usefixtures("available")
def test_named_route_and_panel_resolution_are_stable(registry: REG.Registry) -> None:
    named = R.resolve(
        {"engine": "agy/gemini-3.1-pro-high", "role_kind": "advisory-reviewer"},
        mode="advisory",
        registry=registry,
    )
    assert named.variant == "gemini-3.1-pro-high"
    panel = R.resolve_role("cross-family-review-panel", registry=registry)
    assert [f"{item.engine_id}/{item.variant}" for item in panel] == [
        "agy/gemini-3.1-pro-high",
        "agy/gemini-3.5-flash-high",
    ]
    assert R.panel_halt(panel) is None


def test_unavailable_named_route_halts_without_substitution(
    registry: REG.Registry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        R,
        "preflight",
        lambda _engine_id, **_kwargs: {"available": False, "reason": "not installed"},
    )
    resolution = R.resolve(
        {"engine": "agy/gemini-3.1-pro-high", "role_kind": "worker"},
        mode="dispatch",
        registry=registry,
    )
    assert resolution.fallback is None
    assert "not installed" in str(resolution.halt)


def test_resolver_memo_is_run_scoped(registry: REG.Registry, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        R,
        "preflight",
        lambda _engine_id, **_kwargs: {"available": True, "reason": "available"},
    )
    memo = R.RunMemo()
    request = {
        "capability": "code-generation",
        "role_kind": "worker",
        "task_context": {"context": "bounded"},
    }
    R.resolve(request, mode="dispatch", registry=registry, memo=memo)
    R.resolve(request, mode="dispatch", registry=registry, memo=memo)
    assert len(memo._capability) == 1


def test_panel_cap_and_unknown_capability_fail_closed(registry: REG.Registry) -> None:
    with pytest.raises(REG.RegistryError, match="unknown capability"):
        R.resolve(
            {"capability": "telepathy", "role_kind": "worker"},
            mode="dispatch",
            registry=registry,
        )
    assert REG.PANEL_N_CAP == 7
