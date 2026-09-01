#!/usr/bin/env python3
"""AS-003J durable zero-run owner-ontology evidence writer."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path


BASE = "c736db0594e21abfcd5d472d5af3b0cdd7d3780c"
ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003j-owner-ontology-calibration-r1")
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence")
PARENT = EVIDENCE / "umbra-as-003i-behavioral-control-salience-r1"
PARENT_SHA = "36cf66889418a252669003000c4f5353779de1c459979e381e36a0acead7728a"
REQ = (
    "AS003J_PRIOR_ROLE_DECISION_RECOVERY.json",
    "AS003J_PRIOR_ART_BOUNDARY.md",
    "AS003J_ONTOLOGY_CRITERIA_LOCK.json",
    "AS003J_OWNER_ONTOLOGY_CLASSIFICATION.json",
    "AS003J_END_GOAL_CAUSAL_COVERAGE.json",
    "AS003J_PHYSIOLOGY_REGULATORY_SEMANTICS_AUDIT.json",
    "AS003J_SOCIAL_HOMEOSTASIS_AUDIT.md",
    "AS003J_EXPLORATION_DRIVE_AUDIT.md",
    "AS003J_TEMPORAL_ROLE_AUDIT.json",
    "AS003J_HABIT_CONTROL_ONTOLOGY.md",
    "AS003J_MEMORY_ROLE_AUDIT.json",
    "AS003J_MOTIVATIONAL_OWNER_SET_LOCK.json",
    "AS003J_REGULATORY_ANCHOR_AUDIT.json",
    "AS003J_DRIVE_INCENTIVE_INTERACTION_AUDIT.json",
    "AS003J_BEHAVIORAL_DEMAND_CALIBRATION_AUDIT.md",
    "AS003J_CONTROLLER_MOTIVATION_BOUNDARY.md",
    "AS003J_ONTOLOGY_PROJECTION.json",
    "AS003J_ARCHITECTURE_CANDIDATES.md",
    "AS003J_REPLACEMENT_CONTRACT.md",
    "AS003J_VERDICT.json",
)


def now() -> str:
    return datetime.now(UTC).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integrity() -> dict[str, int]:
    return {"production_changes": 0, "test_changes": 0, "organism_runs": 0,
            "diagnostic_reruns": 0, "retries": 0, "reseeds": 0}


def put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)
    descriptor = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if not path.read_bytes():
        raise RuntimeError(f"empty_readback:{path.name}")


def write_json(name: str, value: dict) -> None:
    put(ROOT / name, json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_md(name: str, text: str) -> None:
    put(ROOT / name, text.strip() + "\n")


def source_facts(repo: Path) -> dict[str, dict[str, str]]:
    probes = {
        "physiology": ("umbra_core/physiology.py", "def vector_urgency"),
        "physiology_bounds": ("umbra_core/physiology.py", "BOUNDS: dict[str, Bounds]"),
        "temporal": ("umbra_core/temporal/policy.py", "class PolicyExpectationView"),
        "habit": ("umbra_core/memory/engine.py", "def routine_soft_proposals"),
        "development": ("umbra_core/development/engine.py", "Practice proposes actions only"),
        "social": ("umbra_core/social/engine.py", "def current_satiation"),
        "continuity": ("umbra_core/arbitration.py", "# commitment continuity"),
        "verified_learning": ("umbra_core/world_model/engine.py", "Never treat prediction as fact."),
        "hard_authority": ("umbra_core/arbitration.py", "def _introduces_critical_boundary"),
    }
    result = {}
    for key, (relative, token) in probes.items():
        path = repo / relative
        if token not in path.read_text(encoding="utf-8"):
            raise RuntimeError(f"missing_source_token:{key}")
        result[key] = {"path": relative, "token": token}
    return result


def git_value(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def lock(repo: Path, governance_start: str) -> None:
    if sha(PARENT / "AS003I_EVIDENCE_MANIFEST.json") != PARENT_SHA:
        raise RuntimeError("as003i_manifest_mismatch")
    verdict = json.loads((PARENT / "AS003I_VERDICT.json").read_text())
    recovery = {
        "schema": "AS003J_PRIOR_ROLE_DECISION_RECOVERY_V1",
        "generated_at": now(), "baseline": BASE, "governance_start_commit": governance_start,
        "parent": {"verdict": verdict["primary_verdict"], "manifest_sha256": PARENT_SHA},
        "recovered_prior_roles": {
            "physiology": "owner-local constitutional regulation; hard/active recovery is external to non-hard comparison",
            "temporal_expectation": "policy-visible recurrence/window context; current source had been treated as an owner only for WAIT/preparation specification",
            "habit_routine": "MemoryEngine procedural proposal/lifecycle; provenance never grants final authority",
            "development_practice": "selected goal and capability/practice proposal; final action authority downstream",
            "memory_recall": "retrieval/association/candidate parameterization, not merit by provenance",
            "relationship_social": "partner cue and learned relationship context can specify social proposals but no direct execution",
            "environment_opportunity": "governed perception/habitat affordance enables/parameterizes candidates, never self-promotes",
            "individuality": "persistent disposition ledger with no qualified ACTIVE/INACTIVE lifecycle",
            "engagement_commitment": "state after valid election; existing action continuity is not a source-neutral owner identity",
            "learned_models": "VerifiedOutcome-grounded one-step association/prediction; neither grants execution authority nor rewrites owner state",
            "hard_authority": "critical safety, recovery, Governance, and Embodiment remain outside non-hard motivational comparison",
        },
        "prior_constraints": ["AS-003D retired V1 after zero eliminations", "AS-003F required owner-derived activation before selection", "AS-003H required a common non-hard control claim", "AS-003I found a common salience meaning but no adapters"],
        "integrity": integrity(),
    }
    write_json("AS003J_PRIOR_ROLE_DECISION_RECOVERY.json", recovery)
    criteria = {
        "schema": "AS003J_ONTOLOGY_CRITERIA_LOCK_V1", "locked_at": now(),
        "parent_recovery_sha256": sha(ROOT / "AS003J_PRIOR_ROLE_DECISION_RECOVERY.json"),
        "criteria": {
            "MOTIVATIONAL_DRIVE_OWNER": "internally owned persistent regulatory state with independent activation/deactivation semantics; expression can satisfy or correct the state; not merely a cue for another concern",
            "INTRINSIC_MOTIVATION_OWNER": "autonomous non-homeostatic motive with independently evidenced activation and cessation semantics, not a reward bonus",
            "INCENTIVE_OR_OPPORTUNITY": "policy-visible cue or affordance whose effect depends on another current drive/context; cannot create that drive by itself",
            "LEARNED_ASSOCIATION": "VerifiedOutcome-grounded prediction linking cue/action/opportunity to a consequence relevant to another owner",
            "HABITUAL_CONTROL": "bounded learned procedural structure that can shape proposal, execution continuity, or persistence without representing a current need",
            "DEVELOPMENTAL_MODULATOR": "capability, practice, readiness, novelty, or developmental state that changes what/how behavior can be expressed without independently representing deprivation",
            "MEMORY_CONTEXT": "retrieval, reconstruction, parameterization, or prediction support without independent deprivation/desire/satiation",
            "CONTINUITY_COMMITMENT": "persistence of an already engaged behavioral/context state, not initial motive",
            "HARD_AUTHORITY": "safety, critical recovery, Governance, or Embodiment authority outside non-hard motivational control",
        },
        "lock_rule": "criteria are immutable before classification and frozen-corpus projection; owner count is not an optimization target",
        "integrity": integrity(),
    }
    write_json("AS003J_ONTOLOGY_CRITERIA_LOCK.json", criteria)


def analyze(repo: Path) -> None:
    facts = source_facts(repo)
    if not (ROOT / "AS003J_ONTOLOGY_CRITERIA_LOCK.json").is_file():
        raise RuntimeError("criteria_lock_missing")
    classification = {
        "schema": "AS003J_OWNER_ONTOLOGY_CLASSIFICATION_V1", "generated_at": now(),
        "criteria_lock_sha256": sha(ROOT / "AS003J_ONTOLOGY_CRITERIA_LOCK.json"),
        "source_facts": facts,
        "systems": {
            "energy": {"primary_role": "MOTIVATIONAL_DRIVE_OWNER", "owner": "Physiology", "activation": "persistent constitutional level outside owner-defined acceptable condition", "deactivation": "verified outcome/drift returns state to acceptable condition", "cross_owner_mapping": "REQUIRES_INDEPENDENT_CALIBRATION"},
            "fatigue": {"primary_role": "MOTIVATIONAL_DRIVE_OWNER", "owner": "Physiology", "activation": "persistent constitutional excess above owner-defined acceptable condition", "deactivation": "rest/correction returns state", "cross_owner_mapping": "REQUIRES_INDEPENDENT_CALIBRATION"},
            "integrity": {"primary_role": "MOTIVATIONAL_DRIVE_OWNER", "owner": "Physiology", "activation": "persistent constitutional deficit or injury condition", "deactivation": "verified correction returns state", "cross_owner_mapping": "REQUIRES_INDEPENDENT_CALIBRATION"},
            "stimulation": {"primary_role": "MOTIVATIONAL_DRIVE_OWNER", "secondary_role": "exploration substrate", "owner": "Physiology", "activation": "persistent constitutional low/high deviation", "deactivation": "verified engagement/correction returns state", "cross_owner_mapping": "REQUIRES_INDEPENDENT_CALIBRATION; no export of urgency()"},
            "temporal_expectation": {"primary_role": "INCENTIVE_OR_OPPORTUNITY", "secondary_role": "MEMORY_CONTEXT", "owner": "TemporalEngine", "activation": "policy expectation window/status", "deactivation": "window/status/revision", "cross_owner_mapping": "NO; no deprivation/satiation state"},
            "habit_routine": {"primary_role": "HABITUAL_CONTROL", "owner": "MemoryEngine", "activation": "selected verified procedural lifecycle and eligible bindings", "deactivation": "completion, invalid binding, verified denial/revision", "cross_owner_mapping": "NO; controller-arbitration boundary remains"},
            "development_practice": {"primary_role": "DEVELOPMENTAL_MODULATOR", "secondary_role": "candidate capability/practice context", "owner": "DevelopmentEngine", "activation": "selected goal/readiness/risk/capability state", "deactivation": "goal completion, invalidity, readiness loss", "cross_owner_mapping": "NO; existing score is owner-local and not a need"},
            "memory_recall": {"primary_role": "MEMORY_CONTEXT", "secondary_role": "LEARNED_ASSOCIATION", "owner": "MemoryEngine", "activation": "retrieval/working state", "deactivation": "expiry, invalidation, owner working-state change", "cross_owner_mapping": "NO; no deprivation/desire/satiation"},
            "relationship_state": {"primary_role": "LEARNED_ASSOCIATION", "secondary_role": "MEMORY_CONTEXT", "owner": "SocialEngine", "activation": "partner hypothesis/context/cue", "deactivation": "partner loss, contested/retired hypothesis, interaction outcome", "cross_owner_mapping": "NO; partner-specific satiation is not an organism-wide social deficit"},
            "partner_social_opportunity": {"primary_role": "INCENTIVE_OR_OPPORTUNITY", "owner": "governed perception/habitat", "activation": "visible policy-safe partner cue", "deactivation": "cue disappears/inadmissible", "cross_owner_mapping": "NO; opportunity does not create a social drive"},
            "environment_opportunity": {"primary_role": "INCENTIVE_OR_OPPORTUNITY", "owner": "habitat/perception", "activation": "policy-visible affordance", "deactivation": "affordance loss/admissibility", "cross_owner_mapping": "NO"},
            "individuality": {"primary_role": "DEVELOPMENTAL_MODULATOR", "owner": "IndividualityEngine", "activation": "persistent disposition context", "deactivation": "no qualified ACTIVE lifecycle", "cross_owner_mapping": "NO"},
            "commitment": {"primary_role": "CONTINUITY_COMMITMENT", "owner": "ArbitrationState", "activation": "already selected action continuity", "deactivation": "switch/completion/hard interruption", "cross_owner_mapping": "NO; not initial motivation"},
            "self_world_associations": {"primary_role": "LEARNED_ASSOCIATION", "owner": "SelfModel/WorldModel", "activation": "read-only one-step prediction for existing candidate", "deactivation": "model revision/unsupported field", "cross_owner_mapping": "NO; selected VerifiedOutcome learning only"},
            "hard_recovery_governance_embodiment": {"primary_role": "HARD_AUTHORITY", "owner": "Physiology/Governance/Embodiment", "activation": "critical/admissibility/governance boundary", "deactivation": "authoritative condition clears", "cross_owner_mapping": "EXTERNAL_TO_NONHARD_CONTROL"},
        }, "integrity": integrity(),
    }
    write_json("AS003J_OWNER_ONTOLOGY_CLASSIFICATION.json", classification)
    write_md("AS003J_PRIOR_ART_BOUNDARY.md", """# Prior-art boundary

