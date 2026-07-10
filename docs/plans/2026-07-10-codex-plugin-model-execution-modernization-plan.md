---
title: Codex Plugin Model, Execution, and Upstream Modernization Plan
type: feat
status: active
date: 2026-07-10
origin: docs/plans/2026-06-27-port-recent-claude-plugin-updates.md
deepened: 2026-07-10
reviewed: 2026-07-10
---

# Codex Plugin Model, Execution, and Upstream Modernization Plan

## Summary

Modernize the Codex model, agent, and execution contracts before importing the next Claude plugin window. The dependency order is: freeze capability truth, land the Sol/Terra/Luna policy in fleet-core, activate and attest Team Execution, repair Saga's Codex-native execution boundary, then selectively import the Claude `0.64.0 -> 0.75.17` family delta and cut over only after fresh-session proof.

This plan supersedes the uncompleted portions of `docs/plans/2026-06-27-port-recent-claude-plugin-updates.md` without rewriting that plan's history. It continues the existing `task-port-recent-claude-plugin-updates` Saga.

---

## Problem Frame

The current Codex source is internally green but describes an older runtime. Codex `788902513e48ea95fd0504ac3c850c8c02e5d920` ships Saga `0.64.0`, team-execution `2.3.0`, and fleet-core `0.5.0`; the next frozen Claude target is `38742ece89880a6b140be237edad6d3f13c97b54`, at Saga `0.75.17`, team-execution `2.14.3`, and fleet-core `0.8.4`.

The focused source window `9470edc..38742ece` contains 156 files: 12 fleet-core files, 63 Saga files, 10 team-execution files, and 71 tests. Importing that window first would build new routing, trust, economics, and reconciliation behavior on stale Codex assumptions.

Five current gaps determine the order:

- `plugins/fleet-core/scripts/fleet_commons/models.json:4-13` still maps work to GPT-5.5, GPT-5.4, and GPT-5.4-mini and defines only `low` through `xhigh`.
- All 25 team-execution agent TOMLs carry an inert `codex_model_hint`; `scripts/validate_codex_plugins.py:505-524` rejects active `model`, and none of those profiles is currently installed in `~/.codex/agents`.
- `plugins/saga/scripts/outcome.py:69-104` says its default dispatcher runs nothing, while `plugins/saga/scripts/outcome_dispatcher.py:151-162` returns a `leaf-*` identifier that can be recorded as dispatched without a launched task.
- Codex 0.144.1 reports models, multi-agent, hooks, goals, and plugins as live surfaces, but Saga still mixes Goal, hooks, subagents, fork, and Workflow into one backend vocabulary. The current task's spawn contract remains generic, so named-role dispatch is not yet proved.
- `plugins/saga/scripts/saga.py:553-597` carries default-valued scalars from the prior tick, but `_explicit_save_scalars` at `plugins/saga/scripts/saga.py:1372-1379` recognizes only orchestration mode. A literal `--destination plan-only` therefore retained this Saga's prior `pr` destination until an append-only correction was written.

The machine's global default is currently `gpt-5.6-terra` at `max`, and `agents.max_depth` is `1`. Plugin policy must therefore select role-specific models explicitly rather than inherit a mutable machine default, and leaf profiles must not use Ultra to create unbounded or unaudited delegation.

---

## Recommended Order

The order establishes a trustworthy Codex execution substrate before any coupled upstream import.

| Order | Unit | Why it comes here |
|---:|---|---|
| 1 | U1. Freeze capability and source truth | Every later decision depends on one reproducible Codex and Claude boundary. |
| 2 | U2. Modernize fleet-core policy | Model, effort, fallback, cost, and proof vocabulary are shared dependencies. |
| 3 | U3. Activate managed agents | Team Execution cannot delegate named roles until profiles are discoverable and enforce active model settings. |
| 4 | U4. Attest Team Execution | Installed profiles are not execution proof; receipts and machine gates must exist first. |
| 5 | U5. Repair Saga's Codex boundary | Saga can consume real dispatch receipts only after Team Execution defines them. |
| 6 | U6. Import correctness and engine substrate | Portable Claude behavior now has Codex-native model and execution seams to target. |
| 7 | U7. Import trust, economics, and advisory reconciliation | These layers depend on proven dispatch, receipts, and engine substrate. |
| 8 | U8. Release and cut over | Metadata and installed state follow behavior and fresh-session proof. |

---

## High-Level Technical Design

The modernization separates concepts the current backend vocabulary overloads.

```text
 Live Codex catalog                    Frozen Claude window
 Sol / Terra / Luna                    9470edc..38742ece
 low..max + Ultra                               |
          |                                      |
          +----------> U1 capability contract <-+
                              |
                   U2 fleet-core policy
                   model | effort | fallback
                   cost  | proof  | receipts
                         /                 \
                        v                   v
             U3 managed agent profiles
                        |
             U4 named dispatch + gates
                        |
                     U5 Saga
                        |
             U6 engine substrate
                               | lifecycle/state
                               | continuation: turn | explicit Goal
                               | dispatch: inline | TE serial | TE delegated | manual
                               | identity: generic | named-attested
                               | hooks: observe | persist | guard
                               v
                 U7 trust/economics/reconciliation
                               |
                    U8 release + fresh-session proof
```

Ultra is intentionally outside the scalar effort ladder. Codex represents it through the model control, but its documented behavior adds automatic subagent delegation; the policy therefore treats Ultra as a root orchestration profile, not as the next leaf-agent effort after `max`.

Saga remains the durable lifecycle and outcome-state owner. Goal is an optional continuation substrate for an explicitly requested long-running objective, hooks are lifecycle extensions, and Team Execution is the reviewer/validator execution protocol; none of those roles is interchangeable.

---

## Requirements

The shipped system must make model choice, dispatch, evidence, and imported behavior observable and reproducible.

### Source and capability truth

R1. Freeze Codex at `788902513e48ea95fd0504ac3c850c8c02e5d920` and Claude at `38742ece89880a6b140be237edad6d3f13c97b54` for this cycle, classify all 156 focused delta files, and require an explicit plan amendment before extending the window.

R2. Record one Codex capability model that separates lifecycle state, continuation, dispatch vehicle, role identity, model/effort policy, and hooks; unsupported source Workflow behavior must remain unavailable.

### Models and managed agents

R3. Replace the GPT-5.4/5.5 default palette with a catalog-aware Sol/Terra/Luna policy while preserving Claude tier names only as lineage keys.

R4. Support scalar efforts `low`, `medium`, `high`, `xhigh`, and `max`; classify Ultra as root-only orchestration with automatic delegation and prohibit it in the 25 leaf agent profiles.

R5. Make every managed team-execution profile carry active `model` and `model_reasoning_effort`, resolve a compatible fallback when the preferred model is unavailable, and record preferred, effective, fallback, and catalog provenance.

R6. Preserve safe agent synchronization: never overwrite unmanaged profiles, remove only stale managed files when asked, remain idempotent when called twice, and verify installed readback after apply.

### Team Execution and Saga

R7. Claim `team-execution-delegated` only when a receipt binds the selected named role, hook-reported active model, exact installed-config digest (including expected effort), child task identity, and result vehicle; generic subagents remain `generic-subagent` evidence and do not satisfy reviewer or validator gates.

