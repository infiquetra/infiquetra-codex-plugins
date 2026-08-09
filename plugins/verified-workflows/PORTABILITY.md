# verified-workflows Portability Notes

## Source And Identity

- Frozen Claude lineage: `team-execution` at `38742ece89880a6b140be237edad6d3f13c97b54`
- Prior Codex adapter: `team-execution` `2.3.0`
- Canonical Codex package: `verified-workflows`
- Active architecture: root-orchestrated Codex V2 workflow execution with 29 role lenses and seven managed
  profiles

This is a behavior adaptation, not an upstream byte-parity claim. The frozen path classifications
and prior targets are recorded in
`../../docs/portability/ports/2026-07-10-saga-07517.json`. The current V2 migration contract and
source authority are recorded in
`../../docs/portability/ports/2026-07-24-codex-v2-orchestration.json`.

The checked-in plugin is the maintained source template. `../../scripts/materialize_verified_workflows.py`
can copy it byte-for-byte into an explicit isolated staging directory while rejecting unsafe
destinations, extra paths, and byte or mode drift. It is not an installer or profile synchronizer.

## Codex-Native V2 Shape

The main Codex session owns only the approved DAG, dependency release, approval boundaries, and final
reporting. Every executable action, including implementation, checks, remediation, review, Git, and
integration, belongs to an approved assignment. Codex V2 owns the live hierarchy, agent paths,
liveness, messages, waits, interruption, and restoration.

The operator-approved Workflow Contract contains only assignments, blocking checks, and external
actions. Its compiler emits deterministic launch specifications and one digest bound to the plan
revision. Native launches select an exact underscore-form profile and bounded `fork_turns` context.
Requested values remain provisional until `session_meta` and `turn_context` agree on the canonical
path, profile, model, effort, provider, effective permission, sandbox, and V2 mode.

The seven profiles are `review_max`, `review_high`, `work_medium`, `work_high`, `test_medium`,
`scan_low`, and `monitor_low`. They are generated from the role registry and the Fleet Core
projection of the native Codex model catalog. Fleet Core preserves each model's
`multi_agent_version`; it does not rewrite V2 models into another mode. Minimal profile TOMLs
contain model, effort, description, and instructions; Codex 0.146.0 inherits effective permission
from the parent turn.

Each attempt returns one closed typed result. Writable attempts declare their paths, concurrent
writers must be disjoint, and returned changed paths must remain within the assignment. At least one
reviewer runs as an independent direct sibling with no implementation history. One
remediation assignment and one targeted recheck are the maximum automatic convergence cycle.

Saga remains the authority for the six retained external routes, egress, execution, and result
validation. Direct CLI routes are advisory and read-only. An approved Verified Workflow may produce
a patch inside a disposable remote-stripped clone; only the Git operator can import it. Output stays
non-gating unless the root independently verifies and adopts a finding.

## Removed Active Machinery

The V2 cutover removes the executable V1 catalog override, plugin hooks, protected-record stores,
intent and receipt writers, named-child attestation joins, raw-hook maintenance, old workflow-record
chains, full workspace-evidence chains, the `select-agent` wrapper, snapshot feasibility gating, and
repository-local agent-profile copies. No active compatibility alias may recreate those writers or
silently fall back from V2.

Historical requirements, plans, reviews, classifications, proof JSON, changelog entries, and frozen
fixtures retain their original vocabulary as non-current evidence. They do not authorize a new run
or establish current runtime truth.

## Developer-Instruction Contract

Codex 0.147.0 added `features.multi_agent_v2.subagent_developer_instructions`. Unset, a spawned child
inherits the parent turn's developer instructions; set blank, it starts with none; either way a
role-specific instruction rendered into the child's profile wins.

This plugin leaves the setting unset and carries per-role text in every managed profile, so child
behavior is a property of the profile rather than of ambient configuration. A port that adopts these
profiles inherits that requirement: the setting must stay absent from every Codex configuration
surface the port ships, and each managed profile must carry non-empty `developer_instructions`.
`validate_developer_instruction_contract` in `scripts/validate_codex_plugins.py` enforces both, and
fails when a `config.toml` exists that is not registered in `CODEX_CONFIG_SURFACES` — the contract
binds the whole surface set, not one named file.

## Compatibility Boundary

`plugins/fleet-core/scripts/fleet_commons/workflow_compat.py` is the closed reader registry for old
plugin, skill, Saga-mode, plan-heading, state-location, evidence, and marker names. Readers may accept
those exact aliases and label them historical. New serializers emit only canonical Verified
Workflows vocabulary.

The generated inventory at
`../../docs/validation/verified-workflows-legacy-token-inventory.json` binds every allowed historical
or parser-compatibility occurrence to its path, classification, token set, and SHA-256 digest. A new
legacy writer or unclassified occurrence fails repository validation.

Historical proof JSON is deliberately not fresh-session release proof. Current release authority
requires isolated installed-byte readback plus the complete Codex V2 behavior matrix defined by the
approved plan.
