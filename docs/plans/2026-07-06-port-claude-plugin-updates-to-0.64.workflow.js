// ===========================================================================
// port-claude-plugin-updates-to-0.64 -- emitted Claude Code workflow harness.
// AUTO-EMITTED from a structured execution-spec by execution_spec.py.
// CONTROL FLOW ONLY -- every agent reads the plan as its authoritative spec.
// Per-unit {model, effort} tiers (R2(b)); R3 pilot/fan-out same-tier +
// R10 enumerated-target reconciliation enforced at emit time.
// ===========================================================================

export const meta = {
  name: "port-claude-plugin-updates-to-0.64",
  description: "Selective re-implementation of infiquetra-claude-plugins b30e0f2..9470edc into Codex surfaces per docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md",
}

function __gate(result, opts) {
  const unitId = opts.unitId || "unknown";

  function isEmptyOrAbsent(val) {
    if (val === null || val === undefined) return true;
    if (typeof val === 'string') return val.trim() === '';
    if (Array.isArray(val)) return val.length === 0;
    if (val instanceof Map || val instanceof Set) return val.size === 0;
    if (typeof val === 'object') return Object.keys(val).length === 0;
    return false;
  }

  function parseResult(val) {
    if (typeof val === 'string') {
      let s = val.trim();
      if (s.startsWith('```')) {
        const lines = s.split('\n');
        if (lines.length >= 2) {
          if (lines[0].startsWith('```')) {
            lines.shift();
          }
          if (lines.length && lines[lines.length - 1].trim() === '```') {
            lines.pop();
          }
          s = lines.join('\n').trim();
        }
      }
      if (s.startsWith('{') || s.startsWith('[')) {
        try {
          return JSON.parse(s);
        } catch (e) {
          // ignore
        }
      }
    }
    return val;
  }

  if (opts.expectsOutput && isEmptyOrAbsent(result)) {
    throw new Error(
      `missing-output: Unit ${unitId} expected structured output but received none or empty.`
    );
  }

  if (typeof result === 'string') {
    let s = result.trim();
    if (s.startsWith('```')) {
      const lines = s.split('\n');
      if (lines.length >= 2) {
        if (lines[0].startsWith('```')) {
          lines.shift();
        }
        if (lines.length && lines[lines.length - 1].trim() === '```') {
          lines.pop();
        }
        s = lines.join('\n').trim();
      }
    }
    if (s.startsWith('{') || s.startsWith('[')) {
      try {
        JSON.parse(s);
      } catch (e) {
        throw new Error(
          `malformed-output: Unit ${unitId} output is a structurally truncated JSON: ${e.message}`
        );
      }
    }
  }

  let targetCount = null;
  if (opts.targets !== undefined && opts.targets !== null) {
    if (typeof opts.targets === 'number') {
      targetCount = opts.targets;
    } else if (Array.isArray(opts.targets)) {
      targetCount = opts.targets.length;
    }
  }

  if (targetCount !== null) {
    const parsed = parseResult(result);
    let producedCount = 0;
    if (parsed !== null && parsed !== undefined) {
      if (Array.isArray(parsed)) {
        producedCount = parsed.length;
      } else if (parsed instanceof Map || parsed instanceof Set) {
        producedCount = parsed.size;
      } else if (typeof parsed === 'object') {
        producedCount = Object.keys(parsed).length;
      } else {
        producedCount = isEmptyOrAbsent(parsed) ? 0 : 1;
      }
    }
    if (producedCount < targetCount) {
      const shortfall = targetCount - producedCount;
      throw new Error(
        `missing-output: Unit ${unitId} produced fewer items than expected. ` +
        `Expected ${targetCount}, produced ${producedCount}. Shortfall: ${shortfall}.`
      );
    }
  }

  if (opts.returns && opts.returns.length > 0) {
    const parsed = parseResult(result);
    if (parsed === null || parsed === undefined || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(
        `missing-output: Unit ${unitId} result is not a structured dictionary. ` +
        `Missing required keys: ${opts.returns.join(', ')}.`
      );
    }
    const missing = opts.returns.filter(
      k => !(k in parsed) || parsed[k] === null || parsed[k] === undefined
    );
    if (missing.length > 0) {
      throw new Error(
        `missing-output: Unit ${unitId} output is missing required keys: ${missing.join(', ')}.`
      );
    }
  }

  return result;
}

// ---- U1: baseline-freeze-classification ----
const U1 = await agent(
  "U1: Freeze the source baseline and write the 0.64 drift-classification artifact (after the operator commits the pending discord-identity-assets 0.2.0 work). Read the plan at docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md as your authoritative spec.\n\nReturn a structured result with keys: status, summary, files_changed.",
  { label: "baseline-freeze-classification", model: "sonnet", effort: "medium" },
)
__gate(U1, { unitId: "U1", expectsOutput: true, returns: ["status", "summary", "files_changed"] })