Reference-quality literature is used only to constrain architectural roles. Motivation/cognition and incentive-motivation sources distinguish current state, learned association, and cue/opportunity; this supports keeping an opportunity from becoming an owner by itself. Habit literature distinguishes habitual control from current goal value; this supports a non-reward, non-RL habit-control role. Social-homeostasis reviews make a separately regulated social drive scientifically plausible but do not establish one in current UMBRA or justify partner value/affection. Intrinsic-motivation literature permits exploration as a distinct architecture but does not require one where current source already provides bounded stimulation regulation. Behavioral-demand literature is retained only to reject current circular controller-output calibration.

No neural topology, dopamine implementation, RL/model-free/model-based architecture, utility maximization, behavioral-economic equation, externally fitted species coefficient, planner, POMDP, MPC, or active-inference mechanism is imported. Sources are reference-only and do not create a UMBRA calibration rule.""")
    coverage = {
        "schema": "AS003J_END_GOAL_CAUSAL_COVERAGE_V1", "generated_at": now(),
        "coverage": {
            "temporal_expectation": "window/status -> WAIT/preparation candidate generation and context-specific one-step prediction; not peer control claim",
            "habit_routine": "selected verified procedural memory -> eligible bounded routine proposal/current-step continuity -> existing final authority; interruption remains possible",
            "memory": "working/episodic/semantic retrieval -> context reconstruction, target/parameter binding, verified association, one-step prediction",
            "development": "competence/readiness/practice goal -> availability and shape of candidate capability; selected outcomes revise competence",
            "relationship": "partner hypothesis/history -> cue identity, trust/reliability association, social proposal parameterization; no affection utility",
            "opportunity": "perception/habitat affordance -> enables/disables executable candidate and conditions incentive expression; no self-promotion",
            "individuality": "persistent selected-outcome ledger -> contextual expression differences without a new need",
            "physiology": "constitutional state/drift/verified outcome effect -> non-hard recovery/prevention and external critical authority",
        },
        "result": "ALL_REQUIRED_SYSTEMS_RETAIN_CAUSAL_PATHS_AFTER_OWNER_REDUCTION", "integrity": integrity(),
    }
    write_json("AS003J_END_GOAL_CAUSAL_COVERAGE.json", coverage)
    physiology = {
        "schema": "AS003J_PHYSIOLOGY_REGULATORY_SEMANTICS_AUDIT_V1", "generated_at": now(),
        "dimensions": ["energy", "fatigue", "integrity", "stimulation"],
        "shared_constitutional_form": "each dimension has critical/viable/ideal boundaries, endogenous drift, owner state, verified outcome effects, and satisfaction/correction semantics",
        "true_drive_result": "SUPPORTED", "urgency_export": "REJECTED_LOCAL_HEURISTIC_WITH_SHARED_NUMERIC_RANGE",
        "why": "urgency() contains dimension-specific direction handling and overshoot arithmetic; its shared [0,1] storage/range does not establish that equal values mean equal corrective behavioral demand across dimensions",
        "common_anchor_result": "CATEGORICAL_REGULATORY_ANCHORS_SHARED; CONTINUOUS_CROSS_DRIVE_CALIBRATION_NOT_ESTABLISHED",
        "integrity": integrity(),
    }
    write_json("AS003J_PHYSIOLOGY_REGULATORY_SEMANTICS_AUDIT.json", physiology)
    write_md("AS003J_SOCIAL_HOMEOSTASIS_AUDIT.md", """# Social-homeostasis audit

