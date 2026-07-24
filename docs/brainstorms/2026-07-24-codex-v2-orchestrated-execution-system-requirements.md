---
date: 2026-07-24
topic: codex-v2-orchestrated-execution-system
maturity: requirements-ready
---

# Codex V2 Orchestrated Execution System Requirements

## Summary

Replace the current Verified Workflows execution machinery with a small, V2-native orchestration kernel. The main Codex session presents one operator-editable workflow contract, coordinates native and external workers through one control plane, verifies the work, and records one concise final account without duplicating Codex's live task tree.

## Product Thesis

The product is a legible, operator-approved workflow rather than an evidence bureaucracy. Codex V2 should own live multi-agent execution, while the plugin owns only the durable intent, authority boundaries, assurance rules, and final run record needed for a human to understand and override what will happen.

## Problem Frame

Verified Workflows currently asks the operator and runtime to carry more evidence, snapshot, and reconciliation machinery than the work normally justifies. The complexity obscures the basic workflow: decide what work is needed, assign it safely, verify it independently, remediate findings, and let the main session integrate the result.

The repository also carries a V1 model-catalog workaround introduced when native V2 agents could not provide the needed profile, model, and reasoning-effort controls. Codex 0.145.0 adds the V2 controls, configured-agent selection, durable hierarchy, messaging, resume behavior, and runtime identity needed to replace that workaround.

## Key Decisions

The selected design is a minimal orchestration kernel with adapters for native and external execution.

| approach | decision | reason |
|---|---|---|
| Minimal orchestration kernel | Selected | Keeps one simple workflow contract while using Codex V2 as the live execution substrate |
| Simplify the existing machinery in place | Rejected | Risks preserving evidence-chain and duplicated-state concepts that caused the current complexity |
| Add a separate V2 workflow product | Rejected | Creates parallel workflow surfaces and a longer, less legible cutover |

**The main session is the orchestrator.** It owns workflow design, operator preview, integration, Git operations, gate decisions, and the final completion claim. Workers contribute bounded work and evidence but do not become independent coordinators of the overall run.

**One control plane does not imply equal authority.** Native V2 agents may fill workflow roles and satisfy review or validation gates. External engines share preview, routing, ownership, status, and recording conventions, but remain non-gating contributors.

**Plans carry the workflow contract.** The original implementation plan must show the proposed graph, assignments, write ownership, checks, reviewers, fallback envelope, and external actions. Operator changes update that workflow section before approval, and the run record binds the exact approved revision.

**Profiles are authoritative execution classes.** A role is a logical lens selected from the maintained role catalog; a profile is the approved model, effort, permission, and execution class used to run that role. Direct V2 overrides must match the selected profile rather than silently redefining it.

**Fallbacks are exact allowlists, not runtime discretion.** Each assignment may name an ordered list of fallback profile IDs and retry conditions. A fallback remains inside the approved envelope only when the role, scope, dependencies, gate authority, write set, external egress, and permission ceiling stay unchanged and the replacement runs with its own exact profile settings.

**Assurance is practical and risk-based.** Every run needs explicit ownership, targeted deterministic checks, at least one independent reviewer, enforced score thresholds, and root integration. It does not need content-addressed evidence chains, full workspace snapshots, or exhaustive treatment of every theoretical failure mode.

**Shared-workspace writes are allowed under explicit ownership.** Native agents and tool-capable external engines may edit assigned, non-overlapping paths. The orchestrator reviews and integrates every contribution and remains the only actor allowed to operate Git.

**V2 is the active execution path.** The release removes active V1 compatibility behavior and performs a live V2 cutover on the current Mac. Historical evidence and a tested rollback procedure remain available, but there is no hidden V1 fallback during normal execution.

## Actors

The workflow separates operator authority, root orchestration, native gate-capable work, and external non-gating contribution.

