# Worker and Result Manifest

Workers produce evidence, never authority. Before work, the root persists a content-addressed intent
that binds workflow, step, attempt, task, logical role, lens, execution class, runtime agent name, expected profile
digest, mutation boundary, required evidence, nonce, and creation time. Retrying the same explicit
nonce/time inputs returns the same intent reference. Every remediation/revalidation attempt gets a
new intent and fresh execution context; follow-up messages cannot alter the bound attempt.

The intent subject declares authorized paths and inherits one protected preflight Git baseline.
Every revision binds exact content, modes, current Git entries, delta paths, and parent subjects.
Later attempts must descend from the prior output even when a finding persists. Existing unrelated
dirty paths remain outside the subject; changing one becomes an unauthorized delta.

A child result becomes gate-eligible only after the root validates the role's output schema,
required protected evidence, and pre/post mutation audit, persists the structured result in protected plugin
data, and persists a root-verification record bound to it. Hook `last_assistant_message` and
transcript paths are never result sources.

The candidate normalized subagent receipt joins:

```text
planned intent + native launch acknowledgement + hook start/stop pair
              + installed-hook readback from the declared Codex home + current role/profile bytes
              + schema-valid result + root verification
```

The join records the mapped runtime agent name, hook-reported agent type, active model, safe permission mode, profile digest, child
and task identity, and timestamps. A launch acknowledgement may follow the hook start because the
native spawn call returns after launch. It labels expected effort as `installed-profile-digest` and
expected sandbox as configured, not observed. Absolute paths, transcripts, prompts, tool arguments,
raw results, environment values, and credentials are forbidden. Without host-issued child
attestation, this is root-accountability diagnostic evidence and always blocks the gate.

External providers do not write worker intents, receipts, or results. Saga binds their dispatch
identity, attestation, liveness, and reconciliation evidence before Verified Workflows may retain a
protected advisory reference. That reference declares `seat_type=external-second-opinion` and
`gate_authority=none`; its findings, score, status, failure, or absence never enter reviewer,
validator, severity, or completion arithmetic.

Inline receipts bind the role/lens/result but explicitly state that no separate child, model,
effort, or sandbox was observed. Deterministic receipts bind the command contract, protected
stream hashes/sizes plus typed stdout projection, and no-write audit, with no model fields. Raw
stdout and stderr are never retained. Root evidence maps each declared evidence ID to a typed
protected subject, snapshot, mutation audit, or command-output record. Tester/scanner claims must
derive from the command-output record rather than a caller assertion.

Records use content-derived references and contained no-follow reads. Raw-pair normalization uses a
prepared, normalized, committed transaction. Retry reads the existing normalized receipt before
raw cleanup, while cleanup revalidates the exact raw hashes before unlinking. Start-only leaves need
a protected abandonment record before pruning; traversal and byte ceilings apply inside leaves.
