---
title: Workflow Feasibility Review Plan
type: fix
status: active
date: 2026-07-18
---

# Workflow Feasibility Review Plan

## Summary

Add a deterministic feasibility review to `verified-workflows` so the root Codex session can detect an unattainable child-attestation contract before it becomes an execution blocker. The root remains the workflow orchestrator; named child profiles remain useful bounded advisory workers, while a strict independent-child gate stays explicit opt-in.

## Problem Frame

The package correctly distinguishes requested child-profile configuration from host-observed runtime facts, but its planning guidance still recommends `verified-workflow` for high-risk work without first proving the runtime can satisfy the selected Workflow Structure. A plan can therefore require child receipts that the installed runtime cannot produce, even though the root could execute the same preferred-independence lenses inline with deterministic validators and root-owned mutation control.

## Requirements

- R1. Review a rendered `## Workflow Structure` against a bounded Codex capability snapshot without launching a child, changing runtime configuration, or treating a fixture as live proof.
- R2. Report each agent-lens row as root-inline gate-capable, advisory-child-only, or strict-child-unavailable, with a concrete correction for any unavailable contract.
- R3. Preserve the root as sole owner of scope, mutation, integration, Git, gates, and completion; child results never gain gate authority merely because a profile was selected.
- R4. Treat any selected `subagent` or `auto` vehicle as infeasible for a gate when the capability projection lacks host-issued child attestation; preferred-independence rows must be changed to `inline` for gate authority, and required-independence rows must remain blocked.
- R5. Make the review available as `verified-workflows:review-workflow` and require it before `verified-workflows:run` or `saga:plan` treats a verified-workflow plan as executable.
- R6. Keep ordinary native subagent use available. The feasibility reviewer may recommend advisory bounded children but must not convert their requested model or effort into observed facts.
- R7. Cover the capability matrix, command-line exit behavior, plan/run guidance, plugin inventory, and release metadata with focused automated tests.

## Key Technical Decisions

- KTD1. The root session is always the orchestrator. Workflow feasibility evaluates whether a plan's evidence contract can be met; it never substitutes, launches, or authorizes a child.
- KTD2. Reuse the existing closed Workflow Structure parser and `protocol_probe` capability vocabulary. The new analyzer composes those inputs into a workflow-level result instead of duplicating role, profile, or runtime-schema parsing.
- KTD3. The analyzer emits one closed result with `ready`, `requires-inline`, or `strict-unavailable` status. `ready` means every gate-authoritative lens is inline or deterministic; advisory children may still be recommended separately. `requires-inline` identifies preferred-independence subagent rows that must be made inline to meet a gate. `strict-unavailable` blocks required-independence rows until a runtime supplies host-issued child attestation.
- KTD4. A committed capability snapshot is bounded evidence of supported runtime shape, not proof that the current session selected a model, effort, sandbox, or child. The analyzer reads only its documented fields, preserves that limitation in its result, and fails closed on malformed or unsupported attestation claims without rejecting unrelated forward-compatible fields.
- KTD5. `saga:plan` recommends `inline` for root-owned high-risk work unless an explicitly selected strict workflow passes feasibility review. `verified-workflow` remains available for validated contracts; `manual` remains an operator handoff, not a delegation fallback.

## Implementation Units

### U1. Add the deterministic feasibility analyzer

Create one workflow-level analyzer that parses the exact plan table, validates the capability snapshot, evaluates each agent lens, and produces a closed JSON review with actionable row findings.

**Files:** `plugins/verified-workflows/scripts/workflow_feasibility.py`, `plugins/verified-workflows/scripts/protocol_probe.py`, `plugins/verified-workflows/tests/test_workflow_feasibility.py`, `plugins/verified-workflows/tests/test_protocol_probe.py`.

**Approach:** Compose `workflow_dispatch.parse_workflow_structure` with the existing snapshot reader and protocol vocabulary. Classify deterministic and root rows as ready, inline preferred-independence lenses as gate-capable with an explicit non-observation limitation, preferred `subagent`/`auto` rows as requiring an inline gate vehicle unless only advisory, and required-independence rows as strict-unavailable when no host-attestation capability is present. Expose a bounded CLI that accepts a plan and snapshot, returns sorted structured findings, and uses nonzero status only for contract correction or invalid input.

**Test scenarios:**

