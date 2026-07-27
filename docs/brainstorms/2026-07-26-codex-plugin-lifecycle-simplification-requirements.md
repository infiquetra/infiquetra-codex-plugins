---
date: 2026-07-26
topic: codex-plugin-lifecycle-simplification
maturity: requirements-ready
source: "docs/ideation/2026-07-11-codex-workflow-control-agent-lifecycle-ideation.md; continuation survivor: Deletion-First Plugin Lifecycle"
---

# Codex Plugin Lifecycle Simplification Requirements

## Summary

Preserve the Codex plugin fleet's public lifecycle capabilities while replacing unjustified internal control machinery with the smallest mechanisms that support real operator paths. Every delivery capability must both reduce active complexity and prove its promised user path, without creating another workflow framework.

## Problem Frame

The lifecycle core accumulated overlapping approval, routing, persistence, recovery, compatibility, and evidence mechanisms while adapting Claude-era behavior to Codex. Saga alone now carries 11,122 lines across 23 `external_action_*` and `engine_*` scripts, with the same external-action operating contract repeated across six public skills.

A recent read-only Claude request exposed the cost: the provider call eventually succeeded, but only after repeated unchanged approvals and several control-layer failures involving adapter selection, preview restoration, process identity, and a missing `USER` environment contract that made the harness appear unauthenticated. The machinery intended to handle edge cases became a more common failure source than the external harness.

The fleet does not need uniform redesign. Verified Workflows recently moved to a smaller Codex V2 execution contract with live proof, while Mission Control and Deploy have clear mutation ownership. The review must concentrate on duplicated internals and confused authority boundaries without weakening controls at real GitHub, deployment, credential, or workspace-write boundaries.

## Key Decisions

The selected approach preserves contracts and simplifies behind them.

| decision | requirement-level consequence |
|---|---|
| Preserve the public lifecycle | Existing public skill entrypoints and promised behavior remain unless the operator separately approves a removal |
| Simplify the lifecycle core first | Saga, Fleet Core, Mission Control, and Deploy receive deep review; Verified Workflows is validated against V2 before any redesign |
| Require two success gates | Each delivery capability must remove or collapse unjustified machinery and prove a named operator path |
| Make external execution caller-owned | Saga or Verified Workflows owns intent, sequencing, authority, retries, and durable evidence; an adapter only invokes a harness |
| Keep external support extensible but small | Harnesses implement one narrow capability contract without acquiring a provider-promotion or action lifecycle |
| Use existing intent as authorization | An explicit user request or approved Verified Workflow contract authorizes the invocation; only material expansion requires renewed approval |
| Permit scoped external writes in V2 | A Verified Workflow may assign non-overlapping paths to an external harness while the root session retains Git authority and audits the resulting diff |
| Prefer existing truth over new bookkeeping | Progress, completion, and closeout are derived from normal artifacts, Git, checks, and board state rather than another state store |

**The existing public surface is protected.** In this document, a public skill is an operator-facing entrypoint such as `$saga:brainstorm` or `$saga:work`. The review may recommend consolidating or retiring one, but implementation cannot remove it or its distinct promised capability without explicit operator approval.

**Internal deletion is approved at the capability boundary.** Once an approved issue or plan identifies the behavior being preserved and the internal machinery being removed, implementation does not require file-by-file approval. This keeps operator control over product behavior without recreating the bookkeeping problem inside the refactor.

**Verified Workflows is a baseline, not a presumed refactor target.** Its current V2 contract and proof must remain green. Changes are justified only by a failed user path, a duplicated ownership boundary, or the agreed external-write integration.

**The July external-action contract is historical input, not inherited truth.** Its multi-stage action bundles, approval fingerprints, provider promotion, claim/replay, dedicated state progression, and external receipt store continue only if the review proves a current operator path or necessary safety boundary that cannot be served more simply.

## Actors

The simplified lifecycle keeps authority with the existing operator and domain owners.

- A1. **Operator.** Selects the work, authorizes consequential effects, approves product-capability removals, and decides whether a material scope expansion may proceed.
- A2. **Codex root session.** Owns the current lifecycle stage, integration, Git, verification, gate decisions, and final completion claim.
- A3. **Saga.** Routes lifecycle work and writes the normal durable requirements, plan, work, review, QA, handoff, and outcome artifacts.
- A4. **Verified Workflows V2.** Coordinates approved multi-agent work, ownership, checks, review, and the concise run record without duplicating Codex's live task tree.
- A5. **External harness.** Performs a bounded read, review, or assigned write through a thin adapter and returns its result to the caller without owning a separate lifecycle.
- A6. **Mutation-domain plugin.** Mission Control owns GitHub SDLC changes and Deploy owns release-tag changes, including their real consequential-action controls.

