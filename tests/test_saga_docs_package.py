"""Drift tests for the Saga family documentation package."""

from __future__ import annotations

import json
import re
from pathlib import Path

from scripts import build_saga_docs_facts, render_saga_docs_assets
from scripts.validate_codex_plugins import TARGET_EXPECTED_PLUGINS

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs" / "saga"
FACTS_PATH = DOCS_ROOT / "generated" / "lifecycle-facts.json"


def load_facts() -> dict:
    return json.loads(FACTS_PATH.read_text(encoding="utf-8"))


def test_generated_facts_are_current() -> None:
    expected = build_saga_docs_facts.dumps(build_saga_docs_facts.build_facts(REPO_ROOT))
    assert FACTS_PATH.read_text(encoding="utf-8") == expected


def test_required_docs_and_visual_assets_exist() -> None:
    facts = load_facts()
    for rel_path in facts["docs_package"]["required_docs"]:
        assert (REPO_ROOT / rel_path).is_file(), rel_path
    for rel_path in facts["docs_package"]["required_visual_assets"]:
        assert (REPO_ROOT / rel_path).is_file(), rel_path


def test_command_catalog_covers_saga_family_skills() -> None:
    facts = load_facts()
    text = (DOCS_ROOT / "command-catalog.md").read_text(encoding="utf-8")
    for plugin in ("saga", "mission-control", "team-execution", "deploy"):
        for skill in TARGET_EXPECTED_PLUGINS[plugin]["skills"]:
            assert f"{plugin}:{skill}" in text
            assert any(row["name"] == skill for row in facts["plugins"][plugin]["skills"])


def test_routable_saga_commands_and_maturities_are_documented() -> None:
    facts = load_facts()
    command_catalog = (DOCS_ROOT / "command-catalog.md").read_text(encoding="utf-8")
    state_doc = (DOCS_ROOT / "state-and-maturity.md").read_text(encoding="utf-8")
    assert len(facts["saga_routing"]["routable_commands"]) == 19
    for command in facts["saga_routing"]["routable_commands"]:
        assert f"saga:{command}" in command_catalog
    for maturity in facts["state"]["readiness_maturities"]:
        assert maturity in state_doc
    assert "derived-never-stored" in facts["state"]["maturity_storage"]


def test_required_scenarios_are_present() -> None:
    facts = load_facts()
    text = (DOCS_ROOT / "scenarios.md").read_text(encoding="utf-8").lower()
    for scenario in facts["docs_package"]["required_scenarios"]:
        assert scenario.lower() in text


def test_docs_use_repo_relative_links() -> None:
    markdown_links = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in DOCS_ROOT.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for target in markdown_links.findall(text):
            if target.startswith(("http://", "https://", "#")):
                continue
            assert not target.startswith("/"), f"{path}: absolute link {target}"
            assert not target.startswith("file:"), f"{path}: file URI {target}"
            rel = (path.parent / target.split("#", 1)[0]).resolve()
            if target.split("#", 1)[0]:
                assert rel.exists(), f"{path}: broken link {target}"


def test_entrypoint_readmes_link_saga_family_guide() -> None:
    entrypoints = {
        REPO_ROOT / "README.md": "docs/saga/README.md",
        REPO_ROOT / "plugins" / "saga" / "README.md": "../../docs/saga/README.md",
        REPO_ROOT / "plugins" / "mission-control" / "README.md": "../../docs/saga/README.md",
        REPO_ROOT / "plugins" / "team-execution" / "README.md": "../../docs/saga/README.md",
        REPO_ROOT / "plugins" / "deploy" / "README.md": "../../docs/saga/README.md",
    }
    for path, link in entrypoints.items():
        assert link in path.read_text(encoding="utf-8")
        assert (path.parent / link).resolve().is_file()


def test_visual_svg_assets_are_nonempty() -> None:
    for name in ("saga-lifecycle-atlas.svg", "readiness-ladder.svg", "ownership-boundaries.svg"):
        text = (DOCS_ROOT / "visual-assets" / name).read_text(encoding="utf-8")
        assert "<svg" in text
        assert len(text) > 500


def test_visual_svg_assets_are_current() -> None:
    expected = render_saga_docs_assets.render_svg_assets(build_saga_docs_facts.build_facts(REPO_ROOT))
    for name, content in expected.items():
        assert (DOCS_ROOT / "visual-assets" / name).read_text(encoding="utf-8") == content


def test_exported_visual_assets_are_nonempty() -> None:
    for name in ("saga-lifecycle-atlas.png", "saga-lifecycle-atlas.pdf"):
        assert (DOCS_ROOT / "visual-assets" / name).stat().st_size > 500
