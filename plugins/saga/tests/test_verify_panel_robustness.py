"""U7: verify-panel consensus recomputation over the verifiers that actually reported (R5).

The emitted refute-N panel used to compare ``refute_count`` against a threshold baked over the
declared ``n``. A verifier that crashed / returned a malformed verdict was silently counted as a
non-refuting N/A vote, so a degraded panel could pass a unit its *reporting* skeptics would have
refuted. The port recomputes the pass-rule threshold over the reporters only, excludes
runtime-missing verifiers, and annotates an UNDER-STRENGTH panel — matching team-execution's
dimension-exclusion semantics.

These oracles pin the generated JavaScript (the single source of truth is
``_emit_panel_reconciliation``, shared across all three panel-emitting sites): one-shot panel,
iterate-to-consensus singleton, and the parallel-wave thunk.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
SCRIPT = SCRIPTS / "execution_spec.py"


def _load() -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("execution_spec", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["execution_spec"] = module
    spec.loader.exec_module(module)
    return module


es = _load()


def _unit(unit_id: str, *, pass_rule: str, iterate: bool, n: int = 3) -> dict:
    return {
        "unit_id": unit_id,
        "label": unit_id.lower(),
        "tier": {"model": "sonnet", "effort": "medium"},
        "verify": {
            "n": n,
            "pass_rule": pass_rule,
            "iterate_to_consensus": iterate,
            "max_iterations": 3,
        },
    }


def _script(units: list[dict]) -> str:
    spec = es.ExecutionSpec.from_dict(
        {"name": "t", "subject_sha": "a" * 40, "units": units}
    )
    return es.emit_workflow_script(spec)


# --- happy: consensus is recomputed over reporters, not the declared n --------------------


def test_one_shot_panel_recomputes_majority_over_reporters() -> None:
    js = _script([_unit("U1", pass_rule="majority", iterate=False)])
    # Reporters must pass the seat, depth, subject, and structured-array binding predicate.
    assert (
        "const U1_reported = U1_verdicts.filter((v, i) => "
        "U1_valid_verifier_verdict(v, i))" in js
    )
    # threshold recomputed over the reporter count, never the baked n.
    assert "const U1_threshold = Math.max(1, Math.ceil(U1_reported.length / 2))" in js
    assert "const U1_refute_count = U1_reported.filter((v) => v.refuted.length > 0).length" in js
    assert "const U1_refuted = U1_refute_count >= U1_threshold" in js


def test_unanimous_threshold_is_all_reporters_not_all_n() -> None:
    js = _script([_unit("U1", pass_rule="unanimous", iterate=False)])
    assert "const U1_threshold = Math.max(1, U1_reported.length)" in js


def test_iterate_singleton_recomputes_over_reporters() -> None:
    js = _script([_unit("U2", pass_rule="majority", iterate=True)])
    assert (
        "const reported = verdicts.filter((v, i) => valid_verifier_verdict(v, i))" in js
    )
    assert "const threshold = Math.max(1, Math.ceil(reported.length / 2))" in js
    assert "if (!refuted) {" in js  # loop consumer: break when not refuted


def test_parallel_wave_thunks_each_recompute() -> None:
    js = _script(
        [
            _unit("A", pass_rule="majority", iterate=True),
            _unit("B", pass_rule="majority", iterate=True),
        ]
    )
    # Two independent units -> one parallel wave -> two thunks, each with its own recompute.
    assert js.count("const reported = verdicts.filter") == 2


# --- edge: runtime-missing verifiers are excluded, panel annotated under-strength ---------


def test_missing_verifiers_are_flagged_and_excluded() -> None:
    js = _script([_unit("U1", pass_rule="majority", iterate=False)])
    assert "const U1_missing_idx = U1_verdicts.map((v, i)" in js
    assert "verifier(s) missing" in js
    assert "UNDER-STRENGTH (quorum floor 2)" in js


def test_disagreement_error_reports_reporting_denominator() -> None:
    js = _script([_unit("U1", pass_rule="majority", iterate=False)])
    # The throw names refuted-of-reporting, not refuted-of-n, and surfaces the missing count.
    assert "reporting verifiers" in js
    assert "U1_reported.length" in js
    assert "U1_missing_idx.length" in js


# --- guard: the naive fixed-n threshold must not survive anywhere -------------------------


@pytest.mark.parametrize("iterate", [True, False])
def test_no_fixed_n_threshold_remains(iterate: bool) -> None:
    js = _script([_unit("U1", pass_rule="majority", iterate=iterate, n=3)])
    # The old form compared refute_count against a python-baked int literal with a pass_rule
    # comment. Recomputation replaced every such site with a JS-side threshold const.
    assert ">= 2  // majority" not in js
    assert ">= 3  // unanimous" not in js
    assert "v && v.refuted && v.refuted.length" not in js  # old non-reporter-aware filter