## Requirements

The requirements are grouped by operator outcome rather than by existing modules.

**Review and simplification contract**

- R1. Existing public plugin entrypoints and their distinct promised behavior must remain available unless the operator explicitly approves a removal.
- R2. Deep simplification review must cover Saga, Fleet Core, Mission Control, and Deploy. Verified Workflows must first be validated against its current V2 contract, while `discord-identity-assets`, `home-lab-ops`, `python-toolkit`, `unifi`, and `test-suite` receive regression and obvious-dead-weight review rather than default redesign.
- R3. The review must map each named operator path to its active callers, authority owner, durable artifacts, prompts, state concepts, and behavior-bearing runtime surfaces before proposing structural change.
- R4. Every retained nontrivial mechanism must be justified by at least one named operator path, active caller, or necessary safety boundary. Historical parity, theoretical extensibility, and tests that exercise only the mechanism itself are not sufficient proof.
- R5. Every delivery capability must pass two hard gates: it produces a net reduction in active states, branches, prompts, modules, or duplicated responsibilities, and it proves the named operator path before and after the change.
- R6. A workstream must not introduce a new orchestration framework, durable state store, approval system, compatibility layer, or provider lifecycle unless an unmet requirement is demonstrated and the operator approves the added mechanism and carrying cost.

**Lifecycle ownership and deletion**

- R7. Each lifecycle responsibility must have one owner: Saga routes and records lifecycle artifacts, Verified Workflows V2 owns delegated execution, Mission Control owns GitHub SDLC mutation, Deploy owns release-tag mutation, and Fleet Core contains only primitives with demonstrated active consumers.
- R8. Tracked lifecycle documents and verified GitHub state must remain durable truth. Local Saga caches and raw session material may assist recovery but must not become a second authority requiring routine reconciliation.
- R9. Ordinary Saga paths must not depend on advanced Outcome dispatch, cost, worktree, or compatibility machinery. Outcome orchestration remains an explicit advanced capability for genuinely cross-session or multi-worktree objectives.
- R10. Durable-artifact reconstruction must remain the normal resume path. Local transcript forensics remains an operator-confirmed last resort rather than a dependency of ordinary `/loop`, `/work`, or re-entry behavior.
- R11. The review must produce evidence-backed `keep`, `simplify`, and `retire` dispositions for overlapping routers, duplicated persistence, compatibility-only code, repeated skill prose, and unreachable runtime branches. Any `retire` disposition that changes public behavior remains blocked until the operator approves it.

**External harness invocation**

- R12. Saga must be able to invoke an external harness directly, and Verified Workflows must be able to use the same harness capability as a bounded worker or reviewer. The capability may be invoked repeatedly; it is not limited to a single call or stage.
- R13. External support must be extensible through a small adapter contract that declares only the harness's actual model, effort, tool, egress, authentication, and write capabilities. Adding a harness must not require changes to Saga lifecycle semantics or add onboarding, promotion, preference, claim/replay, or action-state machinery.
- R14. An explicit user request or an approved Verified Workflow contract must authorize the matching external invocation without a second plugin-specific confirmation. A material expansion of provider or harness, model or cost tier, outbound context, credentials, write scope, permissions, or effect must return to the caller's normal approval boundary.
- R15. Before process launch or any workflow-state mutation, the adapter must validate the actual executable route, requested model and effort, required noninteractive capabilities, declared write mode, and required environment-key presence. Unsupported or mismatched routes must fail before launch with one actionable reason.
- R16. A CLI adapter must preserve the minimum host environment needed for the approved credential path, including `USER` when macOS Keychain lookup depends on it. Results must distinguish launch-user presence, credential-source observation, and provider-account identity, permit `unknown`, and never infer authentication from `USER` or model prose.
- R17. A direct Saga invocation outside Verified Workflows must remain read-only. An approved Verified Workflow may give an external harness direct ownership of explicit, non-overlapping workspace paths.
- R18. The Codex root session must remain the only Git actor and must compare the external harness's actual changed paths and Git state with its assignment before accepting the result. Out-of-scope edits or Git metadata mutation must fail the assignment and pause integration.
- R19. External results remain non-gating under the current V2 contract. The root may independently verify and adopt their work or findings, but raw external output cannot pass a check or reviewer gate.
- R20. The caller must own sequencing, retry decisions, interruption handling, and durable evidence. Useful direct-call output belongs in the Saga artifact, and Verified Workflow output and diff evidence belong in its normal run record; no separate external-action store, approval fingerprint, status card, claim/replay record, or consumption lifecycle is required.
- R21. Every adapter must block literal credentials and undeclared secret-bearing paths from outbound context, report unavailable or invalid execution honestly, and return requested-versus-observed model and effort information when the harness exposes it.

