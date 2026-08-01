---
date: 2026-07-31
topic: verified-workflows-capability-policy-removal
maturity: requirements-ready
---

# Remove Verified Workflows' invented capability policy

## Summary

Verified Workflows enforces a capability policy that this plugin invented, that the Codex harness does not implement, and that contains nothing. Remove it, keep the dependency graph and the post-hoc evidence layer that make the plugin worth having, and correct the documentation and journal entries that still describe the root session as the sole Git owner.

## Problem Frame

Verified Workflows exists to decompose approved work into a dependency graph of Codex subagents, run it, and prove what happened. Layered on top of that is a second, separate thing: a per-role declaration of what an agent is *permitted* to touch, expressed as `workspace_cap`, `external_cap`, and `external_mutation` in the role registry, plus a hard pin from each role category to an exact set of execution profiles.

That layer has no enforcement behind it. Codex 0.146 children inherit the parent turn's effective permission profile, and a profile "cannot independently widen or narrow it" — the plugin's own canon says so at `plugins/saga/references/operator-choice.md:47-48`, repeated at `plugins/verified-workflows/README.md:75-76` and `plugins/verified-workflows/skills/run/references/delegation-safety.md:22-25`. The generated profile files confirm it: `plugins/verified-workflows/agents/work_medium.toml` carries a name, description, model, reasoning effort, and instruction text, and nothing that could constrain a sandbox or a network. There is no key to set.

So the declaration is a string in a YAML file that a validator compares against a hardcoded constant. `external_mutation` is hardcoded to `"forbidden"` for every role category at `plugins/verified-workflows/scripts/render_codex_agents.py:652-658`, and across all 28 roles `external_cap` only ever takes two values — `none` on 25 roles and `allowlisted-read` on 3 monitors. No vocabulary for external mutation exists anywhere in the schema, because the schema was written to forbid it universally.

The cost landed during the Hermes profile self-sovereign evolution workflow. The compiler assigned final Git integration and publication to `git-integration-operator`, the agent created the commit, and then could not push the branch or open the pull request. An explicitly approved root-session exception finished the work with the same credentials, which proves the blocker was declared policy rather than authentication. Work stopped on a constraint that protects nothing.

A second, smaller instance of the same pattern sits next to it. `git-integration-operator` is pinned to `work_medium` as its only allowed profile (`plugins/verified-workflows/config/role-registry.yaml:166-168`, `scripts/render_codex_agents.py:155-160`), and any deviation raises `role ... profile transition violates KTD4`. Publication was therefore forced onto medium-effort Terra regardless of what the approved plan wanted.

## Key Decisions

**Delete the capability policy rather than make it truthful.** An earlier reading of this defect asked which layer should carry a corrected declaration of external authority. The operator's call is that the plugin should not be authoring permission policy at all beyond what the Codex harness already implements. A subagent gets as much capability as the parent session, and the plugin does not pretend otherwise.

**The approved DAG is the product.** Once the operator approves the plan and its Workflow Contract, the root session orchestrates the graph. Deciding what a given node is allowed to do is not part of that job; deciding what runs, in what order, and whether the result is acceptable is.

**Keep the evidence layer; it is not policy.** Blocking a subagent before it acts and reporting what it changed after it acts are different mechanisms with different value. Codex gives you neither typed assignment results nor gate reduction for free, so the reporting half stays. The `writes` column becomes a declaration that results are reported against — a mismatch surfaces to the root as a finding rather than preventing compilation.

**Root-as-Git-owner is retired by a superseding journal entry, not a silent edit.** The claim is not vestigial. It was added on 2026-07-24 in commit `a695ffc`, and `docs/engineering-journal/DECISIONS.md:68` (2026-07-18, "Feasibility Review Keeps Root-Owned Workflows Usable") states it deliberately: the root "remains the owner of scope, mutation, integration, Git, gates, and completion; native child profiles remain bounded advisory workers **unless a runtime can provide authenticated host-issued child attestation**." That escape clause is now satisfied — the plugin validates child runtime identity through combined `session_meta` and `turn_context` readback on the canonical agent path. The record should show a condition that was met, not a history that was rewritten.

