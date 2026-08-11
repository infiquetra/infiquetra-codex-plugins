# Document Re-review — Issue #63 Code-Review Plan Correction

The corrected issue #63 plan is ready to drive the post-U2 repair gate; DR-4, DR-5, and DR-6 are closed and no actionable P0 through P3 finding remains.

## Review-result contract

This independent re-review covers the complete current plan, every prior finding, the completed code review, live GitHub issue #63, repository source, and `AGENTS.md`.

| Field | Value |
|---|---|
| Target | `docs/plans/2026-08-10-issue-63-port-manifest-reconciliation-plan.md` |
| Reviewed revision | Working tree at branch commit `ae0e4f9fcb11e9490f0a87931f82e6e85f2e7f65`; target SHA-256 `5524b47883307e631a5104d17c36e373626c193bdd6547044019db0409067fe2` |
| Linked issue | `infiquetra/infiquetra-codex-plugins#63` |
| Earlier document reviews | `docs/reviews/2026-08-10-issue-63-port-manifest-reconciliation-doc-review.md`; `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-plan-re-review.md` |
| Completed code review | `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-code-review.md` |
| Review artifact | `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-code-review-plan-correction-review.md` |
| Blocked | `false` |
| Applied fixes | DR-4, DR-5, and DR-6 verified resolved; this reviewer edited only this artifact. |
| Override | None |
| Final verdict | `DOC REVIEW COMPLETE` |

## Applied fixes

All three prior findings are resolved by the corrected plan and current repository evidence.

| ID | Prior priority | Correction verified | Evidence | Status |
|---|---|---|---|---|
| DR-4 | P1 | Unit U3 admits only the already-attributed legacy-workflow inventory and digest drift, then requires that drift to be cleared inside Unit U3 before any candidate freeze, evidence capture or finalization, tag, or PR. | Plan lines 238-240 and 254-262; the current inventory check and its one focused test fail only on the stale generated inventory expected at this boundary. | Closed |
| DR-5 | P2 | The runtime-reference boundary now names three whole roots and ten exact Saga files, while retaining exact exclusions. | Plan lines 46-52, 98-102, and 226-230; live consumer and negative-boundary probes below. | Closed |
| DR-6 | P3 | Every prose paragraph is now at most three sentences. | A paragraph probe checked 161 Markdown blocks after excluding the non-sentence `R#.` and `KTD#.` identifiers and found zero violations. | Closed |

## Readiness summary

The plan is internally consistent, source-grounded, and ready for the prospective authority-binding gate that precedes repair implementation.

The repair remains proportionate to an ordinary plugin repository. It restores existing authority, completes the existing manifest contract and tests, and adds no registry, scanner, tag manager, evidence format, or control plane.

## Remaining findings by priority

No actionable P0, P1, P2, or P3 finding remains.

| Priority | Remaining finding | Status |
|---|---|---|
| P0 | None | Closed |
| P1 | None | Closed |
| P2 | None | Closed |
| P3 | None | Closed |

## Unit U3 entry-gate proof

The corrected gate no longer requires Unit U3-owned work before Unit U3 can begin.

| Boundary | Plan requirement | Verification |
|---|---|---|
| Must pass before Unit U3 | Amended authority binding, active classification, focused repair tests including affected Codex 0.147 behavior checks, and independent code re-review with no unresolved P0-P3 finding. | Plan line 254 names only completed pre-Unit-U3 repair and review gates. |
| Sole permitted entry drift | The already-attributed legacy-workflow inventory and its digest binding. | Plan line 256 says “Only” this drift may remain. `python3 scripts/build_legacy_workflow_inventory.py --check` reports only `stale legacy workflow inventory`. |
| Must become green inside Unit U3 | Regenerated inventory, rotated digest binding, plugin validator, and full suite as separate results. | Plan lines 256 and 260-262 assign the work to Unit U3. |
| Must remain blocked until green | Candidate freeze, evidence candidate capture or finalization, tag creation, and PR creation. | Plan line 256 places every consequential boundary after the Unit U3 repair and green checks. |

The completed code review independently established that, after the shared-snapshot repair, only the legacy inventory test and the two combined repository-validation tests retain the same inventory cause. The corrected entry rule therefore admits one attributed cause, not arbitrary repository debt.

