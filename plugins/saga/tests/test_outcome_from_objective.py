"""Tests for `/outcome start --from-parent-issue` ingestion.

Offline: a fake ``runner`` returns fixture GraphQL JSON, so the whole ingestion path (query ->
normalize -> edge inference -> node assembly -> spec) runs with no live ``gh``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"


def _load(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SPEC_MOD = _load("outcome_spec")
STORE_MOD = _load("outcome_store")
_load("outcome_orchestrator")
_load("outcome_dispatcher")
_load("outcome_merge")
_load("outcome_worktrees")
_load("outcome_decompose")
ENG = _load("outcome")
_load("reversibility_certificate")
_load("outcome_board_sync")
DISC = _load("discover_subissues")
EDGES = _load("outcome_edges")


class _FakeResult:
    def __init__(self, stdout: str) -> None:
        self.returncode = 0
        self.stdout = stdout
        self.stderr = ""


def _sub(
    number: int,
    title: str,
    *,
    repo: str | None = None,
    state: str = "OPEN",
    state_reason: str | None = None,
    labels: list[str] | None = None,
    tracked: list[int | tuple[str, int]] | None = None,
    child_count: int = 0,
) -> dict[str, Any]:
    tracked_nodes = [
        {"number": item[1], "repository": {"nameWithOwner": item[0]}}
        if isinstance(item, tuple)
        else {"number": item}
        for item in (tracked or [])
    ]
    node = {
        "number": number,
        "title": title,
        "state": state,
        "stateReason": state_reason,
        "url": f"https://github.com/{repo or 'o/r'}/issues/{number}",
        "labels": {"nodes": [{"name": name} for name in (labels or [])]},
        "assignees": {"nodes": []},
        "trackedIssues": {"nodes": tracked_nodes},
        "subIssues": {"totalCount": child_count},
    }
    if repo is not None:
        node["repository"] = {"nameWithOwner": repo}
    return node


def _runner_for(subs: list[dict[str, Any]], *, parent_title: str = "Objective X") -> Any:
    payload = {
        "data": {
            "repository": {
                "issue": {
                    "number": 100,
                    "title": parent_title,
                    "state": "OPEN",
                    "subIssues": {"totalCount": len(subs), "nodes": subs},
                }
            }
        }
    }

    def _run(cmd: list[str], **kwargs: Any) -> _FakeResult:
        return _FakeResult(json.dumps(payload))

    return _run


# --------------------------------------------------------------------------- outcome_edges


def test_edges_from_relationships_maps_blocked_by_to_depends_on() -> None:
    subissues = [
        {"number": 1, "blocked_by": []},
        {"number": 2, "blocked_by": [1]},
    ]
    depends_on, dropped = EDGES.edges_from_relationships(subissues)
    assert depends_on == {"sub-2": ["sub-1"]}
    assert dropped == []


def test_edges_from_relationships_drops_dangling() -> None:
    subissues = [{"number": 1, "blocked_by": [999]}]
    depends_on, dropped = EDGES.edges_from_relationships(subissues)
    assert depends_on == {}
    assert dropped == [{"reason": "dangling", "from": "sub-1", "to": "sub-999"}]


def test_edges_from_relationships_drops_self_edge() -> None:
    subissues = [{"number": 1, "blocked_by": [1]}]
    depends_on, dropped = EDGES.edges_from_relationships(subissues)
    assert depends_on == {}
    assert dropped == [{"reason": "self", "from": "sub-1", "to": "sub-1"}]


def test_edges_from_relationships_drops_cycle() -> None:
    # 1 blocked_by 2, 2 blocked_by 1 -> the second edge closes a cycle and is dropped.
    subissues = [
        {"number": 1, "blocked_by": [2]},
        {"number": 2, "blocked_by": [1]},
    ]
    depends_on, dropped = EDGES.edges_from_relationships(subissues)
    assert depends_on == {"sub-1": ["sub-2"]}
    assert dropped == [{"reason": "cycle", "from": "sub-2", "to": "sub-1"}]


def test_edges_resolve_cross_repo_duplicate_numbers() -> None:
    tenant = "infiquetra/campps-tenant-setup"
    identity = "infiquetra/campps-identity-access"
    subissues = [
        {"number": 95, "repo": tenant, "blocked_by": [{"number": 95, "repo": identity}]},
        {"number": 95, "repo": identity, "blocked_by": []},
    ]

    depends_on, dropped = EDGES.edges_from_relationships(subissues)

    ids = EDGES.subplot_ids_for_subissues(subissues)
    tenant_id = ids[("infiquetra/campps-tenant-setup", 95)]
    identity_id = ids[("infiquetra/campps-identity-access", 95)]
    assert depends_on == {tenant_id: [identity_id]}
    assert dropped == []


def test_edges_drop_ambiguous_legacy_number_reference() -> None:
    subissues = [
        {"number": 96, "repo": "infiquetra/a", "blocked_by": [95]},
        {"number": 95, "repo": "infiquetra/a", "blocked_by": []},
        {"number": 95, "repo": "infiquetra/b", "blocked_by": []},
    ]

    depends_on, dropped = EDGES.edges_from_relationships(subissues)

    assert depends_on == {}
    assert dropped == [{"reason": "ambiguous", "from": "sub-96", "to": "sub-95"}]


# --------------------------------------------------------------------------- nodes_from_parent_issue


def test_nodes_from_parent_issue_builds_nodes_with_kind_and_github_stamp() -> None:
    subs = [
        _sub(1, "Design", labels=["non-code"]),
        _sub(2, "Build", tracked=[1]),
    ]
    nodes, dropped, title = ENG.nodes_from_parent_issue(
        "o", "r", 100, runner=_runner_for(subs, parent_title="Ship It")
    )
    assert title == "Ship It"
    assert dropped == []
    by_sid = {n["subplot_id"]: n for n in nodes}
    assert by_sid["sub-1"]["kind"] == "non-code"
    assert by_sid["sub-2"]["kind"] == "code"
    assert by_sid["sub-2"]["depends_on"] == ["sub-1"]
    assert by_sid["sub-1"]["github"] == {"repo": "o/r", "issue": "o/r#1", "sub_issue": 1}


def test_cross_repo_duplicate_numbers_get_unique_ids_and_true_stamps() -> None:
    tenant = "infiquetra/campps-tenant-setup"
    identity = "infiquetra/campps-identity-access"
    subs = [
        _sub(95, "Tenant", repo=tenant, tracked=[(identity, 95)]),
        _sub(95, "Identity", repo=identity),
    ]

    nodes, dropped, _title = ENG.nodes_from_parent_issue(
        "infiquetra", "campps-context-library", 69, runner=_runner_for(subs)
    )

    by_sid = {node["subplot_id"]: node for node in nodes}
    ids = EDGES.subplot_ids_for_subissues(
        [{"repo": tenant, "number": 95}, {"repo": identity, "number": 95}]
    )
    tenant_id = ids[(tenant, 95)]
    identity_id = ids[(identity, 95)]
    assert set(by_sid) == {tenant_id, identity_id}
    assert by_sid[tenant_id]["github"]["repo"] == tenant
    assert by_sid[identity_id]["github"]["repo"] == identity
    assert by_sid[tenant_id]["depends_on"] == [identity_id]
    assert dropped == []


def test_repo_qualified_ids_do_not_collide_when_slug_text_matches() -> None:
    subissues = [
        {"repo": "a-b/c", "number": 7},
        {"repo": "a/b-c", "number": 7},
    ]

    ids = EDGES.subplot_ids_for_subissues(subissues)

    assert len(set(ids.values())) == 2


def test_nodes_from_parent_issue_ingests_state_completed_and_not_planned() -> None:
    subs = [
        _sub(1, "Done leaf", state="CLOSED", state_reason="COMPLETED"),
        _sub(2, "Rejected leaf", state="CLOSED", state_reason="NOT_PLANNED"),
        _sub(3, "Open leaf", state="OPEN"),
    ]
    nodes, _dropped, _title = ENG.nodes_from_parent_issue("o", "r", 100, runner=_runner_for(subs))
    by_sid = {n["subplot_id"]: n for n in nodes}
    assert by_sid["sub-1"]["state"] == "done"
    assert by_sid["sub-2"]["state"] == "rejected"
    assert by_sid["sub-3"]["state"] == "pending"


def test_nodes_from_parent_issue_produces_a_validatable_spec() -> None:
    subs = [_sub(1, "A"), _sub(2, "B", tracked=[1])]
    nodes, _dropped, title = ENG.nodes_from_parent_issue("o", "r", 100, runner=_runner_for(subs))
    spec = SPEC_MOD.OutcomeSpec.from_dict({"outcome_id": "demo", "objective": title, "nodes": nodes})
    spec.validate()  # must not raise


def test_nodes_from_parent_issue_rejects_capability_trackers() -> None:
    subs = [_sub(1, "Broad workstream", labels=["capability"])]

    try:
        ENG.nodes_from_parent_issue("o", "r", 100, runner=_runner_for(subs))
    except ENG.OutcomeError as exc:
        assert "requires executable direct children" in str(exc)
        assert "o/r#1" in str(exc)
    else:
        raise AssertionError("expected OutcomeError")


def test_nodes_from_parent_issue_rejects_nested_trackers() -> None:
    subs = [_sub(1, "Nested tracker", child_count=2)]

    try:
        ENG.nodes_from_parent_issue("o", "r", 100, runner=_runner_for(subs))
    except ENG.OutcomeError as exc:
        assert "requires executable direct children" in str(exc)
        assert "o/r#1" in str(exc)
    else:
        raise AssertionError("expected OutcomeError")


# --------------------------------------------------------------------------- parent ref parsing


def test_parse_parent_issue_ref_valid() -> None:
    assert ENG._parse_parent_issue_ref("infiquetra/foo#42") == ("infiquetra", "foo", 42)


def test_parse_parent_issue_ref_rejects_malformed() -> None:
    try:
        ENG._parse_parent_issue_ref("not-a-ref")
    except ENG.OutcomeError:
        pass
    else:
        raise AssertionError("expected OutcomeError")


# --------------------------------------------------------------------------- _ingest_state


def test_ingest_state_open_is_pending() -> None:
    assert ENG._ingest_state("OPEN", None) == "pending"


def test_ingest_state_closed_completed_is_done() -> None:
    assert ENG._ingest_state("CLOSED", "COMPLETED") == "done"


def test_ingest_state_closed_not_planned_is_rejected() -> None:
    assert ENG._ingest_state("CLOSED", "NOT_PLANNED") == "rejected"


# --------------------------------------------------------------------------- CLI wiring


def test_main_start_requires_objective_or_parent_issue(tmp_path: Path) -> None:
    rc = ENG.main(["--repo-root", str(tmp_path), "start", "demo"])
    assert rc == 1


def test_main_start_accepts_from_parent_issue(tmp_path: Path) -> None:
    node = {"subplot_id": "sub-1", "title": "Build", "kind": "code"}
    with (
        patch.object(
            ENG,
            "nodes_from_parent_issue",
            return_value=([node], [], "Parent title"),
        ) as build_nodes,
        patch.object(
            ENG,
            "start",
            return_value=SimpleNamespace(outcome_id="demo", nodes=[node]),
        ) as start,
    ):
        rc = ENG.main(
            [
                "--repo-root",
                str(tmp_path),
                "start",
                "demo",
                "--from-parent-issue",
                "infiquetra/repo#42",
            ]
        )

    assert rc == 0
    build_nodes.assert_called_once_with("infiquetra", "repo", 42)
    assert start.call_args.args[2] == "Parent title"
    assert start.call_args.kwargs["nodes"] == [node]


def test_legacy_from_objective_warns_and_keeps_parent_semantics(
    tmp_path: Path, capsys: Any
) -> None:
    node = {"subplot_id": "sub-1", "title": "Build", "kind": "code"}
    with (
        patch.object(
            ENG,
            "nodes_from_parent_issue",
            return_value=([node], [], "Parent title"),
        ) as build_nodes,
        patch.object(
            ENG,
            "start",
            return_value=SimpleNamespace(outcome_id="demo", nodes=[node]),
        ),
    ):
        rc = ENG.main(
            [
                "--repo-root",
                str(tmp_path),
                "start",
                "demo",
                "--from-objective",
                "infiquetra/repo#42",
            ]
        )

    assert rc == 0
    build_nodes.assert_called_once_with("infiquetra", "repo", 42)
    assert "deprecated" in capsys.readouterr().err


def test_legacy_python_api_alias_preserves_parent_semantics() -> None:
    subs = [_sub(1, "Build")]
    expected = ENG.nodes_from_parent_issue("o", "r", 100, runner=_runner_for(subs))
    assert ENG.nodes_from_objective("o", "r", 100, runner=_runner_for(subs)) == expected
