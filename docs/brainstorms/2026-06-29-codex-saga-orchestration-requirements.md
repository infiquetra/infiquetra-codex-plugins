---
date: 2026-06-29
topic: codex-saga-orchestration
maturity: requirements-ready
---

# Codex Saga Orchestration and Current-Saga Parity Requirements

## Summary

Bring `infiquetra-codex-plugins` Saga from the current Codex `0.22.1` surface to a Codex-native parity target for current Claude Saga `0.41.0`. Claude Saga is source material for intent, contracts, and tests; Codex owns the active operator surface through skills, references, bundled scripts, docs, validation, and explicit backend capability gates.

This is full current Saga parity, not only OutcomeOrchestrator. It includes `saga:outcome`, `saga:promote`, outcome orchestration substrate, status-card projection, completeness-gate safety, generated/operator docs, tests, and metadata updates once behavior exists.

## Problem Frame

The 2026-06-27 Claude-to-Codex update plan identified the missing Saga OutcomeOrchestrator slice, but that work never landed in Codex. Since then, Claude Saga advanced further: current Claude `origin/main` is `b30e0f2`, Saga is `0.41.0`, and it includes outcome orchestration, completeness-gate safety, shared status cards, and `promote`.

Current Codex `main` is `fce697c`, Saga remains `0.22.1`, and the active Codex skill set lacks `outcome` and `promote`. Team-execution agent roster work largely landed, but Saga's orchestration substrate, safety layers, docs, and tests did not. Continuing the old 6-27 plan directly would miss later drift and would risk treating Claude-only host primitives as if Codex could execute them.

The goal is not a lift-and-shift. `infiquetra-codex-plugins` is a curated Codex adapter repo, not a mirror. The parity target is behavior and operator value: Codex users should get the current Saga lifecycle and orchestration capabilities in Codex-native form, with unsupported Claude primitives clearly rejected or degraded rather than quietly advertised.

## Key Decisions

- **Full current Saga parity is the target.** Option B is selected: all current Claude Saga `0.41.0` surfaces that can be expressed safely in Codex are in scope, including `promote`.
- **Codex surface replaces slash-command assumptions.** Claude commands are not active Codex artifacts. `outcome` and `promote` become namespaced Codex skills, with any useful command argument contract mined into skill instructions or scripts.
- **OutcomeOrchestrator coordinates leaf work; it does not become the leaf worker.** The outcome layer owns DAG state, frontier, dispatch receipts, reporting, attention routing, and durable reconstruction. Leaf implementation still routes into native Saga phases such as `plan`, `work`, `qa`, `code-review`, `resume`, or `team-execution`.
- **Backend truth is capability-gated.** Codex may actively offer `inline`, `manual`, `team-execution`, and conditional subagent delegation when the runtime exposes it and the task is safe. Claude Workflow, fork, goal, and hooks remain unavailable unless a real Codex equivalent is proven with tests.
- **Codex harness affordances are positive scope.** The adaptation must inventory what Codex can do that Claude cannot, not only subtract Claude-only primitives. Current Codex affordances such as namespaced skills, lazy-loaded tools, managed Codex agent TOMLs, explicit patch editing, local plugin validation, and conditional multi-agent tooling must be deliberately used, deferred, or rejected.
- **Safety/operator layers are first-class parity, not polish.** Completeness gate and status card work are in scope because they protect the expanded orchestration surface from silent omission and attention overload.
- **Promote is a Saga parity surface, not an outcome subcommand.** `saga:promote` belongs in the parity target because Option B covers current Saga, but it remains a separate journal-promotion workflow with its own write gate.
- **State stays Codex-native.** Runtime and durable local state must use `.codex/saga` or documented repo artifacts, never `.claude/saga`, installed cache copies, or untracked hidden state that cannot be reconstructed.
- **Terminal output stays terminal-safe.** Default operator output uses ASCII/status-card/prose. Mermaid may appear only in explicit docs or export artifacts, not as the default chat/CLI answer.
- **Versions and docs follow behavior.** Saga manifest, README, marketplace inventory, validation inventory, changelog, and generated docs update only after the corresponding Codex-visible behavior and tests exist.

