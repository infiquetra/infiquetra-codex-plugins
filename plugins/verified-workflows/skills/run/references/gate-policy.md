# Gate Policy

Validated assignment results and blocking checks reduce to `pass`, `block`, or `escalate`.

```text
missing or failed blocking check -----------------> block
missing independent reviewer ---------------------> block
review average below 9.0 -------------------------> block
any applicable dimension below 7.0 ---------------> block
invalid exclusion or arithmetic ------------------> invalid gate input
any unresolved actionable finding ----------------> block
resolved finding without targeted recheck --------> block
unresolved finding after remediation and recheck -> escalate
none of the above ---------------------------------> pass
```

The approved workflow names one independent reviewer. Additional reviewers are allowed only when the
approved plan identifies a concrete risk requiring them. Scores are feedback; they do not create
another cycle.

All verified actionable in-scope findings are fixed in one remediation assignment or reclassified
with a concrete reason. One targeted recheck validates those dispositions. If an actionable finding
remains, root stops and returns it to the operator. A second remediation or third review is forbidden.
