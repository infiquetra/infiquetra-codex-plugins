# Mission Control board move fail-loud Codex port plan

Date: 2026-07-16
Issue: `infiquetra/infiquetra-codex-plugins#35`
Parent onboarding: `infiquetra/team-mimir#108`
Risk: medium
Port runbook: `docs/portability/claude-to-codex-plugin-port-runbook.md` v3

## Goal

Port the released Claude Mission Control 2.10.1 `board move` fail-loud behavior
into the Codex adapter as 2.4.2, while preserving Codex package, confirmation,
path, marketplace, and installed-session boundaries.

## Frozen inputs

- Canonical source repository: `infiquetra/infiquetra-claude-plugins`.
- Last imported source behavior: Mission Control 2.10.0 commit
  `9adb971020df9eb5928595760b5e9c75e498ef2c`.
- Source behavior target:
  `5d4dfb2e1d0be5abbe9f3a693e33d152ba7cfcba`.
- Source merged-main proof:
  `a6f3bcff0fe9df213e2d2947afca99d5e7516393`.
- Codex execution base and observed `origin/main`:
  `7b429f765eea2afca3bba63b5c498dc8efb219ff`.
- Current Codex Mission Control: 2.4.1; target: 2.4.2.
- The five commits after the earlier #108 discovery base add only tracked
  issue-template YAML and do not overlap this write set.

## Requirements

R1. Initialize a new v3 port manifest from the exact refs above. Inventory only
the source release rows for root marketplace metadata, plugin manifest,
changelog, `sdlc_manager.py`, the new fail-loud fixture, and prompt/version
guard. Classify every row before behavior edits.

R2. Treat executable behavior and fixtures as `codex-adapt`; recreate manifest
and changelog metadata for the independent 2.4.x lineage. The Claude root
marketplace version row is `reject` for direct copy because the native Codex
marketplace deliberately has no per-entry version.

R3. Make `board_move()` return aggregate success while continuing through all
selected projects. Missing item, missing Status field, unavailable Status
option, or mutation failure makes the aggregate false after every project
result is reported.

R4. The CLI exits 1 iff the aggregate is false. A valid move exits 0. An
unavailable option lists provider-read choices and makes no mutation call.

R5. Adapt all six canonical success/failure cases to Codex imports and paths:
success, unavailable option/no mutation, missing item and Status field,
mutation failure, later-project continuation, and CLI nonzero propagation.

R6. Update only the Codex Mission Control manifest, changelog, portability
record, generated target inventory/facts, port classification, unit evidence,
plan/review, and code review required by the release. Do not add Actions,
branch protection, remote credentials, or a duplicated marketplace version.

R7. Pass source verification and the cycle-specific classification, unit, and
cutover contract tests; focused Mission Control tests; full locked Codex tests;
Ruff; current and target-fixture validators; generated Saga facts/assets; and
diff checks. The shared `port_contract.py validate` command remains bound to the
repository's active external-advisory contract and is not valid for this
concurrent focused port.

R8. Merge only the exact reviewed head. On VM 209, install Codex and set
`CODEX_HOME` inside `/home/agent/.hermes/canaries/team-mimir-108`, install and
enable Mission Control 2.4.2 from merged main, prove installed-source hashes,
invalid-Status nonzero behavior and no mutation, then start a fresh process or
session and prove plugin discovery.

R9. Rollback restores 2.4.1 inside the isolated home or removes the isolated
root. Cleanup must leave no canary path, host-global Codex/npm package, copied
credential, or mutation to the user's existing Codex configuration/cache.

## Implementation units

### U1. Port contract and classification

Capture a sanitized capability snapshot, initialize the exact source/Codex
contract, bind this plan and review, classify every source row, render the
classification, and pass
`tests/test_mission_control_board_move_port_contract.py` before behavior
changes.

### U2. Behavior and fixtures

Adapt the aggregate return and CLI exit behavior plus the six focused fixtures.
Preserve all Codex-native imports, config paths, confirmation rules, and
unrelated Mission Control behavior.

### U3. Release surfaces and evidence

Update 2.4.2 manifest, changelog, portability, validation inventory/facts, unit
evidence, manifest row states, and generated classification. Keep the root
Codex marketplace structurally unchanged.

### U4. Quality and review

Run the focused, full, port, repository, generated-doc, Ruff, and diff gates.
Write the code review, finalize cutover evidence, retain the evidence ref if
required, and open the exact-head PR.

### U5. Merge, isolated install, and rollback

Confirm the target still has zero provider checks, merge the reviewed head,
install on VM 209 under the canary root, prove installed and fresh-session
behavior, rollback, clean up, and attach receipts to #35 and #108.

## Verification

```bash
python3 scripts/port_contract.py verify-source --manifest <manifest> --source-repo <source>
PYTHONPATH=. uv run pytest -q tests/test_mission_control_board_move_port_contract.py -k classification
PYTHONPATH=. uv run pytest -q plugins/mission-control/tests
PYTHONPATH=. uv run pytest -q
uv run ruff check .
python3 scripts/validate_codex_plugins.py --mode current
python3 scripts/validate_codex_plugins.py --mode target-fixture
python3 scripts/build_saga_docs_facts.py --check
python3 scripts/render_saga_docs_assets.py --check
git diff --check
PYTHONPATH=. uv run pytest -q tests/test_mission_control_board_move_port_contract.py
```

## Stop conditions

- Stop on unreachable or changed source refs, execution-base drift, missing or
  unexpected inventory rows, dirty overlap, or failed classification.
- Stop if the adapter changes credentials, confirmation, target allowlist,
  state paths, marketplace schema, or behavior outside `board move`.
- Stop on version, generated-fact, full-suite, installed-hash,
  fresh-session, no-mutation, rollback, or cleanup conflict.

## Scope boundary

In scope: one canonical behavior delta, six adapted fixtures, Mission Control
2.4.2, one v3 port contract, and one isolated VM 209 install/rollback proof.

Out of scope: Codex issues #20, #33, and #34; unrelated Claude changes; global
Codex mutation; GitHub policy creation; and any valid board Status mutation.
