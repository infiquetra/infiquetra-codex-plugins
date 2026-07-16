"""Gate the focused Mission Control 2.10.1 to Codex 2.4.2 port contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import port_contract


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/portability/ports/2026-07-16-mission-control-2101.json"
CLASSIFICATION_PATH = (
    ROOT / "docs/portability/classifications/2026-07-16-mission-control-2101.md"
)

SOURCE_PATHS = [
    ".claude-plugin/marketplace.json",
    "plugins/mission-control/.claude-plugin/plugin.json",
    "plugins/mission-control/CHANGELOG.md",
    "plugins/mission-control/scripts/sdlc_manager.py",
    "plugins/mission-control/tests/test_board_move_exit.py",
    "plugins/mission-control/tests/test_prompt_alignment.py",
]

ADAPTED_ROWS = {
    "src-cb0788572d2f1cb5": (
        SOURCE_PATHS[1],
        "plugins/mission-control/.codex-plugin/plugin.json",
        "plugins/mission-control/tests/test_prompt_alignment.py",
    ),
    "src-97172da2308bf99e": (
        SOURCE_PATHS[2],
        "plugins/mission-control/CHANGELOG.md",
        "plugins/mission-control/tests/test_prompt_alignment.py",
    ),
    "src-8568d1b391a031f3": (
        SOURCE_PATHS[3],
        "plugins/mission-control/scripts/sdlc_manager.py",
        "plugins/mission-control/tests/test_board_move_exit.py",
    ),
    "src-6653531248eb6c51": (
        SOURCE_PATHS[4],
        "plugins/mission-control/tests/test_board_move_exit.py",
        "plugins/mission-control/tests/test_board_move_exit.py",
    ),
    "src-7acce98f94485e48": (
        SOURCE_PATHS[5],
        "plugins/mission-control/tests/test_prompt_alignment.py",
        "plugins/mission-control/tests/test_prompt_alignment.py",
    ),
}


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_classification_freezes_exact_authority_and_inventories() -> None:
    manifest = _manifest()
    source = manifest["source"]
    codex = manifest["codex"]

    assert manifest["port_id"] == "mission-control-board-move-fail-loud-2026-07-16"
    assert source["base_ref"] == "9adb971020df9eb5928595760b5e9c75e498ef2c"
    assert source["target_ref"] == "5d4dfb2e1d0be5abbe9f3a693e33d152ba7cfcba"
    assert source["pathspecs"] == SOURCE_PATHS
    assert source["expected_count"] == len(source["rows"]) == 6
    assert source["inventory_sha256"] == (
        "5f989d44300e4630347c36e840cfb6dc9d62d87f72b2690e61b35016dc46167a"
    )
    assert port_contract.inventory_digest(source["rows"]) == source["inventory_sha256"]

    assert codex["historical_plan_base"] == "7b429f765eea2afca3bba63b5c498dc8efb219ff"
    assert codex["execution_base"] == codex["historical_plan_base"]
    assert codex["expected_count"] == len(codex["rows"]) == 0
    assert codex["inventory_sha256"] == (
        "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
    )


def test_classification_has_one_explicit_treatment_per_source_row() -> None:
    rows = {row["row_id"]: row for row in _manifest()["source"]["rows"]}

    assert set(rows) == {"src-63823a1533d83eba", *ADAPTED_ROWS}
    rejected = rows["src-63823a1533d83eba"]
    assert rejected["new_path"] == SOURCE_PATHS[0]
    assert rejected["state"] == "classified"
    assert rejected["treatment"] == "reject"
    assert rejected["units"] == []
    assert rejected["planned_targets"] == []
    assert rejected["planned_tests"] == []
    assert rejected["rationale"]

    for row_id, (source_path, target, test) in ADAPTED_ROWS.items():
        row = rows[row_id]
        assert row["new_path"] == source_path
        assert row["state"] in {"classified", "implemented", "verified"}
        assert row["treatment"] == "codex-adapt"
        assert row["units"] == ["U2"]
        assert row["planned_targets"] == [target]
        assert row["planned_tests"] == [test]
        assert row["host_primitives"] == []
        assert row["rationale"]


def test_classification_authority_hashes_and_render_are_current() -> None:
    manifest = _manifest()
    authority = manifest["authority"]
    artifacts = [authority["plan"], *authority["reviews"], authority["runbook"]]

    for artifact in artifacts:
        assert _sha256(ROOT / artifact["path"]) == artifact["sha256"]
    capability = authority["capability_snapshot"]
    assert _sha256(ROOT / capability["path"]) == capability["sha256"]
    assert _sha256(ROOT / capability["schema_path"]) == capability["schema_sha256"]
    assert CLASSIFICATION_PATH.read_text(encoding="utf-8") == (
        port_contract.render_manifest(manifest)
    )


def test_classification_preserves_independent_codex_version_lineage() -> None:
    assert _manifest()["version_policy"] == [
        {
            "current_codex_identity": "mission-control",
            "current_codex_version": "2.4.1",
            "policy": "lineage-with-codex-adaptation",
            "release_unit": "U2",
            "source_plugin": "mission-control",
            "source_version": "2.10.1",
            "target_codex_identity": "mission-control",
            "target_codex_version": "2.4.2",
        }
    ]
