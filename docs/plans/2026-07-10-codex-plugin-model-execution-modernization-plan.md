---
title: Codex Plugin Model, Execution, and Upstream Modernization Plan
type: feat
status: active
date: 2026-07-10
origin: docs/plans/2026-06-27-port-recent-claude-plugin-updates.md
deepened: 2026-07-10
amended: 2026-07-10
reviewed: 2026-07-10
---

# Codex Plugin Model, Execution, and Upstream Modernization Plan

## Summary

Modernize the Codex model, agent, workflow, and porting contracts before importing the next Claude plugin window. The dependency order is: freeze capability truth and codify an enforced port contract, preserve the live Codex changes that landed after the original planning base, land the Sol/Terra/Luna execution classes in fleet-core, establish `verified-workflows` as the Codex-native successor to the upstream `team-execution` lineage, preserve 25 logical roles through a smaller attested profile set, repair Saga's execution boundary, selectively import the Claude `0.64.0 -> 0.75.17` family delta without losing the current Codex `0.65.0` behavior, and cut over only after fresh-session proof.

Execution of U1-U9 does not depend on either the legacy Team Execution adapter or Verified Workflows. Saga records the effective backend as `inline`, while the root Codex thread directly coordinates bounded native subagents for exploration, implementation, review, and validation; Verified Workflows remains a product under construction and a system under test.

This plan supersedes the uncompleted portions of `docs/plans/2026-06-27-port-recent-claude-plugin-updates.md` without rewriting that plan's history. It continues the existing `task-port-recent-claude-plugin-updates` Saga.

---

## Problem Frame

The original Codex planning base `788902513e48ea95fd0504ac3c850c8c02e5d920` shipped Saga `0.64.0`, the Codex adapter `team-execution` `2.3.0`, and fleet-core `0.5.0`. At round-three review, live `HEAD` and `origin/main` are `fbd400183c2de70115cbaadc4c301b03d759527d`, Saga is `0.65.0`, and 33 repository paths have changed since the planning base, including 13 under the port's active source/inventory surfaces; U1 must inventory all 33, freeze the approved execution base, and preserve that Codex-side drift rather than resetting to `7889025`. The next frozen Claude target is `38742ece89880a6b140be237edad6d3f13c97b54`, at Saga `0.75.17`, upstream `team-execution` `2.14.3`, and fleet-core `0.8.4`.

The old source name remains lineage truth, while the target Codex package becomes `verified-workflows` `1.0.0`.

The focused source window `9470edc..38742ece`, restricted to the exact pathspecs `plugins/fleet-core`, `plugins/saga`, `plugins/team-execution`, and `tests`, contains 156 files: 12 fleet-core files, 63 Saga files, 10 team-execution files, and 71 tests. The unrestricted repository window contains 333 files and is explicitly out of scope. Importing the focused window first would build new routing, trust, economics, and reconciliation behavior on stale Codex assumptions.

Nine current gaps determine the order:

- `plugins/fleet-core/scripts/fleet_commons/models.json:4-13` still maps work to GPT-5.5, GPT-5.4, and GPT-5.4-mini and defines only `low` through `xhigh`.
- The 25 `team-execution` TOMLs conflate logical role instructions with only three repeated model/effort classes. `scripts/validate_codex_plugins.py:505-524` rejects active `model`, none is currently installed, and the source has no role-to-execution-class contract for risk-adjusted planning.
- The active package, Saga mode, receipt vehicles, state roots, plan anchor, agent marker, and evidence keys all say `team-execution`, even though the agreed Codex design is a root-owned workflow rather than a peer team. Real ignored Saga ticks already persist the old vocabulary, so the rename requires read-old/write-new compatibility rather than global replacement.
- `docs/portability/provenance.md:14-25` contains a prose-only proof-port recipe that explicitly does not cover models, custom agents, hooks, apps, MCP, or native orchestration. No versioned machine contract currently blocks a future port with missing source rows, stale capability assumptions, or active Claude-only primitives.
- `plugins/saga/scripts/outcome.py:69-104` says its default dispatcher runs nothing, while `plugins/saga/scripts/outcome_dispatcher.py:151-162` returns a `leaf-*` identifier that can be recorded as dispatched without a launched task.
- Codex 0.144.1 reports models, multi-agent, hooks, goals, and plugins as live surfaces, but Saga still mixes Goal, hooks, subagents, fork, and Workflow into one backend vocabulary. The current task's spawn contract remains generic, so named-role dispatch is not yet proved.
- `plugins/saga/scripts/saga.py:553-597` carries default-valued scalars from the prior tick, but `_explicit_save_scalars` at `plugins/saga/scripts/saga.py:1372-1379` recognizes only orchestration mode. A literal `--destination plan-only` therefore retained this Saga's prior `pr` destination until an append-only correction was written.
- The reviewed plan selected serial Team Execution to bootstrap U1-U4 even though U3-U5 modify the Team Execution and Saga integration contracts. That makes the target component its own execution and acceptance protocol, so a defect in the target could block or falsely validate its repair.
- `origin/main` advanced after the planning base and now carries Saga `0.65.0` hierarchy behavior. A one-window Claude-only manifest would let an implementation overwrite or misclassify those Codex-native changes, so U1 must bind both the upstream source inventory and the Codex plan-base-to-execution-base preservation inventory.

The machine's global default is currently `gpt-5.6-sol` at `max`, with `agents.max_threads=6` and `agents.max_depth=1`. The current Codex task host advertises four total collaboration slots, so runtime capacity is lower than the config ceiling and must be discovered rather than inferred. Plugin policy must select role-specific models explicitly rather than inherit a mutable machine default, and leaf profiles must not use Ultra to create unbounded or unaudited delegation.

---

## Recommended Order

The order establishes a trustworthy Codex execution substrate before any coupled upstream import.

| Order | Unit | Why it comes here |
|---:|---|---|
| 1 | U1. Freeze capability and source truth | Every later decision depends on one reproducible Codex and Claude boundary. |
| 2 | U2. Modernize fleet-core policy | Model, effort, fallback, cost, and proof vocabulary are shared dependencies. |
| 3 | U9. Establish Verified Workflows identity | New hooks, profiles, and receipts must never be created under an identity that will immediately be retired. |
| 4 | U3. Render managed execution profiles | The 25 logical roles need explicit defaults and allowed risk classes before a smaller profile set can preserve their behavior. |
| 5 | U4. Implement and attest the workflow | Installed profiles are not execution proof; the root-owned DAG, receipts, and machine gates must exist first. |
| 6 | U5. Repair Saga's Codex boundary | Saga can consume canonical workflow receipts only after legacy aliases and new write vocabulary are defined. |
| 7 | U6. Import correctness and engine substrate | Portable Claude behavior now has Codex-native model, workflow, and port-contract seams to target. |
| 8 | U7. Import trust, economics, and advisory reconciliation | These layers depend on proven dispatch, receipts, and engine substrate. |
| 9 | U8. Release and cut over | Metadata and installed state follow behavior, contract validation, and fresh-session proof. |

---

## High-Level Technical Design

The modernization separates concepts the current backend vocabulary overloads.

```text
 Live Codex catalog       Codex preservation drift       Frozen Claude window
 Sol / Terra / Luna       7889025..<execution-base>       9470edc..38742ece
 low..max + Ultra                    |                    four exact pathspecs
          |                          |                           |
          +--------------------> U1 capability + port contract <-+
                              |
                   U2 fleet-core policy
                   model | effort | fallback
                   cost  | proof  | receipts
                              |
              U9 verified-workflows identity
              legacy read | canonical new writes
                              |
                   25 logical role specs
                              +
             defaults + allowed risk classes
                              +
              U3 five execution profiles
                              |
                U4 root-owned workflow DAG
                roles | gates | receipts
                              |
                           U5 Saga
                              |
                   U6 engine substrate
                              | lifecycle/state
                              | continuation: turn | explicit Goal
                              | dispatch: inline | verified-workflow | manual
                              | identity: logical role + execution class
                              | hooks: observe | persist | guard
                              v
                 U7 trust/economics/reconciliation
                              |
                   U8 release + fresh-session proof

 Plan execution control plane (independent of Verified Workflows)

             root Codex coordinator
             Saga backend: inline
             preferred: Sol / max
                      |
        +-------------+-------------+
        |             |             |
   explorer(s)    one writer    reviewer / validator
 Terra / medium   Sol / high    Sol / high or Terra / medium
 requested RO      bounded         requested RO
        +-------------+-------------+
                      |
              root integrates,
              verifies, and commits
```

Ultra is intentionally outside the scalar effort ladder. Codex represents it through the model control, but its documented behavior adds automatic subagent delegation; the policy therefore treats Ultra as a root orchestration profile, not as the next leaf-agent effort after `max`. This plan selects root `max`, not Ultra, because its fan-out is explicit and bounded by the unit DAG.

Saga remains the durable lifecycle and outcome-state owner. Goal is an optional continuation substrate for an explicitly requested long-running objective, hooks are lifecycle extensions, and Verified Workflows defines workflow steps, logical roles, gates, validators, and receipts. The root Codex thread owns spawn, follow-up, wait, integration, and adjudication; native subagent activity is not a Verified Workflows claim without the attested workflow receipt.

---

## Requirements

The shipped system must make model choice, dispatch, evidence, and imported behavior observable and reproducible.

### Source and capability truth

R1. Preserve Codex `788902513e48ea95fd0504ac3c850c8c02e5d920` as the historical planning base, freeze the approved live execution base at U1, freeze Claude at `38742ece89880a6b140be237edad6d3f13c97b54`, classify all 156 source files under the four exact focused pathspecs, classify every plan-base-to-execution-base Codex drift path as preserve, reconcile, or superseded-by-plan, and require an explicit plan amendment before extending either window.

R2. Record one Codex capability model that separates lifecycle state, continuation, workflow mode, per-step dispatch vehicle, logical role, execution class, model/effort policy, and hooks; unsupported source Workflow behavior must remain unavailable.

### Models and managed agents

R3. Replace the GPT-5.4/5.5 default palette with a catalog-aware Sol/Terra/Luna policy while preserving Claude tier names only as lineage keys.

R4. Support scalar efforts `low`, `medium`, `high`, `xhigh`, and `max`; classify Ultra as root-only orchestration with automatic delegation and prohibit it in every leaf execution profile.

R5. Preserve all 25 logical role identifiers and classify each as `agent-lens` or `deterministic-validator`. Every agent-lens records whether independent context is required or preferred, owns one default plus allowed risk-adjustable execution classes, and binds one explicit class whose managed profile carries active `model` and `model_reasoning_effort` with preferred, effective, fallback, and catalog provenance; every deterministic validator instead binds a declared command/evidence contract and never receives an LLM execution class.

R6. Preserve safe agent synchronization across the package rename: recognize the legacy Team Execution marker as managed during an explicit upgrade, write only the Verified Workflows marker, never overwrite unmanaged profiles, remove only stale managed files when asked, remain idempotent when called twice, and verify installed readback after apply.

### Verified Workflows and Saga

R7. Claim `verified-workflow-subagent` only when a receipt binds the selected logical role, execution class, selected agent type, hook-reported active model, exact installed-profile digest, role/lens digest, child task identity, and result vehicle. The installed-profile digest is accepted proof of expected effort because current hooks attest model but not effort; generic subagents remain `generic-subagent` evidence and do not satisfy workflow gates.

R8. Keep `verified-workflow-inline` as the truthful root-owned fallback when profile selection, hook trust, capacity, or safety is unavailable, record `deterministic-tool` for non-agent validators, and disclose the independence limitation of inline logical-role review. Inline may satisfy an agent-lens whose registry marks independence preferred, but it may not satisfy a role whose registry marks independent context required.

R9. Encode workflow gate precedence in executable policy: required logical-role evidence, no unresolved P0/P1 or security blocker, required validator success, and root verification are authoritative. Numeric reviewer scores are supporting evidence only, and the three-remediation-cycle cap escalates to the operator without silently passing a blocker.

R10. Make Saga dispatch two-phase: an intent may reserve a leaf identity, but the outcome stays ready/pending until a real launch acknowledgement is recorded; a synthetic `leaf-*` identifier alone is not dispatched work.

R11. Treat Goal as explicit long-running continuation, hooks as event extensions, and subagents as a dispatch vehicle. Remove unverified caller booleans that advertise goal, subagent, fork, or Workflow as executable backends without a real adapter and receipt.

