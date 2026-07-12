---
title: Codex External Advisory Execution Contract Plan
type: feat
status: active
date: 2026-07-11
origin: docs/brainstorms/2026-07-11-codex-external-advisory-execution-contract-requirements.md
deepened: 2026-07-11
---

# Codex External Advisory Execution Contract Plan

## Summary

Build one Codex-owned external-action runtime that turns approved offload and second-opinion intent into attributable Claude CLI, `agy`, or OpenAI-compatible HTTP execution across all six named Saga stages. The implementation adds durable approval and action state, supervised provider adapters, Codex-owned adjudication and consumption, operator-visible status cards, and a real release matrix without granting external providers live-tree or gate authority.

## Problem Frame

The current Codex surface can offer and persist an external-engine preference, but no production lifecycle call site constructs a runner or consumes `engine_dispatch.dispatch()`. The repository therefore proves registry, resolution, HTTP, receipt, manifest, and reconciliation helpers in isolation while the operator-visible stage-to-provider round trip remains absent (`docs/investigations/external-second-opinion-preference-noop-2026-07-11.md:15`).

The plan must adapt the working Claude contracts without copying Claude host assumptions. The port runbook requires a classified JSON manifest before source-derived behavior changes, Codex root remains the verifier and mutation owner, and existing manifests or launch intent cannot be treated as proof that an external provider ran (`docs/portability/claude-to-codex-plugin-port-runbook.md:169`, `docs/engineering-journal/DECISIONS.md:57`).

## Requirements

The implementation checklist preserves the reviewed requirements while grouping them into buildable contracts.

| ID | implementation requirement | origin requirements | origin flows and acceptance |
|---|---|---|---|
| R1 | One shared runtime must prepare, approve, execute, adjudicate, and consume multi-action bundles for `/ideate`, `/brainstorm`, `/plan`, `/work`, `/doc-review`, and `/code-review`. | R1-R6 | F1-F3; AE1 |
| R2 | Approval must bind the concrete route, outbound context scope, sensitivity, cost and egress posture, and write set; any material change invalidates approval. | R5-R8 | F1, F7; AE2, AE5-AE6 |
| R3 | Repo-and-stage policy must live separately from execution evidence, resolve concrete routes every run, and treat legacy preferences only as unapproved desired intent. | R7-R9 | F7; AE2, AE9 |
| R4 | Capability and explicit-provider routing must remain visible, prefer cross-family second opinions, warn on same-family choices, and never silently substitute. | R10-R14, R45 | F1, F4; AE2-AE3, AE8 |
| R5 | The runtime must support supervised Claude CLI, contained `agy`, and registry-driven OpenAI-compatible HTTP through explicit adapters. | R15-R20 | F2, F5; AE6-AE7 |
| R6 | HTTP provider onboarding must be dry-run first, validate and smoke before apply, store only secret references, apply to a repo-local overlay, and promote canonical rows separately. | R21-R24, R56 | F6; AE11 |
| R7 | Literal credentials must be blocked or redacted before dispatch while approved sensitive business content may cross only the approved egress boundary. | R24-R26 | F1-F2, F6; AE5, AE11 |
| R8 | CLI patch work must run in disposable remote-stripped clones, preserve bounded patches and write-set evidence, and never mutate the live worktree; HTTP remains artifact-only. | R27-R32 | F3, F5; AE6-AE7 |
| R9 | Durable state must distinguish every approval, launch, terminal, receipt, adjudication, and consumption milestone without inferring success. | R33-R35, R39, R47-R51 | F2-F4; AE1, AE3-AE4, AE7, AE9-AE10, AE12 |
| R10 | Second opinions must produce typed findings, remain inert until Codex adjudication, and never satisfy or block a substantive gate independently. | R36-R40 | F2-F3; AE4, AE7-AE8 |
| R11 | Claim-before-launch and append-only transitions must prevent blind redispatch after interruption, resume, or unavailable state persistence. | R33, R38-R39 | F2, F4; AE12 |
| R12 | Best-effort and required-before-continue actions must have distinct progression behavior, with durable operator rationale for removal or continuation. | R41-R46 | F4; AE3-AE4 |
| R13 | Status cards must expose requested and approved intent, actual route and receipt truth, cost and usage, artifact destination, adjudication, and consumption. | R47-R51 | F2-F4; AE1, AE3-AE4, AE7, AE9-AE10, AE12 |
| R14 | Release evidence must prove real Claude CLI, `agy`, and Ollama Cloud actions plus approved action consumption and status rendering across all six stages. | R52-R54 | F1-F6; AE1, AE6-AE8, AE11 |
| R15 | Negative proof must cover credential, route, provider, process, receipt, containment, replay, requiredness, and operator-rejection failures. | R55 | F4-F5; AE3-AE6, AE9, AE12 |
| R16 | Promotion evidence must use versioned definitions and collect the required provider, acceptance, integrity, containment, and rollback measurements without enabling direct mutation. | R32, R57 | F8 |
| R17 | Every source-derived adaptation must pass classification, per-unit evidence, cutover, isolated-install, fresh-session, and rollback gates from the port contract. | Port runbook v3 | Release gate |
| R18 | Codex root must remain the sole live-tree mutation owner, gate authority, external-output verifier, and final completion claimant. | R20, R28-R30, R37, R40 | F3-F5; AE4, AE6-AE7 |

