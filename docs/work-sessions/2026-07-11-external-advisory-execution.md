# External Advisory Execution Work Session

## U1. Freeze the adaptation and capability boundary

The current external-advisory plan now owns the active port contract instead of inheriting the completed Saga 0.75.17 window.

The frozen Claude window is `38742ece89880a6b140be237edad6d3f13c97b54..675712b1d6a55ead11f3e971ed0e119354621bf2`. Three source rows are classified: current second-opinion behavior and supervised delegate behavior are Codex adaptations, while the Claude-host Codex-delegate contract test remains rejected as an active surface.

The Codex execution boundary is `39f0a2f466cb6f58e203ce3e586a959ff853a342..d8f5d165ad0e859af9c7d7f1ba7461b00ec1ae95`. Seven planning, review, investigation, ideation, and decision artifacts are preserved.

**Files modified:** `scripts/port_contract.py`, `tests/test_port_contract.py`, `docs/validation/codex-runtime-capability-snapshot.json`, `docs/portability/manifests/2026-07-11-external-advisory-execution.json`, `docs/portability/classifications/2026-07-11-external-advisory-execution.md`, `docs/engineering-journal/QUEUED.md`.

**Checks run:** classification gate passed; `tests/test_port_contract.py` passed with 25 tests.

**Next step:** Implement U2 action contracts, durable store, and status projection.

## U2. Add the action contract, store, and status projection

External actions now have closed request, approval, state, transition, and requiredness contracts. Each action stores immutable request and approval records, a locked hash-chained event stream with torn-tail recovery, and reproducible JSON and Markdown status projections.

The store uses `<git-common-dir>/saga-external-actions/<saga-id>/<run-id>/<action-id>/`. It rejects path traversal, conflicting immutable rewrites, skipped or contradictory transitions, duplicate event IDs with changed content, broken hash links, and continuation overrides without a terminal failure and rationale.

**Files modified:** `plugins/saga/scripts/external_action_contract.py`, `plugins/saga/scripts/external_action_store.py`, `plugins/saga/scripts/external_action_status.py`, `tests/test_external_action_store.py`, `tests/test_external_action_status.py`.

**Checks run:** 12 focused pytest cases passed; Ruff passed; mypy passed for all three source modules.

**Next step:** Implement U3 approval, policy, egress, and runtime orchestration.
