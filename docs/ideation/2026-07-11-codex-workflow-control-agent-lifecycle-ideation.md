---
date: 2026-07-11
topic: codex-workflow-control-agent-lifecycle
focus: Recent Claude plugin adaptations, worker lifecycle and cache economics, operator control of Verified Workflows, and Mimir promotion loops
scope: broad
repo: infiquetra-codex-plugins
maturity: idea-ready
---

# Ideation: Codex Workflow Control and Agent Lifecycle

## Grounding Context

**Repo:** `infiquetra-codex-plugins` is a curated Codex-native adapter with mandatory source classification, immutable approved workflow rows, root adjudication, and diagnostic child receipts. Its GitHub queue contained only two open issues, so the run also used the repo journal and active implementation surfaces.

**Context-libraries:** `infiquetra-context-library` supplied host-redesign, intentional-divergence, HITL, and deterministic-telemetry constraints. `mimir-context-library` was unrelated to the plugin topic and contributed analogy material only.

**Named repos:** `infiquetra-claude-plugins` supplied current source behavior, 103 open issues, resident-worker semantics, and post-port deltas. `team-mimir` supplied 41 current issues covering decision rails, observability, controlled experiments, separation of duty, and stalled-work escalation.

The live source comparison found unadapted save-intent tracking, sticky Saga `kind`, exact ship-transition confirmation, and a partially adapted second-opinion claim/replay sidecar. Basic workflow recommendation, alternatives, explicit operator choice, and GPT-5.6 model identity were already adapted. Claude resident-worker reuse was an intentionally deferred host-boundary question, not a recent missing port.

External web research failed because the search adapter returned undecodable responses. The requested external-engine second-opinion lane was also unavailable in the active Codex session, so no external advisory result or receipt was claimed.

## Topic Axes

1. Port intake and source-delta classification
2. Worker residency, reuse, reclamation, and cache economics
3. Workflow recommendation, preview, editing, and operator consent
4. Execution evidence, liveness, recovery, and truthful teardown
5. Mimir pilot loops, metrics, and promotion criteria

## Ranked Survivors

### 1. Workflow Contract Studio

Turn a recommended workflow into an inspectable, editable, policy-checked execution contract.

Show the DAG, dependency order, profiles, model and effort requests, independence losses, downgrade paths, evidence obligations, irreversible transitions, abort conditions, and expected operator attention. Operator edits create a new candidate execution revision and a consequence diff; they never mutate an immutable approved run.

This strengthens the existing recommendation and confirmation contract rather than pretending choice is absent. The downside is the high carrying cost of keeping editable fields, consequence semantics, validation, and terminal rendering aligned.

| field | value |
|---|---|
| basis | direct: user seed 2; `plugins/saga/references/operator-choice.md`; immutable Verified Workflow rows and Mimir decision-rail issues |
| source | combined |
| confidence | 95 |
| complexity | High |
| axis | Workflow recommendation, preview, editing, and operator consent |
| status | Unexplored |

### 2. Lifecycle Custody Protocol

Make launch, completion, retention, reuse, cancellation, reclamation, and unknown liveness distinct root-owned states.

Every worker receives an explicit lease or teardown disposition. A double-entry ledger records intended lifecycle actions beside independent runtime evidence, and terminality remains `reclaimed`, `retained-under-lease`, or `teardown-unverified` rather than inferring that completed work means a stopped process.

This directly answers the stop-or-reuse seed while preserving Codex's weak-attestation boundary. Some hosts cannot prove reclamation, so unresolved liabilities must remain visible.

| field | value |
|---|---|
| basis | direct: user seed 1; diagnostic receipt boundary; truthful dispatch contract; Mimir liveness and wedge-escalation queue |
| source | combined |
| confidence | 93 |
| complexity | High |
| axis | Execution evidence, liveness, recovery, and truthful teardown |
| status | Unexplored |

### 3. Port Invariant Control Plane

Track upstream semantic intent continuously instead of rediscovering adaptation debt during manual sweeps.

Machine-built intake groups related source deltas into behavioral invariants, checks them against the frozen manifest, produces native/adapted/deferred candidate classifications, and links intentional divergences to executable revisit triggers. Human review still owns classification and host-specific redesign.

The uncovered save-intent, sticky-kind, ship-confirmation, and second-opinion changes show that commit lists and a tiny Codex issue queue are insufficient freshness controls. The downside is cross-repo schema and CI ownership plus the risk of noisy or falsely complete automated intake.

| field | value |
|---|---|
| basis | direct: post-`38742ece` source comparison; closed JSON classification gate; intentional-divergence guidance |
| source | combined |
| confidence | 91 |
| complexity | High |
| axis | Port intake and source-delta classification |
| status | Unexplored |

### 4. Reuse the Context, Not the Agent

Reclaim workers by default while preserving compact, provenance-bearing context capsules for fresh successors.

