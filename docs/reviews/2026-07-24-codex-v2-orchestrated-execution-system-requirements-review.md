---
date: 2026-07-24
target: docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md
reviewed_revision: working tree at f3e1af75d06ac4c64a499f05e99c54903d978f35
blocked: false
review_type: requirements-readiness-with-external-advisory
---

# Codex V2 Orchestrated Execution System Requirements Review

## Applied Fixes

The review closed every native and external finding without changing the confirmed product scope.

| id | priority | status | finding | applied fix |
|---|---|---|---|---|
| F-01 | P1 | resolved | Strict assignments were referenced but not defined. | Defined strict work as workspace-mutating or authority-bearing and required root-verified runtime readback for every native assignment and descendant. |
| F-02 | P1 | resolved | Write ownership and worker Git prohibitions lacked detection and failure behavior. | Required changed-path audits, hard failure for out-of-boundary writes or worker Git mutation, integration pause, and verified workspace recovery. |
| F-03 | P1 | resolved | Four managed profiles lacked complete mappings and `review_max` could be confused with Ultra. | Added an authoritative six-profile table with exact model IDs, effort, workspace, external-access posture, and intended use; declared `review_max` Sol/max rather than Ultra. |
| F-04 | P1 | resolved | Reviewer dimensions, applicability, empty-set behavior, and hard-stop handling were undefined. | Bound dimensions to numbered role mandates, retained the 0-10 scale, constrained exclusions, made zero applicable dimensions fail, and defined unresolved P0/P1/security/role hard stops as blocking until fresh revalidation. |
| F-05 | P1 | resolved | The approved fallback envelope controlled reapproval but had no semantics. | Defined exact ordered profile allowlists and retry conditions with immutable role, scope, dependency, authority, write, egress, and permission ceilings; added a fallback acceptance example. |
| F-06 | P1 | resolved | Rollback covered machine configuration but not the repository state whose V1 support is removed. | Required a rollback package and exercise that restore the pre-cutover repository ref, project and user configuration, profiles, and model-catalog state from a post-migration starting point. |
| F-07 | P2 | resolved | Runtime verification ownership was ambiguous for direct children and descendants. | Made the root orchestrator the verifier using V2 runtime readback and extended the requirement to every declared descendant. |
| F-08 | P2 | resolved | Remediation counting and continuation after the third round were ambiguous. | Made the three-round counter global to one approved workflow run, prevented new findings from resetting it, and required a newly approved run to continue after pause. |
| F-09 | P2 | resolved | A failed attempt could leave ambiguous partial edits before retry. | Required the root to accept or clean up prior edits, restore a known workspace state, and record that decision before overlapping retry or remediation work. |
| F-10 | P2 | resolved | External egress was disclosed but not bounded. | Limited reads and transmission to declared context paths, limited writes to assigned paths, and blocked credentials or secret-bearing paths regardless of route approval. |
| F-11 | P2 | resolved | Typed final results had no minimum validity contract. | Defined common identity, status, summary, changed-path, check, and finding fields plus reviewer-specific dimensions, exclusions, arithmetic, typed findings, and hard-stop flags. |
| F-12 | P2 | resolved | Ultra, nested delegation, bounded context, and complete V2 proof lacked acceptance coverage. | Added explicit rejection and cutover-blocking examples for child Ultra, undeclared descendants, unbounded history, and incomplete V2 proof. |
| F-13 | P3 | resolved | Flow and acceptance mappings overstated coverage of runtime verification and external failures. | Removed the inaccurate mappings, kept verification under launch, and added a dedicated external-failure acceptance example. |
| F-14 | P3 | resolved | Reviewer independence was asserted but not defined. | Prohibited the implementer and its descendants from reviewing and required a self-contained packet without inherited implementer turns. |
| F-15 | P3 | resolved | The path from an external issue to a root-owned blocker was ambiguous. | Allowed the root to independently verify and adopt an external issue as a root-owned typed finding while keeping raw external output non-gating. |
| N-01 | P2 | resolved | The requirements verified provider identity but did not state V2's same-backend boundary. | Required profiles to execute on the root provider backend and prohibited implied or silent provider switching. |

## External Advisory Evidence

Claude Fable/xhigh supplied an independent read-only pass; Codex root verified every finding against repository evidence before applying it.

| field | value |
|---|---|
| provider | Claude CLI 2.1.218 |
| requested model and effort | `fable`, `xhigh` |
| observed model | `claude-fable-5` in CLI model-usage receipt |
| effort evidence | `xhigh` was present in the invocation; the result receipt did not independently echo effort |
| access | safe mode, `Read` only, no write or shell tools |
| target context | requirements document only |
| terminal status | completed successfully |
| advisory findings | 15: 6 P1, 6 P2, 3 P3 |
| duration and cost | 241.946 seconds; USD 1.22178 reported by the CLI |
| authority | advisory only; final classifications and fixes are Codex-root decisions |

The stage bundle resolved to no configured `doc-review` actions, and the operator explicitly authorized the requested direct Fable/xhigh dispatch instead of pausing on the empty policy bundle. No external output was used directly as gate evidence.

## Readiness Summary

The requirements are ready to drive `/plan`; no unresolved P0, P1, P2, or P3 finding remains.

The document now defines the authority-bearing assignment class, every managed profile, exact fallback behavior, reviewer scoring, workspace and egress enforcement, retry hygiene, typed-result floor, and full repository-plus-host rollback boundary. A planner can choose implementation mechanisms without inventing product behavior in those areas.

## Remaining Findings by Priority

No readiness finding remains after the verified fixes.

| priority | status | finding |
|---|---|---|
| None | closed | No unresolved readiness finding remains. |

## Review Result Contract

The review is unblocked and the requirements may proceed to implementation planning.

| field | value |
|---|---|
| target path | `docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md` |
| reviewed revision | working tree at base `f3e1af75d06ac4c64a499f05e99c54903d978f35` |
| blocked | false |
| finding priorities and statuses | 6 P1 resolved; 7 P2 resolved; 3 P3 resolved; none remaining |
| applied fixes | strictness and runtime verification; profile mappings; fallback semantics; reviewer rubric; write and egress boundaries; remediation and retry behavior; typed results; rollback; traceability and acceptance coverage |
| external review | Claude CLI Fable/xhigh, read-only, 15 advisory findings root-verified |
| review artifact path | `docs/reviews/2026-07-24-codex-v2-orchestrated-execution-system-requirements-review.md` |
| override rationale | none |

## Residual Risk

The review verifies requirements readiness, not live V2 runtime behavior. Exact permission readback, descendant restoration, Luna compatibility, Ultra isolation, current-Mac cutover, and the post-migration rollback drill remain explicit release proofs rather than claims established by this review.
