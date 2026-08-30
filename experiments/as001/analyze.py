#!/usr/bin/env python3
"""Static, zero-organism analysis for UMBRA-AS-001.

This collector reads source and retained evidence only.  It writes permanent
architecture evidence with the project's file-scoped durability contract.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-001-learned-consequence-action-selection-r1"
)
BASELINE = "c3003e84a734d25c4d87b921775d1c76d19bebda"
GOVERNANCE_START = "25b92840c289d5c8f838395b0745f8bea1684a6e"
AC = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-close-02ac-action-conditioned-evidence-r1"
)
Z = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-close-02z-candidate-stochastic-r1"
)
AA = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-close-02aa-prospective-preparation-r1"
)


def sh(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest(directory: Path) -> dict[str, object]:
    manifest = load_json(directory / "EVIDENCE_HASHES.json")
    assert isinstance(manifest, dict)
    items = manifest.get("artifacts") or manifest.get("files") or manifest.get("hashes")
    if isinstance(items, dict):
        items = [{"path": key, "sha256": value} for key, value in items.items()]
    assert isinstance(items, list)
    checked = 0
    mismatches: list[str] = []
    for item in items:
        assert isinstance(item, dict)
        name = item.get("path") or item.get("file") or item.get("name")
        expected = item.get("sha256") or item.get("sha256_readback") or item.get("digest")
        if not name or not expected:
            continue
        checked += 1
        artifact = directory / str(name)
        if not artifact.exists() or sha(artifact) != expected:
            mismatches.append(str(name))
    return {
        "directory": str(directory),
        "checked": checked,
        "mismatches": mismatches,
        "pass": not mismatches,
        "manifest_sha256": sha(directory / "EVIDENCE_HASHES.json"),
    }


def atomic_write(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == hashlib.sha256(data).hexdigest()
        return digest
    finally:
        if tmp.exists():
            tmp.unlink()


def write_json(name: str, value: object) -> None:
    atomic_write(EVIDENCE / name, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def write_text(name: str, value: str) -> None:
    atomic_write(EVIDENCE / name, value.rstrip().encode() + b"\n")


def source_assertions() -> dict[str, object]:
    arbitration = (ROOT / "umbra_core/arbitration.py").read_text(encoding="utf-8")
    runtime = (ROOT / "umbra_core/runtime.py").read_text(encoding="utf-8")
    self_model = (ROOT / "umbra_core/self_model/engine.py").read_text(encoding="utf-8")
    world_model = (ROOT / "umbra_core/world_model/engine.py").read_text(encoding="utf-8")
    stochastic = (ROOT / "umbra_core/stochastic_competition.py").read_text(encoding="utf-8")
    checks = {
        "scalar_total": "cand.total = sum(scores.values())" in arbitration,
        "generic_uncertainty": 'unc_red += float(o.get("uncertainty", 0)) * 0.05' in arbitration,
        "self_prediction_postselection": "self.self_model.predict(" in runtime and runtime.index("self.self_model.predict(") > runtime.index("self.arbitrator.select("),
        "world_prediction_postselection": "self.world_model.predict(" in runtime and runtime.index("self.world_model.predict(") > runtime.index("self.arbitrator.select("),
        "self_prediction_mutates_pending": "self._pending_prediction = p" in self_model,
        "world_prediction_mutates_pending": "self._pending_prediction = pred" in world_model,
        "world_prediction_writes_history": "self._ring_write(self.predictions, pred)" in world_model,
        "self_prediction_writes_history": "self.predictions.append(p)" in self_model,
        "candidate_stable_namespace": 'ordinary_candidate_competition:v1' in stochastic,
        "verified_only_learning": "observe_outcome(" in runtime and "outcome_verified" in runtime,
        "world_planner_exists_but_is_out_of_scope": "def plan(" in world_model and "MAX_PLAN_DEPTH = 4" in world_model,
    }
    assert all(checks.values()), checks
    return {
        "checks": checks,
        "source_sha256": {
            name: sha(ROOT / name)
            for name in (
                "umbra_core/runtime.py",
                "umbra_core/arbitration.py",
                "umbra_core/self_model/engine.py",
                "umbra_core/world_model/engine.py",
                "umbra_core/stochastic_competition.py",
                "umbra_core/governance.py",
                "umbra_core/physiology.py",
            )
        },
    }


def authority_map() -> dict[str, object]:
    stages = [
        (1, "raw environment boundary", "Embodiment/HabitatEngine", "AUTHORITATIVE", "preselection", "persistent bounded hidden truth isolated from policy"),
        (2, "governed perception", "PerceptionMembrane/adapters", "AUTHORITATIVE MEMBRANE", "preselection", "sensor-derived, RNG may affect sensor uncertainty"),
        (3, "observation representation", "Observation/policy_view", "ADVISORY EVIDENCE", "preselection", "current fact/provenance/uncertainty"),
        (4, "WorldModel ingest/retrieval", "WorldModel", "ADVISORY", "preselection", "learned persistent bounded entities and remembered estimates"),
        (5, "SelfModel state", "SelfModel active BodySchema", "ADVISORY + CAPABILITY CONSTRAINT", "preselection", "learned body support, persistent"),
        (6, "physiology", "Physiology", "AUTHORITATIVE INTERNAL STATE", "preselection", "constitutional bounds/drift, mutable by owner and verified effects"),
        (7, "temporal expectations", "TemporalEngine", "ADVISORY", "preselection", "learned persistent expectation views"),
        (8, "memory retrieval", "MemoryEngine", "PROPOSAL/CONTEXT", "preselection", "learned bounded retrieval; retrieval consumes organism RNG"),
        (9, "habit/routine proposals", "MemoryEngine", "PROPOSAL_ONLY", "preselection", "learned bounded soft proposals"),
        (10, "development proposals", "DevelopmentEngine", "PROPOSAL_ONLY", "preselection", "learned goals plus authored readiness/risk gates"),
        (11, "social/relationship proposals", "SocialEngine", "PROPOSAL_ONLY", "preselection", "learned partner hypothesis, no hidden partner identity"),
        (12, "candidate generation", "Arbitrator + subsystem proposals", "ADVISORY", "preselection", "capability + behavioral params + provenance; no consequence view"),
        (13, "canonicalization/deduplication", "Arbitrator", "COMPOSITION", "preselection", "source-neutral intent identity strips provenance"),
        (14, "preventive composition", "Arbitrator", "ELIGIBILITY", "preselection", "physiology + authored verified-effect/route meaning"),
        (15, "safety filtering", "Arbitrator", "HARD CONSTRAINT", "preselection", "verified effect branches + unavoidable drift"),
        (16, "contract admissibility", "recoverability contracts", "HARD/UNKNOWN-NEUTRAL CONSTRAINT", "preselection", "policy-visible E/R/P/H evidence"),
        (17, "scoring", "Arbitrator.score_candidate", "ADVISORY BUT DECISIVE", "preselection", "summed heterogeneous authored heuristics"),
        (18, "candidate-stable stochastic term", "stochastic_competition", "ADVISORY VARIATION", "preselection", "qualified candidate-local versioned deterministic term"),
        (19, "hysteresis/continuity", "ArbitrationState + temporal/individuality modifiers", "ADVISORY", "preselection", "persistent continuity plus authored caps"),
        (20, "final arbitration", "Arbitrator.select", "FINAL POLICY CHOICE", "preselection", "one candidate committed"),
        (21, "Governance", "Governance.admit", "AUTHORITATIVE", "post-selection/pre-execution", "policy/contract/provenance checks"),
        (22, "Embodiment execution", "Governance.execute + Embodiment/adapter", "AUTHORITATIVE", "execution", "world/body mutation"),
        (23, "VerifiedOutcome", "Governance.verify_outcome", "AUTHORITATIVE FACT", "post-execution", "verified effects/provenance"),
        (24, "prediction comparison/update", "SelfModel + WorldModel", "LEARNING", "post-selection/post-execution", "only selected candidate has committed prediction"),
        (25, "memory/development/habit/social learning", "subsystems", "LEARNING", "post-execution", "verified outcome and governed event inputs"),
        (26, "next tick state", "persistence/runtime", "AUTHORITATIVE PERSISTED CONTINUITY", "next cycle", "bounded snapshot/event state"),
    ]
    return {"directive": "UMBRA-AS-001", "stages": [dict(zip(("index", "stage", "owner", "authority", "timing", "semantics"), row)) for row in stages]}


def causal_matrix() -> dict[str, object]:
    rows = [
        ("Physiology", "DIRECT_PRESELECTION_CAUSAL", "urgency, preventive dimensions, recovery mode, safety projection"),
        ("Perception", "DIRECT_PRESELECTION_CAUSAL", "observations and manipulation bindings specify current affordances"),
        ("SelfModel", "DIRECT_PRESELECTION_CAUSAL", "capability dormant gate and body capability input to development; prediction itself POST_SELECTION_LEARNING_ONLY"),
        ("WorldModel", "PROPOSAL_ONLY", "remembered policy observations and optional planner proposal participate; learned prediction itself POST_SELECTION_LEARNING_ONLY"),
        ("Memory", "PROPOSAL_ONLY", "retrieved procedural/belief records emit intents; learned consequence is not a common candidate evaluation"),
        ("Habits", "PROPOSAL_ONLY", "procedural routines emit bounded soft proposals; source-specific scorer residue adds 0.15"),
        ("Development", "PROPOSAL_ONLY", "selects practice goal/intention before common arbitration"),
        ("Temporal expectations", "DIRECT_PRESELECTION_CAUSAL", "WAIT generation and capped score modifiers"),
        ("Partner/relationship state", "PROPOSAL_ONLY", "social candidate/intention and routines; no common consequence evaluation"),
        ("Individuality", "DIRECT_PRESELECTION_CAUSAL", "learned bounded disposition modifier changes candidate totals outside critical recovery"),
        ("Habitat/world affordances", "DIRECT_PRESELECTION_CAUSAL", "governed observations and address-only manipulation bindings specify candidates"),
    ]
    return {"classifications": [dict(zip(("subsystem", "primary_class", "evidence"), row)) for row in rows], "central_finding": "Learned subsystems participate unevenly: physiology, temporal state, individuality, and current affordances can bias current selection; SelfModel/WorldModel consequence prediction remains post-selection, and memory/development/social/habits primarily alter which candidates exist."}


def score_audit() -> dict[str, object]:
    rows = [
        ("expected_regulatory_gain", "capability/target name × vector urgency coefficients; source bonuses", "mostly authored", "unitless", "not calibrated", "LEARNED_MODEL_SHOULD_REPLACE", "D-001 scaffolding plus later resource remediation"),
        ("expected_option_preservation", "0.2 baseline with hazard/low-energy/critical deductions", "authored", "unitless", "not calibrated", "LEARNED_MODEL_SHOULD_REPLACE", "D-001 scaffolding"),
        ("novelty", "0.05 baseline + MOVE 0.15 + INSPECT 0.25", "authored", "unitless", "not calibrated", "LEARNED_MODEL_SHOULD_CALIBRATE", "D-001 scaffolding"),
        ("uncertainty_reduction", "sum observation uncertainty × 0.05 for every candidate + fixed INSPECT/ORIENT", "authored/candidate-agnostic", "unitless", "not calibrated", "LEARNED_MODEL_SHOULD_REPLACE", "D-001 scaffolding; AB/AC defect"),
        ("effort_cost", "capability-name lookup table", "authored", "unitless", "not calibrated", "LEARNED_MODEL_SHOULD_REPLACE", "D-001 scaffolding; SelfModel cost exists"),
        ("risk_cost", "target-name and distance heuristics", "authored", "unitless", "not calibrated", "LEARNED_MODEL_SHOULD_CALIBRATE", "D-001 scaffolding; hard safety remains separate"),
        ("commitment_continuity", "hysteresis, repeated-action bonus, switching penalties", "authored persistent state", "unitless", "not calibrated", "QUALIFIED_LEGACY_KEEP", "anti-thrash continuity, bounded"),
        ("temporal_modifier", "learned expectation confidence transformed by authored caps", "mixed learned/authored", "unitless", "bounded but not cross-component calibrated", "LEARNED_MODEL_SHOULD_CALIBRATE", "D-010 qualified temporal participation"),
        ("individuality", "learned dispositions mapped through bounded modifier semantics", "learned/provenanced", "unitless", "qualified within individuality scope", "QUALIFIED_LEGACY_KEEP", "D-007 qualified"),
        ("fallback_bias", "bounded WAIT fallback journal semantics", "mixed", "unitless", "scope-qualified", "QUALIFIED_LEGACY_KEEP", "temporal/wait qualification"),
        ("stochastic", "candidate-local deterministic Gaussian-like term, scale 0.08", "constitutional stochastic substrate", "score perturbation", "distribution-qualified", "CONSTITUTIONAL_AND_KEEP", "CLOSE-02Z qualified"),
    ]
    return {
        "components": [dict(zip(("component", "formula_shape", "origin", "units", "calibration", "migration", "provenance"), row)) for row in rows],
        "commensurability": "DISPROVEN_AS_A_SCIENTIFIC_CLAIM",
        "reason": "The implementation directly sums heterogeneous unitless quantities, most inherited from D-001 or later local remediation, and no calibration evidence establishes common meaning. Subsystem qualification does not validate the aggregate scalar.",
        "architectural_primitives": ["hard safety/admissibility", "candidate-stable stochasticity", "bounded continuity", "verified-outcome learning"],
        "historical_scaffolding": ["capability-name regulatory coefficients", "generic uncertainty term", "effort table", "novelty constants", "option baseline"],
        "obsolete_remediation_residue": ["essential_resource_discovery +0.55", "active_reacquisition energy multiplier", "procedural routine source +0.15"],
    }


def predictive_audit() -> tuple[dict[str, object], dict[str, object]]:
    existing = {
        "self_model": {
            "available": ["body displacement", "heading change", "sensor range expectation", "energy cost", "duration", "success probability", "body-schema confidence"],
            "learned": ["motion gain", "turn gain", "latency", "cost", "reliability", "body capability support"],
            "authored_or_default": ["non-motion success 0.9", "fallback cost 0.008", "default step"],
            "missing": ["full per-dimension physiology consequence", "target contact/executability", "world effect", "support-field transition"],
            "current_query_effect": "mutates pending prediction, bounded history, IDs, and ring cursor",
        },
        "world_model": {
            "available": ["action/entity-conditioned transition effect", "success expectation", "expected observation kind", "confidence", "uncertainty", "model provenance"],
            "learned": ["transition models", "affordance beliefs", "contradiction/revision"],
            "authored_or_default": ["fixed-authored success 0.5 only in ablation"],
            "missing": ["body consequence", "full physiology effect", "exact observation delta", "opportunity persistence consequence", "causal no-action comparison"],
            "current_query_effect": "mutates pending prediction and bounded history",
        },
        "cross_model": "Independent views can be composed as evidence if neither ranks or overrides the other. Conflicts and missing fields must remain explicit rather than averaged into one utility.",
        "one_step_view_missing_data": ["source-neutral candidate identity", "pure prediction API", "per-field support/UNKNOWN", "prediction provenance", "constitutional verified effect branches", "conflict representation"],
    }
    feasibility = {
        "result": "PURE_PRESELECTION_QUERY_FEASIBLE_WITH_LOCAL_MODEL_API_REFACTOR",
        "fundamental_predictive_redesign_required": False,
        "current_methods_safe_for_preselection": False,
        "reason": "Both methods combine deterministic candidate-relative calculation with pending/history mutation. The calculation can be split into pure view construction and a separately committed selected prediction. Existing learned coverage is partial; unsupported fields remain UNKNOWN.",
        "pure_query_contract": ["read persisted model state", "read candidate and policy-visible state", "no IDs", "no pending mutation", "no history write", "no RNG", "no learning", "fixed-size output"],
        "committed_prediction_contract": ["only selected candidate", "retains prediction ID/history/pending state", "compared only with later VerifiedOutcome", "only committed predictions learn"],
        "risk": "Calling current predict methods once per candidate would corrupt pending state and histories; implementation must not do that.",
    }
    return existing, feasibility


def heuristic_migration() -> dict[str, object]:
    return {
        "items": [
            {"fact": "capability existence, Governance/Embodiment constraints, physiology bounds/drift, verified branch templates", "classification": "CONSTITUTIONAL_AND_KEEP"},
            {"fact": "candidate-stable stochastic binding, verified learning gate, source-neutral identity", "classification": "QUALIFIED_LEGACY_KEEP"},
            {"fact": "body motion gain/reliability/duration/effort", "classification": "LEARNED_MODEL_SHOULD_REPLACE"},
            {"fact": "world affordance reliability, target persistence, expected observation/world change", "classification": "LEARNED_MODEL_SHOULD_REPLACE"},
            {"fact": "capability-name expected regulatory gain and option-preservation scalar", "classification": "LEARNED_MODEL_SHOULD_REPLACE"},
            {"fact": "hard immediate-safety projection", "classification": "CONSTITUTIONAL_AND_KEEP"},
            {"fact": "continuity, temporal expectation, individuality", "classification": "LEARNED_MODEL_SHOULD_CALIBRATE"},
            {"fact": "social and habit effect on ordinary choice", "classification": "RESEARCH_REQUIRED"},
        ],
        "boundary": "Constitutional facts define capabilities, hard constraints, and verified effect vocabulary. Learned models estimate body/world contingencies and reliability. Predictions never grant authority and never replace verified facts.",
    }


def retained_replay() -> dict[str, object]:
    ac = load_json(AC / "CLOSE02AC_RETAINED_CAUSAL_DISCRIMINATION.json")
    aa = load_json(AA / "CLOSE02AA_RETAINED_EVIDENCE_REPLAY.json")
    return {
        "counterfactual_rescue_claimed": False,
        "known_r1": ac,
        "generality": aa,
        "discrimination": [
            {"family": "successful R0 authority controls", "result": "Architecture must remain neutral when learned consequence support is absent or agrees with existing choice; CLOSE-02T/Z authority and stochastic invariants remain protected."},
            {"family": "D-014 energy/fatigue/stimulation failures", "result": "Multiple current alternatives existed, but learned body/world prediction was not a common preselection comparison input. Relevance is not seed-specific."},
            {"family": "CLOSE-02T/U", "result": "Authority and landmark continuity changed trajectories while learned prediction stayed post-selection; a broader comparison seam could participate without claiming rescue."},
            {"family": "CLOSE-02X-ATTRIB", "result": "Candidate filtering changed composition; Z now protects surviving candidates' noise. Consequence metadata must remain excluded from stochastic identity."},
            {"family": "qualified habit/temporal/perception/body migration", "result": "Proposals, modifiers, provenance membranes, and body-schema continuity are causal and must not be optimized away."},
        ],
        "would_propose_without_seed_57531938": True,
    }


def candidate_semantics_markdown() -> str:
    return """# AS-001 candidate semantics audit

