#!/usr/bin/env python3
"""The single Codex CLI version this repository targets.

This is an *expectation*, never an observation. It drives the proof runner's check, the capability
snapshot test assertions, and the generated schema ``const``. It must never be used to stamp an
observed runtime receipt: a builder that records what actually ran captures its own version and
compares it to this constant, because relabelling an observation to match a target falsifies
provenance.

Kept import-free on purpose so both ``scripts/`` consumers and the test suite can import it without
dragging in a dependency graph.
"""

from __future__ import annotations

CODEX_TARGET_VERSION = "0.147.0"
"""The Codex CLI release this repository's capability expectations are written against."""

CAPABILITY_SNAPSHOT_SCHEMA_VERSION = 3
"""``schema_version`` carried by the r4 capability-snapshot revision."""
