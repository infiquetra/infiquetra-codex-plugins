# Hermes Profile Evolution

This Codex-native plugin is a thin consumer of two producer-owned contracts: Team Mimir classifies
repository custody, and the canonical `hermes profile-request` command owns profile dialogue.

Ordinary repository edits continue without contacting Hermes. An intercepted edit that the real
classifier marks as profile-owned, mixed, unknown, or otherwise governed stops at the trusted
`PreToolUse` hook and receives a target-addressed suggestion. The hook is an advisory guardrail. It
does not cover every tool path and cannot prevent same-user, root, shell, external-editor,
disabled-hook, or untrusted-hook edits.

The command accepts bounded JSON on standard input. It does not queue offline work, store a
conversation, select a provider, accept credentials, or mutate profile files itself. `suggest`,
`reply`, and `resume` call the real Hermes command; `doctor` is a read-only compatibility check.

See [PORTABILITY.md](PORTABILITY.md) for supported and excluded surfaces. Hook execution requires
the operator to review and trust the exact Codex hook definition.
