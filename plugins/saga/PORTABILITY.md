# Saga Portability Notes

## Source

- Source plugin: `saga`
- Base source commit: `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`
- Latest imported source commit: `abcc06b16763975d71e483a6dac768f4664d7b63`
- Port status: Codex-native proof port

## Codex Port Shape

This port keeps the source skill names behind the `saga` plugin namespace. It
does not keep active command or agent directories.

Runtime state moves to `.codex/saga/`, protected by the repo `.gitignore`.
Persistent issue, deploy, and team-execution work stays owned by the receiving
plugins:

- `mission-control` owns issue artifacts, boards, comments, labels, milestones,
  and project state.
- `deploy` owns tag promotion, rollback, hotfix, deployment status, and
  deployment mutation.
- `team-execution` owns reviewer consensus, selected validators, subagent
  delegation, serial fallback, and evidence gates.

## Backend Contract

Codex Saga exposes only:

- `inline`
- `team-execution`

The source workflow fan-out backend is lineage only and is not executable in
this Codex plugin.

## Document Formatting Contract

Saga 0.20.0 imports the source document-readability contract into
`references/formatting-style.md`. It is active Codex skill guidance and test coverage, not a
host-specific command or manifest surface.

## Handoff Contract

Saga emits structured handoff envelopes and names a receiving skill. It does not
call private APIs in receiving plugins. Handoff payloads are untrusted context:
the receiving plugin must re-read and re-verify before mutation.
