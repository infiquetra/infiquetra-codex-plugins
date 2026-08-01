---
title: Remove Verified Workflows' unenforceable capability policy
type: fix
status: active
date: 2026-08-01
origin: docs/brainstorms/2026-07-31-verified-workflows-capability-policy-removal-requirements.md
deepened: 2026-08-01
---

# Remove Verified Workflows' unenforceable capability policy

## Summary

Delete the per-role and per-profile capability declarations that Verified Workflows invented, along with the compiler refusals and the profile pin built on them, then correct the live documentation and supersede the journal decisions that name the root session as the sole Git owner. Seven units, sequenced so every unit leaves the validation gate green.

## Problem Frame

The plugin declares `workspace_cap`, `external_cap`, and `external_mutation` per role and asserts them against a hardcoded constant, but nothing enforces them. Codex 0.146 children inherit the parent turn's effective permission profile and a profile cannot widen or narrow it (`plugins/saga/references/operator-choice.md:47-48`), and the generated profiles carry no key that could constrain a sandbox or a network (`plugins/verified-workflows/agents/work_medium.toml`).

The cost is real. During the Hermes profile self-sovereign evolution workflow the compiler assigned publication to `git-integration-operator`, the agent committed, and then could not push or open the pull request. A root-session exception finished the work with the same credentials, which proves the blocker was declared policy rather than authentication.

The same pattern pins `git-integration-operator` to `work_medium` as its only allowed profile, so publication was forced onto medium-effort Terra regardless of what the approved plan wanted.

---

## Requirements

**Removing the declarations**

R1. No role entry in `plugins/verified-workflows/config/role-registry.yaml` carries a `boundaries` block, and `render_codex_agents.py` no longer parses or asserts one. (origin R1)

R2. `allowed_profiles` is gone from the registry, from `RoleSpec`, and from the membership check in `resolve_role`. An assignment may select any member of `PROFILE_IDS`. (origin R2)

R3. `ROOT_ONLY_ACTIONS` is deleted from `render_codex_agents.py`. (origin R4)

R4. The per-profile `workspace` and `external` keys, and the `ProfileResolution` boundary fields they populate, are removed, along with every site that constructs or emits them. (origin R3)

**Removing the refusals**

R5. `workflow_dispatch.py` no longer rejects a non-Git role whose completion condition mentions `git` or `gh`, a read-only assignment that declares writes, or a fallback whose profile boundary differs from the primary's. (origin R3)

R6. A contract assigning `git-integration-operator` a completion condition containing `git push` and `gh pr create` compiles and dispatches to that assignment. (origin R6)

R7. Generated profile instructions carry role scope, not capability prohibitions. (origin R5)

**Changing the evidence, not deleting it**

R8. An undeclared changed path no longer raises `ResultContractError`. The typed result validates and carries a synthesized finding. (origin R11)

R9. The dependency graph, the concurrent-writer overlap check at `workflow_dispatch.py:460-496`, typed results, runtime identity readback, gate evaluation, reviewer independence, and the `git diff --name-only` completion requirement at `workflow_dispatch.py:319-322` are unchanged. (origin R7-R10, R12-R14)

**Correcting the record**

R10. No live guidance under `plugins/verified-workflows/` or `plugins/saga/references/` claims the root session owns Git, or that a profile carries permission or sandbox policy. (origin R15-R17)

R11. `DECISIONS.md` carries a superseding entry naming both prior entries, with a `LEARNINGS.md` companion. (origin R18)

R12. `plugins/verified-workflows/CHANGELOG.md`, archived plans under `docs/plans/`, and the historical receipt snapshot `docs/validation/codex-plugin-modernization-u3.json` are unchanged. That snapshot records a `registry_sha256` that already diverges from the current rendered digest, so it is dated evidence rather than a live check — regenerating it would destroy the record. (origin scope boundary)

**Proving it**

R13. `render_codex_agents.py --check --pretty`, `validate_codex_plugins.py`, the plugin test suite, and `tests/test_verified_workflows_migration.py` all pass after the generated inventory is regenerated. (origin R20-R23)

---

## Key Technical Decisions

KTD1. **Delete the capability layer rather than make it truthful.** Both designs issue 71 originally named — a conditionally publication-capable `work_medium`, and a dedicated publication profile — assume a profile can carry permission. It cannot on Codex 0.146, so either would ship a second unenforceable claim. Rejected in full in the origin document's Design Comparison.

KTD2. **Keep `default_profile`, drop `allowed_profiles`.** `resolve_role` at `render_codex_agents.py:959` uses `default_profile` as a live fallback when a caller omits a profile, so it earns its place. The allowlist at `:960-964` is the constraint that blocked publication. Fallback validation in `workflow_dispatch.py:325` moves from the role's allowlist to `renderer.PROFILE_IDS`.