**Port intake and capability acceptance**

- R22. Every source-derived refresh must continue to use the mandatory Claude-to-Codex port runbook and its classification gate.
- R23. Before source-derived behavior changes, the port intake must reconcile the actual branch diff with the declared port-manifest path scope. Every uncovered behavior-bearing path must be classified as source-derived, Codex-local, intentionally divergent, deferred, or blocked.
- R24. Port acceptance must prove the promised Codex capability and authority boundary rather than byte parity with Claude or completeness of a theoretical provider matrix.
- R25. Each delivery capability must name its operator path, touched runtime surfaces, before-and-after observations, focused checks, and known proof limits. The repository-wide validation result remains separately visible.
- R26. Validation output must distinguish failures on changed paths from unchanged repository failures without suppressing either result or claiming that existing debt was introduced by the current work.
- R27. External-adapter acceptance must use focused user-path canaries for route selection, requested model and effort, required environment preservation, unsupported-capability refusal, scoped writes where applicable, and sanitized observed identity. Each supported adapter proves its declared contract; the fleet does not need an exhaustive cross-product matrix.

**Transcript forensics and re-entry**

- R28. Session discovery must support the current date-based Codex session layout, and extraction must recover bounded user and assistant content from current `response_item` records without reproducing tool input, tool output, or hidden reasoning.
- R29. Transcript compatibility must be protected by small sanitized old/current fixtures that prove discovery and non-empty extraction and count unknown event types explicitly. Raw operator transcripts and unrelated conversation content must never become repository fixtures.
- R30. Transcript forensics must retain its same-machine, recency-capped, current-session-excluding, last-resort boundary and must not grow into a general transcript analytics or event-normalization subsystem.

**Admission, status, and closeout**

- R31. Dispatch admission must validate the selected role, result expectations, host capability, ownership, and external invocation contract before opening an attempt, writing a halt, or mutating durable workflow state.
- R32. A rejected dispatch must leave no half-open attempt or persistent halt and must remain safely retryable. An admitted dispatch must settle its attempt to a terminal or explicitly active state so halt and attempt records cannot silently diverge.
- R33. When the same failing evidence survives two completed repair or validation passes, Saga must classify the remaining problem as a product defect, test-oracle defect, or scope expansion and request one operator decision rather than starting another remediation workflow.
- R34. Operator progress must be rendered from existing Saga artifacts, checks, Git state, and recorded board state. The view must show the active phase and age, completed proof, executable or blocked frontier, validation failures by scope, last known board sync, and the exact remaining completion condition without adding persistence or monitoring.
- R35. Closeout must show branch and merge truth, local-main drift, staged and untracked files, known runtime-artifact directories, and transcript-like files. It must present explicit preserve, ignore, or remove choices and must never delete or settle anything automatically.
- R36. Completion must be derived only when the authoritative artifact, required checks, Git state, mutation-domain state, and approved finish condition agree. Otherwise the operator receives the exact unresolved condition rather than a generic success or failure label.

**Requirements-to-issue handoff**

- R37. Existing defects and enhancement issues must be reused as evidence or implementation slices when they match a requirement; the handoff must not create duplicate cards merely to fit a new hierarchy.
- R38. Contributing cards must use the Operations board's `improve-codex-plugins` Objective field. The handoff must not create an Objective issue or use parentage only to represent Objective membership.
- R39. A parent issue must represent a real outcome-level capability with two or more necessary, independently verifiable implementation slices. Requirements sections, individual tests, repository phases, and documentation edits must not become subissues by default.

## Key Flows

The normal flows preserve current entrypoints while shortening what happens underneath them.

