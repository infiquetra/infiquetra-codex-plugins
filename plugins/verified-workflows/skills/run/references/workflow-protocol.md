# Workflow Protocol

`## Workflow Structure` is a machine-checked Markdown table. The exact columns are:

```text
step_id | depends_on | barrier | role_id | role_kind | independence | execution_class |
runtime_agent_name | vehicle | mutation | required_evidence | role_lens_sha256 | profile_sha256 |
expected_model | expected_effort | validator_required | validator_disabled |
deterministic_contract_sha256
```

Use `-` for an empty cell and comma-separated identifiers for dependencies and evidence. The
separator row must use at least three hyphens per column.

Agent-lens rows bind `role_kind=agent-lens`, the current role lens, the exact underscore-form Codex
runtime agent name, and generated profile digests.
Root rows use `role_id` and `role_kind` `root`, vehicle `root`, independence `n/a`, `n/a` for both
validator-policy cells, and `-` for class, runtime agent, lens, profile, model, effort, and deterministic contract.
Deterministic-validator rows bind `role_kind=deterministic-validator`, vehicle
`deterministic-tool`, independence `n/a`, mutation `none`, no model fields, and the digest of the
complete pinned command/schema contract. Validator rows set exactly one explicit required policy
and may be disabled only when non-required. Reviewer and root rows use `n/a`.

Select every base reviewer until a protected, machine-verifiable skip-review decision exists.
Once selected, a reviewer must return at least one applicable scored dimension; dimension-level
`static-non-applicable` exclusions remain valid. Prompt text or root assertion cannot omit a base
reviewer.

Example shape:

```text
map + implement (root) -----> review-high (security) --+
          |                                             |
          +---------------> test-medium (tests) --------+--> root integrate
                                      barrier: verify
```

Every dependency must name a step, the graph must be acyclic, and a downstream step that depends
on one member of a barrier cohort must depend on every member. The dispatcher emits only:

- `run`: all dependencies passed;
- `follow-up`: an affected role needs another bounded cycle;
- `blocked`: a dependency failed or blocked;
- `escalation`: the three-cycle remediation cap was reached.

The dispatcher does not launch anything. Its CLI requires an explicit agents directory: installed
Codex profile bytes for production, committed source bytes only for fixtures. Every emitted intent
includes `run`, `follow-up`, or `revalidate`, its attempt, the exact predecessor receipt when one
exists, and the prior finding IDs for follow-up. The root persists that intent before execution.
A later intent subject must descend from the prior result subject. Every retry uses a new intent and
fresh execution context. Follow-up messages may report status or clarify the current attempt but
cannot create another attempt, alter its bindings, or supply gate evidence. A named-profile request
is enforceable only when the native surface selects and reports it; otherwise preferred work falls
back inline and required independence blocks.

Model and effort are requested by the approved execution-class row, mapped runtime agent name, and
exact installed profile digest. They become observed runtime facts only after Codex reports the named
selection and child turn context. Sol/Terra MultiAgent V2 must expose spawn metadata through a
non-reserved namespace; dispatch uses `agent_type` and a non-full-history `fork_turns`, normally
`none`. Current V2 reapplies the live parent permission profile after role selection, so each child
runs beneath a permission-homogeneous parent and host-issued rollout context proves the effective
boundary. Missing or mismatched runtime proof degrades preferred work inline and blocks required
independence. An ambient Claude-style session tier file cannot change an
emitted Codex intent or an in-flight remediation chain. To change class, close or abandon the
current chain and approve a new workflow run; receipts and findings from different workflow digests
cannot be spliced together.

Peer or root-to-child messages can improve status visibility inside one attempt but never form a
dependency, barrier, evidence record, retry, or completion requirement.

Before the first intent, the root records an authorized subject plus its pre-existing Git baseline.
Subject revisions inherit that baseline, bind exact Git entries and modes, and reject deltas outside
the authorized paths. Every executed agent or deterministic tool also receives a repository-wide
before/after workspace audit that includes ignored files, file modes, empty directories, symlinks,
and hashed Git control state. Do not run another workspace or Git writer between those snapshots.

Canonical gate-authoritative state and receipt roots are under the plugin-provided writable data
directory outside the repository workspace. Repo-local `.codex/verified-workflows/` is a read-only
legacy migration input only: excluding an active root from the no-write audit would let a child
alter evidence invisibly. Mixed active roots halt.

## External Advisory Boundary

An external engine is not a workflow worker. Saga owns provider resolution, economics, dispatch,
attestation, liveness, and typed reconciliation. Verified Workflows may consume only a protected
structural advisory record whose `seat_type` is `external-second-opinion` and whose
`gate_authority` is `none`. The record may report convergence, Codex-only, external-only, and
conflicting finding keys plus a rendered-report digest. It cannot satisfy a role, contribute a
score, change severity, satisfy a validator, pass a barrier, or block completion.

See [external-engine-workers.md](external-engine-workers.md) for the provider sequence and persisted
lineage names.