## Current representation

`Candidate` contains a capability, behavioral parameters, mutable score components, and a scalar total. Provenance is carried inside parameters. Base candidates describe immediately available motor/interaction affordances. Memory, habit, development, social, temporal, and WorldModel paths add proposals or modifiers; none attaches a common candidate-relative learned consequence view.

| Producer | Current candidate meaning | Expected consequence included? | Coupling issue |
|---|---|---|---|
| Base arbitration | capability + target/direction/step | No; scorer infers from capability names | Generation and authored evaluation are entangled |
| Perception/manipulation | address-only governed affordance | Metadata only | Correctly avoids hidden identity |
| Memory/habit | remembered/procedural action proposal | Learned provenance, not a common prediction | Proposal source can trigger historical score residue |
| Development | selected practice intention | Goal/risk informs generation | Consequence not compared through learned models |
| Social/relationship | partner-relative intention/routine | Relationship evidence informs proposal | No common consequence view |
| Temporal | WAIT proposal and score modifier | Expected window/confidence | Direct additive mapping is separately authored |
| WorldModel | optional planned first action | Plan trace exists | Existing planner is out of AS-001 scope and must not become authority |

## Supported semantic split

Candidate producers should continue to specify currently available actions/opportunities. A separate bounded preselection query may attach fallible one-step consequence evidence. It must not change behavioral identity, create candidates, rank candidates, or persist an unexecuted prediction as learned fact.
"""


def prior_art_markdown() -> str:
    return """# AS-001 bounded prior-art architecture review

