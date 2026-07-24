from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/portability/ports/2026-07-24-codex-v2-orchestration.json"
CLASSIFICATION = (
    ROOT / "docs/portability/classifications/2026-07-24-codex-v2-orchestration.md"
)
HISTORICAL_MANIFEST = ROOT / "docs/portability/ports/2026-07-10-saga-07517.json"


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_v2_contract_freezes_the_review_and_validator_lineage() -> None:
    manifest = _load(MANIFEST)
    source = manifest["source"]
    assert isinstance(source, dict)

    assert source["base_ref"] == "9470edca65b1db06d2f7562eeb2d5a9e48c34dec"
    assert source["target_ref"] == "46fefb6f17f0c9d0d63858978536d3369ab57dfe"
    assert source["pathspecs"] == [
        "plugins/team-execution/skills/team-execution/references/reviewer-registry.md",
        "plugins/team-execution/skills/team-execution/references/validator-registry.md",
    ]
    rows = source["rows"]
    assert isinstance(rows, list)
    assert len(rows) == source["expected_count"] == 2
    assert {row["treatment"] for row in rows} == {"codex-adapt"}
    assert {row["state"] for row in rows} == {"classified"}
    assert {tuple(row["units"]) for row in rows} == {("U6",)}
    assert all(row["capability_refs"] for row in rows)
    assert all(row["codex_invariant_refs"] for row in rows)


def test_v2_contract_binds_schema_r3_and_mints_release_versions_in_u8() -> None:
    manifest = _load(MANIFEST)
    authority = manifest["authority"]
    assert isinstance(authority, dict)
    snapshot = authority["capability_snapshot"]
    assert isinstance(snapshot, dict)
    assert snapshot["schema_version"] == 2
    assert snapshot["schema_path"] == (
        "docs/validation/codex-runtime-capability-snapshot.schema-r3.json"
    )

    codex = manifest["codex"]
    assert isinstance(codex, dict)
    assert codex["historical_plan_base"] == codex["execution_base"]
    assert codex["evidence_ref"] == "refs/tags/evidence/codex-v2-orchestration-20260724"
    assert codex["expected_count"] == 0
    assert codex["rows"] == []

    policies = manifest["version_policy"]
    assert isinstance(policies, list)
    assert {row["current_codex_identity"] for row in policies} == {
        "fleet-core",
        "saga",
        "verified-workflows",
    }
    assert {row["release_unit"] for row in policies} == {"U8"}
    assert {row["target_codex_version"] for row in policies} == {
        "0.11.0+codex.20260724175626",
        "0.79.0+codex.20260724175626",
        "2.0.0+codex.20260724175626",
    }


def test_v2_classification_is_rendered_and_historical_contract_is_unchanged() -> None:
    rendered = CLASSIFICATION.read_text(encoding="utf-8")
    assert "codex-v2-orchestration-2026-07-24" in rendered
    assert "src-7ca0384cf8d21d44" in rendered
    assert "src-76516b36df832272" in rendered
    assert "fleet-core 0.11.0+codex.20260724175626" in rendered
    assert "saga 0.79.0+codex.20260724175626" in rendered
    assert "verified-workflows 2.0.0+codex.20260724175626" in rendered

    digest = hashlib.sha256(HISTORICAL_MANIFEST.read_bytes()).hexdigest()
    assert digest == "1da9e147b0c59bf306e987f9e6e3f29d1c24be57e2d2ab5db6f483afa6cac498"
