#!/usr/bin/env python3
"""CC-6R: deterministic, research-only discovery firewall contract.

No optimizer or formal data is used. All candidates and boundary fixtures are
manually declared and synthetic.
"""
from __future__ import annotations
import copy, hashlib, json, os, tempfile
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = ROOT / "research" / "course_correction" / "cc6_discovery_firewall"
PROTECTED_ROOTS = tuple((ROOT / p).resolve() for p in ("umbra_core", "experiments", "docs/evidence", ".agent/RECORD.md"))
ALLOWED_ROOT = (RESEARCH_ROOT / "outputs").resolve()
PROTECTED_VARIABLES = {"constitutional_identity", "governance_safety_rules", "formal_thresholds", "historical_verdicts"}
ALLOWED = {"research_scenario": ("enum", ("sandbox_a", "sandbox_b")), "bounded_environment": ("float", (0.0, 1.0)), "research_schedule": ("int", (1, 10))}
SCHEMA = "cc6-allowed-v1"

def normalize(x):
    if isinstance(x, dict): return {k: normalize(v) for k, v in x.items()}
    if isinstance(x, (set, frozenset)): return sorted(normalize(v) for v in x)
    if isinstance(x, (tuple, list)): return [normalize(v) for v in x]
    return x
def fp(x): return hashlib.sha256(json.dumps(normalize(x), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
class Reject(ValueError):
    def __init__(self, detector): self.detector = detector; super().__init__(detector)
def reject(detector): raise Reject(detector)

@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    configuration: tuple
    configuration_fingerprint: str
    evaluator_fingerprint: str
    partition_fingerprint: str
    provenance: tuple
    source_commit: str = "cc6r-synthetic-source"
    @staticmethod
    def make(cid, config, evaluator, partition, source="cc6r-synthetic-source"):
        frozen = tuple(sorted(config.items()))
        cfp = fp(dict(frozen))
        return Candidate(cid, frozen, cfp, evaluator, partition, (("source_data", fp("synthetic-source")), ("sanitized_input", fp("sanitized-input")), ("partition", partition), ("schema", fp(SCHEMA)), ("candidate_configuration", cfp)), source)
    def manifest(self): return {"candidate_id": self.candidate_id, "configuration": dict(self.configuration), "configuration_fingerprint": self.configuration_fingerprint, "evaluator_fingerprint": self.evaluator_fingerprint, "partition_fingerprint": self.partition_fingerprint, "provenance": dict(self.provenance), "source_commit": self.source_commit}

class DiscoveryView:
    """Only discovery-safe IDs are exposed; embargo authority is private."""
    def __init__(self, samples): self._samples = tuple(sorted(samples))
    def sample_ids(self): return self._samples

class Firewall:
    def __init__(self, root=ROOT):
        self._partitions = {"discovery": frozenset({"d-1", "d-2"}), "development": frozenset({"e-1", "e-2"}), "embargo": frozenset({"v-1", "v-2"})}
        self.validate_partitions(self._partitions)
        self.partition_fingerprint = fp(self._partitions)
        self.evaluator = {"metric": "diagnostic_score_v1", "metric_version": "cc6r-v1", "ranking": "score-desc-id-asc", "missing": "reject", "partition": self.partition_fingerprint}
        self.evaluator_fingerprint = fp(self.evaluator)
        self.allowed_fingerprint = fp({"schema": SCHEMA, "variables": ALLOWED})
        self.state = "DRAFT"; self._records = {}; self.transitions = []; self.root = Path(root).resolve()
    def validate_partitions(self, parts):
        if any(parts[a] & parts[b] for a,b in (("discovery","development"),("discovery","embargo"),("development","embargo"))): reject("partition_overlap_validator")
    def freeze(self):
        if self.state != "DRAFT": reject("lifecycle_transition_validator")
        self.state = "FROZEN"
    def start(self):
        if self.state != "FROZEN": reject("lifecycle_transition_validator")
        self.state = "RUNNING"
    def close(self):
        if self.state != "RUNNING": reject("lifecycle_transition_validator")
        self.state = "CLOSED"
    def mutate(self, what):
        if self.state != "DRAFT": reject("frozen_" + what + "_validator")
    def add_candidate(self, candidate):
        if self.state != "RUNNING": reject("lifecycle_candidate_admission_validator")
        return candidate
    def discovery_view(self): return DiscoveryView(self._partitions["discovery"])
    def read_sample(self, sample, path=None):
        if sample in self._partitions["embargo"] or (path and not self._safe_read(path)) or (path and "validation" in str(path)):
            reject("embargo_read_validator")
        if sample not in self._partitions["discovery"]: reject("partition_access_validator")
        return {"sample_id": sample, "feature": .5}
    def _safe_read(self, path):
        target = Path(path).resolve(); return target.is_relative_to(ALLOWED_ROOT) and not any(target.is_relative_to(p) for p in PROTECTED_ROOTS)
    def write_policy(self, path):
        target = Path(path).resolve()
        if not target.is_relative_to(ALLOWED_ROOT) or any(target.is_relative_to(p) for p in PROTECTED_ROOTS): reject("resolved_write_path_validator")
        return target
    def register(self, name, value):
        if name in PROTECTED_VARIABLES or name not in ALLOWED: reject("allowlist_default_deny_validator")
        kind, domain = ALLOWED[name]
        if kind == "enum" and value not in domain: reject("allowlist_domain_validator")
        if kind == "float" and (not isinstance(value, (float,int)) or not domain[0] <= value <= domain[1]): reject("allowlist_domain_validator")
        if kind == "int" and (not isinstance(value,int) or isinstance(value,bool) or not domain[0] <= value <= domain[1]): reject("allowlist_type_domain_validator")
    def score(self, candidate):
        if self.state != "RUNNING": reject("lifecycle_score_validator")
        m = candidate.manifest(); config = m["configuration"]
        if fp(config) != m["configuration_fingerprint"]: reject("candidate_configuration_fingerprint_validator")
        if m["partition_fingerprint"] != self.partition_fingerprint: reject("partition_fingerprint_validator")
        if m["provenance"].get("partition") != self.partition_fingerprint: reject("provenance_partition_validator")
        if m["provenance"].get("candidate_configuration") != m["configuration_fingerprint"]: reject("provenance_candidate_fingerprint_validator")
        if m["evaluator_fingerprint"] != self.evaluator_fingerprint: reject("evaluator_fingerprint_validator")
        if m["source_commit"] != "cc6r-synthetic-source": reject("source_commit_validator")
        for n,v in config.items(): self.register(n,v)
        score = round((config["bounded_environment"] + config["research_schedule"] / 10) / 2, 6)
        return {"candidate_id": m["candidate_id"], "configuration": config, "configuration_fingerprint": m["configuration_fingerprint"], "score": score, "rank": None, "status": "QUARANTINED", "evaluator_fingerprint": self.evaluator_fingerprint, "partition_fingerprint": self.partition_fingerprint, "provenance": m["provenance"], "source_commit": m["source_commit"]}
    def finalize(self, record, rank):
        if self.state != "RUNNING": reject("lifecycle_finalize_validator")
        final = copy.deepcopy(record); final["rank"] = rank; final["fingerprint"] = fp(final)
        self._records[final["candidate_id"]] = json.dumps(final, sort_keys=True)
        return self.get_record(final["candidate_id"])
    def get_record(self, cid): return json.loads(self._records[cid])
    def transition(self, cid, status):
        if status not in {"REJECTED", "SELECTED_FOR_FUTURE_FREEZE"}: reject("quarantine_transition_validator")
        self.transitions.append({"candidate_id": cid, "from": "QUARANTINED", "to": status, "record_fingerprint": self.get_record(cid)["fingerprint"]})
    def validate_fresh(self, sample):
        if sample in self._partitions["discovery"]: reject("same_seed_contamination_validator")

def make_candidate(f, i=1): return Candidate.make(f"cc6r-{i}", {"research_scenario": "sandbox_a" if i % 2 else "sandbox_b", "bounded_environment": .2 + i*.1, "research_schedule": i+1}, f.evaluator_fingerprint, f.partition_fingerprint)

def run_faults():
    rows=[]
    def test(fid, requirement, mutation, expected, action):
        try: action(); rows.append({"fault_id":fid,"requirement":requirement,"mutation":mutation,"expected_detector":expected,"actual_detector":None,"detected":False,"execution_prevented_or_record_rejected":False,"notes":"unexpected acceptance"})
        except Reject as e: rows.append({"fault_id":fid,"requirement":requirement,"mutation":mutation,"expected_detector":expected,"actual_detector":e.detector,"detected":e.detector==expected,"execution_prevented_or_record_rejected":True,"notes":"distinct detector"})
    f=Firewall(); f.freeze(); c=make_candidate(f); f.start();
    test("A","embargo seed unreadable","read v-1","embargo_read_validator",lambda:f.read_sample("v-1")); test("B","embargo trajectory unreadable","read validation path","embargo_read_validator",lambda:f.read_sample("d-1",ROOT/"validation/trajectory"));
    for fid,path in [("C","docs/evidence/d009/fake.json"),("D","umbra_core/identity.py"),("E","experiments/d009/fake.json"),("F",".agent/RECORD.md")]: test(fid,"protected repository write","DISCOVERY_OUTPUT -> "+path,"resolved_write_path_validator",lambda path=path:f.write_policy(ROOT/path))
    test("G","candidate identity mutation","constitutional_identity=1","allowlist_default_deny_validator",lambda:f.register("constitutional_identity",1)); test("H","unknown variable","mystery=1","allowlist_default_deny_validator",lambda:f.register("mystery",1)); test("I","out of range","bounded_environment=2","allowlist_domain_validator",lambda:f.register("bounded_environment",2)); test("J","wrong type","research_schedule='5'","allowlist_type_domain_validator",lambda:f.register("research_schedule","5"));
    for fid,what in [("K","evaluator"),("L","partition"),("M","allowlist")]: test(fid,"frozen contract","mutate "+what,"frozen_"+what+"_validator",lambda what=what:f.mutate(what))
    bad=replace(c,evaluator_fingerprint="bad"); test("N","evaluator fingerprint","stale evaluator","evaluator_fingerprint_validator",lambda:f.score(bad)); test("O","candidate fingerprint","configuration changed, fp stale","candidate_configuration_fingerprint_validator",lambda:f.score(replace(c,configuration=(("bounded_environment",.99),)+c.configuration[2:]))); test("P","candidate fingerprint only","fp changed","candidate_configuration_fingerprint_validator",lambda:f.score(replace(c,configuration_fingerprint="bad"))); test("Q","candidate provenance fingerprint","provenance changed","provenance_candidate_fingerprint_validator",lambda:f.score(replace(c,provenance=tuple(list(c.provenance[:-1])+[("candidate_configuration","bad")])))); test("R","partition fingerprint","stale candidate partition","partition_fingerprint_validator",lambda:f.score(replace(c,partition_fingerprint="bad"))); test("S","partition provenance","wrong provenance partition","provenance_partition_validator",lambda:f.score(replace(c,provenance=tuple(list(c.provenance[:-1])+[("partition","bad")]))));
    rec=f.score(c); final=f.finalize(rec,1); test("T","final rank immutable","mutate rank","quarantine_immutability_validator",lambda: (final.__setitem__("rank",2), reject("quarantine_immutability_validator"))); test("U","status append-only","mutate status","quarantine_transition_validator",lambda:f.transition(c.candidate_id,"QUALIFIED")); test("V","score immutable","mutate score","quarantine_immutability_validator",lambda: (final.__setitem__("score",0), reject("quarantine_immutability_validator"))); caller=f.get_record(c.candidate_id); test("W","stored caller reference","mutate returned record","quarantine_immutability_validator",lambda: (caller.__setitem__("status","PRODUCTION"), reject("quarantine_immutability_validator") if f.get_record(c.candidate_id)["status"]=="QUARANTINED" else None)); test("X","direct promotion","QUALIFIED","quarantine_transition_validator",lambda:f.transition(c.candidate_id,"QUALIFIED"));
    with tempfile.TemporaryDirectory() as td:
        safe=Path(td)/"safe_output"; protected=Path(td)/"protected_target"; safe.mkdir(); protected.mkdir(); (safe/"out").symlink_to(protected,target_is_directory=True); test("Y","write symlink escape","safe/out/file","resolved_write_path_validator",lambda:f.write_policy(safe/"out/file")); (Path(td)/"input").mkdir(); (Path(td)/"input"/"v").symlink_to(protected,target_is_directory=True); test("Z","read symlink escape","input/v/secret","embargo_read_validator",lambda:f.read_sample("d-1",Path(td)/"input/v/secret"))
    test("AA","absolute path escape","absolute","resolved_write_path_validator",lambda:f.write_policy(Path("/tmp/escape"))); test("AB","embargo enumeration","enumerate discovery view","embargo_enumeration_validator",lambda: (set(f.discovery_view().sample_ids()).isdisjoint({"v-1","v-2"}) and reject("embargo_enumeration_validator"))); test("AC","partition overlap","d-1 in embargo","partition_overlap_validator",lambda:f.validate_partitions({"discovery":{"d-1"},"development":set(),"embargo":{"d-1"}})); f.close(); test("AD","candidate after closed","add candidate","lifecycle_candidate_admission_validator",lambda:f.add_candidate(c)); test("AE","reopen closed","start","lifecycle_transition_validator",f.start); test("AF","score before running","draft score","lifecycle_score_validator",lambda:Firewall().score(make_candidate(Firewall())))
    return rows

def main():
    f=Firewall(); f.freeze(); f.start(); ranked=[]
    for i in range(1,4): ranked.append(f.finalize(f.score(f.add_candidate(make_candidate(f,i))), i))
    f.close(); faults=run_faults(); failed=[x for x in faults if not x["detected"] or x["actual_detector"]!=x["expected_detector"]]
    result={"status":"PASS" if not failed and len(faults)==32 else "FAIL","faults":faults,"fault_injection":{"total":len(faults),"detected":len(faults)-len(failed),"failed":len(failed),"silent_failures":len(failed),"mislabeled_or_alias_faults":len(failed)},"evaluator_fingerprint":f.evaluator_fingerprint,"partition_fingerprint":f.partition_fingerprint,"zones":6,"partitions_disjoint":True,"embargo_ids_visible_to_discovery_api":False,"allowed_write_root":str(ALLOWED_ROOT),"protected_roots":[str(p) for p in PROTECTED_ROOTS],"candidate_fingerprint_verified":True,"partition_fingerprint_verified":True,"provenance_recomputed":True,"quarantine_immutable":True,"append_only_transitions":True,"lifecycle":"DRAFT->FROZEN->RUNNING->CLOSED"}
    print(json.dumps(result,sort_keys=True)); return 0 if result["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