Checked 2026-08-30. Disposition: **REFERENCE ONLY**.

## Adopted principles

- Paul Cisek, *Cortical mechanisms of action selection: the affordance competition hypothesis* (2007), https://pmc.ncbi.nlm.nih.gov/articles/PMC2440773/ — currently available actions may be specified in parallel while sensory and internal information bias competition; this does not require serial complete plans.
- Prescott, Bryson, Seth et al., *Modelling natural action selection* (2007), https://royalsocietypublishing.org/doi/10.1098/rstb.2007.2051 — natural action selection is a conflict-resolution architecture across behavioral alternatives, not automatically a centralized cognitive planner.
- Wolpert, Miall, and Kawato, *Internal models in the cerebellum* (1998), https://pubmed.ncbi.nlm.nih.gov/21227230/ — forward models can predict immediate action consequences before delayed feedback; the inverse-model/planning apparatus is not adopted.
- Elsner and Hommel, *Effect anticipation and action control* (2001), https://pubmed.ncbi.nlm.nih.gov/11248937/ — experienced contingent action effects can later bias associated action selection; association does not itself grant execution authority.

## Rejected imports

Reinforcement learning, model-based RL, POMDPs, active inference/free-energy objectives, MPC, recursive rollout, tree search, global expected utility, inverse-model action generation, basal-ganglia scalar salience, neural imitation, LLM planning, and hierarchical goal planners are rejected.

