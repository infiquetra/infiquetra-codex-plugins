# verified-workflows

Codex-native, root-owned workflow orchestration for Infiquetra work.

> Release status: `1.0.3+codex.20260718134043` is the active workflow package. Historical Team Execution vocabulary is
> read-only compatibility data; the retired package is not co-installed.

## Skills

- `verified-workflows:run` owns approved workflow DAG execution.
- `verified-workflows:review-workflow` checks whether a Workflow Structure can satisfy its selected evidence contract before execution.
- `verified-workflows:appsec-audit` performs focused application trust-boundary review.
- `verified-workflows:select-agent` displays and launches one maintained native Codex agent profile.

## Codex Execution Shape

```text
                         +--> inline role/reviewer ------+
approved Workflow DAG --> root thread                   +--> evidence --> root gate
                         +--> deterministic validator ---+
                         +--> advisory named child -------+  (strict receipt only with host attestation)

root owns: state, scope, mutation, barriers, consolidation, Git, final decision
child owns: one bounded task and its attributable result
```

Run `review-workflow` before selecting a strict child-evidence workflow. It distinguishes root-inline
gate evidence from advisory child work and blocks only an explicit required-independence contract that
the available runtime cannot attest. Ordinary use of `select-agent` remains available outside a
Verified Workflow gate.

Logical role instructions are separate from model and effort profiles. Planning selects a role
and an execution class; fleet-core resolves the class against one immutable Codex model-catalog
snapshot. The exact installed profile digest proves requested configuration only. A Verified
Workflow result can claim an observed model only after host/runtime attestation, and current Codex
hooks do not report effort.

Execution-class IDs use kebab case because they are durable workflow vocabulary. Codex runtime
agent names use underscores because the native agent selector accepts only lowercase letters,
digits, and underscores:

```text
execution class    runtime agent
review-high    --> review_high
review-max     --> review_max
test-medium    --> test_medium
scan-low       --> scan_low
monitor-low    --> monitor_low
```

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

The plugin profiles are the maintained source. Exact regular-file copies under `.codex/agents/`
provide project-scoped Codex discovery during development; repository validation rejects missing,
extra, symlinked, or byte-drifted copies. U8 later installs the same five profiles globally. Profile
presence is expected configuration, not evidence that Codex selected one or used its model, effort,
sandbox, or independent child. U4 provides the receipt boundary for a runtime that can select named
profiles. Codex currently assigns Sol and Terra to unfinished MultiAgent V2 through the model
catalog, even when the V2 feature flag is false. Restore the stable V1 selector with:

```bash
python3 plugins/fleet-core/scripts/codex_v1_catalog.py install
```

The generator preserves the complete live catalog, changes only Sol and Terra to V1, and configures
`multi_agent=true` with `multi_agent_v2=false`. Restart Codex and open a fresh session after install.
Use `verified-workflows:select-agent` for the pre-spawn catalog, then `/agent` to switch among spawned
threads. Stable V1 profile selection uses `agent_type=<runtime_agent_name>` with a fresh child
(`fork_context=false`; some host wrappers spell the equivalent as `fork_turns=none`). Verify the
host-issued child role, model, and effort rather than child self-report. The profile sandbox remains
configured intent and the effective child permission boundary must still be verified separately.
Ultra automatic delegation is unverified under the V1 override.

Validate the deterministic source bundle:

```bash
python3 plugins/verified-workflows/scripts/render_codex_agents.py --check --pretty
python3 plugins/verified-workflows/scripts/sync_codex_agents.py --dry-run --pretty
```

After an intentional `render_codex_agents.py --write`, refresh the development discovery copies
before validation:

```bash
cp plugins/verified-workflows/agents/*.toml .codex/agents/
python3 scripts/validate_codex_plugins.py
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

## U4 Workflow And Receipt Contract

The `run` skill makes the root Codex thread the workflow engine. The supporting scripts validate an
approved `## Workflow Structure`, emit ready or follow-up intents, normalize evidence, and evaluate
gates. They never launch Codex, call collaboration controls, or claim that a helper-created process
is a native child.

```text
approved DAG -> typed intent -> root dispatch or truthful inline work
                                  |
                                  +-> hook start/stop + root result -> normalized receipt
                                                                    |
required evidence + severity + validator status + root verification -> pass|block|escalate
```