R8. Keep `team-execution-serial` as the truthful fallback when named dispatch, hook trust, capacity, or safety is unavailable, and disclose its reviewer-independence limitation.

R9. Encode reviewer and validator gate precedence in executable policy: P0, security, and required-validator hard failures remain blocking; the three-remediation-cycle cap escalates to the operator and never silently passes them.

R10. Make Saga dispatch two-phase: an intent may reserve a leaf identity, but the outcome stays ready/pending until a real launch acknowledgement is recorded; a synthetic `leaf-*` identifier alone is not dispatched work.

R11. Treat Goal as explicit long-running continuation, hooks as event extensions, and subagents as a dispatch vehicle. Remove unverified caller booleans that advertise goal, subagent, fork, or Workflow as executable backends without a real adapter and receipt.

R12. Add Codex-native plugin hooks only with current Codex event fixtures, trust-state handling, idempotent local receipts, minimal captured data, and no surprise Git, GitHub, deployment, or credential mutation.

### Upstream import and release

R13. Port every intended host-neutral correctness, engine, trust, economics, attestation, and reconciliation behavior with adapted Codex tests; preserve Codex-only skills and classify non-portable Claude commands, agents, hook manifests, Workflow emitters, and paths explicitly.

R14. Keep external-engine outputs and advisory seats outside completion-gate authority, bind them to dispatch identity and evidence digests, and fail loudly on substitution, empty delivery, missing attestation, or malformed findings.

R15. Stage versions, manifests, marketplace inventory, validation inventory, docs, and generated facts/assets as one reviewable release unit, but do not publish or cut over installed plugin/agent/hook state until behavior passes targeted, full-suite, isolated-install, hook, and fresh-session runtime proof.

R16. Maintain a repeatable Claude-to-Codex port procedure that records the frozen source range, current upstream drift, per-file treatment, Codex capability snapshot, agent activation, version policy, validation gates, and durable review/cutover artifacts.

R17. Make cutover reversible: preserve the prior marketplace/cache, managed-agent, and hook-trust state; mutate only plugin-managed surfaces; and require verified rollback steps before changing the real Codex profile.

---

## Origin Traceability

This plan supersedes only the unfinished work in the 2026-06-27 plan. Requirements already landed remain explicit compatibility obligations rather than disappearing from the chain.

| Origin requirement | Disposition in this plan | Coverage |
|---|---|---|
| Origin R1: port the recent Claude delta | Continued against the newer frozen `9470edc..38742ece` window. | R1, R13; U1, U6, U7 |
| Origin R2: add OutcomeOrchestrator | Already landed; repair false dispatch semantics without removing the surface. | R10; U5 |
| Origin R3: preserve Codex host truth | Continued and tightened around current model, agent, Goal, hook, and spawn capabilities. | R2, R11, R13; U1, U5, U6 |
| Origin R4: Team Execution cleanup | Already landed; preserve serial fallback and add attested named execution. | R7-R9; U4 |
| Origin R5: classify non-portable changes | Continued through the commit-bounded treatment artifact. | R1, R13; U1 |
| Origin R6: update metadata only for exposed behavior | Continued with lineage-aware versions and release-last sequencing. | R15; U8 |
| Origin R7: narrow and broad validation | Continued and made reproducible through `uv run` plus isolated/live evidence. | R15; U8 |
| Origin R8: full Team Execution roster | Already landed as 25 source TOMLs; this plan activates, installs, and attests them. | R5, R6; U3, U4 |
| Origin R9: repeatable porting procedure | Still open; U1 updates the canonical provenance recipe and U8 proves it through review/cutover records. | R16; U1, U8 |

---

## Key Technical Decisions

The following decisions are fixed for this plan and constrain implementation.

KTD1. Commit-bound this cycle at Codex `7889025` and Claude `38742ec`: the existing 0.64 import remains historical evidence, while the 156-file `9470edc..38742ece` window is the only upstream source for U1-U8. A later Claude commit requires a new classification and plan amendment.

KTD2. Keep lineage tiers but map them to role semantics, not old model names: the preferred/fallback policy is fixed as follows.

| Lineage key | Intended role | Preferred | Ordered fallback |
|---|---|---|---|
| `fable` | exceptional bounded root judgment | `gpt-5.6-sol` / `max` | `gpt-5.6-terra` / `max`, then `gpt-5.5` at its strongest supported scalar effort |
| `opus` | architecture, security, adversarial review | `gpt-5.6-sol` / `high` | `gpt-5.6-terra` / `high`, then `gpt-5.5` / `high` |
| `sonnet` | general workers and testers | `gpt-5.6-terra` / `medium` | `gpt-5.6-sol` / `medium`, then `gpt-5.5` / `medium` |
| `haiku` | scanners, monitors, bounded extraction | `gpt-5.6-luna` / `low` | `gpt-5.6-terra` / `low`, then `gpt-5.4-mini` / `low` |

The ordered fallbacks prefer the current 5.6 family before the previous generation so tool and schema behavior remain as close as possible to the preferred model while preserving the intended effort. This is a capability-continuity rule, not an unverified price claim.

KTD3. Separate Ultra from scalar effort: `low..max` remains the ordered scalar ladder used for leaf agents, ceilings, riders, and cost policy. Ultra is allowed only on an explicitly selected root/coordinator when the work has independent fan-out, and it never satisfies named Team Execution identity by itself.

KTD4. Require active source pins plus catalog-aware installed rendering: repo-managed agent TOMLs declare the preferred `model` and `model_reasoning_effort`. One synchronization run executes `codex debug models` with an argv-only subprocess, a 15-second timeout, and a 16 MiB output ceiling; on nonzero exit, timeout, or invalid JSON it tries `codex debug models --bundled` once, then fails loud. The parser allowlists only model slug, default reasoning level, supported reasoning levels, visibility/API support needed for selection, and catalog source; it drops instructions and every unknown field. The exact accepted payload is hashed and normalized once, and plan/apply/readback consume that immutable snapshot without a second live read. CI uses fixture catalogs and never depends on a network or mutable user catalog.

KTD5. Make receipts the delegation boundary: plugin installation, agent-file presence, a generic spawn, and `protocol_probe --subagents present` are characterization only. Delegated Team Execution begins only after a real Codex child produces a named-role receipt joined to the hook-reported active model and the SHA-256 digest of the exact installed TOML bytes. Codex hooks do not report reasoning effort, so the digest binds the expected effort rather than pretending the hook observed it. Raw allowlisted SubagentStart/Stop events are atomic, size-bounded, prompt-free files in the host-provided plugin data directory (`0700` directory, `0600` files); normalization validates containment, session/child/role pairing, timestamps, model, digest, and result reference before writing the protected gate receipt. Successful raw pairs are deleted after normalization; incomplete pairs remain diagnostic evidence until an explicit age-bounded prune command removes them.

KTD6. Split Saga execution dimensions instead of growing one backend enum: lifecycle/state remains Saga; continuation is the current task or an explicitly requested Goal; dispatch is inline, manual, Team Execution serial, or Team Execution delegated; identity is generic or named-attested; hooks observe or persist receipts, while enforcement guards remain deferred. Goal and hooks are never leaf execution backends.