- A1. **Operator.** Reviews and edits the proposed workflow, approves its authority and egress boundaries, and decides whether a material contract change may proceed.
- A2. **Main-session orchestrator.** Designs the graph, assigns roles and profiles, verifies runtime identity, coordinates work, owns Git and integration, adjudicates findings, and makes the final decision.
- A3. **Native V2 worker.** Performs bounded implementation, research, testing, scanning, or review with an approved profile and write set.
- A4. **Native V2 reviewer.** Independently evaluates applicable quality dimensions and may satisfy an approved workflow gate.
- A5. **External worker or advisor.** Produces bounded edits or artifacts through an approved provider route but cannot satisfy or control a workflow gate.
- A6. **Codex V2 runtime.** Owns live agent identities, hierarchy, context transfer, messaging, interruption, waiting, and session restoration.
- A7. **Repository checks.** Provide deterministic evidence selected from repository conventions and the risk of the planned change.

## Requirements

The system must make the approved workflow obvious, executable, and reviewable without recreating a general-purpose workflow engine.

**Workflow contract and approval**

- R1. The main session must act as the sole orchestrator for every workflow run.
- R2. Before delegated work begins, the implementation plan must contain a workflow section showing the intended graph, selected logical roles, execution profiles, model and effort, write ownership, dependencies, blocking checks, reviewer gates, ordered fallback profile IDs and retry conditions, and external actions.
- R3. The operator must be able to override any proposed assignment, profile, check, blocking designation, reviewer, external action, or write boundary before approving the workflow.
- R4. Approval must freeze the exact workflow contract used by the run; the final run record must identify the approved plan revision or equivalent exact content binding.
- R5. A change to scope, dependencies, gate authority, write ownership, effective permissions, required gate roles, external egress, or a profile outside the exact approved fallback list must update the plan preview and require renewed approval.
- R6. Retries, interruption recovery, remediation, and fallback selection may continue without repetitive approval only when they match the approved conditions and do not widen permissions, write scope, egress, or authority.
- R7. The orchestrator must never silently substitute an unapproved profile, provider, permission mode, write set, or gate role.

**Roles, profiles, and V2 selection**

- R8. The maintained logical role catalog must retain all 25 current roles, but no run is required to instantiate every role.
- R9. The orchestrator must select only the roles justified by the work and its risks, with at least one independent reviewer on every implementation run.
- R10. The managed profile catalog must include the following authoritative mappings; `review_max` is Sol/max and is not Ultra-backed.

| profile | model | effort | workspace | external access | intended use |
|---|---|---|---|---|---|
| `review_max` | `gpt-5.6-sol` | max | read-only | none | Explicit escalation for unusually ambiguous or high-risk review |
| `review_high` | `gpt-5.6-sol` | high | read-only | none | Architecture, security, adversarial, API, privacy, and quality review |
| `work_high` | `gpt-5.6-sol` | high | workspace-write | none | Demanding implementation |
| `test_medium` | `gpt-5.6-terra` | medium | workspace-write | none | Ordinary implementation, testing, and ambiguous validator interpretation |
| `scan_low` | `gpt-5.6-luna` | low | read-only | none | Bounded extraction and scanner-result reduction |
| `monitor_low` | `gpt-5.6-luna` | low | read-only | allowlisted-read | CI, deployment, and runtime observation |

- R11. `work_high` must remain an explicit escalation from the ordinary `test_medium` worker profile; low-cost profiles use the conditional V2 fallback in R47 without changing their permission boundaries.
- R12. The orchestrator must recommend the least expensive profile capable of the assignment and expose that recommendation for operator override before approval.
- R13. A native assignment must select its configured agent profile explicitly, and any direct model or reasoning-effort fields must exactly match that profile. Profiles execute on the root session's provider backend and must not imply or silently trigger a provider switch.
- R14. A native assignment is strict when it may write the workspace or its result may satisfy a blocking dependency, check, or gate. The root orchestrator must verify runtime readback of the agent profile or type, model, reasoning effort, provider backend, and effective permissions for every native assignment and declared descendant before accepting its result; strict work cannot contribute authority until every field matches exactly.
- R15. Missing readback or a profile, model, effort, provider, or permission mismatch must fail the assignment visibly. The result remains unusable, requested configuration alone is not execution proof, and any replacement must follow the approved fallback envelope or return to preview.
- R16. Ultra must remain an explicit root-only option and must never be assigned to a child agent.

**Native delegation and workspace ownership**

