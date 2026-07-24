from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
TESTS = Path(__file__).parent
for path in (SCRIPTS, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import gate_evaluator as G  # noqa: E402
from test_result_contract import finding, result  # noqa: E402
from test_workflow_dispatch import check, compile_fixture  # noqa: E402


def contract():
    return compile_fixture(
        checks=[
            check(
                "focused",
                after="test",
                command="focused targeted checks",
                failure="fix and rerun",
            ),
            check(),
        ]
    )


def valid_results() -> dict[str, dict[str, object]]:
    return {
        "test": result(),
        "review": result(assignment_id="review", reviewer=True),
    }


def valid_checks() -> dict[str, dict[str, str]]:
    return {
        "focused": {"status": "pass", "detail": "36 focused tests passed"},
        "reviewer-assurance": {"status": "pass", "detail": "review threshold passed"},
    }


def evaluate(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "results": valid_results(),
        "check_outcomes": valid_checks(),
        "reviewer_roots": {"review": "fresh-review-root-1"},
        "implementation_root_identity": "implementation-root",
        "adopted_root_findings": [],
        "remediation_round": 0,
        "revalidated_finding_ids": [],
    }
    values.update(overrides)
    return G.evaluate_gate(contract(), **values)  # type: ignore[arg-type]


def test_passing_scores_checks_and_independence_release_gate() -> None:
    decision = evaluate()
    assert decision["verdict"] == "pass"
    assert decision["root_release"] is True
    assert decision["reviewers"] == ["review"]


def test_empty_applicable_dimensions_fail_closed() -> None:
    results = valid_results()
    results["review"]["dimensions"] = []
    results["review"]["denominator"] = 0
    with pytest.raises(G.GateEvaluationError, match="dimensions must be a non-empty list"):
        evaluate(results=results)


def test_invalid_exclusion_fails_closed() -> None:
    results = valid_results()
    results["review"]["exclusions"] = [
        {"dimension_id": "unused", "reason": "dynamic-not-applicable"}
    ]
    with pytest.raises(G.GateEvaluationError, match="reason is invalid"):
        evaluate(results=results)


def test_arithmetic_mismatch_fails_closed() -> None:
    results = valid_results()
    results["review"]["overall"] = 10.0
    with pytest.raises(G.GateEvaluationError, match="arithmetic mean"):
        evaluate(results=results)


def test_average_below_nine_blocks() -> None:
    results = valid_results()
    results["review"]["dimensions"] = [
        {"dimension_id": "correctness", "score": 8.0, "notes": "needs work"}
    ]
    results["review"]["denominator"] = 1
    results["review"]["overall"] = 8.0
    decision = evaluate(results=results)
    assert decision["verdict"] == "block"
    assert "below 9.0" in " ".join(decision["blocking_reasons"])


def test_dimension_below_seven_blocks() -> None:
    results = valid_results()
    results["review"]["dimensions"] = [
        {"dimension_id": "correctness", "score": 6.0, "notes": "bad"},
        {"dimension_id": "risk", "score": 10.0, "notes": "bounded"},
    ]
    results["review"]["denominator"] = 2
    results["review"]["overall"] = 8.0
    decision = evaluate(results=results)
    assert decision["verdict"] == "block"
    assert "below 7.0" in " ".join(decision["blocking_reasons"])


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"severity": "P0"}, "unresolved P0"),
        ({"severity": "P1"}, "unresolved P1"),
        ({"severity": "P2", "category": "security"}, "unresolved security"),
        ({"severity": "P2", "hard_stop": True}, "role hard stop"),
    ],
)
def test_severity_and_role_hard_stops_block(updates: dict[str, object], message: str) -> None:
    results = valid_results()
    item = finding()
    item.update(updates)
    results["review"]["findings"] = [item]
    decision = evaluate(results=results)
    assert decision["verdict"] == "block"
    assert message in " ".join(decision["blocking_reasons"])


def test_missing_independent_reviewer_identity_blocks() -> None:
    decision = evaluate(reviewer_roots={})
    assert decision["verdict"] == "block"
    assert "lacks a validated fresh-root identity" in " ".join(decision["blocking_reasons"])


