#!/usr/bin/env python3
"""AS-003G offline evidence writer. It imports no UMBRA runtime."""
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import UTC, datetime
from pathlib import Path

BASE="016b71417c3420fdf119aa253e029a0a013ae9d3"
PARENT=Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003f-motivational-context-contract-r1")
ROOT=Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003g-simultaneous-context-control-r1")
PSHA="2340788c8d1e2c19e2161831fdb6c1611f2aa6a85bd64afc77363971ff42c9dc"
HIST={"AS003E":"58c8cbcf4feb956cf52b936bc2b436494074a884bf0e2875326b00460efa47f7","AS003D":"b2a606286f6e197d100298e3e1d73031b1d302e0cccaacd0a9b3da2a9811cbfe","AS003C":"d8eb4cc26048f6b3b8d9ca861dbfab25f56a6e2b95548949997c638f7812268c"}
REQ=("AS003G_PARENT_CONTRACT_RECOVERY.json","AS003G_PROBLEM_DECOMPOSITION.md","AS003G_CONTROL_SEMANTICS_LOCK.json","AS003G_DEFERRAL_CLAIM_AUDIT.json","AS003G_CONTEXT_STOCHASTIC_IDENTITY.md","AS003G_INCUMBENT_PERSISTENCE_CONTRACT.json","AS003G_CONTEXT_EPISODE_AUDIT.json","AS003G_TEMPORAL_CONTROL_CLAIM_AUDIT.json","AS003G_CLOSE02Z_REUSE_BOUNDARY.json","AS003G_PERSISTENT_CONTEXT_STATE_ANALYSIS.md","AS003G_STARVATION_PROOFS.json","AS003G_THRASHING_PROOFS.json","AS003G_STOCHASTIC_AUTHORITY_ANALYSIS.json","AS003G_NONPHYSIOLOGY_CAUSALITY_REVIEW.md","AS003G_COMMON_CONTROL_CLAIM_REQUIREMENTS.md","AS003G_PRIOR_ART_BOUNDARY.md","AS003G_ARCHITECTURE_CANDIDATES.md","AS003G_REPLACEMENT_CONTRACT.md","AS003G_VERDICT.json")
def stamp(): return datetime.now(UTC).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def integ(): return {"production_changes":0,"test_changes":0,"organism_runs":0,"diagnostic_reruns":0,"retries":0,"reseeds":0}
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name("."+p.name+".tmp-"+str(os.getpid()))
 with t.open("w",encoding="utf-8",newline="\n") as h: h.write(s); h.flush(); os.fsync(h.fileno())
 os.replace(t,p); d=os.open(p.parent,os.O_DIRECTORY)
 try: os.fsync(d)
 finally: os.close(d)
 if not p.read_bytes(): raise RuntimeError("empty_readback:"+p.name)
def j(r,n,v): put(r/n,json.dumps(v,sort_keys=True,indent=2)+"\n")
def md(r,n,v): put(r/n,v.strip()+"\n")
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def statics(repo):
 probes={"candidate_namespace":("umbra_core/stochastic_competition.py",'CANDIDATE_COMPETITION_NAMESPACE = "ordinary_candidate_competition:v1"'),"candidate_sigma":("umbra_core/stochastic_competition.py","CANDIDATE_NOISE_SIGMA = 0.08"),"source_neutral_identity":("umbra_core/stochastic_competition.py","PROVENANCE_ONLY_KEYS"),"hard_one_step":("umbra_core/arbitration.py","def _introduces_critical_boundary"),"preventive_numeric":("umbra_core/arbitration.py","def _preventive_attention_dimensions"),"phys_active_recovery":("umbra_core/physiology.py","def active_recovery_needs"),"temporal_window":("umbra_core/temporal/policy.py","class PolicyExpectationView"),"development_goal":("umbra_core/development/engine.py","active_goal_id: str | None = None")}
 out={}
 for k,(r,t) in probes.items():
  p=repo/r
  if t not in p.read_text(encoding="utf-8"): raise RuntimeError("static_source_missing:"+k)
  out[k]={"path":r,"token":t,"present":True}
 return out
