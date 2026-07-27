---
title: Make Codex ports and acceptance capability-first
repo: infiquetra-codex-plugins
type: capability
team: asgard
project: operations
status: Shaping
labels: capability, hermes-task, needs-plan
risk: medium
handoff_maturity: requirements-ready
approval_state: approved
---

# Make Codex ports and acceptance capability-first

### Objective

`improve-codex-plugins` — prove the promised Codex capability and actual diff instead of relying on manifest coverage or theoretical parity.

### Intent

Keep the mandatory Claude-to-Codex runbook and classification gate, but reconcile every port manifest with the actual behavior-bearing branch diff before source-derived mutation. Every uncovered path must be classified as source-derived, Codex-local, intentionally divergent, deferred, or blocked.

Accept a port or defect slice using its named operator path, touched runtime surfaces, before-and-after observations, and focused checks. Keep full-repository validation separately visible and distinguish changed-path failures from unchanged repository debt without suppressing either result.

Reuse issue #54 and enhancement #57 as independently verifiable children.

### Out-of-scope / non-goals

- A new port control plane, semantic compiler, compatibility database, or evidence-chain format.
- Byte-for-byte Claude mirroring or automatic semantic classification.
- A checked-in suppression baseline for repository failures.
- Hiding a nonzero full-repository result because focused checks pass.
- Requiring an exhaustive provider, model, effort, role, and platform matrix for every capability.

### Files expected to change

- `scripts/port_contract.py`
- `scripts/validate_codex_plugins.py`
- `docs/portability/claude-to-codex-plugin-port-runbook.md`
- `docs/portability/ports/`
- `tests/test_port_contract.py`
- `tests/test_codex_627_seam_refreeze_port_contract.py`
- `tests/test_lease_registry_forward_compat_port_contract.py`
- `tests/test_validation_attribution.py`

### Tests to add or update

- Diff-to-manifest reconciliation fixtures covering omitted production paths, repository-local paths, renames, deletions, and intentional divergence.
- Cross-repository evidence resolution without weakening traversal or undeclared-repository guards.
- Capability-slice acceptance fixtures naming the operator path, touched surfaces, proof limits, and focused checks.
- Validation attribution fixtures separating changed and unchanged paths while retaining the true command exit result.
- Regression coverage for unknown-field forward compatibility at active cross-runtime boundaries.

### Context library links

- `docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md`
- `docs/portability/claude-to-codex-plugin-port-runbook.md`
- `docs/engineering-journal/LEARNINGS.md`
- https://github.com/infiquetra/infiquetra-context-library/blob/main/docs/ai-context/context-audit-standard.md
- https://github.com/infiquetra/infiquetra-context-library/blob/main/docs/ai-context/instruction-surfaces.md

### Inputs inventory

- Issue #54 and PR #60 cover lease-registry unknown-field forward compatibility.
- Issue #57 covers an existing port contract that cannot name its cross-repository acceptance harness.
- The July 26 journal records that contract pathspecs can omit changed production files.
- Full-repository validation can currently report unrelated historical defects without identifying their relationship to the current diff.

### Failure modes / pre-mortem

- Treating path coverage as proof that behavioral classification is correct.
- Expanding the manifest schema when the existing classification vocabulary is sufficient.
- Weakening traversal or repository-declaration guards to make cross-repository evidence pass.
- Suppressing unchanged failures instead of reporting their real status.
- Replacing capability-focused acceptance with a smaller but still theoretical matrix.

### Stop conditions

- Stop before source-derived mutation when any behavior-bearing changed path is unclassified.
- Stop if cross-repository evidence requires implicit directory traversal or an undeclared repository.
- Stop if validation attribution changes the underlying command's exit status or hides unchanged failures.
- Stop if the proposed mechanism creates a second port manifest or acceptance authority.

### Acceptance criteria

- [ ] `python3 -m pytest tests/test_port_contract.py -q` passes a regression where an uncovered behavior-bearing diff path blocks classification until explicitly categorized.
- [ ] `python3 scripts/port_contract.py validate --stage classification` exits 0 only when the active manifest covers or classifies every behavior-bearing path in its actual diff.
- [ ] `python3 -m pytest tests/test_codex_627_seam_refreeze_port_contract.py tests/test_lease_registry_forward_compat_port_contract.py -q` passes cross-repository evidence, traversal safety, and unknown-field forward-compatibility cases.
- [ ] `python3 -m pytest tests/test_validation_attribution.py -q` reports changed-path and unchanged-path failures separately while preserving the underlying nonzero result.
- [ ] `python3 scripts/validate_codex_plugins.py` exits 0 with the runbook, manifests, inventories, and active plugin surfaces aligned.
- [ ] `python3 -m pytest -q` exits 0 after the focused proofs pass.

### Verification

```bash
python3 -m pytest \
  tests/test_port_contract.py \
  tests/test_codex_627_seam_refreeze_port_contract.py \
  tests/test_lease_registry_forward_compat_port_contract.py \
  tests/test_validation_attribution.py \
  -q
python3 scripts/port_contract.py validate --stage classification
python3 scripts/validate_codex_plugins.py
python3 -m pytest -q
```

### Handoff maturity

requirements-ready

### Suggested next action

Use `saga:plan <issue>` to sequence diff reconciliation, acceptance attribution, and the two existing child issues.

### Source context

- Source: `docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md`
- Existing children: #54, #57

## Created Issue

- URL: https://github.com/infiquetra/infiquetra-codex-plugins/issues/63
- Number: 63
- Created at: 2026-07-27T00:31:30.877561+00:00