## Actors

- A1. Codex operator: uses Saga skills in normal Codex sessions and needs truthful capability menus, durable re-entry, and concise status.
- A2. Plugin maintainer: ports and adapts Claude Saga behavior into Codex-native plugin surfaces.
- A3. Outcome coordinator: owns outcome-level DAG state, frontier advancement, dispatch receipts, reports, and attention routing.
- A4. Leaf Saga worker: executes the normal lifecycle phase for a subplot through existing Saga or team-execution flows.
- A5. Team-execution runtime: provides reviewer/validator orchestration through managed Codex agents when available and serial fallback when not.
- A6. Journal promotion operator: runs the `promote` workflow and approves any context-library write.
- A7. Reviewer/planner: verifies that parity is behaviorally meaningful and that unsupported Claude primitives are not exposed as active Codex behavior.

## Requirements

**Source Truth And Classification**

- R1. The work must freeze and record both source baselines before implementation planning: Codex `main` at `fce697c` and Claude `origin/main` at `b30e0f2`, or refreshed equivalents if either advances before planning begins.
- R2. The parity analysis must classify both drift windows: historical missing slice `80e8731..aad9d6a` and newer drift `aad9d6a..origin/main`.
- R3. Every changed Claude Saga surface must be classified as `codex-adapt`, `direct script port`, `test oracle`, `defer`, or `reject`.
- R4. Codex-only Saga skills already present, including `ceo-review`, `implementation-spec`, and `product-review`, must be preserved unless a separate explicit decision removes them.

**Codex-Native Surface**

- R5. `outcome` must be exposed as `saga:outcome`, with Codex skill instructions and script-backed operations rather than an active Claude command file.
- R6. `promote` must be exposed as `saga:promote`, with the same Codex skill pattern and explicit approval gate before any context-library write.
- R7. Active Codex plugin roots must not include Claude `.claude-plugin`, `commands`, `agents`, or hooks as executable surfaces.
- R8. Any Claude command text reused for argument contracts must be transformed into Codex skill guidance, not copied as a command.
- R9. Skill instructions must state when the runtime should ask the operator in chat because a richer question tool is unavailable.

**Outcome Orchestration**

- R10. Outcome orchestration must model a whole outcome as a durable DAG of subplots, not as a single linear Saga phase.
- R11. Outcome state must be reconstructable from committed spec/store artifacts and durable completion evidence, not from an in-memory chat session.
- R12. The outcome coordinator must support start, status/report/project, graph, advance, attend/resume, commit/export/import, approve/prune/promote graph edits where Codex equivalents are safe and tested.
- R13. Repeated advance/reconcile operations must be idempotent and must not double-dispatch leaf work.
- R14. Invalid outcome specs must fail before any dispatch or mutation.
- R15. Code leaf completion must require merged PR or equivalent explicit completion evidence; non-code leaf completion must require durable completion evidence that survives machine/session changes.
- R16. Negative terminal states such as failed, rejected, stalled, or blocked must remain visible and must not be masked as successful completion.
- R17. Worktree lifecycle, liveness, merge queue, completion barrier, and economics/reporting behavior from Claude must be adapted where Codex can prove the same operator value.

**Backend Capability Model**

- R18. The active safe backend floor is `inline`, `manual`, and `team-execution`.
- R19. Codex subagent delegation may be offered only when callable tooling exists in the current session and the task is safe to delegate.
- R20. Claude Workflow, fork, goal, and hooks must remain unavailable in active Codex menus unless a specific Codex equivalent is designed, implemented, and tested.
- R21. If a selected backend is unavailable before side effects occur, the coordinator must emit a visible halt/degrade receipt rather than silently substituting behavior.
- R22. If side effects may already have occurred, the coordinator must halt for operator attention rather than rerunning on a weaker backend.

**Completeness Gate**

- R23. The parity target must include a completeness gate for fan-out or delegated leaves where structured output or evidence is expected.
- R24. Missing output, malformed output, missing required keys, and missing required evidence must become loud typed failures.
- R25. Completeness failures must block dependent work rather than releasing partial or absent return envelopes downstream.
- R26. The gate must include an on-demand self-test path proving a planted omission is caught without touching live workspace state.
- R27. Completeness checks must distinguish legitimate no-output leaves from leaves that omitted expected output.

