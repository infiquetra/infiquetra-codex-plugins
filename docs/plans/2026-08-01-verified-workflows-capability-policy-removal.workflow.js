// ===========================================================================
// verified-workflows-capability-policy-removal -- emitted Claude Code workflow harness.
// AUTO-EMITTED from a structured execution-spec by execution_spec.py.
// CONTROL FLOW ONLY -- every agent reads the plan as its authoritative spec.
// Per-unit {model, effort} tiers (R2(b)); R3 pilot/fan-out same-tier +
// R10 enumerated-target reconciliation enforced at emit time.
// ===========================================================================

export const meta = {
  name: "verified-workflows-capability-policy-removal",
  description: "Remove Verified Workflows' unenforceable capability policy (issue 71): delete the per-role and per-profile capability declarations and the compiler refusals built on them, keep the post-hoc evidence layer, and correct the documentation and journal record.",
}
const settlement = {"casualty_threshold_percent":0,"dispatch_id":"workflow:e1a35bc621b6e6246b3451d2","driver":{"invocation_id":null,"units":[{"return_keys":[{"deliverable":"return:status","result_key":"status"},{"deliverable":"return:files_changed","result_key":"files_changed"},{"deliverable":"return:checks_run","result_key":"checks_run"},{"deliverable":"return:notes","result_key":"notes"}],"settlement_unit_id":"U1","workflow_unit_id":"U1"},{"return_keys":[{"deliverable":"return:status","result_key":"status"},{"deliverable":"return:files_changed","result_key":"files_changed"},{"deliverable":"return:checks_run","result_key":"checks_run"},{"deliverable":"return:notes","result_key":"notes"}],"settlement_unit_id":"U3","workflow_unit_id":"U3"},{"return_keys":[{"deliverable":"return:status","result_key":"status"},{"deliverable":"return:files_changed","result_key":"files_changed"},{"deliverable":"return:checks_run","result_key":"checks_run"},{"deliverable":"return:notes","result_key":"notes"},{"deliverable":"return:red_first_reproduction","result_key":"red_first_reproduction"}],"settlement_unit_id":"U2","workflow_unit_id":"U2"},{"return_keys":[{"deliverable":"return:status","result_key":"status"},{"deliverable":"return:files_changed","result_key":"files_changed"},{"deliverable":"return:checks_run","result_key":"checks_run"},{"deliverable":"return:notes","result_key":"notes"}],"settlement_unit_id":"U4","workflow_unit_id":"U4"},{"return_keys":[{"deliverable":"return:status","result_key":"status"},{"deliverable":"return:files_changed","result_key":"files_changed"},{"deliverable":"return:checks_run","result_key":"checks_run"},{"deliverable":"return:notes","result_key":"notes"}],"settlement_unit_id":"U5","workflow_unit_id":"U5"},{"return_keys":[{"deliverable":"return:status","result_key":"status"},{"deliverable":"return:files_changed","result_key":"files_changed"},{"deliverable":"return:checks_run","result_key":"checks_run"},{"deliverable":"return:notes","result_key":"notes"},{"deliverable":"return:u8_gate_status","result_key":"u8_gate_status"}],"settlement_unit_id":"U6","workflow_unit_id":"U6"},{"return_keys":[{"deliverable":"return:status","result_key":"status"},{"deliverable":"return:files_changed","result_key":"files_changed"},{"deliverable":"return:checks_run","result_key":"checks_run"},{"deliverable":"return:notes","result_key":"notes"},{"deliverable":"return:gate_results","result_key":"gate_results"}],"settlement_unit_id":"U7","workflow_unit_id":"U7"}]},"max_attempts":3,"schema":"dispatch_settlement.v1","site":"workflow","units":[{"deliverables":["structured-result","return:status","return:files_changed","return:checks_run","return:notes"],"idempotency_key":"workflow:e1a35bc621b6e6246b3451d2:U1","unit_id":"U1"},{"deliverables":["structured-result","return:status","return:files_changed","return:checks_run","return:notes"],"idempotency_key":"workflow:e1a35bc621b6e6246b3451d2:U3","unit_id":"U3"},{"deliverables":["structured-result","return:status","return:files_changed","return:checks_run","return:notes","return:red_first_reproduction"],"idempotency_key":"workflow:e1a35bc621b6e6246b3451d2:U2","unit_id":"U2"},{"deliverables":["structured-result","return:status","return:files_changed","return:checks_run","return:notes"],"idempotency_key":"workflow:e1a35bc621b6e6246b3451d2:U4","unit_id":"U4"},{"deliverables":["structured-result","return:status","return:files_changed","return:checks_run","return:notes"],"idempotency_key":"workflow:e1a35bc621b6e6246b3451d2:U5","unit_id":"U5"},{"deliverables":["structured-result","return:status","return:files_changed","return:checks_run","return:notes","return:u8_gate_status"],"idempotency_key":"workflow:e1a35bc621b6e6246b3451d2:U6","unit_id":"U6"},{"deliverables":["structured-result","return:status","return:files_changed","return:checks_run","return:notes","return:gate_results"],"idempotency_key":"workflow:e1a35bc621b6e6246b3451d2:U7","unit_id":"U7"}]}

const REPO = "/Users/jefcox/workspace/infiquetra/infiquetra-codex-plugins"

