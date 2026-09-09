"""Publish the AS-015 verified executability-denial source-strength contract."""

from __future__ import annotations

from tools.as015_evidence import publish


def main() -> None:
    payload = {
        "schema": "AS015_VERIFIED_EXECUTABILITY_DENIAL_CONTRACT_V1",
        "directive": "UMBRA-AS-015",
        "evidence_type": "VerifiedExecutabilityDenial",
        "source_strength": "VERIFIED_FINAL_EXECUTION_PREFLIGHT_AFFORDANCE_EVIDENCE",
        "admission": {
            "candidate_origin": "ordinary_policy_generated",
            "terminal_preflight": "same trusted adapter plus Embodiment authority used by execution",
            "executability": "NOT_EXECUTABLE",
            "verified": True,
            "executed": False,
            "policy_visible_target_binding_required": True,
            "initial_reason_allowlist": ["affordance_denied"],
        },
        "explicitly_rejected_reasons": [
            "not_at_resource",
            "not_at_rest",
            "out_of_range",
            "impossible_target",
            "adapter_rejection",
            "unknown",
        ],
        "deferred_commit": {
            "after_current_root_selection": True,
            "after_current_root_governance_and_execution": True,
            "root_local_semantic_deduplication": True,
            "persistent_evidence_id_deduplication": True,
        },
        "allowed_learning_delta": ["AffordanceBelief contradiction evidence and bounded provenance"],
        "forbidden_learning_delta": [
            "TransitionModel support or contradiction",
            "physiology",
            "SelfModel attribution",
            "executed action count",
            "route evidence",
            "memory execution evidence",
            "hidden Habitat identity or coordinates",
        ],
        "thresholds": "existing WorldModel affordance contradiction thresholds unchanged",
        "persistence": "authoritative sanitized event plus WorldModel snapshot/checkpoint state",
        "formal_boundary": {"formal_seed_consumed": False, "scientific_lock_established": False},
    }
    print(publish("AS015_EXECUTABILITY_DENIAL_REASON_CONTRACT.json", payload))


if __name__ == "__main__":
    main()