## Key Technical Decisions

The implementation uses one layered Codex runtime and reuses existing proof primitives instead of widening their authority.

| ID | decision | rationale |
|---|---|---|
| KTD1 | Add one shared external-action runtime; keep lifecycle stages as declarers and consumers. | Stage-owned dispatch would duplicate approval, replay, and evidence behavior six times. |
| KTD2 | Persist each action under `<git-common-dir>/saga-external-actions/<saga-id>/<run-id>/<action-id>/` as immutable `request.json` and `approval.json`, append-only `events.jsonl`, and derived `status.json` / `status.md`. | Mutable snapshots cannot explain uncertain launch or detect lost and contradictory transitions; an exact shared-worktree path prevents implementers from inventing competing stores. |
| KTD3 | Keep the action store separate from `manifest_store.py` and `run_ledger.py`, referencing their manifests and facts instead of overloading them. | Manifests answer what ran and the ledger records facts; neither models operator approval, requiredness, adjudication, and consumption. |
| KTD4 | Let the runtime own adapter selection and factories while `engine_dispatch.py` remains the receipt, integrity, and advisory-evidence validator. | This preserves the tested dispatch contract and prevents provider or stage orchestration from accumulating in the validator. |
| KTD5 | Adapt Claude's bounded second-opinion and supervised-delegate semantics, but implement Codex-native modules and authority boundaries. | The current port manifest rejects Claude host delegates as active Codex surfaces, and no active `second_opinion.py` target exists. |
| KTD6 | Use full disposable local clones pinned to a recorded base, remove remotes, enforce write-set diffing, and preserve patches without live application. | This is the simplest proven containment pattern already used by the sibling implementation; sparse read-set workspaces add complexity not warranted by the operator's trust model. |
| KTD7 | Pin CLI actions to committed `HEAD`, exclude dirty and untracked bytes from the clone, list write-set overlap in the preview, and require explicit approval of that stale-base risk. | This preserves the simplest reproducible clone path without silently implying the provider saw live uncommitted content; Codex root still verifies or rejects the returned patch. |
| KTD8 | Store policy at `.codex/saga/external-action-policy.json`; resolve explicit run edits over repo/stage policy, repo/stage policy over legacy intent, and legacy intent over shipped defaults. Read `engine-prefs.json` only as legacy unapproved intent. | A fixed path and precedence remove ambiguity while avoiding the current category error between preference, approval, and proof. |
| KTD9 | Store operator-local provider rows at `.codex/saga/engine-registry-overlay.yaml`; compose canonical rows first and additive overlay rows second, halt on duplicate keys, and promote canonical rows through a separate reviewed source change. | Operator-local endpoints become selectable without private configuration in the shipped registry or silent canonical shadowing. |
| KTD10 | Keep normal CI hermetic and run the credentialed Claude, `agy`, Ollama Cloud, and six-stage matrix through an explicit attended release harness. | Default CI must remain deterministic while release still requires real provider evidence. |
| KTD11 | Ship runtime modules dark until all six stages consume the common contract; do not activate a partial stage subset as the product. | The requirements explicitly reject another disconnected substrate or partial-MVP deferral. |
| KTD12 | Execute through Verified Workflows with root-owned integration, credential use, Git, and final adjudication. | The change crosses more than eight files, six stages, subprocess and credential boundaries, and requires independent security and evidence review. |

## High-Level Technical Design

The runtime forms a single stateful boundary around existing resolver, dispatch, manifest, ledger, and reconciliation primitives.

```text
 lifecycle stage
      |
      v
 action bundle defaults + repo/stage policy + legacy intent
      |
      v
 prepare concrete routes and egress preview
      |
 operator approval -> immutable approval fingerprint
      |
 durable claim -> append-only action transition
      |
 adapter factory
   |          |                 |
 Claude CLI  agy CLI            OpenAI-compatible HTTP
   |          |                 |
 disposable clone + patch       artifact only
   +----------+-----------------+
              |
 engine_dispatch receipt and evidence validation
              |
 manifest reference + run-ledger fact + status projection
              |
 Codex verification and adjudication
              |
 stage consumption or explicit rejection
```

