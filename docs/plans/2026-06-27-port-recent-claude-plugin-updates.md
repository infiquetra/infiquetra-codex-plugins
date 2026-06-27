---
title: Port Recent Claude Plugin Updates Into Codex Plugins
type: chore
status: active
date: 2026-06-27
---

# Port Recent Claude Plugin Updates Into Codex Plugins

## Summary

Port the recent `infiquetra-claude-plugins` updates into this Codex-native plugin repo without turning this repo into a blind mirror. The concrete upstream delta since the Codex repo last moved is mostly Saga OutcomeOrchestrator work, plus team-execution cleanup and small Claude-only agent metadata updates in other plugins.

The implementation should treat `infiquetra-claude-plugins` `80e8731..aad9d6a` as the source delta, then adapt only the Codex-runnable surfaces into `.codex-plugin` manifests, `skills/`, bundled scripts, docs, tests, and validation inventory.

## Problem Frame

Codex addendum from trust-but-verify review: treat `origin/main` as the implementation baseline unless refreshed; local `main` may include this plan and review state.

The Codex repo currently declares itself a Codex-native adapter, not a full mirror of Claude plugins. `README.md` lists `saga` at `0.22.1`, `team-execution` at `2.0.0`, and several baseline plugins that do not carry Claude agent surfaces. Upstream Claude `main` is now at `aad9d6a`; the plugin-bearing range through `1a1c1a5` ships Saga `0.38.0`, including OutcomeOrchestrator, followed by docs-only ideation commit `aad9d6a`. Codex `origin/main` is at `36d4a5d`; local `main` may include this plan commit and must be separated from implementation baseline.

The risk is not missing a copy operation; the risk is importing Claude-only capabilities as if Codex can execute them, or bumping versions where Codex does not actually expose the changed surface.

## Grounding

- Codex source policy says this repo carries selected Codex-ready plugin surfaces and is not a full mirror.
- `docs/portability/matrix.md` already says Saga should port skills, references, scripts, lifecycle state, and handoff envelopes while omitting command files and Claude-only backend choices.
- `scripts/validate_codex_plugins.py` hard-codes expected current plugin versions and skill inventories, including `saga` `0.22.1` and `team-execution` `2.0.0`.
- Upstream recent plugin delta touches `plugins/saga` heavily, `plugins/team-execution` materially, and `deploy`, `home-lab-ops`, `mission-control`, `unifi`, and `redis-channel` mostly through Claude agent metadata, changelogs, or manifest versions.
- `git diff --name-status 1a1c1a5..aad9d6a` adds only `docs/ideation/2026-06-26-vecu-port-seeds-ideation.md`; classify it in U1 as docs-only non-Codex-surface context, not implementation surface.
- Codex has Saga-only skills not present in Claude current surface: `ceo-review`, `implementation-spec`, and `product-review`. These must be preserved.
- Claude has current Saga skills not present in Codex: `outcome` and `promote`. `outcome` is in the recent delta and should be ported; `promote` is not in the recent delta and should stay out unless scope is explicitly expanded.

## Requirements

R1. Port the recent upstream delta from Claude `80e8731..aad9d6a` into Codex-runnable plugin surfaces without losing Codex-only skills or state paths.

R2. Add the Saga OutcomeOrchestrator surface in Codex form: `skills/outcome`, supporting references, bundled scripts, docs, and tests that prove coordinator invariants.

R3. Preserve Codex host truth. Do not expose Claude command files, Claude agent files, Claude `.claude-plugin` manifests, or Claude-only Workflow behavior as Codex-executable unless there is a verified Codex equivalent.

R4. Port team-execution 2.2 cleanup where it affects Codex: remove stale tmux/pane/setup guidance from active Codex skill/docs, preserve delegated/serial Codex fallback, and add drift tests.

R5. Classify non-portable recent Claude updates explicitly. Agent model pins in `deploy`, `home-lab-ops`, `mission-control`, `unifi`, and `redis-channel` should not become Codex version bumps unless the matching Codex user-facing content is actually present.

