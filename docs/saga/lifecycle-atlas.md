# Lifecycle Atlas

The Lifecycle Atlas is the visual map of Saga family work.

It shows the operator journey, the command lane, durable artifacts, state/maturity, gates, and plugin ownership. The SVG is the editable source; PNG and PDF exports are committed for presentations.

![Saga lifecycle atlas](visual-assets/saga-lifecycle-atlas.svg)

## Visual Assets

| Asset | Use |
|---|---|
| [Saga lifecycle atlas SVG](visual-assets/saga-lifecycle-atlas.svg) | editable source and GitHub rendering |
| [Saga lifecycle atlas PNG](visual-assets/saga-lifecycle-atlas.png) | presentations and image previews |
| [Saga lifecycle atlas PDF](visual-assets/saga-lifecycle-atlas.pdf) | print or deck import |
| [Readiness ladder SVG](visual-assets/readiness-ladder.svg) | maturity explanation |
| [Ownership boundaries SVG](visual-assets/ownership-boundaries.svg) | plugin boundary explanation |

## Map Reading Guide

| Lane | Meaning |
|---|---|
| User intent | What the operator usually says or brings into the workflow. |
| Command | The Saga family skill that owns the moment. |
| Durable artifact | The tracked document that should survive the session. |
| State and maturity | The lifecycle phase or readiness level produced or consumed. |
| Gate | Whether the step is advisory, hard-gated, or mutation-sensitive. |
| Owner plugin | The plugin responsible for mutation or evidence at that moment. |

Generated facts come from [lifecycle-facts.json](generated/lifecycle-facts.json), produced by [build_saga_docs_facts.py](../../scripts/build_saga_docs_facts.py).

