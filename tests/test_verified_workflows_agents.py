from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = ROOT / "plugins" / "verified-workflows"
LEGACY_TREE = "66b23ca83b6ce3b29871954c63a6554c39bfd72e"
RENDERER_PATH = TARGET_ROOT / "scripts" / "render_codex_agents.py"
SYNC_PATH = TARGET_ROOT / "scripts" / "sync_codex_agents.py"


def _load_renderer():
    name = "verified_workflows_u3_integration_renderer"
    spec = importlib.util.spec_from_file_location(name, RENDERER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = _load_renderer()


def _adapt_source_behavior(source: str) -> str:
    lines = source.splitlines()[12:]
    assert lines
    lines[0] = lines[0].lstrip()
    adapted: list[str] = []
    for line in lines:
        if "review-criteria.md" in line:
            continue
        if line.rstrip().endswith("Load rubrics from:"):
            line = line.replace(
                " against these 5 dimensions. Load rubrics from:",
                " using the five preserved dimensions below:",
            )
        adapted.append(
            line.replace(".team-execution.json", ".verified-workflows.json")
            .replace("team-execution", "verified-workflows")
            .replace("Team Execution", "Verified Workflows")
            .replace("CLAUDE.md", "AGENTS.md")
            .replace("Claude", "Codex")
        )
    body = "\n".join(adapted).strip() + "\n"
    body = body.replace(
        "You coordinate only explicitly allowed nonprod automation.\n",
        "You observe only explicitly allowed nonprod automation. The root thread alone may initiate,\n"
        "rerun, cancel, approve, or otherwise mutate a workflow.\n",
    )
    body = body.replace(
        "- No production, staging, force-push, branch deletion, or credential-changing action.\n",
        "- No production, staging, force-push, branch deletion, or credential-changing action.\n"
        "- No workflow dispatch, approval, retry, cancellation, or environment mutation by this role.\n",
    )
    body = body.replace(
        "You are a base reviewer in the `verified-workflows` workflow, always present alongside\n"
        "the security and architecture reviewers.\n",
        "You are always selected as a base logical reviewer alongside the security and architecture\n"
        "reviewers. Your preferred independence may degrade visibly to inline until U4 proves child dispatch.\n",
    )
    body = body.replace(
        "You are a base reviewer in the `verified-workflows` workflow, always present alongside\n"
        "the devil's advocate and security reviewers.\n",
        "You are always selected as a base logical reviewer alongside the devil's advocate and security\n"
        "reviewers. Your preferred independence may degrade visibly to inline until U4 proves child dispatch.\n",
    )
    body = body.replace(
        "You are a base reviewer in the `verified-workflows` workflow, always present alongside\n"
        "the devil's advocate and architecture reviewers.\n",
        "You are always selected as a base logical reviewer alongside the devil's advocate and architecture\n"
        "reviewers. Your preferred independence may degrade visibly to inline until U4 proves child dispatch.\n",
    )
    body = body.replace(
        "- Remote is `github.com/infiquetra/*`.\n",
        "- Remote is `github.com/infiquetra/*`.\n"
        "- The run follows the repository's default-branch model.\n",
    )
    body = body.replace(
        "Report workflow name, run URL or ID, commit SHA, target environment, artifact or endpoint, and\n"
        "rollback notes if available.\n",
        "Report workflow name, run URL or ID, commit SHA, target environment, artifact or endpoint,\n"
        "rollback notes if available, the observed run status, and a separate typed validator gate status.\n",
    )
    return body


def test_all_25_current_role_behaviors_are_digest_bound_and_preserved() -> None:
    registry = R.load_role_registry()
    by_id = {role.role_id: role for role in registry.roles}
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", LEGACY_TREE, "agents"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    source_paths = sorted(path for path in listing if path.endswith(".toml"))

    assert len(source_paths) == 25
    assert {Path(path).stem for path in source_paths} == set(by_id)
    for source_path in source_paths:
        source_text = subprocess.run(
            ["git", "show", f"{LEGACY_TREE}:{source_path}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        role_id = Path(source_path).stem
        source = tomllib.loads(source_text)["developer_instructions"]
        target = (TARGET_ROOT / "roles" / f"{role_id}.md").read_text(encoding="utf-8")
        target_body = target.split("\n---\n", 1)[1].lstrip("\n")
        assert hashlib.sha256(source.encode()).hexdigest() == by_id[role_id].source_behavior_sha256
        assert target_body.startswith(_adapt_source_behavior(source).rstrip("\n"))


def test_renderer_cli_checks_the_committed_five_profile_bundle() -> None:
    result = subprocess.run(
        ["python3", str(RENDERER_PATH), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)

    assert payload["claim"] == "expected-profile-configuration-only"
    assert payload["registry"]["role_count"] == 25
    assert payload["registry"]["role_kind_counts"] == {"agent-lens": 25}
    assert len(payload["profiles"]) == 5
    assert {profile["execution_class"] for profile in payload["profiles"]} == set(
        R.EXPECTED_CLASSES
    )


def test_sync_cli_uses_isolated_codex_home_and_emits_relative_receipt(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    env = {
        **os.environ,
        "FLEET_COMMONS_ROOT": str((ROOT / "plugins" / "fleet-core").resolve()),
    }
    env.pop("CODEX_HOME", None)
    dry = subprocess.run(
        [
            "python3",
            str(SYNC_PATH),
            "--target-dir",
            str(codex_home / "agents"),
            "--isolated-target",
            "--catalog-snapshot",
            str(R.DEFAULT_CATALOG_SNAPSHOT),
            "--dry-run",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    dry_receipt = json.loads(dry.stdout)
    assert dry_receipt["result"] == "planned"
    assert not (codex_home / "agents").exists()

    applied = subprocess.run(
        [
            "python3",
            str(SYNC_PATH),
            "--target-dir",
            str(codex_home / "agents"),
            "--isolated-target",
            "--catalog-snapshot",
            str(R.DEFAULT_CATALOG_SNAPSHOT),
            "--apply",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    receipt = json.loads(applied.stdout)

    assert receipt["result"] == "verified"
    assert receipt["target"] == {
        "kind": "explicit",
        "relative_root": "agents/",
        "real_profile": False,
        "isolated_target": True,
        "real_profile_mutated": False,
    }
    assert receipt["readback"]["verified"] is True
    assert len(list((codex_home / "agents").glob("*.toml"))) == 5
    assert str(tmp_path) not in json.dumps(receipt)


def test_profile_presence_receipt_does_not_claim_runtime_selection() -> None:
    bundle = R.render_bundle(R.load_role_registry(), R.load_catalog_snapshot())
    receipt = R.bundle_receipt(bundle)

    assert receipt["claim"] == "expected-profile-configuration-only"
    assert all("observed_model" not in profile for profile in receipt["profiles"])
    assert all("runtime_selected" not in role for role in receipt["roles"])