KTD3. **The validator synthesizes the undeclared-path finding; it does not trust the agent to self-report.** `result_contract.py:252-253` stops raising and instead appends a finding with `severity: P2`, `category: operations`, `scope_disposition: one-hop`, `hard_stop: false`, and `resolved: false`. One stray path is reported and absorbed; two or more hard-stop through the existing cap at `gate_evaluator.py:310-313`. This honors "a finding, not a block" while keeping a backstop against systematic drift, and reuses the deviation model already in the plugin rather than inventing semantics.

The cap counts *every* one-hop finding, not only synthesized ones — `gate_evaluator.py:307-309` filters the merged list of agent-supplied and root-adopted findings. So "one stray path is absorbed" holds only when the agent reported no one-hop finding of its own; a single undeclared path combined with one agent-reported one-hop finding hard-stops, and also sets `approval_required` at `:314-318`. That is the intended reading — the cap bounds total scope drift, not drift by source — but it must be stated, because the obvious test only exercises synthesized findings and would miss it.

KTD4. **Every unit that changes rendered bytes re-renders `agents/*.toml` inside that unit, AND regenerates the runtime proof; the generated-inventory regenerate is its own terminal unit.** `registry_sha256` is stamped into all seven profile files. `docs/validation/verified-workflows-legacy-token-inventory.json` carries 134 code-and-documentation entries, so it can only settle after the code and the docs have both landed. Discovering this at validation time is what stalled issue #67.

> **Corrected 2026-08-01, twice — once for a claim that was wrong, once for a ripple that was missing.**
>
> *Wrong:* this decision originally said the inventory "carries both a registry digest and 134
> code-and-documentation entries," implying the role-registry edit moves it. It does not. The file's
> `workflow_registry_sha256` is computed live from `WORKFLOW_COMPAT.REGISTRY` at
> `scripts/validate_codex_plugins.py:764-770` and has never hashed `role-registry.yaml`. Only the
> 134-entry text index can move, and only from documentation and code text changes. See U7.
>
> *Missing:* the ripple that genuinely exists is `docs/validation/verified-workflows-runtime-proof.json`,
> which the plan never mentioned. It pins the sha256 of all seven `agents/*.toml` files, so ANY unit
> that re-renders profiles stales it and breaks four tests plus `scripts/validate_codex_plugins.py`
> with "tracked runtime proof is stale." That unit must regenerate it in the same unit with
> `FLEET_COMMONS_ROOT=$PWD/plugins/fleet-core PYTHONDONTWRITEBYTECODE=1 python3 scripts/prove_verified_workflows_runtime.py --pretty > docs/validation/verified-workflows-runtime-proof.json`;
> only the seven profile digests may change. This applies to U1 (done), U2, and U4.

KTD5. **The journal supersedes; it does not edit.** A new `DECISIONS.md` entry names both prior entries and records that the child-attestation condition the 2026-07-18 entry set has since been met. `CHANGELOG.md:35` and `docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md:15` assert root Git ownership and stay as written — they are the evidence this change rests on.

KTD6. **Keep the `git-operator` role category.** With boundaries and the profile pin gone, the category still drives result-schema mapping through `CATEGORY_RESULT_SCHEMAS` and the `minimum_independence` expectation at `render_codex_agents.py:628-632`. Collapsing it would widen this change for no gain.

---

## Implementation Units

### U1. Strip capability declarations from the registry and renderer

Remove the `boundaries` block from all 28 roles and every renderer construct that parses, asserts, or enforces it.

**Goal:** the registry stops declaring capability, and role→profile selection stops being constrained.

**Requirements:** R1, R2, R3.

**Dependencies:** none.

**Files:** `plugins/verified-workflows/config/role-registry.yaml`; `plugins/verified-workflows/scripts/render_codex_agents.py`; `plugins/verified-workflows/scripts/workflow_dispatch.py`; `plugins/verified-workflows/agents/*.toml`; `plugins/verified-workflows/tests/test_role_registry.py`; `plugins/verified-workflows/tests/test_sync_codex_agents.py`; `tests/test_verified_workflows_agents.py`; `tests/test_verified_workflows_migration.py`.

