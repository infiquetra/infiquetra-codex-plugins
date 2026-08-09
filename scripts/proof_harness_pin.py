#!/usr/bin/env python3
"""Frozen identity of the runtime proof harness, and the closed set of proof cases.

This module is deliberately import-free and holds no logic. It exists so the harness digest
lives somewhere other than the files it digests: a constant stored inside a hashed file cannot
be updated without changing the value it pins.

The harness is the set of files that can influence what a receipt says. Freezing it is what
makes a receipt evidence rather than an assertion, because the engine that produced the receipt
cannot also have been quietly changing the instrument (KTD8). Any edit to a file listed in
HARNESS_FILES changes the composite digest, which invalidates every receipt carrying the old
one and forces the affected proofs to be rerun rather than silently accepted.

To rotate the pin deliberately: run

    python3 scripts/prove_verified_workflows_runtime.py --print-harness-sha256

and paste the value below in the same commit as the harness change, with the reason.
"""

from __future__ import annotations

# Repository-relative, sorted, and closed. Adding a file that can change a receipt without
# adding it here would let the instrument drift while the pin stayed still.
HARNESS_FILES: tuple[str, ...] = (
    "plugins/fleet-core/scripts/fleet_commons/codex_model_catalog.py",
    "plugins/fleet-core/scripts/fleet_commons/models.json",
    "plugins/fleet-core/scripts/fleet_commons/tier_palette.py",
    "plugins/fleet-core/scripts/fleet_commons/workflow_compat.py",
    "plugins/verified-workflows/scripts/fleet_commons_shim.py",
    "plugins/verified-workflows/scripts/render_codex_agents.py",
    "plugins/verified-workflows/scripts/sync_codex_agents.py",
    "scripts/codex_capability_probe.py",
    "scripts/codex_target_version.py",
    "scripts/proof_harness_pin.py",
    "scripts/prove_verified_workflows_runtime.py",
    "tests/conftest.py",
)

# The boundary is "executable code that produces or adjudicates evidence", not every transitive
# dependency. The renderer loads the four fleet_commons modules above dynamically through the
# shim, and any of them can change what a profile renders as; `models.json` is in the set because
# after U4 it is the only place a profile's model and effort are stated, so it decides the bytes
# a probe installs. Subject data that is separately digested inside the proof itself — the role
# registry, the role files, the catalog snapshot, and the generated profiles — stays out, because
# a receipt already records those digests and would fail on its own if they moved.
#
# `tests/conftest.py` is in the set even though it is a test file, because its execution-
# environment fixtures BUILD the capability roots, plugin trees and permission configurations the
# skill and permission proofs run against. A fixture that silently stops matching the binary
# changes what those proofs observe, which is the definition used above; it was missed on the
# first pass precisely because "test file" read as "not the instrument".
#
# The shim can be redirected at an external Fleet Core through FLEET_COMMONS_ROOT, which
# would put unhashed code in the path. `harness_sha256` refuses to run under that
# redirection rather than hashing files it was not pointed at, and the proof script loads
# each hashed module by path so a stray `PYTHONPATH` entry cannot quietly substitute a
# different file. Both are drift protection: this pin answers "is the instrument still the
# one that was reviewed?", which is a question about accidents and edits, not about an
# adversary.

# The digest itself lives in `proof_harness_sha256`, which is deliberately NOT in the list above.
# A pin cannot sit inside the set of files it hashes. Splitting it out is what lets this module —
# which declares both the file set and the accepted proof cases below — be hashed like any other
# part of the instrument, so a case's meaning cannot change without moving the digest.
#
# The renderer and the profile synchroniser are listed because they decide the profile bytes a
# probe installs and the `profiles` section a proof publishes; the target-version module because
# a gate reads it. Editing any of them invalidates existing receipts, which is the intended
# consequence rather than an inconvenience: the affected proofs are re-taken.

# Every receipt declares which behavioural claim it is evidence for. A receipt that declares
# nothing, or declares a case not listed here, is refused rather than folded into whichever
# matrix row happens to be next. The identifiers are stable: retire one by removing it and
# rerunning the affected proofs, never by reusing it for a different claim.
PROOF_CASES: dict[str, str] = {
    "profile-identity": (
        "One managed profile spawns a child whose readback matches the requested profile, "
        "model, effort, and provider."
    ),
    "nested-delegation": (
        "A child spawned by a child reports a canonical agent path two levels deep and its own "
        "profile rather than its parent's."
    ),
    "typed-result": (
        "An attempt returns one closed typed result object that the result contract validates."
    ),
    "bounded-history": (
        "A bounded-history child observes the current root marker while a no-history child "
        "excludes the root-only marker."
    ),
    "ultra-root-only": (
        "Ultra is selectable at the root and is not inherited by, or selectable for, a child."
    ),
    "luna-canary": (
        "A single low-cost profile runs on the Luna model and reports Luna back, per profile "
        "rather than pair-wide."
    ),
    # U7's seven permission rows, enumerated by the plan. One identifier per row, because a
    # single "turn-permission" case cannot express a missing row or a duplicate, which is what
    # the plan asks the registry to reject.
    "turn-permission-read-only": "A read-only turn's effective permission tuple.",
    "turn-permission-workspace-write": "A workspace-write turn's effective permission tuple.",
    "turn-permission-multiple-roots": "A turn carrying more than one workspace root.",
    "turn-permission-after-role": "A spawn issued after the role has been applied.",
    "turn-permission-cold-resume": "A cold resume running under current runtime permissions.",
    "turn-permission-later-update": "A permission update arriving on a later turn.",
    "turn-permission-no-widening": (
        "A child cannot widen beyond its parent turn; a widening attempt blocks."
    ),
    # U8's rows. Host-installed and executor-backed are separate mechanisms, and conflating them
    # is a repeat finding in this repository, so they never share an identifier.
    "skill-host-installed-read": "A host-installed plugin skill reference resolves and reads.",
    "skill-executor-permitted-read": (
        "An executor-backed resource read succeeds when the active permission profile permits "
        "its root."
    ),
    "skill-executor-denied-read": (
        "An executor-backed read fails closed with the pinned message and returns no content "
        "when the root is not permitted."
    ),
    "skill-executor-discovery-denial": (
        "A discovery-time denial is distinguishable from a read-time denial."
    ),
    "skill-executor-multiple-roots": (
        "More than one permitted workspace root resolves distinctly rather than collapsing to "
        "the first."
    ),
    "skill-executor-grant-recovery": "A permission grant recovers a previously denied read.",
    "discovery-routing": (
        "A managed profile is discoverable by name and a request for it routes to that exact "
        "profile rather than to a default."
    ),
}