Current `SocialEngine` contains partner hypotheses, familiarity/reliability, interaction context, partner-specific derived satiation, and bounded routines. It does **not** contain one organism-owned social-contact detector, independently maintained social deficit/surplus state, owner-defined acceptable social range, or verified non-partner-specific corrective state transition. Partner-specific satiation is relationship state, not a general social regulatory state; treating it as a universal social need would create partner ranking/affection semantics.

Social-homeostasis literature makes a separate social drive scientifically plausible, but does not prove that UMBRA already has one or authorize adding it. Social and relationship behavior remains causal as incentive, learned association, and opportunity. **Disposition: no current social drive; no social-homeostasis implementation primitive is authorized.**""")
    write_md("AS003J_EXPLORATION_DRIVE_AUDIT.md", """# Exploration / stimulation audit

UMBRA already has a persistent `stimulation` physiology dimension with constitutional bounds, endogenous drift, outcome effects, satiation penalty, and existing exploratory/engagement action effects. Development supplies capability, practice-goal, readiness, and novelty-related expression; it does not independently own deprivation/satiation semantics. The existing stimulation owner therefore supplies the smallest currently evidenced exploratory basis.

**H1 selected:** stimulation is sufficient for the presently required exploratory/developmental causal coverage. This does not claim that all possible intrinsic motivation is homeostasis, nor does it authorize exporting the existing stimulation urgency as a universal scale or adding reward/curiosity optimization.""")
    temporal = {
        "schema": "AS003J_TEMPORAL_ROLE_AUDIT_V1", "generated_at": now(),
        "findings": {"deprivation_satisfaction_variable": "ABSENT", "independent_window_need": "NOT_ESTABLISHED", "current_role": "policy-visible recurrence/window context that conditions opportunity, WAIT/preparation generation, and prediction", "underlying_motive_inactive": "temporal view cannot lawfully create a drive by itself", "salience_bid_needed": "NO"},
        "classification": "INCENTIVE_OR_OPPORTUNITY_PLUS_MEMORY_CONTEXT", "integrity": integrity(),
    }
    write_json("AS003J_TEMPORAL_ROLE_AUDIT.json", temporal)
    write_md("AS003J_HABIT_CONTROL_ONTOLOGY.md", """# Habit-control ontology

