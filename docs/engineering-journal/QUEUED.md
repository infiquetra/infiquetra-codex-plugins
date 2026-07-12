# Queued

### Verified Workflow preview and agent runtime contract  {#verified-workflow-preview-and-agent-runtime-contract}

**Priority.** P1.

**Effort.** Multi-day.

**Worth it when.** Before the next substantial plan uses Verified Workflows or V2 named agents.

**Context.** Extend the Workflow Contract Studio idea in
`docs/ideation/2026-07-11-codex-workflow-control-agent-lifecycle-ideation.md` with the operator-validated
contract from
`docs/retros/task-codex-external-advisory-execution-contract-2026-07-12.md`. The AI must preview the
complete task graph, dependencies, agent roles, model and effort, and recommended per-work-unit
upgrades or downgrades. The operator requests changes conversationally and receives a complete revised
preview until explicit approval. No agent starts before approval. Execution must provide direct thread
switching, visible host-issued runtime receipts, and retained named agents. Any mismatch in approved
role, model, effort, or permissions stops execution and returns to preview instead of silently falling
back inline.

- Prove a credentialed API-client plugin boundary before porting PagerDuty, Slack, Splunk, Todoist, or identity tooling.
- Design a Codex-native replacement for `team-execution` instead of copying the Claude `TeamCreate` flow.
- Consider a generator only after skill-plus-script, credentialed client, MCP/app, and native orchestration boundaries are each proven.
- Review the integration model between `saga:outcome` and the rest of the Saga lifecycle. Current operator expectations lean toward `/plan` and `/work` synchronizing outcome DAG state automatically, while the current coordinator model requires explicit outcome completion, approval, advance, and leaf handoff steps.
- Replace Claude-style slash commands in every Saga-generated operator handoff with Codex-native skill invocations. For example, render `$saga:work <plan>` instead of `/saga:work <plan>` in chat guidance, persisted artifacts, templates, and routing summaries.
