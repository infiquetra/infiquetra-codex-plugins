---
name: board
description: |
  Manage the Infiquetra GitHub Projects boards: Operations, Asgard, and CAMPPS.
  Handles board views, status moves, item adds, terminal-item archive, WIP analysis,
  field discovery, and standup preparation.
when_to_use: |
  Use this skill when the user wants to:

  Board review and status:
  - Review or view Operations, Asgard, or CAMPPS board state
  - Check overall board health or get a snapshot of current work
  - See what's in a specific status, such as Shaping, Active, Assigned, or In Review

  Moving items between statuses:
  - Move an issue to a different board status
  - Update an issue's board status after shaping, implementation, review, or verification

  Adding items to boards:
  - Add an issue or PR to its default repo-mapped board
  - Add an issue or PR to a specific board with --project

  Archiving and cleanup:
  - Archive terminal workflow items after reviewing a dry run
  - Remove stale completed items from active board views

  WIP analysis and standup:
  - Check WIP limits and bottlenecks
  - Generate a right-to-left standup or board-review summary
  - Identify blocked or aging work
---

# SDLC Board

Manage Infiquetra's current project boards:

| Project key | Board | Workflow |
|-------------|-------|----------|
| `operations` | Operations | `Idea -> Shaping -> Ready -> Active -> Verify -> Done` |
| `asgard` | Asgard | `Idea -> Shaping -> Ready -> Active -> Verify -> Done` |
| `campps` | CAMPPS | `Idea -> Committed -> In Progress -> Done -> Parked` |

CAMPPS is a long-lived initiative board, not the retired Mount Olympus execution board.
Deployment state is not a workflow status; use deployment fields and GitHub
Deployments/Environments for environment movement.

## Script Location

```bash
plugins/mission-control/scripts/sdlc_manager.py
```

If `$INFIQUETRA_SDLC_PATH` is unset, use `~/workspace/infiquetra/infiquetra-sdlc` as the default base path.
Always run the script with `python3`.

## Core Operations

### View Board

```bash
# View a board by status
python3 sdlc_manager.py board view --project operations
python3 sdlc_manager.py board view --project asgard
python3 sdlc_manager.py board view --project campps

# Filter to a specific status
python3 sdlc_manager.py board view --project asgard --status "Active"
python3 sdlc_manager.py board view --project campps --status "In Progress"
```

### Add Item

```bash
# Add an issue or PR to the default repo-mapped board
python3 sdlc_manager.py board add --repo infiquetra-sdlc --number 42

# Add an item to a specific board
python3 sdlc_manager.py board add --project asgard --repo infiquetra-sdlc --number 42
python3 sdlc_manager.py board add --project operations --repo infiquetra-sdlc --number 42
```

### Move Item

```bash
# Intent-flow boards
python3 sdlc_manager.py board move --project asgard --repo infiquetra-sdlc --number 42 --status "Active"
python3 sdlc_manager.py board move --project operations --repo infiquetra-sdlc --number 42 --status "Shaping"

# CAMPPS initiative flow
python3 sdlc_manager.py board move --project campps --repo campps-platform --number 42 --status "Committed"
python3 sdlc_manager.py board move --project campps --repo campps-platform --number 42 --status "In Progress"
python3 sdlc_manager.py board move --project campps --repo campps-platform --number 42 --status "Done"
```

Use `board discover-fields` when unsure which Status options exist live.

### Archive Terminal Items

```bash
# Always preview first
python3 sdlc_manager.py board archive --project campps --dry-run
python3 sdlc_manager.py board archive --project asgard --dry-run

# Run only after operator confirmation
python3 sdlc_manager.py board archive --project campps
```

The command archives terminal workflow items. For Operations, Asgard, and CAMPPS that means `Done`.

### WIP And Standup

```bash
python3 sdlc_manager.py board wip --project campps
python3 sdlc_manager.py board wip --project asgard
python3 sdlc_manager.py board standup --project campps
python3 sdlc_manager.py board standup --project operations
```

Standup output walks each board right-to-left using the schema-backed workflow order.

### Discover Fields

```bash
python3 sdlc_manager.py board discover-fields --project campps
python3 sdlc_manager.py board discover-fields --project asgard
python3 sdlc_manager.py board discover-fields --project operations
```

## WIP Limits Reference

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

When WIP is exceeded, stop pulling new work on that board and focus on finishing, swarming,
or moving blocked cards to the right pause state.

## Natural Language Examples

**"Review the Asgard board"**
-> `board view --project asgard`

**"Move issue #42 in infiquetra-sdlc to Active on Asgard"**
-> `board move --project asgard --repo infiquetra-sdlc --number 42 --status "Active"`

**"Add this issue to Operations"**
-> Confirm repo and issue number, then `board add --project operations --repo <repo> --number <N>`

**"Are we over WIP limits?"**
-> Run `board wip` for the relevant board.

**"Let's prep for standup"**
-> `board standup --project campps` or the requested board.

## Reference Documents

- `references/kanban-workflow.md` - Board structure, status definitions, WIP limits, and standup format
- `references/graphql-queries.md` - GraphQL queries used by the script