R12. Add Codex-native plugin hooks only under the canonical Verified Workflows or Saga identities, with current Codex event fixtures, separate old/new trust-state handling, idempotent local receipts, minimal captured data, and no surprise Git, GitHub, deployment, or credential mutation.

### Upstream import and release

R13. Port every intended host-neutral correctness, engine, trust, economics, attestation, and reconciliation behavior with adapted Codex tests; preserve Codex-only skills and classify non-portable Claude commands, agents, hook manifests, Workflow emitters, and paths explicitly.

R14. Keep external-engine outputs and advisory seats outside completion-gate authority, bind them to dispatch identity and evidence digests, and fail loudly on substitution, empty delivery, missing attestation, or malformed findings.

R15. Stage versions, manifests, marketplace inventory, validation inventory, docs, and generated facts/assets as one reviewable release unit, but do not replace installed `team-execution` with `verified-workflows` until behavior passes targeted, full-suite, port-contract, isolated-install, hook, duplicate-plugin, legacy-read/new-write, and fresh-session runtime proof.

R16. Ship `docs/portability/claude-to-codex-plugin-port-runbook.md` as the canonical human procedure for future ports, covering source authority, capability truth, Codex surface selection, Saga-family ownership boundaries, role/class design, workflow ownership, state and trust boundaries, versioning, validation, isolated installation, fresh-session proof, rollback, and explicit stop rules.

R17. Make cutover reversible across package identities: preserve the prior marketplace/cache, managed-agent marker/bytes, hook-trust state, and old/new state roots; mutate only plugin-managed surfaces; and require verified rollback to `team-execution` `2.3.0` before changing the real Codex profile.

R18. Ship `verified-workflows` `1.0.0` as the only canonical Codex package and `verified-workflows:run` as its primary skill; retain `team-execution` only as upstream lineage, historical evidence, and a centralized legacy read alias.

R19. Preserve existing Saga ticks, outcome ledgers, plan anchors, configuration, state roots, receipt vehicles, producer kinds, evidence keys, managed markers, and hook evidence through read-old/write-new normalization. Never rewrite append-only history, silently merge conflicting old/new roots, or emit legacy vocabulary from new work.

R20. Bootstrap a versioned machine port manifest in U1 before any source-behavior unit starts. It must bind the historical Codex planning base, approved execution base, plan-base drift inventory, frozen Claude refs, the four exact rename-aware source pathspecs and inventory digest, the current Codex capability-snapshot digest, the runbook version and SHA-256, one treatment per source path, preserved Codex-only invariants, planned targets/tests, verified evidence, version policy, review, isolated-install, fresh-session, and rollback artifacts.

Classification-stage completeness blocks U2-U9 source work; unit-stage completeness blocks each unit's integration; cutover-stage completeness blocks release.

---

## Origin Traceability

This plan supersedes only the unfinished work in the 2026-06-27 plan. Requirements already landed remain explicit compatibility obligations rather than disappearing from the chain.

| Origin requirement | Disposition in this plan | Coverage |
|---|---|---|
| Origin R1: port the recent Claude delta | Continued against the newer frozen `9470edc..38742ece` window. | R1, R13; U1, U6, U7 |
| Origin R2: add OutcomeOrchestrator | Already landed; repair false dispatch semantics without removing the surface. | R10; U5 |
| Origin R3: preserve Codex host truth | Continued and tightened around current model, agent, Goal, hook, and spawn capabilities. | R2, R11, R13; U1, U5, U6 |
| Origin R4: Team Execution cleanup | Adapt the behavior into Verified Workflows, preserving truthful inline fallback and adding attested logical-role execution. | R7-R9, R18-R19; U4, U9 |
| Origin R5: classify non-portable changes | Continued through the commit-bounded treatment artifact. | R1, R13; U1 |
| Origin R6: update metadata only for exposed behavior | Continued with lineage-aware versions and release-last sequencing. | R15; U8 |
| Origin R7: narrow and broad validation | Continued and made reproducible through `uv run` plus isolated/live evidence. | R15; U8 |
| Origin R8: full Team Execution roster | Preserve all 25 logical role IDs while separating them from the smaller risk-adjustable execution-profile set. | R5-R8; U3, U4 |
| Origin R9: repeatable porting procedure | Close with a canonical runbook, staged machine manifest, deterministic validator, generated classification, per-unit evidence, and cutover proof. | R16, R20; U1-U9 |

---

## Key Technical Decisions

The following decisions are fixed for this plan and constrain implementation.

KTD1. Use two explicit, non-substitutable baselines. Codex `7889025` is the historical planning base, while U1 records the approved live execution-base commit and a complete `7889025..<execution-base>` drift inventory that must be preserved or deliberately reconciled; implementation never resets to the planning base.

Claude `38742ec` is the frozen upstream target, and only the 156 files from `9470edc..38742ece` under `plugins/fleet-core`, `plugins/saga`, `plugins/team-execution`, and `tests` are source-port inputs. A later Claude commit or unclassified Codex drift path requires a new manifest/classification and, when scope changes, a plan amendment.

KTD2. Keep lineage tiers only as source lineage and select one risk-adjustable execution class per planned agent-lens; deterministic validators select no class. Fleet-core owns the five leaf classes below, while Verified Workflows owns each agent-lens's default and allowed transitions.

| Execution class | Default use | Intended profile boundary | Preferred | Ordered fallback |
|---|---|---|---|---|
| `review-max` | Explicit escalation for unusually ambiguous or high-risk review | Read-only review; no external mutation | `gpt-5.6-sol` / `max` | `gpt-5.6-terra` / `max`, then `gpt-5.5` at its strongest supported scalar effort |
| `review-high` | Default architecture, security, adversarial, API, privacy, and quality review | Read-only review; no external mutation | `gpt-5.6-sol` / `high` | `gpt-5.6-terra` / `high`, then `gpt-5.5` / `high` |
| `test-medium` | General workers, testers, and interpretation of ambiguous validator output | Workspace writes only when the workflow step declares them | `gpt-5.6-terra` / `medium` | `gpt-5.6-sol` / `medium`, then `gpt-5.5` / `medium` |
| `scan-low` | Bounded extraction and scanner-result reduction | Local read-only scans; no network or external mutation by default | `gpt-5.6-luna` / `low` | `gpt-5.6-terra` / `low`, then `gpt-5.4-mini` / `low` |
| `monitor-low` | Network-aware CI, deploy, and runtime observation | Allowlisted external reads and waiting; no external mutation | `gpt-5.6-luna` / `low` | `gpt-5.6-terra` / `low`, then `gpt-5.4-mini` / `low` |

Reviewer roles default to `review-high` and may escalate only to `review-max`; tester roles default to `test-medium` and may escalate to `review-high`; scanners default to `scan-low` and monitors to `monitor-low`, and either may escalate to `test-medium` when interpretation rather than deterministic execution is required. Deterministic validators use no model. `scan-low` and `monitor-low` intentionally remain separate despite sharing a model/effort pair because their allowed tool and external-read boundaries differ.

These boundaries remain requested configuration until U4 attests the selected profile and effective permission mode. The ordered fallbacks prefer the current 5.6 family before the previous generation so tool and schema behavior remain close to the selected class while preserving effort; this is a capability-continuity rule, not a price claim.

KTD3. Separate Ultra from scalar effort: `low..max` remains the ordered scalar ladder used for leaf profiles, ceilings, riders, and cost policy. Ultra is allowed only on an explicitly selected root/coordinator when the work has independent fan-out, and it never satisfies Verified Workflows logical-role identity by itself.

The U1-U9 execution coordinator uses explicit `max` so Codex does not add undeclared fan-out beyond the plan's bounded subagent waves.

KTD4. Require active source pins plus catalog-aware installed rendering: a planned agent-lens `{logical_role, execution_class}` resolves through one role registry and the exact selected class renders a managed TOML with preferred `model` and `model_reasoning_effort`; a deterministic validator bypasses rendering and resolves its command contract instead. One synchronization run executes `codex debug models` with an argv-only subprocess, a 15-second timeout, and a 16 MiB output ceiling; on nonzero exit, timeout, or invalid JSON it tries `codex debug models --bundled` once, then fails loud.

The parser allowlists only model slug, default reasoning level, supported reasoning levels, visibility/API support needed for selection, and catalog source; it drops instructions and every unknown field. The exact accepted payload is hashed and normalized once, and plan/apply/readback consume that immutable snapshot without a second live read. Catalog fallback may change the effective model only within the selected class.

CI uses fixture catalogs and never depends on a network or mutable user catalog.

KTD5. Make receipts the workflow boundary: plugin installation, profile-file presence, a generic spawn, and `protocol_probe --subagents present` are characterization only. `verified-workflow-subagent` begins only after a real Codex child produces a receipt joined to the planned logical role, selected execution class and agent type, hook-reported active model, SHA-256 digest of the exact installed profile, role/lens digest, child/task identity, and result reference.

The installed-profile digest is sufficient proof of expected effort; the hook does not observe effort and the receipt must not say it did. Raw allowlisted SubagentStart/Stop events are atomic, size-bounded, prompt-free files in the host-provided plugin data directory (`0700` directory, `0600` files); normalization validates containment, session/child/role pairing, timestamps, model, digests, and result reference before writing the protected gate receipt. Successful raw pairs are deleted after normalization; incomplete pairs remain diagnostic evidence until an explicit age-bounded prune command removes them.

KTD6. Split Saga execution dimensions instead of growing one backend enum: lifecycle/state remains Saga; continuation is the current task or an explicitly requested Goal; canonical workflow mode is `inline`, `manual`, or `verified-workflow`; each workflow step records `subagent`, `inline`, or `deterministic-tool`; identity is generic or logical-role-attested; hooks observe or persist receipts, while enforcement guards remain deferred. Readers accept legacy `team-execution`, but serializers emit only `verified-workflow`.

Goal and hooks are never leaf execution backends. Native serial or parallel subagents remain an execution strategy owned by the root thread.

KTD7. Require launch acknowledgement before outcome commit: `outcome advance` writes an `outcome.dispatch.v2` intent with a deterministic `dispatch_intent_id`, but it must not record `dispatched` until a skill-mediated Codex launch returns an acknowledgement with `ack_kind=launched`, `dispatch_ack_ref`, and a real `leaf_saga_id`. Manual handoff uses `ack_kind=handed-off`, has no leaf Saga id, displays as `handed-off`, and never masquerades as a launch.

Both acknowledgement kinds settle the intent for deduplication, but only launched leaves participate in running/liveness state. Legacy dispatch commits without `ack_kind` display as `legacy-unverified`, remain settled to prevent duplicate launches, block dependent progress, and require explicit evidence-backed reconciliation to `launched` or `handed-off`.

KTD8. Port hooks by behavior, not by file: U4 owns only Verified Workflows `SubagentStart`/`SubagentStop` receipts; U5 owns one read-only Saga `SessionStart` context hook for startup, resume, and compact. Old Team Execution hook trust does not transfer to the new plugin identity.

No Saga PreToolUse, PostToolUse, Stop, or lifecycle-receipt hook ships in this cycle. Claude hook files are test oracles only, blocking `PreToolUse` enforcement is deferred because current Codex documents incomplete unified-exec interception, and the SessionStart hook may only scan contained local Saga state and return concise context; it may not fetch, fast-forward, or mutate Git.

KTD9. Import in dependency batches: fleet-core policy/proof primitives first; host-neutral Saga correctness and engine substrate second; trust/economics/attestation/reconciliation third; upstream `team-execution` advisory behavior adapted into Verified Workflows last. The Claude `codex:delegate` external-engine row, commands, agent markdown, and Workflow emitters do not become active Codex surfaces.

KTD10. Preserve source lineage without assigning it to a different package identity: fleet-core and Saga take frozen source-lineage versions `0.8.4` and `0.75.17`, with current Codex `0.65.0` behavior and later approved execution-base drift preserved in `PORTABILITY.md`; `team-execution` `2.3.0` becomes retired Codex lineage, upstream `team-execution` `2.14.3` remains source metadata, and the canonical target is `verified-workflows` `1.0.0`. U9 may create the unpublished target source manifest needed for validation, but U8 alone updates active marketplace/release inventory, performs installation, and declares the versions released; neither step implies byte parity.

KTD11. Superseded by KTD13: the original serial legacy Team Execution bootstrap is rejected because that adapter and its Saga integration are being replaced. The historical choice remains visible so the amended review can verify that no execution or acceptance gate still depends on it.