**Issue 71's own acceptance criteria are partly superseded.** The issue asks for external mutation to remain unavailable to non-publication agents and for the compiler to reject role/profile pairings with insufficient declared capability. Both presuppose the layer being removed. The issue body is rewritten from this document rather than satisfied as written.

## Design Comparison

Issue 71 required an explicit comparison of two named designs before any remedy is chosen. Both were considered and both are rejected, for the same reason: they rest on a premise the runtime does not support.

| Design | What it assumes | Why it is weaker here |
|---|---|---|
| Make `work_medium` publication-capable when dispatched as `git-integration-operator` | That an execution profile can carry permission, and can carry it conditionally on the dispatching role | A profile cannot widen or narrow inherited permission on Codex 0.146. The conditional would be enforced only by the compiler and by instruction text, so it would ship a second unenforceable claim while adding a role-dependent branch to profile resolution |
| Add a dedicated Git publication agent profile with the external mutation capability | That capability is a property a distinct profile can hold, making the grant visible and auditable | Same defect, plus a new profile, a new category, new render and sync coverage, and new digest surface — recurring maintenance in exchange for a guarantee that still does not exist. The visibility benefit is real but is already available from the approved contract, which names the exact Git commands in the assignment's completion condition |
| **Chosen — remove the capability layer** | That the harness owns permission and the plugin owns decomposition and evidence | Deletes the false claim instead of restating it, unblocks publication, removes the profile pin as a side effect, and shrinks the surface. Accepts openly that no plugin-side containment between subagents exists, because none ever did |

The honest summary of the rejected pair: they differ on *where* to write a promise that cannot be kept. Choosing between them would have produced a more elaborate version of the current defect.

## Requirements

**Removing the capability policy**

R1. The role registry no longer declares per-role capability caps. `workspace_cap`, `external_cap`, `external_mutation`, and `profile_may_not_widen_role` are removed from all 28 role entries in `plugins/verified-workflows/config/role-registry.yaml` and from the validator that asserts them against a per-category constant.

R2. A role no longer pins its execution profile. The per-category profile lock that raises `profile transition violates KTD4` is removed, so the approved contract's assignment row selects the profile — and therefore the model and reasoning effort — without registry veto.

R3. The compiler no longer refuses an assignment on capability grounds. Specifically it stops rejecting a non-Git role whose completion condition mentions `git` or `gh`, a read-only assignment that declares writes, and a fallback profile whose declared boundary differs from the primary's. The per-profile `workspace` and `external` declarations in `scripts/render_codex_agents.py` that feed those refusals go with them, since `workflow_dispatch.py:312` tests the resolved *profile* boundary rather than the role's.

R4. No plugin-side mechanism attempts to narrow what a subagent can do relative to its parent session. A subagent has the capability the Codex harness grants it. This includes deleting the `ROOT_ONLY_ACTIONS` tuple at `scripts/render_codex_agents.py:181-190`, which reserves `git-mutation`, `integration`, `merge`, `deploy-initiation`, `credential-change`, and `completion` to the root session; it has no consumer anywhere in the repository today, so removing it is a clarity fix rather than a behavior change.

R5. Generated profile instructions carry role scope, not capability prohibitions. The `work_medium` instruction telling the child not to run Git unless it is `git-integration-operator` is replaced with guidance to perform the assignment it was given and stay inside it.

R6. Publication actions — push, pull-request creation, tag, merge — execute at the assignment the approved contract names, with no fallback to the root session as the normal mechanism.

**Preserving the graph and the evidence**

R7. The dependency graph is unchanged: assignments, `depends`, acyclic validation, and dependency-ordered release all behave as they do today.

R8. Concurrent writer nodes still require disjoint declared write sets. This is graph correctness — two nodes racing the same file is a defect regardless of anyone's permissions — not capability policy.

R9. Typed results remain required. Every attempt still returns one closed `assignment-result.v1` or `reviewer-result.v1`, still validated by `result_contract.py`, and prose still never releases a dependency.

R10. Runtime readback remains required for identity: canonical agent path, selected profile, model, reasoning effort, provider, and V2 mode. Effective-permission and sandbox fields may still be recorded as observed facts, but no gate depends on them matching a plugin-declared boundary.

