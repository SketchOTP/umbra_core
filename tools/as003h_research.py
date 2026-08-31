#!/usr/bin/env python3
"""AS-003H durable, zero-run calibration-identifiability evidence writer.

This tool imports no UMBRA runtime and never executes an organism.  It records
only static source facts, sealed evidence, bounded logical fixtures, and the
reference-only research boundary authorized by AS-003H.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path


BASE = "b9f903d7954c922d2f52dd0a28762f91ccb22a54"
PARENT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003g-simultaneous-context-control-r1")
ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003h-switching-calibration-r1")
PARENT_SHA = "ff78082a8982da6c11a2c403887c313dbd470f2cf24fbc9f8d1cbd3abaaead3e"
HISTORICAL = {
    "AS003F": "2340788c8d1e2c19e2161831fdb6c1611f2aa6a85bd64afc77363971ff42c9dc",
    "AS003E": "58c8cbcf4feb956cf52b936bc2b436494074a884bf0e2875326b00460efa47f7",
    "AS003D": "b2a606286f6e197d100298e3e1d73031b1d302e0cccaacd0a9b3da2a9811cbfe",
    "AS003C": "d8eb4cc26048f6b3b8d9ca861dbfab25f56a6e2b95548949997c638f7812268c",
}
REQUIRED = (
    "AS003H_TRANSITION_PROPOSITION_AUDIT.json",
    "AS003H_DESCRIPTION_VS_CONTROL_AUDIT.md",
    "AS003H_VALID_SWITCH_LEARNING_TARGETS.json",
    "AS003H_SELF_IMITATION_AUDIT.json",
    "AS003H_DWELL_TIME_IDENTIFIABILITY.json",
    "AS003H_TRANSITION_CLOCK_AUDIT.json",
    "AS003H_CONSTITUTIONAL_PRIOR_AUDIT.json",
    "AS003H_PARAMETER_FREE_PRIOR_AUDIT.json",
    "AS003H_VERIFIED_EPISODE_LEARNING_CONTRACT.md",
    "AS003H_BOOTSTRAP_IDENTIFIABILITY.json",
    "AS003H_RL_BOUNDARY_AUDIT.md",
    "AS003H_COMMON_CONTROL_CLAIM_REQUIREMENTS.md",
    "AS003H_TIMEBASE_CONTRACT.json",
    "AS003H_STARVATION_THRASHING_PROOFS.json",
    "AS003H_CALIBRATION_DATA_INVENTORY.json",
    "AS003H_PROSPECTIVE_DATA_COLLECTION_AUDIT.md",
    "AS003H_PRIOR_ART_BOUNDARY.md",
    "AS003H_ARCHITECTURE_CANDIDATES.md",
    "AS003H_REPLACEMENT_CONTRACT.md",
    "AS003H_VERDICT.json",
)


def stamp() -> str:
    return datetime.now(UTC).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integrity() -> dict[str, int]:
    return {
        "production_changes": 0,
        "test_changes": 0,
        "organism_runs": 0,
        "diagnostic_reruns": 0,
        "retries": 0,
        "reseeds": 0,
    }


def put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    directory = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    if not path.read_bytes():
        raise RuntimeError(f"empty_readback:{path.name}")


def write_json(name: str, value: object) -> None:
    put(ROOT / name, json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_md(name: str, value: str) -> None:
    put(ROOT / name, value.strip() + "\n")


def static_facts(repo: Path) -> dict[str, dict[str, str | bool]]:
    probes = {
        "candidate_stochastic_namespace": ("umbra_core/stochastic_competition.py", 'CANDIDATE_COMPETITION_NAMESPACE = "ordinary_candidate_competition:v1"'),
        "candidate_stochastic_sigma": ("umbra_core/stochastic_competition.py", "CANDIDATE_NOISE_SIGMA = 0.08"),
        "critical_boundary": ("umbra_core/arbitration.py", "def _introduces_critical_boundary"),
        "preventive_numeric_urgency": ("umbra_core/arbitration.py", "def _preventive_attention_dimensions"),
        "physiology_urgency": ("umbra_core/physiology.py", "def vector_urgency"),
        "development_active_goal": ("umbra_core/development/engine.py", "active_goal_id: str | None = None"),
        "selfmodel_verified_commit": ("umbra_core/self_model/engine.py", "Compare prediction to verified outcome; attribute; maybe adapt."),
        "worldmodel_verified_commit": ("umbra_core/world_model/engine.py", "Never treat prediction as fact."),
        "runtime_verified_linkage": ("umbra_core/runtime.py", "verified_outcome_linkage"),
    }
    facts: dict[str, dict[str, str | bool]] = {}
    for key, (relative, token) in probes.items():
        source = repo / relative
        if token not in source.read_text(encoding="utf-8"):
            raise RuntimeError(f"static_source_missing:{key}")
        facts[key] = {"path": relative, "token": token, "present": True}
    return facts


def lock(repo: Path, start_commit: str) -> None:
    if sha(PARENT / "AS003G_EVIDENCE_MANIFEST.json") != PARENT_SHA:
        raise RuntimeError("as003g_manifest_hash_mismatch")
    parent = json.loads((PARENT / "AS003G_VERDICT.json").read_text(encoding="utf-8"))
    facts = static_facts(repo)
    proposition = {
        "schema": "AS003H_TRANSITION_PROPOSITION_AUDIT_V1",
        "locked_at": stamp(),
        "baseline": BASE,
        "governance_start_commit": start_commit,
        "parent": {
            "directive": "UMBRA-AS-003G",
            "verdict": parent["primary_verdict"],
            "manifest_sha256": PARENT_SHA,
        },
        "term": "NONHARD_CONTEXT_SPONTANEOUS_RELEASE",
        "provisional_semantic": "An engaged non-hard context relinquishes behavioral control while it remains owner-valid and ACTIVE, without hard interruption, completion, deactivation, or verified blockage.",
        "necessity_result": "NECESSARY_FOR_CONTINUOUS_ACTIVE_INCUMBENT_RIVAL_ONLY_IF_NO_NEW_OWNER_LIFECYCLE_EVENT_EXISTS",
        "necessity_basis": [
            "AS-003G established that completion, deactivation, verified blockage, and hard interruption are valid release boundaries but cannot release a continuously valid incumbent.",
            "AS-003G rejected activation age and time-unserved as scheduler fairness rather than owner-independent behavioral semantics.",
            "No static protected owner currently supplies a shared non-hard lifecycle event that makes an active incumbent yield to an active rival.",
        ],
        "prohibited_reinterpretations": [
            "ordinary candidate stochasticity as context release",
            "arrival of a rival as automatic incumbent preemption",
            "elapsed engine ticks as a timeout",
            "owner-local urgency as a universal control claim",
        ],
        "static_evidence": facts,
        "no_retuning_rule": "The proposition and valid learning-target classifications are immutable before candidate analysis; a contradiction is reported rather than redefined.",
        "integrity": integrity(),
    }
    write_json("AS003H_TRANSITION_PROPOSITION_AUDIT.json", proposition)
    targets = {
        "schema": "AS003H_VALID_SWITCH_LEARNING_TARGETS_V1",
        "locked_at": stamp(),
        "proposition_sha256": sha(ROOT / "AS003H_TRANSITION_PROPOSITION_AUDIT.json"),
        "valid_verified_facts": {
            "owner_inactive": "CAUSALLY_VERIFIED_OWNER_LIFECYCLE: labels an owner end, not voluntary release.",
            "verified_completion": "CAUSALLY_VERIFIED_OWNER_LIFECYCLE: labels completion, not whether an ongoing owner should yield.",
            "verified_progress": "CAUSALLY_VERIFIED_CONSEQUENCE: can update owner/action consequence knowledge, but a single executed trajectory lacks a stay-versus-switch comparison.",
            "verified_blockage_or_denial": "CAUSALLY_VERIFIED_OWNER_LIFECYCLE: supports release when attributed, not spontaneous release while the owner remains valid.",
            "verified_rival_state_change": "CAUSALLY_VERIFIED_ENVIRONMENT_EVENT: can update rival context evidence; it becomes a release label only if a separately established common control proposition says so.",
            "hard_interruption": "CAUSALLY_VERIFIED_EXTERNAL_AUTHORITY: valid hard boundary, outside ordinary non-hard transition learning.",
        },
        "invalid_as_labels": {
            "controller_chose_switch": "SELF_GENERATED_CIRCULAR",
            "controller_chose_stay": "SELF_GENERATED_CIRCULAR",
            "stochastic_order_elected_other": "SELECTOR_OUTPUT_NOT_VERIFIED_OUTCOME",
            "candidate_was_proposed": "NOT_EXECUTED_NOT_VERIFIED",
            "unexecuted_prediction": "COUNTERFACTUAL_NOT_VERIFIED",
            "counterfactual_would_have_been_better": "REQUIRES_FORBIDDEN_REWARD_COMPARISON",
        },
        "lock_conclusion": "No retained fact is a positive label for NONHARD_CONTEXT_SPONTANEOUS_RELEASE. Verified facts can supervise owner lifecycle and consequence models, but not a free context-release hazard.",
        "integrity": integrity(),
    }
    write_json("AS003H_VALID_SWITCH_LEARNING_TARGETS.json", targets)


def analyze(repo: Path) -> None:
    prop = json.loads((ROOT / "AS003H_TRANSITION_PROPOSITION_AUDIT.json").read_text(encoding="utf-8"))
    targets = json.loads((ROOT / "AS003H_VALID_SWITCH_LEARNING_TARGETS.json").read_text(encoding="utf-8"))
    if prop["baseline"] != BASE or not targets["proposition_sha256"] == sha(ROOT / "AS003H_TRANSITION_PROPOSITION_AUDIT.json"):
        raise RuntimeError("preprojection_lock_integrity_fail")
    facts = static_facts(repo)
    write_md("AS003H_DESCRIPTION_VS_CONTROL_AUDIT.md", """
