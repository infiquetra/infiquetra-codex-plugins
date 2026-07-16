# Mission Control 2.10.1 to Codex 2.4.2 unit evidence

- Recorded at: `2026-07-16T18:17:52Z`
- Reviewed commit: `86c0968ed344b8dfb878b1973cd263caf2af5234`
- Port unit: `U2`
- Result: **PASS**

## Committed-tree checks

| Check | Result |
|---|---|
| `PYTHONPATH=. uv run pytest -q plugins/mission-control/tests` | PASS - 211 tests |
| `PYTHONPATH=. uv run pytest -q plugins/mission-control/tests/test_board_move_exit.py` | PASS - 6 tests |
| `PYTHONPATH=. uv run pytest -q` | 2,221 passed; two unrelated Saga CLI tests encountered mixed real-home workflow provenance |
| isolated rerun of the two affected Saga CLI tests | PASS - 2 tests; every collected test therefore has a passing execution |
| `uv run ruff check .` | PASS |
| `uv run bandit -q -ll plugins/mission-control/scripts/sdlc_manager.py` | PASS - no medium/high findings |
| `python3 scripts/validate_codex_plugins.py --mode current` | PASS |
| `python3 scripts/validate_codex_plugins.py --mode target-fixture` | PASS |
| `python3 scripts/build_legacy_workflow_inventory.py --check` | PASS |
| `python3 scripts/build_saga_docs_facts.py --check` | PASS |
| `python3 scripts/render_saga_docs_assets.py --check` | PASS |
| exact source verification and focused port-contract tests | PASS - 6 frozen rows and 4 contract tests |
| `git diff --check` | PASS |

The default full-suite run inherited both canonical and legacy workflow roots
from the developer home. Two CLI dry-run tests use `Path(".")` as their repo
identity and therefore halted on that mixed provenance. Both passed unchanged
with an issue-scoped empty home. A whole-suite empty-home run is not authoritative
because two different profile/readiness tests intentionally inspect the real
installed Codex home. No unrelated Saga test or production code was changed.

The low-threshold Bandit probe reported eight existing low-severity findings in
the legacy Mission Control script and no medium/high finding. The board-move
delta adds no subprocess, input, credential, or serialization boundary.
