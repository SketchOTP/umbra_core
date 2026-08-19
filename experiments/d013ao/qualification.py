from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import tempfile
from pathlib import Path
from types import MethodType
from typing import Any

import umbra_core

from umbra_core.arbitration import Candidate
from umbra_core.embodiment_adapters.adapter import AdapterRequest
from umbra_core.governance import authority_effect_branches
from umbra_core.recoverability import RecoverabilityStatus, derive_recoverability_view
from umbra_core.runtime import create_organism
from umbra_core.self_model.engine import SupportSemantics


MOTION = {"MOVE", "APPROACH", "RETREAT"}
STATIONARY = {"IDLE", "ORIENT"}
EPSILON = 1.0e-9
FROZEN_HELDOUT_MANIFEST_SHA256 = "f88db39243d839332bc5f99b0d4783f29581e81aa985abe8d63193bf0a402655"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def manifest_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_provenance(args: argparse.Namespace, frozen_hash: str) -> dict[str, Any]:
    umbra_package_root = Path(umbra_core.__file__).resolve().parent
    inputs = {
        "manifest": frozen_hash,
        "qualification": manifest_hash(Path(__file__)),
        "d013al_runner": manifest_hash(args.al_script),
        "d013al_controls": manifest_hash(args.al_controls_script),
        "d013al_per_case_analysis": manifest_hash(
            args.al_evidence / "PER_CASE_ANALYSIS.json"
        ),
        "umbra_core_python_tree": tree_hash(umbra_package_root, {".py"}),
        "d013al_evidence_inputs": tree_hash(args.al_evidence),
    }
    return {"schema": "D013AO_CACHE_PROVENANCE_V1", "input_sha256": inputs}


def tree_hash(root: Path, suffixes: set[str] | None = None) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        candidate
        for candidate in root.rglob("*")
        if candidate.is_file()
        and (suffixes is None or candidate.suffix in suffixes)
        and "__pycache__" not in candidate.parts
    ):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def trace_completed_ticks(trace: dict[str, Any]) -> int | None:
    for row in (trace, trace.get("result", {}), trace.get("summary", {})):
        value = row.get("completed_ticks") if isinstance(row, dict) else None
        if value is not None:
            return int(value)
    return None


def preserving_row(surgery: dict[str, Any]) -> dict[str, Any] | None:
    rows = [
        row
        for row in surgery.get("candidates", [])
        if row.get("currently_admissible")
        and row.get("classification") == "RETAINS_ROBUST_VIABILITY"
    ]
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda row: (
            row["candidate"]["capability"] not in STATIONARY,
            row["candidate"]["capability"] in MOTION,
        ),
    )[0]


def candidate_from(row: dict[str, Any]) -> Candidate:
    return Candidate(str(row["capability"]), dict(row.get("params") or {}))


def applied_candidate(org, candidate: Candidate, tick: int) -> dict[str, Any]:
    params = org._resolve_params(dict(candidate.params))
    if org.embodiment_adapter is not None:
        request = AdapterRequest(
            request_id=f"d013ao-shadow-{tick}",
            capability=candidate.capability,
            params=params,
            attachment_generation=org.embodiment_adapter.state.attachment_generation,
            tick=int(tick),
        )
        _, params, _ = org.embodiment_adapter.preflight_execution(request)
    result = dict(params)
    if candidate.capability in MOTION and "heading" in result:
        body_heading = float(org.embodiment.body.heading)
        delta = float(result.pop("heading")) - body_heading
        result["heading_delta"] = math.atan2(math.sin(delta), math.cos(delta))
    return {"capability": candidate.capability, "params": result}


def support_map(org) -> dict[str, dict[str, Any]]:
    if org.self_model is None:
        return {}
    return {
        capability: org.self_model.capability_support(capability)
        for capability in ("MOVE", "APPROACH", "RETREAT")
    }


