---
date: 2026-07-24
target: docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md
reviewed_revision: working tree at f3e1af75d06ac4c64a499f05e99c54903d978f35
blocked: false
review_type: implementation-readiness-with-external-advisory
---

# Codex V2 Orchestrated Execution System Plan Review

## Applied Fixes

The review closed every actionable native and Claude finding while preserving the approved minimal-kernel scope and main-session orchestration model.

| id | priority | status | finding | applied fix |
|---|---|---|---|---|
| F-01 | P1 | resolved | Rollback state was captured in U1 but could be stale by the U8 host cutover. | Kept U1 as lineage only and required a fresh private capture immediately before host mutation, including the repository rollback ref, three installed plugin versions, project/user config, managed profiles, and model catalog. |
| F-02 | P1 | resolved | Changed-path and Git-authority enforcement had no concrete audit mechanism. | Added a lightweight pre/post audit of HEAD, branch, index, bounded Git-control state, and porcelain-v2 paths; writable attempts are sequential unless V2 proves per-agent mutation attribution, and any ownership or Git divergence hard-fails. |
| F-03 | P2 | resolved | Review assignments could run before the isolated R46 and Luna/candidate proof. | Added an explicit `isolated-proof` assignment between migration and all three reviewers and required complete proof reruns after relevant remediation. |
| F-04 | P2 | resolved | U6 consumed U4 run-record and audit behavior but depended only on U3. | Made U6 depend on both U3 and U4 and aligned the workflow row to `contract, native-runtime`. |
| F-05 | P2 | resolved | Changes after reviewer approval had no closed rereview rule. | Added a narrow allowlist for faithful review/QA transcripts, PR metadata, and generated outputs from unchanged inputs; all other semantic changes return to applicable review, and behavior/config/runtime-proof changes rerun the full matrix. |
| F-06 | P3 | resolved | Listing `.codex/agents/*.toml` as modified could invite direct edits to generated copies. | Marked `plugins/verified-workflows/agents` as maintained source and `.codex/agents` as byte-identical generated project-discovery copies that must never be hand-edited. |
| F-07 | P3 | resolved | Reviewer descendants of the implementation root could not satisfy the origin's independence requirement. | Required separately started fresh V2 review-root sessions with no implementation turns; the implementation root validates returned typed results and remains the final orchestrator. |
| N-01 | P1 | resolved | The plan deferred too much of the workflow serialization contract to implementation. | Defined exact assignment, check, and external-action columns; root-row reservations; parent, context, fallback, external path, and non-gating authority grammars; and one digest over all three tables. |
| N-02 | P1 | resolved | The classification gate and retired-code migration lacked exact artifact and path inventories. | Named the new port manifest, version-policy sidecar, generated classification, protected old manifest, exact deleted modules/tests, rewritten surfaces, and retained historical artifacts. |
| N-03 | P1 | resolved | The release assumed authority to write tracked `.codex`, Git, GitHub, and current-user Codex state. | Added a blocking U8 authority preflight and an explicit pause/resume path that cannot downgrade proof, review, or rollback gates. |
| N-04 | P2 | resolved | External shared-workspace writes were broader than the current registry and contained-adapter contract could safely enforce. | Required registry `write_capable` plus adapter import support, retained provider execution in the contained clone, and made only the root adapter import validated patches after path, Git, base, dirty-overlap, egress, and secret checks. |
| N-05 | P2 | resolved | The run record was assigned to Saga's project state even though Verified Workflows already has owner-controlled user state and project `.codex` may be unwritable. | Moved the canonical record to `~/.codex/verified-workflows/state/<repo>/workflow-runs/`, retained the repository identity guard, and limited project state to a tested writable fallback. |
| N-06 | P2 | resolved | Candidate versioning, installed-byte proof, review, and final release edits had contradictory sequencing. | Prove source behavior and Luna first, mint one aligned candidate set, install and prove those exact bytes, review them, constrain later edits, then proceed through PR, merge, host cutover, rollback, and reapply. |
| N-07 | P3 | resolved | Several major sections lacked opening verdicts and one hard-to-disagree decision still assigned version choice to U7. | Added concise section-opening conclusions and corrected version choice to U8 after initial behavior and Luna proof. |