const __pulledCords = []

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
          // fall through to embedded-JSON extraction
        }
      }
      // Extract an embedded JSON value when the agent prepends conversational prose
      // before the object (sonnet/opus routinely add a "looks good, tests pass" preamble
      // ahead of the return object). Try object first, then array.
      const pairs = [['{', '}'], ['[', ']']];
      for (let i = 0; i < pairs.length; i++) {
        const start = s.indexOf(pairs[i][0]);
        const end = s.lastIndexOf(pairs[i][1]);
        if (start !== -1 && end > start) {
          try {
            return JSON.parse(s.slice(start, end + 1));
          } catch (e) {
            // try the next delimiter pair
          }
        }
      }
    }
    return val;
  }

  // #364 R7: pull_cord -- the worker-initiated out-of-depth disposition, a valid alternative
  // to the return contract (distinct from success and from the missing/malformed throws).
  // Cords batch into __pulledCords for ONE coordinator escalation entry (R8); the unit is
  // never marked complete because the batched check fails the run before it returns.
  const cordProbe = parseResult(result);
  if (cordProbe && typeof cordProbe === 'object' && !Array.isArray(cordProbe)
      && typeof cordProbe.pull_cord === 'string' && cordProbe.pull_cord.trim() !== '') {
    __pulledCords.push({ unit: unitId, reason: cordProbe.pull_cord.trim(),
                         proposal: opts.cordProposal || null });
    return result;
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

function __is429(x) {
  if (x === null || x === undefined) return false;
  if (typeof x === 'number') return x === 429;
  if (typeof x === 'string') return /(^|[^0-9])429([^0-9]|$)/.test(x) || /rate[\s_-]?limit/i.test(x);
  var status = x.status || x.statusCode || x.status_code || x.code;
  if (status === 429 || status === '429') return true;
  if (x.rateLimited === true || x.rate_limited === true) return true;
  var msg = x.message || x.error || '';
  return typeof msg === 'string' && (/(^|[^0-9])429([^0-9]|$)/.test(msg) || /rate[\s_-]?limit/i.test(msg));
}

function __retryAfterMs(signal) {
  if (signal === null || typeof signal !== 'object') return null;
  if (typeof signal.retryAfterMs === 'number') return signal.retryAfterMs;
  if (typeof signal.retryAfter === 'number') return signal.retryAfter * 1000;
  if (typeof signal.retry_after === 'number') return signal.retry_after * 1000;
  return null;
}

function __retryBackoffMs(attempt, baseMs, maxMs, retryAfterMs) {
  if (typeof retryAfterMs === 'number' && retryAfterMs > 0) {
    return Math.min(retryAfterMs, maxMs);
  }
  return Math.min(baseMs * Math.pow(2, attempt - 1), maxMs);
}

async function __retry(thunk, opts) {
  var o = opts || {};
  var maxAttempts = o.maxAttempts || 3;
  var baseMs = o.baseMs || 1000;
  var maxMs = o.maxMs || 60000;
  var sleep = o.sleep || function (ms) {
    return new Promise(function (r) {
      if (typeof setTimeout === 'function') { setTimeout(r, ms); } else { r(); }
    });
  };
  var attempt = 0;
  while (true) {
    attempt++;
    var result;
    var threw = false;
    var caught = null;
    try {
      result = await thunk();
    } catch (err) {
      threw = true;
      caught = err;
    }
    var signal = threw ? caught : result;
    if (__is429(signal) && attempt < maxAttempts) {
      await sleep(__retryBackoffMs(attempt, baseMs, maxMs, __retryAfterMs(signal)));
      continue;
    }
    if (threw) throw caught;
    return result;
  }
}

const __advisories = []
function __logAdvisory(unitId, reported) {
  var items = []
  for (var i = 0; i < reported.length; i++) {
    var adv = reported[i].advisory_corrections || []
    for (var j = 0; j < adv.length; j++) items.push(adv[j])
  }
  if (items.length > 0) {
    __advisories.push({ unit: unitId, corrections: items })
    log(`verify panel over ${unitId}: deliverable UPHELD with ${items.length} advisory correction(s) (narrative/rationale only, non-gating): ` +
        items.map((a) => String(typeof a === "string" ? a : (a.claim || a.id || JSON.stringify(a))).slice(0, 180)).join(" | "))
  }
  return items
}

function __verifierPrompt(basePrompt, unitResult) {
  var rendered;
  try {
    rendered = JSON.stringify(unitResult, null, 2);
  } catch (err) {
    rendered = String(unitResult);
  }
  var repoLine = (typeof REPO === "string")
    ? `PRIMARY REPO PATH: ${REPO}`
    : "PRIMARY REPO PATH: not declared by this workflow";
  return `${basePrompt}

VERIFIER VISIBILITY PROTOCOL (#519):
${repoLine}
- You run in a disposable verifier worktree. Before judging file content, capture the primary
  checkout SHA with: git -C <primary repo path> rev-parse HEAD
- Materialize that exact SHA in your verifier worktree with: git checkout <sha> -- .
- If the unit result names uncommitted files or diffs, inspect the primary checkout read-only
  with git -C <primary repo path> status --short and git -C <primary repo path> diff / diff --
  <path>. For named untracked output files, read the primary checkout path directly; never mutate
  the primary checkout.
- Return examined_sha as the SHA you actually materialized or inspected. If you cannot see enough
  evidence to judge, return a refuted_deliverable entry explaining the visibility gap; do not emit
  prose-only "nothing to verify" output.

VERDICT CONTRACT — two separate buckets. Read this before you write anything.

The unit result you are given contains BOTH a deliverable and a narrative. Sort every disagreement
you find into exactly one of these. Getting the bucket right matters more than finding a lot.

\`refuted_deliverable\` — GATING. A finding belongs here only if the unit's actual WORK is wrong:
- A changed file is wrong, incomplete, or breaks something.
- Required behavior is missing, or behavior the unit was told to preserve was destroyed.
- A test is missing, wrong, asserts nothing, or does not test what it claims.
- A claim in \`checks_run\` is FALSE — the command does not actually pass, or was not actually run,
  or its reported result does not reproduce. Re-run the commands and check.
- The unit says \`status: "done"\` but the work is not done.
- You could not see enough to judge (visibility gap).
A non-empty \`refuted_deliverable\` from a majority of the panel KILLS the unit and HALTS the whole
workflow. Put a finding here only if you would defend stopping the run over it.

\`advisory_corrections\` — NON-GATING. A finding belongs here if the WORK is right but the unit's
own account of it is wrong or misleading:
- Its explanation of WHY something happened is factually incorrect.
- It misattributes a change to the wrong function, file, or line.
- It mischaracterizes a mechanism, or states a rationale that does not hold.
- Its advice to a downstream unit rests on a wrong premise.
These are recorded and handed to the driver. They do NOT stop the run. Report them fully and
precisely — a wrong premise passed downstream causes real damage later, so this bucket is
genuinely valuable, not a consolation prize.

The test: if the unit's code, tests, and check results are all sound, then NOTHING goes in
\`refuted_deliverable\`, no matter how wrong its prose is. Prose errors are advisory. Full stop.

Both keys are REQUIRED and must be arrays. Use \`[]\` for an empty bucket — never omit either one.

UNIT RESULT INPUT (structured evidence — the \`notes\` field is the unit's NARRATIVE, judge it
under \`advisory_corrections\`; the changed files, tests, and \`checks_run\` are the DELIVERABLE):
${rendered}`;
}

// ---- U1: strip-capability-declarations ----
// escalation: HALT if the registry turns out to contain a role whose kind is not agent-lens, or if dropping allowed_profiles breaks a consumer the plan did not name.
// ---- U3: undeclared-paths-become-findings ----
// escalation: HALT if the synthesized finding cannot satisfy the closed field set in \`_finding\` without relaxing an unrelated validation.
// concurrency chunk 1/2 (max_concurrent=1)
const [U1] = await parallel([
  () =>
    __retry(() => agent(
      "Implement Unit U1 of the plan at `docs/plans/2026-08-01-verified-workflows-capability-policy-removal-plan.md` in the repository at REPO. READ the plan's `### U1` section first and treat it as authoritative \u2014 it is more precise than this prompt, and its cited line numbers were verified against source during a doc-review.\n\nGOAL: the role registry stops declaring capability, and role-to-profile selection stops being constrained.\n\nWHAT TO DO:\n1. In `plugins/verified-workflows/config/role-registry.yaml`, delete the four-key `boundaries` mapping and the `allowed_profiles` key from all 28 role entries. Every role is `kind: agent-lens`, so there is a single registry parse path. Keep `default_profile`.\n2. In `plugins/verified-workflows/scripts/render_codex_agents.py`, remove: the boundary parse and equality assert (~`:642-658`), the profile-transition check (~`:640-641`), the `allowed_profiles` membership test inside `resolve_role` (~`:960-964`), the `allowed_profiles` / `workspace_cap` / `external_cap` fields on `RoleSpec` (~`:345-347`), the `workspace` and `external` keys in `ROLE_PROFILE_POLICY` (~`:142-179`), and the dead `ROOT_ONLY_ACTIONS` tuple (~`:181-190`).\n3. The unreachable `_parse_deterministic` branch MUST be made consistent even though no registry entry reaches it: at ~`:790-806` it constructs a `RoleSpec` passing `allowed_profiles=()`, `workspace_cap=None`, and `external_cap=str(command[\"network\"])`. Drop those three keyword arguments. At ~`:830-840` its closed-key set accepts `allowed_profiles` and `boundaries`; drop those two names. Do NOT delete the branch itself \u2014 that is explicitly out of scope.\n4. `bundle_receipt()` at ~`:1187-1246` emits `allowed_profiles`, `workspace_cap`, and `external_cap` into its per-role projection (~`:1228`, ~`:1234-1235`). Drop those three keys from the receipt.\n5. One compiler line moves with this unit so the tree still compiles at the end of it: `plugins/verified-workflows/scripts/workflow_dispatch.py:325` must validate fallback profiles against `renderer.PROFILE_IDS` instead of the role's allowlist.\n6. Re-render the seven profile files (`plugins/verified-workflows/agents/*.toml`) because `registry_sha256` changes: `python3 plugins/verified-workflows/scripts/render_codex_agents.py --write --pretty` (confirm the exact write flag from the script's own `--help` first).\n\nPATTERNS: reuse the existing `_closed_keys` helper for narrowing accepted mappings, and keep the renderer's habit of raising `RoleRegistryError` naming the offending role id.\n\nTESTS to write or retarget in `plugins/verified-workflows/tests/test_role_registry.py` and `test_sync_codex_agents.py` \u2014 the plan's U1 `Test scenarios` list is the spec; implement all seven, including:\n- `RoleSpec` no longer exposes `workspace_cap` or `external_cap` (replaces the assertions at `test_role_registry.py:52-54`).\n- `resolve_role(\"git-integration-operator\", requested_profile=\"work_high\")` now succeeds where it previously raised.\n- `resolve_role` with no requested profile still falls back to `default_profile`.\n- A registry entry that still carries a `boundaries` key is REJECTED as an unknown field, so stale copies fail loudly.\n- A profile outside `PROFILE_IDS` still raises `RoleRegistryError` \u2014 retarget the existing `\"ultra\"` negative test at `test_role_registry.py:159` rather than deleting it.\n- A role whose `minimum_independence` disagrees with its category still raises.\n- `bundle_receipt()` emits no `allowed_profiles`, `workspace_cap`, or `external_cap` key.\n\nVERIFY before returning:\n- `python3 plugins/verified-workflows/scripts/render_codex_agents.py --check --pretty` exits 0.\n- `grep -n 'ROOT_ONLY_ACTIONS\\|external_mutation\\|workspace_cap' plugins/verified-workflows/scripts/render_codex_agents.py plugins/verified-workflows/config/role-registry.yaml` returns nothing.\n- `uv run python -m pytest -q plugins/verified-workflows/tests/test_role_registry.py plugins/verified-workflows/tests/test_sync_codex_agents.py tests/test_verified_workflows_agents.py` passes. Note `tests/test_verified_workflows_agents.py` asserts the receipt `claim` at `:165` and `:239` and lives OUTSIDE the plugin tests directory \u2014 you must run it.\n\nCONSTRAINTS:\n- Do NOT commit, branch, push, or open a pull request. The root session owns every git operation. Leave your work in the working tree.\n- Do NOT regenerate `docs/validation/verified-workflows-legacy-token-inventory.json` \u2014 Unit U7 owns that and is terminal by construction.\n- `python3 scripts/validate_codex_plugins.py` WILL fail until U7 runs, because the inventory digest is now stale. That is expected. Do not chase it and do not hand-edit the inventory.\n- Never touch `plugins/verified-workflows/CHANGELOG.md`, anything under `docs/plans/`, `docs/validation/codex-plugin-modernization-u3.json`, `.claude/`, or `.codex/`.\n\nRETURN a JSON object with keys `status` (\"done\" or \"blocked\"), `files_changed` (array of repo-relative paths), `checks_run` (array of the exact commands you ran with their pass/fail), and `notes` (anything the next unit must know, especially any deviation from the plan).\n\nRETURN CONTRACT (all tiers): your FINAL message MUST be ONLY a single JSON object with the keys status, files_changed, checks_run, notes -- no prose, no markdown code fences, no YAML, and nothing before or after the JSON. The workflow gate parses this final message as JSON and FAILS the unit if it is not a JSON object carrying these keys. Emit it as your last action even if the work is only partial (fill each key with what you have plus a short note).",
      { label: "strip-capability-declarations", model: "opus", effort: "high", schema: {"additionalProperties": true, "properties": {"checks_run": {}, "files_changed": {}, "notes": {}, "status": {}}, "required": ["status", "files_changed", "checks_run", "notes"], "type": "object"} },
    ), { unitId: "U1", maxAttempts: 3 }),
])
__gate(U1, { unitId: "U1", expectsOutput: true, returns: ["status", "files_changed", "checks_run", "notes"], cordProposal: "opus/high -> opus/xhigh (+1 effort rung)" })

// concurrency chunk 2/2 (max_concurrent=1)
const [U3] = await parallel([
  () =>
    __retry(() => agent(
      "Implement Unit U3 of the plan at `docs/plans/2026-08-01-verified-workflows-capability-policy-removal-plan.md` in the repository at REPO. READ the plan's `### U3` section AND its `KTD3` decision first \u2014 both are authoritative and more precise than this prompt.\n\nGOAL: an out-of-scope write is reported as evidence instead of discarding the entire typed result.\n\nWHAT TO DO: in `plugins/verified-workflows/scripts/result_contract.py` at ~`:243-253`, stop raising `ResultContractError` for undeclared changed paths. Compute the undeclared set exactly as today, then append ONE synthesized finding per undeclared path to the normalized `findings` list. Each synthesized finding must satisfy the closed field set enforced by `_finding` at ~`:92-122` and carry:\n- a deterministic `finding_id` derived from the path (same path always yields the same id),\n- `severity: \"P2\"`, `category: \"operations\"`, `scope_disposition: \"one-hop\"`, `resolved: false`, `hard_stop: false`,\n- `location` naming the undeclared path,\n- `impact` / `fix` / `validation` naming the declared write set the path fell outside of.\n\nThe validator SYNTHESIZES this finding. It must never be derived from agent-supplied content \u2014 that is KTD3 and it is the whole point: the agent is not trusted to self-report its own drift.\n\nEverything else in that function is untouched: the closed field set, the `no_change` consistency rule, and terminal-status membership all still apply and still raise.\n\nPATTERNS: `_finding` at `result_contract.py:92-122` for the exact field contract and its `defer`-plus-`hard_stop` prohibition; `SCOPE_DISPOSITIONS` and `FINDING_CATEGORIES` at `:38-50` for the accepted vocabulary. Do not invent new vocabulary.\n\nTESTS in `plugins/verified-workflows/tests/test_result_contract.py` \u2014 the plan's U3 `Test scenarios` list is the spec; implement all seven, including these three that are easy to miss:\n- An assignment declaring `writes: none` that reports changed paths yields findings rather than an exception. This is the live trap: the `git_operator()` fixture declares no writes, so a commit-reporting Git assignment hits this path.\n- Agent-supplied findings and synthesized findings coexist with no `finding_id` collision.\n- ONE agent-supplied `one-hop` finding PLUS ONE synthesized undeclared-path finding produces a hard stop. The cap at `gate_evaluator.py:310-313` filters the MERGED list of agent-supplied and root-adopted findings (built at `:307-309`), so it counts both sources together and also sets `approval_required` at `:314-318`. A synthesized-only test would miss this entirely.\n- Three undeclared paths yield three findings, and feeding them to `gate_evaluator` produces the \"more than one unplanned one-hop finding requires operator approval\" hard stop.\n- A malformed agent-supplied finding still raises `ResultContractError`, and `no_change: true` with a non-empty `changed_paths` still raises. Synthesis must not swallow unrelated contract violations.\n\nVERIFY before returning: `uv run python -m pytest -q plugins/verified-workflows/tests/test_result_contract.py` passes, and a result that previously raised `terminal result changed paths exceed assignment writes` now returns a normalized payload carrying the finding.\n\nCONSTRAINTS:\n- Do NOT commit, branch, push, or open a pull request. The root session owns every git operation.\n- Do NOT touch `render_codex_agents.py`, `workflow_dispatch.py`, or the role registry \u2014 other units own those and are running against the same tree.\n- Do NOT regenerate `docs/validation/verified-workflows-legacy-token-inventory.json`; Unit U7 owns it.\n- Never touch `plugins/verified-workflows/CHANGELOG.md`, anything under `docs/plans/`, `.claude/`, or `.codex/`.\n\nRETURN a JSON object with keys `status`, `files_changed`, `checks_run`, and `notes`.\n\nRETURN CONTRACT (all tiers): your FINAL message MUST be ONLY a single JSON object with the keys status, files_changed, checks_run, notes -- no prose, no markdown code fences, no YAML, and nothing before or after the JSON. The workflow gate parses this final message as JSON and FAILS the unit if it is not a JSON object carrying these keys. Emit it as your last action even if the work is only partial (fill each key with what you have plus a short note).",
      { label: "undeclared-paths-become-findings", model: "opus", effort: "high", schema: {"additionalProperties": true, "properties": {"checks_run": {}, "files_changed": {}, "notes": {}, "status": {}}, "required": ["status", "files_changed", "checks_run", "notes"], "type": "object"} },
    ), { unitId: "U3", maxAttempts: 3 }),
])
__gate(U3, { unitId: "U3", expectsOutput: true, returns: ["status", "files_changed", "checks_run", "notes"], cordProposal: "opus/high -> opus/xhigh (+1 effort rung)" })

// verify: refute-3 panel over U1 (pass_rule: majority;
// panel-level: refuted when the pass-rule threshold over REPORTING verifiers is met (quorum floor 2 of 3 declared; runtime-missing verifiers shrink the denominator))
const U1_verdicts = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U1 (strip-capability-declarations). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U1),
    { label: "strip-capability-declarations verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U1 } },
  ), { unitId: "U1", maxAttempts: 3 }),
])
const U1_verdicts_chunk_2 = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U1 (strip-capability-declarations). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U1),
    { label: "strip-capability-declarations verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U1 } },
  ), { unitId: "U1", maxAttempts: 3 }),
])
const U1_verdicts_chunk_3 = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U1 (strip-capability-declarations). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U1),
    { label: "strip-capability-declarations verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U1 } },
  ), { unitId: "U1", maxAttempts: 3 }),
])
U1_verdicts.push(...U1_verdicts_chunk_2, ...U1_verdicts_chunk_3)
const U1_valid_verifier_verdict = (v) => v != null && typeof v === "object" && Array.isArray(v.refuted_deliverable) && Array.isArray(v.advisory_corrections) && Array.isArray(v.upheld) && typeof v.verifier_identity === "string" && v.verifier_identity.length > 0 && Object.prototype.hasOwnProperty.call(v, "fallback_depth") && typeof v.examined_sha === "string" && v.examined_sha.length > 0
const U1_reported = U1_verdicts.filter((v) => U1_valid_verifier_verdict(v))
const U1_fallback_marker = (() => {
  const depthOf = (v) => {
    const raw = v.fallback_depth
    if (typeof raw === "boolean") return 0
    if (typeof raw === "string" && !/^-?\d+$/.test(raw.trim())) return 0
    const d = Math.trunc(Number(raw))
    return Number.isFinite(d) && d > 0 ? d : 0
  }
  const degraded = U1_reported.filter((v) => depthOf(v) > 0)
  if (degraded.length === 0) return ""
  return " — " + degraded.map((v) => `fallback tier ${depthOf(v)} (${v.verifier_identity || "unknown-verifier"})`).join("; ")
})()
const U1_missing_idx = U1_verdicts.map((v, i) => (!U1_valid_verifier_verdict(v) ? i + 1 : null)).filter((i) => i != null)
const U1_refute_count = U1_reported.filter((v) => v.refuted_deliverable.length > 0).length
const U1_threshold = Math.max(1, Math.ceil(U1_reported.length / 2))  // majority over reporters
const U1_refuted = U1_refute_count >= U1_threshold
__logAdvisory("U1", U1_reported)
if (U1_missing_idx.length > 0) {
  log(`verify panel over U1: ${U1_missing_idx.length}/3 verifier(s) missing (runtime-failure: #${U1_missing_idx.join(", #")}); verdict computed over ${U1_reported.length}/3` +
      (U1_reported.length < 2 ? " — UNDER-STRENGTH (quorum floor 2)" : ""))
}
if (U1_reported.length < 2) {
  throw new Error(`verifier-under-strength: Unit U1 reported ${U1_reported.length}/3 verifiers (quorum floor 2; missing #${U1_missing_idx.join(', #')})${U1_fallback_marker}`)
}
if (U1_refuted) {
  throw new Error(`verifier-disagreement: Unit U1 refuted by ${U1_refute_count}/${U1_reported.length} reporting verifiers (${U1_missing_idx.length} missing)${U1_fallback_marker}`)
}