## Exact runtime-reference boundary proof

The three whole roots and ten exact Saga files are the complete current top-level runtime-reference boundary.

| Selected surface | Live source proof | Result |
|---|---|---|
| `plugins/discord-identity-assets/references/` | The root contains five files, and the installed Discord identity skill names all five at `plugins/discord-identity-assets/skills/discord-identity-assets/SKILL.md:85-89`. | Whole root correct: 5 files and 5 skill links. |
| `plugins/python-toolkit/references/` | The root contains four files, and installed Python Toolkit skills name all four. | Whole root correct: 4 files and 4 unique skill links. |
| `plugins/saga/references/rubrics/` | `plugins/saga/scripts/lifecycle_review.py:59,140-144` selects the phase/tier directory and loads every `*.md` rubric. | Whole root correct: 24 rubric files loaded by the lifecycle engine. |
| Ten exact Saga root files | Every named file has an active skill or script consumer. | Exact allowlist correct: 10 of 10 consumers resolved. |

| Exact Saga file | Active consumer evidence |
|---|---|
| `bridge-signatures.json` | `plugins/saga/scripts/bridge_signatures.py:20` |
| `effort-policy.yaml` | `plugins/saga/scripts/effort_ledger.py:36` |
| `engine-dispatch.md` | `plugins/saga/skills/doc-review/SKILL.md:150` |
| `engine-registry.yaml` | `plugins/saga/scripts/check_engine_registry.py:17` |
| `formatting-style.md` | `plugins/saga/skills/plan/SKILL.md:185` and the installed document-writing skills |
| `model-releases.yaml` | `plugins/saga/scripts/check_engine_registry.py:18` |
| `operator-choice.md` | `plugins/saga/skills/code-review/SKILL.md:61` and other installed Saga skills |
| `outcome-cross-runtime.md` | `plugins/saga/skills/outcome/SKILL.md:63` |
| `outcome-spec.md` | `plugins/saga/skills/outcome/SKILL.md:188` |
| `saga-spec.md` | `plugins/saga/skills/resume/SKILL.md:40,137` and other installed Saga skills |

The six other top-level Saga reference files have zero skill or script consumers by basename. The plan correctly excludes them as unreferenced prose rather than selecting the whole `plugins/saga/references/` root.

The only other plugin-level reference root is `plugins/fleet-core/references/`. Active Fleet scripts, skills, configuration, roles, and agents contain zero references to its two files; `scripts/validate_codex_plugins.py:384` explicitly classifies `effort-convention.md` as lineage documentation.

## Completed code-review correction mapping

All seven completed code-review findings have one bounded repair and an explicit verification path.

| Code-review finding | Plan correction | Status |
|---|---|---|
| #1 shared Codex 0.147 snapshot overwrite | Restore the accepted shared snapshot, preserve the runtime proof unchanged, create and bind the issue #63 schema-r4 snapshot only. | Ready |
| #2 omitted runtime surfaces | Add plugin agents, the proved reference boundary, two exact Hermes contracts, the marketplace, and the Codex configuration with add/delete/rename tests and negative exclusions. | Ready |
| #3 finalized validation reads live authority | Read digest-bound authority bytes from the immutable evidence candidate for finalized version 2. | Ready |
| #4 finalized evidence is empty or mutable | Require nonempty finalized evidence and byte-equivalent evidence after finalization. | Ready |
| #5 source and Codex authority can move | Freeze the six named source and Codex repository/ref fields across version-2 transitions. | Ready |
| #6 missing integrated lifecycle proof | Add the active-to-finalized declared-source `validate_manifest` test, six mutation failures, and later-`HEAD` stability. | Ready |
| #7 formatter-only churn | Restore pre-existing formatting for syntax-unchanged definitions and prohibit unrelated formatting or hardening scope. | Ready |

The post-repair sequence is also complete. Plan lines 238-244 require active reconciliation and classification validation after repairs, separate focused checks, and independent code re-review before Unit U3.

## Live issue and repository consistency

Live issue #63 and the plan still agree that new declared-source evidence belongs only to issue #63 and issue #57 remains immutable history.

