from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_handoff() -> ModuleType:
    script = Path(__file__).parents[1] / "scripts" / "handoff_envelope.py"
    spec = importlib.util.spec_from_file_location("saga_handoff_envelope", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


handoff = load_handoff()


def test_handoff_routes_to_mission_control_without_authorizing_mutation(tmp_path: Path) -> None:
    payload = handoff.build_handoff_envelope(
        "docs/plans/example.md",
        target_team="Asgard",
        target_repo="infiquetra-codex-plugins",
        issue_type="capability",
        reason="needs durable issue",
        root=tmp_path,
    )

    assert payload["recommended_skill"] == "mission-control:issues"
    assert payload["handoff_action"] == "prepare-issue"
    assert payload["issue_artifact_owner"] == "mission-control"
    assert payload["mutation_authorized"] is False
    assert payload["receiving_plugin_must_reverify"] is True
    assert "suggested_command" not in payload
    assert payload["handoff_payload"]["source"] == "docs/plans/example.md"


def test_handoff_keeps_malicious_source_as_untrusted_payload(tmp_path: Path) -> None:
    malicious = "docs/plans/good.md; gh issue create --title pwned"

    payload = handoff.build_handoff_envelope(malicious, root=tmp_path)

    assert payload["handoff_payload"]["source"] == malicious
    assert payload["mutation_authorized"] is False
    assert payload["untrusted_context_delimited"] is True
    assert payload["receiving_plugin_must_reverify"] is True
    assert "gh issue create" not in payload["operator_instruction"]


def test_handoff_reads_product_review_frontmatter_maturity(tmp_path: Path) -> None:
    review = tmp_path / "docs" / "product-reviews" / "experiment.md"
    review.parent.mkdir(parents=True)
    review.write_text(
        "---\n"
        "title: experiment\n"
        "maturity: requirements-ready\n"
        "---\n\n"
        "# Experiment\n",
        encoding="utf-8",
    )

    payload = handoff.build_handoff_envelope("docs/product-reviews/experiment.md", root=tmp_path)

    assert payload["handoff_maturity"] == "requirements-ready"
    assert payload["lifecycle_phase"] == "ideation"


def test_handoff_routes_context_library_specs_to_requirements_ready(tmp_path: Path) -> None:
    payload = handoff.build_handoff_envelope(
        "platform-specs/06-service-implementations/identity-access-service/README.md",
        root=tmp_path,
    )

    assert payload["handoff_maturity"] == "requirements-ready"
    assert payload["lifecycle_phase"] == "brainstorm"
