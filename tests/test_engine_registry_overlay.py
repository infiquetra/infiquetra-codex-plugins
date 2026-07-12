from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent
SCRIPT_DIR = ROOT / "plugins" / "saga" / "scripts"
REGISTRY = ROOT / "plugins" / "saga" / "references" / "engine-registry.yaml"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

OVERLAY = importlib.import_module("engine_overlay")
COMPOSE = importlib.import_module("engine_registry_overlay")
ONBOARDING = importlib.import_module("engine_onboarding")
PROMOTION = importlib.import_module("engine_promotion")


def _row() -> dict[str, object]:
    canonical = COMPOSE.canonical_mapping(REGISTRY)
    spec = {
        "transport": "http", "engine_id": "fixture", "variant": "chat",
        "base_url": "https://api.example.com/v1", "model": "chat",
        "auth_key_env": "FIXTURE_API_KEY", "context_window": 4096,
        "cost_speed_rank": 99, "cost_class": "free",
        "cost_per_token": {"input_usd": 0.0, "output_usd": 0.0},
        "latency_class": "standard", "model_identity": "fixture-chat",
        "last_validated": "2026-07-11",
        "capability_profile": {"code-generation": {"rating": "MODERATE", "note": "fixture"}},
        "prompting_protocol": ["Return advisory evidence."],
        "sources": [{"claim": "fixture", "url": "https://example.com", "date": "2026-07-11", "tag": "TEST", "corroboration": "MODERATE"}],
    }
    return ONBOARDING.build_row(spec, canonical)


def test_overlay_rows_compose_without_mutating_canonical(tmp_path: Path) -> None:
    canonical = tmp_path / "registry.yaml"
    canonical.write_bytes(REGISTRY.read_bytes())
    before = canonical.read_bytes()
    OVERLAY.save_overlay(tmp_path, OVERLAY.EngineOverlay(engines=[_row()]))

    composed = COMPOSE.load_composed_registry(canonical, tmp_path)

    assert composed.by_key("fixture/chat").trust_tier == "probation"
    assert canonical.read_bytes() == before


def test_composition_rejects_canonical_and_overlay_duplicate(tmp_path: Path) -> None:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    duplicate = dict(data["engines"][0])
    duplicate["last_validated"] = str(duplicate["last_validated"])
    duplicate["sources"] = [
        {**source, "date": str(source["date"])} for source in duplicate["sources"]
    ]
    OVERLAY.save_overlay(tmp_path, OVERLAY.EngineOverlay(engines=[duplicate]))

    with pytest.raises(OVERLAY.EngineOverlayError, match="canonical registry and overlay"):
        COMPOSE.load_composed_registry(REGISTRY, tmp_path)


def test_overlay_digest_blocks_stale_and_concurrent_writes(tmp_path: Path) -> None:
    expected = OVERLAY.overlay_sha256(tmp_path)
    first = OVERLAY.EngineOverlay(engines=[_row()])
    OVERLAY.save_overlay(tmp_path, first, expected_sha256=expected)

    with pytest.raises(OVERLAY.EngineOverlayError, match="digest changed"):
        OVERLAY.save_overlay(tmp_path, OVERLAY.EngineOverlay(), expected_sha256=expected)


def test_pin_and_deprecation_transforms_preserve_onboarded_engines() -> None:
    row = _row()
    overlay = OVERLAY.EngineOverlay(engines=[row])

    transformed = (
        OVERLAY.pin_engine(overlay, "code-generation", "fixture/chat"),
        OVERLAY.deprecate_engine(overlay, "fixture/chat"),
        OVERLAY.clear_pin(
            OVERLAY.pin_engine(overlay, "code-generation", "fixture/chat"),
            "code-generation",
        ),
        OVERLAY.clear_deprecated(
            OVERLAY.deprecate_engine(overlay, "fixture/chat"), "fixture/chat"
        ),
    )

    assert all(item.engines == (row,) for item in transformed)


def test_promotion_emits_diff_and_finalizes_only_after_identical_readback(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / "registry.yaml"
    canonical.write_bytes(REGISTRY.read_bytes())
    row = _row()
    OVERLAY.save_overlay(tmp_path, OVERLAY.EngineOverlay(engines=[row]))

    diff = PROMOTION.promotion_diff(
        "fixture/chat", registry_path=canonical, repo_root=tmp_path
    )

    assert "engine_id: fixture" in diff
    with pytest.raises(PROMOTION.PromotionError, match="does not contain promoted row"):
        PROMOTION.finalize_overlay_promotion(
            "fixture/chat",
            registry_path=canonical,
            repo_root=tmp_path,
            expected_overlay_sha256=OVERLAY.overlay_sha256(tmp_path),
        )

    data = yaml.safe_load(canonical.read_text(encoding="utf-8"))
    data["engines"].append(row)
    canonical.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    PROMOTION.finalize_overlay_promotion(
        "fixture/chat",
        registry_path=canonical,
        repo_root=tmp_path,
        expected_overlay_sha256=OVERLAY.overlay_sha256(tmp_path),
    )
    assert OVERLAY.load_overlay(tmp_path).engines == ()