KTD12. Cut over transactionally and retain rollback proof: U8 writes an uncommitted, contained local rollback bundle with `0700` directory and `0600` files holding the exact prior installed `team-execution` package/cache references, managed-agent bytes and legacy markers, old/new managed state, pending managed hook evidence, and hook trust material required for restoration. The committed cutover artifact stores only sanitized relative inventories, hashes, versions, decisions, and readback; it never contains absolute paths, raw config/trust values, prompts, credentials, or secret-bearing state.

U8 proves both a clean isolated install and a seeded old-to-new migration/rollback before touching the real profile, then installs and trusts `verified-workflows`, upgrades only marker-owned profiles, removes the old installed package, and records sanitized fresh-session readback. The final active state may never contain both packages. On failure, disable only new hooks, reinstall `team-execution` `2.3.0`, restore exact managed bytes/trust from the validated local bundle, and verify the previous readback.

Unmanaged agents, unrelated hooks, credentials, and user-owned repo changes are never rollback targets.

KTD13. Execute U1-U9 through Codex-native subagent orchestration owned by the root thread: Saga records `orchestration_mode=inline`, the root keeps lifecycle state, integration, Git, and final gate authority, and direct Codex children receive bounded U-ID tasks. Read-heavy exploration and independent validation may run in parallel; shared-workspace writes are single-writer unless isolated worktrees exist.

Verified Workflows roles and receipts may be exercised only as U3/U4/U8 product evidence, U7 may exercise advisory logic as product evidence, and none of those results determine whether their own implementation is accepted.

KTD14. Treat generic-child role, model, effort, and read-only labels as requested scope rather than enforced isolation until the active runtime proves otherwise. Run every source unit with the parent in `workspace-write` when the host supports it, record the effective permission mode, and reserve U8's real-profile mutation for a separate root-only boundary after isolated proof; if the host forces broader permissions, requested-read-only child evidence remains advisory and no child receives an external-mutation task.

Before each U-ID and each parallel read/review wave, the root records the base HEAD and pre-existing dirty-path set, intersects that set with the unit's declared files, and pauses on overlap until ownership is resolved or an isolated-worktree approach is explicitly selected. The root checks the worktree again after every child wave; an unexpected mutation invalidates that child's evidence and stops integration without rewriting or deleting pre-existing user changes. Independent reviewers and validators use `fork_turns=none` with explicit plan, diff, acceptance, and check inputs; explorers and workers receive only the minimum relevant U-ID context.

KTD15. Rename as a compatibility migration, not a text replacement: `verified-workflows`, `verified-workflows:run`, `verified-workflow`, `## Workflow Structure`, `.codex/verified-workflows/`, `verified-workflow-subagent`, `verified-workflow-inline`, and `verified_workflow_ref` are canonical new writes. One fleet-core `workflow_compat` registry owns the closed old-to-new vocabulary so Saga and Verified Workflows consume it through their normal fleet-core shims without importing one plugin from the other. U9 may hold the unchanged legacy source package beside the unpublished target source while the active marketplace still points only to Team Execution; U8 removes the legacy source in the same transaction that activates the new marketplace entry, and no release or installed profile may expose both.

Readers accept corresponding legacy Team Execution values and label them legacy; historical plans, reviews, ticks, ledgers, changelogs, and Claude catalog entries remain byte- and name-stable. Conflicting valid old/new config or state roots halt for explicit resolution, and no permanent compatibility plugin stub ships.

KTD16. Separate logical jobs from compute configuration: preserve 25 logical role IDs as versioned `agent-lens` or `deterministic-validator` specifications, but install exactly the five KTD2 leaf execution profiles. Each agent-lens registry entry records a minimum independence policy, and planning may elevate `preferred` to `required` for a higher-risk step but may never lower `required`; required independence needs an attested subagent, while preferred independence may degrade visibly to inline.

Deterministic validators bind scripts and evidence schemas without a model, effort, or profile. Any collapse of dedicated role behavior must pass role/lens equivalence fixtures before release.

KTD17. Make Verified Workflows a root-owned DAG rather than a team runtime: `## Workflow Structure` records steps, dependencies/barriers, logical role, role kind, independence, mutation boundary, evidence, and role/lens digest; agent-lens rows also record execution class and resolved expected model/effort, while deterministic rows record their command/evidence contract. The root owns spawn, follow-up, wait, consolidation, remediation routing, selective re-review, and final adjudication.

Root-mediated communication is required; peer messaging is optional and never part of the protocol contract.

KTD18. Separate port guidance from enforcement: `docs/portability/claude-to-codex-plugin-port-runbook.md` explains authority, surface mappings, judgment, and stop rules, while `docs/portability/ports/2026-07-10-saga-07517.json` is the canonical closed-schema machine input and binds the runbook SHA-256. `scripts/port_contract.py` supports explicit `classification`, `unit`, and `cutover` validation stages, verifies both frozen source and Codex drift inventories, renders `docs/portability/codex-saga-07517-drift-classification.md`, and fails `--check` on drift.

`init` never overwrites an existing classified manifest; refresh requires an explicit operation plus the expected prior digest. U1 may bootstrap only the contract/runbook/capability artifacts, and classification must pass before U2-U9 source work. Every source-consuming unit claims permitted rows and writes target/test evidence before its unit-stage gate; U8 requires every non-deferred row verified and every defer/reject rationale current.

Historical classifications are evidence, not current capability authority.

---

## Implementation Units

Nine dependency-ordered units keep foundational policy, package migration, runtime proof, upstream import, and release truth independently reviewable. Stable U-IDs retain their existing numbers; new U9 is intentionally executed before U3.

### U1. Freeze Source and Capability Truth

Create one reproducible baseline, an enforced port contract, and the capability truth every later unit must consume.

**Goal:** Freeze the historical Codex planning base, approved live execution base, Codex preservation drift, and Claude source refs; classify all 156 focused source files; capture the live 0.144.1 model/feature/agent/thread state; define the separated execution dimensions; and ship the human plus machine contracts that govern this and future Claude-to-Codex ports.

**Requirements:** R1, R2, R11, R13, R16, R20.

**Dependencies:** None.

**Files:** `AGENTS.md`, `README.md`, `docs/portability/claude-to-codex-plugin-port-runbook.md`, `docs/portability/ports/2026-07-10-saga-07517.json`, `docs/portability/codex-saga-07517-drift-classification.md`, `docs/portability/matrix.md`, `docs/portability/provenance.md`, `docs/validation/codex-runtime-capability-snapshot.json`, `scripts/port_contract.py`, `scripts/validate_codex_plugins.py`, `plugins/saga/PORTABILITY.md`, `plugins/team-execution/PORTABILITY.md`, `plugins/fleet-core/PORTABILITY.md`, `plugins/saga/references/operator-choice.md`, `plugins/saga/references/saga-spec.md`, `plugins/saga/tests/test_codex_operator_choice.py`, `tests/test_port_contract.py`, `tests/test_port_runbook.py`, `tests/test_codex_runtime_capability_snapshot.py`, `tests/test_outcome_backends.py`, `tests/test_operator_choice_drift.py`, `tests/test_validate_codex_plugins.py`.

**Approach:** Record Codex `7889025` as the historical plan base, record the approved live HEAD/origin commit as the execution base, classify every path in the plan-base drift inventory as preserve, reconcile, or superseded-by-plan, and fail if any current path is missing. Record the frozen Claude hashes, the exact source pathspec list (`plugins/fleet-core`, `plugins/saga`, `plugins/team-execution`, `tests`), verify the target commit still exists, and separately record the observed Claude local/main/origin refs and whether the frozen target remains reachable. Upstream advancement is drift evidence, not permission to extend the window.

`port_contract.py init` captures the normalized rename-aware `git diff --name-status -M` source inventory and Codex drift inventory into unclassified JSON rows. It refuses to overwrite an existing manifest; `refresh` requires the expected prior manifest digest and preserves completed classifications while exposing additions, removals, and renames for review. `validate --stage classification|unit|cutover` applies a closed schema and stage policy; `verify-source` compares a supplied source checkout without making CI depend on it; `render` and `--check` generate and verify the human classification.

A source row starts as `classified` with surface kind, `direct-port|codex-adapt|defer|reject`, rationale, planned target paths/tests, capability references, and preserved Codex-only invariants; a source-consuming unit may advance it to `implemented` and then `verified` only with existing target paths and check evidence. The manifest also binds schema version, runbook version and SHA-256, plan/review paths, source base/target/observed refs and pathspecs, Codex plan/execution refs, both inventory digests, capability-snapshot digest, affected-plugin version policy, and release evidence. U1 is the sole bootstrap exception: it may create only the runbook, contract, capability, and supporting validation artifacts; classification must pass before U2-U9 import or adaptation work starts.

The runbook explains maintained-source authority; when behavior belongs in a skill, script, hook, custom profile, MCP server, app, or protected state; and the fixed plugin-set ownership map: fleet-core owns shared policy/proof and cross-plugin compatibility vocabulary, Saga owns lifecycle and continuation, Verified Workflows owns DAG/roles/gates/receipts, mission-control owns SDLC mutations, and deploy owns tag promotion. Its source-authority table is derived from `docs/portability/matrix.md`: a vendored surface such as mission-control changes in its named canonical repository first, a Codex adapter changes here, and installed cache is never either source. It also covers Claude-to-Codex surface mapping, role/class design, state/trust/mutation boundaries, lifecycle gates, worked examples, and stop conditions; `AGENTS.md` and `README.md` make it mandatory for future imports.

`tests/test_port_runbook.py` protects required sections, normative mappings, stop rules, source-authority cases, and the AGENTS/README pointers, while the manifest digest detects unversioned runbook changes.

The mapping table is normative: recreate `.claude-plugin` manifests as `.codex-plugin` manifests rather than copying; convert commands to skills/scripts; classify markdown agents as logical roles/lenses, execution profiles, deterministic validators, references, or rejects; map TeamCreate/Workflow to a root-owned DAG and SendMessage to root-mediated follow-up; reimplement only supported hooks with trust and `PLUGIN_DATA`; keep mutable state in `PLUGIN_DATA` or protected `.codex` roots; never treat installed cache as source or an undeclared dependency; consider MCP only for typed external actions; and keep deterministic checks out of LLM personas. Worked examples cover one reviewer, scanner, workflow, hook, and unsupported feature.

Commit only an allowlisted capability snapshot: schema version, capture time, CLI version, Codex/Claude refs, normalized model slugs/default/supported efforts, selected feature states, custom-agent schema fields, spawn/steer/wait fields, effective parent permission mode, whether per-child sandbox selection is exposed, configured and host-advertised thread limits, managed-agent count, catalog source/hash, and official source URLs. Record whether the live spawn surface can enforce per-child model/effort/sandbox or only accept host selection and prompt steering. Do not persist model instructions, prompts, absolute user paths, environment values, tokens, or unrelated config.

Replace the single capability menu with explicit lifecycle, continuation, workflow, step vehicle, logical-role, execution-class, and hook dimensions; retain only currently executable choices and classify the rest as unavailable, adapted later, or rejected. `validate_codex_plugins.py` invokes the offline port-contract gate in current, target-fixture, and cutover modes.

**Patterns to follow:** Preserve the commit-bounded evidence style in `docs/portability/codex-saga-064-drift-classification.md`, the proof-port starting point in `docs/portability/provenance.md`, and the Codex-native boundary in `docs/engineering-journal/DECISIONS.md`; do not reuse execution-attestation schemas as source-port provenance.

**Test scenarios:** Happy path: given the frozen refs, four exact pathspecs, and both inventories, the JSON manifest accounts for exactly 156 unique source files plus every Codex drift path and every row has one treatment; rendered Markdown is byte-current; the sanitized capability snapshot validates against its closed schema and distinguishes config thread ceilings from current host capacity. Edge cases: duplicate renames, files spanning plugin and root-test paths, an empty delta, a newer Claude or Codex `origin/main`, an existing classified manifest, a spawn surface with no per-child model/effort fields, historical capability claims, and called-twice init/refresh/render are reported without changing the frozen range, destroying classifications, or inventing enforcement. Error paths: an unrestricted 333-file source inventory, a missing/unreachable frozen commit, execution-base drift after approval, missing/duplicate/unexpected row, unknown disposition/schema key, unversioned runbook digest change, absolute/traversal/cache/secret-shaped field, Claude command/agent/Workflow/TeamCreate/SendMessage marked `direct-port`, active hook without capability evidence and adapted tests, adapted behavior without planned target/test, a row advanced without real evidence, deferred behavior without rationale, removed preserved Codex path, changed frozen range/pathspec, generated drift, cutover without evidence, unsupported backend advertised as active, or requested child model reported as effective without observable proof fails the appropriate stage gate.