# AS-003H descriptive dynamics versus behavioral control

## Distinction locked before candidate evaluation

An estimate that owner episodes historically ended after a duration, or that the controller historically switched after a duration, is a description. It becomes a behavioral authority only if its event is independently grounded and its application has a verified causal meaning for the current owner/rival relation.

| Candidate target | Classification | Reason |
| --- | --- | --- |
| Completion/deactivation/blockage episode end | CAUSALLY_VERIFIED | The owner-state event is independently verified, but it ends an episode rather than labels spontaneous release. |
| Action-attributed verified progress | CAUSALLY_VERIFIED | Revises a one-step consequence relation. It does not say that switching versus staying was preferable. |
| Historical controller switch frequency | SELF_GENERATED_CIRCULAR | Its positive labels were emitted by the unqualified controller. |
| Dwell-time histogram of those switches | DESCRIPTIVE_ONLY | Predicts historical timing but has no normative authority. |
| HMM/semi-Markov hidden state sequence | DESCRIPTIVE_ONLY | A fitted latent description is not a verified behavioral-control proposition. |
| Hazard fitted to self-generated releases | NORMATIVE_WITHOUT_AUTHORITY | Numerical probability does not establish why a valid current owner ought to yield. |

## Finding

Existing verified learning paths correctly keep prediction distinct from fact and commit only after a verified outcome. They can learn action/owner consequences. They do not provide the missing positive target for `NONHARD_CONTEXT_SPONTANEOUS_RELEASE`; promoting a descriptive duration or switch-frequency fit to authority would violate that separation.
""")
    write_json("AS003H_SELF_IMITATION_AUDIT.json", {
        "schema": "AS003H_SELF_IMITATION_AUDIT_V1", "generated_at": stamp(),
        "architecture": "fit a context-release probability from historical controller release events, then sample future releases from that model",
        "generator_audit": {
            "initial_release_events": "No qualified spontaneous-release generator exists in AS-003G; only lifecycle/hard events and initial residual ordering are qualified.",
            "historical_switches": "A controller-produced switch is not itself a VerifiedOutcome.",
            "consequence_discrimination": "One executed trajectory can verify progress, denial, or completion, but cannot establish the unexecuted stay/switch alternative without forbidden counterfactual reward comparison.",
        },
        "classification": "SELF_IMITATION_NOT_VERIFIED_LEARNING",
        "sole_architecture_result": "REJECTED",
        "valid_retained_learning": "Owner lifecycle and action-consequence relations only; neither identifies a voluntary non-hard release hazard.",
        "integrity": integrity(),
    })
    write_json("AS003H_DWELL_TIME_IDENTIFIABILITY.json", {
        "schema": "AS003H_DWELL_TIME_IDENTIFIABILITY_V1", "generated_at": stamp(),
        "episode_durations": {
            "activation_to_completion": "NATURAL_OWNER_DURATION; valid descriptive owner-lifecycle observation, not desired spontaneous release duration.",
            "activation_to_deactivation": "NATURAL_OWNER_DURATION; may be exogenous/owner-specific and is not cross-owner control.",
            "engagement_to_verified_blockage": "CENSORED_OR_LIFECYCLE_END; can support blockage learning, not persistence timing preference.",
            "engagement_to_hard_interruption": "EXTERNAL_HARD_AUTHORITY; not non-hard competition evidence.",
            "engagement_to_self_generated_release": "INVALID_SELECTOR_OUTPUT; fitting it reproduces the generator.",
        },
        "cross_owner_problem": "A physiology recovery episode, social interaction, temporal window, and development goal have different causal completion processes. Their raw durations have no established shared switching unit.",
        "conclusion": "Dwell time is identifiable descriptively for owner episodes where endings are verified, but desired voluntary release duration is not identifiable from retained UMBRA evidence.",
        "integrity": integrity(),
    })
    write_json("AS003H_TRANSITION_CLOCK_AUDIT.json", {
        "schema": "AS003H_TRANSITION_CLOCK_AUDIT_V1", "generated_at": stamp(),
        "tick_time_hazard": "REJECTED: raw runtime frequency makes body/runtime cadence behavioral authority unless an independently defined organism-time calibration exists.",
        "executed_action_event": "PREFERRED_OBSERVATION_CLOCK_ONLY: portable reconsideration boundary after a completed action, but does not create a release label or probability.",
        "verified_outcome_event": "PREFERRED_LEARNING_CLOCK_ONLY: preserves verified-learning authority and body independence, but verified outcome does not select staying versus switching.",
        "owner_state_change_event": "VALID_OWNER_LIFECYCLE_RECONSIDERATION: completion/deactivation/blockage is a legitimate release boundary; a continuing owner has no spontaneous-release event.",
        "mixed_event_process": "POSSIBLE_CLOCK_FAMILY_NOT_CONTROL: a finite set of verified/action/owner events can bound reevaluation but needs a separate release semantic.",
        "conclusion": "Use event time, not raw ticks, for any future reconsideration process. A clock answers when a rule may run, not what causes non-hard release.",
        "integrity": integrity(),
    })
    write_json("AS003H_CONSTITUTIONAL_PRIOR_AUDIT.json", {
        "schema": "AS003H_CONSTITUTIONAL_PRIOR_AUDIT_V1", "generated_at": stamp(),
        "candidates": {
            "global_spontaneous_release_hazard": {"semantic": "conditional probability of release at a qualified event", "units": "probability per event", "calibration": "NOT_ESTABLISHED", "result": "REJECTED_FREE_PARAMETER"},
            "global_dwell_time_distribution": {"semantic": "episode duration before release", "units": "event duration", "calibration": "NOT_ESTABLISHED", "result": "REJECTED_UNRELATED_OWNER_DURATIONS"},
            "global_adaptation_timescale": {"semantic": "common organism adaptation speed", "units": "time", "calibration": "NOT_ESTABLISHED", "result": "REJECTED_NO_SWITCHING_MEASUREMENT"},
        },
        "independent_sources": {
            "runtime_frequency": "REJECTED: technical cadence, not organism control.",
            "physical_or_embodiment_timescale": "REJECTED: body/actuator pace does not measure motivational release.",
            "physiology_drift": "REJECTED: owner-local regulation dynamics are not common context timing.",
            "action_completion_cadence": "REJECTED: observation cadence only.",
            "memory_habit_development_temporal_times": "REJECTED: subsystem lifecycle values do not calibrate cross-owner release.",
            "external_literature": "REFERENCE_ONLY: reports calibrated/fitted study-specific dynamics, not a portable UMBRA coefficient.",
        },
        "restart_migration": "A value could be persisted, but persistence does not establish semantic authority.",
        "conclusion": "No independently defensible global source-neutral transition prior is calibrated by existing qualified UMBRA or external evidence.",
        "integrity": integrity(),
    })
    write_json("AS003H_PARAMETER_FREE_PRIOR_AUDIT.json", {
        "schema": "AS003H_PARAMETER_FREE_PRIOR_AUDIT_V1", "generated_at": stamp(),
        "attempts": {
            "uniform_probability": "REJECTED: choosing the event support and probability domain supplies a hidden policy.",
            "one_half_switch": "REJECTED: symmetric number is still an authored release chance.",
            "jeffreys_prior": "REJECTED: epistemic prior about an unknown parameter, not organismal behavioral authority.",
            "maximum_entropy_prior": "REJECTED: distribution choice and support encode a free control policy.",
            "hash_threshold": "REJECTED: deterministic randomness relabels an arbitrary probability.",
            "first_stochastic_bit": "REJECTED: produces a 0.5 control rule without calibration.",
            "fixed_geometric_or_exponential": "REJECTED: rate/scale remains a hidden timescale.",
        },
        "conclusion": "Mathematical symmetry removes neither the behavioral proposition nor its calibration requirement.",
        "integrity": integrity(),
    })
    write_md("AS003H_VERIFIED_EPISODE_LEARNING_CONTRACT.md", """
