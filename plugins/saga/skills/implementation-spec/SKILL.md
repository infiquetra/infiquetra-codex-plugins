---
name: implementation-spec
description: Author profile-backed, builder-ready implementation specs for Infiquetra context libraries. Detects or asks for the target *-context-library, uses that library's own authoring standard, and routes buildability-style review through saga:doc-review when the profile defines exact inputs and pass criteria.
argument-hint: "[context-library path | service/module path | topic]"
---

# Implementation Spec

Use this when the deliverable is a multi-document implementation specification in an Infiquetra
`*-context-library`, not a repo-local WHAT spec.

This is a profile-driven authoring harness. It is not limited to one product, but it must use the target
library's own standard. If no governing standard exists, stop and ask the operator for the standard
instead of inventing one.

## Target Resolution

Resolve the target in this order:

1. Explicit path or library named in `$ARGUMENTS`.
2. Current repo, when it is a `*-context-library`.
3. Nearby sibling `*-context-library` repos.
4. Operator selection when multiple plausible targets remain.

Use the helper to inspect candidates:

```bash
python3 plugins/saga/scripts/implementation_spec_audit.py discover --start .
```

Known profile detection:

| Standard path | Profile | Status |
|---|---|---|
| `platform-specs/06-service-implementations/README.md` | service implementation | fully supported when the standard contains the required markers |
| `platform-specs/06-feature-modules/README.md` | feature module | supported only when the target library defines a full authoring standard |

## Workflow

1. Read the detected authoring standard first.
2. Produce a research brief before authoring:
   - settled decisions with sources;
   - entity, endpoint, module, or workflow inventories implied by the requirements;
   - cross-spec obligations from already-shipped specs;
   - divergences from in-flight repos or current docs;
   - open questions with recommended answers and the cost of deciding wrong.
3. Ask the operator to resolve product forks before authoring.
4. Author in dependency-aware waves:
   - foundation contracts first;
   - dependent workflows, scenarios, integrations, and operations second;
   - README or index last.
5. Close defect classes while authoring:
   - lifecycle closure matrix for stateful domains;
   - cross-record rules referenced from their owning spec, not re-derived;
   - contract and prose synchronized both directions.
6. Run mechanical verification. For service implementations:

   ```bash
   python3 plugins/saga/scripts/implementation_spec_audit.py audit --target platform-specs/06-service-implementations/<service>
   ```

7. Route review through `saga:doc-review`.
   - Use buildability-probe mode only when the profile defines exact inputs and a pass criterion.
   - Otherwise run the normal readiness-skeptic pass and record the profile gap.

## Buildability Probe Contract

For profiles that define a buildability probe, the probe is a fresh-context simulation of a cold builder.
The probe receives only the profile's exact input set and writes one artifact under `docs/reviews/`.

The probe output must include:

- implementation breakdown;
- exhaustive assumptions-and-questions by category;
- per-question boundary-test classification;
- `VERDICT: PASS` only when there are zero spec defects.

Boundary test: if two reasonable implementers could answer a question differently, and the difference is
visible in API behavior, data shape, or user experience, it is a spec defect. Otherwise it is an
execution-time discovery.

## Rules

- Do not use `saga:spec` for this. `saga:spec` is the WHAT-only sibling.
- Do not apply one library's folder contract to another library.
- Do not author from a thin or missing standard.
- Do not run the probe inline in the same context that authored the spec.
- Use repo-relative paths in written artifacts.
- Follow `saga/references/formatting-style.md`.

## References

- `references/profile-contract.md`
- `plugins/saga/scripts/implementation_spec_audit.py`
- `saga/references/formatting-style.md`
