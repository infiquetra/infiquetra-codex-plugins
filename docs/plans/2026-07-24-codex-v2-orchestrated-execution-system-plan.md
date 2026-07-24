---
title: Codex V2 Orchestrated Execution System Plan
type: feature
status: active
date: 2026-07-24
origin: docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md
deepened: 2026-07-24
reviewed: 2026-07-24
---

# Codex V2 Orchestrated Execution System Plan

## Summary

Replace the current Verified Workflows evidence-chain runtime with a small Codex V2 orchestration kernel while keeping the existing `verified-workflows` plugin and skill identities. Saga remains the lifecycle owner, the main Codex session remains the sole orchestrator and Git owner, Codex V2 owns the live agent tree, and the plugin owns one operator-editable workflow contract, typed result validation, risk-based assurance, and one concise run record.

The delivery destination is one reviewed repository release merged to `main` and installed into the current Codex environment. There is no nonproduction plugin environment. Repository proof, merge, current-Mac installation, fresh-session V2 proof, and rollback are separate gates.

## Problem Frame

The repository currently has an 18-column workflow parser, protected subject records, repository-wide snapshots, content-addressed intents, hook joins, receipt chains, mutation audits, and a 3,235-line workflow-record module. That machinery duplicates parts of the live agent system and makes an ordinary implementation workflow difficult to understand or override.

The active runtime is also pointed in the wrong direction for the target design. The project config enables multi-agent support but explicitly disables V2, active documentation tells operators to install a V1 model-catalog override, and the maintained profile set has five profiles rather than the required six because `work_high` does not exist. Static profile bytes and the existing diagnostic proof do not establish the profile, model, effort, provider, effective permission, restoration, Luna, or Ultra behavior required for cutover.

Codex 0.145.0 supplies the V2 substrate this design needs. The repository should use that substrate directly rather than keep a plugin-owned scheduler. The migration must nevertheless preserve all 25 logical role lenses, the reviewer scoring contract, Saga lifecycle compatibility, external-action approval and egress controls, historical V1 evidence, and a tested path back to the pre-cutover repository and host state.

## Requirements

These 12 plan requirements preserve every origin requirement R1-R51 and add the repository's classification and delivery obligations.

- R1. The main Codex session is the sole workflow orchestrator and owner of approval binding, dependency release, integration, Git operations, remediation, merge, installation, and completion. This carries origin R1-R7.
- R2. Every plan intended for delegated execution contains one concise, operator-editable workflow contract covering graph, role, profile, exact model and effort, bounded context, write ownership, blocking checks, reviewer gates, fallback conditions, and external actions. Material changes require renewed approval. This carries origin R2-R7 and R30-R31.
- R3. Preserve all 25 logical roles and provide exactly six authoritative child profiles: `review_max`, `review_high`, `work_high`, `test_medium`, `scan_low`, and `monitor_low`, with the mappings and permission ceilings in origin R10. Select only risk-justified roles and the least expensive capable profile. This carries origin R8-R16.
- R4. Native V2 work uses explicit configured-agent selection, bounded or absent inherited history, declared descendant paths, non-overlapping write ownership, exact runtime identity and permission readback, typed terminal results, and root-only Git. Mismatch, undeclared delegation, out-of-scope writes, or worker Git mutation fails visibly. This carries origin R13-R24.
- R5. Connect Saga's existing external-action lifecycle to the same preview and run record. Approved tool-capable engines may write only non-overlapping declared paths; response-only engines remain artifact-only; all external results remain non-gating and secret-safe. This carries origin R25-R29.
- R6. Assurance is risk-based: targeted deterministic checks, at least one independent fresh-context reviewer, role-lens score validation, average at least 9.0, no applicable dimension below 7.0, unresolved hard-stop findings blocking, and no more than three remediation rounds per approved run. This carries origin R30-R37.
- R7. Codex V2 remains authoritative for live hierarchy, identity, liveness, messages, waits, interruption, and restoration. The plugin records only the approved contract, runtime readback, typed outcomes, checks, findings, remediation count, and root decision in one concise durable record. This carries origin R38-R43.
- R8. Remove active V1-only configuration, model-catalog tooling, instructions, tests, and execution fallbacks while retaining historical requirements, plans, proofs, and classifications as non-current lineage. This carries origin R44-R45.
- R9. A live V2 release exercise using the current authenticated Codex identity and project configuration must prove every capability in origin R46, test Luna as a complete leaf or remap the two low-cost profile IDs to Terra/low, and prove Ultra is explicit and root-only. Missing proof blocks merge and installation. This carries origin R46-R48.
- R10. After merge, cut over the current Mac's project and user configuration, managed profiles, plugins, and model catalog; verify a fresh session; and exercise rollback from post-migration state to the pre-cutover repository ref and host configuration. All source, metadata, docs, snapshots, probes, and tests must agree. This carries origin R49-R51.
- R11. Load and pass the mandatory Claude-to-Codex classification gate before altering frozen source-derived role behavior. Treat this work as a Codex-native redesign against the existing frozen lineage rather than silently refreshing Claude source refs.
- R12. Deliver through the selected `inline` backend to a reviewed PR, successful CI, merge to `main`, supported plugin installation, managed-profile synchronization, and fresh-session installed-state readback. No installed cache file is edited as maintained source.

## Key Technical Decisions

The target has one plan contract, one native V2 execution tree, one private run record, and one root decision.

