"""Cutover-owned raw hook lifecycle boundary tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
RAW = importlib.import_module("raw_hook_maintenance")
FACADE = importlib.import_module("dispatch_receipt")


def test_dispatch_facade_reexports_cutover_owned_operations() -> None:
    assert FACADE.create_raw_abandonment_record is RAW.create_raw_abandonment_record
    assert FACADE.prune_raw_receipts is RAW.prune_raw_receipts
    assert FACADE.delete_raw_pair is RAW.delete_raw_pair


def test_empty_raw_store_produces_digest_bound_dry_run(tmp_path: Path) -> None:
    plugin_data = tmp_path / "plugin-data"
    plugin_data.mkdir(mode=0o700)

    plan = RAW.prune_raw_receipts(
        plugin_data,
        older_than_seconds=RAW.MAX_EVENT_AGE_SECONDS,
    )

    assert plan["claim"] == "raw-prune-plan"
    assert plan["apply"] is False
    assert plan["entries"] == []
    assert len(plan["plan_sha256"]) == 64


def test_apply_requires_exact_dry_run_digest(tmp_path: Path) -> None:
    plugin_data = tmp_path / "plugin-data"
    plugin_data.mkdir(mode=0o700)

    with pytest.raises(RAW.DispatchReceiptError, match="exact dry-run plan digest"):
        RAW.prune_raw_receipts(
            plugin_data,
            older_than_seconds=RAW.MAX_EVENT_AGE_SECONDS,
            apply=True,
        )


def test_abandonment_requires_explicit_root_reason(tmp_path: Path) -> None:
    plugin_data = tmp_path / "plugin-data"
    plugin_data.mkdir(mode=0o700)

    with pytest.raises(RAW.DispatchReceiptError, match="reason"):
        RAW.create_raw_abandonment_record(
            plugin_data,
            parent_session_id="parent",
            child_id="child",
            turn_id="turn",
            reason="age-only",
        )