- An all-inline preferred-independence review plan returns `ready`, has no child claim, and preserves requested profile fields only.
- A preferred-independence `subagent` row returns `requires-inline` with the exact step ID and `inline` correction.
- A required-independence row returns `strict-unavailable` when the snapshot lacks host attestation.
- A deterministic validator and root step stay ready without model/effort fields.
- A malformed plan, malformed documented capability shape, or attempt to claim host attestation from an unsupported fixture fails closed.

### U2. Publish the workflow-review skill and explain the execution boundary

Expose the analyzer through a short skill that reviews a plan before execution and explains the resulting root-inline, advisory-child, or strict-unavailable contract.

**Files:** `plugins/verified-workflows/skills/review-workflow/SKILL.md`, `plugins/verified-workflows/README.md`, `plugins/verified-workflows/CHANGELOG.md`, `plugins/verified-workflows/.codex-plugin/plugin.json`, `scripts/validate_codex_plugins.py`, `tests/test_verified_workflows_migration.py`, `tests/test_validate_codex_plugins.py`.

**Approach:** Make `review-workflow` read-only and deterministic. It reports the plan revision, capability-snapshot digest, row-level feasibility, required amendment, and residual evidence limitation. Update package metadata and validation inventory as one release unit. Keep `select-agent` as the pre-spawn helper for ordinary delegation; this new skill reviews workflow authority, not ordinary subagent availability.

**Test scenarios:**

- Plugin inventory recognizes exactly the new skill and release version.
- The skill contract forbids spawning, configuration writes, and claims of observed child model or effort.
- Source validation continues to reject malformed manifests and stale package inventory.

### U3. Make planning and execution consume feasibility before a strict workflow claim

Require an explicit feasibility result at the verified-workflow boundary and correct the backend recommendation so root-owned work does not default to an impossible strict gate.

**Files:** `plugins/verified-workflows/skills/run/SKILL.md`, `plugins/saga/skills/plan/SKILL.md`, `plugins/verified-workflows/tests/test_workflow_feasibility.py`, `tests/test_saga_docs_package.py`, `tests/test_saga_doc_formatting.py`.

**Approach:** Put the feasibility review before any workflow intent, receipt, child dispatch, or execution claim. A `requires-inline` result directs the planner to render inline preferred-independence lenses and record `inline` orchestration; a `strict-unavailable` result blocks only the explicit strict contract and points to its needed host capability. Update backend guidance so risk alone does not choose `verified-workflow`; strict independently attestable execution must be both intended and feasible.

**Test scenarios:**

- Planning guidance recommends `inline` for high-risk root-owned work when no strict-attestation capability is present.
- Run guidance refuses to call an infeasible subagent gate verified and preserves advisory-child use as non-gating evidence.
- Existing Saga documentation-package and formatting checks remain green.

### U4. Record the operating decision and validate the release candidate

Capture the durable boundary decision, run focused and package-level validation, and retain a release-ready diff without touching installed cache copies.

**Files:** `docs/engineering-journal/DECISIONS.md`, `docs/validation/verified-workflows-legacy-token-inventory.json`, `scripts/build_legacy_workflow_inventory.py`, `docs/plans/2026-07-18-workflow-feasibility-review-plan.md`, `docs/reviews/2026-07-18-workflow-feasibility-review-plan-doc-review.md`.

**Approach:** Record that strict attestation is an opt-in authority level rather than the default workflow mode. Regenerate the sealed legacy-token inventory through its repository script after inspecting the decision diff, so the inventory records the intentional journal revision without rewriting historical content. Validate analyzer behavior, parser integration, documentation contracts, manifest inventory, and the repository validator before review and release preparation.

**Test scenarios:**

- The engineering decision names the root-owned fallback and the condition for revisiting it, and the legacy-token inventory check recognizes the deliberate decision revision.
- Focused analyzer and package-inventory tests pass with no installed-cache modification.

## Scope Boundaries

This change does not create or modify a host-issued Codex attestation mechanism, change model-provider access, launch or reconfigure real subagents, loosen severity or deterministic-validator gates, or alter the Olympus retirement source candidate. It only prevents new plans from misrepresenting an unsupported child-evidence contract.

## Risk Analysis And Mitigation

The main risk is silently downgrading a workflow that truly requires independent proof. The analyzer avoids that by returning `strict-unavailable` for required independence and by requiring an explicit plan amendment to root-inline for preferred lenses. A second risk is treating static capability material as session truth; the result labels it as configuration-level evidence and never claims observed execution attributes.
