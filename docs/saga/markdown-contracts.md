# Markdown Contracts

Saga documents should be readable by humans and reliable for downstream agents.

The shared contract lives at [formatting-style.md](../../plugins/saga/references/formatting-style.md), and the structural gate lives at [test_saga_doc_formatting.py](../../tests/test_saga_doc_formatting.py).

## Failure Matrix

| Bad shape | Why it fails | Good shape |
|---|---|---|
| Adjacent `**basis:**`, `**confidence:**`, `**complexity:**` lines | CommonMark collapses them into one paragraph. | Put compact fields in a table. |
| Four or more prose sentences in one block | Readers cannot scan the artifact quickly. | Use short paragraphs separated by blank lines. |
| A ranked list with repeated prose blocks | Comparative data becomes hard to compare. | Use a table for rank, title, confidence, and complexity. |
| `maturity` in Saga frontmatter | Maturity is derived, never stored. | Store `lifecycle_phase`; derive maturity during handoff. |
| Handoff issue without source context | The receiver cannot verify what artifact produced the issue. | Include source artifact path and maturity/source context. |
| A plan unit as a nested bullet with loose fields | Renderers detach fields or collapse structure. | Use `### U<N>.` headings with blank-line-separated bold labels. |

## Bad And Good Example

Bad:

```markdown
**basis:** direct: docs/example.md
**confidence:** 88
**complexity:** Low
```

Good:

```markdown
| field | value |
|---|---|
| basis | direct: docs/example.md |
| confidence | 88 |
| complexity | Low |
```

## Maintenance Rule

When a doc-writing skill adds a new generated artifact shape, link [formatting-style.md](../../plugins/saga/references/formatting-style.md) and add the artifact template to [test_saga_doc_formatting.py](../../tests/test_saga_doc_formatting.py) when the collapse pattern could recur.