# VERIFIED_EPISODE_SWITCH_DYNAMICS_V0 audit

## Bounded admissible state

An episode record could retain canonical context identity, activation/engagement episode identifier, bounded verified-completion/blockage/deactivation/hard-interruption counters, bounded feature summaries, and a persisted model version. It must retain no unbounded raw history and no unexecuted counterfactual result.

## What valid evidence can learn

Verified action outcomes can update SelfModel/WorldModel consequence relations. Verified owner completion, blockage, or deactivation can characterize owner episode endings. These are valid causal models because their labels are independent of a voluntary context-release decision.

## Identifiability failure

They do **not** identify `P(NONHARD_CONTEXT_SPONTANEOUS_RELEASE | current owner/rival state)`: no retained or prospective valid positive label says a continuing owner should have yielded. Adding self-generated release endings makes the target circular. Replacing that gap with “switch if a different context would have progressed more” requires unexecuted counterfactuals and an authored cross-context payoff, which is prohibited.

## Result

`VERIFIED_EPISODE_SWITCH_DYNAMICS_V0` may describe/learn verified owner lifecycles but is not an implementation-ready non-hard switching controller.
""")
    write_json("AS003H_BOOTSTRAP_IDENTIFIABILITY.json", {
        "schema": "AS003H_BOOTSTRAP_IDENTIFIABILITY_V1", "generated_at": stamp(),
        "novel_organism": "No voluntary release events, no context-specific hazard estimate, and no valid learned duration model exist.",
        "novel_context": "Same absence applies even in an organism with other owner histories; no semantic justification transfers raw duration across owner kinds.",
        "candidate_first_switch_causes": {
            "constitutional_prior": "REJECTED: no independent calibration exists.",
            "stochastic_bootstrap": "REJECTED: an arbitrary hazard under another name.",
            "inherited_species_default": "REJECTED: no constitutional semantic/calibration source exists.",
            "owner_completion_or_blockage": "VALID_BUT_NOT_SPONTANEOUS: ends the owner episode rather than solving continuous active rivals.",
            "developmental_exploration": "REJECTED: without an outcome-grounded control proposition it is an authored policy.",
        },
        "result": "SWITCHING_BOOTSTRAP_UNRESOLVED_UNDER_CURRENT_BOUNDARY",
        "integrity": integrity(),
    })
    write_md("AS003H_RL_BOUNDARY_AUDIT.md", """
