# Saga Family State Policy

## Scope

This policy covers local runtime state and proof evidence for the Codex `saga` and
`team-execution` plugins.

## State Roots

- `saga` uses `.codex/saga/` for repo-local state.
- `team-execution` uses `.codex/team-execution/` for repo-local state.
- Shared proof runs use `.codex/proofs/` for local, untracked proof scratch data.

Repo-local state is allowed only when the relevant path is ignored or otherwise protected from
accidental commits. If the repo-local path is not protected, use a user-local fallback under
`~/.codex/<plugin>/state/<repo>/`.

## Allowed Data

State files may contain:

- Selected lifecycle, reviewer, and validator names.
- Non-secret command names, exit codes, and summarized output.
- Relative evidence paths.
- Gate status, remediation-loop counts, warnings, and blocked reasons.
- Redacted identifiers needed to trace a proof run.

State files must not contain:

- Secrets, tokens, credentials, or credential provenance that identifies a secret source.
- Raw production payloads, sensitive prompts, or protected operational data.
- Full remote logs when summaries and stable links are sufficient.
- Unredacted personal data unless the target repo already treats it as shareable test data.

## Redaction

Redact before writing state. Prefer summaries and artifact pointers over copied transcripts.
Evidence that might contain credentials, protected payloads, or production-only identifiers stays
main-thread local and is not delegated to subagents.

## Retention And Cleanup

Local state is temporary. Keep only the artifacts needed to prove the current task, then remove
scratch state after the PR or handoff is complete. Tracked proof documents must be shareable and
must not depend on ignored state for interpretation.
