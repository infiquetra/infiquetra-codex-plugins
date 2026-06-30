# Validator Evidence and State - team-execution

Validator evidence is stored as JSON state plus referenced artifacts.

## State Location

Default repo-local state:

```text
.codex/team-execution/
```

Use this location only when it is ignored or otherwise protected from commits.
If the repo-local path is not protected, use:

```text
~/.codex/team-execution/state/<repo>/
```

## State File Shape

Use one JSON file per validator run:

```json
{
  "validator": "security-scanner",
  "group": "scanner",
  "required": true,
  "selection_reason": "Python API code and dependency lockfile changed",
  "tools": [
    {
      "name": "bandit",
      "command": "uv run bandit -r plugins/",
      "available": true,
      "setup": "uv add --dev bandit"
    }
  ],
  "inputs": ["plugins/example", "pyproject.toml"],
  "evidence": ["logs/security-scanner-2026-06-06.txt"],
  "findings": [],
  "status": "pass",
  "remediation_loop": 0,
  "execution_mode": "delegated",
  "vehicle": "team-execution-delegated"
}
```

Serial fallback records the same fields, with `execution_mode` set to `serial`
and `vehicle` set to `team-execution-serial`, plus an explicit note that
consensus was not independently delegated.

Gate-facing vehicle values:

- `team-execution-delegated` — selected validator role ran as a delegated Codex agent.
- `team-execution-serial` — selected validator role ran serially in the main thread.
- `generic-subagent` — non-selected generic assistance; recordable context, not validator evidence.
- `inline-assist` — inline helper work; recordable context, not validator evidence.

Only `team-execution-delegated` and `team-execution-serial` satisfy Team Execution reviewer or
validator gates.

## Evidence Rules

- Keep evidence paths relative when they are inside the repo.
- Do not store secrets, tokens, credentials, production identifiers, or sensitive payloads.
- Prefer summaries plus artifact paths over large pasted logs.
- Include exact command, exit code, and relevant stdout/stderr summary.
- Include timestamps for remote CI and runtime checks.
- Redact before writing state.

## Completion Summary

Final reports include selected validators, skipped validators, gate result,
state directory, evidence paths, remaining warnings, and blocked signals.
