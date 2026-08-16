"""D-013A focused regression for recovery-focus priority."""

from umbra_core.arbitration import Arbitrator
from umbra_core.physiology import Physiology
from umbra_core.util import SeededRNG


def test_energy_need_preempts_stale_non_energy_recovery_focus():
    physiology = Physiology(energy=0.0525, stimulation=0.14)
    arbitrator = Arbitrator()
    arbitrator.state.recovery_focus = "stimulation"

    chosen = arbitrator.select(
        physiology,
        [
            {
                "kind": "resource",
                "relative_direction": 0.0,
                "estimated_distance": 3.8,
                "confidence": 1.0,
                "uncertainty": 0.0,
            }
        ],
        181,
        SeededRNG(13013),
    )

    # D-013T closes the exact same-variable critical-boundary hole.
    assert chosen.capability == "SIGNAL_ASSISTANCE"
    assert chosen.params["reason"] == "energy_recovery_route_infeasible"
