#!/usr/bin/env python3
"""AS-003I durable, zero-run motivational-control semantics evidence writer."""
from __future__ import annotations

import argparse, hashlib, json, os
from datetime import UTC, datetime
from pathlib import Path

BASE = "55f488585c1fc694953023ba12a961970eaa20a0"
ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003i-behavioral-control-salience-r1")
PARENT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003h-switching-calibration-r1")
PARENT_SHA = "2c158c780faeba4745ad29b02891fcd05fbfa5a67db1ce2be87088566a18d713"
FROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003f-motivational-context-contract-r1")
HIST = {"AS003G":"ff78082a8982da6c11a2c403887c313dbd470f2cf24fbc9f8d1cbd3abaaead3e","AS003F":"2340788c8d1e2c19e2161831fdb6c1611f2aa6a85bd64afc77363971ff42c9dc","AS003E":"58c8cbcf4feb956cf52b936bc2b436494074a884bf0e2875326b00460efa47f7","AS003D":"b2a606286f6e197d100298e3e1d73031b1d302e0cccaacd0a9b3da2a9811cbfe","AS003C":"d8eb4cc26048f6b3b8d9ca861dbfab25f56a6e2b95548949997c638f7812268c"}
REQ = ("AS003I_PARENT_BOUNDARY_RECOVERY.json","AS003I_ARCHITECTURE_FAMILY_LOCK.json","AS003I_COMMON_SEMANTIC_AUDIT.json","AS003I_FINAL_COMMON_PATH_ARCHITECTURE.md","AS003I_CONTROL_OWNER_INVENTORY.json","AS003I_OWNER_LOCAL_VS_COMMON_CONTROL.json","AS003I_CONSTITUTIONAL_LEARNED_FACTOR_MAP.json","AS003I_DYNAMIC_SALIENCE_AUDIT.json","AS003I_FIRST_EXPERIENCE_CONTRACT.md","AS003I_AFFECTIVE_CURRENCY_AUDIT.md","AS003I_SUBJECTIVE_VALUE_BOUNDARY.md","AS003I_CALIBRATION_SEMANTICS.json","AS003I_COMMON_ANCHOR_AUDIT.json","AS003I_CONSTITUTIONAL_CALIBRATION_AUDIT.json","AS003I_VERIFIED_SALIENCE_LEARNING_CONTRACT.md","AS003I_CROSS_OWNER_CALIBRATION_AUDIT.json","AS003I_CONTROL_SWITCHING_CONTRACT.md","AS003I_NONPHYSIOLOGY_GENERALITY.md","AS003I_FROZEN_CORPUS_PROJECTION.json","AS003I_PRIOR_ART_BOUNDARY.md","AS003I_ARCHITECTURE_CANDIDATES.md","AS003I_REPLACEMENT_CONTRACT.md","AS003I_VERDICT.json")

def now(): return datetime.now(UTC).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def integ(): return {"production_changes":0,"test_changes":0,"organism_runs":0,"diagnostic_reruns":0,"retries":0,"reseeds":0}
def put(p,s):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(f".{p.name}.tmp-{os.getpid()}")
    with t.open("w",encoding="utf-8",newline="\n") as h: h.write(s); h.flush(); os.fsync(h.fileno())
    os.replace(t,p); d=os.open(p.parent,os.O_DIRECTORY)
    try: os.fsync(d)
    finally: os.close(d)
    if not p.read_bytes(): raise RuntimeError("empty_readback:"+p.name)
def j(n,v): put(ROOT/n,json.dumps(v,indent=2,sort_keys=True)+"\n")
def md(n,v): put(ROOT/n,v.strip()+"\n")
def facts(repo):
    probes={"physiology_urgency":("umbra_core/physiology.py","def vector_urgency"),"temporal_views":("umbra_core/temporal/engine.py","def build_policy_expectation_views"),"development_goal":("umbra_core/development/engine.py","active_goal_id: str | None = None"),"routine_proposal":("umbra_core/memory/engine.py","def routine_soft_proposals"),"verified_world_learning":("umbra_core/world_model/engine.py","Never treat prediction as fact."),"hard_boundary":("umbra_core/arbitration.py","def _introduces_critical_boundary"),"candidate_noise":("umbra_core/stochastic_competition.py","CANDIDATE_NOISE_SIGMA = 0.08")}
    out={}
    for k,(f,t) in probes.items():
        if t not in (repo/f).read_text(): raise RuntimeError("source_missing:"+k)
        out[k]={"path":f,"token":t,"present":True}
    return out

