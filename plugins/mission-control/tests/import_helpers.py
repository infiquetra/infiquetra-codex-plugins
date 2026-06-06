"""Test import helpers for mission-control."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_plugin_module(module_name: str, filename: str) -> ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]

    script_path = Path(__file__).resolve().parent.parent / "scripts" / filename
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_sdlc_manager() -> ModuleType:
    return load_plugin_module("mission_control_sdlc_manager", "sdlc_manager.py")


def load_sync_template_docs() -> ModuleType:
    return load_plugin_module("mission_control_sync_template_docs", "sync_template_docs.py")
