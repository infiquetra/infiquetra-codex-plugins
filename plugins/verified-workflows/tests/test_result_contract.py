from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
TESTS = Path(__file__).parent
for path in (SCRIPTS, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import result_contract as R  # noqa: E402
from test_workflow_dispatch import compile_fixture  # noqa: E402


def launch(assignment_id: str = "test"):
    return next(
        spec for spec in compile_fixture().launch_specs if spec.assignment_id == assignment_id
    )


def finding() -> dict[str, object]:
    return {
        "finding_id": "finding-1",
        "severity": "P2",
        "category": "correctness",
        "location": "tests/test_feature.py",
        "impact": "missed edge case",
        "fix": "add the case",
        "validation": "run the focused test",
        "resolved": False,
        "hard_stop": False,
    }


def result(*, assignment_id: str = "test", reviewer: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "assignment_id": assignment_id,
        "attempt_id": f"{assignment_id}-attempt-1",
        "agent_path": f"/root/{assignment_id}",
        "role_id": "devils-advocate-reviewer" if reviewer else "scenario-tester",
        "profile_id": "review_high" if reviewer else "test_medium",
        "terminal_status": "completed",
        "summary": "bounded task complete",
        "changed_paths": [] if reviewer else ["tests/test_feature.py"],
        "no_change": reviewer,
        "checks": [{"check_id": "focused", "status": "pass", "detail": "passed"}],
        "findings": [],
        "residual_risks": [],
    }
    if reviewer:
        payload.update(
            {
                "dimensions": [
                    {"dimension_id": "correctness", "score": 9.0, "notes": "sound"},
                    {"dimension_id": "risk", "score": 10.0, "notes": "bounded"},
                ],
                "exclusions": [],
                "denominator": 2,
                "overall": 9.5,
                "verdict": "accept",
                "hard_stop": False,
            }
        )
    return payload


def test_assignment_result_passes_and_is_normalized() -> None:
    normalized = R.validate_result(
        result(), launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
    )
    assert normalized["terminal_status"] == "completed"
    assert normalized["changed_paths"] == ["tests/test_feature.py"]


def test_reviewer_extension_validates_arithmetic() -> None:
    normalized = R.validate_result(
        result(assignment_id="review", reviewer=True),
        launch("review"),
        expected_attempt_id="review-attempt-1",
        expected_agent_path="/root/review",
    )
    assert normalized["overall"] == 9.5


def test_message_only_completion_is_rejected() -> None:
    with pytest.raises(R.ResultContractError, match="message is not completion"):
        R.validate_result(
            "done", launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
        )


def test_closed_schema_rejects_extra_fields() -> None:
    payload = result()
    payload["raw_output"] = "forbidden"
    with pytest.raises(R.ResultContractError, match="fields must be exactly"):
        R.validate_result(
            payload, launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
        )


def test_changed_path_outside_write_scope_fails() -> None:
    payload = result()
    payload["changed_paths"] = ["src/outside.py"]
    with pytest.raises(R.ResultContractError, match="exceed assignment writes"):
        R.validate_result(
            payload, launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
        )


def test_no_change_must_match_changed_paths() -> None:
    payload = result()
    payload["no_change"] = True
    with pytest.raises(R.ResultContractError, match="no_change"):
        R.validate_result(
            payload, launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
        )


def test_reviewer_arithmetic_drift_fails() -> None:
    payload = result(assignment_id="review", reviewer=True)
    payload["overall"] = 10.0
    with pytest.raises(R.ResultContractError, match="arithmetic mean"):
        R.validate_result(
            payload,
            launch("review"),
            expected_attempt_id="review-attempt-1",
            expected_agent_path="/root/review",
        )


def test_typed_finding_is_preserved() -> None:
    payload = copy.deepcopy(result())
    payload["findings"] = [finding()]
    normalized = R.validate_result(
        payload, launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
    )
    assert normalized["findings"][0]["severity"] == "P2"