The canonical action identity includes repository identity, Saga/run identity, stage, bundle and action IDs, approval fingerprint, attempt, and immutable request digest. The approval fingerprint covers route identity, provider and model, cost class, egress metadata, context and sensitivity summary, base revision, and write set; a changed value creates a new preview rather than mutating approval history.

The action store lives under the repository Git common directory beside existing Saga manifests and run facts so worktrees share replay truth. It writes one immutable action record and an append-only, lock-protected event stream per action; a renderer produces JSON and Markdown status projections without making the projection authoritative.

Policy and registry overlays remain machine-local under `.codex/saga/`. Policy precedence is explicit run edits, then the repo-and-stage policy, then legacy unapproved intent, then shipped stage defaults. Registry composition is additive-only: an overlay may introduce a new engine/variant key but may not replace a canonical row; an identical or conflicting duplicate halts until canonical promotion or overlay removal resolves it.

### Action Lifecycle

The event log uses one closed transition graph so requiredness and resume behavior cannot drift between stages.

| current milestone | accepted event | resulting milestone or outcome |
|---|---|---|
| requested | route resolved and preview persisted | resolved |
| resolved | operator approves unchanged egress contract | approved |
| resolved | operator rejects or removes action | rejected / not launched |
| approved | durable claim appended | claimed |
| claimed | adapter launch acknowledged | launched |
| claimed | launch cannot start | unavailable / not launched |
| launched | valid terminal receipt and output arrive | available |
| launched | timeout, interruption, cancellation, malformed receipt, or containment failure occurs | timed out / interrupted / canceled / invalid evidence |
| available | Codex accepts all or part of the evidence | accepted |
| available | Codex rejects the evidence | rejected |
| accepted | named stage attaches the accepted evidence | consumed |
| any non-consumed state | material route, context, sensitivity, base, or write-set change | new resolved preview; prior approval remains historical and unusable |

Best-effort terminal failures may continue visibly. Required terminal failures pause until retry creates a new attempt, the operator removes the action, or the operator records a continuation override and rationale; no override rewrites the failed attempt.

## Implementation Units

### U1. Freeze the adaptation and capability boundary

Classify every Claude-derived contract and every net-new Codex target before behavior changes.

**Goal:** Create the cycle port manifest, bind the reviewed requirements and plan, classify source-derived second-opinion and delegate behavior, and record the Codex-native rejection or adaptation for every source row.

**Requirements:** R17, R18; origin R15-R20, R27-R40.

**Dependencies:** None.

**Files:** `docs/portability/manifests/2026-07-11-external-advisory-execution.json`; `docs/portability/matrix.md`; `tests/test_port_contract.py`; existing `scripts/port_contract.py` as validator.

**Approach:** Start a new manifest rather than extending the completed `2026-07-10-saga-07517.json` window. Classify Claude `second_opinion.py`, `agy_delegate.py`, and supervised delegate contracts as semantic inputs; reject Claude command, Workflow, TeamCreate, direct Codex-delegate, and host-cache assumptions; declare every new runtime, store, adapter, skill, and test target before U2.

**Patterns to follow:** `docs/portability/claude-to-codex-plugin-port-runbook.md`; `docs/portability/manifests/2026-07-10-saga-07517.json`; `scripts/port_contract.py`.

**Test scenarios:** A complete classified manifest passes the classification gate; a missing source row, unclassified target, changed runbook digest, active Claude-only primitive, or unapproved source-window drift fails before implementation. A Codex-native module with no source counterpart is recorded as net-new adaptation rather than falsely labeled direct-port.

**Verification:** The classification report names zero unclassified rows and preserves the frozen source and Codex execution bases.

### U2. Add the action contract, store, and status projection

Establish durable action identity and transition truth without invoking a provider.

**Goal:** Define action bundles, approval fingerprints, requiredness, lifecycle states, immutable records, append-only transitions, replay reads, and derived status cards.

**Requirements:** R1-R3, R9, R11-R13.

**Dependencies:** U1.

**Files:** `plugins/saga/scripts/external_action_contract.py`; `plugins/saga/scripts/external_action_store.py`; `plugins/saga/scripts/external_action_status.py`; `tests/test_external_action_store.py`; `tests/test_external_action_status.py`; `tests/test_status_card.py`.

**Approach:** Use closed enums and versioned JSON schemas for milestones and terminal outcomes. Store request and approval records immutably, append transitions under a file lock with expected-sequence checks, reference rather than copy engine manifests and ledger facts, and make every projection reproducible from the event history.

**Patterns to follow:** `plugins/saga/scripts/manifest_store.py`; `plugins/saga/scripts/run_ledger.py:54`; `plugins/saga/scripts/provenance_manifest.py`; `plugins/saga/scripts/status_card.py:26`.