The issue has five distinct acceptance criteria and retains the exact origin, target, containment, immutable tag, clean-checkout, merge-ref, post-merge, and issue-ordering outcomes. It also retains the explicit no-new-control-plane boundary.

Live `origin/main` remains `ed8d74f260f029e41ee4e6e44975f9d70522697a`. Neither the issue #57 historical evidence tag nor the issue #63 evidence tag exists remotely, which remains the required pre-Unit-U3 state.

The active manifest remains in the expected pre-correction-gate state: schema version 2, active reconciliation, empty evidence, the earlier plan digest, and two document-review authority entries. The operator did not authorize the prospective plan-digest, review-cardinality, manifest, or classification mutation in this review.

## Issue-phase rubric review

All three core issue rubrics and all three applicable conditional rubrics pass after the corrections.

| Rubric | Applicability | Verdict | Evidence |
|---|---|---|---|
| Acceptance criteria clarity | Core | PASS | The five live issue criteria and the plan gates now produce the same pass/fail verdict without a circular prerequisite. |
| Devil's advocate | Core | PASS | The repair is the smallest correction to the seven reviewed defects and introduces no adjacent subsystem. |
| Specification fidelity | Core | PASS | The plan remains within requirements R22-R27 and live issue #63 while preserving issue #54 and issue #57 history. |
| Context completeness | Conditional; non-trivial repository change | PASS | Every repair file, symbol, test path, runtime-reference root or exact file, and negative boundary is named. |
| Issue sizing | Conditional; multi-unit branch | PASS | The remaining repair is one bounded plugin-repository PR and needs no new implementation unit. |
| Prerequisite mapping | Conditional; staged U1/U2/U3 lifecycle | PASS | Unit U3 entry, allowed drift, internal repair, green freeze gate, issue ordering, and external proof sequence are explicit. |

## Checks

Only narrow document and read-only probes were run.

| Check | Result |
|---|---|
| Installed Saga document-review workflow | Read completely from Saga `0.83.0+codex.20260729205037`, including all six issue rubrics and the shared formatting contract. |
| Plan handoff digest | Passed: SHA-256 is exactly `5524b47883307e631a5104d17c36e373626c193bdd6547044019db0409067fe2`. |
| Completed code-review readback | Passed: all seven findings, their evidence, proportional fixes, and the attributed legacy-inventory residual were checked against the plan. |
| Narrow Saga document tests | Passed: `PYTHONPATH="$PWD" .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_saga_doc_formatting.py tests/test_saga_docs_package.py` — 40 passed in 0.07 seconds. |
| Paragraph limit | Passed: 161 Markdown paragraph blocks checked, zero blocks over three semantic sentences. |
| Exact reference consumers | Passed: 10 of 10 exact Saga files have active consumers; zero unexpected Saga root files have skill or script consumers. |
| Whole reference roots | Passed: Discord 5 files/5 links; Python Toolkit 4 files/4 unique links; Saga 24 rubric files loaded by the lifecycle engine. |
| Negative reference boundary | Passed: zero Fleet runtime mentions; Fleet effort guidance is classified as lineage documentation; six unselected Saga root files have zero active consumers. |
| Legacy inventory boundary | Expected entry drift confirmed: builder `--check` reports `stale legacy workflow inventory`; the focused currentness test reports 1 expected failure on the same generated-file mismatch. |
| Live GitHub issue #63 readback | Passed: corrected intent, acceptance criteria, and superseding comment remain current. |
| Live remote readback | Passed: `origin/main` is `ed8d74f...`; neither evidence tag exists remotely. |
| Plan whitespace | Passed: scoped `git diff --check`. |
| Initial uv launcher | The sandbox denied the user cache; the same document tests were rerun from the existing repository virtual environment with the cache provider disabled and passed. |
| Broader code tests and validators | Not run; they belong to repair and Unit U3, not this narrow document re-review. |

## Residual risk and blocked status

Repair implementation is not blocked by document readiness. The next authorized lifecycle action is the plan-correction authority-binding gate; this review did not perform it or begin repairs.

The remote tag publication, source-harness execution, final clean-checkout validation, PR merge-ref comparison, and post-merge comparison remain intentionally unexecuted Unit U3 work rather than review defects.

DOC REVIEW COMPLETE
