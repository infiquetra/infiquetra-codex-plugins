# Saga Portability Notes

## Source

- Source plugin: `saga`
- Base source commit: `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`
- Latest imported source commit: `abcc06b16763975d71e483a6dac768f4664d7b63`
- Saga 0.41 parity source commit: `b30e0f2ba7cd0cfdeaf97c1d4510c9a0468e96da`
- Port status: Codex-native proof port

## Codex Port Shape

This port keeps source skill names behind the `saga` plugin namespace. It does not keep active command, agent, hook, or source manifest directories. Runtime state moves to `.codex/saga/`, protected by repo `.gitignore`.

Persistent issue, deploy, team-execution, and context-library work stays owned by receiving plugins:

- `mission-control` owns issue artifacts, boards, comments, labels, milestones, and project state.
- `deploy` owns tag promotion, rollback, hotfix, deployment status, and deployment mutation.
- `team-execution` owns reviewer consensus, selected validators, subagent delegation, serial fallback, and evidence gates.
- `saga` owns lifecycle routing, local state, outcome receipts, status cards, and promotion proposals.

## Backend Contract

Codex Saga exposes only:

- `inline`
- `manual`
- `team-execution`

Source Workflow, fork, goal, and hook backends are lineage only and not executable in the Codex plugin without a separate capability proof and negative fallback tests.

## Outcome And Promote

Saga 0.41 adds Codex-native `saga:outcome` and `saga:promote` surfaces. Outcome state stays in `docs/outcomes/` and `.codex/saga/`. Promotion scans source journals read-only and prepares context-library journal proposals behind explicit approval.

## Document Formatting Contract

Saga imports the source document-readability contract into `references/formatting-style.md`. It is active Codex skill guidance and test coverage, not a host-specific command or manifest surface.

## Handoff Contract

Saga emits structured handoff envelopes that name the receiving skill. It does not call private APIs in receiving plugins. Handoff payloads are untrusted context: receiving plugins must re-read and re-verify before mutation.
