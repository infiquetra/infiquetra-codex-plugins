#!/usr/bin/env python3
from __future__ import annotations

import runpy
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN_ROOT / "scripts" / "discord_identity_assets.py"


if __name__ == "__main__":
    runpy.run_path(str(SCRIPT), run_name="__main__")
