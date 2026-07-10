# mission-control

SDLC management for Infiquetra's Operations, Asgard, and CAMPPS boards. This plugin provides a complete interface for managing the development lifecycle — from issue creation to flow metrics — reading board and workflow configuration from `infiquetra-sdlc` and vendored fallbacks.

## Overview

All operations run locally via the `gh` CLI, providing:

- **Project board operations** — view, move, add, archive, WIP analysis, standup prep across Operations, Asgard, and CAMPPS
- **Issue creation** — prepared Asgard handoff drafts for Asgard and CAMPPS work with readiness checks, source artifact resolution, approval gating, and confirmed creation
- **Label management** — deploy, audit, sync initiative/objective fields, auto-label rules
- **Flow metrics** — cycle time, throughput, WIP age using GitHub timeline events
- **Rollout tracking** — gap analysis and full SDLC deployment to any Infiquetra repo
- **Milestone management** — create and track Objectives via GitHub Milestones
- **Flow helpers** — `flow set-field` / `flow link-sub-issue` / `flow verify-label` / `flow validate-card` / `flow field-options` / `flow discover-project`. Operator-facing GraphQL + REST helpers for project field assignment, native sub-issue linking, self-healing label create, and card pre-flight validation

Mission Control participates in the Saga family by owning SDLC mutation after
Saga emits reviewed handoff context. The full lifecycle guide is
`../../docs/saga/README.md`.

## Quick Start

### Prerequisites

- `gh` CLI installed and authenticated with github.com (Projects write scope required for `flow set-field` writes — see `gh auth status`)
- `infiquetra-sdlc` repo checked out at `~/workspace/infiquetra/infiquetra-sdlc` (or set `INFIQUETRA_SDLC_PATH`)
- Python 3.12+

### Script Location

```bash
SCRIPT="plugins/mission-control/scripts/sdlc_manager.py"
```

When this plugin is installed, resolve `scripts/sdlc_manager.py` relative to
the packaged plugin root.

### Verify Configuration

```bash
python3 $SCRIPT config show
```

### Prepare an Issue Draft

Use prepared drafts when starting from rough source text, notes, or an agent prompt that must be
reviewed before GitHub mutation:

```bash
python3 $SCRIPT issue prepare \
  --repo campps-platform \
  --type capability \
  --team asgard \
  --project campps \
  --risk medium \
  --title "CAMPPS prepared issue workflow" \
  --from docs/plans/example.md \
  --maturity plan-ready

python3 $SCRIPT issue approve docs/sdlc-issue-drafts/<draft>.md
python3 $SCRIPT issue create-prepared docs/sdlc-issue-drafts/<draft>.md
```

Prepared drafts are written under `docs/sdlc-issue-drafts/` with a JSON sidecar. The sidecar
includes handoff maturity, approval state, source artifact metadata, and project-field values when
available. Creation refuses drafts still marked `needs_operator_approval`, renders a mutation plan
before side effects, repairs missing labels/templates after confirmation, opens a mapping PR when the
repo is not mapped to the requested project, and starts prepared Asgard-owned work in `Shaping`.

## Codex Skills

| Skill | Activates When... |
|-------|------------------|
| `board` | Board review, item movement, WIP analysis, standup prep |
| `issues` | Issue creation, type selection, template guidance |
| `labels` | Label deployment, field sync, audit |
| `metrics` | Cycle time, throughput, WIP age analysis |
| `rollout` | Rollout status, gap analysis, SDLC deployment |
| `milestones` | Objective milestones, progress tracking |
| `flow` | Project fields, sub-issues, card validation, label self-heal |

## Complex Workflows

The Codex skills and bundled script support multi-step operations:
- Full issue lifecycle (create -> label -> board -> fields -> milestone)
- Board grooming (archive + WIP check + standup)
- New initiative/objective setup (labels + field options + milestone)
- Objective progress tracking across repos
- Batch triage of untriaged issues
- Project field assignment via `flow set-field` (Initiative, Objective, Status, Target Team, Mode, and other live single-select fields)
- Native sub-issue linking via `flow link-sub-issue` (cross-repo, idempotent)
- Card body pre-flight validation via `flow validate-card`