The exact Workflow Structure has 18 columns, including `role_kind`, `runtime_agent_name`, the
deterministic contract digest, and explicit `validator_required` and `validator_disabled` policy. Production requires all
base reviewers plus at least one required validator until a protected skip-review selector exists.
Each emitted `run`, `follow-up`, or `revalidate` intent binds its complete row, protected subject,
attempt, predecessor, and finding IDs. The approved execution class and installed profile digest
request model and effort; they do not prove runtime selection. An ambient session-tier override
cannot change a persisted intent or follow-up. Changing class closes the current receipt chain and
starts a newly approved workflow run.

Before work, the root records authorized paths and the pre-existing Git baseline. Subject revisions
inherit that baseline and exact Git/content/mode bindings. Agent and deterministic-tool runs also
use repository-wide before/after snapshots covering ignored files, empty directories, modes,
symlinks, and hashed Git control state. These audit intervals require a quiescent workspace.

The plugin hook accepts only `SubagentStart` and `SubagentStop` for the five underscore-form runtime
agent names.
It discards prompts, transcript paths, results, tool arguments, environment, and credentials; raw
receipt paths use hashed runtime identifiers and private local permissions. A normalized subagent
receipt requires content-addressed pre-launch intent, root-observed installed-hook readback from a
Verified Workflows path contained in the declared Codex home, native launch,
matching start/stop, schema-valid result, mutation-audit, and root-verification records. It binds the
role lens, exact profile digest, hook-reported model, and child identity. Profile bytes bind expected
effort and configured sandbox, but the hook observes neither effective effort nor sandbox.

The record chain is root-accountability evidence. Codex hook events are not signed, so it is not
cryptographic proof against another process running under the same operating-system user. Because
Codex does not provide host-issued child attestation, candidate subagent receipts are diagnostic and
always block the gate; the current gate-capable vehicle is truthful inline execution. Gate inputs
cannot substitute digest-shaped strings: root evidence maps declared IDs to typed protected
records, tester/scanner claims derive from protected command-output records, and the evaluator opens
every receipt and requires one receipt for every workflow step. Command records retain hashes and
sizes plus typed deterministic projections, never raw streams. Prepared and committed consumption
markers make normalization retryable. Start-only cleanup requires explicit protected abandonment;
prune traversal is bounded inside every leaf and remains dry-run first.

Gate policy is severity first. Missing required evidence, missing required independence, unresolved
P0/P1 or security hard stops, failed required validators, or missing root verification blocks.
Numeric scores are advisory until represented by typed findings, and the third unresolved
remediation cycle escalates instead of passing. A resolution authorizes a changed descendant subject
for the next affected-role run; it cannot suppress the current finding before revalidation. The gate
rejects its own implementation paths. Required monitor/deploy evidence remains blocked until an
authenticated observation adapter exists; non-required observations can warn only.

Reproduce the non-mutating runtime characterization and repository checks:

```bash
python3 scripts/prove_verified_workflows_runtime.py --pretty
python3 scripts/validate_codex_plugins.py
```

The tracked proof is deliberately a historical V2 dry-run characterization, not current
fresh-session release proof. It records the prior spawn request fields plus source hook, profile,
registry, and capability-snapshot hashes without reading the default Codex authentication file,
installing the unpublished package, trusting hooks, or claiming a live child receipt. Optional live mode consumes
an isolated installed-byte readback envelope. That envelope proves only that isolated installed
bytes match source; hook trust and task execution remain unobserved. The harness never launches a
nested Codex process.

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
- U3: logical roles and the five managed execution profiles (complete in source; project-discoverable,
  not globally installed)
- U4: dispatch, hook receipts, gates, and sanitized runtime characterization (complete in source;
  tracked non-live outcome `diagnostic`)
- U4F: historical V2 bootstrap evidence retained for the original port; current native agent use
  applies the Fleet Core V1 catalog override until V2 is ready
- U8: atomic marketplace/install cutover and rollback proof

See [PORTABILITY.md](PORTABILITY.md) for the source mapping and
[`docs/portability/claude-to-codex-plugin-port-runbook.md`](../../docs/portability/claude-to-codex-plugin-port-runbook.md)
for future Claude-to-Codex ports. The current lifecycle context is in the
[Saga family guide](../../docs/saga/README.md).
