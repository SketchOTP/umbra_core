#!/usr/bin/env python3
"""Publish the immutable AS-015 terminal evidence manifest."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from tools.as015_evidence import ROOT, publish

NAMES = (
    "AS015_SCIENTIFIC_LOCK_V1.json",
    "AS015_SEED_MANIFEST.json",
    "AS015_SEED_DISJOINTNESS_PROOF.json",
    "AS015_PRELOCK_READINESS_V2.json",
    "AS015_D003_VERIFIED_DENIAL_CURRENT_AUTHORITY_PASS.json",
    "AS015_VERIFIED_DENIAL_VALIDATION.json",
    "AS015_PREFLIGHT_DENIAL_REVALIDATION_RESULT.json",
    "AS015_FULL_CLI_SURFACE_PREFLIGHT_V2.json",
    "AS015_FORMAL_POPULATION_FAILURE_V1.json",
    "AS015_FORMAL_POPULATION_CLOSEOUT_V1.json",
)


def main() -> None:
    files = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in NAMES}
    closeout = json.loads((ROOT / "AS015_FORMAL_POPULATION_CLOSEOUT_V1.json").read_text())
    manifest = {
        "schema": "AS015_EVIDENCE_MANIFEST_V1",
        "directive": "UMBRA-AS-015",
        "terminal_verdict": closeout["terminal_verdict"],
        "scientific_implementation_sha": closeout["scientific_implementation_sha"],
        "governance_publication_sha": closeout["governance_publication_sha"],
        "files": files,
        "formal_cases_directory": "AS015_FORMAL_POPULATION_WORK_V1/case-results",
        "formal_case_count": closeout["population"]["completed_case_records"],
        "readback": "PASS",
    }
    digest = publish("AS015_EVIDENCE_MANIFEST_V1.json", manifest)
    print(json.dumps({"sha256": digest, "terminal_verdict": manifest["terminal_verdict"]}, sort_keys=True))


if __name__ == "__main__":
    main()