R6. Update manifests, marketplace inventory, README tables, portability docs, generated Saga docs, validation expectations, and changelogs only where the Codex surface truly changes.

R7. Finish with both narrow targeted validation and broad final validation: plugin validator, generated-doc checks, targeted Saga/team-execution tests including adapted top-level upstream tests, and full pytest.

R8. Port the full Claude `team-execution/agents` roster into Codex agent definitions, not only role prompts. Keep all reviewer, scanner, tester, monitor, and deploy-watcher identities available to team-execution.

R9. Add a repeatable Claude-to-Codex porting procedure for future upstream refreshes, including source-range proof, surface classification, agent roster sync, version policy, validation gates, and review artifact updates.

## Key Technical Decisions

KTD1. Source delta is commit-bounded, not date-vague: Use Claude `80e8731..aad9d6a`, with `1a1c1a5..aad9d6a` explicitly classified as docs-only ideation context. Re-check both `origin/main` refs before implementation. If upstream advances again, either extend the range deliberately or stop and refresh this plan.

KTD2. Codex adaptation beats mirroring: Copy or port behavior into `.codex-plugin`, `skills/`, `scripts/`, `references/`, docs, and tests. Do not copy `.claude-plugin`, `commands/`, `agents/`, or `hooks/` wholesale.

KTD3. OutcomeOrchestrator is a new Codex skill, not a slash command: Port `plugins/saga/skills/outcome/SKILL.md` and the script/reference stack. Mine `commands/outcome.md` only for argument contract text where useful.

KTD4. Backend menu must be Codex capability-gated: Preserve the Outcome coordinator invariant that it routes and never executes leaf work. Map Claude-only backends Workflow/fork/goal to explicit unavailable or degraded Codex outcomes unless a Codex runtime capability is verified in tests. Treat `subagent` separately: Codex can expose subagent tooling, but use it only when the host exposes callable tooling and user/task context authorizes delegated work; otherwise halt/degrade visibly.

KTD4a. Codex terminal output stays terminal-safe: default `outcome graph` output must be ASCII/table/prose, not Mermaid. Mermaid may remain only as an explicit export format or repository documentation artifact.

Codex addendum: implement an explicit backend capability profile. `inline`, `team-execution`, and `manual` are the safe floor. `subagent` is conditional on callable Codex tooling and delegation authorization. Workflow/fork/goal remain unavailable unless tests prove a Codex equivalent. Default `outcome graph` output must be terminal-safe ASCII/table/prose; keep Mermaid only behind explicit export or docs paths.

KTD5. Saga state stays Codex-native: Keep `.codex/saga` and other Codex paths when porting upstream `saga.py` and lifecycle changes; do not regress to `.claude/saga`.

KTD6. Team-execution cleanup is behavioral for Codex: Remove active references to `validator-pane-behavior.md`, `team-setup`, tmux panes, and agent-overflow from Codex active surfaces. Historical changelog notes may remain clearly historical.

KTD7. Version bumps must mean exposed behavior: Do not bump `deploy`, `home-lab-ops`, `mission-control`, `unifi`, or `redis-channel` solely because Claude agent frontmatter changed. If a version is bumped, the plan unit must also port the actual Codex-visible content behind that version.

KTD8. Tests are part of the port, not follow-up: Every feature-bearing unit below includes the upstream or adapted tests needed to catch drift. Missing tests are a blocker, not a note.

KTD9. Team-execution agents are Codex agent definitions: repo-managed source files live under `plugins/team-execution/agents/` and sync into `~/.codex/agents/`. The sync must be explicit, preserve unrelated local agents, and mark generated files so stale generated agents can be removed safely.

KTD10. Model mapping is Codex-native, not Claude names copied as behavior: preserve Claude `opus`/`sonnet`/`haiku` lineage metadata, map them to Codex model and effort hints, and verify which fields Codex actually honors. If Codex TOML cannot pin model directly, team-execution passes model overrides at spawn time and keeps TOML effort/profile defaults.