# AS-003H reinforcement-learning boundary

Learning an attributed probability of an independently observed owner completion/blockage event is not reinforcement learning by itself. It predicts a verified event and does not select a policy.

A model becomes prohibited RL or an equivalent hidden utility controller if it learns a release policy from reward, discounted return, Q/value terms, policy gradients, “better than staying” counterfactuals, or an authored payoff for progress/rival opportunity. Those mechanisms would need a common tradeoff currency precisely where AS-003H has not established one.

The rejected self-imitation proposal is not automatically RL, but it is still invalid: it copies unqualified selector outputs rather than learning a VerifiedOutcome-grounded event. No current candidate crosses into permitted policy authority.
""")
    write_md("AS003H_COMMON_CONTROL_CLAIM_REQUIREMENTS.md", """
# CURRENT_NONHARD_BEHAVIORAL_CONTROL_CLAIM requirement

AS-003H establishes that a standalone spontaneous-release probability cannot be calibrated from the available verified episodes. The missing primitive is not a generic score, reward, owner importance, or designer preference.

A future common behavioral-control claim would have to state one current organism-level proposition with the **same meaning and unit** for every ACTIVE non-hard owner: the state-dependent tendency for that owner to gain, retain, or relinquish behavioral control under currently verified internal and environmental conditions.