Integration: a fresh planning agent can follow `AGENTS.md`, bootstrap or load a manifest, and is blocked from source behavior work until classification validates; Saga tests consume the new capability vocabulary without exposing Workflow, Goal, or hooks as leaf executors or generic subagents as workflow proof.

**Verification:** A reviewer can reproduce the 156-file focused count, both inventory digests, source pathspecs, frozen refs, execution-base preservation set, runbook digest, generated classification, and capability digest despite current upstream drift; validate the runbook and port manifest offline; map every later unit to permitted source rows; and find no caller-asserted backend truth, unclassified active source primitive, or unclassified Codex drift path.

### U2. Modernize Fleet-Core Model, Effort, Cost, and Proof Policy

Make fleet-core the current Codex source of truth before any consumer changes.

**Goal:** Port the portable fleet-core `0.5.0 -> 0.8.4` primitives while replacing the old role-bound model map with the five Sol/Terra/Luna execution classes, scalar `max`, Ultra separation, catalog fallback, cost weights, retry clamp, and shared proof types.

**Requirements:** R3, R4, R5, R13, R14, R20.

**Dependencies:** U1.

**Files:** `plugins/fleet-core/scripts/fleet_commons/models.json`, `plugins/fleet-core/scripts/fleet_commons/tier_palette.py`, `plugins/fleet-core/scripts/fleet_commons/tier_resolver.py`, `plugins/fleet-core/scripts/fleet_commons/effort_rider.py`, `plugins/fleet-core/scripts/fleet_commons/codex_model_catalog.py`, `plugins/fleet-core/scripts/fleet_commons/cost_weights.json`, `plugins/fleet-core/scripts/fleet_commons/cost_weights.py`, `plugins/fleet-core/scripts/fleet_commons/retry_backoff.py`, `plugins/fleet-core/scripts/fleet_commons/bridge_receipt.py`, `plugins/fleet-core/scripts/fleet_commons/delegation_audit.py`, `plugins/fleet-core/scripts/fleet_commons/delegation_state.py`, `plugins/fleet-core/scripts/fleet_commons/output_attestation.py`, `plugins/fleet-core/references/tier-palette.md`, `plugins/fleet-core/tests/test_codex_model_catalog.py`, `plugins/fleet-core/tests/test_tier_resolver.py`, `plugins/fleet-core/tests/test_render_tier_table.py`, `plugins/fleet-core/tests/test_retry_backoff.py`, `plugins/fleet-core/tests/test_bridge_receipt.py`.

**Approach:** Claim only the U1 fleet-core source rows permitted for U2 and preserve every applicable Codex execution-base drift invariant. Extend the canonical registry schema with the five execution classes, preferred/fallback models, supported scalar-effort handling, and a distinct root-orchestration profile. Keep role defaults and allowed transitions out of fleet-core; U3 owns them.

Implement KTD4's bounded argv-only catalog reader and allowlisted projection; hash the exact accepted input and pass one immutable normalized snapshot through resolution, rendering, apply, and readback. Clamp only downward to supported scalar effort, retain refreshed-versus-bundled provenance, and keep the five consumer shims unchanged unless module-resolution behavior changes. Advance each claimed manifest row only after its target exists and its named evidence passes, then require `port_contract.py validate --stage unit --unit U2` before integration.

**Patterns to follow:** Preserve the single-registry derivation in `plugins/fleet-core/scripts/fleet_commons/tier_palette.py` and deterministic injected clock/RNG patterns in `retry_backoff.py`.

**Test scenarios:** Happy path: a full 5.6 fixture resolves all five KTD2 execution classes and emits riders through `max`. Edge cases: Luna without Ultra, a preferred model absent with a compatible fallback present, a fallback whose effort ceiling is lower, duplicate catalog slugs, refreshed failure followed by bundled success, unknown extra fields, and repeated consumers of one snapshot resolve deterministically. Error paths: role-specific defaults leaking into fleet-core, timeout, oversized output, both catalog commands failing, empty/malformed JSON, forbidden instruction leakage, input-hash change during one run, no compatible fallback, unknown effort, Ultra requested for a leaf, or upward effort clamping fails loud.

Integration: class resolution, rendered policy tables, cost weights, retry behavior, receipts, and output attestation share one registry without second literals or a second catalog read.

**Verification:** Fixture-based tests prove exact mappings and fallback provenance; no leaf tier returns Ultra; existing consumers import the upgraded fleet-core modules through the canonical shim; and every U2 manifest row plus Codex preservation invariant passes the unit-stage gate.

### U9. Establish Verified Workflows Identity and Compatibility Vocabulary

Create the new package before any new profiles, hooks, receipts, or state are written under the identity being retired.

**Goal:** Materialize the unpublished target Codex package `verified-workflows` `1.0.0`, expose `verified-workflows:run` and `verified-workflows:appsec-audit` in target-fixture validation, establish the canonical/legacy vocabulary and allowlist, and keep the unchanged Team Execution source and active marketplace entry only until U8 performs the source/marketplace/install cutover.

**Requirements:** R18, R19, R20.

**Dependencies:** U1, U2.

**Files:** `plugins/team-execution/**`, `plugins/verified-workflows/.codex-plugin/plugin.json`, `plugins/verified-workflows/README.md`, `plugins/verified-workflows/PORTABILITY.md`, `plugins/verified-workflows/CHANGELOG.md`, `plugins/verified-workflows/skills/run/SKILL.md`, `plugins/verified-workflows/skills/appsec-audit/SKILL.md`, `plugins/verified-workflows/scripts/fleet_commons_shim.py`, `plugins/fleet-core/scripts/fleet_commons/workflow_compat.py`, `plugins/fleet-core/tests/test_workflow_compat.py`, `.gitignore`, `pyproject.toml`, `docs/portability/matrix.md`, `docs/portability/provenance.md`, `docs/validation/saga-family-target-inventory.json`, `scripts/validate_codex_plugins.py`, `scripts/prove_codex_plugin_profile.py`, `tests/test_verified_workflows_migration.py`, `tests/test_validate_codex_plugins.py`, `tests/test_saga_docs_package.py`, `tests/test_prove_codex_plugin_profile.py`.

**Approach:** Claim the permitted upstream Team Execution identity rows and every affected Codex drift invariant. Materialize maintained target content in `plugins/verified-workflows` with explicit source provenance and a one-to-one old/new path map in the port manifest, while leaving the legacy package byte-identical and solely active in the marketplace during development; do not create a compatibility stub or install both. The fleet-core `workflow_compat.py` registry owns the closed mapping among plugin/skill names, Saga modes, anchors, state/config roots, receipt vehicles, producer kinds, evidence aliases, and managed markers.

Saga and Verified Workflows load it only through their fleet-core shims, so neither plugin imports the other's source or requires the other to be installed merely to parse compatibility vocabulary. Target fixtures and under-construction portability docs name Verified Workflows; the active marketplace, root plugin table, installed-state baseline, and generated visible inventory continue to name Team Execution until U8. The Claude source catalog, frozen 10-file count, historical plans/reviews/changelogs, and portability lineage retain `team-execution`.

U9 creates the unpublished `1.0.0` target source manifest required to validate the renamed package, but it does not replace the active marketplace entry, modify a real profile, or claim a release. Target-fixture validation sees the new package; development validation permits the second source root only while the marketplace names Team Execution alone and the target is marked unpublished; current-install validation continues to describe Team Execution until U8 performs the atomic source, marketplace, and installed-state swap. The validator carries an explicit historical/lineage/migration-fixture allowlist and rejects legacy active writes outside it.

Advance claimed manifest rows only with existing targets and passing tests, then require the U9 unit-stage gate.

**Patterns to follow:** Preserve the curated-adapter and cache-is-installed-state decisions in `docs/engineering-journal/DECISIONS.md`; use the replacement mapping style in `docs/portability/saga-family-capability-map.md` without rewriting history.

**Test scenarios:** Happy path: target-fixture validation discovers one canonical `verified-workflows` package with `run` and `appsec-audit`, maps the upstream `team-execution` row to it, and emits no legacy target vocabulary, while development/current-install validation proves the byte-identical legacy source and old install are the only active surfaces before U8. Edge cases: historical plans/reviews, Claude catalog entries, the frozen source classification, and legacy fixtures retain their old names; a called-twice materialization is idempotent; Saga can parse the shared vocabulary when Verified Workflows is absent and vice versa. Error paths: a global replacement alters lineage, both package roots/manifests are published as active, the legacy source changes after target materialization, a consumer imports another plugin directly, compatibility mappings diverge, a legacy token is emitted by a new serializer/template, an unallowlisted active old path remains, a compatibility plugin stub duplicates skills/hooks, or source metadata claims upstream byte parity fails validation.

Integration: the target-fixture plugin inventory and generated Saga-family facts resolve Verified Workflows while the active marketplace and installed profile remain untouched until U8.

**Verification:** Maintained target source has one canonical target package/skill identity, the byte-identical legacy source remains the sole marketplace-active package until U8, current-install state remains unchanged, both plugins consume one fleet-core compatibility registry without cross-plugin imports, every surviving old token is classified as upstream lineage, temporary development source, historical evidence, parser alias, or migration fixture, no new hook/profile/state artifact can be created under the retired identity, and the U9 manifest gate passes.

### U3. Create Verified Workflows Roles, Classes, and Managed Profiles

Preserve the 25 jobs while reducing duplicated compute configuration to five catalog-aware profiles.

**Goal:** Convert the 25 logical role IDs into versioned role/lens or deterministic-validator specifications, define their defaults and allowed KTD2 risk classes, render exactly five managed custom-agent profiles, and prove isolated discovery/readback without overwriting user-owned agents or cutting over the real profile before U8.

**Requirements:** R5, R6, R8, R18, R20.

**Dependencies:** U2, U9.

**Files:** `plugins/verified-workflows/roles/*.md`, `plugins/verified-workflows/config/role-registry.yaml`, `plugins/verified-workflows/agents/*.toml`, `plugins/verified-workflows/scripts/render_codex_agents.py`, `plugins/verified-workflows/scripts/sync_codex_agents.py`, `scripts/validate_codex_plugins.py`, `plugins/verified-workflows/tests/test_role_registry.py`, `plugins/verified-workflows/tests/test_role_lens_equivalence.py`, `plugins/verified-workflows/tests/test_agent_tier_sync.py`, `plugins/verified-workflows/tests/test_sync_codex_agents.py`, `tests/test_verified_workflows_agents.py`, `tests/test_validate_codex_plugins.py`.

**Approach:** Claim the permitted role/profile source rows and preserve every existing role slug and behavior as a role specification. Default every existing role to `agent-lens`; convert one to `deterministic-validator` only when an existing pinned non-LLM command plus evidence schema covers the role's complete required behavior and its equivalence fixture passes. A candidate tool, data-fetch command, or partial scan is not enough; if judgment or result interpretation remains, the role stays an agent-lens and may use deterministic commands as supporting steps.

The single role registry records minimum independence (`required|preferred`) plus default/allowed execution classes for agent-lenses, or a contained command and evidence schema for deterministic validators; it never redefines fleet-core execution-class models or efforts. Independence defaults to preferred to preserve the current truthful serial/inline fallback, and a role is marked required only when its preserved contract already demands separate-context evidence. A workflow step may elevate preferred to required based on risk but may never lower a role's minimum.

Planning selects an effective class only for agent-lenses. Generate only `review-max`, `review-high`, `test-medium`, `scan-low`, and `monitor-low` profiles, keeping common evidence, untrusted-input, mutation, and output contracts in profile developer instructions and role-specific criteria in the versioned role/lens input. A dedicated-role fixture may collapse into a shared profile only when equivalence tests preserve required findings, exclusions, output schema, and hard constraints.

Dry-run and apply consume U2's one immutable catalog snapshot and record logical role, role kind, minimum/effective independence, selected class when applicable, preferred/effective/fallback model, expected effort, catalog source/hash, exact profile and role/lens digests, and action. Advance the claimed port rows only after equivalence and isolated-install evidence pass.

Resolve the managed target as an explicit canonical `--target-dir` for tests, otherwise `$CODEX_HOME/agents` when set, falling back to `~/.codex/agents`; durable output records profile-relative paths rather than absolute user paths. Recognize the old marker only during explicit migration, write the new marker, refuse unmanaged collisions, and remove legacy-owned files only with apply plus U8's expected pre-state digest. During U3, apply/readback run only against an isolated `CODEX_HOME`; the real profile receives dry-run characterization and remains byte-identical.

