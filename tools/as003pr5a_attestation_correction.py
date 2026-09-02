#!/usr/bin/env python3
"""Append-only correction for the first R5A root-attestation hash convention."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as003pr5a.protocol import retained_root_attestation


result = retained_root_attestation()
result.update(
    {
        "schema": "AS003PR5A_RETAINED_ROOT_ATTESTATION_CORRECTION_V1",
        "corrects": "AS003PR5A_RETAINED_ROOT_ATTESTATION.json",
        "correction": {
            "field": "rng_sha256",
            "first_record_value": "2da4ec4349444ffcfa9fdfe18df057801dd59d0bdec424389948e82907b2dc38",
            "correct_value": "e2c69703d1fc3181bb62beaf9584410dfad02dba8141c3536198b0ce792aad68",
            "cause": "first R5A verifier added a newline absent from the locked R5 recovery digest convention",
            "retained_root_bytes_changed": False,
        },
        "preservation": "the preliminary create-once attestation remains unchanged; this correction is authoritative",
    }
)
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["result"] == "PASS" else 1)
