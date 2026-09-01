#!/usr/bin/env python3
"""Frozen read-only interpretation for fresh AS-003P-R3 evidence only."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


CLASS_KEYS = {
    "STRONG_MUST_CONTINUATION": "strong_must",
    "STRONG_MAY_CONTINUATION": "strong_may",
    "WEAK_MAY_CONTINUATION": "weak_may",
    "NO_CONTINUATION": "no_continuation",
    "UNKNOWN": "unknown",
}
OWNER_BY_CAPABILITY = {
    "CHARGE": frozenset({"energy"}),
    "REST": frozenset({"fatigue", "integrity"}),
    "INSPECT": frozenset({"stimulation"}),
}
KIND_BY_CAPABILITY = {
    "CHARGE": frozenset({"resource", "novel_crystal"}),
    "REST": frozenset({"rest"}),
    "INSPECT": frozenset({"inspect"}),
}
IDEAL = {"energy": 0.70, "fatigue": 0.20, "integrity": 0.85, "stimulation": 0.55}
VIABLE = {
    "energy": (0.30, 0.90),
    "fatigue": (0.05, 0.70),
    "integrity": (0.35, 0.98),
    "stimulation": (0.25, 0.80),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"non-object JSONL row at {path}:{number}")
            rows.append(value)
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def modality(row: Mapping[str, Any] | None) -> str:
    return str((row or {}).get("modality", "UNKNOWN"))


def candidate_profile_map(row: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(item.get("candidate_identity", "")): str(
            (item.get("profile") or {}).get("classification", "UNKNOWN")
        )
        for item in row.get("candidate_profiles", ())
        if item.get("candidate_identity")
    }


def available_services(frame: Mapping[str, Any]) -> list[dict[str, Any]]:
    capabilities = frame.get("constitutional_capabilities") or {}
    routes = frame.get("route_support") or {}
    timings = frame.get("service_timing") or {}
    rows: list[dict[str, Any]] = []
    for opportunity_id, opportunity in sorted((frame.get("opportunities") or {}).items()):
        kind = str(opportunity.get("kind", ""))
        for capability, kinds in KIND_BY_CAPABILITY.items():
            if kind not in kinds:
                continue
            requirements = {
                "capability": modality(capabilities.get(capability)),
                "future_opportunity": modality(opportunity.get("future")),
                "route": modality(routes.get(opportunity_id)),
                "timing": modality(timings.get(capability)),
            }
            if all(value in {"MUST", "MAY"} for value in requirements.values()):
                rows.append(
                    {
                        "identity": f"modal-service:{capability}:{opportunity_id}",
                        "capability": capability,
                        "owners": sorted(OWNER_BY_CAPABILITY[capability]),
                        "requirements": requirements,
                    }
                )
    return rows


def ordinary_physiology(frame: Mapping[str, Any]) -> bool:
    physiology = frame.get("physiology_root") or {}
    return all(
        low <= float(physiology.get(owner, float("nan"))) <= high
        for owner, (low, high) in VIABLE.items()
    )


def regulatory_conflict_dimensions(
    frame: Mapping[str, Any], views: Iterable[Mapping[str, Any]]
) -> list[str]:
    physiology = frame.get("physiology_root") or {}
    result: list[str] = []
    material = tuple(views)
    for owner in sorted(IDEAL):
        value = float(physiology.get(owner, IDEAL[owner]))
        if value == IDEAL[owner]:
            continue
        orders = {
            (view.get("channels") or {}).get(f"physiology.{owner}", {}).get("order")
            for view in material
            if (view.get("channels") or {}).get(f"physiology.{owner}", {}).get("status") == "SUPPORTED"
        }
        if len(orders) > 1:
            result.append(owner)
    return result


def views_differ(views: Iterable[Mapping[str, Any]]) -> bool:
    signatures = {
        json.dumps(view.get("channels") or {}, sort_keys=True, separators=(",", ":"))
        for view in views
    }
    return len(signatures) > 1


def pair_distinctions(profiles: Mapping[str, str]) -> int:
    return sum(
        left_class != right_class
        for (_, left_class), (_, right_class) in itertools.combinations(sorted(profiles.items()), 2)
    )


def analyze(planning_path: Path, decision_path: Path) -> dict[str, dict[str, Any]]:
    planning = read_jsonl(planning_path)
    decisions = read_jsonl(decision_path)
    decisions_by_tick = {int(row.get("tick", -1)): row for row in decisions}
    complete = [row for row in planning if "frame" in row and "candidate_profiles" in row]
    rejected = [row for row in planning if row not in complete]
    classes: Counter[str] = Counter()
    opportunity_modalities: Counter[str] = Counter()
    frame_distinctions = 0
    pair_distinction_count = 0
    max_frontier = 0
    overflow = 0
    candidate_count = 0
    exposure_rows: list[dict[str, Any]] = []
    ordinary_count = 0
    multi_drive_count = 0
    multiple_service_count = 0
    differing_consequence_count = 0
    future_uncertainty_count = 0
    exposed_count = 0
    exposed_distinction_count = 0

    for row in complete:
        frame = row["frame"]
        profiles = candidate_profile_map(row)
        candidate_count += len(profiles)
        for classification in profiles.values():
            classes[classification] += 1
        distinctions = pair_distinctions(profiles)
        if distinctions:
            frame_distinctions += 1
            pair_distinction_count += distinctions
        for item in row.get("candidate_profiles", ()):
            profile = item.get("profile") or {}
            active = int(profile.get("max_active_paths", 0))
            max_frontier = max(max_frontier, active)
            if profile.get("reason") == "BRANCH_FRONTIER_EXCEEDED" or active > 32:
                overflow += 1
        for opportunity in (frame.get("opportunities") or {}).values():
            for scope in ("current", "future"):
                opportunity_modalities[f"{scope}:{modality(opportunity.get(scope))}"] += 1

        tick = int(row.get("tick", frame.get("organism_tick", -1)))
        decision = decisions_by_tick.get(tick, {})
        competition = decision.get("distributed_competition") or {}
        views = tuple(competition.get("views") or ())
        ordinary = bool(len(views) >= 2 and ordinary_physiology(frame))
        conflict_dimensions = regulatory_conflict_dimensions(frame, views)
        services = available_services(frame)
        service_owners = sorted({owner for service in services for owner in service["owners"]})
        differing = views_differ(views)
        future_unknown = any(
            modality(opportunity.get("future")) == "UNKNOWN"
            for opportunity in (frame.get("opportunities") or {}).values()
        )
        multi_drive = ordinary and len(conflict_dimensions) >= 2
        multiple_services = len(services) >= 2 and len(service_owners) >= 2
        exposed = multi_drive and multiple_services and differing
        ordinary_count += int(ordinary)
        multi_drive_count += int(multi_drive)
        multiple_service_count += int(multiple_services)
        differing_consequence_count += int(differing)
        future_uncertainty_count += int(future_unknown)
        exposed_count += int(exposed)
        exposed_distinction_count += int(exposed and distinctions > 0)
        if exposed or distinctions:
            exposure_rows.append(
                {
                    "tick": tick,
                    "ordinary": ordinary,
                    "regulatory_conflict_dimensions": conflict_dimensions,
                    "available_services": services,
                    "differing_candidate_consequences": differing,
                    "future_opportunity_unknown": future_unknown,
                    "profile_pair_distinctions": distinctions,
                    "as003l_conflict_exposed": exposed,
                }
            )

    errors = [
        row.get("capture_error") or row.get("evaluation_error") or "INCOMPLETE_FRAME"
        for row in rejected
    ]
    modal_summary = {
        "schema": "AS003PR3_MODAL_EVIDENCE_SUMMARY_V1",
        "source": "fresh AS-003P-R3 planning trace only",
        "planning_trace_sha256": sha256(planning_path),
        "decision_trace_sha256": sha256(decision_path),
        "frames_attempted": len(planning),
        "frames_complete": len(complete),
        "frames_rejected": len(rejected),
        "capture_or_evaluation_errors": errors,
        "candidate_count": candidate_count,
        "profile_distribution": {
            key: classes.get(label, 0) for label, key in CLASS_KEYS.items()
        },
        "raw_profile_classifications": dict(sorted(classes.items())),
        "frames_with_candidate_profile_distinctions": frame_distinctions,
        "candidate_pairs_with_profile_distinctions": pair_distinction_count,
        "opportunity_modalities": dict(sorted(opportunity_modalities.items())),
        "branch_frontier_maximum": max_frontier,
        "branch_overflow_count": overflow,
    }
    exposure = {
        "schema": "AS003PR3_CONFLICT_EXPOSURE_AUDIT_V1",
        "definition": {
            "ordinary": "at least two distributed-competition candidates and all four physiology owners within viable bands",
            "multi_drive_active_conflict": "ordinary frame with at least two non-ideal physiology owners whose supported one-step consequences differ across candidates",
            "multiple_regulatory_services": "at least two modal services spanning at least two owners with capability, future opportunity, route, and timing each MUST or MAY",
            "as003l_residual_conflict": "multi-drive active conflict plus multiple source-backed regulatory services plus differing candidate consequence views",
        },
        "ordinary_decisions": ordinary_count,
        "multi_drive_active_conflict_decisions": multi_drive_count,
        "decisions_with_multiple_regulatory_services": multiple_service_count,
        "decisions_with_differing_candidate_consequences": differing_consequence_count,
        "decisions_where_future_opportunity_uncertainty_was_present": future_uncertainty_count,
        "decisions_exposing_as003l_residual_conflict": exposed_count,
        "exposed_decisions_with_profile_distinctions": exposed_distinction_count,
        "reported_rows": exposure_rows,
        "result": (
            "RELEVANT_EXPOSURE_WITH_MODAL_DISTINCTION"
            if exposed_distinction_count
            else "RELEVANT_EXPOSURE_WITHOUT_MODAL_DISTINCTION"
            if exposed_count
            else "FIXTURE_DID_NOT_EXPOSE_RELEVANT_CONFLICT"
        ),
    }
    if rejected:
        blocker = "EVIDENCE_UNKNOWN"
    elif exposed_distinction_count:
        blocker = "BLOCKER_EXPRESSED"
    elif exposed_count:
        blocker = "BLOCKER_NOT_EXPRESSED_DESPITE_EXPOSURE"
    else:
        blocker = "FIXTURE_DID_NOT_EXPOSE_BLOCKER"
    reassessment = {
        "schema": "AS003PR3_AS003L_REASSESSMENT_V1",
        "classification": blocker,
        "fresh_frames_complete": len(complete),
        "relevant_exposure_count": exposed_count,
        "relevant_exposure_with_profile_distinction_count": exposed_distinction_count,
        "modal_evidence_non_utility": True,
        "r1_invalid_counts_used": False,
    }
    future_relation = {
        "schema": "AS003PR3_AS002_FUTURE_RELATION_V1",
        "disposition": (
            "RELATIONAL_CONTRACT_RESEARCH_JUSTIFIED"
            if blocker == "BLOCKER_EXPRESSED"
            else "NO_RELATION_YET"
        ),
        "epistemic_strength_is_not_preference": True,
        "must_may_unknown_order_assumed": False,
        "as002_modified": False,
    }
    return {
        "AS003PR3_MODAL_EVIDENCE_SUMMARY.json": modal_summary,
        "AS003PR3_CONFLICT_EXPOSURE_AUDIT.json": exposure,
        "AS003PR3_AS003L_REASSESSMENT.json": reassessment,
        "AS003PR3_AS002_FUTURE_RELATION.json": future_relation,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--planning", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.planning, args.decision)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in result.items():
        destination = args.output / name
        destination.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: hashlib.sha256((args.output / name).read_bytes()).hexdigest() for name in sorted(result)}, sort_keys=True))


if __name__ == "__main__":
    main()
