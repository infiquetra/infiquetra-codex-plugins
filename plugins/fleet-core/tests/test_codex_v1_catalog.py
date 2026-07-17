"""Tests for the temporary Sol/Terra MultiAgent V1 catalog override."""

from __future__ import annotations

import copy
import importlib.util
import json
import stat
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "plugins/fleet-core/scripts/codex_v1_catalog.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("codex_v1_catalog_under_test", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


v1 = _load()


def _row(slug: str, version: str | None, *, ultra: bool = False) -> dict:
    efforts = ["low", "medium", "high"]
    if ultra:
        efforts.append("ultra")
    row = {
        "slug": slug,
        "default_reasoning_level": "low",
        "supported_reasoning_levels": [
            {"effort": effort, "description": f"description-{effort}"} for effort in efforts
        ],
        "visibility": "list",
        "supported_in_api": True,
        "base_instructions": f"preserve-{slug}",
        "unknown": {"nested": [slug]},
    }
    if version is not None:
        row["multi_agent_version"] = version
    return row


def _payload() -> dict:
    return {
        "models": [
            _row("gpt-5.6-sol", "v2", ultra=True),
            _row("gpt-5.6-terra", "v2", ultra=True),
            _row("gpt-5.6-luna", "v1"),
            _row("gpt-5.5", None),
        ],
        "catalog_unknown": {"must": "survive"},
    }


def _raw(payload: dict | None = None) -> bytes:
    return json.dumps(payload or _payload()).encode()


def test_transform_changes_only_target_multi_agent_versions() -> None:
    original = _payload()
    rendered = v1.transform_catalog(_raw(original), source="fixture")

    expected = copy.deepcopy(original)
    for row in expected["models"]:
        if row["slug"] in v1.TARGET_MODELS:
            row["multi_agent_version"] = "v1"

    assert rendered.payload == expected
    assert rendered.changed_models == v1.TARGET_MODELS
    assert rendered.ultra_warning is True
    assert not rendered.raw_bytes.startswith(b"\xef\xbb\xbf")
    assert json.loads(rendered.raw_bytes) == expected


def test_transform_is_idempotent() -> None:
    first = v1.transform_catalog(_raw(), source="fixture")
    second = v1.transform_catalog(first.raw_bytes, source="fixture")

    assert second.changed_models == ()
    assert second.raw_bytes == first.raw_bytes


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda payload: payload["models"].pop(0), "missing target models"),
        (
            lambda payload: payload["models"][0].__setitem__("multi_agent_version", "future"),
            "unsupported multi_agent_version",
        ),
    ],
)
def test_transform_rejects_target_schema_drift(mutate, match: str) -> None:
    payload = _payload()
    mutate(payload)

    with pytest.raises(v1.V1CatalogError, match=match):
        v1.transform_catalog(_raw(payload), source="fixture")


def test_transform_rejects_utf8_bom() -> None:
    with pytest.raises(v1.V1CatalogError, match="without BOM"):
        v1.transform_catalog(b"\xef\xbb\xbf" + _raw(), source="fixture")


def test_read_source_prefers_codex_cache_and_drops_cache_metadata(tmp_path: Path) -> None:
    cache = {
        **_payload(),
        "client_version": "0.144.5",
        "fetched_at": "2026-07-17T00:00:00Z",
        "etag": "private-cache-metadata",
    }
    (tmp_path / "models_cache.json").write_bytes(_raw(cache))

    source, raw = v1.read_source(codex_home=tmp_path)
    payload = json.loads(raw)

    assert source == "cache"
    assert set(payload) == {"models"}
    assert payload["models"] == cache["models"]


def test_config_render_preserves_unrelated_values_and_removes_v2_workaround(
    tmp_path: Path,
) -> None:
    path = tmp_path / "models.json"
    original = b'''model = "gpt-5.6-sol"\napproval_policy = "never"\n\n[agents]\nmax_threads = 6\n\n[features.multi_agent_v2]\nhide_spawn_agent_metadata = false\ntool_namespace = "agents"\n\n[mcp_servers.example]\nurl = "https://example.test"\n'''

    rendered = v1.render_config(original, path)
    parsed = tomllib.loads(rendered.decode())

    assert parsed["model"] == "gpt-5.6-sol"
    assert parsed["agents"]["max_threads"] == 6
    assert parsed["mcp_servers"]["example"]["url"] == "https://example.test"
    assert parsed["model_catalog_json"] == str(path.resolve())
    assert parsed["features"] == {"multi_agent": True, "multi_agent_v2": False}
    assert b"hide_spawn_agent_metadata" not in rendered
    assert b"tool_namespace" not in rendered


def test_config_render_updates_existing_feature_table(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    original = b"[features]\nhooks = true\nmulti_agent = false\nmulti_agent_v2 = true\n"

    parsed = tomllib.loads(v1.render_config(original, path).decode())

    assert parsed["features"] == {"hooks": True, "multi_agent": True, "multi_agent_v2": False}


def test_config_render_does_not_replace_nested_catalog_key(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    original = b'[example]\nmodel_catalog_json = "nested-value"\n'

    parsed = tomllib.loads(v1.render_config(original, path).decode())

    assert parsed["model_catalog_json"] == str(path.resolve())
    assert parsed["example"]["model_catalog_json"] == "nested-value"


def test_config_render_rejects_inline_features(tmp_path: Path) -> None:
    with pytest.raises(v1.V1CatalogError, match="inline top-level features"):
        v1.render_config(b"features = { multi_agent = true }\n", tmp_path / "models.json")


def test_install_writes_private_bom_free_catalog_and_one_time_backup(tmp_path: Path) -> None:
    home = tmp_path / "codex-home"
    catalog_path = home / v1.CATALOG_RELATIVE_PATH
    config_path = home / "config.toml"
    config_path.parent.mkdir()
    original = b'model = "gpt-5.6-sol"\n'
    config_path.write_bytes(original)
    rendered = v1.transform_catalog(_raw(), source="fixture")

    v1.write_catalog(catalog_path, rendered)
    backup = v1.install_config(config_path, catalog_path)
    first_config = config_path.read_bytes()
    v1.install_config(config_path, catalog_path)

    assert backup is not None and backup.read_bytes() == original
    assert config_path.read_bytes() == first_config
    assert not catalog_path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert stat.S_IMODE(catalog_path.stat().st_mode) == 0o600
    receipt = v1.validate_installed(catalog_path, config_path)
    assert receipt["status"] == "valid"
    assert receipt["target_versions"] == {slug: "v1" for slug in v1.TARGET_MODELS}

    v1.rollback_config(config_path)
    assert config_path.read_bytes() == original
