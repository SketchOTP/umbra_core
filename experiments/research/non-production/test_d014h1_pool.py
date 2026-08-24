from __future__ import annotations

from d014h1_pool import MAX_PROPOSALS, current_production_fixture, evaluate, candidate_key
from d014h1_replay import replay_twice


def test_all_current_sources_are_emitted():
    result = evaluate(current_production_fixture())
    sources = {row["raw"]["source_name"] for row in result["source_emissions"]}
    assert sources == {
        "base_arbitration", "critical_recovery", "manipulation", "routine_habit",
        "development", "memory", "social", "world_model", "temporal",
        "individuality", "dormant_capability", "final_safety",
    }


def test_duplicate_identity_merges_without_source_weight():
    result = evaluate(current_production_fixture())
    idle = [g for g in result["dedup_groups"] if g["merged"]["capability"] == "IDLE"]
    assert len(idle) == 1
    assert idle[0]["merged"]["duplicate_count"] == 3
    assert idle[0]["merged"]["score_components"]["source_identity_bonus"] == 0.0


def test_source_neutral_tie_uses_candidate_key():
    payload = current_production_fixture()
    payload["proposals"] = payload["proposals"][:2]
    result = evaluate(payload)
    assert result["selected"]["candidate_key"] == min(
        candidate_key(row) for row in payload["proposals"]
    )


def test_overflow_is_fail_closed():
    payload = current_production_fixture()
    payload["proposals"] = payload["proposals"] * (MAX_PROPOSALS // len(payload["proposals"]) + 1)
    result = evaluate(payload)
    assert result["status"] == "OVERFLOW"


def test_deterministic_replay_is_byte_equal():
    assert replay_twice()["replay_equal"] is True
