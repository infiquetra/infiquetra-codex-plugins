from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_audit() -> ModuleType:
    script = Path(__file__).parents[1] / "scripts" / "implementation_spec_audit.py"
    spec = importlib.util.spec_from_file_location("saga_implementation_spec_audit", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit = load_audit()


def test_discover_marks_service_implementation_profile_ready(tmp_path: Path) -> None:
    library = tmp_path / "campps-context-library"
    standard = library / "platform-specs" / "06-service-implementations" / "README.md"
    standard.parent.mkdir(parents=True)
    standard.write_text(
        "# Service Implementations\n\n"
        "## Folder Contract\n\n"
        "## Completeness Checklist\n\n"
        "## Definition of Done\n\n"
        "Probe inputs are exact.\n",
        encoding="utf-8",
    )

    profiles = audit.discover(tmp_path, library)

    assert len(profiles) == 1
    assert profiles[0].library == "campps-context-library"
    assert profiles[0].profile == "service-implementations"
    assert profiles[0].status == "ready"


def test_discover_marks_thin_feature_module_profile_needed(tmp_path: Path) -> None:
    library = tmp_path / "mimir-context-library"
    standard = library / "platform-specs" / "06-feature-modules" / "README.md"
    standard.parent.mkdir(parents=True)
    standard.write_text("# 06 Feature Modules\n\n- [Characters](./characters/)\n", encoding="utf-8")

    profiles = audit.discover(tmp_path, library)

    assert len(profiles) == 1
    assert profiles[0].profile == "feature-modules"
    assert profiles[0].status == "profile-needed"


def test_audit_service_implementation_finds_missing_contract_files(tmp_path: Path) -> None:
    target = tmp_path / "platform-specs" / "06-service-implementations" / "identity-access-service"
    target.mkdir(parents=True)
    (target / "api").mkdir()
    (target / "api" / "openapi.yaml").write_text("openapi: 3.0.3\n", encoding="utf-8")

    result = audit.audit_service_implementation(target)

    assert result["passed"] is False
    assert "api/endpoint-specifications.md" in result["missing"]
    assert "workflows/*-workflow.md" in result["missing"]
    assert result["warnings"] == ["api/openapi.yaml declares OpenAPI 3.0.3, expected 3.1"]


def test_audit_allows_links_inside_context_library_boundary(tmp_path: Path) -> None:
    target = tmp_path / "campps-context-library" / "platform-specs" / "06-service-implementations" / "svc"
    shared = tmp_path / "campps-context-library" / "platform-specs" / "05-technical-specifications"
    target.mkdir(parents=True)
    shared.mkdir(parents=True)
    (shared / "README.md").write_text("# Shared\n", encoding="utf-8")
    (target / "README.md").write_text(
        "[shared](../../05-technical-specifications/README.md)\n",
        encoding="utf-8",
    )

    assert audit.broken_relative_links(target) == []