R11. Changed paths are still reported and still compared against the assignment's declared writes, but the comparison stops being fatal. Today `scripts/result_contract.py:252-253` raises `ResultContractError` on any undeclared path, which discards the entire typed result — so the assignment yields no usable evidence and its dependents never release. Instead the result must validate, with each undeclared path attached as a finding carrying a `scope_disposition` for root adjudication.

R12. The `git-integration-operator` completion condition still must include the final `git diff --name-only` validation, because that is how the changed-path evidence gets produced.

R13. Gate evaluation is unchanged. Missing required evidence, failed blocking checks, verified P0/P1 hard stops, and missing independence still block, and scores remain advisory.

R14. Reviewer independence rules are unchanged. Required-independence lenses, sibling launch with `fork_turns=none`, and the bar on an implementer reviewing its own work all stay.

**Correcting the record**

R15. `plugins/verified-workflows/README.md` stops describing the root session as the Git owner and stops implying that profiles carry permission or sandbox policy. The root is described as the orchestrator of an approved graph and the adjudicator of its evidence.

R16. `skills/run/references/delegation-safety.md`, `skills/run/references/workflow-protocol.md`, and `skills/review-workflow/SKILL.md:8` are corrected wherever they assert a capability boundary the plugin does not enforce — including the statement that a child cannot merge, deploy, or handle credentials, the requirement that a fallback stay inside the role's permission boundary, and the claim that the root owns integration and Git.

R17. `plugins/saga/references/operator-choice.md` keeps its factual statement that children inherit the parent's permission and a profile cannot widen or narrow it. What changes is the conclusion drawn from it: that fact is the reason a plugin-side capability declaration is pointless, not a reason to forbid the work.

R18. A superseding `docs/engineering-journal/DECISIONS.md` entry retires root-as-Git-owner and names **both** prior entries it supersedes — 2026-07-18 "Feasibility Review Keeps Root-Owned Workflows Usable" (`:68`) and 2026-07-24 "Codex V2 Owns Live Execution..." (`:50`, asserting root ownership of integration, Git, gates, and merge at `:52`) — and records that the child-attestation condition the earlier entry named has since been met. A companion `LEARNINGS.md` entry records the generalizable rule.

R19. The body of issue 71 is rewritten to state the actual defect and to replace the acceptance criteria that assume the capability layer survives.

**Proving it**

R20. A regression test reproduces the current failure: a contract that assigns publication to `git-integration-operator` must compile and dispatch, where today the declared capability contradicts the assigned action.

R21. A test proves an assignment may select any generated profile the approved contract names, so publication is no longer forced onto medium-effort Terra.

R22. A test proves an out-of-declared-writes change is reported as a finding on the assignment result rather than blocking compilation.

R23. Existing runtime-receipt coverage for agent path, profile, model, and reasoning effort continues to pass unchanged.

## Key Flows

F1. Approved graph with a publication node.

**Trigger:** the operator approves a plan whose Workflow Contract ends with a Git integration assignment.

The compiler validates the graph, the write sets, and the completion conditions, and binds the contract digest to the approved plan revision. It does not consult a capability declaration. The root launches each node as a direct child, validates runtime identity from readback, and releases dependencies on validated typed results. The publication node commits, runs `git diff --name-only`, pushes the branch, and opens the pull request. The root records the receipt and evaluates gates.

**Covers R2, R3, R6, R7, R9, R10, R12, R13.**

F2. A node writes outside its declared paths.

**Trigger:** an assignment's returned `changed_paths` include a path the contract did not declare.

The root compares reported paths against the declared write set and raises a finding with a `scope_disposition`. The operator or the existing one-hop deviation rule adjudicates it. Nothing was prevented from running; the evidence is what catches it.

**Covers R11, R13.**

## Acceptance Examples

AE1. Publication compiles and dispatches.

**Given** a Workflow Contract whose final assignment names `git-integration-operator` with a completion condition containing `git diff --name-only`, `git push`, and `gh pr create`, **when** the contract is compiled, **then** it validates and dispatches to that assignment, and no capability check rejects it.

**Covers R1, R3, R6, R20.**

AE2. Profile selection is the plan's call.