// ---- U2: remove-compiler-refusals ----
// depends_on: U1 (barrier)
// escalation: STOP CONDITION — if a compiled publication contract still cannot dispatch after U1 and U2, then the Codex harness rather than the declared policy blocked the original Hermes push. Report status=blocked with the evidence and do NOT proceed; the whole change re-scopes.
const U2 = await agent(
  "Implement Unit U2 of the plan at `docs/plans/2026-08-01-verified-workflows-capability-policy-removal-plan.md` in the repository at REPO. Unit U1 has already landed in this working tree. READ the plan's `### U2` section first \u2014 it is authoritative and its line citations were verified during a doc-review.\n\nGOAL: the compiler stops refusing work it cannot actually prevent.\n\nWHAT TO DO in `plugins/verified-workflows/scripts/workflow_dispatch.py`:\n- Remove the read-only-cannot-declare-writes check (~`:312-313`).\n- Remove the `GIT_WORD_RE` rejection of Git commands on non-Git roles (~`:315-318`). `GIT_WORD_RE` has exactly one consumer \u2014 that refusal \u2014 so delete its definition at ~`:23` along with it.\n- Remove the fallback boundary-equality comparison (~`:330-336`).\n- KEEP the `git diff --name-only` completion requirement at ~`:319-322`. That is evidence production, not capability policy, and requirement R9 pins it. Deleting it is a defect.\n- KEEP the concurrent-writer overlap check at ~`:460-496` and the dependency-graph mechanics. R9 pins those too.\n\nTHEN, with the last consumers gone, remove the profile-level boundary vocabulary:\n- Drop the `workspace` and `external` keys from `PROFILE_POLICY` (~`:91-141` in `render_codex_agents.py`).\n- Drop the `workspace_boundary` and `external_boundary` fields from the profile-resolution dataclass (~`:413-414`).\n- TWO FURTHER SITES in `render_codex_agents.py` populate and emit those fields and MUST change in this same unit or the module breaks: `resolve_profile` constructs them from the policy dict at ~`:1091-1092`, and `bundle_receipt()` emits them into the per-profile projection at ~`:1205-1206`.\n- The class is named `ProfileResolution`, NOT `ResolvedProfile`. Grep for `ProfileResolution`.\n\nPATTERNS: the `git_operator()` fixture helper at `plugins/verified-workflows/tests/test_workflow_dispatch.py:69-77` for building assignment rows.\n\nTESTS in `plugins/verified-workflows/tests/test_workflow_dispatch.py` \u2014 the plan's U2 `Test scenarios` list is the spec; implement all six. The FIRST one is the red-first reproduction of the original production failure and is the most important thing in this unit:\n- A contract whose `git-integration-operator` row has a completion condition containing `git push`, `gh pr create`, AND `git diff --name-only` compiles and dispatches to that assignment.\n- A contract assigning `git-integration-operator` the `work_high` profile compiles, and the resulting assignment's model and effort resolve from `work_high` rather than `work_medium`.\n- A non-Git role whose completion condition mentions `git status` compiles instead of raising.\n- A `git-integration-operator` row whose completion OMITS `git diff --name-only` still raises \u2014 proving the retained evidence requirement did not go out with the refusals.\n- A fallback naming a profile outside `PROFILE_IDS` still raises; a fallback naming a valid profile with a different former boundary now compiles.\n- A cyclic `depends` graph and overlapping concurrent write sets both still raise.\n\nSTOP CONDITION \u2014 read this carefully. The premise of this entire change is that DECLARED POLICY, not the Codex harness, blocked a real publication push during the Hermes run. No run record for that failure exists locally, so the premise is inferred, not proven. The first test scenario above is the reproduction that tests it. If the publication contract still cannot compile and dispatch after U1 and U2 are in place, the harness was the blocker, the premise is wrong, and the work must stop for a re-scope rather than continue. In that case return `status: \"blocked\"` with the exact failure in `notes`, and set `red_first_reproduction` to a description of what actually happened.\n\nVERIFY before returning: `uv run python -m pytest -q plugins/verified-workflows/tests/test_workflow_dispatch.py` passes, `python3 plugins/verified-workflows/scripts/render_codex_agents.py --check --pretty` exits 0, and the previously-failing publication contract now produces an `Assignment` whose role is `git-integration-operator`.\n\nCORRECTED HANDOFF FROM U1 — U1's own notes contained four statements that its verify panel refuted and that the driving session then re-confirmed against source. Trust THIS block over anything U1's notes say:\n1. U1 removed the closed-key names `allowed_profiles` and `boundaries` from the `agent_keys` set inside `_parse_role` (~`:773-785`) \u2014 the LIVE, reachable agent-lens validation path that every registry load executes. U1's notes wrongly described this as tidying the unreachable `_parse_deterministic` branch. That branch (~`:636-761`) only lost three keyword arguments and is still dead code with zero call sites. If you touch registry key validation, `_parse_role` is the function that matters.\n2. U1 added an unplanned check rejecting a `default_profile` outside `PROFILE_IDS`. The check is sound and stays. But U1's stated reason for it was wrong: a MISSING `default_profile` key was never a risk, because `_closed_keys` (~`:398-408`) enforces exact set equality and `_parse_role` applies it with `default_profile` required, so the key cannot be absent. The check's real value is catching a mistyped VALUE.\n3. `scripts/validate_codex_plugins.py` currently EXITS 0 on this tree, and so does `python3 scripts/build_legacy_workflow_inventory.py --check`. The plan's claim that U1's registry edit stales the legacy token inventory is FALSE: `workflow_registry_sha256` is computed live from `WORKFLOW_COMPAT.REGISTRY` at `validate_codex_plugins.py:764-770` and never hashed the role registry. Treat a validator FAILURE as a real signal from your own change, not as expected background noise.\n4. Re-rendering the seven `agents/*.toml` profiles stales `docs/validation/verified-workflows-runtime-proof.json`, which pins their sha256 values; leaving it stale breaks four tests plus `validate_codex_plugins.py` with 'tracked runtime proof is stale'. Your change to `PROFILE_POLICY` and the profile-resolution dataclass alters the rendered profiles, so you MUST re-render and then regenerate the proof with: `FLEET_COMMONS_ROOT=$PWD/plugins/fleet-core PYTHONDONTWRITEBYTECODE=1 python3 scripts/prove_verified_workflows_runtime.py --pretty > docs/validation/verified-workflows-runtime-proof.json`. Only the seven profile digests should change; `harness_sha256` and every claim field must stay byte-identical.\n\nCONSTRAINTS:\n- Do NOT commit, branch, push, or open a pull request. The root session owns every git operation.\n- Do NOT regenerate `docs/validation/verified-workflows-legacy-token-inventory.json`; Unit U7 owns it. Unlike the plan's original claim, it is NOT expected to be stale \u2014 see corrected handoff item 3.\n- Never touch `plugins/verified-workflows/CHANGELOG.md`, anything under `docs/plans/`, `.claude/`, or `.codex/`.\n\nRETURN a JSON object with keys `status`, `files_changed`, `checks_run`, `notes`, and `red_first_reproduction` (what the reproduction test proved \u2014 this is the evidence that the change's premise held).\n\nRETURN CONTRACT (all tiers): your FINAL message MUST be ONLY a single JSON object with the keys status, files_changed, checks_run, notes, red_first_reproduction -- no prose, no markdown code fences, no YAML, and nothing before or after the JSON. The workflow gate parses this final message as JSON and FAILS the unit if it is not a JSON object carrying these keys. Emit it as your last action even if the work is only partial (fill each key with what you have plus a short note).",
  { label: "remove-compiler-refusals", model: "opus", effort: "high", schema: {"additionalProperties": true, "properties": {"checks_run": {}, "files_changed": {}, "notes": {}, "red_first_reproduction": {}, "status": {}}, "required": ["status", "files_changed", "checks_run", "notes", "red_first_reproduction"], "type": "object"} },
)
__gate(U2, { unitId: "U2", expectsOutput: true, returns: ["status", "files_changed", "checks_run", "notes", "red_first_reproduction"], cordProposal: "opus/high -> opus/xhigh (+1 effort rung)" })

