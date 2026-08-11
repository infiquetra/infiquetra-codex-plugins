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
| 2026-08-11T02:29:17.771Z | validate-provider-49-52 | 019feea6-529c-7352-a600-69eb1035fd77 | gpt-5.6-sol/high; explicit | Normal permissions | w24; repository main | Read-only validation of Operations issues #49-#52 | Completed and accepted; tab closed | Resumable by durable identifier if needed |
| 2026-08-11T02:29:17.929Z | validate-saga-54-58 | 019feea6-5fe2-7062-a8bc-83c95aa64bae | gpt-5.6-terra/high; explicit | Normal permissions | w24; repository main | Read-only validation of Operations issues #54-#58 | Completed and accepted; tab closed | Resumable by durable identifier if needed |
| 2026-08-11T02:29:18.132Z | validate-fleet-59-63 | 019feea6-6d64-7492-b2a9-deb9feab4bd1 | gpt-5.6-sol/high; explicit | Normal permissions | w24; repository main | Read-only validation of Operations issues #59-#63 | Completed and accepted; tab closed | Resumable by durable identifier if needed |
| 2026-08-11T02:41:12.751Z | validation-log-scribe | 019feeb2-0814-7b01-a2e6-58fef89f39d3 | gpt-5.6-terra/medium; explicit | YOLO mode; this dedicated worktree is outside the root session's default writable root | w24; validation-log worktree on docs/improve-codex-plugins-validation-log | Append validation and orchestration decisions | Completed and root-accepted; git diff --check passed; tab closed | Durable identifier retained |
| 2026-08-11T02:46:12.307Z | issue-61-plan-author | 019feeb6-9a2a-7a43-bb63-7b1c10f92e00 | gpt-5.6-terra/high; explicit | YOLO mode; dedicated worktree is outside root's default writable root | w24; issue-61-plan worktree on docs/issue-61-saga-plan | Saga plan for parent #61 narrowed to #51/#52 | Active plan author | Resume by durable identifier if needed |
| 2026-08-11T02:46:12.308Z | issue-63-plan-author | 019feeb6-9a29-78e0-9190-51c4e518f236 | gpt-5.6-sol/high; explicit | YOLO mode; dedicated worktree is outside root's default writable root | w24; issue-63-plan worktree on docs/issue-63-saga-plan | Saga plan for parent #63 narrowed to #57 plus diff-to-manifest completeness | Active plan author | Resume by durable identifier if needed |
| 2026-08-11T02:46:12.606Z | issue-62-plan-author | 019feeb6-9b59-7a10-96e1-2829dee95a6a | gpt-5.6-sol/high; explicit | YOLO mode; dedicated worktree is outside root's default writable root | w24; issue-62-plan worktree on docs/issue-62-saga-plan | Saga plan for parent #62 narrowed to #55/#56 plus bounded current-session recovery | Active plan author | Resume by durable identifier if needed |

## Child-session decisions

| Timestamp (ISO 8601 with timezone) | Issue/workstream | Asking session | Question | Decision | Evidence/reason | Scope impact | Outcome/commit | Supersedes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-08-11T02:45:02.001Z | #49 and #50 | validate-provider-49-52; validate-fleet-59-63 | Whether to retain the two provider issues under #61 despite the validators' disagreement | Close both NOT_PLANNED; accept the narrower provider evidence | PR #69 removed the status, approval, and chaperone surfaces. Provider telemetry, persistence, subscription economics, and account detection would recreate retired control-plane machinery. | #61 retains only #51 effort forwarding and #52 macOS USER preservation. | #49 and #50 closed NOT_PLANNED | |
| 2026-08-11T02:45:02.002Z | #56 | validate-saga-54-58 | Whether .git/info/exclude makes the repository ignore-rule issue obsolete | Retain #56 under #62 | .git/info/exclude is machine-local, and external lifecycle tooling can create .claude state. | One repository-owned ignore rule and verification that no runtime path is tracked; no archive or new canonical state. | #56 remains open in Shaping | |
| 2026-08-11T02:45:02.003Z | #57 | validate-saga-54-58 | Whether to retriage the companion-repository evidence issue as nonpriority | Retain #57 under #63 | The current source-port evidence contract requires cwd "." and cannot truthfully name a declared companion-repository harness. | One verified companion-repository selector, not arbitrary paths or a second control plane. | #57 remains open in Shaping | |
| 2026-08-11T02:45:02.004Z | Final issue grouping and parent boundaries | validate-provider-49-52; validate-saga-54-58; validate-fleet-59-63 | How to group retained work after the validators and direct source and GitHub checks | #61 owns #51 effort forwarding and #52 macOS USER preservation; #62 owns #55 transient-attempt settlement, #56 .claude ignore, and bounded discovery/extraction for current Codex sessions; #63 owns #57 companion-repository evidence and diff-to-manifest completeness. | All three validators plus direct source and GitHub checks. | #62 has no monitor, status database, archive, or new canonical state. #63 has no second manifest or control plane. Keep closed children linked as history. | Parent boundaries recorded | |
| 2026-08-11T02:45:02.005Z | GitHub reconciliation | Root | Whether the issue and Operations Project states match the final grouping | Reconciliation complete | #49 and #50 closed NOT_PLANNED and moved Idea to Done; #54 was already closed COMPLETED and moved Shaping to Done; #58 closed COMPLETED and moved Idea to Done because PR #68 removed the feasibility gate from the active path and PR #69 deleted its implementation and tests; #59 closed COMPLETED and moved Shaping to Done because PRs #68, #69, and #72 completed the broad simplification. | #51 and #52 moved Idea to Shaping. #55, #56, #57, #61, #62, and #63 remain open in Shaping. Validation comments were added to every retained issue. | Live GitHub issue and board readback verified | |
| 2026-08-11T02:48:52.001Z | Herdr workspace placement | Root | How to keep the three plan-author sessions in workspace w24 | Inherit HERDR_WORKSPACE_ID=w24 for relaunches. | Passing the literal existing identifier through `agent --workspace` created three new workspaces labelled w24. The sessions were idle and unprompted. Root closed w25-w27 and live launch readback showed w24:tE, w24:tF, and w24:tG with focused=false. | All issue work remains in the requested workspace. Future launches from this orchestration terminal omit --workspace unless the wrapper intentionally creates a named workspace. | No issue work occurred in the discarded workspaces. | |

## Update procedure

Root owns this log. When a child session needs a decision, it should ask root
with the issue or workstream, the decision needed, and the supporting evidence.
Root appends one row with a complete ISO 8601 timestamp including timezone after
deciding. Record the result or commit when known. Later decisions name any
earlier entries they supersede; never rewrite prior rows. Child sessions do not
self-record root decisions.
