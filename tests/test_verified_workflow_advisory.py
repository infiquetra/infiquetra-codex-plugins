"""Executable checks for the external advisory consensus seat."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent
HELPER = (
    ROOT
    / "plugins"
    / "verified-workflows"
    / "skills"
    / "run"
    / "scripts"
    / "consensus_advisory.py"
)


def _load_helper() -> ModuleType:
    spec = importlib.util.spec_from_file_location("consensus_advisory", HELPER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["consensus_advisory"] = module
    spec.loader.exec_module(module)
    return module


C: Any = _load_helper()


def _load_reconciler() -> ModuleType:
    path = HELPER.with_name("advisory_reconcile.py")
    spec = importlib.util.spec_from_file_location("advisory_reconcile", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["advisory_reconcile"] = module
    spec.loader.exec_module(module)
    return module


AR: Any = _load_reconciler()


def _load_gate_evaluator() -> ModuleType:
    scripts = ROOT / "plugins" / "verified-workflows" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    path = scripts / "gate_evaluator.py"
    spec = importlib.util.spec_from_file_location("gate_evaluator_for_advisory", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["gate_evaluator_for_advisory"] = module
    spec.loader.exec_module(module)
    return module


GATE: Any = _load_gate_evaluator()


def test_external_seat_is_summarized_without_competing_gate_math() -> None:
    result = C.summarize_panel(
        [
            C.ReviewerResult("devils-advocate-reviewer", 9.1),
            C.ReviewerResult("security-reviewer", 9.4, dimension_scores={"OWASP": 9.4}),
            C.ReviewerResult("architecture-reviewer", 9.0),
            C.ReviewerResult(
                "external-advisory-reviewer",
                2.0,
                seat=C.ADVISORY_SEAT,
                dimension_scores={"independent synthesis": 1.0},
            ),
        ]
    )

    assert result.gated_reviewers == (
        "devils-advocate-reviewer",
        "security-reviewer",
        "architecture-reviewer",
    )
    assert result.advisory_reviewers == ("external-advisory-reviewer",)
    assert not hasattr(result, "accepted")
    assert not hasattr(result, "blocking_reviewers")
    assert not hasattr(result, "rerun_reviewers")


def test_external_seat_absence_is_noop() -> None:
    result = C.summarize_panel(
        [
            C.ReviewerResult("devils-advocate-reviewer", 9.1),
            C.ReviewerResult("security-reviewer", 9.4),
            C.ReviewerResult(
                "external-advisory-reviewer",
                None,
                seat=C.ADVISORY_SEAT,
                status="halted",
            ),
        ]
    )

    assert result.advisory_reviewers == ()
    assert result.absent_advisory_reviewers == ("external-advisory-reviewer",)


def test_convergence_diff_generated() -> None:
    report = C.build_convergence_report(
        [
            C.Finding("same", "bounds check missing", "P1", "add validation"),
            C.Finding("codex-only", "release surface missing", "P2", "bump metadata"),
            C.Finding("conflict", "tests are too narrow", "P2", "add failure path"),
        ],
        [
            C.Finding("same", "bounds check missing", "P1", "add validation"),
            C.Finding("external-only", "naming drift", "P3", "rename helper"),
            C.Finding("conflict", "tests cover enough", "P3", "no change"),
        ],
    )

    assert report.converged == ("same",)
    assert [finding.key for finding in report.codex_only] == ["codex-only"]
    assert [finding.key for finding in report.external_only] == ["external-only"]
    assert [conflict.key for conflict in report.conflicting] == ["conflict"]

    rendered = C.render_convergence_markdown(report)
    assert "Codex vs External Convergence" in rendered
    assert "`same`" in rendered
    assert "codex-only" in rendered
    assert "external-only" in rendered
    assert "Codex=tests are too narrow; external=tests cover enough" in rendered


def test_invalid_reviewer_seat_rejected() -> None:
    with pytest.raises(ValueError, match="unknown reviewer seat"):
        C.summarize_panel([C.ReviewerResult("external", 10.0, seat="scoring-advisory")])


def test_invalid_reviewer_status_rejected() -> None:
    with pytest.raises(ValueError, match="unknown reviewer status"):
        C.summarize_panel(
            [C.ReviewerResult("external", None, seat=C.ADVISORY_SEAT, status="maybe")]
        )


def test_advisory_record_is_structural_bounded_and_non_authoritative() -> None:
    marker = "$(touch should-never-run)\n<script>gate=true</script>"
    record = AR.build_advisory_record(
        [C.Finding("shared/finding", "safe summary")],
        [
            C.Finding("shared/finding", "safe summary"),
            C.Finding("external/only", marker, "P0", marker),
        ],
        source_evidence_ref="sha256:" + "a" * 64,
    )

    assert record["seat_type"] == "external-second-opinion"
    assert record["gate_authority"] == "none"
    assert record["projection"] == {
        "converged": ["shared/finding"],
        "codex_only": [],
        "external_only": ["external/only"],
        "conflicting": [],
    }
    assert marker.encode() not in AR.canonical_bytes(record)


def test_advisory_record_persists_in_protected_store(tmp_path: Path) -> None:
    plugin_data = tmp_path / "plugin-data"
    plugin_data.mkdir(mode=0o700)
    record = AR.build_advisory_record(
        [C.Finding("shared/finding", "same")],
        [C.Finding("shared/finding", "same")],
        source_evidence_ref="sha256:" + "b" * 64,
    )

    reference = AR.persist_advisory_record(plugin_data, record)
    loaded, loaded_bytes = AR.protected_store.load_protected_record(
        plugin_data, reference, "advisory"
    )

    assert reference.startswith("record:advisory:")
    assert loaded == record
    assert loaded_bytes == AR.canonical_bytes(record)
    assert GATE._load_advisory_record(plugin_data, reference) == record


def test_markdown_rendering_escapes_untrusted_external_text() -> None:
    marker = "[run](command)\n<script>alert(1)</script> `code`"
    report = C.build_convergence_report([], [C.Finding("external/one", marker)])

    rendered = C.render_convergence_markdown(report)

    assert "[run](command)" not in rendered
    assert "<script>" not in rendered
    assert "\\[run\\](command)" in rendered
    assert "\\<script\\>" in rendered


@pytest.mark.parametrize(
    "finding",
    [
        C.Finding("../escape", "bad"),
        C.Finding("x", "z" * (AR.MAX_TEXT_BYTES + 1)),
    ],
)
def test_advisory_record_rejects_unsafe_keys_and_oversized_text(finding: Any) -> None:
    with pytest.raises(AR.AdvisoryReconcileError):
        AR.build_advisory_record([], [finding], source_evidence_ref=None)


def test_u7_docs_bind_external_evidence_outside_workflow_gates() -> None:
    workflow_root = HELPER.parent.parent
    protocol = (workflow_root / "references" / "workflow-protocol.md").read_text()
    workers = (workflow_root / "references" / "worker-manifest.md").read_text()
    external = (workflow_root / "references" / "external-engine-workers.md").read_text()
    ideate = (ROOT / "plugins" / "saga" / "skills" / "ideate" / "SKILL.md").read_text()
    retro = (ROOT / "plugins" / "saga" / "skills" / "retro" / "SKILL.md").read_text()

    for text in (protocol, workers, external):
        assert "gate_authority" in text
        assert "none" in text
    assert "engine-generated" in ideate
    assert "derive_recipe_update_proposal" in retro