// verify: refute-3 panel over U2 (pass_rule: majority;
// panel-level: refuted when the pass-rule threshold over REPORTING verifiers is met (quorum floor 2 of 3 declared; runtime-missing verifiers shrink the denominator))
const U2_verdicts = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U2 (remove-compiler-refusals). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U2),
    { label: "remove-compiler-refusals verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U2 } },
  ), { unitId: "U2", maxAttempts: 3 }),
])
const U2_verdicts_chunk_2 = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U2 (remove-compiler-refusals). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U2),
    { label: "remove-compiler-refusals verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U2 } },
  ), { unitId: "U2", maxAttempts: 3 }),
])
const U2_verdicts_chunk_3 = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U2 (remove-compiler-refusals). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U2),
    { label: "remove-compiler-refusals verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U2 } },
  ), { unitId: "U2", maxAttempts: 3 }),
])
U2_verdicts.push(...U2_verdicts_chunk_2, ...U2_verdicts_chunk_3)
const U2_valid_verifier_verdict = (v) => v != null && typeof v === "object" && Array.isArray(v.refuted_deliverable) && Array.isArray(v.advisory_corrections) && Array.isArray(v.upheld) && typeof v.verifier_identity === "string" && v.verifier_identity.length > 0 && Object.prototype.hasOwnProperty.call(v, "fallback_depth") && typeof v.examined_sha === "string" && v.examined_sha.length > 0
const U2_reported = U2_verdicts.filter((v) => U2_valid_verifier_verdict(v))
const U2_fallback_marker = (() => {
  const depthOf = (v) => {
    const raw = v.fallback_depth
    if (typeof raw === "boolean") return 0
    if (typeof raw === "string" && !/^-?\d+$/.test(raw.trim())) return 0
    const d = Math.trunc(Number(raw))
    return Number.isFinite(d) && d > 0 ? d : 0
  }
  const degraded = U2_reported.filter((v) => depthOf(v) > 0)
  if (degraded.length === 0) return ""
  return " — " + degraded.map((v) => `fallback tier ${depthOf(v)} (${v.verifier_identity || "unknown-verifier"})`).join("; ")
})()
const U2_missing_idx = U2_verdicts.map((v, i) => (!U2_valid_verifier_verdict(v) ? i + 1 : null)).filter((i) => i != null)
const U2_refute_count = U2_reported.filter((v) => v.refuted_deliverable.length > 0).length
const U2_threshold = Math.max(1, Math.ceil(U2_reported.length / 2))  // majority over reporters
const U2_refuted = U2_refute_count >= U2_threshold
__logAdvisory("U2", U2_reported)
if (U2_missing_idx.length > 0) {
  log(`verify panel over U2: ${U2_missing_idx.length}/3 verifier(s) missing (runtime-failure: #${U2_missing_idx.join(", #")}); verdict computed over ${U2_reported.length}/3` +
      (U2_reported.length < 2 ? " — UNDER-STRENGTH (quorum floor 2)" : ""))
}
if (U2_reported.length < 2) {
  throw new Error(`verifier-under-strength: Unit U2 reported ${U2_reported.length}/3 verifiers (quorum floor 2; missing #${U2_missing_idx.join(', #')})${U2_fallback_marker}`)
}
if (U2_refuted) {
  throw new Error(`verifier-disagreement: Unit U2 refuted by ${U2_refute_count}/${U2_reported.length} reporting verifiers (${U2_missing_idx.length} missing)${U2_fallback_marker}`)
}

