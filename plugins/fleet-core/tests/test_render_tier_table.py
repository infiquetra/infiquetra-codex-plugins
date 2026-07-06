"""render_tier_table tests (0.64 port follow-up — coverage upstream carries in
tests/test_tier_resolver.py::test_skill_registry_sync; the Codex plan SKILL.md does not
embed the generated block, so the port covers the renderer behaviorally instead).

Loads the module the same way the sibling fleet_commons tests do, with
FLEET_COMMONS_ROOT pinned to this checkout's fleet-core so resolution is deterministic.
"""

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
    spec = importlib.util.spec_from_file_location(f"fc_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


render_tier_table = _load("render_tier_table")

# Minimal injected policy covering every key _ROW_SPECS references.
_POLICY = {
    "judgment": {
        "default_model": "opus",
        "default_effort": "high",
        "rationale": "judgment rationale",
    },
    "mechanical": {
        "default_model": "sonnet",
        "default_effort": "medium",
        "rationale": "mechanical rationale",
    },
    "purely-mechanical": {
        "default_model": "haiku",
        "default_effort": "low",
        "rationale": "purely mechanical rationale",
    },
    "read-only-survey": {
        "default_model": "sonnet",
        "default_effort": "low",
        "rationale": "survey rationale",
    },
    "offload": {
        "default_model": "sonnet",
        "default_effort": "medium",
        "rationale": "offload rationale",
    },
    "second-opinion": {
        "default_model": "opus",
        "default_effort": "high",
        "rationale": "second-opinion rationale",
    },
}


def test_render_rows_covers_every_row_spec() -> None:
    rows = render_tier_table.render_rows(_POLICY)
    assert len(rows) == len(render_tier_table._ROW_SPECS)
    labels = [label for label, _, _ in rows]
    assert labels == [label for label, _ in render_tier_table._ROW_SPECS]


def test_tier_cell_single_and_split_rows() -> None:
    rows = dict((label, tier) for label, tier, _ in render_tier_table.render_rows(_POLICY))
    assert rows["Judgment, design, adversarial review, architectural decisions"] == "`opus / high`"
    # The mechanical row spans two registry keys and preserves the sonnet-vs-haiku split.
    mechanical = rows["Mechanical, deterministic, scripted transforms, scaffolding"]
    assert mechanical == "`sonnet / medium` (or `haiku / low` for purely mechanical)"


def test_render_table_shape_and_content() -> None:
    table = render_tier_table.render_table(_POLICY)
    lines = table.splitlines()
    assert lines[0] == "| Work shape | Default tier | Rationale |"
    assert lines[1] == "|---|---|---|"
    assert len(lines) == 2 + len(render_tier_table._ROW_SPECS)
    assert "offload rationale" in table
    assert "judgment rationale; " not in table  # single-key rows are not joined


def test_render_block_is_marker_delimited() -> None:
    block = render_tier_table.render_block(_POLICY)
    assert block.startswith(render_tier_table.TIER_TABLE_BEGIN)
    assert block.endswith(render_tier_table.TIER_TABLE_END)
    assert render_tier_table.render_table(_POLICY) in block


def test_render_against_live_registry_and_seeded_divergence() -> None:
    """The live tier_policy.json renders cleanly, and a seeded divergence is visible —
    the property upstream's skill_registry_sync drift guard relies on."""
    fresh = render_tier_table.render_block()
    assert render_tier_table.TIER_TABLE_BEGIN in fresh
    assert "`opus / high`" in fresh
    divergent = fresh.replace("`opus / high`", "`opus / medium`", 1)
    assert divergent != fresh


def test_main_prints_block(capsys) -> None:
    assert render_tier_table.main([]) == 0
    out = capsys.readouterr().out
    assert render_tier_table.TIER_TABLE_BEGIN in out
    assert out.strip().endswith(render_tier_table.TIER_TABLE_END)