def test_implementation_root_or_reused_review_root_is_not_independent() -> None:
    decision = evaluate(reviewer_roots={"review": "implementation-root"})
    assert decision["verdict"] == "block"
    assert "not independent" in " ".join(decision["blocking_reasons"])


def test_missing_or_failed_blocking_check_blocks() -> None:
    missing = valid_checks()
    missing.pop("reviewer-assurance")
    assert "blocking check reviewer-assurance is missing" in evaluate(
        check_outcomes=missing
    )["blocking_reasons"]
    failed = valid_checks()
    failed["focused"] = {"status": "failed", "detail": "one failure"}
    assert "blocking check focused is failed" in evaluate(
        check_outcomes=failed
    )["blocking_reasons"]


def test_fourth_automatic_remediation_round_is_forbidden() -> None:
    with pytest.raises(G.GateEvaluationError, match="fourth automatic"):
        evaluate(remediation_round=4)


def test_third_unresolved_round_escalates() -> None:
    results = valid_results()
    results["review"]["findings"] = [finding()]
    decision = evaluate(results=results, remediation_round=3)
    assert decision["verdict"] == "escalate"
    assert decision["next_remediation_round"] is None


def test_remediated_finding_requires_fresh_focused_revalidation() -> None:
    results = valid_results()
    item = finding()
    item["resolved"] = True
    results["review"]["findings"] = [item]
    without = evaluate(results=results, remediation_round=1)
    assert without["verdict"] == "block"
    assert "without fresh focused revalidation" in " ".join(without["blocking_reasons"])
    with_revalidation = evaluate(
        results=results,
        remediation_round=1,
        revalidated_finding_ids=["finding-1"],
    )
    assert with_revalidation["verdict"] == "pass"


def test_remediation_round_requires_focused_check() -> None:
    checks = valid_checks()
    checks["focused"] = {"status": "warn", "detail": "not rerun"}
    decision = evaluate(check_outcomes=checks, remediation_round=1)
    assert decision["verdict"] == "block"
    assert "fresh focused revalidation" in " ".join(decision["blocking_reasons"])


def test_root_findings_require_explicit_verification_and_then_gate() -> None:
    adopted = {"finding": finding(), "verified": False, "source": "root-review"}
    with pytest.raises(G.GateEvaluationError, match="not independently verified"):
        evaluate(adopted_root_findings=[adopted])
    adopted["verified"] = True
    decision = evaluate(adopted_root_findings=[adopted])
    assert decision["verdict"] == "block"
    assert decision["finding_count"] == 1


def test_terminal_failure_blocks() -> None:
    results = valid_results()
    results["test"]["terminal_status"] = "failed"
    decision = evaluate(results=results)
    assert decision["verdict"] == "block"
    assert "terminal status is failed" in " ".join(decision["blocking_reasons"])


def test_evaluator_has_no_retired_evidence_dependencies() -> None:
    source = (SCRIPTS / "gate_evaluator.py").read_text().casefold()
    for retired in (
        "subject",
        "workspace-snapshot",
        "content-addressed",
        "hook receipt",
        "intent record",
        "plugin-data",
    ):
        assert retired not in source


def test_cli_returns_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from test_workflow_dispatch import assignment, plan, reviewer, worker

    plan_path = tmp_path / "plan.md"
    plan_path.write_text(
        plan(
            [assignment("implement"), reviewer(), worker()],
            checks=[
                check("focused", after="test", command="focused checks"),
                check(),
            ],
        )
    )
    payload = {
        "results": valid_results(),
        "check_outcomes": valid_checks(),
        "reviewer_roots": {"review": "fresh-root"},
        "implementation_root_identity": "implementation-root",
        "adopted_root_findings": [],
        "remediation_round": 0,
        "revalidated_finding_ids": [],
    }
    input_path = tmp_path / "gate.json"
    input_path.write_text(json.dumps(payload))
    assert G.main(
        [
            "--plan",
            str(plan_path),
            "--plan-revision",
            "revision",
            "--input",
            str(input_path),
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "pass"
