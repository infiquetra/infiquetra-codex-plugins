# Improve Codex Plugins Orchestration Charter

This charter governs the remaining Operations GitHub Project work for the
improve-codex-plugins objective in the infiquetra-codex-plugins repository. It
gives the root orchestration session durable boundaries; it is not evidence
that any issue remains wanted or that any runtime state is current.

## Objective and starting point

Work the remaining Operations Project cards whose Objective field is
improve-codex-plugins. An initial live snapshot found 13 cards for repository
issues #49–#52, #54–#59, and #61–#63. That list is orientation only. Re-read the
board and each GitHub issue before acting. In particular, repository issue #54
was already closed while its board card still showed Shaping.

Before synchronization, the local checkout had 20 dirty paths. Those changes
were preserved in commit dc74954 on local rescue branch
rescue/pre-improve-codex-plugins-20260810. The clean base was then synchronized
and independently verified at commit dd1746e for local main, origin/main, and
live remote main. These are recorded starting facts, not a substitute for the
next live read.

## Evidence rules

Start from live truth. Keep these kinds of evidence separate:

- Repository source shows what the tracked source currently declares.
- GitHub issues and the Operations Project show current delivery intent and
  workflow state.
- Installed plugin bytes show what is available in a particular local
  installation.
- Fresh runtime behavior shows what a newly created Codex session actually
  does.

Never infer one from another. Re-read the applicable source, GitHub state,
installed bytes, or fresh runtime behavior before making a claim about it.

## Issue intake and lifecycle

For every candidate issue, validate its facts and whether the work is still
desirable. Close, retriage, or mark the issue and board card Done when it is
obsolete, duplicated, already satisfied, or no longer wanted. Do not implement
an issue merely because it exists.

For retained work, use this lifecycle:

1. Validate the issue against current source and GitHub state.
2. Produce a decision-complete Saga plan.
3. Have a separate Saga document-review session review every plan.
4. Fix every actionable finding and re-review until the plan is ready.
5. Implement the approved work.
6. Have a separate Saga code-review session review all generated code.
7. Fix every actionable code-review finding and have the fixes independently
   re-reviewed. If root rejects a finding, explicitly reclassify it as
   non-actionable with supporting evidence.
8. Run narrow checks first, then broader checks when the change warrants them.
9. Complete the pull request (PR), continuous integration (CI), merge, issue,
   and board closeout.
10. Where relevant, refresh the marketplace, install or activate the plugin,
    and prove live behavior in a newly created Codex session.

Bound review loops. Fix concrete errors until the implementation works. Do not
add speculative security harnesses, abstractions, or rare-edge-case machinery.
Security, privacy, and reliability should fit an ordinary Codex plugin
repository.

## Root and child-session operation

The root session owns orchestration, monitors child-session questions, and
independently validates child-session recommendations. Root-owned Saga
orchestration uses inline mode. Child sessions may invoke Verified Workflows
when useful, but root watches scope and keeps the work proportionate.
Root may accept a separately reviewed plan when it remains within this charter.
Material changes to scope or risk still go to Jeff.

Child work uses Codex only through Herdr tabs in workspace w24:

- Use unique tabs with one root pane; do not use pane splits.
- Create tabs in the background with --no-focus.
- Select and verify the model and reasoning effort explicitly for every child.
  If a child deliberately inherits either setting, record that choice.
- YOLO mode, the local agent wrapper's elevated-permission --yolo mode, is
  authorized only when the assigned scope actually needs it.
- Keep roughly no more than three active issue streams.
- Use separate author, reviewer, implementer, tester, or live-test sessions
  when independence or a different model or reasoning effort is useful.
- Close a named child-session tab promptly after its output is accepted and its
  handoff or branch state is durable. Record its session name or identifier
  when later resumption may matter. Retain only active or intentionally retained
  sessions so workspace w24 remains manageable.

## Authority and repository care

Jeff is mostly away. Within this charter, root may make reasonable bounded
choices and may commit, push, create and merge PRs, refresh the marketplace,
install or deploy plugins, access required credentials, activate runtime state,
and conduct live tests. Stop for Jeff when a choice would materially change
product behavior, scope, security posture, or operational risk beyond this
charter.

Preserve unrelated work. Use separate issue branches and worktrees; never
broad-stage a shared worktree. Do not edit installed cache snapshots as source.
Keep secrets and private runtime material out of repository documentation and
fixtures.

Root records decisions made in response to child-session questions in the
companion [decision log](2026-08-10-improve-codex-plugins-decision-log.md).