**Approach:** delete the four-key `boundaries` mapping and `allowed_profiles` from all 28 role entries — every role is `kind: agent-lens`, so there is one *registry* parse path to change. In the renderer drop the boundary parse and equality assert (`:642-658`), the profile-transition check (`:640-641`), the `allowed_profiles` membership test in `resolve_role` (`:960-964`), the `allowed_profiles`, `workspace_cap`, and `external_cap` fields on `RoleSpec` (`:345-347`), the `workspace` and `external` keys in `ROLE_PROFILE_POLICY` (`:142-179`), and the dead `ROOT_ONLY_ACTIONS` tuple (`:181-190`). One line in the compiler moves with them: `workflow_dispatch.py:325` validates fallbacks against `renderer.PROFILE_IDS` instead of the role's allowlist, so the tree still compiles at the end of this unit. Re-render the seven profile files because `registry_sha256` changes.

**The dead `deterministic-validator` branch must be updated even though it is unreachable.** `_parse_deterministic` constructs a `RoleSpec` passing `allowed_profiles=()`, `workspace_cap=None`, and `external_cap=str(command["network"])` at `:800-802`, and its closed-key set at `:830-840` accepts `allowed_profiles` and `boundaries`. No registry entry uses `kind: deterministic-validator` and no test exercises it, but a dataclass constructor cannot pass fields that no longer exist. Drop those three keyword arguments and the two key names. Removing the branch wholesale stays out of scope; making it consistent with the narrowed `RoleSpec` does not.

There is a third consumer beyond the parser and the resolver: `bundle_receipt()` at `:1187-1246` emits `allowed_profiles`, `workspace_cap`, and `external_cap` into its per-role projection (`:1228`, `:1234-1235`). Drop those three keys from the receipt. Two root-level test files exercise that projection — `tests/test_verified_workflows_agents.py` asserts the receipt `claim` at `:165` and `:239`, and `tests/test_verified_workflows_migration.py` reads the registry — so both live outside `plugins/verified-workflows/tests/` and must be run for this unit. Neither currently asserts the three removed keys by name, so the expected churn is the receipt shape, not the assertions.

**Patterns to follow:** the existing `_closed_keys` helper for narrowing accepted mappings; the renderer's habit of raising `RoleRegistryError` with the offending role id.

**Test scenarios:**

- Happy path — loading the registry yields 28 roles, and `RoleSpec` no longer exposes `workspace_cap` or `external_cap`. Replaces the assertions at `test_role_registry.py:52-54`.
- Happy path — `resolve_role("git-integration-operator", requested_profile="work_high")` returns a resolution selecting `work_high`, where today it raises.
- Happy path — `resolve_role` with no requested profile still falls back to `default_profile`.
- Edge case — a registry entry that still carries a `boundaries` key is rejected as an unknown field, so stale copies fail loudly rather than being silently ignored.
- Edge case — `resolve_role` with a profile outside `PROFILE_IDS` still raises `RoleRegistryError`. The existing `"ultra"` negative test at `test_role_registry.py:159` is retargeted here rather than deleted.
- Error path — a role whose `minimum_independence` disagrees with its category still raises, proving KTD6's retained checks survive.
- Integration — `bundle_receipt()` produces a projection carrying no `allowed_profiles`, `workspace_cap`, or `external_cap` key, and `tests/test_verified_workflows_agents.py` still passes against the reshaped receipt.

**Verification:** `render_codex_agents.py --check --pretty` exits 0 against the re-rendered profiles, and `grep -n 'ROOT_ONLY_ACTIONS\|external_mutation\|workspace_cap' plugins/verified-workflows/scripts/render_codex_agents.py plugins/verified-workflows/config/role-registry.yaml` returns nothing.

### U2. Remove the compiler's capability refusals

Delete the three assignment-level rejections that exist only to enforce the removed policy.

**Goal:** the compiler stops refusing work it cannot actually prevent.

**Requirements:** R4, R5, R6, and R9 — the "unchanged" set has no unit of its own, and this unit's error-path scenarios are where it is proved.

**Dependencies:** U1.

**Files:** `plugins/verified-workflows/scripts/workflow_dispatch.py`; `plugins/verified-workflows/scripts/render_codex_agents.py`; `plugins/verified-workflows/tests/test_workflow_dispatch.py`.

**Approach:** remove the read-only-cannot-declare-writes check (`:312-313`), the `GIT_WORD_RE` rejection of Git commands on non-Git roles (`:315-318`), and the fallback boundary-equality comparison (`:330-336`). Keep the `git diff --name-only` completion requirement at `:319-322` — that is evidence production, not capability policy, and R9 pins it. `GIT_WORD_RE` has exactly one consumer, the refusal at `:315`, so its definition at `workflow_dispatch.py:23` is deleted with it.