## Implementation Units

### U1. Refresh Source Inventory And Scope

Record exactly what is being ported and what is being classified as non-portable.

**Goal:**

Create the implementation baseline so later units do not accidentally widen into full mirror work.

**Requirements:**

R1, R3, R5, R6.

**Dependencies:**

None.

**Files:**

`docs/portability/matrix.md`, `docs/portability/provenance.md`, `docs/engineering-journal/DECISIONS.md`, `docs/engineering-journal/LEARNINGS.md`, `README.md`.

**Approach:**

Codex addendum: before wiring dispatch, add backend-profile tests and graph-output tests. Replace `AskUserQuestion` prose with Codex question-tool fallback wording: use the tool only when available, otherwise ask a concise blocking question in chat.

Update the source snapshot from the old June 6 catalog to the current Claude/Codex refs. Add a concise classification table: portable now, Codex-adapted, non-portable Claude-only, docs-only source context, and deferred pre-existing upstream differences. Treat `promote` and `redis-channel` as out of this recent-delta port unless the operator expands scope.

**Edge cases:**

Do not overwrite existing context-audit lineage. Do not treat untracked local files in either repo as source truth.

**Error / failure paths:**

If `git ls-remote origin main` no longer matches local `main`, stop and refresh the delta rather than mixing stale and current evidence.

**Verification:**

`python3 scripts/validate_codex_plugins.py` should still pass or fail only on known pre-port inventory mismatches that U5 will resolve.

### U2. Port Saga Core Orchestration Changes

Bring over the non-outcome Saga engine changes that OutcomeOrchestrator depends on.

**Goal:**

Update Saga lifecycle storage, backend recommendation, orchestration provenance, execution spec emission, and override-rate support while preserving Codex paths and backend truth.

**Requirements:**

R1, R3, R6, R7.

**Dependencies:**

U1.

**Files:**

`plugins/saga/scripts/saga.py`, `plugins/saga/scripts/lifecycle_state.py`, `plugins/saga/scripts/execution_spec.py`, `plugins/saga/scripts/team_emitter.py`, `plugins/saga/scripts/override_rate_reader.py`, `plugins/saga/references/operator-choice.md`, `plugins/saga/references/execution-spec.md`, `plugins/saga/references/saga-spec.md`, `plugins/saga/tests/test_lifecycle_state.py`, `plugins/saga/tests/test_saga_state.py`, plus adapted tests from upstream `tests/test_workflow_emitter.py`, `tests/test_operator_choice_drift.py`, and `tests/test_override_rate.py`.

**Approach:**

Port upstream logic selectively. Keep `.codex/saga` in `saga.py`. Add orchestration recommended/operator-choice/downgrade fields if they remain meaningful for Codex. Adapt `operator-choice.md` so Codex does not claim Workflow execution unless a Codex equivalent is verified. Keep existing Codex tests for `inline` and `team-execution` behavior green.

**Edge cases:**

Existing sagas with no new orchestration fields must still parse. A save tick with no explicit orchestration mode must not silently restamp `inline` over a prior richer choice.

**Error / failure paths:**

Malformed execution specs must fail validation before any generated workflow or saga tick is accepted.

**Verification:**

Run `PYTHONPATH=. python3 -m pytest plugins/saga/tests/test_lifecycle_state.py plugins/saga/tests/test_saga_state.py tests/test_workflow_emitter.py tests/test_operator_choice_drift.py tests/test_override_rate.py -q` plus adapted execution-spec checks if they land under different names.

### U3. Add Codex OutcomeOrchestrator

Port the new OutcomeOrchestrator as a Codex skill and script stack.

**Goal:**

Expose `saga:outcome` as a coordinator above leaf sagas with durable DAG state, derived status, idempotent advance, report/projection, worktree lifecycle, liveness, economics, and integration coverage.