// ---- U4: retire-git-prohibition-from-profiles ----
// depends_on: U1, U2 (barrier)
// escalation: HALT if the instruction template cannot be edited without changing the runtime-identity sentences, which must stay.
const U4 = await agent(
  "Implement Unit U4 of the plan at `docs/plans/2026-08-01-verified-workflows-capability-policy-removal-plan.md` in the repository at REPO. Units U1, U2, and U3 have already landed in this working tree. READ the plan's `### U4` section first.\n\nThis is a mechanical template edit plus a deterministic re-render. Do not redesign anything.\n\nGOAL: the generated profiles stop asserting a prohibition the runtime does not implement.\n\nWHAT TO DO:\n1. In the developer-instruction template inside `plugins/verified-workflows/scripts/render_codex_agents.py`, replace the sentence \"Do not run Git unless the role is `git-integration-operator`\" with guidance to perform the assigned bounded role and stay inside it. Match the surrounding voice.\n2. LEAVE the surrounding sentences about runtime identity coming from Codex readback exactly as they are \u2014 those remain true and are not part of this change.\n3. Re-render all seven profile files under `plugins/verified-workflows/agents/`. Confirm the exact write flag from `python3 plugins/verified-workflows/scripts/render_codex_agents.py --help`.\n4. `plugins/verified-workflows/tests/test_agent_tier_sync.py` is listed defensively. A sweep for every identifier this change removes found NO hit in that file, so expect no edit. Confirm that before touching it \u2014 if it genuinely asserts instruction bytes, update it; otherwise leave it alone and say so in your notes.\n\nPATTERNS: the existing instruction text in `plugins/verified-workflows/agents/work_medium.toml`, which already separates compute defaults from logical-role identity.\n\nTESTS \u2014 the plan's U4 `Test scenarios`:\n- The rendered `work_medium` instructions contain no Git prohibition, and `--check --pretty` agrees with the committed bytes.\n- All seven profiles re-render deterministically; a second `--check` after the first is a no-op.\n- A hand-edited profile whose bytes drift from the renderer still fails `--check`, proving the drift guard survives.\n\n5. MANDATORY AFTER THE RE-RENDER \u2014 this was missing from the plan and is not optional. `docs/validation/verified-workflows-runtime-proof.json` pins the sha256 of all seven `agents/*.toml` files. Re-rendering them makes it stale, which breaks four tests plus `scripts/validate_codex_plugins.py` with 'verified-workflows: U4 runtime proof validation failed: tracked runtime proof is stale'. Regenerate it with exactly:\n`FLEET_COMMONS_ROOT=$PWD/plugins/fleet-core PYTHONDONTWRITEBYTECODE=1 python3 scripts/prove_verified_workflows_runtime.py --pretty > docs/validation/verified-workflows-runtime-proof.json`\nOnly the seven profile digests should change; `harness_sha256` and every claim field must remain byte-identical. Verify that in the diff before returning.\n\nVERIFY before returning: `grep -rn 'Do not run Git' plugins/verified-workflows/` returns nothing, `python3 plugins/verified-workflows/scripts/render_codex_agents.py --check --pretty` exits 0, `python3 scripts/validate_codex_plugins.py` exits 0, and `uv run python -m pytest -q plugins/verified-workflows/tests` passes.\n\nCONSTRAINTS:\n- Do NOT commit, branch, push, or open a pull request. The root session owns every git operation.\n- Do NOT regenerate `docs/validation/verified-workflows-legacy-token-inventory.json`; Unit U7 owns it. Contrary to the plan's original claim, that file is NOT expected to be stale: `workflow_registry_sha256` is computed live from `WORKFLOW_COMPAT.REGISTRY` at `scripts/validate_codex_plugins.py:764-770` and never hashed the role registry. Treat a `validate_codex_plugins.py` FAILURE as a real signal from your own change, not as expected background noise.\n- Never touch `plugins/verified-workflows/CHANGELOG.md`, anything under `docs/plans/`, `.claude/`, or `.codex/`.\n\nRETURN a JSON object with keys `status`, `files_changed`, `checks_run`, and `notes`.\n\nRETURN CONTRACT (all tiers): your FINAL message MUST be ONLY a single JSON object with the keys status, files_changed, checks_run, notes -- no prose, no markdown code fences, no YAML, and nothing before or after the JSON. The workflow gate parses this final message as JSON and FAILS the unit if it is not a JSON object carrying these keys. Emit it as your last action even if the work is only partial (fill each key with what you have plus a short note).",
  { label: "retire-git-prohibition-from-profiles", model: "sonnet", effort: "medium", schema: {"additionalProperties": true, "properties": {"checks_run": {}, "files_changed": {}, "notes": {}, "status": {}}, "required": ["status", "files_changed", "checks_run", "notes"], "type": "object"} },
)
__gate(U4, { unitId: "U4", expectsOutput: true, returns: ["status", "files_changed", "checks_run", "notes"], cordProposal: "sonnet/medium -> sonnet/high (+1 effort rung)" })