It must define: provenance from each owner; a shared unit that is not merely probability-range false commensurability; how current state and verified one-step consequences update it; a non-arbitrary calibration protocol; treatment of UNKNOWN and first experience; bounded persistence, restart/migration, and individuality; and a categorical/hard-authority boundary. It may not be authored coefficients, cross-owner source rank, global reward, survival utility, or a planner.

Probability alone is insufficient: probabilities of fatigue worsening, opportunity expiry, partner departure, and habit completion concern different propositions. A common `[0,1]` range does not make those claims interchangeable.
""")
    write_json("AS003H_TIMEBASE_CONTRACT.json", {
        "schema": "AS003H_TIMEBASE_CONTRACT_V1", "generated_at": stamp(),
        "required_property": "Body/runtime independence across different tick rates, actuators, migration, pause/resume, and restart.",
        "raw_engine_ticks": "REJECTED_AS_BEHAVIORAL_AUTHORITY",
        "organism_time": "NOT_ESTABLISHED_FOR_SPONTANEOUS_RELEASE; an authoritative unit would still require a switching calibration.",
        "executed_action_events": "VALID_RECONSIDERATION_CLOCK_ONLY",
        "verified_outcome_events": "VALID_LEARNING_CLOCK_ONLY",
        "context_episodes": "VALID_OWNER_LIFECYCLE_DESCRIPTION_ONLY",
        "conclusion": "No extant authoritative timebase supplies a source-neutral voluntary-release timescale.",
        "integrity": integrity(),
    })
    fixtures = {
        "continuous_incumbent_and_rival": "Without a valid release event/hazard, incumbent may persist forever; starvation possible.",
        "incumbent_progresses": "Progress does not establish when it should yield; forced switching needs a separate common claim.",
        "incumbent_repeatedly_blocked": "Verified blockage is a valid lifecycle release, not spontaneous switching.",
        "persistent_rival_opportunity": "Opportunity alone does not preempt under AS-003F/G source-neutral boundary.",
        "transient_rival_opportunity": "A lost opportunity may be verified afterward but cannot provide a counterfactual label for an unexecuted switch.",
        "three_contexts": "Pairwise/rotational hazards need a common control claim or become source/fairness policy.",
        "newly_active_rival": "Active-set change permits reconsideration but not automatic dethroning.",
        "hard_interruption_and_resumption": "Hard authority is valid external interruption; it does not calibrate normal non-hard release.",
        "new_organism": "No history supplies first voluntary switch.",
        "migrated_organism": "Persistence preserves a learned model but cannot justify an unidentifiable one.",
    }
    write_json("AS003H_STARVATION_THRASHING_PROOFS.json", {
        "schema": "AS003H_STARVATION_THRASHING_PROOFS_V1", "generated_at": stamp(),
        "method": "Pure logical fixtures; no organism/candidate execution.", "fixtures": fixtures,
        "thrashing": {
            "per_outcome_or_per_tick_re_election": "REJECTED: makes residual randomness ordinary control and can switch every event.",
            "minimum_dwell_time": "REJECTED: arbitrary timeout without calibration.",
            "categorical_persistence": "BOUNDED_AGAINST_THRASHING but permits starvation for continuous rivals.",
            "learned_self_switch_frequency": "CIRCULAR and cannot prove either starvation or thrashing safety.",
        },
        "conclusion": "None of the three permitted transition candidates proves both non-starvation and non-thrashing without a missing calibrated/common control primitive.",
        "integrity": integrity(),
    })
    write_json("AS003H_CALIBRATION_DATA_INVENTORY.json", {
        "schema": "AS003H_CALIBRATION_DATA_INVENTORY_V1", "generated_at": stamp(),
        "sources": {
            "AS003C_frozen_AB_traces": "INVALID_SELECTOR_OUTPUT: V1 full-frontier/CLOSE-02Z selections are not ground-truth context transitions.",
            "AS003F_context_reconstruction": "CONTEXT_STATE_ONLY: 327 zero, 2315 single, and five development+memory coactivations expose the proposition but do not label voluntary releases.",
            "AS003G_transition_analysis": "CONTEXT_STATE_ONLY: proves persistence/lifecycle and lack of shared non-hard release fact.",
            "qualified_habit_routine_fixtures": "VALID_CALIBRATION_TARGET_FOR_OWNER_COMPLETION_ONLY.",
            "temporal_fixtures": "VALID_CALIBRATION_TARGET_FOR_WINDOW_STATUS_ONLY.",
            "development_fixtures": "VALID_CALIBRATION_TARGET_FOR_OWNER_GOAL_LIFECYCLE_ONLY.",
            "social_relationship_fixtures": "CONTEXT_STATE_ONLY: no universal voluntary-release label.",
            "historical_context_like_transitions": "INSUFFICIENT: absent common semantic and verified stay-versus-switch labels.",
        },
        "conclusion": "No retained corpus provides a valid calibration target for a spontaneous release hazard.",
        "integrity": integrity(),
    })
    write_md("AS003H_PROSPECTIVE_DATA_COLLECTION_AUDIT.md", """