KTD7. Require launch acknowledgement before outcome commit: `outcome advance` writes an `outcome.dispatch.v2` intent with a deterministic `dispatch_intent_id`, but it must not record `dispatched` until a skill-mediated Codex launch returns an acknowledgement with `ack_kind=launched`, `dispatch_ack_ref`, and a real `leaf_saga_id`. Manual handoff uses `ack_kind=handed-off`, has no leaf Saga id, displays as `handed-off`, and never masquerades as a launch. Both acknowledgement kinds settle the intent for deduplication, but only launched leaves participate in running/liveness state. Legacy dispatch commits without `ack_kind` display as `legacy-unverified`, remain settled to prevent duplicate launches, block dependent progress, and require explicit evidence-backed reconciliation to `launched` or `handed-off`.

KTD8. Port hooks by behavior, not by file: U4 owns only Team Execution `SubagentStart`/`SubagentStop` receipts; U5 owns one read-only Saga `SessionStart` context hook for startup, resume, and compact. No Saga PreToolUse, PostToolUse, Stop, or lifecycle-receipt hook ships in this cycle. Claude hook files are test oracles only, blocking `PreToolUse` enforcement is deferred because current Codex documents incomplete unified-exec interception, and the SessionStart hook may only scan contained local Saga state and return concise context; it may not fetch, fast-forward, or mutate Git.

KTD9. Import in dependency batches: fleet-core policy/proof primitives first; host-neutral Saga correctness and engine substrate second; trust/economics/attestation/reconciliation third; Team Execution advisory integration last. The Claude `codex:delegate` external-engine row, commands, agent markdown, and Workflow emitters do not become active Codex surfaces.

KTD10. Preserve the repository's established version semantics instead of inventing false parity: fleet-core and Saga take the frozen source-lineage versions `0.8.4` and `0.75.17`, with Codex adaptations documented in `PORTABILITY.md`; Team Execution remains on its already divergent Codex adapter line and advances from `2.3.0` to `2.4.0`. Metadata changes land only in U8 and never imply byte parity.

KTD11. Use Team Execution for eventual implementation, with a mandatory bootstrap mode: U1-U4 run as serial Team Execution because named dispatch is the feature being built. U5-U8 may switch to delegated Team Execution only after U4's fresh-session gate produces a valid receipt; otherwise they remain serial without downgrade theater.

KTD12. Cut over transactionally and retain rollback proof: U8 records the prior installed marketplace/cache version, managed-agent digests, and hook trust/digests before mutation; proves source and isolated-profile behavior first; applies the real-profile changes last; and records sanitized readback. On failure, disable only the new hooks, reinstall the recorded prior plugin versions, restore only plugin-managed agent files, and verify the previous readback. Unmanaged agents, unrelated hooks, credentials, and user-owned repo changes are never rollback targets.

---

## Implementation Units

Eight dependency-ordered units keep foundational policy, runtime proof, upstream import, and release truth independently reviewable.

### U1. Freeze Source and Capability Truth

Create one reproducible baseline and replace the overloaded backend story with a Codex capability contract.

**Goal:** Freeze the current Codex/Claude refs, classify all 156 focused delta files, capture the live 0.144.1 model/feature/agent state, and define the separated execution dimensions consumed by later units.

**Requirements:** R1, R2, R11, R13, R16.

**Dependencies:** None.

**Files:** `docs/portability/codex-saga-07517-drift-classification.md`, `docs/portability/matrix.md`, `docs/portability/provenance.md`, `docs/validation/codex-runtime-capability-snapshot.json`, `plugins/saga/PORTABILITY.md`, `plugins/team-execution/PORTABILITY.md`, `plugins/fleet-core/PORTABILITY.md`, `plugins/saga/references/operator-choice.md`, `plugins/saga/references/saga-spec.md`, `plugins/saga/tests/test_codex_operator_choice.py`, `tests/test_codex_runtime_capability_snapshot.py`, `tests/test_outcome_backends.py`, `tests/test_operator_choice_drift.py`.

**Approach:** Record the frozen Codex and Claude hashes, verify the target commit still exists, and separately record the observed Claude local/main/origin refs and whether the frozen target remains reachable. Upstream advancement is drift evidence, not permission to extend the window. Record the 12/63/10/71 file split and update the canonical provenance recipe with source-range proof, classification, runtime snapshot, agent activation, version, validation, review, and cutover steps. Commit only an allowlisted capability snapshot: schema version, capture time, CLI version, Codex/Claude refs, normalized model slugs/default/supported efforts, selected feature states, custom-agent schema fields, spawn-tool fields, managed-agent count, catalog source/hash, and official source URLs. Do not persist model instructions, prompts, absolute user paths, environment values, tokens, or unrelated config. Replace the single capability menu with explicit lifecycle, continuation, dispatch, identity, and hook dimensions; retain only currently executable choices and classify the rest as unavailable, adapted later, or rejected.

**Patterns to follow:** Preserve the commit-bounded evidence style in `docs/portability/codex-saga-064-drift-classification.md` and the Codex-native boundary in `docs/engineering-journal/DECISIONS.md`.

**Test scenarios:** Happy path: given the frozen refs and inventories, the classification accounts for exactly 156 unique files and every row has one treatment; the sanitized capability snapshot validates against its closed schema. Edge cases: duplicate renames, files spanning plugin and root-test paths, an empty delta, and a newer `origin/main` are counted or reported without changing the frozen range. Error paths: a missing/unreachable frozen commit, unclassified file, unsupported backend advertised as active, forbidden snapshot field, or missing catalog evidence fails the gate. Integration: existing Saga operator-choice and outcome-backend tests consume the new capability vocabulary without exposing Workflow, Goal, hooks, or generic subagents as proven leaf executors.

**Verification:** A reviewer can reproduce the counts and frozen refs despite current upstream drift, validate the sanitized snapshot and port recipe, map every later unit to classified source rows, and find no caller-asserted backend truth in the active capability table.

### U2. Modernize Fleet-Core Model, Effort, Cost, and Proof Policy

Make fleet-core the current Codex source of truth before any consumer changes.

**Goal:** Port the portable fleet-core `0.5.0 -> 0.8.4` primitives while replacing the old model map with Sol/Terra/Luna, scalar `max`, Ultra separation, catalog fallback, cost weights, retry clamp, and shared proof types.

**Requirements:** R3, R4, R5, R13, R14.

**Dependencies:** U1.

**Files:** `plugins/fleet-core/scripts/fleet_commons/models.json`, `plugins/fleet-core/scripts/fleet_commons/tier_palette.py`, `plugins/fleet-core/scripts/fleet_commons/tier_resolver.py`, `plugins/fleet-core/scripts/fleet_commons/effort_rider.py`, `plugins/fleet-core/scripts/fleet_commons/codex_model_catalog.py`, `plugins/fleet-core/scripts/fleet_commons/cost_weights.json`, `plugins/fleet-core/scripts/fleet_commons/cost_weights.py`, `plugins/fleet-core/scripts/fleet_commons/retry_backoff.py`, `plugins/fleet-core/scripts/fleet_commons/bridge_receipt.py`, `plugins/fleet-core/scripts/fleet_commons/delegation_audit.py`, `plugins/fleet-core/scripts/fleet_commons/delegation_state.py`, `plugins/fleet-core/scripts/fleet_commons/output_attestation.py`, `plugins/fleet-core/references/tier-palette.md`, `plugins/fleet-core/tests/test_codex_model_catalog.py`, `plugins/fleet-core/tests/test_tier_resolver.py`, `plugins/fleet-core/tests/test_render_tier_table.py`, `plugins/fleet-core/tests/test_retry_backoff.py`, `plugins/fleet-core/tests/test_bridge_receipt.py`.

