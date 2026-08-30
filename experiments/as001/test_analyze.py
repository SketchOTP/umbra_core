"""Focused zero-organism proofs for the AS-001 architecture analysis."""

from __future__ import annotations

import unittest

from experiments.as001 import analyze


class AS001ArchitectureProof(unittest.TestCase):
    def test_authority_path_is_complete(self) -> None:
        stages = analyze.authority_map()["stages"]
        self.assertEqual([row["index"] for row in stages], list(range(1, 27)))

    def test_all_required_subsystems_are_classified(self) -> None:
        rows = analyze.causal_matrix()["classifications"]
        self.assertEqual(len(rows), 11)
        self.assertTrue(all(row["primary_class"] for row in rows))

    def test_scalar_score_commensurability_is_not_claimed(self) -> None:
        audit = analyze.score_audit()
        self.assertEqual(audit["commensurability"], "DISPROVEN_AS_A_SCIENTIFIC_CLAIM")
        self.assertEqual(len(audit["components"]), 11)

    def test_preselection_query_preserves_unknown(self) -> None:
        _, feasibility = analyze.predictive_audit()
        self.assertFalse(feasibility["fundamental_predictive_redesign_required"])
        self.assertFalse(feasibility["current_methods_safe_for_preselection"])
        self.assertIn("no learning", feasibility["pure_query_contract"])

    def test_architecture_comparison_is_bounded_to_three(self) -> None:
        text = analyze.architecture_candidates_markdown()
        self.assertEqual(text.count("## Candidate "), 3)
        self.assertIn("Evidence-conditioned distributed competition", text)

    def test_protected_stochastic_substrate_is_present(self) -> None:
        checks = analyze.source_assertions()["checks"]
        self.assertTrue(checks["candidate_stable_namespace"])
        self.assertTrue(checks["verified_only_learning"])

    def test_terminal_verdict_does_not_authorize_successor(self) -> None:
        result = analyze.verdict()
        self.assertEqual(result["verdict"], "AS001_CURRENT_ARBITRATION_REPLACEMENT_REQUIRED")
        self.assertFalse(result["implementation_successor_authorized"])
        self.assertEqual(result["organism_runs"], 0)

    def test_planner_import_is_rejected(self) -> None:
        review = analyze.prior_art_markdown()
        self.assertIn("recursive rollout", review)
        self.assertIn("rejected", review.lower())


if __name__ == "__main__":
    unittest.main()