- KTD1. Keep the public product identity and replace the kernel. `verified-workflows:run`, `verified-workflows:select-agent`, `verified-workflows:review-workflow`, Saga's `verified-workflow` mode, and the 25 role IDs remain stable. The old evidence-chain implementation is deleted from the active path rather than shortened or wrapped, and no parallel V2 plugin is introduced.
- KTD2. Use Codex V2 as the live scheduler. The plugin compiles an approved plan contract into launch specifications and validates returned results; it does not persist a second executable DAG, replay V2 events, or infer liveness from plugin records.
- KTD3. Replace the current 18-column structure with three compact canonical tables. Assignments use `id`, `depends`, `parent`, `role`, `profile`, `model`, `effort`, `context`, `writes`, `completion`, and ordered `fallback`; checks use `id`, `owner`, `after`, `command-or-proof`, `blocking`, and `failure`; external actions use `id`, `purpose`, `provider`, `model`, `egress`, `context`, `sensitivity`, `cost`, `writes-or-artifact`, `requiredness`, and `authority`, whose only accepted value is `non-gating`. Parent is `root`, another assignment ID, or the bootstrap-only `fresh-root:<id>`. Root-owned bootstrap rows reserve the displayed root role labels and `profile=root`; delegated rows require a role-registry ID and one of the six managed profile IDs. Assignment context is exactly `root`, `none`, or `turns:<positive-int>`; external context is `none` or a comma-delimited allowlist of canonical repository-relative paths. Fallback is `none` or an ordered comma-delimited list of `profile@condition` entries. The approved plan revision plus one canonical digest over all three tables binds the run.
- KTD4. Use underscore profile IDs everywhere new state is written. Roles map directly to one or more of the six profile IDs. Historical hyphenated execution-class and V1 receipt values remain readable only in historical artifacts; they are not accepted as new executable contracts.
- KTD5. Runtime authority comes from V2 launch and turn-context readback, not from TOML bytes, prompt claims, custom receipt hooks, or the old model-catalog projection. The root validates profile or agent type, model, effort, provider backend, effective permission, and canonical agent path before accepting strict work. If 0.145.0 cannot expose one of those fields, cutover stops and the accepted V2 path does not retain the old hook as substitute authority.
- KTD6. Store one compact JSON run record under the existing owner-controlled user state root `~/.codex/verified-workflows/state/<repo>/workflow-runs/<run-id>.json`, guarded by the existing repository-identity marker, and reference it from the Saga tick. A git-ignored `.codex/verified-workflows/` root is a tested fallback only when the active sandbox can write it. Updates replace the bounded current record atomically; they do not create a content-addressed chain, copy raw model output, snapshot the workspace, or duplicate the V2 event stream.
- KTD7. Validate a small closed typed-result schema at the root. Common fields cover assignment, attempt, canonical path, role, profile, terminal status, summary, changed paths or no-change, checks, findings, and residual risk. Reviewer extensions carry scored mandates, typed exclusions, arithmetic, typed findings, and hard-stop flags.
- KTD8. Reuse Saga's external-action policy, preview, approval fingerprint, egress sanitization, provider adapters, status, and root adjudication. A non-empty write set is accepted only when the engine registry marks the route `write_capable` and the selected adapter supports bounded patch capture and shared-workspace import; caller input cannot promote a response-only route. The provider remains contained, the root adapter rejects paths outside the approved set and Git metadata, then imports the validated patch into the shared workspace only if the approval-bound base and dirty-overlap preconditions still match. Do not create a second external control plane inside Verified Workflows.
- KTD9. Replace the old gate evaluator with a root-owned decision reducer over the approved contract, V2 identity readback, typed results, deterministic check outcomes, adopted root findings, and remediation count. Messages and raw external output remain incapable of releasing a dependency or gate.
- KTD10. Keep V2-only normal operation and rollback as separate concepts. The source tree has no active V1 fallback after cutover. Rollback restores the pre-cutover repository ref, installed versions of `fleet-core`, `saga`, and `verified-workflows`, project and user config, managed profiles, and model-catalog state as an attended operator action.
- KTD11. Bootstrap this self-modifying change inline. The implementation root performs all maintained-source writes and Git operations. Because origin R32 prohibits the implementer and its descendants from reviewing, each authority-bearing reviewer runs under a separately started, fresh V2 review-root session that reuses the current Codex authentication and configuration; that review root launches the exact named review profile with no inherited implementation turns and returns its typed result to the implementation root for validation. Bounded descendants of the implementation root may explore or run non-gating checks only.
- KTD12. Release `fleet-core`, `saga`, and `verified-workflows` as one aligned change because the V1 catalog, lifecycle contract, external-action seam, profiles, and workflow kernel cross those package boundaries. After source behavior and the Luna decision pass a live current-session proof against the project-discovered candidate profiles, mint one candidate version set and run the full release proof and reviewers from fresh sessions using the same authenticated Codex identity. Deterministic source-to-package checks bind the reviewed source to the release, and merged installed bytes are proven during the attended install/rollback/reapply phase. Any later behavior, profile, config, or runtime-proof change reruns the affected reviewers and the complete V2 matrix before merge.
- KTD13. Use a lightweight root-owned workspace and Git audit rather than full snapshots. Before each writable wave, capture `HEAD`, symbolic branch, the index SHA-256, a bounded digest of worktree-local refs/config/hooks, and `git status --porcelain=v2 --untracked-files=all`; after each contribution, recompute them and derive changed paths from root-run Git status/diff plus untracked entries. Concurrent writable agents are allowed only when V2 supplies per-agent mutation attribution; otherwise writable attempts run sequentially with the root quiescent. Any path outside the declared owner, observed worker Git command, or Git-control divergence hard-fails the assignment and pauses integration.
- KTD14. Repository editing, GitHub merge, and current-Codex deployment are separate authority checks. U8 may begin only in a session that can write tracked `.codex` files and Git metadata, reach GitHub, and mutate the current user's Codex plugin, profile, config, and model-catalog surfaces through supported commands; otherwise the run pauses and resumes in an explicitly authorized session without weakening a gate.

## Workflow Contract

This bootstrap contract is the operator-editable graph for implementing, reviewing, merging, and installing this release.

