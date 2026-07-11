# Outcome Dispatch Ledger

The outcome ledger is append-only. `outcome.dispatch.v2` first records an intent, then an
evidence-backed acknowledgement. Reconciliation appends the acknowledgement and never rewrites a v1
commit. A v1 synthetic leaf id is `legacy-unverified`: it settles deduplication but does not advance
dependents until reconciliation supplies a launch receipt or confirmed handoff reference.