**Test scenarios:** Create and read a valid action; reject duplicate IDs with different request digests; accept idempotent replays; reject skipped, duplicated, regressed, or contradictory transitions; recover a projection after interruption; fail closed on corrupt or unavailable state; render every R51 status distinctly; keep secrets out of records and projections; share truth across worktrees through the Git common directory.

**Verification:** A fresh process can reconstruct approval, launch, receipt, adjudication, and consumption truth solely from the durable action history and referenced evidence.

### U3. Build approval, policy, and runtime orchestration

Turn stage declarations into approved, replay-safe action attempts while keeping provider execution abstract.

**Goal:** Implement bundle preparation, concrete route preview, approval invalidation, policy resolution, claim-before-launch, requiredness progression, adjudication, consumption, and a thin operator CLI/API.

**Requirements:** R1-R4, R7, R9-R13, R18.

**Dependencies:** U2.

**Files:** `plugins/saga/scripts/external_action_runtime.py`; `plugins/saga/scripts/external_action.py`; `plugins/saga/scripts/external_action_policy.py`; `plugins/saga/scripts/external_action_egress.py`; `plugins/saga/references/external-action-defaults.yaml`; `plugins/saga/scripts/engine_offer.py`; `plugins/saga/scripts/engine_preference.py`; `plugins/saga/scripts/engine_dispatch.py`; `tests/test_external_action_runtime.py`; `tests/test_external_action_egress.py`; `tests/test_engine_offer.py`; `tests/test_engine_dispatch_attestation.py`.

**Approach:** Expose prepare, approve, execute, adjudicate, consume, and status operations over one library contract. Apply the KTD8 policy precedence, import legacy preferences only as desired intent, fingerprint the complete egress contract, scan and redact or block credential-like outbound values before adapter selection, require run-specific approval, claim durably before adapter launch, and map failures through best-effort or required progression without fabricating evidence.

**Patterns to follow:** `plugins/saga/scripts/engine_resolver.py:334`; `plugins/saga/scripts/engine_dispatch.py:236`; `plugins/saga/scripts/engine_offer.py:165`; sibling `plugins/saga/scripts/second_opinion.py:843` for bounded context and claim/replay semantics only.

**Test scenarios:** Prepare and approve multiple actions; invalidate approval after provider, model, cost, egress, context, sensitivity, base, or write-set changes; prevent launch without approval; convert legacy preferences into unapproved intent; enforce policy precedence; block or redact credential-like values before any adapter call and report the sanitized context digest; prevent duplicate dispatch after uncertain resume; reject explicit-provider substitution; warn and require approval for same-family opinion; continue best-effort failure visibly; pause required failure until a durable override; prevent external results from setting gate fields.

**Verification:** A hermetic adapter fixture completes the full requested-to-consumed lifecycle, and every negative path leaves a truthful terminal or paused state.

### U4. Implement supervised adapters and disposable-clone containment

Provide real Claude CLI, `agy`, and HTTP execution behind one runtime-owned adapter factory.

**Goal:** Add adapter selection, generic CLI invocation metadata, supervised Claude and `agy` runners, disposable-clone patch capture, process cleanup, and reuse of the generic HTTP bridge.

**Requirements:** R4-R5, R7-R10, R18.

**Dependencies:** U3.

**Files:** `plugins/saga/scripts/external_action_adapters.py`; `plugins/saga/scripts/external_action_workspace.py`; `plugins/saga/scripts/claude_delegate.py`; `plugins/saga/scripts/agy_delegate.py`; `plugins/saga/scripts/engine_dispatch.py`; `plugins/saga/scripts/engine_bridge_http.py`; `plugins/saga/references/engine-registry.yaml`; `tests/test_external_action_adapters.py`; `tests/test_external_action_workspace.py`; `tests/test_claude_delegate.py`; `tests/test_agy_delegate.py`; `tests/test_engine_bridge_http.py`.

**Approach:** Make the runtime adapter factory select by registry transport and invocation recipe. Adapt the sibling delegate supervision pattern for timeouts, no-output detection, signal cleanup, terminal result writing, local cloning, remote removal, base SHA capture, binary patch preservation, and write-set scoring; do not copy Claude host paths or Codex-delegate identity. Keep HTTP artifact-only and pass all results through existing receipt validation.

**Patterns to follow:** `plugins/saga/scripts/engine_bridge_http.py:134`; `plugins/saga/scripts/engine_dispatch.py:1494`; sibling `plugins/agy/scripts/agy_delegate.py:654`; sibling `plugins/codex/scripts/codex_delegate.py:1267` for containment mechanics only.

**Test scenarios:** Run successful Claude and `agy` fixture processes; handle binary-not-found, authentication failure, timeout, no output, nonzero exit, SIGTERM, and incomplete cleanup; preserve a valid in-scope patch; reject write-set escape; prove live-tree nonmutation; record dirty overlap and pinned base; reject a receipt whose provider, model, invocation, or output attestation differs; route two OpenAI-compatible providers through the same HTTP adapter; keep authorization values out of output and evidence.

