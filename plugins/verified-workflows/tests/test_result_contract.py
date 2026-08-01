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
        "scope_disposition": "planned",
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


def test_declared_changed_paths_synthesize_no_finding() -> None:
    normalized = R.validate_result(
        result(), launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
    )
    assert normalized["findings"] == []


def test_changed_path_outside_write_scope_becomes_a_synthesized_finding() -> None:
    payload = result()
    payload["changed_paths"] = ["src/outside.py"]
    normalized = R.validate_result(
        payload, launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
    )
    assert normalized["changed_paths"] == ["src/outside.py"]
    assert len(normalized["findings"]) == 1
    synthesized = normalized["findings"][0]
    assert synthesized["severity"] == "P2"
    assert synthesized["category"] == "operations"
    assert synthesized["scope_disposition"] == "one-hop"
    assert synthesized["resolved"] is False
    assert synthesized["hard_stop"] is False
    assert synthesized["location"] == "src/outside.py"
    assert synthesized["finding_id"].startswith(R.UNDECLARED_WRITE_FINDING_PREFIX)
    for field in ("impact", "fix", "validation"):
        assert "tests/test_feature.py" in synthesized[field]
    # The synthesized finding is validator-owned and stable across runs.
    assert synthesized == R.validate_result(
        payload, launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
    )["findings"][0]


def test_assignment_declaring_no_writes_reports_paths_instead_of_raising() -> None:
    from test_workflow_dispatch import assignment, git_operator, reviewer, worker

    contract = compile_fixture(
        [assignment("implement"), worker(), reviewer(), git_operator()]
    )
    spec = next(
        item for item in contract.launch_specs if item.assignment_id == "integrate"
    )
    assert spec.writes == ()
    payload = result()
    payload.update(
        {
            "assignment_id": "integrate",
            "attempt_id": "integrate-attempt-1",
            "agent_path": "/root/integrate",
            "role_id": "git-integration-operator",
            "profile_id": spec.agent_type,
            "changed_paths": ["src/feature.py"],
        }
    )
    normalized = R.validate_result(
        payload,
        spec,
        expected_attempt_id="integrate-attempt-1",
        expected_agent_path="/root/integrate",
    )
    assert len(normalized["findings"]) == 1
    assert normalized["findings"][0]["location"] == "src/feature.py"
    assert "declared no writes" in normalized["findings"][0]["impact"]


def test_agent_and_synthesized_findings_coexist_without_id_collision() -> None:
    payload = copy.deepcopy(result())
    payload["findings"] = [finding()]
    payload["changed_paths"] = ["tests/test_feature.py", "src/outside.py"]
    normalized = R.validate_result(
        payload, launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
    )
    ids = [item["finding_id"] for item in normalized["findings"]]
    assert len(ids) == 2
    assert len(set(ids)) == 2
    assert ids[0] == "finding-1"
    assert ids[1].startswith(R.UNDECLARED_WRITE_FINDING_PREFIX)


def test_three_undeclared_paths_yield_three_findings_and_a_gate_hard_stop() -> None:
    from test_gate_evaluator import evaluate, valid_results

    payload = result()
    payload["changed_paths"] = ["src/one.py", "src/two.py", "src/three.py"]
    normalized = R.validate_result(
        payload, launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
    )
    assert [item["location"] for item in normalized["findings"]] == [
        "src/one.py",
        "src/three.py",
        "src/two.py",
    ]

    results = valid_results()
    results["test"]["changed_paths"] = ["src/one.py", "src/two.py", "src/three.py"]
    decision = evaluate(results=results)
    assert (
        "more than one unplanned one-hop finding requires operator approval"
        in decision["blocking_reasons"]
    )
    # approval_required drives the escalate verdict and blocks root release.
    assert decision["verdict"] == "escalate"
    assert decision["root_release"] is False


def test_one_agent_one_hop_plus_one_synthesized_finding_hard_stops() -> None:
    from test_gate_evaluator import evaluate, valid_results

    agent_finding = finding()
    agent_finding.update({"finding_id": "agent-one-hop", "scope_disposition": "one-hop"})
    results = valid_results()
    results["test"]["findings"] = [agent_finding]
    results["test"]["changed_paths"] = ["tests/test_feature.py", "src/outside.py"]
    decision = evaluate(results=results)
    assert (
        "more than one unplanned one-hop finding requires operator approval"
        in decision["blocking_reasons"]
    )
    assert decision["verdict"] == "escalate"
    assert decision["root_release"] is False


def test_synthesis_does_not_swallow_other_contract_violations() -> None:
    malformed = finding()
    malformed["severity"] = "P9"
    payload = copy.deepcopy(result())
    payload["findings"] = [malformed]
    payload["changed_paths"] = ["src/outside.py"]
    with pytest.raises(R.ResultContractError, match="severity is invalid"):
        R.validate_result(
            payload, launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
        )

    stale = result()
    stale["changed_paths"] = ["src/outside.py"]
    stale["no_change"] = True
    with pytest.raises(R.ResultContractError, match="no_change"):
        R.validate_result(
            stale, launch(), expected_attempt_id="test-attempt-1", expected_agent_path="/root/test"
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
    assert normalized["findings"][0]["scope_disposition"] == "planned"


def test_deferred_finding_cannot_claim_a_hard_stop() -> None:
    item = finding()
    item.update({"scope_disposition": "defer", "hard_stop": True})
    with pytest.raises(R.ResultContractError, match="cannot combine"):
        R.validate_finding(item)
