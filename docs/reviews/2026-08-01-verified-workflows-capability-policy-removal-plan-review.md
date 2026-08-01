# Plan review — Verified Workflows capability-policy removal

Readiness review of the implementation plan for issue 71 before `/work`. Ten findings, all fixed in place. Two were `P1`: the plan as written would have broken the renderer module, because it declared out of scope a code path that constructs the very dataclass fields it deletes.

## Review-result contract

| field | value |
|---|---|
| target | `docs/plans/2026-08-01-verified-workflows-capability-policy-removal-plan.md` |
| reviewed revision | working tree at `0c20724` (target untracked) |
| classification | plan (`docs/plans/` tie-breaker) |
| rubrics run | none — the rubric engine offers `idea`, `spec`, `issue` only, with no `plan` phase; issue-phase rubrics were already run against issue 71 in the 2026-07-31 review |
| blocked | no |
| override rationale | not applicable |
| linked issue | https://github.com/infiquetra/infiquetra-codex-plugins/issues/71 |
| origin | `docs/brainstorms/2026-07-31-verified-workflows-capability-policy-removal-requirements.md` |
| prior review | `docs/reviews/2026-07-31-verified-workflows-capability-policy-removal-doc-review.md` |
| artifact | `docs/reviews/2026-08-01-verified-workflows-capability-policy-removal-plan-review.md` |

## Findings

All ten were fixed in place. None remain open.

| # | priority | area | finding | status |
|---|:---:|---|---|---|
| D1 | P1 | U1 / scope | Scope boundary excluded a branch that constructs the deleted `RoleSpec` fields | fixed |
| D2 | P1 | U2 | Two sites that construct and emit the profile boundary fields were unlisted | fixed |
| D3 | P2 | U6 | Journal supersession chain misstated; a third live entry unaddressed | fixed |
| D4 | P2 | KTD3 / U3 | "One stray path is absorbed" is only true when the agent reports no one-hop finding | fixed |
| D5 | P2 | U5 | Half of the cited `workflow-protocol.md` range had no disposition | fixed |
| D6 | P3 | U2 | Class named `ProfileResolution`, cited as `ResolvedProfile` | fixed |
| D7 | P3 | KTD3 | One-hop cap cited at `:308-311`; actual check is `:310-313` | fixed |
| D8 | P3 | U1 | `allowed_profiles` field line omitted from the `RoleSpec` edit list | fixed |
| D9 | P3 | Open Questions | Both questions answerable from the repository, left open | fixed |
| D10 | P3 | traceability | R9 had no owning unit | fixed |

### D1. Scope boundary contradicted R2 and R4 (P1)

The plan declared `_parse_deterministic` and the `command.network` path out of scope, while R2 removes `allowed_profiles` from `RoleSpec` and R4 removes the boundary fields. That function constructs a `RoleSpec` passing `allowed_profiles=()`, `workspace_cap=None`, and `external_cap=str(command["network"])` at `render_codex_agents.py:800-802`, and its closed-key set at `:830-840` accepts `allowed_profiles` and `boundaries`.

A dataclass constructor cannot pass fields that no longer exist. An implementer honoring the scope boundary could not satisfy R2; one honoring R2 would silently violate the stated scope. The branch is genuinely unreachable — no registry entry uses `kind: deterministic-validator` and no test exercises it — but unreachable is not the same as absent.

Fixed by narrowing the scope boundary to exclude only *deleting* the branch, and adding the constructor and key-set edits to U1.

### D2. Unlisted construction and emission sites for the profile boundary fields (P1)

U2 removed `workspace` and `external` from `PROFILE_POLICY` and the boundary fields from the profile-resolution dataclass, but named neither site that populates them: `resolve_profile` constructs them at `render_codex_agents.py:1091-1092`, and `bundle_receipt()` emits them into the per-profile projection at `:1205-1206`. Same failure mode as D1 — deleting fields whose producers and consumers stay behind. U2's approach now names both.

### D3. Journal supersession chain misstated (P2)

U6 treated `DECISIONS.md:50` (2026-07-24) and `:68` (2026-07-18) as two independent entries to supersede. `:64` records that the first already supersedes the second, conditional on the U8 live cutover gate passing. Writing them as peers would put an inaccurate chain into the permanent record.