**Approach:** Extend the canonical registry schema with preferred/fallback models, supported scalar-effort handling, and a distinct orchestration-profile field. Implement KTD4's bounded argv-only catalog reader and allowlisted projection; hash the exact accepted input and pass one immutable normalized snapshot through resolution, rendering, apply, and readback. Clamp only downward to supported scalar effort, retain refreshed-versus-bundled provenance, and keep the five consumer shims unchanged unless module-resolution behavior changes.

**Patterns to follow:** Preserve the single-registry derivation in `plugins/fleet-core/scripts/fleet_commons/tier_palette.py` and deterministic injected clock/RNG patterns in `retry_backoff.py`.

**Test scenarios:** Happy path: a full 5.6 fixture resolves the four lineage rows to the KTD2 mapping and emits riders through `max`. Edge cases: Luna without Ultra, a preferred model absent with a compatible fallback present, a fallback whose effort ceiling is lower, duplicate catalog slugs, refreshed failure followed by bundled success, unknown extra fields, and repeated consumers of one snapshot resolve deterministically. Error paths: timeout, oversized output, both catalog commands failing, empty/malformed JSON, forbidden instruction leakage, input-hash change during one run, no compatible fallback, unknown effort, Ultra requested for a leaf, or upward effort clamping fails loud. Integration: tier resolution, rendered policy tables, cost weights, retry behavior, receipts, and output attestation share one registry without second literals or a second catalog read.

**Verification:** Fixture-based tests prove exact mappings and fallback provenance; no leaf tier returns Ultra; existing consumers import the upgraded fleet-core modules through the canonical shim.

### U3. Activate and Safely Install the 25 Managed Agents

Turn lineage comments into executable custom-agent configuration with catalog-aware installed output.

**Goal:** Require active preferred `model` and `model_reasoning_effort` in all 25 source TOMLs, render an effective installed profile for the live catalog, and prove safe discovery/readback without overwriting user-owned agents.

**Requirements:** R5, R6, R8.

**Dependencies:** U2.

**Files:** `plugins/team-execution/agents/*.toml`, `plugins/team-execution/scripts/sync_codex_agents.py`, `scripts/validate_codex_plugins.py`, `plugins/team-execution/tests/test_agent_tier_sync.py`, `plugins/team-execution/tests/test_sync_codex_agents.py`, `tests/test_team_execution_agents.py`, `tests/test_validate_codex_plugins.py`.

**Approach:** Keep source lineage comments but make direct `model` mandatory and replace the raw-copy sync with a deterministic renderer. Dry-run and apply consume U2's one immutable catalog snapshot and record preferred/effective/fallback model, expected effort, catalog source/hash, SHA-256 of exact rendered TOML bytes, and action. Apply validates all staged managed files first, journals prior managed bytes, uses contained atomic replacements, restores only touched managed files on failure, and performs installed TOML byte/readback verification before reporting success.

**Patterns to follow:** Retain the managed marker and unmanaged-conflict behavior in `plugins/team-execution/scripts/sync_codex_agents.py:12-76`; continue deriving validation expectations from fleet-core rather than maintaining a second map.

**Test scenarios:** Happy path: a full catalog renders and installs 10 Sol/high reviewers, 8 Terra/medium testers, and 7 Luna/low scanners with exact byte/readback. Edge cases: partial catalog fallback, max-depth-one config, stale managed files, an already-current target, and a second apply are deterministic and idempotent. Error paths: unmanaged name collision, malformed source TOML, catalog hash drift, no compatible model, failed atomic replacement, mismatched readback, or direct source model diverging from policy restores the prior managed set and leaves unmanaged files byte-identical. Integration: a temporary Codex home receives exactly 25 valid profiles while unrelated profiles remain byte-identical.

**Verification:** Source validation requires active pins, dry-run explains every choice, apply/readback reports 25 managed profiles, and rerunning produces only unchanged actions.

### U4. Add Attested Team Execution Dispatch and Machine Gates

Prove which role actually ran and make consensus/validator outcomes executable policy rather than prose.

**Goal:** Add named-role dispatch receipts, truthful serial fallback, minimal SubagentStart/SubagentStop hook evidence, and a machine-checkable reviewer/validator gate with explicit hard-failure precedence; enable delegated mode only when a fresh isolated runtime proves it.

**Requirements:** R7, R8, R9, R12, R14.

**Dependencies:** U3.

**Files:** `plugins/team-execution/hooks/hooks.json`, `plugins/team-execution/hooks/agent_receipt.py`, `plugins/team-execution/scripts/dispatch_receipt.py`, `plugins/team-execution/scripts/gate_evaluator.py`, `plugins/team-execution/scripts/protocol_probe.py`, `scripts/prove_team_execution_runtime.py`, `docs/validation/team-execution-runtime-proof.json`, `plugins/team-execution/skills/team-execution/SKILL.md`, `plugins/team-execution/skills/team-execution/references/consensus-protocol.md`, `plugins/team-execution/skills/team-execution/references/validator-evidence-state.md`, `plugins/team-execution/skills/team-execution/references/worker-manifest.md`, `plugins/team-execution/tests/test_dispatch_receipt.py`, `plugins/team-execution/tests/test_gate_evaluator.py`, `plugins/team-execution/tests/test_protocol_probe.py`, `tests/test_prove_team_execution_runtime.py`, `tests/test_team_execution_orchestration_regressions.py`.

**Approach:** Treat `protocol_probe` as a unit fixture, not live proof. The trusted plugin hook accepts at most 64 KiB and records only event name, parent/session/turn/child identifiers, agent type, active model, permission mode, installed-config digest, and timestamps; it never records prompts, transcripts, tool arguments, results, environment, or credentials. The handler validates `agent_type` as a managed slug and computes the digest itself from the contained marker-owned installed TOML; it never accepts a payload-supplied digest or arbitrary path. It writes atomic raw files beneath a contained per-session/per-child directory in the host-provided plugin data root with KTD5 permissions. `dispatch_receipt.py` joins one start/stop pair to the planned role, expected effort from the digested TOML, and an allowlisted result reference, writes a normalized protected receipt, then deletes the completed raw pair. A separate explicit `--prune-stale --older-than <duration>` path handles incomplete evidence. `prove_team_execution_runtime.py` is dry-run by default; `--live` creates an isolated Codex home, installs/trusts the reviewed source plugin and exact hook digest there, syncs all 25 agents, opens an authenticated fresh task that requests `architecture-reviewer`, and writes a sanitized result. If the host cannot select that named profile, the proof records `serial-only` and delegated mode remains disabled; this does not become a false release blocker.

**Patterns to follow:** Preserve vehicle vocabulary and the serial safety boundary in `plugins/team-execution/skills/team-execution/SKILL.md:20-47`; preserve contained receipt validation patterns from `plugins/saga/scripts/team_execution_readiness.py`.