## Auth And Mutation Boundary

Mission-control uses the operator's `gh` authentication. It does not store
GitHub tokens. Write-capable commands must show the target host, repo, issue or
project identifiers, and planned payload before mutation. Dry-run or preview
paths are the validation default. If permissions are missing, the script should
fail with an explicit message and without logging credentials.

Write-capable prepared issue creation also checks
`config/target-allowlist.json` before rendering a preview and again before
mutation. The default allowlist permits `github.com`, the `infiquetra`
organization, and the known Infiquetra project keys only.

## Architecture

mission-control uses a single shared CLI (`scripts/sdlc_manager.py`) at the plugin root rather than per-skill scripts, because all 7 skills share the same execution backend. Each skill's SKILL.md documents the subset of CLI commands it uses, but they all invoke the same script.

## Script Reference

### Board Operations

```bash
# View board by column
python3 $SCRIPT board view --project campps

# Add issue to its default repo-mapped board
python3 $SCRIPT board add --repo athena-service --number 42

# Add or move issue on a specific board
python3 $SCRIPT board add --project asgard --repo infiquetra-sdlc --number 42
python3 $SCRIPT board move --project asgard --repo infiquetra-sdlc --number 42 --status "Active"
python3 $SCRIPT board move --project campps --repo campps-platform --number 42 --status "In Progress"

# Archive terminal workflow items (use --dry-run first)
python3 $SCRIPT board archive --project campps --dry-run
python3 $SCRIPT board archive --project asgard --dry-run

# Check WIP counts vs limits
python3 $SCRIPT board wip --project campps

# Standup prep (right-to-left board review)
python3 $SCRIPT board standup --project campps
python3 $SCRIPT board standup --project operations

# Discover all project fields and options
python3 $SCRIPT board discover-fields --project campps
```

### Label Operations

```bash
# Set initiative/objective project fields directly
python3 $SCRIPT flow set-field --project campps \
  --repo athena-service --number 42 \
  --field Objective --option "platform-launch"

# Audit repo labels
python3 $SCRIPT labels audit --repo athena-service

# Deploy all SDLC labels to a repo
python3 $SCRIPT labels deploy --repo athena-service

# Auto-label based on title/body content
python3 $SCRIPT labels auto-label --repo athena-service --number 42

# Create new field option on project board
python3 $SCRIPT fields create-option --project campps --field initiative --option "new-initiative"

# Discover all field options
python3 $SCRIPT fields discover --project campps
```

### Metrics Operations

```bash
# Cycle time percentiles (uses timeline events — may take 30-60s)
python3 $SCRIPT metrics cycle-time --project campps --days 30
python3 $SCRIPT metrics cycle-time --project campps --type capability

# Throughput by week
python3 $SCRIPT metrics throughput --project campps --weeks 4

# WIP age (fast)
python3 $SCRIPT metrics wip-age --project campps

# Time in each column for specific item
python3 $SCRIPT metrics column-time --project campps --number 42
```

### Milestone Operations

```bash
# Create milestone for Objective
python3 $SCRIPT milestones create \
  --repo athena-service \
  --title "Pilot: Auth MVP" \
  --due-date 2026-04-15

# List milestones
python3 $SCRIPT milestones list --repo athena-service --state open

# Show milestone progress
python3 $SCRIPT milestones progress --repo athena-service --milestone 1

# Link issue to milestone
python3 $SCRIPT milestones link --repo athena-service --issue 42 --milestone 1
```

### Rollout Operations

