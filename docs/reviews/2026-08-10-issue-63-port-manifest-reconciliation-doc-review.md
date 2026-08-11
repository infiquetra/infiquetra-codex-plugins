# Document Review — Issue #63 Port Manifest Reconciliation and Companion Harness

The issue #63 plan is ready to guide implementation after all review findings were repaired and re-reviewed.

## Review-result contract

The durable record identifies the reviewed working tree and the completed readiness gate.

| Field | Value |
|---|---|
| Target | `docs/plans/2026-08-10-issue-63-port-manifest-reconciliation-plan.md` |
| Reviewed revision | Working tree; target SHA-256 `e145f62ed0893741abc7fd495ae92e84009dedf287fee65d75b4baafc7c1d58c` |
| Issue | `infiquetra/infiquetra-codex-plugins#63` |
| Reviewer session | `019feec4-5434-7ac0-a5a7-734db56c638c` |
| Reviewer | `gpt-5.6-terra`, high reasoning effort |
| Review artifact | `docs/reviews/2026-08-10-issue-63-port-manifest-reconciliation-doc-review.md` |
| Blocked | false |
| Override | none |
| Final verdict | `REVIEW COMPLETE` |

## Grounding and pins

The plan binds one Codex execution cycle and one companion-source harness without changing the ordinary source checkout.

| Subject | Verified value | Review use |
|---|---|---|
| Codex approved plan base | `43b18477906ba9790ef3ca555ecfd993da068a35` | Required parent of the reviewed plan commit and initial `codex.execution_base` authority. |
| Codex local checkout at review | `0db153bf2ae24156c301708c9a6139eb3d3878d9` | Observation only; the plan requires a fresh mainline check before candidate freeze. |
| Codex `origin/main` at artifact review | `ed8d74f260f029e41ee4e6e44975f9d70522697a` | Observation only; later behavior-bearing drift must stop candidate preparation. |
| Ordinary source checkout `HEAD` | `7f2b98f2ac61431c98d177c25277d287a111aef4` | Preserved checkout; it is never fetched, switched, cleaned, or updated. |
| Ordinary source checkout `origin/main` | `1f6c6df4f080247150f489280836e7f4eda4973d` | Stale local observation, not source authority. |
| Source remote `main` | `b53827bb055e08ccc6aa547cade04aedf4385456` | Exact source base and target for the issue #63 disposable checkout. |
| Companion harness | `tools/run_cross_runtime_outcome_acceptance.py`, blob `7c6c9aac411ec2a119b45e77558298846e7ee7b5`, 99,980 bytes | Verified from a disposable bare fetch of the pinned remote commit. |

## Review rounds and repairs

The earlier findings were repaired in the plan and decision journal, then checked again against the current contract, source evidence, and generated binding.

| Round | Reviewer finding | Exact repair verified | Status |
|---|---|---|---|
| Initial authority review | Initialization did not make every authority input explicit. | U1b now names the manifest, port identifier, disposable source repository, source identity/base/target/pathspec, Codex plan base/execution base/evidence ref, review artifact, classification, runbook, capability snapshot/schema, repository identity, and explicit `[]` policy input. | Resolved |
| Initial schema review | Version dispatch and the empty-policy exception were not exact enough to test. | U1a now requires version 1 to reject `repository` and require nonempty policy; version 2 permits only optional `repository: "source"`; new writes are version 2; `[]` is limited to equal source refs, empty source rows, and all-Codex-local reconciliation rows. | Resolved |
| Initial source review | Companion resolution lacked a safe, reproducible repository and revision boundary. | U2 now resolves `CODEX_PORT_SOURCE_REPO` first, otherwise the Git-common-directory sibling; it verifies normalized origin and exact target `HEAD` before realpath containment, while `repo_head` remains the Codex proof subject. | Resolved |
| Initial mechanical-binding review | The journal edit did not yet state inventory regeneration and validator-digest rotation as a bound pair. | U3 requires regeneration after the journal edit, changes only the inventory digest and adjacent validator reason comment, and requires both inventory check and plugin validation. | Resolved |
| Lifecycle review | The gate that enforces reconciliation could not govern its own first implementation. | U1a is restricted to the Codex-local version-2 substrate and focused tests in its own commit; U1b immediately inventories that commit from the reviewed execution base, classifies every behavior path `codex-local`, renders, and passes classification before companion behavior. | Resolved |
| Lifecycle review | Active validation against later `HEAD` would permanently invalidate historical evidence. | The closed reconciliation state permits current-`HEAD` validation only while evidence is empty and the evidence ref is absent; finalized validation resolves the immutable evidence tag and never later `HEAD`. | Resolved |
| Lifecycle review | The evidence-tag lifecycle was circular or could silently rewind. | U3 commits the finalized candidate before creating the absent tag, validates retained ancestry, forbids finalized-to-active/ref/ancestry/inventory rewinds, and uses reviewed `-attempt-N` refs for changed candidates. | Resolved |
| Lifecycle review | The contract-only version-policy rule could permit an empty policy outside the narrow cycle. | The version-2 `[]` exception is constrained to the stated source-equality, source-empty, and all-Codex-local conditions; issue #63 alone uses it. | Resolved |
| Focused publication review | A local evidence tag would not resolve in a fresh clone or continuous integration checkout. | After local finalized validation and before pull-request creation, U3 pushes only the exact evidence tag without force, reads the exact `origin` ref back as the frozen candidate, fetches only that ref into a disposable clean checkout, and passes finalized-manifest validation there. Any failure stops. | Resolved |
| Final re-review | The repaired remote-publication lifecycle, inventory binding, and plan boundary were rechecked. | Published tags are never moved or deleted; a changed candidate requires a reviewed attempt-suffixed ref; no generic release workflow, tag manager, evidence-chain format, or port control plane was added. | Resolved |

