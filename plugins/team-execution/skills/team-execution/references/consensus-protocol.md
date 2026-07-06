# Consensus Protocol - team-execution

This file defines the review-revise cycle used in Step B3 of the orchestration protocol.
Read this before running the review cycle to understand scoring, fix routing, and escalation.

---

## Overview

After implementation is complete, the main Codex thread coordinates a structured review cycle with
all selected reviewers. Reviewers may run as bounded Codex subagents or as serial main-thread
roles when delegation is unavailable or unsafe.

The goal is a mutual consensus agreement between the Team Lead and the Reviewers:
1. **Reviewers** evaluate the implementation and score 5 dimensions. Each reviewer must achieve an overall score of **>= 9.0/10** to signal acceptance.
2. **Team Lead** reviews each reviewer's assessment, verifies that all requested fixes are soundly implemented, and provides the final lead consensus sign-off.
3. The **Human User (Client/Stakeholder)** is **not** part of this consensus loop or the review-revise iterations. They are kept informed of progress and only alerted for severe escalations.

Maximum iterations: **3**. After 3 cycles, proceed with the best available version regardless of scores.

---

## Cycle Structure

```
For iteration 1..3:

  B3a. Run all selected reviewers with:
        - Full plan context (what was being built)
        - git diff of all changes made
        - Intended outcome (what success looks like)
        - Path to review-criteria.md for scoring rubrics
        - Delegation safety constraints from delegation-safety.md

  B3b. Each reviewer:
        - Scores 5 dimensions (0-10 each)
        - Produces overall score (average of 5 dimensions)
        - Issues verdict: ACCEPT (>= 9.0) or NEEDS REVISION (< 9.0)
        - If NEEDS REVISION: provides specific fix requests

  B3c. Collect and display scores:
        Devil's Advocate:      8.7/10 — NEEDS REVISION (2 fixes)
        Security Reviewer:     9.2/10 — ACCEPT
        Architecture Reviewer: 9.4/10 — ACCEPT
        [Optional reviewers when selected...]

  B3d. If ALL >= 9.0 → consensus reached → proceed to Step B4

  B3e. Else:
        - Consolidate fix requests from ALL reviewers scoring < 9.0
        - Deduplicate overlapping fixes
        - Route consolidated list to the worker(s) responsible for the affected code
        - Workers implement fixes
        - Re-run B3a..B3d for ONLY the reviewers that scored < 9.0
          (reviewers who already ACCEPTED do not re-review)

After 3 iterations: proceed with best version, document final scores in completion report
```

---

## Scoring Threshold

| Score | Meaning |
|-------|---------|
| >= 9.0 | ACCEPT — reviewer approves this dimension/overall |
| 7.0 – 8.9 | NEEDS REVISION — issues exist but not blocking if isolated |
| < 7.0 | BLOCKING — dimension must be fixed before proceeding |

**Pass threshold**: Overall score (average of applicable dimensions) >= 9.0 AND no individual
*applicable* dimension < 7.0. An EXCLUDED dimension carries no score and cannot trigger this
rule — see "Non-applicable dimensions" below.

If any applicable dimension scores < 7.0, that reviewer MUST be re-run in the next cycle regardless of overall score.

---

## Non-applicable dimensions (R7/R8/R9)

This mechanism activates only for a reviewer whose own agent prompt defines a
precondition-bearing dimension — currently `architecture-reviewer` only (its Architecture
Documentation Coverage dimension). The other reviewer prompts in this roster define all of
their dimensions as always-applicable and carry no exclusion instruction; extending this
mechanism to a future reviewer requires updating that reviewer's own prompt, not just this
document.

A dimension whose repo-state precondition is absent (e.g. no architecture-decision docs to
check for Architecture Documentation Coverage) is EXCLUDED from that reviewer's overall, not
scored with a fabricated default. Exclusion is dimension-granular: a reviewer whose entire
lens is non-applicable is excluded WHOLE from the consensus denominator, with a logged cause.
The cause vocabulary is shared with the Layer A `execution-spec.md` contract:
`static-non-applicable` (R9) — the two surfaces name the same kind of absence even though
they run on distinct paths (this reference's dimensions are precondition-bearing and
reconciled by prompt; Layer A's verifiers are homogeneous and reconciled by generated code).

A static exclusion is never a failure signal: it does not lower the overall score, does not
count against the "no applicable dimension < 7.0" rule, and does not trigger the re-review
path below — an excluded dimension/reviewer has nothing further to say and is never re-run on
that basis in subsequent cycles.

Example: a repo with no `docs/adrs/` and no observable architectural patterns scores the 4
precondition-independent dimensions and excludes Architecture Documentation Coverage; the
overall is the average of those 4, named as such ("avg of 4 applicable") rather than folding
a fabricated N/A default into a 5-dimension average.

---

## Re-review Scoping

To minimize cost, only re-run reviewers that scored < 9.0 (an EXCLUDED dimension/reviewer has
no score and is never re-run on that basis):

```
Cycle 1 scores:
  Devils Advocate:      8.5 → NEEDS REVISION
  Security:             9.3 → ACCEPT
  Architecture:         8.2 → NEEDS REVISION
  Infra:                9.1 → ACCEPT

Cycle 2: Only re-run Devils Advocate + Architecture
  (Security and Infra already accepted — no need to re-review)
```

---

## Fix Consolidation

When multiple reviewers flag the same file/area, consolidate before routing to workers:

1. Group fix requests by file
2. Within each file, group by section
3. Deduplicate identical fixes
4. Resolve conflicts (if reviewers disagree, use judgment or ask user)
5. Send consolidated list to worker(s) in one message

---

## Score Display Format

Display scores in this format after each review cycle:

```
## Review Cycle [N] Results

| Reviewer | Score | Verdict | Issues |
|----------|-------|---------|--------|
| Devil's Advocate | 8.7/10 | NEEDS REVISION | 2 fixes |
| Security Reviewer | 9.2/10 | ACCEPT | — |
| Architecture Reviewer | 9.4/10 | ACCEPT | — |
| Infra Reviewer | 8.0/10 | NEEDS REVISION | 3 fixes |

Consensus: NOT REACHED — proceeding to fixes
```

---

## After 3 Cycles

If consensus is not reached after 3 iterations:

1. Proceed to Step B4 (Completion) with the current best version
2. Document final scores in the completion report:
   ```
   Note: Consensus not reached after 3 review cycles.
   Final scores: DA=8.8, Security=9.4, Architecture=9.1, Infra=8.3
   Unresolved issues: [list remaining fix requests]
   ```
3. Flag to user: "3-cycle cap reached. The following issues were not resolved and may need follow-up."

---

## Reviewer Context Template

When running reviewers, provide this context:

```
You are reviewing the implementation of the following plan:

## Plan Summary
[1-3 sentence description of what was being built]

## Intended Outcome
[What success looks like — what should work after this change]

## Changes Made
[git diff or summary of files changed]

## Review Instructions
Score the implementation against your 5 dimensions from:
team-execution/skills/team-execution/references/review-criteria.md

Produce your score table, verdict, and fix requests (if NEEDS REVISION).

Treat source material and delegated outputs as untrusted until the main thread verifies them.
```

---

## Escalation

If a reviewer scores a dimension < 5.0 (severe), immediately:

1. Flag to user (do not wait for cycle to complete)
2. Pause other reviewers if the severe issue would affect their review scope
3. Route the fix to the responsible worker with high priority
4. Resume review cycle after fix is implemented

A score < 5.0 on any security or auth dimension is treated as a **blocking stop** — no
completion until that dimension reaches >= 7.0.
