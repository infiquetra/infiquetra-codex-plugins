# Reviewer Registry - team-execution

This file defines base reviewers and optional reviewers. A reviewer can run as a
bounded Codex subagent when delegation is available and safe, or as a serial
main-thread role when delegation is unavailable.

## Base Reviewers

These reviewers are included for every non-trivial team-execution plan.

| Reviewer | Focus |
|----------|-------|
| `devils-advocate-reviewer` | Assumptions, edge cases, failure modes, alternatives, scope creep |
| `security-reviewer` | Auth/authZ, secrets, PII, input validation, dependencies, supply chain |
| `architecture-reviewer` | Patterns, separation of concerns, dependency direction, conventions |

## Optional Reviewers - Code Plans

| Keywords in Plan | Suggested Reviewer | Prompt Material |
|---|---|---|
| CDK, CloudFormation, Lambda, DynamoDB, S3, IAM, KMS, infrastructure, AWS | `infra-reviewer` | Focus on IaC, permissions, deployment model, cost, and blast radius |
| API, endpoint, REST, OpenAPI, versioning, SDK, contract, breaking change | `api-reviewer` | Focus on API compatibility, versioning, contracts, and clients |
| pytest, test, coverage, integration test, mock, fixture, e2e, test suite | `testing-reviewer` | Focus on test scope, meaningful coverage, and verification commands |
| refactor, lint, patterns, DRY, complexity, technical debt, abstraction | `code-quality-reviewer` | Focus on maintainability, clarity, and local idioms |
| PII, GDPR, data classification, consent, retention, personal data, privacy | `privacy-reviewer` | Focus on data minimization, retention, and privacy controls |

## Optional Reviewers - Docs And Specs

| Keywords in Plan | Suggested Reviewer | Prompt Material |
|---|---|---|
| docs, README, specification, guide, runbook, architecture doc, documentation | `clarity-reviewer` | Focus on reader clarity, ambiguity, and operational usefulness |
| issue template, GitHub issue, task description, acceptance criteria, AI prompt, SKILL.md, spec | `ai-usefulness-reviewer` | Focus on whether the artifact is actionable for humans and agents |

## Plan Type

| Plan Type | Definition | Reviewer Set |
|-----------|------------|--------------|
| `code` | Primarily code, infrastructure, refactors, or bug fixes | Base plus relevant code reviewers |
| `docs/specs` | Primarily documentation, specs, issue templates, skills, or runbooks | Base plus relevant docs reviewers |
| `mixed` | Code and documentation/spec content | Base plus relevant code and docs reviewers |

Docs-only plans are still plans for future implementation and deserve review unless the user
explicitly accepts a lighter path.

## Triage Escape Hatch

A plan qualifies for lightweight review only when all are true:

1. Single config file change.
2. No security, auth, secrets, permissions, or PII surface.
3. Fewer than 3 files modified.
4. No specification or documentation content.

If any condition fails, use the full base reviewer set.

## Custom Reviewers

Users may add custom reviewers. Record the custom role, focus area, required status, and prompt
material in the plan's `## Team Structure` section.
