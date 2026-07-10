# verified-workflows

Codex-native, root-owned workflow orchestration for Infiquetra work.

> Development status: `1.0.0` is an unpublished target package. The active marketplace continues
> to expose `team-execution` `2.3.0` until the U8 transactional cutover and runtime proof pass.

## Skills

- `verified-workflows:run` owns approved workflow DAG execution.
- `verified-workflows:appsec-audit` performs focused application trust-boundary review.

## Codex Execution Shape

```text
                         +--> role or reviewer child --+
approved Workflow DAG --> root thread                  +--> evidence --> root gate
                         +--> deterministic validator -+

root owns: state, scope, mutation, barriers, consolidation, Git, final decision
child owns: one bounded task and its attributable result
```

Logical role instructions are separate from model and effort profiles. Planning selects a role
and an execution class; fleet-core resolves the class against one immutable Codex model-catalog
snapshot. A Verified Workflow result can claim a model only after runtime attestation, and it can
claim effort only from the exact installed profile digest because Codex hooks do not report effort.

## U3 Role And Profile Contract

All 25 preserved jobs are versioned agent lenses. None is currently a deterministic validator:
each scanner, tester, monitor, and reviewer still requires judgment or result interpretation.

```text
25 logical role lenses
        |
        +--> reviewer ------> review-high --explicit risk--> review-max
        +--> tester --------> test-medium --interpretation--> review-high
        +--> scanner -------> scan-low ----interpretation--> test-medium
        +--> monitor -------> monitor-low -interpretation--> test-medium
                                      |
                            immutable catalog resolution
                                      |
                       exactly five managed Codex profiles
```

The committed profiles are expected configuration, not evidence that Codex selected a profile or
used its model, effort, sandbox, or independent child. U4 owns that attestation boundary.

Validate the deterministic source bundle:

```bash
python3 plugins/verified-workflows/scripts/render_codex_agents.py --check --pretty
python3 plugins/verified-workflows/scripts/sync_codex_agents.py --dry-run --pretty
```

The synchronizer defaults to dry-run and reads `codex debug models` once, with the bounded bundled
fallback owned by fleet-core. Tests and CI inject the committed catalog snapshot explicitly. An
implicit `$CODEX_HOME` is always treated as a real profile; isolated proof requires both an explicit
`--target-dir` and `--isolated-target`.

Apply validates all five profiles before writing, refuses unmanaged collisions and unsafe
filesystem entries, uses one persistent lock inode, journals prior managed bytes, performs atomic
per-file replacements, and verifies exact readback. A preparing, prepared, or applying journal is
restored with `--recover`; a committed cleanup failure never triggers rollback. Stale profiles are
preserved unless `--remove-stale` is given. Legacy ownership requires `--migrate-legacy`. Both forms
of destructive cleanup require the exact pre-state digest. Real-profile apply or recovery also
requires `--allow-real-profile` and remains reserved for U8.

Example isolated fixture proof:

```bash
mkdir -p /tmp/verified-workflows-codex
python3 plugins/verified-workflows/scripts/sync_codex_agents.py \
  --target-dir /tmp/verified-workflows-codex/agents \
  --isolated-target \
  --catalog-snapshot docs/validation/codex-runtime-capability-snapshot.json \
  --dry-run --pretty
```

## Compatibility

Fleet-core's `workflow_compat.py` is the only old-to-new vocabulary registry. Readers accept exact
Team Execution aliases and label them legacy. New serializers emit only Verified Workflows names.
Neither Saga nor this plugin imports the other plugin's source.

The legacy package remains byte-stable and solely marketplace-active during development. Do not
install both packages or create a compatibility plugin stub.

## Isolated Source Materialization

The checked-in package is the source template. Materialize it only into an isolated staging path:

```bash
python3 scripts/materialize_verified_workflows.py --destination /tmp/verified-workflows-stage --pretty
```

The command refuses Codex profile/cache destinations, symlinks, extra paths, byte drift, and mode
drift. Repeating it against an unchanged stage is a verified no-op; it never installs the plugin or
mutates profile state.

## Delivery Sequence

- U9: package identity and compatibility vocabulary
- U3: logical roles and the five managed execution profiles (complete in source; not installed)
- U4: dispatch, hook receipts, gates, and fresh runtime proof
- U8: atomic marketplace/install cutover and rollback proof

See [PORTABILITY.md](PORTABILITY.md) for the source mapping and
[`docs/portability/claude-to-codex-plugin-port-runbook.md`](../../docs/portability/claude-to-codex-plugin-port-runbook.md)
for future Claude-to-Codex ports. The current lifecycle context is in the
[Saga family guide](../../docs/saga/README.md).
