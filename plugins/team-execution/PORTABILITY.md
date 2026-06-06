# team-execution Portability Notes

## Source

- Source plugin: `team-execution`
- Source commit: `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`
- Port status: Codex-native proof port

## Codex Port Shape

This port keeps the portable reviewer, validator, consensus, and evidence rules from the source
plugin. It does not keep active command or agent directories. Runtime behavior is exposed through
Codex skills and package-local scripts.

The active state root is repo-local `.codex/team-execution/` only when that path is ignored or
otherwise protected from commits. The user-local fallback is
`~/.codex/team-execution/state/<repo>/`.

## Runtime Modes

- `delegated`: used when Codex subagents are available and the task is safe to delegate.
- `serial`: used when subagents are absent, unsafe, or backpressured. Serial mode records
  per-role reviewer and validator artifacts and labels consensus as serial with independence
  limits.

Subagents never authorize mutation. The main thread owns final verification, confirmation gates,
state writes, and the completion decision.

## Retired Source Behavior

The source display setup and host-specific command entrypoints are lineage only in this repo. The
Codex port replaces display-pane behavior with evidence grouping and bounded delegation notes.
