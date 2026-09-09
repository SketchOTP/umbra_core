"""Publish the A/B/C attribution for inherited full-suite exclusions."""

from __future__ import annotations

from tools.as015_evidence import publish


BASELINES = {
    "sealed_as014": "b8977c6c05ad3ca89743368bbfd0fc48bb2b1ee7",
    "pre_as014": "a97171a2dab7c1750e2556727bce9e3648bb359a",
}

NODES = {
    "tests/test_d012.py::test_disposable_real_runtime_dry_run_and_process_audit": {
        "classification": "PREEXISTING_INHERITED_FAILURE",
        "reason": "legacy child-process launch exits before its startup status is recorded",
    },
    "tests/test_d012_process_boundary.py::test_full_distinct_process_campaign": {
        "classification": "PREEXISTING_INHERITED_FAILURE",
        "reason": "same legacy child-process launch surface as D-012 dry run",
    },
    "tests/test_d013ab_multineed_corridor.py::test_active_fatigue_recovery_uses_corridor_adjudication_once": {
        "classification": "STALE_BEHAVIOR_COUPLED_ASSERTION",
        "reason": "requires a historical resource choice although all three baselines select REST",
    },
    "tests/test_d013ab_multineed_corridor.py::test_integrity_and_stimulation_candidates_share_the_boundary": {
        "classification": "STALE_BEHAVIOR_COUPLED_ASSERTION",
        "reason": "omits ordinary target-bound ORIENT from its historical capability set in all three baselines",
    },
    "tests/test_d013ak_authority_reachability.py::test_default_13035_authority_retains_charge_without_changing_score": {
        "classification": "PREEXISTING_INHERITED_FAILURE",
        "reason": "reaches the same NO_SAFE_ACTION state in all three baselines",
    },
    "tests/test_d013h_v2_formal_readiness.py::test_real_perception_path_detects_material_resource_change": {
        "classification": "STALE_BEHAVIOR_COUPLED_ASSERTION",
        "reason": "the material key is unchanged under its legacy physical move in all three baselines",
    },
    "tests/test_d013y_integrated.py::test_cold_start_discovery_uses_physical_action_and_real_observation": {
        "classification": "STALE_BEHAVIOR_COUPLED_ASSERTION",
        "reason": "the fixed eighty-tick policy trajectory never acquires the expected current resource observation in all three baselines",
    },
}


def main() -> None:
    payload = {
        "schema": "AS015_COMPLETE_SUITE_INHERITED_EXCLUSIONS_V1",
        "directive": "UMBRA-AS-015",
        "current_candidate": "working_tree_prelock",
        "baselines": BASELINES,
        "comparison": "all listed nodes fail with materially identical assertions at current, sealed AS-014, and pre-AS-014",
        "nodes": NODES,
        "production_change_authorized": False,
        "replacement_authorized": False,
        "applicable_suite_exclusion": [
            "tests/test_close02x_prospective_recoverability.py",
            *[node.split("::", 1)[0] for node in NODES],
        ],
    }
    print(publish("AS015_COMPLETE_SUITE_INHERITED_EXCLUSIONS.json", payload))


if __name__ == "__main__":
    main()
