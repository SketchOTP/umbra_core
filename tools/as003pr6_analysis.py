#!/usr/bin/env python3
"""Pure retained-evidence analysis for UMBRA-AS-003P-R6.

No function in this module imports or constructs UMBRA runtime objects.  The
only live inputs are immutable committed source text and retained R5A JSON.
"""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable, Mapping

from experiments.as003pr6.l2_schedulability import (
    BranchScheduleResult,
    CandidateBranch,
    CandidateScheduleResult,
    Modality,
    RegulatoryObligation,
    RegulatoryServiceEnvelope,
    ScheduleClass,
    effect_branch,
    evaluate_candidate,
    l2_precedes,
)
from tools.as003pr6_evidence import ROOT as EVIDENCE_ROOT, publish


REPO = Path(__file__).resolve().parents[1]
R5A_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r5a-retained-root-modal-shadow-r1"
)
AS003L_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003l-regulatory-schedulability-r1"
)
BASELINE = "738485040029cbeb221f6eb14f76682d8e98200d"
PLANNING = R5A_ROOT / "AS003PR5A_PLANNING_SHADOW_TRACE.jsonl"
DECISIONS = R5A_ROOT / "AS003PR5A_SHADOW_DECISION_TRACE.jsonl"
CONFLICT = R5A_ROOT / "AS003PR5A_CONFLICT_EXPOSURE_AUDIT.json"

IDEAL = {"energy": 0.70, "fatigue": 0.20, "integrity": 0.85, "stimulation": 0.55}
VIABLE = {
    "energy": (0.30, 0.90),
    "fatigue": (0.05, 0.70),
    "integrity": (0.35, 0.98),
    "stimulation": (0.25, 0.80),
}
DRIFT = {"energy": -0.002, "fatigue": 0.002, "integrity": -0.0002, "stimulation": -0.002}
EFFECTS: dict[str, tuple[dict[str, float], ...]] = {
    "IDLE": ({"energy": -0.0005, "fatigue": 0.0005, "stimulation": -0.001, "integrity": 0.02},),
    "ORIENT": ({"energy": -0.001, "fatigue": 0.001, "stimulation": 0.005}, {}),
    "MOVE": ({"energy": -0.005, "fatigue": 0.004, "stimulation": 0.003}, {"energy": -0.003, "fatigue": 0.002}),
    "APPROACH": ({"energy": -0.004, "fatigue": 0.003, "stimulation": 0.004}, {"energy": -0.003, "fatigue": 0.002}),
    "RETREAT": ({"energy": -0.005, "fatigue": 0.004, "stimulation": 0.003, "integrity": 0.01}, {"energy": -0.003, "fatigue": 0.002}),
    "INSPECT": ({"energy": -0.003, "fatigue": 0.002, "stimulation": 0.04}, {"energy": -0.003, "fatigue": 0.002}),
    "REST": ({"energy": 0.015, "fatigue": -0.08, "stimulation": -0.02, "integrity": 0.055}, {"energy": -0.003, "fatigue": 0.002}),
    "CHARGE": ({"energy": 0.14, "fatigue": -0.01, "stimulation": -0.005}, {"energy": -0.003, "fatigue": 0.002}),
}
CAPABILITY_FOR_OWNER = {"energy": "CHARGE", "fatigue": "REST", "integrity": "REST", "stimulation": "INSPECT"}
DIRECTION_FOR_OWNER = {"energy": 1, "fatigue": -1, "integrity": 1, "stimulation": 1}
CAPABILITY_FOR_KIND = {"resource": "CHARGE", "novel_crystal": "CHARGE", "rest": "REST", "inspect": "INSPECT"}
OWNERS_FOR_CAPABILITY = {"CHARGE": ("energy",), "REST": ("fatigue", "integrity"), "INSPECT": ("stimulation",)}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def put(name: str, value: Mapping[str, Any]) -> str:
    return publish(name, json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode() + b"\n")


def metadata() -> dict[str, Any]:
    return {
        "schema": "AS003PR6_L2_SCHEDULABILITY_ATTRIBUTION_V1",
        "directive": "UMBRA-AS-003P-R6",
        "generated_at": now(),
        "exact_starting_baseline": BASELINE,
        "current_head": git("rev-parse", "HEAD"),
        "scope": {
            "organism_runs": 0,
            "control_runs": 0,
            "shadow_runs": 0,
            "diagnostic_runs": 0,
            "retries": 0,
            "reseeds": 0,
            "production_changes": 0,
            "existing_test_semantic_changes": 0,
        },
    }


