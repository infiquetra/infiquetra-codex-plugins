# Check Outcome State

The approved Blocking Checks table is the complete deterministic gate inventory. Each observed outcome is a closed object with `status` and `detail`.

- `pass`: the command or proof satisfies its approved completion condition.
- `warn`: a nonblocking signal needs attention.
- `failed`: the check ran and failed.
- `blocked`: required input, tool, permission, or observation was unavailable.

Every blocking check must be present and `pass`. Missing evidence is `blocked`, never an implied pass. Unexpected check IDs fail input validation.

The root runs commands with the exact approved command or proof boundary, records the concise outcome in the current run record, and keeps raw command streams outside the record. Checks do not create agent identities or a second task graph. After any accepted remediation, the focused blocking check must pass again before release.
