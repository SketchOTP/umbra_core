"""Publish the AS-015 verified-executability-denial source-contract audit."""

from __future__ import annotations

from tools.as015_evidence import publish


def main() -> None:
    payload = {
        "directive": "UMBRA-AS-015",
        "predecessor_prefight_failure_sha256": "ba6db5c987a45c8391fa54bf34490107277c368b2f33e801a4f5736dc85eea1e",
        "source_graph": [
            "ordinary policy candidate generation",
            "Organism._candidate_executability",
            "Arbitrator execution_ready filtering",
            "Governance.execute_and_verify for admitted executed proposals",
            "Organism._finish_outcome",
            "WorldModel.observe_outcome",
        ],
        "confirmed_contracts": {
            "preflight_authority": "_candidate_executability uses adapter preflight then Embodiment.preflight_primitive and exposes only EXECUTABLE/NOT_EXECUTABLE/UNKNOWN",
            "executed_learning": "WorldModel.observe_outcome invokes _update_transition and _update_affordance only for a verified executed outcome",
            "transition_semantics": "_update_transition protects a single anomaly and weakens at its existing threshold",
            "affordance_semantics": "_update_affordance owns independent support/contradiction status and weakens only with existing thresholds",
            "manipulation_boundary": "observe_environmental_outcome rejects denied proposals and is MANIPULATE-specific; it is not a lawful reuse path",
        },
        "gap": "NOT_EXECUTABLE policy candidates have no deferred, policy-bound, verified affordance-denial learning channel",
        "required_properties": {
            "deferred_after_current_root": True,
            "deduplicated_by_semantic_candidate_and_root": True,
            "allowlisted_reason_only": True,
            "affordance_only": True,
            "no_hidden_habitat_identity": True,
            "no_rng_or_current_root_selection_effect": True,
        },
        "execution_boundary": {"formal_seed_consumed": False, "scientific_lock_established": False},
    }
    print(publish("AS015_VERIFIED_DENIAL_SOURCE_AUDIT.json", payload))


if __name__ == "__main__":
    main()
