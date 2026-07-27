# verified-workflows

Root-owned Codex V2 workflow orchestration for Infiquetra work.

The main Codex session is the sole orchestrator and Git owner. Codex V2 owns the live agent
hierarchy, liveness, messaging, waiting, interruption, and restoration. This plugin compiles an
operator-approved contract, validates runtime identity and typed results, audits writable attempts,
evaluates gates, and writes one concise run record.

Release candidate: `2.1.0+codex.20260727035515` is the explicit, root-orchestrated V2-only package. Historical Team
Execution names and earlier V1 or hook-based proof artifacts are lineage only; they are not active
execution paths.

## Skills

- `verified-workflows:run` executes an approved Workflow Contract.
- `verified-workflows:review-workflow` checks the contract before execution without launching work.
- `verified-workflows:select-agent` lists and launches one maintained native V2 profile outside a
  workflow gate.
- `verified-workflows:appsec-audit` performs a focused application trust-boundary review.

## Execution Shape

```text
approved Workflow Contract
          |
          v
main Codex session (orchestrator only)
          |
          +--> named Codex V2 assignments
          +--> fresh V2 independent-review roots
          |
          v
typed results + runtime readback + changed-path validation
          |
          v
dependency release or operator blocker
```

The operator sees and can edit the intended execution before launch. The canonical `## Workflow
Contract` contains three compact tables:

```text
Assignments:
id | depends | role | profile | model | effort | writes | completion | fallback

Blocking checks:
id | owner | after | command-or-proof | blocking | failure

External actions:
id | purpose | provider | model | egress | context | sensitivity | cost |
writes-or-artifact | requiredness | authority
```

Use `External actions: []` when no external action is approved. The compiler canonicalizes these
tables and binds their digest to the approved plan revision. A material graph, role, profile, model,
effort, context, write, fallback, check, external-action, or authority change requires a new preview
and approval.

## Managed V2 Profiles

Logical roles are separate from compute profiles. The role registry preserves 28 role lenses; the
workflow selects one of seven generated profiles:

| Profile | Model | Effort | Workspace intent | Purpose |
|---|---|---|---|---|
| `review_max` | `gpt-5.6-sol` | `max` | read-only | Exceptional-risk independent review |
| `review_high` | `gpt-5.6-sol` | `high` | read-only | Normal independent review |
| `work_medium` | `gpt-5.6-terra` | `medium` | declared write | Ordinary implementation, remediation, and Git integration |
| `work_high` | `gpt-5.6-sol` | `high` | declared write | Complex bounded implementation |
| `test_medium` | `gpt-5.6-terra` | `medium` | declared write | Ordinary testing and validation |
| `scan_low` | `gpt-5.6-terra` | `low` | read-only | Low-cost repository scanning |
| `monitor_low` | `gpt-5.6-terra` | `low` | read-only | Allowlisted external observation |

Ultra is root-only. Codex 0.145.0 children inherit the parent turn's effective permission profile;
profile sandbox fields express intent and cannot independently widen or narrow that permission.
Luna remains a V1-only child model in this runtime, so the V2-only low profiles use Terra/low.

Generate and verify the maintained source profiles:

```bash
python3 plugins/verified-workflows/scripts/render_codex_agents.py --check --pretty
python3 plugins/verified-workflows/scripts/sync_codex_agents.py --dry-run --pretty
```

The plugin `agents/` directory is canonical. Exact regular-file copies under `.codex/agents/`
provide project-scoped development discovery. Global synchronization is transactional: it validates
all profiles before writing, rejects unmanaged collisions and unsafe paths, journals prior bytes,
performs atomic replacements, and verifies readback. Real-profile apply or recovery requires
`--allow-real-profile`.

## Runtime And Result Proof

Requested launch fields, profile bytes, prompts, and child self-report do not prove execution. Before
a delegated attempt can count, the root validates combined Codex V2 `session_meta` and
`turn_context` for the canonical agent path, selected profile or agent type, model, effort, provider,
effective permission, sandbox, and V2 mode.

Each attempt returns one closed `assignment-result.v1` or `reviewer-result.v1` object. The root
validates it with `result_contract.py`; prose, mailbox messages, and terminal notices do not release
dependencies. Same-attempt continuation uses `followup_task` on the same path. Retry, remediation,
and revalidation use a fresh attempt ID and fresh canonical path.

Concurrent writable assignments must have disjoint write sets. Dependency-ordered assignments may
share paths. Returned changed paths must remain inside the assignment's approved write paths, and
only `git-integration-operator` may run Git commands.

At least one authority-bearing reviewer runs beneath a separately launched fresh V2 review root with
no implementation turns. The implementer and its descendants cannot review their own work.
Additional reviewers are selected only for concrete architecture, security, privacy, API,
infrastructure, or testing risk.

`gate_evaluator.py` reduces only validated typed results, deterministic checks, root-adopted
findings, and reviewer assurance. Missing required evidence, failed blocking checks, unresolved
actionable findings, or missing independence block. One remediation and one targeted recheck are
the maximum automatic convergence cycle.

## External Actions

Saga owns external provider selection, approval fingerprints, egress policy, execution, status, and
root adjudication. External providers receive only declared context in a contained workspace.
CLI routes are advisory and read-only, receive a minimal environment, and return an artifact.
Non-empty external write sets fail closed until an enforceable filesystem boundary exists.

External output is always `non-gating`. A finding affects the native gate only after independent root
verification and explicit adoption.

## Run Record

The root atomically replaces one bounded JSON record at
`~/.codex/verified-workflows/state/<repo>/workflow-runs/<run-id>.json`, or a verified git-ignored
project fallback. It stores the approval binding, validated runtime identity, typed outcomes,
checks, findings, remediation count, external-action projection, and root decision. It does not copy
raw V2 events, messages, transcripts, or model output.

## Validation

```bash
python3 plugins/verified-workflows/scripts/render_codex_agents.py --check --pretty
python3 plugins/verified-workflows/scripts/workflow_feasibility.py \
  --plan docs/plans/YYYY-MM-DD-topic-plan.md \
  --plan-revision <approved-revision> \
  --snapshot docs/validation/codex-runtime-capability-snapshot.json \
  --pretty
python3 scripts/prove_verified_workflows_runtime.py --pretty
python3 scripts/validate_codex_plugins.py
```

The tracked proof JSON records historical characterization and is not a substitute for fresh
installed-byte and runtime readback during release. See [PORTABILITY.md](PORTABILITY.md) for source
lineage and compatibility boundaries, and the [Saga family guide](../../docs/saga/README.md) for
the surrounding lifecycle.
