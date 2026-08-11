---
title: Issue 61 Claude Adapter Boundaries Work Session
type: work-session
status: complete
date: 2026-08-10
plan: docs/plans/2026-08-10-issue-61-claude-adapter-boundaries-plan.md
review: docs/reviews/2026-08-10-issue-61-claude-adapter-boundaries-doc-review.md
branch: fix/issue-61-claude-adapter-boundaries
---

# Issue 61 Claude Adapter Boundaries Work Session

## Summary

Implemented the three reviewed units for GitHub issue #61. The shipped Claude registry recipe now
matches its configured effort, the one-shot adapter fails closed before launch for invalid effort or
missing `USER`, and the maintained contract describes the requested-versus-observed receipt boundary
and the Claude-only identity input.

## Completed Units

| Unit | Result |
|---|---|
| U1 | Added the Claude recipe effort and registry checks for blank, duplicated, or mismatched recipe values while preserving recipes without an effort flag. |
| U2 | Added the five-value Claude effort preflight, one `--effort` argument pair, Claude-only non-blank `USER`, pre-launch unavailable results, receipt assertions, and negative non-Claude coverage. |
| U3 | Updated the dispatch adapter contract. The reviewed baseline already contained the matching engineering-journal decision, so it did not require another edit. |

## Independent Code-Review Repairs

The follow-up review produced three narrow findings. Receipt binding now requires exactly one
two-token `--effort <configured value>` pair in the recorded process command arguments while retaining
the invocation-digest check. Registry validation now tokenizes every recipe before deciding whether an
effort flag exists, including quoted flag forms. The launch test now exercises all five supported
Claude effort values from the adapter's maintained constant.

## Verification

| Check | Result |
|---|---|
| Red-first focused registry and adapter tests | expected failure: 20 passed, 15 failed before implementation |
| Initial implementation focused registry and adapter tests | 35 passed |
| Code-review repair red-first focused tests | expected failure: 39 passed, 9 failed before repair |
| `python3 -m pytest plugins/saga/tests/test_external_action_adapters.py plugins/saga/tests/test_engine_routing.py tests/test_external_action_adapters.py tests/test_engine_registry_lint.py -q` | 48 passed |
| `python3 -m ruff check` on the six changed Python files | pass |
| `git diff --check` | pass |
| `python3 scripts/validate_codex_plugins.py` | pass |
| `.venv/bin/python -m pytest -q` | 2716 passed, 18 warnings |

The first full-suite attempt with `/opt/homebrew/bin/python3` stopped during collection because that
interpreter lacked the declared Pillow dependency. `uv` created the ignored project `.venv` from the
existing lockfile, and the complete suite then passed there without a dependency or lockfile change.

## Pending Live Proof

The installed-plugin fresh-session proof remains assigned to a later independent live-test session.
This implementation has not refreshed the marketplace or edited an installed cache snapshot.

## Attended Source-Level Live Proof (2026-08-11)

The reviewed source branch completed the Claude Command Line Interface (CLI) smoke through
`plugins/saga/scripts/external_action_adapters.py`; no installed plugin cache was used. The existing
non-blank `USER` and macOS Keychain-backed session were used without login, logout, credential
changes, Keychain unlocks, account inspection, or retained provider output, receipt, or process
environment data.

| Check | Sanitized result |
|---|---|
| Bounded direct request | `claude-cli/opus`, `mode=direct`, empty context and write sets, and the registry-configured `high` effort completed with the requested recognizable marker. |
| Launch and receipt proof | The result was available; the redacted receipt contained exactly one two-token `--effort high` pair, and both the selected-invocation digest and output attestation validated. |
| Child-environment boundary | The Claude child retained `USER`; temporary unrelated secret-name sentinels (`AWS_SESSION_TOKEN`, `ANTHROPIC_API_KEY`, and `ISSUE61_UNRELATED_SECRET`) were absent. |
| No-write containment | The bounded result had no changed paths, patch reference, or patch digest. |
| Missing-identity and non-Claude corroboration | `python3 -m pytest -q plugins/saga/tests/test_external_action_adapters.py::test_cli_child_environment_drops_root_secret_variables plugins/saga/tests/test_external_action_adapters.py::test_non_claude_cli_launch_omits_user 'tests/test_external_action_adapters.py::test_claude_missing_user_is_unavailable_before_runner[None]' 'tests/test_external_action_adapters.py::test_claude_missing_user_is_unavailable_before_runner[]' 'tests/test_external_action_adapters.py::test_claude_missing_user_is_unavailable_before_runner[   ]'` passed: 5 tests. No live non-Claude provider was called. |
| Focused regression suite | `python3 -m pytest -q plugins/saga/tests/test_external_action_adapters.py plugins/saga/tests/test_engine_routing.py tests/test_external_action_adapters.py tests/test_engine_registry_lint.py` passed: 48 tests. |

## Next Step

The attended source-level gate is complete. The installed-plugin fresh-session proof remains a
separate, unrun authorization boundary.
