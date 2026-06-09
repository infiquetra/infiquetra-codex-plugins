# team-execution

Codex-native reviewer and validator orchestration for Infiquetra work.

The plugin provides two related skills:

- `team-execution`: plan and run reviewer consensus, selected validator gates,
  evidence capture, and guarded nonprod automation.
- `appsec-audit`: focused application security review for URL and input trust
  boundaries.

## Runtime Modes

- `delegated`: Codex subagents are available and the task is safe to delegate.
- `serial`: subagents are unavailable, unsafe, or backpressured. The main thread
  runs each role sequentially, records per-role artifacts, labels consensus as
  serial, and states the independence limits.

Subagents are advisory evidence collectors. They do not authorize mutation,
change scope, bypass confirmation, or make the final completion decision.

Team Execution participates in the Saga family by owning reviewer consensus,
validator selection, and evidence capture. The full lifecycle guide is
`../../docs/saga/README.md`.

## Reviewer Protocol

Base reviewers:

| Reviewer | Focus |
|----------|-------|
| `devils-advocate-reviewer` | Assumptions, edge cases, failure modes, scope creep |
| `security-reviewer` | Auth/authZ, secrets, PII, input validation, supply chain |
| `architecture-reviewer` | Patterns, separation of concerns, convention adherence |

Optional reviewers are selected from repository and plan signals. Reviewer
consensus requires overall score `>= 9.0/10` and no dimension `< 7.0`.

## Validator Gates

Validators are selected by context; the full roster is not run by default.

| Group | Roles |
|-------|-------|
| Scanners | `security-scanner`, `iac-cost-scanner`, `api-compat-scanner`, `dependency-scanner` |
| Testers | `smoke-tester`, `scenario-tester`, `api-contract-tester`, `sdk-regression-tester`, `event-flow-tester`, `ui-regression-tester`, `performance-tester`, `concurrency-tester` |
| Monitors | `github-actions-monitor`, `runtime-monitor` |
| Operational | `deploy-watcher` |

Required validators with missing tools are `blocked` with setup guidance.
Optional validators may report `warn` or `skipped-by-config`.

## State

Repo-local state uses:

```text
.codex/team-execution/
```

Use repo-local state only when ignored or otherwise protected from commits. If
that path is not protected, use:

```text
~/.codex/team-execution/state/<repo>/
```

State may contain selected roles, command names, exit codes, summarized output,
relative evidence paths, findings, gate status, and remediation counts. Redact
secrets, tokens, credentials, production payloads, and protected operational
data before writing state.

## Protocol Probe

The deterministic probe exercises runtime-mode and state-policy behavior:

```bash
python3 plugins/team-execution/scripts/protocol_probe.py --subagents absent --pretty
```

Examples:

```bash
python3 plugins/team-execution/scripts/protocol_probe.py \
  --subagents present \
  --validator security-scanner:scanner:required:bandit:present

python3 plugins/team-execution/scripts/protocol_probe.py \
  --subagents absent \
  --validator security-scanner:scanner:required:semgrep:missing
```

## Reference Files

- `skills/team-execution/references/reviewer-registry.md`
- `skills/team-execution/references/review-criteria.md`
- `skills/team-execution/references/consensus-protocol.md`
- `skills/team-execution/references/validator-registry.md`
- `skills/team-execution/references/validator-criteria.md`
- `skills/team-execution/references/validator-execution-order.md`
- `skills/team-execution/references/validator-evidence-state.md`
- `skills/team-execution/references/validator-spawn-quirks.md`
- `skills/team-execution/references/validator-pane-behavior.md`
- `skills/team-execution/references/delegation-safety.md`

## Plugin Structure

```text
team-execution/
├── .codex-plugin/plugin.json
├── skills/
│   ├── appsec-audit/SKILL.md
│   └── team-execution/
│       ├── SKILL.md
│       └── references/
├── scripts/protocol_probe.py
├── tests/test_protocol_probe.py
├── README.md
├── PORTABILITY.md
└── CHANGELOG.md
```
