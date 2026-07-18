# verified-workflows Portability Notes

## Source And Identity

- Upstream lineage: `team-execution` at frozen Claude commit
  `38742ece89880a6b140be237edad6d3f13c97b54`
- Prior Codex adapter: `team-execution` `2.3.0`
- Canonical Codex package: `verified-workflows` `1.0.3+codex.20260718134043`
- Current status: released and active with 25 role lenses, five generated profiles, a root-owned DAG
  interpreter, closed hook receipts, severity-first gates, and one marketplace workflow identity

This is a behavior adaptation, not an upstream byte-parity claim. The frozen path-by-path source
treatments and old-to-new targets are recorded in
`../../docs/portability/ports/2026-07-10-saga-07517.json`.

The checked-in directory is the only source template. `../../scripts/materialize_verified_workflows.py`
stages it byte-for-byte into an explicit isolated destination, rejects drift and managed Codex
paths, and is idempotent on a second call. It is not an installer or profile synchronizer.

## Codex-Native Shape

The Claude team runtime becomes a root-owned Codex workflow DAG. The root thread owns state,
barriers, mutation, integration, and final adjudication. Current Sol/Terra sessions use a generated
full-catalog override to select stable MultiAgent V1 until V2 is ready. Profile-selected work uses
`agent_type` plus a fresh child (`fork_context=false`, or a host wrapper's equivalent
`fork_turns=none`); task naming alone is never selection. Peer communication is not required.

Logical roles are independent of compute profiles. U3 preserves all 25 role behaviors as agent
lenses, records closed class transitions and role-level boundary caps, and renders exactly five
catalog-bound model/effort profiles. No current role qualifies as deterministic because every role
still needs judgment or result interpretation. `scripts/sync_codex_agents.py` proves isolated
installation, live-then-bundled catalog resolution, collision safety, explicit stale cleanup,
partitioned readback, exact rollback, and preparing/prepared/applying/committed recovery without
claiming runtime selection. Implicit `$CODEX_HOME` targets are real; isolated fixtures require an
explicit target plus sentinel.

U4F historically separated durable kebab-case execution classes from Codex-safe underscore runtime
agent names and published byte-identical project discovery copies under `.codex/agents/`. Official
Codex custom agent discovery can load the five profile definitions, while workflow rows and receipts
retain both identities. The first fresh CLI task used the default restricted V2 schema and proved that
`task_name=review_high` produced `agent_role=null` and inherited parent effort. Source inspection then
identified the required V2 bootstrap; a later fresh task with the saved configuration selected
`scan_low` and recorded `agent_role=scan_low`, Luna/low, and read-only. The original negative receipt
remains useful evidence that task naming is not profile selection, but no longer classifies the
configured runtime as inline-only.

U4 adapts the peer-team source behavior into a root-owned Codex workflow. The deterministic
dispatcher parses one closed Workflow Structure and emits intents only. The root persists the intent
before work and records an authorized subject plus pre-existing Git baseline. Later attempts must
descend from the prior result, use a fresh execution context, and bind the approved execution class;
status/clarification messages cannot create a retry or change class. Codex does not consume the
source's mutable session-tier file. Operator class changes begin a newly approved workflow run
instead of splicing into an existing receipt chain. The root can record content-addressed
installed-hook readback, launch, schema-valid result,
mutation-audit, and root-verification evidence. A named-child claim additionally requires the
minimal start/stop pair and exact role, lens, profile, model, and child bindings. The evidence is an
auditable root-accountability diagnostic, not same-user cryptographic or host-issued attestation,
so it always blocks the gate. Expected effort and configured sandbox intent come from the profile
digest; current hooks observe neither directly. Native V1 child activity proves role, model, and
effort, while effective permission remains a separate runtime fact.
Gate evaluation requires all base reviewers plus one
required validator, opens typed protected evidence, requires exact workflow step coverage and
dependency chronology, rejects self-acceptance, stays severity first, and caps remediation at three
cycles with escalation. Resolutions cannot remove a finding until a later affected-role receipt
consumes the changed descendant subject and revalidates it.

Agent and deterministic-tool runs use whole-repository before/after audits that include ignored
files, modes, empty directories, symlinks, and hashed Git control state. Deterministic commands also
bind argv, implementation/schema digests, cwd, timeout, output ceiling, exit status, and protected
stream hashes/sizes plus typed deterministic output; raw stdout/stderr are never retained. Tester
and scanner claims derive from protected command-output records. Required monitor/deploy evidence
waits for an authenticated observation adapter. Root evidence is an
evidence-ID-to-protected-record map; digest-shaped text is never accepted as evidence. Raw pruning
requires an unchanged dry-run plan, explicit abandonment for an incomplete start, and entry/byte
ceilings inside each leaf.

The tracked U4 proof is a sanitized non-mutating historical characterization. It records `diagnostic` because
the configured snapshot exposes named selection but the committed artifact intentionally carries no
live child transcript or receipt. Root-owned fresh-task evidence separately proves the selector,
child model/effort, and parent-inherited effective permission boundary needed to start U5. It does
not itself prove installation, trust, or candidate receipt-chain gate authority. A separate isolated
envelope proves installed-byte equality; the completed U8 cutover published the package, installed it
into the real profile, trusted hooks, and recorded the complete cutover receipt and rollback proof.

The three frozen upstream selection/gate registries are exact test fixtures, not active legacy
instructions. Their hashes bind the closed Codex-native selection policy, typed evidence schemas,
default-branch automation restriction, custom-reviewer contract, and explicit U7 advisory deferral.
Upstream advisory-seat/convergence and external worker-manifest changes remain assigned to U7;
Saga fallback/quorum emitter changes remain assigned to U6; release metadata remains U8. U4 claims
only the source session-tier row and adapts it to immutable approved-row/intent binding.

## Compatibility Boundary

`plugins/fleet-core/scripts/fleet_commons/workflow_compat.py` is the closed registry for plugin and
skill names, Saga mode, plan heading and anchor, state/config locations, receipt vehicles, producer
kind, evidence key, managed marker, and Git snapshot prefix. Consumers load it through their own byte-identical
fleet-core shim. Readers may accept the exact old aliases; serializers always write canonical
Verified Workflows values.

Historical plans, reviews, ticks, changelogs, Claude catalog rows, and frozen classification rows
retain their original Team Execution vocabulary. The completed U8 transaction removed the old package
from the active marketplace while preserving its exact legacy vocabulary and readable state roots.

The exact temporary and historical token inventory is generated by
`../../scripts/build_legacy_workflow_inventory.py` and bound at
`../../docs/validation/verified-workflows-legacy-token-inventory.json`. It records exact paths,
classifications, token sets, and SHA-256 digests so a new legacy writer or global history rewrite
fails validation.
