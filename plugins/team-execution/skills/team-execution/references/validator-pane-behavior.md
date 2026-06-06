# Validator Display Behavior - team-execution

The source display-pane model is retired for the Codex port. This file remains
only to preserve the operator-relevant behavior: keep role output grouped,
inspectable, and tied to evidence artifacts.

## Codex Replacement

- Group reviewer artifacts under `reviewers/<role>.json`.
- Group scanner, tester, monitor, and operational artifacts under
  `validators/<role>.json`.
- Record `execution_mode` as `delegated` or `serial`.
- Record subagent capability as `present` or `absent` in proof artifacts.
- Record backpressure fallback when delegation exists but cannot be used.

## Retired Behavior

Terminal display layout, pane routing, and host-specific setup assets are not
runtime requirements in this Codex plugin. They must not be treated as gates for
reviewer consensus, validator execution, or completion.
