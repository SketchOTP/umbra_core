import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from d014h_replay import replay_twice, synthetic_fixture
from d014h_regulation import canonical_bytes, evaluate


def test_synthetic_replay_is_byte_equal():
    result = replay_twice(synthetic_fixture())
    assert result["replay_equal"] is True
    assert canonical_bytes(result["first"]) == canonical_bytes(result["second"])


def test_existing_candidates_only_and_duplicate_provenance():
    result = evaluate(synthetic_fixture())
    assert [p["capability"] for p in result["proposals"]] == ["IDLE", "CHARGE"]
    assert result["proposals"][1]["provenance"]["duplicate_source_indices"] == [2]


def test_unknown_is_neutral_and_vector_is_preserved():
    payload = synthetic_fixture()
    payload["candidates"][0]["policy_context"] = {"policy_visible": True}
    result = evaluate(payload)
    idle = result["proposals"][0]
    assert idle["context"]["route"]["status"] == "UNKNOWN"
    assert idle["context"]["time_to_benefit"]["status"] == "UNKNOWN"
    assert idle["context"]["modifier"] == 0
    assert set(idle["context"]["successor"]["branches"][0]["values"]) == {
        "energy", "fatigue", "integrity", "stimulation"
    }
