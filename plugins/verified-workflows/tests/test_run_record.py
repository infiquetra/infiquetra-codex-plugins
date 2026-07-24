from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
TESTS = Path(__file__).parent
for path in (SCRIPTS, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import protocol_probe as P  # noqa: E402
import result_contract as results  # noqa: E402
import run_record as records  # noqa: E402
from test_result_contract import result  # noqa: E402
from test_workflow_dispatch import compile_fixture  # noqa: E402


def launch():
    return next(spec for spec in compile_fixture().launch_specs if spec.assignment_id == "test")


def receipt(path: str = "/root/test") -> P.RuntimeReceipt:
    return P.RuntimeReceipt(
        session_id="thread",
        parent_thread_id="root",
        agent_path=path,
        agent_type="test_medium",
        model="gpt-5.6-terra",
        reasoning_effort="medium",
        model_provider="openai",
        approval_policy="never",
        permission_profile="managed",
        sandbox_mode="workspace-write",
        multi_agent_version="v2",
        terminal_observed=False,
        git_mutation_observed=False,
        child_paths=(),
        source_events=("session_meta", "turn_context"),
    )


def new_record() -> dict[str, object]:
    return records.new_run_record(
        repository_id="infiquetra/example",
        run_id="run-1",
        contract=compile_fixture(),
    )


def normalized(*, terminal_status: str = "completed", changed: bool = True) -> dict[str, object]:
    payload = result()
    payload["terminal_status"] = terminal_status
    if not changed:
        payload["changed_paths"] = []
        payload["no_change"] = True
    return results.validate_result(
        payload,
        launch(),
        expected_attempt_id="test-attempt-1",
        expected_agent_path="/root/test",
    )


def test_one_atomic_record_round_trips(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    state = records.initialize_user_state_root(repo, state_parent=tmp_path / "state")
    running = records.start_attempt(new_record(), launch(), receipt(), attempt_id="test-attempt-1")
    completed = records.finish_attempt(running, normalized())
    path = records.write_run_record(repo, state, completed)

    assert path == state / "workflow-runs" / "run-1.json"
    loaded = records.read_run_record(repo, state, "run-1")
    assert loaded["attempts"][0]["status"] == "completed"
    assert list(path.parent.glob("*.json")) == [path]
    text = path.read_text()
    assert "session_meta" not in text
    assert "turn_context" not in text


def test_same_attempt_restoration_preserves_path() -> None:
    running = records.start_attempt(new_record(), launch(), receipt(), attempt_id="test-attempt-1")
    assert records.start_attempt(
        running, launch(), receipt(), attempt_id="test-attempt-1"
    ) == running
    with pytest.raises(records.RunRecordError, match="preserve assignment and agent path"):
        records.start_attempt(
            running, launch(), receipt("/root/other"), attempt_id="test-attempt-1"
        )


def test_terminal_identity_cannot_be_reused() -> None:
    running = records.start_attempt(new_record(), launch(), receipt(), attempt_id="test-attempt-1")
    completed = records.finish_attempt(running, normalized())
    with pytest.raises(records.RunRecordError, match="terminal attempt identity"):
        records.start_attempt(completed, launch(), receipt(), attempt_id="test-attempt-1")


def test_retry_requires_fresh_path_and_partial_edit_classification() -> None:
    running = records.start_attempt(new_record(), launch(), receipt(), attempt_id="test-attempt-1")
    failed = records.finish_attempt(running, normalized(terminal_status="failed"))
    second_receipt = receipt("/root/test-retry")
    with pytest.raises(records.RunRecordError, match="partial edits must be classified"):
        records.start_attempt(failed, launch(), second_receipt, attempt_id="test-attempt-2")
    retried = records.start_attempt(
        failed,
        launch(),
        second_receipt,
        attempt_id="test-attempt-2",
        prior_edit_disposition="carry-forward",
    )
    assert retried["attempts"][-1]["agent_path"] == "/root/test-retry"
    with pytest.raises(records.RunRecordError, match="fresh canonical agent path"):
        records.start_attempt(
            failed,
            launch(),
            receipt(),
            attempt_id="test-attempt-2",
            prior_edit_disposition="cleanup",
        )


def test_repository_identity_marker_blocks_cross_repo_reuse(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    state = records.initialize_user_state_root(first, state_parent=tmp_path / "state")
    with pytest.raises(records.RunRecordError, match="does not match"):
        records.validate_state_root(second, state)
