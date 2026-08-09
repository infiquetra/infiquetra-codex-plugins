#!/usr/bin/env python3
"""Generate the r4 capability-snapshot schema from the r3 revision plus the target constant.

The schema is generated rather than hand-edited so its ``codex_cli_version`` const cannot drift from
``CODEX_TARGET_VERSION``. That drift is exactly what this round is correcting: four hard version pins
had already fallen out of step with one another because each was maintained by hand.

The r3 revision stays on disk unmodified. Artifacts already validated against it keep validating; r4
is a new revision, not a rewrite of the old one.

Usage:
    python3 scripts/render_capability_schema.py --check   # non-zero when the committed file drifted
    python3 scripts/render_capability_schema.py --write
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codex_target_version import (  # noqa: E402
    CAPABILITY_SNAPSHOT_SCHEMA_VERSION,
    CODEX_TARGET_VERSION,
)

ROOT = Path(__file__).resolve().parent.parent
BASE_SCHEMA = ROOT / "docs/validation/codex-runtime-capability-snapshot.schema-r3.json"
TARGET_SCHEMA = ROOT / "docs/validation/codex-runtime-capability-snapshot.schema-r4.json"

OVERRIDE_FILTER_RULE = "codex-0.147.0/model-supports-multi-agent-backend"
COLLABORATION_RULE = "codex-0.147.0/collab-tools-enabled"
SESSION_FACT_SOURCE = "current-0.147-live-tool-contract"


def _override_filter_property() -> dict:
    """Whether a MultiAgent V2 session may select this model as an explicit override."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["rule", "passes"],
        "properties": {
            "rule": {"const": OVERRIDE_FILTER_RULE},
            "passes": {"type": "boolean"},
        },
    }


def _collaboration_property() -> dict:
    """Whether a V2 session running this model receives collaboration tools, by session position."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["rule", "as_root", "as_child"],
        "properties": {
            "rule": {"const": COLLABORATION_RULE},
            "as_root": {"type": "boolean"},
            "as_child": {"type": "boolean"},
        },
    }


def build_schema() -> dict:
    """Return the r4 schema: the r3 shape with the version constants and the two projections."""
    schema = copy.deepcopy(json.loads(BASE_SCHEMA.read_text(encoding="utf-8")))

    schema["properties"]["schema_version"] = {"const": CAPABILITY_SNAPSHOT_SCHEMA_VERSION}
    schema["properties"]["runtime"]["properties"]["codex_cli_version"] = {
        "const": CODEX_TARGET_VERSION
    }

    model = schema["properties"]["catalog"]["properties"]["models"]["items"]
    # "disabled" is the snake_case wire value of MultiAgentVersion::Disabled and was previously
    # unrepresentable, so a catalog reporting it could not be captured at all.
    multi_agent_version = model["properties"]["multi_agent_version"]
    for key in ("enum", "anyOf", "oneOf"):
        if key in multi_agent_version:
            multi_agent_version = {"enum": ["v1", "v2", "disabled", None]}
            model["properties"]["multi_agent_version"] = multi_agent_version
            break

    # The proof harness and the capture script both stamp where a session fact came from; the r4
    # revision adds the 0.147 live-tool-contract source without retiring the earlier ones, so an
    # r3-era value stays describable.
    session_fact_source = schema["properties"]["runtime"]["properties"].get("session_fact_source")
    if isinstance(session_fact_source, dict) and "enum" in session_fact_source:
        if SESSION_FACT_SOURCE not in session_fact_source["enum"]:
            session_fact_source["enum"] = [*session_fact_source["enum"], SESSION_FACT_SOURCE]

    model["properties"]["multi_agent_v2_override_filter"] = _override_filter_property()
    model["properties"]["multi_agent_v2_collaboration"] = _collaboration_property()
    model["required"] = [
        *model["required"],
        "multi_agent_v2_override_filter",
        "multi_agent_v2_collaboration",
    ]
    return schema


def dumps(schema: dict) -> str:
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.check == args.write:
        parser.error("pass exactly one of --check or --write")

    rendered = dumps(build_schema())
    if args.write:
        TARGET_SCHEMA.write_text(rendered, encoding="utf-8")
        print(f"wrote {TARGET_SCHEMA.relative_to(ROOT)}")
        return 0

    if not TARGET_SCHEMA.exists():
        print(f"{TARGET_SCHEMA.relative_to(ROOT)} is missing", file=sys.stderr)
        return 1
    if TARGET_SCHEMA.read_text(encoding="utf-8") != rendered:
        print(
            f"{TARGET_SCHEMA.relative_to(ROOT)} drifted from its generator; "
            "re-run with --write",
            file=sys.stderr,
        )
        return 1
    print("capability schema current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
