# Code review — Issue 61 Claude adapter boundaries

**Verdict: CLEAN.** The repaired Issue 61 implementation at `26fed027e4f76db20d35f053d260b50c4b99d501`
has no actionable P0, P1, P2, or P3 findings against `origin/main`.

## Review-result contract

| field | value |
|---|---|
| reviewer | Codex session `019feeec-62e8-78e2-961e-333d1df15e29`, `gpt-5.6-terra` with high reasoning effort |
| target | branch `fix/issue-61-claude-adapter-boundaries` against `origin/main` |
| merge base | `43b18477906ba9790ef3ca555ecfd993da068a35`; reviewed `origin/main` was `ed8d74f260f029e41ee4e6e44975f9d70522697a` |
| initial implementation revision | `6aedeeaebe534f87599866d3c6ecaf466e4ba941` |
| repair revision | `26fed027e4f76db20d35f053d260b50c4b99d501` |
| mode and backend | report-only, inline; no subagent dispatch |
| blocked | no — no P0 or P1 findings remain |
| linked issue | `infiquetra/infiquetra-codex-plugins#61` |
| plan | `docs/plans/2026-08-10-issue-61-claude-adapter-boundaries-plan.md` |
| prior document review | `docs/reviews/2026-08-10-issue-61-claude-adapter-boundaries-doc-review.md` |
| work session | `docs/work-sessions/2026-08-10-issue-61-claude-adapter-boundaries.md` |

## Scope and completion audit

**Scope Check: CLEAN.** The branch changes the approved Claude command line interface effort and
macOS identity boundaries, their registry representation, tests, the adapter contract, and required
historical-inventory bindings. The repair commit is confined to the three code-review findings.

| Plan item | State | Evidence |
|---|---|---|
| U1 — registry effort contract | DONE | `plugins/saga/references/engine-registry.yaml:31-41` declares `--effort high`; `plugins/saga/scripts/engine_registry.py:309-334` tokenizes recipes and rejects blank, duplicate, or mismatched values while allowing no flag. |
| U2 — adapter launch and receipt boundary | DONE | `plugins/saga/scripts/external_action_adapters.py:89-90` emits the configured pair; `:425-469` preserves invocation-digest validation and requires one matching two-token receipt pair; `:511-520` fails unavailable before launch for invalid effort or blank `USER`. |
| U3 — contract and regression coverage | DONE | `plugins/saga/references/dispatch-adapter-contract.md:20-29` distinguishes requested arguments from provider-observed effort; focused tests cover all five values and receipt failure paths. |
| Attended macOS Keychain smoke | UNVERIFIABLE | The review did not access credentials or run live providers. The plan requires an attended, sanitized comparison using existing authentication. |
| Installed-plugin fresh-session proof | UNVERIFIABLE | The review did not install or refresh plugins. A separately owned live session must prove the installed surface after authorization. |

**COMPLETION: 3 DONE, 0 PARTIAL, 0 NOT-DONE, 0 CHANGED, 2 UNVERIFIABLE.** The two unverifiable
items are remaining live gates, not code-review findings.

## Original findings and dispositions

| # | Priority | Original finding | Disposition | Direct re-review evidence |
|---|---:|---|---|---|
| 1 | P2 | A receipt could omit the configured effort from its recorded process command arguments and still pass the invocation-digest check. | FIXED in `26fed027e4f76db20d35f053d260b50c4b99d501` | `external_action_adapters.py:443-469` rejects absent, duplicate, blank, equals-form, and mismatched effort arguments while `:425-426` retains digest validation. `tests/test_external_action_adapters.py:123-172` covers both the malformed argv cases and a digest mismatch. |
| 2 | P2 | The registry validator could miss a quoted `--effort` token and accept a recipe whose effort disagreed with the invocation. | FIXED in `26fed027e4f76db20d35f053d260b50c4b99d501` | `engine_registry.py:312-334` runs `shlex.split()` before token inspection, returns only when no normalized effort token exists, and rejects conflicting values. `tests/test_engine_registry_lint.py:119-153` exercises quoted pair and equals forms. |
| 3 | P3 | Regression coverage exercised only `high` and `xhigh`, leaving three documented values unproved. | FIXED in `26fed027e4f76db20d35f053d260b50c4b99d501` | `plugins/saga/tests/test_external_action_adapters.py:35-97` parameterizes the launch proof over all five maintained `CLAUDE_EFFORTS` values. |

## Final re-review result

The direct re-review inspected the complete branch diff from `origin/main` through
`26fed027e4f76db20d35f053d260b50c4b99d501`. Correctness, security, testing, maintainability, and
reliability coverage found no regression in the restricted child environment, pre-launch unavailable
paths, requested-versus-observed receipt semantics, or non-Claude compatibility.

No actionable P0, P1, P2, or P3 findings remain. No finding was suppressed for low confidence.

## Evidence

| Check | Result |
|---|---|
| Focused registry and adapter suites | `48 passed` — `plugins/saga/tests/test_external_action_adapters.py`, `plugins/saga/tests/test_engine_routing.py`, `tests/test_external_action_adapters.py`, and `tests/test_engine_registry_lint.py` |
| Ruff on changed Python files | passed |
| `python3 scripts/validate_codex_plugins.py` | passed |
| `git diff --check origin/main...26fed027e4f76db20d35f053d260b50c4b99d501` | clean |

## Remaining live gate

The attended macOS Keychain smoke and installed-plugin fresh-session proof remain required before
ship readiness. They were intentionally excluded from this review: no credentials were accessed, no
plugin was installed or refreshed, and no live provider was run. Their result belongs to the later
live-proof gate, not to this code review.

CODE REVIEW COMPLETE