**Status Card And Operator UX**

- R28. Saga status-bearing surfaces must converge on one shared status-card renderer or shared rendering contract for operator-facing status.
- R29. The status card must be derived on read from durable state or evidence, never from operator-writable status fields.
- R30. `outcome` status must reuse or adapt the outcome projection as the single source for progress, frontier, blockers, attention, and negative terminals.
- R31. `/work`, `/code-review`, `/qa`, `/outcome`, and `/resume` status boundaries should use consistent labels and traceable evidence where their data exists.
- R32. Unknown or not-yet-reached status must render honestly as unknown/not-reached, not as done.

**Promote**

- R33. `saga:promote` must remain a journal-promotion workflow, not an outcome orchestration feature.
- R34. `promote` must scan workspace engineering journals read-only, exclude self-feed from the context-library, and write only to `infiquetra-context-library`'s engineering journal after explicit approval.
- R35. Promotion must be sparse and judgment-based: it promotes cross-repo or explicitly marked transcendent lessons, not every generalizable note.
- R36. Promotion must be idempotent through stable source keys or an equivalent ledger so reruns do not duplicate entries.

**Docs, Metadata, And Validation**

- R37. Saga docs in `docs/saga` must be regenerated or updated to describe the Codex-native surface, not copied wholesale from Claude's `plugins/saga/docs`.
- R38. Saga plugin metadata, README, marketplace inventory, validation expectations, and changelog must agree after behavior lands.
- R39. Validation must fail if manifests advertise `outcome` or `promote` before their Codex skills/scripts/tests exist.
- R40. The test suite must include adapted coverage for outcome spec/store/dispatcher/projection/report/replay/liveness/worktrees/merge/economics, completeness gate, status card, promote scan, team emitter, operator-choice drift, workflow emission, and override rate where those concepts remain active.
- R41. Final validation must include targeted Saga tests, plugin validation, generated-doc checks when relevant, and full repository pytest with `PYTHONPATH=.`.

**Harness Delta And Mutation Boundaries**

- R42. Planning must produce a Codex-vs-Claude harness delta table before implementation begins.
- R43. The harness delta must map Claude primitives to one of: active Codex implementation, explicit unavailable/degraded behavior, deferred follow-up, or rejected lineage-only context.
- R44. The harness delta must also map Codex-only affordances to one of: required implementation mechanism, optional enhancement, deferred follow-up, or deliberately unused.
- R45. Codex-only affordances to classify include namespaced skills, lazy-loaded tools, conditional multi-agent/subagent tooling, managed Codex agent TOMLs, explicit patch editing, local plugin validation, and installed-cache source-truth boundaries.
- R46. Mutating operations from Claude, including GitHub writes, commits, pushes, auto-merge, worktree cleanup, context-library journal writes, or generated state publication, must default to preview/dry-run/propose-only behavior and require explicit operator approval unless a specific Codex-safe automation policy is tested and documented.
- R47. Tests for inactive Claude primitives such as Workflow, fork, goal, and hooks must be negative or capability-gate tests, not success-path emission tests, unless the implementation explicitly activates a proven Codex equivalent.

## Key Flows