**Backend:** `inline`.

**Destination:** reviewed PR, merge to `main`, then supported installation and V2 cutover in the current Codex environment.

**Root model policy:** explicit Sol/max for orchestration and integration. Ultra is exercised only in the root-only proof and is not required for implementation.

| id | depends | parent | role | profile | model | effort | context | writes | completion | fallback |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | - | root | root orchestrator | root | `gpt-5.6-sol` | max | root | `unit:U1` | classification and capability baseline pass | none |
| profiles | baseline | root | root implementer | root | `gpt-5.6-sol` | max | root | `unit:U2` | six-profile and 25-role tests pass | none |
| contract | profiles | root | root implementer | root | `gpt-5.6-sol` | max | root | `unit:U3` | contract compiler and approval tests pass | none |
| native-runtime | contract | root | root implementer | root | `gpt-5.6-sol` | max | root | `unit:U4` | native readback, audit, typed-result, and run-record tests pass | none |
| assurance | native-runtime | root | root implementer | root | `gpt-5.6-sol` | max | root | `unit:U5` | gate and three-round remediation tests pass | none |
| external | contract, native-runtime | root | root implementer | root | `gpt-5.6-sol` | max | root | `unit:U6` | external policy, egress, patch-import, audit, and non-gating tests pass | none |
| migration | assurance, external | root | root implementer | root | `gpt-5.6-sol` | max | root | `unit:U7` | no active V1 path; package and generated-doc validation pass | none |
| runtime-proof | migration | root | root orchestrator | root | `gpt-5.6-sol` | max | root | `unit:U8-proof` | full R46 matrix, Luna decision, candidate versions, source/package binding, and Ultra root-only proof pass | none |
| testing-review | runtime-proof | `fresh-root:testing-review` | `testing-reviewer` | `review_high` | `gpt-5.6-sol` | high | none | none | mandate average >=9, each >=7, no hard stop | `review_max@terminal-failure-or-ambiguity` |
| architecture-review | runtime-proof | `fresh-root:architecture-review` | `architecture-reviewer` | `review_high` | `gpt-5.6-sol` | high | none | none | mandate average >=9, each >=7, no hard stop | `review_max@terminal-failure-or-ambiguity` |
| security-review | runtime-proof | `fresh-root:security-review` | `security-reviewer` | `review_high` | `gpt-5.6-sol` | high | none | none | mandate average >=9, each >=7, no hard stop | `review_max@terminal-failure-or-ambiguity` |
| release | testing-review, architecture-review, security-review | root | root orchestrator | root | `gpt-5.6-sol` | max | root | `unit:U8-release` | final diff allowlist, checks, PR CI, merge, install readback, fresh-session proof, rollback drill, and V2 reapply pass | none |

`unit:U1` through `unit:U7` are bootstrap-only root write bindings resolved to the exact paths in the matching unit's **Files** field; the root executes them sequentially and does not delegate those writes. `unit:U8-proof` is limited to the U8 candidate version and proof artifacts before review, while `unit:U8-release` is limited to U8's closed post-review allowlist, delivery metadata, supported host mutations, and rollback/reapply evidence. Each `fresh-root:*` review is a separately started V2 root with no implementation history, so the reviewer is outside the implementation root's descendant tree while the implementation root remains the final orchestrator.

The reviewer fallback changes only cost and effort; role, read-only permission, no-egress boundary, packet, gate, and write set remain unchanged. `scan_low` and `monitor_low` are not assignment fallbacks here: if Luna fails the complete V2 leaf proof, those same profile IDs are changed to Terra/low before candidate versioning, then the full matrix runs against the remapped project profiles.

### Blocking Checks

Every row is part of the approved contract digest; changing a command, owner, order, or blocking value requires an updated preview.

| id | owner | after | command-or-proof | blocking | failure |
|---|---|---|---|---|---|
| classification | root | baseline | `python3 scripts/port_contract.py validate --manifest docs/portability/ports/2026-07-24-codex-v2-orchestration.json --stage classification` | yes | stop before source-derived behavior changes |
| focused | root | migration | focused profile, role, contract, result, audit, gate, external-action, capability, and migration pytest modules named by U1-U7 | yes | fix and rerun affected unit |
| plugin-validation | root | migration | `python3 scripts/validate_codex_plugins.py` | yes | fix source/inventory drift |
| generated-facts | root | migration | `python3 scripts/build_saga_docs_facts.py --check` | yes | regenerate from canonical inputs |
| generated-assets | root | migration | `python3 scripts/render_saga_docs_assets.py --check` | yes | regenerate from canonical inputs |
| full-pytest | root | migration | `python3 -m pytest -q` | yes | fix or document an environment blocker; no merge |
| v2-runtime | root | runtime-proof | `python3 scripts/prove_verified_workflows_runtime.py --live` plus the U8 operation matrix, using the current authenticated Codex identity and project-discovered profiles | yes | block candidate review and cutover |
| reviewer-assurance | fresh review roots | runtime-proof | all three typed reviewer results satisfy score, exclusion, and hard-stop policy | yes | remediate and revalidate within the shared three-round cap |
| delivery | root | release | PR checks pass; merge SHA is on `origin/main`; installed plugin/profile/config readback matches merged source | yes | block merge or completion at the failing boundary |
| rollback | root | release | fresh pre-cutover package restores repository ref, installed plugin versions, project/user config, profiles, and model catalog; merged V2 is then re-applied | yes | restore the known safe state and stop |

### External Actions

`External actions: []` is the exact approved value for this implementation run.

Adding an external review, offload, provider route, transmitted context, or external write set is a material workflow amendment and requires an updated preview using KTD3's external-action columns. The completed Claude Fable/xhigh requirements and plan reviews are upstream advisory evidence, not implementation assignments or gates.