- F1. **Review one operator path.** **Trigger:** a lifecycle capability enters simplification review. The maintainer traces the public promise to its callers, authority owner, artifacts, and runtime surfaces, classifies machinery as keep, simplify, or retire, and obtains approval for any public behavior removal. **Covers R1-R11.**
- F2. **Invoke an external harness directly.** **Trigger:** the operator explicitly asks Saga to use a named harness, model, and effort. Saga validates the exact route and credential environment, performs a read-only invocation, and records useful output in the current artifact without a second approval or external-action lifecycle. **Covers R12-R16, R20-R21.**
- F3. **Use an external harness in a Verified Workflow.** **Trigger:** an approved V2 contract assigns an external worker or reviewer. The adapter validates admission, the harness reads or edits only its assigned scope, and the root audits the diff, runs native checks and review, and records the normal role result. **Covers R12-R21, R31-R32.**
- F4. **Refresh a source-derived capability.** **Trigger:** a Claude plugin delta is selected for porting. The maintainer loads the port manifest, reconciles it with the actual diff, classifies every behavior-bearing path, adapts the promised Codex capability, and proves its focused user path before repository-wide validation. **Covers R22-R27.**
- F5. **Recover work without a durable artifact.** **Trigger:** no Saga artifact or resolvable issue can reconstruct same-machine work. The operator confirms transcript forensics, discovery excludes the current session and caps candidates, extraction reads only supported bounded content, and the recovered result is used as fallible context rather than authority. **Covers R8, R10, R28-R30.**
- F6. **Reject an inadmissible dispatch.** **Trigger:** a role, result contract, host capability, ownership boundary, or external route is invalid. Admission returns one reason before durable mutation, leaving no attempt/halt residue and allowing a later corrected retry. **Covers R15, R31-R33.**
- F7. **Report progress and close out.** **Trigger:** the operator asks what remains or whether work is complete. Saga derives the answer from normal artifacts and external domain truth, shows validation and repository dirt separately, and asks for an explicit choice only where preservation or cleanup is genuinely consequential. **Covers R33-R36.**

## Acceptance Examples

These examples pin the failure-prone boundaries without enumerating every theoretical edge case.

- AE1. **Requested Claude route runs without duplicate approval.** **Given:** the operator asks for Claude with a named model and maximum effort. **When:** the adapter validates that exact supported route and the required host environment. **Then:** it invokes the harness once under the original request, records the result in the caller's artifact, and creates no approval fingerprint or action-store record. **Covers R12-R16, R20.**
- AE2. **Missing `USER` fails before a misleading launch.** **Given:** the selected Claude credential path depends on macOS Keychain identity. **When:** the launch environment omits `USER`. **Then:** preflight reports the missing environment contract before spawning Claude and does not claim that the provider is unauthenticated. **Covers R15-R16.**
- AE3. **A material route expansion returns to approval.** **Given:** the operator approved a read-only external review. **When:** the caller proposes a different harness, higher cost tier, additional outbound paths, or workspace writes. **Then:** the caller updates its normal preview or workflow contract and requests approval; an unchanged retry does not. **Covers R14, R17.**
- AE4. **An external V2 worker edits assigned paths.** **Given:** an approved Verified Workflow assigns an external harness two non-overlapping source paths. **When:** the harness edits only those paths and performs no Git operation. **Then:** the root may accept the contribution after diff audit, deterministic checks, and native gate evidence. **Covers R17-R19.**
- AE5. **An external write-boundary violation fails integration.** **Given:** an external worker edits an unassigned file or Git metadata. **When:** the root audits the returned workspace state. **Then:** the assignment fails, integration pauses, and the external result cannot satisfy a gate. **Covers R18-R19.**
- AE6. **A new harness does not create a new lifecycle.** **Given:** a maintainer adds another external CLI. **When:** it implements the small adapter contract and its declared capability canaries. **Then:** Saga and Verified Workflows can invoke it without new approval states, provider promotion, claim/replay, or stage-specific integration branches. **Covers R12-R13, R20-R21, R27.**
- AE7. **An uncovered port path blocks classification.** **Given:** the actual branch diff changes a behavior-bearing dispatcher file outside the port manifest's path scope. **When:** the classification gate runs. **Then:** behavior changes stop until the path is classified or proved repository-local. **Covers R22-R24.**
- AE8. **Existing lint debt is not misattributed.** **Given:** focused capability checks pass and repository-wide validation reports failures only on unchanged paths. **When:** acceptance is summarized. **Then:** the capability proof and the failing full result are both reported, and the unchanged failures are not labeled as introduced by the change. **Covers R25-R26.**
- AE9. **Current transcript schema produces usable bounded context.** **Given:** recent Codex sessions live under date-based directories and store user and assistant messages as `response_item` records. **When:** the last-resort tools discover and extract a sanitized fixture. **Then:** discovery finds candidates, extraction yields non-empty bounded messages, and unknown event types are counted without retaining raw transcripts. **Covers R28-R30.**
- AE10. **Transient admission failure leaves no settlement residue.** **Given:** a dispatcher request has an invalid reviewer packet or unavailable external capability. **When:** admission rejects it. **Then:** no persistent halt or open attempt is written, and a corrected request may retry normally. **Covers R31-R32.**
- AE11. **Repeated validation residue becomes one decision.** **Given:** the same failing evidence remains after two completed passes. **When:** Saga reaches the stopping rule. **Then:** it classifies the residue and asks whether to repair the defect, correct the test oracle, or split the expanded scope; it does not silently launch another pass. **Covers R33.**
- AE12. **Closeout reports truth without automatic cleanup.** **Given:** a branch is merged but local main has drift and an untracked transcript-like file remains. **When:** the operator requests closeout. **Then:** the report distinguishes merge truth, drift, and sensitive dirt and asks whether to preserve, ignore, or remove the artifact without taking that action automatically. **Covers R34-R36.**
- AE13. **Verified Workflows remains unchanged when its proof passes.** **Given:** the current V2 contract, runtime readback, ownership audit, checks, and review flow all pass. **When:** the fleet review evaluates Verified Workflows. **Then:** it records the baseline as retained and does not redesign it merely to make every plugin look uniformly changed. **Covers R2, R4-R7.**
- AE14. **Issue decomposition reflects executable work.** **Given:** an existing defect already implements one independently verifiable slice of a larger capability. **When:** the requirements are handed off. **Then:** the existing issue is reused and linked under a genuine capability parent, while all contributing cards receive the `improve-codex-plugins` Objective field. **Covers R37-R39.**