- F1. **Refresh and classify source drift.** **Trigger:** planning begins. The maintainer verifies current Codex and Claude refs, computes historical and newer drift windows, classifies every Saga surface, and records explicit in-scope/defer/reject decisions. **Covers R1, R2, R3, R42, R43, R44, R45.**
- F2. **Start an outcome.** **Trigger:** operator invokes `saga:outcome` to start or load an outcome. The skill creates or reads a durable outcome spec/store, validates the DAG, prints a terminal-safe status/projection, and offers only Codex-proven next actions. **Covers R5, R10, R11, R14, R28.**
- F3. **Advance a ready frontier.** **Trigger:** operator runs an outcome advance/reconcile action. The coordinator derives ready leaves, checks backend capability, dispatches or halts each leaf with visible receipts, and records evidence without double-dispatching repeated ticks. **Covers R12, R13, R18, R19, R20, R21.**
- F4. **Handle blocked or failed leaves.** **Trigger:** a leaf fails, stalls, is rejected, lacks evidence, or hits an unavailable backend. The coordinator surfaces the issue in one status projection, blocks only dependent subtrees, and routes hands-on repair through native Saga re-entry. **Covers R16, R21, R22, R23, R25, R30.**
- F5. **Render operator status.** **Trigger:** a Saga surface reaches a status boundary. It renders a fixed, traceable status card from durable state, using shared vocabulary and honest unknown states. **Covers R28, R29, R31, R32.**
- F6. **Promote transcendent learnings.** **Trigger:** operator invokes `saga:promote`. The skill scans repo journals read-only, clusters sparse candidates, proposes a context-library journal diff, waits for approval, and writes only the approved destination. **Covers R33, R34, R35, R36.**
- F7. **Finalize parity metadata.** **Trigger:** behavior and tests pass. Maintainer updates manifest/version/docs/marketplace/validator/changelog together and runs validation gates. **Covers R37, R38, R39, R40, R41, R47.**

## Acceptance Examples

- AE1. **Outcome skill exists without Claude commands.** **Given:** Codex Saga parity lands. **When:** the plugin inventory is inspected. **Then:** `plugins/saga/skills/outcome/SKILL.md` exists, but Claude `commands/outcome.md` is not an active Codex surface. **Covers R5, R7, R8.**
- AE2. **Unsupported backend does not masquerade as available.** **Given:** an outcome leaf recommends a Claude-only Workflow backend. **When:** Codex has no proven equivalent. **Then:** the coordinator emits a visible unavailable/degraded receipt and offers a safe Codex backend or halt path. **Covers R18, R20, R21.**
- AE3. **Advance is idempotent.** **Given:** a ready leaf has already been dispatched and recorded. **When:** `advance` is run again. **Then:** the same leaf is not dispatched twice and the status projection stays consistent. **Covers R11, R13.**
- AE4. **Silent omission blocks dependent work.** **Given:** a delegated leaf expected structured output. **When:** the leaf exits without required output or evidence. **Then:** the completeness gate emits a typed failure and dependent leaves do not start. **Covers R23, R24, R25.**
- AE5. **Status is traceable and honest.** **Given:** tests have not run for a work item. **When:** the status card renders. **Then:** the test row shows unknown/not-reached rather than done, and determinable cells include references to their source evidence. **Covers R28, R29, R31, R32.**
- AE6. **Promote writes only behind approval.** **Given:** `saga:promote` finds a cross-repo learning candidate. **When:** it prepares a context-library journal update. **Then:** it shows a proposed diff and waits for explicit approval before writing, and it does not modify source repos or SDLC state. **Covers R33, R34, R35.**
- AE7. **Metadata cannot get ahead of behavior.** **Given:** `outcome` or `promote` is listed in Saga metadata. **When:** plugin validation runs. **Then:** validation fails if the corresponding skill/script/test surface is missing. **Covers R37, R38, R39.**
- AE8. **Harness delta blocks lift-and-shift.** **Given:** Claude provides a slash command, hook, Workflow backend, or `AskUserQuestion` interaction. **When:** planning classifies it. **Then:** the plan names the Codex-native replacement, unavailable/degraded path, deferral, or rejection; it does not copy the primitive by default. **Covers R42, R43.**
- AE9. **Codex-only affordance is considered deliberately.** **Given:** the current Codex session exposes conditional multi-agent tooling. **When:** outcome backend planning runs. **Then:** the plan either uses it behind safety gates, defers it with rationale, or rejects it; it does not ignore it because Claude did not have the same harness. **Covers R44, R45.**
- AE10. **Mutation stays operator-gated.** **Given:** a Claude outcome flow would auto-merge or push. **When:** the Codex implementation reaches that action. **Then:** it previews/proposes the mutation and waits for explicit approval unless a tested Codex-safe automation policy covers it. **Covers R46.**

## Success Criteria

