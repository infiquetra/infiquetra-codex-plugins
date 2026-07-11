from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import dispatch_receipt as facade  # noqa: E402
import workflow_records as records  # noqa: E402


def test_facade_preserves_workflow_record_api() -> None:
    assert facade.create_intent_record is records.create_intent_record
    assert facade.create_result_record is records.create_result_record
    assert facade.create_resolution_record is records.create_resolution_record
    assert facade.create_root_verification_record is records.create_root_verification_record
    assert facade.persist_normalized is records.persist_normalized
    assert facade.recover_normalization_commit is records.recover_normalization_commit


def test_workflow_records_remains_smaller_than_legacy_facade() -> None:
    assert len(Path(records.__file__).read_text(encoding="utf-8").splitlines()) < 3500
