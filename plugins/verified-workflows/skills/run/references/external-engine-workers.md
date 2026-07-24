# External Engine Advisory Protocol

External engines are evidence providers behind a Codex-root chaperone. They are not native Codex
children, workflow members, reviewers of record, or gatekeepers. Saga owns registry resolution,
preflight, dispatch, economics, attestation, liveness, and typed reconciliation. Verified Workflows
projects only the resulting non-gating status and artifact digests into its concise run record.

## Root-Owned Sequence

```text
offer or recommendation (read-only)
        |
        v
pre-dispatch economics and spend authority
        |
        v
registry resolve + auth preflight + context-fit check
        |
        v
generic CLI/HTTP bridge dispatch + receipt + liveness
        |
        v
read-only advisory artifact
        |
        v
Codex-root verification + typed reconciliation
        |
        +-- implementation guidance -> root-owned apply/test path
        |
        +-- second opinion or divergence -> Saga action reference only
```

Native Codex agents never appear in the external-engine registry. Model and effort for native
children come from managed execution profiles; model and effort for an external provider come from
the validated registry invocation. Neither surface may impersonate the other.

## Trust And Substitution

- External text is opaque data. It is never a shell argument, write path, gate token, role result,
  or completion decision.
- A workflow external-action row enters Saga's immutable request and approval fingerprint. Its
  authority is always `non-gating`; requiredness may pause dispatch sequencing but cannot satisfy a
  workflow check or reviewer gate.
- CLI routes are advisory and read-only. They receive a scoped Git workspace containing only
  declared context, a minimal environment, and no undeclared source history. Non-empty external
  write sets fail closed until an enforceable filesystem boundary exists.
- HTTP routes execute only the canonical registry invocation. The executable URL host is checked
  against the workflow egress allowlist, and caller input cannot replace the endpoint, model, or
  authentication environment.
- Every successful bridge receipt binds engine, variant, transport, model, effort, the complete
  secret-free invocation, output attestation, and non-negative finite telemetry.
- A capability-routed result that differs from the operator-approved preview is
  `substituted-engine` and cannot satisfy a gate.
- Persisted v1 enum member `FELL_BACK_TO_CLAUDE` and value `fell-back-to-claude` remain unchanged for
  schema compatibility. On the Codex host their operator label is "fell back to Codex root."
- Persisted v1 field `verified_by_claude` remains unchanged. It means a Codex-root verification was
  recorded; the spelling is lineage, not current host identity.

## Economics And Recommendation

Recommendation, offer, and promotion commands are read-only. A metered route must have complete
cost inputs and pass the pre-dispatch economics decision before any provider call. Free routes still
require trust, context, receipt, liveness, and reconciliation checks. Spend increases remain an
operator decision.

Provider onboarding is dry-run by default. `--apply` additionally requires a contained regular
registry target, an exact expected pre-write SHA-256, atomic replacement, and post-write readback.
It stores registry metadata and an environment-variable name only, never a credential or probe body.

## Typed Reconciliation

Saga's three closed intents are `offload`, `second-opinion`, and `divergence`. Ordered source
finding IDs and evidence digest must be covered exactly by one bounded typed reconciliation result.
The Codex root is the adjudicator. Raw provider or panel text is not written to the run-fact ledger.

The external advisory panel cap is seven. Every member must pass preflight before dispatch. Identical
content at the same ordinal may deduplicate while preserving producer identities; separate ordinals
remain separately accountable. Per-member output is capped at 64 KiB and cumulative output at
256 KiB before root adjudication.

## Verified Workflows Boundary

`consensus_advisory.py` may compare selected Codex findings with external findings for an operator
report. `advisory_reconcile.py` emits only bounded structural keys plus a rendered-report digest.
The gate accepts the advisory seat only with `gate_authority="none"`; participation, score, failure,
halt, or absence cannot pass or block the workflow. An external finding enters gate evaluation only
after the root independently verifies and adopts it as an ordinary root-owned typed finding.
Selected logical reviewer and validator results remain the other gate inputs.

See Saga's `engine-output-trust-boundary.md`, `dispatch-adapter-contract.md`,
`engine-dispatch.md`, and `reconcile.py` for the canonical enforcement details.