- Current Codex Saga advertises the same intentional lifecycle surface as current Claude Saga where Codex can safely support it.
- Unsupported Claude-only primitives are visible only as lineage or unavailable choices with explicit receipts.
- Codex-only harness affordances are either used intentionally or explicitly deferred/rejected with rationale.
- `saga:outcome` can be used to inspect, report, advance, and recover an outcome without losing DAG state across sessions.
- Completeness and status-card layers reduce silent failure and operator attention cost rather than adding prose-only decoration.
- `saga:promote` works as a gated, idempotent journal-promotion workflow.
- Repository validation and targeted tests prove behavior before version and inventory metadata are bumped.

## Scope Boundaries

- No full mirror of `infiquetra-claude-plugins`.
- No active Claude `.claude-plugin`, `commands`, `agents`, or hooks in Codex Saga.
- No installed Codex cache edits; this repo remains source truth.
- No activation of `redis-channel` or unrelated plugins.
- No claim that Workflow/fork/goal/hook backends work in Codex until separately proven.
- No silent writes to GitHub, SDLC, deployment state, or context-library journal from Saga parity work.
- No automatic merge, push, worktree cleanup, or cross-repo write path without preview and explicit approval unless a tested Codex-safe policy is documented.
- No default Mermaid in terminal/chat output.
- No removal of Codex-only Saga skills as part of parity unless separately approved.

## Dependencies / Assumptions

- Team-execution's current Codex agent roster and serial fallback remain available as the primary delegated backend boundary.
- The planner will refresh Claude/Codex refs if either repository advances before implementation begins.
- Some Claude tests will become Codex test oracles rather than literal tests because command/runtime assumptions differ.
- Generated docs may require adaptation to this repo's existing `docs/saga` layout rather than Claude's `plugins/saga/docs` layout.
- Full parity may require several implementation commits, but the release is not complete until behavior, docs, metadata, and validation agree.

## Outstanding Questions

**Resolve before planning**

- None. Option B selected full current Saga parity as the target.

**Deferred to planning**

- Exact implementation sequence and commit slicing.
- Whether status-card migration lands before or after the first usable `saga:outcome` read/report path.
- Which Claude tests can be reused directly and which must be rewritten around Codex skills.
- Exact Saga version number for the Codex release after parity lands.
- Which Codex-only affordances are present in the implementation session and should become required mechanisms rather than optional enhancements.
- Whether any Codex runtime support now exists for additional backend primitives beyond `inline`, `manual`, `team-execution`, and conditional subagents.

## Sources / Research

- `AGENTS.md`: repo is a Codex-native adapter, not a full Claude mirror; active skill surface lives under `plugins/<name>/skills`.
- `README.md`: current Codex Saga is `0.22.1`; active plugin table does not include current Saga parity.
- `docs/plans/2026-06-27-port-recent-claude-plugin-updates.md`: original missing plan for OutcomeOrchestrator and team-execution agent roster.
- `docs/brainstorms/2026-05-27-codex-plugin-repo-requirements.md`: establishes curated adapter repo and host-specific divergence rules.
- `docs/brainstorms/2026-06-06-codex-saga-family-replacement-requirements.md`: establishes Saga-family ownership boundaries, Codex backend set, and `.codex/saga` state.
- `docs/portability/provenance.md` and `docs/portability/matrix.md`: existing port provenance and plugin treatment matrix.
- `docs/engineering-journal/DECISIONS.md`: records active Codex backend set and rejection of Claude command/agent/manifest surfaces.
- `docs/engineering-journal/LEARNINGS.md`: records porting validation lessons and drift-check expectations.
- Claude `origin/main` at `b30e0f2`: current Saga `0.41.0` source material, including `outcome`, `promote`, completeness gate, status card, tests, and docs.
- Codex `main` at `fce697c`: current Codex source state before parity work.

## Recommended Next Step

Run `/plan` against this requirements document. The plan should refresh refs, build an explicit surface classification table, then sequence implementation by dependency: substrate and capability profile first, outcome read/report path, dispatch/reconcile, safety/operator layers, promote, docs/metadata, and final validation.