## Implementation Units

The eight units replace foundations before deletion, then prove and install one coherent candidate.

### U1. Freeze lineage and establish the V2 runtime contract

Capture the exact pre-change source, port-classification, Codex 0.145.0, project configuration, user configuration, managed profiles, local model catalog, and runtime capability baseline without changing the active host.

**Goal:** Make the migration reproducible and define the exact native V2 readback shape before implementation depends on it.

**Requirements:** R1, R4, R8, R9, R10, R11.

**Dependencies:** None.

**Files:** Modify `scripts/capture_codex_runtime_capabilities.py`, the capability schemas and `docs/validation/codex-runtime-capability-snapshot.json`, `scripts/prove_verified_workflows_runtime.py`, and their focused tests. Add `docs/portability/ports/2026-07-24-codex-v2-orchestration.json`, `docs/portability/ports/2026-07-24-codex-v2-orchestration-version-policy.json`, and the generated `docs/portability/classifications/2026-07-24-codex-v2-orchestration.md`; do not reopen or mutate `docs/portability/ports/2026-07-10-saga-07517.json`. Add only sanitized baseline evidence under `docs/validation/`; keep exact rollback bytes outside committed evidence.

**Approach:** Bootstrap the new manifest with `scripts/port_contract.py`, populate its preservation inventory and version-policy sidecar, and pass its classification stage before touching source-derived role behavior. Record this cycle as a Codex-native redesign that preserves frozen role mandates and does not move Claude refs. Use the current authenticated Codex identity and project configuration with Codex 0.145.0 to capture the actual V2 tool namespace and launch/turn-context fields; fresh `codex exec` sessions reuse that login and discover the candidate profiles from this repository. Extend the capability schema to express configured-agent selection, model, effort, provider, permissions, bounded context, nested delegation, messaging, wait/list, interruption, restoration, Luna, and Ultra root-only support. Capture the current project and user config, profile inventory, model-catalog pointer, installed plugin versions, and repository ref as lineage and sanitized baseline evidence. U1 does not authorize later rollback from stale bytes: U8 recaptures and verifies the private rollback package immediately before current-host mutation.

**Patterns to follow:** Use the closed snapshot/schema validation and current-session proof path in `scripts/prove_verified_workflows_runtime.py`, project `.codex/agents` discovery, and the mandatory classification sequence in `docs/portability/claude-to-codex-plugin-port-runbook.md`.

**Test scenarios:** Happy path: Codex 0.145.0 exposes V2 configured-agent launch and every required identity field. Drift: a missing field, model mismatch, effort mismatch, provider switch, or effective-permission mismatch fails the proof. Classification: moved source refs, unclassified preserved behavior, or stale capability digests block source work. Rollback capture: private material can restore exact pre-state while committed evidence contains no absolute paths, credentials, or raw config secrets.

**Verification:** The classification gate and capability schema tests pass, and the current-session probe truthfully reports supported or blocking status without changing authentication or installed plugins.

### U2. Publish the six-profile and 25-role contract

Add `work_high`, align every role to authoritative underscore profile IDs, and reduce the role registry to logical mandates, selection triggers, boundaries, and typed result policy.

**Goal:** Separate durable role lenses from six exact execution profiles without carrying evidence-chain schemas or unconditional reviewer fan-out.

**Requirements:** R3, R4, R6.

**Dependencies:** U1.

**Files:** Modify `plugins/verified-workflows/config/role-registry.yaml`, relevant `plugins/verified-workflows/roles/*.md`, the maintained `plugins/verified-workflows/agents/*.toml` source, `plugins/verified-workflows/scripts/render_codex_agents.py`, `plugins/verified-workflows/scripts/sync_codex_agents.py`, and their profile, role, sync, and equivalence tests. Regenerate the tracked project-discovery copies under `.codex/agents/*.toml`; never hand-edit those copies.

**Approach:** Add `work_high.toml`; preserve every role ID and numbered mandate; map role defaults and allowed escalations directly to the six underscore profile IDs; encode profile model, effort, workspace, and external-access ceilings exactly once in the maintained agent source. Render byte-identical project-discovery copies through the existing renderer/sync path. Replace unconditional base-reviewer selection with one required independent reviewer plus risk-triggered additional roles. Replace protected evidence schemas with the common typed result and reviewer extension required by R7. Preserve source behavior digests or reclassify the exact prompt changes before accepting them.

**Patterns to follow:** Retain role boundaries and scoring at `plugins/verified-workflows/config/role-registry.yaml`, profile generation through `render_codex_agents.py`, and transactional profile installation through `sync_codex_agents.py`.

**Test scenarios:** Exactly 25 role IDs load and every selected profile ID exists. Exactly six profiles render with the required model, effort, workspace, and external access. `review_max` is Sol/max, `work_high` is Sol/high workspace-write, Ultra is rejected as a child profile, and a role cannot widen its boundary through escalation. Stale five-profile assumptions and hyphenated new execution classes fail.

**Verification:** Renderer check, isolated sync/recover tests, role registry tests, and profile parity tests pass with no current user-profile mutation.

### U3. Replace the evidence parser with a compact workflow compiler

Compile the approved plan's concise native and external tables into a validated launch envelope without creating subjects, snapshots, content-addressed intents, or a second task tree.

**Goal:** Make the workflow obvious to the operator and mechanically safe enough for root orchestration.

**Requirements:** R1, R2, R3, R4, R5, R7.

**Dependencies:** U2.

**Files:** Rewrite or replace `plugins/verified-workflows/scripts/workflow_dispatch.py` and `plugins/verified-workflows/scripts/workflow_feasibility.py`; update `plugins/verified-workflows/skills/review-workflow/SKILL.md`, `plugins/verified-workflows/skills/run/references/workflow-protocol.md`, and focused compiler/feasibility tests. The compiler accepts exactly the KTD3 assignment, check, and external-action column sets and emits one digest over all three canonical tables.

