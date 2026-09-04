from pathlib import Path

from experiments.as010.full_config import as010_config, semantic_fingerprint


def test_as010_full_flags_are_explicit():
    value = as010_config(101, Path("/tmp/as010-test.sqlite"), "R0")
    fingerprint = semantic_fingerprint(value)
    assert fingerprint["bounded_continuation_enabled"] is True
    assert fingerprint["world_model_enabled"] is True
    assert fingerprint["world_model_config"]["route_demand_learning_enabled"] is True
    assert fingerprint["world_model_config"]["planning_enabled"] is True


def test_as010_regime_scenarios_are_canonical():
    assert as010_config(101, Path("/tmp/as010-test.sqlite"), "R0").temporal_scenario_id == "S0"
    assert as010_config(101, Path("/tmp/as010-test.sqlite"), "R1").temporal_scenario_id == "S16"
    assert as010_config(101, Path("/tmp/as010-test.sqlite"), "R2").temporal_scenario_id == "S10"
    assert as010_config(101, Path("/tmp/as010-test.sqlite"), "R3").temporal_scenario_id == "S12"
