# Improve Codex Plugins Decision Log

This log gives a future root session the operating decisions for the
improve-codex-plugins Operations Project work and records answers to
child-session questions. It complements the orchestration charter; current
GitHub, source, installed-byte, and runtime facts still require a live read.

## Session-wide operator decisions

- Work only the remaining Operations Project cards whose Objective field is
  improve-codex-plugins, after validating that each remains desirable.
- Root owns orchestration and uses Saga inline mode. Child sessions may use
  Verified Workflows when useful, subject to root's scope and proportionality
  review.
- Use Codex child sessions only, launched in unique single-root-pane Herdr tabs
  in workspace w24. Create them in the background with --no-focus; never use
  pane splits.
- Select and verify each child session's model and reasoning effort explicitly.
  A deliberate inheritance must be stated in the launch record.
- The first two pre-work sessions inherited gpt-5.6-sol/max unintentionally.
  They were not interrupted. Every later launch requires an explicit model and
  reasoning effort.
- Keep roughly no more than three active issue streams. Separate author,
  reviewer, implementer, tester, and live-test work when independence or a
  different model or reasoning effort is useful.
- Close a named child-session tab promptly after its output is accepted and its
  handoff or branch state is durable. Record its session name or identifier
  when later resumption may matter. Keep only active or intentionally retained
  sessions so workspace w24 remains manageable.
- YOLO mode, the local agent wrapper's elevated-permission --yolo mode, is
  authorized only when the assigned scope actually needs it.
- Root may make bounded choices and may commit, push, create and merge PRs,
  refresh the marketplace, install or deploy plugins, access required
  credentials, activate runtime state, and conduct live tests. Escalate to Jeff
  for a material change to product behavior, scope, security posture, or
  operational risk.
- Preserve unrelated work. Use separate issue branches and worktrees, never
  broad-stage a shared worktree, and never edit installed cache snapshots as
  maintained source.
- Keep credentials, secrets, and private runtime material out of repository
  documentation and fixtures.

## Initial orchestration decision

Before synchronization, the local checkout had 20 dirty paths. Those paths were
preserved in commit dc74954 on local rescue branch
rescue/pre-improve-codex-plugins-20260810. The clean base was then synchronized.
Local main, origin/main, and live remote main were independently verified at
commit dd1746e. The two commits were historical evidence, not instructions to
repeat the rescue or sync work; any later reliance required revalidation.

## Child-session register

This compact register preserves resumable continuity without keeping completed
tabs open. New session rows are appended, and their launch identity and routing
facts are immutable. Root may update only Current outcome/closure and
Handoff/resume as a session progresses or closes.

| Start timestamp | Session/tab name | Durable Codex session identifier | Model/effort | Permission mode | Workspace/cwd or branch | Assignment | Current outcome/closure | Handoff/resume |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-08-11T01:48:22.554Z | agent-skill-author | 019fee81-0dad-7f83-897d-a4ed28fd74e3 | gpt-5.6-sol/max; inherited unintentionally | Normal permissions | w24; repository main | First skill-author attempt | Blocked by write root; no changes; tab closed | Superseded by agent-skill-write |
| 2026-08-11T01:49:04.494Z | repo-sync-audit | 019fee82-241c-7d62-b2ff-c65855130083 | gpt-5.6-sol/max; inherited unintentionally | Normal permissions | w24; repository main | Read-only dirty-base audit | Completed with rescue/sync recommendation; tab closed | Accepted output; no resumption expected |
| 2026-08-11T01:56:29.512Z | agent-skill-write | 019fee88-be8c-7e21-86a5-e036881b0d97 | gpt-5.6-terra/medium; explicit | Extended write root for ~/.codex/skills; no YOLO | w24; repository main | Author agent-launcher skill | Completed and validated; tab closed | Durable session identifier retained |
| 2026-08-11T02:02:49.101Z | agent-wrapper-no-focus | 019fee8e-4f72-7fd3-b2e1-f8d80e05fe20 | gpt-5.6-sol/high; explicit | Extended write root for ~/.local/bin; no YOLO | w24; repository main | Implement no-focus wrapper path | Completed and validated; tab closed | Durable session identifier retained |
| 2026-08-11T02:08:57.067Z | session-charter-author | 019fee93-54b2-7cd0-9c77-24636f7e784b | gpt-5.6-terra/high; explicit | YOLO mode; dedicated worktree was outside root's default writable root, and the document author needed write access there | w24; session-charter worktree on docs/improve-codex-plugins-session-charter | Author and fix charter documents | Completed document authoring and all review repairs; git diff --check passed; tab closed after root accepted output | Reviewed files ready for root commit; durable session identifier retained |
| 2026-08-11T02:14:27.434Z | session-charter-doc-review | 019fee98-fea3-7f72-a4b3-8fdf78b1f327 | gpt-5.6-sol/high; explicit | Normal permissions | Same session-charter worktree and branch | Read-only independent review | All eight original findings and both repair follow-ups resolved on final re-review; tab closed after root accepted output | REVIEW COMPLETE; no resumption expected |

## Child-session decisions

| Timestamp (ISO 8601 with timezone) | Issue/workstream | Asking session | Question | Decision | Evidence/reason | Scope impact | Outcome/commit | Supersedes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Update procedure

Root owns this log. When a child session needs a decision, it should ask root
with the issue or workstream, the decision needed, and the supporting evidence.
Root appends one row with a complete ISO 8601 timestamp including timezone after
deciding. Record the result or commit when known. Later decisions name any
earlier entries they supersede; never rewrite prior rows. Child sessions do not
self-record root decisions.