- R17. Native workers may edit only the explicitly assigned paths in the approved workflow, and concurrently writable assignments must not overlap. Before accepting a contribution, the root must compare its changed paths with the assignment; an out-of-boundary edit fails the assignment visibly and must be excluded or deliberately repaired before integration.
- R18. The main-session orchestrator must review and integrate worker edits and must exclusively own commits, branches, rebases, merges, pushes, and other Git operations. An observed worker Git operation or repository-metadata mutation is a hard assignment failure that pauses integration until the root restores and verifies repository state.
- R19. A worker may spawn a child or grandchild only when the approved graph declares that descendant path and its work remains within the ancestor's scope and write ownership.
- R20. Reviewers and scanners must receive a self-contained task packet with no inherited turn history by default; cooperative workers and testers may receive a positive bounded amount of history when the workflow declares it.
- R21. Full-history context must not be the default for configured child profiles; the approved workflow must use either no inherited turns or an explicit positive bound.
- R22. Inter-agent messages may coordinate progress, clarify assignments, or report state, but they cannot satisfy dependencies, checks, findings, or gates.
- R23. Every worker and reviewer must return a typed final result containing assignment and attempt identity, canonical agent path, role and profile, terminal status, summary, changed paths or an explicit no-change statement, checks and outcomes, and findings or residual risks. Reviewer results must additionally contain scored dimensions, typed exclusions, arithmetic, typed findings, and hard-stop flags; the root must reject incomplete or malformed results.
- R24. The orchestrator must own dependency release, finding adjudication, remediation dispatch, and the final integration decision even when descendants coordinate among themselves.

**External execution**

- R25. External actions must appear in the same workflow preview as native assignments and show their purpose, provider, model, egress destination, exact readable or transmittable context paths, sensitivity, cost class when available, assigned write paths or artifact destination, and non-gating status.
- R26. A tool-capable external engine may read or transmit only its declared, secret-screened context and must never receive literal credentials, inherited root secret variables, or secret-bearing paths regardless of approval. Current CLI routes are advisory and read-only; a non-empty write set must fail closed until an enforceable filesystem boundary exists.
- R27. External workers must never perform Git operations or mutate the shared workspace. Any future external-write capability requires a separately reviewed filesystem boundary and the same write-ownership audit and failure behavior as native workers.
- R28. External results must remain non-gating: they cannot independently pass, fail, block, or satisfy a workflow gate. The root may verify and adopt an externally surfaced issue as a root-owned typed finding, after which the ordinary native gate and remediation rules apply to that root finding.
- R29. External unavailability, timeout, invalid output, or rejection must be visible in the run record and must not be represented as successful execution.

**Checks, review, and remediation**

- R30. The workflow preview must list the deterministic checks the orchestrator intends to run, identify which are blocking, and allow the operator to override that selection before approval.
- R31. Check selection must follow repository conventions and the risk of the changed behavior rather than a fixed maximal suite.
- R32. At least one reviewer must be independent of the implementation assignment; the reviewer must not be the implementer or its descendant and must receive a self-contained review packet with no inherited implementer turns. The orchestrator may require multiple reviewers when distinct risk lenses are material.
- R33. Each required reviewer must score every applicable numbered mandate from its approved role lens on a 0-10 scale. Only statically non-applicable mandates may be excluded with a typed rationale, the root must validate dimensions and exclusions against the role lens, zero applicable dimensions fails the gate, and passage requires an average of at least 9.0 with no applicable dimension below 7.0.
- R34. Any valid unresolved P0, P1, security, or role-declared hard-stop finding must fail the reviewer gate regardless of aggregate score. A valid hard stop cannot be cleared by root assertion or score arithmetic; it requires remediation and fresh revalidation.
- R35. The orchestrator may run up to three remediation and focused-revalidation rounds per approved workflow run. A round may address multiple findings, and findings discovered during remediation do not reset the shared counter.
- R36. If blocking findings remain after three remediation rounds, the workflow must pause with the unresolved findings and completed evidence visible to the operator. Continuing requires an amended workflow preview and a newly approved run with a new bounded allowance.
- R37. Root integration and the final targeted checks must occur after accepted worker changes and required remediation are present in the shared workspace.

**Durability and run record**

