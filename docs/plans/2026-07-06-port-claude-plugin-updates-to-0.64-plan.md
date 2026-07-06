---
title: Port Recent Claude Plugin Updates (saga 0.41 to 0.64 window) Into Codex Plugins
type: chore
status: active
date: 2026-07-06
---

# Port Recent Claude Plugin Updates (saga 0.41 to 0.64 window) Into Codex Plugins

## Summary

Selectively re-implement the `infiquetra-claude-plugins` delta `b30e0f2..9470edc` into this
Codex-native adapter repo: the fleet-commons tier/retry substrate as a new Codex `fleet-core`
plugin, the saga board-autonomy and ship-ceremony waves, the evidence/manifest stack, engine
capability routing, team-execution protocol updates, mission-control vendored behavioral sync,
and unifi retry adoption — while keeping Claude-host-only surfaces (hooks, agent markdown,
Workflow emission, marketplace generation) rejected or negative-gated.

## Problem Frame

The Codex saga surface was last synced at Claude `b30e0f2` (2026-06-29, the 0.41 parity work).
Upstream is now at `9470edc`: 31 plugin-bearing commits, 141 files, ~16k insertions; saga
0.41.0→0.64.0, team-execution 2.4.0→2.11.0, mission-control 2.3.1→2.5.1, plus two new plugins
(`fleet-core`, `agy`). Other Codex plugins carry older baselines (team-execution lineage 2.2.0,
mission-control 2.1.0, unifi 1.0.0, deploy 0.1.1); the pre-window upstream bumps are almost all
Claude agent model pins, except mission-control 2.3.0's `jeff-intent`→`operations` project
rename and 2.3.1's `issue create-prepared` recovery fix, which are real behavior the vendored
copy lacks. The risk is unchanged from prior cycles: importing Claude-only capabilities as if
Codex can execute them, or bumping versions without the exposed behavior behind them.

## Grounding

