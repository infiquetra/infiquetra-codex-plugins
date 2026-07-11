from __future__ import annotations
import importlib.util
from pathlib import Path

PATH = Path(__file__).parents[1] / "plugins/saga/scripts/verified_workflow_readiness.py"
spec = importlib.util.spec_from_file_location("u5_readiness", PATH); assert spec and spec.loader
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

def test_canonical_workflow_ref_and_legacy_heading_are_readable(tmp_path):
    plan = tmp_path / "docs/plans/x.md"; plan.parent.mkdir(parents=True)
    plan.write_text("## Workflow Structure\n", encoding="utf-8")
    result = M.validate_verified_workflow_ready(tmp_path, orchestration_mode="verified-workflow", orchestration_ref="docs/plans/x.md#workflow-structure", context="work")
    assert result.status == "ready" and result.resolved_ref.endswith("#workflow-structure")
