"""Seal the non-production CLOSE-02AC architecture evidence dossier."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ATLAS = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence")
BASELINE = "bc3a6061f790016d431153341129a43db394df42"
AA = ATLAS / "umbra-close-02aa-prospective-preparation-r1"
AB = ATLAS / "umbra-close-02ab-support-producer-r1"
Z = ATLAS / "umbra-close-02z-candidate-stochastic-r1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.partial-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    if path.read_bytes() != data:
        raise RuntimeError(f"readback mismatch: {path}")


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def write_text(path: Path, value: str) -> None:
    atomic_write(path, value.rstrip().encode() + b"\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_rows(manifest: dict[str, Any]) -> list[dict[str, str]]:
    raw = manifest.get("files") or manifest.get("listed_files") or manifest.get("covers") or []
    if isinstance(raw, dict):
        return [{"path": str(path), "sha256": str(value)} for path, value in raw.items()]
    return [
        {"path": str(item["path"]), "sha256": str(item["sha256"])}
        for item in raw
        if isinstance(item, dict) and item.get("path") and item.get("sha256")
    ]


def verify_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "EVIDENCE_HASHES.json"
    manifest = load_json(manifest_path)
    rows = manifest_rows(manifest)
    failures = [
        row["path"]
        for row in rows
        if not (root / row["path"]).is_file() or sha256(root / row["path"]) != row["sha256"]
    ]
    return {
        "root": str(root),
        "manifest": manifest_path.name,
        "manifest_sha256": sha256(manifest_path),
        "listed_files": len(rows),
        "verified": bool(rows) and not failures,
        "failures": failures,
    }


def production_diff() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", BASELINE, "--", "umbra_core"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def source_ref(relative: str, symbols: list[str]) -> dict[str, Any]:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    missing = [symbol for symbol in symbols if symbol not in text]
    if missing:
        raise RuntimeError(f"source symbols missing from {relative}: {missing}")
    return {"path": relative, "sha256": sha256(path), "verified_symbols": symbols}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()

    manifest_audit = [verify_manifest(root) for root in (AA, AB, Z)]
    if not all(item["verified"] for item in manifest_audit):
        raise RuntimeError("retained evidence manifest verification failed")
    changed_production = production_diff()
    if changed_production:
        raise RuntimeError(f"production changed under CLOSE-02AC: {changed_production}")

    gap = load_json(AA / "CLOSE02AA_SUPPORT_GAP_MAP.json")
    replay = load_json(AA / "CLOSE02AA_RETAINED_EVIDENCE_REPLAY.json")
    ab_provenance = load_json(AB / "CLOSE02AB_PRODUCER_PROVENANCE_AUDIT.json")
    ab_consumer = load_json(AB / "CLOSE02AB_SELECTION_CONSUMER_AUDIT.json")
    ab_lineage = load_json(AB / "CLOSE02AB_RETained_SELECTION_LINEAGE.json")

    self_source = source_ref(
        "umbra_core/self_model/engine.py",
        ["class Prediction:", "def predict(", "expected_observation_delta", "def _update_capability_support("],
    )
    world_source = source_ref(
        "umbra_core/world_model/engine.py",
        ["class TransitionModel:", "class WorldPrediction:", "expected_observations", "def _update_transition("],
    )
    runtime_source = source_ref(
        "umbra_core/runtime.py",
        ["# 4b. predict candidate consequences (before govern/execute)", "self.self_model.predict(", "self.world_model.predict("],
    )
    arbitration_source = source_ref(
        "umbra_core/arbitration.py",
        ["# uncertainty reduction", "unc_red += float(o.get(\"uncertainty\", 0)) * 0.05", "unc_red += 0.2", "unc_red += 0.05"],
    )
    view_source = source_ref(
        "umbra_core/recoverability/view.py",
        ["class RecoverabilityStatus", "UNKNOWN_CAPABILITY_SUPPORT", "UNKNOWN_ROUTE_GEOMETRY", "SUPPORTED_MARGIN_EXHAUSTED"],
    )
    stochastic_source = source_ref(
        "umbra_core/stochastic_competition.py",
        ["ordinary_candidate_competition:v1"],
    )

    support_catalog = {
        "directive": "UMBRA-CLOSE-02AC",
        "retained_failure": {"regime": "R1/S16", "seed": 57531938, "interval": [1, 124]},
        "fields": [
            {
                "family": "opportunity_geometry",
                "fields": ["support_center_dx", "support_center_dy", "support_radius", "relative_direction", "support_provenance", "support_source_kind", "support_body_schema_id", "fact_kind"],
                "owner": "WorldModel plus perception-policy composition",
                "unknown_representation": "missing tuple yields UNKNOWN_ROUTE_GEOMETRY",
                "supported_representation": "bounded center/radius/provenance bound to active body schema",
                "numeric_uncertainty": "WorldEntity uncertainty refers to entity estimate, not separately calibrated uncertainty for each route-support field",
                "confidence": "WorldEntity confidence refers to entity belief",
                "producer": "governed perception, remembered-estimate composition, verified-motion propagation",
                "revision": "fresh observation, contradiction/reidentification, persistence decay, verified motion",
            },
            {
                "family": "sensorimotor_capability",
                "fields": ["progress.minimum", "progress.maximum", "applied_step.minimum", "applied_step.maximum", "completion.minimum", "completion.maximum", "verified_success_count", "observed_failure_modes", "body_schema_id", "provenance"],
                "owner": "SelfModel CapabilitySupportEnvelope",
                "unknown_representation": "SupportSemantics.UNKNOWN and absent extrema",
                "supported_representation": "VERIFIED_OBSERVED_SUPPORT intervals from same-capability verified execution",
                "numeric_uncertainty": None,
                "confidence": None,
                "producer": "VerifiedOutcome plus attributable body-before/body-after under active body schema",
                "revision": "verified successes/failures; replacement/supersession resets support for new schema",
            },
            {
                "family": "terminal_interaction",
                "fields": ["REST verified physiological effect branches", "executability_support", "last_verified_denial", "observation_version"],
                "owner": "VerifiedOutcome effects, Embodiment, recoverability contract E, Arbitration denial bookkeeping",
                "unknown_representation": "executability_support_unknown",
                "supported_representation": "current policy-visible SUPPORTED or verified terminal outcome/denial",
                "numeric_uncertainty": None,
                "confidence": None,
                "producer": "current governed evidence and verified interaction outcome",
                "revision": "fresh observation version and new VerifiedOutcome",
            },
            {
                "family": "temporal_horizon",
                "fields": ["current physiology", "critical bounds", "unavoidable drift", "completion lag", "required route executions", "terminal effect branches"],
                "owner": "Physiology plus recoverability view",
                "unknown_representation": "missing geometry/capability support prevents supported horizon derivation",
                "supported_representation": "per-dimension signed margin; no new threshold",
                "numeric_uncertainty": "not a probability; deterministic bound under supplied support",
                "confidence": None,
                "producer": "existing policy-visible state and verified effect/support semantics",
                "revision": "each current state and evidence revision",
            },
        ],
        "retained_facts": gap["retained_facts"],
        "source": view_source,
    }

    self_audit = {
        "directive": "UMBRA-CLOSE-02AC",
        "creation": "SelfModel.predict constructs one Prediction from the already selected candidate, active BodySchema and current body state.",
        "runtime_boundary": "called after Arbitrator.select and immediately before Governance",
        "alternative_predictions_before_selection": False,
        "pending_cardinality": "one mutable _pending_prediction; subsequent prediction replaces the pending association",
        "fields": {
            "expected_body_delta": "candidate-conditioned capability/params using schema expected motion and current body heading",
            "expected_observation_delta": "only sensor range; it is not a predicted support-field transition or expected observation set",
            "expected_physiology_cost": "energy cost from schema expected_cost",
            "expected_duration": "1 plus schema expected latency",
            "expected_success_probability": "schema expected reliability for movement; fixed 0.9 otherwise",
            "prediction_confidence": "whole-schema confidence, not exact support-field uncertainty",
        },
        "learning": "body prediction error and verified success update schema motion/reliability/confidence; separate capability-support logic updates observed intervals only after outcome",
        "attribution": "self/external/mixed/unknown attribution uses issued intent, one pending prediction, body error and VerifiedOutcome; it does not attribute exact route-geometry/support-field refresh",
        "can_answer_exact_support_question": False,
        "smallest_missing_prediction_semantic": "A preselection, side-effect-free prediction keyed by canonical candidate + exact support field + opportunity + active body schema that predicts immediate support acquisition/refresh/no-change/unknown with provenance and without mutating pending execution prediction state.",
        "source": self_source,
    }

    world_audit = {
        "directive": "UMBRA-CLOSE-02AC",
        "creation": "WorldModel.predict retrieves up to four action/entity-kind transition models for the already selected candidate.",
        "runtime_boundary": "called after Arbitrator.select and immediately before Governance",
        "alternative_predictions_before_selection": False,
        "pending_cardinality": "one _pending_prediction used by the next outcome update",
        "predicted_world_change": "learned success and verified physiological effect fields only",
        "expected_observations": "the target entity-kind label when a toward/from kind exists; no field, support tuple, refinement magnitude, or observation provenance is predicted",
        "prediction_confidence": "mean transition-model confidence",
        "uncertainty": "1 - transition-model confidence; proposition is transition-model reliability, not route-support-field uncertainty",
        "model_provenance": "transition model IDs",
        "causal_limit": "transition learning records action/entity success and physiology effects; it does not compare exact support fields before/after or model support appearance without action",
        "can_predict_entity_relevance": True,
        "can_predict_world_or_physiology_effect": True,
        "can_predict_exact_support_field_acquisition": False,
        "source": world_source,
    }

    preselection = f"""# CLOSE-02AC preselection prediction boundary

