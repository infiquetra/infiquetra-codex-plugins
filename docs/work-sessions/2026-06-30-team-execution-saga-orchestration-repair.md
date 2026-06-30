# 2026-06-30 Team Execution Saga Orchestration Repair

## Summary

Implemented the reviewed repair plan for the Saga/Team Execution orchestration mismatch. Team Execution
state now requires a concrete receipt before executable lifecycle boundaries, and unavailable delegation
routes to serial Team Execution or an explicit downgrade instead of silent inline execution.

## Completed Work

- U1: Added shared Team Execution readiness validation in `plugins/saga/scripts/team_execution_readiness.py`.
- U2: Added Saga save-time Team Execution readiness and provenance checks in `plugins/saga/scripts/saga.py`.
- U3: Updated planning instructions and backend-choice references so Team Execution Phase A produces a
  `## Team Structure` receipt and records recommendation, operator choice, actual mode, and ref.
- U4: Updated work/resume/loop instructions so executable Team Execution enters Phase B or repairs/halts.
- U5: Added Team Execution role `vehicle` provenance for reviewer and validator evidence.
- U6: Required Outcome Team Execution dispatch to carry `orchestration_ref`, including ledger records.
- U7: Added cross-surface regression tests for the observed failure shapes.
- U8: Updated the engineering journal and this work-session checkpoint.

## Key Decisions

Team Execution readiness is a receipt invariant, not a metadata invariant. Draft planning may carry
Team Execution intent without a ref; executable contexts must resolve `orchestration_ref` to a
`## Team Structure` section or protected evidence root.

Delegation absence or backpressure is still Team Execution when the selected roles run serially.
Generic subagents and inline helpers are assistance only unless their evidence is converted into
selected Team Execution role records.

## Checks Run

- `PYTHONPATH=. python3 -m pytest -q tests/test_team_execution_readiness.py plugins/saga/tests/test_saga_state.py tests/test_capability_degrade.py tests/test_override_rate.py`
- `PYTHONPATH=. python3 -m pytest -q tests/test_team_execution_lifecycle_text.py tests/test_operator_choice_drift.py plugins/saga/tests/test_lifecycle_state.py tests/test_saga_doc_formatting.py`
- `PYTHONPATH=. python3 -m pytest -q plugins/team-execution/tests/test_protocol_probe.py`
- `PYTHONPATH=. python3 -m pytest -q tests/test_outcome_dispatcher.py tests/test_outcome_backends.py tests/test_outcome_completion.py tests/test_outcome_integration.py`
- `PYTHONPATH=. python3 -m pytest -q tests/test_team_execution_orchestration_regressions.py tests/test_team_execution_lifecycle_text.py plugins/team-execution/tests/test_protocol_probe.py tests/test_outcome_dispatcher.py`
- `PYTHONPATH=. python3 -m pytest -q tests/test_team_execution_readiness.py tests/test_team_execution_lifecycle_text.py tests/test_team_execution_orchestration_regressions.py plugins/saga/tests/test_saga_state.py plugins/saga/tests/test_lifecycle_state.py plugins/team-execution/tests/test_protocol_probe.py tests/test_outcome_dispatcher.py tests/test_outcome_backends.py tests/test_outcome_completion.py tests/test_outcome_integration.py tests/test_operator_choice_drift.py tests/test_capability_degrade.py tests/test_override_rate.py`
- `python3 -m ruff check <touched Python files>`
- `git diff --check`
- `python3 scripts/validate_codex_plugins.py`
- `PYTHONPATH=. python3 -m pytest -q`

## Reviewer Gate

Team Execution reviewers re-checked the final diff after blocker fixes. Security, devil's advocate, and
architecture reviewers all cleared their previous findings with no remaining blockers. Their final
dimension scores were 8/10 or higher, with correctness, coverage, operational safety, and plan alignment
at 9/10.

## Next Step

Prepare PR-ready handoff or commit once the operator chooses the next Git boundary.