**Approach:** Parse only the compact contract defined in KTD3. Validate unique IDs, acyclic dependencies, `root`/assignment/`fresh-root:<id>` parent grammar, known roles and profiles, exact profile/model/effort agreement, assignment `root|none|turns:<positive-int>` context grammar, external path allowlists, non-overlapping concurrent write sets, root-only Git, declared descendants, blocking check and reviewer coverage, `profile@condition` fallback envelopes, fixed external `non-gating` authority, and complete external route fields. Permit `fresh-root:<id>` only for bootstrap review rows whose separately started review-root identity is returned and validated. Canonicalize all three approved tables and bind their one digest plus plan revision. Emit root-owned launch specifications; do not persist runtime status.

**Patterns to follow:** Preserve bounded input, identifier, cycle, and graph checks from the current `workflow_dispatch.py`, but remove role/profile SHA columns and all intent/receipt generation. Keep `review-workflow` read-only and make it validate this contract plus U1 capability truth.

**Test scenarios:** A valid mixed native/external graph compiles deterministically. Cycles, duplicate IDs, overlapping concurrent write paths, child Ultra, missing independent review, unbounded context, direct profile mismatch, undeclared descendants, missing external egress fields, widened fallbacks, or a material post-approval edit fail with one actionable error. Reordering non-semantic fields produces the same binding; changing authority or ownership does not.

**Verification:** Compiler and feasibility tests pass, and one fixture plan can be edited by an operator and rebound without any protected-record directory.

### U4. Make native V2 execution and typed results authoritative

Route approved assignments through configured V2 agents, verify exact runtime identity, and record canonical attempts and typed outcomes while leaving live execution state in Codex.

**Goal:** Replace V1 selection, custom hook attestation, and diagnostic receipts with native V2 launch/readback and root validation.

**Requirements:** R1, R4, R7, R9.

**Dependencies:** U3.

**Files:** Rewrite `plugins/verified-workflows/skills/run/SKILL.md`, `plugins/verified-workflows/skills/select-agent/SKILL.md`, and `plugins/verified-workflows/scripts/protocol_probe.py`. Add `plugins/verified-workflows/scripts/result_contract.py`, `plugins/verified-workflows/scripts/run_record.py`, and `plugins/verified-workflows/scripts/workspace_audit.py` with focused native-runtime, result-contract, run-record, and workspace-audit tests. Remove `plugins/verified-workflows/hooks/` from active execution; missing required V2 readback blocks cutover rather than retaining a hook fallback.

**Approach:** Launch each assignment with its exact configured profile and declared context bound. Validate V2 profile/type, model, effort, provider, effective permissions, and canonical agent path before strict work can count. Permit only declared nested paths. Treat messages as coordination only. Validate terminal results and changed paths, classify partial edits before retries, reconnect to the same path for same-attempt restoration, and require fresh canonical paths for retries, remediation, and revalidation. Apply KTD13's root-owned pre/post audit around every writable attempt. Atomically update one bounded run record at `~/.codex/verified-workflows/state/<repo>/workflow-runs/<run-id>.json`, using the existing repository identity marker; use the ignored project fallback only after a focused writable-root probe passes.

**Patterns to follow:** Use the owner-controlled Verified Workflows state root already resolved by `plugins/saga/scripts/verified_workflow_readiness.py`, Saga's tick as a pointer rather than a duplicate record, and Codex V2's returned identities. Preserve the root-only action list from the role registry and fail closed where current configured-profile bytes are merely requested intent.

**Test scenarios:** Exact configured-agent readback passes. Requested-only identity, wrong model/effort/provider/permission, malformed result, message-only completion, out-of-boundary changes, worker Git mutation, Git-control divergence, undeclared child, or reused terminal identity fails. Sequential writable attempts pass without V2 mutation attribution; concurrent writable attempts require proven per-agent attribution. Same-attempt resume preserves identity; retry after classified cleanup or carry-forward creates a fresh identity. The run record remains one concise object and does not copy V2 events.

**Verification:** Focused native runtime and result tests pass, and fresh live sessions using the current login produce accepted readback for a strict worker and a fresh-context reviewer.

### U5. Reduce assurance to checks, independent review, and bounded remediation

Replace receipt-chain adjudication with a small root-owned evaluator over typed results, deterministic checks, role scores, findings, and remediation state.

**Goal:** Enforce the requirements' meaningful gates without recreating the removed evidence bureaucracy.

**Requirements:** R6, R7.

**Dependencies:** U4.

**Files:** Rewrite `plugins/verified-workflows/scripts/gate_evaluator.py`, `plugins/verified-workflows/skills/run/references/gate-policy.md`, `validator-evidence-state.md`, and `worker-manifest.md`; replace their focused tests.

**Approach:** Validate checks selected in the approved contract, reviewer independence, mandate coverage, typed exclusions, score arithmetic, hard stops, adopted root findings, and one shared three-round remediation counter. Let the root release dependencies only from valid native results, check outcomes, or independently verified root findings. Keep final targeted checks after accepted changes and remediation are present.

**Patterns to follow:** Preserve the registry's 0-10 scoring, average 9.0, minimum dimension 7.0, static non-applicability, and role hard stops. Preserve severity-first review behavior, but make the score threshold blocking as required by the reviewed requirements.

**Test scenarios:** Passing scores and checks release the gate. Empty applicable dimensions, invalid exclusions, arithmetic mismatch, average below 9, a dimension below 7, unresolved P0/P1/security/role hard stop, missing independent reviewer, missing blocking check, or a fourth automatic remediation round fails. A remediated finding passes only after fresh focused revalidation.

