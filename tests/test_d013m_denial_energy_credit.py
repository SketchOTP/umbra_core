"""D-013M verifies denied recovery cannot grant positive energy."""

from umbra_core.governance import Governance
from umbra_core.physiology import Physiology


def test_verified_denied_charge_has_no_positive_energy_credit():
    physiology = Physiology(energy=0.2395, drift_enabled=False)
    before = physiology.energy
    outcome = Governance().verify_outcome(
        "CHARGE",
        {"ok_raw": False, "reason": "not_at_resource"},
    )

    physiology.apply_outcome_effects(outcome.physiology_effects)

    assert outcome.verified is True
    assert outcome.success is False
    assert outcome.physiology_effects["energy"] < 0
    assert physiology.energy < before