**Requirements:**

R2, R3, R6, R7.

**Dependencies:**

U2.

**Files:**

`plugins/saga/skills/outcome/SKILL.md`, `plugins/saga/references/outcome-spec.md`, `plugins/saga/scripts/outcome.py`, `plugins/saga/scripts/outcome_spec.py`, `plugins/saga/scripts/outcome_store.py`, `plugins/saga/scripts/outcome_dispatcher.py`, `plugins/saga/scripts/outcome_github.py`, `plugins/saga/scripts/outcome_liveness.py`, `plugins/saga/scripts/outcome_merge.py`, `plugins/saga/scripts/outcome_orchestrator.py`, `plugins/saga/scripts/outcome_projection.py`, `plugins/saga/scripts/outcome_report.py`, `plugins/saga/scripts/outcome_costs.py`, `plugins/saga/scripts/outcome_decompose.py`, `plugins/saga/scripts/outcome_worktrees.py`, `docs/saga/*`, `docs/saga/generated/lifecycle-facts.json`, adapted upstream `test_outcome_*` suites, and Codex backend-profile/graph-output drift tests.

**Approach:**

Codex addendum: before wiring dispatch, add backend-profile tests and graph-output tests. Replace `AskUserQuestion` prose with Codex question-tool fallback wording: use the tool only when available, otherwise ask a concise blocking question in chat.

Port upstream modules in dependency order: spec, store/replay, command coordinator, dispatcher seam, completion/merge, decompose/worktrees, report/projection, backend degrade/liveness, economics, then integration. Replace Claude-only command references with Codex skill invocation guidance, and replace `AskUserQuestion` prose with Codex question-tool fallback wording: use the tool only when available, otherwise ask a concise blocking question in chat. Add Codex backend profile before wiring dispatch: `inline`, `team-execution`, and `manual` are the safe floor; `subagent` is conditional on callable Codex tooling and delegation authorization; Workflow/fork/goal stay unavailable unless proven by tests. Default `graph` output must be terminal-safe ASCII/table/prose; keep Mermaid only behind explicit export/docs path. Keep the coordinator invariant: it routes leaf work and prints native leaf re-entry instructions; it does not perform leaf implementation work.

**Edge cases:**

Deleting `.codex/saga` or git-common-dir cache must not lose canonical outcome structure. Repeated `advance` must not double-dispatch. GitHub outages must defer rather than create sticky false terminal states. Worktree liveness must use real git path normalization in at least one regression test.

**Error / failure paths:**

Invalid specs fail before dispatch. Unavailable backends return explicit HALT/degrade receipts rather than silently substituting unverified behavior. `commit` must refuse `main`/`master`.

**Verification:**

Run `PYTHONPATH=. python3 -m pytest tests/test_outcome_*.py tests/test_outcome_backend_profile.py tests/test_outcome_graph_output.py -q` plus one end-to-end integration slice proving dispatch is load-bearing, not bypassed by fake harvest data.

### U4. Port Team-Execution 2.2 Cleanup And Codex Agent Roster

Remove stale active tmux/pane guidance and add the complete Codex-native team-execution agent roster.

Codex agent roster addendum: port all 25 upstream Claude team-execution agents into Codex TOML definitions, then make team-execution select named Codex agents when delegated mode is available. Keep serial fallback for unavailable or backpressured agents, but do not reduce the source roster.

Claude model lineage maps to Codex defaults as follows: `opus` reviewer agents use high reasoning and the strongest available model hint, `sonnet` tester agents use medium/high reasoning and the standard strong model hint, and `haiku` scanner/monitor agents use low/medium reasoning and the fast model hint. Tests must prove generated TOML parses and the sync layer preserves these hints or records the spawn-time override needed.

**Goal:**

Make Codex team-execution active docs match post-2.2 model: no `/team-setup`, no pane behavior reference, no tmux setup path; full reviewer/scanner/tester/monitor roster is available as Codex agents with delegated and serial fallback semantics.