Apply validates all staged files first, journals prior managed bytes, uses contained atomic replacements, restores only touched managed files on failure, and verifies exact installed bytes.

**Patterns to follow:** Retain unmanaged-conflict and atomic rollback behavior from `plugins/team-execution/scripts/sync_codex_agents.py:12-76` as legacy source evidence; derive model expectations from fleet-core and role behavior from one registry rather than maintaining literals in generated TOMLs.

**Test scenarios:** Happy path: all 25 logical roles have exactly one role kind; every agent-lens resolves to one default and at least one allowed execution class plus an independence policy; every deterministic validator resolves to one contained command/evidence contract and no class; a full catalog renders and installs exactly five valid profiles in an isolated home; representative Devil's Advocate, security, tester, scanner, monitor, and deterministic fixtures match the dedicated-role behavioral baseline; the real profile remains unchanged. Edge cases: explicit allowed risk escalation, preferred versus required independence, deterministic role with no LLM, partial catalog fallback, max-depth-one config, target override, `$CODEX_HOME`, stale legacy-managed files, already-current output, and second isolated apply are deterministic and idempotent. Error paths: missing/duplicate role, a deterministic role with model/class fields, an agent-lens without class or independence, forbidden class transition, behavior loss in equivalence fixtures, real-profile apply without opt-in and expected digest, unmanaged collision, malformed role/profile, catalog drift, no compatible model, failed atomic replacement, mismatched readback, or legacy marker removal without migration proof fails or restores prior managed bytes.

Integration: a temporary Codex home receives exactly five profiles, all 25 logical roles remain addressable through the registry, unrelated profiles remain byte-identical, and the U3 unit-stage manifest gate passes.

**Verification:** Validation proves 25 stable role IDs, closed agent-lens-to-class/independence mappings, deterministic command contracts without model fields, complete behavior/evidence coverage, five exact installed profiles, unchanged second run, no real-profile mutation in U3, and complete U3 manifest evidence.

### U4. Implement and Attest the Root-Owned Verified Workflow

Prove which logical role ran and make the workflow DAG, follow-up loop, and severity/validator gates executable policy.

**Goal:** Add `## Workflow Structure`, root-owned step dispatch and follow-up, logical-role receipts, truthful inline/deterministic fallback, minimal SubagentStart/SubagentStop hook evidence, and a machine-checkable gate with explicit hard-failure precedence; enable subagent vehicle claims only when a fresh isolated runtime proves them.

**Requirements:** R7, R8, R9, R12, R14, R20.

**Dependencies:** U3.

**Files:** `plugins/verified-workflows/hooks/hooks.json`, `plugins/verified-workflows/hooks/agent_receipt.py`, `plugins/verified-workflows/scripts/workflow_dispatch.py`, `plugins/verified-workflows/scripts/dispatch_receipt.py`, `plugins/verified-workflows/scripts/gate_evaluator.py`, `plugins/verified-workflows/scripts/protocol_probe.py`, `scripts/prove_verified_workflows_runtime.py`, `docs/validation/verified-workflows-runtime-proof.json`, `plugins/verified-workflows/skills/run/SKILL.md`, `plugins/verified-workflows/skills/run/references/workflow-protocol.md`, `plugins/verified-workflows/skills/run/references/gate-policy.md`, `plugins/verified-workflows/skills/run/references/validator-evidence-state.md`, `plugins/verified-workflows/skills/run/references/worker-manifest.md`, `plugins/verified-workflows/skills/run/references/delegation-safety.md`, `plugins/verified-workflows/tests/test_workflow_dispatch.py`, `plugins/verified-workflows/tests/test_dispatch_receipt.py`, `plugins/verified-workflows/tests/test_gate_evaluator.py`, `plugins/verified-workflows/tests/test_protocol_probe.py`, `tests/test_prove_verified_workflows_runtime.py`, `tests/test_verified_workflows_orchestration_regressions.py`.

**Approach:** Claim only permitted U4 workflow source rows and preserve applicable execution-base drift. Treat `protocol_probe` as a unit fixture, not live proof. `workflow_dispatch.py` is a deterministic DAG/state interpreter: it consumes an approved `## Workflow Structure`, validates rows, and emits typed ready-step or follow-up intents, but it never starts Codex processes or calls collaboration tools.

The `verified-workflows:run` skill is the runtime adapter; the root resolves each role file, constructs the bounded role/lens task from the versioned specification plus step context, invokes native spawn/follow-up/wait controls when available, returns the result reference to the deterministic scripts, and remains the only completion authority. Rows bind step ID, dependencies/barrier, logical role, role kind, independence, execution class and resolved expected model/effort when agent-backed, mutation boundary, required evidence, and role/lens digest. The root waits at barriers, routes follow-up or consolidated remediation to the owning thread, selectively reruns affected roles, and requires an attested child for `independence=required`; an inline fallback may satisfy only `independence=preferred`.

Root-mediated follow-up is required; peer messaging is optional and never required. Each step records `subagent`, `inline`, or `deterministic-tool` rather than one global delegated/serial team mode.

The trusted plugin hook accepts at most 64 KiB and records only event name, parent/session/turn/child identifiers, selected profile, active model, permission mode, installed-profile digest, and timestamps; it never records prompts, transcripts, tool arguments, results, environment, or credentials. The handler validates `agent_type` as one of U3's five slugs, resolves only `$CODEX_HOME/agents/<validated-slug>.toml` with the same fallback as U3, verifies containment plus the new marker, and computes the digest itself. It writes atomic raw files beneath a contained per-session/per-child directory in `PLUGIN_DATA` with KTD5 permissions.

`dispatch_receipt.py` joins one start/stop pair to the planned logical role, class, role/lens digest, expected effort from the profile digest, and allowlisted result reference. `gate_evaluator.py` requires role evidence, no unresolved blocker, required validator success, and root verification; numeric scores never override severity.

`prove_verified_workflows_runtime.py` is dry-run by default. `--live` requires a caller-supplied, already authenticated isolated `CODEX_HOME` or an explicit operator-completed login in that home; the harness never reads, copies, symlinks, prints, or persists the default profile's `auth.json`, keychain material, tokens, or provider credentials. It installs/trusts the new plugin/hook, syncs five profiles, opens a fresh task for one role/class pair, and records an attested subagent receipt, `inline-only`, or `auth-unavailable`.

The latter two outcomes cannot support a subagent claim and do not become false release blockers for the inline capability.

**Patterns to follow:** Preserve the current role criteria and hard-failure intent from `plugins/team-execution/skills/team-execution/` as legacy behavior evidence, but use severity-first review findings and contained receipt validation from `plugins/saga/scripts/team_execution_readiness.py` rather than its old names.

**Test scenarios:** Happy path: a DAG interpreter emits ready intents, the skill/root runs independent read-only roles in parallel, joins at a barrier, sends consolidated fixes to one worker, selectively reruns affected roles, executes required deterministic validators, and yields `verified-workflow-subagent` only for a matching role/class/profile/lens/model/digest/result chain; a preferred-independence inline role yields `verified-workflow-inline` with its limitation. Edge cases: duplicate or out-of-order events, incomplete pairs, stale pruning, backpressure, max-thread exhaustion, stale profile or lens digest, allowed risk escalation, deterministic tool step, root follow-up to a running or idle child, default/explicit Codex homes, unavailable isolated authentication, and called-twice intent/normalization/gate evaluation remain idempotent. Error paths: a Python helper claiming it spawned a child, automatic default-profile credential copy/symlink, secret-bearing proof, dependency cycle, unsatisfied barrier, required-independence role forced inline, peer messaging required by the plan, oversized/malformed event, prompt-bearing field, payload-supplied path/digest, escape, unsafe permissions, unknown/generic profile, missing trust, mismatched model, missing result, forged child, unresolved P0/P1/security finding, required validator failure, or numeric score used to override severity blocks or escalates; the cycle cap never passes it.

Integration: the isolated harness records a valid role/class receipt, explicit `inline-only`, or `auth-unavailable`; a generic-only task proves automatic root-owned inline fallback, and the U4 unit-stage manifest gate passes.

**Verification:** No test or live report can claim `verified-workflow-subagent` without a complete role/class/lens/profile receipt chain; no helper script claims native spawn authority; the sanitized proof names its capability outcome and hook/profile hashes; gate output is deterministic pass/block/escalate with contained evidence. An `inline-only` result leaves U5-U8 executable through root-owned Saga `inline`, but cannot satisfy subagent evidence or any role marked independence required; all U4 manifest rows pass their unit gate.

### U5. Repair Saga's Codex-Native Continuation and Dispatch Boundary

Make Saga record what Codex actually launched and use current hooks/goals for their real roles.

**Goal:** Refactor Saga's overloaded backend model, require typed launch or handoff acknowledgement before outcome state advances, migrate ambiguous dispatch records safely, integrate Verified Workflows receipts, read legacy Team Execution state without rewriting it, expose Goal only as explicit continuation, and add one nonblocking Codex-native SessionStart hook.

**Requirements:** R2, R7, R10, R11, R12, R19, R20.

**Dependencies:** U4.

**Files:** `plugins/saga/scripts/saga.py`, `plugins/saga/scripts/lifecycle_state.py`, `plugins/saga/scripts/outcome_spec.py`, `plugins/saga/scripts/outcome_store.py`, `plugins/saga/scripts/outcome.py`, `plugins/saga/scripts/outcome_dispatcher.py`, `plugins/saga/scripts/verified_workflow_readiness.py`, `plugins/saga/scripts/workflow_emitter.py`, `plugins/saga/scripts/override_rate_reader.py`, `plugins/saga/hooks/hooks.json`, `plugins/saga/hooks/session_context.py`, `plugins/saga/skills/outcome/SKILL.md`, `plugins/saga/skills/loop/SKILL.md`, `plugins/saga/skills/resume/SKILL.md`, `plugins/saga/skills/work/SKILL.md`, `plugins/saga/skills/plan/SKILL.md`, `plugins/saga/references/operator-choice.md`, `plugins/saga/references/outcome-spec.md`, `plugins/saga/references/saga-spec.md`, `plugins/saga/tests/test_lifecycle_state.py`, `plugins/saga/tests/test_saga_state.py`, `tests/test_outcome_dispatcher.py`, `tests/test_outcome_backends.py`, `tests/test_outcome_dispatch_migration.py`, `tests/test_outcome_integration.py`, `tests/test_verified_workflow_readiness.py`, `tests/test_capability_degrade.py`, `tests/test_legacy_workflow_compatibility.py`.

**Approach:** Claim only permitted U5 Saga source rows, re-read and preserve the current Saga `0.65.0` hierarchy behavior plus any later approved execution-base behavior, and require the U5 unit-stage manifest gate before integration. Replace caller-supplied `--host-capable` and `--workflow-available` truth with typed dispatch intents consumed by the skill-mediated Codex runtime. Canonical `orchestration_mode` values are `inline`, `manual`, and `verified-workflow`; Saga loads the shared fleet-core `workflow_compat` registry through its own shim, reads legacy `team-execution`, and labels it without rewriting old ticks or importing Verified Workflows.

Add three backward-compatible Saga v1 fields: `continuation_mode` (`turn` or `goal`, default `turn`), `continuation_ref` (default empty), and `identity_mode` (`generic` or `logical-role-attested`, default `generic`). New plan receipts use `## Workflow Structure` / `#workflow-structure`, new state writes use `.codex/verified-workflows/` or `~/.codex/verified-workflows/state/<repo>/`, and new evidence writes `verified_workflow_ref`; readers also accept the old anchor, roots, vehicles, producer kind, and `team_execution_ref`. Old roots are read-only.

An explicit ref wins; otherwise one valid canonical root, then one valid legacy root is selected, while conflicting valid old/new config or roots halt for operator resolution. Historical receipts require matching run/freshness identity and cannot satisfy a new run merely because they parse.

Persist `continuation_mode=goal` and its Goal reference only after an explicit operator request and a successful Goal-tool result with a stable identifier. If the tool returns no stable identifier, preserve `continuation_mode=turn`, leave `continuation_ref` empty, and do not claim binding. Generalize `_explicit_save_scalars` to detect every provided persisted non-list scalar `save` option, excluding sticky identity flags, so explicit default values replace prior values.

