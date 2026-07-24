# verified-workflows Portability Notes

## Source And Identity

- Frozen Claude lineage: `team-execution` at `38742ece89880a6b140be237edad6d3f13c97b54`
- Prior Codex adapter: `team-execution` `2.3.0`
- Canonical Codex package: `verified-workflows`
- Active architecture: root-owned Codex V2 workflow execution with 25 role lenses and six managed
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

The main Codex session owns the approved DAG, dependency release, integration, Git, gates, and final
adjudication. Codex V2 owns the live hierarchy, agent paths, liveness, messages, waits, interruption,
and restoration. The plugin does not maintain a parallel scheduler or task-state tree.

The operator-approved Workflow Contract contains only assignments, blocking checks, and external
actions. Its compiler emits deterministic launch specifications and one digest bound to the plan
revision. Native launches select an exact underscore-form profile and bounded `fork_turns` context.
Requested values remain provisional until `session_meta` and `turn_context` agree on the canonical
path, profile, model, effort, provider, effective permission, sandbox, and V2 mode.

The six profiles are `review_max`, `review_high`, `work_high`, `test_medium`, `scan_low`, and
`monitor_low`. They are generated from the role registry and the Fleet Core projection of the native
Codex model catalog. Fleet Core preserves each model's `multi_agent_version`; it does not rewrite V2
models into another mode. Profile sandbox configuration expresses intent because Codex 0.145.0
children inherit the parent turn's effective permission.

Each attempt returns one closed typed result. Writable attempts are bounded by declared paths and a
before-and-after workspace audit. At least one reviewer runs beneath an independent fresh V2 review
root with no implementation history. The root reduces typed results, deterministic checks, adopted
findings, and reviewer assurance into one gate decision and one concise run record.

Saga remains the authority for external provider approval, egress, execution, status, and
adjudication. Response-only output stays an artifact. Write-capable output is imported only as a
validated bounded patch by the root. External output remains non-gating unless the root independently
verifies and adopts a finding.

## Removed Active Machinery

The V2 cutover removes the executable V1 catalog override, plugin hooks, protected-record stores,
intent and receipt writers, named-child attestation joins, raw-hook maintenance, old workflow-record
chains, and full workspace-evidence chains. No active compatibility alias may recreate those writers
or silently fall back from V2.

Historical requirements, plans, reviews, classifications, proof JSON, changelog entries, and frozen
fixtures retain their original vocabulary as non-current evidence. They do not authorize a new run
or establish current runtime truth.

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