**Test scenarios:** Happy path: fixtures for a named custom reviewer with a matching model/config digest and child result become `team-execution-delegated`; a valid serial role becomes `team-execution-serial` with the limitation recorded. Edge cases: duplicate or out-of-order events, incomplete pairs, explicit stale pruning, backpressure, max-thread exhaustion, stale config digest, and called-twice normalization/gate evaluation remain idempotent. Error paths: oversized or malformed event, prompt-bearing field, symlink/path escape, unsafe permissions, generic agent type, missing hook trust, mismatched model, missing stop/result, forged child id, P0/security finding, or required validator failure cannot satisfy delegated consensus; the cycle cap returns escalation, not pass. Integration: the isolated live harness records either a valid named reviewer receipt or an explicit `serial-only` negative proof; a generic-only task proves automatic serial fallback.

**Verification:** No test or live report can claim delegated Team Execution without a complete receipt chain; the sanitized runtime proof names its capability outcome and hook/config hashes; gate output is a deterministic pass/block/escalate result with contained evidence paths. A `serial-only` result leaves U5-U8 executable in serial mode but cannot satisfy delegated evidence.

### U5. Repair Saga's Codex-Native Continuation and Dispatch Boundary

Make Saga record what Codex actually launched and use current hooks/goals for their real roles.

**Goal:** Refactor Saga's overloaded backend model, require typed launch or handoff acknowledgement before outcome state advances, migrate ambiguous legacy dispatch records safely, integrate Team Execution receipts, expose Goal only as explicit continuation, and add one nonblocking Codex-native SessionStart hook.

**Requirements:** R2, R7, R10, R11, R12.

**Dependencies:** U4.

**Files:** `plugins/saga/scripts/saga.py`, `plugins/saga/scripts/lifecycle_state.py`, `plugins/saga/scripts/outcome_spec.py`, `plugins/saga/scripts/outcome_store.py`, `plugins/saga/scripts/outcome.py`, `plugins/saga/scripts/outcome_dispatcher.py`, `plugins/saga/scripts/team_execution_readiness.py`, `plugins/saga/hooks/hooks.json`, `plugins/saga/hooks/session_context.py`, `plugins/saga/skills/outcome/SKILL.md`, `plugins/saga/skills/loop/SKILL.md`, `plugins/saga/skills/resume/SKILL.md`, `plugins/saga/skills/work/SKILL.md`, `plugins/saga/references/operator-choice.md`, `plugins/saga/references/outcome-spec.md`, `plugins/saga/tests/test_lifecycle_state.py`, `plugins/saga/tests/test_saga_state.py`, `tests/test_outcome_dispatcher.py`, `tests/test_outcome_backends.py`, `tests/test_outcome_dispatch_migration.py`, `tests/test_outcome_integration.py`, `tests/test_team_execution_readiness.py`, `tests/test_capability_degrade.py`.

**Approach:** Replace caller-supplied `--host-capable` and `--workflow-available` truth with typed dispatch intents consumed by the skill-mediated Codex runtime. Keep existing `orchestration_mode` as the compatibility dispatch choice and add three backward-compatible Saga v1 fields: `continuation_mode` (`turn` or `goal`, default `turn`), `continuation_ref` (default empty), and `identity_mode` (`generic` or `named-attested`, default `generic`). Persist a Goal reference only after an explicit operator request and successful Goal-tool result; if the tool returns no stable identifier, leave `continuation_ref` empty and do not claim binding. Generalize `_explicit_save_scalars` to detect every provided persisted non-list scalar `save` option, excluding sticky identity flags, so explicit default values replace prior values.

For outcome dispatch, write KTD7's v2 intent/ack records without changing the compatible outcome-spec v1 shape. Derive `ready`, `intent-created`, `dispatched`, `handed-off`, and `legacy-unverified` from the ledger: only `ack_kind=launched` creates `dispatched` and a `leaf_saga_id`; handoff settles without liveness or dependent progress; legacy commits settle against duplication but block progress. Add an explicit reconciliation command that requires a contained launch receipt or operator-confirmed handoff reference before appending a v2 acknowledgement; never rewrite ledger history. The one Saga hook handles SessionStart startup/resume/compact, reads contained local Saga state, and returns concise re-entry context only.

**Patterns to follow:** Keep `.codex/saga` append-only tick semantics and reuse the existing contained `orchestration_ref` validation. Follow the official plugin-hook default `hooks/hooks.json` layout and keep hook writes in `PLUGIN_DATA` or ignored local Saga state.

**Test scenarios:** Happy path: inline and serial/delegated Team Execution intents become dispatched only after matching launched acknowledgements; an operator-confirmed manual acknowledgement becomes handed-off; an explicitly requested Goal can resume the same Saga id; SessionStart adds concise re-entry context without mutation. Edge cases: repeated advance, duplicate acknowledgement, crashed launch between intent and ack, missing agent capacity, absent or identifier-less Goal result, untrusted hooks, compact/resume startup, and explicit default-valued `--destination plan-only`, `--status active`, `--phase 0`, `--round 0`, or `--progress-pct 0` replace prior values. Legacy records remain settled and visible, and evidence-backed reconciliation is append-only and idempotent. Error paths: synthetic leaf id treated as launch proof, caller-asserted capability, acknowledgement for the wrong intent/subplot, unsafe ref, unsupported Workflow/fork choice, legacy auto-upgrade, or hook mutation attempt fails loud without advancing the node. Integration: a fresh session restores Saga state, launches one real leaf through the selected vehicle, records its receipt, and does not double-dispatch on the next reconcile.

**Verification:** Outcome reports distinguish ready, intent-created, dispatched, handed-off, legacy-unverified, and complete states; no node is marked dispatched solely because a stable id was minted; old Saga ticks round-trip with defaults; Goal and hooks disappear from execution-backend menus; the shipped Saga hook inventory contains only the declared SessionStart behavior.

### U6. Import Host-Neutral Correctness and the Engine Substrate

Bring in the portable first half of the Claude window through the new Codex boundaries.

**Goal:** Port isolated outcome/board/retry correctness plus the external-engine HTTP bridge, registry, resolver, overlays, auth/preflight, conformance, and model/effort invocation using U2 and U5 contracts.

**Requirements:** R1, R3, R10, R13, R14.

**Dependencies:** U2, U5.

**Files:** `plugins/saga/scripts/board_progression.py`, `plugins/saga/scripts/discover_subissues.py`, `plugins/saga/scripts/outcome_edges.py`, `plugins/saga/scripts/outcome_github.py`, `plugins/saga/scripts/execution_spec.py`, `plugins/saga/scripts/team_emitter.py`, `plugins/saga/scripts/engine_bridge_http.py`, `plugins/saga/scripts/bridge_signatures.py`, `plugins/saga/scripts/engine_registry.py`, `plugins/saga/scripts/engine_registry_cli.py`, `plugins/saga/scripts/engine_resolver.py`, `plugins/saga/scripts/engine_dispatch.py`, `plugins/saga/scripts/engine_overlay.py`, `plugins/saga/scripts/check_engine_registry.py`, `plugins/saga/references/engine-registry.yaml`, `plugins/saga/references/model-releases.yaml`, `plugins/saga/references/dispatch-adapter-contract.md`, `plugins/saga/references/engine-dispatch.md`, `plugins/saga/tests/test_board_progression.py`, `plugins/saga/tests/test_execution_spec_tiers.py`, `plugins/saga/tests/test_engine_routing.py`, `tests/test_outcome_board_sync.py`, `tests/test_outcome_command.py`, `tests/test_outcome_from_objective.py`, `tests/test_outcome_integration.py`, `tests/test_engine_bridge_http.py`, `tests/test_engine_registry_conformance.py`, `tests/test_engine_registry_lint.py`, `tests/test_engine_registry_cli.py`.