def lock(repo,start):
    if sha(PARENT/"AS003H_EVIDENCE_MANIFEST.json")!=PARENT_SHA: raise RuntimeError("as003h_manifest_mismatch")
    parent=json.loads((PARENT/"AS003H_VERDICT.json").read_text())
    recovery={"schema":"AS003I_PARENT_BOUNDARY_RECOVERY_V1","generated_at":now(),"baseline":BASE,"governance_start_commit":start,"parent":{"verdict":parent["primary_verdict"],"manifest_sha256":PARENT_SHA},"recovered":{"activation":"owner-derived categorical ACTIVE/INACTIVE only; UNKNOWN remains evidence quality","identity":"source-neutral semantic context identity; proposal provenance never grants authority","initial_election":"scale-free event-keyed residual only among genuinely unordered contexts","persistence":"categorical after valid engagement","release":"completion/deactivation/verified blockage and hard interruption","starvation":"continuous active incumbent/rival cannot be resolved by persistence","rejected":"self-generated hazard learning, arbitrary hazard/timeouts, activation-age/unserved fairness, CLOSE-02Z sigma reuse"},"gap":"one current, source-neutral cross-owner proposition by which active non-hard contexts can bid to gain/retain/relinquish behavioral final-path access","integrity":integ()}
    j("AS003I_PARENT_BOUNDARY_RECOVERY.json",recovery)
    families={"schema":"AS003I_ARCHITECTURE_FAMILY_LOCK_V1","locked_at":now(),"parent_recovery_sha256":sha(ROOT/"AS003I_PARENT_BOUNDARY_RECOVERY.json"),"families":{"C1_motivational_salience":{"meaning":"current source-neutral bid for mutually exclusive behavioral final-path access","role":"leading hypothesis","forbidden":"utility/reward/source priority"},"C2_dynamic_incentive_salience":{"meaning":"current owner state modulates independently learned association/opportunity in a control bid","role":"leading hypothesis specialization","forbidden":"Pavlovian-only import or Zhang/Berridge coefficients"},"C3_affective_currency":{"meaning":"transient hedonic/valence claim mediates conflict","role":"serious comparator","forbidden":"pleasure maximization or affection score"},"C4_subjective_value":{"meaning":"scalar evaluated outcome value maximized across options","role":"negative control","forbidden":"global expected utility/reward"}},"no_fifth_family":"No architecture family may be added after projection.","integrity":integ()}
    j("AS003I_ARCHITECTURE_FAMILY_LOCK.json",families)
    semantic={"schema":"AS003I_COMMON_SEMANTIC_AUDIT_V1","locked_at":now(),"family_lock_sha256":sha(ROOT/"AS003I_ARCHITECTURE_FAMILY_LOCK.json"),"C1":{"proposition":"current claim for exclusive behavioral access","same_across_owners":True,"larger":"stronger current entitlement to win/retain non-hard context control","equal":"no semantic fact distinguishes claims; residual tie only","zero":"no present non-hard access claim, not owner inexistence","unknown":"claim support unavailable; must not suppress first experience","negative":"not meaningful; deactivation is categorical","location":"owner-state × current policy-visible context/opportunity × separately provenanced association","pre_candidate":True,"requires_opportunity":"claim can exist without an executable candidate; expression requires admissible candidate","recomputed":"at authoritative state/opportunity events, not persisted as reward"},"C2":{"result":"SEMANTICALLY_COMPATIBLE_ONLY_IF_SAME_C1_PROPOSITION","constraint":"state and learned association remain separate; no common operation/coefficient is assumed"},"C3":{"result":"SEMANTIC_UNRESOLVED","risk":"hedonic intensity becomes global reward"},"C4":{"result":"NEGATIVE_CONTROL_GLOBAL_UTILITY"},"lock_conclusion":"C1 provides one provisional cross-owner *meaning*, but no owner-to-claim mapping/calibration is locked.","integrity":integ()}
    j("AS003I_COMMON_SEMANTIC_AUDIT.json",semantic)