## Success Criteria

Success means the common lifecycle is easier to operate because the code owns fewer concepts, not because complexity has moved into new names.

- Every capability parent reports a net reduction in active control machinery and a passing before-and-after operator-path proof.
- A requested external harness can run directly from Saga without duplicate plugin approval, while a Verified Workflow can assign it bounded workspace writes under existing V2 ownership and root verification.
- The Claude path preserves the requested model, effort, and required credential environment and distinguishes requested, accepted, and observed execution truth.
- No active normal path depends on the dedicated external-action approval fingerprint, claim/replay, provider-promotion, status-card, or action-store lifecycle.
- Verified Workflows retains its current V2 acceptance proof except for the explicitly approved external-write integration.
- Port classification detects behavior-bearing files omitted from the declared manifest scope before source-derived mutation.
- Transcript discovery and extraction pass current-schema canaries without checking in raw transcripts or making forensics a normal-path dependency.
- Dispatch rejection leaves no persistent attempt/halt contradiction, and repeated identical remediation stops at one explicit operator decision.
- Progress and closeout truth come from existing artifacts and domain state, with no new monitor or durable status store.
- Full-repository failures remain visible and accurately attributed without invalidating focused proof or hiding existing debt.

## Scope Boundaries

The program is fleet-aware but deliberately concentrates change where lifecycle complexity exists.

**In scope**

- Saga lifecycle internals, shared Fleet Core consumers, Mission Control and Deploy integration boundaries, and Verified Workflows external-role integration.
- Reconciliation of existing defects and enhancements that expose route truth, credential environment, settlement, repository hygiene, port classification, or obsolete Verified Workflow gates.
- Prompt, documentation, test, and validation changes required to keep the simplified behavior coherent.
- Regression and obvious-dead-weight review of the five narrower proof or operational plugins.

**Deferred for separate approval**

- Removal or semantic consolidation of any public skill entrypoint.
- Promotion of external results to independent reviewer or workflow-gate authority.
- Additional direct-mutation modes outside an approved Verified Workflow.
- Broad changes to Outcome as a product rather than isolation of its advanced machinery from the normal lifecycle.
- The exact parent/subissue topology and sequencing produced by planning and Mission Control handoff.

**Outside this program's identity**

- A replacement lifecycle product or second workflow engine.
- A provider marketplace, automated provider promotion system, or cost-optimization control plane.
- A durable mirror of external calls, Codex V2 tasks, Git state, or board state.
- Exhaustive certification of every model, provider, effort, role, and failure combination.
- Automatic branch deletion, artifact cleanup, issue closure, deployment, or other consequential closeout mutation.
- A general transcript archive, analytics product, or normalized event platform.
- Byte-for-byte mirroring of Claude plugins or reintroduction of retired plugin aliases.

