"""Pure R6F-R1 harness and symbol checks; no organism construction."""

from __future__ import annotations

from umbra_core.decision_trace import canonical_fingerprint
from umbra_core.physiology import verified_outcome_effect_branches


def test_corrected_symbols_are_callable() -> None:
    assert callable(canonical_fingerprint)
    assert callable(verified_outcome_effect_branches)


def test_corrected_symbols_are_purely_probeable() -> None:
    assert isinstance(canonical_fingerprint({"probe": True}), str)
    assert verified_outcome_effect_branches("IDLE")
