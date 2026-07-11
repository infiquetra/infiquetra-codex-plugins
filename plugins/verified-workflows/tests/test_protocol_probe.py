from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import protocol_probe as P  # noqa: E402

SNAPSHOT = Path(__file__).parents[3] / "docs" / "validation" / "codex-runtime-capability-snapshot.json"


def snapshot() -> tuple[dict[str, object], str]:
    payload, digest = P._read_snapshot(SNAPSHOT)
    return payload, digest


def test_current_generic_surface_is_inline_only() -> None:
    value, digest = snapshot()
    result = P.probe_protocol(snapshot=value, snapshot_sha256=digest)
    assert result["claim"] == "unit-fixture-only"
    assert result["runtime_proof"] is False
    assert result["spawn_surface"] == "generic"
    assert result["outcome"] == "inline-only"


@pytest.mark.parametrize("surface", ["absent", "backpressure", "capacity-zero"])
def test_preferred_independence_degrades_truthfully(surface: str) -> None:
    value, digest = snapshot()
    result = P.probe_protocol(
        snapshot=value, snapshot_sha256=digest, spawn_surface=surface
    )
    assert result["outcome"] == "inline-only"


def test_required_independence_blocks_without_named_proof() -> None:
    value, digest = snapshot()
    result = P.probe_protocol(
        snapshot=value,
        snapshot_sha256=digest,
        spawn_surface="generic",
        independence="required",
    )
    assert result["outcome"] == "blocked"


def test_named_pair_remains_fixture_candidate_not_runtime_claim() -> None:
    value, digest = snapshot()
    result = P.probe_protocol(
        snapshot=value,
        snapshot_sha256=digest,
        spawn_surface="named",
        hook_pair="present",
    )
    assert result["outcome"] == "attestation-candidate"
    assert "verified-workflow-subagent" not in json.dumps(result)


def test_deterministic_path_is_model_free_fixture() -> None:
    value, digest = snapshot()
    result = P.probe_protocol(
        snapshot=value,
        snapshot_sha256=digest,
        role_kind="deterministic-validator",
        independence="n/a",
    )
    assert result["outcome"] == "deterministic-tool-candidate"


def test_probe_contains_no_process_or_collaboration_launcher() -> None:
    source = (SCRIPTS / "protocol_probe.py").read_text()
    assert "subprocess" not in source
    assert "spawn_agent" not in source
    assert "collaboration." not in source
