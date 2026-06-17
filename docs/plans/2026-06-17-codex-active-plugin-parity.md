# Codex Active-Plugin Parity Update

## Summary

Port the recent Claude active-plugin updates into this Codex plugin repo, adjusted for Codex packaging and execution boundaries.

Scope is active parity for `saga` and `mission-control` only. Do not do a full catalog audit, do not add GitHub Actions, and do not port Claude-only commands, agents, `.claude-plugin`, or Workflow backend behavior.

Source truth:

- Board topology and issue-contract generated data come from `infiquetra-sdlc`.
- Codex packaging and validation truth live in `.codex-plugin` manifests, Codex skill docs, scripts, and pytest.

## Key Decisions

- Active boards are `jeff-intent`, `asgard`, and `campps`; Mount Olympus is retired historical context only.
- `objective` remains a non-actionable issue type and milestone/objective concept, but `objective.yml` is no longer an active generated template.
- Vendor `issue_contract_data.py`, `issue_contract_data.py.sha256`, and `issue_contract_shim.py` from the SDLC generated output. Compute and pin `issue_contract_shim.py.sha256` in this repo.
- Saga still exposes only `inline` and `team-execution`. `adversarial_confidence` and broad fanout map to `team-execution` in Codex; `cc-workflows-ultracode` stays unreachable.
- Add validator and pytest parity checks. Do not add `.github/workflows/ci.yml`.

## Implementation Units

### U1. Persist Topology And Contract Artifacts

Copy current `infiquetra-sdlc` topology and generated issue-contract artifacts into Mission Control. Add local hash parity checks for the vendored generated modules without running the SDLC generator from this repo.

### U2. Update Mission Control Runtime

Load generated issue-contract modules by file path, enforce the expanded card contract, add prepared-issue approval state, support repeatable `board add --project`, and switch active project choices to `campps`, `asgard`, and `jeff-intent`.

### U3. Update Mission Control Docs, Proof, And Tests

Replace active Mount Olympus guidance with CAMPPS or Asgard as appropriate. Keep objective as a non-actionable issue type while removing `objective.yml` from generated template docs. Adapt tests to Codex skill, script, manifest, README, and generated-doc surfaces.

### U4. Update Saga Backend Recommendation

Add `has_code_surface` and `adversarial_confidence` inputs. Keep Codex reachable backends to `inline` and `team-execution`; never offer `cc-workflows-ultracode` as executable.

### U5. Update Release And Validation Metadata

Bump Saga to `0.22.1` and Mission Control to `2.1.0` across manifests, README, target inventory, validator expectations, changelogs, generated Saga facts, and durable notes.

## Test Plan

Run:

```bash
python3 scripts/validate_codex_plugins.py
```

```bash
PYTHONPATH=. python3 -m pytest \
  plugins/mission-control/tests/test_issue_contract_parity.py \
  plugins/mission-control/tests/test_card_validator.py \
  plugins/mission-control/tests/test_template_sync.py \
  plugins/mission-control/tests/test_issue_prepare.py \
  plugins/mission-control/tests/test_issue_prepare_compile_approve.py \
  plugins/mission-control/tests/test_issue_create_prepared.py \
  plugins/mission-control/tests/test_board_add_multi_project.py \
  plugins/mission-control/tests/test_project_mappings_resolution.py \
  plugins/mission-control/tests/test_prompt_alignment.py \
  tests/test_prove_codex_plugin_profile.py \
  -q
```

```bash
PYTHONPATH=. python3 -m pytest \
  plugins/saga/tests/test_lifecycle_state.py \
  plugins/saga/tests/test_codex_operator_choice.py \
  tests/test_validate_codex_plugins.py \
  tests/test_saga_docs_package.py \
  -q
```

```bash
PYTHONPATH=. python3 -m pytest -q
```