With the last consumers gone, drop `workspace` and `external` from `PROFILE_POLICY` (`:91-141`) and the `workspace_boundary` / `external_boundary` fields from `ProfileResolution` (`:413-414`). **Two further sites in `render_codex_agents.py` populate and emit those fields and must change in the same unit:** `resolve_profile` constructs them from the policy dict at `:1091-1092`, and `bundle_receipt()` emits them into the per-profile projection at `:1205-1206`. The class is named `ProfileResolution`, not `ResolvedProfile` — grep for the former.

**Patterns to follow:** the `git_operator()` fixture helper at `tests/test_workflow_dispatch.py:69-77` for building assignment rows.

**Test scenarios:**

- Happy path — a contract whose `git-integration-operator` row has a completion condition containing `git push`, `gh pr create`, and `git diff --name-only` compiles and dispatches to that assignment. This is the red-first reproduction of the Hermes failure.
- Happy path — a contract assigning `git-integration-operator` the `work_high` profile compiles, and the resulting assignment's model and effort resolve from `work_high` rather than `work_medium`.
- Happy path — a non-Git role whose completion condition mentions `git status` compiles instead of raising.
- Edge case — a `git-integration-operator` row whose completion omits `git diff --name-only` still raises, proving the retained evidence requirement did not go out with the refusals.
- Edge case — a fallback naming a profile outside `PROFILE_IDS` still raises; a fallback naming a valid profile with a different former boundary now compiles.
- Error path — a cyclic `depends` graph and overlapping concurrent write sets both still raise, proving R9's graph mechanics are untouched.

**Verification:** the publication contract that previously failed to compile now produces an `Assignment` whose role is `git-integration-operator`, and the retained graph and completion checks still reject their negative cases.

### U3. Undeclared changed paths become a finding, not a raised error

Replace the hard rejection of out-of-scope writes with a synthesized, gate-visible finding.

**Goal:** drift is reported as evidence instead of discarding the entire typed result.

**Requirements:** R8.

**Dependencies:** none. Independent of U1 and U2; may land in any order relative to them.

**Files:** `plugins/verified-workflows/scripts/result_contract.py`; `plugins/verified-workflows/tests/test_result_contract.py`.

**Approach:** at `:243-253` stop raising `ResultContractError` for undeclared paths. Compute the undeclared set as today, then append one synthesized finding per undeclared path to the normalized `findings` list, built to satisfy `_finding`'s closed field set: a deterministic `finding_id` derived from the path, `severity: P2`, `category: operations`, `scope_disposition: one-hop`, `resolved: false`, `hard_stop: false`, with `location` naming the path and `impact` / `fix` / `validation` naming the declared write set it fell outside. Synthesis happens in the validator, never from agent-supplied content, per KTD3. Every other validation in the function — the closed field set, `no_change` consistency, terminal-status membership — is untouched.

**Patterns to follow:** `_finding` at `result_contract.py:92-122` for the exact field contract and its `defer`-plus-`hard_stop` prohibition; `SCOPE_DISPOSITIONS` and `FINDING_CATEGORIES` at `:38-50` for the accepted vocabulary.

**Test scenarios:**

- Happy path — a result whose `changed_paths` all sit inside `writes` validates with no synthesized finding added.
- Happy path — a result with one undeclared path validates, and the normalized findings list gains exactly one `P2` / `operations` / `one-hop` entry whose `location` is that path.
- Edge case — a result with three undeclared paths yields three findings; passing them to `gate_evaluator` produces the "more than one unplanned one-hop finding requires operator approval" hard stop from `gate_evaluator.py:308-311`.
- Edge case — an assignment declaring `writes: none` that reports changed paths yields findings rather than an exception. This is the live trap: the `git_operator()` fixture declares no writes, so a commit-reporting Git assignment hits this path.
- Edge case — agent-supplied findings and synthesized findings coexist without `finding_id` collision.
- Edge case — one agent-supplied `one-hop` finding plus one synthesized undeclared-path finding produces a hard stop, because the cap counts both sources together. This is the case a synthesized-only test would miss.
- Error path — a malformed agent-supplied finding still raises `ResultContractError`, and `no_change: true` with a non-empty `changed_paths` still raises. Synthesis must not swallow unrelated contract violations.

**Verification:** a result that today raises `terminal result changed paths exceed assignment writes` instead returns a normalized payload carrying the finding, and feeding three such paths to the gate evaluator produces a hard stop.

### U4. Retire the Git prohibition from generated profile instructions

Rewrite the instruction text so profiles describe scope rather than forbid capability.

**Goal:** the generated profiles stop asserting a prohibition the runtime does not implement.

**Requirements:** R7.

**Dependencies:** U1.

**Files:** `plugins/verified-workflows/scripts/render_codex_agents.py`; `plugins/verified-workflows/agents/*.toml`; `plugins/verified-workflows/tests/test_agent_tier_sync.py`.

