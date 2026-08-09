"""Discovery and routing across every tracked plugin, and the receipt that proved it.

`tests/test_explicit_skill_invocation.py` checks that two plugins are explicit-only. It does not
resolve every plugin, and it says nothing about what happens to a skill that declares no policy at
all -- which, measured in U10, is injected into the model context by default. This module covers
the whole tracked set and pins the receipt's refusals.

Nothing here runs Codex. The runtime facts were measured once into
`docs/validation/codex-0147-discovery-routing.json`; these tests check the repository against that
receipt and check that the receipt cannot be quietly weakened.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
RECEIPT_PATH = ROOT / "docs" / "validation" / "codex-0147-discovery-routing.json"


def _load_prove_script():
    name = "u10_prove_verified_workflows_runtime"
    if name in sys.modules:
        return sys.modules[name]
    path = ROOT / "scripts" / "prove_verified_workflows_runtime.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = _load_prove_script()
RECEIPT = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))


def tracked_plugins() -> list[str]:
    return [entry["name"] for entry in json.loads(MARKETPLACE.read_text())["plugins"]]


def source_skills(plugin: str) -> list[Path]:
    skills = ROOT / "plugins" / plugin / "skills"
    if not skills.is_dir():
        return []
    return sorted(
        path for path in skills.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()
    )


def implicit_policy(skill: Path) -> bool | None:
    """The declared policy, or None when the skill ships no policy file at all.

    None is not "false". Codex 0.147 documents `allow_implicit_invocation` as defaulting to
    true, and U10 measured that default holding, so a missing file means the skill IS injected.
    """

    manifest = skill / "agents" / "openai.yaml"
    if not manifest.is_file():
        return None
    policy = (yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}).get("policy") or {}
    return policy.get("allow_implicit_invocation")


# --- the receipt itself -------------------------------------------------------------------


def test_the_committed_discovery_receipt_validates() -> None:
    P.validate_discovery_routing(RECEIPT)


def test_every_tracked_plugin_resolved_in_an_isolated_home() -> None:
    """Explicit resolution for each plugin, measured against repository source.

    The receipt was taken by installing this worktree as a local marketplace into a disposable
    CODEX_HOME, so a plugin resolving here is a statement about the source in this branch rather
    than about whatever the operator happened to have installed.
    """

    per_plugin = RECEIPT["isolated_discovery"]["per_plugin"]
    assert sorted(per_plugin) == sorted(tracked_plugins())

    for plugin in tracked_plugins():
        row = per_plugin[plugin]
        assert row["all_resolved"], f"{plugin} did not fully resolve: {row['unresolved']}"
        assert row["skills_in_source"] == len(source_skills(plugin)), plugin
        assert row["skills_resolved"] == row["skills_in_source"], plugin


def test_the_receipt_counts_match_the_source_tree() -> None:
    expected = sum(len(source_skills(plugin)) for plugin in tracked_plugins())
    assert RECEIPT["isolated_discovery"]["skills_in_source"] == expected
    assert RECEIPT["isolated_discovery"]["skills_resolved"] == expected
    assert RECEIPT["isolated_discovery"]["every_source_skill_resolved"] is True
    assert RECEIPT["isolated_discovery"]["listing_errors"] == []


def test_each_applicable_search_scope_resolved() -> None:
    """user, repo and system each returned rows; admin is recorded as not measured."""

    observed = RECEIPT["scopes"]["observed_counts"]
    for scope in ("user", "repo", "system"):
        assert observed.get(scope, 0) > 0, scope
    assert "admin" not in observed
    assert RECEIPT["criteria"]["admin-scope-resolution"]["measured"] is False
    assert RECEIPT["criteria"]["admin-scope-resolution"]["reason"]


def test_removing_a_plugin_stops_it_resolving() -> None:
    removal = RECEIPT["removal"]
    assert removal["stops_resolving"] is True
    assert removal["removed_plugin_rows_after"] == 0
    assert removal["rows_after"] < removal["rows_before"]
    # An unrelated plugin is unaffected, which is what makes the removal specific rather than a
    # listing that simply stopped working.
    assert removal["unrelated_plugin_rows_after"]["saga"] == len(source_skills("saga"))


def test_offered_is_never_recorded_as_executed() -> None:
    assert RECEIPT["criteria"]["skill-execution"]["measured"] is False
    assert RECEIPT["criteria"]["skill-execution"]["reason"]


def test_custom_agent_profiles_still_require_their_own_synchronisation() -> None:
    """R21: no packaging path carries a profile to where Codex reads it."""

    profiles = RECEIPT["agent_profiles"]
    assert profiles["codex_home_agents_dir_after_installing_every_plugin"] == "absent"
    assert profiles["profiles_present_inside_plugin_cache"] is True
    assert profiles["separate_synchronisation_still_required"] is True
    assert (ROOT / profiles["mechanism"]).is_file()


# --- what the repository declares, checked against the measured default -------------------


def test_a_skill_with_no_policy_file_is_injected_by_default() -> None:
    """The measurement that makes the inventory below meaningful.

    Three canaries in one turn: explicit-only stayed out, an explicit true went in, and one with
    no policy file at all went in too. The absence is evidence rather than a null result because
    the other two appear in the same recorded request.
    """

    canaries = RECEIPT["context_injection"]["canaries"]
    assert canaries["u10-explicit-only"]["injected"] is False
    assert canaries["u10-implicit-yes"]["injected"] is True
    assert canaries["u10-no-policy-file"]["policy_file"] is None
    assert canaries["u10-no-policy-file"]["injected"] is True


def test_implicit_lists_the_skill_rather_than_loading_it() -> None:
    """"Injected" is three different claims, and only two of them are true.

    An implicit skill contributes its name and description to every request; its instruction body
    does not travel. So the difference between the two modes is who may initiate -- a listed skill
    is one the model can choose unprompted -- rather than how much context a skill costs. Stating
    it as "the skill is loaded into context" overstates the cost by roughly thirty times and
    understates the part that actually matters.
    """

    depth = RECEIPT["context_injection"]["what_is_injected"]
    assert depth["measured"] is True
    assert depth["name"] is True
    assert depth["description"] is True
    assert depth["body"] is False

    cost = depth["cost_for_the_25_default_implicit_skills"]
    assert cost["their_bodies_not_sent_chars"] > 10 * cost["name_and_description_chars"]

    finding = next(
        item for item in RECEIPT["findings"]
        if item["id"] == "implicit-injection-unstated-for-eight-plugins"
    )
    assert finding["primary_consequence"] == "model-selectable without operator request"


def test_the_declared_explicit_only_set_is_exactly_saga_and_verified_workflows() -> None:
    declared = {
        plugin
        for plugin in tracked_plugins()
        for skill in source_skills(plugin)
        if implicit_policy(skill) is False
    }
    assert declared == {"saga", "verified-workflows"}


def test_the_implicitly_injected_inventory_matches_the_receipt() -> None:
    """Every skill shipping no policy file is injected; the receipt names the same set.

    This is deliberately an inventory rather than a prohibition. Whether these skills should be
    implicitly routable is the operator's call; what U10 refuses to allow is for the answer to go
    unrecorded, which is how it stood before this test existed.
    """

    inventory = {
        plugin: sorted(
            skill.name for skill in source_skills(plugin) if implicit_policy(skill) is None
        )
        for plugin in tracked_plugins()
    }
    inventory = {plugin: skills for plugin, skills in inventory.items() if skills}

    recorded = {
        plugin: row["no_policy_file_so_implicit_by_default"]
        for plugin, row in RECEIPT["isolated_discovery"]["per_plugin"].items()
        if row["no_policy_file_so_implicit_by_default"]
    }
    assert inventory == recorded

    finding = next(
        item for item in RECEIPT["findings"]
        if item["id"] == "implicit-injection-unstated-for-eight-plugins"
    )
    assert sorted(finding["plugins"]) == sorted(inventory)
    assert finding["skills"] == sum(len(skills) for skills in inventory.values())


def test_no_skill_declares_a_non_boolean_invocation_policy() -> None:
    for plugin in tracked_plugins():
        for skill in source_skills(plugin):
            declared = implicit_policy(skill)
            assert declared is None or isinstance(declared, bool), f"{plugin}:{skill.name}"


# --- the receipt's refusals ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda r: r["criteria"]["skill-execution"].update(measured=True),
            "listing a skill is not running one",
        ),
        (
            lambda r: r["isolated_discovery"].update(listing_errors=[{"path": "x", "message": "y"}]),
            "records listing errors",
        ),
        (
            lambda r: r["isolated_discovery"]["per_plugin"]["saga"].update(unresolved=["work"]),
            "claims everything resolved while naming",
        ),
        (
            lambda r: r["isolated_discovery"]["per_plugin"]["saga"].update(skills_resolved=1),
            "claims everything resolved but resolved",
        ),
        (
            lambda r: r["scopes"]["observed_counts"].update(workspace=3),
            "scopes Codex 0.147 does not define",
        ),
        (
            lambda r: r["context_injection"]["canaries"].__setitem__(
                "u10-implicit-yes", {"policy_file": None, "injected": False}
            )
            or r["context_injection"]["canaries"].__setitem__(
                "u10-no-policy-file", {"policy_file": None, "injected": False}
            ),
            "records no injected canary",
        ),
        (
            lambda r: r["agent_profiles"].update(separate_synchronisation_still_required=False),
            "still need their own sync",
        ),
        (
            lambda r: r["criteria"].__setitem__("something-new", {"measured": False}),
            "unmeasured with no reason",
        ),
    ],
)
def test_a_weakened_discovery_receipt_is_refused(mutate, expected: str) -> None:
    payload = json.loads(json.dumps(RECEIPT))
    mutate(payload)
    with pytest.raises(P.RuntimeProofError, match=expected):
        P.validate_discovery_routing(payload)


def test_a_single_canary_cannot_carry_the_injection_claim() -> None:
    """One absent marker is indistinguishable from a request that carried no skills at all."""

    payload = json.loads(json.dumps(RECEIPT))
    payload["context_injection"]["canaries"] = {
        "u10-explicit-only": {"policy_file": "explicit", "injected": False}
    }
    with pytest.raises(P.RuntimeProofError, match="at least two injection canaries"):
        P.validate_discovery_routing(payload)