# AS-003H prospective data-collection audit

Shadow-only observation can record owner activation/deactivation, completion, blockage, action outcomes, and opportunity changes without changing behavior. Those observations can strengthen owner lifecycle and consequence models.

It cannot generate a valid label that a continuing incumbent ought to release: a shadow alternative remains unexecuted, and treating a current defective selector's switch as ground truth recreates self-imitation. Verified outcomes alone do not distinguish the counterfactual switch/stay result.

**Result:** current shadow-only collection cannot identify the missing hazard/control parameter. No data-collection successor is recommended.
""")
    write_md("AS003H_PRIOR_ART_BOUNDARY.md", """
# AS-003H prior-art boundary

## Richman et al. (2023), PMC10651489 — REFERENCE ONLY

Adopt only the qualitative observation that persistent goal states, stochastic transitions, and need-dependent modulation can coexist. Reject direct import of the energy landscape, fitted relative-need scale, gradient, diffusion/noise coefficient, neural implementation, and any numerical transition calibration.

## Sanabria et al. (2019), PMC6907728 — REFERENCE ONLY

Adopt only that motivated behavior can be organized over persistent states and that state-transition structures make temporal hypotheses explicit. Reject promoting a Markov/semi-Markov description to UMBRA behavioral authority without a verified target.

