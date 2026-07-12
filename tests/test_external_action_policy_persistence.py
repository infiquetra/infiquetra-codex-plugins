from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT_DIR = ROOT / "plugins" / "saga" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

POLICY = importlib.import_module("external_action_policy")


def _action() -> dict[str, object]:
    return {
        "action_id": "review-1", "intent": "second-opinion", "trigger": "operator-approved",
        "requiredness": "best-effort", "consumption_point": "review",
        "provider_constraints": {}, "context_scope": ["plan"], "sensitivity": "internal",
        "write_set": [], "evidence_destination": ".codex/saga/external-actions",
    }


def test_policy_save_is_digest_bound_closed_and_owner_only(tmp_path: Path) -> None:
    expected = POLICY.policy_sha256(tmp_path)
    path = POLICY.save_policy(tmp_path, {"plan": [_action()]}, expected_sha256=expected)

    assert POLICY.load_policy(tmp_path)["plan"][0].action_id == "review-1"
    assert path.stat().st_mode & 0o777 == 0o600
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1
    with pytest.raises(POLICY.PolicyError, match="digest changed"):
        POLICY.save_policy(tmp_path, {"plan": [_action()]}, expected_sha256=expected)
