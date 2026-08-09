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

RUNTIME_PROOF_HARNESS_SHA256 = (
    "edbd95411c09b7dcda25b7d3547ee7aa4627a899150335c66b6370e6d02b416f"
)