## Dependencies / Assumptions

The simplification depends on existing domain contracts remaining available and independently verifiable.

- Codex V2 continues to provide the configured-agent, ownership, runtime-readback, messaging, review, and restoration behavior already proven by Verified Workflows.
- External CLIs expose enough deterministic capability or help output to validate the requested route before consequential work; unsupported claims remain explicitly unavailable.
- The mandatory port manifest and classification tooling remain the authority for source-derived refreshes.
- Git and GitHub can provide branch, merge, issue, project, and board facts needed for derived progress and closeout views.
- Codex transcript storage is not treated as a stable public API; small supported fixtures define the compatibility slice and expose drift.
- Mission Control and Deploy retain their current consequential-action previews and confirmations. This program removes duplicate lifecycle approvals, not safety boundaries at real mutation domains.
- Historical requirements, plans, reviews, and QA artifacts remain available as lineage even when this document supersedes their active product requirements.

## Outstanding Questions

No unresolved product decision blocks implementation planning.

**Deferred to planning and handoff**

- The exact keep, simplify, and retire inventory after caller and reachability analysis.
- The smallest adapter registration and result shape that satisfies R12-R21, including which currently advertised harnesses have active users beyond Claude.
- The enforcement and recovery mechanism for external direct writes that meets the existing V2 ownership and root-audit contract without recreating isolated-workspace machinery.
- The exact focused canaries and before-and-after complexity measures for each delivery capability.
- The mapping of issues #49-#59 into capability parents, standalone issues, or independently verifiable subissues without duplication.
- Release ordering, compatibility window, plugin version changes, and removal of obsolete documentation and tests.

## Sources / Research

These sources establish the existing product boundaries, prior requirements, current complexity, and concrete defect evidence.

- `README.md`: active plugin fleet, Codex-native adapter boundary, and validation contract.
- `plugins/saga/README.md` and `docs/saga/README.md`: normal lifecycle, execution-mode ownership, durable artifacts, and advanced Outcome boundary.
- `plugins/verified-workflows/skills/run/SKILL.md`: current V2 workflow, ownership, review, and runtime-proof contract.
- `plugins/mission-control/README.md` and `plugins/deploy/README.md`: domain-specific mutation ownership and consequential-action boundaries.
- `plugins/fleet-core/README.md`: active shared primitives and compatibility-only surfaces.
- `docs/brainstorms/2026-07-11-codex-external-advisory-execution-contract-requirements.md`: prior multi-provider action lifecycle superseded where it conflicts with R12-R21.
- `docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md`: V2 baseline, including the external-write limitation intentionally superseded by R17-R18.
- `docs/qa/qa-task-codex-v2-orchestrated-execution-system-2026-07-24.md`: current V2 live capability proof.
- `docs/reviews/2026-07-12-codex-plugins-improvement-review.md`: duplicated prose, shared primitives, oversized Outcome surface, and authority-risk findings.
- `docs/portability/claude-to-codex-plugin-port-runbook.md`: mandatory source classification and capability-first port procedure.
- `docs/portability/saga-family-capability-map.md`: active capability owners and retired alias boundary.
- `plugins/saga/skills/resume/references/session-forensics.md`: current last-resort transcript privacy and recovery constraints.
- GitHub issues [#49](https://github.com/infiquetra/infiquetra-codex-plugins/issues/49), [#50](https://github.com/infiquetra/infiquetra-codex-plugins/issues/50), [#51](https://github.com/infiquetra/infiquetra-codex-plugins/issues/51), [#52](https://github.com/infiquetra/infiquetra-codex-plugins/issues/52), [#54](https://github.com/infiquetra/infiquetra-codex-plugins/issues/54), [#55](https://github.com/infiquetra/infiquetra-codex-plugins/issues/55), [#56](https://github.com/infiquetra/infiquetra-codex-plugins/issues/56), [#57](https://github.com/infiquetra/infiquetra-codex-plugins/issues/57), [#58](https://github.com/infiquetra/infiquetra-codex-plugins/issues/58), and [#59](https://github.com/infiquetra/infiquetra-codex-plugins/issues/59): current route-truth, environment, settlement, hygiene, portability, V2, and simplification evidence.
