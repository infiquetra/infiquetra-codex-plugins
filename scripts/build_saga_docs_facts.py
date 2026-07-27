#!/usr/bin/env python3
"""Build deterministic facts for the Saga family documentation package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_codex_plugins import (  # noqa: E402
    CURRENT_EXPECTED_PLUGINS,
    TARGET_EXPECTED_PLUGINS,
)

CURRENT_SAGA_FAMILY_PLUGINS = ("saga", "mission-control", "verified-workflows", "deploy")
TARGET_SAGA_FAMILY_PLUGINS = ("saga", "mission-control", "verified-workflows", "deploy")
SAGA_FAMILY_PLUGINS = CURRENT_SAGA_FAMILY_PLUGINS

SAGA_ROUTABLE_COMMANDS = (
    "office-hours",
    "ideate",
    "product-review",
    "brainstorm",
    "spec",
    "implementation-spec",
    "plan",
    "doc-review",
    "work",
    "code-review",
    "qa",
    "investigate",
    "founder-review",
    "strategy",
    "optimize",
    "handoff",
    "retro",
    "resume",
    "loop",
)

SAGA_ALIAS_SKILLS = ("ceo-review",)

LIFECYCLE_PHASES = ("ideation", "brainstorm", "plan", "review", "work", "qa", "retro")
PHASE_STATUSES = ("pending", "in_progress", "complete")
THREAD_STATUSES = ("active", "blocked", "paused", "handed-off", "done", "abandoned")

MATURITY_BY_PHASE = {
    "ideation": "idea-ready",
    "brainstorm": "requirements-ready",
    "plan": "plan-ready",
    "review": "plan-ready",
    "work": "resume-ready",
    "qa": "resume-ready",
    "retro": "resume-ready",
}

READINESS_MATURITIES = (
    "idea-ready",
    "experiment-ready",
    "requirements-ready",
    "plan-ready",
    "resume-ready",
    "deferred-context",
)

COMMAND_STATES = {
    "office-hours": "shipped",
    "ideate": "shipped",
    "product-review": "shipped",
    "brainstorm": "shipped",
    "spec": "advisory off-chain shipped",
    "implementation-spec": "advisory off-chain shipped",
    "plan": "shipped",
    "doc-review": "hard gate shipped",
    "work": "shipped",
    "code-review": "shipped",
    "qa": "advisory gate-only shipped",
    "investigate": "advisory off-chain shipped",
    "founder-review": "shipped",
    "strategy": "advisory shipped",
    "optimize": "advisory off-chain shipped",
    "handoff": "shipped envelope",
    "retro": "advisory terminal shipped",
    "resume": "advisory stub",
    "loop": "router re-entry",
}

MAIN_CHAIN = (
    "idea-ready/experiment-ready/requirements-ready",
    "saga:plan",
    "saga:doc-review",
    "saga:work",
    "saga:code-review",
    "saga:qa",
    "saga:handoff or saga:retro",
)

OWNER_BOUNDARIES = {
    "saga": {
        "owns": "lifecycle choice, local Saga state, routing, durable lifecycle artifacts, and handoff envelopes",
        "does_not_own": "issue mutation, deployment mutation, reviewer/validator execution, or another owner's state",
    },
    "mission-control": {
        "owns": "GitHub issues, prepared issue drafts, comments, labels, milestones, project boards, project fields, rollout, and flow metrics",
        "does_not_own": "Saga lifecycle phase authority or deployment tags",
    },
    "verified-workflows": {
        "owns": "root-orchestrated workflow DAGs, logical role execution, selected validators, barriers, and receipt-backed gate evidence",
        "does_not_own": "final mutation approval, lifecycle authority, scope expansion, or deployment ownership",
    },
    "deploy": {
        "owns": "tag promotion, rollback, hotfix, deployment status, release-note previews, and deployment guardrails",
        "does_not_own": "readiness review, issue lifecycle, or code implementation",
    },
}

TARGET_OWNER_BOUNDARIES = dict(OWNER_BOUNDARIES)

REQUIRED_DOCS = (
    "docs/saga/README.md",
    "docs/saga/lifecycle-atlas.md",
    "docs/saga/command-catalog.md",
    "docs/saga/state-and-maturity.md",
    "docs/saga/associated-plugins.md",
    "docs/saga/scenarios.md",
    "docs/saga/markdown-contracts.md",
    "docs/saga/recovery-playbooks.md",
    "docs/saga/quick-reference.md",
)

REQUIRED_VISUAL_ASSETS = (
    "docs/saga/visual-assets/saga-lifecycle-atlas.svg",
    "docs/saga/visual-assets/saga-lifecycle-atlas.png",
    "docs/saga/visual-assets/saga-lifecycle-atlas.pdf",
    "docs/saga/visual-assets/readiness-ladder.svg",
    "docs/saga/visual-assets/ownership-boundaries.svg",
)

REQUIRED_SCENARIOS = (
    "vague idea to plan",
    "experiment-ready prototype to plan",
    "plan-ready issue to PR",
    "PR-ready work through review and QA",
    "handoff issue creation",
    "security-sensitive review escalation",
    "deployment after QA",
    "hotfix flow",
    "stalled Saga recovery",
)


def repo_root_from_script() -> Path:
    return REPO_ROOT


def read_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: missing frontmatter")
    try:
        end = lines[1:].index("---") + 1
    except ValueError as exc:
        raise ValueError(f"{path}: unterminated frontmatter") from exc

    data: dict[str, str] = {}
    current_key: str | None = None
    for line in lines[1:end]:
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current_key is not None:
            data[current_key] = f"{data[current_key]} {line.strip()}".strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        stripped_value = value.strip()
        if stripped_value in {"|", ">", "|-", ">-", "|+", ">+"}:
            stripped_value = ""
        data[current_key] = stripped_value
    return data


def skill_facts(
    repo_root: Path,
    plugin: str,
    inventory: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    inventory = inventory or CURRENT_EXPECTED_PLUGINS
    facts: list[dict[str, str]] = []
    for skill in inventory[plugin]["skills"]:
        path = repo_root / "plugins" / plugin / "skills" / skill / "SKILL.md"
        meta = read_frontmatter(path)
        declared_name = meta.get("name")
        if declared_name != skill:
            raise ValueError(f"{path}: frontmatter name {declared_name!r} != {skill!r}")
        facts.append(
            {
                "name": skill,
                "namespace": f"{plugin}:{skill}",
                "description": meta.get("description", ""),
                "skill_path": path.relative_to(repo_root).as_posix(),
            }
        )
    return facts


def build_facts(repo_root: Path, inventory_mode: str = "current") -> dict[str, Any]:
    if inventory_mode == "current":
        inventory = CURRENT_EXPECTED_PLUGINS
        saga_family_plugins = CURRENT_SAGA_FAMILY_PLUGINS
        owner_boundaries = OWNER_BOUNDARIES
    elif inventory_mode == "target-fixture":
        inventory = TARGET_EXPECTED_PLUGINS
        saga_family_plugins = TARGET_SAGA_FAMILY_PLUGINS
        owner_boundaries = TARGET_OWNER_BOUNDARIES
    else:
        raise ValueError(f"unknown Saga facts inventory mode: {inventory_mode!r}")

    plugins: dict[str, Any] = {}
    for plugin in saga_family_plugins:
        expected = inventory[plugin]
        plugins[plugin] = {
            "version": expected["version"],
            "skills": skill_facts(repo_root, plugin, inventory),
        }

    return {
        "schema_version": "1.0",
        "generated_by": "scripts/build_saga_docs_facts.py",
        "source_files": [
            "scripts/validate_codex_plugins.py",
            "plugins/saga/references/saga-spec.md",
            "plugins/saga/skills/loop/references/dispatch-table.md",
            "plugins/saga/references/formatting-style.md",
        ],
        "plugins": plugins,
        "saga_routing": {
            "routable_commands": list(SAGA_ROUTABLE_COMMANDS),
            "alias_skills": list(SAGA_ALIAS_SKILLS),
            "main_chain": list(MAIN_CHAIN),
            "command_states": COMMAND_STATES,
            "hard_gates": [
                {
                    "name": "doc-review readiness",
                    "owner": "saga:doc-review",
                    "blocks": "saga:work when unresolved P0/P1 findings remain",
                }
            ],
            "advisory_commands": [
                "saga:spec",
                "saga:qa",
                "saga:investigate",
                "saga:strategy",
                "saga:optimize",
                "saga:retro",
                "saga:resume",
            ],
        },
        "state": {
            "lifecycle_phases": list(LIFECYCLE_PHASES),
            "phase_statuses": list(PHASE_STATUSES),
            "thread_statuses": list(THREAD_STATUSES),
            "maturity_by_lifecycle_phase": MATURITY_BY_PHASE,
            "readiness_maturities": list(READINESS_MATURITIES),
            "maturity_storage": "derived-never-stored",
        },
        "owner_boundaries": owner_boundaries,
        "docs_package": {
            "required_docs": list(REQUIRED_DOCS),
            "required_visual_assets": list(REQUIRED_VISUAL_ASSETS),
            "required_scenarios": list(REQUIRED_SCENARIOS),
        },
    }


def dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_or_check(repo_root: Path, check: bool) -> int:
    path = repo_root / "docs" / "saga" / "generated" / "lifecycle-facts.json"
    payload = dumps(build_facts(repo_root, inventory_mode="current"))
    if check:
        if not path.is_file():
            print(f"missing generated facts: {path}", file=sys.stderr)
            return 1
        current = path.read_text(encoding="utf-8")
        if current != payload:
            print(f"stale generated facts: {path}", file=sys.stderr)
            print("run: python3 scripts/build_saga_docs_facts.py", file=sys.stderr)
            return 1
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    print(f"wrote {path.relative_to(repo_root)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated facts are missing or stale")
    parser.add_argument("--repo-root", type=Path, default=repo_root_from_script())
    args = parser.parse_args()
    return write_or_check(args.repo_root.resolve(), args.check)


if __name__ == "__main__":
    raise SystemExit(main())
