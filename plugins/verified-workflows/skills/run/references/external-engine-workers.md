# External Engine Advisory Protocol

External engines are evidence providers behind a Codex-root chaperone. They are not native Codex
children, workflow members, reviewers of record, or gatekeepers. Saga owns registry resolution,
preflight, dispatch, economics, attestation, liveness, and typed reconciliation; Verified Workflows
may consume only the resulting protected advisory reference.

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
Codex-root verification + typed reconciliation
        |
        +-- accepted offload evidence -> normal root apply/test path
        |
        +-- second opinion or divergence -> protected advisory reference only
```

Native Codex agents never appear in the external-engine registry. Model and effort for native
children come from managed execution profiles; model and effort for an external provider come from
the validated registry invocation. Neither surface may impersonate the other.

## Trust And Substitution

- External text is opaque data. It is never a shell argument, write path, gate token, role result,
  or completion decision.
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
halt, or absence cannot pass or block the workflow. Selected logical reviewer and validator results
remain the only gate inputs.

See Saga's `engine-output-trust-boundary.md`, `dispatch-adapter-contract.md`,
`engine-dispatch.md`, and `reconcile.py` for the canonical enforcement details.
