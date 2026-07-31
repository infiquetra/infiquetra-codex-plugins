---
title: codex#67 — Resolve Frozen-Source Port Oracles From Detached Worktrees
type: fix
status: active
date: 2026-07-30
origin: https://github.com/infiquetra/infiquetra-codex-plugins/issues/67
---

# codex#67 — Resolve Frozen-Source Port Oracles From Detached Worktrees

## Summary

Make the two frozen-source port-contract modules locate the authoritative source checkout from Git's recorded common directory when a clean detached worktree runs the suite. Keep `CODEX_PORT_SOURCE_REPO` as an explicit override, verify the selected checkout's `origin`, and fail the affected oracle tests when neither route is trustworthy.

## Problem Frame

The default lookup in both modules derives `ROOT.parent / "infiquetra-claude-plugins"` (`tests/test_lease_registry_forward_compat_port_contract.py:61-72`, `tests/test_codex_627_seam_refreeze_port_contract.py:68-93`). That works only from a sibling checkout; it cannot work from the clean detached worktrees required for full-suite gates.

Current-main verification at `12b5f2c` confirmed the defect outside the workspace: the two modules produced 25 passed and 8 skipped with no environment override, while the verified Claude checkout produced 33 passed when supplied through `CODEX_PORT_SOURCE_REPO`. The issue's claim that the skips lack a remedy is stale: both modules now name the variable in `-rs` output, but the authoritative default gate still weakens itself by skipping all eight frozen-source oracle tests.

Git records the parent clone independently of a worktree's checkout path. From the detached worktree, `git rev-parse --path-format=absolute --git-common-dir` returned the primary clone's `.git` directory, so the source sibling can be derived without a machine-specific path. This is an established repository pattern (`tests/test_outcome_store.py:76-78`).

---

## Requirements

R1. A clean detached worktree created outside the workspace resolves the required Claude source checkout without setting `CODEX_PORT_SOURCE_REPO` when that checkout is a sibling of the primary Codex clone.

R2. `CODEX_PORT_SOURCE_REPO` remains the documented highest-precedence override for layouts that do not have the sibling checkout.

R3. Every resolved source checkout is a Git worktree whose `origin` identity matches the manifest's `source.repository_id`; a wrong checkout must not satisfy a frozen-source oracle.

R4. When no valid source checkout can be resolved, each affected oracle test fails loudly with a message containing `CODEX_PORT_SOURCE_REPO`; the default gate must not return green by skipping those tests.

R5. The two current frozen-source port-contract modules use one shared resolution mechanism and contain no local fallback or skip logic.

R6. The portability runbook states the automatic detached-worktree resolution, the environment override, and the loud failure condition.

R7. Implementation leaves `scripts/port_contract.py`, all port manifests, continuous-integration configuration, and the unrelated `.claude/` ignore defect unchanged. The planning-required decision-journal entry has already produced one authorized generated update to `docs/validation/verified-workflows-legacy-token-inventory.json` and its pinned hash in `scripts/validate_codex_plugins.py`; no implementation unit may extend that validation-evidence change.

---

## Key Technical Decisions

**KTD1 — Resolve through Git's common directory before failing.** The shared resolver first accepts an explicitly configured `CODEX_PORT_SOURCE_REPO`; otherwise it asks Git for the current clone's absolute common directory, derives the primary checkout and then its sibling named by the manifest source repository identifier. This survives a detached worktree whose own parent is unrelated to the workspace, unlike the current `ROOT.parent` rule.

**KTD2 — Validate repository identity, not only `.git` presence.** A candidate must be a Git worktree and expose an `origin` URL that normalizes to the manifest's `source.repository_id`. A path to any Git repository is insufficient because re-deriving a frozen inventory from the wrong source would create misleading green evidence.

**KTD3 — Fail affected oracles closed when resolution fails.** The resolver reports the override name, expected repository identity, and attempted automatic route through a test failure rather than `pytest.skip`. A source-free clone cannot truthfully execute a frozen-source oracle, so a red gate is preferable to a successful gate that omitted its strongest port checks.

**KTD4 — Keep the resolver in test support and leave the sealed validator alone.** Extend `tests/conftest.py` with the shared resolver and test it in a focused companion module. The scope is the pytest oracle layer; adding a local-path mapping to `scripts/port_contract.py` would change the sealed manifest validator and incorrectly broaden this repair.

