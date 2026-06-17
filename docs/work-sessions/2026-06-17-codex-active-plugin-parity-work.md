---
title: Codex Active-Plugin Parity Work Session
type: work-session
status: complete
date: 2026-06-17
plan: docs/plans/2026-06-17-codex-active-plugin-parity.md
branch: codex/active-plugin-parity
---

# Codex Active-Plugin Parity Work Session

## Summary

Implemented the approved active-plugin parity plan for `mission-control` and `saga`.

The update ports current active topology and issue-contract behavior from the Infiquetra source repos
while preserving Codex packaging boundaries: no Claude command directories, no agents, no
`.claude-plugin` manifests, no GitHub Actions workflow, and no executable source workflow backend.

## Completed Units

| Unit | Result |
|---|---|
| U1 | Vendored current SDLC schema, project mappings, issue-contract data, shim, and hash sidecars. |
| U2 | Updated Mission Control runtime for CAMPPS routing, generated contract validation, prepared draft approval, and repeatable board project targeting. |
| U3 | Updated Mission Control docs, proof flow, generated template reference, and tests for CAMPPS/Asgard active routing. |
| U4 | Updated Saga backend recommendation for `has_code_surface` and `adversarial_confidence` while keeping only `inline` and `team-execution` reachable. |
| U5 | Bumped Saga to `0.22.1`, Mission Control to `2.1.0`, refreshed target inventory, generated Saga facts/assets, changelogs, and validation checks. |

## Verification

| Check | Result |
|---|---|
| `python3 plugins/mission-control/config/generated/check_issue_contract_parity.py` | pass |
| `python3 scripts/validate_codex_plugins.py` | pass |
| `python3 scripts/validate_codex_plugins.py --mode target-fixture` | pass |
| `python3 scripts/validate_codex_plugins.py --mode cutover` | pass |
| `python3 scripts/build_saga_docs_facts.py --check` | pass |
| `python3 scripts/render_saga_docs_assets.py --check` | pass |
| `PYTHONPATH=. python3 -m pytest plugins/mission-control/tests -q` | 158 passed |
| `PYTHONPATH=. python3 -m pytest tests/test_prove_codex_plugin_profile.py tests/test_validate_codex_plugins.py tests/test_saga_docs_package.py -q` | 22 passed |
| `PYTHONPATH=. python3 -m pytest plugins/saga/tests/test_lifecycle_state.py plugins/saga/tests/test_codex_operator_choice.py -q` | 8 passed |
| `git diff --check` | pass |
| `PYTHONPATH=. python3 -m pytest -q` | 258 passed |
| `ruff check .` | fails on pre-existing out-of-scope lint in `test_typed_exceptions.py`, `team-execution/scripts/protocol_probe.py`, and generated-doc helper import patterns |

## Residual Notes

- Mount Olympus remains in vendored config and runtime compatibility branches as retired historical context only.
- `objective` remains a non-actionable coordination type; `objective.yml` is not in the active generated template set.
- The implementation was committed locally on `codex/active-plugin-parity`; it has not been pushed
  or PR'd in this work session.
