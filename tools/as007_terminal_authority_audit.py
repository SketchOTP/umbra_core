#!/usr/bin/env python3
"""Publish the AS-007 terminal-interaction authority map.

The map is a source audit only.  It does not instantiate or run an organism.
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
OUT = EVIDENCE / "AS007_TERMINAL_EXECUTABILITY_AUTHORITY_MAP.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def publish(value: object) -> str:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        raise FileExistsError(OUT)
    temporary = OUT.with_name(f".{OUT.name}.{os.getpid()}.tmp")
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, OUT)
    directory = os.open(OUT.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return sha(OUT)


def main() -> None:
    sources = {
        "arbitration": REPO / "umbra_core/arbitration.py",
        "embodiment": REPO / "umbra_core/embodiment.py",
        "adapter": REPO / "umbra_core/embodiment_adapters/adapter.py",
        "governance": REPO / "umbra_core/governance.py",
        "runtime": REPO / "umbra_core/runtime.py",
        "contracts": REPO / "umbra_core/recoverability/contracts.py",
    }
    terminal = {
        "REST": {
            "candidate_generation": "policy-visible rest observation; critical recovery may also construct REST from observation estimated_distance <= 2.2 on the legacy path",
            "ordinary_selection": "candidate enters the common admissible pool and is now retained only when the runtime categorical gate is EXECUTABLE",
            "critical_selection": "initial and fallback candidates pass immediate safety, Contract E admissibility, and categorical executability before commit",
            "adapter_preflight": "attachment/generation/profile/capability validation, then parameter translation",
            "embodiment_preflight": "current projected rest feature exists, body is within feature.radius + 0.3, and feature.restable",
            "execution": "_apply_primitive REST invokes the same Embodiment.preflight_primitive predicate",
            "verification": "Governance verifies success or not_at_rest/failure effects through the existing VerifiedOutcome path",
            "route_binding": "WorldModel route binding is created from the emitted candidate and current body schema; this gate does not create route evidence",
            "unknown_behavior": "direct terminal execution is fail-closed when preflight is unavailable",
        },
        "CHARGE": {
            "candidate_generation": "policy-visible resource/novel_crystal observation; critical recovery may construct CHARGE for a current target",
            "ordinary_selection": "candidate enters the common admissible pool and is now retained only when the runtime categorical gate is EXECUTABLE",
            "critical_selection": "initial and fallback candidates pass immediate safety, Contract E admissibility, and categorical executability before commit",
            "adapter_preflight": "attachment/generation/profile/capability validation, then parameter translation",
            "embodiment_preflight": "current resource/novel_crystal feature exists, is within feature.radius + 0.3, and is chargeable; impossible_node is rejected",
            "execution": "_apply_primitive CHARGE invokes the same Embodiment.preflight_primitive predicate",
            "verification": "Governance verifies success or not_at_resource/affordance failure through the existing VerifiedOutcome path",
            "route_binding": "WorldModel route binding is created from the emitted candidate and current body schema; this gate does not create route evidence",
            "unknown_behavior": "direct terminal execution is fail-closed when preflight is unavailable",
        },
        "INSPECT": {
            "candidate_generation": "policy-visible inspect observation; critical stimulation recovery may construct INSPECT toward inspect",
            "ordinary_selection": "candidate enters the common admissible pool and is now retained only when the runtime categorical gate is EXECUTABLE",
            "critical_selection": "initial and fallback candidates pass immediate safety, Contract E admissibility, and categorical executability before commit",
            "adapter_preflight": "attachment/generation/profile/capability validation, then parameter translation",
            "embodiment_preflight": "current inspect/noise_blink feature exists, is within feature.radius + 0.8, and is inspectable; stochastic outcome remains execution/verification evidence",
            "execution": "_apply_primitive INSPECT evaluates the same target, range, and inspectable predicate; noise_blink may then consume its existing execution RNG",
            "verification": "Governance verifies success, out_of_range, or noise_fail through the existing VerifiedOutcome path",
            "route_binding": "WorldModel route binding is created from the emitted candidate and current body schema; this gate does not create route evidence",
            "unknown_behavior": "direct terminal execution is fail-closed when preflight is unavailable",
        },
    }
    result = {
        "schema": "AS007_TERMINAL_EXECUTABILITY_AUTHORITY_MAP_V1",
        "directive": "UMBRA-AS-007",
        "scope": {"production_runs": 0, "organism_runs": 0, "organism_ticks": 0},
        "contract": {
            "categorical_results": ["EXECUTABLE", "NOT_EXECUTABLE", "UNKNOWN"],
            "policy_exposure": "categorical readiness only",
            "hidden_habitat_values_exposed": False,
            "terminal_capabilities": ["REST", "CHARGE", "INSPECT"],
            "motion_semantics": "APPROACH/MOVE/RETREAT remain verified-outcome actions, not terminal preflight claims",
            "source_of_truth": "adapter preflight followed by Embodiment.preflight_primitive; Governance execution uses the same adapter and Embodiment path",
        },
        "terminal_interactions": terminal,
        "known_gap_closed": "Critical recovery previously checked immediate safety and Contract E only after fallback selection; the initial terminal recovery candidate was not uniformly gated by current execution readiness.",
        "stale_readiness": "No readiness result is persisted or reused by the gate; it is recomputed at the selection boundary from current adapter/Embodiment authority.",
        "source_fingerprints": {name: sha(path) for name, path in sources.items()},
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"readback_sha256={publish(result)}")


if __name__ == "__main__":
    main()
