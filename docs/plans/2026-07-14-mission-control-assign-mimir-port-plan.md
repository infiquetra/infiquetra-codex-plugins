# Mission Control assign-to-Mimir Codex port plan

Issue: `infiquetra/infiquetra-codex-plugins#23`

Status: implementation and local review complete; PR, merge, installed marketplace proof, and
outcome reconciliation remain.

## Frozen authority

- Canonical repository: `infiquetra/infiquetra-claude-plugins`
- Source base: `1457aed6ee2d3a58900bc4b069871609d2fd166a` (Mission Control 2.9.0)
- Source target: `9adb971020df9eb5928595760b5e9c75e498ef2c` (merged Mission Control 2.10.0 behavior)
- Codex execution base: `fc077d46a541e58d57fb420b0f63589b7fb8b600`
- Authority class: `AUTH-VENDORED`; the Claude implementation is canonical and the Codex copy adapts only host paths, manifest shape, and release metadata.

## Work

1. Refresh the sanitized Codex runtime capability snapshot and bootstrap a focused JSON port contract for the exact Mission Control source delta.
2. Classify the command, tests, skills, README, changelog, and manifest rows. Preserve Codex-owned mutation-preview, target-allowlist, `.codex` state, and manifest differences.
3. Port `flow assign-mimir` and every canonical fixture. Add explicit cross-repository parity assertions against the frozen Claude target.
4. Update Codex operator guidance, `PORTABILITY.md`, plugin version/changelog, target inventory, and generated docs.
5. Run focused tests, the full suite, both Codex plugin validation modes, generated documentation checks, review, PR, merge, marketplace upgrade, installed CLI negative/positive/idempotency proof, and fresh-thread pickup boundary.

## Port-contract note

`scripts/port_contract.py` exposes general `init` arguments but its current `validate` command is deliberately sealed to the older `external-advisory-execution-2026-07-11` contract constants. This cycle will still bootstrap through `init`; a focused repository test will bind the new manifest to its exact refs, inventories, classifications, target files, and evidence without weakening or replacing the sealed historical gate.

## Stop conditions

Stop on source-ref drift, an unclassified source row, any behavioral difference from frozen 2.10.0, loss of Codex mutation safeguards, validation drift, install/readback failure, or inability to restore the prior installed plugin exactly.
