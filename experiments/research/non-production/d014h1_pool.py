from __future__ import annotations
import hashlib,json
from copy import deepcopy
MAX_PROPOSALS=256
MAX_UNIQUE_CANDIDATES=128
DIMENSIONS=("energy","fatigue","integrity","stimulation")
SOURCE_NAMES=("base_arbitration","critical_recovery","manipulation","routine_habit","development","memory","social","world_model","temporal","individuality","dormant_capability","final_safety")
def canonical_bytes(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def fingerprint(v): return hashlib.sha256(canonical_bytes(v)).hexdigest()
def candidate_key(c): return fingerprint({"capability":c["capability"],"params":c["params"]})
def _finite(v): return isinstance(v,(int,float)) and not isinstance(v,bool) and v==v and abs(float(v))!=float("inf")
def _safe(v):
    if v is None or isinstance(v,(str,bool,int)): return
    if isinstance(v,float):
        if not _finite(v): raise ValueError("non_finite")
        return
    if isinstance(v,dict):
        for k,x in v.items():
            if not isinstance(k,str): raise ValueError("non_string_key")
            _safe(x)
        return
    if isinstance(v,list):
        for x in v: _safe(x)
        return
    raise ValueError("non_json_value")
def _score(c,state):
    branches=state.get("effect_branches",{}).get(c["capability"],[])
    phys=state.get("physiology",{}); drift=state.get("drift",{}); vals=[]
    for branch in branches:
        margins=[]
        for name in DIMENSIONS:
            item=phys.get(name,{})
            if not _finite(item.get("value")): continue
            after=float(item["value"])+float(branch.get("effect",{}).get(name,0))+float(drift.get(name,0))
            margins.append(-1.0 if after<float(item.get("critical_low",.05)) or after>float(item.get("critical_high",.95)) else 1.0)
        if margins: vals.append(min(margins))
    return min(vals) if vals else 0.0
def _normalize(raw,index):
    if not isinstance(raw,dict): raise ValueError("proposal_not_object")
    source,cap,params,ctx=raw.get("source_name"),raw.get("capability"),raw.get("params",{}),raw.get("policy_context",{})
    if source not in SOURCE_NAMES: raise ValueError("unknown_source")
    if not isinstance(cap,str) or not cap: raise ValueError("capability")
    if not isinstance(params,dict) or not isinstance(ctx,dict): raise ValueError("params_or_context")
    if ctx.get("policy_visible") is not True: raise ValueError("not_policy_visible")
    _safe(params); _safe(ctx)
    prov=ctx.get("provenance",[]); refs=ctx.get("evidence_refs",[])
    if not isinstance(prov,list) or not all(isinstance(x,str) and x for x in prov): raise ValueError("provenance")
    if not isinstance(refs,list) or not all(isinstance(x,str) and x for x in refs): raise ValueError("evidence_refs")
    support=ctx.get("native_support",0.0); support=float(support) if _finite(support) else 0.0
    c={"source_name":source,"source_index":index,"capability":cap,"params":deepcopy(params),"policy_context":deepcopy(ctx),"provenance":sorted(set(prov)),"evidence_refs":sorted(set(refs)),"native_support":max(-1,min(1,support))}
    c["candidate_key"]=candidate_key(c); return c
def _merge(group):
    first=min(group,key=lambda x:(x["source_index"],x["source_name"]))
    return {"candidate_key":first["candidate_key"],"capability":first["capability"],"params":deepcopy(first["params"]),"provenance":sorted({p for x in group for p in x["provenance"]}),"evidence_refs":sorted({e for x in group for e in x["evidence_refs"]}),"source_names":sorted({x["source_name"] for x in group}),"native_support":max(x["native_support"] for x in group),"duplicate_count":len(group)}
def evaluate(state):
    proposals=state.get("proposals",[])
    if len(proposals)>MAX_PROPOSALS: return {"status":"OVERFLOW","overflow":"proposal_count","selected":None}
    emissions=[{"index":i,"raw":deepcopy(x)} for i,x in enumerate(proposals)]
    normalized=[]; rejected=[]
    for i,x in enumerate(proposals):
        try: normalized.append(_normalize(x,i))
        except ValueError as e: rejected.append({"index":i,"reason":str(e)})
    groups={}
    for x in normalized: groups.setdefault(x["candidate_key"],[]).append(x)
    if len(groups)>MAX_UNIQUE_CANDIDATES: return {"status":"OVERFLOW","overflow":"unique_candidate_count","selected":None,"source_emissions":emissions,"normalized":normalized,"rejected":rejected}
    dedup=[]; candidates=[]
    for key in sorted(groups):
        c=_merge(groups[key]); comp={"physiology":_score(c,state),"native_support":c["native_support"],"source_identity_bonus":0.0}; c["score_components"]=comp; c["total_score"]=sum(comp.values())
        dedup.append({"candidate_key":key,"members":deepcopy(groups[key]),"merged":deepcopy(c)}); candidates.append(c)
    candidates.sort(key=lambda c:(-float(c["total_score"]),c["candidate_key"]))
    selected=candidates[0] if candidates else None
    return {"status":"SELECTED" if selected else "NO_SAFE_ACTION","source_emissions":emissions,"normalized_proposals":normalized,"rejected_proposals":rejected,"dedup_groups":dedup,"candidates":candidates,"selected":selected,"selection_iterations":[] if selected is None else [{"iteration":0,"candidate_key":selected["candidate_key"],"eligible":True}],"post_selection_replacement_count":0,"governance_lineage":None if selected is None else {"candidate_key":selected["candidate_key"],"source_names":selected["source_names"],"provenance":selected["provenance"]},"verified_outcome_lineage":None}
def current_production_fixture():
    phys={n:{"value":v,"critical_low":.05,"critical_high":.95} for n,v in (("energy",.7),("fatigue",.2),("integrity",.9),("stimulation",.4))}
    def p(s,c,params,support=0.0): return {"source_name":s,"capability":c,"params":params,"policy_context":{"policy_visible":True,"provenance":["CURRENT_OBSERVATION"],"evidence_refs":["fixture:"+s],"native_support":support}}
    return {"physiology":phys,"drift":{"energy":-.002,"fatigue":.002,"integrity":-.0002,"stimulation":-.002},"effect_branches":{"IDLE":[{"effect":{}}],"CHARGE":[{"effect":{"energy":.1}}],"APPROACH":[{"effect":{"energy":-.02,"fatigue":.01}}],"REST":[{"effect":{"fatigue":-.08}}],"INSPECT":[{"effect":{"stimulation":.04}}],"MOVE":[{"effect":{"energy":-.04,"fatigue":.02}}]},"proposals":[p("base_arbitration","IDLE",{}),p("critical_recovery","REST",{"toward":"rest"}),p("manipulation","MANIPULATE",{"kind":"USE"}),p("routine_habit","APPROACH",{"toward":"resource","step":1},.1),p("development","INSPECT",{"toward":"inspect"},.05),p("memory","APPROACH",{"toward":"resource","step":1},.2),p("social","INSPECT",{"toward":"partner"},.1),p("world_model","CHARGE",{"toward":"resource"},.3),p("temporal","WAIT",{"duration":1},.05),p("individuality","MOVE",{"step":1}),p("dormant_capability","IDLE",{}),p("final_safety","IDLE",{})]}