// ---- U5: correct-live-documentation ----
// depends_on: U1, U2, U3, U4 (barrier)
// escalation: HALT if correcting a documentation surface would require changing a statement that is still true after U1-U4.
const U5 = await agent(
  "Implement Unit U5 of the plan at `docs/plans/2026-08-01-verified-workflows-capability-policy-removal-plan.md` in the repository at REPO. Units U1 through U4 have already landed in this working tree \u2014 READ THE ACTUAL CODE as it now stands before writing a single sentence about what the plugin does. READ the plan's `### U5` section first; it names each line and its disposition.\n\nGOAL: the guidance an agent or operator reads matches what the plugin actually does. This unit has NO test surface, so accuracy is entirely on you.\n\nEXACT DISPOSITIONS \u2014 each was decided during a doc-review, do not improvise past them:\n- `plugins/verified-workflows/README.md:5` stops calling the root session the Git owner. Describe it instead as the orchestrator of an approved graph and the adjudicator of its evidence. `:75-76`, `:104`, and the profile table lose the workspace-intent column's implication of enforcement.\n- `plugins/verified-workflows/skills/run/references/delegation-safety.md:16-18` drops the claim that a child cannot merge, deploy, or handle credentials. `:22-25` KEEPS the inheritance fact \u2014 it is true and load-bearing.\n- `plugins/verified-workflows/skills/run/references/workflow-protocol.md` needs BOTH of its cited lines handled, not one. `:22-23` drops the permission-boundary constraint on fallbacks. `:20-21` loses \"Only `git-integration-operator` may own Git commands\", because U2 deleted the `GIT_WORD_RE` check that enforced it \u2014 leaving the sentence would preserve exactly the unenforced-rule defect this whole change removes. BUT the second half of that same sentence, requiring the final `git diff --name-only` validation, STAYS: requirement R9 pins it and `workflow_dispatch.py:319-322` still enforces it.\n- `plugins/verified-workflows/skills/review-workflow/SKILL.md:8` stops asserting root ownership of integration and Git.\n- `plugins/saga/references/operator-choice.md:47-48` stays VERBATIM \u2014 the statement that a profile cannot widen or narrow inherited permission is true and load-bearing. Only the conclusion drawn from it changes.\n\nFRAMING TO GET RIGHT: removing containment LANGUAGE is not removing containment. Nothing prevented a subagent from mutating anything before this change either \u2014 only the documentation implied otherwise. State the actual control plainly: operator approval of the plan and of the workflow contract. Do not delete the guidance and leave a gap.\n\nPATTERNS: the existing README voice \u2014 short declarative sentences, no hedging.\n\nVERIFY before returning:\n- `grep -rn 'Git owner' plugins/` returns ONLY `plugins/verified-workflows/CHANGELOG.md:35`.\n- `git diff --stat` shows NO change under `docs/plans/`.\n- Every sentence you wrote is true of the code as it now stands. Re-read `workflow_dispatch.py` and `render_codex_agents.py` to confirm rather than trusting the plan's description of them.\n\nCONSTRAINTS:\n- Do NOT commit, branch, push, or open a pull request. The root session owns every git operation.\n- `plugins/verified-workflows/CHANGELOG.md` and every file under `docs/plans/` are HISTORY and must stay exactly as written \u2014 they are the evidence this change rests on. A blanket text sweep for \"root owns Git\" phrasing would rewrite them; do not run one.\n- Do NOT regenerate `docs/validation/verified-workflows-legacy-token-inventory.json`; Unit U7 owns it.\n- Do NOT edit `docs/engineering-journal/` \u2014 Unit U6 owns the journal.\n- Never touch `.claude/` or `.codex/`.\n\nRETURN a JSON object with keys `status`, `files_changed`, `checks_run`, and `notes`.\n\nRETURN CONTRACT (all tiers): your FINAL message MUST be ONLY a single JSON object with the keys status, files_changed, checks_run, notes -- no prose, no markdown code fences, no YAML, and nothing before or after the JSON. The workflow gate parses this final message as JSON and FAILS the unit if it is not a JSON object carrying these keys. Emit it as your last action even if the work is only partial (fill each key with what you have plus a short note).",
  { label: "correct-live-documentation", model: "opus", effort: "high", schema: {"additionalProperties": true, "properties": {"checks_run": {}, "files_changed": {}, "notes": {}, "status": {}}, "required": ["status", "files_changed", "checks_run", "notes"], "type": "object"} },
)
__gate(U5, { unitId: "U5", expectsOutput: true, returns: ["status", "files_changed", "checks_run", "notes"], cordProposal: "opus/high -> opus/xhigh (+1 effort rung)" })

// verify: refute-3 panel over U5 (pass_rule: majority;
// panel-level: refuted when the pass-rule threshold over REPORTING verifiers is met (quorum floor 2 of 3 declared; runtime-missing verifiers shrink the denominator))
const U5_verdicts = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U5 (correct-live-documentation). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U5),
    { label: "correct-live-documentation verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U5 } },
  ), { unitId: "U5", maxAttempts: 3 }),
])
const U5_verdicts_chunk_2 = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U5 (correct-live-documentation). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U5),
    { label: "correct-live-documentation verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U5 } },
  ), { unitId: "U5", maxAttempts: 3 }),
])
const U5_verdicts_chunk_3 = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U5 (correct-live-documentation). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U5),
    { label: "correct-live-documentation verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U5 } },
  ), { unitId: "U5", maxAttempts: 3 }),
])
U5_verdicts.push(...U5_verdicts_chunk_2, ...U5_verdicts_chunk_3)
const U5_valid_verifier_verdict = (v) => v != null && typeof v === "object" && Array.isArray(v.refuted_deliverable) && Array.isArray(v.advisory_corrections) && Array.isArray(v.upheld) && typeof v.verifier_identity === "string" && v.verifier_identity.length > 0 && Object.prototype.hasOwnProperty.call(v, "fallback_depth") && typeof v.examined_sha === "string" && v.examined_sha.length > 0
const U5_reported = U5_verdicts.filter((v) => U5_valid_verifier_verdict(v))
const U5_fallback_marker = (() => {
  const depthOf = (v) => {
    const raw = v.fallback_depth
    if (typeof raw === "boolean") return 0
    if (typeof raw === "string" && !/^-?\d+$/.test(raw.trim())) return 0
    const d = Math.trunc(Number(raw))
    return Number.isFinite(d) && d > 0 ? d : 0
  }
  const degraded = U5_reported.filter((v) => depthOf(v) > 0)
  if (degraded.length === 0) return ""
  return " — " + degraded.map((v) => `fallback tier ${depthOf(v)} (${v.verifier_identity || "unknown-verifier"})`).join("; ")
})()
const U5_missing_idx = U5_verdicts.map((v, i) => (!U5_valid_verifier_verdict(v) ? i + 1 : null)).filter((i) => i != null)
const U5_refute_count = U5_reported.filter((v) => v.refuted_deliverable.length > 0).length
const U5_threshold = Math.max(1, Math.ceil(U5_reported.length / 2))  // majority over reporters
const U5_refuted = U5_refute_count >= U5_threshold
__logAdvisory("U5", U5_reported)
if (U5_missing_idx.length > 0) {
  log(`verify panel over U5: ${U5_missing_idx.length}/3 verifier(s) missing (runtime-failure: #${U5_missing_idx.join(", #")}); verdict computed over ${U5_reported.length}/3` +
      (U5_reported.length < 2 ? " — UNDER-STRENGTH (quorum floor 2)" : ""))
}
if (U5_reported.length < 2) {
  throw new Error(`verifier-under-strength: Unit U5 reported ${U5_reported.length}/3 verifiers (quorum floor 2; missing #${U5_missing_idx.join(', #')})${U5_fallback_marker}`)
}
if (U5_refuted) {
  throw new Error(`verifier-disagreement: Unit U5 refuted by ${U5_refute_count}/${U5_reported.length} reporting verifiers (${U5_missing_idx.length} missing)${U5_fallback_marker}`)
}