def lock(root,repo,commit):
 if sha(PARENT/"AS003F_EVIDENCE_MANIFEST.json")!=PSHA: raise RuntimeError("as003f_manifest_hash_mismatch")
 p=load(PARENT/"AS003F_VERDICT.json"); c=load(PARENT/"AS003F_SIMULTANEOUS_CONTEXT_DATASET.json")
 rec={"schema":"AS003G_PARENT_CONTRACT_RECOVERY_V1","generated_at":stamp(),"baseline":BASE,"parent":{"directive":"UMBRA-AS-003F","verdict":p["primary_verdict"],"manifest_sha256":PSHA,"missing_proposition":p["missing_proposition"],"supported_boundary":p["disposition"]},"frozen_corpus":c["summary"],"preserved_historical_manifests":HIST,"retrieval_limits":p["basis"]["corpus_limits"],"integrity":integ()}
 j(root,"AS003G_PARENT_CONTRACT_RECOVERY.json",rec)
 md(root,"AS003G_PROBLEM_DECOMPOSITION.md","""# AS-003G problem decomposition

## C1 -- initial election

Several non-hard contexts are ACTIVE, no engaged context exists, and no hard authority or owner lifecycle event selects one. A contract must establish whether a unique common categorical fact elects a context, or whether the contexts are genuinely unordered and may use a source-neutral residual tie.

## C2 -- persistence

An already engaged context remains ACTIVE. Persistence may retain control until owner revalidation fails, completion/blockage occurs, or hard authority interrupts. It cannot decide the no-incumbent state.

## C3 -- switching / starvation

The incumbent remains ACTIVE while an independently legitimate rival also remains ACTIVE. A complete contract needs an owner-independent reason to reconsider or switch; initial election alone leaves the rival indefinitely excluded.""")
 sem={"schema":"AS003G_CONTROL_SEMANTICS_LOCK_V1","locked_at":stamp(),"baseline":BASE,"governance_start_commit":commit,"parent_recovery_sha256":sha(root/"AS003G_PARENT_CONTRACT_RECOVERY.json"),"semantics":{"one_step_deferral_loss":"CONTEXT_CANNOT_SAFELY_DEFER_ONE_ORDINARY_DECISION only when owner-authoritative and policy-visible evidence establishes that omitting its next ordinary expression crosses an already-established boundary or irreversibly loses the presently relevant opportunity; never importance or owner-local urgency.","owner_lifecycle":"Completion, deactivation, withdrawal, or verified blockage ends that owner episode; never comparative merit.","active_set_change":"Changed active set is RECONSIDER only, never PREEMPT.","verified_service":"Owner-attributed selected VerifiedOutcome is context expression/progress; no yielding presupposed.","continuous_activation_age":"Authoritative ticks continuously ACTIVE; physical duration, not presumed entitlement.","time_since_verified_expression":"Authoritative ticks since owner-attributed selected outcome; observable duration, not presumed fairness authority.","incumbent_engagement":"Persisted source-neutral identity valid while owner ACTIVE and no hard interruption; no numeric bonus.","stochastic_tie":"At a justified election event deterministic keyed ordering resolves only genuinely unordered contexts; never score, probability, or per-tick hazard."},"stochastic_constraints":{"namespace":"context_election:v1 (analysis-only)","key_fields":["persistent_organism_basis","election_event_identity","canonical_context_identity"],"excluded":["proposal_source","owner_rank","insertion_order","candidate_index","candidate_gaussian_sigma"],"no_free_parameter":"Ordering an unordered finite set is scale-free; no sigma or transition probability is locked."},"no_retuning_rule":"Locked meanings cannot change after projection results; contradictions are reported.","integrity":integ()}
 j(root,"AS003G_CONTROL_SEMANTICS_LOCK.json",sem)