**Given** an approved contract that assigns `git-integration-operator` a profile other than `work_medium`, **when** the contract is compiled, **then** it validates, and the resulting model and reasoning effort come from the selected profile.

**Covers R2, R21.**

AE3. A Git command in an ordinary assignment no longer fails compilation.

**Given** an assignment on a non-Git role whose completion condition mentions `git status`, **when** the contract is compiled, **then** it validates. Whether one node should own integration is a graph-design question the operator settles at approval, not a compiler refusal.

**Covers R3, R4.**

AE4. Out-of-scope writes surface as evidence.

**Given** an assignment declaring writes under one directory that returns a `changed_paths` entry outside it, **when** the root validates the typed result, **then** the result validates successfully, carries a finding with a `scope_disposition` for that path, and reaches adjudication — where today the same input raises `ResultContractError` and the result is discarded.

**Covers R11, R22.**

AE5. Runtime identity still gates.

**Given** an attempt whose `turn_context` readback reports a different model than the approved profile, **when** the root validates the attempt, **then** it blocks on runtime receipt mismatch exactly as it does today.

**Covers R10, R23.**

## Scope Boundaries

**In scope**

- The role registry, the agent renderer, the workflow compiler, the typed-result validator, the generated profile instruction text, and their tests, within `plugins/verified-workflows/`.
- The documentation surfaces that assert the removed policy, including `plugins/saga/references/operator-choice.md` where it draws the wrong conclusion from a correct fact.
- The journal entries that record and now supersede the root-as-Git-owner decision.
- The body of issue 71.

**Out of scope**

- Fleet Core's parallel boundary vocabulary. `plugins/fleet-core/scripts/fleet_commons/tier_palette.py:38-39` and `tier_resolver.py:105-106` carry their own `workspace_boundary` and `external_boundary` fields on execution classes. Verified Workflows does not consume them — its renderer loads only the `codex_model_catalog` and `workflow_compat` shims — and `plugins/saga/scripts/execution_spec.py` has zero references to either field. The same critique probably applies there, but it is a different plugin with different consumers and belongs in its own issue.
- GitHub credentials, tokens, and authentication. The Hermes reproduction proved authentication was never the blocker.
- The external-actions contract. External provider output stays `non-gating` and advisory; this work does not turn that row type into a publication channel.
- Reviewer independence, gate reduction, and the remediation and recheck convergence rules.
- The wider Saga lifecycle and the outcome DAG.
- Historical records stay untouched. `plugins/verified-workflows/CHANGELOG.md:35` and `docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md:15` both assert root Git ownership, and both are history — a blanket text sweep that rewrites them would destroy the record this change depends on. Only live guidance is corrected; the journal supersedes rather than edits.

## Dependencies / Assumptions

**The digest ripple is a hard constraint on sequencing.** Editing `plugins/verified-workflows/config/role-registry.yaml` re-renders all seven files under `plugins/verified-workflows/agents/`, each of which stamps a `registry_sha256` header. Separately, both the registry edit and the documentation edits force a regenerate of `docs/validation/verified-workflows-legacy-token-inventory.json` — it carries a `workflow_registry_sha256` plus 134 doc and code entries, is produced by `scripts/build_legacy_workflow_inventory.py`, and is gated by `scripts/validate_codex_plugins.py` and `tests/test_verified_workflows_migration.py`. This is the same trap that stalled issue 67; planning should treat the regenerate as an explicit unit rather than discovering it at validation time.

**Assumption — the Hermes block was policy, not runtime.** The issue reports that the runtime rejected `git push` and `gh pr create`, but no workflow run record for it exists locally under `~/.codex/verified-workflows/state/`, so the rejecting layer could not be confirmed from this repository. The reasoning above holds it was declared policy, because children inherit the parent turn's permission and the root pushed successfully with the same credentials in the same session. If a red-first reproduction shows the Codex harness itself refused, R6 is not deliverable by registry changes alone and the work stops for a re-scope.

**Assumption — the child-attestation condition is genuinely met.** R18 rests on reading combined `session_meta` and `turn_context` readback as the "authenticated host-issued child attestation" that the 2026-07-18 decision named. That reading should be stated plainly in the superseding entry so a future reader can disagree with it on the record.

