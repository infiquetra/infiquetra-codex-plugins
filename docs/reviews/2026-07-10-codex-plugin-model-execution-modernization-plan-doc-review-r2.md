# Doc Review Round 2: Codex Plugin Model, Execution, and Upstream Modernization Plan

This is the historical review of the first Codex-native execution amendment. The later Verified Workflows, role/profile, and port-contract amendment is reviewed in `docs/reviews/2026-07-10-codex-plugin-model-execution-modernization-plan-doc-review-r3.md`; use round three for the current verdict. Blocked: SUPERSEDED.

## Applied Fixes

Eight implementation-readiness findings were resolved from repository, runtime, and official Codex evidence.

| ID | Priority | Status | Finding | Applied fix |
|---|---|---|---|---|
| DR2-01 | P1 | FIXED | U3 could apply managed agents to the real profile before U8's isolated proof and cutover gate. | Limited U3 apply/readback to an isolated `CODEX_HOME`; added a real-profile refusal unless U8 supplies `--allow-real-profile` and the expected pre-state digest. |
| DR2-02 | P1 | FIXED | Generic children inherit parent permissions, so the plan's read-only labels were not enforceable on the active spawn surface. | Reclassified those labels as requested scope, selected parent `workspace-write` for U1-U7 when supported, reserved broader authority for root-only U8, and added pre/post mutation checks. |
| DR2-03 | P1 | FIXED | The plan had no hard preflight for pre-existing edits that overlap a unit's file set. | Added KTD14 and a per-wave HEAD/dirty-path snapshot; ambiguous overlap pauses the unit and existing user changes are never absorbed, rewritten, or deleted. |
| DR2-04 | P2 | FIXED | U3 installation wording could be mistaken for proof that Codex selected a named profile with the requested model and effort. | Made U3 installation-only and U4 the named-selection proof gate; generic child model, effort, agent type, and sandbox choices remain preferences without runtime readback. |
| DR2-05 | P2 | FIXED | Agent sync and hook receipt lookup did not share an explicit, safe Codex-home resolution rule. | Standardized both on explicit test target or `$CODEX_HOME/agents`, with `~/.codex/agents` fallback, canonical containment, managed-marker validation, and no payload-supplied path or digest. |
| DR2-06 | P2 | FIXED | “Independent review” did not define a clean Codex context boundary. | Required `fork_turns=none` for reviewers and validators with explicit plan, diff, acceptance, and check inputs; other children receive only minimum U-ID context. |
| DR2-07 | P2 | FIXED | Product-test-only wording omitted U7 even though U7 changes Team Execution advisory and consensus logic. | Limited Team Execution receipts/gates to U4/U8 evidence, identified U7 advisory/consensus tests separately, and barred all such evidence from accepting its own implementation. |
| DR2-08 | P3 | FIXED | The plan still routed to the review that this round was performing. | Marked the plan reviewed and changed the next step to overlap reconciliation, explicit execution approval, then `saga:work` U1 with Saga `inline`. |

## Readiness Summary

HISTORICAL PASS: no P0-P3 finding remained in the round-two document. The later material amendment supersedes this verdict.

The amendment removes the circular trust dependency cleanly:

```text
root Codex + Saga inline
        |
        +--> bounded generic children (helpers)
        |
        +--> root-owned diff, tests, review, and commits
        |
        +--> Team Execution only as U3/U4/U7/U8 product evidence
```

## Review-Result Contract

The durable review result is a clean plan verdict with a separate environmental preflight warning.