def analyze(root,repo):
 L=load(root/"AS003G_CONTROL_SEMANTICS_LOCK.json")
 if L["baseline"]!=BASE: raise RuntimeError("lock_baseline_mismatch")
 S=statics(repo); C=load(PARENT/"AS003F_SIMULTANEOUS_CONTEXT_DATASET.json")["summary"]
 j(root,"AS003G_DEFERRAL_CLAIM_AUDIT.json",{"schema":"AS003G_DEFERRAL_CLAIM_AUDIT_V1","generated_at":stamp(),"locked_claim":L["semantics"]["one_step_deferral_loss"],"owner_assessment":{"physiology":"HARD_ONLY_SUPPORTED: existing one-step critical boundary is external; non-hard preventive relevance is numeric urgency and cannot become threshold.","temporal":"PARTIAL_OWNER_LOCAL: ACTIVE windows establish relevance but not universal irreversible loss after one ordinary omission.","social":"NOT_ESTABLISHED: opportunity may disappear, but no cross-owner one-step loss contract exists.","habit":"NOT_ESTABLISHED: completion/binding/denial end routine but deferral is not common irreversible loss.","development":"NOT_ESTABLISHED: selected valid goal exists, but readiness/risk/resource values are owner-local.","memory":"NOT_ESTABLISHED: recall may enable candidate but no universal next-step loss is defined.","opportunity":"NOT_A_MOTIVATIONAL_OWNER: enables candidates only."},"conclusion":"NO_COMMON_CATEGORICAL_DEFERRAL_CLAIM_SUPPORTED; hard one-step safety remains external.","static_evidence":S,"integrity":integ()})
 md(root,"AS003G_CONTEXT_STOCHASTIC_IDENTITY.md","""# AS-003G context stochastic identity

A future residual election identity must encode context kind, semantic scope, materially necessary opportunity/entity/partner identity, owner semantic-state version, and activation-episode identity only when that episode is owner-authoritative. It excludes proposal source, owner rank, candidate index, insertion order, and numerical activation strength.

A deterministic key combines persistent organism basis, analysis-only context_election:v1 namespace, authoritative election-event identity, and canonical context identity. Restart/migration must preserve basis plus owner event/episode identifiers. This reuses only CLOSE-02Z infrastructure principles, never its candidate namespace, candidate identity, Gaussian distribution, or sigma.""")
 j(root,"AS003G_INCUMBENT_PERSISTENCE_CONTRACT.json",{"schema":"AS003G_INCUMBENT_PERSISTENCE_CONTRACT_V1","generated_at":stamp(),"result":"CATEGORICAL_PERSISTENCE_SUPPORTED_AFTER_VALID_ELECTION","rule":"Engaged context retains control while source-neutrally identified, owner ACTIVE, and no hard interruption/end event occurs.","end_events":["owner completion","owner deactivation/withdrawal","verified blockage","hard safety/recovery/Governance/Embodiment interruption"],"not_a_rule":["incumbent bonus","switch penalty","dwell coefficient","preemption solely because rival ACTIVE"],"limit":"Does not solve C1 or C3 for continuously active rivals.","integrity":integ()})
 j(root,"AS003G_CONTEXT_EPISODE_AUDIT.json",{"schema":"AS003G_CONTEXT_EPISODE_AUDIT_V1","generated_at":stamp(),"owner_episode_boundaries":{"development":["goal completion","invalidity/readiness withdrawal","verified revision"],"temporal":["window completion/pass","status/version revision"],"habit":["procedure completion","invalid binding","verified denial"],"social":["partner/context disappearance","owner context change","verified completion/denial"],"memory":["recall ends","item invalidation"],"physiology":["hard recovery external; non-hard categorical episode unestablished"],"individuality":["no established lifecycle"]},"finding":"Owner-end events are real re-election boundaries but do not guarantee one while incumbent and rival continue ACTIVE.","no_artificial_episode_rule":"Elapsed ticks are prohibited timeout disguised as episode.","integrity":integ()})
 j(root,"AS003G_TEMPORAL_CONTROL_CLAIM_AUDIT.json",{"schema":"AS003G_TEMPORAL_CONTROL_CLAIM_AUDIT_V1","generated_at":stamp(),"continuous_activation_age":{"unit":"authoritative organism tick","result":"SCHEDULER_SEMANTICS_REJECTED","reason":"Oldest does not have cross-owner behavioral entitlement; oldest-first is fairness and can starve late arrivals."},"time_since_verified_expression":{"unit":"authoritative organism tick","result":"SCHEDULER_SEMANTICS_REJECTED","reason":"Unserved duration guarantees rotation but does not identify organismal control now."},"verified_service":{"result":"OWNER_LOCAL_ATTRIBUTION_NOT_COMMON_SWITCH_SEMANTIC","reason":"Verified outcomes are valid but no common rule says serviced active context yields."},"active_set_change":{"result":"RECONSIDER_NOT_PREEMPT","reason":"Arrival/departure is revalidation boundary, not right to dethrone incumbent."},"integrity":integ()})
 j(root,"AS003G_CLOSE02Z_REUSE_BOUNDARY.json",{"schema":"AS003G_CLOSE02Z_REUSE_BOUNDARY_V1","generated_at":stamp(),"reusable_infrastructure_only":["persistent organism basis","semantic-key hashing","source neutrality","restart/migration reproducibility","pool permutation stability"],"not_reusable_without_new_authority":["ordinary candidate namespace","candidate behavioral identity","Gaussian distribution","candidate sigma 0.08","per-tick candidate semantics","context engagement/switching authority"],"static_evidence":{k:S[k] for k in ("candidate_namespace","candidate_sigma","source_neutral_identity")},"conclusion":"Residual ordering of genuinely unordered finite context set is scale-free; any random value/probability interacting with evidence requires calibration.","integrity":integ()})
 md(root,"AS003G_PERSISTENT_CONTEXT_STATE_ANALYSIS.md","""# PERSISTENT_CONTEXT_STATE_V0 analysis

1. Owners expose categorical ACTIVE/INACTIVE; UNKNOWN stays evidence quality.
2. Unique qualified deferral context would elect categorically; genuinely unordered no-incumbent contexts could use event-keyed source-neutral ordering.
3. Valid engagement persists without numeric bonus.
4. Completion, deactivation, verified blockage, hard interruption, and real owner episode ends release engagement; active-set changes reconsider but do not preempt.
5. Candidate authority and Governance/Embodiment/VerifiedOutcome remain downstream.

Incomplete: no common non-hard deferral fact is established. A continuously active incumbent/rival pair may never get another election event. A spontaneous switch requires hazard/dynamics, prohibited and uncalibrated as a free parameter.""")
 fs=["physiology+social","physiology+temporal","physiology+development","habit+social","temporal+development","memory+development","incumbent+newly_activated_rival"]
 j(root,"AS003G_STARVATION_PROOFS.json",{"schema":"AS003G_STARVATION_PROOFS_V1","generated_at":stamp(),"proof_model":"Static logical fixtures only; no candidate or organism execution.","fixtures":{x:{"event_gated_persistence":"STARVATION_POSSIBLE if incumbent/rival remain ACTIVE and no owner-end/hard/qualified-deferral event occurs.","initial_only_stochastic":"STARVATION_POSSIBLE after initial election for unselected continuing rival.","age_or_unserved_time":"REJECTED scheduler fairness, not organism control."} for x in fs},"conclusion":"No parameter-free nonnumeric candidate proves eventual control for continuously active rival; no timeout remedy.","integrity":integ()})
 j(root,"AS003G_THRASHING_PROOFS.json",{"schema":"AS003G_THRASHING_PROOFS_V1","generated_at":stamp(),"per_tick_stochastic_reelection":"REJECTED: randomness becomes ordinary motivational authority and permits every-tick switching.","event_gated_reelection":"BOUNDED: only valid initial/owner-end/hard/qualified episode events.","active_set_change":"RECONSIDER_ONLY: automatic replacement on arrival is unjustified preemption.","persistence":"SUPPORTED after valid election but not starvation cure.","integrity":integ()})
 j(root,"AS003G_STOCHASTIC_AUTHORITY_ANALYSIS.json",{"schema":"AS003G_STOCHASTIC_AUTHORITY_ANALYSIS_V1","generated_at":stamp(),"frozen_corpus":{"zero_context":C["zero_active_contexts"],"single_context":C["one_active_context"],"multiple_context":C["multiple_active_contexts"],"coactivation":C["owner_pair_coactivation_counts"]},"classification":{"single_context":"NO_ELECTION_NEEDED","hard_preemption":"EXTERNAL_HARD_AUTHORITY","incumbent_persistence":"SOURCE_NEUTRAL_IDENTITY_NOT_RETAINED","unordered_initial":"CONDITIONALLY_ACCEPTABLE_EVENT_KEYED_RESIDUAL_ONLY","spontaneous_switch":"REQUIRES_CALIBRATED_HAZARD_OR_COMMON_DYNAMICS"},"finding":"Five coactivations cannot estimate global stochastic-authority fraction; expose need but neither globally support nor reject residual ties.","disposition":"Initial tie ordering can be scale-free after categorical exhaustion. Stochastic transition over time is not parameter-free.","integrity":integ()})
 md(root,"AS003G_NONPHYSIOLOGY_CAUSALITY_REVIEW.md","""# AS-003G non-physiology causal coverage

Temporal views establish owner-local preparation relevance; routines need eligible bounded bindings; development persists selected valid goal; social contexts need policy-visible partner/cue; memory specifies recalled relations; opportunity enables but cannot self-promote; SelfModel/WorldModel retain one-step consequence and selected-only learning. Individuality remains bounded variation, not proven independent activation.

No role gains owner-independent right to displace another continuing active context. Rotation is scheduler fairness and is rejected.""")
 md(root,"AS003G_COMMON_CONTROL_CLAIM_REQUIREMENTS.md","""# AS-003G common behavioral-control claim requirements

No common claim is established. Missing proposition: among simultaneous non-hard contexts, what owner-independent organism fact changes tendency to gain or retain behavioral control?

A future claim needs one cross-system meaning; units if any; constitutional/learned provenance; verified-outcome calibration; UNKNOWN and first-experience behavior; persistence/hard-interruption interaction; source-neutral identity; restart/migration state; boundedness; and a proof it is not utility. It cannot be weights, rank, timeout, unserved queue, or fixed hazard.

Richman-style spontaneous transition requires explicit calibrated hazard/dynamics. UMBRA lacks it.""")
 md(root,"AS003G_PRIOR_ART_BOUNDARY.md","""# AS-003G prior-art boundary

Richman et al. (2023) observed persistent hungry/thirsty choice bouts with stochastic transitions; previous choice strongly predicted while relative needs modulated switching. The model uses need-shaped landscapes and fitted relative-scale, gradient, and noise parameters. [Nature](https://www.nature.com/articles/s41586-023-06715-z)

Palmer and Kristan, Burnett et al., Cisek, and Faulkes are reference-only support for context sensitivity, rival motivations, parallel action, and persistence/switching distinction.

Adopted: persistent context and event-sensitive reconsideration are plausible. Rejected: landscape, relative-need scale, fitted coefficients, diffusion equation, neural simulation, RL, active inference, POMDP/MPC, planner, utility, source priority, hierarchy.""")
 md(root,"AS003G_ARCHITECTURE_CANDIDATES.md","""# AS-003G architecture candidates

## A -- categorical persistence plus event-gated stochastic election

Initial election uses source-neutral event-keyed residual ordering only for genuinely unordered contexts; engagement persists; owner-end/hard events reelect. Incomplete: continuing rival starvation possible.

## B -- A plus common categorical deferral

Uniquely deferral-constrained context can trigger reconsideration; residual ties stay event-keyed. Incomplete: no common non-hard deferral semantics cover protected owners.

## C -- common behavioral-control claim with calibrated switching

Not supported as contract. Exact future boundary: define common tendency/dynamics, unit, calibration, owner provenance, persistence interaction, and no utility/weights.""")
 md(root,"AS003G_REPLACEMENT_CONTRACT.md","""# AS-003G replacement-contract disposition

No implementation-ready contract is supported. Activation, identity, lifecycle release, hard interruption, persistence, and event-keyed residual ordering are bounded but cannot lawfully switch a continuing incumbent/rival pair.

Closest qualitative architecture is persistent stochastic goal state, but spontaneous switching requires calibrated hazard/noise or other common dynamics. CLOSE-02Z sigma cannot transfer; activation age and unserved duration are scheduler semantics. Future work must define, not implement, common behavioral-control / transition-calibration primitive.""")
 j(root,"AS003G_VERDICT.json",{"schema":"AS003G_VERDICT_V1","generated_at":stamp(),"primary_verdict":"AS003G_STOCHASTIC_SWITCH_CALIBRATION_PRIMITIVE_REQUIRED","verdict_basis":["Categorical activation and persistence supported only after valid election.","No common non-hard deferral/preemption state across protected owners.","Activation age and time since service are scheduler fairness, not organism control.","Event-gated residual initial election scale-free but cannot switch continuous incumbent/rival.","Spontaneous stochastic switching requires calibrated hazard/noise/gradient or common dynamics; none established."],"explicit_dispositions":{"stochastic_initial_election":"CONDITIONALLY_ACCEPTABLE_EVENT_GATED_SOURCE_NEUTRAL_RESIDUAL_ONLY","incumbent_persistence":"ACCEPTABLE_AFTER_VALID_ELECTION","switching":"OWNER_END_OR_HARD_EVENTS_INSUFFICIENT_FOR_CONTINUOUS_RIVALS","starvation":"REMAINS_POSSIBLE_WITHOUT_NEW_SWITCH_SEMANTICS","spontaneous_transitions":"REQUIRE_UNESTABLISHED_CALIBRATION","common_control_claim":"NOT_ESTABLISHED; REQUIRED_IF_SHARED_NON_EVENT_DYNAMICS_PURSUED"},"v1_status":"SUPPORTED_DOMINANCE_DISTRIBUTED_COMPETITION_V1_REMAINS_RETIRED","recommendation":None,"integrity":integ()})