Capsules contain bounded inputs, artifact hashes, findings, failed checks, decisions, and failure lineage. Same-identity reuse becomes an exceptional capability requiring runtime proof and remains forbidden where reviewer independence matters.

This captures most cache and handoff value without depending on hidden conversational state. Capsule construction consumes tokens and can omit tacit context, so its cost and fidelity need measurement.

| field | value |
|---|---|
| basis | reasoned: reusable verified state preserves locality while fresh execution identities reduce stale-context and separation-of-duty risk |
| source | frame-agent |
| confidence | 89 |
| complexity | Med |
| axis | Worker residency, reuse, reclamation, and cache economics |
| status | Unexplored |

### 5. Mimir Promotion Laboratory

Use Mimir's current queue as a governed proving ground for workflow and lifecycle changes.

Each pilot preregisters a hypothesis, baseline, cohort, safety gates, failure budget, deterministic metrics, observation window, operator veto, and promotion threshold. Successful behavior graduates into a Codex classification or reusable governance rule; failures preserve divergence evidence and rollback learning.

Mimir already queues the needed decision rails, harness metrics, stall escalation, controlled experiments, and separation-of-duty review. Its workload may not be representative enough for fleet-wide promotion.

| field | value |
|---|---|
| basis | direct: team-mimir issue themes, engineering journal, and deterministic fleet telemetry requirements |
| source | combined |
| confidence | 88 |
| complexity | Med |
| axis | Mimir pilot loops, metrics, and promotion criteria |
| status | Unexplored |

### 6. Context Locality Scheduler

Group related work by shared evidence and cache economics while keeping independence boundaries explicit.

The scheduler chooses between fresh workers, capsule handoff, short retention, or proven same-worker reuse using source overlap, role compatibility, cache half-life, next-use probability, and teardown cost. Review-repair cohorts may share locality, but author and independent reviewer identities remain separate.

This develops the grouping and cache-read/write seed into a measurable scheduling policy. It requires substantial telemetry before warm retention can be shown to outperform capsule hydration.

| field | value |
|---|---|
| basis | direct: user seed 1; Claude segment residency and cache TTL; fleet telemetry; Mimir separation-of-duty rules |
| source | combined |
| confidence | 84 |
| complexity | High |
| axis | Worker residency, reuse, reclamation, and cache economics |
| status | Unexplored |

### 7. Transition-Scoped Consent

Separate approval of an execution shape from authority for stateful or irreversible lifecycle transitions.

Workflow approval grants bounded execution capabilities, while explicit save intent, sticky Saga identity, contradictory state changes, and the exact ship transition remain independently enforced decisions. Consequential transitions consume their own consent and time out closed.

This turns three recent Claude deltas into one coherent Codex-native consent model instead of unrelated flag ports. Additional consent states may create prompt fatigue without clear policy envelopes.

| field | value |
|---|---|
| basis | direct: Claude commits for save-intent, sticky `kind`, and exact ship-transition confirmation; current fail-closed operator contract |
| source | frame-agent |
| confidence | 83 |
| complexity | Med |
| axis | Workflow recommendation, preview, editing, and operator consent |
| status | Unexplored |

## Did not survive (revivable)