**Approach:** Port host-neutral algorithms and schemas, adapt `.claude` paths to Codex state, and require engine variants to carry enforceable model and effort through the dispatch envelope. Replace stale `codex --effort` recipes with current `--model` plus `-c model_reasoning_effort=...`; omit the Claude `codex:delegate` row so native subagents cannot masquerade as an external engine.

**Patterns to follow:** Preserve outcome board-write certificates and idempotency from the 0.64 Codex port. Use fleet-core receipts and catalog normalization rather than re-declaring model, effort, retry, or attestation schemas inside Saga.

**Test scenarios:** Happy path: cross-repo objective ingestion, crash-replay board comment dedupe, registry resolution, auth preflight, route explain, and an HTTP bridge dry run preserve typed evidence. Edge cases: duplicate issue numbers across repos, empty registry, overlay pin/deprecate replay, partial credentials, model fallback, timeout/retry clamp, and called-twice board sync remain deterministic. Error paths: unsupported source command/hook/Workflow surface, `codex:delegate`, stale `--effort` invocation, missing model/effort envelope, invalid registry row, unavailable explicit engine, or failed certificate halts before side effects. Integration: one temporary bridge execution records the resolved engine/model/effort and receipt without granting completion authority.

**Verification:** All classified U6 rows have adapted tests, current Codex invocations enforce their advertised model/effort, and no native-subagent or Claude-host primitive appears as an external-engine success path.

### U7. Import Trust, Economics, Attestation, and Advisory Reconciliation

Layer the coupled 0.75 trust and advisory behavior only after dispatch and engine proof are real.

**Goal:** Port provider recommendation/onboarding, offload economics, output trust and attestation, liveness, typed reconciliation, and the team-execution advisory seat while keeping every external result outside hard gate authority.

**Requirements:** R7, R9, R13, R14.

**Dependencies:** U4, U6.

**Files:** `plugins/saga/scripts/chaperone_economics.py`, `plugins/saga/scripts/engine_offer.py`, `plugins/saga/scripts/engine_recommend.py`, `plugins/saga/scripts/engine_onboarding.py`, `plugins/saga/scripts/engine_promotion.py`, `plugins/saga/scripts/provenance_manifest.py`, `plugins/saga/scripts/reconcile.py`, `plugins/saga/references/engine-output-trust-boundary.md`, `plugins/saga/references/surface_intent_defaults.yaml`, `plugins/team-execution/skills/team-execution/scripts/consensus_advisory.py`, `plugins/team-execution/skills/team-execution/references/consensus-protocol.md`, `plugins/team-execution/skills/team-execution/references/external-engine-workers.md`, `plugins/team-execution/skills/team-execution/references/worker-manifest.md`, `tests/test_chaperone_economics.py`, `tests/test_engine_offer.py`, `tests/test_engine_recommend.py`, `tests/test_engine_onboarding.py`, `tests/test_engine_promotion.py`, `tests/test_bridge_lie_detector.py`, `tests/test_engine_dispatch_attestation.py`, `tests/test_reconcile.py`, `tests/test_team_execution_consensus.py`, `tests/test_team_execution_consensus_advisory.py`.

**Approach:** Preserve the source's dispatch identity, evidence digest, bounded structural projection, panel cap, and ordered reconciliation semantics. Preserve the persisted v1 names `verified_by_claude`, enum member `FELL_BACK_TO_CLAUDE`, and value `fell-back-to-claude` exactly; translate them only in operator-facing labels/docs, and do not migrate the stored schema in this cycle. Exclude advisory findings from reviewer/validator score arithmetic even when attested. `engine_recommend.py`, `engine_offer.py`, and `engine_promotion.py` remain read-only proposal/report surfaces. `engine_onboarding.py` defaults to dry-run and may write the registry only with explicit `--apply`, an expected pre-write SHA-256, a contained target, and post-write readback; it never stores credentials or secret-bearing probe output.

**Patterns to follow:** Reuse the current Codex verified-versus-adjudicated manifest boundary and hash-chained run ledger. Keep recommendations advisory, spending checks before dispatch, and provider promotion read-only until explicit operator action.

**Test scenarios:** Happy path: a test-gated offload passes pre-dispatch economics, returns valid attestation and liveness proof, produces bounded findings, and reconciles as advisory evidence; an explicitly applied onboarding proposal matches its expected digest and readback. Edge cases: free provider, budget boundary, seven-seat panel cap, duplicate findings, rejected offload retention, called-twice reconcile/apply, dry-run byte identity, and exact legacy v1 names remain stable. Error paths: malicious finding text, substituted engine, zero external tokens, hash mismatch, missing liveness join, empty delivery, over-budget route, probationary provider in an advisory role, missing finding coverage, advisory vote entering hard-gate math, stale pre-write digest, symlink/path escape, secret-bearing output, or mutation from recommend/offer/promotion fails loud. Integration: a Claude-labeled hard-gate record and external advisory report converge or conflict visibly while only the named Codex reviewer/validator set determines completion.

**Verification:** Adversarial tests prove external text is inert, economics stop spending before dispatch, attestation catches disguised fallback, reconciliation is idempotent, and advisory consensus cannot pass or block a hard gate by itself.

### U8. Version, Validate, Install, and Prove Fresh-Session Cutover

Publish metadata only after source, installed state, hooks, agents, and runtime behavior agree.

**Goal:** Release fleet-core `0.8.4`, Saga `0.75.17`, and team-execution `2.4.0`; update all inventory/docs/generated surfaces; refresh the local marketplace install; and prove model policy, truthful named-or-serial execution, hooks, Saga re-entry, imported behavior, and rollback in fresh Codex tasks.

**Requirements:** R1, R5, R6, R7, R8, R12, R13, R15, R16, R17.

**Dependencies:** U3, U4, U5, U6, U7.