- R38. Codex V2 must remain the source of truth for live agent paths, hierarchy, liveness, messaging, interruption, and waiting; the plugin must not maintain a duplicate executable task tree.
- R39. Interruption or root-session resume during the same attempt must restore or reconnect to the same canonical V2 agent identity when the runtime supports it.
- R40. A retry after terminal failure, a remediation assignment, or a revalidation assignment must use a fresh canonical agent path and produce a distinct result entry. Before dispatching overlapping work, the root must classify the prior attempt's workspace edits as accepted carry-forward or rejected cleanup, restore a known state accordingly, and record that decision without requiring a full workspace snapshot.
- R41. The workflow must produce one concise durable run record containing the approved graph, assignments, runtime identity readback, external route outcomes, typed results, checks, findings, remediation rounds, and root decision.
- R42. The default run record must not require content-addressed evidence chains, full workspace snapshots, duplicated event logs, or replayable copies of V2 execution state.
- R43. A dependency or gate may be satisfied only by the root's validated interpretation of a native typed result, deterministic check, or root-owned typed finding adopted from independently verified evidence, never by an informal message, raw external output, or an unverified status claim.

**V2 cutover and release proof**

- R44. The repository must enable V2 as the active multi-agent path and remove active configuration, scripts, documentation, and tests whose purpose is to force V1-compatible model rows or V1-only agent behavior.
- R45. Historical V1 requirements, plans, and proof artifacts must remain available as lineage and rollback evidence without being presented as current operating instructions.
- R46. The release must prove configured-agent selection, explicit model and effort, exact effective permissions, bounded context, nested approved delegation, typed results, coordination messaging, follow-up, wait and list behavior, interruption, and root-session restoration in an isolated V2 exercise. Failure or unavailable proof for any listed capability blocks cutover.
- R47. Luna must be tested as a V2 leaf profile; if that complete proof fails, `scan_low` and `monitor_low` must be remapped to Terra/low before cutover rather than using Luna through V1.
- R48. The release must include a root-only Ultra proof that confirms Ultra is available only through explicit root selection and is never offered to child assignments.
- R49. Cutover must include the current Mac's project and user-level Codex configuration, installed managed profiles, removal of the local V1 model-catalog override, and fresh-session runtime readback.
- R50. A documented rollback package must restore the pre-cutover repository release or ref, project and user configuration, managed profiles, and local model-catalog state if live V2 proof fails. The rollback must be exercised from post-migration repository state; it is an operator action, not an automatic per-assignment fallback.
- R51. Repository behavior, plugin metadata, operator documentation, capability snapshots, probes, and tests must agree before the release claims V2 readiness.

## Key Flows

The normal path is intentionally short, with approval before delegation and one root decision after assurance.

- F1. **Compile and approve the workflow.** **Trigger:** an implementation plan is ready to run. The orchestrator selects relevant roles, assigns profiles and non-overlapping write sets, proposes checks and reviewers, declares approved fallbacks and external routes, then updates the plan with any operator overrides before approval. **Covers R1-R13, R16, R25, R30-R32.**
- F2. **Launch native and external work.** **Trigger:** the workflow contract is approved. The orchestrator verifies each native agent's runtime identity and permissions, launches approved external routes, and prevents work from starting when its observed authority or ownership does not match the contract. **Covers R13-R18, R25-R29.**
- F3. **Coordinate bounded descendants.** **Trigger:** an approved assignment benefits from nested delegation. The parent launches only declared descendants, uses bounded or absent inherited history, and uses messages for coordination while the root retains dependency and gate authority. **Covers R19-R24, R38, R43.**
- F4. **Verify and review.** **Trigger:** assigned implementation work returns. The root validates typed results, runs the approved deterministic checks, dispatches the independent reviewer set, applies score and hard-stop rules, and releases dependent work only from validated evidence. **Covers R23, R24, R30-R34, R37, R43.**
- F5. **Remediate findings.** **Trigger:** a blocking check or reviewer finding remains. The orchestrator classifies prior workspace edits, launches a fresh bounded remediation assignment and focused revalidation inside the approved envelope, increments the run-wide counter, then either integrates or pauses after the third unresolved round. **Covers R5-R7, R35-R37, R40.**
- F6. **Resume an interrupted attempt.** **Trigger:** the root session or an active assignment is interrupted. The orchestrator restores the same attempt and canonical agent identities when possible, records any terminal failure honestly, and uses fresh identities only for retries or new remediation work. **Covers R38-R41.**
- F7. **Decide and record.** **Trigger:** checks and reviewer gates reach a terminal state. The root integrates accepted work, makes the final decision, and writes one concise run record bound to the approved plan without copying the live V2 task tree. **Covers R4, R18, R37, R41-R43.**
- F8. **Cut over or roll back.** **Trigger:** repository migration and isolated V2 proof pass. The maintainer updates current-Mac configuration and profiles, starts a fresh Codex session, runs live proof, and either confirms V2 readiness or performs the documented rollback. **Covers R44-R51.**