// ---- U6: supersede-journal-decisions ----
// depends_on: U5 (barrier)
// escalation: If the record does not settle whether the U8 live cutover gate passed, say so plainly in the entry rather than guessing, and report it in u8_gate_status.
const U6 = await agent(
  "Implement Unit U6 of the plan at `docs/plans/2026-08-01-verified-workflows-capability-policy-removal-plan.md` in the repository at REPO. Units U1 through U5 have already landed. READ the plan's `### U6` section AND `KTD5` first \u2014 the supersession chain is subtle and a doc-review already caught one wrong version of it.\n\nGOAL: a future reader can trace why root-owned Git existed and why it stopped.\n\nTHE CHAIN, precisely. Read `docs/engineering-journal/DECISIONS.md` and confirm each of these against the file before writing:\n- `:64` already records that the 2026-07-24 entry supersedes the 2026-07-18 one, CONDITIONAL on the U8 live cutover gate passing. So the two are NOT peers and must not be written as peers.\n- Your new entry supersedes the 2026-07-24 entry \"Codex V2 Owns Live Execution...\" at `:50`, which asserts root ownership of integration, Git, gates, and merge at `:52`.\n- It notes that the 2026-07-18 entry \"Feasibility Review Keeps Root-Owned Workflows Usable\" at `:68` was ALREADY conditionally superseded by that one.\n- CHECK whether the U8 gate actually passed before asserting which of the two was operative. If the record does not settle it, SAY SO in the entry rather than guessing.\n\nONE NEARBY ENTRY IS NOT SUPERSEDED AND MUST BE NAMED AS SURVIVING: the 2026-07-17 entry \"Normalize Subject-Exclusion Parent Links And Bootstrap Self-Hosting Fixes Manually\" at `:78`, whose claim at `:84` holds that Verified Workflows cannot grant gate authority over changes to its own implementation, and that self-hosting patches keep root ownership of implementation, integration, Git, release, and installation. That is the exact category THIS change falls into, it remains true, and a reader of your new entry would otherwise conclude the opposite. Name it as surviving. (Note: the 2026-07-17 entry that `:64` supersedes is the SEPARATE temporary V1 catalog entry at `:90`, not this one. Do not confuse them.)\n\nBE HONEST ABOUT THE WEAK LINK: state plainly that the 2026-07-18 entry conditioned child execution on \"authenticated host-issued child attestation\", that combined `session_meta` and `turn_context` readback on the canonical agent path is being read as satisfying that condition, and that a future reader may reasonably disagree with that reading. Put the disagreement on the record rather than hiding it.\n\nTHE `LEARNINGS.md` COMPANION carries the generalizable rule: a policy the host does not implement is documentation, not a control, and it will eventually block real work. Include Evidence (the issue and the changed paths) and Mechanism (Codex 0.146 children inherit the parent turn's effective permission profile, so a declared per-role capability string was compared against a hardcoded constant and contained nothing).\n\nPATTERNS: the existing entry shape \u2014 `## YYYY-MM-DD: Title Case Statement`, short paragraphs, a closing plan or evidence pointer. Today's date is 2026-08-01.\n\nVERIFY before returning: both prior entries are cited by DATE AND TITLE in the new entry, and the earlier entries themselves are UNMODIFIED (`git diff docs/engineering-journal/DECISIONS.md` shows only an addition).\n\nCONSTRAINTS:\n- Do NOT commit, branch, push, or open a pull request. The root session owns every git operation.\n- The journal SUPERSEDES; it does not EDIT. Never rewrite an existing entry.\n- Do NOT regenerate `docs/validation/verified-workflows-legacy-token-inventory.json`; Unit U7 owns it.\n- Never touch `plugins/verified-workflows/CHANGELOG.md`, anything under `docs/plans/`, `.claude/`, or `.codex/`.\n\nRETURN a JSON object with keys `status`, `files_changed`, `checks_run`, `notes`, and `u8_gate_status` (what the record actually says about whether the U8 live cutover gate passed: \"passed\", \"not-passed\", or \"unsettled-by-the-record\").\n\nRETURN CONTRACT (all tiers): your FINAL message MUST be ONLY a single JSON object with the keys status, files_changed, checks_run, notes, u8_gate_status -- no prose, no markdown code fences, no YAML, and nothing before or after the JSON. The workflow gate parses this final message as JSON and FAILS the unit if it is not a JSON object carrying these keys. Emit it as your last action even if the work is only partial (fill each key with what you have plus a short note).",
  { label: "supersede-journal-decisions", model: "opus", effort: "high", schema: {"additionalProperties": true, "properties": {"checks_run": {}, "files_changed": {}, "notes": {}, "status": {}, "u8_gate_status": {}}, "required": ["status", "files_changed", "checks_run", "notes", "u8_gate_status"], "type": "object"} },
)
__gate(U6, { unitId: "U6", expectsOutput: true, returns: ["status", "files_changed", "checks_run", "notes", "u8_gate_status"], cordProposal: "opus/high -> opus/xhigh (+1 effort rung)" })