def derive_for_candidate(org, phys, observations, tick: int, candidate: Candidate) -> dict[str, Any]:
    branches = authority_effect_branches(
        candidate,
        org.embodiment,
        org.embodiment_adapter,
        resolve_params=org._resolve_params,
    )
    return derive_recoverability_view(
        organism_tick=int(tick),
        body_schema_id=(
            org.self_model.active.body_schema_id if org.self_model is not None else "unknown"
        ),
        physiology=phys.to_state(),
        active_needs=phys.active_recovery_needs(),
        observations=copy.deepcopy(observations),
        candidate=applied_candidate(org, candidate, int(tick)),
        authority_effect_branches=branches,
        capability_support=support_map(org),
        body_energy_cost_scale=float(org.embodiment.body.energy_cost_scale),
        pending_commitment=bool(org.embodiment.to_state().get("pending_actuation")),
    )


def relation(selected: dict[str, Any], preserving: dict[str, Any]) -> dict[str, Any]:
    selected_projection = selected["candidate_projection"]
    preserving_projection = preserving["candidate_projection"]
    selected_margin = selected_projection.get("minimum_supported_margin")
    preserving_margin = preserving_projection.get("minimum_supported_margin")
    selected_status = selected_projection["status"]
    preserving_status = preserving_projection["status"]
    route_distinction = False
    if selected_margin is not None and preserving_margin is not None:
        route_distinction = float(selected_margin) < float(preserving_margin) - EPSILON
    if (
        selected_status == RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
        and preserving_status == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
    ):
        route_distinction = True

    selected_motion = selected_projection["candidate_motion_support"]
    preserving_motion = preserving_projection["candidate_motion_support"]
    selected_nonzero = (
        selected_motion.get("maximum") is not None
        and abs(float(selected_motion["maximum"])) > EPSILON
        and selected_motion.get("semantics")
        == SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value
    )
    preserving_hard_zero = (
        preserving_motion.get("minimum") == 0.0
        and preserving_motion.get("maximum") == 0.0
        and preserving_motion.get("semantics") == SupportSemantics.HARD_CONTRACT.value
    )
    structural_distinction = bool(
        selected_nonzero
        and preserving_hard_zero
        and int(selected.get("known_recovery_opportunity_count", 0)) > 0
    )
    sufficient_route_support = bool(
        selected_margin is not None
        and preserving_margin is not None
        and selected_projection.get("overall_semantics")
        in {
            SupportSemantics.HARD_CONTRACT.value,
            SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value,
        }
        and preserving_projection.get("overall_semantics")
        in {
            SupportSemantics.HARD_CONTRACT.value,
            SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value,
        }
    )
    return {
        "route_distinction": route_distinction,
        "structural_motion_vs_retention_distinction": structural_distinction,
        "distinguished": route_distinction or structural_distinction,
        "sufficient_route_support": sufficient_route_support,
        "selected_status": selected_status,
        "preserving_status": preserving_status,
        "selected_margin": selected_margin,
        "preserving_margin": preserving_margin,
        "false_confident": bool(
            selected_status == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
        ),
        "wrong_classification": bool(
            selected_status == RecoverabilityStatus.SUPPORTED_MARGIN_POSITIVE.value
            and preserving_status == RecoverabilityStatus.SUPPORTED_MARGIN_EXHAUSTED.value
        ),
    }


def capture_views(
    al,
    work: Path,
    *,
    name: str,
    seed: int,
    condition: str,
    intervention: str,
    target: int,
    selected_row: dict[str, Any],
    preserving_candidate_row: dict[str, Any],
) -> dict[str, Any]:
    org = create_organism(al.cfg(work, f"ao-{name}", seed, condition, intervention))
    original = org.arbitrator.select
    capture: dict[str, Any] = {}
    selected_candidate = candidate_from(selected_row)
    preserving_candidate = candidate_from(preserving_candidate_row)

    def traced(self, phys, observations, tick, rng, *extra, **kwargs):
        chosen = original(phys, observations, tick, rng, *extra, **kwargs)
        if int(tick) == target:
            selected_view = derive_for_candidate(
                org, phys, observations, int(tick), selected_candidate
            )
            preserving_view = derive_for_candidate(
                org, phys, observations, int(tick), preserving_candidate
            )
            capture.update(
                tick=int(tick),
                selected_view=selected_view,
                preserving_view=preserving_view,
                relation=relation(selected_view, preserving_view),
                policy_observation_count=len(observations),
                policy_geometry_count=sum(
                    observation.get("support_center_dx") is not None
                    and observation.get("support_radius") is not None
                    for observation in observations
                ),
                active_needs=phys.active_recovery_needs(),
                body_schema_id=(
                    org.self_model.active.body_schema_id
                    if org.self_model is not None
                    else None
                ),
            )
        return chosen

    org.arbitrator.select = MethodType(traced, org.arbitrator)
    try:
        while org.tick < target and not capture:
            org.tick_once()
    finally:
        org.close()
    return capture