## Acceptance Examples

The examples pin the conditional behavior most likely to become ambiguous during planning.

- AE1. **Operator override changes the approved plan.** **Given:** the orchestrator proposes `work_high` and a broad blocking test suite. **When:** the operator selects `test_medium` and narrows one check to non-blocking. **Then:** the workflow section is updated before approval and the run record binds that exact revision. **Covers R2-R5, R12, R30.**
- AE2. **Observed model mismatch blocks work.** **Given:** an assignment selects `test_medium`. **When:** runtime readback shows a model or effort that does not match Terra/medium. **Then:** the assignment fails visibly before its output can satisfy a dependency or gate. **Covers R13-R15, R43.**
- AE3. **Permission intent is not permission proof.** **Given:** a strict child assignment requires read-only execution. **When:** the effective child permissions cannot be read back or do not exactly match. **Then:** the child cannot satisfy the strict gate, and any reassignment outside the approved fallback envelope requires a new preview. **Covers R5, R14, R15.**
- AE4. **External writes fail closed.** **Given:** a workflow requests a non-empty write set for an external CLI route. **When:** the route is validated. **Then:** dispatch stops because the current release has no enforceable external filesystem boundary; native V2 writes remain subject to declared ownership and audit. **Covers R17, R18, R26, R27.**
- AE5. **External advice cannot pass review.** **Given:** an external reviewer reports no findings. **When:** the native reviewer gate has not passed. **Then:** the workflow remains gated because the external result is advisory only. **Covers R28, R32-R34.**
- AE6. **Messages do not release dependencies.** **Given:** a worker sends a message saying its task is complete. **When:** no valid typed final result has returned. **Then:** dependent work remains blocked. **Covers R22-R24, R43.**
- AE7. **Risk justifies multiple reviewers.** **Given:** a change has independent security and migration risks. **When:** the orchestrator compiles the workflow. **Then:** it may assign separate applicable reviewers, and all required native reviewer gates must pass. **Covers R9, R32-R34.**
- AE8. **Remediation is bounded.** **Given:** blocking findings remain after each focused revalidation. **When:** the third remediation round still fails. **Then:** the root pauses and reports unresolved findings rather than launching a fourth automatic round. **Covers R35, R36.**
- AE9. **Resume preserves an attempt.** **Given:** the root session stops while a native worker is active. **When:** the session resumes and V2 restoration succeeds. **Then:** the orchestrator reconnects to the same canonical agent path instead of double-dispatching the assignment. **Covers R38-R40.**
- AE10. **Retry creates new evidence.** **Given:** an agent reaches terminal failure with partial workspace edits. **When:** the orchestrator retries inside the approved envelope. **Then:** the root first records whether those edits are accepted or removed, restores the selected state, and launches the retry with a fresh canonical path and result entry. **Covers R6, R40, R41.**
- AE11. **Luna failure produces a V2 mapping.** **Given:** Luna cannot pass the complete V2 leaf proof. **When:** cutover proceeds. **Then:** low-cost scan and monitor profiles use Terra/low and no active path invokes Luna through V1. **Covers R44, R47.**
- AE12. **Live cutover fails closed.** **Given:** repository migration is complete but fresh-session current-Mac proof fails. **When:** the maintainer invokes rollback. **Then:** V2 readiness is not claimed and the rollback restores the pre-cutover repository ref, project and user configuration, managed profiles, and model-catalog state. **Covers R49-R51.**
- AE13. **Ultra cannot become a child profile.** **Given:** a proposed child assignment selects Ultra directly or through a fallback. **When:** the workflow is compiled. **Then:** the assignment is rejected before approval or launch; `review_max` remains Sol/max. **Covers R10, R16, R48.**
- AE14. **Nested delegation stays declared and bounded.** **Given:** a worker attempts to spawn an undeclared descendant or pass full inherited history without a positive bound. **When:** the root validates the launch. **Then:** the descendant is rejected before its output can count. **Covers R19-R21.**
- AE15. **External failure remains visible and non-gating.** **Given:** an approved external route times out or returns invalid output. **When:** the workflow records its result. **Then:** it records a non-success state, does not represent the provider as completed, and neither passes nor blocks a gate by itself. **Covers R28, R29, R41.**
- AE16. **Root adoption gives an external issue native authority.** **Given:** an external advisor surfaces a credible defect. **When:** the root independently verifies it and records a root-owned typed finding. **Then:** the finding participates in ordinary severity, remediation, and gate handling; the raw external output still has no gate authority. **Covers R28, R34, R43.**
- AE17. **Write-boundary violations taint the assignment.** **Given:** a native or external worker edits an unassigned path or changes Git metadata. **When:** the root audits the contribution. **Then:** the assignment fails, integration pauses, and the root restores and verifies repository state before continuing. **Covers R17, R18, R27, R40.**
- AE18. **Incomplete isolated proof blocks cutover.** **Given:** every V2 proof passes except interruption recovery or effective-permission readback. **When:** release readiness is evaluated. **Then:** cutover remains blocked because every capability listed by R46 is required. **Covers R14, R15, R46.**
- AE19. **Fallbacks use only the frozen envelope.** **Given:** an assigned profile is unavailable. **When:** the approved workflow lists a replacement profile with the same role, scope, write set, authority, egress, and permission ceiling. **Then:** the root may launch that exact fallback without renewed approval; an unlisted or wider replacement returns to preview. **Covers R2, R5-R7, R13-R15.**
- AE20. **External context is an enforced boundary.** **Given:** an external worker requests an undeclared source path or encounters a credential-bearing file. **When:** it prepares or performs the action. **Then:** the additional content is withheld, credential content remains blocked regardless of operator route approval, and the event cannot be reported as successful if the declared task cannot continue. **Covers R25, R26, R29.**
- AE21. **Malformed typed results cannot release work.** **Given:** a worker returns prose without assignment identity, changed paths, or required reviewer dimensions. **When:** the root validates the result. **Then:** the result is rejected and no dependency or gate is released. **Covers R23, R43.**