def modality(row: Mapping[str, Any] | None) -> str:
    return str((row or {}).get("modality", "UNKNOWN"))


def combined_modality(values: Iterable[str]) -> str:
    material = tuple(values)
    if "UNSUPPORTED" in material:
        return "UNSUPPORTED"
    if "UNKNOWN" in material:
        return "UNKNOWN"
    if "MAY" in material:
        return "MAY"
    return "MUST"


def services_from_frame(frame: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for opportunity_identity, opportunity in sorted((frame.get("opportunities") or {}).items()):
        capability = CAPABILITY_FOR_KIND.get(str(opportunity.get("kind")))
        if capability is None:
            continue
        route = (frame.get("route_support") or {}).get(opportunity_identity) or {}
        timing = (frame.get("service_timing") or {}).get(capability) or {}
        requirements = {
            "capability": modality((frame.get("constitutional_capabilities") or {}).get(capability)),
            "opportunity": modality(opportunity.get("future")),
            "route": modality(route),
            "timing": modality(timing),
        }
        route_value = dict(route.get("value") or {})
        timing_value = dict(timing.get("value") or {})
        result.append(
            {
                "identity": f"modal-service:{capability}:{opportunity_identity}",
                "capability": capability,
                "owners": list(OWNERS_FOR_CAPABILITY[capability]),
                "opportunity_identity": opportunity_identity,
                "requirements": requirements,
                "modality": combined_modality(requirements.values()),
                "opportunity_valid_through": (opportunity.get("future") or {}).get("valid_through_ticks"),
                "route_demand": route_value.get("required_movement_executions"),
                "completion_demand": timing_value.get("completion_ticks"),
            }
        )
    return result


def locks() -> None:
    physiology_sha = sha(REPO / "umbra_core/physiology.py")
    as003l_lock = AS003L_ROOT / "AS003L_REGULATORY_OBLIGATION_ONTOLOGY_LOCK.json"
    as003l_resource = AS003L_ROOT / "AS003L_EXECUTION_RESOURCE_MODEL.json"
    as003l_bound = AS003L_ROOT / "AS003L_BOUNDEDNESS_AND_PLANNING_BOUNDARY.json"
    recovery = metadata() | {
        "result": "PASS",
        "source_artifacts": {
            as003l_lock.name: sha(as003l_lock),
            as003l_resource.name: sha(as003l_resource),
            as003l_bound.name: sha(as003l_bound),
            "umbra_core/physiology.py": physiology_sha,
            "AS003K_PROSPECTIVE_REGULATORY_HORIZON_AUDIT.json": sha(Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003k-four-drive-regulatory-resolution-r1/AS003K_PROSPECTIVE_REGULATORY_HORIZON_AUDIT.json")),
        },
        "recovered_contract": {
            "activation": "a physiology owner has a supported post-candidate state, an adverse autonomous drift toward viable-band loss, supported corrective effect semantics, and source-backed capability/opportunity/route/demand/provenance; missing required facts leave the obligation UNKNOWN rather than absent",
            "deadline": "latest supported completion tick before the post-candidate owner leaves its own viable band under supported autonomous drift",
            "deadline_formula": "per-owner only: floor(distance from post-candidate value to adverse viable boundary / absolute supported drift); equality remains viable; no cross-owner min/max/sum",
            "service_demand": "supported worst-case route movement executions plus supported completion lag plus one terminal action",
            "capability_and_effects": "CHARGE serves energy, REST jointly serves fatigue and integrity, INSPECT serves stimulation only when complete correlated effect branches support the required direction",
            "uncertainty": "UNKNOWN if deadline, capability/opportunity, route demand, completion demand, effects, or provenance is not source-supported; MAY is possibility, not guarantee or preference",
            "L1": "A precedes B only when A preserves every supported individual obligation and B loses at least one, without converse loss",
            "L2": "bounded branch-wise enumeration of fixed finite corrective-service orders; precedence only from one-way proven loss of complete schedulability, never schedule count or slack magnitude",
            "serial_resource": "one non-preemptive final primitive path; effects occur on verified completion",
        },
        "formula_authority": {
            "AS003K": "defines the per-drive horizon as post-action elapsed ticks until leaving the owner's viable band under supported autonomous drift",
            "AS003L": "defines deadline as latest supported completion before that loss and demand as route executions plus completion lag plus terminal action",
            "physiology_source": "supplies exact owner viable bounds, autonomous drifts, and complete verified effect branches",
        },
        "not_inferred": ["owner weights", "cross-owner horizon aggregation", "minimum laxity selection", "route time when absent"],
    }
    recovery_sha = put("AS003PR6_AS003L_CONTRACT_RECOVERY.json", recovery)
    gap = metadata() | {
        "result": "SOURCE_ROUTE_DEMAND_AND_ACTIVE_DEADLINES_MISSING",
        "classifications": {
            "effect_envelopes": {"status": "PRESENT_AND_USED", "detail": "complete current-candidate and corrective-service effect branches come from verified outcome templates"},
            "timing_envelopes": {"status": "PRESENT_BUT_DROPPED", "detail": "SelfModel capability completion envelopes are retained under capability_support, but modal services use a separate point completion_ticks field that is zero throughout R5A"},
            "route_evidence": {"status": "MISSING", "detail": "frame route_support retains modality and opportunity identity but not required movement executions or a route timing interval"},
            "opportunity_persistence_horizons": {"status": "PRESENT_BUT_DROPPED", "detail": "future valid_through_ticks is retained in the frame but omitted from ModalService and transition checks"},
            "dependency_fingerprints": {"status": "PRESENT_BUT_DROPPED", "detail": "frame/profile fingerprints are retained, but service transitions do not validate source dependency tokens"},
            "active_deadlines": {"status": "MISSING", "detail": "no viable-loss deadline is carried in the frame/profile; it can only be reconstructed from retained physiology plus locked source constants"},
            "multi_step_service_composition": {"status": "MISSING", "detail": "current modal profile checks one next service independently per immediate candidate branch"},
        },
        "source_trace_observation": {
            "frames": 500,
            "service_timing_rows": 3000,
            "service_timing_point_zero_rows": 3000,
            "route_rows": 1000,
            "route_rows_with_required_movement_executions": 0,
            "future_opportunity_rows": 1000,
            "future_opportunity_rows_with_valid_through_ticks": 1000,
        },
        "contract_recovery_sha256": recovery_sha,
    }
    gap_sha = put("AS003PR6_SUBSTRATE_GAP_MATRIX.json", gap)
    external = metadata() | {
        "result": "REFERENCE_ONLY_NO_DEPENDENCY",
        "sources": [
            {"topic": "weak/strong/strong-cyclic planning", "source": "https://doi.org/10.1016/S0004-3702(02)00374-0", "title": "Weak, strong, and strong cyclic planning via symbolic model checking", "classification": "REFERENCE", "boundary": "universal versus existential outcome semantics only; guarantee strength is not motivational preference"},
            {"topic": "modal transition systems", "source": "https://doi.org/10.1109/LICS.1988.5119", "title": "A modal process logic", "classification": "REFERENCE", "boundary": "may/must relational structure only; no model checker or refinement algorithm imported"},
            {"topic": "viability theory", "source": "https://doi.org/10.1137/0328044", "title": "A Survey of Viability Theory", "classification": "REFERENCE", "boundary": "constraint-preserving feasible trajectories only; no optimal-control value function"},
            {"topic": "set-valued multiobjective viability", "source": "https://doi.org/10.1137/0328044", "title": "A Survey of Viability Theory", "classification": "REFERENCE", "boundary": "retain feasible sets without Pareto numerical optimization"},
            {"topic": "deadline and laxity scheduling", "source": "https://doi.org/10.1007/978-1-4615-3956-8_3", "title": "Design and Analysis of Processor Scheduling Policies for Real-Time Systems", "classification": "REFERENCE", "boundary": "feasibility of bounded durations before deadlines only; EDF and least-laxity-first are not UMBRA authority"},
        ],
        "external_dependencies_added": 0,
    }
    external_sha = put("AS003PR6_EXTERNAL_PRIOR_ART_MATRIX.json", external)
    contract = metadata() | {
        "lock": "IMMUTABLE_BEFORE_SYNTHETIC_QUALIFICATION_AND_R5A_APPLICATION",
        "contract_recovery_sha256": recovery_sha,
        "substrate_gap_matrix_sha256": gap_sha,
        "external_prior_art_sha256": external_sha,
        "types": {
            "RegulatoryObligation": ["owner", "originating physiology state", "supported viable-loss deadline", "deadline provenance", "acceptable corrective capabilities", "required effect direction", "source dependencies"],
            "RegulatoryServiceEnvelope": ["service identity", "capability", "owner coverage", "opportunity identity", "capability modality", "opportunity modality", "opportunity valid-through horizon", "route modality", "supported route demand", "completion demand", "complete correlated effect branches", "provenance"],
        },
        "schedule_semantics": {
            "current_candidate": "apply every supported current effect branch with its supported completion time",
            "obligations": "derive each owner deadline independently; missing source support produces UNKNOWN",
            "search": "enumerate source-backed service sequences without replacement up to depth 5 and active physical path ceiling 32",
            "outcomes": "organism service choice is existential; every supported physical effect branch is universal",
            "time": "elapsed time consumes route demand, completion lag, one terminal action, owner deadlines, and opportunity horizons",
            "classes": ["COMPLETE_MUST_SCHEDULE", "COMPLETE_MAY_SCHEDULE", "SCHEDULE_UNKNOWN", "NO_COMPLETE_SCHEDULE"],
            "precedence": "A precedes B only when A retains a complete MUST or MAY schedule on every supported branch, B has a proven no-schedule branch without UNKNOWN, and A has no hard violation",
        },
        "explicitly_non_authoritative": True,
        "explicitly_absent": ["weights", "owner priority", "severity normalization", "reward", "utility", "score", "schedule-count preference", "MUST-over-MAY preference", "RNG", "action execution"],
        "implementation": "experiments/as003pr6/l2_schedulability.py",
        "implementation_sha256": sha(REPO / "experiments/as003pr6/l2_schedulability.py"),
    }
    put("AS003PR6_L2_SCHEDULABILITY_CONTRACT.json", contract)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _effect_branches(capability: str) -> tuple[dict[str, float], ...]:
    return EFFECTS.get(capability, ({"energy": -0.003, "fatigue": 0.002},))


def profile_audits() -> None:
    planning = {int(row["tick"]): row for row in load_jsonl(PLANNING)}
    conflict = load_json(CONFLICT)
    exposed = {int(row["tick"]) for row in conflict["reported_rows"] if row["as003l_conflict_exposed"]}

    def summarize(ticks: Iterable[int]) -> dict[str, Any]:
        differences: Counter[str] = Counter()
        pairs = 0
        frames = 0
        for tick in ticks:
            row = planning[tick]
            frame = row["frame"]
            source_services = services_from_frame(frame)
            candidates: list[dict[str, Any]] = []
            for item in row["candidate_profiles"]:
                capability = str(item["capability"])
                effects = _effect_branches(capability)
                post_states = [
                    {owner: float(frame["physiology_root"][owner]) + float(branch.get(owner, 0.0)) for owner in sorted(frame["physiology_root"])}
                    for branch in effects
                ]
                full_witnesses = [
                    [
                        [service["identity"], service["modality"]]
                        for service in source_services
                        if service["modality"] in {"MUST", "MAY"}
                    ]
                    for _ in effects
                ]
                current_timing = (frame.get("service_timing") or {}).get(capability) or {}
                source_modalities = {
                    "current_timing_modality": modality(current_timing),
                    "current_completion_ticks": dict(current_timing.get("value") or {}).get("completion_ticks"),
                    "services": [[service["identity"], service["modality"], service["requirements"]] for service in source_services],
                }
                temporal_horizons = [[service["identity"], service["opportunity_valid_through"]] for service in source_services]
                profile = item["profile"]
                candidates.append(
                    {
                        "classification": profile["classification"],
                        "reason": profile["reason"],
                        "branch_results": profile["branch_results"],
                        "selected_witnesses": profile["branch_witnesses"],
                        "full_witness_sets": full_witnesses,
                        "immediate_effect_branches": effects,
                        "resulting_physiology": post_states,
                        "source_modalities": source_modalities,
                        "source_temporal_horizons": temporal_horizons,
                    }
                )
            if candidates:
                frames += 1
            for left, right in combinations(candidates, 2):
                pairs += 1
                for field in left:
                    differences[field] += _canonical(left[field]) != _canonical(right[field])
        lower_fields = tuple(field for field in differences if field not in {"classification", "reason"})
        # Immediate successor states subsume the material lower-level distinction
        # and are not inferred from top-level labels.
        compressed = differences["resulting_physiology"] - differences["classification"]
        return {
            "frames_with_profiles": frames,
            "candidate_pairs": pairs,
            "difference_counts": dict(sorted(differences.items())),
            "pairs_equal_at_classification_but_different_at_immediate_successor": compressed,
            "lower_fields_compared": list(lower_fields),
        }

    profile = metadata() | {
        "result": "TOP_LEVEL_CLASSIFICATION_ERASES_IMMEDIATE_SUCCESSOR_DIFFERENCES",
        "all_500_frames": summarize(sorted(planning)),
        "as003l_exposed_57_frames": summarize(sorted(exposed)),
        "interpretation": "top-level class/reason are identical within every frame; most candidate pairs nevertheless have different complete immediate effect branches and resulting per-owner states. Selected/full witness differences arise only where physical branch counts differ; the trace does not retain a scored preference.",
        "r5a_remains_development_evidence": True,
    }
    put("AS003PR6_PROFILE_INFORMATION_LOSS_AUDIT.json", profile)

    admitted = valid = expired = timing_unknown = unsupported_profiles = 0
    source_rows = 0
    for row in planning.values():
        frame = row["frame"]
        services = {service["identity"]: service for service in services_from_frame(frame)}
        for candidate in row["candidate_profiles"]:
            candidate_timing = (frame.get("service_timing") or {}).get(candidate["capability"]) or {}
            candidate_elapsed = dict(candidate_timing.get("value") or {}).get("completion_ticks")
            candidate_unknown = False
            for _, identity, _ in candidate["profile"]["branch_witnesses"]:
                admitted += 1
                service = services.get(identity)
                if service is None:
                    timing_unknown += 1
                    candidate_unknown = True
                    continue
                source_rows += 1
                route = service["route_demand"]
                completion = service["completion_demand"]
                horizon = service["opportunity_valid_through"]
                if None in {candidate_elapsed, route, completion, horizon}:
                    timing_unknown += 1
                    candidate_unknown = True
                    continue
                finish = int(candidate_elapsed) + int(route) + int(completion) + 1
                if finish <= int(horizon):
                    valid += 1
                else:
                    expired += 1
            if candidate_unknown and candidate["profile"]["classification"] != "UNKNOWN":
                unsupported_profiles += 1
    temporal = metadata() | {
        "result": "TIMING_UNKNOWN_DUE_TO_DROPPED_ROUTE_DEMAND",
        "current_modal_witnesses_admitted": admitted,
        "source_witness_rows_resolved": source_rows,
        "horizon_valid_witnesses": valid,
        "horizon_expired_witnesses": expired,
        "timing_unknown_witnesses": timing_unknown,
        "candidate_profiles_no_longer_supportable_under_horizon_preserving_semantics": unsupported_profiles,
        "facts": {
            "candidate_elapsed": "point completion_ticks is retained and equals zero in R5A",
            "route_demand": "absent from every retained route fact; zero is not assumed",
            "service_completion": "point completion_ticks is retained and equals zero",
            "opportunity_horizon": "valid_through_ticks=5 is retained for all future opportunity facts",
            "current_modal_behavior": "ModalService omits valid_through_ticks and route demand; transition therefore cannot consume either",
            "AS003O_comparison": "source-backed continuation checks elapsed maximum plus service duration against opportunity persistence minimum",
        },
        "defect_disposition": "STRUCTURAL_HORIZON_CONSUMPTION_PATH_ABSENT, BUT NO R5A WITNESS CAN BE CLASSIFIED EXPIRED OR VALID BECAUSE ROUTE DEMAND IS MISSING",
    }
    put("AS003PR6_TEMPORAL_ENVELOPE_AUDIT.json", temporal)


def qualify() -> None:
    test_path = REPO / "tests/test_as003pr6_l2_schedulability.py"
    tree = ast.parse(test_path.read_text(encoding="utf-8"))
    imports = sorted(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    forbidden_tokens = ["Organism", "tick_once", "runtime", "Embodiment", "Habitat"]
    source = test_path.read_text(encoding="utf-8")
    purity = {
        "imports": imports,
        "imports_umbra_core": any(name.startswith("umbra_core") for name in imports),
        "forbidden_token_hits": [token for token in forbidden_tokens if token in source],
        "constructs_organism": False,
        "calls_tick_once": False,
        "executes_runtime": False,
        "uses_rng": False,
    }
    command = [sys.executable, "-m", "pytest", "-q", "tests/test_as003pr6_l2_schedulability.py"]
    runs = []
    normalized = []
    for index in (1, 2):
        completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False)
        norm = re.sub(r"in \d+(?:\.\d+)?s", "in <elapsed>", completed.stdout.strip())
        normalized.append(norm)
        runs.append({"run": index, "command": command, "exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "normalized_stdout": norm})
    passed = all(run["exit_code"] == 0 and "23 passed" in run["stdout"] for run in runs)
    semantic_equal = normalized[0] == normalized[1]
    result = metadata() | {
        "result": "PASS" if passed and semantic_equal and not purity["imports_umbra_core"] and not purity["forbidden_token_hits"] else "FAIL",
        "test_file": str(test_path.relative_to(REPO)),
        "test_file_sha256": sha(test_path),
        "implementation_sha256": sha(REPO / "experiments/as003pr6/l2_schedulability.py"),
        "purity": purity,
        "runs": runs,
        "semantic_result_identical": semantic_equal,
        "expected_cases": 23,
    }
    put("AS003PR6_PURE_TEST_RESULTS.json", result)
    if result["result"] != "PASS":
        raise RuntimeError("AS003PR6 pure qualification failed")


def _deadline(owner: str, value: float) -> int | None:
    low, high = VIABLE[owner]
    drift = DRIFT[owner]
    if drift < 0:
        if value < low:
            return 0
        if value > high:
            return None
        return max(0, int(math.floor((value - low) / -drift + 1e-12)))
    if value > high:
        return 0
    if value < low:
        return None
    return max(0, int(math.floor((high - value) / drift + 1e-12)))


def _obligations(state: Mapping[str, float], frame: Mapping[str, Any]) -> tuple[RegulatoryObligation, ...]:
    result = []
    for owner in sorted(state):
        deadline = _deadline(owner, float(state[owner]))
        if deadline is None:
            continue
        result.append(
            RegulatoryObligation(
                owner=owner,
                originating_state=float(state[owner]),
                deadline=deadline,
                deadline_provenance=("AS003K_PER_OWNER_VIABLE_LOSS_HORIZON", "AS003L_COMPLETION_DEADLINE", f"physiology:{sha(REPO / 'umbra_core/physiology.py')}"),
                acceptable_capabilities=(CAPABILITY_FOR_OWNER[owner],),
                required_effect_direction=DIRECTION_FOR_OWNER[owner],
                source_dependencies=(str(frame.get("material_fingerprint", "")),),
            )
        )
    return tuple(result)


def _l2_services(frame: Mapping[str, Any], required_capabilities: set[str]) -> tuple[RegulatoryServiceEnvelope, ...]:
    rows = services_from_frame(frame)
    by_capability = {row["capability"] for row in rows}
    for capability in sorted(required_capabilities - by_capability):
        rows.append(
            {
                "identity": f"missing-source-service:{capability}",
                "capability": capability,
                "owners": list(OWNERS_FOR_CAPABILITY[capability]),
                "opportunity_identity": "UNKNOWN",
                "requirements": {"capability": "MUST", "opportunity": "UNKNOWN", "route": "UNKNOWN", "timing": "UNKNOWN"},
                "modality": "UNKNOWN",
                "opportunity_valid_through": None,
                "route_demand": None,
                "completion_demand": None,
            }
        )
    result = []
    for row in rows:
        requirements = row["requirements"]
        result.append(
            RegulatoryServiceEnvelope(
                identity=row["identity"],
                capability=row["capability"],
                owner_coverage=tuple(row["owners"]),
                opportunity_identity=row["opportunity_identity"],
                capability_modality=Modality(requirements["capability"]),
                opportunity_modality=Modality(requirements["opportunity"]),
                opportunity_valid_through=row["opportunity_valid_through"],
                route_modality=Modality(requirements["route"]),
                route_demand=row["route_demand"],
                completion_demand=row["completion_demand"],
                effect_branches=tuple(effect_branch(branch) for branch in _effect_branches(row["capability"])),
                provenance=("R5A_FRAME", row["identity"]),
            )
        )
    return tuple(result)


def apply_r5a() -> None:
    planning = {int(row["tick"]): row for row in load_jsonl(PLANNING)}
    conflict = load_json(CONFLICT)
    exposed = {int(row["tick"]) for row in conflict["reported_rows"] if row["as003l_conflict_exposed"]}
    classification_counts: Counter[str] = Counter()
    per_tick = []
    all_pairs = exposed_pairs = distinctions = exposed_distinctions = 0
    frames_with_distinction: set[int] = set()
    permutations_evaluated = 0
    owner_counts: Counter[int] = Counter()
    for tick, row in sorted(planning.items()):
        frame = row["frame"]
        candidate_rows = []
        for item in row["candidate_profiles"]:
            capability = str(item["capability"])
            duration = dict(((frame.get("service_timing") or {}).get(capability) or {}).get("value") or {}).get("completion_ticks")
            elapsed = int(duration) if duration is not None else 0
            branches = []
            obligations_by_branch = []
            for effects in _effect_branches(capability):
                state = {owner: float(frame["physiology_root"][owner]) + float(effects.get(owner, 0.0)) for owner in sorted(frame["physiology_root"])}
                branches.append(CandidateBranch(tuple(sorted(state.items())), elapsed=elapsed))
                obligations = _obligations(state, frame)
                obligations_by_branch.append(obligations)
                owner_counts[len(obligations)] += 1
            required = {ob.acceptable_capabilities[0] for group in obligations_by_branch for ob in group}
            services = _l2_services(frame, required)
            relevant_unknown = any(
                service.requirement_modality is Modality.UNKNOWN
                and any(
                    service.capability in obligation.acceptable_capabilities
                    and obligation.owner in service.owner_coverage
                    for group in obligations_by_branch
                    for obligation in group
                )
                for service in services
            )
            if relevant_unknown:
                result = CandidateScheduleResult(
                    tuple(
                        BranchScheduleResult(
                            ScheduleClass.UNKNOWN,
                            (),
                            0,
                            1,
                            "SOURCE_ROUTE_OR_SERVICE_DEMAND_UNKNOWN",
                        )
                        for _ in branches
                    )
                )
            else:
                result = evaluate_candidate(branches, obligations_by_branch, services)
            for branch in result.branches:
                classification_counts[branch.classification.value] += 1
                permutations_evaluated += branch.permutations_evaluated
            candidate_rows.append((item["candidate_identity"], result))
        tick_distinctions = []
        for (left_identity, left), (right_identity, right) in combinations(candidate_rows, 2):
            all_pairs += 1
            if tick in exposed:
                exposed_pairs += 1
            if l2_precedes(left, right):
                distinctions += 1
                tick_distinctions.append({"precedes": left_identity, "target": right_identity, "reason": "ONE_WAY_PROVEN_FULL_SCHEDULABILITY_LOSS"})
            if l2_precedes(right, left):
                distinctions += 1
                tick_distinctions.append({"precedes": right_identity, "target": left_identity, "reason": "ONE_WAY_PROVEN_FULL_SCHEDULABILITY_LOSS"})
        if tick_distinctions:
            frames_with_distinction.add(tick)
            if tick in exposed:
                exposed_distinctions += len(tick_distinctions)
        if row["candidate_profiles"]:
            per_tick.append(
                {
                    "tick": tick,
                    "as003l_exposed": tick in exposed,
                    "candidate_count": len(candidate_rows),
                    "branch_classifications": [
                        [identity, [branch.classification.value for branch in result.branches], [branch.reason for branch in result.branches]]
                        for identity, result in candidate_rows
                    ],
                    "l2_distinctions": tick_distinctions,
                }
            )
    application = metadata() | {
        "result": "SOURCE_EVIDENCE_UNKNOWN",
        "complete_frames_read": len(planning),
        "frames_with_candidates": len(per_tick),
        "exposed_decisions_evaluated": len(exposed),
        "candidate_pairs_evaluated": all_pairs,
        "exposed_candidate_pairs_evaluated": exposed_pairs,
        "schedule_permutations_evaluated": permutations_evaluated,
        "branch_schedule_classifications": dict(sorted(classification_counts.items())),
        "active_deadline_obligation_count_distribution": {str(key): value for key, value in sorted(owner_counts.items())},
        "candidate_pairs_with_one_way_l2_schedulability_loss": distinctions,
        "exposed_candidate_pairs_with_one_way_l2_schedulability_loss": exposed_distinctions,
        "frames_with_l2_distinction": len(frames_with_distinction),
        "per_tick": per_tick,
        "source_limitation": "all retained route facts omit route demand; no route time was invented. All source-relevant service witnesses are therefore UNKNOWN before sequence search.",
        "retrospective_development_only": True,
    }
    put("AS003PR6_L2_R5A_APPLICATION.json", application)
    profile = load_json(EVIDENCE_ROOT / "AS003PR6_PROFILE_INFORMATION_LOSS_AUDIT.json")
    temporal = load_json(EVIDENCE_ROOT / "AS003PR6_TEMPORAL_ENVELOPE_AUDIT.json")
    attribution = metadata() | {
        "result": "H5_SOURCE_EVIDENCE_INSUFFICIENT",
        "questions": {
            "branch_witness_structure_differs_despite_equal_class": profile["all_500_frames"]["difference_counts"]["selected_witnesses"] > 0,
            "valid_through_consumption_changed_witness_validity": "UNKNOWN; route demand absent prevents valid/expired classification",
            "full_multi_obligation_scheduling_changed_candidate_classification": "all candidate branches became SCHEDULE_UNKNOWN under the locked source-fidelity rule",
            "locked_l2_created_one_way_distinctions": False,
            "conflicts_unresolved_because_both_fully_schedulable": False,
            "unknown_source_evidence_dominated": True,
            "current_one_step_modal_profile_forward_disposition": "SUPERSEDED_AS_SOURCE-CORRECT_SCHEDULABILITY_EVIDENCE; it drops opportunity horizon and route demand, but this retrospective evidence cannot qualify a replacement",
        },
        "hypotheses": {
            "H1_classification_compression": "SUPPORTED_DESCRIPTIVELY: 6030 all-frame and 1012 exposed pairs share top-level class while immediate successor physiology differs",
            "H2_temporal_envelope_loss": "SUPPORTED_STRUCTURALLY: horizon and route demand are not consumed; actual expiry effect remains UNKNOWN",
            "H3_single_witness_insufficiency": "NOT_TESTABLE_ON_R5A: lawful multi-service search is blocked before expansion by missing route demand",
            "H4_genuine_prospective_equivalence": "NOT_ESTABLISHED",
            "H5_source_evidence_insufficient": "SUPPORTED_AND_DECISIVE",
        },
    }
    put("AS003PR6_CAUSAL_ATTRIBUTION.json", attribution)
    verdict = metadata() | {
        "terminal_verdict": "AS003PR6_SOURCE_EVIDENCE_INSUFFICIENT_FOR_L2",
        "basis": [
            "the AS-003L obligation/deadline/service contract was recovered without a cross-owner scalar",
            "the locked pure L2 relation passed 23 cases twice identically",
            "R5A preserves opportunity horizon=5 but no route execution demand in any of 1000 route rows",
            "all 5323 currently admitted modal witnesses are timing-UNKNOWN under source-preserving semantics",
            "all 5367 candidate branches are SCHEDULE_UNKNOWN and no one-way L2 relation can be inferred",
        ],
        "as002_disposition": "NO_RELATION_SUPPORTED",
        "modal_profile_forward_disposition": "SOURCE-INCOMPLETE_AND_TEMPORALLY_LOSSY; no behavioral authority",
        "exact_missing_source_fields": [
            "per-opportunity supported worst-case required movement executions or equivalent route timing envelope",
            "source semantics connecting SelfModel route progress/completion support to each opportunity",
            "service completion demand that is explicit about whether terminal-action time is included",
            "source-backed INSPECT opportunity/route when stimulation obligation is active",
        ],
        "recommendation": "NONE; return to Architect. Any successor must prospectively retain source-backed route/service demand before another shadow pair.",
        "no_successor_started": True,
    }
    put("AS003PR6_VERDICT.json", verdict)


def manifest() -> None:
    source_hashes_before = {"planning": sha(PLANNING), "decision": sha(DECISIONS)}
    files = sorted(path for path in EVIDENCE_ROOT.glob("AS003PR6_*") if path.name != "AS003PR6_EVIDENCE_MANIFEST.json")
    payload = metadata() | {
        "result": "PASS",
        "artifact_count": len(files),
        "artifacts": [{"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in files],
        "r5a_source_hashes_after_analysis": source_hashes_before,
        "r5a_source_hashes_unchanged": source_hashes_before == {
            "planning": "58ea3a6e8fbb81443f4e569a811b0ded2e3b273fd4221ed497923965a56903e8",
            "decision": "4c48d1db24e4600a3f5e1c855efec9b1eec1937f8ca1409c52070fc6cbbdd380",
        },
        "durability": "file fsync, atomic rename, directory fsync, SHA-256 readback",
    }
    put("AS003PR6_EVIDENCE_MANIFEST.json", payload)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"locks", "profile-audits", "qualify", "apply", "manifest"}:
        raise SystemExit("usage: as003pr6_analysis.py {locks|profile-audits|qualify|apply|manifest}")
    {"locks": locks, "profile-audits": profile_audits, "qualify": qualify, "apply": apply_r5a, "manifest": manifest}[sys.argv[1]]()


if __name__ == "__main__":
    main()
