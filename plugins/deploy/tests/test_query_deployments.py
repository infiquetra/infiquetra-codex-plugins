"""Tests for deployment status rendering."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_query_deployments() -> ModuleType:
    module_name = "deploy_query_deployments"
    if module_name in sys.modules:
        return sys.modules[module_name]
    script = Path(__file__).resolve().parents[1] / "scripts" / "query_deployments.py"
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


query_deployments = load_query_deployments()


def test_strip_prefix_normalizes_deployment_tags() -> None:
    assert query_deployments.strip_prefix("nonprod-v1.2.3") == "1.2.3"
    assert query_deployments.strip_prefix("rollback-production-v1.2.3") == "1.2.3"


def test_detect_drift_reports_environment_versions() -> None:
    drift = query_deployments.detect_drift(
        {
            "nonprod": "nonprod-v1.2.4",
            "staging": "staging-v1.2.3",
            "production": "production-v1.2.3",
        }
    )

    assert drift == ["nonprod: 1.2.4", "staging: 1.2.3", "production: 1.2.3"]


def test_render_status_reports_missing_envs_and_workflow() -> None:
    rendered = query_deployments.render_status(
        "infiquetra/example",
        {
            "nonprod": {"ref": "nonprod-v1.2.3"},
            "staging": None,
            "production": {"ref": "production-v1.2.3"},
        },
    )

    assert "- staging: no deployment found" in rendered
    assert "drift: none detected" in rendered
    assert "workflow: https://github.com/infiquetra/example/actions" in rendered
