# Verified Workflows V2 Bootstrap Correction

## Goal

Correct the false U4F conclusion that current Codex cannot select named child profiles, enable the
runtime configuration required by Sol/Terra MultiAgent V2, and release U5-U8 without weakening the
reviewed five-profile design.

## Result

- Kept the five reviewed profiles: `review_high`, `review_max`, `test_medium`, `scan_low`, and
  `monitor_low`. The 25 logical roles remain lenses mapped onto those profiles; product-source
  implementation remains root-owned.
- Enabled expanded V2 spawn metadata under the non-reserved `agents` namespace in repository and
  user Codex configuration.
- Proved from a fresh saved-config task that a Sol/xhigh parent dispatching `scan_low` with
  `fork_turns=none` produced a Luna/low, read-only child with `agent_role=scan_low`. Later source and
  rollout inspection established that read-only came from the read-only parent: current V2
  reapplies parent permission after role selection. Permission-homogeneous parent tasks are required.
- Corrected the runtime snapshot, runbook v3, Saga operator-choice guidance, Verified Workflows
  protocol, proof classifications, port contract, tests, and engineering journal.
- Preserved the distinction between runtime profile selection and gate-authoritative workflow
  evidence: U8 must still join the planned role/lens, installed profile digest, hook events, child
  context, result, and root verification.

## Checks

- Profile renderer: five profiles and 25 role/lens mappings current.
- Focused runtime, contract, Saga, and validation checks: 114 passed.
- Full repository suite: 1,710 passed.
- Scoped Ruff, repository validator, classification contract, generated classification, legacy
  inventory, and `git diff --check`: passed.

## Handoff

Start U5 from a fresh Codex task so the configured `agents` namespace is present in the task's tool
schema. Dispatch profile-selected children with `agent_type` and `fork_turns=none`, verify the first
child runtime context, and continue through U5-U8 using the approved Workflow Structure in the plan.
