from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from experiments.as003pr3.semantic_comparator import compare_run_records


CORPUS = json.loads(
    (Path(__file__).parents[1] / "experiments/as003pr3/COMPARATOR_CORPUS.json").read_text()
)


LEFT = {
    "session": "session-left",
    "event1": "event-left-1",
    "event2": "event-left-2",
    "entity1": "entity-left-1",
    "entity2": "entity-left-2",
    "model1": "model-left-1",
    "model2": "model-left-2",
    "affordance": "affordance-left",
    "prediction": "prediction-left",
    "error": "error-left",
}
RIGHT = {
    "session": "session-right",
    "event1": "event-right-1",
    "event2": "event-right-2",
    "entity1": "entity-right-1",
    "entity2": "entity-right-2",
    "model1": "model-right-1",
    "model2": "model-right-2",
    "affordance": "affordance-right",
    "prediction": "prediction-right",
    "error": "error-right",
}


def _record(ids: dict[str, str]) -> dict:
    state = {
        "schema_version": "8",
        "identity": {
            "agent_id": "agent:seeded",
            "lineage_id": "agent:seeded",
            "birth_event_id": "birth:seeded",
            "identity_commitment": "commitment:seeded",
        },
        "physiology": {"energy": 0.5, "fatigue": 0.2, "integrity": 1.0, "stimulation": 0.4},
        "embodiment": {"body": {"body_schema_id": "body:seeded", "position": [1.0, 2.0]}},
        "perception": {"history": [{"tick": 1, "kind": "RESOURCE"}]},
        "arbitration": {"last_action": "ORIENT"},
        "governance": {"decisions": [{"tick": 1, "allowed": True}]},
        "self_model": {
            "active": {"body_schema_id": "body:seeded", "capability_support": {"MOVE": "SUPPORTED"}},
            "predictions": [{"prediction_id": ids["prediction"], "capability": "MOVE", "confidence": 0.75}],
            "errors": [{"error_id": ids["error"], "prediction_id": ids["prediction"], "body_error": 0.1}],
        },
        "world_model": {
            "entities": {
                ids["entity1"]: {"entity_id": ids["entity1"], "entity_kind": "RESOURCE", "confidence": 0.8},
                ids["entity2"]: {"entity_id": ids["entity2"], "entity_kind": "REST", "confidence": 0.7},
            },
            "models": {
                ids["model1"]: {"model_id": ids["model1"], "action": "CHARGE", "source_entity_id": ids["entity1"], "predicted_effect": {"energy": 0.2}, "confidence": 0.8},
                ids["model2"]: {"model_id": ids["model2"], "action": "REST", "source_entity_id": ids["entity2"], "predicted_effect": {"fatigue": -0.2}, "confidence": 0.7},
            },
            "affordances": {
                ids["affordance"]: {"affordance_id": ids["affordance"], "entity_kind": "RESOURCE", "action": "CHARGE", "confidence": 0.9}
            },
            "predictions": [{"prediction_id": ids["prediction"], "source_model_id": ids["model1"], "action": "CHARGE"}],
            "contradictions": [],
            "supersessions": [],
            "plan_traces": [],
            "observation_log": [{"tick": 1, "kind": "RESOURCE"}],
            "prediction_errors": [0.1],
            "state_hash": f"world-hash-{ids['session']}",
        },
        "development": {"attempt_history": ["ORIENT", "CHARGE"], "competence": 0.2},
        "memory": {"episodes": {}, "beliefs": {}, "procedural": {}},
        "social": {"hypotheses": {}, "pending": {}},
        "individuality": {"dispositions": [{"dimension": "novelty", "value": 0.1}]},
        "temporal": {
            "organism_age_ticks": 2,
            "last_time_anchor": {"session_id_at_commit": ids["session"], "state_hash": f"anchor-{ids['session']}"},
            "state_hash": f"temporal-{ids['session']}",
        },
        "pending_action": None,
        "delayed_proposal": None,
        "session_id": ids["session"],
        "tick": 2,
        "metrics": {"cells": [["b", 2], ["a", 1]], "ticks": 2},
    }
    events = [
        {
            "sequence": 1,
            "event_id": ids["event1"],
            "agent_id": "agent:seeded",
            "event_type": "birth",
            "schema_version": "8",
            "monotonic_time": 0.0,
            "wall_time": 10.0,
            "causal_parent_ids": [],
            "payload": {"session_id": ids["session"], "kind": "birth"},
            "payload_hash": f"payload-{ids['session']}",
            "previous_event_hash": "genesis",
            "event_hash": f"event-hash-1-{ids['session']}",
        },
        {
            "sequence": 2,
            "event_id": ids["event2"],
            "agent_id": "agent:seeded",
            "event_type": "outcome_verified",
            "schema_version": "8",
            "monotonic_time": 1.0,
            "wall_time": 11.0,
            "causal_parent_ids": [ids["event1"]],
            "payload": {"session_id": ids["session"], "source_model_id": ids["model1"], "value": 1.0},
            "payload_hash": f"payload-2-{ids['session']}",
            "previous_event_hash": f"event-hash-1-{ids['session']}",
            "event_hash": f"event-hash-2-{ids['session']}",
        },
    ]
    return {
        "timeline": [{"tick": 1, "capability": "ORIENT"}, {"tick": 2, "capability": "CHARGE"}],
        "authoritative_events": events,
        "final_authoritative_state": state,
        "rng_state": {"seed": 45878900, "draws": [1, 2, 3]},
        "candidate_identities_by_tick": [
            {"tick": 1, "pool": ["ORIENT", "CHARGE"], "selected": "ORIENT"},
            {"tick": 2, "pool": ["ORIENT", "CHARGE"], "selected": "CHARGE"},
        ],
    }