| id | title | summary | reason | status |
|---|---|---|---|---|
| R1 | Intent-Aware Source Delta Bundles | Classify related changes as semantic bundles. | Dominated by Port Invariant Control Plane. | rejected |
| R2 | Receipt-Backed Worker Leases | Give every child a disposition and TTL. | Subsumed by Lifecycle Custody Protocol. | rejected |
| R3 | Editable Consent Packet | Preview and edit workflow rows before approval. | Subsumed by Workflow Contract Studio. | rejected |
| R4 | Child Terminality Ledger | Separate completion, termination, and reclamation. | Subsumed by Lifecycle Custody Protocol. | rejected |
| R5 | Ephemeral-versus-Reuse Pilot | Compare fresh and reusable workers. | Narrower than Mimir Promotion Laboratory. | rejected |
| R6 | Review-Repair Affinity Cohorts | Bound locality to one repair lineage. | Subsumed by Context Locality Scheduler. | rejected |
| R7 | Consequence-Diff Editing | Explain the operational effects of workflow edits. | Retained as a Workflow Contract Studio component. | rejected |
| R8 | Delta-by-Exception Intake | Open intake only for unmatched contracts. | Subsumed by Port Invariant Control Plane. | rejected |
| R9 | Lease-or-Reap Residency | Retain only with a next assignment and TTL. | Too binary beside the custody protocol. | rejected |
| R10 | Workflow Counterproposal | Submit a new candidate instead of approving an opaque row. | Subsumed by Workflow Contract Studio. | rejected |
| R11 | Teardown Receipt | Require explicit retained, reclaimed, or unverified terminality. | Subsumed by Lifecycle Custody Protocol. | rejected |
| R12 | Failure-Budget Promotion | Gate pilots on deterministic failure budgets. | Retained inside Mimir Promotion Laboratory. | rejected |
| R13 | Warm Repair Cohorts | Reuse workers within one defect family. | Assumes identity reuse before evidence supports it. | rejected |
| R14 | Intent-Change Tripwires | Emit compatibility records from upstream intent changes. | Retained inside Port Invariant Control Plane. | rejected |
| R15 | Port Intent Ledger | Track semantic intent rather than commits. | Dominated by the executable control-plane synthesis. | rejected |
| R16 | Economic Worker Leases | Price and expire worker residency. | Covered by Lifecycle Custody and Context Locality. | rejected |
| R17 | Editable Decision Diff | Present the recommendation as a policy delta. | Subsumed by Workflow Contract Studio. | rejected |
| R18 | Teardown Evidence Event | Require root-observed reclamation evidence. | Subsumed by Lifecycle Custody Protocol. | rejected |
| R19 | Mimir Promotion Court | Use Mimir for governed promotion. | Less operationally complete than the laboratory. | rejected |
| R20 | Port Invariant Compiler | Generate cross-host invariant tests. | Retained inside Port Invariant Control Plane. | rejected |
| R21 | Divergence Trigger Graph | Reopen deferred decisions when evidence changes. | Retained inside Port Invariant Control Plane. | rejected |
| R22 | Affinity Worker Commons | Pool proven workers by identity and locality. | Prematurely assumes reusable worker identity. | rejected |
| R23 | Cache-Aware Segment Packing | Schedule work by shared context and independence. | Retained inside Context Locality Scheduler. | rejected |
| R24 | Approval Policy Distillation | Learn proposed defaults from operator edits. | Depends on Workflow Contract Studio evidence first. | rejected |
| R25 | Lifecycle Double-Entry | Reconcile intended actions with observed runtime state. | Retained inside Lifecycle Custody Protocol. | rejected |
| R26 | Evidence-to-Promotion Flywheel | Promote successful queue experiments into capabilities. | Subsumed by Mimir Promotion Laboratory. | rejected |
| R27 | Port Customs | Quarantine source-change articles independently. | Analogy adds no capability beyond invariant intake. | rejected |
| R28 | Balanced Lifecycle Entries | Pair new intent fields with enforcement behavior. | Too narrow beside the port and consent survivors. | rejected |
| R29 | Orbital Worker Berths | Assign completed workers a next mission or retirement. | Analogy duplicates the custody protocol. | rejected |
| R30 | Context Locality Exchange | Treat context as perishable inventory. | Retained inside Context Locality Scheduler. | rejected |
| R31 | Operator Flight Plan | Recompile edited constraints into an approved route. | Analogy duplicates Workflow Contract Studio. | rejected |
| R32 | Harbor Custody States | Separate delivery from worker departure. | Analogy duplicates Lifecycle Custody Protocol. | rejected |
| R33 | Preregistered Mimir Trial | Declare hypotheses and promotion thresholds. | Retained inside Mimir Promotion Laboratory. | rejected |
| R34 | Port Intake Without Sweeps | Eliminate manual delta discovery. | Too absolute because semantic completeness is unproved. | rejected |
| R35 | Permanent Worker Guild | Retain workers for an outcome campaign. | High lifecycle and independence risk without attestation. | rejected |
| R36 | Stateless Workers Only | Require universal single-use workers. | Overcorrects and forecloses measured reuse. | rejected |
| R37 | Operator-Owned Workflow Source | Let operators edit every workflow field. | Some safety invariants must remain policy-controlled. | rejected |
| R38 | No Runtime Approval Prompts | Preapprove envelopes and eliminate routine prompts. | Premature before transition taxonomy and consequence rendering. | rejected |
| R39 | Receipts Are Allegations | Trust no receipt for any terminal fact. | Corroborated diagnostic receipts remain useful. | rejected |
| R40 | Automatic Mimir Contest | Continuously auto-promote winning variants. | Exceeds current governance evidence. | rejected |

All five topic axes retain at least one survivor. Most cuts were narrower mechanisms or analogies already captured by stronger combined survivors.

## Co-ideation Log

| source | entered | idea / seed | outcome |
|---|---|---|---|
| user-seed | Phase 0 | Finished subagents should be explicitly stopped or deliberately reused to improve cache economics. | Survived through #2, #4, and #6 after correcting the assumption that resident workers were a missing recent Codex port. |
| user-seed | Phase 0 | Operators need better visibility, approval information, and editing of recommended Verified Workflows. | Survived through #1 and #7 after correcting the assumption that basic recommendation and explicit choice were absent. |
| frame-agent | Phase 2 | Six divergent frames generated 42 grounded candidates. | Seven combined or frame-native candidates survived. |
| engine-generated | Phase 2 | External second-opinion lane selected. | No candidate entered: the active Codex session exposed no usable external-engine runner and produced no receipt. |
