# Gate Policy

The root reduces the approved contract, validated typed results, deterministic check outcomes, fresh-root reviewer identities, independently verified root findings, and one shared remediation counter to `pass`, `block`, or `escalate`.

```text
missing or failed blocking check -----------------> block
missing fresh-root independent reviewer ----------> block
review average below 9.0 -------------------------> block
any applicable dimension below 7.0 ---------------> block
invalid exclusion or arithmetic ------------------> invalid gate input
unresolved P0/P1, security, or role hard stop ----> block
unresolved P2/P3 ----------------------------------> block
resolved finding without focused revalidation ----> block
unresolved issue after remediation round 3 -------> escalate
none of the above ---------------------------------> pass
```

Every selected reviewer returns at least one applicable dimension. Exclusions are dimension-specific and use only `static-non-applicable`. Overall is the arithmetic mean of applicable dimensions. A high average never overrides a typed finding or hard stop.

The implementer and its descendants cannot supply authority-bearing review. Every required reviewer has a separately validated fresh-root identity, no implementation turns, a read-only profile, and its typed reviewer result. Additional reviewers are risk-triggered, not mandatory ceremony.

Only the root adopts independently verified findings and releases dependencies. Messages, raw model output, external advisory output, and claimed success flags have no gate authority.

Remediation uses one workflow-wide counter from zero through three. Each affected role reruns with a fresh canonical agent path. Partial edits are classified before retry. A finding marked resolved counts only after the focused blocking check passes on the changed state and the finding ID appears in the fresh revalidation set. A fourth automatic round is forbidden.