- Target: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`
- Reviewed revision: working tree at repository HEAD `718e8353dd90fe4a9a44d197741c40920d1926f2`; reviewed plan blob `c7299a3e794b9ea1f11dc0b937416da6c5664549`
- Blocked status: SUPERSEDED by the round-three review
- Classification: implementation plan
- Review type: readiness-skeptic plus compatibility, security, operations, current Codex capability, and deployment/cutover scrutiny
- Formal rubric phase: none; plan artifacts do not map to the idea, issue, or spec rubric phases
- Linked origin: `docs/plans/2026-06-27-port-recent-claude-plugin-updates.md`
- Linked Saga: `task-port-recent-claude-plugin-updates`
- Prior review: `docs/reviews/2026-07-10-codex-plugin-model-execution-modernization-plan-doc-review.md` (historical pre-amendment review)
- Review artifact: `docs/reviews/2026-07-10-codex-plugin-model-execution-modernization-plan-doc-review-r2.md`
- Current review: `docs/reviews/2026-07-10-codex-plugin-model-execution-modernization-plan-doc-review-r3.md`
- External review panel: not requested; skipped
- Operator override: none

## Verification Evidence

The current evidence supports every corrected decision while preserving runtime proof for U1-U8.

- Frozen source truth remains reproducible: `9470edc..38742ece` contains 156 focused files split 12 fleet-core, 63 Saga, 10 Team Execution, and 71 tests. The Claude checkout's current `HEAD` and local `main` are `321f74c65f80d4819e78f440c93d264a30862fab`; local `origin/main` is `7e8f84bc20fb7cf409d09151b4cdc2f33ca5b328`; the frozen target remains an ancestor.
- The plan maps all R1-R17 requirements, all nine origin requirements, KTD1-KTD14, and the acyclic U1-U8 dependency chain. Its eight `Files:` sections contain 143 unique path entries.
- The current roster contains 25 source profiles with the planned split: 10 opus/high reviewers, 8 sonnet/medium testers, and 7 haiku/low scanners or monitors. No Team Execution-managed profile is installed in the real `~/.codex/agents` directory.
- Live Codex is `0.144.1`; the local catalog exposes eight rows, including Sol, Terra, and Luna, scalar efforts through `max`, Ultra on Sol/Terra, and GPT-5.6 multi-agent versions. Global config currently selects Sol/max with `agents.max_threads=6` and `agents.max_depth=1`; this task exposes four total collaboration slots.
- The active generic spawn contract exposes task name, message, and fork context, but no per-child model, effort, named-agent, sandbox override, or selection readback. The plan now treats those choices as preferences until U4 produces hook-backed evidence.
- Official Codex documentation confirms that generic children inherit parent sandbox and permission settings; custom agent TOMLs may define `model`, `model_reasoning_effort`, and `sandbox_mode`; hook input exposes active `model`, `agent_type`, `agent_id`, `turn_id`, and permission mode; plugin hooks receive `PLUGIN_DATA` and require trust for the current definition.
- At review time, 13 currently modified paths overlap the plan's declared file set. KTD14 now makes that a required ownership/preflight decision rather than silently treating those edits as implementation output.

## Remaining Findings by Priority

No P0, P1, P2, or P3 finding remained in the round-two revision. Round three owns the current verdict.

## Review Artifact Path

This artifact remains the historical round-two verdict and is superseded by round three.

`docs/reviews/2026-07-10-codex-plugin-model-execution-modernization-plan-doc-review-r2.md`

## Residual Risk / Limited Evidence

The remaining risks are execution evidence that the plan deliberately defers to its implementation gates.

- The current generic spawn surface cannot prove a requested child model, effort, named profile, or read-only sandbox. U4 must produce a named hook/config receipt before delegated Team Execution can be enabled; otherwise the durable result remains `serial-only` and plan execution stays root-owned `inline`.
- The current worktree has overlapping user changes. `/work` must run KTD14's ownership and dirty-path preflight before U1 writes, and must pause rather than infer whether those changes belong to this plan.
- Codex catalogs, hook schemas, and host capacity can change after review. U1 captures a sanitized immutable capability snapshot and U8 refreshes it before real-profile cutover.
- This review establishes plan readiness, not shipped behavior. Targeted tests, independent review, full locked-environment validation, isolated-profile proof, fresh-session proof, and rollback readback remain mandatory.