**Approach:** in the developer-instruction template replace "Do not run Git unless the role is `git-integration-operator`" with guidance to perform the assigned bounded role and stay inside it. Leave the surrounding sentences about runtime identity coming from Codex readback — those remain true. Re-render all seven profiles. Confirm whether `test_agent_tier_sync.py` actually asserts instruction bytes before editing it; the origin document flags it as named in issue 71 but carrying no reference to boundaries, `allowed_profiles`, or the registry.

**Patterns to follow:** the existing instruction text in `agents/work_medium.toml`, which already separates compute defaults from logical-role identity.

**Test scenarios:**

- Happy path — the rendered `work_medium` instructions contain no Git prohibition, and `render_codex_agents.py --check --pretty` agrees with the committed bytes.
- Edge case — all seven profiles re-render deterministically; a second `--check` run after the first is a no-op.
- Error path — a hand-edited profile whose bytes drift from the renderer still fails `--check`, proving the drift guard survives.

**Verification:** `grep -rn 'Do not run Git' plugins/verified-workflows/` returns nothing, and `--check` exits 0.

### U5. Correct the live documentation surfaces

Fix every shipped instruction that claims root owns Git or that profiles carry permission.

**Goal:** the guidance an agent or operator reads matches what the plugin does.

**Requirements:** R10, R12.

**Dependencies:** U1, U2, U3. The docs describe the post-change behavior, so they land after it exists.

**Files:** `plugins/verified-workflows/README.md`; `plugins/verified-workflows/skills/run/references/delegation-safety.md`; `plugins/verified-workflows/skills/run/references/workflow-protocol.md`; `plugins/verified-workflows/skills/review-workflow/SKILL.md`; `plugins/saga/references/operator-choice.md`.

**Approach:** `README.md:5` stops calling the root the Git owner and describes it as the orchestrator of an approved graph and the adjudicator of its evidence; `:75-76`, `:104`, and the profile table lose the workspace-intent column's implication of enforcement. `delegation-safety.md:16-18` drops the claim that a child cannot merge, deploy, or handle credentials; `:22-25` keeps the inheritance fact. `workflow-protocol.md` needs both of its cited lines handled, not one: `:22-23` drops the permission-boundary constraint on fallbacks, and `:20-21` loses "Only `git-integration-operator` may own Git commands" because U2 deletes the `GIT_WORD_RE` check that enforced it — leaving it would preserve exactly the unenforced-rule defect this change removes. The second half of that sentence, requiring the final `git diff --name-only` validation, stays: R9 pins it and `workflow_dispatch.py:319-322` still enforces it. `review-workflow/SKILL.md:8` stops asserting root ownership of integration and Git. In `operator-choice.md` the statement at `:47-48` stays verbatim — it is true and load-bearing — and only the conclusion drawn from it changes, per origin R17. Leave `CHANGELOG.md` and every file under `docs/plans/` untouched.

**Patterns to follow:** the existing README voice — short declarative sentences, no hedging.

**Test expectation:** none — documentation prose with no behavioral surface. The assertions that matter are R12's untouched-history check and U7's inventory regenerate, both verified there.

**Verification:** `grep -rn 'Git owner' plugins/` returns only `CHANGELOG.md:35`, and `git diff --stat` shows no change under `docs/plans/`.

### U6. Supersede the root-as-Git-owner journal decisions

Record the reversal as a new decision that names what it replaces and why the condition changed.

**Goal:** a future reader can trace why root-owned Git existed and why it stopped.

**Requirements:** R11.

**Dependencies:** U5.

**Files:** `docs/engineering-journal/DECISIONS.md`; `docs/engineering-journal/LEARNINGS.md`.

**Approach:** add a dated entry that records the supersession chain accurately rather than treating the two prior entries as peers. `DECISIONS.md:64` already states that the 2026-07-24 entry supersedes the 2026-07-18 one "after the U8 live cutover gate passes," so the new entry supersedes 2026-07-24 "Codex V2 Owns Live Execution..." at `:50` — which asserts root ownership of integration, Git, gates, and merge at `:52` — and notes that 2026-07-18 "Feasibility Review Keeps Root-Owned Workflows Usable" at `:68` was already conditionally superseded by it. Check whether the U8 gate passed before asserting which of the two was operative; if the record does not settle it, say so rather than guessing.