**Verification:** Each adapter produces a terminal, schema-valid, attributable result or a precise unusable state, and CLI patch tests leave the live worktree unchanged.

### U5. Complete provider onboarding and policy persistence

Make new OpenAI-compatible routes safely selectable without provider-specific execution branches.

**Goal:** Add validated repo-local overlays, bounded smoke-before-apply, secret-reference handling, optimistic concurrency, canonical promotion separation, and policy persistence.

**Requirements:** R3, R4, R6-R7, R13.

**Dependencies:** U3. May proceed in parallel with U4 after the shared adapter protocol is stable.

**Files:** `plugins/saga/scripts/engine_onboarding.py`; `plugins/saga/scripts/engine_registry.py`; `plugins/saga/scripts/engine_registry_overlay.py`; `plugins/saga/scripts/engine_registry_cli.py`; `plugins/saga/scripts/engine_promotion.py`; `plugins/saga/scripts/external_action_policy.py`; `plugins/saga/references/engine-registry.yaml`; `tests/test_engine_onboarding.py`; `tests/test_engine_registry_overlay.py`; `tests/test_engine_registry_conformance.py`; `tests/test_engine_promotion.py`.

**Approach:** Preserve dry-run as default, validate closed registry metadata, resolve only environment-variable names, run a bounded non-sensitive smoke through the generic HTTP adapter, and apply with an expected overlay digest. Compose overlays additively and halt on canonical or overlay duplicate keys; make canonical promotion emit a reviewed source diff and never treat overlay success as shipped-registry proof.

**Patterns to follow:** `plugins/saga/scripts/engine_onboarding.py:52`; `plugins/saga/scripts/engine_registry.py:379`; existing onboarding and promotion tests.

**Test scenarios:** Preview without mutation; reject missing key reference, unsupported protocol, unsafe URL, invalid capability claims, failed smoke, secret value input, stale overlay digest, and canonical or overlay duplicate keys; apply idempotently after successful smoke; select the new provider in a later action and read back its receipt; prove canonical registry remains unchanged until promotion; preserve concurrent unrelated overlay rows; remove the overlay row only after identical canonical promotion is readable.

**Verification:** A fixture provider moves from preview through smoke and overlay apply to a receipted action without provider-specific code or secret exposure.

### U6. Integrate all six lifecycle stages

Replace disconnected offers with one prepare-approve-execute-consume contract at each named consumption point.

**Goal:** Wire default bundles, operator prompts, status cards, requiredness, artifacts, typed opinions, and consumption into `/ideate`, `/brainstorm`, `/plan`, `/work`, `/doc-review`, and `/code-review` together.

**Requirements:** R1-R4, R9-R14, R18.

**Dependencies:** U4, U5.

**Files:** `plugins/saga/skills/ideate/SKILL.md`; `plugins/saga/skills/brainstorm/SKILL.md`; `plugins/saga/skills/plan/SKILL.md`; `plugins/saga/skills/work/SKILL.md`; `plugins/saga/skills/doc-review/SKILL.md`; `plugins/saga/skills/code-review/SKILL.md`; `plugins/saga/references/external-action-defaults.yaml`; `plugins/saga/scripts/reconcile.py`; `tests/test_engine_offer.py`; `tests/test_external_action_lifecycle_contract.py`; `tests/test_reconcile.py`.

**Approach:** Parameterize the six stage contracts around one runtime vocabulary. Preserve each stage's reviewed default action bundle and named consumption point; offload artifacts remain inert until accepted, second opinions enter typed reconciliation, status cards are always rendered, and no stage converts preference, timeout, or provider absence into external evidence.

**Patterns to follow:** Current Engine Offer sections in the six skills; `plugins/saga/scripts/reconcile.py`; `plugins/verified-workflows/scripts/advisory_reconcile.py` for non-authoritative typed convergence.

**Test scenarios:** Assert all six skills invoke the common runtime and expose the correct defaults; run offload and second-opinion fixtures through each stage; remove or change an action before approval; consume accepted evidence and reject unused evidence; halt an unavailable panel before partial dispatch; continue best-effort failure; pause and override required failure; ensure the plan stage is covered alongside the five currently mapped offer stages.

**Verification:** A parameterized contract test proves every stage prepares, executes, renders, adjudicates, and consumes through the shared runtime with no legacy offer-only path.

### U7. Prove the vertical runtime and negative matrix

Join stores, adapters, stages, receipts, reconciliation, and promotion evidence under hermetic tests.

**Goal:** Add complete cross-layer proof for action lifecycles, failure behavior, credential boundaries, containment, replay, onboarding, and promotion metrics.

