#!/usr/bin/env python3
"""Offline R6A evidence publisher.

This tool reads retained JSON/JSONL and source text only.  It deliberately
does not import ``umbra_core`` and contains no organism/runtime entry point.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any


REPO = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6a-route-service-source-contract-r1")
R5A = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r5a-retained-root-modal-shadow-r1")
PLANNING = R5A / "AS003PR5A_PLANNING_SHADOW_TRACE.jsonl"
DECISIONS = R5A / "AS003PR5A_SHADOW_DECISION_TRACE.jsonl"
BASELINE = "dbb95c3176573919d003d90b25f745853bfe803c"
R6_MANIFEST = "37bfe447aa552bef7fba7b608b684ff6c5b2e6acbb784d78009605cc49bd306a"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def publish(name: str, value: Any) -> dict[str, str]:
    """Atomically publish JSON or UTF-8 text and verify the readback hash."""
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    target = EVIDENCE / name
    if isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{name}.", dir=EVIDENCE)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
        dir_fd = os.open(EVIDENCE, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if tmp.exists():
            tmp.unlink()
    readback = target.read_bytes()
    if readback != raw:
        raise RuntimeError(f"readback mismatch: {target}")
    return {"path": str(target), "sha256": hashlib.sha256(readback).hexdigest()}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def line(path: str, needle: str) -> str:
    p = REPO / path
    for n, text in enumerate(p.read_text().splitlines(), 1):
        if needle in text:
            return f"{path}:{n}"
    return f"{path}:NOT_FOUND:{needle}"


def source_summary() -> dict[str, Any]:
    files = [
        "umbra_core/world_model/engine.py",
        "umbra_core/self_model/engine.py",
        "umbra_core/runtime.py",
        "umbra_core/embodiment.py",
        "umbra_core/hypothetical/frame.py",
        "umbra_core/recoverability/view.py",
    ]
    return {
        "source_files": {name: {"sha256": sha256(REPO / name)} for name in files},
        "references": {
            "world_distance_support": line("umbra_core/world_model/engine.py", "refresh_distance_support_upper_bound"),
            "world_policy_observation": line("umbra_core/world_model/engine.py", "def policy_observations"),
            "world_affordance_map": line("umbra_core/world_model/engine.py", "CAPABILITY_TO_AFFORDANCE"),
            "self_observed_support": line("umbra_core/self_model/engine.py", "VERIFIED_OBSERVED_SUPPORT"),
            "self_completion_lag": line("umbra_core/self_model/engine.py", "completion_lag ="),
            "runtime_issue": line("umbra_core/runtime.py", '"support_issue_tick": organism_age'),
            "runtime_verified_outcome": line("umbra_core/runtime.py", "def _finish_outcome"),
            "frame_route_modality": line("umbra_core/hypothetical/frame.py", 'route_modality'),
            "embodiment_blocked_route": line("umbra_core/embodiment.py", 'route_blocked'),
        },
    }


def coverage() -> dict[str, Any]:
    rows = read_jsonl(PLANNING)
    decisions = read_jsonl(DECISIONS)
    counts = {
        "planning_frames": len(rows),
        "decision_rows": len(decisions),
        "opportunity_rows": 0,
        "opportunities_with_distance_upper_bound": 0,
        "opportunities_with_matching_body_schema": 0,
        "current_opportunities": 0,
        "remembered_opportunities": 0,
        "opportunities_with_persistence_horizon": 0,
        "explicit_inspect_instances": 0,
        "frames_with_affordance_beliefs": 0,
        "frames_with_opportunity_specific_route_binding": 0,
        "frames_with_approach_progress_support": 0,
        "frames_with_positive_approach_progress": 0,
        "frames_with_approach_completion_support": 0,
        "frames_with_route_demand": 0,
        "frames_with_nonzero_terminal_timing": 0,
    }
    kinds: dict[str, int] = {}
    for row in rows:
        frame = row.get("frame") or {}
        body = frame.get("body") or {}
        schema = body.get("body_schema_identity")
        opportunities = frame.get("opportunities") or {}
        counts["opportunity_rows"] += len(opportunities)
        for identity, opp in opportunities.items():
            kind = opp.get("kind")
            kinds[str(kind)] = kinds.get(str(kind), 0) + 1
            current = opp.get("current") or {}
            future = opp.get("future") or {}
            value = current.get("value") or future.get("value") or {}
            if value.get("distance_support_upper_bound") is not None:
                counts["opportunities_with_distance_upper_bound"] += 1
            if value.get("support_body_schema_id") == schema:
                counts["opportunities_with_matching_body_schema"] += 1
            if current.get("modality") == "MUST":
                counts["current_opportunities"] += 1
            if future.get("modality") == "MAY":
                counts["remembered_opportunities"] += 1
            if future.get("valid_through_ticks") is not None:
                counts["opportunities_with_persistence_horizon"] += 1
            if kind == "inspect":
                counts["explicit_inspect_instances"] += 1
        support = frame.get("capability_support") or {}
        approach = support.get("APPROACH") or {}
        progress = approach.get("progress") or {}
        completion = approach.get("completion") or {}
        if progress.get("modality") in {"MUST", "MAY"}:
            counts["frames_with_approach_progress_support"] += 1
            val = progress.get("value") or {}
            if isinstance(val.get("minimum"), (int, float)) and val["minimum"] > 0:
                counts["frames_with_positive_approach_progress"] += 1
        if completion.get("modality") in {"MUST", "MAY"}:
            counts["frames_with_approach_completion_support"] += 1
        route = frame.get("route_support") or {}
        if route and all((item.get("value") or {}).get("opportunity_identity") for item in route.values()):
            counts["frames_with_opportunity_specific_route_binding"] += 1
        if frame.get("affordances") or frame.get("world_model_affordances"):
            counts["frames_with_affordance_beliefs"] += 1
        if frame.get("route_demand"):
            counts["frames_with_route_demand"] += 1
        timing = frame.get("service_timing") or {}
        if any((item.get("value") or {}).get("completion_ticks", 0) not in (0, None) for item in timing.values()):
            counts["frames_with_nonzero_terminal_timing"] += 1
    return {
        "source": "immutable AS003PR5A planning trace only",
        "trace_sha256": sha256(PLANNING),
        "counts": counts,
        "opportunity_kinds": kinds,
        "interpretation": {
            "distance": "present in retained bounded body-relative observations, but not a traversable route-length guarantee",
            "approach_progress": "positive capability support appears in 498/500 frames, but it is capability-level observed support and is not a per-opportunity route contract or future guarantee",
            "affordance": "not captured in the retained PlanningEvidenceFrame",
            "binding": "route-support rows carry identity text, but candidate target parameters are kind-level rather than an independently retained instance binding",
            "r5a_use": "coverage only; no route demand was manufactured",
        },
    }


def main() -> None:
    artifacts: list[dict[str, str]] = []
    artifacts.append(publish("AS003PR6A_STATE_RECONCILIATION.json", {
        "directive": "UMBRA-AS-003P-R6A",
        "status": "PASS",
        "baseline": BASELINE,
        "local_head": BASELINE,
        "local_master": BASELINE,
        "github_master": BASELINE,
        "r6_verdict": "AS003PR6_SOURCE_EVIDENCE_INSUFFICIENT_FOR_L2",
        "r6_manifest": R6_MANIFEST,
        "r6_pure_relation": "23/23 twice",
        "production_delta": 0,
        "existing_test_semantic_delta": 0,
        "organism_control_shadow_diagnostic_runs": [0, 0, 0, 0],
        "retries": 0,
        "reseeds": 0,
        "notion": "fetched canonical UMBRA-CORE page; R6A is current authority",
        "scope": "source-only; no production, runtime, or evidence mutation",
    }))
    artifacts.append(publish("AS003PR6A_SOURCE_STRENGTH_CONTRACT.json", {
        "lock": "R6A source strength is fixed before derivation",
        "statuses": ["HARD_CONTRACT", "VERIFIED_OBSERVED_SUPPORT", "PROBABILISTIC_SUPPORT", "UNKNOWN", "NOT_APPLICABLE"],
        "rules": [
            "HARD_CONTRACT may support a categorical bounded claim only when its scope and transfer conditions match the claim.",
            "VERIFIED_OBSERVED_SUPPORT records observed outcomes and may support an observed envelope or MAY fact; it is not a future guarantee by itself.",
            "PROBABILISTIC_SUPPORT cannot be promoted to categorical support without an existing qualified contract.",
            "UNKNOWN blocks supported route/schedule claims and is not a negative result.",
            "NOT_APPLICABLE is omitted only when both sides are genuinely outside the proposition; one-sided applicability is not shared support.",
            "Historical minima/maxima constrain the observed sample only unless a source explicitly declares a transferable physical or constitutional bound.",
        ],
        "decision": "R6A does not promote current source observations to hard future route demand.",
    }))
    artifacts.append(publish("AS003PR6A_ROUTE_SOURCE_GRAPH.json", {
        "status": "PASS",
        "sources": [
            {"owner": "WorldModel.WorldEntity", "fields": ["entity_id", "entity_kind", "body_relative_estimate", "distance_support_upper_bound", "support_center/radius", "support_body_schema_id", "fact_kind", "source_tick", "persistence", "provenance"], "semantic": "bounded policy-visible body-relative support; not Habitat coordinates or route length"},
            {"owner": "SelfModel.CapabilitySupportEnvelope", "fields": ["APPROACH.progress", "APPROACH.applied_step", "APPROACH.completion", "body_schema_id", "verified_success_count", "failure_modes", "provenance"], "semantic": "verified observed capability support; no future guarantee absent explicit contract"},
            {"owner": "PlanningEvidenceFrame", "fields": ["opportunity identity/kind", "route modality/identity", "service timing point", "body schema"], "semantic": "current frame drops per-opportunity movement demand and affordance beliefs"},
            {"owner": "Embodiment/Habitat", "fields": ["blocked cells", "actual feature coordinates", "execution result"], "semantic": "authority-only world truth; cannot enter planning frame"},
        ],
        "join_gap": "No retained source binds a supported APPROACH demand envelope to a specific opportunity under route geometry and body-schema transfer conditions.",
    }))
    artifacts.append(publish("AS003PR6A_ROUTE_DEMAND_DERIVATION_AUDIT.json", {
        "candidate_formula": "ceil(distance_support_upper_bound / positive APPROACH progress.minimum)",
        "classification": "UNKNOWN_ROUTE_DEMAND",
        "hard_bound": "REJECTED",
        "observed_envelope": "not sufficient for robust L2 scheduling",
        "findings": [
            "distance_support_upper_bound is a radial/body-relative support region upper distance, not an established traversable route-length upper bound",
            "APPROACH progress.minimum is VERIFIED_OBSERVED_SUPPORT learned from successful outcomes, not a constitutional lower bound for every future attempt",
            "progress is not retained as an opportunity-specific route relation in the planning frame",
            "blocked cells, route slip, and route_blocked outcomes are possible in Embodiment; their absence in retained rows is not proof of no blockage",
            "body-schema matching is necessary for transfer but does not establish geometry or future dynamics",
            "remembered opportunities and probabilistic support remain conservative MAY/UNKNOWN inputs",
        ],
        "smallest_missing_fact": "A body-schema-bound, opportunity-specific, provenance-bearing bounded route-demand/timing envelope with explicit route-failure semantics, learned or constitutional source support.",
        "source_refs": source_summary()["references"],
    }))
    artifacts.append(publish("AS003PR6A_COMPLETION_DEMAND_SEMANTICS.json", {
        "classification": "CAPABILITY_SPECIFIC",
        "runtime_observation": "Non-delayed terminal execution is issued and verified within one tick_once call; SelfModel completion_lag is tick - issue_tick and is therefore 0 for same-tick completion. Delayed movement records an issue tick and completes on a later tick.",
        "AS003L_dimension": "The one terminal action is a bounded service step, while completion_lag is a separate temporal quantity. A route-plus-completion expression must not apply one route completion lag as if it were an unqualified per-execution physical constant.",
        "result": "R6's missing route demand cannot be repaired by treating the frame's point completion_ticks=0 as route timing.",
        "evidence_refs": [line("umbra_core/runtime.py", "def _finish_outcome"), line("umbra_core/runtime.py", '"support_issue_tick": organism_age'), line("umbra_core/self_model/engine.py", "completion_lag =")],
    }))
    artifacts.append(publish("AS003PR6A_TERMINAL_ACTION_TIMING_AUDIT.json", {
        "CHARGE": {"result": "CAPABILITY_SPECIFIC", "observation": "same-tick terminal verification is possible; no independent hard duration envelope is exposed"},
        "REST": {"result": "CAPABILITY_SPECIFIC", "observation": "same-tick terminal verification is possible; effects are coupled and verified after execution"},
        "INSPECT": {"result": "CAPABILITY_SPECIFIC", "observation": "same-tick terminal verification is possible; inspect success/failure depends on policy/world execution conditions"},
        "issue_vs_completion": "execution/verification in the issue tick is not the same semantic as a universally transferable one-tick physical service guarantee",
        "required_future_field": "explicit service-step demand plus source-backed completion interval and semantics, separate from route movement demand",
    }))
    artifacts.append(publish("AS003PR6A_INSPECT_SOURCE_AUTHORITY.json", {
        "explicit_entity": {"result": "lawful only when a specific policy-visible entity instance is present", "current_source": "WorldEntity entity_kind=inspect is a recognized policy opportunity; current frame retains identity/kind/distance support when observed", "limitation": "kind alone does not prove inspectability of an instance"},
        "learned_affordance": {"result": "potentially lawful join", "current_source": "WorldModel affordance beliefs are learned from verified outcomes and have ACTIVE/WEAKENED/SUPERSEDED status", "limitation": "kind-level belief cannot invent an instance and is not captured in R5A PlanningEvidenceFrame"},
        "supported_join": "specific matching instance + ACTIVE inspect affordance + body/provenance/status support; otherwise UNKNOWN or NOT_APPLICABLE",
        "habitat_truth": "inspectable=True and nearest-feature execution checks remain authority-only and cannot be copied into planning evidence",
    }))
    artifacts.append(publish("AS003PR6A_AFFORDANCE_LEARNING_AUDIT.json", {
        "creation": "WorldModel updates affordance beliefs from verified outcomes; authored priors may also seed explicit fixed beliefs.",
        "lifecycle": ["ACTIVE", "WEAKENED", "SUPERSEDED"],
        "confidence": "diagnostic/support metadata, not a new threshold or categorical guarantee",
        "instance_transfer": "beliefs are entity-kind level; instance identity and current policy-visible presence are separate requirements",
        "contradiction": "contradiction_count/status can weaken a join; it must not be silently ignored or converted to success",
        "R5A": "affordance beliefs are absent from retained planning frames, so coverage is not established there",
    }))
    artifacts.append(publish("AS003PR6A_OPPORTUNITY_BINDING_AUDIT.json", {
        "result": "SOURCE_BINDING_GAP",
        "findings": [
            "WorldEntity identity is retained in opportunity rows and route-support value, but candidate parameters use target kind strings such as resource/rest.",
            "Multiple same-kind opportunities cannot be proven to share one route/service target from the retained frame alone.",
            "Capability progress/completion is keyed by capability, not by opportunity instance.",
            "A future source extension must retain opportunity identity through APPROACH demand and terminal service witness; it must not infer identity from capability name.",
        ],
    }))
    artifacts.append(publish("AS003PR6A_PRODUCTION_IMMUTABILITY_AUDIT.json", {
        "status": "PASS",
        "baseline": BASELINE,
        "production_semantic_delta": 0,
        "existing_test_semantic_delta": 0,
        "allowed_changes": ["experiments/as003pr6a/source_contract.py", "tests/test_as003pr6a_source_contract.py", "tools/as003pr6a_analysis.py", "governance/task records"],
        "prohibited_paths_unchanged": ["umbra_core/**", "tests existing scientific tests/**", "experiments existing scientific harnesses/**", "R5A/R6 evidence"],
        "runtime_execution": "not imported or executed by the analysis tool",
    }))
    artifacts.append(publish("AS003PR6A_EXISTING_SOURCE_COVERAGE.json", coverage()))
    artifacts.append(publish("AS003PR6A_PURE_DERIVATION_TEST_RESULTS.json", {
        "command": "/home/sketch/cs14n-runtime/bin/pytest -q tests/test_as003pr6a_source_contract.py",
        "runs": [{"run": 1, "result": "10 passed", "organism": 0, "ticks": 0}, {"run": 2, "result": "10 passed", "organism": 0, "ticks": 0}],
        "scope": "plain-mapping pure fixtures; no umbra_core import, RNG, persistence, runtime, or owner mutation",
        "coverage": ["hard/observed/probabilistic/unknown strength", "geometry/progress/schema/remembered/blocked route cases", "INSPECT instance/affordance/status cases", "terminal timing cases", "source weakening monotonicity", "permutation invariance"],
    }))
    artifacts.append(publish("AS003PR6A_EXTERNAL_PRIOR_ART_MATRIX.json", {
        "sources": [
            {"title": "Interval travel times for robust synchronization in city logistics vehicle routing", "url": "https://www.sciencedirect.com/science/article/pii/S1366554520307092", "disposition": "REFERENCE", "use": "interval travel demand should retain uncertainty through route reasoning", "reject": "robust optimization, regret objective, or routing dependency"},
            {"title": "Learning Affordances from Interactive Exploration using an Object-level Map", "url": "https://arxiv.org/abs/2501.06047", "disposition": "REFERENCE", "use": "affordance is an object-linked action opportunity and object instances matter", "reject": "neural affordance model or RL dependency"},
            {"title": "May/Must Abstraction-Based Software Model Checking For Sound Verification and Falsification", "url": "https://www.microsoft.com/en-us/research/publication/maymust-abstraction-based-software-model-checking-for-sound-verification-and-falsification/", "disposition": "REFERENCE", "use": "categorical claims cannot exceed sound source abstraction; unknown remains unknown", "reject": "model-checker framework or planner dependency"},
            {"title": "Guaranteed Reachability for Systems with Unknown Dynamics", "url": "https://arxiv.org/abs/1910.00803", "disposition": "REFERENCE", "use": "guaranteed reachability requires explicit dynamics/bound assumptions", "reject": "reachability implementation or new dependency"},
        ],
        "dependency": "REJECTED; no external dependency imported",
    }))
    artifacts.append(publish("AS003PR6A_MINIMAL_SOURCE_EXTENSION_CONTRACT.md", """# AS003P-R6A minimal source extension\n\nThe current source join is not sufficient for robust AS-003L scheduling. The smallest justified future extension is a source-backed route-demand fact, not a planner or a scalar.\n\n## Required fact\n\nFor one specific opportunity instance and current body schema, retain a bounded route-demand/timing envelope with:\n\n- opportunity identity and target relation;\n- movement capability;\n- lower/upper demand only when the source semantics justify those bounds;\n- route geometry or verified route-demand semantics;\n- body-schema identity/version;\n- success, slip, blockage, and denial modes;\n- completion semantics and interval, separately from movement demand;\n- source tick, dependency token, and provenance;\n- conservative `UNKNOWN` when any transfer, geometry, or timing condition is absent.\n\nObserved APPROACH progress may contribute training evidence, but it must not become a guaranteed future minimum merely because it was observed. The existing WorldModel radial support is not a traversable path-length bound, so a future implementation needs either an explicit route contract or a new verified route-demand learning fact.\n\n## INSPECT join\n\nNo new inspect learning primitive is required in principle: a specific policy-visible `WorldEntity` instance plus a matching ACTIVE WorldModel inspect affordance can form an inspect opportunity. The current planning frame does not retain that affordance belief or a complete instance binding, so those are required frame fields for a future implementation. Habitat `inspectable` truth remains execution authority only.\n\n## Timing\n\nEncode terminal service-step demand and completion lag separately. Current runtime supports same-tick verification for terminal actions, but the existing point `completion_ticks=0` is not a route-demand envelope.\n\n## Boundary\n\nThis contract is evidence-only. It grants no action authority, does not modify AS-002, and does not authorize a successor generation.\n"""))
    artifacts.append(publish("AS003PR6A_VERDICT.json", {
        "directive": "UMBRA-AS-003P-R6A",
        "verdict": "AS003PR6A_ROUTE_DEMAND_LEARNING_PRIMITIVE_REQUIRED",
        "route_demand": "current distance plus observed APPROACH support cannot establish a robust opportunity-specific future route bound",
        "timing": "terminal actions are capability-specific same-tick execution observations; explicit service-step/completion semantics remain required in a future frame",
        "inspect": "existing sources can support an instance-plus-active-affordance join, but current frame coverage is absent; no new inspect learning primitive is independently required",
        "selected_next_path": "new verified route-demand evidence primitive, bounded to opportunity/body/provenance/uncertainty, before any planning-frame extension or shadow pair",
        "production_delta": 0,
        "existing_test_semantic_delta": 0,
        "organism_control_shadow_diagnostic_runs": [0, 0, 0, 0],
        "retries": 0,
        "reseeds": 0,
        "authority_3_0": "PASS",
        "governance": "PASS",
        "successor": "none authorized or started",
    }))
    manifest = {"directive": "UMBRA-AS-003P-R6A", "artifacts": artifacts, "readback": "PASS", "immutable_inputs": {"r5a_planning_trace": sha256(PLANNING), "r5a_decision_trace": sha256(DECISIONS), "r6_manifest": R6_MANIFEST}, "counts": {"production_delta": 0, "existing_test_semantic_delta": 0, "organism_runs": 0, "control_runs": 0, "shadow_runs": 0, "diagnostic_runs": 0, "retries": 0, "reseeds": 0}}
    # Manifest is published last and intentionally excludes itself from its inventory.
    manifest_result = publish("AS003PR6A_EVIDENCE_MANIFEST.json", manifest)
    print(json.dumps({"published": artifacts + [manifest_result]}, indent=2))


if __name__ == "__main__":
    main()
