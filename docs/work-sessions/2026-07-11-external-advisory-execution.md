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

## U3. Build approval, policy, egress, and runtime orchestration

The shared runtime now resolves explicit actions over repo/stage policy, legacy preferences, and shipped defaults. All six stage bundles are data-authored, while legacy `engine-prefs.json` values remain unapproved intent rather than launch authority.

Outbound payloads are recursively sanitized before any store or executor call. Credential-shaped strings are redacted without retaining values, private keys block the action, and the approved payload digest, route, egress, cost class, context scope, base revision, and write set bind one approval fingerprint.

The provider-neutral runtime implements prepare, approve, claim-before-launch, launch acknowledgement, terminal failure mapping, adjudication, consumption, and status refresh. Executors are injected and must return validated evidence, so no provider is represented as active before U4 wires `engine_dispatch`.

**Files modified:** `plugins/saga/references/external-action-defaults.yaml`, `plugins/saga/scripts/external_action_policy.py`, `plugins/saga/scripts/external_action_egress.py`, `plugins/saga/scripts/external_action_runtime.py`, `plugins/saga/scripts/external_action.py`, `tests/test_external_action_policy.py`, `tests/test_external_action_egress.py`, `tests/test_external_action_runtime.py`.

**Checks run:** 23 combined U2/U3 pytest cases passed; Ruff passed; scoped mypy passed for all four U3 source modules.

**Next step:** Implement U4 supervised Claude, `agy`, and HTTP adapters with disposable-clone containment.
## U4 - Supervised external adapters

- Added disposable local-clone workspaces with detached checkout, remote removal, binary patch capture, write-set enforcement, and cleanup.
- Added supervised Agy and Claude CLI adapters plus thin delegate entry points.
- Added the `claude-cli/opus` registry route and `claude-delegate` bridge-signature policy.
- Preserved the established Agy invocation digest contract while adding Claude model and effort metadata.
- Focused tests: `64 passed`.
- Ruff: passed.
- Mypy: the four U4 source files pass with `--follow-imports=skip`; unrestricted import following reaches seven pre-existing errors in `fleet_commons_shim.py` and `engine_bridge_http.py`.
## U5 - Provider onboarding and policy persistence

- Extended repo-local engine overlays with validated additive provider rows and canonical-plus-overlay composition.
- Redirected OpenAI-compatible onboarding apply away from the canonical registry and into a digest-bound overlay after a bounded non-sensitive HTTP smoke.
- Added environment-variable secret-reference enforcement, duplicate-key rejection, optimistic concurrency, and composed-registry CLI visibility.
- Added atomic digest-bound external-action policy persistence.
- Added canonical promotion diff output and overlay finalization that requires identical canonical readback.
- Focused tests: `77 passed`.
- Ruff: passed.
- Mypy: passed for the six U5 source files with `--follow-imports=skip --ignore-missing-imports`.