**Requirements:** R1-R16, R18.

**Dependencies:** U6.

**Files:** `tests/test_external_action_integration.py`; `tests/test_external_action_release_matrix.py`; `tests/test_external_action_workspace.py`; `tests/test_engine_dispatch_attestation.py`; `tests/test_engine_onboarding.py`; `tests/test_engine_promotion.py`; `tests/test_reconcile.py`; `tests/test_bridge_lie_detector.py`; `tests/test_bridge_receipt_drift.py`.

**Approach:** Use fake CLI binaries, a local HTTP fixture, isolated repositories, and fresh processes to test the same public runtime API the skills call. Define and version qualifying run, major rewrite, provider distribution, integrity failure, containment failure, and rollback-drill measurements before adding new promotion evidence.

**Patterns to follow:** Existing receipt lie-detector, drift, reconciliation corruption, onboarding, and promotion suites; do not count injected fake runners as production wiring proof.

**Test scenarios:** Cover every R55 negative case plus approval invalidation, no approval, claim-store failure, crash after claim, crash after launch, duplicate resume, corrupted transition, receipt substitution, malformed typed finding, same-family warning, unavailable explicit provider, secret-like payload, dirty-base conflict, write-set escape, status projection recovery, and root rejection. Prove that no external output changes a hard gate and that no failed action is represented as consumed.

**Verification:** The hermetic matrix passes in normal CI and demonstrates every state transition and failure outcome without external credentials.

### U8. Run attended live proof and cut over the release

Prove the named providers and lifecycle stages in a controlled real run, then change release metadata last.

**Goal:** Execute the real Claude CLI, `agy`, Ollama Cloud, six-stage, onboarding, requiredness, status-card, and rollback matrix; complete port evidence, isolated install, fresh-session readback, and metadata cutover.

**Requirements:** R6, R13-R18.

**Dependencies:** U7.

**Files:** `plugins/saga/scripts/external_action_release_matrix.py`; `docs/validation/codex-external-action-runtime-proof.json`; `docs/validation/codex-external-action-runtime-proof.schema.json`; `docs/portability/manifests/2026-07-11-external-advisory-execution.json`; `docs/portability/matrix.md`; `plugins/saga/.codex-plugin/plugin.json`; `.agents/plugins/marketplace.json`; `README.md`; `tests/test_external_action_release_matrix.py`; `scripts/validate_codex_plugins.py`.

**Approach:** Require an attended command and explicit provider credentials, use bounded non-secret fixtures, sanitize receipts, run real providers before changing version metadata, verify the installed plugin in isolation and a fresh Codex session, and preserve rollback material outside committed evidence. Fail cutover if any provider, stage, receipt, negative case, or fresh-session check is unproved.

**Patterns to follow:** `docs/validation/codex-plugin-modernization-cutover.json`; `docs/validation/verified-workflows-runtime-proof.json`; the port runbook cutover gate.

**Test scenarios:** Complete at least one real Claude action, one real `agy` action, and one real Ollama Cloud action; cover all six stages, both intents, best-effort and required behavior, CLI patch and HTTP artifact results, cross-family and warned same-family routing, overlay onboarding and receipt readback, operator rejection, and rollback drill. Reject missing authentication, unexpected spend or egress metadata, secret leakage, invalid sanitized evidence, installed-version mismatch, or a fresh session that falls back to offer-only behavior.

**Verification:** The schema-valid, content-addressed validation artifact references valid action records and receipts for the complete matrix, the port manifest reaches cutover-ready, isolated and fresh-session checks pass, and release metadata is internally consistent.

## Workflow Structure