One nearby entry is **not** superseded and must be named as surviving: 2026-07-17 "Normalize Subject-Exclusion Parent Links And Bootstrap Self-Hosting Fixes Manually" at `:78`, whose `:84` holds that "Verified Workflows cannot grant gate authority to changes in its own implementation" and that self-hosting patches keep root ownership of implementation, integration, Git, release, and installation. That is the category this very change falls into, it remains true, and a reader of the new entry could otherwise conclude the opposite. (The 2026-07-17 policy that `:64` supersedes is the separate temporary V1 catalog entry at `:90`, not this one.) State plainly that the 2026-07-18 entry conditioned child execution on "authenticated host-issued child attestation," that combined `session_meta` and `turn_context` readback on the canonical agent path is being read as satisfying it, and that a future reader may disagree with that reading on the record. The `LEARNINGS.md` entry carries the generalizable rule: a policy the host does not implement is documentation, not a control, and it will eventually block real work. Per repository convention both entries ship in the same commit as the change.

**Patterns to follow:** the existing entry shape — `## YYYY-MM-DD: Title Case Statement`, short paragraphs, a closing plan or evidence pointer.

**Test expectation:** none — journal prose with no behavioral surface.

**Verification:** both prior entries are cited by date and title in the new entry, and the earlier entries themselves are unmodified.

### U7. Regenerate the generated inventory and prove the whole gate

Rebuild the digest-bound inventory and run every gate end to end.

**Goal:** the repository validates as one coherent unit, with the digest ripple resolved deliberately rather than discovered.

**Requirements:** R13.

**Dependencies:** U1, U2, U3, U4, U5, U6. This unit is terminal by construction — the inventory covers both code and documentation entries, so it cannot settle until all of them have landed.

**Files:** `docs/validation/verified-workflows-legacy-token-inventory.json`.

**Approach:** run `python3 scripts/build_legacy_workflow_inventory.py --write` to regenerate. Then run the full gate. Do not hand-edit the JSON; if `--check` and `--write` disagree, that is a real defect in an earlier unit, not a file to patch.

> **Corrected 2026-08-01 — the digest-ripple premise was wrong.** This section originally claimed that
> "both the registry edit from U1 and the prose edits from U5 and U6 move it." The U1 half is false.
> `workflow_registry_sha256` is not a digest of `plugins/verified-workflows/config/role-registry.yaml`
> and is not a frozen historical value: `workflow_registry_sha256()` at
> `scripts/validate_codex_plugins.py:764-770` computes it live on every run by JSON-encoding
> `WORKFLOW_COMPAT.REGISTRY` — the workflow-name compatibility map, 18 entries — and hashing that.
> It has never hashed the role registry. Measured after U1 and U3 landed:
> `build_legacy_workflow_inventory.py --check` exits 0 and `scripts/validate_codex_plugins.py` exits 0.
> What can still legitimately move this file is its 134-entry list, which indexes code and
> documentation *text*, so the U5 and U6 prose edits remain plausible movers. A `--write` that
> produces no diff is a valid outcome. Falsified by the U1 verify panel and independently
> re-confirmed against source by the driving session.

**Patterns to follow:** the generated-artifact convention used across `docs/validation/` — regenerate through the named builder, never by hand.

**Test scenarios:**

- Happy path — `build_legacy_workflow_inventory.py --check` exits 0 after `--write`, and a second `--write` is a no-op.
- Integration — `tests/test_verified_workflows_migration.py` and `scripts/validate_codex_plugins.py` both pass against the regenerated inventory.
- Integration — the full plugin suite `uv run python -m pytest -q plugins/verified-workflows/tests` passes.
- Error path — reverting any single earlier unit's file makes `--check` fail, proving the inventory genuinely tracks both code and documentation.

**Verification:** `render_codex_agents.py --check --pretty`, `validate_codex_plugins.py`, `pytest plugins/verified-workflows/tests`, and `pytest tests/test_verified_workflows_migration.py` all exit 0 on a clean tree.

---

## Execution Shape

**Execution backend: `cc-workflows-ultracode`** — a Claude Code dynamic workflow over the U1-U7 dependency graph, with the root session owning branch, commits, and the pull request. The saga tick records this value directly.

This repository is the subject of the work, not the toolchain that executes it. The lifecycle runs on the operator's installed Claude saga plugin, and its state lives under `.claude/saga/`. Nothing under `plugins/` in this checkout is invoked as tooling — those files are the artifact being changed, and running them would mean testing the repair against itself.

The Codex `verified-workflow` backend is not a candidate. It is a different harness on a different surface, it is what this plan rewrites, and a Claude Code session cannot execute it.

**Available parallelism is modest — the graph is mostly a chain.** U3 is independent of everything and can run alongside U1. U2 and U4 both depend on U1 and both edit `render_codex_agents.py`, so they run in sequence, not concurrently. U5, U6, and U7 are strictly ordered. Peak concurrency is therefore two, in the first stage only. The value of the workflow shape here is per-unit boundaries and verification, not wall-clock.

