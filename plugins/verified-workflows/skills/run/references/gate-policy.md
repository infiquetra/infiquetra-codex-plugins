# Gate Policy

Validated assignment results and blocking checks reduce to `pass`, `block`, or `escalate`.

```text
missing or failed blocking check -----------------> block
missing independent reviewer ---------------------> block
invalid exclusion or arithmetic ------------------> invalid gate input
reviewer score alone ------------------------------> advisory
unresolved planned actionable finding ------------> block
one direct blocker within one-hop budget ----------> one repair and targeted check
deferred adjacent nonblocking finding -------------> report; do not block
approval-required or second unplanned issue -------> escalate
actual P0/P1 secret/auth/destructive/disclosure ---> hard stop
resolved finding without targeted recheck --------> block
unresolved finding after remediation and recheck -> escalate
none of the above ---------------------------------> pass
```

The approved workflow names one independent reviewer. Additional reviewers are allowed only when the
approved plan identifies a concrete risk requiring them. Scores are advisory. A score or finding
category alone does not block; concrete typed findings, blocking checks, and role hard stops do.

The run has one global unplanned-repair budget. Root may classify one direct blocker as `one-hop`
only when it stays inside the existing writes and adds no file, dependency, interface, schema,
state, role, abstraction, cross-plugin/repository work, or live mutation. One repair and one
targeted recheck consume the budget. A second issue, broader scope, failed recheck, or new authority
requires operator approval. Adjacent nonblocking work is `defer`; automatic issue creation is out
of scope.