def manifest(root,commit):
 miss=[x for x in REQ if not (root/x).is_file()]
 if miss: raise RuntimeError("missing:"+",".join(miss))
 h={x:sha(root/x) for x in REQ}
 j(root,"AS003G_EVIDENCE_MANIFEST.json",{"schema":"AS003G_FINAL_EVIDENCE_MANIFEST_V1","generated_at":stamp(),"baseline":BASE,"closeout_evidence_commit":commit,"durability":"file fsync, atomic rename, directory fsync, readback SHA-256","required_file_count":len(REQ),"required_files":h,"integrity":integ()})
 if load(root/"AS003G_EVIDENCE_MANIFEST.json")["required_files"]!=h: raise RuntimeError("manifest_readback_mismatch")
p=argparse.ArgumentParser(); p.add_argument("--root",type=Path,default=ROOT); p.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument("--lock",action="store_true"); p.add_argument("--analyze",action="store_true"); p.add_argument("--manifest",action="store_true"); p.add_argument("--governance-commit"); p.add_argument("--closeout-evidence-commit"); a=p.parse_args()
if sum((a.lock,a.analyze,a.manifest))!=1: raise SystemExit("choose exactly one action")
if a.lock:
 if not a.governance_commit: raise SystemExit("governance commit required")
 lock(a.root,a.repo,a.governance_commit)
elif a.analyze: analyze(a.root,a.repo)
else:
 if not a.closeout_evidence_commit: raise SystemExit("closeout evidence commit required")
 manifest(a.root,a.closeout_evidence_commit)