| Stage | Units | Concurrency | Suggested tier |
|---|---|:---:|---|
| 1 | U1, U3 | 2 | Opus — registry surgery and validator semantics both carry judgment |
| 2 | U2 | 1 | Opus — decides which refusals are policy and which are evidence |
| 3 | U4 | 1 | Sonnet — mechanical template edit plus a deterministic re-render |
| 4 | U5, then U6 | 1 | Opus — prose that must be exactly right about what the plugin now does |
| 5 | U7 | 1 | Sonnet — generator invocation and gate execution, no judgment |

Tiers are explicit per unit rather than inherited from the session, per the repository's model-tiering rule.

---

## Risks & Dependencies

**The Hermes reproduction was never captured, so the blocking layer is inferred.** No workflow run record exists under `~/.codex/verified-workflows/state/`. The reasoning that declared policy blocked the push rests on children inheriting the parent's permission and the root pushing successfully with the same credentials in the same session. *Mitigation:* U2's first test scenario is the red-first reproduction. If a compiled publication contract still cannot dispatch after U1 and U2, the harness — not the policy — was the blocker, and the work stops for a re-scope rather than proceeding to U4 through U7.

**Removing containment language could read as removing containment.** Nothing prevented a subagent from mutating anything before this change either; only the documentation implied otherwise. *Mitigation:* U5 states the actual control plainly — operator approval of the plan and the contract — rather than deleting the guidance and leaving a gap.

**The digest ripple can strand a partial landing.** ~~Any unit that lands without U7 leaves `validate_codex_plugins.py` failing.~~ *Corrected 2026-08-01:* this overstated the risk in one direction and missed it in another. A unit landing without U7 does **not** by itself fail `validate_codex_plugins.py` — measured after U1 and U3 landed, both it and `build_legacy_workflow_inventory.py --check` exit 0, because the inventory's digest field never tracked the role registry (see KTD4). The real stranding risk is the **runtime proof**: any unit that re-renders `agents/*.toml` without regenerating `docs/validation/verified-workflows-runtime-proof.json` fails four tests and `validate_codex_plugins.py` immediately, within that unit. *Mitigation:* KTD4 now requires the regenerate inside the re-rendering unit, and still makes U7 terminal and mandatory; the branch is not PR-ready until it runs.

**A blanket text sweep would rewrite history.** `CHANGELOG.md:35` and the archived 2026-07-24 plan both assert root Git ownership. *Mitigation:* R12 pins them as untouched and U5's verification greps for exactly that.

---

## Alternatives Considered

The two designs issue 71 originally mandated were both rejected, and the origin document carries the full comparison.

| Alternative | Why rejected |
|---|---|
| Make `work_medium` publication-capable only under `git-integration-operator` | Assumes a profile can carry permission conditionally. It cannot on Codex 0.146, so the conditional would be enforced only by the compiler and instruction text — a second unenforceable claim plus a role-dependent branch in profile resolution |
| Add a dedicated Git publication agent profile | Same defect, plus a new profile, category, render and sync coverage, and digest surface. Its visibility benefit already exists in the approved contract, which names the exact Git commands in the completion condition |
| Keep a truthful role-level declaration with compile-time-only enforcement | Considered during brainstorming and rejected by the operator: the plugin should not author permission policy beyond what the harness implements, and a declaration with no enforcement is the thing being removed |
| Split documentation correction into its own issue | Rejected because the generated inventory covers both code and documentation entries, so a split leaves the first pull request failing validation |

---

## Scope Boundaries

**Out of scope**

- Fleet Core's parallel boundary vocabulary at `plugins/fleet-core/scripts/fleet_commons/tier_palette.py:38-39` and `tier_resolver.py:105-106`. Verified Workflows does not consume it and `plugins/saga/scripts/execution_spec.py` has zero references.
- GitHub credentials and authentication. The reproduction proved authentication was never the blocker.
- The external-actions contract. Provider output stays `non-gating`; this work does not make it a publication channel.
- Reviewer independence, gate reduction, and the remediation and recheck convergence rules.
- Deleting the `_parse_deterministic` / `command.network` branch in the renderer. All 28 roles are `kind: agent-lens`, so that branch is unreachable from this registry, and removing dead code is a separate cleanup. U1 still edits it — a constructor cannot pass `RoleSpec` fields that no longer exist — but only to keep it consistent, not to retire it.

**Deferred to follow-up work**