| step_id | depends_on | barrier | role_id | role_kind | independence | execution_class | runtime_agent_name | vehicle | mutation | required_evidence | role_lens_sha256 | profile_sha256 | expected_model | expected_effort | validator_required | validator_disabled | deterministic_contract_sha256 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| u1 | - | - | root | root | n/a | - | - | root | declared-write | u1.port-classification | - | - | - | - | n/a | n/a | - |
| u2 | u1 | - | root | root | n/a | - | - | root | declared-write | u2.action-store-tests | - | - | - | - | n/a | n/a | - |
| u3 | u2 | - | root | root | n/a | - | - | root | declared-write | u3.runtime-integration-tests | - | - | - | - | n/a | n/a | - |
| u4 | u3 | - | root | root | n/a | - | - | root | declared-write | u4.adapter-containment-tests | - | - | - | - | n/a | n/a | - |
| u5 | u3 | - | root | root | n/a | - | - | root | declared-write | u5.onboarding-overlay-tests | - | - | - | - | n/a | n/a | - |
| u6 | u4,u5 | - | root | root | n/a | - | - | root | declared-write | u6.lifecycle-contract-tests | - | - | - | - | n/a | n/a | - |
| u7 | u6 | - | root | root | n/a | - | - | root | declared-write | u7.hermetic-negative-matrix | - | - | - | - | n/a | n/a | - |
| u8 | u7 | - | root | root | n/a | - | - | root | declared-write | u8.live-proof,u8.cutover-proof | - | - | - | - | n/a | n/a | - |
| review-architecture | u8 | final-quality | architecture-reviewer | agent-lens | preferred | review-high | review_high | auto | none | review.architecture | e48b37cea0b26bf39cae4d6611b4219e907d52d284ba6b9489b523a4b16c835f | 42e86e00e054281b0a79e4b3b9b544c04a31eb2fd6b53c0489adc42ea639c9a8 | gpt-5.6-sol | high | n/a | n/a | - |
| review-security | u8 | final-quality | security-reviewer | agent-lens | preferred | review-high | review_high | auto | none | review.security | bf5bc1b66c0ee3d06071976b659c522c23057c56de5f6cc010556b2653c86980 | 42e86e00e054281b0a79e4b3b9b544c04a31eb2fd6b53c0489adc42ea639c9a8 | gpt-5.6-sol | high | n/a | n/a | - |
| review-adversarial | u8 | final-quality | devils-advocate-reviewer | agent-lens | preferred | review-high | review_high | auto | none | review.adversarial | 129f6dca0702ffcd4be7f9e5d0939e8e6806788846ba4058044c931883ef0e63 | 42e86e00e054281b0a79e4b3b9b544c04a31eb2fd6b53c0489adc42ea639c9a8 | gpt-5.6-sol | high | n/a | n/a | - |
| review-testing | u8 | final-quality | testing-reviewer | agent-lens | preferred | review-high | review_high | auto | none | review.testing | a867575e24c86b0573485d1d8bbd81514af3654d544342677b85f4bed0d9af63 | 42e86e00e054281b0a79e4b3b9b544c04a31eb2fd6b53c0489adc42ea639c9a8 | gpt-5.6-sol | high | n/a | n/a | - |
| validate-security | u8 | final-quality | security-scanner | agent-lens | preferred | scan-low | scan_low | auto | none | validate.security | 54c03db73fa75650e95c93ea642a38fdcc342f57315c3b8bf2d96b2431e63cb9 | bbb5cb1c6d3fc28ac66d61bb2794ed1824b814913f42079a568cdfa2b7cdfb50 | gpt-5.6-luna | low | true | false | - |
| validate-smoke | u8 | final-quality | smoke-tester | agent-lens | preferred | test-medium | test_medium | auto | none | validate.smoke | 30004d950c02721615f9abf944207abb3f288d275d1297802e91d97ce73a476a | 6d69bb4d5e477574ce186a353a3d2fcc7f8ab6b1f014b93aebb05084aecccc1b | gpt-5.6-terra | medium | true | false | - |
| finalize | review-architecture,review-security,review-adversarial,review-testing,validate-security,validate-smoke | - | root | root | n/a | - | - | root | none | workflow.final-gate | - | - | - | - | n/a | n/a | - |

## Workflow Execution Notes

Verified Workflows coordinates root-owned implementation with independent, evidence-only review and validation. The table uses the exact machine contract and binds the current committed role lenses and execution profiles; production dispatch must rebind against installed profile bytes and halt on digest drift.

Root executes U1-U8 sequentially except U4 and U5, which may proceed concurrently after U3 when their declared write sets do not overlap. Agent-lens rows run only after U8 and are evidence-only; they never own implementation files, credentials, Git, integration, live provider calls, or completion.

The `final-quality` barrier requires all three base reviewers, the triggered testing reviewer, and both required validators before the no-mutation `finalize` step. The root rejects completion when evidence is missing, a validator fails, a P0/P1 finding remains, the action store or receipt chain is contradictory, profile or role digests drift, or live evidence cannot be tied to the approved action; the runtime under construction never validates its own gate authority.

## Risks and Dependencies

The highest risks are false execution claims, replay duplication, credential leakage, subprocess escape, and a release matrix that passes only against fixtures.

| risk | impact | mitigation |
|---|---|---|
| Existing helpers are mistaken for production wiring | The feature repeats the current no-op failure | U3 and U6 require a public runtime call path and six-stage vertical tests. |
| Approval and launch state diverge after interruption | Duplicate cost, conflicting evidence, or unapproved egress | Immutable approval fingerprints, claim-before-launch, append-only transitions, and fail-closed resume. |
| CLI process or patch escapes containment | Live-tree or out-of-scope mutation | Remote-stripped disposable clones, terminal cleanup, binary diff capture, write-set scoring, root-only apply. |
| Secret-like content reaches a provider | Credential disclosure | Central payload scanning before adapter selection and negative fixtures at the dispatch boundary. |
| Remote receipt overstates provider identity | Misleading verification claim | Record configured route and observed response identity within the adapter trust model only. |
| Local overlays drift from canonical registry | Non-reproducible routing | Digest-bound overlays, status disclosure, and separate reviewed promotion. |
| Credentialed proof becomes flaky default CI | Unreliable development gate and unintended cost | Hermetic CI plus explicit attended release harness with provider-account controls. |
| Upstream Claude changes during implementation | Unbounded port scope | Frozen manifest window and explicit amendment requirement. |

