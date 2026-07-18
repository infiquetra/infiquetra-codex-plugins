from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import dispatch_receipt as facade  # noqa: E402
import workspace_evidence as evidence  # noqa: E402


def test_facade_preserves_workspace_evidence_api() -> None:
    assert facade.create_workflow_run_record is evidence.create_workflow_run_record
    assert facade.create_subject_record is evidence.create_subject_record
    assert facade.create_workspace_snapshot_record is evidence.create_workspace_snapshot_record
    assert facade.create_mutation_audit_record is evidence.create_mutation_audit_record


def test_workspace_evidence_remains_bounded() -> None:
    assert len(Path(evidence.__file__).read_text(encoding="utf-8").splitlines()) < 1800


def test_subject_exclusion_parents_are_immediate() -> None:
    assert evidence._subject_exclusion_parent_paths(
        ("top-level.txt", "docs/generated/output.json", "nested/tree")
    ) == frozenset({".", "docs/generated", "nested"})