---

## Implementation Units

### U1. Add a shared, identity-checked port-source resolver

Create one test-support resolver that discovers a source checkout safely from any linked worktree.

**Goal:** Satisfy R1-R4 with a small, directly testable interface that receives the current repository root and expected source repository identifier.

**Requirements:** R1, R2, R3, R4.

**Dependencies:** None.

**Files:** Modify `tests/conftest.py`; create `tests/test_port_source_resolution.py`.

**Approach:** Give an explicit `CODEX_PORT_SOURCE_REPO` precedence. Without it, resolve the absolute Git common directory, derive the primary clone's parent directory, and look for the sibling named by the terminal component of `source.repository_id`. Normalize SSH and HTTPS `origin` forms before comparing them to the expected identifier. Return only a verified checkout; make absence, Git-command failure, a non-worktree candidate, or an identity mismatch a clear failure that preserves the override remedy.

**Patterns to follow:** `tests/test_outcome_store.py:76-78` for common-directory invariance; `plugins/saga/scripts/outcome_compat.py:133-159` and `tests/test_outcome_cross_runtime.py:109-152` for Git-command failure and remote-identity handling.

**Test scenarios:** Red-first: record the current source-free detached-worktree invocation returning success with skipped oracle tests; that successful-but-incomplete result contradicts R4 before the resolver exists. A valid explicit override wins over automatic discovery. A detached-worktree common directory locates a valid sibling source checkout. A missing candidate, malformed Git result, or unavailable Git command reports `CODEX_PORT_SOURCE_REPO` and does not skip. A candidate whose `origin` is another repository fails with both the expected and observed identities. A valid source with either normalized SSH or HTTPS GitHub URL is accepted.

**Verification:** The focused resolver tests demonstrate automatic discovery, override precedence, and fail-closed behavior without relying on the operator's workspace path.

### U2. Migrate both frozen-source contracts to the shared resolver

Replace the two divergent local lookup functions with the tested resolver and preserve every existing oracle assertion.

**Goal:** Satisfy R4-R5 without changing the frozen ranges, manifests, or what the port oracles assert.

**Requirements:** R3, R4, R5, R7.

**Dependencies:** U1.

**Files:** Modify `tests/test_lease_registry_forward_compat_port_contract.py`; modify `tests/test_codex_627_seam_refreeze_port_contract.py`; extend `tests/test_port_source_resolution.py` if migration-structure coverage belongs there.

**Approach:** Replace `DEFAULT_SOURCE_REPO`, `_source_repo()`, and per-test `pytest.skip` branches with one import of the shared resolver, passing the existing manifest's `source.repository_id`. Leave the frozen range constants, inventory derivation, and assertions intact. Add a focused structural regression guard that both modules use the shared mechanism so a future port cannot restore a copy-pasted resolver.

**Patterns to follow:** The existing module contracts at `tests/test_lease_registry_forward_compat_port_contract.py:90-176` and `tests/test_codex_627_seam_refreeze_port_contract.py:86-93`; the per-port-gate precedent recorded in `docs/engineering-journal/DECISIONS.md` under the 2026-07-19 lease-safe-substrate decision.

**Test scenarios:** In an external detached worktree with its primary clone beside the Claude checkout, both modules run all 33 tests without an environment override. A correct explicit override also runs all 33 tests. A missing or wrong source checkout makes the source-dependent tests fail with the remedy instead of yielding a green skip-only result. The named inventory and frozen-range assertions remain unchanged and pass against the verified Claude checkout.

**Verification:** `PYTHONPATH=. uv run pytest -q tests/test_lease_registry_forward_compat_port_contract.py tests/test_codex_627_seam_refreeze_port_contract.py` reports no skips in the representative detached-worktree layout, and `CODEX_PORT_SOURCE_REPO=<valid-clone>` produces the same passing results.

### U3. Document the resolver contract and prove the authoritative gate

Make the required port runbook describe the same source-resolution contract the tests enforce.

**Goal:** Satisfy R6 while proving the repaired default gate, per-port contracts, and repository validation remain sound.

**Requirements:** R1, R2, R4, R6, R7.

**Dependencies:** U1, U2.

**Files:** Modify `docs/portability/claude-to-codex-plugin-port-runbook.md`.

