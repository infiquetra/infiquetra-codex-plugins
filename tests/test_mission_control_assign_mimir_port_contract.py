"""Gate the focused Mission Control 2.10.0 to Codex 2.4.0 port contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import port_contract


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/portability/ports/2026-07-14-mission-control-2100.json"
CLASSIFICATION_PATH = ROOT / "docs/portability/classifications/2026-07-14-mission-control-2100.md"

SOURCE_PATHS = [
    "plugins/mission-control/.claude-plugin/plugin.json",
    "plugins/mission-control/CHANGELOG.md",
    "plugins/mission-control/README.md",
    "plugins/mission-control/scripts/sdlc_manager.py",
    "plugins/mission-control/skills/flow/SKILL.md",
    "plugins/mission-control/skills/issues/SKILL.md",
    "plugins/mission-control/tests/test_assign_mimir.py",
    "plugins/mission-control/tests/test_prompt_alignment.py",
]

EXPECTED_ROWS = {
    "src-cb0788572d2f1cb5": (
        SOURCE_PATHS[0],
        "plugins/mission-control/.codex-plugin/plugin.json",
        "plugins/mission-control/tests/test_prompt_alignment.py",
    ),
    "src-97172da2308bf99e": (
        SOURCE_PATHS[1],
        "plugins/mission-control/CHANGELOG.md",
        "plugins/mission-control/tests/test_prompt_alignment.py",
    ),
    "src-f3ca108fe3b1bb10": (
        SOURCE_PATHS[2],
        "plugins/mission-control/README.md",
        "plugins/mission-control/tests/test_prompt_alignment.py",
    ),
    "src-8568d1b391a031f3": (
        SOURCE_PATHS[3],
        "plugins/mission-control/scripts/sdlc_manager.py",
        "plugins/mission-control/tests/test_assign_mimir.py",
    ),
    "src-9a03ccbd6eef0110": (
        SOURCE_PATHS[4],
        "plugins/mission-control/skills/flow/SKILL.md",
        "plugins/mission-control/tests/test_prompt_alignment.py",
    ),
    "src-c9844af1dfc2ccb7": (
        SOURCE_PATHS[5],
        "plugins/mission-control/skills/issues/SKILL.md",
        "plugins/mission-control/tests/test_prompt_alignment.py",
    ),
    "src-4c65cb3b2e99165a": (
        SOURCE_PATHS[6],
        "plugins/mission-control/tests/test_assign_mimir.py",
        "plugins/mission-control/tests/test_assign_mimir.py",
    ),
    "src-7acce98f94485e48": (
        SOURCE_PATHS[7],
        "plugins/mission-control/tests/test_prompt_alignment.py",
        "plugins/mission-control/tests/test_prompt_alignment.py",
    ),
}


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_contract_freezes_exact_authority_and_inventories() -> None:
    manifest = _manifest()
    source = manifest["source"]
    codex = manifest["codex"]

    assert manifest["port_id"] == "mission-control-assign-mimir-2026-07-14"
    assert source["base_ref"] == "1457aed6ee2d3a58900bc4b069871609d2fd166a"
    assert source["target_ref"] == "9adb971020df9eb5928595760b5e9c75e498ef2c"
    assert source["pathspecs"] == SOURCE_PATHS
    assert source["expected_count"] == len(source["rows"]) == 8
    assert source["inventory_sha256"] == (
        "5fb3eac32977a1d1987bd1a9fb77c1453a39a64918f0f76b4701394e463d8b8f"
    )
    assert port_contract.inventory_digest(source["rows"]) == source["inventory_sha256"]

    assert codex["historical_plan_base"] == ("fc077d4f4485a7f2398a7b201947479d998e0a33")
    assert codex["execution_base"] == codex["historical_plan_base"]
    assert codex["expected_count"] == len(codex["rows"]) == 0
    assert codex["inventory_sha256"] == (
        "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
    )
    assert codex["evidence_ref"] == ("refs/tags/evidence/mission-control-assign-mimir-20260714")


def test_every_source_row_has_one_explicit_codex_adaptation() -> None:
    rows = {row["row_id"]: row for row in _manifest()["source"]["rows"]}

    assert set(rows) == set(EXPECTED_ROWS)
    for row_id, (source_path, target, test) in EXPECTED_ROWS.items():
        row = rows[row_id]
        assert row["new_path"] == source_path
        assert row["state"] in {"classified", "implemented", "verified"}
        assert row["treatment"] == "codex-adapt"
        assert row["units"] == ["U2"]
        assert row["planned_targets"] == [target]
        assert row["planned_tests"] == [test]
        assert row["host_primitives"] == []
        assert row["rationale"]


def test_authority_hashes_and_generated_classification_are_current() -> None:
    manifest = _manifest()
    authority = manifest["authority"]
    artifacts = [authority["plan"], *authority["reviews"]]

    for artifact in artifacts:
        assert _sha256(ROOT / artifact["path"]) == artifact["sha256"]
    runbook = authority["runbook"]
    assert port_contract._historical_file_by_sha256(
        ROOT, runbook["path"], runbook["sha256"]
    )
    capability = authority["capability_snapshot"]
    assert _sha256(ROOT / capability["path"]) == capability["sha256"]
    assert _sha256(ROOT / capability["schema_path"]) == capability["schema_sha256"]
    assert CLASSIFICATION_PATH.read_text(encoding="utf-8") == (
        port_contract.render_manifest(manifest)
    )


def test_version_policy_preserves_independent_codex_lineage() -> None:
    assert _manifest()["version_policy"] == [
        {
            "current_codex_identity": "mission-control",
            "current_codex_version": "2.3.0",
            "policy": "lineage-with-codex-adaptation",
            "release_unit": "U2",
            "source_plugin": "mission-control",
            "source_version": "2.10.0",
            "target_codex_identity": "mission-control",
            "target_codex_version": "2.4.0",
        }
    ]
