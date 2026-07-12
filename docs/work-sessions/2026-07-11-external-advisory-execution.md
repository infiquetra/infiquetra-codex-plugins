# External Advisory Execution Work Session

## U1. Freeze the adaptation and capability boundary

The current external-advisory plan now owns the active port contract instead of inheriting the completed Saga 0.75.17 window.

The frozen Claude window is `38742ece89880a6b140be237edad6d3f13c97b54..675712b1d6a55ead11f3e971ed0e119354621bf2`. Three source rows are classified: current second-opinion behavior and supervised delegate behavior are Codex adaptations, while the Claude-host Codex-delegate contract test remains rejected as an active surface.

The Codex execution boundary is `39f0a2f466cb6f58e203ce3e586a959ff853a342..d8f5d165ad0e859af9c7d7f1ba7461b00ec1ae95`. Seven planning, review, investigation, ideation, and decision artifacts are preserved.

**Files modified:** `scripts/port_contract.py`, `tests/test_port_contract.py`, `docs/validation/codex-runtime-capability-snapshot.json`, `docs/portability/manifests/2026-07-11-external-advisory-execution.json`, `docs/portability/classifications/2026-07-11-external-advisory-execution.md`, `docs/engineering-journal/QUEUED.md`.

**Checks run:** classification gate passed; `tests/test_port_contract.py` passed with 25 tests.

**Next step:** Implement U2 action contracts, durable store, and status projection.