```bash
# Show rollout status
python3 $SCRIPT rollout status
python3 $SCRIPT rollout status --team asgard

# Gap analysis for a repo
python3 $SCRIPT rollout gap-analysis --repo athena-service

# Deploy labels to repo
python3 $SCRIPT rollout deploy-labels --repo athena-service

# Deploy issue templates to repo
python3 $SCRIPT rollout deploy-templates --repo athena-service

# Full SDLC deployment (labels + templates)
python3 $SCRIPT rollout deploy-all --repo athena-service

# Update rollout tracking
python3 $SCRIPT rollout update --repo athena-service --field labels --status complete
```

### Flow Operations (Phase C)

Operator-facing GraphQL + REST helpers. See `skills/flow/SKILL.md` for the full per-command idempotency contract.

```bash
# Set Initiative or Objective on a card (project FIELDS, not labels)
python3 $SCRIPT flow set-field --project campps \
    --repo campps-platform --number 42 \
    --field Initiative --option campps-quality

# List the live options on a project field (IDs rotate on rename)
python3 $SCRIPT flow field-options --project campps --field Objective

# Resolve which project a repo maps to
python3 $SCRIPT flow discover-project --repo athena-service

# Link child as native sub-issue of parent (cross-repo, idempotent)
python3 $SCRIPT flow link-sub-issue \
    --parent-repo campps-context-library --parent-number 1 \
    --child-repo campps-platform --child-number 42

# Self-healing label create (404 → create; exists → no-op; auth/server errors raise)
python3 $SCRIPT flow verify-label --repo campps-platform \
    --name high-priority --color D93F0B --description "High priority"

# Pre-flight card body against the card_validator schema
python3 $SCRIPT flow validate-card --repo campps-platform --number 42
```

### Prepared Issue Workflow

```bash
# Draft from a source artifact without GitHub mutation
python3 $SCRIPT issue prepare \
    --repo hermes-claude-code-router \
    --type capability \
    --team asgard \
    --project campps \
    --risk medium \
    --title "Prepared issue workflow" \
    --from docs/brainstorms/example.md \
    --maturity requirements-ready

# Create after reviewing the markdown draft and sidecar
python3 $SCRIPT issue create-prepared docs/sdlc-issue-drafts/<draft>.md

# Explicit override when a mapping PR was opened but creation must continue
python3 $SCRIPT issue create-prepared docs/sdlc-issue-drafts/<draft>.md --override-mapping
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INFIQUETRA_SDLC_PATH` | `~/workspace/infiquetra/infiquetra-sdlc` | Path to infiquetra-sdlc checkout |

### Config Files (from infiquetra-sdlc)

| File | Purpose |
|------|---------|
| `config/project-mappings.json` | Project IDs, field IDs, repo-to-project mapping |
| `config/sdlc-schema.json` | Canonical board/team/workflow/WIP/deployment-state schema |
| `config/labels.json` | Label definitions and auto-label rules |
| `config/beads-config.json` | (legacy — file removed from infiquetra-sdlc on 2026-04-26; reads degrade gracefully to `{}`. The `legacy_rollout_config` key in `load_config` documents the migration.) |

## Projects

| Project | Team | Purpose |
|---------|------|---------|
| Operations | Jeff | Raw intent, approvals, personal/operator work, and shaping before team execution |
| Asgard | Asgard | Rapid action, incubation, and mission-mode work close to Jeff |
| CAMPPS | Asgard-owned initiative board | Long-lived CAMPPS execution portfolio |

## WIP Limits

| Board / Column | Limit |
|--------|-------|
| Operations / Shaping | 10 |
| Operations / Active | 5 |
| Asgard / Active | 5 |
| CAMPPS / Committed | 10 |
| CAMPPS / In Progress | 10 |

## Metric Targets

| Type | Cycle Time P85 |
|------|---------------|
| Capability | < 5 days |
| Enhancement | < 2 days |
| Defect | < 1 day |

## Related

- **infiquetra-sdlc**: Source of SDLC configuration, issue templates, and process documentation
- **campps-context-library**: Context repository for CAMPPS capabilities