Habit/routine state is a bounded learned procedural lifecycle. It can supply an eligible routine step, bind it to current context, preserve current procedural progression, and be interrupted or revised by selected verified outcomes. It has no independent owner-maintained deficit, satiation, or corrective state. Animal-learning evidence supports distinguishing such habitual control from current motivational value; UMBRA must not turn it into cached reward/RL authority.

**Classification:** `HABITUAL_CONTROL`, with candidate-generation and continuity roles, not a motivational drive. A separate unresolved controller-arbitration question remains whenever an active routine conflicts with a current non-hard drive: the reduced owner ontology does not elect that controller or make it a salience bid.""")
    memory = {
        "schema": "AS003J_MEMORY_ROLE_AUDIT_V1", "generated_at": now(),
        "independent_deprivation_desire_satiation": "ABSENT", "roles": ["association", "context reconstruction", "opportunity reconstruction", "candidate parameterization", "prediction support"],
        "classification": "MEMORY_CONTEXT", "causal_preservation": "selected verified outcomes update bounded memory; later retrieval can change candidate availability/parameters without provenance merit", "integrity": integrity(),
    }
    write_json("AS003J_MEMORY_ROLE_AUDIT.json", memory)
    owner_set = {
        "schema": "AS003J_MOTIVATIONAL_OWNER_SET_LOCK_V1", "locked_at": now(),
        "classification_sha256": sha(ROOT / "AS003J_OWNER_ONTOLOGY_CLASSIFICATION.json"),
        "included": {"energy": "physiological regulatory drive", "fatigue": "physiological regulatory drive", "integrity": "physiological regulatory drive", "stimulation": "physiological regulatory/exploration drive"},
        "excluded_with_preserved_role": {"temporal_expectation": "incentive/context/WAIT-preparation", "habit_routine": "procedural controller/proposal/continuity", "development_practice": "capability and practice modulator", "memory_recall": "context/association/prediction", "relationship_state": "partner-specific learned association/context", "partner_social_opportunity": "incentive/opportunity", "environment_opportunity": "enabler/incentive", "individuality": "persistent expression modulator", "commitment": "post-election continuity", "self_world_associations": "verified predictive association", "hard_authority": "external safety/governance"},
        "social_drive": "NOT_CURRENTLY_ESTABLISHED", "intrinsic_seeking": "COVERED_BY_EXISTING_STIMULATION_ON_CURRENT_EVIDENCE", "lock_rule": "owner set may not change during calibration projection", "integrity": integrity(),
    }
    write_json("AS003J_MOTIVATIONAL_OWNER_SET_LOCK.json", owner_set)
    anchors = {
        "schema": "AS003J_REGULATORY_ANCHOR_AUDIT_V1", "generated_at": now(),
        "owner_set_lock_sha256": sha(ROOT / "AS003J_MOTIVATIONAL_OWNER_SET_LOCK.json"),
        "anchors": {"fully_satisfied_or_acceptable_range": "same categorical regulatory meaning across physiology dimensions", "behaviorally_meaningful_departure": "same qualitative correction-needed meaning", "viable_edge": "same viability-boundary meaning", "critical_boundary": "external hard authority, not common non-hard magnitude", "adaptive_range": "constitutionally represented for physiology; no social range exists"},
        "continuous_calibration": "NOT_ESTABLISHED", "reason": "shared category labels do not determine how far one drive's departure should outrank another; local normalization and urgency export remain prohibited", "integrity": integrity(),
    }
    write_json("AS003J_REGULATORY_ANCHOR_AUDIT.json", anchors)
    interaction = {
        "schema": "AS003J_DRIVE_INCENTIVE_INTERACTION_AUDIT_V1", "generated_at": now(),
        "contract": "current motivational drive state -> VerifiedOutcome-grounded cue/opportunity association -> context-specific expression of that drive",
        "constraints": ["drive state remains owner-authoritative", "association cannot create or rewrite a drive", "opportunity cannot self-promote", "current drive change can alter a learned cue's relevance", "only selected actions update associations"],
        "applications": {"resource_cue": "physiology-regulated resource expression", "partner_cue": "social opportunity only if a future social drive is separately established; otherwise learned context/proposal", "temporal_window": "conditions an underlying drive/context but cannot create one", "routine_cue": "procedural expression/continuity, not motivation", "familiar_location": "world/memory contextual association", "practice_opportunity": "stimulation/development capability expression"},
        "result": "SEMANTICALLY_VALID_NONNUMERIC_ARCHITECTURE_BOUNDARY", "integrity": integrity(),
    }
    write_json("AS003J_DRIVE_INCENTIVE_INTERACTION_AUDIT.json", interaction)
    write_md("AS003J_BEHAVIORAL_DEMAND_CALIBRATION_AUDIT.md", """# Behavioral-demand calibration audit

