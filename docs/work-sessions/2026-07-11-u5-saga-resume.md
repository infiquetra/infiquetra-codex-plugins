# U5 Saga Resume

## Completed

- Treated commits `2133648` and `61753fc` as authoritative. Host-issued rollout context, not a
  child self-report, confirms `review_max` is `gpt-5.6-sol`/`max` and `scan_low` is
  `gpt-5.6-luna`/`low`.
- Recorded KTD22 as the remaining execution limitation: MultiAgent V2 reapplies the parent
  permission profile after role selection. This workspace-write root therefore owns product-source
  changes; no read-only reviewer, scanner, or monitor profile is dispatched beneath it.
- Fixed Saga's explicit-default scalar merge regression. Every supplied persisted, non-list scalar
  `save` option is now parser-derived and marked explicit, excluding sticky identity fields. A
  literal `--destination plan-only` can now supersede a prior `merge` value.

## Evidence

- Commit: `e2cf3f8 fix(saga): honor explicit default scalar saves`.
- Check: `UV_CACHE_DIR=/private/tmp/codex-uv-cache PYTHONPATH=. uv run pytest
  plugins/saga/tests/test_saga_state.py -q` — 10 passed.
- The root-owned Saga tick was persisted after the workspace-write implementation task returned.

## U5 Completion

- Canonical new-write vocabulary now uses `inline`, `manual`, and `verified-workflow`; the legacy
  `team-execution` input is normalized on read/save rather than emitted by new Saga ticks.
- Saga records `continuation_mode`, `continuation_ref`, and `identity_mode`. Goal remains an explicit
  continuation binding, not an outcome backend.
- Outcome reconciliation writes `outcome.dispatch.v2` intents and accepts only a typed launched or
  handed-off acknowledgement as settlement. A legacy synthetic leaf commit remains visible as
  `legacy-unverified` and cannot advance dependent work.
- Added the canonical readiness adapter and a single non-mutating SessionStart hook for startup,
  resume, and compact context.
- Recovered interrupted intent handling without duplicate launch: an unresolved v2 intent remains
  visible as `intent-created` and blocks automatic relaunch until append-only reconciliation supplies
  local launch authority or an operator-confirmed handoff.
- Migrated hierarchy and board-sync fixtures from the synthetic v1 commit to a typed v2 launch
  acknowledgement. The source-only Workflow, fork, subagent, and Goal vehicles now halt visibly
  rather than becoming caller-asserted capabilities.
- Added `docs/validation/codex-plugin-modernization-u5.json`, verified all U5 source and Codex rows
  with its evidence, rendered the classification, and regenerated the legacy-token inventory.
- Fresh named-profile review blocked commit `651f9a6`: architecture and adversarial review ran as
  Sol/max/read-only, security as Sol/high/read-only, and concurrency validation as
  Terra/medium/workspace-write. Root verification confirmed the reported launch, reducer,
  compatibility, path-containment, evidence-binding, and instruction-context defects.
- Commits `1de047d` through `16a3a27` resolved the initial and follow-up P1/P2 findings: production
  dispatch cannot synthesize launch or handoff; owner-state launch receipts bind an unpredictable
  run id, intent timestamp, repo identity, owner, and safe mode; Goal and logical-role identity fail
  closed; legacy acknowledgements reconcile append-only; and mixed canonical/legacy roots halt.
- Commit `def7179` makes port evidence bind an exact reviewed target tree rather than relying on an
  ancestor-only claim. Each later remediation refreshed the U5 artifact and manifest against the
  exact behavior-bearing commit.
- Commit `7e7f5dd` preserves imported dispatch acknowledgements as inert
  `outcome.dispatch.audit.v1` records. Export/import/re-export retains history, while dispatch
  reduction, replay, and reconciliation ignore the archive as authority. Commit `3e4d6de` binds the
  resulting U5 evidence to that exact code tree.
- Final fresh-context reruns closed U5 with no P0-P3 findings. The devil's-advocate child was observed
  from its first host `turn_context` as `review_max`, `gpt-5.6-sol`, `max`, read-only. The concurrency
  child was observed as `test_medium`, `gpt-5.6-terra`, `medium`, workspace-write and carried the
  plan's exact role/profile digests plus the `tester-evidence` output contract.

## Checks

- `PYTHONPATH=. uv run pytest -q plugins/saga/tests tests/test_outcome_dispatcher.py
  tests/test_outcome_backends.py tests/test_outcome_dispatch_migration.py
  tests/test_outcome_command.py tests/test_outcome_integration.py tests/test_outcome_liveness.py
  tests/test_outcome_completion.py tests/test_outcome_replay.py tests/test_capability_degrade.py
  tests/test_verified_workflow_readiness.py tests/test_saga_session_context.py` — 519 passed.
- `PYTHONPATH=. uv run pytest -q tests/test_port_contract.py` — 24 passed.
- `python3 scripts/port_contract.py validate --stage unit --unit U5` — passed.
- `python3 scripts/build_legacy_workflow_inventory.py --check` and
  `python3 scripts/validate_codex_plugins.py` — passed.
- The named validator's literal `uv` commands exited 2 because its managed sandbox could not read the
  user cache. It reran the same suites with an isolated cache and recorded 519 and 24 passes; the root
  independently ran the literal commands successfully. No product file was modified by validation.

## Next Step

Begin U6 from the frozen Claude window
`9470edca65b1db06d2f7562eeb2d5a9e48c34dec..38742ece89880a6b140be237edad6d3f13c97b54`,
using the approved host-neutral import and engine-substrate workflow. The later observed Claude head
`46fefb6f17f0c9d0d63858978536d3369ab57dfe` is inventory provenance only and is not a port input.
`.serena/project.yml` remains user-owned and unstaged.
