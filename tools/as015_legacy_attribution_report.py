"""Publish the source-backed AS-015 pre-lock legacy-failure attribution."""

from __future__ import annotations

from tools.as015_evidence import publish


def main() -> None:
    payload = {
        "directive": "UMBRA-AS-015",
        "inputs": {
            "failure_inventory_sha256": "6809ce767c870d0d0ae5dec99089393582339444bf6bac4032758cf4fd5204ba",
            "baseline_differential_sha256": "01cb0a3daa56f4cc54657c754ece22085be3e884f31d13ea68969b5e7b8c55d7",
            "owner_path_audit_sha256": "e2ededd58984423abb21103a3464a137f2427387a85ad21a4903924afa257df1",
        },
        "classifications": [
            {
                "node_id": "tests/test_d003.py::test_contradiction_weakens_obsolete_model",
                "classification": "STALE_BEHAVIOR_COUPLED_ASSERTION",
                "basis": "all A/B/C baselines fail; the asserted 150-tick trajectory has zero verified CHARGE outcomes, so no contradictory CHARGE evidence reached WorldModel",
                "preserved_claim": "verified contradictory outcomes, not proposals or world truth, revise an established transition/affordance model while a single anomaly does not rewrite it",
            },
            {
                "node_id": "tests/test_d003.py::test_false_affordance_is_revised",
                "classification": "STALE_BEHAVIOR_COUPLED_ASSERTION",
                "basis": "all A/B/C baselines fail; the 160-tick trajectory has zero verified CHARGE outcomes and therefore cannot create or revise the asserted charge_from affordance",
                "preserved_claim": "verified contradictory outcomes can revise a learned affordance without hidden world truth",
            },
            {
                "node_id": "tests/test_d003.py::test_changed_affordance_adaptation",
                "classification": "STALE_BEHAVIOR_COUPLED_ASSERTION",
                "basis": "all A/B/C baselines fail; the 180-tick trajectory has zero verified CHARGE outcomes and zero CHARGE contradictions",
                "preserved_claim": "sufficient contradictory verified evidence weakens or supersedes an active learned model",
            },
            {
                "node_id": "tests/test_d006.py::test_full_tick_recognizes_proposes_governs_and_opens_pending",
                "classification": "STALE_BEHAVIOR_COUPLED_ASSERTION",
                "basis": "all A/B/C baselines fail; ten ticks recognize one partner but propose/select no social signal, hence governed execution and pending creation are never reached",
                "preserved_claim": "only an admitted and executed social signal may durably open a pending interaction",
            },
            {
                "node_id": "tests/test_d009.py::test_manipulation_candidates_compete_in_arbitration",
                "classification": "STALE_BEHAVIOR_COUPLED_ASSERTION",
                "basis": "all A/B/C baselines fail; policy-visible manipulation bindings generate two address-only MANIPULATE candidates, but the fixed selector chooses APPROACH. Existing D-009 execution-journal coverage protects governed manipulation after selection.",
                "preserved_claim": "policy-visible manipulation candidates participate lawfully and an admitted selected manipulation follows the trusted Governance/adapter/Habitat commit path",
            },
            {
                "node_id": "tests/test_d010.py::test_all_production_runtime_tick_uses_are_classified",
                "classification": "PREEXISTING_INHERITED_FAILURE",
                "basis": "all A/B/C baselines fail; the historical Q4 inventory keys entries by source line and is stale independently of AS-014/AS-015. This is a test-inventory maintenance defect, not a temporal-continuity finding.",
                "preserved_claim": "each current production runtime-tick dependency has one reviewed orchestration/temporal/boundedness classification; checkpoint prefix plus absolute retained tail preserve authoritative logical history",
            },
            {
                "node_id": "tests/test_d010.py::test_expression_adaptive_trim_on_rss_growth",
                "classification": "ENVIRONMENT_DEPENDENT_PERFORMANCE_ASSERTION",
                "basis": "all A/B/C baselines fail; the assertion prescribes a deterministic call count after a synthetic RSS sequence, whereas native allocator trimming is best-effort. The qualified claim is governed RSS boundedness, not a guaranteed immediate allocator release.",
                "preserved_claim": "adaptive maintenance is invoked only on measured growth, is non-behavioral, and governed RSS performance bounds remain enforced",
            },
        ],
        "nonregression": {
            "as015_viability_kernel_introduction": "RULED_OUT_BY_A_B_C",
            "as014_persistence_introduction": "RULED_OUT_BY_A_B_C",
            "formal_seed_consumed": False,
            "scientific_lock_established": False,
        },
        "required_next_step": "replace each stale assertion only with an equal-or-stronger current-authority test, then run exact nodes and owner suites",
    }
    print(publish("AS015_LEGACY_FAILURE_ATTRIBUTION.json", payload))


if __name__ == "__main__":
    main()
