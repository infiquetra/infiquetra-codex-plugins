# Doc Review — Codex 0.147.0 Alignment Requirements

**Target:** `docs/brainstorms/2026-08-08-codex-0147-alignment-requirements.md`
**Reviewed revision:** working tree (untracked at review time)
**Date:** 2026-08-08
**Reviewers:** Claude (host, owns the verdict) + Codex `gpt-5.6-sol` max (advisory second opinion)
**Blocked status:** not blocked — the single escalated question was resolved by the operator

## Verdict

The document is implementation-ready except for one operator decision. Both passes found the same
class of defect: the upstream analysis was sound, and the requirements under-specified this
repository's own gates and proof contracts.

The most consequential finding overturned a design decision the operator had already approved. The
"three independent facts" model was technically wrong — only the catalog's `multi_agent_version` is a
source fact, and the other two values are derived from it by rules Codex owns. The requirements now
model one raw fact plus two versioned projections. The operator's underlying intent (stop conflating
what Codex reports with what this repository decided) is preserved; the mechanism changed.

## Findings

| ID | Priority | Source | Location | Status |
|---|---|---|---|---|
| D1 | P1 | Codex | Summary, R1–R3 | Fixed — one raw fact plus two derived projections |
| D2 | P1 | Codex | R2 / R8 consumers | Fixed — added R4 (schema revision decision), widened R10 |
| D3 | P1 | Claude | AGENTS.md gate absent | Fixed — added R23 (port manifest classification) |
| D4 | P1 | Claude | packaging absent | Fixed — added R25, R26 |
| D5 | P1 | Codex | R15 environment permissions | Resolved — operator kept it in-round with R19's stop rule |
| D6 | P1 | Codex | R14 / AE3 | Fixed — split host-installed from executor-backed |
| D7 | P1 | Codex | R10 environment identity | Fixed — durable tuple, or explicit harness authorization |
| D8 | P1 | Codex | developer-instruction decision | Fixed — full key path, narrowed rationale, added R8 |
| D9 | P1 | Codex | R13 tool absence | Fixed — schema evidence required, added R16 |
| D10 | P1 | Codex | R17–R18 topology | Fixed — pinned SHAs and common base in R24 |
| D11 | P1 | Codex | Units 7–8 missing | Fixed — added R20, R21 |
| D12 | P1 | Codex | R11 falsifies history | Fixed (partial) — disposition framework added; file list dismissed |
| D13 | P2 | Codex | Sources precision | Fixed |
| D14 | P2 | Codex | Luna oracle undefined | Fixed — added R17, decoupled per-profile gating |
| D15 | P2 | Codex | R9 reviewer identity | Fixed — negative control framing in R11 |
| D16 | P2 | Codex | Scope boundary conflicts | Fixed |
| D17 | P2 | Codex | R19 release versions | Fixed — named plugins in R25 |
| D18 | P2 | Claude | R1 producer unnamed | Superseded by the D1 rewrite |

## Claude adjudication of advisory findings

Every Codex finding was verified against Codex source or this repository before adoption.

**Kept in full (13).** D1, D2, D6, D7, D8, D9, D11, D13, D14, D15, D16, D17, and the topology half of
D10. Independently verified: the derivation rules at `multi_agents_common.rs:36-42` and
`spec_plan.rs:533-543`; the `features.multi_agent_v2` config path; the merge base
`95637f7056835fea66bdd0044414af480fc0fd74`; the two 0.146.1-only commits; the provider-registry
rejection in `spawn.rs`; the schema `const` at `schema-r3.json:74`; and the `{1, 2}` schema-version
constraint at `port_contract.py:379`.

**Downgraded (1).** D12 — the disposition framework is correct and adopted, because rewriting the
dated CHANGELOG entry would falsify an accurate 0.146 record. Codex additionally named
`plugins/verified-workflows/PORTABILITY.md`, `plugins/saga/references/operator-choice.md`, and the
port runbook as carrying Luna claims. A grep of all three found **no Luna references**. That portion
is dismissed as unverified.

**Corrected against Codex (1).** Codex reported the two 0.146.1-only commits as "two release-branch
backports." They are one behavioral backport (`7558bede75dd`) plus the release commit
(`79b4f03d3596`) — Codex itself made this correction in D10 against my original wording, and the
final text reflects the verified split.

**Escalated, then resolved (1).** D5 — Codex argued the turn-environment permission work needs its own
tracked outcome with a blocking stop rule, and that a native Codex defect there must halt the round.
The operator had already declined a separate outcome, so rather than overturn that on a reviewer's
say-so it was escalated as a blocking question. The operator resolved it: the work **stays in-round**,
carrying R19's stop rule. The case matrix and stop rule were adopted regardless, since they improve
the requirement under either scoping.

## Applied fixes

Requirements grew from R1–R16 to R1–R26 and acceptance examples from AE4 to AE5. Substantive changes:

- Summary and Key Decisions rewritten around one raw fact plus two derived projections.
- New requirement groups for the developer-instruction contract and positive discovery proof.
- Per-profile canary gating decoupled, so a monitoring failure no longer drags a passing scanner back
  to Terra.
- Permission drift explicitly excluded from model-fallback remediation, since the permission path is
  model-independent.
- Four hard version gates now named, up from three.
- Scope boundaries corrected: workspace-local staging permitted, user-profile installation forbidden,
  and the portable-migration rationale changed from "would lose profiles" to "adds no capability."

## Residual risk

The two live canaries and the permission case matrix remain unrun; every claim about 0.147.0 runtime
behavior in this document is source-derived. That is the intended state for a requirements document,
and R15 through R19 exist precisely to convert it into evidence.

Neither reviewer executed a test suite or modified repository source outside this document.
