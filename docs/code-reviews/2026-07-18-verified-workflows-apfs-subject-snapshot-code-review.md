---
date: 2026-07-18
target: origin/main...fix/verified-workflows-apfs-subject-snapshot
reviewed_revision: fe93073db66877df79dff3d69d6dde95f4410535
blocked: false
review_type: code-quality
mode: manual-bootstrap-advisory
---

# Verified Workflows APFS Subject Snapshot Code Review

## Findings

No P0-P3 findings survived root adjudication. The independent security-reviewer evidence returned an
`accept` verdict with no typed findings, and root correctness, maintainability, API-compatibility, and
adversarial passes found no additional issue.

| priority | status | finding |
|---|---|---|
| None | closed | No merge-blocking or advisory code finding remains. |

## Scope Check

**CLEAN.** The branch changes only the approved subject-snapshot projection, its regression coverage,
the aligned patch-release surfaces, and the required lifecycle evidence artifacts.

Intent: allow authorized missing files and directories to enter a subject chain without weakening
outside-scope evidence.

Delivered: immediate-parent-only link normalization, strict negative controls, release `1.0.2`, and a
manual self-hosting review/validation gate.

## Plan Completion

| item | mode | state | evidence |
|---|---|---|---|
| R1-R5 / U1 subject continuity and strict evidence | DIFF | DONE | `workspace_evidence.py`; focused subject-chain and mutation-control tests. |
| R6 / U2 aligned patch release | DIFF | DONE | Manifest, validators, generated facts/inventory, portability docs, changelog, README, and direct tests. |
| R9 / U3 manual bootstrap | DIFF | DONE | Registry-bound advisory reviewer and validator attempts plus root quality gates. |
| R7 installed source/cache parity | EXTERNAL-STATE | UNVERIFIABLE | Requires the post-merge marketplace install and cache readback in U4. |
| R8 preservation replay and issue #357 replacement run | CROSS-REPO | NOT-DONE | Intentionally gated behind merge and explicit U4 continuation authority. |

Completion: U1-U3 DONE; U4 remains the approved post-merge continuation rather than missing code in
this PR.

## Review Coverage

Selected lenses:

- correctness — root traced exclusion-parent derivation, traversal, and subject ancestry.
- security — registry-bound `security-reviewer` challenged the filesystem trust boundary.
- testing — registry-bound `scenario-tester` ran the APFS and negative-control matrix.
- maintainability/conventions — root checked scope, naming, generated surfaces, and repository policy.
- API compatibility — root verified schemas and old protected records remain readable and unmodified.
- adversarial — selected because the change alters protected evidence; sibling, higher-ancestor,
  hardlink/inode, mode, symlink, and Git-control controls were challenged.

Suppressed findings: 0. Validator-rejected findings: 0. Pre-existing findings: 0.

## Review Result Contract

| field | value |
|---|---|
| reviewed revision | `fe93073db66877df79dff3d69d6dde95f4410535` |
| input digest | `7dd89c5558e245418b8a5494ed7f795bad037a36edaab00855bc8c480dedd6cc` |
| blocked | false |
| findings | none |
| scope check | clean |
| plan completion | U1-U3 done; U4 post-merge |
| linked plan | `docs/plans/2026-07-17-verified-workflows-apfs-subject-snapshot-plan.md` |
| linked work session | `docs/work-sessions/2026-07-18-verified-workflows-apfs-subject-snapshot.md` |
| QA artifact | `docs/qa/qa-task-verified-workflows-apfs-subject-snapshot-2026-07-18.md` |

## Residual Risk

Linux execution remains CI evidence rather than local evidence; the portable directory-creation case was
inspected and passes by filesystem semantics, but only APFS ran here. Installed-cache parity and the
replacement issue #357 root receipt remain U4 gates. The two child attempts are advisory because this
plugin cannot grant authority to its own implementation.
