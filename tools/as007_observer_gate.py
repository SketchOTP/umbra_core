#!/usr/bin/env python3
"""Run the bounded AS-007 pre-freeze observer-only parity gate.

This delegates only the already-qualified common-root parity mechanism to a
fresh AS-007 evidence subroot.  It is development evidence, not the frozen
scientific A/B/R1 sequence.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

EVIDENCE_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-007-recovery-executability-integrated-viability-r1/observer-gate-r1"
)


def main() -> None:
    from experiments.as006 import observer_preflight as gate

    gate.EVIDENCE_ROOT = EVIDENCE_ROOT
    gate.WORK_ROOT = EVIDENCE_ROOT / "common-root-work"
    result = gate.orchestrate()
    result = {
        **result,
        "schema": "AS007_OBSERVER_DEVELOPMENT_GATE_RESULT_V1",
        "directive": "UMBRA-AS-007",
        "classification": "PRE_FREEZE_OBSERVER_ONLY_DEVELOPMENT",
        "scientific_sequence": False,
        "planning_authority": False,
        "retries": 0,
        "reseeds": 0,
    }
    gate._publish_json("AS007_OBSERVER_DEVELOPMENT_GATE_RESULT.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("observer_semantic_parity") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