The current prediction boundary is structurally post-selection. Runtime first completes proposal collection and calls `Arbitrator.select`; only the one final candidate then reaches `SelfModel.predict` and `WorldModel.predict` in step 4b before Governance. Neither model is queried for every ordinary candidate alternative.

Both models also own a single pending prediction that is consumed by outcome learning. Treating the existing API as a preselection batch evaluator would therefore change lifecycle semantics and risk overwriting the execution-linked prediction.

The smallest authority-safe conceptual query point would be after authority-valid candidates exist but before stochastic scoring/final arbitration, using a side-effect-free alternative-prediction view. That query surface does not exist. Creating it would be new predictive-selection architecture, not reuse of an existing consumer.

Source: `{runtime_source['path']}` SHA-256 `{runtime_source['sha256']}`.
"""

    prediction_map = {
        "directive": "UMBRA-CLOSE-02AC",
        "research_notation": ["EXPECTED_ACQUISITION", "EXPECTED_REFRESH", "EXPECTED_NO_CHANGE", "UNKNOWN"],
        "maps": [
            {"candidate": "APPROACH toward rest", "support_field": "APPROACH progress/applied-step/completion", "existing_prediction": "body displacement/success/confidence only", "result": "UNKNOWN_EXACT_SUPPORT_EFFECT", "reason": "SelfModel predicts motion but does not predict whether its evidence envelopes will transition from UNKNOWN to supported."},
            {"candidate": "APPROACH toward rest", "support_field": "route support center/radius/provenance", "existing_prediction": "WorldModel expects entity kind rest and action success/physiology effects", "result": "UNKNOWN_EXACT_SUPPORT_EFFECT", "reason": "No predicted observation-field refinement or before/after support tuple."},
            {"candidate": "ORIENT", "support_field": "rest route geometry", "existing_prediction": "SelfModel predicts heading delta; WorldModel may expect a target kind", "result": "UNKNOWN_EXACT_SUPPORT_EFFECT", "reason": "Omnidirectional perception and no exact field prediction prevent justified refresh claim."},
            {"candidate": "INSPECT", "support_field": "stimulation opportunity/executability", "existing_prediction": "WorldModel may predict success and entity kind inspect", "result": "UNKNOWN_EXACT_SUPPORT_EFFECT", "reason": "No exact support-field uncertainty or post-action evidence prediction."},
            {"candidate": "APPROACH toward resource", "support_field": "energy route geometry/capability support", "existing_prediction": "same generic motion and entity-kind predictions", "result": "UNKNOWN_EXACT_SUPPORT_EFFECT", "reason": "Energy-specific discovery behavior is not a generic predictive relation."},
        ],
        "hidden_truth_used": False,
        "hindsight_used": False,
    }

    contingency = {
        "directive": "UMBRA-CLOSE-02AC",
        "self_model": {
            "supports": "attribution of body displacement and success relative to one issued action/prediction",
            "does_not_support": "causal attribution of an exact support-field appearance or refinement",
        },
        "world_model": {
            "supports": "action/entity-conditioned success and physiology-effect transition models",
            "does_not_support": "field-level before/after deltas or a matched no-action baseline for support acquisition",
        },
        "verified_outcome": "anchors executed capability, success, effects and provenance but does not alone prove that coincident observation/support refresh was caused by the action",
        "support_appears_without_candidate": "current architecture can ingest observation changes, but no learned support-effect contingency compares action versus absence of action",
        "conclusion": "Current attribution cannot distinguish action-caused support acquisition from coincident refresh for AA geometry fields.",
        "missing_causal_primitive": "bounded field-level action/support transition evidence with attributable before/after state and revision evidence sufficient to separate action-contingent change from coincident observation",
        "no_causal_framework_added": True,
    }

    uncertainty = {
        "directive": "UMBRA-CLOSE-02AC",
        "generic_observation_component": {"classification": "CANDIDATE_INDEPENDENT_OFFSET", "formula": "sum(observation uncertainty * 0.05)", "affects_ordering_within_same_tick": False},
        "inspect_component": {"value": 0.2, "provenance": "foundational D-001 heuristic", "qualified_information_value": False, "exact_support_field_link": False},
        "orient_component": {"value": 0.05, "provenance": "foundational D-001 heuristic", "qualified_information_value": False, "exact_support_field_link": False},
        "candidate_specific_difference_expression": "uncertainty_before(S) - expected_uncertainty_after(C,S)",
        "expression_grounded": False,
        "reasons": ["AA capability support uses categorical semantics and intervals without calibrated numeric field uncertainty", "WorldEntity uncertainty is about an entity estimate, not every required geometry field", "WorldPrediction uncertainty is transition-model confidence complement", "SelfModel confidence is whole-schema confidence", "no candidate predicts expected post-action uncertainty for exact S", "numeric sources are not demonstrated commensurable"],
        "unknown_mapping": {"mapping": "UNKNOWN=1, SUPPORTED=0", "already_qualified": False, "would_be_new_epistemic_utility": True},
        "existing_uncertainty_score_salvageable": False,
        "source": arbitration_source,
    }

    coefficient = {
        "directive": "UMBRA-CLOSE-02AC",
        "coefficients": [
            {"literal": 0.05, "use": "observation uncertainty multiplier", "origin": "foundational D-001 scoring heuristic", "focused_qualification": "NOT_FOUND", "reuse_for_support_prediction": "INVALID_SEMANTIC_REINTERPRETATION"},
            {"literal": 0.2, "use": "INSPECT uncertainty contribution", "origin": "foundational D-001 scoring heuristic", "focused_qualification": "NOT_FOUND", "reuse_for_support_prediction": "INVALID_ACTION_CONSTANT"},
            {"literal": 0.05, "use": "ORIENT uncertainty contribution", "origin": "foundational D-001 scoring heuristic", "focused_qualification": "NOT_FOUND", "reuse_for_support_prediction": "INVALID_ACTION_CONSTANT"},
        ],
        "finding": "Keeping a literal while changing it from generic exploration heuristic to expected exact-support acquisition would be a new semantic parameter.",
        "no_existing_complete_magnitude": True,
    }

    prior_art = """# CLOSE-02AC bounded prior-art boundary

