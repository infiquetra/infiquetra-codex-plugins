from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import engine_offer  # noqa: E402
import engine_preference  # noqa: E402
import external_action_policy as policy  # noqa: E402


def test_defaults_cover_all_six_stages(tmp_path: Path) -> None:
    defaults = policy.load_defaults()
    assert set(defaults) == {"ideate", "brainstorm", "plan", "work", "doc-review", "code-review"}
    assert len(policy.resolve("ideate", repo_root=tmp_path).actions) == 2


def test_precedence_is_explicit_policy_legacy_default(tmp_path: Path) -> None:
    engine_preference.save_preference(tmp_path, "work", engine_offer.Preference(intent="none"))
    assert policy.resolve("work", repo_root=tmp_path).source == "legacy"
    assert policy.resolve("work", repo_root=tmp_path).actions == ()
    path = tmp_path / policy.POLICY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "stages": {"work": []}}), encoding="utf-8")
    assert policy.resolve("work", repo_root=tmp_path).source == "policy"
    explicit = [{"action_id": "one", "intent": "offload", "trigger": "x", "consumption_point": "y"}]
    assert policy.resolve("work", repo_root=tmp_path, explicit_actions=explicit).source == "explicit"


def test_legacy_intent_selects_matching_default(tmp_path: Path) -> None:
    engine_preference.save_preference(
        tmp_path, "work", engine_offer.Preference(intent="second-opinion", model="opus", effort="high")
    )
    result = policy.resolve("work", repo_root=tmp_path)
    assert result.source == "legacy"
    assert [item.intent for item in result.actions] == ["second-opinion"]


def workflow_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "action_id": "external-edit",
        "purpose": "bounded implementation",
        "provider": "claude-cli",
        "model": "opus",
        "egress": ["networked", "provider.example"],
        "context": ["src/input.py"],
        "sensitivity": "internal",
        "cost": "metered",
        "writes_or_artifact": ["src/output.py", "artifact:review"],
        "requiredness": "required",
        "authority": "non-gating",
    }
    row.update(overrides)
    return row


def test_workflow_rows_join_existing_policy_contract() -> None:
    template = policy.workflow_rows_to_templates([workflow_row()])[0]

    assert template.action_id == "external-edit"
    assert template.intent == "offload"
    assert template.requiredness.value == "required-before-continue"
    assert template.context_scope == ("src/input.py",)
    assert template.write_set == ("src/output.py",)
    assert template.provider_constraints == {
        "provider": "claude-cli",
        "model": "opus",
        "egress": ["networked", "provider.example"],
        "cost": "metered",
        "authority": "non-gating",
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"authority": "blocking"},
        {"context": ["../outside"]},
        {"context": [".env"]},
        {"writes_or_artifact": [".git/config"]},
    ],
)
def test_workflow_rows_reject_authority_and_path_expansion(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(policy.PolicyError):
        policy.workflow_rows_to_templates([workflow_row(**overrides)])
