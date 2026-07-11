# Codex Outcome Dispatch Boundary

Saga records lifecycle and outcome intent. A skill-mediated Codex launch supplies the typed
acknowledgement; native child execution is not inferred from a backend name or caller capability flag.
Canonical workflow mode is `verified-workflow`; legacy `team-execution` values are read-only input.

An acknowledgement is `launched` with a real leaf Saga id or `handed-off` with an operator reference.
Only `launched` participates in liveness and dependent progress.
