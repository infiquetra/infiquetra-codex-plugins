"""Registry-derived static and catalog-resolved execution-class table tests."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

_FLEET_CORE = Path(__file__).resolve().parents[1]
_SCRIPTS = _FLEET_CORE / "scripts"
os.environ["FLEET_COMMONS_ROOT"] = str(_FLEET_CORE)
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _load(name: str) -> ModuleType:
    path = _SCRIPTS / "fleet_commons" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"render_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


palette = _load("tier_palette")
catalog = _load("codex_model_catalog")
renderer = _load("render_tier_table")


def _row(slug: str, efforts: tuple[str, ...]) -> dict:
    return {
        "slug": slug,
        "default_reasoning_level": efforts[0],
        "supported_reasoning_levels": [{"effort": effort} for effort in efforts],
        "visibility": "list",
        "supported_in_api": True,
    }


def test_static_table_is_registry_derived_and_covers_exact_classes() -> None:
    rows = renderer.render_rows()
    assert tuple(row[0] for row in rows) == palette.EXECUTION_CLASSES
    table = renderer.render_table()
    assert table.startswith("| Execution class | Purpose | Boundary | Preferred | Ordered fallback |")
    assert "`gpt-5.6-sol` / `max`" in table
    assert "`gpt-5.5` / `strongest supported scalar`" in table
    assert "workspace=read-only; external=allowlisted-read" in table
    assert "logical role" not in table.lower()


def test_scan_and_monitor_remain_separate_rows() -> None:
    table = renderer.render_table()
    assert table.count("`scan-low`") == 1
    assert table.count("`monitor-low`") == 1
    assert "external=none" in table
    assert "external=allowlisted-read" in table


def test_marker_block_and_main_output(capsys) -> None:
    block = renderer.render_block()
    assert block.startswith(renderer.TIER_TABLE_BEGIN)
    assert block.endswith(renderer.TIER_TABLE_END)
    assert renderer.main([]) == 0
    assert capsys.readouterr().out.strip() == block


def test_reference_generated_block_is_current() -> None:
    reference = (_FLEET_CORE / "references/tier-palette.md").read_text(encoding="utf-8")
    start = reference.index(renderer.TIER_TABLE_BEGIN)
    end = reference.index(renderer.TIER_TABLE_END, start) + len(renderer.TIER_TABLE_END)
    assert reference[start:end] == renderer.render_block()


def test_resolved_table_consumes_one_supplied_snapshot() -> None:
    snapshot = catalog.normalize_catalog(
        {
            "models": [
                _row("gpt-5.6-sol", ("low", "medium", "high", "xhigh", "max", "ultra")),
                _row("gpt-5.6-terra", ("low", "medium", "high", "xhigh", "max", "ultra")),
                _row("gpt-5.6-luna", ("low", "medium", "high", "xhigh", "max")),
                _row("gpt-5.5", ("low", "medium", "high", "xhigh")),
                _row("gpt-5.4-mini", ("low", "medium", "high", "xhigh")),
            ]
        },
        source="fixture",
    )
    table = renderer.render_resolved_table(snapshot)
    assert table.count(snapshot.normalized_sha256[:12]) == len(palette.EXECUTION_CLASSES)
    assert "| `review-max` | `gpt-5.6-sol` | `max` | `max` |" in table
    assert "| `monitor-low` | `gpt-5.6-luna` | `low` | `low` |" in table