**Requirements:**

R3, R4, R6, R7, R8.

**Dependencies:**

U1.

**Files:**

`plugins/team-execution/agents/*.toml`, `plugins/team-execution/scripts/sync_codex_agents.py`, `plugins/team-execution/skills/team-execution/SKILL.md`, `plugins/team-execution/skills/team-execution/references/`, `plugins/team-execution/README.md`, `plugins/team-execution/CHANGELOG.md`, `plugins/team-execution/.codex-plugin/plugin.json`, `tests/test_validate_codex_plugins.py`, `tests/test_team_execution_agents.py`, new or adapted team-execution drift tests.

**Approach:**

Delete/retire `validator-pane-behavior.md` active references. Update skill reference list and README. Do not copy Claude `commands/`; transform the full Claude `agents/` roster into Codex `.toml` agent definitions plus sync tooling. Add guard tests equivalent to upstream release-triad/tmux cleanup, plus agent roster completeness, generated TOML parsing, dry-run sync, stale-generated-agent cleanup, and spawn-profile mapping tests.

**Edge cases:**

Existing docs may discuss old lineage if clearly historical. Active skill guidance must not ask the user to use tmux panes or run deleted setup commands. Agent sync must not overwrite unrelated local `~/.codex/agents/*.toml` files.

**Error / failure paths:**

If validator docs still mention `validator-pane-behavior.md` deletion, validation fails. If an agent cannot be synced or spawned, team-execution records delegated-mode unavailability and falls back to serial role execution.

**Verification:**

Run `PYTHONPATH=. python3 -m pytest plugins/team-execution/tests tests/test_team_execution_plugin.py tests/test_team_emitter.py tests/test_team_execution_agents.py -q` plus grep-based drift over active surfaces and a dry-run agent sync proof.
### U5. Update Codex Manifests, Marketplace, And Validation Inventory

Bring metadata into sync with actual Codex behavior after U2-U4.

**Goal:**

Update versions, skill inventories, README tables, and validator constants so they describe the real Codex plugin surface.

**Requirements:**

R1, R5, R6, R7.

**Dependencies:**

U2, U3, U4.

**Files:**

`.agents/plugins/marketplace.json`, `plugins/saga/.codex-plugin/plugin.json`, `plugins/team-execution/.codex-plugin/plugin.json`, `plugins/*/CHANGELOG.md`, `README.md`, `scripts/validate_codex_plugins.py`, `docs/portability/matrix.md`, `docs/cutover/cache-replacement.md`.

**Approach:**

Bump `saga` only after `outcome` is present and tested. Bump `team-execution` only after active tmux/pane cleanup lands. For `deploy`, `home-lab-ops`, `mission-control`, `unifi`, and `redis-channel`, add explicit portability notes for Claude-only agent model pins and avoid version bumps unless matching Codex-visible content is ported. Update validator expected skill lists to include `outcome` only after U3.

**Edge cases:**

Do not bump `home-lab-ops` to a version that implies unported `team-scaffold`. Do not advertise `redis-channel` as active unless its server boundary proof is reopened.

**Error / failure paths:**

Manifest version, marketplace version, README table, and validation constants must not disagree.

**Verification:**

Run `python3 scripts/validate_codex_plugins.py` and targeted manifest/profile tests.

### U6. Regenerate Docs And Run Final Gates

Close the port with generated documentation, validation, and residual-risk notes.

**Goal:**

Ensure all generated and human docs reflect the new Codex surface and every ported behavior has a test gate.

**Requirements:**

R6, R7.

**Dependencies:**

U1, U2, U3, U4, U5.

**Files:**

`docs/saga/*`, `docs/saga/generated/lifecycle-facts.json`, `docs/saga/visual-assets/*`, `tests/test_saga_docs_package.py`, `tests/test_saga_doc_formatting.py`, `docs/engineering-journal/DECISIONS.md`, `docs/engineering-journal/LEARNINGS.md`.

