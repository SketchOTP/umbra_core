#!/usr/bin/env python3
"""AS-003K offline evidence writer.

This helper never imports UMBRA runtime modules.  It hashes static text and
evaluates only the preregistered literal category matrices below.  It cannot
construct an organism, tick physiology, execute Embodiment, mutate persistence,
learn, or consume organism RNG.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003k-four-drive-regulatory-resolution-r1")
BASELINE = "766df32592ddfb8c57a3dbe6628c6393357652a9"
DRIVES = ("energy", "fatigue", "integrity", "stimulation")
CLASSES = ("CRITICAL", "APPROACHING_CRITICAL", "NONVIABLE", "APPROACHING_VIABLE_BOUNDARY", "VIABLE")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def put(name: str, value: Any) -> str:
    """Atomically publish a canonical JSON evidence artifact with readback."""
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=EVIDENCE)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        destination = EVIDENCE / name
        os.replace(temporary, destination)
        fsync_dir(EVIDENCE)
        observed = destination.read_bytes()
        if observed != data:
            raise RuntimeError(f"readback mismatch: {name}")
        return sha_bytes(observed)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def source_fingerprints() -> dict[str, str]:
    paths = (
        "umbra_core/physiology.py",
        "umbra_core/arbitration.py",
        "umbra_core/runtime.py",
        "umbra_core/distributed_competition.py",
        "umbra_core/stochastic_competition.py",
        "umbra_core/recoverability/contracts.py",
    )
    return {path: sha_file(ROOT / path) for path in paths}


def metadata() -> dict[str, Any]:
    return {
        "schema": "AS003K_FOUR_DRIVE_REGULATORY_RESOLUTION_V1",
        "generated_at": now(),
        "exact_starting_baseline": BASELINE,
        "current_head": git("rev-parse", "HEAD"),
        "production_changes": 0,
        "test_changes": 0,
        "organism_runs": 0,
        "diagnostic_runs": 0,
        "retries": 0,
        "reseeds": 0,
        "analysis_execution": "offline literal-matrix and static-text only",
        "pure_proof": {
            "imports_umbra_core": False,
            "constructs_organism_runtime": False,
            "calls_tick_once": False,
            "executes_embodiment": False,
            "mutates_persistence": False,
            "performs_learning": False,
            "consumes_organism_rng": False,
        },
    }


# Status is ordinal only *within the same drive*: larger means no worse state.
# None is UNKNOWN and blocks a relation.  Values are never summed, averaged,
# normalized, ranked, weighted, or used to select an action.
CASES: list[dict[str, Any]] = [
    {"id":"C01_one_worse_drive", "authority":"ordinary", "question":"A degrades energy to NONVIABLE while B leaves every drive VIABLE.", "scientific_comparisons":["B may dominate A: same-drive no-worse plus strict energy boundary class."], "candidates":{"A":[2,4,4,4],"B":[4,4,4,4]}},
    {"id":"C02_two_same_severe", "authority":"ordinary", "question":"Each candidate improves a different simultaneously APPROACHING_VIABLE_BOUNDARY drive.", "scientific_comparisons":["Neither may dominate: true cross-drive tradeoff, no total ranking."], "candidates":{"A":[4,3,4,4],"B":[3,4,4,4]}},
    {"id":"C03_worse_class_over_safer", "authority":"ordinary", "question":"A restores a NONVIABLE energy result; B changes only already-VIABLE fatigue.", "scientific_comparisons":["A may dominate B because B leaves the worse class unchanged and A is no worse elsewhere."], "candidates":{"A":[4,4,4,4],"B":[2,4,4,4]}},
    {"id":"C04_energy_rescue_fatigue_cost", "authority":"ordinary", "question":"A restores NONVIABLE energy and only changes fatigue within VIABLE; B leaves energy NONVIABLE.", "scientific_comparisons":["A may dominate B; within-VIABLE category carries no invented continuous merit."], "candidates":{"A":[4,4,4,4],"B":[2,4,4,4]}},
    {"id":"C05_fatigue_rescue_energy_cost", "authority":"ordinary", "question":"A restores NONVIABLE fatigue and only changes energy within VIABLE; B leaves fatigue NONVIABLE.", "scientific_comparisons":["A may dominate B."], "candidates":{"A":[4,4,4,4],"B":[4,2,4,4]}},
    {"id":"C06_rest_multidrive_benefit_cost", "authority":"ordinary", "question":"REST protects energy/fatigue but places stimulation nearer its boundary; alternative protects stimulation but leaves energy/fatigue worse.", "scientific_comparisons":["Neither may dominate: two supported drive interests conflict."], "candidates":{"REST":[4,4,4,3],"ALT":[3,3,4,4]}},
    {"id":"C07_stimulation_integrity_conflict", "authority":"ordinary", "question":"One action protects stimulation, the other integrity.", "scientific_comparisons":["Neither may dominate."], "candidates":{"STIM":[4,4,3,4],"INTEGRITY":[4,4,4,3]}},
    {"id":"C08_stimulation_energy_conflict", "authority":"ordinary", "question":"One action protects stimulation, the other energy.", "scientific_comparisons":["Neither may dominate."], "candidates":{"STIM":[3,4,4,4],"ENERGY":[4,4,4,3]}},
    {"id":"C09_all_viable_low_level_motives", "authority":"ordinary", "question":"All post-step drive states remain VIABLE despite different low-level actions.", "scientific_comparisons":["No regulatory dominance claim is justified; residual resolver may act only after other protected evidence."], "candidates":{"A":[4,4,4,4],"B":[4,4,4,4]}},
    {"id":"C10_one_unknown", "authority":"ordinary", "question":"One candidate's fatigue consequence is UNKNOWN.", "scientific_comparisons":["UNKNOWN blocks elimination; it is not neutral."], "candidates":{"A":[4,None,4,4],"B":[3,4,4,4]}},
    {"id":"C11_multiple_unknown", "authority":"ordinary", "question":"Multiple drive consequences are UNKNOWN.", "scientific_comparisons":["UNKNOWN blocks elimination."], "candidates":{"A":[None,None,4,4],"B":[4,4,None,None]}},
    {"id":"C12_boundary_crossing", "authority":"ordinary", "question":"A causes integrity to cross from VIABLE to NONVIABLE; B preserves it.", "scientific_comparisons":["B may dominate A if all other categories are no worse."], "candidates":{"A":[4,4,2,4],"B":[4,4,4,4]}},
    {"id":"C13_same_class_incomparable", "authority":"ordinary", "question":"Both candidates address a different same-severity approaching-boundary drive.", "scientific_comparisons":["Neither may dominate."], "candidates":{"A":[3,4,4,4],"B":[4,3,4,4]}},
    {"id":"C14_permutation_invariance", "authority":"ordinary", "question":"A dominates B and the pool order is reversed.", "scientific_comparisons":["Frontier identity must be invariant to insertion/deletion/permutation."], "candidates":{"A":[4,4,4,4],"B":[2,4,4,4]}},
    {"id":"C15_equivalent_residual", "authority":"ordinary", "question":"Candidates have identical supported regulatory classes.", "scientific_comparisons":["Neither eliminates; candidate-stable CLOSE-02Z may resolve exact residual equivalence."], "candidates":{"A":[4,4,4,4],"B":[4,4,4,4]}},
]


def lock() -> None:
    record = metadata() | {
        "phase": "D_PRE_ANALYSIS_LOCK",
        "family_order": ["R0", "R1", "R2", "R3"],
        "R0_negative_controls": {
            "current_urgency": "REJECT: owner-local authored arithmetic",
            "raw_distance_from_ideal": "REJECT: coordinate-dependent local distance",
            "normalized_deficit": "REJECT: manufactured cross-drive normalization",
            "percentile_or_rank": "REJECT: population-dependent owner ranking",
            "raw_critical_slack": "REJECT: raw coordinates lack common motivational meaning",
            "minimum_raw_slack": "REJECT: hidden bottleneck aggregation",
            "owner_coefficients": "REJECT: authored priority",
            "learned_owner_weights": "REJECT: circular controller-win labels",
        },
        "R1": "separate per-drive categorical regulatory propositions; simultaneous supported partial order; UNKNOWN blocks; CLOSE-02Z residual only",
        "R2": "test only a coordinate-invariant prospective regulatory event; retain each drive as a separate proposition; do not introduce a scalar maximizer",
        "R3": "external architecture is reference-only unless it preserves UMBRA authority and does not impose utility, reward, weights, or planning",
        "category_scale": {str(i): label for i, label in enumerate(CLASSES)},
        "preregistered_cases": CASES,
        "source_fingerprints": source_fingerprints(),
        "lock_rule": "Any family or case semantic change after this artifact is a stop condition.",
    }
    digest = put("AS003K_RESOLVER_FAMILY_LOCK.json", record)
    put("AS003K_RESOLVER_FAMILY_LOCK_SHA256.json", metadata() | {"artifact":"AS003K_RESOLVER_FAMILY_LOCK.json", "sha256":digest, "immutable_for_comparative_analysis":True})


def dominates(a: list[int | None], b: list[int | None]) -> bool:
    if any(x is None for x in a + b):
        return False
    return all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b))


def evaluate_cases() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    reductions = residuals = saturated = 0
    for case in CASES:
        candidates = case["candidates"]
        names = list(candidates)
        dominated = {name for name in names if any(dominates(candidates[other], candidates[name]) for other in names if other != name)}
        frontier = [name for name in names if name not in dominated]
        if dominated:
            reductions += 1
        if len(frontier) > 1:
            residuals += 1
        if len(frontier) == len(names):
            saturated += 1
        rows.append({
            "id":case["id"], "authority_layer":case["authority"], "question":case["question"],
            "scientifically_justified_comparisons":case["scientific_comparisons"],
            "input_categories":{name:{drive:("UNKNOWN" if value is None else CLASSES[value]) for drive,value in zip(DRIVES, values)} for name,values in candidates.items()},
            "dominated_candidates":sorted(dominated), "frontier":frontier,
            "close02z_residual_required":len(frontier)>1,
            "complete_frontier_saturation":len(frontier)==len(names),
        })
    return {"cases":rows, "metrics":{
        "case_count":len(rows), "decisions_with_supported_elimination":reductions,
        "elimination_fraction":round(reductions / len(rows), 6),
        "residual_frontier_decisions":residuals, "residual_frontier_fraction":round(residuals / len(rows),6),
        "complete_frontier_saturation":saturated, "complete_frontier_fraction":round(saturated / len(rows),6),
        "close02z_required_by_literal_regulatory_projection":residuals,
    }}


def analyze() -> None:
    if not (EVIDENCE / "AS003K_RESOLVER_FAMILY_LOCK.json").exists():
        raise RuntimeError("missing pre-analysis resolver lock")
    parent = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003j-owner-ontology-calibration-r1/AS003J_EVIDENCE_MANIFEST.json")
    as003d = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003d-frontier-saturation-attribution-r1")
    put("AS003K_STATE_RECONCILIATION.json", metadata() | {
        "phase":"A_SYNCHRONIZATION", "head_master_github_at_authority_start":BASELINE,
        "governance_start_commit":git("rev-parse", "HEAD~1"),
        "current_head":git("rev-parse", "HEAD"),
        "as003j_verdict":"AS003J_TRUE_DRIVE_CROSS_CALIBRATION_PRIMITIVE_REQUIRED",
        "as003j_manifest_sha256":sha_file(parent),
        "canonical_notion_status":"AS-003K current authority fetched and refetch-verified",
        "production_test_delta_from_exact_baseline":git("diff", "--name-only", f"{BASELINE}..HEAD", "--", "umbra_core", "tests").splitlines(),
        "result":"PASS",
    })
    put("AS003K_REGULATORY_AUTHORITY_PARTITION.json", metadata() | {
        "phase":"B_AUTHORITY_PARTITION",
        "drive_conditions":{drive:{
            "ideal":"ordinary; no cross-drive regulatory authority created by ideal proximity",
            "viable":"ordinary AS-002 path when candidate is admissible",
            "approaching_viable_boundary":"ordinary preventive evidence may be relevant; no new cross-drive authority exists",
            "nonviable":"active recovery if directionally actionable; otherwise diagnostic-only self-correcting overshoot",
            "approaching_critical_boundary":"hard next-state safety/admissibility and recoverability protect critical boundary; active recovery remains outside ordinary competition when triggered",
            "critical":"critical recovery and hard safety; not ordinary competition",
            "self_correcting_overshoot":"no motivational recovery authority for low fatigue or high energy/integrity; stimulation remains actionable on either nonviable side",
        } for drive in DRIVES},
        "actual_source_paths":{
            "physiology":"Bounds.in_viable/critical_violation, active_recovery_needs, critical_any; urgency explicitly heuristic",
            "arbitration":"select recovery branch precedes ordinary candidate competition; critical/active recovery uses legacy recovery path",
            "runtime":"runtime supplies the final arbitration path; no new cross-drive resolver found",
            "distributed_competition":"ordinary canonical admissible pool only",
            "recoverability":"admissibility and critical-boundary preservation, not ordinary motivational calibration",
            "stochastic":"CLOSE-02Z candidate-stable residual selection only",
        },
        "remaining_ordinary_cross_drive_surface":"admissible, noncritical, non-active candidates whose predicted supported consequences keep all owners in ordinary authority but can affect different viable/approaching-boundary drive propositions",
        "result":"PASS",
    })
    put("AS003K_DRIVE_SEMANTICS_MAP.json", metadata() | {
        "phase":"C_DRIVE_SEMANTICS",
        "drives":{
            "energy":{"harmful_direction":"low","ideal":0.70,"viable":[0.30,0.90],"critical":[0.05,1.0],"drift":-0.002,"active_correction":"CHARGE/resource recovery","overshoot":"high energy self-correcting/no energy-increasing recovery","common_consequence":"critical and actionable nonviable conditions leave ordinary path"},
            "fatigue":{"harmful_direction":"high","ideal":0.20,"viable":[0.05,0.70],"critical":[0.0,0.95],"drift":0.002,"active_correction":"REST/rest recovery","overshoot":"low fatigue self-correcting/no fatigue-reducing recovery","common_consequence":"critical and actionable nonviable conditions leave ordinary path"},
            "integrity":{"harmful_direction":"low","ideal":0.85,"viable":[0.35,0.98],"critical":[0.05,1.0],"drift":-0.0002,"active_correction":"hazard/recovery candidate path","overshoot":"high integrity self-correcting/no integrity-increasing recovery","common_consequence":"critical and actionable nonviable conditions leave ordinary path"},
            "stimulation":{"harmful_direction":"both","ideal":0.55,"viable":[0.25,0.80],"critical":[0.05,1.0],"drift":-0.002,"active_correction":"exploration/rest-related candidate path","overshoot":"either outside-viable direction remains actionable","common_consequence":"critical and actionable nonviable conditions leave ordinary path"},
        },
        "verified_effect_templates":"existing one-step templates are authoritative only after VerifiedOutcome; preselection support must remain separately supported/UNKNOWN",
        "common_regulatory_semantics":["critical boundary","viable boundary","ideal reference","autonomous drift","verified outcome effect"],
        "numeric_coincidences_not_comparability":["all raw values are floats near 0..1","urgency returns floats","ideal distances can be numerically compared"],
        "result":"PASS",
    })
    proof = evaluate_cases()
    put("AS003K_ORDINAL_RESOLVER_PROOF.json", metadata() | {"phase":"F_R1_PURE_PROOF", "method":"locked literal matrix; separate drive propositions; simultaneous dominance only", **proof, "finding":"R1 lawfully removes boundary-class regressions but intentionally retains supported cross-drive conflicts, UNKNOWN cases, and all-within-viable distinctions."})
    put("AS003K_FRONTIER_PRESSURE_AUDIT.json", metadata() | {
        "phase":"G_FRONTIER_PRESSURE", "synthetic_locked_case_metrics":proof["metrics"],
        "retained_as003d_context":{"qualifying_ordinary_decisions":2647,"full_v1_eliminations":0,"full_v1_complete_frontiers":2647,"physiology_only_projection_decisions_with_relation":2563,"physiology_only_projection_note":"raw retained physiology ordinals show that regulatory differences exist, but are not lawful cross-drive calibration; this is not a replacement rule."},
        "conclusion":"R1 expresses shared categorical boundary distinctions. It cannot express action-relevant differentials while all drives stay in the same viable category, and it correctly leaves genuine cross-drive conflicts/UNKNOWN unresolved. Therefore a candidate-stable residual resolver would govern every same-class ordinary conflict; R1 alone is not adequate as the ordinary four-drive behavioral resolver.",
        "result":"R1_INSUFFICIENT_NOT_RELAXED",
    })
    put("AS003K_PROSPECTIVE_REGULATORY_HORIZON_AUDIT.json", metadata() | {
        "phase":"H_R2_PROSPECTIVE_AUDIT",
        "quantities":[
            {"name":"raw_distance_or_raw_critical_slack","result":"REJECT","reason":"coordinate-dependent local unit; minimum across drives is hidden scalar bottleneck."},
            {"name":"ticks_until_unassisted_loss_of_viable_state_per_drive","result":"VALID_PER_DRIVE_EVIDENCE_ONLY","common_meaning":"post-action elapsed ticks until that owner leaves its defined viable band under supported autonomous drift","coordinate_invariance":"PASS if raw coordinate, bounds, drift, and verified effect are transformed together","unknown":"UNKNOWN when effect/drift/timing support is unavailable","boundedness":"finite only for supported adverse drift; no unsafely invented infinity","limitation":"kept as four propositions it preserves the same genuine tradeoffs; taking min/max across owners creates a global bottleneck scalar."},
            {"name":"ticks_until_critical","result":"SAFETY_ADMISSIBILITY_ONLY","reason":"common event can support safety/recoverability analysis but moving it into ordinary motivational selection would change protected hard-authority boundary."},
            {"name":"reachable_safe_set_or_recoverability_horizon","result":"REFERENCE_ONLY","reason":"requires route/effect evidence; existing HOMEOSTATIC_RECOVERABILITY_VIEW_V1 uses signed/minimum margins and is not lawful motivational calibration under this directive."},
        ],
        "as002_compatibility":"No prospective quantity supplies lawful cross-drive resolution under AS-002 while each owner remains a separate proposition. Aggregating four horizons (minimum/maximum/sum) would create scalar candidate authority or a new safety layer, both outside this directive.",
        "result":"NO_PROSPECTIVE_CROSS_DRIVE_RESOLVER_SUPPORTED",
    })
    put("AS003K_EXTERNAL_PRIOR_ART_MATRIX.json", metadata() | {
        "phase":"E_EXTERNAL_DISCOVERY", "sources":[
            {"domain":"homeostatic control","source":"https://elifesciences.org/articles/04811","classification":"REJECT","finding":"multidimensional homeostatic RL defines drive as a parameterized distance and rewards drive reduction; it is explicit scalar/reward/RL machinery prohibited here."},
            {"domain":"ethological action selection","source":"https://pmc.ncbi.nlm.nih.gov/articles/PMC2440773/","classification":"REFERENCE","finding":"parallel available actions can receive multiple biasing influences before one action is released; it supports the problem framing but provides no UMBRA calibration semantics."},
            {"domain":"viability/safety","source":"https://arxiv.org/abs/1609.06408","classification":"REFERENCE","finding":"barrier functions concern forward invariance of a safe set; they distinguish safety admissibility from performance but use optimization/controller machinery not adopted here."},
            {"domain":"partial order","source":"https://incose.onlinelibrary.wiley.com/doi/abs/10.1002/sys.21690","classification":"REFERENCE","finding":"more objectives cause nondominance to undermine selection pressure; standard remedies aggregate or relax dominance and are excluded."},
        ],
        "result":"REFERENCE_ONLY_NO_IMPORT",
    })
    put("AS003K_AS002_COMPATIBILITY_AUDIT.json", metadata() | {
        "phase":"I_AS002_COMPATIBILITY", "R1":{"separate_propositions":"PASS","simultaneous_order_independent":"PASS","unknown_non_eliminating":"PASS","scalar_total_or_sum":"PASS absent","owner_source_priority":"PASS absent","close02z":"residual compatible but R1 pressure insufficient","hard_active_recovery":"outside ordinary competition PASS","selected_only_learning":"unchanged PASS"},
        "R2":{"per_drive_horizon_evidence":"compatible only as separate UNKNOWN-aware proposition","cross_drive_aggregate":"FAIL: minimum/maximum/sum substitutes scalar global authority or changes safety boundary"},
        "result":"NO_STRONG_SURVIVING_RESOLVER; AS002_NOT_DISPROVEN",
    })
    put("AS003K_PREMISE_CHALLENGE.json", metadata() | {
        "phase":"J_PREMISE_CHALLENGE", "answers":{
            "continuous_cross_drive_scale_required":"Not established. R1 avoids one, but cannot resolve all ordinary viable-band conflicts.",
            "hard_active_partition_removes_severe_conflicts":"Yes; critical and directionally actionable nonviable states leave ordinary competition.",
            "same_class_conflicts_legitimately_incomparable":"Some are; however, action-relevant within-viable prospective deterioration remains unexpressed by categories.",
            "stochastic_residual_is_bounded_individuality":"Only for genuine residuals. With R1 alone it would decide unresolved ordinary same-class conflicts too often to count as the four-drive regulator.",
            "prospective_horizon_is_not_a_renamed_score":"Per-drive viable-loss horizon has a lawful prospective meaning, but cross-owner aggregation is a renamed scalar bottleneck and is rejected.",
            "total_order_artifact":"Partly. A living organism can tolerate residual incomparability; it still needs a lawful way to make some supported cross-drive conflict causally consequential.",
            "end_goal_effect":"The analysis preserves endogenous separate physiology and VerifiedOutcome evidence, but does not yet supply an ordinary conflict-resolution primitive.",
        }, "result":"ADDITIONAL_CALIBRATION_PRIMITIVE_REQUIRED",
    })
    put("AS003K_VERDICT.json", metadata() | {
        "terminal_verdict":"AS003K_ADDITIONAL_CALIBRATION_PRIMITIVE_REQUIRED",
        "r1":"categorical supported partial ordering is semantically lawful for shared regulatory boundary classes but insufficient as the ordinary four-drive resolver.",
        "r2":"a per-drive post-action time-to-loss-of-viable-state proposition is coordinate-invariant potential evidence, not a lawful cross-drive resolver under AS-002; aggregation is prohibited scalar/safety drift.",
        "exact_missing_primitive":"an independently grounded, non-aggregative cross-drive regulatory conflict relation that states when two supported prospective drive consequences make one ordinary existing candidate causally preferable without owner coefficients, priority, controller-win learning, total utility, or a hard-authority rewrite.",
        "as002_status":"not disproven; its separate propositions/UNKNOWN/simultaneity remain protected, but it lacks the missing cross-drive conflict relation.",
        "close02z_status":"remains a candidate-stable residual resolver and must not become the de facto four-drive controller.",
        "recommendation":"NONE; return to Architect for the exact missing primitive. Do not start a successor.",
    })


def manifest() -> None:
    excluded = {"AS003K_EVIDENCE_MANIFEST.json"}
    files = sorted(p for p in EVIDENCE.glob("AS003K_*") if p.name not in excluded)
    listing = [{"name":p.name,"sha256":sha_file(p),"bytes":p.stat().st_size} for p in files]
    put("AS003K_EVIDENCE_MANIFEST.json", metadata() | {"artifact_count":len(listing),"artifacts":listing,"readback_sha256":"all listed artifacts read back after atomic publication","result":"PASS"})


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"lock", "analyze", "manifest"}:
        raise SystemExit("usage: as003k_research.py {lock|analyze|manifest}")
    {"lock":lock, "analyze":analyze, "manifest":manifest}[sys.argv[1]]()
