#!/usr/bin/env python3
"""Derived operator projections for Saga external actions."""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import external_action_store as store_module  # noqa: E402
import bridge_signatures  # noqa: E402
import fleet_commons_shim  # noqa: E402

_receipt = fleet_commons_shim.load("bridge_receipt")


STATUS_SCHEMA = "saga.external-action.status.v1"


def project(
    snapshot: store_module.Snapshot, *, evidence_root: Path | None = None
) -> dict[str, Any]:
    approval = snapshot.approval
    last = snapshot.events[-1] if snapshot.events else None
    complete = next(
        (event for event in reversed(snapshot.events) if event["event"] == "complete"),
        None,
    )
    complete_detail = dict(complete.get("detail", {})) if complete else {}
    receipt = complete_detail.get("runner_receipt")
    receipt_errors: list[str] = []
    if isinstance(receipt, dict):
        evidence_text = _evidence_text(complete_detail.get("evidence_ref"), evidence_root)
        receipt_errors.extend(_receipt.validate_receipt(receipt))
        receipt_errors.extend(
            bridge_signatures.validate_receipt_signature(
                receipt,
                evidence_text=evidence_text,
            )
        )
    adjudication = next(
        (
            event
            for event in reversed(snapshot.events)
            if event["event"] in {"accept", "reject"}
        ),
        None,
    )
    consumption = next(
        (event for event in reversed(snapshot.events) if event["event"] == "consume"),
        None,
    )
    route = dict(approval.route) if approval else {}
    raw_invocation = route.get("invocation")
    invocation: dict[str, Any] = dict(raw_invocation) if isinstance(raw_invocation, dict) else {}
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
        "route": route or None,
        "resolved_provider": route.get("engine_id"),
        "resolved_model": invocation.get("model") or route.get("model") or route.get("variant"),
        "adapter_class": invocation.get("via") or route.get("adapter_class"),
        "launch_acknowledged": any(event["event"] == "launch" for event in snapshot.events),
        "receipt_validity": (
            "valid" if isinstance(receipt, dict) and not receipt_errors
            else "invalid" if isinstance(receipt, dict)
            else "not-available"
        ),
        "receipt_errors": receipt_errors,
        "cost_class": approval.cost_class if approval else None,
        "estimated_usage": route.get("estimated_usage"),
        "observed_usage": receipt.get("external_tokens") if isinstance(receipt, dict) else None,
        "egress": dict(approval.egress) if approval else None,
        "evidence_destination": snapshot.request.evidence_destination,
        "consumption_point": snapshot.request.consumption_point,
        "adjudication": adjudication["event"] if adjudication else "pending",
        "consumed_artifact": (
            dict(consumption.get("detail", {})).get("artifact_ref") if consumption else None
        ),
        "event_count": len(snapshot.events),
        "last_event": last["event"] if last else None,
        "last_event_at": last["at"] if last else None,
        "last_detail": dict(last.get("detail", {})) if last else {},
    }


def _evidence_text(reference: Any, evidence_root: Path | None = None) -> str:
    if not isinstance(reference, str):
        return ""
    try:
        path = Path(reference)
        if evidence_root is not None:
            path = evidence_root / path.name
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    evidence = artifact.get("evidence") if isinstance(artifact, dict) else None
    return evidence if isinstance(evidence, str) else ""


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
        ("Resolved provider", status["resolved_provider"]),
        ("Resolved model", status["resolved_model"]),
        ("Adapter class", status["adapter_class"]),
        ("Launch acknowledged", status["launch_acknowledged"]),
        ("Receipt validity", status["receipt_validity"]),
        ("Cost class", status["cost_class"]),
        ("Estimated usage", status["estimated_usage"]),
        ("Observed usage", status["observed_usage"]),
        ("Egress", status["egress"]),
        ("Evidence destination", status["evidence_destination"]),
        ("Consumption point", status["consumption_point"]),
        ("Codex adjudication", status["adjudication"]),
        ("Consumed artifact", status["consumed_artifact"]),
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
    status = project(store_module.read_snapshot(store), evidence_root=store.root)
    store_module.write_projection(store, status, render(status))
    return status