**Approach:** Add the default resolution order, `CODEX_PORT_SOURCE_REPO` override, origin-identity requirement, and fail-closed outcome to the validation guidance. Preserve the existing classification and port-manifest rules; do not alter the parser fixture in `tests/test_port_contract.py`, whose `../infiquetra-claude-plugins` value tests CLI argument parsing rather than oracle discovery.

**Patterns to follow:** The runbook's validation and stop-rule sections at `docs/portability/claude-to-codex-plugin-port-runbook.md:172-179` and `:208-266`.

**Test scenarios:** Test expectation: none -- this is an operator-documentation update. The implementation verification must demonstrate that the documented no-environment detached-worktree command runs all frozen-source oracle tests, that an invalid override fails with the documented remedy, and that the port-contract test selection remains green.

**Verification:** In a clean detached worktree created outside the workspace, run the exact full gate and confirm zero failures and no skips from either frozen-source module. Run `PYTHONPATH=. uv run pytest tests/ -q -k port_contract` and `python3 scripts/validate_codex_plugins.py`; both must pass. Confirm `scripts/port_contract.py` and every file under `docs/portability/ports/` are absent from the diff.

---

## System-Wide Impact

The repair changes only test discovery for two current frozen-source contracts, but it closes an enforcement gap that affects every future port patterned after them. Of the 17 current port manifests, eight name `infiquetra/infiquetra-claude-plugins` as their source and two name `openai/codex`; the resolver takes the manifest identifier so it does not encode Claude-specific identity beyond the current environment-variable compatibility surface.

No production plugin behavior, release artifact, deployment, or GitHub workflow changes. The authoritative local full-suite gate becomes stricter in source-free layouts: it correctly turns red instead of returning a passing result with frozen-source tests missing.

---

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| An unrelated sibling Git checkout is selected. | Require normalized `origin` identity to match `source.repository_id` before any frozen-range command runs. |
| A nonstandard clone layout has no sibling source. | Keep the explicit environment override; otherwise fail with the precise remedy rather than skipping. |
| Git metadata is unavailable or malformed. | Treat the discovery error as a test failure that names the required override and never fall back to an unchecked path. |
| The shared helper drifts from one contract module. | Delete both local resolvers and add a focused regression guard for shared use. |
| Scope expands into manifest-validation redesign. | Preserve the sealed `scripts/port_contract.py` and require an empty diff for it and all port manifests. |

---

## Prerequisites

No pending GitHub issue or pull request is a prerequisite: both target modules and their frozen source manifests are present on current `main`. Execution needs a linked Git worktree with a usable common Git directory plus either a sibling checkout whose `origin` matches the manifest source repository identifier or an explicitly supplied `CODEX_PORT_SOURCE_REPO`; the frozen base and target objects must be available in that checkout.

This repair is a prerequisite for future frozen-source port contracts to rely on the default full-suite gate. It does not reopen or re-validate completed ports; a new red result from an unchanged existing contract is a stop condition, not permission to alter that contract.

---

## Scope Boundaries

**Non-goals:** Fixing `.claude/` ignore behavior; adding continuous integration; editing `scripts/port_contract.py`; changing frozen ranges or port manifests; rerunning completed-port evidence; and changing the unrelated Outcome test-order issue.

**Authorized planning bookkeeping:** Adding the required decision-journal entry regenerated `docs/validation/verified-workflows-legacy-token-inventory.json` and its historical-digest binding in `scripts/validate_codex_plugins.py`. The operator explicitly approved that generated maintenance update before review. It is complete, validation-clean, and outside the U1-U3 execution write set; no other historical evidence may change.

**Deferred to Follow-Up Work:** Adding frozen-source oracle modules for the other six Claude-source manifests, or introducing a broader source-checkout registry for unrelated upstream repositories. The shared resolver should remain generic enough to support that work, but this issue changes only the two modules that currently execute frozen-source re-derivation.

---

## Sources

- GitHub issue #67, live state verified 2026-07-30: `requirements-ready`, no comments, current main `12b5f2c`.
- `tests/test_lease_registry_forward_compat_port_contract.py:61-176` and `tests/test_codex_627_seam_refreeze_port_contract.py:68-93`.
- Detached-worktree measurement at current main: 25 passed / 8 skipped without the override; 33 passed with the verified Claude checkout.
- `tests/test_outcome_store.py:76-78`, which already treats Git's common directory as invariant across worktrees.