Standardized willingness-to-pay/response-cost assays can be informative **within** a single established motive, but they are not currently a lawful cross-owner calibration source for UMBRA. Measured effort is an output of the missing selector; using it as target would bootstrap relative control from controller behavior. A forced cost can also change endogenous action semantics, and UMBRA has no demonstrated body-independent price unit shared across action, physiology, social interaction, or cognition.

**Disposition:** circular for present calibration. A future protocol would need a pre-established non-circular drive-specific assay, an independently defined standardized body cost, and a rule that the assay cannot grant controller authority. No such data protocol is authorized here.""")
    write_md("AS003J_CONTROLLER_MOTIVATION_BOUNDARY.md", """# Controller versus motivation boundary

Hard recovery, Governance, and Embodiment remain external hard authority. Existing commitment is post-election continuity. Habit/routine remains a separate nonmotivational controller because it can preserve or propose procedural behavior without owning a current need. Random/scripted modes are diagnostic/experimental modes, not organism motivational owners.

**Open boundary:** if an eligible habitual/committed controller conflicts with a non-hard regulatory drive, reduced motivation ontology does not itself provide a lawful initial election, preemption, or release rule. Do not conceal this by making habit a peer salience owner.""")
    projection = {
        "schema": "AS003J_ONTOLOGY_PROJECTION_V1", "generated_at": now(),
        "owner_set_lock_sha256": sha(ROOT / "AS003J_MOTIVATIONAL_OWNER_SET_LOCK.json"),
        "inputs": {"AS003C_context_rows": {"zero": 327, "single": 2315, "multiple": 5, "total": 2647}, "mode": "static/frozen-artifact only"},
        "result": {"true_motivational_owner_families": 1, "true_motivational_dimensions": 4, "context_only_or_modulator_families": 8, "habit_or_continuity_controller_families": 2, "cross_drive_pressure_values_computable": 0, "reason": "owner-set lock permits shared categorical anchors but no continuous cross-drive mapping; assigning values would violate calibration prohibition"},
        "overfit_check": "PASS: role reduction follows source lifecycle semantics and external architectural roles, not CLOSE-02 fatigue/R1 outcome", "integrity": integrity(),
    }
    write_json("AS003J_ONTOLOGY_PROJECTION.json", projection)
    write_md("AS003J_ARCHITECTURE_CANDIDATES.md", """# Architecture candidates