**Verification:** Gate tests cover every threshold and hard stop, and no evaluator input references subjects, snapshots, content-addressed records, or hook receipts.

### U6. Join external actions to the shared control plane

Expose approved external work in the same plan preview and run record while retaining Saga's route approval, egress, provider, status, and adjudication authority.

**Goal:** Support bounded external assistance and shared-workspace edits without granting external results gate authority.

**Requirements:** R2, R5, R7.

**Dependencies:** U3, U4.

**Files:** Modify `plugins/saga/scripts/external_action_contract.py`, `plugins/saga/scripts/external_action_policy.py`, `plugins/saga/scripts/external_action_lifecycle.py`, `plugins/saga/scripts/external_action_runtime.py`, `plugins/saga/scripts/external_action_adapters.py`, `plugins/saga/scripts/external_action_workspace.py`, `plugins/saga/scripts/external_action_status.py`, `plugins/saga/scripts/engine_dispatch.py`, `plugins/saga/references/engine-registry.yaml`, `plugins/saga/references/dispatch-adapter-contract.md`, `plugins/verified-workflows/skills/run/references/external-engine-workers.md`, `plugins/verified-workflows/skills/run/references/delegation-safety.md`, and the corresponding contract, policy, lifecycle, runtime, adapter, workspace, status, dispatch, and workflow-integration tests.

**Approach:** Import approved external rows from the workflow contract into the existing action lifecycle and approval fingerprint. Accept a non-empty write set only when the registry route is `write_capable` and the adapter advertises bounded patch capture plus shared-workspace import; caller input cannot promote a response-only route. Keep the provider in the existing contained clone, validate its patch against approved paths and Git-metadata denial, then let the root-owned adapter apply that patch to the shared workspace only when approval-bound base, dirty-state, and overlap preconditions still match. Return route status and root-audited changed paths to the concise run record. Reject gate-shaped provider fields. Allow the root to adopt an independently verified external issue as an ordinary root-owned typed finding.

**Patterns to follow:** Reuse Saga's preparation, immutable request, approval fingerprint, egress sanitization, requiredness, provider adapters, status projection, and exact finding adjudication. Do not add a second registry or provider executor in Verified Workflows.

**Test scenarios:** An approved `write_capable` contained-provider patch inside one non-overlapping path is validated, imported by the root adapter, audited, and recorded. A false caller write-capability claim, missing adapter import support, changed base, dirty overlap, undeclared context, secret-bearing paths, widened egress, external Git mutation, or out-of-scope paths fail before import. Response-only output cannot write. Success, failure, timeout, invalid output, and operator rejection remain visible and non-gating. A root-adopted finding must be independently verified before entering the native gate.

**Verification:** Existing external-action suites plus new shared-workspace and same-record tests pass; no live provider call is required for unit proof.

### U7. Remove active V1 and evidence-chain surfaces, then align the release

Delete superseded execution machinery and update every active script, test, instruction, manifest, inventory, and generated document to describe only the V2 kernel.

**Goal:** Prevent hidden fallback, stale operator guidance, or release metadata from keeping the old system active.

**Requirements:** R8, R10, R12.

**Dependencies:** U5, U6.

**Files:** Apply this closed migration inventory:

| disposition | exact active paths |
|---|---|
| Delete | `plugins/fleet-core/scripts/codex_v1_catalog.py`, `plugins/fleet-core/tests/test_codex_v1_catalog.py`, `tests/test_codex_v1_agent_compatibility.py` |
| Delete | `plugins/verified-workflows/scripts/protected_store.py`, `workspace_evidence.py`, `dispatch_receipt.py`, `named_child_attestation.py`, `raw_hook_maintenance.py`, `workflow_records.py`, `plugins/verified-workflows/hooks/agent_receipt.py`, and `plugins/verified-workflows/hooks/hooks.json` |
| Delete tests | `plugins/verified-workflows/tests/test_protected_store.py`, `test_workspace_evidence.py`, `test_dispatch_receipt.py`, `test_named_child_attestation.py`, `test_raw_hook_maintenance.py`, `test_workflow_records.py`, and `test_agent_receipt.py` |
| Rewrite or adapt | `plugins/fleet-core/scripts/fleet_commons/codex_model_catalog.py`, model data/tests, `plugins/verified-workflows/scripts/workflow_dispatch.py`, `workflow_feasibility.py`, `protocol_probe.py`, `gate_evaluator.py`, profile renderer/sync, active run/select/review skills and references, and their replacement tests |
| Retain as historical | Existing legacy-token inventory, its generator, historical requirements/plans/reviews/classifications/proof JSON, and frozen-source fixtures, with active guidance labeling them non-current |

Also update active Saga and Verified Workflows docs, root `README.md`, portability matrix/provenance, validation scripts, generated Saga facts/assets inputs, manifests, changelogs, and version tests.

**Approach:** Remove old active code and replace only the behavior still required by U3-U6. Keep historical plans, reviews, classifications, legacy inventories, and prior proof JSON unchanged or explicitly labeled historical. Make the Fleet Core catalog projection preserve native V2 metadata instead of forcing V1 rows. Regenerate checked artifacts from canonical inputs. Prepare the three plugin release surfaces without versioning them; U8 chooses and mints the aligned candidate versions only after the initial source-behavior and Luna proof passes.

**Patterns to follow:** Use repository generators rather than manual edits to generated facts and assets. Preserve parser compatibility only where active Saga state requires it; do not retain executable V1 selection or old receipt writers under a compatibility name.

**Test scenarios:** Active-source scans find no V1 installation command, forced V1 row, five-profile claim, hidden V1 fallback, or old protected-record dependency. Historical artifacts remain byte-stable and labeled non-current. All manifests, marketplace inventory, versions, generated facts/assets, portability status, capability snapshots, and tests agree.

