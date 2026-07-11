#!/usr/bin/env python3
"""Validate the Infiquetra Codex plugin repo."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from argparse import ArgumentParser
from pathlib import Path
from typing import Any


_REPO_ROOT_FOR_HINTS = Path(__file__).resolve().parent.parent


def _load_fleet_module(module: str) -> Any:
    """Load one fleet-core module through the canonical repo shim."""

    import sys

    fleet_scripts = _REPO_ROOT_FOR_HINTS / "plugins" / "fleet-core" / "scripts"
    if str(fleet_scripts) not in sys.path:
        sys.path.insert(0, str(fleet_scripts))
    import fleet_commons_shim  # noqa: PLC0415

    return fleet_commons_shim.load(module)


WORKFLOW_COMPAT = _load_fleet_module("workflow_compat")


LEGACY_EXPECTED_PLUGINS: dict[str, dict[str, Any]] = {
    "blueprint-reviewer": {
        "version": "0.1.0",
        "skills": ("blueprint-review", "issue-review", "spec-review"),
    },
    "home-lab-ops": {
        "version": "1.0.0",
        "skills": (
            "ansible-preflight",
            "inventory-sync",
            "monitoring-guard",
            "proxmox-operations",
            "vault-helper",
        ),
    },
    "python-toolkit": {
        "version": "1.0.0",
        "skills": ("python-patterns", "python-project-setup", "python-testing-patterns"),
    },
    "sdlc-manager": {
        "version": "1.4.0",
        "skills": (
            "sdlc-board",
            "sdlc-flow",
            "sdlc-issues",
            "sdlc-labels",
            "sdlc-metrics",
            "sdlc-milestones",
            "sdlc-rollout",
        ),
    },
    "unifi": {
        "version": "1.1.0",
        "skills": ("unifi-network", "unifi-protect"),
    },
    "test-suite": {
        "version": "2.0.0",
        "skills": ("run-quality-checks",),
    },
}

PRE_CUTOVER_EXPECTED_PLUGINS: dict[str, dict[str, Any]] = {
    "saga": {
        "version": "0.75.17+codex.20260711160644",
        "skills": (
            "office-hours",
            "ideate",
            "product-review",
            "brainstorm",
            "spec",
            "implementation-spec",
            "strategy",
            "plan",
            "work",
            "outcome",
            "qa",
            "investigate",
            "retro",
            "resume",
            "handoff",
            "promote",
            "founder-review",
            "ceo-review",
            "doc-review",
            "code-review",
            "optimize",
            "loop",
        ),
    },
    "deploy": {
        "version": "0.1.1",
        "skills": (
            "deploy-state",
            "deploy",
            "deploy-status",
            "deploy-notes",
            "deploy-hotfix",
        ),
    },
    "mission-control": {
        "version": "2.3.0",
        "skills": (
            "board",
            "flow",
            "issues",
            "labels",
            "metrics",
            "milestones",
            "rollout",
        ),
    },
    "team-execution": {
        "version": "2.3.0",
        "skills": ("team-execution", "appsec-audit"),
    },
    "discord-identity-assets": {
        "version": "0.2.0",
        "skills": ("discord-identity-assets",),
    },
    "fleet-core": {
        "version": "0.8.4+codex.20260711134422",
        "skills": (),
        "library": True,
    },
    "home-lab-ops": LEGACY_EXPECTED_PLUGINS["home-lab-ops"],
    "python-toolkit": LEGACY_EXPECTED_PLUGINS["python-toolkit"],
    "unifi": LEGACY_EXPECTED_PLUGINS["unifi"],
    "test-suite": LEGACY_EXPECTED_PLUGINS["test-suite"],
}

TARGET_EXPECTED_PLUGINS: dict[str, dict[str, Any]] = {
    name: spec
    for name, spec in PRE_CUTOVER_EXPECTED_PLUGINS.items()
    if name != "team-execution"
}
TARGET_EXPECTED_PLUGINS["verified-workflows"] = {
    "version": "1.0.0+codex.20260711160140",
    "skills": ("run", "appsec-audit"),
}
CURRENT_ONLY_LEGACY_PLUGINS = {
    "team-execution": PRE_CUTOVER_EXPECTED_PLUGINS["team-execution"],
}

# U8 completed the source and marketplace cutover; current and target inventories now agree.
CURRENT_EXPECTED_PLUGINS = TARGET_EXPECTED_PLUGINS

# Backward-compatible name for current-mode tests and callers.
EXPECTED_PLUGINS = CURRENT_EXPECTED_PLUGINS

CLAUDE_CATALOG = {
    "deploy",
    "discord-identity-assets",
    "docs-generator",
    "fleet-core",
    "home-lab-ops",
    "identity-toolkit",
    "marketplace-lister",
    "mission-control",
    "pagerduty",
    "python-toolkit",
    "redis-channel",
    "saga",
    "sdk-lifecycle",
    "slack",
    "splunk",
    "team-execution",
    "test-suite",
    "todoist-manager",
    "unifi",
}

ALLOWED_STATUSES = {"included", "proof-port", "deferred", "blocked", "unsupported"}
REQUIRED_CUTOVER_TERMS = ("trusted source", "allowlisted inventory", "pins", "rollback")
VALIDATION_MODES = {"current", "target-fixture", "cutover"}
TARGET_FIXTURE = Path("docs/validation/saga-family-target-inventory.json")
ISSUE_CONTRACT_DIR = Path("plugins/mission-control/config/generated")
ISSUE_CONTRACT_ARTIFACTS = (
    Path("issue_contract_data.py"),
    Path("issue_contract_shim.py"),
)
REQUIRED_SAGA_FAMILY_DOCS = (
    Path("docs/portability/source-baseline-saga-family.md"),
    Path("docs/portability/saga-family-capability-map.md"),
    Path("docs/portability/saga-family-known-use-inventory.md"),
)
OLD_ACTIVE_PLUGINS = {"blueprint-reviewer", "sdlc-manager"}
OLD_ACTIVE_SKILLS = {
    "blueprint-review",
    "issue-review",
    "spec-review",
    "sdlc-board",
    "sdlc-flow",
    "sdlc-issues",
    "sdlc-labels",
    "sdlc-metrics",
    "sdlc-milestones",
    "sdlc-rollout",
}
REQUIRED_NAMESPACE_PROOF_SKILLS = {
    "saga:plan",
    "saga:work",
    "saga:brainstorm",
    "verified-workflows:run",
    "verified-workflows:appsec-audit",
}
REQUIRED_STATE_ROOTS = {
    ".codex/saga/",
    WORKFLOW_COMPAT.emit(WORKFLOW_COMPAT.REPO_STATE_ROOT),
}
REQUIRED_LEGACY_STATE_ROOTS = set(
    WORKFLOW_COMPAT.legacy_values(WORKFLOW_COMPAT.REPO_STATE_ROOT)
)
REQUIRED_UNPUBLISHED_PLUGINS: set[str] = set()
REQUIRED_LEGACY_READ_PLUGINS = {"team-execution"}
TARGET_REMOVED_PLUGINS = OLD_ACTIVE_PLUGINS | {"team-execution"}
REQUIRED_MIGRATION_REPLACEMENTS = {
    "sdlc-board": ("mission-control:board",),
    "sdlc-flow": ("mission-control:flow",),
    "sdlc-issues": ("mission-control:issues",),
    "sdlc-labels": ("mission-control:labels",),
    "sdlc-metrics": ("mission-control:metrics",),
    "sdlc-milestones": ("mission-control:milestones",),
    "sdlc-rollout": ("mission-control:rollout",),
    "blueprint-review": ("saga:doc-review", "team-execution:team-execution"),
    "spec-review": ("saga:spec", "saga:doc-review", "team-execution:team-execution"),
    "issue-review": ("saga:doc-review", "mission-control:issues", "team-execution:team-execution"),
}
REQUIRED_ROLLBACK_SPLIT_PHRASES = (
    "partial replacement activation is not a successful merge state",
    "full Saga-family cutover",
    "non-activating preparatory work",
    "rollback",
)

STALE_ACTIVE_PATTERNS = (
    "~/.claude/plugins/cache",
    "infiquetra-claude-plugins/plugins/",
    ".claude-plugin",
    "Claude Code",
    "Claude Code plugin",
    "claude-plugins repository",
)
LINEAGE_ALLOWED_PARTS = {
    "PORTABILITY.md",
    "CHANGELOG.md",
    "docs/portability/provenance.md",
    "docs/portability/source-baseline-saga-family.md",
    "docs/portability/saga-family-capability-map.md",
    "docs/portability/saga-family-known-use-inventory.md",
}
TEAM_EXECUTION_AGENT_MARKER = WORKFLOW_COMPAT.legacy_values(
    WORKFLOW_COMPAT.MANAGED_AGENT_MARKER
)[0]
LEGACY_TEAM_EXECUTION_FILE_COUNT = 52
LEGACY_TEAM_EXECUTION_TREE_SHA256 = (
    "ee3486b96fc07308d089d0cabf09a218ecd3008369c5adb2444e70719c1e8c0e"
)
STAGED_MARKETPLACE_SHA256 = (
    "42803919b39b720599b9692bfdcd95bcfe8c31b06ebb2c976aacaa890fdfea8a"
)
LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256 = (
    "28629cd87365344459eaa028cb494372f704a8a5244ec3b19b7accc63511be75"
)
LEGACY_WORKFLOW_INVENTORY = Path(
    "docs/validation/verified-workflows-legacy-token-inventory.json"
)
LEGACY_WORKFLOW_INVENTORY_EXCLUDED = {
    LEGACY_WORKFLOW_INVENTORY,
    Path("scripts/validate_codex_plugins.py"),
}
LEGACY_WORKFLOW_EXCLUDED_TOP_LEVEL = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    ".codex",
    ".serena",
}
LEGACY_WORKFLOW_EXACT_CLASSIFICATIONS = {
    Path(".agents/plugins/marketplace.json"): "temporary-active-marketplace",
    Path(".gitignore"): "legacy-readable-state-root",
    Path("AGENTS.md"): "current-pre-cutover-inventory",
    Path("README.md"): "migration-documentation",
    Path("pyproject.toml"): "migration-fixture",
    Path("docs/validation.md"): "migration-documentation",
    Path("docs/validation/codex-runtime-capability-snapshot.json"): "historical-evidence",
    Path("docs/validation/saga-family-codex-proof.md"): "migration-documentation",
    Path("docs/validation/saga-family-target-inventory.json"): "legacy-read-metadata",
    Path("plugins/fleet-core/CHANGELOG.md"): "lineage-documentation",
    Path("plugins/fleet-core/PORTABILITY.md"): "lineage-documentation",
    Path("plugins/fleet-core/README.md"): "migration-documentation",
    Path("plugins/fleet-core/references/effort-convention.md"): "lineage-documentation",
    Path("plugins/fleet-core/scripts/fleet_commons/tier_palette.py"): "legacy-parser",
    Path("plugins/fleet-core/scripts/fleet_commons/tier_resolver.py"): "legacy-parser",
    Path("plugins/fleet-core/scripts/fleet_commons/workflow_compat.py"): "compat-registry",
    Path("plugins/saga/CHANGELOG.md"): "lineage-documentation",
    Path("plugins/saga/PORTABILITY.md"): "lineage-documentation",
    Path("plugins/saga/README.md"): "migration-documentation",
    Path("plugins/verified-workflows/README.md"): "migration-documentation",
    Path("plugins/verified-workflows/PORTABILITY.md"): "lineage-documentation",
    Path("plugins/verified-workflows/CHANGELOG.md"): "lineage-documentation",
    Path("scripts/build_legacy_workflow_inventory.py"): "inventory-builder",
    Path("scripts/build_saga_docs_facts.py"): "current-target-projection",
    Path("scripts/capture_codex_runtime_capabilities.py"): "historical-evidence",
    Path("scripts/port_contract.py"): "frozen-source-contract",
    Path("scripts/prove_codex_plugin_profile.py"): "migration-documentation",
    Path("scripts/render_saga_docs_assets.py"): "migration-documentation",
}
LEGACY_WORKFLOW_HISTORICAL_DOC_PARTS = {
    "brainstorms",
    "code-reviews",
    "engineering-journal",
    "ideation",
    "investigations",
    "outcomes",
    "plans",
    "reviews",
    "work-sessions",
}
LEGACY_WORKFLOW_SAGA_WRITERS = {
    Path("plugins/saga/scripts/execution_spec.py"),
    Path("plugins/saga/scripts/lifecycle_state.py"),
    Path("plugins/saga/scripts/manifest_store.py"),
    Path("plugins/saga/scripts/outcome.py"),
    Path("plugins/saga/scripts/outcome_dispatcher.py"),
    Path("plugins/saga/scripts/outcome_spec.py"),
    Path("plugins/saga/scripts/provenance_manifest.py"),
    Path("plugins/saga/scripts/saga.py"),
    Path("plugins/saga/scripts/team_emitter.py"),
}
LEGACY_WORKFLOW_SAGA_READERS = {
    Path("plugins/saga/scripts/override_rate_reader.py"),
    Path("plugins/saga/scripts/team_execution_readiness.py"),
    Path("plugins/saga/scripts/verified_workflow_readiness.py"),
}
LEGACY_WORKFLOW_SAGA_INSTRUCTIONS = {
    Path("plugins/saga/references/execution-spec.md"),
    Path("plugins/saga/references/engine-dispatch.md"),
    Path("plugins/saga/references/operator-choice.md"),
    Path("plugins/saga/references/saga-spec.md"),
    Path("plugins/saga/skills/code-review/SKILL.md"),
    Path("plugins/saga/skills/doc-review/SKILL.md"),
    Path("plugins/saga/skills/founder-review/SKILL.md"),
    Path("plugins/saga/skills/investigate/SKILL.md"),
    Path("plugins/saga/skills/investigate/references/methodology.md"),
    Path("plugins/saga/skills/loop/SKILL.md"),
    Path("plugins/saga/skills/loop/references/drive-and-resume.md"),
    Path("plugins/saga/skills/optimize/SKILL.md"),
    Path("plugins/saga/skills/optimize/references/experiment-loop.md"),
    Path("plugins/saga/skills/outcome/SKILL.md"),
    Path("plugins/saga/skills/plan/SKILL.md"),
    Path("plugins/saga/skills/plan/references/plan-sections.md"),
    Path("plugins/saga/skills/qa/SKILL.md"),
    Path("plugins/saga/skills/resume/SKILL.md"),
    Path("plugins/saga/skills/retro/SKILL.md"),
    Path("plugins/saga/skills/retro/references/self-edit-safety.md"),
    Path("plugins/saga/skills/work/SKILL.md"),
    Path("plugins/saga/skills/work/references/execution-strategy.md"),
}
VALID_LEGACY_WORKFLOW_CLASSIFICATIONS = {
    "compat-registry",
    "compatibility-fixture",
    "current-doc-renderer",
    "current-install-proof",
    "current-pre-cutover-documentation",
    "current-pre-cutover-inventory",
    "current-target-projection",
    "frozen-source-contract",
    "historical-evidence",
    "inventory-builder",
    "legacy-parser",
    "legacy-read-metadata",
    "legacy-readable-state-root",
    "lineage-documentation",
    "migration-documentation",
    "migration-fixture",
    "temporary-active-marketplace",
    "temporary-legacy-test-path",
    "temporary-saga-instructions",
    "temporary-saga-reader",
    "temporary-saga-writer",
}
CUTOVER_DISALLOWED_LEGACY_CLASSIFICATIONS = {
    "temporary-active-marketplace",
    "current-pre-cutover-inventory",
    "temporary-legacy-test-path",
    "current-target-projection",
    "current-install-proof",
    "current-doc-renderer",
    "current-pre-cutover-documentation",
    "temporary-saga-instructions",
    "temporary-saga-writer",
}
LEGACY_WORKFLOW_HISTORY_SENTINELS = {
    "docs/plans/2026-06-30-team-execution-saga-orchestration-repair-plan.md": {
        "sha256": "46027456753e756e33e8e6d48fe372717be31da48e2f754d01e3f95fe1b96d5e",
        "tokens": (
            "## Team Structure",
            "Team Execution",
            "#team-structure",
            ".codex/team-execution/",
            "team-execution",
            "team-execution-delegated",
            "team-execution-serial",
            "team_execution_ref",
            "~/.codex/team-execution/state/",
        ),
    },
    "docs/reviews/2026-06-30-team-execution-saga-orchestration-repair-plan-doc-review.md": {
        "sha256": "4466cda9aae3e714ed224d91e589c8057f04d65970502fb8cece4da32dfdc3a0",
        "tokens": (
            "## Team Structure",
            "Team Execution",
            "team-execution",
            "team_execution_ref",
        ),
    },
    "docs/investigations/2026-06-30-team-execution-saga-orchestration-debug-report.md": {
        "sha256": "ecc08eceda3a67dc81d15b1930753fe236ca7c1ae9b3ad9dd506cdecfb0ac4fa",
        "tokens": (
            "## Team Structure",
            "Team Execution",
            "#team-structure",
            ".codex/team-execution/",
            "team-execution",
            "team-execution-delegated",
            "team-execution-serial",
        ),
    },
}
TEAM_EXECUTION_AGENT_ROSTER = {
    "ai-usefulness-reviewer",
    "api-compat-scanner",
    "api-contract-tester",
    "api-reviewer",
    "architecture-reviewer",
    "clarity-reviewer",
    "code-quality-reviewer",
    "concurrency-tester",
    "dependency-scanner",
    "deploy-watcher",
    "devils-advocate-reviewer",
    "event-flow-tester",
    "github-actions-monitor",
    "iac-cost-scanner",
    "infra-reviewer",
    "performance-tester",
    "privacy-reviewer",
    "runtime-monitor",
    "scenario-tester",
    "sdk-regression-tester",
    "security-reviewer",
    "security-scanner",
    "smoke-tester",
    "testing-reviewer",
    "ui-regression-tester",
}
def _derive_model_hints() -> dict[str, tuple[str, str]]:
    """Derive the lineage->``(codex_model, codex_effort)`` hint map from the fleet-core palette.

    U3: the validator's expectations become a single palette-derived projection instead of a
    second hand-maintained copy of the registry — the roster TOMLs, the palette, and this
    validator are then guaranteed to agree by construction (three-way drift guard). A failure
    to load the palette is fatal for validation, surfaced as an ImportError rather than a
    silently stale literal.
    """
    palette = _load_fleet_module("tier_palette")
    return {model: palette.codex_tier(model) for model in palette.MODELS}


TEAM_EXECUTION_MODEL_HINTS = _derive_model_hints()

SCRIPT_FIELD_RE = re.compile(r"^\s*script:\s*(?P<path>\S+)\s*$", re.MULTILINE)
PLUGIN_SCRIPT_RE = re.compile(r"(?P<path>plugins/[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+\.py)")
MATRIX_ROW_RE = re.compile(r"^\|\s*`(?P<plugin>[^`]+)`\s*\|\s*(?P<status>[a-z-]+)\s*\|")
SOURCE_MODEL_RE = re.compile(r'^# source_model = "(?P<model>[^"]+)"$', re.MULTILINE)
CODEX_MODEL_HINT_RE = re.compile(r'^# codex_model_hint = "(?P<model>[^"]+)"$', re.MULTILINE)


def validate_repository(root: Path, mode: str = "current") -> list[str]:
    errors: list[str] = []
    if mode not in VALIDATION_MODES:
        return [f"unknown validation mode `{mode}`"]

    if mode == "current":
        expected_plugins = CURRENT_EXPECTED_PLUGINS
        validate_marketplace(root, expected_plugins, errors)
        validate_plugins(root, expected_plugins, errors)
        validate_verified_workflows_canonical_surface(root, errors)
        validate_saga_workflow_independence(root, errors)
        validate_legacy_workflow_token_allowlist(root, errors, mode="cutover")
        validate_cutover_evidence(root, mode, errors)
    elif mode == "cutover":
        expected_plugins = TARGET_EXPECTED_PLUGINS
        validate_marketplace(root, expected_plugins, errors)
        validate_plugins(root, expected_plugins, errors)
        validate_verified_workflows_canonical_surface(root, errors)
        validate_saga_workflow_independence(root, errors)
        validate_legacy_workflow_token_allowlist(root, errors, mode="cutover")
        validate_cutover_evidence(root, mode, errors)
    else:
        expected_plugins = TARGET_EXPECTED_PLUGINS
        validate_target_fixture(root, errors)
        validate_plugins(
            root,
            expected_plugins,
            errors,
        )
        validate_verified_workflows_canonical_surface(root, errors)
        validate_saga_workflow_independence(root, errors)

    validate_matrix(root, mode, errors)
    validate_provenance(root, expected_plugins, errors)
    validate_cutover(root, errors)
    validate_issue_contract_parity(root, errors)
    validate_port_contract(
        root,
        "cutover" if mode in {"current", "cutover"} else "classification",
        errors,
    )
    validate_saga_family_docs(root, errors)
    validate_deletion_migration_map(root, errors)
    validate_verified_workflows_agents(root, errors)
    validate_verified_workflows_runtime(root, errors)
    return errors


def validate_port_contract(root: Path, stage: str, errors: list[str]) -> None:
    """Run the offline staged source-port gate without depending on the Claude checkout."""

    try:
        from scripts import port_contract
    except ImportError:
        import port_contract  # type: ignore[no-redef]

    path = root / port_contract.DEFAULT_MANIFEST
    try:
        manifest = port_contract.load_manifest(path)
    except port_contract.ContractError as exc:
        errors.append(f"port contract: {exc}")
        return
    for error in port_contract.validate_manifest(root, manifest, stage=stage):
        errors.append(f"port contract ({stage}): {error}")


def deterministic_tree_digest(path: Path, errors: list[str]) -> tuple[int, str] | None:
    """Hash relative path, mode, size, and content for a contained source tree."""

    if not path.is_dir():
        errors.append(f"legacy source tree missing `{path}`")
        return None
    candidates = sorted(
        child
        for child in path.rglob("*")
        if "__pycache__" not in child.parts and (child.is_file() or child.is_symlink())
    )
    symlinks = [child for child in candidates if child.is_symlink()]
    if symlinks:
        errors.append(
            "legacy source tree must not contain symlinks: "
            f"{[child.relative_to(path).as_posix() for child in symlinks]}"
        )
        return None

    digest = hashlib.sha256()
    for child in candidates:
        try:
            content = child.read_bytes()
            mode = child.stat().st_mode & 0o777
        except OSError as exc:
            errors.append(f"legacy source tree unreadable `{child}`: {exc}")
            return None
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(f"{mode:o}".encode("ascii"))
        digest.update(b"\0")
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return len(candidates), digest.hexdigest()


def validate_staged_workflow_identity(root: Path, errors: list[str]) -> None:
    """Prove the U9 dual-source state without treating both packages as active."""

    marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
    marketplace = load_json(marketplace_path, errors)
    if marketplace is not None:
        raw_entries = marketplace.get("plugins", [])
        entries = raw_entries if isinstance(raw_entries, list) else []
        names = {
            entry.get("name")
            for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get("name"), str)
        }
        active_workflow_ids = names & {"team-execution", "verified-workflows"}
        if active_workflow_ids != {"team-execution"}:
            errors.append(
                "U9 staged marketplace must activate only `team-execution`; "
                f"found={sorted(active_workflow_ids)}"
            )
        try:
            marketplace_sha256 = hashlib.sha256(marketplace_path.read_bytes()).hexdigest()
        except OSError as exc:
            errors.append(f"staged marketplace unreadable: {exc}")
        else:
            if marketplace_sha256 != STAGED_MARKETPLACE_SHA256:
                errors.append(
                    "U9 staged marketplace bytes changed before cutover: "
                    f"expected {STAGED_MARKETPLACE_SHA256}, got {marketplace_sha256}"
                )

    legacy_digest = deterministic_tree_digest(root / "plugins" / "team-execution", errors)
    if legacy_digest is not None:
        file_count, tree_sha256 = legacy_digest
        if (file_count, tree_sha256) != (
            LEGACY_TEAM_EXECUTION_FILE_COUNT,
            LEGACY_TEAM_EXECUTION_TREE_SHA256,
        ):
            errors.append(
                "legacy team-execution source changed during U9 staging: "
                f"expected files={LEGACY_TEAM_EXECUTION_FILE_COUNT} "
                f"sha256={LEGACY_TEAM_EXECUTION_TREE_SHA256}, "
                f"got files={file_count} sha256={tree_sha256}"
            )

    fixture_path = root / TARGET_FIXTURE
    fixture = load_json(fixture_path, errors)
    if fixture is not None:
        unpublished = string_set_field(
            fixture,
            "unpublished_plugins",
            fixture_path,
            errors,
        )
        if unpublished != REQUIRED_UNPUBLISHED_PLUGINS:
            errors.append(
                "target fixture unpublished plugin mismatch: "
                f"expected={sorted(REQUIRED_UNPUBLISHED_PLUGINS)} "
                f"actual={sorted(unpublished)}"
            )
        development_lock = fixture.get("development_lock")
        expected_lock = {
            "active_workflow_plugin": "team-execution",
            "unpublished_workflow_plugin": "verified-workflows",
            "marketplace_sha256": STAGED_MARKETPLACE_SHA256,
            "legacy_source_file_count": LEGACY_TEAM_EXECUTION_FILE_COUNT,
            "legacy_source_tree_sha256": LEGACY_TEAM_EXECUTION_TREE_SHA256,
        }
        if development_lock != expected_lock:
            errors.append("target fixture development_lock does not match U9 staged source truth")

    validate_verified_workflows_canonical_surface(root, errors)
    validate_saga_workflow_independence(root, errors)
    validate_legacy_workflow_token_allowlist(root, errors)


def expected_legacy_workflow_classification(path: Path) -> str | None:
    """Return the required classification for one inventoried legacy-token path."""

    if path == Path("docs/work-sessions/2026-07-11-u5-saga-resume.md"):
        return "historical-evidence"
    if path in LEGACY_WORKFLOW_EXACT_CLASSIFICATIONS:
        return LEGACY_WORKFLOW_EXACT_CLASSIFICATIONS[path]
    if path.parts[:2] == ("plugins", "team-execution"):
        return None
    if path.parts[:4] == (
        "plugins",
        "verified-workflows",
        "tests",
        "fixtures",
    ):
        return "migration-fixture"
    if path.parts[:2] == ("plugins", "saga"):
        if path.parts[:3] == ("plugins", "saga", "tests"):
            return "migration-fixture"
        if path in LEGACY_WORKFLOW_SAGA_WRITERS:
            return "legacy-parser"
        if path in LEGACY_WORKFLOW_SAGA_READERS:
            return "temporary-saga-reader"
        if path in LEGACY_WORKFLOW_SAGA_INSTRUCTIONS:
            return "legacy-parser"
        return None
    if path.parts[:3] == ("plugins", "fleet-core", "tests"):
        return "compatibility-fixture"
    if path.parts and path.parts[0] == "tests":
        return "migration-fixture"
    if path.parts and path.parts[0] == "docs":
        if len(path.parts) > 1 and path.parts[1] in LEGACY_WORKFLOW_HISTORICAL_DOC_PARTS:
            return "historical-evidence"
        if path.parts[:2] == ("docs", "portability"):
            return "lineage-documentation"
        if path.parts[:2] == ("docs", "cutover"):
            return "migration-documentation"
        if path.parts[:2] in {("docs", "saga"), ("docs", "baseline")}:
            return "migration-documentation"
        if path.parts[:2] == ("docs", "validation"):
            return "migration-documentation"
    return None


def workflow_registry_sha256() -> str:
    payload = {
        key: {"canonical": entry.canonical, "legacy": list(entry.legacy)}
        for key, entry in WORKFLOW_COMPAT.REGISTRY.items()
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def serialized_legacy_history_sentinels() -> dict[str, dict[str, Any]]:
    return {
        path: {"sha256": spec["sha256"], "tokens": list(spec["tokens"])}
        for path, spec in LEGACY_WORKFLOW_HISTORY_SENTINELS.items()
    }


def legacy_historical_entries_sha256(entries: list[dict[str, Any]]) -> str:
    historical = sorted(
        (entry for entry in entries if entry.get("classification") == "historical-evidence"),
        key=lambda entry: str(entry.get("path")),
    )
    encoded = json.dumps(historical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_legacy_history_sentinels(root: Path, errors: list[str]) -> None:
    """Keep representative historical evidence byte-stable across inventory refreshes."""

    for raw_path, spec in LEGACY_WORKFLOW_HISTORY_SENTINELS.items():
        path = root / raw_path
        try:
            content = path.read_bytes()
            text = content.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"historical workflow sentinel unreadable `{raw_path}`: {exc}")
            continue
        if hashlib.sha256(content).hexdigest() != spec["sha256"]:
            errors.append(f"historical workflow sentinel digest drifted `{raw_path}`")
        missing = [token for token in spec["tokens"] if token not in text]
        if missing:
            errors.append(
                f"historical workflow sentinel `{raw_path}` missing tokens {missing}"
            )


def legacy_workflow_file_facts(root: Path) -> dict[str, dict[str, Any]]:
    """Return exact token and digest facts, excluding separately bound legacy source."""

    tokens = {
        value
        for spec in WORKFLOW_COMPAT.REGISTRY.values()
        for value in spec.legacy
    }
    facts: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root)
        if (
            (rel.parts and rel.parts[0] in LEGACY_WORKFLOW_EXCLUDED_TOP_LEVEL)
            or "__pycache__" in rel.parts
            or rel in LEGACY_WORKFLOW_INVENTORY_EXCLUDED
            or rel.parts[:2] == ("plugins", "team-execution")
        ):
            continue
        try:
            content = path.read_bytes()
            text = content.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        found = sorted(token for token in tokens if token in text)
        if found:
            facts[rel.as_posix()] = {
                "tokens": found,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
    return facts


def validate_legacy_workflow_token_allowlist(
    root: Path,
    errors: list[str],
    mode: str = "staged",
    *,
    enforce_history_sentinels: bool = True,
) -> None:
    """Require exact, digest-bound classification of every surviving legacy token."""

    if mode not in {"staged", "cutover"}:
        errors.append(f"unknown legacy workflow allowlist mode `{mode}`")
        return
    if enforce_history_sentinels:
        validate_legacy_history_sentinels(root, errors)
    inventory_path = root / LEGACY_WORKFLOW_INVENTORY
    inventory = load_json(inventory_path, errors)
    if inventory is None:
        return
    expected_keys = {
        "schema_version",
        "generated_by",
        "workflow_registry_sha256",
        "legacy_team_execution_tree",
        "history_sentinels",
        "historical_inventory_sha256",
        "entries",
    }
    if set(inventory) != expected_keys:
        errors.append(
            f"{LEGACY_WORKFLOW_INVENTORY}: fields must be {sorted(expected_keys)}"
        )
    if inventory.get("schema_version") != 1:
        errors.append(f"{LEGACY_WORKFLOW_INVENTORY}: schema_version must be 1")
    if inventory.get("generated_by") != "scripts/build_legacy_workflow_inventory.py":
        errors.append(f"{LEGACY_WORKFLOW_INVENTORY}: generated_by is invalid")
    if inventory.get("workflow_registry_sha256") != workflow_registry_sha256():
        errors.append(f"{LEGACY_WORKFLOW_INVENTORY}: workflow registry digest drifted")
    if inventory.get("legacy_team_execution_tree") != {
        "file_count": LEGACY_TEAM_EXECUTION_FILE_COUNT,
        "sha256": LEGACY_TEAM_EXECUTION_TREE_SHA256,
    }:
        errors.append(f"{LEGACY_WORKFLOW_INVENTORY}: legacy source binding drifted")
    if inventory.get("history_sentinels") != serialized_legacy_history_sentinels():
        errors.append(f"{LEGACY_WORKFLOW_INVENTORY}: historical sentinel binding drifted")
    if enforce_history_sentinels and (
        inventory.get("historical_inventory_sha256")
        != LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256
    ):
        errors.append(f"{LEGACY_WORKFLOW_INVENTORY}: historical inventory binding drifted")

    raw_entries = inventory.get("entries")
    if not isinstance(raw_entries, list):
        errors.append(f"{LEGACY_WORKFLOW_INVENTORY}: entries must be a list")
        return
    declared: dict[str, dict[str, Any]] = {}
    entry_keys = {"path", "classification", "tokens", "sha256"}
    for index, entry in enumerate(raw_entries):
        label = f"{LEGACY_WORKFLOW_INVENTORY}: entries[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        if set(entry) != entry_keys:
            errors.append(f"{label} fields must be {sorted(entry_keys)}")
            continue
        raw_path = entry.get("path")
        if not isinstance(raw_path, str):
            errors.append(f"{label}.path must be a string")
            continue
        rel = Path(raw_path)
        if rel.is_absolute() or ".." in rel.parts or rel.as_posix() != raw_path:
            errors.append(f"{label}.path must be a normalized repo-relative path")
            continue
        if raw_path in declared:
            errors.append(f"{label}.path duplicates `{raw_path}`")
            continue
        classification = entry.get("classification")
        required_classification = expected_legacy_workflow_classification(rel)
        if classification not in VALID_LEGACY_WORKFLOW_CLASSIFICATIONS:
            errors.append(f"{label}.classification is invalid")
        elif classification != required_classification:
            errors.append(
                f"{label}.classification must be `{required_classification}`, "
                f"got `{classification}`"
            )
        raw_tokens = entry.get("tokens")
        if (
            not isinstance(raw_tokens, list)
            or not raw_tokens
            or not all(isinstance(token, str) for token in raw_tokens)
            or raw_tokens != sorted(set(raw_tokens))
        ):
            errors.append(f"{label}.tokens must be a sorted unique non-empty string list")
        digest = entry.get("sha256")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            errors.append(f"{label}.sha256 must be lowercase SHA-256")
        declared[raw_path] = entry

    valid_entries = [entry for entry in raw_entries if isinstance(entry, dict)]
    if legacy_historical_entries_sha256(valid_entries) != inventory.get(
        "historical_inventory_sha256"
    ):
        errors.append(f"{LEGACY_WORKFLOW_INVENTORY}: historical entry digest is invalid")

    actual = legacy_workflow_file_facts(root)
    compare_inventory(
        set(actual),
        set(declared),
        "legacy workflow token path inventory",
        errors,
    )
    for raw_path in sorted(set(actual) & set(declared)):
        entry = declared[raw_path]
        if entry.get("tokens") != actual[raw_path]["tokens"]:
            errors.append(f"{raw_path}: legacy workflow token set drifted")
        if entry.get("sha256") != actual[raw_path]["sha256"]:
            errors.append(f"{raw_path}: legacy workflow content digest drifted")
        if (
            mode == "cutover"
            and entry.get("classification") in CUTOVER_DISALLOWED_LEGACY_CLASSIFICATIONS
        ):
            errors.append(
                f"{raw_path}: cutover-active surface retains legacy workflow tokens "
                f"{actual[raw_path]['tokens']} classified as `{entry.get('classification')}`"
            )


def validate_verified_workflows_canonical_surface(root: Path, errors: list[str]) -> None:
    """Reject legacy writes and cross-plugin imports from maintained target surfaces."""

    plugin_root = root / "plugins" / "verified-workflows"
    if not plugin_root.is_dir():
        errors.append("U9 staged source missing `plugins/verified-workflows`")
        return
    symlinks = sorted(path for path in plugin_root.rglob("*") if path.is_symlink())
    for path in symlinks:
        errors.append(
            f"{path.relative_to(root)}: canonical target source must not contain symlinks"
        )
    lineage_docs = {
        plugin_root / "README.md",
        plugin_root / "PORTABILITY.md",
        plugin_root / "CHANGELOG.md",
    }
    legacy_tokens = {
        value
        for spec in WORKFLOW_COMPAT.REGISTRY.values()
        for value in spec.legacy
    }
    candidates = sorted(
        path
        for path in plugin_root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path not in lineage_docs
        and path.name != "fleet_commons_shim.py"
        and expected_legacy_workflow_classification(path.relative_to(root))
        != "migration-fixture"
    )
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"verified-workflows source unreadable `{path}`: {exc}")
            continue
        rel = path.relative_to(root)
        if "TODO" in text:
            errors.append(f"{rel}: unpublished target contains scaffold TODO text")
        for token in sorted(legacy_tokens):
            if token in text:
                errors.append(f"{rel}: canonical target emits legacy token `{token}`")
        if path.suffix == ".py":
            is_test_source = path.is_relative_to(plugin_root / "tests")
            for forbidden in (
                "plugins/team-execution",
                "plugins/saga",
            ):
                if forbidden in text:
                    errors.append(f"{rel}: target source contains cross-plugin import `{forbidden}`")
            try:
                parsed = ast.parse(text, filename=str(path))
            except SyntaxError as exc:
                errors.append(f"{rel}: invalid Python while checking imports: {exc}")
                continue
            imported = {
                alias.name
                for node in ast.walk(parsed)
                if isinstance(node, ast.Import)
                for alias in node.names
            }
            for node in ast.walk(parsed):
                if not isinstance(node, ast.ImportFrom) or node.module is None:
                    continue
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)
            forbidden_imports = {
                name for name in imported if is_cross_plugin_module(name)
            }
            if forbidden_imports and not is_test_source:
                errors.append(
                    f"{rel}: target source directly imports another workflow plugin "
                    f"{sorted(forbidden_imports)}"
                )
            dynamic_imports = sorted(
                name
                for name in imported
                if name == "importlib"
                or name == "importlib.import_module"
                or name.startswith("importlib.util")
                or name.startswith("importlib.machinery")
                or name == "builtins"
                or name.startswith("builtins.__import__")
                or name.startswith("builtins.exec")
                or name.startswith("builtins.eval")
            )
            dangerous_calls = any(
                isinstance(node, ast.Call)
                and (
                    isinstance(node.func, ast.Name)
                    and node.func.id in {"__import__", "exec", "eval"}
                    or isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"__import__", "exec", "eval"}
                )
                for node in ast.walk(parsed)
            )
            import_primitive_string = any(
                isinstance(node, ast.Constant) and node.value == "__import__"
                for node in ast.walk(parsed)
            )
            if not is_test_source and (
                dynamic_imports or dangerous_calls or import_primitive_string
            ):
                errors.append(
                    f"{rel}: dynamic imports are not allowed in canonical target source; "
                    "load shared modules through fleet_commons_shim"
                )

    portability_path = plugin_root / "PORTABILITY.md"
    portability = read_text(portability_path, errors)
    if portability is not None:
        required_sentinel = "This is a behavior adaptation, not an upstream byte-parity claim."
        if required_sentinel not in portability:
            errors.append(
                "verified-workflows/PORTABILITY.md: missing no-upstream-byte-parity sentinel"
            )
        byte_parity_claims = (
            r"(?i)\b(?:claims?|maintains?|provides?)\s+(?:upstream\s+)?byte[- ]parity\b",
            r"(?i)\bbyte-identical\s+to\s+(?:the\s+)?upstream\b",
        )
        if any(re.search(pattern, portability) for pattern in byte_parity_claims):
            errors.append(
                "verified-workflows/PORTABILITY.md: must not claim upstream byte parity"
            )


def validate_verified_workflows_agents(root: Path, errors: list[str]) -> None:
    """Validate the closed U3 role registry and exact five generated profiles."""

    plugin_root = root / "plugins" / "verified-workflows"
    script = plugin_root / "scripts" / "render_codex_agents.py"
    required = (
        script,
        plugin_root / "config" / "role-registry.yaml",
        plugin_root / "roles",
        plugin_root / "agents",
    )
    missing = [path.relative_to(root).as_posix() for path in required if not path.exists()]
    if missing:
        errors.append(f"verified-workflows: U3 role/profile surfaces missing {missing}")
        return
    try:
        environment = {
            **os.environ,
            "FLEET_COMMONS_ROOT": str((root / "plugins" / "fleet-core").resolve()),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        result = subprocess.run(  # noqa: S603 - fixed interpreter and repository script
            [
                sys.executable,
                str(script),
                "--check",
                "--catalog-snapshot",
                str(root / "docs" / "validation" / "codex-runtime-capability-snapshot.json"),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode:
            detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "failed"
            raise RuntimeError(detail)
        receipt = json.loads(result.stdout)
        if receipt.get("claim") != "expected-profile-configuration-only":
            raise RuntimeError("renderer made an unsupported runtime claim")
        if receipt.get("registry", {}).get("role_count") != 25:
            raise RuntimeError("renderer did not preserve exactly 25 logical roles")
        if len(receipt.get("profiles", [])) != 5:
            raise RuntimeError("renderer did not produce exactly five profiles")
        validate_verified_workflows_project_agents(root, receipt, errors)
    except (OSError, RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        errors.append(f"verified-workflows: U3 role/profile validation failed: {exc}")


def validate_verified_workflows_project_agents(
    root: Path,
    render_receipt: dict[str, Any],
    errors: list[str],
) -> None:
    """Bind project-local Codex discovery files to the generated runtime profiles."""

    project_agents = root / ".codex" / "agents"
    try:
        children = list(project_agents.iterdir())
    except OSError as exc:
        errors.append(f".codex/agents: unreadable project agent directory: {exc}")
        return
    rendered = render_receipt.get("profiles")
    if not isinstance(rendered, list):
        errors.append("verified-workflows: renderer profile receipt is invalid")
        return
    expected_names = {
        f"{profile.get('runtime_agent_name')}.toml"
        for profile in rendered
        if isinstance(profile, dict)
        and isinstance(profile.get("runtime_agent_name"), str)
    }
    actual_names = {child.name for child in children}
    if actual_names != expected_names:
        errors.append(
            ".codex/agents: project runtime agent inventory drifted; "
            f"missing={sorted(expected_names - actual_names)} "
            f"unexpected={sorted(actual_names - expected_names)}"
        )
    for profile in rendered:
        if not isinstance(profile, dict):
            errors.append("verified-workflows: renderer profile entry is invalid")
            continue
        runtime_name = profile.get("runtime_agent_name")
        execution_class = profile.get("execution_class")
        if not isinstance(runtime_name, str) or not isinstance(execution_class, str):
            errors.append("verified-workflows: renderer profile identity is invalid")
            continue
        project_path = project_agents / f"{runtime_name}.toml"
        source_path = (
            root / "plugins" / "verified-workflows" / "agents" / f"{runtime_name}.toml"
        )
        if project_path.is_symlink() or not project_path.is_file():
            errors.append(
                f".codex/agents/{runtime_name}.toml: project runtime agent must be a regular file"
            )
            continue
        try:
            if project_path.read_bytes() != source_path.read_bytes():
                errors.append(
                    f".codex/agents/{runtime_name}.toml: project runtime agent bytes "
                    f"drifted from execution class `{execution_class}`"
                )
        except OSError as exc:
            errors.append(
                f".codex/agents/{runtime_name}.toml: runtime agent readback failed: {exc}"
            )


def validate_verified_workflows_runtime(root: Path, errors: list[str]) -> None:
    """Validate the closed U4 hook, workflow, receipt, gate, and proof surfaces."""

    plugin_root = root / "plugins" / "verified-workflows"
    required = (
        plugin_root / "hooks" / "hooks.json",
        plugin_root / "hooks" / "agent_receipt.py",
        plugin_root / "scripts" / "workflow_dispatch.py",
        plugin_root / "scripts" / "dispatch_receipt.py",
        plugin_root / "scripts" / "protected_store.py",
        plugin_root / "scripts" / "workspace_evidence.py",
        plugin_root / "scripts" / "workflow_records.py",
        plugin_root / "scripts" / "named_child_attestation.py",
        plugin_root / "scripts" / "gate_evaluator.py",
        plugin_root / "scripts" / "protocol_probe.py",
        root / "scripts" / "prove_verified_workflows_runtime.py",
        root / "docs" / "validation" / "verified-workflows-runtime-proof.json",
    )
    references = {
        "workflow-protocol.md",
        "gate-policy.md",
        "validator-evidence-state.md",
        "worker-manifest.md",
        "delegation-safety.md",
    }
    reference_root = plugin_root / "skills" / "run" / "references"
    missing = [path.relative_to(root).as_posix() for path in required if not path.is_file()]
    missing.extend(
        (reference_root / name).relative_to(root).as_posix()
        for name in sorted(references)
        if not (reference_root / name).is_file()
    )
    if missing:
        errors.append(f"verified-workflows: U4 runtime surfaces missing {missing}")
        return
    hooks_path = plugin_root / "hooks" / "hooks.json"
    hooks = load_json(hooks_path, errors)
    expected_matcher = "^(review_max|review_high|test_medium|scan_low|monitor_low)$"
    expected_command = 'python3 "$PLUGIN_ROOT/hooks/agent_receipt.py"'
    if not isinstance(hooks, dict) or set(hooks) != {"hooks"}:
        errors.append("verified-workflows hooks: top-level fields must be exactly `hooks`")
    else:
        events = hooks.get("hooks")
        if not isinstance(events, dict) or set(events) != {"SubagentStart", "SubagentStop"}:
            errors.append("verified-workflows hooks: only SubagentStart/Stop are allowed")
        else:
            for event_name, groups in events.items():
                expected_status = (
                    "Recording Verified Workflows agent start"
                    if event_name == "SubagentStart"
                    else "Recording Verified Workflows agent stop"
                )
                valid = (
                    isinstance(groups, list)
                    and len(groups) == 1
                    and isinstance(groups[0], dict)
                    and set(groups[0]) == {"matcher", "hooks"}
                    and groups[0].get("matcher") == expected_matcher
                    and isinstance(groups[0].get("hooks"), list)
                    and len(groups[0]["hooks"]) == 1
                    and isinstance(groups[0]["hooks"][0], dict)
                    and set(groups[0]["hooks"][0])
                    == {"type", "command", "timeout", "statusMessage"}
                    and groups[0]["hooks"][0].get("type") == "command"
                    and groups[0]["hooks"][0].get("command") == expected_command
                    and groups[0]["hooks"][0].get("timeout") == 10
                    and groups[0]["hooks"][0].get("statusMessage") == expected_status
                )
                if not valid:
                    errors.append(
                        f"verified-workflows hooks: {event_name} definition is not closed"
                    )
    proof_path = root / "docs" / "validation" / "verified-workflows-runtime-proof.json"
    proof = load_json(proof_path, errors)
    if proof is None:
        return
    try:
        result = subprocess.run(  # noqa: S603 - fixed repository proof script
            [sys.executable, str(root / "scripts" / "prove_verified_workflows_runtime.py")],
            cwd=root,
            env={
                **os.environ,
                "FLEET_COMMONS_ROOT": str(
                    (root / "plugins" / "fleet-core").resolve()
                ),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode:
            raise RuntimeError("runtime proof script failed")
        expected_proof = json.loads(result.stdout)
        if proof != expected_proof:
            raise RuntimeError("tracked runtime proof is stale")
        if proof.get("capability_outcome") not in {
            "diagnostic",
            "inline-only",
            "auth-unavailable",
        }:
            raise RuntimeError("runtime proof capability outcome is invalid")
        if proof.get("live_invocation_performed") is not False:
            raise RuntimeError("U4 tracked proof must remain a non-mutating characterization")
        if proof.get("runtime_receipt_ref") is not None:
            raise RuntimeError("U4 tracked proof must not claim a live receipt")
        if proof.get("runtime_receipt_sha256") is not None or proof.get(
            "live_envelope_sha256"
        ) is not None:
            raise RuntimeError("U4 tracked proof must not carry live-envelope evidence")
    except (OSError, RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        errors.append(f"verified-workflows: U4 runtime proof validation failed: {exc}")


def is_cross_plugin_module(name: str) -> bool:
    """Return whether an import or constant module name reaches sibling workflow source."""

    normalized = name.replace("-", "_")
    return (
        normalized == "saga"
        or normalized.startswith("saga.")
        or normalized == "team_execution"
        or normalized.startswith("team_execution.")
        or normalized == "plugins.saga"
        or normalized.startswith("plugins.saga.")
        or normalized == "plugins.team_execution"
        or normalized.startswith("plugins.team_execution.")
    )


def static_string_value(node: ast.AST) -> str | None:
    """Fold literal-only string expressions used by dynamic import calls."""

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = static_string_value(node.left)
        right = static_string_value(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            part = static_string_value(value)
            if part is None:
                return None
            parts.append(part)
        return "".join(parts)
    return None


def validate_saga_workflow_independence(root: Path, errors: list[str]) -> None:
    """Reject Saga source dependencies on the separately installed target plugin."""

    saga_root = root / "plugins" / "saga"
    if not saga_root.is_dir():
        errors.append("Saga source missing while checking workflow package independence")
        return
    symlinks = sorted(path for path in saga_root.rglob("*") if path.is_symlink())
    for path in symlinks:
        errors.append(f"{path.relative_to(root)}: Saga source must not contain symlinks")
    for path in sorted(saga_root.rglob("*.py")):
        if (
            path.is_symlink()
            or "tests" in path.relative_to(saga_root).parts
            or "__pycache__" in path.parts
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
            parsed = ast.parse(text, filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            errors.append(f"Saga source unreadable while checking workflow independence `{path}`: {exc}")
            continue
        imported: set[str] = set()
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)
        literal_targets = {
            value
            for node in ast.walk(parsed)
            if (value := static_string_value(node)) is not None
        }
        references = imported | literal_targets
        forbidden = sorted(
            value
            for value in references
            if is_verified_workflows_source_reference(value)
        )
        if forbidden:
            errors.append(
                f"{path.relative_to(root)}: Saga must not import Verified Workflows source "
                f"{forbidden}"
            )


def is_verified_workflows_source_reference(value: str) -> bool:
    normalized = value.replace("-", "_").replace("/", ".")
    return (
        normalized == "verified_workflows"
        or normalized.startswith("verified_workflows.")
        or normalized == "plugins.verified_workflows"
        or normalized.startswith("plugins.verified_workflows.")
    )


def validate_marketplace(
    root: Path,
    expected_plugins: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    path = root / ".agents" / "plugins" / "marketplace.json"
    payload = load_json(path, errors)
    if payload is None:
        return
    plugins = payload.get("plugins")
    if not isinstance(plugins, list):
        errors.append("marketplace.json field `plugins` must be a list")
        return

    seen: set[str] = set()
    for entry in plugins:
        if not isinstance(entry, dict):
            errors.append("marketplace plugin entries must be objects")
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            errors.append("marketplace plugin entry missing string `name`")
            continue
        if name in seen:
            errors.append(f"marketplace contains duplicate plugin entry `{name}`")
        seen.add(name)
        expected_path = f"./plugins/{name}"
        source = entry.get("source")
        if not isinstance(source, dict) or source.get("source") != "local":
            errors.append(f"marketplace entry `{name}` must use local source")
        elif source.get("path") != expected_path:
            errors.append(f"marketplace entry `{name}` path must be `{expected_path}`")
        policy = entry.get("policy")
        if not isinstance(policy, dict) or policy.get("installation") != "AVAILABLE":
            errors.append(f"marketplace entry `{name}` must be installable")

    expected = set(expected_plugins)
    if seen != expected:
        errors.append(
            "marketplace inventory mismatch: "
            f"missing={sorted(expected - seen)} unexpected={sorted(seen - expected)}"
        )


def validate_plugins(
    root: Path,
    expected_plugins: dict[str, dict[str, Any]],
    errors: list[str],
    optional_plugins: dict[str, dict[str, Any]] | None = None,
) -> None:
    plugins_root = root / "plugins"
    actual_plugins = {
        path.name for path in plugins_root.iterdir() if path.is_dir() and not path.name.startswith(".")
    }
    expected_plugin_names = set(expected_plugins)
    optional_plugin_names = set(optional_plugins or {}) - expected_plugin_names
    allowed_plugin_names = expected_plugin_names | optional_plugin_names
    missing_plugins = expected_plugin_names - actual_plugins
    unexpected_plugins = actual_plugins - allowed_plugin_names
    if missing_plugins or unexpected_plugins:
        errors.append(
            "plugin directory inventory mismatch: "
            f"missing={sorted(missing_plugins)} "
            f"unexpected={sorted(unexpected_plugins)}"
        )

    for plugin_name, expected in expected_plugins.items():
        plugin_root = plugins_root / plugin_name
        validate_plugin(root, plugin_root, plugin_name, expected, errors)
    for plugin_name, expected in (optional_plugins or {}).items():
        if plugin_name in expected_plugins:
            continue
        plugin_root = plugins_root / plugin_name
        if plugin_root.exists():
            validate_plugin(root, plugin_root, plugin_name, expected, errors)


def validate_plugin(
    repo_root: Path,
    plugin_root: Path,
    plugin_name: str,
    expected: dict[str, Any],
    errors: list[str],
) -> None:
    if not plugin_root.is_dir():
        errors.append(f"{plugin_name}: missing plugin directory")
        return

    is_library_plugin = expected.get("library", False)

    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = load_json(manifest_path, errors)
    if manifest is not None:
        if manifest.get("name") != plugin_name:
            errors.append(f"{plugin_name}: manifest name mismatch")
        if manifest.get("version") != expected["version"]:
            errors.append(f"{plugin_name}: manifest version must be {expected['version']}")
        if not is_library_plugin:
            if manifest.get("skills") not in ("skills", "./skills/"):
                errors.append(f"{plugin_name}: manifest skills path must resolve to skills")
            interface = manifest.get("interface")
            if not isinstance(interface, dict) or not interface.get("defaultPrompt"):
                errors.append(f"{plugin_name}: manifest interface.defaultPrompt is required")

        for forbidden in (".claude-plugin", "commands"):
            if (plugin_root / forbidden).exists():
                errors.append(f"{plugin_name}: active Codex plugin must not contain `{forbidden}`")
        agents_root = plugin_root / "agents"
        if agents_root.exists():
            if plugin_name == "team-execution":
                validate_team_execution_agents(agents_root, errors)
            elif plugin_name == "verified-workflows":
                pass
            else:
                errors.append(f"{plugin_name}: active Codex plugin must not contain `agents`")

    portability = plugin_root / "PORTABILITY.md"
    if not portability.is_file():
        errors.append(f"{plugin_name}: missing PORTABILITY.md")

    if is_library_plugin:
        # Scripts-only library plugin (e.g. fleet-core): no skills surface to validate.
        return

    skills_root = plugin_root / "skills"
    expected_skills = set(expected["skills"])
    if skills_root.is_dir():
        actual_skills = {path.name for path in skills_root.iterdir() if path.is_dir()}
    else:
        errors.append(f"{plugin_name}: missing skills directory")
        actual_skills = set()
    if actual_skills != expected_skills:
        errors.append(
            f"{plugin_name}: skill inventory mismatch "
            f"missing={sorted(expected_skills - actual_skills)} "
            f"unexpected={sorted(actual_skills - expected_skills)}"
        )

    for skill_name in sorted(expected_skills):
        skill_md = skills_root / skill_name / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{plugin_name}/{skill_name}: missing SKILL.md")
            continue
        text = read_text(skill_md, errors)
        if text is None:
            continue
        frontmatter_name = extract_frontmatter_name(text)
        if frontmatter_name != skill_name:
            errors.append(
                f"{plugin_name}/{skill_name}: frontmatter name must be `{skill_name}`"
            )

    for markdown_path in iter_plugin_markdown_files(plugin_root):
        text = read_text(markdown_path, errors)
        if text is None:
            continue
        validate_active_text(repo_root, markdown_path, text, errors)
        validate_script_references(repo_root, plugin_root, markdown_path, text, errors)


def validate_team_execution_agents(agents_root: Path, errors: list[str]) -> None:
    if not agents_root.is_dir():
        errors.append("team-execution: `agents` must be a directory")
        return

    all_files = sorted(path for path in agents_root.iterdir() if path.is_file())
    non_toml = [path.name for path in all_files if path.suffix != ".toml"]
    if non_toml:
        errors.append(
            "team-execution: agents directory may contain only Codex TOML agents, "
            f"unexpected={non_toml}"
        )

    toml_files = sorted(path for path in all_files if path.suffix == ".toml")
    actual_roster = {path.stem for path in toml_files}
    if actual_roster != TEAM_EXECUTION_AGENT_ROSTER:
        errors.append(
            "team-execution: agent roster mismatch "
            f"missing={sorted(TEAM_EXECUTION_AGENT_ROSTER - actual_roster)} "
            f"unexpected={sorted(actual_roster - TEAM_EXECUTION_AGENT_ROSTER)}"
        )

    for path in toml_files:
        text = path.read_text(encoding="utf-8")
        first_lines = text.splitlines()[:8]
        if TEAM_EXECUTION_AGENT_MARKER not in first_lines:
            errors.append(f"team-execution/{path.name}: missing managed marker")

        source_model_match = SOURCE_MODEL_RE.search(text)
        source_model = source_model_match.group("model") if source_model_match else None
        if source_model is None:
            errors.append(f"team-execution/{path.name}: missing source_model lineage")
        elif source_model not in TEAM_EXECUTION_MODEL_HINTS:
            errors.append(
                f"team-execution/{path.name}: unsupported source_model `{source_model}`"
            )

        codex_model_match = CODEX_MODEL_HINT_RE.search(text)
        codex_model_hint = codex_model_match.group("model") if codex_model_match else None
        if codex_model_hint is None:
            errors.append(f"team-execution/{path.name}: missing codex_model_hint lineage")

        try:
            payload = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            errors.append(f"team-execution/{path.name}: invalid TOML: {exc}")
            continue

        if payload.get("name") != path.stem:
            errors.append(f"team-execution/{path.name}: name must match filename stem")
        if "model" in payload:
            errors.append(
                f"team-execution/{path.name}: use codex_model_hint lineage, not direct model pin"
            )
        developer_instructions = payload.get("developer_instructions")
        if not isinstance(developer_instructions, str) or not developer_instructions.strip():
            errors.append(f"team-execution/{path.name}: developer_instructions required")
        if source_model in TEAM_EXECUTION_MODEL_HINTS:
            expected_hint, expected_effort = TEAM_EXECUTION_MODEL_HINTS[source_model]
            if codex_model_hint != expected_hint:
                errors.append(
                    f"team-execution/{path.name}: codex_model_hint must be `{expected_hint}`"
                )
            if payload.get("model_reasoning_effort") != expected_effort:
                errors.append(
                    f"team-execution/{path.name}: model_reasoning_effort must be "
                    f"`{expected_effort}`"
                )


def validate_active_text(repo_root: Path, path: Path, text: str, errors: list[str]) -> None:
    rel = path.relative_to(repo_root)
    if lineage_allowed(rel):
        return
    for pattern in STALE_ACTIVE_PATTERNS:
        if pattern in text:
            errors.append(f"{rel}: contains stale host reference `{pattern}`")


def lineage_allowed(rel: Path) -> bool:
    rel_text = rel.as_posix()
    if rel.name in LINEAGE_ALLOWED_PARTS:
        return True
    return rel_text in LINEAGE_ALLOWED_PARTS


def iter_plugin_markdown_files(plugin_root: Path) -> list[Path]:
    candidates = [plugin_root / "README.md", plugin_root / "PORTABILITY.md"]
    skills_root = plugin_root / "skills"
    if skills_root.is_dir():
        candidates.extend(sorted(skills_root.rglob("*.md")))
    references_root = plugin_root / "references"
    if references_root.is_dir():
        candidates.extend(sorted(references_root.rglob("*.md")))
    return [path for path in candidates if path.is_file()]


def validate_script_references(
    repo_root: Path,
    plugin_root: Path,
    path: Path,
    text: str,
    errors: list[str],
) -> None:
    for match in SCRIPT_FIELD_RE.finditer(text):
        raw_path = match.group("path").strip("'\"")
        validate_relative_file(path.parent, plugin_root, raw_path, path, errors)

    for match in PLUGIN_SCRIPT_RE.finditer(text):
        raw_path = match.group("path")
        validate_relative_file(repo_root, plugin_root.parent.parent, raw_path, path, errors)


def validate_relative_file(
    base_dir: Path,
    allowed_root: Path,
    raw_path: str,
    source_path: Path,
    errors: list[str],
) -> None:
    candidate = Path(raw_path)
    rel_source = source_path.relative_to(allowed_root.parent if allowed_root.name == "plugins" else allowed_root)
    if candidate.is_absolute() or ".." in candidate.parts:
        errors.append(f"{rel_source}: script reference `{raw_path}` must stay inside package")
        return
    resolved = (base_dir / candidate).resolve()
    if not resolved.is_relative_to(allowed_root.resolve()):
        errors.append(f"{rel_source}: script reference `{raw_path}` escapes package")
        return
    if not resolved.is_file():
        errors.append(f"{rel_source}: script reference `{raw_path}` points to missing file")


def validate_matrix(root: Path, mode: str, errors: list[str]) -> None:
    path = root / "docs" / "portability" / "matrix.md"
    text = read_text(path, errors)
    if text is None:
        return

    rows: dict[str, str] = {}
    for line in text.splitlines():
        match = MATRIX_ROW_RE.match(line)
        if match:
            rows[match.group("plugin")] = match.group("status")

    if set(rows) != CLAUDE_CATALOG:
        errors.append(
            "portability matrix catalog mismatch: "
            f"missing={sorted(CLAUDE_CATALOG - set(rows))} "
            f"unexpected={sorted(set(rows) - CLAUDE_CATALOG)}"
        )
    bad_statuses = {plugin: status for plugin, status in rows.items() if status not in ALLOWED_STATUSES}
    if bad_statuses:
        errors.append(f"portability matrix has invalid statuses: {bad_statuses}")
    if rows.get("team-execution") == "blocked":
        errors.append("team-execution must not remain blocked in the Saga-family matrix")
    if mode != "current":
        for plugin_name in ("saga", "deploy", "mission-control", "team-execution"):
            if rows.get(plugin_name) not in {"included", "proof-port"}:
                errors.append(f"{plugin_name} must be included or proof-port for {mode}")
    for required in ("Verified:", "Review trigger:", "Source snapshot:"):
        if required not in text:
            errors.append(f"portability matrix missing `{required}`")


def validate_provenance(
    root: Path,
    expected_plugins: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    path = root / "docs" / "portability" / "provenance.md"
    text = read_text(path, errors)
    if text is None:
        return
    for plugin_name in expected_plugins:
        if f"`{plugin_name}`" not in text:
            errors.append(f"provenance missing `{plugin_name}`")
    if "Proof-Port Recipe" not in text or "test-suite" not in text:
        errors.append("provenance missing test-suite proof-port recipe")


def validate_target_fixture(root: Path, errors: list[str]) -> None:
    path = root / TARGET_FIXTURE
    payload = load_json(path, errors)
    if payload is None:
        return
    validate_target_fixture_payload(payload, path, errors)


def string_set_field(
    payload: dict[str, Any],
    field: str,
    path: Path,
    errors: list[str],
) -> set[str]:
    """Read one JSON string-list field without letting malformed fixtures crash validation."""

    value = payload.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{path}: field `{field}` must be a list of strings")
        return set()
    return set(value)


def validate_target_fixture_payload(
    payload: dict[str, Any],
    path: Path,
    errors: list[str],
) -> None:
    if payload.get("schema_version") != "2.0":
        errors.append(f"{path}: schema_version must be `2.0`")
    plugins = payload.get("plugins")
    if not isinstance(plugins, list):
        errors.append(f"{path}: field `plugins` must be a list")
        return

    actual_plugins: dict[str, dict[str, Any]] = {}
    for entry in plugins:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            errors.append(f"{path}: plugin entries must be objects with string names")
            continue
        if entry["name"] in actual_plugins:
            errors.append(f"{path}: duplicate plugin entry `{entry['name']}`")
        actual_plugins[entry["name"]] = entry

    compare_inventory(
        set(actual_plugins),
        set(TARGET_EXPECTED_PLUGINS),
        "target fixture plugin inventory",
        errors,
    )

    for plugin_name, expected in TARGET_EXPECTED_PLUGINS.items():
        entry = actual_plugins.get(plugin_name)
        if entry is None:
            continue
        if entry.get("version") != expected["version"]:
            errors.append(
                f"{path}: {plugin_name} version must be {expected['version']}"
            )
        if plugin_name == "verified-workflows" and entry.get("publication_status") != "released":
            errors.append(f"{path}: verified-workflows must be marked released after U8")
        skills = entry.get("skills")
        if not isinstance(skills, list) or not all(isinstance(skill, str) for skill in skills):
            errors.append(f"{path}: {plugin_name} skills must be a list of strings")
            continue
        compare_inventory(
            set(skills),
            set(expected["skills"]),
            f"target fixture {plugin_name} skills",
            errors,
        )
        forbidden_dirs = (
            (".claude-plugin", "commands")
            if plugin_name == "verified-workflows"
            else (".claude-plugin", "commands", "agents")
        )
        raw_forbidden_dirs = entry.get("forbidden_active_dirs", [])
        if not isinstance(raw_forbidden_dirs, list) or not all(
            isinstance(item, str) for item in raw_forbidden_dirs
        ):
            errors.append(f"{path}: {plugin_name} forbidden_active_dirs must be strings")
            raw_forbidden_dirs = []
        for forbidden in forbidden_dirs:
            if forbidden in raw_forbidden_dirs:
                continue
            errors.append(f"{path}: {plugin_name} must forbid active `{forbidden}` directories")
    removed_plugins = string_set_field(payload, "removed_plugins", path, errors)
    compare_inventory(
        removed_plugins,
        TARGET_REMOVED_PLUGINS,
        "target fixture removed plugins",
        errors,
    )

    unpublished_plugins = string_set_field(payload, "unpublished_plugins", path, errors)
    compare_inventory(
        unpublished_plugins,
        REQUIRED_UNPUBLISHED_PLUGINS,
        "target fixture unpublished plugins",
        errors,
    )
    legacy_read_plugins = string_set_field(payload, "legacy_readable_plugins", path, errors)
    compare_inventory(
        legacy_read_plugins,
        REQUIRED_LEGACY_READ_PLUGINS,
        "target fixture legacy-readable plugins",
        errors,
    )

    namespace_proof = string_set_field(payload, "required_namespace_proof", path, errors)
    compare_inventory(
        namespace_proof,
        REQUIRED_NAMESPACE_PROOF_SKILLS,
        "target fixture namespace proof skills",
        errors,
    )

    state_roots = string_set_field(payload, "required_state_roots", path, errors)
    compare_inventory(
        state_roots,
        REQUIRED_STATE_ROOTS,
        "target fixture canonical state roots",
        errors,
    )
    legacy_state_roots = string_set_field(
        payload,
        "legacy_readable_state_roots",
        path,
        errors,
    )
    compare_inventory(
        legacy_state_roots,
        REQUIRED_LEGACY_STATE_ROOTS,
        "target fixture legacy-readable state roots",
        errors,
    )

    mutation_plugins = string_set_field(payload, "mutation_gate_plugins", path, errors)
    required_mutation_plugins = {"deploy", "mission-control", "discord-identity-assets"}
    compare_inventory(
        mutation_plugins,
        required_mutation_plugins,
        "target fixture mutation-gated plugins",
        errors,
    )


def validate_saga_family_docs(root: Path, errors: list[str]) -> None:
    for rel_path in REQUIRED_SAGA_FAMILY_DOCS:
        path = root / rel_path
        if read_text(path, errors) is None:
            continue

    disposition_text = ""
    for rel_path in (
        Path("docs/portability/saga-family-capability-map.md"),
        Path("docs/portability/saga-family-known-use-inventory.md"),
    ):
        text = read_text(root / rel_path, errors)
        if text is not None:
            disposition_text += text

    for skill in sorted(OLD_ACTIVE_SKILLS):
        if f"`{skill}`" not in disposition_text and skill not in disposition_text:
            errors.append(f"saga-family disposition docs missing `{skill}`")

    matrix = read_text(root / "docs" / "portability" / "matrix.md", errors)
    if matrix is not None and "| `team-execution` | blocked |" in matrix:
        errors.append("portability matrix still marks team-execution as blocked")


def validate_cutover_evidence(root: Path, mode: str, errors: list[str]) -> None:
    proof_doc = root / "docs" / "validation" / "saga-family-codex-proof.md"
    proof_schema = root / "docs" / "validation" / "saga-family-codex-proof.schema.json"
    rollback_doc = root / "docs" / "cutover" / "saga-family-rollback-and-split.md"
    modernization_doc = (
        root / "docs" / "portability" / "codex-plugin-modernization-cutover-and-rollback.md"
    )
    modernization_record = (
        root / "docs" / "validation" / "codex-plugin-modernization-cutover.json"
    )
    for path in (
        proof_doc,
        proof_schema,
        rollback_doc,
        modernization_doc,
        modernization_record,
    ):
        if not path.is_file():
            errors.append(f"cutover evidence missing `{path.relative_to(root)}`")

    schema = load_json(proof_schema, errors)
    if schema is not None:
        required = set(schema.get("required", []))
        missing = {
            "schema_version",
            "run_id",
            "default_profile_mutated",
            "installed_plugins",
            "namespace_proof",
            "old_skill_absence",
            "flows",
            "state_proof",
            "mutation_boundary",
            "codex_cli_install",
        } - required
        if missing:
            errors.append(f"proof schema missing required fields: {sorted(missing)}")

    rollback_text = read_text(rollback_doc, errors)
    if rollback_text is not None:
        lower = rollback_text.lower()
        for phrase in REQUIRED_ROLLBACK_SPLIT_PHRASES:
            if phrase.lower() not in lower:
                errors.append(
                    f"{rollback_doc.relative_to(root)} missing rollback/split phrase `{phrase}`"
                )

    validate_modernization_cutover_record(root, modernization_record, mode, errors)


def validate_modernization_cutover_record(
    root: Path,
    path: Path,
    mode: str,
    errors: list[str],
) -> None:
    payload = load_json(path, errors)
    if payload is None:
        return
    expected_keys = {
        "schema_version",
        "recorded_at",
        "source_head",
        "status",
        "versions",
        "rollback_bundle",
        "pre_state",
        "clean_home_lane",
        "seeded_migration_lane",
        "real_profile",
        "sanitization",
    }
    if set(payload) != expected_keys:
        errors.append(f"{path.relative_to(root)} fields must be {sorted(expected_keys)}")
    if payload.get("schema_version") != 1:
        errors.append(f"{path.relative_to(root)} schema_version must be 1")
    source_head = payload.get("source_head")
    if not isinstance(source_head, str) or re.fullmatch(r"[0-9a-f]{40}", source_head) is None:
        errors.append(f"{path.relative_to(root)} source_head must be a full commit")
    else:
        resolved = subprocess.run(
            ["git", "rev-parse", source_head],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", source_head, "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if resolved.returncode != 0 or resolved.stdout.strip() != source_head:
            errors.append(f"{path.relative_to(root)} source_head is unavailable")
        elif ancestor.returncode != 0:
            errors.append(f"{path.relative_to(root)} source_head is not current history")
    expected_versions = {
        "fleet-core": TARGET_EXPECTED_PLUGINS["fleet-core"]["version"],
        "saga": TARGET_EXPECTED_PLUGINS["saga"]["version"],
        "verified-workflows": TARGET_EXPECTED_PLUGINS["verified-workflows"]["version"],
        "retired-team-execution": "2.3.0",
    }
    if payload.get("versions") != expected_versions:
        errors.append(f"{path.relative_to(root)} version readback is stale")
    rollback = payload.get("rollback_bundle")
    if not isinstance(rollback, dict) or rollback.get("sha256") != (
        "03d6193260328b9e880dd3f0b64737fda565591ed8eb948f020e92538b038563"
    ):
        errors.append(f"{path.relative_to(root)} rollback bundle digest is invalid")
    elif (
        rollback.get("directory_mode") != "0700"
        or rollback.get("archive_mode") != "0600"
        or rollback.get("restore_shape_validated") is not True
        or rollback.get("committed") is not False
    ):
        errors.append(f"{path.relative_to(root)} rollback bundle policy is invalid")
    clean = payload.get("clean_home_lane")
    if not isinstance(clean, dict) or (
        clean.get("plugin_cli_commands_succeeded") is not True
        or clean.get("installed_plugin_count") != 10
        or clean.get("legacy_workflow_active") is not False
        or clean.get("canonical_workflow_active") is not True
        or clean.get("profile_counts")
        != {"canonical": 5, "legacy": 0, "unmanaged": 0}
        or clean.get("isolated_credentials_copied") is not False
    ):
        errors.append(f"{path.relative_to(root)} clean-home evidence is invalid")
    seeded = payload.get("seeded_migration_lane")
    if not isinstance(seeded, dict) or (
        seeded.get("plugin_pre_sha256") != seeded.get("plugin_restored_sha256")
        or seeded.get("plugin_archive_pre_sha256")
        != seeded.get("plugin_archive_restored_sha256")
        or seeded.get("profile_pre_state_sha256")
        != seeded.get("profile_restored_sha256")
        or seeded.get("profile_archive_pre_sha256")
        != seeded.get("profile_archive_restored_sha256")
        or seeded.get("duplicate_workflow_surface") is not False
        or seeded.get("rollback_exact") is not True
    ):
        errors.append(f"{path.relative_to(root)} seeded migration/rollback evidence is invalid")
    sanitization = payload.get("sanitization")
    if not isinstance(sanitization, dict) or set(sanitization.values()) != {False}:
        errors.append(f"{path.relative_to(root)} sanitization declaration is invalid")
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        raw_text = ""
    if any(token in raw_text for token in ('/Users/', 'file://', '"HOME"', '"CODEX_HOME"')):
        errors.append(f"{path.relative_to(root)} contains an unsanitized local value")
    real = payload.get("real_profile")
    if not isinstance(real, dict):
        errors.append(f"{path.relative_to(root)} real_profile must be an object")
    elif mode in {"current", "cutover"} and (
        payload.get("status") != "cutover-complete"
        or real.get("apply_started") is not True
        or real.get("applied") is not True
        or real.get("fresh_session") != "passed"
        or not isinstance(real.get("installed_readback"), dict)
        or not isinstance(real.get("profile_readback"), dict)
    ):
        errors.append(f"{path.relative_to(root)} real-profile cutover evidence is incomplete")


def validate_deletion_migration_map(root: Path, errors: list[str]) -> None:
    docs = (
        root / "README.md",
        root / "docs" / "cutover" / "cache-replacement.md",
        root / "docs" / "cutover" / "saga-family-rollback-and-split.md",
        root / "docs" / "portability" / "saga-family-capability-map.md",
        root / "docs" / "portability" / "saga-family-known-use-inventory.md",
    )
    text_parts = []
    for path in docs:
        text = read_text(path, errors)
        if text is not None:
            text_parts.append(text)
    combined = "\n".join(text_parts)

    for skill, replacements in REQUIRED_MIGRATION_REPLACEMENTS.items():
        if f"`{skill}`" not in combined and skill not in combined:
            errors.append(f"migration docs missing old invocation `{skill}`")
        for replacement in replacements:
            if f"`{replacement}`" not in combined and replacement not in combined:
                errors.append(
                    f"migration docs missing replacement `{replacement}` for `{skill}`"
                )


def compare_inventory(
    actual: set[str],
    expected: set[str],
    label: str,
    errors: list[str],
) -> None:
    if actual != expected:
        errors.append(
            f"{label} mismatch: missing={sorted(expected - actual)} "
            f"unexpected={sorted(actual - expected)}"
        )


def validate_cutover(root: Path, errors: list[str]) -> None:
    path = root / "docs" / "cutover" / "cache-replacement.md"
    text = read_text(path, errors)
    if text is None:
        return
    lower = text.lower()
    for term in REQUIRED_CUTOVER_TERMS:
        if term not in lower:
            errors.append(f"cutover doc missing `{term}` gate")


def validate_issue_contract_parity(root: Path, errors: list[str]) -> None:
    """Ensure vendored Mission Control issue-contract artifacts match sidecars."""

    generated_dir = root / ISSUE_CONTRACT_DIR
    check_script = generated_dir / "check_issue_contract_parity.py"
    if not check_script.is_file():
        errors.append(f"issue-contract parity check missing `{check_script.relative_to(root)}`")

    for rel_artifact in ISSUE_CONTRACT_ARTIFACTS:
        artifact = generated_dir / rel_artifact
        sidecar = artifact.with_suffix(artifact.suffix + ".sha256")
        if not artifact.is_file():
            errors.append(f"issue-contract artifact missing `{artifact.relative_to(root)}`")
            continue
        if not sidecar.is_file():
            errors.append(f"issue-contract hash sidecar missing `{sidecar.relative_to(root)}`")
            continue
        try:
            actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
            expected = sidecar.read_text(encoding="utf-8").strip()
        except OSError as exc:
            errors.append(f"issue-contract artifact unreadable `{artifact.relative_to(root)}`: {exc}")
            continue
        if actual != expected:
            errors.append(
                f"issue-contract hash mismatch for `{artifact.relative_to(root)}`: "
                f"expected {expected}, got {actual}"
            )


def extract_frontmatter_name(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    frontmatter = text[4:end]
    for line in frontmatter.splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


def load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    text = read_text(path, errors)
    if text is None:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path}: JSON root must be an object")
        return None
    return payload


def read_text(path: Path, errors: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: unable to read: {exc}")
        return None


def main() -> int:
    parser = ArgumentParser(description="Validate the Infiquetra Codex plugin repo.")
    parser.add_argument(
        "--mode",
        choices=sorted(VALIDATION_MODES),
        default="current",
        help="Validation mode. Defaults to current active inventory.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    errors = validate_repository(repo_root, mode=args.mode)
    if errors:
        print(f"Codex plugin validation failed ({args.mode}):")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Codex plugin validation passed ({args.mode}): {repo_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
