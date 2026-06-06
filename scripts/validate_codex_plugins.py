#!/usr/bin/env python3
"""Validate the Infiquetra Codex plugin repo."""

from __future__ import annotations

import json
import re
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any


CURRENT_EXPECTED_PLUGINS: dict[str, dict[str, Any]] = {
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
        "version": "1.0.0",
        "skills": ("unifi-network", "unifi-protect"),
    },
    "test-suite": {
        "version": "2.0.0",
        "skills": ("run-quality-checks",),
    },
}

TARGET_EXPECTED_PLUGINS: dict[str, dict[str, Any]] = {
    "saga": {
        "version": "0.19.0",
        "skills": (
            "office-hours",
            "ideate",
            "brainstorm",
            "spec",
            "strategy",
            "plan",
            "work",
            "qa",
            "investigate",
            "retro",
            "resume",
            "handoff",
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
        "version": "2.0.0",
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
        "version": "2.0.0",
        "skills": ("team-execution", "appsec-audit"),
    },
    "home-lab-ops": CURRENT_EXPECTED_PLUGINS["home-lab-ops"],
    "python-toolkit": CURRENT_EXPECTED_PLUGINS["python-toolkit"],
    "unifi": CURRENT_EXPECTED_PLUGINS["unifi"],
    "test-suite": CURRENT_EXPECTED_PLUGINS["test-suite"],
}

# Backward-compatible name for current-mode tests and callers.
EXPECTED_PLUGINS = CURRENT_EXPECTED_PLUGINS

CLAUDE_CATALOG = {
    "deploy",
    "docs-generator",
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
REQUIRED_NAMESPACE_PROOF_SKILLS = {"saga:plan", "saga:work", "saga:brainstorm"}
REQUIRED_STATE_ROOTS = {".codex/saga/", ".codex/team-execution/"}

STALE_ACTIVE_PATTERNS = (
    "~/.claude/plugins/cache",
    "infiquetra-claude-plugins/plugins/",
    ".claude-plugin",
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

SCRIPT_FIELD_RE = re.compile(r"^\s*script:\s*(?P<path>\S+)\s*$", re.MULTILINE)
PLUGIN_SCRIPT_RE = re.compile(r"(?P<path>plugins/[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+\.py)")
MATRIX_ROW_RE = re.compile(r"^\|\s*`(?P<plugin>[^`]+)`\s*\|\s*(?P<status>[a-z-]+)\s*\|")


def validate_repository(root: Path, mode: str = "current") -> list[str]:
    errors: list[str] = []
    if mode not in VALIDATION_MODES:
        return [f"unknown validation mode `{mode}`"]

    if mode == "current":
        expected_plugins = CURRENT_EXPECTED_PLUGINS
        validate_marketplace(root, expected_plugins, errors)
        validate_plugins(
            root,
            expected_plugins,
            errors,
            optional_plugins=TARGET_EXPECTED_PLUGINS,
        )
    elif mode == "cutover":
        expected_plugins = TARGET_EXPECTED_PLUGINS
        validate_marketplace(root, expected_plugins, errors)
        validate_plugins(root, expected_plugins, errors)
        validate_cutover_evidence(root, errors)
    else:
        expected_plugins = TARGET_EXPECTED_PLUGINS
        validate_target_fixture(root, errors)

    validate_matrix(root, mode, errors)
    validate_provenance(root, expected_plugins, errors)
    validate_cutover(root, errors)
    if mode != "current":
        validate_saga_family_docs(root, errors)
    return errors


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

    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = load_json(manifest_path, errors)
    if manifest is not None:
        if manifest.get("name") != plugin_name:
            errors.append(f"{plugin_name}: manifest name mismatch")
        if manifest.get("version") != expected["version"]:
            errors.append(f"{plugin_name}: manifest version must be {expected['version']}")
        if manifest.get("skills") not in ("skills", "./skills/"):
            errors.append(f"{plugin_name}: manifest skills path must resolve to skills")
        interface = manifest.get("interface")
        if not isinstance(interface, dict) or not interface.get("defaultPrompt"):
            errors.append(f"{plugin_name}: manifest interface.defaultPrompt is required")

    for forbidden in (".claude-plugin", "commands", "agents"):
        if (plugin_root / forbidden).exists():
            errors.append(f"{plugin_name}: active Codex plugin must not contain `{forbidden}`")

    portability = plugin_root / "PORTABILITY.md"
    if not portability.is_file():
        errors.append(f"{plugin_name}: missing PORTABILITY.md")

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


def validate_target_fixture_payload(
    payload: dict[str, Any],
    path: Path,
    errors: list[str],
) -> None:
    plugins = payload.get("plugins")
    if not isinstance(plugins, list):
        errors.append(f"{path}: field `plugins` must be a list")
        return

    actual_plugins: dict[str, dict[str, Any]] = {}
    for entry in plugins:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            errors.append(f"{path}: plugin entries must be objects with string names")
            continue
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
        for forbidden in (".claude-plugin", "commands", "agents"):
            if forbidden in entry.get("forbidden_active_dirs", []):
                continue
            errors.append(f"{path}: {plugin_name} must forbid active `{forbidden}` directories")

    removed_plugins = set(payload.get("removed_plugins", []))
    compare_inventory(
        removed_plugins,
        OLD_ACTIVE_PLUGINS,
        "target fixture removed plugins",
        errors,
    )

    namespace_proof = set(payload.get("required_namespace_proof", []))
    missing_namespace = REQUIRED_NAMESPACE_PROOF_SKILLS - namespace_proof
    if missing_namespace:
        errors.append(
            "target fixture missing namespace proof skills: "
            f"{sorted(missing_namespace)}"
        )

    state_roots = set(payload.get("required_state_roots", []))
    missing_state_roots = REQUIRED_STATE_ROOTS - state_roots
    if missing_state_roots:
        errors.append(f"target fixture missing state roots: {sorted(missing_state_roots)}")

    mutation_plugins = set(payload.get("mutation_gate_plugins", []))
    if {"deploy", "mission-control"} - mutation_plugins:
        errors.append("target fixture must require mutation gates for deploy and mission-control")


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


def validate_cutover_evidence(root: Path, errors: list[str]) -> None:
    proof_doc = root / "docs" / "validation" / "saga-family-codex-proof.md"
    proof_schema = root / "docs" / "validation" / "saga-family-codex-proof.schema.json"
    rollback_doc = root / "docs" / "cutover" / "saga-family-rollback-and-split.md"
    for path in (proof_doc, proof_schema, rollback_doc):
        if not path.is_file():
            errors.append(f"cutover evidence missing `{path.relative_to(root)}`")


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
