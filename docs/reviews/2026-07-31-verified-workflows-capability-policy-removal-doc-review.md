# Doc review — Verified Workflows capability-policy removal

Readiness review of the requirements document and its parent GitHub issue before planning. Both were corrected in place; nothing remains blocking.

## Review-result contract

| field | value |
|---|---|
| target | `docs/brainstorms/2026-07-31-verified-workflows-capability-policy-removal-requirements.md` |
| secondary target | GitHub issue #71 (`infiquetra/infiquetra-codex-plugins`) |
| reviewed revision | working tree at `0c20724` (target document untracked) |
| classification | requirements (`docs/brainstorms/` tie-breaker) plus issue-phase rubrics for #71 |
| rubrics run | issue phase — cores `acceptance_criteria_clarity`, `devils_advocate_issue`, `spec_fidelity`; extras `context_completeness`, `issue_sizing`, `prerequisite_mapping` |
| blocked | no |
| override rationale | not applicable |
| linked issue | https://github.com/infiquetra/infiquetra-codex-plugins/issues/71 |
| artifact | `docs/reviews/2026-07-31-verified-workflows-capability-policy-removal-doc-review.md` |

## Findings

All findings were fixed in place. None remain open.

| # | priority | target | finding | status |
|---|:---:|---|---|---|
| 1 | P1 | doc | R11 misdescribed the enforcement mechanism and omitted its location | fixed |
| 2 | P1 | issue | Acceptance criteria contradicted the chosen direction and were largely untestable | fixed |
| 3 | P2 | doc | `ROOT_ONLY_ACTIONS` unlisted in the removal set | fixed |
| 4 | P2 | doc | Fate of the per-profile `workspace` / `external` keys left ambiguous | fixed |
| 5 | P2 | doc | Two live documentation surfaces and a second journal entry were missed | fixed |
| 6 | P2 | doc | No guard against a text sweep rewriting changelog and archived plans | fixed |
| 7 | P2 | issue | Premature design foreclosed the option that was actually chosen | fixed |
| 8 | P3 | doc | One Sources row was carried from the issue, not verified | fixed |
| 9 | P3 | doc | `ROLE_PROFILE_POLICY` line range off by one | fixed |

### 1. R11 misdescribed the enforcement mechanism (P1)

The requirement said an out-of-scope changed path would become a finding "not a compile-time refusal and not an automatic terminal failure." There is no compile-time check for this. `plugins/verified-workflows/scripts/result_contract.py:252-253` raises `ResultContractError`, which discards the entire typed result — so the assignment produces no usable evidence and its dependents never release.

An implementer following the original text would have searched for a compiler check that does not exist and could have left the real hard-fail in place. R11 now names the file, the line range, and the behavior change; AE4 was corrected to match.

### 2. Issue acceptance criteria contradicted the direction (P1)

Four of the nine original criteria presupposed the capability layer surviving — external mutation remaining unavailable to non-publication agents, and the compiler rejecting role/profile pairings with insufficient declared capability. Several others were reviewer-subjective with no nameable artifact ("the plan records the complete reasoning," "documentation explains which agent performs Git publication").

The body and title were rewritten from the requirements document. The eight replacement criteria each name a grep, a command exit status, or a specific test assertion.

### 3. `ROOT_ONLY_ACTIONS` unlisted (P2)

`plugins/verified-workflows/scripts/render_codex_agents.py:181-190` reserves `git-mutation`, `integration`, `merge`, `deploy-initiation`, `credential-change`, and `completion` to the root session. It is the clearest textual encoding of the policy being retired, and the document did not mention it.

Rated P2 rather than P1 because it is dead — no consumer exists anywhere in `plugins/`, `scripts/`, or `tests/`. R4 now names it and states that removing it is a clarity fix, not a behavior change.

### 4. Per-profile `workspace` / `external` keys ambiguous (P2)

R1 removed the boundary fields from the role registry, but `scripts/render_codex_agents.py:91-141` declares `workspace` and `external` per *profile* as well, and `ResolvedProfile.workspace_boundary` — not the role's field — is what `workflow_dispatch.py:312` actually tests. Removing only the role-level fields would leave the refusal with a live input. R3 now covers the profile-level keys explicitly.

### 5. Missed documentation surfaces and a second journal entry (P2)

`plugins/verified-workflows/skills/review-workflow/SKILL.md:8` asserts that the root owns integration and Git, and `docs/engineering-journal/DECISIONS.md:50` (2026-07-24) asserts the same at `:52` — a second decision entry beyond the 2026-07-18 one the document already named. R16 and R18 were extended.

### 6. No guard against rewriting history (P2)

`plugins/verified-workflows/CHANGELOG.md:35` and `docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md:15` both assert root Git ownership. An agent executing a blanket sweep for that phrasing would rewrite the record this change depends on. Scope Boundaries now names both paths as history that stays untouched.

### 7. Premature design in the issue (P2)

The original body required planning to choose between two named designs. Both rest on the premise that an execution profile can carry permission, which Codex 0.146 does not support — so the mandated comparison foreclosed the option that was actually chosen. The rewritten body records both as considered and rejected, with the reason, satisfying the original intent without constraining the outcome.

### 8. Unverified Sources row (P3)

The Sources table is headed "Verified during this brainstorm," but `plugins/verified-workflows/tests/test_agent_tier_sync.py` was carried from issue #71's expected-files list and contains no reference to role boundaries, `allowed_profiles`, or the registry. The row is now split, attributed to the issue, and marked unconfirmed.

### 9. Line range off by one (P3)

`ROLE_PROFILE_POLICY` spans `:142-179`, not `:142-178`.

## Rubric notes carried forward, not fixed

Two issue-phase observations were judged acceptable rather than corrected.

**Issue sizing.** The `issue_sizing` rubric flags more than fifteen touched paths as multi-issue-in-disguise, and this issue exceeds that. Splitting was rejected because the code change, the documentation correction, and the generated-inventory regenerate are coupled through one digest — `docs/validation/verified-workflows-legacy-token-inventory.json` covers both code and documentation entries, so a split would leave the first PR failing validation. Planning should still decompose it into units.

**Prerequisite mapping.** No upstream issue or PR blocks this work. The only real ordering constraint is internal — registry edit, profile re-render, inventory regenerate — and it is recorded in both the requirements document and the issue.

## Residual risk

One assumption remains load-bearing and unverifiable from this repository: that declared policy, not the Codex harness, rejected the push during the Hermes run. No workflow run record exists locally under `~/.codex/verified-workflows/state/`. Both the requirements document and the issue carry this as an explicit stop condition — if a red-first reproduction shows the harness refused, the work re-scopes rather than proceeding.
