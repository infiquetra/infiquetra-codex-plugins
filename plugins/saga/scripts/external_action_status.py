#!/usr/bin/env python3
"""Derived operator projections for Saga external actions."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import external_action_store as store_module  # noqa: E402


STATUS_SCHEMA = "saga.external-action.status.v1"


def project(snapshot: store_module.Snapshot) -> dict[str, Any]:
    approval = snapshot.approval
    last = snapshot.events[-1] if snapshot.events else None
    return {
        "schema": STATUS_SCHEMA,
        "saga_id": snapshot.request.saga_id,
        "run_id": snapshot.request.run_id,
        "action_id": snapshot.request.action_id,
        "stage": snapshot.request.stage,
        "intent": snapshot.request.intent,
        "requiredness": snapshot.request.requiredness.value,
        "state": snapshot.state.value,
        "request_sha256": snapshot.request.request_sha256,
        "approval_fingerprint": approval.approval_fingerprint if approval else None,
        "route": dict(approval.route) if approval else None,
        "cost_class": approval.cost_class if approval else None,
        "egress": dict(approval.egress) if approval else None,
        "evidence_destination": snapshot.request.evidence_destination,
        "consumption_point": snapshot.request.consumption_point,
        "event_count": len(snapshot.events),
        "last_event": last["event"] if last else None,
        "last_event_at": last["at"] if last else None,
        "last_detail": dict(last.get("detail", {})) if last else {},
    }


def _value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, dict):
        return ", ".join(f"{key}={value[key]}" for key in sorted(value)) or "-"
    return str(value)


def render(status: dict[str, Any]) -> str:
    rows = (
        ("State", status["state"]),
        ("Intent", status["intent"]),
        ("Requiredness", status["requiredness"]),
        ("Route", status["route"]),
        ("Cost class", status["cost_class"]),
        ("Egress", status["egress"]),
        ("Evidence destination", status["evidence_destination"]),
        ("Consumption point", status["consumption_point"]),
        ("Approval fingerprint", status["approval_fingerprint"]),
        ("Last event", status["last_event"]),
    )
    lines = [
        f"# External Action `{status['action_id']}`",
        "",
        f"The action is `{status['state']}`; this card is derived from its immutable records and event log.",
        "",
        "| field | value |",
        "|---|---|",
    ]
    lines.extend(f"| {label} | {_value(value)} |" for label, value in rows)
    return "\n".join(lines) + "\n"


def refresh(store: store_module.Store) -> dict[str, Any]:
    status = project(store_module.read_snapshot(store))
    store_module.write_projection(store, status, render(status))
    return status