- Last-cycle procedure: the 8-step port checklist in
  `docs/plans/2026-06-27-port-recent-claude-plugin-updates.md` ("Repeatable Claude-To-Codex Port
  Procedure") and the classification pattern in `docs/portability/codex-saga-041-harness-delta.md`.
- Standing policy: backend truth is `inline` / `manual` / `team-execution` / conditional
  subagents; Workflow, fork, goal, hooks are inactive (DECISIONS 2026-06-17); mutation boundary
  is propose-only by default (`codex-saga-041-harness-delta.md` §Mutation Boundary); vendored
  mission-control mirrors canonical behavior, not bytes (LEARNINGS 2026-06-20); versions mean
  exposed behavior (KTD7, 2026-06-27 plan).
- Current Codex inventory: saga 0.41.0 (22 skills, 37 scripts incl. the outcome family,
  `execution_spec.py`, `completeness_gate.py`, `team_emitter.py`, `status_card.py`);
  team-execution 2.2.0 (25-agent TOML roster, `sync_codex_agents.py` with hard-coded
  `TEAM_EXECUTION_MODEL_HINTS`); mission-control 2.1.0 vendored; unifi 1.0.0; deploy 0.1.1.
- Validator: `scripts/validate_codex_plugins.py` hard-codes `TARGET_EXPECTED_PLUGINS` versions +
  skill tuples, the team-execution roster/model hints, stale-host-path bans, and state roots.
- Upstream delta classification (2026-07-06 exploration): portable stdlib CLIs vs Claude-host-only
  surfaces mapped per feature; upstream tests live at repo-root `tests/`, adapted here into the
  per-plugin `plugins/<name>/tests/` layout this repo uses.
- Operator decisions (2026-07-06): full-family scope; fleet-commons lands as a Codex `fleet-core`
  plugin; remote gate transport (#379) deferred with redis-channel; `agy` out of scope.
- Working tree precondition: the finished discord-identity-assets 0.2.0 change set (24 files) is
  uncommitted and must land as its own commit before the port baseline freezes.

## Requirements

R1. Port the upstream delta `b30e0f2..9470edc` selectively into Codex-runnable surfaces without
losing Codex-only skills, `.codex/saga` state paths, or intentional vendored divergences.

R2. Land the fleet-commons substrate as a Codex `fleet-core` scripts-only plugin: tier palette,
tier resolver, `tier_policy.json`, `models.json`, effort rider, retry/backoff, render helpers,
plus byte-identical vendored `fleet_commons_shim.py` copies in consuming plugins with a drift
test. The shim resolution ladder is rewritten for Codex: env override → repo walk-up →
`~/.codex` plugin layout → fail-loud (no Claude `installed_plugins.json` rung).

R3. Port the saga board-autonomy wave with certificate-gated writes only: reversibility
certificate, outcome board-sync, `board_progression.py` (idempotency keys, bounded retry,
`project_arc`), board↔saga reconciliation on resume, schema-resolved board status, and
`/outcome start --from-objective` DAG seeding.

R4. Port the ship/lifecycle wave: `ship_ceremony.py` with its #481/#483/#484 fixes, the saga
branch-refresh-on-save fix with default-branch protection, gate-divergence telemetry, and the
run-fact ledger (append-only, hash-chained, telemetry-only — never gates).

R5. Port the evidence stack: provenance manifests (verified vs adjudicated), manifest store and
reader, completeness-gate updates, and verify-panel robustness (consensus recomputed over
reporting verifiers; failed or non-applicable panel members tolerated).

R6. Port engine capability routing (`engine_registry.py`, `engine_resolver.py`,
`engine_dispatch.py`, registry YAML, references) with chaperone dispatch capability-gated to
Codex backend truth, and team-execution protocol updates: artifact-pointer passing, consensus
hardening, resident-worker and required-evidence-absence protocol content adapted to serial
fallback, and tier/effort integration replacing hard-coded model hints.

R7. Sync the vendored mission-control by behavior: `operations` project rename (2.3.0),
`issue create-prepared` recovery (2.3.1), issue-write verbs `close/reopen/comment/label-add/
label-remove` (2.4.0), contents-API PUT fix, and `executor_profile_lint.py` (2.5.0), preserving
intentional Codex divergences and their guard tests.

R8. Adopt the shared retry/backoff in unifi network and protect clients (upstream 1.2.0).

R9. Preserve Codex host truth: no Claude command files, agent markdown, hooks, Workflow
emission, or marketplace generation as active surface; negative gates are tested, not assumed.

R10. Update manifests, README table, portability matrix/provenance, validation inventory,
`saga-family-target-inventory.json`, and changelogs only where Codex-visible behavior changed;
finish with targeted per-plugin tests, `python3 scripts/validate_codex_plugins.py`, and full
`python3 -m pytest`.

R11. Record the deferred/rejected set durably: PreCompact spore + residency hooks, remote gate
transport (#379, deferred with redis-channel), `agy`, marketplace generator, sandbox spawn-site
enforcement mechanism, Workflow wave-thunk retry wrapping.

## Key Technical Decisions

KTD1. Commit-bounded source delta: Claude `b30e0f2..9470edc`, with per-plugin lineage baselines
recorded (saga 0.41.0, team-execution 2.2.0, mission-control 2.1.0, unifi 1.0.0, deploy 0.1.1).
If upstream advances before implementation, extend deliberately or refresh this plan — never mix
stale and current evidence.

KTD2. Fleet-commons is a Codex plugin, not scattered copies: `plugins/fleet-core` mirrors the
upstream scripts-only shape so future syncs diff cleanly, and the byte-identical vendored-shim
drift guard is preserved. The resolution ladder is Codex-native (env → walk-up → `~/.codex` →
fail-loud); Claude cache rungs are dropped, not emulated.

KTD3. Dual model palette: Claude tier names (opus/sonnet/haiku, fable) remain lineage metadata in
`models.json`; the active Codex registry maps them to Codex models and effort ceilings (extending
the existing gpt-5.5/gpt-5.4/gpt-5.4-mini hints). Tier validation HALTs on effort above a
model's ceiling, matching upstream semantics with Codex values.

KTD4. Host-only surfaces stay rejected: hooks (spore, residency), Claude agent markdown,
Workflow `.workflow.js` wave-thunk wrapping, and TeamCreate chaperone emission are lineage-only.
Retry/backoff applies to the Codex dispatcher paths; chaperone dispatch resolves to
team-execution or serial fallback and emits unavailable/degraded receipts otherwise.

KTD5. Mutation boundary is unchanged: the reversibility certificate's allow-listed board
operations are the only new autonomous writes; everything else stays propose-only or behind
explicit operator confirmation (ship ceremony's PR-open/merge included).

KTD6. Saga versions to 0.64.0 as a parity label, consistent with the 0.41 precedent: the number
names the upstream parity target while `PORTABILITY.md` and provenance record the non-ported
surfaces. Other plugins bump only for exposed Codex behavior (team-execution, mission-control,
unifi, fleet-core new at its upstream-aligned version 0.5.0); deploy does NOT bump (agent-metadata-only
upstream delta).

KTD7. Tests are part of every unit: upstream repo-root tests are adapted into this repo's
`plugins/<name>/tests/` layout in the same unit as the behavior. Missing tests block the unit.

KTD8. Mission-control sync is behavioral, not byte-mirroring: port routing semantics and verbs,
keep intentional Codex divergences (allowlists, exact-plan confirmation) with their guard tests.

KTD9. Concurrency cap of 3 agents (operator constraint, 2026-07-06, rate-limit history): the
execution spec's `depends_on` graph must keep every topological wave at width ≤3. The current
spec's widest wave is `[U5, U7, U9]` (exactly 3). Any spec revision or re-emit must re-verify
layer widths before running.

## Implementation Units

### U1. Baseline Freeze And Delta Classification

**Goal:** Commit the pending discord-identity-assets 0.2.0 work (operator confirms the commit),
freeze the source baseline, and write the drift-classification artifact for this window.

**Requirements:** R1, R11.

**Dependencies:** none.

**Files:** `docs/portability/codex-saga-064-drift-classification.md` (new),
`docs/portability/matrix.md`, `docs/portability/provenance.md`,
`docs/engineering-journal/DECISIONS.md`.

**Approach:** Land the uncommitted 0.2.0 change set as its own commit first. Record both repos'
`origin/main` refs and dirty state. Produce a classification table in the 041-harness-delta
style: codex-adapt / direct-port / reject-active-surface / defer, per feature, including the
deferred set (spore, residency hook, #379 transport, agy, marketplace, sandbox enforcement).
Add matrix rows for `fleet-core` (proof-port) and `agy` (deferred, out of scope by operator
decision 2026-07-06).

**Edge cases:** Do not treat untracked files in either repo as source truth; read only
`origin/main` refs of the Claude repo.

**Failure paths:** If `git ls-remote` shows upstream moved past `9470edc`, stop and extend the
window deliberately per KTD1.

**Test expectation:** none — classification/docs unit; verification is
`python3 scripts/validate_codex_plugins.py` still passing pre-port.

### U2. fleet-core Plugin And Codex Resolution Ladder

**Goal:** Create `plugins/fleet-core` with the fleet-commons primitives and a Codex-native shim,
and vendor the shim into saga, team-execution, mission-control, and unifi.

**Requirements:** R2, R9.

**Dependencies:** U1.

**Files:** `plugins/fleet-core/.codex-plugin/plugin.json`, `plugins/fleet-core/scripts/
fleet_commons_shim.py`, `plugins/fleet-core/scripts/fleet_commons/{tier_palette.py,
tier_resolver.py, tier_policy.json, models.json, effort_rider.py, retry_backoff.py,
render_tier_table.py}`, `plugins/fleet-core/references/{tier-palette.md, effort-convention.md}`,
vendored `fleet_commons_shim.py` in `plugins/{saga,team-execution,mission-control}/scripts/` and
`plugins/unifi/skills/unifi-{network,protect}/scripts/`, `plugins/fleet-core/tests/`,
`plugins/fleet-core/README.md`, `plugins/fleet-core/CHANGELOG.md`.

**Approach:** Port the upstream modules stdlib-only. Rewrite the shim ladder per KTD2:
`FLEET_COMMONS_ROOT` env → repo walk-up → `~/.codex` plugin/cache layout probe → fail-loud with
a typed error. Extend `models.json` per KTD3 with the Codex model registry (Claude names as
lineage keys mapping to Codex model + effort ceiling). Add the byte-identity drift test across
all vendored copies.

**Edge cases:** Shim must behave when run from an installed cache copy (read-only), from the
repo, and from a bare env override; no third-party imports; no writes at import time.

**Failure paths:** Resolution failure raises a typed, actionable error naming the ladder rungs
tried — never a silent fallback to stale logic.

**Test scenarios:** ladder rung order and fail-loud behavior; byte-identity of vendored shims;
tier resolve for each work shape; effort above ceiling HALTs; retry_backoff bounded attempts and
429 classification. Files: `plugins/fleet-core/tests/test_fleet_commons_resolution.py`,
`plugins/fleet-core/tests/test_tier_resolver.py`, `plugins/fleet-core/tests/test_retry_backoff.py`,
`plugins/fleet-core/tests/test_shim_drift.py`.

### U3. Tier And Effort Integration Across saga And team-execution

**Goal:** Route tier/effort decisions through the fleet-core palette: saga `execution_spec.py`
tier merge/validation, `team_emitter.py` effort cascade, team-execution TOML roster and
`sync_codex_agents.py` consuming the palette instead of hard-coded hints.

**Requirements:** R2, R6, R9.

**Dependencies:** U2.

**Files:** `plugins/saga/scripts/execution_spec.py`, `plugins/saga/scripts/team_emitter.py`,
`plugins/team-execution/scripts/sync_codex_agents.py`, `plugins/team-execution/agents/*.toml`
(25 files, role-tier metadata), `scripts/validate_codex_plugins.py`
(`TEAM_EXECUTION_MODEL_HINTS` derived from palette), related references.

**Approach:** Port upstream #362/#363/#370 semantics: `segment_units()` merges via
`tier_palette.strongest()`; `Tier.validate()` HALTs on effort over ceiling; effort is a
validated first-class field cascade-resolved per teammate. Regenerate the TOML roster through
`sync_codex_agents.py` dry-run before sync; the validator's hints become palette-derived, not a
second hand-maintained copy.

**Edge cases:** Roster regeneration must not touch unrelated files in `~/.codex/agents`;
generated-file markers preserved so stale agents remain removable.

**Failure paths:** Palette unresolvable (shim failure) blocks emission with the typed error, not
a silent default tier.

**Test scenarios:** tier merge picks strongest; HALT on ceiling breach; effort cascade
resolution; roster/validator/palette three-way drift guard. Files:
`plugins/saga/tests/test_execution_spec_tiers.py`,
`plugins/saga/tests/test_effort_rider.py`,
`plugins/team-execution/tests/test_agent_tier_sync.py`.

### U4. Saga Board Autonomy And Mission-Control Issue Verbs

**Goal:** Port the certificate-gated board-write loop end to end: reversibility certificate,
outcome board-sync, `board_progression.py`, schema-resolved status, and the paired
mission-control issue-write verbs.

**Requirements:** R3, R7 (verbs), R9.

**Dependencies:** U1 (classification), U2 (retry primitive for bounded board retries).

**Files:** `plugins/saga/scripts/reversibility_certificate.py` (new),
`plugins/saga/scripts/outcome_board_sync.py` (new),
`plugins/saga/scripts/board_progression.py` (new), `plugins/saga/scripts/outcome.py`,
`plugins/saga/scripts/outcome_dispatcher.py`, `plugins/saga/scripts/outcome_projection.py`,
`plugins/saga/skills/outcome/SKILL.md`, `plugins/saga/skills/loop/SKILL.md`,
`plugins/saga/skills/work/SKILL.md`,
`plugins/mission-control/scripts/sdlc_manager.py` (issue close/reopen/comment/label verbs,
`_rest_delete`), per-plugin tests.

**Approach:** Direct-port the stdlib scripts with `.codex/saga` state paths. The certificate
declares the allow-listed reversible board operations saga may write autonomously; anything
outside it degrades to operator-prompted mission-control flow (KTD5). `board_progression.py`
keeps idempotency keys, bounded retry via `retry_backoff`, and the `project_arc` derived arc.
Board status resolves from schema, never a hardcoded status name.

**Edge cases:** Missing certificate file means no autonomous writes at all; duplicate
idempotency keys are no-ops; `gh` absence degrades loudly.

**Failure paths:** A board write outside the certificate allow-list must refuse and surface the
proposed operation, not queue it silently.

**Test scenarios:** certificate allow/deny paths; idempotent re-runs; bounded retry on 429;
schema status resolution; verbs idempotency (close twice, label-add existing). Files:
`plugins/saga/tests/test_reversibility_certificate.py`,
`plugins/saga/tests/test_outcome_board_sync.py`,
`plugins/saga/tests/test_board_progression.py`,
`plugins/mission-control/tests/test_issue_write_verbs.py`.

### U5. Outcome Reconciliation And From-Objective Seeding

**Goal:** Port board↔saga drift reconciliation on resume and `/outcome start --from-objective`
DAG seeding from GitHub Objective sub-issues.

**Requirements:** R3.

**Dependencies:** U4 (board-sync ledger is reconciliation's input).

**Files:** `plugins/saga/scripts/outcome_reconcile.py` (new),
`plugins/saga/scripts/outcome_github.py` (new), `plugins/saga/scripts/outcome_edges.py` (new),
`plugins/saga/scripts/discover_subissues.py`, `plugins/saga/scripts/outcome.py`,
`plugins/saga/references/outcome-spec.md`, `plugins/saga/skills/outcome/SKILL.md`.

**Approach:** Direct-port; reconciliation is read-only detection with proposed repairs (KTD5).
From-objective seeding uses `gh` GraphQL for sub-issue discovery and infers `depends_on` edges;
output stays terminal-safe ASCII per the standing graph-output policy.

**Edge cases:** Objective with zero sub-issues; sub-issue cycles must be rejected at seed time;
board rows deleted out from under the ledger.

**Failure paths:** GraphQL failures surface partial-discovery clearly rather than seeding a
truncated DAG silently.

**Test scenarios:** drift detected/none; proposed-repair envelope shape; edge inference incl.
cycle rejection; empty objective. Files: `plugins/saga/tests/test_outcome_reconcile.py`,
`plugins/saga/tests/test_outcome_from_objective.py`.

### U6. Ship Ceremony, Branch Refresh, And Telemetry

**Goal:** Port `ship_ceremony.py` (with the open-PR, `--saga-id`, and `Fixes #N` auto-close
fixes), the branch-refresh-on-save fix, gate-divergence telemetry, and the run-fact ledger.

**Requirements:** R4.

**Dependencies:** U1.

**Files:** `plugins/saga/scripts/ship_ceremony.py` (new),
`plugins/saga/scripts/saga.py` (branch refresh + default-branch protection),
`plugins/saga/scripts/gate_divergence_reader.py` (new),
`plugins/saga/scripts/run_ledger.py` (new), `plugins/saga/scripts/lifecycle_state.py`,
`plugins/saga/references/{saga-spec.md, run-fact-ledger.md,
gate-divergence-instrumentation.md}`, `plugins/saga/skills/work/SKILL.md` and
`plugins/saga/skills/work/references/pr-continuation-loop.md`, affected skill texts (brainstorm, founder-review, investigate, loop,
outcome, retro).

**Approach:** Ceremony is a resumable idempotent state machine shelling `gh`; every mutating
transition (open PR, request review, merge-adjacent steps) stays behind explicit operator
confirmation per KTD5. Branch refresh updates branch/head_sha from live git on every save
without clobbering the default branch. Run ledger is append-only hash-chained
`run-facts.jsonl` under `.codex/saga`, derive-on-read, telemetry-only. Gate-divergence reader
computes rubber-stamp rate across gates.

**Edge cases:** Ceremony resume mid-state; PR already open (#481 path); task-kind saga
resolution by branch (#484); ledger chain verification on a truncated file.

**Failure paths:** Chain verification failure reports the first bad link and never "repairs" the
ledger; ceremony refuses to advance past a failed `gh` step.

**Test scenarios:** ceremony state transitions + resume + idempotency; branch refresh with and
without default-branch protection; ledger append/verify/tamper detection; divergence rate math.
Files: `plugins/saga/tests/test_ship_ceremony.py`, `plugins/saga/tests/test_saga_branch_refresh.py`,
`plugins/saga/tests/test_run_ledger.py`, `plugins/saga/tests/test_gate_divergence.py`.

### U7. Evidence Stack: Provenance Manifests And Verify-Panel Robustness

**Goal:** Port provenance manifests (verified vs adjudicated), manifest store/reader,
completeness-gate updates, and verify-panel consensus recomputation.

**Requirements:** R5.

**Dependencies:** U1; U3 (execution_spec shared file — sequence edits to avoid conflicts).

**Files:** `plugins/saga/scripts/provenance_manifest.py` (new),
`plugins/saga/scripts/manifest_store.py` (new), `plugins/saga/scripts/manifest_reader.py` (new),
`plugins/saga/scripts/completeness_gate.py`, `plugins/saga/scripts/execution_spec.py`,
`plugins/saga/scripts/outcome_orchestrator.py`, `plugins/saga/references/execution-spec.md`,
skills code-review/qa/retro/work/outcome.

**Approach:** Direct-port the manifest trio; wire completeness gate and orchestrator to consume
them. Verify-panel logic recomputes consensus over the verifiers that actually reported,
tolerating failed and non-applicable members instead of fabricating N/A votes — matching
team-execution's dimension-exclusion semantics (U8).

**Edge cases:** Zero reporting verifiers (panel void, not pass); adjudicated overriding verified
must be visibly marked; manifest store on read-only filesystem.

**Failure paths:** Malformed manifest is a typed error at read, never a silent skip.

**Test scenarios:** verified-vs-adjudicated distinction round-trips; consensus over partial
panels; void panel; completeness gate consuming manifests. Files:
`plugins/saga/tests/test_provenance_manifest.py`,
`plugins/saga/tests/test_verify_panel_robustness.py`.

### U8. Engine Routing And Team-Execution Protocol Updates

**Goal:** Port engine capability routing capability-gated to Codex backends, artifact-pointer
passing, consensus hardening, and the 2.3.0/2.4.0 protocol content adapted to serial fallback.

**Requirements:** R6, R9.

**Dependencies:** U3 (emitter/spec files shared), U7 (consensus semantics shared).

**Files:** `plugins/saga/scripts/engine_registry.py` (new),
`plugins/saga/scripts/engine_resolver.py` (new), `plugins/saga/scripts/engine_dispatch.py` (new),
`plugins/saga/references/{engine-dispatch.md, engine-registry.yaml}`,
`plugins/saga/skills/{plan,doc-review}/SKILL.md`,
`plugins/team-execution/scripts/artifact_pointer.py` (new),
`plugins/team-execution/references/{artifact-pointers.md, external-engine-workers.md,
consensus-protocol.md, worker-manifest.md, validator-evidence-state.md,
validator-execution-order.md}`, `plugins/team-execution/skills/team-execution/SKILL.md`.

**Approach:** Registry/resolver port directly (stdlib + YAML-in-repo). Dispatch resolves only to
backends this host proves: team-execution surfaces or serial fallback; Workflow/TeamCreate
chaperone emission is negative-gated with unavailable/degraded receipts (KTD4). Resident-worker
residency and required-evidence-absence (`missing-output` vs `skipped-by-config`) content is
adapted as protocol references with serial-mode wording — no persistent-teammate claims Codex
cannot honor.

**Edge cases:** Capability with no resolvable engine (advisory mode returns "unresolvable", run
mode halts); explicit engine unavailable halts rather than substitutes; pointer to a missing
artifact is a typed failure.

**Failure paths:** Dispatch never falls back to an unproven backend silently; every degrade
emits a receipt.

**Test scenarios:** capability resolution advisory vs run; halt-not-substitute; negative gates
for Workflow/fork/goal; pointer round-trip + missing-target failure; consensus dimension
exclusion. Files: `plugins/saga/tests/test_engine_routing.py`,
`plugins/team-execution/tests/test_artifact_pointers.py`,
`plugins/team-execution/tests/test_consensus_hardening.py`.

### U9. Mission-Control Vendored Behavioral Sync And Unifi Retry

**Goal:** Bring the vendored mission-control to canonical behavior (operations rename, recovery
fix, PUT fix, executor-profile lint) and adopt shared retry in the unifi clients.

**Requirements:** R7, R8.

**Dependencies:** U2 (shim), U4 (sdlc_manager.py shared file).

**Files:** `plugins/mission-control/scripts/sdlc_manager.py`,
`plugins/mission-control/config/{project-mappings.json, sdlc-schema.json}`,
`plugins/mission-control/scripts/executor_profile_lint.py` (new),
`plugins/mission-control/skills/**` (operations wording),
`plugins/unifi/skills/unifi-network/scripts/unifi_network_client.py`,
`plugins/unifi/skills/unifi-protect/scripts/unifi_protect_client.py`, per-plugin tests.

**Approach:** Behavioral sync per KTD8: rename `jeff-intent`→`operations` across config, script
choices, and skill guidance with dated provenance notes; port the create-prepared recovery and
contents-API PUT fix; executor-profile lint validates against the fleet-core palette via the
vendored shim. Unifi clients route rate-limit handling through `retry_backoff`.

**Edge cases:** Saved invocations using `--project jeff-intent` must fail with a migration
message, not map silently; intentional Codex divergences (allowlists, confirmation gates) must
survive the sync — run their guard tests.

**Failure paths:** If canonical-vs-vendored divergence is ambiguous (can't tell intentional from
drift), stop and classify in U1's artifact rather than guessing.

**Test scenarios:** operations mapping + legacy-name rejection; create-prepared recovery
sidecar; verbs covered in U4; lint pass/fail against palette; unifi 429 bounded retry. Files:
`plugins/mission-control/tests/test_operations_rename.py`,
`plugins/mission-control/tests/test_executor_profile_lint.py`,
`plugins/unifi/tests/test_unifi_retry.py` (or the plugins' existing client test files).

### U10. Manifests, Inventory, Docs, And Final Validation

**Goal:** Align every release surface with what actually shipped and prove the repo green.

**Requirements:** R10, R11, KTD6.

**Dependencies:** U2–U9.

**Files:** `plugins/*/.codex-plugin/plugin.json`, `plugins/*/CHANGELOG.md`, `README.md`,
`docs/portability/{matrix.md, provenance.md}`, `docs/validation/saga-family-target-inventory.json`,
`scripts/validate_codex_plugins.py` (`TARGET_EXPECTED_PLUGINS`, roster, hints), `PORTABILITY.md`
files, `docs/engineering-journal/{DECISIONS.md, LEARNINGS.md}`.

**Approach:** Versions per KTD6: saga 0.64.0 (parity label), team-execution and mission-control
and unifi to the versions whose behavior is now exposed, fleet-core new, deploy unchanged.
Changelogs describe Codex-visible behavior only. Validator inventory updated last, after
behavior exists. Journal captures the cycle's LEARNINGS (at minimum: the shim-ladder adaptation
and any upstream test-adaptation surprises) in the same commits as the changes.

**Edge cases:** Baseline plugins in `LEGACY_EXPECTED_PLUGINS` vs target fixtures must stay
consistent; stale-host-path bans must not flag lineage-only mentions in classification docs.

**Failure paths:** Any validator or pytest failure blocks the cycle close; no
"known-failure" waivers without a recorded decision.

**Test scenarios:** full-suite proof, not new tests: `python3 scripts/validate_codex_plugins.py`
exits 0; `python3 -m pytest` green; targeted re-run of each new unit's tests. Files: existing
suite.

## Scope Boundaries

Out of scope (true non-goals this cycle):

- `agy` plugin in any form (operator decision 2026-07-06; Antigravity ecosystem lives in its own
  repo). Recorded as a deferred matrix row only.
- Claude hooks as active surface: PreCompact spore hooks, team-spawn residency hook.
- Workflow/fork/goal backends, `.workflow.js` wave-thunk retry wrapping, TeamCreate chaperone
  emission.
- `marketplace.json` generation and marketplace publishing.
- redis-channel plugin activation.
- Claude agent markdown and command files (contract-text mining only).
- Chasing upstream past `9470edc`.

Deferred to follow-up work (want it eventually, not now):

- Remote gate approval transport (#379) — lands with a future redis-channel server-boundary
  proof; outcome gates stay terminal-prompted.
- `saga_spore.py` state serializer — revisit if Codex grows a compaction/session seam.
- Sandbox spawn-site enforcement mechanism — references adapt now (U8 wording), enforcement
  waits for a Codex isolation primitive.
- CHANGELOG canonical-grammar adoption for plugins not otherwise bumped.

## Risk Analysis & Mitigation

- **Shim-ladder divergence from upstream** (highest): a Codex-modified `fleet_commons_shim.py`
  breaks the byte-identity assumption upstream drift guards rely on. Mitigation: our drift test
  compares Codex copies to the Codex fleet-core canonical (not upstream's), and U1's
  classification records the deliberate divergence so future syncs re-apply it knowingly.
- **Shared-file collision**: `execution_spec.py`, `team_emitter.py`, `sdlc_manager.py`, and
  `outcome.py` are each touched by multiple units. Mitigation: dependency ordering above is
  strict; units editing the same file land serially (U3 before U7 before U8; U4 before U9).
- **Vendored mission-control drift vs intent**: the sync could flatten intentional Codex
  divergences. Mitigation: guard tests run in U9 and the LEARNINGS 2026-06-20 rule is the
  acceptance bar.
- **Version-label confusion**: saga 0.64.0 as parity label while surface is selective.
  Mitigation: KTD6 + PORTABILITY.md non-ported table, same as the 0.41 precedent.