**Approach:**

Regenerate Codex Saga docs from the Codex source model, not by copying Claude `plugins/saga/docs` wholesale. Add journal entries explaining the Codex adaptation decisions and any intentionally deferred upstream surfaces.

**Edge cases:**

Generated SVG/PDF/PNG outputs should update only if source facts changed. Avoid broad formatting churn in unrelated docs.

**Error / failure paths:**

If docs generation cannot reproduce committed assets, stop and fix the renderer/model drift before considering the port complete.

**Verification:**

Run:

```bash
python3 scripts/build_saga_docs_facts.py --check
python3 scripts/render_saga_docs_assets.py --check
PYTHONPATH=. python3 -m pytest tests/test_saga_docs_package.py tests/test_saga_doc_formatting.py -q
python3 scripts/validate_codex_plugins.py
PYTHONPATH=. python3 -m pytest plugins/saga/tests plugins/team-execution/tests tests/test_outcome_*.py tests/test_workflow_emitter.py tests/test_operator_choice_drift.py tests/test_override_rate.py tests/test_team_emitter.py tests/test_team_execution_plugin.py tests/test_validate_codex_plugins.py -q
PYTHONPATH=. python3 -m pytest tests/test_outcome_backend_profile.py tests/test_outcome_graph_output.py -q
PYTHONPATH=. python3 -m pytest -q
```

## Repeatable Claude-To-Codex Port Procedure

Use this checklist for every future `infiquetra-claude-plugins` refresh.

1. Refresh and record source truth: fetch both repos, record the Claude range, Codex `origin/main`, local branch, dirty state, and exact plugin-bearing commits.
2. Inventory the delta by surface: skills, references, scripts, tests, docs, agents, manifests, commands, hooks, MCP/apps, workflows, and changelogs.
3. Classify every changed surface as `direct-port`, `codex-adapt`, `metadata-only`, `claude-only`, `deferred`, or `blocked`; update portability/provenance before implementation widens.
4. For team-execution agent deltas, regenerate the full Codex TOML roster, update model/effort mapping, run dry-run sync, and verify no unrelated `~/.codex/agents` files would be touched.
5. Port behavior in dependency order: shared scripts/references first, skills second, manifests/docs/README last. Do not bump versions until Codex-visible behavior exists and tests pass.
6. Run targeted tests for each changed plugin, then `python3 scripts/validate_codex_plugins.py`, docs generation checks, and `PYTHONPATH=. python3 -m pytest -q`.
7. Update the review artifact with unresolved portability risks, non-ported Claude-only surfaces, checks run, and exact residual follow-up.
8. Commit only intended repo files; leave cache copies, local Codex config, synced generated agents, and unrelated user files untouched unless the task explicitly includes install/sync.
## Scope Boundaries

- No full `infiquetra-claude-plugins` mirror.
- No `redis-channel` activation in Codex in this plan.
- No `promote` skill port unless the operator expands from recent-delta port to current-surface parity.
- No Claude `.claude-plugin`, `commands/`, `agents/`, or hook installation copied as-is.
- No deployment, marketplace install, or cache replacement work until repository validation is green.

## Deferred Follow-Up Work

- Reassess `redis-channel` as its own server-boundary proof.
- Decide whether `promote` belongs in Codex Saga after OutcomeOrchestrator lands.
- Revisit Codex dynamic-workflow or multi-agent backend support if a callable equivalent to Claude Workflow becomes available and stable.
- Consider a broader non-Saga plugin parity pass for `home-lab-ops` 1.1/1.2 and other baseline plugins, but do not hide it inside this port.

## Recommended Execution

Run this inline through U1 and U5 metadata decisions, but use team-execution review gates for U2-U4 because the work touches more than eight files, includes orchestration logic, and can create false host-capability claims. Treat U3 OutcomeOrchestrator as the highest-risk unit and land it only after U2 tests pass.
