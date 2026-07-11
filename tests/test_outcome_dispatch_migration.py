"""U5 append-only outcome dispatch migration contract."""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins/saga/scripts"
sys.path.insert(0, str(SCRIPTS))
def load(name: str):
    spec = importlib.util.spec_from_file_location(f"u5_{name}", SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    return module

OUTCOME = load("outcome")

def test_launch_ack_is_required_for_dispatched_state(tmp_path, monkeypatch):
    common = tmp_path / ".git"; common.mkdir()
    monkeypatch.setattr(OUTCOME.outcome_store.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(returncode=0, stdout=f"{common}\n", stderr=""))
    OUTCOME.start(tmp_path, "u5", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    pending = OUTCOME.advance(tmp_path, "u5", dispatcher=lambda _req: "leaf-u5-leaf")
    assert pending.dispatched == []
    assert pending.status["states"]["leaf"] == "legacy-unverified"

    # A real skill-mediated acknowledgement, not the synthetic legacy identifier, is launch truth.
    OUTCOME.start(tmp_path, "u5b", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    launched = OUTCOME.advance(tmp_path, "u5b", dispatcher=lambda _req: {"ack_kind": "launched", "dispatch_ack_ref": "receipt:1", "leaf_saga_id": "real-leaf-1"})
    assert launched.dispatched == ["leaf"]
    assert launched.status["states"]["leaf"] == "dispatched"


def test_manual_ack_settles_without_liveness_and_reconciliation_is_append_only(tmp_path, monkeypatch):
    common = tmp_path / ".git"; common.mkdir()
    monkeypatch.setattr(OUTCOME.outcome_store.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(returncode=0, stdout=f"{common}\n", stderr=""))
    OUTCOME.start(tmp_path, "u5c", "U5", nodes=[{"subplot_id": "leaf", "title": "leaf"}])
    OUTCOME.advance(tmp_path, "u5c", dispatcher=lambda _req: {"ack_kind": "handed-off", "dispatch_ack_ref": "operator:42"})
    assert OUTCOME.status(tmp_path, "u5c")["states"]["leaf"] == "handed-off"
    with __import__("pytest").raises(OUTCOME.OutcomeError, match="already acknowledged"):
        OUTCOME.reconcile_dispatch_ack(OUTCOME._store(tmp_path, "u5c"), outcome_id="u5c", subplot_id="leaf", ack_kind="handed-off", dispatch_ack_ref="operator:43")
