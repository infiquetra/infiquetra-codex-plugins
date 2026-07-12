# DEBUG REPORT — external second-opinion preference produces no advisory run

- **Status:** DONE_WITH_CONCERNS
- **Date:** 2026-07-11
- **Source:** operator report that `second-opinion` was selected during `/ideate` but no external result was observed

## Symptom

The operator selected `second-opinion` during an attended `/ideate` run. The preference was saved, but the run produced only native Codex candidates, no external advisory output, and no external-engine receipt.

The same choice was offered for `/brainstorm`, but its use was stopped before persistence because the preceding Ideate run could not prove an external round trip.

## Root cause

The failure is a missing product-to-runtime integration, not a confirmed provider outage.

1. Historical seed `S-26` required a per-command decision for `/ideate`, `/brainstorm`, `/plan`, `/work`, `/doc-review`, and `/code-review` in `../infiquetra-claude-plugins/docs/plans/plugin-fleet-ideation-2026-07-03/survivors/seeds.json`.
2. Claude issue `#394` and merged PR `#558` deliberately implemented second-opinion triggers only for `/work`, `/doc-review`, and `/code-review`. The issue explicitly kept `/ideate`, `/brainstorm`, and `/plan` out of scope.
3. Codex later added an Engine Offer to `plugins/saga/skills/ideate/SKILL.md:44` and `plugins/saga/skills/brainstorm/SKILL.md:49`. Both contracts state that the offer is advisory and never dispatches, scores, or gates work.
4. Accepting the offer invokes `plugins/saga/scripts/engine_preference.py`, which persists intent but does not execute an engine.
5. Actual external execution lives behind `plugins/saga/scripts/engine_dispatch.py:236`, whose `dispatch()` API requires a concrete `runner` callable.
6. No production Codex plugin surface calls `engine_dispatch.dispatch()` or `dispatch_advisory_panel()`. Current non-test references stop at offer/preference documentation and workflow contracts.
7. The modernization plan imported the registry, resolver, HTTP bridge, trust boundary, receipts, and reconciliation, but explicitly excluded activation of `agy` in `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md:840`.
8. Therefore the saved `second-opinion` preference has no consumer capable of constructing a production runner, invoking the selected provider, returning typed findings, or emitting a receipt. Native execution continues and the requested advisory lane is silently absent unless the orchestrator notices and reports it.

Prediction: selecting `second-opinion` in another current Codex `/ideate` or `/brainstorm` run will save the preference but produce no external receipt regardless of provider credentials. Result: confirmed by the Ideate run `749774b1`, whose survivor checkpoint records the unavailable lane and contains no engine-generated or advisory evidence.

Prediction: provider installation alone will not correct the symptom because dispatch is never reached. Result: `agy` is installed and lists the configured Gemini variants, while repository-wide production-call-site search still finds no caller of the dispatch API.

## Fix

Diagnosis only. The root cause is a design gap spanning stage posture, production runner ownership, operator confirmation and spending, typed result consumption, receipt readback, and failure semantics; it is not a trivial fix suitable for `/investigate`.

Route to `/brainstorm` for a Codex External Advisory Execution Contract before planning implementation.

## Evidence

- Ideate run `.codex/saga/ideate/749774b1/survivors.md` records `second-opinion` as requested but unavailable and contains no external advisory result.
- `.codex/saga/engine-prefs.json` stored the Ideate preference, proving selection reached persistence.
- No engine receipt, advisory artifact, or provider run exists under the run's local Saga state.
- `command -v agy` succeeds and `agy models` lists `Gemini 3.1 Pro (High)` and `Gemini 3.5 Flash (High)`, so the CLI/model discovery prerequisite is present.
- `plugins/saga/references/engine-registry.yaml` maps the `second-opinion` capability to `agy/gemini-3.1-pro-high` and requires an `agy-delegate` receipt emitter.
- `tests/test_engine_dispatch_attestation.py` supplies fake runners and synthetic receipts; it proves dispatch validation but not a production stage-to-provider round trip.
- GitHub issue `infiquetra/infiquetra-claude-plugins#394` is closed by PR `#558`, but its explicit non-goals leave `/ideate`, `/brainstorm`, and `/plan` unresolved.
- No current Claude or Codex issue tracks the remaining `S-26` slice.

Residual concern: no direct paid-provider smoke was run because the failing path stops before provider invocation. Provider authentication and receipt emission still require separate acceptance proof after the production runner is designed.

## Regression test

Recommended: add a production-boundary integration test that selects `second-opinion` for an attended stage, consumes the saved preference, resolves an available registry entry, invokes the real configured runner through a controlled smoke fixture, obtains typed findings plus a schema-valid receipt, and records the advisory reference without affecting any hard gate.

Add a negative test proving that a selected preference with no usable runner halts or reports `unavailable`; it must never silently continue as though the advisory lane ran.

Existing tests should not have been considered sufficient because they validate helpers with injected fake runners and never assert that `/ideate` or `/brainstorm` consumes the preference and reaches a production adapter.

## Related

- `../infiquetra-claude-plugins/docs/brainstorms/2026-06-27-external-engine-capability-routing-requirements.md`
- `../infiquetra-claude-plugins/docs/plans/2026-07-10-issue-394-second-opinion-triggers-plan.md`
- `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`
- `docs/ideation/2026-07-11-codex-workflow-control-agent-lifecycle-ideation.md`
- Claude objective `#336`, issue `#394`, and PR `#558`
- Historical survivor `S-26`: offload-versus-second-opinion posture across lifecycle stages
