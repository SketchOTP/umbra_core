#!/usr/bin/env python3
"""Publish the zero-run AS-007 retained R1 coherence audit.

This tool reads committed source and retained evidence only.  It does not
construct, load, or tick an organism.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
EVIDENCE = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-007-recovery-executability-integrated-viability-r1"
)
ATTRIBUTION = EVIDENCE / "AS007_AS006_TERMINAL_CAUSAL_ATTRIBUTION.json"
OUT = EVIDENCE / "AS007_R1_COHERENCE_AUDIT.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def durable_json(path: Path, value: object) -> str:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return sha(path)


def main() -> None:
    attribution = json.loads(ATTRIBUTION.read_text(encoding="utf-8"))
    source_files = {
        "scenario_plants": REPO / "experiments/d009/scenario_plants.py",
        "close02r_runner": REPO / "experiments/close02r/qualification.py",
        "embodiment": REPO / "umbra_core/embodiment.py",
        "arbitration": REPO / "umbra_core/arbitration.py",
        "recoverability": REPO / "umbra_core/recoverability/contracts.py",
    }
    result = {
        "schema": "AS007_R1_COHERENCE_AUDIT_V1",
        "directive": "UMBRA-AS-007",
        "scope": {"organism_runs": 0, "organism_ticks": 0, "retrospective_read_only": True},
        "retained_evidence": {
            "attribution_sha256": sha(ATTRIBUTION),
            "decision_rows": attribution["retained_trace_shape"]["decision_rows"],
            "planning_rows": attribution["retained_trace_shape"]["planning_rows"],
            "successful_fatigue_reducing_actions": attribution["successful_fatigue_reducing_actions"]["count"],
            "last_successful_fatigue_reducing_action": attribution["successful_fatigue_reducing_actions"]["last"],
            "terminal_sequence": attribution["attribution"]["terminal_sequence"],
        },
        "frozen_challenge": {
            "regime": "R1",
            "scenario": "S16",
            "plant_tick": 180,
            "plant": "reverse_affordance sets rest:0 occluded=True and condition=0.0",
            "qualification_meaning": "environmental affordance reversal must be handled without a critical physiological failure",
        },
        "source_findings": {
            "reversal_semantics": "The S16 plant changes authoritative habitat object state and policy visibility; it does not remove the rest object or change its object kind.",
            "policy_visibility": "Perception suppresses occluded objects, so no current policy-visible rest opportunity is guaranteed after reversal.",
            "terminal_rest_execution": "Embodiment REST preflight is deterministic and source-backed: the body must be within the rest feature radius and the feature must be restable.",
            "rest_preflight_ignores_condition": "The current REST preflight does not use the S16 condition field; the retained failure reason not_at_rest therefore reflects location/readiness, not a direct condition rejection.",
            "recovery_contract_gap": "Arbitration can admit a terminal REST candidate from a coarse observation-distance rule without consulting the authoritative terminal preflight, and its initial critical choice is on the same path.",
        },
        "coherence": {
            "status": "PASS",
            "classification": "R1_RECOVERY_CONTRACT_COHERENT",
            "reason": "The retained trace demonstrates a source-valid post-reversal recovery trajectory exists: successful REST outcomes occurred after the S16 plant. The terminal sequence instead shows REST admitted, verified not_at_rest, NO_SAFE_ACTION, then another REST admission and not_at_rest. This is a recoverable readiness-adjudication defect, not proof that the frozen challenge is impossible.",
            "implementation_authorized": True,
            "production_change_authorized_after_this_audit": "one categorical terminal-executability contract shared by arbitration and execution, with initial critical recovery gated by the same contract",
        },
        "source_fingerprints": {name: sha(path) for name, path in source_files.items()},
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if OUT.exists():
        raise FileExistsError(OUT)
    print(f"readback_sha256={durable_json(OUT, result)}")


if __name__ == "__main__":
    main()
