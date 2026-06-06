"""Tests for release-note previews."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_preview_release_notes() -> ModuleType:
    module_name = "deploy_preview_release_notes"
    if module_name in sys.modules:
        return sys.modules[module_name]
    script = Path(__file__).resolve().parents[1] / "scripts" / "preview_release_notes.py"
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


preview_release_notes = load_preview_release_notes()


def test_render_notes_summarizes_commit_range() -> None:
    rendered = preview_release_notes.render_notes(
        "staging-v1.2.2",
        "v1.2.3",
        {
            "commits": [
                {"sha": "abcdef123", "commit": {"message": "Fix deploy check\n\nbody"}},
                {"sha": "123456789", "commit": {"message": "Add release evidence"}},
            ],
            "files": [{"filename": "README.md"}],
        },
    )

    assert "release notes preview: staging-v1.2.2...v1.2.3" in rendered
    assert "commits: 2" in rendered
    assert "files changed: 1" in rendered
    assert "- abcdef1 Fix deploy check" in rendered