**Files:** `plugins/fleet-core/.codex-plugin/plugin.json`, `plugins/saga/.codex-plugin/plugin.json`, `plugins/team-execution/.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `README.md`, `plugins/fleet-core/README.md`, `plugins/saga/README.md`, `plugins/team-execution/README.md`, `plugins/fleet-core/CHANGELOG.md`, `plugins/saga/CHANGELOG.md`, `plugins/team-execution/CHANGELOG.md`, `docs/baseline/codex-visible-plugins.md`, `docs/portability/codex-plugin-modernization-cutover-and-rollback.md`, `docs/validation/codex-plugin-modernization-cutover.json`, `docs/validation/saga-family-target-inventory.json`, `docs/saga/generated/lifecycle-facts.json`, `scripts/validate_codex_plugins.py`, `scripts/build_saga_docs_facts.py`, `scripts/render_saga_docs_assets.py`, `tests/test_validate_codex_plugins.py`, `tests/test_saga_docs_package.py`, `tests/test_team_execution_agents.py`.

**Approach:** Update behavior-bearing versions and manifests together and run all Python checks through the locked project environment (`PYTHONPATH=. uv run ...`; Pillow is already declared in `pyproject.toml`/`uv.lock`, and the repository root is required because pytest uses importlib mode while tests import `scripts.*`). Before mutation, write a sanitized pre-state containing source HEAD, installed marketplace/cache versions, exact managed-agent digests, hook-definition/trust digests, and catalog hash; exclude absolute user paths, prompts, config values, and credentials. Use the plugin creator's cachebuster/reinstall path rather than editing installed cache files. Prove installation, hook trust, and agent sync in an isolated Codex profile first. Apply to the real profile only after source/full-suite and isolated gates pass, then open fresh tasks so stale in-process state cannot satisfy proof. If any real-profile gate fails, execute KTD12's documented rollback and verify prior readback before stopping.

**Patterns to follow:** Follow existing generated-doc `--check` gates and marketplace/source/cache separation. Preserve unrelated user changes, including `.serena/project.yml`.

**Test scenarios:** Happy path: validators, generated docs, focused plugin tests, and full `PYTHONPATH=. uv run pytest` pass; isolated install exposes the three target versions and 25 agents; fresh tasks prove the three role-class installed policies, serial fallback, hook receipts, and Saga re-entry. When U4 produced a named receipt, fresh live tasks additionally prove Sol/high reviewer, Terra/medium tester, and Luna/low scanner execution before delegated mode is enabled. Edge cases: second install, existing unrelated agents/hooks, untrusted hooks, stale cache version, unavailable preferred model, and a newer Claude `origin/main` are recorded without changing the frozen proof. Error paths: manifest/version drift, missing locked dependency, missing repository import root, cache edited as source, fresh task loading old plugin state, generic subagent reported as named, hook receipt missing, unsanitized proof field, full-suite collection failure, failed real-profile apply, or failed rollback readback blocks cutover. Integration: one end-to-end plan/work/review/outcome slice produces model, dispatch, gate, Saga, and external-advisory receipts without automatic PR, merge, deploy, or provider mutation.

**Verification:** Source and installed readback match target versions; all declared checks pass; the sanitized cutover record contains pre-state, isolated proof, applied state, capability outcome, and rollback verification status; three role-class policy/readback proofs plus one serial fallback are durable; live named-role receipts are required only to enable delegated mode; the frozen 156-file classification has no unresolved active row.

---

## Team Structure

The selected implementation backend is Team Execution, but delegation remains disabled until the plan's own activation gate is proved.

### Runtime

- Destination: `plan-only` for this planning turn.
- Recommended and selected future backend: `team-execution`.
- U1-U4 mode: serial Team Execution; generic exploration may assist but cannot satisfy reviewer or validator gates.
- U5-U8 mode: delegated only after U4 records one valid named-role fresh-session receipt; otherwise serial.
- State root: `.codex/team-execution/` when ignored and contained, otherwise the user-local fallback.
- Main-thread final verification: required.

### Workers

| Workstream | Units | Execution rule |
|---|---|---|
| Capability and fleet-core bootstrap | U1-U2 | Serialize shared policy files in the main thread. |
| Agent activation and receipt engine | U3-U4 | Serialize until the named-dispatch gate passes. |
| Saga runtime boundary | U5 | One writer; reviewers inspect in parallel only after U4. |
| Upstream import batches | U6-U7 | Independent read/test work may delegate; shared files remain single-writer. |
| Release and cutover | U8 | Main thread owns installed-state mutation and final readback. |

### Reviewers

| Role | Required | Selection reason |
|---|---:|---|
| `devils-advocate-reviewer` | yes | Base reviewer; challenges false capability and simulated-proof claims. |
| `security-reviewer` | yes | Base reviewer; covers hooks, external engines, receipts, and trust boundaries. |
| `architecture-reviewer` | yes | Base reviewer; covers cross-plugin ownership and dependency order. |

### Validators

| Role | Group | Required | Selection reason | Blocking rule |
|---|---|---:|---|---|
| `api-compat-scanner` | scanner | yes | Verifies current Codex model, agent, hook, and CLI schemas. | Schema mismatch blocks the affected unit. |
| `security-scanner` | scanner | yes | Exercises untrusted engine output and unsafe hook/receipt paths. | P0/security hard failure blocks completion. |
| `scenario-tester` | tester | yes | Runs model fallback, serial/delegated, outcome ack, and fresh-session scenarios. | Missing required scenario evidence blocks cutover. |

### Gates

- Reviewer consensus threshold: overall `>= 9.0/10` and no dimension `< 7.0`.
- Reviewer non-consensus blocks validators unless the operator explicitly overrides.
- P0, security, and required-validator hard failures remain blocking after the remediation-cycle cap.
- Maximum three remediation loops; exhaustion escalates to the operator and never converts a blocker to pass.
- Delegated evidence is accepted only with U4's named-role receipt; otherwise the same roles run serially and disclose the independence limit.

This Team Structure is the future execution receipt. The generic Explore agents used to deepen this plan do not constitute a Team Execution run.

---

## System-Wide Impact

The work changes source policy, generated agent configuration, local plugin hooks, Saga state transitions, and installed marketplace behavior.

- fleet-core becomes the single model/effort/cost/proof authority for Saga and team-execution; mission-control and UniFi continue consuming the shared library through their existing shims.
- team-execution gains transactional writes only to marker-owned agent files and prompt-free hook receipts in the host-provided plugin data root; normalized evidence is protected and completed raw pairs are removed. It does not gain mutation authority over source, GitHub, or deployments.
- Saga state remains in `.codex/saga` and committed outcome artifacts. Goal and hook state are references/receipts, not replacement sources of truth; legacy dispatch commits remain visible until explicitly reconciled.
- External providers remain behind registry auth, trust, economics, and explicit mutation boundaries. No secret values or provider credentials enter repository artifacts.
- Fresh-session testing is mandatory because plugin, agent, hook, and model configuration can be cached by a running Codex process. Real-profile cutover records sanitized pre-state and rolls back only managed surfaces on failure.

---

## Risks and Dependencies

The largest risks are false runtime proof, source drift, and trust-boundary regression.

| Risk or dependency | Impact | Mitigation |
|---|---|---|
| Codex catalog or schema changes after planning | Pinned models or fields become invalid. | Refresh catalog at U1/U8, use fixture-driven normalization, and require compatible fallback/readback. |
| Ultra causes recursive or generic delegation | Unbounded cost and untrusted gate evidence. | Root-only policy, `max_depth=1` proof, no Ultra in leaf TOMLs, named receipts required for Team Execution. |
| Custom agents are installed but not selected | Team Execution is reported but not run. | U4 hook/model/config receipt and serial fallback; simulated probe never counts. |
| Plugin hooks are untrusted or compose poorly | Missing evidence or surprising behavior. | Minimal nonblocking hooks first, explicit trust readback, fixture tests, idempotent receipts, no Git mutation. |
| Saga records dispatch before launch | Outcome DAG advances around nonexistent work. | Two-phase intent/ack state and crash-replay tests. |
| Existing outcome commits contain synthetic leaf ids | Active historical DAGs could be silently reinterpreted as launched. | Classify as settled `legacy-unverified`; block dependency progress until append-only evidence-backed reconciliation. |
| Claude `main` advances during implementation | Mixed baselines and unreviewed scope. | Commit-bound window; amendment required to extend. |
| External output reaches executable or gate sinks | Prompt injection, unsafe actions, or false consensus. | Opaque-data contract, attestation, evidence digests, report-only advisory seat, adversarial tests. |
| Full pytest is run outside the locked dev environment or without the repo import root | False missing-dependency/import failure or skipped proof. | Use `PYTHONPATH=. uv run pytest`; Pillow and test dependencies are already declared and locked; require green collection before release. |
| Real-profile install partially succeeds | Plugin, agents, and hook trust disagree. | Capture pre-state, prove isolated profile first, mutate real profile last, roll back only managed surfaces, and require prior-state readback. |

---

## Alternatives Considered

The rejected alternatives either preserve stale assumptions or produce unverifiable execution claims.

| Alternative | Decision |
|---|---|
| Import Claude `0.75.17` first, then update models | Rejected: the imported engine and tier layers would immediately require rework and could encode unsupported Codex behavior. |
| Change only lineage comments and inherit the machine model | Rejected: the machine default is mutable and current Codex supports active per-agent model/effort configuration. |
| Treat Ultra as the rung after `max` | Rejected: documented Ultra behavior includes automatic delegation and changes execution semantics. |
| Count installed TOMLs or `protocol_probe --subagents present` as delegated proof | Rejected: neither proves a named child ran with the intended model or returned gate evidence. |
| Keep Goal, hooks, fork, subagent, and Workflow in one backend enum | Rejected: they represent different lifecycle dimensions and several lack executable adapters. |
| Copy Claude hook files and commands directly | Rejected: payloads, tool names, paths, trust, and mutation assumptions differ. |
| Invent Codex-ahead versions for every plugin | Rejected: it conflicts with the established lineage-version policy and obscures the frozen source mapping. Saga/fleet-core preserve lineage labels; Team Execution advances its existing Codex-native line. |

---

## Success Metrics

Completion is evidence-based rather than version-based.

- Exactly 156 focused source files have an explicit imported, adapted, deferred, or rejected treatment.
- All 25 managed agent sources contain active model/effort policy, and installed readback accounts for all 25 without touching unrelated profiles.
- Installed readback proves Sol/high reviewer, Terra/medium tester, and Luna/low scanner policies plus one serial fallback. Delegated mode additionally requires matching live receipts for any role it claims; otherwise the durable capability outcome is `serial-only` and no generic child is counted as Team Execution.
- Outcome integration proves zero state transitions to `dispatched` without a matching launch acknowledgement and zero duplicate launches on replay.
- Hook fixtures and live smoke prove trusted, idempotent, non-mutating SessionStart and subagent receipt behavior alongside existing hooks.
- External-engine adversarial tests catch substitution, empty delivery, missing attestation, malicious findings, and advisory-gate contamination.
- Plugin validation, generated docs checks, focused suites, full locked-environment pytest, isolated install, fresh-session cutover, and rollback-readback proof all pass before metadata is released.

---

## Scope Boundaries

The plan modernizes the Codex adapter and imports only behavior that fits the verified Codex boundaries.

### Non-goals

- No full mirror of `infiquetra-claude-plugins`.
- No active Claude `.claude-plugin`, `commands`, markdown agents, raw hook manifests, Workflow emitters, `SendMessage`, or `.claude/saga` paths.
- No activation of `agy`, redis-channel remote gate transport, or the Claude `codex:delegate` external-engine row.
- No recursive Ultra leaf delegation and no claim that generic subagents satisfy Team Execution consensus.
- No automatic Git fetch/fast-forward, commit, push, PR, merge, deploy, provider registration, or credential mutation from hooks or this plan-only turn.
- No editing installed plugin cache as maintained source.
- No changes to the sibling `team-freya` repository.

### Deferred to Follow-Up Work

- Blocking `PreToolUse` policy hooks, until Codex unified-exec interception is complete enough to support an honest enforcement claim.
- Recursive agent depth above one, until cost and fan-out controls have a separate explicit design.
- Automatic Goal creation or recurring wakeups; Goal remains opt-in for an explicitly requested long-running objective.
- Any Claude commit after `38742ece`, which requires a new commit-bounded classification.

---

## Sources and Research

The plan combines live repository/runtime evidence with current official Codex documentation.

- `plugins/fleet-core/scripts/fleet_commons/models.json:2-14`: current canonical GPT-5.4/5.5 dual palette and scalar effort ladder.
- `plugins/team-execution/scripts/sync_codex_agents.py:38-76`: current safe but raw-copy synchronization behavior.
- `scripts/validate_codex_plugins.py:242-263` and `scripts/validate_codex_plugins.py:479-524`: palette-derived hints and direct-model rejection.
- `plugins/team-execution/skills/team-execution/SKILL.md:20-47`: delegated/serial and vehicle semantics.
- `plugins/saga/scripts/outcome.py:69-104`: record-only default dispatcher.
- `plugins/saga/scripts/outcome_dispatcher.py:42-55`, `plugins/saga/scripts/outcome_dispatcher.py:151-162`, and `plugins/saga/scripts/outcome_dispatcher.py:232-247`: active/host-dependent backend model, synthetic dispatch result, and caller-asserted capabilities.
- `plugins/saga/scripts/saga.py:553-597` and `plugins/saga/scripts/saga.py:1372-1379`: scalar carry-forward and the missing explicit-destination marker that caused the plan-only readback regression.
- `plugins/saga/scripts/outcome_spec.py:44-78`, `plugins/saga/scripts/outcome.py:437-451`, and `plugins/saga/scripts/outcome.py:784-890`: current v1 state vocabulary and intent/commit records that treat a synthetic dispatcher result as settled dispatch.
- `docs/portability/codex-saga-064-drift-classification.md`: previous commit-bounded import classification and Codex adaptation rules.
- `docs/portability/provenance.md` and `docs/engineering-journal/DECISIONS.md`: preserved-lineage version policy, port recipe, curated adapter, active backend, receipt, and fleet-core policy history.
- `pyproject.toml` and `uv.lock`: the declared locked dev environment already includes Pillow, pytest, PyYAML, requests, and urllib3.
- [Official Codex model guidance](https://learn.chatgpt.com/docs/models): Sol for complex/open-ended work, Terra for everyday work, Luna for clear/repeatable work; `max` deepens one task while Ultra adds subagent delegation.
- [Official Codex subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents): custom agent TOMLs support `model` and `model_reasoning_effort`; current local Codex delegates on direct or applicable skill instructions; default max depth is one.
- [Official Codex plugin guidance](https://learn.chatgpt.com/docs/build-plugins): plugins can bundle hooks under `hooks/hooks.json`, but hook trust is explicit.
- [Official Codex hook reference](https://learn.chatgpt.com/docs/hooks): plugin hooks expose active `model`, SubagentStart/Stop `agent_type`, and current event limitations.

---

## Recommended Next Step

Await explicit execution approval. If approved, enter `saga:work` at U1 in serial Team Execution mode; do not enable delegated mode unless U4 later produces the required named-role receipt.
