#!/usr/bin/env python3
"""Lock the AS-015 source and categorical viability contract before implementation."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from tools.as015_evidence import publish


def sha(relative: str) -> str:
    return hashlib.sha256((REPOSITORY / relative).read_bytes()).hexdigest()


def main() -> None:
    source_audit = {
        "schema": "AS015_SOURCE_HYPOTHESIS_AUDIT_V1",
        "directive": "UMBRA-AS-015",
        "sources": {
            "physiology": {"path": "umbra_core/physiology.py", "sha256": sha("umbra_core/physiology.py")},
            "arbitration": {"path": "umbra_core/arbitration.py", "sha256": sha("umbra_core/arbitration.py")},
            "governance": {"path": "umbra_core/governance.py", "sha256": sha("umbra_core/governance.py")},
            "recoverability_view": {"path": "umbra_core/recoverability/view.py", "sha256": sha("umbra_core/recoverability/view.py")},
            "s16_plant": {"path": "experiments/d009/scenario_plants.py", "sha256": sha("experiments/d009/scenario_plants.py")},
        },
        "s16": {"tick": 180, "action": "reverse_affordance", "object": "rest:0", "effect": "occluded/unavailable"},
        "verified_regulators": {
            "REST": {"fatigue": -0.08, "energy": 0.015, "integrity": 0.055, "stimulation": -0.02},
            "CHARGE": {"energy": 0.14, "fatigue": -0.01, "stimulation": -0.005},
            "MOVE": {"energy": -0.005, "fatigue": 0.004, "stimulation": 0.003},
            "APPROACH": {"energy": -0.004, "fatigue": 0.003, "stimulation": 0.004},
            "FAILED_MOTION": {"energy": -0.003, "fatigue": 0.003},
        },
        "existing_limitation": {
            "fatigue": "critical recovery selects REST when observed; otherwise blind MOVE search",
            "energy": "has a resource/CHARGE-specific recovery corridor",
            "finding": "AS015_SINGLE_TARGET_FATIGUE_RECOVERY_DEFECT_CONFIRMED",
        },
        "safety_boundary": "_introduces_critical_boundary conservatively evaluates every authority-reachable branch plus next-tick drift; AS-015 shall not relax it.",
    }
    contract = {
        "schema": "AS015_MULTI_NEED_VIABILITY_CONTRACT_V1",
        "directive": "UMBRA-AS-015",
        "status": "PREIMPLEMENTATION_LOCKED",
        "non_goals": [
            "no scalar utility or global mood score",
            "no authored need-to-action table",
            "no hidden Habitat coordinates or object identity in policy",
            "no relaxation of verified-outcome branch safety",
            "no promotion of historical observed motion into a future guarantee",
        ],
        "source_inputs": [
            "current physiology and existing critical bounds",
            "unavoidable DEFAULT_DRIFT",
            "authoritative effect branches and categorical current executability",
            "ordinary policy-visible candidates and observations",
            "body-schema-valid support only where its semantics permit the stated use",
        ],
        "endpoint_rule": {
            "definition": "A terminal candidate is an endpoint for dimension d only when every authoritative branch available at the current root is directionally corrective for d and the preflight says EXECUTABLE.",
            "derivation": "candidate capability plus its authoritative branches, not a static need-to-action map",
            "direct_endpoint_status": "ROBUST_NOW only when all componentwise projected branch-plus-drift states remain noncritical",
        },
        "route_rule": {
            "definition": "A route is formed only by an ordinary policy-visible target-bound route candidate and a matching terminal candidate.",
            "robustness": "Every projected intermediate branch must remain noncritical in every homeostatic dimension.",
            "observed_motion_boundary": "VERIFIED_OBSERVED_SUPPORT may describe a MAY route but cannot establish guaranteed future arrival or a hard last-route preservation obligation.",
            "unknown": "Missing, probabilistic, schema-mismatched, or non-guaranteeing route evidence remains UNKNOWN rather than becoming infeasible or safe.",
        },
        "authority_rule": {
            "active_recovery": "When an active need has one or more ROBUST_NOW endpoints, select only among those endpoints through the existing non-utility recovery competition.",
            "preservation": "An ordinary candidate may not transition from at least one ROBUST_NOW endpoint to none when an alternative remains; this is a categorical constraint, not a preference bonus.",
            "last_resort": "If no robust route exists, NO_SAFE_ACTION remains valid; the mechanism must not invent rescue.",
        },
        "vector_rule": "All energy, fatigue, integrity, and stimulation projections are checked componentwise for every branch; no dimension is scalarized or exempted.",
        "persistence_rule": "The viability evaluator is derived at decision time, consumes no RNG, stores no policy state, and must remain snapshot/restart and bounded-persistence compatible.",
        "qualification_boundary": "The retained AS-014 seed establishes causal development attribution only. New behavior requires fresh post-lock AS-015 evidence.",
    }
    print(json.dumps({
        "source_audit_sha256": publish("AS015_SOURCE_HYPOTHESIS_AUDIT.json", source_audit),
        "contract_sha256": publish("AS015_MULTI_NEED_VIABILITY_CONTRACT.json", contract),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
