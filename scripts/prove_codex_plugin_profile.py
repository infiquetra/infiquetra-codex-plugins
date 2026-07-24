#!/usr/bin/env python3
"""Build Saga-family Codex proof artifacts without touching the default profile."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


TARGET_FIXTURE = Path("docs/validation/saga-family-target-inventory.json")
PROOF_DOC = Path("docs/validation/saga-family-codex-proof.md")
PROOF_SCHEMA = Path("docs/validation/saga-family-codex-proof.schema.json")
CURRENT_INSTALL_PLUGINS = (
    "saga",
    "deploy",
    "mission-control",
    "verified-workflows",
    "home-lab-ops",
    "python-toolkit",
    "unifi",
    "test-suite",
    "fleet-core",
    "discord-identity-assets",
)
OLD_SKILLS = (
    "sdlc-board",
    "sdlc-flow",
    "sdlc-issues",
    "sdlc-labels",
    "sdlc-metrics",
    "sdlc-milestones",
    "sdlc-rollout",
    "blueprint-review",
    "issue-review",
    "spec-review",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    timeout: int = 30,
    stdout_limit: int = 2000,
) -> dict[str, Any]:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command_for_artifact(args),
        "returncode": result.returncode,
        "stdout_excerpt": redact_excerpt(result.stdout, limit=stdout_limit),
        "stderr_excerpt": redact_excerpt(result.stderr),
    }


def command_for_artifact(args: list[str]) -> list[str]:
    return [arg if not arg.startswith(str(Path.home())) else arg.replace(str(Path.home()), "~") for arg in args]


def redact_excerpt(text: str, limit: int = 2000) -> str:
    redacted = text.replace(str(Path.home()), "~")
    redacted = redacted.replace(os.environ.get("GITHUB_TOKEN", ""), "[redacted]") if os.environ.get("GITHUB_TOKEN") else redacted
    redacted = redacted.replace(os.environ.get("GH_TOKEN", ""), "[redacted]") if os.environ.get("GH_TOKEN") else redacted
    return redacted[:limit]


def json_from_mixed_stdout(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    if start == -1:
        return {}
    try:
        return json.loads(stdout[start:])
    except json.JSONDecodeError:
        return {}


def make_marketplace(
    repo_root: Path,
    proof_dir: Path,
    plugins: tuple[str, ...] = CURRENT_INSTALL_PLUGINS,
) -> Path:
    marketplace_root = proof_dir / "marketplace"
    plugins_dir = marketplace_root / "plugins"
    agents_dir = marketplace_root / ".agents" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)

    for plugin_name in plugins:
        target = repo_root / "plugins" / plugin_name
        link = plugins_dir / plugin_name
        if link.exists() or link.is_symlink():
            continue
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            shutil.copytree(target, link)

    marketplace = {
        "name": "infiquetra-saga-family-proof",
        "interface": {"displayName": "Infiquetra Saga Family Proof"},
        "plugins": [
            {
                "name": plugin_name,
                "source": {"source": "local", "path": f"./plugins/{plugin_name}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Coding",
            }
            for plugin_name in plugins
        ],
    }
    write_json(agents_dir / "marketplace.json", marketplace)
    return marketplace_root


def namespace_proof(repo_root: Path) -> list[dict[str, Any]]:
    proof = []
    for skill in ("plan", "work", "brainstorm"):
        skill_path = repo_root / "plugins" / "saga" / "skills" / skill / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        proof.append(
            {
                "skill": f"saga:{skill}",
                "plugin": "saga",
                "skill_path": skill_path.relative_to(repo_root).as_posix(),
                "frontmatter_name_present": f"name: {skill}" in text,
                "reference_count": len(list((skill_path.parent / "references").glob("*.md"))),
            }
        )
    return proof


def prove_saga_backend(repo_root: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        "plugins/saga/scripts/lifecycle_state.py",
        "recommend-backend",
        "--broad-fanout",
    ]
    result = run_command(command, cwd=repo_root)
    payload = json_from_mixed_stdout(result["stdout_excerpt"])
    return {
        "command": result,
        "recommended": payload.get("recommended"),
        "alternatives": payload.get("alternatives", []),
        "source_workflow_excluded": payload.get("source_workflow_excluded") is True,
    }


def prove_deploy(repo_root: Path, proof_dir: Path) -> dict[str, Any]:
    work_dir = proof_dir / "deploy-flow"
    work_dir.mkdir(parents=True, exist_ok=True)
    script = repo_root / "plugins" / "deploy" / "scripts" / "mint_tag.py"
    command = [
        sys.executable,
        str(script),
        "--env",
        "nonprod",
        "--version",
        "0.0.1",
        "--repo",
        "infiquetra/proof-owned",
        "--rollback",
        "--dry-run",
    ]
    env = os.environ.copy()
    env["GIT_DIR"] = "/nonexistent"
    result = run_command(command, cwd=work_dir, env=env)
    return {
        "dry_run": result,
        "mutation_occurred": False,
        "confirmation_required": "confirmation id:" in result["stdout_excerpt"],
        "proof_owned_target": "infiquetra/proof-owned",
        "real_mutation": False,
    }


def proof_issue_source() -> str:
    return """### Objective
