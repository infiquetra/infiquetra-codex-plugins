"""U3: roster / validator / palette three-way tier drift guard.

The team-execution agent roster (25 TOMLs), the validator's model-hint expectations, and the
canonical fleet-core palette must agree by construction. Each TOML carries a ``source_model``
lineage tier plus its ``codex_model_hint`` header and ``model_reasoning_effort``; all three
are now a single projection of the palette's ``codex_tier`` mapping. This test fails loudly if
any of the three drifts from the palette.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

PLUGIN_ROOT = Path(__file__).parents[1]
AGENTS_DIR = PLUGIN_ROOT / "agents"
SCRIPTS = PLUGIN_ROOT / "scripts"
REPO_ROOT = PLUGIN_ROOT.parents[1]

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fleet_commons_shim  # noqa: E402

_PALETTE = fleet_commons_shim.load("tier_palette")

_SOURCE_MODEL_RE = re.compile(r'^# source_model = "(?P<model>[^"]+)"$', re.MULTILINE)
_CODEX_HINT_RE = re.compile(r'^# codex_model_hint = "(?P<model>[^"]+)"$', re.MULTILINE)


def _toml_files() -> list[Path]:
    return sorted(AGENTS_DIR.glob("*.toml"))


def test_roster_is_non_empty() -> None:
    assert _toml_files(), "expected team-execution agent TOMLs"


def test_every_agent_agrees_with_palette() -> None:
    for path in _toml_files():
        text = path.read_text(encoding="utf-8")
        source_match = _SOURCE_MODEL_RE.search(text)
        assert source_match, f"{path.name}: missing source_model"
        source_model = source_match.group("model")
        assert source_model in _PALETTE.MODELS, f"{path.name}: {source_model} not in palette"

        expected_model, expected_effort = _PALETTE.codex_tier(source_model)

        hint_match = _CODEX_HINT_RE.search(text)
        assert hint_match, f"{path.name}: missing codex_model_hint"
        assert hint_match.group("model") == expected_model, (
            f"{path.name}: codex_model_hint {hint_match.group('model')} != palette "
            f"{expected_model}"
        )

        payload = tomllib.loads(text)
        assert payload.get("model_reasoning_effort") == expected_effort, (
            f"{path.name}: model_reasoning_effort {payload.get('model_reasoning_effort')} "
            f"!= palette {expected_effort}"
        )


def test_validator_hints_are_palette_projection() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import scripts.validate_codex_plugins as validator

    expected = {model: _PALETTE.codex_tier(model) for model in _PALETTE.MODELS}
    assert validator.TEAM_EXECUTION_MODEL_HINTS == expected