// verify: refute-3 panel over U6 (pass_rule: majority;
// panel-level: refuted when the pass-rule threshold over REPORTING verifiers is met (quorum floor 2 of 3 declared; runtime-missing verifiers shrink the denominator))
const U6_verdicts = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U6 (supersede-journal-decisions). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U6),
    { label: "supersede-journal-decisions verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U6 } },
  ), { unitId: "U6", maxAttempts: 3 }),
])
const U6_verdicts_chunk_2 = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U6 (supersede-journal-decisions). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U6),
    { label: "supersede-journal-decisions verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U6 } },
  ), { unitId: "U6", maxAttempts: 3 }),
])
const U6_verdicts_chunk_3 = await parallel([
  () => __retry(() => agent(
    __verifierPrompt("REFUTE-N VERIFIER over unit U6 (supersede-journal-decisions). You are an adversarial skeptic: attempt to REFUTE the unit's result, do NOT re-do its work. Read the unit's output and the evidence it cites; for each claimed finding decide REFUTED (with a concrete reason) or UPHELD, and sort every refutation into the gating bucket or the advisory bucket per the VERDICT CONTRACT below. Emit a structured verdict {refuted_deliverable: [...], advisory_corrections: [...], upheld: [...], verifier_identity: ..., fallback_depth: ..., examined_sha: ...}.\n\nEcho verifier_identity: saga:readonly-verifier and fallback_depth: 0 back in your verdict (do NOT alter them). Include examined_sha as the git SHA you actually materialized or inspected.", U6),
    { label: "supersede-journal-decisions verifier", model: "opus", effort: "high", agentType: "saga:readonly-verifier", isolation: "worktree", schema: {"additionalProperties": true, "properties": {"advisory_corrections": {"type": "array"}, "examined_sha": {"minLength": 1, "type": "string"}, "fallback_depth": {}, "refuted_deliverable": {"type": "array"}, "upheld": {"type": "array"}, "verifier_identity": {"minLength": 1, "type": "string"}}, "required": ["refuted_deliverable", "advisory_corrections", "upheld", "verifier_identity", "fallback_depth", "examined_sha"], "type": "object"}, input: { unit_result: U6 } },
  ), { unitId: "U6", maxAttempts: 3 }),
])
U6_verdicts.push(...U6_verdicts_chunk_2, ...U6_verdicts_chunk_3)
const U6_valid_verifier_verdict = (v) => v != null && typeof v === "object" && Array.isArray(v.refuted_deliverable) && Array.isArray(v.advisory_corrections) && Array.isArray(v.upheld) && typeof v.verifier_identity === "string" && v.verifier_identity.length > 0 && Object.prototype.hasOwnProperty.call(v, "fallback_depth") && typeof v.examined_sha === "string" && v.examined_sha.length > 0
const U6_reported = U6_verdicts.filter((v) => U6_valid_verifier_verdict(v))
const U6_fallback_marker = (() => {
  const depthOf = (v) => {
    const raw = v.fallback_depth
    if (typeof raw === "boolean") return 0
    if (typeof raw === "string" && !/^-?\d+$/.test(raw.trim())) return 0
    const d = Math.trunc(Number(raw))
    return Number.isFinite(d) && d > 0 ? d : 0
  }
  const degraded = U6_reported.filter((v) => depthOf(v) > 0)
  if (degraded.length === 0) return ""
  return " — " + degraded.map((v) => `fallback tier ${depthOf(v)} (${v.verifier_identity || "unknown-verifier"})`).join("; ")
})()
const U6_missing_idx = U6_verdicts.map((v, i) => (!U6_valid_verifier_verdict(v) ? i + 1 : null)).filter((i) => i != null)
const U6_refute_count = U6_reported.filter((v) => v.refuted_deliverable.length > 0).length
const U6_threshold = Math.max(1, Math.ceil(U6_reported.length / 2))  // majority over reporters
const U6_refuted = U6_refute_count >= U6_threshold
__logAdvisory("U6", U6_reported)
if (U6_missing_idx.length > 0) {
  log(`verify panel over U6: ${U6_missing_idx.length}/3 verifier(s) missing (runtime-failure: #${U6_missing_idx.join(", #")}); verdict computed over ${U6_reported.length}/3` +
      (U6_reported.length < 2 ? " — UNDER-STRENGTH (quorum floor 2)" : ""))
}
if (U6_reported.length < 2) {
  throw new Error(`verifier-under-strength: Unit U6 reported ${U6_reported.length}/3 verifiers (quorum floor 2; missing #${U6_missing_idx.join(', #')})${U6_fallback_marker}`)
}
if (U6_refuted) {
  throw new Error(`verifier-disagreement: Unit U6 refuted by ${U6_refute_count}/${U6_reported.length} reporting verifiers (${U6_missing_idx.length} missing)${U6_fallback_marker}`)
}

// ---- U7: regenerate-inventory-and-prove-the-gate ----
// depends_on: U1, U2, U3, U4, U5, U6 (barrier)
// escalation: HALT if \`--check\` and \`--write\` disagree after a clean regenerate — that is a real defect in an earlier unit, not a file to patch.
const U7 = await agent(
  "Implement Unit U7 of the plan at `docs/plans/2026-08-01-verified-workflows-capability-policy-removal-plan.md` in the repository at REPO. Units U1 through U6 have all landed in this working tree. READ the plan's `### U7` section and `KTD4` first.\n\nThis unit is terminal by construction and involves NO judgment. Run the generator, then run every gate.\n\nGOAL: the repository validates as one coherent unit, with the digest ripple resolved deliberately rather than discovered.\n\nWHAT TO DO:\n1. Run `python3 scripts/build_legacy_workflow_inventory.py --write` to regenerate `docs/validation/verified-workflows-legacy-token-inventory.json`. That file carries a `workflow_registry_sha256` plus 134 code-and-documentation entries.\n\nCORRECTED PREMISE — the plan's original framing of this step was WRONG and was falsified during the U1 verify panel, then re-confirmed independently by the driving session. Do not act on the old framing:\n- `workflow_registry_sha256` is NOT a digest of `plugins/verified-workflows/config/role-registry.yaml`, and it is NOT a frozen historical value. It is computed live on every run by `workflow_registry_sha256()` at `scripts/validate_codex_plugins.py:764-770`, which JSON-encodes `WORKFLOW_COMPAT.REGISTRY` — the workflow-NAME compatibility map, 18 entries — and sha256es it. It has never hashed the role registry.\n- Therefore U1's role-registry edit does NOT move this field and does NOT stale this file. Measured after U1 and U3 landed: `build_legacy_workflow_inventory.py --check` exits 0 and `scripts/validate_codex_plugins.py` exits 0.\n- What CAN legitimately move this file is the 134-entry list, which indexes code and documentation TEXT. The prose edits from U5 and U6 are the plausible movers. If `--write` produces no diff at all, that is a valid outcome — report it and move on. Do NOT go hunting for a registry digest ripple; there is none.\n- If `workflow_registry_sha256` itself ever changes, that means the workflow-name compatibility map changed, which is a real and unrelated event worth reporting loudly.\n2. NEVER hand-edit that JSON. If `--check` and `--write` disagree, that is a genuine defect in an earlier unit \u2014 report it as `status: \"blocked\"` with the diff, do not patch around it.\n\nTHEN RUN THE FULL GATE and record each exit status:\n- `python3 scripts/build_legacy_workflow_inventory.py --check` (must exit 0 after the write; a second `--write` must be a no-op)\n- `python3 plugins/verified-workflows/scripts/render_codex_agents.py --check --pretty`\n- `python3 scripts/validate_codex_plugins.py`\n- `uv run python -m pytest -q plugins/verified-workflows/tests`\n- `uv run python -m pytest -q tests/test_verified_workflows_migration.py tests/test_verified_workflows_agents.py`\n- `python3 -m pytest -q` (the whole suite)\n- `git diff --check` (whitespace)\n\nAlso confirm the scope boundaries held across the entire change:\n- `git diff --stat` shows NO change under `docs/plans/`.\n- `plugins/verified-workflows/CHANGELOG.md` is unchanged.\n- `docs/validation/codex-plugin-modernization-u3.json` is unchanged. That file records a `registry_sha256` that ALREADY diverges from the current rendered digest \u2014 it is dated historical evidence, not a live check, and regenerating it would destroy the record.\n\nPATTERNS: the generated-artifact convention used across `docs/validation/` \u2014 regenerate through the named builder, never by hand.\n\nCONSTRAINTS:\n- Do NOT commit, branch, push, or open a pull request. The root session owns every git operation.\n- Never touch `.claude/` or `.codex/`.\n- If a gate fails, report it honestly with the exact output. Do not fix an earlier unit's work silently \u2014 name what failed and where.\n\nRETURN a JSON object with keys `status`, `files_changed`, `checks_run`, `notes`, and `gate_results` (an object mapping each gate command above to its exit status and, on failure, the relevant output).\n\nRETURN CONTRACT (all tiers): your FINAL message MUST be ONLY a single JSON object with the keys status, files_changed, checks_run, notes, gate_results -- no prose, no markdown code fences, no YAML, and nothing before or after the JSON. The workflow gate parses this final message as JSON and FAILS the unit if it is not a JSON object carrying these keys. Emit it as your last action even if the work is only partial (fill each key with what you have plus a short note).",
  { label: "regenerate-inventory-and-prove-the-gate", model: "sonnet", effort: "medium", schema: {"additionalProperties": true, "properties": {"checks_run": {}, "files_changed": {}, "gate_results": {}, "notes": {}, "status": {}}, "required": ["status", "files_changed", "checks_run", "notes", "gate_results"], "type": "object"} },
)
__gate(U7, { unitId: "U7", expectsOutput: true, returns: ["status", "files_changed", "checks_run", "notes", "gate_results"], cordProposal: "sonnet/medium -> sonnet/high (+1 effort rung)" })

if (__pulledCords.length > 0) {
  throw new Error(`pull-cord (#364): ${__pulledCords.length} unit(s) self-reported out of depth -- ` +
    __pulledCords.map((c) => `${c.unit}: ${c.reason}` + (c.proposal ? ` (propose ${c.proposal})` : ' (no legal climb: top of ladder or session ceiling -- HALT)')).join('; ') +
    '. ONE batched escalation ask -- confirm climbs via /tier patch and re-emit.')
}

return {
  units: { U1: U1, U2: U2, U3: U3, U4: U4, U5: U5, U6: U6, U7: U7 },
  advisory_corrections: __advisories,
}
