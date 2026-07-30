# Changelog - verified-workflows

All notable changes to this plugin are documented here.

## [3.0.0] - 2026-07-29

### Changed

- Reduce the Workflow Contract assignment table to role, profile, writes, completion, and fallback;
  model and effort now derive from the maintained profile.
- Use the native Codex 0.146 agent lifecycle and direct-sibling reviewers. The root dispatches every
  assignment through native `agent_type` and validates combined runtime readback.
- Make numeric review scores advisory. Gates block on required evidence, failed blocking checks,
  independence, and verified P0/P1 or explicit hard-stop findings.
- Add bounded deviation disposition (`planned`, `one-hop`, `defer`, `approval-required`) with one
  direct-cause fix and one targeted recheck before operator approval is required.
- Keep Luna fallback on Terra because the 0.146 catalog still reports Luna as V1.

### Removed

- Remove `verified-workflows:select-agent`, snapshot-driven feasibility gating, repository-local
  `.codex/agents` copies, sandbox fields from managed profiles, and automatic multi-round
  convergence.

## [2.1.0] - 2026-07-26

### Changed

- Make all Verified Workflow skills explicit-only and reduce root to dispatch, runtime-receipt
  verification, dependency release, approval boundaries, and reporting.
- Replace executable root rows with a nine-column assignment contract and require blocking checks
  to name an executable assignment owner.
- Add `work_medium` on Terra/medium plus `implementation-worker`, `remediation-worker`, and
  `git-integration-operator`.
- Enforce disjoint concurrent write sets, assignment-bounded changed paths, Git ownership by the Git
  operator, one remediation assignment, and one targeted recheck.

### Removed

- Remove the before-and-after workspace audit subsystem and its serialized-writer guidance.

## [2.0.0] - 2026-07-24

### Changed

- Replace the parallel intent, hook receipt, protected-record, workspace-evidence, and workflow-state
  machinery with a compact Codex V2 contract compiler, runtime probe, typed result validator,
  bounded workspace audit, severity-first gate, and one root-owned run record.
- Expand the managed profile set to six with `work_high`, preserve native catalog V2 metadata, and
  require matching `session_meta` plus `turn_context` readback before delegated work counts.
- Require one independent reviewer beneath a fresh V2 review root and add risk-triggered reviewers
  only when the work warrants them.
- Integrate approval-bound Saga external actions into the same contract and run record while keeping
  all provider output non-gating.

### Removed

- Remove executable V1 fallback, plugin hooks, protected evidence stores, receipt chains, and hidden
  inline downgrade paths from active workflow execution.

## [1.0.3] - 2026-07-18

### Added

- Add `review-workflow`, a deterministic preflight that distinguishes root-inline gate evidence,
  advisory child work, and an unavailable strict child-attestation contract.

### Changed

- Make root-inline the planning recommendation for root-owned high-risk work unless the operator
  explicitly selects and proves independently attestable child execution.

## [1.0.2] - 2026-07-18

### Fixed

- Keep outside-scope subject ancestry stable when an authorized missing file or directory is created
  on APFS by normalizing only the immediate subject-exclusion parent's directory link count.
- Preserve strict higher-ancestor, sibling, inode, hardlink, mode, symlink, ignored-file, and Git-control
  evidence while retaining readability of existing protected records.

## [1.0.1] - 2026-07-17

### Changed

- Use the temporary Fleet Core V1 catalog override for Sol and Terra instead of requiring the
  unfinished MultiAgent V2 namespace workaround.
- Add `select-agent` as the lightweight pre-spawn catalog for the five maintained profiles; keep
  `/agent` as the spawned-thread switcher.
- Keep Verified Workflow attestation and gates opt-in so ordinary native agent delegation remains
  usable.

## [1.0.0] - 2026-07-11

### Added

- Establish the active Verified Workflows Codex package identity.
- Add `run` and `appsec-audit` skill surfaces.
- Define the root-owned workflow DAG and compatibility boundaries.
- Preserve 25 logical jobs as versioned agent lenses with closed selection, independence,
  evidence-schema, and role-level boundary contracts.
- Render exactly five catalog-bound managed profiles and add live-catalog, persistent-lock profile
  sync with explicit isolated targets, stale cleanup, partitioned receipts, exact rollback, and
  preparing/prepared/applying/committed crash recovery.
- Bind all three frozen reviewer/validator registries, typed evidence schemas, shared scoring and
  gate semantics, default-branch eligibility, and deferred external advisory behavior.
- Add the closed Workflow Structure parser and deterministic ready/follow-up intent emitter; the
  root Codex thread remains the sole native spawn, steering, wait, mutation, and completion owner.
- Bind explicit role-kind and deterministic-command contract digests, require all base reviewers
  plus one required validator, and make identical explicit intent inputs content-addressed and
  idempotent.
- Add minimal prompt-free SubagentStart/SubagentStop capture; protected intent, trust, launch,
  result, mutation-audit, and root-verification records; retry-safe transactional normalization;
  truthful inline fallback; deterministic/root receipts; and bounded stale-raw pruning.
- Bind authorized subjects to a pre-existing Git baseline, exact path/content/mode deltas, and
  cross-attempt ancestry; add whole-workspace plus Git-control no-write audits for agents and
  deterministic tools.
- Bind installed-hook readback to a Verified Workflows path inside the declared Codex home, root
  evidence IDs to typed protected records, and deterministic execution to stream hashes/sizes plus
  typed output, cwd, timeout, and output ceilings. Raw command streams are never retained.
- Derive tester/scanner claims from protected command-output records, block required monitor/deploy
  evidence until an authenticated adapter exists, and reject broad permission modes.
- Bootstrap Sol/Terra MultiAgent V2 named-profile selection through an expanded non-reserved
  `agents` namespace; require `agent_type`, a non-full-history fork, and child runtime readback while
  retaining the full hook/profile/result join for Verified Workflows receipt authority.
- Make protected resolutions authorize only a later affected-role rerun, require finding and subject
  continuity across attempts, and require explicit abandonment before pruning incomplete raw starts.
- Add severity-first `pass`, `block`, and `escalate` gates that load exact protected evidence for
  every workflow step, derive validator/finding state, reject self-acceptance, and keep numeric
  scores advisory.
- Add a sanitized runtime proof harness and tracked current characterization. The configured named
  spawn surface yields `diagnostic` without embedded live evidence; separate fresh-task proof
  demonstrates selected profile/model/effort/sandbox, while isolated readback and U8 still own hook
  trust, installed-byte, cutover, and rollback authority.

### Migration

- Adapt behavior from the upstream `team-execution` lineage without claiming byte parity.
- Read exact legacy vocabulary through fleet-core and write only canonical Verified Workflows
  vocabulary.
- Retire Team Execution `2.3.0` after isolated install, migration, rollback, and fresh-session proof.