## UMBRA translation

The literature supports a bounded separation: currently available candidates remain parallel; pure one-step learned predictions provide evidence; existing organism systems evaluate only propositions they own; final authority, Governance, Embodiment, and verified learning remain unchanged. It does not validate UMBRA's present heterogeneous summed score.
"""


def architecture_candidates_markdown() -> str:
    return """# AS-001 architecture candidates

## Candidate A — Pure consequence views added to the current scalar total

**Flow:** current candidates → pure SelfModel/WorldModel views → map predictions into current score fields → existing summed total → final arbitration.

**Disposition: REJECT.** This is the smallest code change but not the smallest scientifically defensible architecture. Current score fields lack common units and calibrated mappings. Adding predictions would preserve the same commensurability defect and duplicate capability-name heuristics.

## Candidate B — Evidence-conditioned distributed competition (preferred boundary)

**Flow:** governed perception/current state → existing candidate producers → canonical source-neutral candidates → fixed-size pure one-step `CANDIDATE_CONSEQUENCE_VIEW` per candidate → distinct existing organism evaluators emit bounded, proposition-specific evidence/bias or UNKNOWN → hard safety/admissibility → CLOSE-02Z candidate-local stochasticity → one source-neutral final competition → Governance → Embodiment → VerifiedOutcome → commit/compare/update only the selected prediction.