def historical_qualification(al, al_evidence: Path, work: Path) -> list[dict[str, Any]]:
    cases = load(al_evidence / "PER_CASE_ANALYSIS.json")
    results: list[dict[str, Any]] = []
    for case in cases:
        scenario = str(case["scenario"])
        if scenario.startswith("long-") or scenario == "delayed-I3":
            continue
        surgery = case["surgery"]
        if not surgery.get("action_caused_viability_exit"):
            continue
        preserving = preserving_row(surgery)
        if preserving is None:
            continue
        print(f"historical {scenario}", flush=True)
        capture = capture_views(
            al,
            work,
            name=scenario,
            seed=int(case["seed"]),
            condition=str(case["condition"]),
            intervention=str(case["intervention"]),
            target=int(surgery["tick"]),
            selected_row=surgery["selected"],
            preserving_candidate_row=preserving["candidate"],
        )
        results.append(
            {
                "scenario": scenario,
                "seed": int(case["seed"]),
                "condition": case["condition"],
                "intervention": case["intervention"],
                "causal_family": case.get("causal_family"),
                "selected": surgery["selected"],
                "preserving_alternative": preserving["candidate"],
                "capture": capture,
            }
        )
    return results


def heldout_qualification(
    al,
    manifest: dict[str, Any],
    work: Path,
    out: Path,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in manifest["cases"]:
        print(f"heldout trace {item['name']}", flush=True)
        trace = al.trace_case(
            work,
            str(item["name"]),
            int(item["seed"]),
            str(item["condition"]),
            str(item["intervention"]),
            max_ticks=int(item["max_ticks"]),
        )
        hint = trace.get("first_no_safe_tick")
        result: dict[str, Any] = {
            **item,
            "first_no_safe_tick": hint,
            "action_caused_exit": False,
            "capture": None,
            "trace_completed_ticks": trace_completed_ticks(trace),
            "trace_disposition": "NO_BOUNDARY_WITHIN_FROZEN_HORIZON",
        }
        if hint is not None:
            print(f"heldout oracle {item['name']} at {hint}", flush=True)
            boundary = al.find_boundary(trace, int(hint))
            result["boundary"] = boundary
            result["trace_disposition"] = "BOUNDARY_NOT_REPRODUCED"
            if boundary.get("status") == "REPRODUCED":
                meta = (
                    str(item["name"]),
                    int(item["seed"]),
                    str(item["condition"]),
                    str(item["intervention"]),
                    int(hint),
                )
                surgery = al.surgery_at_boundary(work, meta, boundary)
                result["action_caused_exit"] = bool(
                    surgery.get("action_caused_viability_exit")
                )
                result["trace_disposition"] = "REPRODUCED_NON_ACTION_EXIT"
                result["causal_family"] = al.causal_family(trace, surgery)
                result["selected"] = surgery.get("selected")
                preserving = preserving_row(surgery)
                result["preserving_alternative"] = (
                    preserving["candidate"] if preserving is not None else None
                )
                if result["action_caused_exit"] and preserving is not None:
                    result["capture"] = capture_views(
                        al,
                        work,
                        name=str(item["name"]),
                        seed=int(item["seed"]),
                        condition=str(item["condition"]),
                        intervention=str(item["intervention"]),
                        target=int(surgery["tick"]),
                        selected_row=surgery["selected"],
                        preserving_candidate_row=preserving["candidate"],
                    )
                    result["trace_disposition"] = "QUALIFYING_ACTION_EXIT_CAPTURED"
        results.append(result)
        dump(out / "HELDOUT_RESULTS.partial.json", results)
    return results


def normalized_events(org) -> list[dict[str, Any]]:
    return [
        {
            "sequence": event["sequence"],
            "event_type": event["event_type"],
            "monotonic_time": event["monotonic_time"],
            "payload": normalize_diagnostic_ids(event["payload"]),
        }
        for event in org.store.iter_events()
    ]


def normalize_diagnostic_ids(value: Any) -> Any:
    """Remove only non-authoritative UUIDs minted by diagnostic SelfModel rows."""
    if isinstance(value, dict):
        return {
            key: normalize_diagnostic_ids(item)
            for key, item in value.items()
            if key
            not in {
                "prediction_id",
                "decision_id",
                "error_id",
                "snapshot_id",
                "old_model_id",
                "new_model_id",
            }
        }
    if isinstance(value, list):
        return [normalize_diagnostic_ids(item) for item in value]
    return value


def neutrality_run(al, work: Path, name: str, shadow: bool, ticks: int = 300) -> dict[str, Any]:
    org = create_organism(al.cfg(work, name, 13110, "C0", "I0"))
    original = org.arbitrator.select
    candidate_rows: list[Any] = []
    shadow_views: list[Any] = []

    def traced(self, phys, observations, tick, rng, *extra, **kwargs):
        generated = self.generate_candidates(phys, observations, tick)
        scored = [self.score_candidate(copy.deepcopy(c), phys, observations, tick) for c in generated]
        candidate_rows.append([al.candidate_dict(candidate) for candidate in scored])
        chosen = original(phys, observations, tick, rng, *extra, **kwargs)
        if shadow:
            shadow_views.append(derive_for_candidate(org, phys, observations, int(tick), chosen))
        return chosen

    org.arbitrator.select = MethodType(traced, org.arbitrator)
    runtime_rows: list[Any] = []
    try:
        for _ in range(ticks):
            runtime_rows.append(org.tick_once())
        return {
            "runtime_rows": normalize_diagnostic_ids(runtime_rows),
            "candidate_rows": candidate_rows,
            "rng_state": org.rng.export_state(),
            "events": normalized_events(org),
            "physiology": org.phys.to_state(),
            "body": org.embodiment.to_state(),
            "shadow_view_count": len(shadow_views),
        }
    finally:
        org.close()


def summarize(
    historical: list[dict[str, Any]], heldout: list[dict[str, Any]]
) -> dict[str, Any]:
    historical_relations = [row["capture"]["relation"] for row in historical if row["capture"]]
    heldout_exits = [row for row in heldout if row["action_caused_exit"]]
    heldout_captures = [row for row in heldout_exits if row.get("capture")]
    heldout_relations = [row["capture"]["relation"] for row in heldout_captures]
    return {
        "historical": {
            "cases": len(historical_relations),
            "distinguished": sum(row["distinguished"] for row in historical_relations),
            "correct_unknown": sum(not row["distinguished"] for row in historical_relations),
            "false_confident": sum(row["false_confident"] for row in historical_relations),
            "wrong": sum(row["wrong_classification"] for row in historical_relations),
        },
        "heldout": {
            "cases": len(heldout),
            "action_caused_exits": len(heldout_exits),
            "no_boundary_observed": sum(
                row.get("trace_disposition") == "NO_BOUNDARY_WITHIN_FROZEN_HORIZON"
                for row in heldout
            ),
            "unresolved_replays": sum(
                row.get("trace_disposition") == "BOUNDARY_NOT_REPRODUCED"
                for row in heldout
            ),
            "reproduced_non_action_exits": sum(
                row.get("trace_disposition") == "REPRODUCED_NON_ACTION_EXIT"
                for row in heldout
            ),
            "sufficient_policy_support": sum(
                row["sufficient_route_support"] for row in heldout_relations
            ),
            "correctly_distinguished": sum(
                row["distinguished"] and row["sufficient_route_support"]
                for row in heldout_relations
            ),
            "unknown": sum(
                not (row["distinguished"] and row["sufficient_route_support"])
                for row in heldout_relations
            ),
            "false_confident": sum(row["false_confident"] for row in heldout_relations),
            "wrong": sum(row["wrong_classification"] for row in heldout_relations),
        },
    }


def first_difference(left: list[Any], right: list[Any]) -> dict[str, Any] | None:
    for index, (left_item, right_item) in enumerate(zip(left, right)):
        if left_item != right_item:
            return {"index": index, "off": left_item, "on": right_item}
    if len(left) != len(right):
        return {"index": min(len(left), len(right)), "off_length": len(left), "on_length": len(right)}
    return None


def qualification_errors(
    result: dict[str, Any],
    historical: list[dict[str, Any]],
    heldout: list[dict[str, Any]],
    controls: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    historical_summary = result["historical"]
    heldout_summary = result["heldout"]
    neutrality = result["shadow_neutrality"]
    heldout_exits = [row for row in heldout if row.get("action_caused_exit")]
    if len(historical) != 13 or any(not row.get("capture") for row in historical):
        errors.append("HISTORICAL_CAPTURE_INCOMPLETE")
    if int(historical_summary["distinguished"]) < 11:
        errors.append("HISTORICAL_DISTINCTION_BELOW_GATE")
    if historical_summary["false_confident"] or historical_summary["wrong"]:
        errors.append("HISTORICAL_CLASSIFICATION_ERROR")
    if len(heldout) != 12:
        errors.append("HELDOUT_MANIFEST_COVERAGE_INCOMPLETE")
    if result.get("manifest_sha256") != FROZEN_HELDOUT_MANIFEST_SHA256:
        errors.append("HELDOUT_FROZEN_MANIFEST_HASH_MISMATCH")
    if result.get("manifest_frozen_before_labels") is not True:
        errors.append("HELDOUT_MANIFEST_NOT_FROZEN_BEFORE_LABELS")
    if result.get("heldout_manifest_exact") is not True:
        errors.append("HELDOUT_MANIFEST_IDENTITY_MISMATCH")
    valid_dispositions = {
        "NO_BOUNDARY_WITHIN_FROZEN_HORIZON",
        "BOUNDARY_NOT_REPRODUCED",
        "REPRODUCED_NON_ACTION_EXIT",
        "QUALIFYING_ACTION_EXIT_CAPTURED",
    }
    if any(row.get("trace_disposition") not in valid_dispositions for row in heldout):
        errors.append("HELDOUT_REPLAY_DISPOSITION_MISSING")
    if any(not row.get("capture") for row in heldout_exits):
        errors.append("HELDOUT_ACTION_EXIT_CAPTURE_INCOMPLETE")
    if int(heldout_summary["sufficient_policy_support"]) < 2:
        errors.append("HELDOUT_POLICY_SUPPORT_BELOW_GATE")
    if (
        heldout_summary["correctly_distinguished"]
        != heldout_summary["sufficient_policy_support"]
    ):
        errors.append("HELDOUT_SUPPORTED_CASE_NOT_DISTINGUISHED")
    if heldout_summary["false_confident"] or heldout_summary["wrong"]:
        errors.append("HELDOUT_CLASSIFICATION_ERROR")
    if any(
        neutrality.get(key) is not True
        for key in ("runtime_rows", "candidate_rows", "rng_state", "events", "physiology", "body")
    ) or int(neutrality.get("shadow_view_count", 0)) != 300:
        errors.append("SHADOW_NEUTRALITY_FAIL")
    formal_s2 = controls["formal_s2"]
    if (
        formal_s2.get("survived") is not True
        or formal_s2.get("robust_viability") is not True
        or int(formal_s2.get("completed_ticks", 0)) != 7200
    ):
        errors.append("FORMAL_S2_CONTROL_FAIL")
    for name in ("ample_energy", "ample_rest", "ample_both"):
        if controls[name].get("pass") is not True:
            errors.append(f"{name.upper()}_CONTROL_FAIL")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--al-script", type=Path, required=True)
    parser.add_argument("--al-controls-script", type=Path, required=True)
    parser.add_argument("--al-evidence", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = load(args.manifest)
    frozen_hash = manifest_hash(args.manifest)
    current_cache_provenance = cache_provenance(args, frozen_hash)
    al = load_module("d013al_runner", args.al_script)
    controls_module = load_module("d013al_controls", args.al_controls_script)
    work = Path(tempfile.mkdtemp(prefix="d013ao-", dir="/mnt/storage1tb/tmp"))
    try:
        historical_path = args.out / "HISTORICAL_RESULTS.json"
        heldout_path = args.out / "HELDOUT_RESULTS.json"
        cache_provenance_path = args.out / "CACHE_PROVENANCE.json"
        cache_is_current = (
            cache_provenance_path.exists()
            and load(cache_provenance_path) == current_cache_provenance
        )
        if historical_path.exists() and cache_is_current:
            print("reusing completed historical results", flush=True)
            historical = load(historical_path)
        else:
            historical = historical_qualification(al, args.al_evidence, work)
            dump(historical_path, historical)
        if heldout_path.exists() and cache_is_current:
            print("reusing completed frozen-heldout results", flush=True)
            heldout = load(heldout_path)
        else:
            heldout = heldout_qualification(al, manifest, work, args.out)
            dump(heldout_path, heldout)
        dump(cache_provenance_path, current_cache_provenance)
        for row in historical:
            capture = row.get("capture")
            if capture:
                capture["relation"] = relation(
                    capture["selected_view"], capture["preserving_view"]
                )
        for row in heldout:
            capture = row.get("capture")
            if capture:
                capture["relation"] = relation(
                    capture["selected_view"], capture["preserving_view"]
                )
        dump(historical_path, historical)
        dump(heldout_path, heldout)
        summary = summarize(historical, heldout)
        off = neutrality_run(al, work, "neutrality-off", False)
        on = neutrality_run(al, work, "neutrality-on", True)
        neutrality = {
            key: off[key] == on[key]
            for key in (
                "runtime_rows",
                "candidate_rows",
                "rng_state",
                "events",
                "physiology",
                "body",
            )
        }
        neutrality["shadow_view_count"] = on["shadow_view_count"]
        dump(
            args.out / "NEUTRALITY_DIAGNOSTIC.json",
            {
                "runtime_first_difference": first_difference(
                    off["runtime_rows"], on["runtime_rows"]
                ),
                "event_first_difference": first_difference(off["events"], on["events"]),
            },
        )
        dump(args.out / "SHADOW_NEUTRALITY.json", neutrality)
        controls = {
            "formal_s2": al.formal_s2_control(work),
            "ample_energy": controls_module.run(
                work, "ao-ample-energy", energy=0.8, fatigue=0.68
            ),
            "ample_rest": controls_module.run(
                work, "ao-ample-rest", energy=0.31, fatigue=0.2
            ),
            "ample_both": controls_module.run(
                work, "ao-ample-both", energy=0.8, fatigue=0.2
            ),
            "stale_opportunity": next(
                row for row in historical if row["scenario"] == "default-13024"
            ),
            "no_known_opportunity": next(
                row for row in historical if row["scenario"] == "combined-I4-C5"
            ),
            "energy_scale_i7": next(
                row for row in historical if row["scenario"] == "energy-scale-I7"
            ),
        }
        dump(args.out / "CONTROL_RESULTS.json", controls)
        result = {
            "manifest_sha256": frozen_hash,
            "manifest_frozen_before_labels": manifest.get("frozen_before_labels") is True,
            "heldout_manifest_exact": [
                (row["name"], row["seed"], row["condition"], row["intervention"], row["max_ticks"])
                for row in heldout
            ] == [
                (row["name"], row["seed"], row["condition"], row["intervention"], row["max_ticks"])
                for row in manifest["cases"]
            ],
            **summary,
            "shadow_neutrality": neutrality,
            "formal_s2": controls["formal_s2"],
        }
        errors = qualification_errors(result, historical, heldout, controls)
        result["qualification_errors"] = errors
        result["pass"] = not errors
        dump(args.out / "QUALIFICATION_SUMMARY.json", result)
        print(json.dumps(result, indent=2, sort_keys=True), flush=True)
        if errors:
            raise RuntimeError("D013AO_QUALIFICATION_FAIL:" + ",".join(errors))
    finally:
        # The work root contains only disposable run databases.  Evidence has
        # already been copied to the separate output directory.
        import shutil

        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