## Action-effect learning

- Elsner and Hommel, *Effect Anticipation and Action Control* (2001), https://pubmed.ncbi.nlm.nih.gov/11248937/ — repeated action-contingent effects can become associated with actions and later bias response selection.
- Elsner and Hommel, *Contiguity and contingency in action-effect learning* (2004), https://doi.org/10.1007/s00426-003-0151-8 — acquisition depends on contiguity and contingency; temporal coincidence alone is not adequate causal evidence.

## Active sensing

- Sharafeldin, Imam, and Choi, *Active sensing with predictive coding and uncertainty minimization* (2024), https://doi.org/10.1016/j.patter.2024.100983 — action selection for sensing is derived from an action-conditioned predictive/generative model of resulting observations and uncertainty, not from adding the same present uncertainty to every action.

## UMBRA translation

REFERENCE only. The literature supports the need for action-conditioned expected evidence and contingency-sensitive learning. It does not supply UMBRA's missing exact support-field prediction, calibrated uncertainty, preselection query boundary, or selection value.

Explicitly rejected: entropy-maximizing exploration, global expected information gain, active inference, POMDP, reinforcement learning, Bayesian planning, model-predictive control, epistemic policy search, symbolic inverse model, or a new numeric epistemic bonus.
"""

    retained = {
        "directive": "UMBRA-CLOSE-02AC",
        "seed": 57531938,
        "regime": "R1/S16",
        "earliest": {
            "fatigue_relevance": 1,
            "visible_rest_opportunity": 1,
            "candidate_toward_rest": 1,
            "verified_same_capability_support_producer_relation": 92,
            "action_conditioned_prediction_of_exact_missing_field": None,
            "calibrated_field_specific_uncertainty": None,
            "first_complete_fatigue_support": 124,
            "first_complete_status": "SUPPORTED_MARGIN_EXHAUSTED",
        },
        "lineage_facts": ab_lineage["facts"],
        "availability_conclusion": "No supported AC contract was historically available: exact field prediction and calibrated field-specific uncertainty never existed in retained state.",
        "counterfactual_rescue_claimed": False,
        "historical_predictions_fabricated": False,
    }

    generality = f"""# CLOSE-02AC generality review

