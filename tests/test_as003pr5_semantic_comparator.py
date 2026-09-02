"""Pure adversarial qualification for the prospectively locked R5 comparator."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from experiments.as003pr5.semantic_comparator import compare_run_records


ROOT = Path(__file__).parents[1]
CORPUS = json.loads(
    (ROOT / "experiments/as003pr5/AS003PR5_COMPARATOR_CORPUS.json").read_text(encoding="utf-8")
)
PREFORK = {
    "agent-root", "lineage-root", "birth-root", "commitment-root",
    "body-root", "binding-root", "schema-root", "profile-root", "habitat-root",
    "event-root", "model-root", "entity-root",
}


def _record(*, side: str) -> dict:
    session = f"session-{side}"
    event = f"event-{side}"
    request = f"request-{side}"
    state = {
        "identity": {
            "agent_id": "agent-root", "lineage_id": "lineage-root",
            "birth_event_id": "birth-root", "identity_commitment": "commitment-root",
        },
        "physiology": {"energy": 0.6, "fatigue": 0.2, "integrity": 1.0, "stimulation": 0.4},
        "embodiment_adapter": {
            "body_instance_id": "body-root", "attachment_generation": 1,
            "profile_id": "profile-root", "body_schema_id": "schema-root",
        },
        "embodiment": {"occupancy": {"body_instance_id": "body-root", "generation": 1}},
        "self_model": {
            "active": {"body_binding_id": "binding-root", "body_schema_id": "schema-root", "schema_version": 1}
        },
        "world_model": {
            "entities": {
                "entity-root": {"entity_id": "entity-root", "kind": "RESOURCE", "confidence": 0.8}
            },
            "models": {
                "model-root": {
                    "model_id": "model-root", "source_entity_id": "entity-root",
                    "action": "CHARGE", "predicted_effect": {"energy": 0.2}, "confidence": 0.75,
                }
            },
            "affordances": {},
            "state_hash": f"world-{side}",
        },
        "memory": {"episodes": {}}, "social": {"partners": {}},
        "development": {"stage": "juvenile"}, "individuality": {"novelty": 0.1},
        "temporal": {"age": 2, "session_id_at_commit": session, "state_hash": f"temporal-{side}"},
        "pending_action": {"request_id": request, "capability": "ORIENT"},
        "delayed_proposal": None,
        "session_id": session,
        "tick": 2,
        "metrics": {"cells": [["b", 2], ["a", 1]], "ticks": 2},
    }
    events = [
        {
            "sequence": 1, "event_id": "event-root", "agent_id": "agent-root",
            "event_type": "runtime_ready", "causal_parent_ids": [],
            "payload": {"body_instance_id": "body-root"},
            "payload_hash": "root-payload", "previous_event_hash": "genesis", "event_hash": "root-hash",
        },
        {
            "sequence": 2, "event_id": event, "agent_id": "agent-root",
            "event_type": "action_requested", "causal_parent_ids": ["event-root"],
            "payload": {"session_id": session, "request_id": request, "capability": "ORIENT"},
            "payload_hash": f"payload-{side}", "previous_event_hash": "root-hash", "event_hash": f"hash-{side}",
        },
    ]
    return {
        "final_authoritative_state": state,
        "authoritative_events": events,
        "timeline": [{"tick": 1, "capability": "ORIENT"}],
        "candidate_identities_by_tick": [{"tick": 1, "pool": ["ORIENT", "INSPECT"], "selected": "ORIENT"}],
        "rng_state": {"seed": 45878900, "state": [1, 2, 3]},
        "final_habitat_state": {
            "habitat_id": "habitat-root", "version": 0,
            "objects": [{"kind": "RESOURCE", "x": 4, "y": 3}],
        },
    }


def _case(case_id: str) -> tuple[dict, dict]:
    left = _record(side="left")
    right = _record(side="right")
    if case_id == "C01":
        right = copy.deepcopy(left)
    elif case_id == "C02":
        right["final_authoritative_state"]["embodiment_adapter"]["body_instance_id"] = "body-other"
    elif case_id == "C03":
        right["final_authoritative_state"]["self_model"]["active"]["body_schema_id"] = "schema-other"
    elif case_id == "C04":
        right["final_habitat_state"]["habitat_id"] = "habitat-other"
    elif case_id == "C05":
        right["authoritative_events"][1]["causal_parent_ids"] = [right["authoritative_events"][1]["event_id"]]
    elif case_id in {"C06", "C07", "C15"}:
        pass
    elif case_id == "C08":
        right["authoritative_events"][1]["payload"]["request_id"] = "request-unrelated"
    elif case_id == "C09":
        right["rng_state"]["state"][-1] = 4
    elif case_id == "C10":
        right["final_authoritative_state"]["physiology"]["fatigue"] = 0.21
    elif case_id == "C11":
        right["timeline"][0]["capability"] = "INSPECT"
    elif case_id == "C12":
        right["final_authoritative_state"]["world_model"]["models"]["model-root"]["confidence"] = 0.5
    elif case_id == "C13":
        right["final_habitat_state"]["objects"][0]["x"] = 5
    elif case_id == "C14":
        right["authoritative_events"] = list(reversed(right["authoritative_events"]))
    elif case_id == "C16":
        right["final_authoritative_state"]["temporal"]["age"] = 3
    elif case_id == "C17":
        right["final_authoritative_state"]["embodiment_adapter"]["attachment_generation"] = 2
    elif case_id == "C18":
        right["final_authoritative_state"]["pending_action"]["capability"] = "REST"
    elif case_id == "C19":
        right["final_authoritative_state"]["pending_action"]["request_id"] = right["final_authoritative_state"]["session_id"]
    elif case_id == "C20":
        model = right["final_authoritative_state"]["world_model"]["models"].pop("model-root")
        model["model_id"] = "model-renamed"
        right["final_authoritative_state"]["world_model"]["models"]["model-renamed"] = model
    elif case_id == "C21":
        right["final_authoritative_state"]["metrics"]["cells"].reverse()
    elif case_id == "C22":
        right["final_authoritative_state"]["embodiment"]["occupancy"]["body_instance_id"] = "body-stale"
    elif case_id == "C23":
        right["candidate_identities_by_tick"][0]["pool"].reverse()
    elif case_id == "C24":
        right["candidate_identities_by_tick"][0]["selected"] = "INSPECT"
    else:
        raise AssertionError(case_id)
    return left, right


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda case: case["id"])
def test_locked_comparator_corpus(case):
    left, right = _case(case["id"])
    report = compare_run_records(left, right, pre_fork_exact_ids=PREFORK)
    assert report["semantic_equal"] is case["expected_equal"], report


def test_corpus_contract_is_complete():
    assert [case["id"] for case in CORPUS["cases"]] == [f"C{index:02d}" for index in range(1, 25)]
    assert CORPUS["pass_requirement"] == {"false_positives": 0, "false_negatives": 0, "repeat_runs": 2}


def test_common_root_exact_ids_override_administrative_classification():
    left, right = _case("C07")
    report = compare_run_records(left, right, pre_fork_exact_ids=PREFORK | {"event-left"})
    assert report["semantic_equal"] is False
    assert report["first_semantic_divergence"]["reason"] == "PRE_FORK_IDENTITY_MISMATCH"