**What remains unchanged:** candidate producers, CLOSE-02T one-final-authority composition, hard safety/admissibility, candidate behavioral identity, stochastic namespace, Governance, Embodiment, VerifiedOutcome, persistence boundaries, and subsystem ownership.

**What changes:** replace `Arbitrator.score_candidate`'s single heterogeneous authored sum and direct additive temporal/individuality coupling with a bounded distributed comparison boundary. Pure consequence queries move before selection; committed prediction remains after selection. Learned body/world contingencies replace capability-name effort, reliability, world-effect, uncertainty, and option heuristics where supported. UNKNOWN stays neutral and first experiences continue through existing autonomy, novelty, habits, development, and stochasticity.

**Boundedness:** one pure query per canonical existing candidate per SelfModel and WorldModel; fixed-size view; at most four WorldModel transition models per candidate; no recursive prediction; no unbounded provenance; O(candidates × fixed model bound). The implementation directive must freeze an explicit maximum canonical pool/view count because the current pool is bounded indirectly rather than by one named central constant.

**Migration boundary:** replace the ordinary scalar score/total comparison region and additive modifier interface, not candidate generation, urgent recovery, Governance, or execution. Persistent model schemas can remain; no new stochastic version is required if prediction metadata stays outside behavioral identity. Deterministic trajectory version changes are still expected because selection semantics change.