**Verification:** Focused migration tests, legacy-token checks, generated-document checks, and `scripts/validate_codex_plugins.py` pass before live release proof.

### U8. Prove V2, review, merge, install, and exercise rollback

Run the complete V2 matrix through fresh sessions that reuse the current Codex authentication and project configuration, then complete independent reviews, repository checks, PR and merge lifecycle, current Codex installation, fresh-session readback, and post-migration rollback drill.

**Goal:** Finish with merged source and a current Codex environment that actually runs the approved V2 system, with a proven recovery path.

**Requirements:** R6, R9, R10, R12.

**Dependencies:** U7.

**Files:** Modify the tracked `.codex/config.toml`, final capability/proof JSON and schemas, cutover and rollback docs, plugin manifests/changelogs/version inventories, the code-review and QA artifacts, and only generated release evidence required by repository convention. User-level Codex config, managed profiles, model catalog, and plugin cache change only through supported installation/sync commands after merge.

**Approach:** Start with KTD14's authority preflight. If the active session cannot write tracked `.codex` files and Git metadata, reach GitHub, or later mutate the current user's Codex surfaces through supported commands, persist the checkpoint and resume U8 in an authorized session; do not downgrade a gate.

Using the current authenticated Codex identity and project configuration, run an initial source-tree exercise covering configured-agent selection, exact model/effort/provider/permission, no-history and bounded-history context, declared nested delegation, typed results, messages, follow-up, wait/list, interruption, restoration, Luna leaf behavior, and Ultra root-only behavior. Fresh `codex exec` sessions use CLI feature overrides for V2, select the unmodified native `$CODEX_HOME/models_cache.json` instead of the active legacy V1 catalog clone, and discover the candidate profile bytes from project `.codex/agents`; they do not create another login or mutate installed plugins. The proof records and validates the native catalog digest and required V2 rows. If Luna fails any required operation, remap `scan_low` and `monitor_low` to Terra/low without changing permissions and rerun the entire matrix. Once behavior and the Luna decision are stable, choose the aligned release versions, update the three plugin manifests/changelogs/inventories, bind the resulting package bytes to the reviewed source, and rerun the complete R46 matrix before review. Installed-byte proof occurs after merge, after the obsolete user-level catalog pointer is removed, through the attended install, rollback, and reapply exercise.

Start each testing, architecture, and security reviewer as a fresh V2 review-root session reusing the current Codex authentication and configuration, launch the contract's exact read-only project profile beneath that root with no implementation turns, and return the typed result to the implementation root. Remediate at most three shared rounds. A behavior, profile, tracked/user config, adapter, runtime-proof input, or proof-command change reruns the complete matrix and every affected reviewer. After all reviewer gates pass, the only no-rereview edits allowed are review/QA artifacts that faithfully transcribe already returned typed results, PR metadata, and generator outputs produced solely from unchanged reviewed inputs. Any other path or semantic change returns to the applicable reviewer; the final root audit enforces this allowlist.

Run focused checks, full pytest, repository validation, generated checks, and final doc/code review. Commit atomically, open the PR, wait for CI, merge, and verify the merge SHA on `origin/main`. Immediately before the first current-host mutation, freshly capture and verify a private rollback package containing the approved pre-migration repository ref, current project and user config, managed profiles, model-catalog state, and installed `fleet-core`, `saga`, and `verified-workflows` versions; U1 evidence supplies lineage but is not used as assumed-current host state. Refresh the marketplace and install the three merged plugin versions through supported `codex plugin` commands, synchronize managed profiles through the validated sync script, remove the user-level V1 catalog override, and start a fresh Codex session for live readback. From that post-migration state, restore every package field and the repository ref, prove restoration, then deliberately reapply the merged V2 release and repeat the fresh-session smoke proof.

**Patterns to follow:** Use current-session `codex exec` with project profile discovery before merge, the supported marketplace upgrade/add/list sequence after merge, exact source-to-installed-byte readback, and `sync_codex_agents.py` transactional apply/recover semantics. Never edit cache snapshots directly.

**Test scenarios:** Full V2 happy path succeeds under Codex 0.145.0. Any missing R46 capability blocks candidate review, merge, and installation. Luna complete pass keeps Luna; any failure selects the preapproved Terra/low remap and requires full rerun before versioning. Child Ultra is rejected while explicit root Ultra is observed. A reviewer launched under the implementation root, a stale review packet, a reviewer threshold or hard-stop failure, or a fourth remediation round blocks PR. A post-review source/config/runtime change without complete applicable reruns fails the final audit. CI failure blocks merge. Stale rollback state or installed version/profile/config mismatch blocks host mutation or completion. Rollback restores the old repository, all three installed plugin versions, project/user config, profiles, and catalog from post-migration state, and reapply returns to the merged V2 state without residue.

**Verification:** Candidate-byte R46 evidence and three independent review-root results pass before PR. `origin/main` contains the merge SHA, all required PR checks pass, `codex plugin list --json` and managed-profile readback match merged source, a fresh session reports V2 and exact profile execution, the fresh rollback drill restores repository plus host state, and the final re-applied V2 smoke proof passes.

## Risk Analysis and Mitigation

The principal risks are missing native authority, stale rollback state, and accidental recreation of the retired control plane; every one has a blocking proof or closed fallback.

