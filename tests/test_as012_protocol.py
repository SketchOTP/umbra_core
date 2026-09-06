"""AS-012 exact-entrypoint and causal-isolation protections."""
from __future__ import annotations

from pathlib import Path

from experiments.as012.downstream import VARIANTS, ablation, boundedness, soak
from experiments.as012.full_config import config, fingerprint


def test_as012_boundedness_exact_entrypoint_short_run(tmp_path: Path):
    result = boundedness(39125001, tmp_path / "boundedness", ticks=40)
    assert result["ticks"] == 40
    assert result["restart_continuity"] is True
    assert "cpu_fraction_one_core" in result


def test_as012_soak_exact_entrypoint_short_run(tmp_path: Path):
    result = soak(39125002, tmp_path / "soak", warmup_seconds=0.2, measure_seconds=0.2)
    assert result["schema"] == "AS012_REALTIME_SOAK_RESULT_V1"
    assert result["restart_continuity"] is True


def test_as012_ablation_flags_are_matched_and_isolated(tmp_path: Path):
    rows = {variant: ablation(39125003, tmp_path / variant, variant, ticks=8) for variant in VARIANTS}
    assert {row["seed"] for row in rows.values()} == {39125003}
    assert rows["full"]["bounded_continuation_enabled"] is True
    assert rows["full"]["route_learning_enabled"] is True
    assert rows["terminal_readiness_disabled"]["terminal_readiness_seam"] is True
    assert rows["continuation_disabled"]["bounded_continuation_enabled"] is False
    assert rows["continuation_disabled"]["route_learning_enabled"] is True
    assert rows["route_learning_disabled"]["bounded_continuation_enabled"] is True
    assert rows["route_learning_disabled"]["route_learning_enabled"] is False


def test_as012_full_config_fingerprint_has_required_switches(tmp_path: Path):
    value = fingerprint(config(39125004, tmp_path / "config.sqlite", "R1"))
    assert value["bounded_continuation_enabled"] is True
    assert value["world_model_enabled"] is True
    assert value["world_model_config"]["route_demand_learning_enabled"] is True