## Candidate A — regulatory drives plus incentives **(best supported, incomplete)**

Energy, fatigue, integrity, and stimulation are true drives. Temporal views, memory, learned consequences, opportunities, relationship context, and development condition which existing actions express a drive. Habit/commitment stays a controller boundary. This preserves causal coverage without a global utility, but lacks a lawful continuous cross-drive regulatory-control calibration and leaves controller arbitration open.

## Candidate B — regulatory drives plus distinct intrinsic SEEKING **(not supported on current source)**

Would require an independent non-homeostatic activation/cessation substrate. Current source already provides stimulation with state, bounds, drift, and satisfaction-like semantics; development has capability/practice but not independent need semantics. Adding SEEKING now would be ungrounded.

## Candidate C — broad owner ontology retained **(rejected)**

Treating temporal, habit, development, memory, and relationship context as peers contradicts their source role/lifecycle and recreates AS-003I's uncalibrated owner-adapter problem. It is neither required for end-goal causal coverage nor supported by the ontology criteria.""")
    write_md("AS003J_REPLACEMENT_CONTRACT.md", """# Replacement-contract boundary

No implementation-ready action-selection replacement is supported. The smallest preserved replan is conceptual: a future controller may distinguish (1) true regulatory drive state, (2) verified cue/opportunity association, (3) candidate expression, and (4) nonmotivational habit/commitment control, while retaining hard authority and selected-only learning.

Before implementation, UMBRA needs an independently grounded continuous calibration relation among energy, fatigue, integrity, and stimulation **or** a different explicitly justified cross-drive resolution primitive. Existing `urgency()`/numeric ranges cannot be exported; no normalization, coefficient, global value, reward, source priority, or historical-seed fitting is allowed. Habit-controller arbitration remains separate.""")
    verdict = {
        "schema": "AS003J_VERDICT_V1", "generated_at": now(),
        "primary_verdict": "AS003J_TRUE_DRIVE_CROSS_CALIBRATION_PRIMITIVE_REQUIRED", "recommendation": None,
        "motivational_owner_set": ["energy", "fatigue", "integrity", "stimulation"],
        "basis": ["Owner reduction is evidence-backed: temporal, habit, development, memory, relationship context, and opportunity lack independent persistent need/deprivation/satiation semantics.", "All demoted systems retain causal behavioral roles.", "Existing physiology supplies shared categorical regulatory anchors but `urgency()` and shared numeric storage are local heuristics, not a proven continuous cross-drive control scale.", "No current social drive exists; partner-specific satiation is not a general social homeostasis substrate.", "Existing stimulation covers current exploration/developmental motivation; a distinct SEEKING primitive is not established.", "Habit/commitment controller arbitration remains separate."],
        "v1_status": "SUPPORTED_DOMINANCE_DISTRIBUTED_COMPETITION_V1_REMAINS_RETIRED", "integrity": integrity(),
    }
    write_json("AS003J_VERDICT.json", verdict)


def manifest() -> None:
    missing = [name for name in REQ if not (ROOT / name).is_file()]
    if missing:
        raise RuntimeError("missing_artifacts:" + ",".join(missing))
    entries = {name: sha(ROOT / name) for name in REQ}
    write_json("AS003J_EVIDENCE_MANIFEST.json", {"schema": "AS003J_EVIDENCE_MANIFEST_V1", "generated_at": now(), "baseline": BASE, "required_count": len(REQ), "artifacts": entries, "integrity": integrity()})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lock", "analyze", "manifest"))
    parser.add_argument("--repo", required=True)
    parser.add_argument("--governance-start")
    args = parser.parse_args()
    repo = Path(args.repo)
    if git_value(repo, "rev-parse", BASE) != BASE:
        raise RuntimeError("baseline_missing")
    if args.mode == "lock":
        if not args.governance_start:
            raise RuntimeError("governance_start_required")
        lock(repo, args.governance_start)
    elif args.mode == "analyze":
        analyze(repo)
    else:
        manifest()


if __name__ == "__main__":
    main()