For outcome dispatch, write KTD7's v2 intent/ack records without changing the compatible outcome-spec v1 shape. Derive `ready`, `intent-created`, `dispatched`, `handed-off`, and `legacy-unverified` from the ledger: only `ack_kind=launched` creates `dispatched` and a `leaf_saga_id`; handoff settles without liveness or dependent progress; legacy commits settle against duplication but block progress. Add an explicit reconciliation command that requires a contained launch receipt or operator-confirmed handoff reference before appending a v2 acknowledgement; never rewrite ledger history.

The one Saga hook handles SessionStart startup/resume/compact, reads contained local Saga state, and returns concise re-entry context only.

**Patterns to follow:** Keep `.codex/saga` append-only tick semantics, centralize alias handling instead of scattering string comparisons, and reuse contained `orchestration_ref` validation. Follow the official plugin-hook default `hooks/hooks.json` layout and keep hook writes in `PLUGIN_DATA` or ignored local Saga state.

**Test scenarios:** Happy path: inline and Verified Workflows intents become dispatched only after matching launched acknowledgements; new ticks/receipts/state contain only canonical vocabulary; an operator-confirmed manual acknowledgement becomes handed-off; an explicitly requested Goal with a stable id resumes the same Saga id; SessionStart adds concise re-entry context without mutation; execution-base `0.65.0` hierarchy scenarios still pass. Edge cases: parse an old Saga tick with old mode/ref while its original checksum remains unchanged, resume an old `#team-structure` receipt labeled legacy, read old vehicle/producer/evidence keys, repeated advance, duplicate acknowledgement, crash between intent and ack, missing capacity, identifier-less Goal that leaves continuation in turn mode, untrusted hooks, compact/resume, identical dual config, and explicit default-valued scalars remain deterministic. Error paths: conflicting old/new roots or config, legacy serializer output from a newly created tick, old receipt reused for a fresh run, missing/escaping ref, synthetic leaf as launch proof, caller-asserted capability, wrong acknowledgement, unsupported Workflow/fork, legacy auto-rewrite, loss of execution-base behavior, or hook mutation fails loud without advancing.

Integration: a fresh session restores a legacy Saga, materializes new workflow evidence without rewriting history, launches one real leaf, records its receipt, and does not double-dispatch.

**Verification:** Outcome reports distinguish ready, intent-created, dispatched, handed-off, legacy-unverified, and complete; no node advances from a stable id alone; legacy fixture checksums remain unchanged while new serializers emit only canonical workflow vocabulary; conflicts halt; Goal and hooks disappear from backend menus; execution-base hierarchy behavior remains green; the Saga hook inventory contains only the declared SessionStart behavior; and the U5 manifest gate passes.

### U6. Import Host-Neutral Correctness and the Engine Substrate

Bring in the portable first half of the Claude window through the new Codex boundaries.

**Goal:** Port isolated outcome/board/retry correctness plus the external-engine HTTP bridge, registry, resolver, overlays, auth/preflight, conformance, and model/effort invocation using U2 and U5 contracts.

**Requirements:** R1, R3, R10, R13, R14, R20.

**Dependencies:** U1, U2, U5.

**Files:** `docs/portability/ports/2026-07-10-saga-07517.json`, `plugins/saga/scripts/board_progression.py`, `plugins/saga/scripts/discover_subissues.py`, `plugins/saga/scripts/outcome_edges.py`, `plugins/saga/scripts/outcome_github.py`, `plugins/saga/scripts/execution_spec.py`, `plugins/saga/scripts/workflow_emitter.py`, `plugins/saga/scripts/engine_bridge_http.py`, `plugins/saga/scripts/bridge_signatures.py`, `plugins/saga/scripts/engine_registry.py`, `plugins/saga/scripts/engine_registry_cli.py`, `plugins/saga/scripts/engine_resolver.py`, `plugins/saga/scripts/engine_dispatch.py`, `plugins/saga/scripts/engine_overlay.py`, `plugins/saga/scripts/check_engine_registry.py`, `plugins/saga/references/engine-registry.yaml`, `plugins/saga/references/model-releases.yaml`, `plugins/saga/references/dispatch-adapter-contract.md`, `plugins/saga/references/engine-dispatch.md`, `plugins/saga/tests/test_board_progression.py`, `plugins/saga/tests/test_execution_spec_tiers.py`, `plugins/saga/tests/test_engine_routing.py`, `tests/test_outcome_board_sync.py`, `tests/test_outcome_command.py`, `tests/test_outcome_from_objective.py`, `tests/test_outcome_integration.py`, `tests/test_engine_bridge_http.py`, `tests/test_engine_registry_conformance.py`, `tests/test_engine_registry_lint.py`, `tests/test_engine_registry_cli.py`, `tests/test_port_contract.py`.

**Approach:** Consume only U1 manifest rows classified `direct-port` or `codex-adapt`, preserve applicable execution-base drift, update row status and target/test evidence only as behavior lands, and require `port_contract.py validate --stage unit --unit U6` before integration. Port host-neutral algorithms and schemas, adapt `.claude` paths to Codex state, and require engine variants to carry enforceable model and effort through the dispatch envelope. Replace stale `codex --effort` recipes with current `--model` plus `-c model_reasoning_effort=...`; omit the Claude `codex:delegate` row so native subagents cannot masquerade as an external engine.

**Patterns to follow:** Preserve outcome board-write certificates and idempotency from the 0.64 Codex port. Use fleet-core receipts and catalog normalization rather than re-declaring model, effort, retry, or attestation schemas inside Saga.

**Test scenarios:** Happy path: cross-repo objective ingestion, crash-replay board comment dedupe, registry resolution, auth preflight, route explain, and an HTTP bridge dry run preserve typed evidence. Edge cases: duplicate issue numbers across repos, empty registry, overlay pin/deprecate replay, partial credentials, model fallback, timeout/retry clamp, and called-twice board sync remain deterministic. Error paths: unsupported source command/hook/Workflow surface, `codex:delegate`, stale `--effort` invocation, missing model/effort envelope, invalid registry row, unavailable explicit engine, or failed certificate halts before side effects.

Integration: one temporary bridge execution records the resolved engine/model/effort and receipt without granting completion authority.

**Verification:** All U6 manifest rows are permitted and carry current target/test evidence, Codex invocations enforce their advertised model/effort, generated classification remains current, and no native-subagent or Claude-host primitive appears as an external-engine success path.

### U7. Import Trust, Economics, Attestation, and Advisory Reconciliation

Layer the coupled 0.75 trust and advisory behavior only after dispatch and engine proof are real.

**Goal:** Port provider recommendation/onboarding, offload economics, output trust and attestation, liveness, typed reconciliation, and the upstream Team Execution advisory behavior into Verified Workflows while keeping every external result outside hard gate authority.

**Requirements:** R7, R9, R13, R14, R20.

**Dependencies:** U4, U6.

**Files:** `docs/portability/ports/2026-07-10-saga-07517.json`, `plugins/saga/scripts/chaperone_economics.py`, `plugins/saga/scripts/engine_offer.py`, `plugins/saga/scripts/engine_recommend.py`, `plugins/saga/scripts/engine_onboarding.py`, `plugins/saga/scripts/engine_promotion.py`, `plugins/saga/scripts/provenance_manifest.py`, `plugins/saga/scripts/reconcile.py`, `plugins/saga/references/engine-output-trust-boundary.md`, `plugins/saga/references/surface_intent_defaults.yaml`, `plugins/verified-workflows/skills/run/scripts/advisory_reconcile.py`, `plugins/verified-workflows/skills/run/references/workflow-protocol.md`, `plugins/verified-workflows/skills/run/references/external-engine-workers.md`, `plugins/verified-workflows/skills/run/references/worker-manifest.md`, `tests/test_chaperone_economics.py`, `tests/test_engine_offer.py`, `tests/test_engine_recommend.py`, `tests/test_engine_onboarding.py`, `tests/test_engine_promotion.py`, `tests/test_bridge_lie_detector.py`, `tests/test_engine_dispatch_attestation.py`, `tests/test_reconcile.py`, `tests/test_verified_workflow_gates.py`, `tests/test_verified_workflow_advisory.py`, `tests/test_port_contract.py`.

**Approach:** Consume only permitted U1 manifest rows, preserve applicable execution-base drift, and require `port_contract.py validate --stage unit --unit U7` after current target/test evidence is recorded. Preserve the source's dispatch identity, evidence digest, bounded structural projection, panel cap, and ordered reconciliation semantics. Preserve persisted v1 names `verified_by_claude`, enum member `FELL_BACK_TO_CLAUDE`, and value `fell-back-to-claude` exactly; translate them only in operator-facing labels/docs, and do not migrate the stored schema in this cycle.

External advisory findings never enter severity, required-role, or validator gate arithmetic even when attested; authority attaches to selected logical-role evidence, not a custom-agent filename. `engine_recommend.py`, `engine_offer.py`, and `engine_promotion.py` remain read-only proposal/report surfaces. `engine_onboarding.py` defaults to dry-run and may write the registry only with explicit `--apply`, an expected pre-write SHA-256, a contained target, and post-write readback; it never stores credentials or secret-bearing probe output.

**Patterns to follow:** Reuse the current Codex verified-versus-adjudicated manifest boundary and hash-chained run ledger. Keep recommendations advisory, spending checks before dispatch, and provider promotion read-only until explicit operator action.

**Test scenarios:** Happy path: a test-gated offload passes pre-dispatch economics, returns valid attestation and liveness proof, produces bounded findings, and reconciles as advisory evidence; an explicitly applied onboarding proposal matches its expected digest and readback. Edge cases: free provider, budget boundary, seven-seat panel cap, duplicate findings, rejected offload retention, called-twice reconcile/apply, dry-run byte identity, and exact legacy v1 names remain stable. Error paths: malicious finding text, substituted engine, zero external tokens, hash mismatch, missing liveness join, empty delivery, over-budget route, probationary provider in an advisory role, missing finding coverage, advisory vote entering hard-gate math, stale pre-write digest, symlink/path escape, secret-bearing output, or mutation from recommend/offer/promotion fails loud.

Integration: a Claude-labeled hard-gate record and external advisory report converge or conflict visibly while only the named Codex reviewer/validator set determines completion.

**Verification:** Adversarial tests prove external text is inert, economics stop spending before dispatch, attestation catches disguised fallback, reconciliation is idempotent, advisory evidence cannot pass or block a hard gate, and every U7 manifest row has current target/test evidence.

### U8. Version, Validate, Install, and Prove Fresh-Session Cutover

Publish metadata only after source, installed state, hooks, agents, and runtime behavior agree.

**Goal:** Release fleet-core `0.8.4`, Saga `0.75.17`, and `verified-workflows` `1.0.0`; retire installed `team-execution` `2.3.0`; update all inventory/docs/generated surfaces; refresh the local marketplace install; and prove role/class policy, truthful subagent-or-inline execution, hooks, legacy Saga re-entry, runbook/contract conformance, imported behavior, and rollback in fresh Codex tasks.

**Requirements:** R1, R5-R8, R12-R20.

**Dependencies:** U1, U3, U4, U5, U6, U7, U9.