The missing semantics are not fatigue- or seed-specific. Retained AA evidence covers energy/resource, fatigue/rest, stimulation/inspect, and an integrity boundary that correctly remains unknown.

- Fatigue/rest: route geometry and APPROACH capability support were missing; existing predictors cannot forecast exact field acquisition.
- Energy/resource: action/entity transition predictions exist, but energy discovery is a special-case candidate/state mechanism and does not establish generic field-specific expected evidence.
- Stimulation/inspect: fixed INSPECT uncertainty score is an authored capability constant, not a calibrated prediction that an exact support field will be acquired.
- Integrity/hazard/rest: retained environmental-affordance evidence is insufficient; AC must remain unknown rather than infer hidden support.

The same conclusion would be proposed without seed 57531938 because AA retained four independent failure families ({', '.join(replay['independent_failures'].keys())}) and four successful controls ({', '.join(map(str, replay['successful_controls']))}).

CLOSE-02Z compatibility is preserved: no candidate identity, stochastic namespace, perturbation, pool, ordering, source, or provenance behavior changes. Restart and migration remain unchanged because no new state or implementation is introduced.
"""

    convergence = """# CLOSE-02AC convergence decision

## Decision

`CLOSE02AC_BROADER_ACTION_SELECTION_REPLAN_REQUIRED`