## Success Criteria

Success means normal work reads as one approved plan followed by one trustworthy account of what actually happened.

- The operator can understand and alter the full intended workflow before any delegated work or external egress begins.
- Native V2 assignments prove the exact profile, model, effort, provider, and effective permissions that actually ran.
- Workers can contribute in parallel without overlapping write ownership or acquiring Git authority.
- At least one independent native reviewer and the approved deterministic checks govern integration.
- External contributions are useful within the same workflow but cannot masquerade as gate evidence.
- Interruption and retry behavior is visible, durable, and does not double-dispatch the same attempt.
- The final durable artifact is concise enough to audit without reconstructing a content-addressed evidence graph.
- A fresh Codex session on the current Mac proves the V2 configuration and managed profiles after the V1 override is removed.

## Scope Boundaries

The first release deliberately excludes machinery that does not improve the ordinary operator workflow.

### Deferred for later

- Automated optimization of profile selection from historical cost or quality telemetry.
- Direct budget enforcement beyond provider-account controls and operator-visible cost class.
- Promotion of external providers from non-gating contributors to authoritative workflow roles.
- Broader multi-host rollout after the current-Mac cutover proves the repository contract.
- Additional managed profiles beyond the six approved execution classes.

### Outside this product's identity

- A general-purpose workflow engine, scheduler, or event-sourced execution platform.
- A plugin-maintained replayable mirror of Codex V2's task tree.
- Content-addressed evidence chains or full workspace snapshots as default workflow requirements.
- Hidden V1 fallback, mixed V1/V2 execution, or runtime model-catalog rewriting to make V1 rows appear V2-compatible.
- Git authority for native or external workers.
- Gate authority for external engines.
- Mandatory activation of every logical role on every workflow.
- Automatic continuation after unresolved findings exceed the remediation limit.