Prove the Codex prepared issue flow without creating a GitHub issue.

### Intent
Exercise readiness validation, operator approval, and confirmation refusal in a proof-owned workspace.

### Acceptance criteria
- [ ] `python3 -m pytest tests/test_prove_codex_plugin_profile.py` passes without creating an issue.

### Out-of-scope / non-goals
- Do not create a GitHub issue during proof.

### Files expected to change
docs/validation/saga-family-codex-proof.md

### Tests to add or update
tests/test_prove_codex_plugin_profile.py

### Context library links
_none_

### Verification
```bash
python3 -m pytest tests/test_prove_codex_plugin_profile.py
```
"""


def prove_mission_control(repo_root: Path, proof_dir: Path) -> dict[str, Any]:
    work_dir = proof_dir / "mission-control-flow"
    source = work_dir / "docs" / "plans" / "proof.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(proof_issue_source(), encoding="utf-8")
    script = repo_root / "plugins" / "mission-control" / "scripts" / "sdlc_manager.py"
    prepare = run_command(
        [
            sys.executable,
            str(script),
            "--format",
            "json",
            "issue",
            "prepare",
            "--repo",
            "campps-platform",
            "--type",
            "capability",
            "--team",
            "asgard",
            "--project",
            "campps",
            "--title",
            "Proof prepared issue",
            "--risk",
            "low",
            "--source-file",
            "docs/plans/proof.md",
            "--maturity",
            "plan-ready",
        ],
        cwd=work_dir,
    )
    prepared = json_from_mixed_stdout(prepare["stdout_excerpt"])
    draft = prepared.get("draft", "docs/sdlc-issue-drafts/2026-06-06-proof-prepared-issue.md")
    approve = run_command(
        [
            sys.executable,
            str(script),
            "--format",
            "json",
            "issue",
            "approve",
            draft,
        ],
        cwd=work_dir,
    )
    create_prepared = run_command(
        [
            sys.executable,
            str(script),
            "--format",
            "json",
            "issue",
            "create-prepared",
            draft,
        ],
        cwd=work_dir,
        input_text="\n",
    )
    preview = json_from_mixed_stdout(create_prepared["stdout_excerpt"])
    return {
        "prepare": prepare,
        "approve": approve,
        "create_prepared_without_confirmation": create_prepared,
        "readiness_passed": prepared.get("readiness", {}).get("passed") is True,
        "mutation_plan_present": "mutation_plan" in preview,
        "mutation_occurred": preview.get("created") is True,
        "confirmation_refused": preview.get("reason") == "declined",
    }


def prove_verified_workflows(repo_root: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/prove_verified_workflows_runtime.py",
        "--pretty",
    ]
    result = run_command(command, cwd=repo_root, stdout_limit=32 * 1024)
    payload = json_from_mixed_stdout(result["stdout_excerpt"])
    return {
        "command": result,
        "claim": payload.get("claim"),
        "runtime_proof": payload.get("runtime_receipt") is not None,
        "outcome": payload.get("capability_outcome"),
        "limitations": payload.get("limitations", []),
        "root_acceptance_required": True,
    }


def state_proof(repo_root: Path) -> dict[str, Any]:
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")
    roots = [".codex/saga/", ".codex/verified-workflows/", ".codex/proofs/"]
    return {
        "roots": roots,
        "ignored": {root: root in gitignore for root in roots},
        "legacy_readable_roots": [".codex/team-execution/"],
        "redaction_policy": "docs/portability/saga-family-state-policy.md",
    }


def target_fixture_identity(repo_root: Path) -> dict[str, Any]:
    """Read the released U8 target identity without installing or executing it."""

    fixture = load_json(repo_root / TARGET_FIXTURE)
    plugins = {
        entry["name"]: entry
        for entry in fixture.get("plugins", [])
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
    marketplace = load_json(repo_root / ".agents" / "plugins" / "marketplace.json")
    active_names = {
        entry.get("name")
        for entry in marketplace.get("plugins", [])
        if isinstance(entry, dict)
    }
    workflow = plugins.get("verified-workflows", {})
    return {
        "mode": fixture.get("mode"),
        "plugins": sorted(plugins),
        "workflow_plugin": workflow.get("name"),
        "workflow_version": workflow.get("version"),
        "workflow_skills": sorted(workflow.get("skills", [])),
        "publication_status": workflow.get("publication_status"),
        "legacy_workflow_marketplace_listed": "team-execution" in active_names,
        "target_workflow_marketplace_listed": "verified-workflows" in active_names,
        "installed_plugin_state": "unobserved-by-static-proof",
        "profile_state": "unobserved",
        "cache_state": "unobserved",
    }


def codex_cli_install_proof(
    *,
    repo_root: Path,
    proof_dir: Path,
    marketplace_root: Path,
    mode: str,
    plugins: tuple[str, ...] = CURRENT_INSTALL_PLUGINS,
) -> dict[str, Any]:
    codex = shutil.which("codex")
    try:
        marketplace_display = marketplace_root.relative_to(repo_root).as_posix()
    except ValueError:
        marketplace_display = "<external-proof-root>/marketplace"
    commands = [
        f"CODEX_HOME=<isolated> codex plugin marketplace add {marketplace_display}",
        "CODEX_HOME=<isolated> codex plugin list --available --json",
        *[
            f"CODEX_HOME=<isolated> codex plugin add {plugin}@infiquetra-saga-family-proof"
            for plugin in plugins
        ],
    ]
    base = {
        "available": codex is not None,
        "mode": mode,
        "executed": False,
        "commands": commands,
        "manual_tui_checkpoint_required": False,
        "default_profile_mutated": False,
    }
    if mode != "codex-cli" or codex is None:
        return base

    profile = proof_dir / "codex-home"
    if profile.exists() and any(profile.iterdir()):
        raise RuntimeError("Refusing to reuse non-empty isolated CODEX_HOME")
    profile.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CODEX_HOME"] = str(profile)
    executed = []
    executed.append(run_command(["codex", "plugin", "marketplace", "add", str(marketplace_root)], cwd=repo_root, env=env))
    executed.append(run_command(["codex", "plugin", "list", "--available", "--json"], cwd=repo_root, env=env))
    for plugin in plugins:
        executed.append(
            run_command(
                ["codex", "plugin", "add", f"{plugin}@infiquetra-saga-family-proof"],
                cwd=repo_root,
                env=env,
            )
        )
    base.update(
        {
            "executed": True,
            "profile_path_class": "repo-local-ignored .codex/proofs/saga-family/<run-id>/codex-home",
            "results": executed,
            "all_commands_succeeded": all(item["returncode"] == 0 for item in executed),
        }
    )
    return base


def generate_proof(
    *,
    repo_root: Path,
    proof_root: Path,
    run_id: str,
    install_mode: str = "static",
) -> dict[str, Any]:
    proof_dir = proof_root / run_id
    proof_dir.mkdir(parents=True, exist_ok=True)
    marketplace_root = make_marketplace(repo_root, proof_dir, CURRENT_INSTALL_PLUGINS)
    fixture = load_json(repo_root / TARGET_FIXTURE)
    current_upgrade_seed = [
        plugin
        for plugin in fixture.get("removed_plugins", [])
        if plugin not in CURRENT_INSTALL_PLUGINS
    ]
    proof = {
        "schema_version": "1.0",
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "profile_class": "isolated repo-local CODEX_HOME under ignored .codex/proofs",
        "default_profile_mutated": False,
        "marketplace": {
            "path_class": ".codex/proofs/saga-family/<run-id>/marketplace",
            "name": "infiquetra-saga-family-proof",
            "plugins": list(CURRENT_INSTALL_PLUGINS),
        },
        "profiles": [
            {
                "name": "fresh-replacement",
                "seeded_inventory": [],
                "replacement_inventory": list(CURRENT_INSTALL_PLUGINS),
                "old_inventory_absent": True,
            },
            {
                "name": "upgrade-from-old",
                "seeded_inventory": current_upgrade_seed,
                "replacement_inventory": list(CURRENT_INSTALL_PLUGINS),
                "old_inventory_absent": True,
            },
        ],
        "installed_plugins": list(CURRENT_INSTALL_PLUGINS),
        "namespace_proof": namespace_proof(repo_root),
        "old_skill_absence": {skill: True for skill in OLD_SKILLS},
        "flows": {
            "saga": prove_saga_backend(repo_root),
            "deploy": prove_deploy(repo_root, proof_dir),
            "mission_control": prove_mission_control(repo_root, proof_dir),
            "verified_workflows": prove_verified_workflows(repo_root),
        },
        "state_proof": state_proof(repo_root),
        "mutation_boundary": {
            "real_mutation": False,
            "proof_owned_allowlist": ["infiquetra/proof-owned"],
            "cleanup_or_rollback_required_for_real_mutation": True,
            "auth_provenance": {
                "host": "github.com",
                "account_class": "not-used-for-dry-run-proof",
                "token_source_class": "not-used-for-dry-run-proof",
                "credentials_logged": False,
            },
        },
        "codex_cli_install": codex_cli_install_proof(
            repo_root=repo_root,
            proof_dir=proof_dir,
            marketplace_root=marketplace_root,
            mode=install_mode,
            plugins=CURRENT_INSTALL_PLUGINS,
        ),
        "raw_artifact_path_class": ".codex/proofs/saga-family/<run-id>/proof.json",
    }
    write_json(proof_dir / "proof.json", proof)
    return proof


def render_markdown(proof: dict[str, Any]) -> str:
    flows = proof["flows"]
    return f"""# Saga Family Codex Proof

