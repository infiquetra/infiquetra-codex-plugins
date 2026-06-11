---
name: product-review
description: De-risk surviving Infiquetra ideas before committing to a build. Slots after saga:ideate and before saga:brainstorm or saga:plan. Per idea: riskiest assumption, smallest build-to-learn, success metric threshold, premise check, and operator-confirmed route.
argument-hint: "[ideation doc path | topic | idea list]"
---

# Product Review

Use this after `saga:ideate` when ideas are promising but the bet is not proven enough for full
requirements or implementation planning.

Product review answers: which surviving ideas are worth building, and what is the cheapest way to learn
before committing?

It writes `docs/product-reviews/YYYY-MM-DD-<topic>-product-review.md`. It does not write requirements,
plans, code, issues, Saga state, commits, PRs, or deployment state.

## Position

- `saga:ideate` generates and ranks grounded candidates.
- `saga:product-review` de-risks those candidates by assumption, experiment, metric, and premise.
- `saga:brainstorm` deepens a validated idea into requirements.
- `saga:plan` can consume an `experiment-ready` prototype as a scoped spike.

## Workflow

1. Resolve the subject from `$ARGUMENTS`.
   - If it is a `docs/ideation/` artifact, read the ranked survivors and revivable cut.
   - If it is a topic or list, treat the named ideas as the review set.
   - If the subject is missing, ask for the ideation doc or idea set.
2. Offer near-miss revivals when an ideation artifact includes a cut list. Use:

   ```bash
   python3 plugins/saga/scripts/product_review.py revival --survivors '<json>' --cut '<json>'
   ```

3. Review each idea one at a time:
   - riskiest assumption;
   - smallest build-to-learn;
   - success metric and concrete threshold;
   - premise check against current grounding.
4. Compute route recommendations with:

   ```bash
   python3 plugins/saga/scripts/product_review.py route --ideas '<json>'
   ```

5. Confirm routes with the operator before treating them as real.
6. Write the product-review artifact using `references/product-review-template.md`.
7. Route onward:
   - prototypes -> `saga:plan` with `maturity: experiment-ready`;
   - full builds -> `saga:brainstorm` with `maturity: requirements-ready`;
   - parked ideas -> `deferred-context`.

## Rules

- A route without a threshold is not actionable. Ask for the threshold or record `needs_threshold`.
- A failed premise parks the idea, even if it is otherwise attractive.
- The helper recommends; the operator decides.
- Use repo-relative paths in written artifacts.
- Follow `saga/references/formatting-style.md`.

## References

- `references/product-review-template.md`
- `plugins/saga/scripts/product_review.py`
- `saga/references/formatting-style.md`