## Root decisions, not reviewer findings

The root session made two proportionality corrections. They are accepted scope decisions rather than defects found by this reviewer.

| Decision | Effect |
|---|---|
| Keep reconciliation to `state`, `expected_count`, `inventory_sha256`, and normalized `rows`. | The existing `codex.evidence_ref` remains the single target authority; reconciliation does not duplicate `target_ref`. |
| Compare selected behavior paths at pull-request merge and post-merge time. | The proof compares normalized inventory plus each selected path's presence, mode, and blob content, not impossible whole-Git-tree equality. |

## Final readiness review

The final plan remains narrow and implementation-ready. It preserves issue #54 as unchanged version-1 historical evidence, upgrades only issue #57 for the one source harness, and keeps the focused capability result, plugin validator result, and full-suite result separate.

| Priority | Remaining finding | Status |
|---|---|---|
| P0 | None | Closed |
| P1 | None | Closed |
| P2 | None | Closed |
| P3 | None | Closed |

The plan requires issue #63 to merge before issue #61 or issue #62 behavior branches. Its pre-freeze mainline check and merge-ref/post-merge selected-path proof make that ordering enforceable without turning unrelated documentation into behavior scope.

## Checks and scope audit

The review stayed report-only until this reviewer-owned durable artifact was authorized.

| Check | Result |
|---|---|
| Issue-phase Saga rubrics | All six core lenses applied: acceptance-criteria clarity, devil's advocate, specification fidelity, context completeness, issue sizing, and prerequisite mapping. No remaining actionable finding. |
| Source remote pin | `origin/main` read back as `b53827bb055e08ccc6aa547cade04aedf4385456`; a disposable bare fetch confirmed the harness path, blob, and size. |
| Generated inventory binding | `python3 scripts/build_legacy_workflow_inventory.py --check` passed; this artifact introduced no legacy-token inventory entry or digest rotation. |
| Document and formatting tests | `PYTHONPATH="$PWD" uv run pytest -q tests/test_saga_doc_formatting.py tests/test_saga_docs_package.py` passed: 40 tests. |
| Narrow validator tests | `PYTHONPATH="$PWD" uv run pytest -q tests/test_validate_codex_plugins.py` passed: 57 tests. |
| Plugin validation | `python3 scripts/validate_codex_plugins.py` passed. |
| Diff whitespace | `git diff --check` passed. |

The artifact adds no implementation behavior. The plan, decision journal, inventory, and validator digest binding remain author-owned uncommitted planning changes; this review adds only this reviewer-owned artifact and any mechanically required inventory binding.

## Residual execution risk

Implementation must still perform the planned live checks. In particular, it must re-evaluate mainline behavior drift before freezing, use the disposable source checkout, publish and read back the exact evidence ref before opening a pull request, and preserve the separate focused, plugin-validator, and full-suite exit results.

REVIEW COMPLETE — no actionable P0, P1, P2, or P3 findings remain.