## Dependencies / Assumptions

The cutover depends on Codex 0.145.0 behavior remaining available in the live installation used for proof.

- Codex V2 continues to expose configured agent selection, direct model and reasoning-effort controls, canonical hierarchy, messaging, follow-up, wait/list/interrupt operations, and root-session restoration.
- Configured V2 agents expose enough runtime identity and effective-permission information to enforce the strict profile contract; if live proof cannot demonstrate that readback, V2 cutover is blocked rather than inferred from configuration.
- Native child agents and tool-capable external engines share the repository workspace, making accurate non-overlapping write ownership a load-bearing safety boundary.
- The existing 25 logical roles remain useful as optional lenses even though the execution mechanism and evidence model are simplified.
- The older external-advisory requirements remain historical input, but this document supersedes their contained-patch ceiling and separate external-runtime framing where the two conflict.
- Planning will determine the smallest migration sequence and exact repository surfaces without reintroducing the rejected evidence architecture.

## Outstanding Questions

No product decision blocks implementation planning.

**Deferred to planning**

- Exact implementation sequence and atomic commit boundaries.
- Exact location and compact serialization of the approved workflow section, typed result variants, and final run record, while preserving the minimum fields in R23.
- Exact migration treatment for each V1-only helper, snapshot, generated inventory, and documentation reference.
- Exact isolated and live proof fixtures needed to exercise all required V2 operations without modifying unrelated user state.
- Exact per-assignment fallback lists and retry conditions that use the closed envelope semantics defined above.
- Exact lightweight mechanism for detecting changed-path and Git-authority violations without restoring the retired evidence chain.
- Version numbers for affected plugins after behavior, documentation, and validation agree.

## Sources / Research

These sources establish the current repository state, prior product contracts, and Codex V2 capabilities that planning must reconcile.

- `.codex/config.toml`: project configuration currently enables multi-agent V1 behavior and disables V2.
- `plugins/verified-workflows/agents/`: maintained configured-agent profiles and their current model, effort, and sandbox intent.
- `plugins/verified-workflows/skills/run/` and `plugins/verified-workflows/skills/run/references/`: current workflow execution and evidence contract.
- `plugins/verified-workflows/config/role-registry.yaml`: current logical-role mandates, typed result contracts, score scale, and static-exclusion policy.
- `plugins/fleet-core/scripts/codex_v1_catalog.py`: active local model-catalog compatibility path to remove from normal operation.
- `scripts/capture_codex_runtime_capabilities.py` and `scripts/prove_verified_workflows_runtime.py`: current capability snapshot and runtime proof surfaces that need V2 truth.
- `docs/plans/2026-07-17-codex-v1-agent-compatibility-plan.md`: current V1 workaround, rollback context, and affected surfaces.
- `docs/brainstorms/2026-07-11-codex-external-advisory-execution-contract-requirements.md`: prior external routing, approval, receipt, and containment decisions partially superseded here.
- [Codex V2 stable feature registration](https://github.com/openai/codex/pull/34383): V2 is stable in Codex 0.145.0 but remains disabled by default.
- [V2 model and reasoning overrides](https://github.com/openai/codex/pull/32749): direct child model and effort selection and default exposure.
- [V2 backend boundary](https://github.com/openai/codex/pull/32751): child model overrides remain on the root session's provider backend.
- [Unified configured-agent definitions](https://github.com/openai/codex/pull/33550): V2 uses the shared configured-agent profile surface.
- [Configured-agent defaults and full-history behavior](https://github.com/openai/codex/pull/33631): configured model and effort defaults are honored by V2 execution.
- [Configured-agent selection visibility](https://github.com/openai/codex/pull/33572): agent-type selection appears when configured roles exist.
- [Role-selected effort validation](https://github.com/openai/codex/pull/33656): effort validation follows the selected role's model.
- [V2 descendant restoration](https://github.com/openai/codex/pull/32837) and [restored execution metadata](https://github.com/openai/codex/pull/33657): root resume restores descendant identity and execution properties.
- [Parent-owned V2 task hierarchy](https://github.com/openai/codex/pull/33841): child threads remain visible within the root-owned execution tree.
