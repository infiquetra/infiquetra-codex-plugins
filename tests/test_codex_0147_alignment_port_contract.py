"""Contract tests for the staged Codex 0.147.0 alignment port."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts import port_contract


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "docs/portability/ports/2026-08-08-codex-0147-alignment.json"
)
CLASSIFICATION_PATH = (
    ROOT / "docs/portability/classifications/2026-08-08-codex-0147-alignment.md"
)
PRE_EXTENSION_MANIFESTS = (
    ROOT / "docs/portability/ports/2026-07-29-codex-0146-native-harness.json",
    ROOT / "docs/portability/ports/2026-07-29-codex-0146-cross-plugin-alignment.json",
)
EXPECTED_PATHSPECS = [
    "codex-rs/core/src/tools/handlers/multi_agents_common.rs",
    "codex-rs/core/src/tools/spec_plan.rs",
    "codex-rs/core/config.schema.json",
    "codex-rs/core/src/agent/role.rs",
    "codex-rs/core/src/agent/control/spawn.rs",
    "codex-rs/ext/skills/src/tools/read.rs",
    "codex-rs/ext/skills/src/provider/executor.rs",
    "codex-rs/core-plugins/src/agent_plugin_manifest.rs",
    "codex-rs/app-server-protocol/src/protocol/v2/plugin_search.rs",
    "codex-rs/core-plugins/src/marketplace.rs",
    "codex-rs/core/src/tools/handlers/multi_agents_spec.rs",
    "codex-rs/protocol/src/protocol.rs",
]
CAPABILITY_BINDING_ERRORS = {
    "capability snapshot Codex historical plan base does not match the port contract",
    "capability snapshot Codex execution base does not match the port contract",
    "capability snapshot Claude source base does not match the port contract",
    "capability snapshot Claude source target does not match the port contract",
}
MISMATCHED_SNAPSHOT_REFS = {
    "codex_historical_plan_base": "1" * 40,
    "codex_execution_base": "2" * 40,
    "source_base": "3" * 40,
    "source_target": "4" * 40,
}


def _manifest() -> dict:
    return port_contract.load_manifest(MANIFEST_PATH)


@pytest.fixture
def manifest_with_mismatched_snapshot_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    manifest = _manifest()
    real_loads = port_contract.json.loads

    def loads_with_mismatched_snapshot_refs(
        payload: str | bytes | bytearray,
        *args: object,
        **kwargs: object,
    ) -> object:
        value = real_loads(payload, *args, **kwargs)
        if not (
            isinstance(value, dict)
            and {"refs", "runtime", "catalog"}.issubset(value)
        ):
            return value
        snapshot = copy.deepcopy(value)
        snapshot["refs"]["codex"]["historical_plan_base"] = (
            MISMATCHED_SNAPSHOT_REFS["codex_historical_plan_base"]
        )
        snapshot["refs"]["codex"]["execution_base"] = MISMATCHED_SNAPSHOT_REFS[
            "codex_execution_base"
        ]
        snapshot["refs"]["claude"]["source_base"] = MISMATCHED_SNAPSHOT_REFS[
            "source_base"
        ]
        snapshot["refs"]["claude"]["source_target"] = MISMATCHED_SNAPSHOT_REFS[
            "source_target"
        ]
        return snapshot

    monkeypatch.setattr(port_contract.json, "loads", loads_with_mismatched_snapshot_refs)
    return manifest


def _capability_binding_errors(errors: list[str]) -> set[str]:
    return {
        error
        for error in errors
        if "capability snapshot" in error
        and "does not match the port contract" in error
    }


def test_divergent_topology_round_trips(tmp_path: Path) -> None:
    manifest = _manifest()
    topology = manifest["source"]["topology"]
    round_trip_path = tmp_path / "port.json"

    port_contract.write_json(round_trip_path, manifest)
    round_trip = port_contract.load_manifest(round_trip_path)

    assert round_trip["source"]["topology"] == topology
    assert topology == {
        "common_base": "95637f7056835fea66bdd0044414af480fc0fd74",
        "left": {
            "peeled_commit": "79b4f03d35962b005b007a015113b38930711665",
            "tag": "rust-v0.146.1",
        },
        "left_only_commits": [
            {
                "commit": "7558bede75dd7f9ed96c4ff00ccc6b28ded01159",
                "disposition": (
                    "Behavior is present in rust-v0.147.0 through its mainline implementation; "
                    "exclude this left-only backport commit from the focused diff."
                ),
            },
            {
                "commit": "79b4f03d35962b005b007a015113b38930711665",
                "disposition": (
                    "This commit records the rust-v0.146.1 release only; exclude it from the "
                    "focused diff."
                ),
            },
        ],
        "right": {
            "peeled_commit": "be6e8eac029b183056b7e4402879f15d2c85f61b",
            "tag": "rust-v0.147.0",
        },
    }
    assert manifest["source"]["pathspecs"] == EXPECTED_PATHSPECS
    assert CLASSIFICATION_PATH.read_text(encoding="utf-8") == port_contract.render_manifest(
        manifest
    )


def test_manifest_missing_common_base_fails_classification() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["source"]["topology"].pop("common_base")

    errors = port_contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any(
        "source.topology keys mismatch" in error and "common_base" in error
        for error in errors
    )


def test_left_only_commit_without_disposition_fails_classification() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["source"]["topology"]["left_only_commits"][0].pop("disposition")

    errors = port_contract.validate_manifest(ROOT, manifest, stage="classification")

    assert any(
        "source.topology.left_only_commits[0] keys mismatch" in error
        and "disposition" in error
        for error in errors
    )


def test_pre_extension_contracts_still_validate() -> None:
    for path in PRE_EXTENSION_MANIFESTS:
        errors = port_contract.validate_manifest(
            ROOT,
            port_contract.load_manifest(path),
            stage="classification",
        )
        assert errors == [], path.name


def test_codex_0147_alignment_manifest_passes_classification() -> None:
    assert port_contract.validate_manifest(ROOT, _manifest(), stage="classification") == []


def test_staged_topology_exempts_mismatched_capability_snapshot_refs(
    manifest_with_mismatched_snapshot_refs: dict,
) -> None:
    manifest = manifest_with_mismatched_snapshot_refs
    assert manifest["port_id"] not in port_contract.CURRENT_PORT_IDS

    errors = port_contract.validate_manifest(ROOT, manifest, stage="classification")

    assert errors == []
    assert _capability_binding_errors(errors) == set()


def test_promoted_topology_restores_all_capability_snapshot_ref_bindings(
    manifest_with_mismatched_snapshot_refs: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = manifest_with_mismatched_snapshot_refs
    monkeypatch.setattr(
        port_contract,
        "CURRENT_PORT_IDS",
        {*port_contract.CURRENT_PORT_IDS, manifest["port_id"]},
    )

    errors = port_contract.validate_manifest(ROOT, manifest, stage="classification")

    assert _capability_binding_errors(errors) == CAPABILITY_BINDING_ERRORS


def test_staged_manifest_without_topology_keeps_all_snapshot_ref_bindings(
    manifest_with_mismatched_snapshot_refs: dict,
) -> None:
    manifest = manifest_with_mismatched_snapshot_refs
    manifest["source"].pop("topology")
    assert manifest["port_id"] not in port_contract.CURRENT_PORT_IDS

    errors = port_contract.validate_manifest(ROOT, manifest, stage="classification")

    assert _capability_binding_errors(errors) == CAPABILITY_BINDING_ERRORS