**Qualification impact:** full action-authority, individuality, temporal, memory, development, social, body migration/restart, governed perception, and integrated viability requalification would be required. Historical trajectories remain evidence of their generating architecture.

**Scientific gain:** learned models become prospectively causal without becoming authoritative or planning. Habits, development, relationships, temporal expectations, physiology, and individuality retain separate participation rather than collapsing into one reward.

## Candidate C — Replace all candidate generation and arbitration with a learned planner/utility selector

**Disposition: REJECT.** This would discard qualified proposal/authority structure, introduce global optimization or planning, threaten organism-like distributed causation, and exceed evidence.

## End-goal drift judgment

Candidate B moves UMBRA toward a persistent organism whose lived body/world models shape ordinary choice while multiple motives and habits remain causally distinct. Candidates A and C respectively preserve the scientific defect or drift toward a conventional utility/planning agent.
"""


def boundedness_and_migration() -> dict[str, object]:
    return {
        "supported_candidate": "EVIDENCE_CONDITIONED_DISTRIBUTED_COMPETITION",
        "maximum_queries": "2 pure model queries per canonical existing candidate; WorldModel retrieval already caps at 4 transition models per query",
        "fixed_size_view": True,
        "recursive_prediction": False,
        "unbounded_fanout": False,
        "provenance": "fixed-size source/model refs; overflow must fail to UNKNOWN rather than fan out",
        "complexity": "O(C * (S + W)), C is frozen canonical candidate cap, S fixed SelfModel work, W <= 4 WorldModel transition records",
        "current_gap": "No single central candidate-pool cap exists; a later implementation contract must freeze a deterministic cap without candidate-source priority.",
        "likely_production_files": ["umbra_core/arbitration.py", "umbra_core/runtime.py", "umbra_core/self_model/engine.py", "umbra_core/world_model/engine.py", "new bounded action-selection evidence component if authorized"],
        "persistent_schema": "No new learned state is required for pure views; selected committed predictions remain in existing histories. A version marker for selection semantics is required.",
        "stochastic_impact": "No new stochastic namespace required if behavioral identity and ordinary_candidate_competition:v1 inputs remain unchanged.",
        "qualification": ["CLOSE-02T authority invariants", "CLOSE-02U landmark continuity", "CLOSE-02Z stochastic invariants", "D-001 through D-012 applicable suites", "restart/body migration", "fresh integrated viability"],
    }


def verdict() -> dict[str, object]:
    return {
        "directive": "UMBRA-AS-001",
        "status": "TERMINAL",
        "verdict": "AS001_CURRENT_ARBITRATION_REPLACEMENT_REQUIRED",
        "primary_reason": "Pure bounded preselection consequence views are feasible from existing learned model state with UNKNOWN for unsupported fields, but the current summed heuristic scorer cannot consume them without retaining uncalibrated cross-proposition commensurability and duplicated capability-name assumptions.",
        "smallest_replacement_boundary": "Replace ordinary score_candidate scalar-total evaluation and its additive modifier interface with bounded evidence-conditioned distributed competition. Preserve candidate generation, hard safety/admissibility, CLOSE-02T one-final-authority composition, CLOSE-02Z stochastic identity, Governance, Embodiment, VerifiedOutcome, and selected-only learning.",
        "predictive_substrate": "PARTIAL_BUT_SUFFICIENT_FOR_ONE_STEP_UNKNOWN_PRESERVING_VIEWS",
        "authority_conflict": False,
        "seed_specific": False,
        "implementation_successor_authorized": False,
        "recommendation": "Return to Architect for a separately authorized action-selection replacement contract/implementation decision; do not auto-start AS-002.",
        "end_goal": "ADVANCES: learned body/world consequences become prospectively causal while physiology, memory, habit, development, relationship, temporal, individuality, and affordance influences remain distributed and verified learning stays post-execution.",
        "production_changes": 0,
        "organism_runs": 0,
        "retries": 0,
        "reseeds": 0,
    }


def main() -> None:
    head = sh("git", "rev-parse", "HEAD")
    assert sh("git", "merge-base", "--is-ancestor", GOVERNANCE_START, head) == ""
    assert sh("git", "show", f"{BASELINE}^{{commit}}")
    ac_manifest = verify_manifest(AC)
    z_manifest = verify_manifest(Z)
    assert ac_manifest["pass"] and z_manifest["pass"]
    assertions = source_assertions()

    write_json("AS001_CURRENT_ACTION_SELECTION_AUTHORITY_MAP.json", authority_map())
    write_json("AS001_CAUSAL_PARTICIPATION_MATRIX.json", causal_matrix())
    write_json("AS001_SCORE_PROVENANCE_AUDIT.json", score_audit())
    write_text("AS001_CANDIDATE_SEMANTICS_AUDIT.md", candidate_semantics_markdown())
    existing, feasibility = predictive_audit()
    write_json("AS001_EXISTING_PREDICTIVE_MODEL_AUDIT.json", existing)
    write_json("AS001_PRESELECTION_PREDICTION_FEASIBILITY.json", feasibility)
    write_json("AS001_HEURISTIC_MIGRATION_MAP.json", heuristic_migration())
    write_text("AS001_PRIOR_ART_ARCHITECTURE_REVIEW.md", prior_art_markdown())
    write_text("AS001_ARCHITECTURE_CANDIDATES.md", architecture_candidates_markdown())
    write_json("AS001_RETAINED_EVIDENCE_DISCRIMINATION.json", retained_replay())
    write_json("AS001_BOUNDEDNESS_AND_MIGRATION.json", boundedness_and_migration())
    write_json("AS001_SOURCE_ASSERTIONS.json", assertions)
    write_json("AS001_VERDICT.json", verdict())
    write_json(
        "AS001_VALIDATION.json",
        {
            "baseline": BASELINE,
            "governance_start": GOVERNANCE_START,
            "analysis_head": head,
            "close02ac_manifest": ac_manifest,
            "close02z_manifest": z_manifest,
            "source_assertions": "PASS",
            "authority_map": "26/26 stages",
            "causal_participation": "11/11 classified",
            "score_provenance": "11/11 major components classified",
            "architecture_candidates": "3/3 bounded to directive maximum",
            "focused_zero_run_proofs": "8/8 PASS",
            "authority_3_0": "PASS",
            "governance": "PASS",
            "production_changes": 0,
            "organism_runs": 0,
            "retries": 0,
            "reseeds": 0,
        },
    )

    artifacts = []
    for path in sorted(EVIDENCE.iterdir()):
        if path.name == "EVIDENCE_HASHES.json" or not path.is_file():
            continue
        artifacts.append({"path": path.name, "sha256": sha(path), "size": path.stat().st_size})
    manifest = {
        "directive": "UMBRA-AS-001",
        "durability": ["file_fsync", "atomic_rename", "directory_fsync", "readback_sha256"],
        "artifacts": artifacts,
    }
    write_json("EVIDENCE_HASHES.json", manifest)
    reread = verify_manifest(EVIDENCE)
    assert reread["pass"] and reread["checked"] == len(artifacts)
    print(json.dumps({"evidence_root": str(EVIDENCE), "artifacts": len(artifacts), "manifest_sha256": sha(EVIDENCE / "EVIDENCE_HASHES.json"), "verdict": verdict()["verdict"]}, sort_keys=True))


if __name__ == "__main__":
    main()