Separately, a third entry is live and unaddressed: 2026-07-17 at `:78`, whose `:84` holds that Verified Workflows cannot grant gate authority over changes to its own implementation and that self-hosting patches keep root ownership of implementation, integration, Git, release, and installation. That is the category this change belongs to. It stays true, and a reader of the new entry could reasonably conclude otherwise unless it is named as surviving. U6 now covers both points, and flags the U8 gate status as something to check rather than assume.

### D4. The one-hop cap counts every finding, not only synthesized ones (P2)

KTD3 said one stray path is absorbed and two or more hard-stop. `gate_evaluator.py:307-309` builds `one_hop_findings` from the merged list of agent-supplied and root-adopted findings, so a single undeclared path hard-stops whenever the agent independently reported a one-hop finding, and also sets `approval_required` at `:314-318`.

The behavior is right — the cap bounds total scope drift, not drift by source — but the plan's phrasing would have produced tests that only exercise synthesized findings and miss the interaction. KTD3 now states it, and U3 gains a mixed-source scenario.

### D5. Half of a cited range had no disposition (P2)

U5 cited `workflow-protocol.md:20-23` but described only the fallback change at `:22-23`. Line `:20` asserts "Only `git-integration-operator` may own Git commands" — enforced today by the `GIT_WORD_RE` check that U2 deletes. Leaving it would preserve an unenforced rule, which is the exact defect class this change removes. The sentence's second half, requiring the final `git diff --name-only` validation, stays because R9 pins it and `workflow_dispatch.py:319-322` still enforces it.

### D6-D8. Naming and line-number corrections (P3)

The profile-resolution class is `ProfileResolution`; the plan called it `ResolvedProfile`, so a grep would have returned nothing. The one-hop cap check is at `gate_evaluator.py:310-313`, not `:308-311` — the Sources table's broader `:305-318` was already right. U1's `RoleSpec` edit list named `:346-347` but `allowed_profiles` sits at `:345` and R2 requires it gone.

### D9. Both open questions were answerable (P3)

A sweep for every removed identifier across `plugins/`, `scripts/`, and `tests/` settles both. `test_agent_tier_sync.py` contains no reference to anything this change touches. `GIT_WORD_RE` is defined at `workflow_dispatch.py:23` and used only at `:315`, so it is deleted outright rather than retained. Both are now recorded with their answers instead of left open.

The same sweep bounds the change: outside the registry's 140 references, only `render_codex_agents.py` (32), `workflow_dispatch.py` (4), `test_role_registry.py` (4), and `test_sync_codex_agents.py` (1) are affected. Fleet Core's 18 are the separate vocabulary held out of scope.

### D10. R9 had no owning unit (P3)

Every other requirement appears in some unit's Requirements list. R9 — the set of mechanics that must not change — appeared in none, though U2's error-path scenarios prove it. Now listed under U2.

## Citations verified

Spot-checking found the plan's anchors accurate apart from the corrections above. Confirmed against source: the boundary parse and equality assert at `render_codex_agents.py:642-658`; the profile-transition raise at `:640-641`; the independence expectation at `:628-632`; `resolve_role` and its allowlist gate at `:949`, `:960-964`; `bundle_receipt` at `:1187` with role keys at `:1228`, `:1234-1235`; all four dispatch anchors at `workflow_dispatch.py:312-313`, `:315-318`, `:319-322`, `:325`, `:330-336`; the undeclared-path raise at `result_contract.py:252-253`; every test citation; every documentation line; both journal entries and the archived plan; 28 roles each carrying `boundaries` and `allowed_profiles`, all `kind: agent-lens`; 134 inventory entries; and both `--check` and `--write` on the inventory builder.

## Residual risk

Unchanged from the origin review and not resolvable from this repository: no run record exists under `~/.codex/verified-workflows/state/` for the Hermes failure, so the claim that declared policy rather than the Codex harness blocked the push remains an inference. U2's first test scenario is the red-first reproduction, and the plan stops for re-scope if it shows otherwise.

Newly noted: whether the U8 live cutover gate passed determines which of the two prior journal decisions was operative when this change begins. U6 must establish it from the record rather than assume, and say so plainly if the record does not settle it.
