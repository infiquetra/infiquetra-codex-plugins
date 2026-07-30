# Doc review — Codex 0.146 native-harness alignment amendment

**Target:** `docs/plans/2026-07-29-codex-0146-native-harness-alignment-plan.md`
**Classification:** implementation plan
**Status:** PASS; U8-U11 implemented and source-ready
**Reviewed:** 2026-07-29 working tree
**Scope:** U8-U11 amendment; U1-U7 remain source-ready and are not reopened

## Readiness verdict

The amended plan is decision-complete for the additional Codex 0.146 cross-plugin work. It now
separates the already implemented U1-U7 baseline from unapproved U8-U11, preserves the original
port inventory, freezes the other 34 plugin-facing source rows in a new amendment cycle, and makes
routing proof deterministic and non-mutating.

No actionable P0-P3 finding remains. The operator approved U8-U11 on 2026-07-29, redirected U11
to the normal profile, and the implemented amendment reached source-ready on 2026-07-30 with all
17 routing rows and repository gates passing.

## Findings closed in this review

| id | priority | status | finding | fix applied |
|---|---:|---|---|---|
| DR-A1 | P1 | FIXED | The earlier review still said `approved` even though the plan had materially changed and U8-U11 had not been approved. | Set the plan to `plan-ready`, recorded U1-U7 as source-ready, and placed U8-U11 behind a new operator-approval boundary. |
| DR-A2 | P1 | FIXED | Extending the existing frozen pathspec set would violate the port runbook's execution-base stop rule. | Kept the 11-row native-harness inventory frozen and specified a separate amendment-cycle manifest with 34 non-overlapping 0.146 rows. |
| DR-A3 | P1 | FIXED | The verification section called nonexistent `port_contract.py check` syntax. | Replaced it with executable `validate --stage classification`, `verify-source`, and `render --check` commands for each manifest. |
| DR-A4 | P1 | FIXED | The original natural-language canary could invoke a mutating skill and did not define a parseable result. | Made it route-only, prohibited tools and skill execution, required JSON Schema output, and assigned exact canonical route IDs. |
| DR-A5 | P1 | FIXED | The canary ran before U9/U10, so it could not prove the final Saga descriptions and resume boundary. | Split U8 contract freeze from U11 execution and required the final canary after Saga source and targeted tests stabilize. |
| DR-A6 | P1 | SUPERSEDED | A temporary `CODEX_HOME` had no authentication boundary and risked credential copying or a silent default-profile fallback. | The operator explicitly replaced isolated authentication with a bounded normal-profile refresh; credentials remain untouched. |
| DR-A7 | P2 | FIXED | The plugin refresh and model invocation were not reproducible. | Named the marketplace, all ten plugin refreshes, Codex/model/effort flags, one invocation per prompt, receipt fields, and native marketplace restoration. |
| DR-A8 | P2 | FIXED | A credential or source stop could have been recorded as a passing canary substitute. | Required all 17 rows to pass for source-ready status; source or normal-profile refresh/restoration failure leaves U11 incomplete. |
| DR-A9 | P2 | FIXED | Saga cleanup lacked a measurable baseline and exact resume/hook assertions. | Recorded 20 blocking-question files, 16 `ToolSearch` files, and 15 Claude-agent-vocabulary files, plus explicit native-first resume and advisory-hook assertions. |
| DR-A10 | P2 | FIXED | Amendment evidence could overwrite U1-U7 receipts or silently change unrelated plugin versions. | Preserved earlier receipts, limited version changes to final changed bytes, and required approval before any non-Saga plugin edit or version decision. |
| DR-A11 | P2 | FIXED | The source comparison named tags but not immutable commits. | Recorded the peeled 0.145 and 0.146 commits and required source verification against them. |
| DR-A12 | P3 | FIXED | The plan could duplicate the amendment manifest's inventory indefinitely. | Limited the feature-boundary list to `init` bootstrap input and made the generated manifest authoritative after creation. |
| DR-A13 | P1 | FIXED | The first amendment draft froze only four additional source files even though the deep 0.145-to-0.146 code review found 41 plugin-facing changed rows in the selected feature boundaries. | Assigned the seven already-classified rows to the frozen manifest and required a 34-row amendment inventory spanning skill rendering/resources, plugin loading, native tools/models, history/resume, and hooks. |
| DR-A14 | P2 | FIXED | The existing manifest's base is the parent of the 0.145 release tag, while the plan described an exact tag-to-tag comparison. | Proved the parent-to-tag difference is only `codex-rs/Cargo.toml` and required byte equivalence for all 41 selected plugin-facing paths. |
| DR-A15 | P2 | FIXED | Additional 0.146 features could invite unnecessary rewrites of manifests, agent synchronization, cache lookup, domain HTTP clients, or dormant lease code. | Added explicit retain/defer decisions and kept non-Saga changes behind reproducible failure plus operator approval. |
| DR-A16 | P1 | FIXED | The 0.145 and 0.146 release tags are siblings, so the exact 0.145 tag cannot satisfy the port tool's required ancestor relationship. | With operator approval, retained the exact tag as human comparison authority and used the byte-equivalent shared parent as the amendment's machine-contract base. |
| DR-A17 | P2 | FIXED | The separately authenticated canary added an unnecessary second-login barrier after the normal profile was already authenticated. | At operator direction, use the normal profile, bound mutation to the Infiquetra marketplace and ten plugins, restore the original Git source/ref, and leave credentials, trust, sessions, agents, and unrelated plugins untouched. |

## Evidence checked

- Mandatory port runbook version 4, including frozen-inventory, bounded repair, and stop rules. The
  operator explicitly overrode the cycle's isolated-authentication choice for U11.
- Existing `codex-0146-native-harness` manifest and generated classification.
- OpenAI Codex source at peeled commits
  `25af12f7e61572b0bc18ddb1008be543b91519b0` and
  `e363b08c9175ac1cbe5893615dd2cb9ddf95043b`.
- Live Codex 0.146 `exec`, plugin-marketplace, and plugin-install command schemas.
- Current ten-plugin marketplace inventory and 49-skill catalog.
- Active Saga instruction inventory for stale interaction and agent vocabulary.
- Full 1,167-file tag diff followed by the 41-row plugin-facing feature inventory: seven rows are
  already frozen and 34 belong to the amendment cycle.
- Saga's active hook declaration, Fleet's cache-resolution contract, Verified Workflows agent
  synchronization, and bundled domain HTTP clients.

The formal SDLC issue rubric is not applicable to this implementation plan. The readiness review
used the plan criteria from `saga:doc-review`; no external reviewer panel was requested.

## Residual execution risks

- Model routing is probabilistic. The fixed model, low effort, one-shot structured rows, and
  description-only one-retry limit bound that risk without building a plugin selector.
- The normal-profile marketplace source must be restored after the canary; restoration failure
  blocks U11.
- A non-Saga routing failure may reveal real catalog overlap. The plan reports it and stops rather
  than broadening this amendment.

## Approval boundary

Approval covers U8-U11 source changes and the bounded normal-profile marketplace/plugin refresh
described in the plan. It does not authorize commit, push, PR, merge, publication, profile
synchronization, trusted-hook mutation, restart, issue creation, or deployment.
