#!/usr/bin/env python3
"""The frozen harness digest, and nothing else.

This module holds one constant and is deliberately excluded from ``HARNESS_FILES``. A pin cannot
live inside the set of files it hashes: updating it would change the value it pins, so the two
could never agree. Splitting it out lets ``proof_harness_pin`` — which declares the file set and
the accepted proof cases — be hashed like any other part of the instrument, closing the gap where
the case registry's meanings could change without moving the digest.

To rotate deliberately, in the same commit as the harness change and with the reason recorded:

    python3 scripts/prove_verified_workflows_runtime.py --print-harness-sha256
"""

from __future__ import annotations

# Rotated for U9: the Luna promotion gate no longer tests the raw catalog `multi_agent_version`
# for equality with "v2" -- a property that does not decide the question -- and promotion is now
# read per profile from a canary receipt instead of one pair-wide boolean. Both the renderer and
# the profile synchroniser changed, and the receipt adjudication moved out of the proof tool into
# the renderer so one rule serves both. Receipts carrying the previous digest are invalid.
#
# Rotated again for U10: the offline turn driver was split out of `capture_tool_specification`
# so a second caller can read the raw request bodies, and `capture_context_injection` was added
# on top of it to measure which skills actually reach a turn's model context. The proof tool
# gained `validate_discovery_routing`. Both are instrument changes, so receipts carrying
# d79eba136ccd are invalid.
RUNTIME_PROOF_HARNESS_SHA256 = (
    "a3a8ed57126bac533199144fd01f75e75ac79f9c722590fd6b634e37e318eff4"
)