def _case(case_id: str) -> tuple[dict, dict]:
    left = _record(LEFT)
    right = _record(RIGHT)
    if case_id == "C01":
        pass
    elif case_id == "C02":
        left["final_authoritative_state"]["session_id"] = LEFT["session"]
    elif case_id == "C03":
        pass
    elif case_id == "C04":
        pass
    elif case_id == "C05":
        right["final_authoritative_state"]["world_model"]["predictions"][0]["source_model_id"] = RIGHT["model2"]
    elif case_id == "C06":
        right["final_authoritative_state"]["identity"]["agent_id"] = "agent:other"
    elif case_id == "C07":
        right["final_authoritative_state"]["world_model"]["models"][RIGHT["model1"]]["predicted_effect"]["energy"] = 0.25
    elif case_id == "C08":
        right["final_authoritative_state"]["world_model"]["models"][RIGHT["model1"]]["confidence"] = 0.81
    elif case_id == "C09":
        right["final_authoritative_state"]["physiology"]["fatigue"] = 0.21
    elif case_id == "C10":
        right["timeline"] = list(reversed(right["timeline"]))
    elif case_id == "C11":
        right["final_authoritative_state"]["physiology"] = dict(reversed(list(right["final_authoritative_state"]["physiology"].items())))
    elif case_id == "C12":
        right["authoritative_events"] = list(reversed(right["authoritative_events"]))
    elif case_id == "C13":
        pass
    elif case_id == "C14":
        right["final_authoritative_state"]["temporal"]["organism_age_ticks"] = 3
    elif case_id == "C15":
        right_entities = right["final_authoritative_state"]["world_model"]["entities"]
        right["final_authoritative_state"]["world_model"]["entities"] = dict(reversed(list(right_entities.items())))
    elif case_id == "C16":
        pass
    elif case_id == "C17":
        right["final_authoritative_state"]["world_model"]["predictions"][0]["source_model_id"] = RIGHT["model2"]
    elif case_id == "C18":
        right["final_authoritative_state"]["world_model"]["affordances"][RIGHT["affordance"]]["confidence"] = 0.4
    elif case_id == "C19":
        pass
    elif case_id == "C20":
        right["final_authoritative_state"]["self_model"]["active"]["capability_support"]["MOVE"] = "UNSUPPORTED"
    elif case_id == "C21":
        pass
    elif case_id == "C22":
        pass
    elif case_id == "C23":
        pass
    elif case_id == "C24":
        right["authoritative_events"][1]["causal_parent_ids"] = [RIGHT["event2"]]
    elif case_id == "C25":
        right = copy.deepcopy(left)
    elif case_id == "C26":
        right["final_authoritative_state"]["development"]["competence"] = 0.3
    elif case_id == "C27":
        right["rng_state"] = copy.deepcopy(left["rng_state"])
    elif case_id == "C28":
        right["rng_state"]["draws"][-1] = 4
    else:
        raise AssertionError(case_id)
    return left, right


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda case: case["id"])
def test_locked_comparator_corpus(case):
    left, right = _case(case["id"])
    report = compare_run_records(left, right)
    assert report["semantic_equal"] is case["expected_equal"], report


def test_corpus_is_complete_and_immutable_shape():
    assert [case["id"] for case in CORPUS["cases"]] == [f"C{index:02d}" for index in range(1, 29)]
    assert CORPUS["pass_requirement"] == {"false_positives": 0, "false_negatives": 0, "deleted_cases": 0}


def test_comparator_reports_derivative_and_administrative_differences_separately():
    report = compare_run_records(_record(LEFT), _record(RIGHT))
    assert report["semantic_equal"] is True
    assert report["administrative_difference_count"] > 0
    assert report["derivative_difference_count"] > 0
    assert report["semantic_difference_count"] == 0
