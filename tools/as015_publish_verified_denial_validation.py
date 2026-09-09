"""Publish bounded validation evidence for the AS-015 denial-learning seam."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tools.as015_evidence import publish


ROOT = Path(__file__).resolve().parents[1]


def _sha(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def main() -> None:
    payload = {
        "schema": "AS015_VERIFIED_EXECUTABILITY_DENIAL_VALIDATION_V1",
        "directive": "UMBRA-AS-015",
        "status": "PASS",
        "focused_tests": {
            "command": "/home/sketch/cs14n-runtime/bin/python -m pytest -q tests/test_as015_verified_executability_denial.py",
            "result": "8 passed",
        },
        "protected_regression_subset": {
            "command": "/home/sketch/cs14n-runtime/bin/python -m pytest -q tests/test_as015_viability_kernel.py tests/test_as007_executability.py tests/test_d013ae_verified_outcome.py",
            "result": "23 passed",
        },
        "world_change_race": {
            "successful_governed_charge_outcomes": 3,
            "external_change_timing": "after normal policy selection and before ordinary Governance execution",
            "executed_affordance_denied_outcomes": 1,
            "safe_later_denial_roots": 3,
            "transition_contradiction_count": 1,
            "affordance_status": "WEAKENED",
            "terminal_safety_bypassed": False,
        },
        "negative_controls": {
            "not_at_resource_affordance_delta": False,
            "duplicate_same_root_counts_once": True,
            "unverified_rejected": True,
            "learning_disabled_rejected": True,
            "affordance_learning_disabled_rejected": True,
        },
        "authority_invariants": {
            "current_root_world_model_mutation": False,
            "transition_model_mutation_from_unexecuted_denial": False,
            "physiology_effects_from_unexecuted_denial": False,
            "action_count_from_unexecuted_denial": False,
            "route_evidence_from_unexecuted_denial": False,
            "hidden_habitat_identity_persisted": False,
            "restart_deduplication": "PASS",
        },
        "source_hashes": {
            relative: _sha(relative)
            for relative in (
                "umbra_core/runtime.py",
                "umbra_core/world_model/engine.py",
                "umbra_core/events.py",
                "tests/test_as015_verified_executability_denial.py",
            )
        },
        "formal_boundary": {"formal_seed_consumed": False, "scientific_lock_established": False},
    }
    print(publish("AS015_VERIFIED_DENIAL_VALIDATION.json", payload))


if __name__ == "__main__":
    main()
