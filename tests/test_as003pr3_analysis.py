"""Pure schema/exposure checks for frozen AS-003P-R3 interpretation tooling."""

from __future__ import annotations

import json

from tools.as003pr3_analyze import analyze


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def planning_row(*, classifications=("STRONG_MAY_CONTINUATION", "NO_CONTINUATION")):
    opportunities = {
        "resource:1": {
            "kind": "resource",
            "current": {"modality": "MUST"},
            "future": {"modality": "MAY"},
        },
        "rest:1": {
            "kind": "rest",
            "current": {"modality": "MUST"},
            "future": {"modality": "MAY"},
        },
    }
    frame = {
        "organism_tick": 1,
        "physiology_root": {"energy": 0.6, "fatigue": 0.3, "integrity": 0.8, "stimulation": 0.55},
        "constitutional_capabilities": {name: {"modality": "MUST"} for name in ("CHARGE", "REST")},
        "opportunities": opportunities,
        "route_support": {name: {"modality": "MUST"} for name in opportunities},
        "service_timing": {name: {"modality": "MUST"} for name in ("CHARGE", "REST")},
    }
    return {
        "tick": 1,
        "frame": frame,
        "candidate_profiles": [
            {
                "candidate_identity": f"candidate:{index}",
                "profile": {"classification": classification, "max_active_paths": 4, "reason": "fixture"},
            }
            for index, classification in enumerate(classifications)
        ],
    }


def decision_row():
    return {
        "tick": 1,
        "distributed_competition": {
            "views": [
                {
                    "identity": "candidate:0",
                    "channels": {
                        "physiology.energy": {"status": "SUPPORTED", "order": -0.1},
                        "physiology.fatigue": {"status": "SUPPORTED", "order": -0.3},
                    },
                },
                {
                    "identity": "candidate:1",
                    "channels": {
                        "physiology.energy": {"status": "SUPPORTED", "order": -0.2},
                        "physiology.fatigue": {"status": "SUPPORTED", "order": -0.1},
                    },
                },
            ]
        },
    }


def test_analysis_detects_exposed_distinction_without_preference_order(tmp_path):
    planning = tmp_path / "planning.jsonl"
    decision = tmp_path / "decision.jsonl"
    write_jsonl(planning, [planning_row()])
    write_jsonl(decision, [decision_row()])
    result = analyze(planning, decision)
    summary = result["AS003PR3_MODAL_EVIDENCE_SUMMARY.json"]
    exposure = result["AS003PR3_CONFLICT_EXPOSURE_AUDIT.json"]
    reassessment = result["AS003PR3_AS003L_REASSESSMENT.json"]
    relation = result["AS003PR3_AS002_FUTURE_RELATION.json"]
    assert summary["frames_complete"] == 1
    assert summary["frames_with_candidate_profile_distinctions"] == 1
    assert exposure["decisions_exposing_as003l_residual_conflict"] == 1
    assert reassessment["classification"] == "BLOCKER_EXPRESSED"
    assert relation["disposition"] == "RELATIONAL_CONTRACT_RESEARCH_JUSTIFIED"
    assert relation["must_may_unknown_order_assumed"] is False


def test_analysis_does_not_call_nonexposure_a_structural_failure(tmp_path):
    planning = tmp_path / "planning.jsonl"
    decision = tmp_path / "decision.jsonl"
    write_jsonl(planning, [planning_row(classifications=("STRONG_MAY_CONTINUATION", "STRONG_MAY_CONTINUATION"))])
    row = decision_row()
    row["distributed_competition"]["views"] = row["distributed_competition"]["views"][:1]
    write_jsonl(decision, [row])
    result = analyze(planning, decision)
    assert result["AS003PR3_CONFLICT_EXPOSURE_AUDIT.json"]["result"] == "FIXTURE_DID_NOT_EXPOSE_RELEVANT_CONFLICT"
    assert result["AS003PR3_AS003L_REASSESSMENT.json"]["classification"] == "FIXTURE_DID_NOT_EXPOSE_BLOCKER"