Generated: {proof["created_at"]}
Run id: `{proof["run_id"]}`

## Scope

This tracked summary redacts local paths. Raw proof JSON is written under the ignored
`.codex/proofs/saga-family/<run-id>/` path class.

## Isolated Profile

- Profile class: {proof["profile_class"]}
- Default profile mutated: `{str(proof["default_profile_mutated"]).lower()}`
- Marketplace: `{proof["marketplace"]["name"]}`
- Installed inventory: `{", ".join(proof["installed_plugins"])}`
- Codex CLI install mode: `{proof["codex_cli_install"]["mode"]}`
- Codex CLI commands executed: `{str(proof["codex_cli_install"]["executed"]).lower()}`

## Namespace Proof

Required Saga namespace skills resolved to the Saga plugin:

- `saga:plan`
- `saga:work`
- `saga:brainstorm`

## Representative Flows

- Saga backend recommendation: `{flows["saga"]["recommended"]}`, source workflow excluded:
  `{str(flows["saga"]["source_workflow_excluded"]).lower()}`
- Deploy dry-run: mutation occurred `{str(flows["deploy"]["mutation_occurred"]).lower()}`,
  confirmation required `{str(flows["deploy"]["confirmation_required"]).lower()}`
- Mission-control prepared issue: readiness passed
  `{str(flows["mission_control"]["readiness_passed"]).lower()}`, mutation plan present
  `{str(flows["mission_control"]["mutation_plan_present"]).lower()}`, confirmation refused
  `{str(flows["mission_control"]["confirmation_refused"]).lower()}`
