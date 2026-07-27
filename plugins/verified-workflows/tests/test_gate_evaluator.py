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
    implementation = result()
    implementation.update(
        {
            "assignment_id": "implement",
            "attempt_id": "implement-attempt-1",
            "agent_path": "/root/implement",
            "role_id": "implementation-worker",
            "profile_id": "work_medium",
            "changed_paths": ["src/feature.py"],
        }
    )
    values = {
        "implement": implementation,
        "test": result(),
        "review": result(assignment_id="review", reviewer=True),
    }
    mandates = next(
        spec.reviewer_mandate_ids
        for spec in contract().launch_specs
        if spec.assignment_id == "review"
    )
    values["review"]["dimensions"] = [
        {"dimension_id": mandate, "score": 10.0, "notes": "satisfied"}
        for mandate in mandates
    ]
    values["review"]["denominator"] = len(mandates)
    values["review"]["overall"] = 10.0
    return values


def valid_authorities() -> dict[str, dict[str, str]]:
    values: dict[str, dict[str, str]] = {}
    for spec in contract().launch_specs:
        if spec.agent_type is None:
            continue
        fresh = spec.assignment_id == "review"
        root = "fresh-review-root-1" if fresh else "implementation-root"
        values[spec.assignment_id] = {
            "attempt_id": f"{spec.assignment_id}-attempt-1",
            "session_id": f"{spec.assignment_id}-session",
            "agent_path": f"/root/{spec.assignment_id}",
            "parent_thread_id": root,
            "execution_root_id": root,
            "runtime_receipt_sha256": "a" * 64,
            "registry_sha256": spec.registry_sha256,
            "role_lens_sha256": str(spec.role_lens_sha256),
            "profile_sha256": str(spec.profile_sha256),
        }
    return values


def valid_checks() -> dict[str, dict[str, str]]:
    return {
        "focused": {"status": "pass", "detail": "36 focused tests passed"},
        "reviewer-assurance": {"status": "pass", "detail": "review threshold passed"},
    }


def evaluate(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "results": valid_results(),
        "attempt_authorities": valid_authorities(),
        "check_outcomes": valid_checks(),
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
    results["review"]["overall"] = 9.9
    with pytest.raises(G.GateEvaluationError, match="arithmetic mean"):
        evaluate(results=results)


def test_average_below_nine_blocks() -> None:
    results = valid_results()
    results["review"]["dimensions"] = [
        {"dimension_id": item["dimension_id"], "score": 8.0, "notes": "needs work"}
        for item in results["review"]["dimensions"]
    ]
    results["review"]["denominator"] = 5
    results["review"]["overall"] = 8.0
    decision = evaluate(results=results)
    assert decision["verdict"] == "block"
    assert "below 9.0" in " ".join(decision["blocking_reasons"])


def test_dimension_below_seven_blocks() -> None:
    results = valid_results()
    results["review"]["dimensions"][0]["score"] = 6.0
    results["review"]["dimensions"][0]["notes"] = "bad"
    results["review"]["denominator"] = 5
    results["review"]["overall"] = 9.2
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


def test_missing_attempt_authority_fails_closed() -> None:
    authorities = valid_authorities()
    authorities.pop("review")
    with pytest.raises(G.GateEvaluationError, match="exactly cover"):
        evaluate(attempt_authorities=authorities)


def test_implementation_root_or_reused_review_root_is_not_independent() -> None:
    authorities = valid_authorities()
    authorities["review"]["execution_root_id"] = "implementation-root"
    authorities["review"]["parent_thread_id"] = "implementation-root"
    with pytest.raises(G.GateEvaluationError, match="reuses the implementation root"):
        evaluate(attempt_authorities=authorities)


def test_result_cannot_select_its_own_attempt_identity() -> None:
    results = valid_results()
    results["test"]["attempt_id"] = "test-attempt-2"
    with pytest.raises(G.GateEvaluationError, match="attempt_id mismatch"):
        evaluate(results=results)


def test_attempt_authority_must_match_approved_role_and_profile_digests() -> None:
    authorities = valid_authorities()
    authorities["test"]["profile_sha256"] = "b" * 64
    with pytest.raises(G.GateEvaluationError, match="profile_sha256.*approved launch"):
        evaluate(attempt_authorities=authorities)


def test_reviewer_mandate_roster_must_match_role_lens() -> None:
    results = valid_results()
    results["review"]["dimensions"][0]["dimension_id"] = "fabricated"
    with pytest.raises(G.GateEvaluationError, match="mandate roster"):
        evaluate(results=results)


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


def test_second_automatic_remediation_round_is_forbidden() -> None:
    with pytest.raises(G.GateEvaluationError, match="more than one remediation"):
        evaluate(remediation_round=2)


def test_unresolved_finding_after_one_remediation_escalates() -> None:
    results = valid_results()
    results["review"]["findings"] = [finding()]
    decision = evaluate(results=results, remediation_round=1)
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
        "attempt_authorities": valid_authorities(),
        "check_outcomes": valid_checks(),
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