| risk | impact | mitigation |
|---|---|---|
| Codex 0.145.0 omits a required runtime field | Strict work could be accepted from requested configuration rather than observed execution | U1 and U8 fail cutover; do not retain hooks or V1 as hidden authority fallbacks |
| Simplification deletes behavior that still protects a real boundary | Writes, Git mutation, external egress, or reviewer gates could weaken | Preserve those boundaries explicitly in the compiler, typed result, gate, and external-action tests before deleting old modules |
| The plugin recreates a scheduler under new names | Complexity and duplicated live truth return | Keep live identity, hierarchy, liveness, messages, waiting, and restoration exclusively in V2; bound the plugin to compile/validate/record |
| Role/profile migration drifts from the 25 maintained lenses | Reviewer behavior or escalation policy changes silently | Classification gate, role-count/mandate equivalence tests, exact six-profile validation, and no new hyphenated executable state |
| Current-Mac cutover leaves repository and host on different releases | New instructions could run against old plugins or profiles | Merge first, then supported marketplace install, transactional profile sync, exact byte/readback checks, and fresh session |
| V1 removal makes recovery impossible | A failed live cutover strands the operator | Record lineage in U1, freshly capture exact private pre-state immediately before host mutation, and exercise repository-plus-host rollback from post-migration state |
| U1 rollback evidence becomes stale before host cutover | The drill restores old assumptions rather than the actual current installation | Recapture repository predecessor, all three installed plugin versions, project/user config, profiles, and model catalog immediately before the first host mutation |
| The active session lacks Git, GitHub, tracked `.codex`, or user-Codex authority | U8 could partially release or mutate only some required surfaces | Run KTD14 preflight, persist a checkpoint, and resume in an authorized session without weakening proof or review gates |
| External shared-workspace support widens data or mutation scope | Secrets or unrelated files could leave the boundary | Reuse approval fingerprints and egress sanitization; add explicit context/write allowlists, overlap checks, secret-path denial, Git denial, and root audit |
| Review fan-out becomes the same bureaucracy being removed | Normal changes remain expensive and slow | Require one reviewer, add roles only for concrete risk, use exact score/hard-stop policy, and rerun only affected reviewers within the shared three-round cap |

## Alternatives Considered

The rejected alternatives either preserve duplicated authority, add another operator surface, or hide a runtime mismatch.

- Incrementally shorten the old evidence machinery: rejected because its module and schema boundaries encode the duplicated task/evidence model the requirements remove.
- Publish a separate V2 workflow plugin: rejected because it would create two operator surfaces, duplicate role/profile catalogs, and lengthen cutover.
- Keep the V1 catalog as an automatic fallback: rejected because normal operation would no longer be provably V2 and profile/runtime mismatches could be hidden.
- Make Saga own the live task graph: rejected because Saga should persist lifecycle and pointers while Codex V2 owns live execution state.
- Require an external implementation reviewer by default: rejected because external engines are non-gating and no external action was approved for this plan; native fresh-context V2 reviewers provide the required gate.
- Preserve full workspace snapshots as optional strict mode: deferred rather than included. A future specialized high-assurance product can be designed separately if a concrete use case justifies it.

## Hard-to-Disagree Decisions

These decisions close the few implementation choices that would otherwise reopen scope during delivery.

- The exact V2 receipt field names and restoration mechanics are discovered from Codex 0.145.0 in U1; the product contract is fixed, but the adapter must follow observed runtime shape rather than guessed schema names.
- Luna remains preferred only if the complete leaf proof passes. Terra/low under the same two low-cost profile IDs is the already approved fallback, not a reason to preserve V1.
- Old protected records remain historical evidence; the new kernel does not migrate them into the concise run record or claim continuity it cannot prove.
- The active candidate versions are chosen during U8 only after initial source behavior and the Luna decision are proved; deterministic package binding and fresh-session review precede merge, while installation proof is exercised on the current Codex home after merge with rollback and reapply.

## Scope Boundaries

The work replaces workflow execution and its release surfaces without changing Codex, credentials, provider authority, or historical evidence.

This plan does not modify Codex itself, add a new provider, change credentials, grant external gate authority, make Ultra a child profile, require every role on every run, or build production/nonproduction plugin environments. It does not rewrite historical V1 plans, reviews, classifications, or proof artifacts.

This plan does not retain content-addressed workflow evidence, full workspace snapshots, duplicated event logs, protected subject chains, or a plugin-owned executable task tree in the active path. It also does not remove Saga lifecycle state, the external-action approval runtime, role lenses, reviewer scoring, root-only Git, or supported plugin installation controls.

## System-Wide Impact

The public plugin and lifecycle identities stay stable while runtime authority moves to native V2 and current-host state changes only after merge.

- `verified-workflows` changes from a protected-evidence scheduler into a small V2 contract, result, assurance, and recording layer.
- `saga` continues to own lifecycle/backend choice and gains a direct pointer to the concise workflow run plus same-preview external actions.
- `fleet-core` stops forcing V1 catalog rows and preserves V2 model metadata and profile mappings.
- Repository plans become the visible workflow approval surface; `/work` executes the approved contract, and `/review-workflow` validates it without launching work.
- The current Mac moves to V2 at project and user scope after merge, with six managed profiles and no active V1 catalog override.
- Historical evidence remains usable for lineage and rollback but no longer describes current operating instructions.

## Sources

The plan is grounded in the reviewed requirements, current repository configuration, maintained workflow code, Saga contracts, and the mandatory portability runbook.

- `docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md:11`
- `docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md:67`
- `docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md:77`
- `docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md:99`
- `docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md:110`
- `docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md:118`
- `docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md:129`
- `docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md:138`
- `docs/reviews/2026-07-24-codex-v2-orchestrated-execution-system-requirements-review.md:53`
- `.codex/config.toml:3`
- `README.md:29`
- `plugins/verified-workflows/scripts/workflow_dispatch.py:23`
- `plugins/verified-workflows/skills/run/SKILL.md:66`
- `plugins/verified-workflows/config/role-registry.yaml:71`
- `plugins/verified-workflows/config/role-registry.yaml:85`
- `plugins/saga/references/operator-choice.md:8`
- `plugins/saga/scripts/saga.py:9`
- `docs/portability/claude-to-codex-plugin-port-runbook.md:175`
