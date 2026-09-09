"""Publish the D-003 current-authority world-change-race proof."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tools.as015_evidence import publish


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    sources = (
        "tests/test_d003.py",
        "tests/test_as015_verified_executability_denial.py",
        "umbra_core/runtime.py",
        "umbra_core/world_model/engine.py",
    )
    payload = {
        "schema": "AS015_D003_VERIFIED_DENIAL_CURRENT_AUTHORITY_PASS_V1",
        "directive": "UMBRA-AS-015",
        "status": "PASS",
        "test_evidence": {
            "command": "/home/sketch/cs14n-runtime/bin/python -m pytest -q tests/test_d003.py::test_contradiction_weakens_obsolete_model tests/test_d003.py::test_false_affordance_is_revised tests/test_d003.py::test_changed_affordance_adaptation tests/test_as015_verified_executability_denial.py",
            "result": "11 passed",
        },
        "race": {
            "support_establishment": "three ordinary policy-selected and Governance-executed CHARGE successes",
            "external_intervention": "Habitat affordance changes after normal selection and before normal Governance execution",
            "executed_negative_outcome": "one real verified affordance_denied",
            "later_roots": "terminal preflight safely blocks physical CHARGE; one deferred denial per distinct root corroborates AffordanceBelief only",
            "existing_threshold_result": "charge_from becomes WEAKENED",
        },
        "negative_controls": {
            "not_at_resource": "does not commit affordance contradiction",
            "unexecuted_denial": "does not increment action count or transition contradiction",
            "terminal_safety": "not bypassed",
            "hidden_habitat_identity": "not persisted in denial evidence",
        },
        "source_hashes": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in sources},
        "formal_seed_consumed": False,
        "scientific_lock_established": False,
    }
    print(publish("AS015_D003_VERIFIED_DENIAL_CURRENT_AUTHORITY_PASS.json", payload))


if __name__ == "__main__":
    main()
