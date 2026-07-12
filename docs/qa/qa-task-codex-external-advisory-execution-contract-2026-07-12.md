# QA Report: External Advisory Execution Contract

| Field | Value |
|-------|-------|
| Date | 2026-07-12 |
| Target | PR #28 |
| Reviewed revision | `89ad9d2db6334b2f3df679c59e4710234de1fd91` |
| Merge state | post-merge on `main` |
| Tier | Standard |
| Scope | behavior, security, API, deployment, config, docs |
| Saga | `task-codex-external-advisory-execution-contract` |
| Backend | Verified Workflow plus fresh deterministic post-merge checks |

## Ship Verdict: ship

No critical, high, or medium findings exist in any in-scope risk class, so the Standard-tier blocking threshold is clear.

## Health Score: 100 (baseline n/a, delta n/a)

| Risk class (in scope) | Score |
|-----------------------|-------|
| behavior | 100 |
| security | 100 |
| API | 100 |
| deployment | 100 |
| config | 100 |
| docs | 100 |

The score is the deterministic gstack-formula port over assigned severity counts. It is a signal; the severity-banded verdict above is the decision.

## Verified Workflow evidence

- The approved workflow run `record:workflow-run:6240d68db9bafff53e1337320acebce6b87985e548022a067ff357f35bd85b00` passed with no blockers, remediation items, or warnings.
- Protected subject `record:subject:fcbbc2764ae2611a50c105d4026a9ad516ea3c5651b1466ffe293d9ad712d07a` covered the external-advisory implementation, proof, latest evidence bundle, tests, and lifecycle documentation.
- The protected feature head and shipped merge commit both resolve to Git tree `22dc915a9f1ecee82fa689bb8fcffbbb09e28bca`, binding the workflow evidence to the shipped bytes.
- Final workflow reviewer scores were architecture 9.6, security 9.5, adversarial 9.4, and testing 9.4, with no findings.
- No provenance-manifest tree exists under the resolved Git common directory. The adjudicated verified ratio is therefore no data, not zero.

## Top findings

None.

## Summary by severity

| Severity | Count | Blocks at this tier? |
|----------|-------|----------------------|
| critical | 0 | yes |
| high | 0 | yes |
| medium | 0 | yes |
| low | 0 | no |

## Pass/fail by risk class

| Risk class | Result | Evidence |
|------------|--------|----------|
| behavior | pass | `159` focused lifecycle, adapter, runtime, store, policy, workspace, release, onboarding, registry, and port-contract tests passed at the merge commit. This plugin repository has no UI surface, so browser QA is not applicable. |
| security | pass | Scoped Bandit scan of changed Python source reported zero medium/high findings; the Verified Workflow security review and scanner also passed. |
| API | pass | The same `159` tests exercised action request/approval/evidence contracts, lifecycle integration, provider onboarding, registry composition, receipt validation, and CLI behavior. |
| deployment | pass | Exact evidence-tag verification passed twice consecutively with digest `a2dfa2ae5b6b456ed8f4e96151fd490822816376f44a73d25f339c3b9f04de09`; cutover, installation, fresh-session, and rollback evidence remained valid. |
| config | pass | Port classification, U2-U8 unit gates, cutover gate, engine registry overlays, plugin manifests, and repository cutover validation passed. |
| docs | pass | Generated classification was current, the port manifest validated, and repository cutover validation found no stale documentation or inventory bindings. |

## Acceptance commands

```text
python3 -m pytest -q -p no:cacheprovider <17 focused test files>  # 159 passed
uv run bandit -q -ll <changed Python source files>                # zero findings
external_action_release_matrix.py --verify --expected-ref ...    # passed twice
port_contract.py validate --stage classification                 # passed
port_contract.py validate --stage unit --unit U2..U8             # passed
port_contract.py validate --stage cutover                        # passed
validate_codex_plugins.py --mode cutover                         # passed
port_contract.py render --check                                  # current
external_action.py --help                                        # passed
```

## Findings

None.

## Recommended regression tests

- Preserve the exact-ref regression where an untracked action-store `.lock` exists, and require repeated verification to remain idempotent.
- Re-run the attended provider/install/rollback matrix when provider CLI recipes, receipt schemas, installation behavior, or rollback logic changes.
- Keep the six-stage lifecycle contract parameterization aligned whenever a Saga stage or default action bundle changes.

## Deferred (with repro)

None.
