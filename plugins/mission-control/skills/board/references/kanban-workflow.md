# Board Workflow Reference

Condensed reference for the Infiquetra GitHub Projects boards. The canonical source of
truth is `$INFIQUETRA_SDLC_PATH/config/sdlc-schema.json`, with prose context in
`$INFIQUETRA_SDLC_PATH/docs/process/board-topology.md` and
`$INFIQUETRA_SDLC_PATH/docs/process/kanban-workflow.md`.

---

## Boards

| Project key | Board | Purpose |
|-------------|-------|---------|
| `operations` | Operations | Raw operator intent, approvals, personal/operator work, and shaping |
| `asgard` | Asgard | Jeff-proximal rapid action, incubation, and mission-mode work |
| `campps` | CAMPPS | Long-lived CAMPPS initiative execution board |

Prefer project views over new boards until scale, automation, or reporting needs justify
a separate board.

---

## Workflows

### Operations And Asgard

```
Idea -> Shaping -> Ready -> Active -> Verify -> Done
```

| Status | Purpose |
|--------|---------|
| Idea | Captured thought or opportunity. Not shaped enough for execution. |
| Shaping | Intent is being clarified, scoped, or turned into an actionable card. |
| Ready | Work is shaped enough to route or start. Operations must name a target team before promotion. |
| Active | The owner is working the card. |
| Verify | Outcome is being checked before closure or promotion. |
| Done | Completed or intentionally closed for this board. |

Asgard modes:

| Mode | Use |
|------|-----|
| Rapid Action | Reversible, time-sensitive work that benefits from low ceremony. |
| Incubator | Exploratory work likely to define future CAMPPS execution. |
| Mission | Focused, high-leverage work close to Jeff with a clear outcome. |

### CAMPPS

```
Idea -> Committed -> In Progress -> Done -> Parked
```

| Status | Purpose |
|--------|---------|
| Idea | Candidate initiative work or proof card that is not yet committed. |
| Committed | Accepted into the CAMPPS portfolio for active execution. |
| In Progress | Execution or verification is actively underway. |
| Done | Work is completed. |
| Parked | Work is intentionally paused without closing the initiative. |

Pause state: `Parked`. Older Mount Olympus status names such as `Assigned`,
`In Review`, `Deployment Ready`, and `Deployed` are retired historical terms.
Deployment state belongs in deployment fields and GitHub Deployments/Environments,
not in the core Status workflow.

---

## WIP Limits

| Board | Status | Limit |
|-------|--------|-------|
| Operations | Shaping | 10 |
| Operations | Ready | 10 |
| Operations | Active | 5 |
| Operations | Verify | 5 |
| Asgard | Shaping | 8 |
| Asgard | Ready | 8 |
| Asgard | Active | 5 |
| Asgard | Verify | 5 |
| CAMPPS | Committed | 10 |
| CAMPPS | In Progress | 10 |

When a limit is exceeded, finish or unblock current work before pulling more into that status.
Critical defects can temporarily override WIP, but the exception should be visible in the card.

---

## Standup Format

Walk right-to-left through the relevant board:

| Board | Review order |
|-------|--------------|
| Operations / Asgard | Done -> Verify -> Active -> Ready -> Shaping -> Idea |
| CAMPPS | Parked -> Done -> In Progress -> Committed -> Idea |

Ask:

- What is terminal and safe to archive?
- What is waiting for verification or review?
- What is actively owned, and is it aging?
- What is blocked or waiting on Jeff?
- What should move next, and what should stay out of WIP?

---

## Common Scenarios

### Raw Intent From Jeff

1. Capture on Operations as `Idea`.
2. Shape until target team and context pack are clear.
3. Move to `Ready`.
4. Route to Asgard, CAMPPS, Jeff, or External/Deferred based on target team.

### Explicit Cross-Team Transfer

1. Treat Asgard and CAMPPS as sibling target boards, not stages in a default funnel.
2. Keep work on the selected board unless an operator explicitly routes, transfers, clones, or links it elsewhere.
3. When a transfer is requested, make the receiving issue self-contained: target repo or surface, acceptance criteria, verification, risk, approvals, and context links must be clear.

### CAMPPS Engineering Flow

1. Start in `Idea` until the operator commits the initiative work.
2. Move through `Committed` and `In Progress`.
3. Close as `Done` or park as `Parked`.
4. Track environment promotion separately through deployment fields and deployment records.

---

## Metrics Boundaries

Cycle time starts when active ownership begins:

| Board | Start | Terminal |
|-------|-------|----------|
| Operations / Asgard | Active | Done |
| CAMPPS | In Progress | Done |

Legacy Mount Olympus timeline values may still include `Assigned`, `In Review`, or
`Deployed`; tooling may read them for history but should not create new CAMPPS cards with those statuses.
