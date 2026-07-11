# Gate Policy

The gate verdict is `pass`, `block`, or `escalate`. Hard failures take precedence over reviewer
averages and advisory opinions.

```text
missing/forged evidence? --------------------------> block
root-accountability child without host attestation? -> block
required independence without host-attested child? -> block
unresolved P0/P1, security, or role hard stop? ----> block
required validator absent/failed/blocked? ---------> block
typed root verification missing? ------------------> block
remediable issue before cycle 3? ------------------> block and rerun affected role
remediable issue at cycle 3? ----------------------> escalate
none of the above? --------------------------------> pass
```

Each gate step records its independence, evidence vehicle, role evidence reference, typed root
verification reference, validator requirement/status, config-disable status, optional score, and
typed findings. `skipped-by-config` is valid only for an explicitly disabled non-required
validator. Required and disabled is an invalid contract.

An unresolved P0 or P1 always blocks. Any unresolved security finding or role-specific hard stop
also blocks regardless of its numeric score. P2/P3 nonsecurity findings require remediation; the
third unresolved cycle escalates and never passes.

An optional validator warning is reported but does not block by itself. External advisory seats
must declare `gate_authority=none`; their presence, score, failure, or absence cannot pass or block a
hard gate.

Reviewer arithmetic remains supporting evidence: overall is the mean of applicable dimensions and
9.0 is the review target. A low score creates an advisory warning only. It affects the hard gate
only after the reviewer expresses the underlying concern as a typed finding or role hard stop. A
high average can never override severity or missing evidence. Every base reviewer is mandatory
until a protected skip-review selector exists. A selected reviewer must return at least one
applicable dimension and may exclude only individual dimensions.

A protected resolution is permission to run the next affected-role attempt, not permission to
erase the current finding. The next intent binds the exact predecessor, every prior finding ID, and
a subject descended from the prior output. A finding disappears only when a later receipt consumes
the changed resolution subject and revalidates without that finding. Persistent findings remain
byte-identical across attempts.

The gate loads one protected normalized receipt for every workflow step and requires exact step-set,
workflow, dependency, attempt, role, vehicle, result, and root-verification bindings. Syntax-shaped
references and caller-supplied findings or validator statuses have no authority. Root evidence is
an evidence-ID-to-typed-protected-record map. Agent validator evidence references are protected
command-output records whose argv/tool/exit facts derive from the protected record; snapshots and
caller assertions cannot stand in for command evidence. Raw command streams are never retained.
Required monitor/deploy evidence remains blocked until an authenticated observation adapter exists.
Deterministic validators additionally bind their pinned command contract and before/after no-write
audit. The evaluator
refuses to evaluate Verified Workflows implementation paths, because the protocol under test cannot
approve itself.
