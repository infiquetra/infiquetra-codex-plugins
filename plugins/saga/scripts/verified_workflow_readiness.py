#!/usr/bin/env python3
"""Canonical Verified Workflows receipt resolver with legacy read-only compatibility."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def _legacy() -> Any:
    path = Path(__file__).with_name("team_execution_readiness.py")
    spec = importlib.util.spec_from_file_location("saga_legacy_readiness", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_verified_workflow_ready(repo_root: Path, *, orchestration_mode: str, orchestration_ref: str,
                                    context: str, plan_path: str = "") -> Any:
    """Accept old Team Structure evidence only as legacy input; resolve canonical refs for new work."""
    legacy = _legacy()
    path, _sep, anchor = orchestration_ref.partition("#")
    candidate = repo_root / path
    if orchestration_mode == "verified-workflow" and anchor == "workflow-structure" and candidate.is_file() and "## Workflow Structure" in candidate.read_text(encoding="utf-8"):
        return legacy.ReadinessResult("ready", "Workflow Structure receipt resolved", "Verified Workflow may execute", orchestration_ref)
    mode = "team-execution" if orchestration_mode in {"verified-workflow", "team-execution"} else orchestration_mode
    legacy_ref = orchestration_ref.replace("#workflow-structure", "#team-structure").replace(".codex/verified-workflows/", ".codex/team-execution/").replace("~/.codex/verified-workflows/state/", "~/.codex/team-execution/state/")
    result = legacy.validate_team_execution_ready(repo_root, orchestration_mode=mode,
        orchestration_ref=legacy_ref, context=context, plan_path=plan_path)
    if result.resolved_ref:
        result = type(result)(result.status, result.reason, result.repair_hint,
            result.resolved_ref.replace("#team-structure", "#workflow-structure").replace(".codex/team-execution/", ".codex/verified-workflows/").replace("~/.codex/team-execution/state/", "~/.codex/verified-workflows/state/"))
    return result