## External Advisory Evidence

Claude Fable/xhigh supplied the requested independent read-only second opinion. Codex root independently checked all seven returned findings against the requirements, plan graph, repository files, portability runbook, agent generation path, external-action contracts, and state-location code before adopting them.

| field | first attempt | successful bounded retry |
|---|---|---|
| provider | Claude CLI 2.1.218 | Claude CLI 2.1.218 |
| requested model and effort | `fable`, `xhigh` | `fable`, `xhigh` |
| observed model | `claude-fable-5` in CLI usage receipt | `claude-fable-5` in CLI usage receipt |
| effort evidence | `xhigh` in invocation; terminal receipt did not independently echo effort | `xhigh` in invocation; terminal receipt did not independently echo effort |
| access | safe mode, plan permission, `Read`/`Grep`/`Glob`, no writes or shell | safe mode, read-only, at most four `Read` calls, no writes or shell |
| context | plan-oriented review packet | plan, origin requirements, requirements review, and `AGENTS.md` |
| terminal status | no usable review result after budget exhaustion | completed successfully with typed `ready-with-fixes` result |
| turns | 32 | 6 |
| duration | 317.697 seconds API; 394.868 seconds total | 266.067 seconds API; 264.780 seconds total |
| reported cost | USD 3.404517 | USD 1.832217 |
| findings | none adopted | 7: 2 P1, 3 P2, 2 P3 |
| authority | advisory only | advisory only; final classifications and fixes are Codex-root decisions |

The stage bundle resolved to `External actions: []`, and the operator explicitly requested the same direct Fable/xhigh second-opinion exception used for the requirements review. No external-action policy or approval boundary was changed, and no Claude output was accepted without local verification.

## Readiness Summary

The plan is ready for `saga:work`; no unresolved P0, P1, P2, or P3 finding remains.

The workflow now exposes the orchestrator's exact assignments, checks, reviewers, fallback envelope, and external-action state; closes reviewer independence and release ordering; names the retired and replacement surfaces; and makes live V2 proof, Git authority, host cutover, and rollback blocking rather than assumed.

## Remaining Findings by Priority

No implementation-readiness finding remains after the verified fixes.

| priority | status | finding |
|---|---|---|
| None | closed | No unresolved implementation-readiness finding remains. |

## Review Result Contract

The review is unblocked and the plan may proceed to implementation under its inline workflow contract.

| field | value |
|---|---|
| target path | `docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md` |
| reviewed revision | working tree at base `f3e1af75d06ac4c64a499f05e99c54903d978f35` |
| blocked | false |
| finding priorities and statuses | 5 P1 resolved; 6 P2 resolved; 3 P3 resolved; none remaining |
| applied fixes | contract serialization; audit and Git authority; exact portability and migration inventory; generated profile ownership; run-record state; external patch import; proof/review/version sequencing; deployment preflight; fresh rollback capture |
| external review | Claude CLI Fable/xhigh, two read-only attempts, 7 findings from the successful bounded retry, all root-verified |
| review artifact path | `docs/reviews/2026-07-24-codex-v2-orchestrated-execution-system-plan-review.md` |
| override rationale | none |

## Residual Risk

This review establishes implementation readiness, not live Codex 0.145.0 behavior. Exact V2 readback, Luna leaf capability, Ultra root isolation, external patch import, candidate-byte proof, current-host installation, and rollback/reapply remain explicit U8 gates. The present session cannot write tracked `.codex`, Git metadata, or current-user Codex state, so U8 must pass its authority preflight and resume in a suitable session rather than treating this review as deployment proof.
