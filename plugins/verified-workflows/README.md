# verified-workflows

Root-owned Codex V2 workflow orchestration for Infiquetra work.

The main Codex session is the sole orchestrator of the approved graph and the adjudicator of its
evidence. Codex V2 owns the live agent hierarchy, liveness, messaging, waiting, interruption, and
restoration. This plugin compiles an operator-approved contract, validates runtime identity and
typed results, audits writable attempts, evaluates gates, and writes one concise run record.

Release candidate: `3.0.0+codex.20260729164721` is the explicit, root-orchestrated V2-only package. Historical Team
Execution names and earlier V1 or hook-based proof artifacts are lineage only; they are not active
execution paths.

## Skills

- `verified-workflows:run` executes an approved Workflow Contract.
- `verified-workflows:review-workflow` checks the contract before execution without launching work.
- `verified-workflows:appsec-audit` performs a focused application trust-boundary review.

Direct, non-workflow delegation uses Codex's native `agent_type` field.

## Execution Shape

```text
approved Workflow Contract
          |
          v
main Codex session (orchestrator only)
          |
          +--> named Codex V2 assignments
          +--> direct-sibling independent reviewers
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
id | depends | role | profile | writes | completion | fallback

Blocking checks:
id | owner | after | command-or-proof | blocking | failure

External actions:
id | purpose | provider | model | egress | context | sensitivity | cost |
writes-or-artifact | requiredness | authority
```

Use `External actions: []` when no external action is approved. The compiler canonicalizes these
tables and binds their digest to the approved plan revision. Model and effort derive from the
maintained profile. A material graph, role, profile, context, write, fallback, check,
external-action, or authority change requires a new preview and approval.

## Managed V2 Profiles

Logical roles are separate from compute profiles. The role registry preserves 29 role lenses; the
workflow selects one of seven generated profiles:

| Profile | Model | Effort | Contract write intent | Purpose |
|---|---|---|---|---|
| `review_max` | `gpt-5.6-sol` | `max` | read-only | Exceptional-risk independent review |
| `review_high` | `gpt-5.6-sol` | `high` | read-only | Normal independent review |
| `work_medium` | `gpt-5.6-terra` | `medium` | declared write | Ordinary implementation, remediation, and Git integration |
| `work_high` | `gpt-5.6-sol` | `high` | declared write | Complex bounded implementation |
| `test_medium` | `gpt-5.6-terra` | `medium` | declared write | Ordinary testing and validation |
| `scan_low` | `gpt-5.6-terra` | `low` | read-only | Low-cost repository scanning |
| `monitor_low` | `gpt-5.6-terra` | `low` | read-only | Allowlisted external observation |

Ultra is root-only. The write-intent column states what the approved contract expects an assignment
to do. It is not a sandbox control. Codex 0.146.0 children inherit the parent turn's effective
permission profile. A generated profile carries a model, an effort, and instruction text, and no key
that could constrain a filesystem or a network. Scope comes from the operator-approved plan and
contract; runtime readback reports the permission that actually applied. Luna remains V1 in the
0.146 catalog, so the V2-only low profiles use Terra/low.

Generate and verify the maintained source profiles:

```bash
python3 plugins/verified-workflows/scripts/render_codex_agents.py --check --pretty
python3 plugins/verified-workflows/scripts/sync_codex_agents.py --dry-run --pretty
```

The plugin `agents/` directory is canonical. Repository-local `.codex/agents/` overrides are not
maintained. Isolated synchronization remains available for source canaries; any current-user profile
apply is a separate operator-approved release action.

## Runtime And Result Proof

Requested launch fields, profile bytes, prompts, and child self-report do not prove execution. Before
a delegated attempt can count, the root validates combined Codex V2 `session_meta` and
`turn_context` for the canonical agent path, selected profile or agent type, model, effort, provider,
effective permission, sandbox, and V2 mode.

Each attempt returns one closed `assignment-result.v1` or `reviewer-result.v1` object. The root
validates it with `result_contract.py`; prose, mailbox messages, and terminal notices do not release
dependencies. Same-attempt continuation uses `followup_task` on the same path. Retry, remediation,
and revalidation use a fresh attempt ID and fresh canonical path.

Concurrent writable assignments must have disjoint write sets; the compiler rejects an overlap.
Dependency-ordered assignments may share paths. A returned changed path outside the assignment's
approved write paths does not discard the result. The validator records one `P2` `one-hop` finding
for it, and more than one unplanned `one-hop` finding in a run is a hard stop for operator approval.

At least one authority-bearing reviewer runs as a direct sibling of the implementation assignment
with no implementation turns. The implementer and its descendants cannot review their own work.
Additional reviewers are selected only for concrete architecture, security, privacy, API,
infrastructure, or testing risk.

`gate_evaluator.py` reduces only validated typed results, deterministic checks, root-adopted
findings, and reviewer assurance. Missing required evidence, failed blocking checks, verified P0/P1
hard stops, or missing independence block. Scores are advisory. One remediation and one targeted
recheck are the maximum automatic convergence cycle.

Every finding declares `scope_disposition` as `planned`, `one-hop`, `defer`, or
`approval-required`. One direct-cause, in-allowlist deviation may receive one fix and targeted
recheck. A second issue, broader causal layer, failed recheck, or new surface stops for operator
approval. Nonblocking adjacent hardening is reported and deferred.

## External Actions

Saga owns six exact external provider routes, egress policy, execution, and result validation.
External providers receive only declared context in a disposable remote-stripped workspace.
Direct-mode CLI routes are read-only and return an artifact. A Verified Workflow may authorize
writes inside the disposable clone; only the Git integration operator can import the resulting patch.

External output is always `non-gating`. A finding affects the native gate only after independent root
verification and explicit adoption.

## Run Record

The root atomically replaces one bounded JSON record at
`~/.codex/verified-workflows/state/<repo>/workflow-runs/<run-id>.json`, or a verified git-ignored
project fallback. It stores the approval binding, validated runtime identity, typed outcomes,
checks, findings, deviation use, remediation count, external-action projection, and root decision.
It does not copy raw V2 events, messages, transcripts, or model output.

## Validation

```bash
python3 plugins/verified-workflows/scripts/render_codex_agents.py --check --pretty
python3 scripts/prove_verified_workflows_runtime.py --pretty
python3 scripts/validate_codex_plugins.py
```

The tracked proof JSON records historical characterization and is not a substitute for fresh
installed-byte and runtime readback during release. See [PORTABILITY.md](PORTABILITY.md) for source
lineage and compatibility boundaries, and the [Saga family guide](../../docs/saga/README.md) for
the surrounding lifecycle.
