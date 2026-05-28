#!/usr/bin/env python3
"""Validate the Infiquetra Codex plugin repo."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


EXPECTED_PLUGINS: dict[str, dict[str, Any]] = {
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

CLAUDE_CATALOG = {
    "blueprint-reviewer",
    "docs-generator",
    "home-lab-ops",
    "identity-toolkit",
    "marketplace-lister",
    "pagerduty",
    "python-toolkit",
    "redis-channel",
    "sdk-lifecycle",
    "sdlc-manager",
    "slack",
    "splunk",
    "team-execution",
    "test-suite",
    "todoist-manager",
    "unifi",
}

ALLOWED_STATUSES = {"included", "proof-port", "deferred", "blocked", "unsupported"}
REQUIRED_CUTOVER_TERMS = ("trusted source", "allowlisted inventory", "pins", "rollback")

STALE_ACTIVE_PATTERNS = (
    "~/.claude/plugins/cache",
    "infiquetra-claude-plugins/plugins/",
    ".claude-plugin",
    "Claude Code plugin",
    "claude-plugins repository",
)

SCRIPT_FIELD_RE = re.compile(r"^\s*script:\s*(?P<path>\S+)\s*$", re.MULTILINE)
PLUGIN_SCRIPT_RE = re.compile(r"(?P<path>plugins/[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+\.py)")
MATRIX_ROW_RE = re.compile(r"^\|\s*`(?P<plugin>[^`]+)`\s*\|\s*(?P<status>[a-z-]+)\s*\|")


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    validate_marketplace(root, errors)
    validate_plugins(root, errors)
    validate_matrix(root, errors)
    validate_provenance(root, errors)
    validate_cutover(root, errors)
    return errors


def validate_marketplace(root: Path, errors: list[str]) -> None:
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

    expected = set(EXPECTED_PLUGINS)
    if seen != expected:
        errors.append(
            "marketplace inventory mismatch: "
            f"missing={sorted(expected - seen)} unexpected={sorted(seen - expected)}"
        )


def validate_plugins(root: Path, errors: list[str]) -> None:
    plugins_root = root / "plugins"
    actual_plugins = {
        path.name for path in plugins_root.iterdir() if path.is_dir() and not path.name.startswith(".")
    }
    expected_plugins = set(EXPECTED_PLUGINS)
    if actual_plugins != expected_plugins:
        errors.append(
            "plugin directory inventory mismatch: "
            f"missing={sorted(expected_plugins - actual_plugins)} "
            f"unexpected={sorted(actual_plugins - expected_plugins)}"
        )

    for plugin_name, expected in EXPECTED_PLUGINS.items():
        plugin_root = plugins_root / plugin_name
        validate_plugin(root, plugin_root, plugin_name, expected, errors)


def validate_plugin(
    repo_root: Path,
    plugin_root: Path,
    plugin_name: str,
    expected: dict[str, Any],
    errors: list[str],
) -> None:
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
    actual_skills = {path.name for path in skills_root.iterdir() if path.is_dir()}
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
        validate_active_text(repo_root, skill_md, text, errors)
        validate_script_references(repo_root, plugin_root, skill_md, text, errors)

    readme = plugin_root / "README.md"
    if readme.is_file():
        text = read_text(readme, errors)
        if text is not None:
            validate_active_text(repo_root, readme, text, errors)
            validate_script_references(repo_root, plugin_root, readme, text, errors)


def validate_active_text(repo_root: Path, path: Path, text: str, errors: list[str]) -> None:
    rel = path.relative_to(repo_root)
    for pattern in STALE_ACTIVE_PATTERNS:
        if pattern in text:
            errors.append(f"{rel}: contains stale host reference `{pattern}`")


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


def validate_matrix(root: Path, errors: list[str]) -> None:
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
    if rows.get("team-execution") not in {"blocked", "unsupported"}:
        errors.append("team-execution must be blocked or unsupported in the matrix")
    for required in ("Verified:", "Review trigger:", "Source snapshot:"):
        if required not in text:
            errors.append(f"portability matrix missing `{required}`")


def validate_provenance(root: Path, errors: list[str]) -> None:
    path = root / "docs" / "portability" / "provenance.md"
    text = read_text(path, errors)
    if text is None:
        return
    for plugin_name in EXPECTED_PLUGINS:
        if f"`{plugin_name}`" not in text:
            errors.append(f"provenance missing `{plugin_name}`")
    if "Proof-Port Recipe" not in text or "test-suite" not in text:
        errors.append("provenance missing test-suite proof-port recipe")


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
    repo_root = Path(__file__).resolve().parents[1]
    errors = validate_repository(repo_root)
    if errors:
        print("Codex plugin validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Codex plugin validation passed: {repo_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
