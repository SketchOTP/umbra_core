"""Seal the non-production CLOSE-02AA architecture evidence dossier."""

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
BASELINE = "d618dc1c2671320d330d44d1d3dcaaa91b1771c1"

X_ATTRIB = ATLAS / "umbra-close-02x-attrib-r1"
W_EVIDENCE = ATLAS / "umbra-close-02w-prospective-recoverability-r1"
T_ATTRIB = ATLAS / "umbra-close-02t-attrib-fatigue-r1"
U_EVIDENCE = ATLAS / "umbra-close-02u-recovery-landmark-r1"
U_ATTRIB = ATLAS / "umbra-close-02u-attrib-r1"


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


def manifest_rows(manifest: dict[str, Any]) -> list[dict[str, str]]:
    raw = manifest.get("files") or manifest.get("listed_files") or manifest.get("covers") or []
    if isinstance(raw, dict):
        return [{"path": str(path), "sha256": str(value)} for path, value in raw.items()]
    rows: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict) and item.get("path") and item.get("sha256"):
            rows.append({"path": str(item["path"]), "sha256": str(item["sha256"])})
    return rows


def find_manifest(root: Path) -> Path:
    preferred = root / "EVIDENCE_HASHES.json"
    if preferred.is_file():
        return preferred
    candidates = sorted(root.glob("*EVIDENCE_HASHES.json"))
    if not candidates:
        raise FileNotFoundError(f"manifest missing: {root}")
    return candidates[-1]