// ---- U2: fleet-core-plugin-and-shim ----
// depends_on: U1 (barrier)
// ---- U6: ship-ceremony-branch-refresh-telemetry ----
// depends_on: U1 (barrier)
const [U2, U6] = await parallel([
  () =>
    agent(
      "U2: Create the Codex fleet-core plugin (tier palette, resolver, models.json dual palette, effort rider, retry_backoff) with the Codex-native shim resolution ladder, vendor the shim into consuming plugins, and add the drift test. Read the plan at docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md as your authoritative spec.\n\nReturn a structured result with keys: status, summary, files_changed, tests_run.",
      { label: "fleet-core-plugin-and-shim", model: "opus", effort: "high" },
    ),
  () =>
    agent(
      "U6: Port ship_ceremony.py with its follow-up fixes, the saga branch-refresh-on-save fix, gate-divergence telemetry, and the run-fact ledger. Read the plan at docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md as your authoritative spec.\n\nReturn a structured result with keys: status, summary, files_changed, tests_run.",
      { label: "ship-ceremony-branch-refresh-telemetry", model: "sonnet", effort: "medium" },
    ),
])
__gate(U2, { unitId: "U2", expectsOutput: true, returns: ["status", "summary", "files_changed", "tests_run"] })
__gate(U6, { unitId: "U6", expectsOutput: true, returns: ["status", "summary", "files_changed", "tests_run"] })

// ---- U3: tier-effort-integration ----
// depends_on: U2 (barrier)
// ---- U4: board-autonomy-and-issue-verbs ----
// depends_on: U1, U2 (barrier)
const [U3, U4] = await parallel([
  () =>
    agent(
      "U3: Route saga execution_spec tier merge/validation, team_emitter effort cascade, and the team-execution TOML roster + validator hints through the fleet-core palette. Read the plan at docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md as your authoritative spec.\n\nReturn a structured result with keys: status, summary, files_changed, tests_run.",
      { label: "tier-effort-integration", model: "opus", effort: "high" },
    ),
  () =>
    agent(
      "U4: Port the certificate-gated board-write loop (reversibility certificate, outcome board-sync, board_progression, schema-resolved status) and the paired mission-control issue-write verbs. Read the plan at docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md as your authoritative spec.\n\nReturn a structured result with keys: status, summary, files_changed, tests_run.",
      { label: "board-autonomy-and-issue-verbs", model: "opus", effort: "high" },
    ),
])
__gate(U3, { unitId: "U3", expectsOutput: true, returns: ["status", "summary", "files_changed", "tests_run"] })
__gate(U4, { unitId: "U4", expectsOutput: true, returns: ["status", "summary", "files_changed", "tests_run"] })

// ---- U5: outcome-reconcile-from-objective ----
// depends_on: U4 (barrier)
// ---- U7: evidence-manifests-verify-panels ----
// depends_on: U3 (barrier)
// ---- U9: mission-control-sync-unifi-retry ----
// depends_on: U2, U4 (barrier)
const [U5, U7, U9] = await parallel([
  () =>
    agent(
      "U5: Port board-vs-saga reconciliation on resume and /outcome start --from-objective DAG seeding. Read the plan at docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md as your authoritative spec.\n\nReturn a structured result with keys: status, summary, files_changed, tests_run.",
      { label: "outcome-reconcile-from-objective", model: "sonnet", effort: "medium" },
    ),
  () =>
    agent(
      "U7: Port provenance manifests (verified vs adjudicated), manifest store/reader, completeness-gate updates, and verify-panel consensus recomputation over reporting verifiers. Read the plan at docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md as your authoritative spec.\n\nReturn a structured result with keys: status, summary, files_changed, tests_run.",
      { label: "evidence-manifests-verify-panels", model: "opus", effort: "high" },
    ),
  () =>
    agent(
      "U9: Behaviorally sync vendored mission-control (operations rename, create-prepared recovery, contents-API PUT fix, executor-profile lint) and adopt shared retry in the unifi clients. Read the plan at docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md as your authoritative spec.\n\nReturn a structured result with keys: status, summary, files_changed, tests_run.",
      { label: "mission-control-sync-unifi-retry", model: "sonnet", effort: "medium" },
    ),
])
__gate(U5, { unitId: "U5", expectsOutput: true, returns: ["status", "summary", "files_changed", "tests_run"] })
__gate(U7, { unitId: "U7", expectsOutput: true, returns: ["status", "summary", "files_changed", "tests_run"] })
__gate(U9, { unitId: "U9", expectsOutput: true, returns: ["status", "summary", "files_changed", "tests_run"] })

// ---- U8: engine-routing-team-protocol ----
// depends_on: U3, U7 (barrier)
const U8 = await agent(
  "U8: Port engine capability routing gated to Codex backend truth, artifact-pointer passing, consensus hardening, and the resident-worker / evidence-absence protocol content adapted to serial fallback. Read the plan at docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md as your authoritative spec.\n\nReturn a structured result with keys: status, summary, files_changed, tests_run.",
  { label: "engine-routing-team-protocol", model: "opus", effort: "high" },
)
__gate(U8, { unitId: "U8", expectsOutput: true, returns: ["status", "summary", "files_changed", "tests_run"] })

// ---- U10: manifests-inventory-final-validation ----
// depends_on: U2, U3, U4, U5, U6, U7, U8, U9 (barrier)
const U10 = await agent(
  "U10: Align manifests, README, portability docs, validation inventory, and changelogs with the shipped surface; run full validation (validate_codex_plugins.py + pytest) and report. Read the plan at docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md as your authoritative spec.\n\nReturn a structured result with keys: status, summary, files_changed, validation_results.",
  { label: "manifests-inventory-final-validation", model: "sonnet", effort: "medium" },
)
__gate(U10, { unitId: "U10", expectsOutput: true, returns: ["status", "summary", "files_changed", "validation_results"] })
