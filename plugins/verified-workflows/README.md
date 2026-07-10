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
and an execution class; fleet-core resolves the class against the live Codex model catalog. A
Verified Workflow result can claim a model only after runtime attestation, and it can claim effort
only from the exact installed profile digest because Codex hooks do not report effort.

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
- U3: logical roles and the five managed execution profiles
- U4: dispatch, hook receipts, gates, and fresh runtime proof
- U8: atomic marketplace/install cutover and rollback proof

See [PORTABILITY.md](PORTABILITY.md) for the source mapping and
[`docs/portability/claude-to-codex-plugin-port-runbook.md`](../../docs/portability/claude-to-codex-plugin-port-runbook.md)
for future Claude-to-Codex ports. The current lifecycle context is in the
[Saga family guide](../../docs/saga/README.md).