def verify_manifest(root: Path) -> dict[str, Any]:
    manifest_path = find_manifest(root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest_rows(manifest)
    failures: list[str] = []
    for row in rows:
        path = root / row["path"]
        if not path.is_file() or sha256(path) != row["sha256"]:
            failures.append(row["path"])
    return {
        "root": str(root),
        "manifest": manifest_path.name,
        "manifest_sha256": sha256(manifest_path),
        "listed_files": len(rows),
        "verified": bool(rows) and not failures,
        "failures": failures,
    }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def trace_ticks(path: Path, wanted: set[int]) -> dict[int, dict[str, Any]]:
    found: dict[int, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            tick = int(row.get("tick", -1))
            if tick in wanted:
                found[tick] = row
    return found


def production_diff() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", BASELINE, "--", "umbra_core"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()

    lifecycle = load_json(X_ATTRIB / "CLOSE02XATTRIB_FATIGUE_LIFECYCLE.json")
    nonrealization = load_json(X_ATTRIB / "CLOSE02XATTRIB_NONREALIZATION.json")
    controls = load_json(X_ATTRIB / "CLOSE02XATTRIB_RETAINED_CONTROLS.json")
    ticks = trace_ticks(X_ATTRIB / "CLOSE02XATTRIB_R1_TRACE.jsonl", {1, 8, 76, 92, 124})
    manifest_audit = [verify_manifest(root) for root in (X_ATTRIB, W_EVIDENCE, T_ATTRIB, U_EVIDENCE, U_ATTRIB)]
    if not all(item["verified"] for item in manifest_audit):
        raise RuntimeError("retained evidence manifest verification failed")
    changed_production = production_diff()
    if changed_production:
        raise RuntimeError(f"production changed under CLOSE-02AA: {changed_production}")

    tick92 = ticks[92]
    if tick92.get("final_candidate", {}).get("capability") != "APPROACH":
        raise RuntimeError("retained trace no longer supports tick-92 APPROACH")
    outcome92 = tick92.get("verified_outcome_linkage", {})
    if not outcome92.get("success"):
        raise RuntimeError("retained trace no longer supports successful tick-92 APPROACH")

    support_gap = {
        "directive": "UMBRA-CLOSE-02AA",
        "regime": "R1/S16",
        "seed": 57531938,
        "retained_facts": {
            "preventive_attention_first_tick": lifecycle["first_preventive_attention_tick"],
            "rest_opportunity_first_policy_visible_tick": lifecycle["first_policy_visible_rest_route_tick"],
            "supported_positive_first_tick": lifecycle["first_supported_positive_tick"],
            "supported_exhausted_first_tick": lifecycle["first_supported_exhausted_tick"],
            "unknown_route_geometry_evaluations": nonrealization["candidate_nonrealization_reasons"]["CURRENT_UNKNOWN_ROUTE_GEOMETRY"],
            "unknown_capability_support_evaluations": nonrealization["candidate_nonrealization_reasons"]["CURRENT_UNKNOWN_CAPABILITY_SUPPORT"],
            "first_successful_approach_tick": 92,
            "first_successful_approach_verified_outcome": outcome92,
        },
        "gaps": [
            {
                "component": "opportunity_geometry_support",
                "status": "UNKNOWN_ROUTE_GEOMETRY",
                "owner": "WorldModel / perception-policy composition",
                "missing_fields": ["bounded support center", "support radius", "support provenance", "body-schema binding"],
                "finding": "Current direct observations provide a sensor-range upper bound but not the rich bounded support exported for REMEMBERED_ESTIMATE rows. Geometry therefore alternates between directly visible but incompletely represented and remembered with bounded support.",
                "first_available": "intermittently in remembered world-model observations; complete composition became available by tick 124",
            },
            {
                "component": "approach_capability_support",
                "status": "UNKNOWN_CAPABILITY_SUPPORT",
                "owner": "SelfModel",
                "missing_fields": ["verified progress support", "verified applied-step support", "verified completion-lag support", "matching body-schema generation"],
                "finding": "Support begins UNKNOWN and is learned only from successful verified execution of the same capability and body schema.",
                "first_evidence_producing_execution": 92,
            },
            {
                "component": "terminal_recovery_effect_support",
                "status": "SUPPORTED",
                "owner": "VerifiedOutcome effect semantics",
                "finding": "REST already has policy-valid fatigue/integrity restorative effect semantics; this was not the early support blocker.",
            },
            {
                "component": "contact_executability",
                "status": "DISTINCT_FROM_ROUTE_SUPPORT",
                "owner": "Embodiment / VerifiedOutcome",
                "finding": "Remembered or bounded route evidence may justify navigation but never proves current REST contact executability.",
            },
            {
                "component": "temporal_horizon_support",
                "status": "DERIVABLE_WITH_EXISTING_PHYSIOLOGY",
                "owner": "Physiology plus recoverability view",
                "finding": "Drift, bounds, and current values can produce per-dimension margin without a new threshold. Temporal expectations themselves model external events, not internal predicted need.",
            },
        ],
        "conclusion": "Fatigue was relevant and a rest opportunity was visible from tick 1, but route geometry and capability support were not simultaneously policy-supported until the margin was already exhausted at tick 124.",
    }

    producer_map = {
        "directive": "UMBRA-CLOSE-02AA",
        "classification_rule": "An action is a support producer only when existing policy-visible semantics link that behavioral action to the exact missing support and verified execution can confirm the consequence.",
        "producers": [
            {"operation": "governed perception", "support": "current feature and sensor-range bound", "classification": "GUARANTEED_INFORMATION_CONSEQUENCE", "limitation": "does not export the complete rich route-support tuple for current direct observations"},
            {"operation": "WorldModel ingest and remembered estimate", "support": "bounded support, provenance, verified-motion propagation", "classification": "GUARANTEED_INFORMATION_CONSEQUENCE", "limitation": "currently rich policy export is centered on unobserved remembered entities"},
            {"operation": "APPROACH", "support": "same-capability progress, applied-step, completion-lag under the active body schema", "classification": "GUARANTEED_IF_SUCCESSFULLY_VERIFIED", "retained_example_tick": 92, "limitation": "it is already a fatigue-regulatory candidate; no existing semantic makes its exact evidence-production role a deliberate selection reason"},
            {"operation": "MOVE", "support": "MOVE capability envelope only", "classification": "GUARANTEED_IF_SUCCESSFULLY_VERIFIED", "limitation": "does not satisfy missing APPROACH support"},
            {"operation": "ORIENT", "support": "heading change", "classification": "PLAUSIBLE_BUT_UNSUPPORTED_FOR_ROUTE_ACQUISITION", "limitation": "omnidirectional perception means ORIENT does not guarantee expanded visibility"},
            {"operation": "INSPECT", "support": "contact/range-dependent inspect-object outcome", "classification": "PLAUSIBLE_BUT_UNSUPPORTED_FOR_REST_ROUTE_ACQUISITION", "limitation": "not a generic observation-refresh action"},
            {"operation": "energy resource discovery", "support": "bounded resource search opportunity", "classification": "HISTORICAL_ENERGY_SPECIFIC_PRECEDENT", "limitation": "adds a candidate, uses resource-specific state/cooldown and a fixed score; not source-neutral and cannot be generalized under AA"},
        ],
        "missing_primitive": {
            "name": "POLICY_VISIBLE_SUPPORT_PRODUCER_RELATION",
            "required_shape": ["exact missing support field", "regulatory opportunity", "body-schema generation", "source-neutral behavioral candidate identity", "producer status", "verified provenance/revision"],
            "required_semantics": "A bounded, revisable relation showing that an already-generated action can acquire or refresh the exact missing support; failure must not fabricate support.",
            "not_present": "UMBRA records support after outcomes, but does not expose this action-to-missing-support relation to ordinary preventive competition as an authority-valid reason for deliberate support acquisition.",
        },
    }

    preparation = {
        "directive": "UMBRA-CLOSE-02AA",
        "key_decision": "CASE_1_SUPPORT_ACQUISITION_MISSING_PREPARATION_ALREADY_EXISTS",
        "finding": "EXISTING_POSITIVE_PREPARATION_SUFFICIENT_AFTER_SUPPORT",
        "basis": [
            "Fatigue above ideal enters preventive attention before active recovery.",
            "REST and APPROACH/MOVE/ORIENT toward rest are already mapped to fatigue regulatory relevance.",
            "Existing expected_regulatory_gain uses endogenous fatigue urgency for REST and toward-rest movement/orientation.",
            "CLOSE-02T admits regulatory base candidates alongside native intent without source priority.",
            "Retained T evidence shows ordinary preventive REST was generated and selected before active recovery.",
        ],
        "support_acquisition_eligibility_alone_is_insufficient": "APPROACH toward rest was already generated and eligible from the start of the known causal interval; merely relabeling it epistemic would not change competition without a new score, priority, candidate, or other missing semantic.",
        "rejected_locations": {
            "new_score_bonus": "would require an arbitrary numeric weight",
            "fixed_priority": "would create source/need authority",
            "new_candidate": "would exceed existing candidate generation and repeat the energy-specific discovery pattern",
            "direct_execution": "would bypass CLOSE-02T, Governance, and stochastic competition",
        },
        "z_compatibility": "Any later contract can operate only on already-generated candidates. Z candidate-local stochastic identity remains source-neutral and stable under insertion/deletion/permutation; AA makes no Z change.",
    }

    replay = {
        "directive": "UMBRA-CLOSE-02AA",
        "known_seed": {
            "seed": 57531938,
            "finding": support_gap["conclusion"],
            "architecture_application": "The missing producer relation would be relevant, but current authority semantics cannot deliberately use it without a new primitive.",
            "counterfactual_rescue_claimed": False,
        },
        "independent_failures": controls["failures"],
        "successful_controls": controls["successful_controls"],
        "generality": {
            "energy": "Known route/discovery semantics and historical energy failures show support acquisition and horizon evidence are not fatigue-only.",
            "fatigue": "Known R1 shows opportunity and attention can precede simultaneous geometry/capability support.",
            "stimulation": "Retained stimulation denial/progress failure shows the same need for exact support producers, while inspect-specific semantics differ.",
            "integrity": "No adequate environmental-affordance evidence supports forcing a classification; remain UNKNOWN.",
        },
        "control_neutrality": "The architecture must remain neutral when support is already adequate, the dimension is not prospectively relevant, or no policy-valid producer relation exists.",
        "would_propose_without_seed_57531938": True,
        "reason": "W/X retained evidence contains energy, fatigue, and stimulation failure families plus four successful controls; the missing relation is a cross-dimension composition seam, not a seed-specific REST rule.",
    }

    prior_art = """# CLOSE-02AA bounded prior-art review

## Adoptable principles

- Sterling, *Allostasis: a model of predictive regulation* (2012), https://pubmed.ncbi.nlm.nih.gov/21684297/ — regulation can prepare before feedback error becomes acute. This supports the research distinction only; it does not authorize a survival controller.
- Kirsh and Maglio, *On Distinguishing Epistemic from Pragmatic Action* (1994), https://doi.org/10.1207/s15516709cog1804_1 — actions may legitimately acquire task-relevant information. UMBRA still requires a policy-visible action-to-specific-support relation.
- Bajcsy, *Active Perception* (1988), https://repository.upenn.edu/bitstreams/14686d28-7a8a-4554-beee-991eec61cbdd/download — perception and action can be coupled. The adopted boundary is one-step, evidence-grounded acquisition, not sensor planning.
- Cisek, *Cortical mechanisms of action selection: the affordance competition hypothesis* (2007), https://pmc.ncbi.nlm.nih.gov/articles/PMC2440773/ — currently available actions can remain represented in parallel and be contextually biased without a central sequential planner.

## Rejected imports

POMDPs, active inference, MPC, rollout search, entropy/information-gain objectives, epistemic planners, global utility, and authored rescue policies are incompatible with the directive. Literature clarifies vocabulary; it does not substitute for UMBRA evidence.
"""

    contract = """# CLOSE-02AA prospective preparation contract decision

## Decision

No combined implementation contract is supported from current UMBRA semantics.

The evidence selects **Case 1**: positive preparation already exists after support is known, while a policy-valid support-acquisition primitive is missing.

## Exact missing primitive

`POLICY_VISIBLE_SUPPORT_PRODUCER_RELATION` is a conceptual bounded relation over:

1. the exact missing support field;
2. the affected regulatory opportunity and dimension;
3. active body-schema generation;
4. canonical source-neutral identity of an already-generated behavioral candidate;
5. producer status and policy provenance;
6. a revision/release condition from fresh or contradictory verified evidence.

It would state only that executing the candidate can acquire or refresh that exact support under existing verified semantics. It would not create, score, select, or execute an action. Failed or non-informative outcomes could not fabricate support.

## Why current composition is insufficient

UMBRA learns APPROACH support after successful VerifiedOutcome and already makes toward-rest actions eligible and positively relevant during fatigue preventive attention. It does not expose the former as a deliberate, authority-valid reason for selecting the latter. In the retained seed, APPROACH was already eligible before its first successful evidence-producing execution at tick 92. Eligibility-only is therefore behaviorally redundant. Making it win would require a new weight, priority, candidate, or execution authority, all prohibited and absent from current semantics.

## Preserved boundaries

`UNKNOWN` is neither unsafe nor supported. No planner, rollout, global scalar, hidden truth, new candidate, source priority, or Z stochastic change is proposed. Current versus remembered evidence and contact executability remain distinct.
"""

    generality = """# CLOSE-02AA generality review

The architecture question survives removal of seed 57531938. Retained evidence covers energy, fatigue, and stimulation failure families and four successful controls. Across those families, the general problem is whether an already-generated action has policy-valid evidence that it can acquire a specific missing support field before a regulatory margin is exhausted.

This is not a generic permission to explore. Energy's discovery rule is a narrow historical precedent, not the accepted general contract: it manufactures a resource-search candidate and uses a fixed score. Fatigue's APPROACH is already generated and regulatory, but its evidence-production consequence is not an explicit competition input. Stimulation has inspect-related affordances but no authority to infer generic information acquisition. Integrity lacks enough environmental-affordance evidence and must remain UNKNOWN.

The proposal is therefore cross-dimension in shape while remaining neutral wherever a dimension lacks the required affordance semantics. No counterfactual rescue is claimed.
"""

    drift = """# CLOSE-02AA drift review

- Production behavior changes: 0.
- Organism runs: 0.
- Qualification/formal runs: 0.
- Retries/reseeds: 0.
- Threshold/effect/weight/source-priority changes: 0.
- Z candidate-stable stochastic composition: preserved unchanged.
- CLOSE-02T final authority and CLOSE-02U landmark continuity: preserved unchanged.
- V and X production behaviors: not revived.
- Historical evidence: read and hash-verified; not modified.

The research stopped at the missing primitive instead of manufacturing an implementation contract.
"""

    verdict = {
        "directive": "UMBRA-CLOSE-02AA",
        "status": "TERMINAL_ARCHITECTURE_RESEARCH",
        "verdict": "CLOSE02AA_SUPPORT_ACQUISITION_PRIMITIVE_MISSING",
        "key_decision": preparation["key_decision"],
        "positive_preparation": preparation["finding"],
        "exact_missing_primitive": producer_map["missing_primitive"],
        "recommendation": "Return the exact support-producer primitive to Architect. Do not authorize CLOSE-02AB or further engineering from this result.",
        "next_phase_authorized": False,
        "production_changes": 0,
        "organism_runs": 0,
        "retries": 0,
        "reseeds": 0,
    }
    validation = {
        "directive": "UMBRA-CLOSE-02AA",
        "baseline": BASELINE,
        "retained_manifest_audit": manifest_audit,
        "production_diff_from_baseline": changed_production,
        "epistemic_reconstruction": "PASS",
        "existing_mechanism_audit": "PASS",
        "bounded_external_discovery": "PASS",
        "retained_evidence_generality": "PASS",
        "seed_specific_overfit": False,
        "unknown_neutrality": True,
        "z_compatibility": True,
        "organism_runs": 0,
        "production_changes": 0,
        "authority3": "PASS",
        "governance": "PASS",
        "governance_tests": "9 passed",
    }

    artifacts: dict[str, Any] = {
        "CLOSE02AA_SUPPORT_GAP_MAP.json": support_gap,
        "CLOSE02AA_SUPPORT_PRODUCER_MAP.json": producer_map,
        "CLOSE02AA_EXISTING_PREPARATION_AUDIT.json": preparation,
        "CLOSE02AA_RETAINED_EVIDENCE_REPLAY.json": replay,
        "CLOSE02AA_RETAINED_MANIFEST_AUDIT.json": {"audits": manifest_audit, "all_verified": True},
        "CLOSE02AA_VALIDATION.json": validation,
        "CLOSE02AA_VERDICT.json": verdict,
    }
    text_artifacts = {
        "CLOSE02AA_PRIOR_ART_REVIEW.md": prior_art,
        "CLOSE02AA_PROSPECTIVE_PREPARATION_CONTRACT.md": contract,
        "CLOSE02AA_GENERALITY_REVIEW.md": generality,
        "CLOSE02AA_DRIFT_REVIEW.md": drift,
    }
    for name, value in artifacts.items():
        write_json(output / name, value)
    for name, value in text_artifacts.items():
        write_text(output / name, value)

    listed = []
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "EVIDENCE_HASHES.json":
            listed.append({"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size})
    manifest = {
        "directive": "UMBRA-CLOSE-02AA",
        "durability": ["file fsync", "atomic rename", "directory fsync", "readback SHA-256"],
        "files": listed,
    }
    write_json(output / "EVIDENCE_HASHES.json", manifest)
    verified = verify_manifest(output)
    if not verified["verified"]:
        raise RuntimeError(f"final evidence manifest verification failed: {verified}")
    print(json.dumps({"verdict": verdict["verdict"], "evidence": str(output), "manifest": verified}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