## Hazard learning — REFERENCE ONLY

Wilson et al. (2010), PMC2966286, establishes that a hazard parameter can be inferred from an observed change-point process. It does not establish that an organism's controller-generated switch stream supplies independent ground-truth events. A probability model needs labels whose event proposition is independent of the control it will authorize.

## Disposition

Prior art supports explicit temporal modeling and calibrated learning **after** an observed event process exists. It does not solve AS-003H's causal bootstrap and imports no RL, reward, planner, global utility, fitted coefficient, or UMBRA controller.
""")
    write_md("AS003H_ARCHITECTURE_CANDIDATES.md", """
# AS-003H bounded architecture candidates

## A. Independently calibrated constitutional switching dynamics — REJECTED

Would need one source-neutral event probability/timescale with a shared behavioral meaning and independent calibration. No existing UMBRA or external source measures voluntary cross-owner release. A fixed value, dwell distribution, or adaptation time merely hides a free control policy.

## B. Verified-episode learned switching dynamics — REJECTED

Valid verified labels cover completion, blockage, deactivation, hard interruption, and executed consequences. They do not label an active incumbent's voluntary yield. Fitting the controller's own releases is `SELF_IMITATION_NOT_VERIFIED_LEARNING`; inferring “would have been better” requires prohibited counterfactual payoff comparison.

