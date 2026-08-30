"""Pure zero-organism proofs for the AS-002 competition contract."""

from __future__ import annotations

import unittest

from experiments.as002 import analyze


def candidate(identity: str, channels: dict[str, analyze.EvidenceValue], noise: float) -> analyze.EvaluatedCandidate:
    return analyze.EvaluatedCandidate(identity, channels, noise)


class AS002CompetitionProof(unittest.TestCase):
    def test_same_input_is_deterministic(self) -> None:
        items = [candidate("A", {"x": analyze.supported(1)}, 0.1), candidate("B", {"x": analyze.supported(0)}, 0.9)]
        self.assertEqual(analyze.resolve(items), analyze.resolve(items))

    def test_supported_dominance_beats_larger_noise(self) -> None:
        a = candidate("A", {"x": analyze.supported(2)}, -1.0)
        b = candidate("B", {"x": analyze.supported(1)}, 1.0)
        self.assertTrue(analyze.dominates(a, b))
        self.assertEqual(analyze.resolve([a, b]).identity, "A")

    def test_cross_channel_conflict_is_not_summed(self) -> None:
        a = candidate("A", {"energy": analyze.supported(2), "fatigue": analyze.supported(0)}, 0.1)
        b = candidate("B", {"energy": analyze.supported(0), "fatigue": analyze.supported(2)}, 0.2)
        self.assertFalse(analyze.dominates(a, b))
        self.assertFalse(analyze.dominates(b, a))
        self.assertEqual(analyze.resolve([a, b]).identity, "B")

    def test_unknown_is_neutral_and_preserves_first_experience(self) -> None:
        known = candidate("known", {"effect": analyze.supported(2)}, 0.1)
        novel = candidate("novel", {"effect": analyze.unknown()}, 0.8)
        self.assertFalse(analyze.dominates(known, novel))
        self.assertIn("novel", [item.identity for item in analyze.frontier([known, novel])])

    def test_unknown_becoming_supported_changes_relation(self) -> None:
        a = candidate("A", {"effect": analyze.supported(2)}, 0.1)
        b_unknown = candidate("B", {"effect": analyze.unknown()}, 0.9)
        b_supported = candidate("B", {"effect": analyze.supported(1)}, 0.9)
        self.assertFalse(analyze.dominates(a, b_unknown))
        self.assertTrue(analyze.dominates(a, b_supported))

    def test_contradictory_revision_changes_relation_again(self) -> None:
        a = candidate("A", {"effect": analyze.supported(2, "v1")}, 0.1)
        b = candidate("B", {"effect": analyze.supported(1, "v1")}, 0.9)
        revised = candidate("B", {"effect": analyze.supported(3, "v2")}, 0.9)
        self.assertTrue(analyze.dominates(a, b))
        self.assertTrue(analyze.dominates(revised, a))

    def test_permutation_invariance(self) -> None:
        items = [candidate("A", {"x": analyze.supported(1)}, 0.1), candidate("B", {"x": analyze.supported(1)}, 0.2)]
        self.assertEqual(analyze.resolve(items).identity, analyze.resolve(list(reversed(items))).identity)

    def test_unrelated_weak_insertion_does_not_reverse_existing_relation(self) -> None:
        a = candidate("A", {"x": analyze.supported(2)}, 0.1)
        b = candidate("B", {"x": analyze.supported(1)}, 0.9)
        weak = candidate("W", {"x": analyze.supported(0)}, 9.0)
        self.assertTrue(analyze.dominates(a, b))
        self.assertTrue(analyze.dominates(a, b))
        self.assertEqual(analyze.resolve([a, b, weak]).identity, "A")

    def test_unrelated_deletion_preserves_survivor_evidence(self) -> None:
        a = candidate("A", {"x": analyze.supported(2)}, 0.1)
        b = candidate("B", {"x": analyze.supported(1)}, 0.9)
        weak = candidate("W", {"x": analyze.supported(0)}, 9.0)
        before = {item.identity: item.channels for item in analyze.frontier([a, b, weak])}
        after = {item.identity: item.channels for item in analyze.frontier([a, b])}
        self.assertEqual(before["A"], after["A"])

    def test_source_duplicate_cannot_amplify(self) -> None:
        a1 = candidate("same-behavior", {"x": analyze.supported(1)}, 0.2)
        a2 = candidate("same-behavior", {"x": analyze.supported(1)}, 0.2)
        self.assertEqual(len(analyze.frontier([a1, a2])), 1)

    def test_provenance_alone_does_not_change_relation(self) -> None:
        a = candidate("A", {"x": analyze.supported(1, "memory")}, 0.1)
        b = candidate("B", {"x": analyze.supported(1, "development")}, 0.2)
        self.assertFalse(analyze.dominates(a, b))
        self.assertFalse(analyze.dominates(b, a))

    def test_channel_count_is_not_a_vote(self) -> None:
        a = candidate("A", {"x": analyze.supported(2), "y": analyze.supported(0)}, 0.1)
        b = candidate("B", {"x": analyze.supported(1), "y": analyze.supported(1)}, 0.2)
        self.assertFalse(analyze.dominates(a, b))
        self.assertFalse(analyze.dominates(b, a))

    def test_stochastic_term_resolves_only_frontier(self) -> None:
        dominant = candidate("D", {"x": analyze.supported(2)}, -5.0)
        defeated = candidate("F", {"x": analyze.supported(1)}, 5.0)
        self.assertEqual(analyze.resolve([dominant, defeated]).identity, "D")

    def test_exact_stochastic_tie_uses_behavioral_identity(self) -> None:
        a = candidate("A", {"x": analyze.supported(1)}, 0.5)
        b = candidate("B", {"x": analyze.supported(1)}, 0.5)
        self.assertEqual(analyze.resolve([b, a]).identity, "A")

    def test_contract_produces_existing_candidate_only(self) -> None:
        items = [candidate("A", {"x": analyze.supported(1)}, 0.1), candidate("B", {"x": analyze.supported(1)}, 0.2)]
        self.assertIn(analyze.resolve(items), items)


if __name__ == "__main__":
    unittest.main()