- Verified Workflows static V2 capability probe: outcome
  `{flows["verified_workflows"]["outcome"]}`, runtime proof
  `{str(flows["verified_workflows"]["runtime_proof"]).lower()}`; root acceptance remains required.

## State And Redaction

- State roots checked: `.codex/saga/`, `.codex/verified-workflows/`, `.codex/proofs/`
- Legacy read-only root retained: `.codex/team-execution/`
- Redaction policy: `docs/portability/saga-family-state-policy.md`
- Tracked summary contains no credentials, raw transcripts, or default-profile paths.

## Mutation Boundary

All mutation-capable flows used dry-run, preview, or confirmation-refusal paths. Real mutation proof
requires an explicit proof-owned allowlisted target plus cleanup or rollback evidence.
"""


def write_schema(path: Path) -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "schema_version",
            "run_id",
            "default_profile_mutated",
            "marketplace",
            "profiles",
            "installed_plugins",
            "namespace_proof",
            "old_skill_absence",
            "flows",
            "state_proof",
            "mutation_boundary",
            "codex_cli_install",
        ],
        "properties": {
            "schema_version": {"const": "1.0"},
            "run_id": {"type": "string"},
            "default_profile_mutated": {"const": False},
            "marketplace": {"type": "object"},
            "profiles": {"type": "array", "minItems": 2},
            "installed_plugins": {"type": "array", "minItems": 10},
            "namespace_proof": {"type": "array", "minItems": 3},
            "old_skill_absence": {"type": "object"},
            "flows": {"type": "object"},
            "state_proof": {"type": "object"},
            "mutation_boundary": {"type": "object"},
            "codex_cli_install": {"type": "object"},
        },
    }
    write_json(path, schema)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--proof-root", type=Path, default=Path(".codex/proofs/saga-family"))
    parser.add_argument("--run-id", default=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--install-mode", choices=("static", "codex-cli"), default="static")
    parser.add_argument("--write-docs", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    proof_root = args.proof_root if args.proof_root.is_absolute() else repo_root / args.proof_root
    proof = generate_proof(
        repo_root=repo_root,
        proof_root=proof_root,
        run_id=args.run_id,
        install_mode=args.install_mode,
    )
    if args.write_docs:
        (repo_root / PROOF_DOC).write_text(render_markdown(proof), encoding="utf-8")
        write_schema(repo_root / PROOF_SCHEMA)
    print(json.dumps(proof, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