**Files:** `plugins/team-execution/**`, `plugins/fleet-core/.codex-plugin/plugin.json`, `plugins/saga/.codex-plugin/plugin.json`, `plugins/verified-workflows/.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `README.md`, `plugins/fleet-core/README.md`, `plugins/saga/README.md`, `plugins/verified-workflows/README.md`, `plugins/fleet-core/CHANGELOG.md`, `plugins/saga/CHANGELOG.md`, `plugins/verified-workflows/CHANGELOG.md`, `docs/baseline/codex-visible-plugins.md`, `docs/portability/ports/2026-07-10-saga-07517.json`, `docs/portability/codex-plugin-modernization-cutover-and-rollback.md`, `docs/validation/codex-plugin-modernization-cutover.json`, `docs/validation/saga-family-target-inventory.json`, `docs/saga/generated/lifecycle-facts.json`, `scripts/port_contract.py`, `scripts/validate_codex_plugins.py`, `scripts/build_saga_docs_facts.py`, `scripts/render_saga_docs_assets.py`, `tests/test_port_contract.py`, `tests/test_validate_codex_plugins.py`, `tests/test_saga_docs_package.py`, `tests/test_verified_workflows_agents.py`, `tests/test_verified_workflows_migration.py`.

**Approach:** Update behavior-bearing release versions/manifests together, remove the temporary legacy source root in the same release change that activates the Verified Workflows marketplace entry, and run all Python checks through the locked project environment (`PYTHONPATH=. uv run ...`; the repository root is required because pytest uses importlib mode while tests import `scripts.*`). Transition the port manifest to cutover-ready only after every non-deferred source row is verified, every defer/reject rationale is revalidated, every Codex execution-base invariant passes, and the review/cutover paths exist.

Require `port_contract.py validate --stage cutover` before any installed-state mutation.

Before mutation, create KTD12's protected, uncommitted local rollback bundle and separately write a committed sanitized pre-state containing only source HEAD, relative old/new marketplace/cache inventory and hashes, managed-agent hashes/markers, old/new managed state-root inventory, pending managed hook-evidence hashes, hook definition/trust digests, and catalog hash. Exclude absolute user paths, raw managed bytes, prompts, config/trust values, environment values, and credentials from committed evidence. Validate that the local bundle can restore the captured state before continuing, and use the plugin creator's cachebuster/reinstall path rather than editing cache.

Run two isolated lanes. A clean-home lane proves first installation, trust, five-profile sync, skill/hook discovery, and canonical writes. A seeded-migration lane reconstructs the prior managed Team Execution package, markers, agents, trust shape, old roots, and pending managed events from safe fixtures or the local rollback bundle; it then proves read-old/write-new migration, removal of Team Execution, duplicate-surface absence, and an exact rollback to the seeded pre-state.

Neither lane copies default-profile credentials; a live isolated fresh task runs only when the operator has separately authenticated that isolated home, otherwise U4's capability remains `inline-only` or `auth-unavailable`. Apply the transaction to the real profile only after source/full-suite/contract/both-isolated-lane gates pass, using `--allow-real-profile` plus matching pre-state and rollback-bundle digests. Then open a fresh task through the already authenticated real profile to prove runtime discovery; on any failure, execute KTD12 rollback and verify exact prior readback.

**Patterns to follow:** Follow existing generated-doc `--check` gates and marketplace/source/cache separation. Preserve unrelated user changes, including `.serena/project.yml`.

**Test scenarios:** Happy path: cutover-stage port-contract validation, generated docs, focused tests, and full `PYTHONPATH=. uv run pytest` pass; the clean-home lane exposes the three target versions and exactly five profiles; the seeded lane migrates from Team Execution, proves legacy Saga re-entry/canonical writes, removes duplicate surfaces, and restores exact prior managed state on rollback; fresh tasks prove risk-class selection, logical-role/lens binding, inline fallback, hook receipts, and only the new plugin skills. When U4 produced a receipt, fresh tasks additionally prove review-high, test-medium, and scan-low execution before subagent vehicle claims are enabled.

Edge cases: second install, unrelated profiles/hooks, old managed markers, pending old raw events, untrusted new hooks, stale cache, unavailable preferred model, newer Claude or Codex `origin/main`, and unchanged legacy artifact checksums are handled without extending the frozen proof. Error paths: incomplete/stale port manifest, unclassified execution-base drift, manifest/version/runbook drift, missing or unreadable local rollback bundle, raw trust/config values in committed proof, both plugins enabled, duplicate skill/hook, old active write, conflicting roots, old trust reused, missing locked dependency/import root, cache edited as source, generic child reported as role-attested, required-independence role satisfied inline, missing receipt, unsanitized proof, full-suite failure, failed isolated rollback, failed real-profile apply, or failed real-profile rollback blocks cutover. Integration: one end-to-end plan/work/review/outcome slice produces model, workflow, gate, Saga, and external-advisory receipts without automatic PR, merge, deploy, or provider mutation.

**Verification:** Source and installed readback match target versions; active inventory contains Verified Workflows and not Team Execution; all checks pass; the sanitized cutover record contains hashed pre-state, both isolated-lane proofs, applied state, capability outcome, and rollback status without restoration secrets; the local rollback bundle is separately validated; five-profile accounting plus role/class proofs and one inline fallback are durable; live role receipts are required only for subagent vehicle claims; the port manifest has 100% stage-appropriate treatment/evidence and Codex-drift coverage; and generated classification is current.

---

## Codex-Native Execution Strategy

The root Codex thread owns the run directly; Verified Workflows is one of the components it creates and tests.

### Runtime Contract

- Destination: `plan-only` for this planning turn.
- Shape-based recommendation after cutover: `verified-workflow` because the nine units are cross-cutting and include security, migration, review, and fan-out signals.
- Operator-selected and effective Saga backend: `inline` because the recommended backend is under repair.
- Mechanical strategy: direct Codex serial or parallel subagents coordinated by the root thread.
- Permission strategy: parent `workspace-write` for U1-U7 when supported; broader real-profile authority is root-only in U8 after isolated proof.
- Root authority: Saga state, task ordering, shared-file integration, Git boundaries, final verification, and completion decisions.
- Fallback: when native subagents are unavailable or backpressured, continue serially in the root thread; do not fall back into either the legacy or new workflow plugin.

The operator-choice rationale is explicit: using Verified Workflows to implement and accept Verified Workflows would make the target protocol its own bootstrap trust root. `inline` identifies the runtime owner and does not mean every task must stay in one model context.

### Agent Topology and Model Policy

Use the lowest-capability role that can complete each bounded task, while keeping integration judgment in the root.

| Codex role | Work | Preferred model / effort | Mutation boundary |
|---|---|---|---|
| Root coordinator | Plan state, cross-unit decisions, integration, final verification | `gpt-5.6-sol` / `max` | Sole owner of Saga, shared integration files, Git, install, and cutover |
| Explorer | Code/docs tracing, source classification, file-overlap discovery | `gpt-5.6-terra` / `medium` | Requested read-only; root verifies no mutation |
| Worker | One bounded implementation unit or isolated file set | `gpt-5.6-sol` / `high` | One writer at a time in the shared worktree; parallel only in isolated worktrees |
| Reviewer | Correctness, architecture, security, and regression review | `gpt-5.6-sol` / `high` | Requested read-only; root verifies no mutation; findings remain advisory |
| Validator | Focused tests, schema checks, logs, and evidence reduction | `gpt-5.6-terra` / `medium`; `gpt-5.6-luna` / `low` for deterministic scans | Requested read-only except declared test artifacts; root verifies scope |

The root model and effort are selected explicitly before execution. The active generic spawn surface accepts task name, message, and fork context but exposes no per-child model, effort, named profile, sandbox override, or selection readback; prompt steering is therefore a request, not proof. Codex can load `model`, `model_reasoning_effort`, and `sandbox_mode` from a selected custom-agent TOML, but U3 only installs those profiles and U4 must prove profile plus logical-role selection through hook and lens evidence.

Until that proof exists, child values and mutation labels are preferences guarded by KTD14, and U3/U4 remain systems under test rather than execution governors.

Ultra is not selected for this run. The root already has an explicit dependency graph and bounded fan-out, so proactive delegation would reduce predictability without adding a missing capability.

### Per-Unit Wave

Each U-ID moves through the same host-native sequence.

```text
root selects U-ID and ownership
          |
          +--> requested-RO explorer(s) -----+
          |                                   |
          +--> docs/schema researcher --------+--> root synthesizes
                                                  |
                                      one worker or root writes
                                                  |
                              +-------------------+-------------------+
                              |                                       |
                    requested-RO reviewer                  focused validator(s)
                              +-------------------+-------------------+
                                                  |
                                  root inspects diff, verifies, commits