Dependencies are authenticated Claude CLI and `agy` installations, an operator-managed Ollama Cloud key reference, Git available for disposable clones and common-directory state, and the existing registry, resolver, bridge, receipt, manifest, ledger, reconciliation, and Verified Workflows substrates.

## Alternatives Considered

The chosen design favors one explicit runtime and evidence model over smaller but misleading changes.

| alternative | decision |
|---|---|
| Extend `engine_offer.py` to call one provider directly | Rejected because it leaves six stage semantics, replay, requiredness, and consumption fragmented. |
| Store lifecycle state only in engine manifests | Rejected because manifests do not represent approval, requiredness, adjudication, or consumption. |
| Store lifecycle state only in the run ledger | Rejected because an append-only fact stream alone lacks per-action transition validation and projection contracts. |
| Copy Claude `second_opinion.py` and delegates | Rejected because host assumptions and active-source classifications differ; semantic adaptation is required. |
| Build sparse read-scoped workspaces | Rejected for v1 as disproportionate complexity under the operator's existing provider trust model. |
| Let normal CI call paid providers | Rejected because credentials, spend, and external availability make it nondeterministic. |
| Activate only review stages first | Rejected because the requirements explicitly make the six-stage round trip one adaptation scope. |

## Success Metrics

The release is successful only when behavior and evidence agree.

- All six lifecycle stages complete at least one approved external action through the shared runtime and render a durable status card.
- Real Claude CLI, `agy`, and Ollama Cloud actions each produce valid, attributable receipts and explicit Codex adjudication.
- The full R55 negative matrix produces no synthetic success, silent substitution, duplicate dispatch, credential exposure, live-tree mutation, or external gate authority.
- Normal CI remains fully hermetic; the attended live matrix is separately reproducible and sanitizes all committed evidence.
- Direct mutation remains disabled while qualifying-run evidence is collected under stable versioned definitions.
- Port classification, per-unit evidence, isolated install, fresh-session readback, cutover, and rollback gates all pass before metadata release.

## Scope Boundaries

The plan delivers the full v1 adaptation but does not widen provider or mutation authority.

**In scope:** shared action runtime; durable action state; Claude CLI, `agy`, and OpenAI-compatible HTTP; overlay onboarding; all six stages; typed reconciliation; status cards; hermetic and live proof; port and release evidence.

**Out of scope:** direct Anthropic API; non-OpenAI-compatible generic protocols; provider-side spend enforcement; live-tree mutation by any external provider; external gate authority; native Codex children masquerading as external opinions; additional lifecycle stages.

**Deferred to follow-up work:** reconsider direct mutation only after the requirements' measured promotion gate is satisfied; add separately reviewed protocol adapters; promote useful operator-local provider rows into the canonical registry; migrate from the v1 store only through a versioned schema change.

## Sources and Research

The plan is grounded in current Codex seams, reviewed requirements, port controls, and sibling implementation patterns.

- `docs/brainstorms/2026-07-11-codex-external-advisory-execution-contract-requirements.md:11`
- `docs/reviews/2026-07-11-codex-external-advisory-execution-contract-requirements-review.md`
- `docs/investigations/external-second-opinion-preference-noop-2026-07-11.md:15`
- `docs/portability/claude-to-codex-plugin-port-runbook.md:14`
- `docs/portability/manifests/2026-07-10-saga-07517.json`
- `plugins/saga/scripts/engine_registry.py:379`
- `plugins/saga/scripts/engine_resolver.py:334`
- `plugins/saga/scripts/engine_dispatch.py:236`
- `plugins/saga/scripts/engine_bridge_http.py:134`
- `plugins/saga/scripts/manifest_store.py:83`
- `plugins/saga/scripts/run_ledger.py:54`
- `plugins/saga/scripts/engine_onboarding.py:52`
- `tests/test_engine_offer.py:18`
- `tests/test_engine_bridge_http.py:193`
- `tests/test_engine_dispatch_attestation.py:109`
- `tests/test_reconcile.py:115`
- `../infiquetra-claude-plugins/plugins/saga/scripts/second_opinion.py:843`
- `../infiquetra-claude-plugins/plugins/agy/scripts/agy_delegate.py:654`
- `../infiquetra-claude-plugins/plugins/codex/scripts/codex_delegate.py:1267`