## C. Mixed constitutional bootstrap plus verified learning — REJECTED

The bootstrap is uncalibrated and the update target remains absent. Combining two unsupported parts does not create authority.

## Convergence

No permitted switching-hazard family survives. The exact missing primitive is specified separately as a common, current non-hard behavioral-control proposition; this document does not introduce it as a fourth candidate.
""")
    write_md("AS003H_REPLACEMENT_CONTRACT.md", """
# AS-003H replacement-contract disposition

No implementation-ready switching-dynamics contract is supported.

The next architecture boundary, if authorized by the Architect, must first establish a `CURRENT_NONHARD_BEHAVIORAL_CONTROL_CLAIM`: an independently meaningful, calibratable, state-dependent common proposition by which heterogeneous ACTIVE non-hard owners can gain, retain, or relinquish control. It must preserve owner provenance, UNKNOWN, first experience, selected-only VerifiedOutcome learning, categorical hard authority, body independence, migration/restart, bounded state, and candidate-stable residual individuality.

It must not collapse to a weighted global utility, source priority, timeout, fairness scheduler, reward/value/RL, planner, or a standalone arbitrary hazard. No AS-003I implementation recommendation is made.
""")
    write_json("AS003H_VERDICT.json", {
        "schema": "AS003H_VERDICT_V1", "generated_at": stamp(),
        "primary_verdict": "AS003H_COMMON_BEHAVIORAL_CONTROL_CLAIM_REQUIRED",
        "recommendation": None,
        "v1_status": "SUPPORTED_DOMINANCE_DISTRIBUTED_COMPETITION_V1_REMAINS_RETIRED",
        "answers": {
            "can_switching_dynamics_be_learned": "Not as voluntary non-hard release under current evidence; verified episode learning can learn lifecycle/consequence facts only.",
            "what_supervises_learning": "Verified owner completion/blockage/deactivation and action consequences supervise their own causal propositions, not switch desirability.",
            "what_creates_first_switch": "No independently authorized process. Lifecycle/hard events are not spontaneous release; a free bootstrap is rejected.",
            "is_global_switching_timescale_meaningful": "No: existing body/runtime/subsystem timescales do not measure cross-owner motivational release.",
            "does_spontaneous_switching_require_arbitrary_coefficient": "Any standalone constitutional hazard does under current evidence.",
            "is_common_behavioral_control_claim_unavoidable": "Yes, if UMBRA requires non-hard voluntary release between continuously active contexts.",
        },
        "basis": [
            "No valid positive label for NONHARD_CONTEXT_SPONTANEOUS_RELEASE exists in retained verified data.",
            "Self-generated switching is circular and counterfactual comparison would introduce prohibited reward authority.",
            "No independent source calibrates a global hazard/dwell/adaptation timescale.",
            "Event clocks bound reconsideration but do not supply a release cause.",
            "Permitted candidates cannot jointly rule out starvation and thrashing.",
        ],
        "integrity": integrity(),
    })


def manifest() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        raise RuntimeError("missing_required_artifacts:" + ",".join(missing))
    inventory = {name: sha(ROOT / name) for name in REQUIRED}
    data = {
        "schema": "AS003H_EVIDENCE_MANIFEST_V1", "generated_at": stamp(),
        "baseline": BASE, "parent_manifest_sha256": PARENT_SHA,
        "historical_manifest_sha256": HISTORICAL, "required_artifacts": inventory,
        "required_artifact_count": len(REQUIRED), "integrity": integrity(),
        "verdict": json.loads((ROOT / "AS003H_VERDICT.json").read_text(encoding="utf-8"))["primary_verdict"],
    }
    write_json("AS003H_EVIDENCE_MANIFEST.json", data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lock", "analyze", "manifest"))
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--start-commit", default="")
    args = parser.parse_args()
    if args.mode == "lock":
        if not args.start_commit:
            raise SystemExit("--start-commit required for lock")
        lock(args.repo, args.start_commit)
    elif args.mode == "analyze":
        analyze(args.repo)
    else:
        manifest()


if __name__ == "__main__":
    main()