```

The root waits at every join before opening the next dependent unit. A child reports its U-ID, files read or changed, checks run, result, and unresolved risks; it does not update Saga state or declare the unit complete. Explorers and workers receive only the relevant U-ID context, while independent reviewers and validators use `fork_turns=none` and receive explicit target paths, acceptance criteria, diff or merge-base inputs, and required checks in their task message.

### Concurrency and File Ownership

Compute capacity from the active host and `agents.max_threads`, then use the lower limit. On the 2026-07-10 planning host, config permits six open agent threads but the task runtime exposes four total collaboration slots, so the root may run at most three children concurrently.

- Before assigning a writer or starting a parallel wave, record HEAD and the pre-existing dirty-path set, intersect it with the unit's declared files, and pause that unit when ownership is ambiguous; never absorb existing edits into plan output by assumption.
- Parallelize requested-read-only exploration, documentation research, review, and independent validators only after that snapshot; compare the worktree afterward and reject evidence from any child that mutated undeclared paths.
- Keep one writer in a shared worktree. Shared-worktree children do not stage, commit, or run the full suite.
- Permit parallel writers only in separate worktrees with disjoint declared ownership; merge in dependency order and re-run conflicts serially.
- Keep U8 install, hook trust, package replacement, real-profile mutation, rollback, and final readback in the root thread.

### Unit Routing

The routing maximizes context isolation without creating write races.

| Workstream | Units | Codex-native execution rule |
|---|---|---|
| Capability and fleet-core bootstrap | U1-U2 | Parallel requested-read-only grounding; root or one worker serializes shared policy changes. |
| Package identity migration | U9 | One writer owns the source move and compatibility vocabulary; independent history/denylist checks inspect afterward. |
| Role profiles and workflow receipts | U3-U4 | One implementation writer; independent reviewers and validators inspect afterward. Managed Verified Workflows profiles are only systems under test. |
| Saga runtime boundary | U5 | One writer owns shared Saga state code; requested-read-only regression and schema agents may run in parallel. |
| Upstream import batches | U6-U7 | Parallelize classification and focused test analysis; serialize overlapping source changes or isolate them in worktrees. |
| Release and cutover | U8 | Root-only mutation and readback after parallel requested-read-only preflight checks. |

### Acceptance Gates

- Each U-ID passes its named focused tests before the root integrates it.
- At least one fresh-context, requested-read-only Codex review examines each behavior-bearing unit; security-sensitive U3, U4, U5, U7, and U8 receive a dedicated security or operations pass.
- The root resolves findings by severity and verifies the actual diff and test output; no numeric workflow score is used to accept this plan's work.
- `/code-review` remains the formal work-to-PR gate after U1-U9, followed by the U8 port-contract, full-suite, isolated-profile, fresh-session, and rollback gates.
- Verified Workflows receipts, role evidence, and validator policy are accepted only as declared product-test evidence for U3, U4, U7, and U8. They never decide whether their own implementation is correct.

---

## System-Wide Impact

The work changes source policy, generated agent configuration, local plugin hooks, Saga state transitions, and installed marketplace behavior.

- fleet-core becomes the single model/effort/cost/proof and cross-plugin workflow-compatibility authority for Saga and Verified Workflows; mission-control and UniFi continue consuming the shared library through their existing shims.
- Verified Workflows gains transactional writes only to marker-owned profile files and prompt-free hook receipts in `PLUGIN_DATA`; normalized evidence is protected and completed raw pairs are removed. It does not gain mutation authority over source, GitHub, or deployments.
- Saga state remains in `.codex/saga` and committed outcome artifacts. Goal and hook state are references/receipts, not replacement sources of truth; legacy Team Execution values and dispatch commits remain readable and visible until explicitly reconciled, while new writes use only canonical workflow vocabulary.
- Future Claude-to-Codex imports become contract-gated: the runbook carries human judgment and the per-cycle JSON manifest carries exact source inventory, capability, treatment, preservation, test, version, and cutover evidence.
- External providers remain behind registry auth, trust, economics, and explicit mutation boundaries. No secret values or provider credentials enter repository artifacts.
- Fresh-session testing is mandatory because plugin, agent, hook, and model configuration can be cached by a running Codex process. Real-profile cutover records sanitized pre-state and rolls back only managed surfaces on failure.
- The implementation run itself introduces no new orchestration plugin or bootstrap agent fleet. It uses Codex's native root/child thread controls, while permanent model-pinned profiles remain deliverables and test subjects of U3/U4.

---

## Risks and Dependencies

The largest risks are false runtime proof, source drift, and trust-boundary regression.

| Risk or dependency | Impact | Mitigation |
|---|---|---|
| Codex catalog or schema changes after planning | Pinned models or fields become invalid. | Refresh catalog at U1/U8, use fixture-driven normalization, and require compatible fallback/readback. |
| Codex `origin/main` advances after the historical planning base | Current Saga or plugin behavior can be overwritten by a source-only port. | U1 freezes the approved execution base, inventories every plan-base drift path, and blocks units that do not preserve or explicitly reconcile it. |
| Verified Workflows is used to implement or accept itself | A defect in the target protocol can block or falsely validate the work. | Keep the Saga backend `inline`; use direct Codex children and root-owned acceptance gates. |
| The active child-spawn surface does not expose model, effort, named-profile, sandbox overrides, or readback | A requested child may run with a host-selected model and write-capable inherited permissions. | Use parent `workspace-write` for source units when supported, treat child settings as preferences, apply KTD14 pre/post snapshots, keep root verification authoritative, and require U3/U4 proof before claiming pinned-profile behavior. |
| Pre-existing user work overlaps a unit's declared files | A child could overwrite or accidentally claim unrelated work as plan output. | Intersect the unit file set with the preflight dirty-path snapshot; pause on ambiguous ownership or use an explicitly approved isolated worktree; never rewrite user changes. |
| Ultra causes recursive or generic delegation | Unbounded cost and untrusted gate evidence. | Root-only policy, `max_depth=1` proof, no Ultra in leaf profiles, role/class receipts required for workflow claims. |
| Profiles are installed but the role/class is not selected | Verified Workflows is reported but not run. | U4 role/lens/model/profile receipt and inline fallback; simulated probe never counts. |
| Package rename is applied as a broad replacement | Claude lineage or append-only evidence is corrupted. | U9 centralized aliases, historical allowlist, generated denylist checks, and no rewriting of old artifacts. |
| Old and new plugins are enabled together | Duplicate skills, hooks, or implicit invocation make runtime behavior ambiguous. | U9 permits dual source roots only while the target is explicitly unpublished and absent from the active marketplace; isolated add/prove/remove transaction; U8 fails unless exactly one canonical plugin is active. |
| Legacy marker, hook trust, or state is misclassified | Managed profiles become unmanaged, hooks run untrusted, or resumable work disappears. | Capture exact old bytes/trust/roots, recognize legacy ownership only during migration, read old roots without writing them, and roll back exactly. |
| Runbook prose or generated classification drifts from actual policy | Future ports repeat Claude-shaped mechanisms while appearing compliant. | Bind runbook version and SHA-256 in the closed JSON manifest, test its normative sections, use a deterministic renderer, integrate validation, and run a fresh planning-agent acceptance test. |
| Plugin hooks are untrusted or compose poorly | Missing evidence or surprising behavior. | Minimal nonblocking hooks first, explicit trust readback, fixture tests, idempotent receipts, no Git mutation. |
| Saga records dispatch before launch | Outcome DAG advances around nonexistent work. | Two-phase intent/ack state and crash-replay tests. |
| Existing outcome commits contain synthetic leaf ids | Active historical DAGs could be silently reinterpreted as launched. | Classify as settled `legacy-unverified`; block dependency progress until append-only evidence-backed reconciliation. |
| Claude `main` advances during implementation | Mixed baselines and unreviewed scope. | Commit-bound window; amendment required to extend. |
| External output reaches executable or gate sinks | Prompt injection, unsafe actions, or false consensus. | Opaque-data contract, attestation, evidence digests, report-only advisory seat, adversarial tests. |
| Full pytest is run outside the locked dev environment or without the repo import root | False missing-dependency/import failure or skipped proof. | Use `PYTHONPATH=. uv run pytest`; Pillow and test dependencies are already declared and locked; require green collection before release. |
| Real-profile install partially succeeds | Package identity, profiles, state, and hook trust disagree. | Capture pre-state, prove isolated profile first, mutate real profile last, roll back only managed surfaces, and require prior-state readback. |

---

## Alternatives Considered

The rejected alternatives either preserve stale assumptions or produce unverifiable execution claims.

| Alternative | Decision |
|---|---|
| Import Claude `0.75.17` first, then update models | Rejected: the imported engine and tier layers would immediately require rework and could encode unsupported Codex behavior. |
| Change only lineage comments and inherit the machine model | Rejected: the machine default is mutable and current Codex supports active per-agent model/effort configuration. |
| Treat Ultra as the rung after `max` | Rejected: documented Ultra behavior includes automatic delegation and changes execution semantics. |
| Keep the Team Execution name for compatibility | Rejected: it would continue promising peer-team behavior the Codex adapter no longer implements; compatibility belongs in centralized readers, not canonical writes. |
| Run U1-U4 through Verified Workflows | Rejected: the workflow and its Saga boundary are repair targets, so the protocol cannot be its own bootstrap trust root. |
| Add a permanent bootstrap-agent plugin only to run this plan | Rejected: Codex already provides root-owned subagents, custom-agent configuration, thread limits, steering, and collection; another orchestration layer would add the same indirection this amendment removes. |
| Keep 25 manually coupled custom-agent TOMLs | Rejected: the roles repeat five compute classes, couple job semantics to model policy, and multiply maintenance and migration risk. |
| Collapse roles without equivalence fixtures | Rejected: fewer profiles are not success if role constraints, exclusions, or finding quality regress. |
| Count installed TOMLs or `protocol_probe --subagents present` as subagent proof | Rejected: neither proves the selected role/class/lens ran with the intended model or returned gate evidence. |
| Keep Goal, hooks, fork, subagent, and Workflow in one backend enum | Rejected: they represent different lifecycle dimensions and several lack executable adapters. |
| Copy Claude hook files and commands directly | Rejected: payloads, tool names, paths, trust, and mutation assumptions differ. |
| Publish only a prose port runbook | Rejected: prose can explain judgment but cannot prove exact source coverage, current capability evidence, or generated classification consistency. |
| Assign the upstream Team Execution version to Verified Workflows | Rejected: it would conflate source lineage with a new Codex package identity. Saga/fleet-core preserve lineage labels; Verified Workflows starts at `1.0.0`. |

---

## Success Metrics

Completion is evidence-based rather than version-based.

- The JSON port manifest and generated classification cover exactly 156 focused source files under the four named pathspecs plus every Codex plan-base-to-execution-base drift path, with one explicit source treatment, one explicit Codex preservation treatment, a matching runbook digest, and no unresolved stage-appropriate row.
- U1-U9 execute with Saga `orchestration_mode=inline`; native child tasks are attributable by U-ID, and no Verified Workflows receipt or score is required to implement or accept the workflow itself.
- All 25 logical role IDs remain addressable: every agent-lens has complete independence/default/allowed-class and equivalence evidence, every deterministic validator has a command/evidence contract and no model fields, and installed readback accounts for exactly five managed profiles without touching unrelated profiles.
- Installed readback proves review-high, test-medium, and scan-low policies plus one inline fallback. Subagent vehicle claims additionally require matching live role/class/lens/profile receipts; otherwise the durable capability outcome is `inline-only` and no generic child is counted as Verified Workflows.
- Active inventory exposes only `verified-workflows:run` and `verified-workflows:appsec-audit`; new state and receipts contain only canonical vocabulary, while legacy Team Execution ticks, roots, refs, and receipts remain readable without byte changes.
- Outcome integration proves zero state transitions to `dispatched` without a matching launch acknowledgement and zero duplicate launches on replay.
- Hook fixtures and live smoke prove trusted, idempotent, non-mutating SessionStart and subagent receipt behavior alongside existing hooks.
- External-engine adversarial tests catch substitution, empty delivery, missing attestation, malicious findings, and advisory-gate contamination.
- Classification, per-unit, and cutover port-contract validation; generated docs checks; focused suites; full locked-environment pytest; clean-home install; seeded package migration; fresh-session cutover; and exact rollback-readback proof all pass before active marketplace metadata is released.
- A fresh planning agent can start from `AGENTS.md`, follow the runbook, initialize a manifest, and is blocked from implementation until source classification and capability evidence validate.

---

## Scope Boundaries

The plan modernizes the Codex adapter and imports only behavior that fits the verified Codex boundaries.

### Non-goals

- No full mirror of `infiquetra-claude-plugins`.
- No active Claude `.claude-plugin`, `commands`, markdown agents, raw hook manifests, Workflow emitters, `SendMessage`, or `.claude/saga` paths.
- No activation of `agy`, redis-channel remote gate transport, or the Claude `codex:delegate` external-engine row.
- No recursive Ultra leaf delegation and no claim that generic subagents satisfy Verified Workflows role evidence.
- No active Team Execution package, skill, state write, receipt write, agent marker, or Saga write vocabulary after cutover; the old name remains only in upstream lineage, centralized readers, migration fixtures, and historical evidence.
- No use of Verified Workflows as the implementation backend or acceptance authority for this plan; its profiles, receipts, gates, and advisory logic remain U3/U4/U7/U8 systems under test.
- No required peer-to-peer child messaging; the root owns follow-up and adjudication.
- No permanent bootstrap-agent bundle solely to execute U1-U9.
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
- Live Codex repository baseline at round-three review: historical plan base `7889025`, current `HEAD`/`origin/main` `fbd4001`, Saga `0.65.0`, 33 changed repository paths, and a 13-path intersection with the port's active source/inventory surfaces; U1 inventories all drift and refreshes/freezes the execution base rather than relying on these review-time values.
- Frozen Claude source reproduction: `git diff --name-only 9470edc..38742ece -- plugins/fleet-core plugins/saga plugins/team-execution tests` yields 156 paths split 12/63/10/71, while the unrestricted repository range yields 333 and is out of scope.
- `plugins/team-execution/scripts/sync_codex_agents.py:38-76`: current safe but raw-copy synchronization behavior.
- `scripts/validate_codex_plugins.py:242-263` and `scripts/validate_codex_plugins.py:479-524`: palette-derived hints and direct-model rejection.
- `plugins/team-execution/skills/team-execution/SKILL.md:20-47`: delegated/serial and vehicle semantics.
- `plugins/saga/scripts/outcome.py:69-104`: record-only default dispatcher.
- `plugins/saga/scripts/outcome_dispatcher.py:42-55`, `plugins/saga/scripts/outcome_dispatcher.py:151-162`, and `plugins/saga/scripts/outcome_dispatcher.py:232-247`: active/host-dependent backend model, synthetic dispatch result, and caller-asserted capabilities.
- `plugins/saga/scripts/saga.py:553-597` and `plugins/saga/scripts/saga.py:1372-1379`: scalar carry-forward and the missing explicit-destination marker that caused the plan-only readback regression.
- `plugins/saga/scripts/outcome_spec.py:44-78`, `plugins/saga/scripts/outcome.py:437-451`, and `plugins/saga/scripts/outcome.py:784-890`: current v1 state vocabulary and intent/commit records that treat a synthetic dispatcher result as settled dispatch.
- `docs/portability/codex-saga-064-drift-classification.md`: previous commit-bounded import classification and Codex adaptation rules.
- `docs/portability/provenance.md:14-25`: the current proof-port recipe and its explicit orchestration/MCP/app limitations, which U1 replaces with a runbook plus machine contract.
- `docs/portability/provenance.md` and `docs/engineering-journal/DECISIONS.md`: preserved-lineage version policy, curated adapter, active backend, receipt, and fleet-core policy history.
- `pyproject.toml` and `uv.lock`: the declared locked dev environment already includes Pillow, pytest, PyYAML, requests, and urllib3.
- `plugins/saga/skills/work/references/execution-strategy.md:43-91`: native inline, serial-subagent, and parallel-subagent mechanics are independent of Saga's runtime-backend choice and already define file-overlap and worktree safety.
- [Official Codex model guidance](https://learn.chatgpt.com/docs/models): Sol for complex/open-ended work, Terra for everyday work, Luna for clear/repeatable work; `max` deepens one task while Ultra adds subagent delegation.
- [Official Codex subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents): Codex owns spawning, steering, waiting, and result collection; built-in `default`, `worker`, and `explorer` agents are available; generic children inherit the parent sandbox/permission mode; custom agent TOMLs support `model`, `model_reasoning_effort`, and `sandbox_mode`; current local Codex delegates on direct or applicable skill instructions; default max depth is one.
- [Official Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference): `agents.max_threads`, `agents.max_depth`, and role config layers define host concurrency and custom-agent configuration.
- Live 2026-07-10 runtime projection: Codex CLI `0.144.1` reports eight catalog rows, including Sol/Terra/Luna, scalar efforts through `max`, Ultra on Sol/Terra, and multi-agent versions on the GPT-5.6 family; the sanitized committed snapshot remains a U1 deliverable.
- [Official Codex plugin guidance](https://learn.chatgpt.com/docs/build-plugins): plugins can bundle hooks under `hooks/hooks.json`, but hook trust is explicit.
- [Official Codex hook reference](https://learn.chatgpt.com/docs/hooks): plugin hooks expose active `model`, SubagentStart/Stop `agent_type`, and current event limitations.

---

## Recommended Next Step

Round-three `saga:doc-review` passed after all actionable P0-P3 findings were fixed in place. Await explicit operator approval; after approval, reconcile pre-existing edits that overlap U1, freeze the approved execution base, and enter `saga:work` at U1 with Saga backend `inline` and the Codex-native subagent strategy above. Neither legacy Team Execution nor Verified Workflows may implement or accept any U1-U9 unit.
