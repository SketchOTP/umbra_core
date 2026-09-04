from __future__ import annotations

import json
from pathlib import Path

from experiments.as008.qualification import REGIMES, validate_seed_contract


def test_as008_seed_contract_has_four_disjoint_eight_seed_regimes():
    contract = validate_seed_contract()
    assert tuple(contract["regimes"]) == REGIMES
    flat = [seed for regime in REGIMES for seed in contract["regimes"][regime]]
    assert len(flat) == 32
    assert len(set(flat)) == 32
    assert contract["historical_overlap"] == []


def test_as008_runner_has_no_legacy_seed_fallback():
    source = Path("experiments/as008/qualification.py").read_text()
    assert "CLOSE02VR" not in source
    assert "fresh_seeds" not in source
    assert "fallback_seed_sources" in source


def test_as008_manifest_shape_is_frozen():
    path = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-008-fresh-integrated-viability-r1/AS008_FORMAL_SEED_MANIFEST.json")
    value = json.loads(path.read_text())
    assert value["seed_status"] == "frozen_before_formal_execution"
    assert value["runs"] == 32
    assert value["horizon_ticks"] == 7200