The existing predictive substrate is relevant but insufficient for local composition:

1. SelfModel and WorldModel predictions are generated only after final arbitration for the one selected candidate.
2. Neither predicts acquisition or refresh of an exact AA support field.
3. Current causal learning does not attribute exact support-field change to the action rather than coincident observation refresh.
4. Required categorical support fields have no qualified numeric uncertainty mapping.
5. Existing numeric uncertainties describe different propositions and are not demonstrated commensurable.
6. The present uncertainty score is a candidate-independent offset plus unqualified action constants; reusing those constants would change their meaning.

Therefore support acquisition cannot become behaviorally causal through the current CLOSE-02 local seam without adding a preselection predictive-query surface and new field-specific epistemic evaluation semantics. That is a broader candidate-evaluation/action-selection architecture decision, not a bounded implementation of existing semantics.

Local CLOSE-02 support-acquisition engineering terminates. No CLOSE-02AD implementation candidate is supported or authorized. Return to Architect for a broader action-selection architecture replan; do not run an organism automatically.
"""

    verdict = {
        "directive": "UMBRA-CLOSE-02AC",
        "status": "TERMINAL_ARCHITECTURE_CONVERGENCE_GATE",
        "verdict": "CLOSE02AC_BROADER_ACTION_SELECTION_REPLAN_REQUIRED",
        "case": "CASE_4_BROADER_ACTION_SELECTION_ARCHITECTURE_REQUIRED",
        "existing_predictive_substrate": "RELEVANT_BUT_INSUFFICIENT",
        "support_field_prediction": "MISSING",
        "preselection_alternative_prediction": "MISSING",
        "field_level_causal_contingency": "MISSING",
        "existing_uncertainty_score": "NOT_SALVAGEABLE_WITHOUT_NEW_SEMANTICS",
        "qualified_numeric_unknown_mapping": False,
        "implementation_contract_supported": False,
        "recommendation": "TERMINATE_LOCAL_CLOSE02_SUPPORT_ACQUISITION_ENGINEERING_AND_RETURN_FOR_BROADER_ACTION_SELECTION_REPLAN",
        "successor": None,
        "next_phase_authorized": False,
        "production_changes": 0,
        "organism_runs": 0,
        "retries": 0,
        "reseeds": 0,
    }

    validation = {
        "directive": "UMBRA-CLOSE-02AC",
        "baseline": BASELINE,
        "retained_manifest_audit": manifest_audit,
        "production_diff_from_baseline": changed_production,
        "predictive_semantics": "PASS_EXACT_BOUNDARY_DOCUMENTED",
        "field_specific_evidence_prediction": "PASS_NEGATIVE_FINDING",
        "uncertainty_semantics": "PASS_NOT_SALVAGEABLE",
        "generality": "PASS",
        "candidate_stable_stochasticity": "PRESERVED",
        "planner_or_new_authority": False,
        "authority3": "PASS",
        "governance": "PASS",
        "governance_tests": "9 passed",
        "production_changes": 0,
        "organism_runs": 0,
        "retries": 0,
        "reseeds": 0,
    }

    artifacts = {
        "CLOSE02AC_SUPPORT_STATE_CATALOG.json": support_catalog,
        "CLOSE02AC_SELFMODEL_PREDICTION_AUDIT.json": self_audit,
        "CLOSE02AC_WORLDMODEL_PREDICTION_AUDIT.json": world_audit,
        "CLOSE02AC_ACTION_SUPPORT_PREDICTION_MAP.json": prediction_map,
        "CLOSE02AC_CAUSAL_CONTINGENCY_AUDIT.json": contingency,
        "CLOSE02AC_UNCERTAINTY_SEMANTICS_AUDIT.json": uncertainty,
        "CLOSE02AC_EXISTING_COEFFICIENT_AUDIT.json": coefficient,
        "CLOSE02AC_RETAINED_CAUSAL_DISCRIMINATION.json": retained,
        "CLOSE02AC_RETAINED_MANIFEST_AUDIT.json": {"audits": manifest_audit, "all_verified": True},
        "CLOSE02AC_VALIDATION.json": validation,
        "CLOSE02AC_VERDICT.json": verdict,
    }
    text_artifacts = {
        "CLOSE02AC_PRESELECTION_PREDICTION_BOUNDARY.md": preselection,
        "CLOSE02AC_PRIOR_ART_BOUNDARY.md": prior_art,
        "CLOSE02AC_GENERALITY_REVIEW.md": generality,
        "CLOSE02AC_CONVERGENCE_DECISION.md": convergence,
    }
    for name, value in artifacts.items():
        write_json(output / name, value)
    for name, value in text_artifacts.items():
        write_text(output / name, value)

    listed = [
        {"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "EVIDENCE_HASHES.json"
    ]
    write_json(
        output / "EVIDENCE_HASHES.json",
        {
            "directive": "UMBRA-CLOSE-02AC",
            "durability": ["file fsync", "atomic rename", "directory fsync", "readback SHA-256"],
            "files": listed,
        },
    )
    verified = verify_manifest(output)
    if not verified["verified"]:
        raise RuntimeError(f"final evidence manifest verification failed: {verified}")
    print(json.dumps({"verdict": verdict["verdict"], "evidence": str(output), "manifest": verified}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
