# Code Review: Codex V1 Agent Compatibility

- Target: working tree on `fix/codex-v1-agent-compatibility`
- Base: `origin/main` at merge base `38518d825330b44a8232a4e09938452905049d5d`
- Reviewed revision: working tree based on `38518d825330b44a8232a4e09938452905049d5d`
- Plan: `docs/plans/2026-07-17-codex-v1-agent-compatibility-plan.md`
- Work session: pending at review time
- Blocked: no

## Scope Check

**DRIFT DETECTED.** The intended change is a reproducible Sol/Terra V1 catalog override plus a
native selector for the five maintained profiles. The working tree delivers that behavior and also
fixes two validation-adjacent defects exposed by the version bump: frozen cutover evidence was
incorrectly compared to current versions, and two CLI tests leaked real user workflow state through
`HOME`. Both are bounded test/validator changes; neither changes runtime plugin behavior.

The formal merge-base diff contained 31 tracked files. The new generator, generator tests, selector
skill, selector contract test, and plan were still untracked and therefore inspected separately;
they must be included in the delivery commit.

## Findings

### P2

| # | File | Issue | Reviewer | Confidence | Route |
|---|---|---|---|---|---|
| 1 | `plugins/fleet-core/README.md:63` | Source-selection documentation contradicted the implementation | correctness, API contract, maintainability | 100 | resolved |

Finding 1 mattered because operators were told that `install` performed the refreshed-then-bundled
lookup, while `read_source` actually prefers `$CODEX_HOME/models_cache.json` and falls back directly
to the bundled catalog. The README and plan now describe the cache-first behavior, bundled fallback,
refresh precondition, and explicit `--source-json` escape hatch.

No P0 or P1 findings survived the confidence gate.

## Plan Completion

| Unit | State | Evidence |
|---|---|---|
| U1 | DONE | `plugins/fleet-core/scripts/codex_v1_catalog.py`, focused tests, and isolated install/check/rollback proof |
| U2 | CHANGED | Active config, docs, and drift tests now select V1; the digest-bound V2 capability snapshot remains immutable historical evidence instead of being rewritten |
| U3 | DONE | `plugins/verified-workflows/skills/select-agent/` plus plugin inventory and contract tests |
| U4 | PARTIAL | Focused tests, validator, isolated runtime proof, and this review are complete; final full-suite rerun, fresh-session proof, PR, merge, and cleanup remain |

COMPLETION: 2/4 DONE, 0 PARTIAL requirements, 0 NOT-DONE, 1 CHANGED, 1 delivery unit in progress.

## Coverage

- Lenses: correctness, security, testing, maintainability, deploy/migration verification,
  reliability, API contract, adversarial, and agent-native.
- Suppressed: 1 narrow compatibility concern below confidence 75. The line-oriented TOML editor
  rejects configs containing array-of-table syntax; it fails before replacing the config, and no
  current Codex config surface in scope uses that syntax.
- External second opinion: not executed because the best-effort egress action was not approved.
- Runtime evidence: the generated 292 KB catalog was BOM-free, selected V1 for Sol, Terra, and Luna,
  and rollback restored the original isolated config byte-for-byte.
- Residual risk: Ultra remains unsupported under the override. The final proof must use a fresh,
  non-Ultra Codex session and verify host-issued child role, model, and effort.

> Verdict: safe to continue. Finding 1 is resolved, no P0 or P1 issue blocks delivery, and the final
> test and fresh-session gates remain required.
