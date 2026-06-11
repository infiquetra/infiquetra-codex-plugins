# Product Review Template

Use this for `docs/product-reviews/YYYY-MM-DD-<topic>-product-review.md`.

Follow `saga/references/formatting-style.md`: open each section with a one-line verdict, keep prose short,
and use tables for comparisons and route summaries.

~~~markdown
---
title: {{topic}} product review
type: product-review
date: {{YYYY-MM-DD}}
topic: {{topic-slug}}
maturity: {{experiment-ready | requirements-ready | deferred-context}}
source: {{docs/ideation/... | direct}}
---

# {{Topic}} Product Review

## Summary

{{One-line decision summary.}}

## Reviewed Ideas

| Idea | Riskiest assumption | Smallest build-to-learn | Metric | Threshold | Premise | Route |
|---|---|---|---|---|---|---|
| {{idea}} | {{assumption}} | {{experiment}} | {{metric}} | {{threshold}} | {{holds/fails}} | {{saga:plan / saga:brainstorm / parked}} |

## Route Decisions

| Route | Ideas | Maturity | Next command |
|---|---|---|---|
| Prototype experiment | {{ideas}} | `experiment-ready` | `saga:plan` |
| Full requirements | {{ideas}} | `requirements-ready` | `saga:brainstorm` |
| Parked | {{ideas}} | `deferred-context` | none until revived |

## Open Questions

- {{Only unresolved questions that block the next route. Delete this section if empty.}}
~~~

## Post-write checklist

- [ ] Frontmatter includes `type: product-review`, `date`, `topic`, `maturity`, and `source`.
- [ ] Every routed idea has a metric and threshold, or is marked `needs_threshold`.
- [ ] Parked ideas include the premise failure.
- [ ] The route table uses `saga:plan`, `saga:brainstorm`, or parked only.
- [ ] No placeholder remains.