**No plugin-side containment replaces what is removed.** After this change, nothing prevents any subagent from mutating anything the parent session could mutate. That is already true today; the change is that the documentation will stop implying otherwise. Approval of the plan and the contract is the control.

## Outstanding Questions

**Deferred to planning**

- Whether `default_profile` survives as a non-binding convenience default once `allowed_profiles` and the category lock are gone, and what that means for the `fallback` column, which is currently validated against the role's allowed profiles.
- Whether the `role_kind`, `category`, and `boundaries` keys collapse into a smaller role schema, or whether only the boundary keys are dropped and the rest of the shape is preserved to minimize the digest and test surface.
- Whether the changed-path finding in R11 reuses an existing `finding` category and `scope_disposition` value or needs a new one.
- The exact ordering of the registry edit, the profile re-render, and the legacy-token-inventory regenerate so validation passes at each unit boundary.

## Sources / Research

Verified during this brainstorm; all paths repository-relative.

| Claim | Evidence |
|---|---|
| `git-integration-operator` declares no external capability and forbids external mutation | `plugins/verified-workflows/config/role-registry.yaml:153-175` |
| `external_mutation` is hardcoded `"forbidden"` for every role category | `plugins/verified-workflows/scripts/render_codex_agents.py:652-658` |
| Role category pins the allowed profile set; deviation raises KTD4 | `plugins/verified-workflows/scripts/render_codex_agents.py:142-179`, `:640-641` |
| `ROOT_ONLY_ACTIONS` reserves `git-mutation`, `merge`, and `completion` to root, with no consumer in the repository | `plugins/verified-workflows/scripts/render_codex_agents.py:181-190` |
| Undeclared changed paths raise `ResultContractError` and discard the whole typed result | `plugins/verified-workflows/scripts/result_contract.py:243-253` |
| `work_medium` declares external access `none` | `plugins/verified-workflows/scripts/render_codex_agents.py:113-119` |
| Generated profiles carry no sandbox or network keys | `plugins/verified-workflows/agents/work_medium.toml` |
| A profile cannot widen or narrow inherited permission on Codex 0.146 | `plugins/saga/references/operator-choice.md:47-48`; `plugins/verified-workflows/README.md:75-76`; `plugins/verified-workflows/skills/run/references/delegation-safety.md:22-25` |
| Compiler refuses Git words on non-Git roles and writes on read-only assignments | `plugins/verified-workflows/scripts/workflow_dispatch.py:312-322` |
| Fallback profiles must match the primary's declared boundaries | `plugins/verified-workflows/scripts/workflow_dispatch.py:324-336` |
| Root described as sole orchestrator and Git owner | `plugins/verified-workflows/README.md:5`, added 2026-07-24 in commit `a695ffc` |
| Root-owned Git recorded as a decision, with a child-attestation escape clause | `docs/engineering-journal/DECISIONS.md:68` (2026-07-18) |
| Child forbidden to merge, deploy, or handle credentials | `plugins/verified-workflows/skills/run/references/delegation-safety.md:16-18` |
| External action authority is always `non-gating` | `plugins/verified-workflows/scripts/workflow_dispatch.py:380-381` |
| Legacy token inventory pins a registry digest and is validator-gated | `docs/validation/verified-workflows-legacy-token-inventory.json`; `scripts/build_legacy_workflow_inventory.py`; `scripts/validate_codex_plugins.py`; `tests/test_verified_workflows_migration.py` |
| Fleet Core's boundary fields are a separate, unconsumed vocabulary | `plugins/fleet-core/scripts/fleet_commons/tier_palette.py:38-39`; `tier_resolver.py:105-106`; no references in `plugins/saga/scripts/execution_spec.py` |
| Existing coverage that asserts the removed fields | `plugins/verified-workflows/tests/test_role_registry.py`; `test_sync_codex_agents.py` |
| Existing coverage that dispatches `git-integration-operator` | `plugins/verified-workflows/tests/test_workflow_dispatch.py:73`, `:356`, `:366` |
| `test_agent_tier_sync.py` is named in issue 71 but contains no reference to role boundaries, `allowed_profiles`, or the registry — treat it as unconfirmed until planning greps it | issue 71 "Files expected to change" |