- Applying the same critique to Fleet Core's execution-class boundary fields, which are carried as data by `tier_palette.py` and consumed by Saga and Mission Control.
- Deciding whether the `boundaries` concept returns in any form once Codex exposes per-child permission control. Nothing in this plan forecloses it.

---

## Open Questions

Both questions carried from the origin document are now resolved by inspection, and are kept here with their answers rather than deleted.

- **Does `test_agent_tier_sync.py` assert anything this change touches?** No. A sweep for every removed identifier across `plugins/`, `scripts/`, and `tests/` returns no hit in that file. U4 lists it defensively; expect no edit.
- **Does `GIT_WORD_RE` have a consumer beyond the refusal removed in U2?** No. It is defined at `workflow_dispatch.py:23` and used only at `:315`. The constant is deleted along with the rejection.

The same sweep bounds the whole change: outside the registry, the only files referencing the removed identifiers are `render_codex_agents.py` (32 references), `workflow_dispatch.py` (4), `test_role_registry.py` (4), and `test_sync_codex_agents.py` (1). Fleet Core's 18 references are the separate vocabulary held out of scope. The two root-level test files in U1's file list contain none, which confirms the expected churn there is the receipt shape rather than any assertion.

---

## Sources / Research

| Fact | Evidence |
|---|---|
| All 28 roles are `agent-lens` and every one carries a four-key `boundaries` block | `plugins/verified-workflows/config/role-registry.yaml` |
| `external_mutation` hardcoded `"forbidden"` for every category | `plugins/verified-workflows/scripts/render_codex_agents.py:652-658` |
| Profile pin and its KTD4 error | `plugins/verified-workflows/scripts/render_codex_agents.py:640-641`, `:142-179` |
| `default_profile` is a live fallback; `allowed_profiles` is the constraint | `plugins/verified-workflows/scripts/render_codex_agents.py:959-964` |
| `ROOT_ONLY_ACTIONS` defined with no consumer in the repository | `plugins/verified-workflows/scripts/render_codex_agents.py:181-190` |
| Compiler capability refusals and fallback boundary check | `plugins/verified-workflows/scripts/workflow_dispatch.py:312-336` |
| Undeclared paths raise and discard the whole result | `plugins/verified-workflows/scripts/result_contract.py:243-253` |
| Finding field contract and accepted vocabulary | `plugins/verified-workflows/scripts/result_contract.py:38-50`, `:92-122` |
| One-hop cap that backstops KTD3 | `plugins/verified-workflows/scripts/gate_evaluator.py:305-318` |
| A profile cannot widen or narrow inherited permission | `plugins/saga/references/operator-choice.md:47-48` |
| Both journal entries asserting root Git ownership | `docs/engineering-journal/DECISIONS.md:50`, `:68` |
| Generated inventory carries a registry digest and 134 entries | `docs/validation/verified-workflows-legacy-token-inventory.json`; `scripts/build_legacy_workflow_inventory.py` |
| Existing assertions on the removed fields | `plugins/verified-workflows/tests/test_role_registry.py:52-54`, `:159`; `test_sync_codex_agents.py:111` |
| Git-operator fixture declares `writes: none` | `plugins/verified-workflows/tests/test_workflow_dispatch.py:69-77` |
| A third consumer emits the removed fields into a receipt projection | `plugins/verified-workflows/scripts/render_codex_agents.py:1187-1246`, keys at `:1228`, `:1234-1235` |
| The profile boundary fields are also constructed and emitted, and the class is `ProfileResolution` | `plugins/verified-workflows/scripts/render_codex_agents.py:408-415`, constructed `:1091-1092`, emitted `:1205-1206` |
| The unreachable `deterministic-validator` branch still passes the removed `RoleSpec` fields | `plugins/verified-workflows/scripts/render_codex_agents.py:790-806`, closed-key set `:830-840` |
| `GIT_WORD_RE` has exactly one consumer | `plugins/verified-workflows/scripts/workflow_dispatch.py:23`, used only at `:315` |
| The 2026-07-24 entry already conditionally supersedes the 2026-07-18 one | `docs/engineering-journal/DECISIONS.md:64` |
| A live 2026-07-17 entry keeps root Git ownership for self-hosting patches | `docs/engineering-journal/DECISIONS.md:78`, claim at `:84` |
| Root-level tests exercise that projection | `tests/test_verified_workflows_agents.py:165`, `:239`; `tests/test_verified_workflows_migration.py` |
| Concurrent-writer overlap check that R9 preserves | `plugins/verified-workflows/scripts/workflow_dispatch.py:460-496` |
| Verified Workflows cannot gate changes to its own implementation | `docs/engineering-journal/DECISIONS.md` (2026-07-17 self-hosting bootstrap entry) |
