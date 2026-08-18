from __future__ import annotations

from types import MethodType

from umbra_core.arbitration import Arbitrator, Candidate
from umbra_core.governance import Governance
from umbra_core.physiology import Physiology, verified_outcome_effect_branches
from umbra_core.runtime import OrganismConfig, create_organism
from umbra_core.util import SeededRNG


def _fatigue_state() -> Physiology:
    return Physiology(energy=0.80, fatigue=0.95, integrity=0.90, stimulation=0.55)


def _rest_observation() -> list[dict[str, float | str]]:
    return [{"kind": "rest", "estimated_distance": 1.0, "relative_direction": 0.0}]


def _replace_with(arbitrator: Arbitrator, replacement: Candidate) -> None:
    def replace(self, phys, observations, chosen, tick):
        return replacement

    arbitrator._preserve_recoverability = MethodType(replace, arbitrator)


def _mark_unsafe(arbitrator: Arbitrator, predicate) -> None:
    def introduces(self, candidate, phys, *, ignore=None):
        return bool(predicate(candidate))

    arbitrator._introduces_critical_boundary = MethodType(introduces, arbitrator)


def test_safe_original_survives_unsafe_preservation_replacement():
    arbitrator = Arbitrator()
    replacement = Candidate("APPROACH", {"source": "unsafe_replacement"})
    _replace_with(arbitrator, replacement)
    _mark_unsafe(
        arbitrator,
        lambda candidate: candidate.params.get("source") == "unsafe_replacement",
    )

    chosen = arbitrator.select(
        _fatigue_state(), _rest_observation(), 1, SeededRNG(13013)
    )

    assert chosen.capability == "REST"
    assert chosen.params.get("source") != "no_safe_action"


def test_safe_preservation_replacement_remains_available():
    arbitrator = Arbitrator()
    replacement = Candidate("APPROACH", {"source": "safe_replacement"})
    _replace_with(arbitrator, replacement)
    _mark_unsafe(arbitrator, lambda candidate: False)

    chosen = arbitrator.select(
        _fatigue_state(), _rest_observation(), 1, SeededRNG(13013)
    )

    assert chosen is replacement


def test_safe_preservation_replacement_can_replace_unsafe_original():
    arbitrator = Arbitrator()
    replacement = Candidate("CHARGE", {"source": "safe_replacement"})
    _replace_with(arbitrator, replacement)
    _mark_unsafe(arbitrator, lambda candidate: candidate.capability == "REST")

    def alternatives(self, phys, observations, tick):
        return [Candidate("IDLE", {})]

    arbitrator.generate_candidates = MethodType(alternatives, arbitrator)
    chosen = arbitrator.select(
        _fatigue_state(), _rest_observation(), 1, SeededRNG(13013)
    )

    assert chosen is replacement


def test_unsafe_replacement_does_not_hide_another_safe_candidate():
    arbitrator = Arbitrator()
    replacement = Candidate("MOVE", {"source": "unsafe_replacement"})
    _replace_with(arbitrator, replacement)
    _mark_unsafe(
        arbitrator,
        lambda candidate: candidate.capability == "REST"
        or candidate.params.get("source") == "unsafe_replacement",
    )

    def alternatives(self, phys, observations, tick):
        return [Candidate("IDLE", {})]

    arbitrator.generate_candidates = MethodType(alternatives, arbitrator)
    chosen = arbitrator.select(
        _fatigue_state(), _rest_observation(), 1, SeededRNG(13013)
    )

    assert chosen.capability == "IDLE"
    assert chosen.params.get("source") != "no_safe_action"


def test_truly_empty_safe_set_remains_explicit_no_safe_action():
    arbitrator = Arbitrator()
    _mark_unsafe(
        arbitrator,
        lambda candidate: candidate.params.get("source") != "no_safe_action",
    )

    def alternatives(self, phys, observations, tick):
        return [Candidate("MOVE", {})]

    arbitrator.generate_candidates = MethodType(alternatives, arbitrator)
    chosen = arbitrator.select(
        _fatigue_state(), _rest_observation(), 1, SeededRNG(13013)
    )

    assert chosen.params["source"] == "no_safe_action"


def test_delayed_i3_tick_428_keeps_a_current_rule_safe_action(tmp_path):
    organism = create_organism(
        OrganismConfig(
            db_path=str(tmp_path / "delayed-i3.sqlite"),
            seed=13013,
            intervention="I3",
            world_model_enabled=True,
        )
    )
    try:
        rows = organism.run_ticks(428)
        chosen = rows[-1]
        assert chosen["tick"] == 428
        assert chosen.get("no_safe_action") is not True
        assert chosen["capability"] is not None
    finally:
        organism.close()


def test_delayed_orient_and_body_energy_scaling_semantics_are_unchanged():
    assert verified_outcome_effect_branches("ORIENT")[1] == {}
    outcome = Governance().verify_outcome(
        "MOVE",
        {"ok_raw": True, "reason": "ok", "energy_cost_scale": 2.0},
    )
    assert outcome.physiology_effects["energy"] == -0.01