def analyze(repo):
    for p in ("AS003I_PARENT_BOUNDARY_RECOVERY.json","AS003I_ARCHITECTURE_FAMILY_LOCK.json","AS003I_COMMON_SEMANTIC_AUDIT.json"):
        if not (ROOT/p).is_file(): raise RuntimeError("missing_lock:"+p)
    static=facts(repo); inv=json.loads((FROOT/"AS003F_CONTEXT_OWNER_INVENTORY.json").read_text())["owners"]
    owners={k:{"authority":v["owner"],"activation":v["evidence_inputs"],"deactivation":v["satisfaction_deactivation"],"candidate_role":v["candidate_implications"],"learning":v["learning"],"classification":("OWNER" if k not in {"environment_opportunity","engaged_behavioral_context","individuality"} else "CONTEXT_OR_STATE_NOT_NEW_OWNER")} for k,v in inv.items()}
    j("AS003I_CONTROL_OWNER_INVENTORY.json",{"schema":"AS003I_CONTROL_OWNER_INVENTORY_V1","generated_at":now(),"owners":owners,"finding":"Opportunity enables expression but is not an owner; engagement is state; individuality lacks qualified ACTIVE lifecycle and cannot be added to repair calibration.","integrity":integ()})
    local={"physiology":"vector urgency is owner-local regulation magnitude; requires an independently grounded translation from current regulatory condition to shared access claim, not normalization.","temporal":"ACTIVE/window/version establishes temporal relevance; requires a common meaning for present access demand, not time-until-window-expiry scalar.","habit_routine":"eligibility/procedure state is categorical/local; requires an access-demand semantic independent of execution frequency.","development_practice":"readiness/risk/learning-progress score is existing internal selector heuristic, not qualified cross-owner currency.","relationship_social":"partner/context/relation evidence is owner-local; no affection scalar may stand in for access claim.","memory_recall":"retrieval/provenance can specify context but memory is not automatically a controlling owner.","environment_opportunity":"affordance is enabling condition, never self-promoting motivation."}
    j("AS003I_OWNER_LOCAL_VS_COMMON_CONTROL.json",{"schema":"AS003I_OWNER_LOCAL_VS_COMMON_CONTROL_V1","generated_at":now(),"owner_local_magnitudes":local,"normalization_test":{"min_max":"REJECTED","z_score":"REJECTED","percentile":"REJECTED","per_owner_unit_interval":"REJECTED","softmax_rank":"REJECTED","reason":"Comparable ranges do not create one behavioral-control proposition."},"result":"NO_EXISTING_OWNER_MAGNITUDE_IS_A_COMMON_CLAIM","integrity":integ()})
    factors={"physiology":{"constitutional":"authoritative state/critical hard boundary","learned":"verified body/world action effects; cannot rewrite physiology","result":"association-modulated expression plausible; common mapping uncalibrated"},"temporal":{"constitutional":"ACTIVE status/window/version","learned":"verified recurrence/context reliability","result":"common mapping uncalibrated"},"habit":{"constitutional":"bounded eligible procedure state","learned":"selected verified routine outcomes","result":"common mapping uncalibrated"},"development":{"constitutional":"stage/readiness/goal validity","learned":"selected verified competence/progress","result":"existing internal score cannot be exported"},"social":{"constitutional":"policy-visible partner/context","learned":"verified relationship/routine association","result":"common mapping uncalibrated"},"memory":{"constitutional":"working/retrieval state","learned":"verified episodic/procedural facts","result":"not independently qualified as control owner"}}
    j("AS003I_CONSTITUTIONAL_LEARNED_FACTOR_MAP.json",{"schema":"AS003I_CONSTITUTIONAL_LEARNED_FACTOR_MAP_V1","generated_at":now(),"factors":factors,"separation":"current state cannot rewrite association; associations cannot write physiology/activation; downstream proposal provenance cannot modify claim.","integrity":integ()})
    j("AS003I_DYNAMIC_SALIENCE_AUDIT.json",{"schema":"AS003I_DYNAMIC_SALIENCE_AUDIT_V1","generated_at":now(),"hypothesis":"current owner state × independently verified context/opportunity association can recompute a current C1 control claim","fixtures":{"physiology_known_recovery_cue":"PARTIAL: state and learned action effects exist; no common bid calibration","temporal_known_opportunity":"PARTIAL: expectation/reliability exist; no common bid calibration","social_familiar_partner":"PARTIAL: cues/relations exist; no common bid calibration","habit_established_procedure":"PARTIAL: routine eligibility/outcomes exist; no common bid calibration","development_practice":"PARTIAL: state/competence exist, but existing score is not exportable","novel_opportunity":"UNKNOWN_PRESERVED: no association cannot equal zero claim"},"result":"SEMANTICALLY_PLAUSIBLE_BUT_NOT_CALIBRATED_ACROSS_OWNERS","integrity":integ()})
    md("AS003I_FINAL_COMMON_PATH_ARCHITECTURE.md","""# Final common path architecture audit

The missing claim must attach first to a motivational **context**, not an action candidate: contexts contend for temporary access to the mutually exclusive behavioral final path; an engaged context may then specify existing candidates, which remain subject to one-step consequence selection, hard safety, Governance, Embodiment, and VerifiedOutcome. Candidate salience cannot substitute for context election because it would flatten source/context identity back into a candidate utility.

Context claim and candidate admissibility are therefore distinct. An opportunity may enable a candidate and modulate a context's present expression, but does not acquire control authority by itself.
""")
    md("AS003I_FIRST_EXPERIENCE_CONTRACT.md","""# First-experience boundary

No verified association must not equal zero control claim. ACTIVE owner state, policy-visible novel opportunity, constitutional owner semantics, and scale-free residual election among genuinely equal/unresolved claims may preserve first expression. This establishes availability only; it does not calibrate a cross-owner claim. A learned association may later modulate expression after selected VerifiedOutcome, but cannot be the sole bootstrap.
""")
    md("AS003I_AFFECTIVE_CURRENCY_AUDIT.md","""# Affective currency audit

Cabanac-style alliesthesia establishes a serious contrast: internal state can change a stimulus's hedonic effect, and pleasure/displeasure has been proposed as a common currency. In UMBRA, adding `AFFECTIVE_VALENCE` now would require assigning every protected owner a common hedonic meaning and would select behavior by maximizing that scalar. No qualified affective substrate, independently calibrated valence anchors, or non-utility control rule exists. Relationship state must not become an affection score. **Result: not required/supported; it would prematurely recreate global utility.**
""")
    md("AS003I_SUBJECTIVE_VALUE_BOUNDARY.md","""# Subjective-value negative control

`all context factors -> scalar subjective value -> choose maximum` has a common scale only by aggregating heterogeneous owner inputs, needs relative weights or learned reward authority, and selects the maximum evaluated outcome. This is materially the historical scorer/global utility architecture under a better name.

**Classification: `SUBJECTIVE_VALUE_GLOBAL_UTILITY_REJECTED`.**
""")
    j("AS003I_CALIBRATION_SEMANTICS.json",{"schema":"AS003I_CALIBRATION_SEMANTICS_V1","generated_at":now(),"C1_unit":"one current source-neutral bid for access to mutually exclusive non-hard behavioral control","ranking":"Only meaningful after every owner maps to the same proposition; rank alone is not a calibration method.","absolute_magnitude":"Needed only if it has shared behavioral anchor; none currently established.","retention_switching":"Would use same claim; rival overtakes only on a meaningful recomputed claim, equality uses categorical engagement/residual tie.","margin_hysteresis":"NOT_AUTHORIZED: no independent threshold prevents thrashing.","result":"SEMANTIC_DEFINED_CALIBRATION_MISSING","integrity":integ()})
    anchors={"zero":"same C1 meaning only if no active present access claim; current owner activation thresholds are not equivalent","activation":"REJECTED false calibration: owner-specific ACTIVE boundaries differ","deactivation_completion":"valid categorical release, not a common numeric anchor","hard_boundary":"external authority, not non-hard scale anchor","verified_expression":"owner-local outcome, not common access magnitude","maximum_observed":"REJECTED post-hoc/range normalization"}
    j("AS003I_COMMON_ANCHOR_AUDIT.json",{"schema":"AS003I_COMMON_ANCHOR_AUDIT_V1","generated_at":now(),"anchors":anchors,"result":"NO_COMMON_NUMERIC_ANCHOR_ESTABLISHED","integrity":integ()})
    j("AS003I_CONSTITUTIONAL_CALIBRATION_AUDIT.json",{"schema":"AS003I_CONSTITUTIONAL_CALIBRATION_AUDIT_V1","generated_at":now(),"mappings":{"physiology_urgency_to_claim":"EVIDENCE_INSUFFICIENT","temporal_window_to_claim":"EVIDENCE_INSUFFICIENT","routine_eligibility_to_claim":"EVIDENCE_INSUFFICIENT","development_score_to_claim":"ARBITRARY_OWNER_WEIGHT_IF_EXPORTED","social_relation_to_claim":"EVIDENCE_INSUFFICIENT","uniform_owner_constant":"ARBITRARY_OWNER_WEIGHT"},"conclusion":"No existing constitutional semantic derives relative owner calibration; no AS-003C outcome fitting allowed.","integrity":integ()})
    md("AS003I_VERIFIED_SALIENCE_LEARNING_CONTRACT.md","""# Verified salience-learning boundary

Selected VerifiedOutcome may update cue-to-consequence, action-to-owner-progress, opportunity reliability, body executability, and completion associations. It may not train from action/context win frequency, prior salience output, unexecuted alternatives, or counterfactual better/worse claims.

These associations can remain owner/provenance-specific and modulate a future context's expression. They supply no verified label that one owner should have had **more** behavioral access than another at the same time. Cross-owner calibration is therefore not learned by this contract.
""")
    j("AS003I_CROSS_OWNER_CALIBRATION_AUDIT.json",{"schema":"AS003I_CROSS_OWNER_CALIBRATION_AUDIT_V1","generated_at":now(),"question":"What verified event says social should exert more/less control than temporal or physiology in the same state?","answer":"NONE_RETAINED_OR_CURRENTLY_QUALIFIED","owner_local_learning":"SUPPORTED_FOR_ASSOCIATIONS_AND_LIFECYCLE_ONLY","relative_learning":"REJECTED: requires controller wins, counterfactual comparison, or authored common outcome/reward","constitutional_mapping":"REQUIRED_BUT_NOT_DERIVED","result":"CROSS_OWNER_SALIENCE_CALIBRATION_PRIMITIVE_REQUIRED","integrity":integ()})
    md("AS003I_CONTROL_SWITCHING_CONTRACT.md","""# Control switching contract audit

If a calibrated C1 claim existed, initial election could choose the uniquely higher supported claim; categorical engagement could retain exact ties; a rival could legitimately overtake on a meaningful recomputed higher claim; completion/deactivation/blockage releases; hard authority interrupts; source-neutral scale-free ordering only resolves genuine equality/unresolved initial ties.

No numerical hysteresis, margin, or per-tick hazard is authorized. Because calibration is missing, the above is a semantic requirement, not an implementable switching rule. Thrashing/noise cannot be solved by inventing a band, and starvation cannot be ruled out with uncalibrated claims.
""")
    md("AS003I_NONPHYSIOLOGY_GENERALITY.md","""# Non-physiology generality

Temporal, habit, development, social, and memory-related contexts have valid local state/association/lifecycle semantics. None has a defensible current mapping into the C1 common bid. Physiology is best instrumented, but this cannot make its urgency the de facto universal currency; critical physiology stays external hard authority. Environmental opportunity remains an expression condition rather than a motivation owner.

Consequently, a physiology-only salience architecture is rejected as insufficient; non-physiology participation is semantically plausible but presently uncalibratable.
""")
    j("AS003I_FROZEN_CORPUS_PROJECTION.json",{"schema":"AS003I_FROZEN_CORPUS_PROJECTION_V1","generated_at":now(),"prerequisite_locks":{"family":sha(ROOT/"AS003I_ARCHITECTURE_FAMILY_LOCK.json"),"semantic":sha(ROOT/"AS003I_COMMON_SEMANTIC_AUDIT.json")},"retained_context_counts":{"zero":327,"single":2315,"multiple":5,"total":2647},"projection":{"claims_computable":0,"reason":"No locked owner-to-C1 calibration adapter exists; assigning values/normalizing would violate the lock.","initial_elections":"NOT_COMPUTABLE","incumbent_retention":"NOT_COMPUTABLE","rival_overtakes":"NOT_COMPUTABLE","residual_ties":"NOT_COMPUTABLE","physiology_dominance_rate":"NOT_COMPUTABLE","nonphysiology_control_episodes":"NOT_COMPUTABLE"},"observed_limits":"The five development+memory coactivations are insufficient to fit or validate owner mappings. V1/CLOSE-02Z choices are invalid selector output, not salience ground truth.","integrity":integ()})
    md("AS003I_PRIOR_ART_BOUNDARY.md","""# Prior-art boundary

Natural action-selection literature supports incompatible behavioral requests and a final common path, but does not provide a UMBRA equation or neural topology. Incentive-salience work distinguishes dynamic wanting from liking and cached learned value; current state plus learned associations can affect motivation, but its biological coefficients/Pavlovian neural mechanism are not imported. Cabanac's pleasure currency is a serious comparator but would require an unestablished affective substrate. Neuroeconomic subjective value illustrates the rejected scalar-maximization family.

Disposition: **REFERENCE ONLY**. No dopamine, basal-ganglia topology, Zhang/Berridge coefficient, reward value, expected utility, affective maximization, or controller is adopted.
""")
    md("AS003I_ARCHITECTURE_CANDIDATES.md","""# Architecture candidates

## A. Motivational salience control claim — semantically coherent, not calibrated

One value would mean current bid for exclusive behavioral access, not outcome goodness. It preserves owner state/association provenance and allows dynamic switching in principle. It fails implementation readiness because no protected-owner adapter has a non-arbitrary common calibration.

## B. Dynamic incentive-salience-like control — semantically coherent, not calibrated

Owner state × verified association is a plausible provenance pattern. It generalizes only at the semantic level; no common operation/anchor exists for physiology, temporal, habit, development, and social owners.

## C. Affective/valence currency — rejected now

Without an independent affective substrate it is pleasure/global utility under a new label.

Subjective value is the locked negative control and is rejected as global utility.
""")
    md("AS003I_REPLACEMENT_CONTRACT.md","""# Replacement-contract disposition

No implementation-ready salience contract is supported. AS-003I supports only the semantic form of a future `CURRENT_NONHARD_BEHAVIORAL_CONTROL_CLAIM`: a current source-neutral bid for access to mutually exclusive non-hard behavior, distinct from outcome value, reward, and hedonic liking.

The missing primitive is **cross-owner salience calibration**: independently justified adapter semantics and shared anchors that make a physiology, temporal, habit, development, and social bid mean the same thing without per-owner coefficients/normalization. It must preserve categorical activation, UNKNOWN/first experience, owner provenance, selected-only VerifiedOutcome learning, hard authority, bounded persistence, migration, and residual tie stochasticity.
""")
    j("AS003I_VERDICT.json",{"schema":"AS003I_VERDICT_V1","generated_at":now(),"primary_verdict":"AS003I_CROSS_OWNER_SALIENCE_CALIBRATION_PRIMITIVE_REQUIRED","recommendation":None,"v1_status":"SUPPORTED_DOMINANCE_DISTRIBUTED_COMPETITION_V1_REMAINS_RETIRED","basis":["C1 has one coherent semantic meaning: current non-hard behavioral-access bid.","No protected owner has an independently calibrated adapter into that common claim.","Normalization/ranking and constitutional constants would create false comparability or arbitrary owner weights.","Verified outcomes learn owner-local associations/lifecycle, not relative cross-owner access demand.","Subjective value/global utility and ungrounded affective currency are rejected."],"integrity":integ()})

def manifest():
    missing=[n for n in REQ if not (ROOT/n).is_file()]
    if missing: raise RuntimeError("missing:"+",".join(missing))
    m={"schema":"AS003I_EVIDENCE_MANIFEST_V1","generated_at":now(),"baseline":BASE,"parent_manifest_sha256":PARENT_SHA,"historical_manifest_sha256":HIST,"required_artifacts":{n:sha(ROOT/n) for n in REQ},"required_artifact_count":len(REQ),"integrity":integ(),"verdict":json.loads((ROOT/"AS003I_VERDICT.json").read_text())["primary_verdict"]}
    j("AS003I_EVIDENCE_MANIFEST.json",m)
def main():
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("lock","analyze","manifest"));p.add_argument("--repo",type=Path,required=True);p.add_argument("--start-commit",default="");a=p.parse_args()
    if a.mode=="lock":
        if not a.start_commit: raise SystemExit("--start-commit required")
        lock(a.repo,a.start_commit)
    elif a.mode=="analyze": analyze(a.repo)
    else: manifest()
if __name__=="__main__": main()
