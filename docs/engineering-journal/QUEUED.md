# Queued

- Prove a credentialed API-client plugin boundary before porting PagerDuty, Slack, Splunk, Todoist, or identity tooling.
- Design a Codex-native replacement for `team-execution` instead of copying the Claude `TeamCreate` flow.
- Consider a generator only after skill-plus-script, credentialed client, MCP/app, and native orchestration boundaries are each proven.
- Review the integration model between `saga:outcome` and the rest of the Saga lifecycle. Current operator expectations lean toward `/plan` and `/work` synchronizing outcome DAG state automatically, while the current coordinator model requires explicit outcome completion, approval, advance, and leaf handoff steps.
- Replace Claude-style slash commands in every Saga-generated operator handoff with Codex-native skill invocations. For example, render `$saga:work <plan>` instead of `/saga:work <plan>` in chat guidance, persisted artifacts, templates, and routing summaries.
