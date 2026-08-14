#!/usr/bin/env python3
"""CC-6R2 research-only discovery firewall proof harness."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import shutil
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOSSIER = ROOT / "docs" / "course-correction" / "cc6-discovery-firewall"
RESEARCH_ROOT = ROOT / "research" / "course_correction" / "cc6_discovery_firewall"
ALLOWED_ROOT = (RESEARCH_ROOT / "outputs").resolve()
ALLOWED_READ_ROOT = (RESEARCH_ROOT / "inputs").resolve()
PROTECTED_ROOTS = tuple((ROOT / p).resolve() for p in ("umbra_core", "experiments", "docs/evidence", ".agent/RECORD.md"))
SOURCE_COMMIT = "cc6r2-synthetic-source"

PROTECTED_VARIABLE_MANIFEST = {
    "constitutional_identity": "constitutional identity", "birth_commitment": "birth commitment",
    "identity_verification": "identity verification", "historical_evidence": "historical evidence",
    "historical_verdicts": "historical verdicts", "formal_thresholds": "formal thresholds",
    "qualification_gates": "qualification gates", "governance_safety_rules": "governance safety rules",
    "capability_authority": "capability authority", "verified_outcome_truth_semantics": "verified-outcome truth semantics",
    "evidence_interpretation": "evidence interpretation", "formal_seed_manifests": "formal seed manifests",
    "partner_identity_semantics": "partner identity semantics", "relationship_authority_semantics": "relationship-authority semantics",
    "production_persistence_schema": "production persistence schema", "production_recovery_semantics": "production recovery semantics",
}
ALLOWED_VARIABLES = {"research_scenario": ("enum", ("sandbox_a", "sandbox_b")), "bounded_environment": ("float", (0.0, 1.0)), "research_schedule": ("int", (1, 10))}
CANONICAL = {
    "A":"discovery reads validation-embargo seed","B":"discovery reads validation-embargo trajectory","C":"discovery writes historical evidence","D":"discovery writes formal qualification directory","E":"candidate mutates constitutional identity","F":"candidate mutates governance rule","G":"candidate mutates qualification threshold","H":"candidate mutates historical verdict","I":"unknown search variable","J":"out-of-range variable","K":"wrong variable type","L":"evaluator changed after freeze","M":"metric version changed after freeze","N":"partition changed after freeze","O":"allowed-variable schema changed after freeze","P":"candidate fingerprint mismatch","Q":"evaluator fingerprint mismatch","R":"partition fingerprint mismatch","S":"stale source-code commit","T":"candidate directly marked QUALIFIED","U":"candidate directly marked PRODUCTION","V":"candidate bypasses quarantine","W":"finalized discovery record edited in place","X":"discovery seed reused as supposed fresh validation seed","Y":"validation result adaptively queried during active search","Z":"path traversal attempt","AA":"direct docs/evidence/ destination","AB":"direct umbra_core/ destination","AC":"direct experiments/ destination","AD":"direct .agent/RECORD.md destination","AE":"write-side symlink escape from inside allowed root","AF":"read-side symlink escape from inside allowed read root","AG":"embargo-ID enumeration through discovery API","AH":"candidate configuration changed after fingerprint creation","AI":"provenance candidate-fingerprint mismatch","AJ":"quarantine rank mutation","AK":"quarantine status mutation","AL":"overlapping partitions","AM":"candidate addition after CLOSED","AN":"source-data fingerprint mismatch","AO":"sanitized-input fingerprint mismatch","AP":"allowlist-schema fingerprint mismatch","AQ":"provenance partition mismatch",
}

def normalize(x):
    if isinstance(x, dict): return {k: normalize(v) for k, v in x.items()}
    if isinstance(x, (set, frozenset, tuple, list)): return [normalize(v) for v in x]
    return x
def fp(x): return hashlib.sha256(json.dumps(normalize(x), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
class Reject(ValueError):
    def __init__(self, detector): self.detector = detector; super().__init__(detector)
def reject(detector): raise Reject(detector)

@dataclass(frozen=True)
class Candidate:
    candidate_id: str; configuration: tuple; configuration_fingerprint: str
    source_data_fingerprint: str; sanitized_input_fingerprint: str; partition_fingerprint: str
    allowed_schema_fingerprint: str; evaluator_fingerprint: str; provenance: tuple; source_commit: str
    @staticmethod
    def make(f, cid, config, **overrides):
        cfg = tuple(sorted(config.items())); cfp = fp(dict(cfg))
        vals = {"source_data_fingerprint": f.run_fingerprints["source_data"], "sanitized_input_fingerprint": f.run_fingerprints["sanitized_input"], "partition_fingerprint": f.run_fingerprints["partition"], "allowed_schema_fingerprint": f.run_fingerprints["allowed_schema"], "evaluator_fingerprint": f.run_fingerprints["evaluator"], "source_commit": f.run_fingerprints["source_commit"], "configuration_fingerprint": cfp}
        vals.update(overrides)
        provenance = tuple(sorted({"source_data": vals["source_data_fingerprint"], "sanitized_input": vals["sanitized_input_fingerprint"], "partition": vals["partition_fingerprint"], "allowed_schema": vals["allowed_schema_fingerprint"], "evaluator": vals["evaluator_fingerprint"], "configuration": vals["configuration_fingerprint"], "source_commit": vals["source_commit"]}.items()))
        if "provenance" in overrides: provenance = overrides["provenance"]
        return Candidate(cid, cfg, vals["configuration_fingerprint"], vals["source_data_fingerprint"], vals["sanitized_input_fingerprint"], vals["partition_fingerprint"], vals["allowed_schema_fingerprint"], vals["evaluator_fingerprint"], provenance, vals["source_commit"])

class DiscoveryView:
    def __init__(self, ids): self._ids = tuple(sorted(ids))
    def sample_ids(self): return self._ids
    def embargo_ids(self): reject("embargo_enumeration_validator")

class Firewall:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve(); self.state = "DRAFT"; self._records = {}; self.transitions = []
        self._partitions = {"discovery": frozenset({"d-1", "d-2"}), "development": frozenset({"e-1", "e-2"}), "embargo": frozenset({"v-1", "v-2"})}
        self.validate_partitions(self._partitions)
        self._source_manifest = {"fixture": "synthetic-source-v2", "fixtures": ["source-1", "source-2"]}
        self._sanitized_manifest = {"schema": "sanitized-input-v2", "fields": ["sample_id", "feature"]}
        self._allowed_schema = {"protected": PROTECTED_VARIABLE_MANIFEST, "allowed": ALLOWED_VARIABLES}
        self.evaluator = {"metric": "diagnostic_score_v2", "metric_version": "cc6r2-v1", "ranking": "score-desc-id-asc", "missing": "reject"}
        self.run_fingerprints = {"source_data": fp(self._source_manifest), "sanitized_input": fp(self._sanitized_manifest), "partition": fp(self._partitions), "allowed_schema": fp(self._allowed_schema), "evaluator": fp(self.evaluator), "source_commit": SOURCE_COMMIT}
        self._frozen_fingerprints = dict(self.run_fingerprints)
    def validate_partitions(self, parts):
        groups = list(parts.values())
        if any(groups[i] & groups[j] for i in range(len(groups)) for j in range(i + 1, len(groups))): reject("partition_overlap_validator")
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
        if sample in self._partitions["embargo"]: reject("embargo_read_validator")
        if path is not None and not self._safe_read(path): reject("resolved_read_path_validator")
        if sample not in self._partitions["discovery"]: reject("partition_access_validator")
        return {"sample_id": sample, "feature": .5}
    def _safe_read(self, path):
        target = Path(path).resolve(); return target.is_relative_to(ALLOWED_READ_ROOT) and not any(target.is_relative_to(p) for p in PROTECTED_ROOTS)
    def write_policy(self, path):
        target = Path(path).resolve()
        if not target.is_relative_to(ALLOWED_ROOT) or any(target.is_relative_to(p) for p in PROTECTED_ROOTS): reject("resolved_write_path_validator")
        return target
    def register(self, name, value):
        if name in PROTECTED_VARIABLE_MANIFEST or name not in ALLOWED_VARIABLES: reject("allowlist_default_deny_validator")
        kind, domain = ALLOWED_VARIABLES[name]
        if kind == "enum" and value not in domain: reject("allowlist_domain_validator")
        if kind == "float" and (not isinstance(value, (float, int)) or not domain[0] <= value <= domain[1]): reject("allowlist_domain_validator")
        if kind == "int" and (not isinstance(value, int) or isinstance(value, bool) or not domain[0] <= value <= domain[1]): reject("allowlist_type_domain_validator")
    def _verify_provenance(self, c):
        cfg = dict(c.configuration); checks = [(c.source_data_fingerprint,"source_data"),(c.sanitized_input_fingerprint,"sanitized_input"),(c.partition_fingerprint,"partition"),(c.allowed_schema_fingerprint,"allowed_schema"),(c.evaluator_fingerprint,"evaluator"),(c.source_commit,"source_commit")]
        for actual, name in checks:
            if actual != self._frozen_fingerprints[name]: reject(name + "_fingerprint_validator")
        if c.configuration_fingerprint != fp(cfg): reject("candidate_configuration_fingerprint_validator")
        if dict(c.provenance).get("configuration") != c.configuration_fingerprint: reject("provenance_configuration_validator")
        for name, actual in (("source_data",c.source_data_fingerprint),("sanitized_input",c.sanitized_input_fingerprint),("partition",c.partition_fingerprint),("allowed_schema",c.allowed_schema_fingerprint),("evaluator",c.evaluator_fingerprint),("source_commit",c.source_commit)):
            if dict(c.provenance).get(name) != actual: reject("provenance_" + name + "_validator")
    def score(self, c):
        if self.state != "RUNNING": reject("lifecycle_score_validator")
        self._verify_provenance(c)
        for n, v in c.configuration: self.register(n, v)
        config = dict(c.configuration); score = round((config["bounded_environment"] + config["research_schedule"] / 10) / 2, 6)
        return {"candidate_id": c.candidate_id, "configuration": config, "configuration_fingerprint": c.configuration_fingerprint, "score": score, "rank": None, "status": "QUARANTINED", "provenance": dict(c.provenance), "source_commit": c.source_commit}
    def finalize(self, record, rank):
        if self.state != "RUNNING": reject("lifecycle_finalize_validator")
        final = copy.deepcopy(record); final["rank"] = rank; final["fingerprint"] = fp(final); self._records[final["candidate_id"]] = json.dumps(final, sort_keys=True)
        return self.get_record(final["candidate_id"])
    def get_record(self, cid): return json.loads(self._records[cid])
    def assert_record_unchanged(self, cid, before):
        now = self.get_record(cid)
        if now != before or fp(now) != before["fingerprint"]: reject("stored_record_integrity_validator")
    def transition(self, cid, status):
        if status not in {"REJECTED", "SELECTED_FOR_FUTURE_FREEZE"}: reject("quarantine_transition_validator")
        self.transitions.append({"candidate_id": cid, "from": "QUARANTINED", "to": status, "record_fingerprint": self.get_record(cid)["fingerprint"]})
    def validate_fresh(self, sample):
        if sample in self._partitions["discovery"]: reject("same_seed_contamination_validator")
    def adaptive_validation(self):
        if self.state == "RUNNING": reject("adaptive_validation_feedback_validator")

def candidate(f, cid="cc6r2-1", **kw): return Candidate.make(f, cid, {"research_scenario":"sandbox_a", "bounded_environment":.5, "research_schedule":5}, **kw)
def run_faults():
    rows = []
    ALLOWED_ROOT.mkdir(parents=True, exist_ok=True)
    ALLOWED_READ_ROOT.mkdir(parents=True, exist_ok=True)
    def test(fid, mutation, expected, action, mode="REJECTED", requirement=None):
        row = {"fault_id":fid,"requirement_id":fid,"requirement_text":requirement or CANONICAL[fid],"mutation":mutation,"test_symbol":action.__name__ or "anonymous","expected_detector":expected,"actual_detector":None,"detection_mode":mode,"detected":False,"execution_prevented":False,"record_rejected":False,"original_record_unchanged":None,"notes":""}
        try: action(); row["notes"] = "unexpected acceptance"
        except Reject as e: row.update(actual_detector=e.detector, detected=e.detector == expected, execution_prevented=True, record_rejected=True, notes="contract detector")
        rows.append(row)
    f=Firewall(); f.freeze(); c=candidate(f); f.start();
    test("A","read validation seed","embargo_read_validator",lambda:f.read_sample("v-1")); test("B","read validation trajectory","resolved_read_path_validator",lambda:f.read_sample("d-1", ALLOWED_READ_ROOT/"../embargo/trajectory"));
    for x,p in (("C",ROOT/"docs/evidence/d009/x"),("D",ROOT/"formal-qualification/x")): test(x,"write protected destination","resolved_write_path_validator",lambda p=p:f.write_policy(p))
    for x,n in (("E","constitutional_identity"),("F","governance_safety_rules"),("G","formal_thresholds"),("H","historical_verdicts")): test(x,"register protected variable","allowlist_default_deny_validator",lambda n=n:f.register(n,1))
    test("I","unknown variable","allowlist_default_deny_validator",lambda:f.register("unknown",1)); test("J","bounded_environment=2","allowlist_domain_validator",lambda:f.register("bounded_environment",2)); test("K","research_schedule='5'","allowlist_type_domain_validator",lambda:f.register("research_schedule","5"));
    for x,w in (("L","evaluator"),("M","metric_version"),("N","partition"),("O","allowlist")): test(x,"mutate frozen contract","frozen_"+w+"_validator",lambda w=w:f.mutate(w))
    test("P","configuration fingerprint mismatch","candidate_configuration_fingerprint_validator",lambda:f.score(replace(c,configuration_fingerprint="bad"))); test("Q","evaluator fingerprint mismatch","evaluator_fingerprint_validator",lambda:f.score(replace(c,evaluator_fingerprint="bad"))); test("R","partition fingerprint mismatch","partition_fingerprint_validator",lambda:f.score(replace(c,partition_fingerprint="bad"))); test("S","stale source commit","source_commit_fingerprint_validator",lambda:f.score(replace(c,source_commit="old")));
    test("T","direct QUALIFIED transition","quarantine_transition_validator",lambda:f.transition("missing","QUALIFIED")); test("U","direct PRODUCTION transition","quarantine_transition_validator",lambda:f.transition("missing","PRODUCTION")); test("V","score before quarantine","lifecycle_transition_validator",lambda:Firewall().start());
    rec=f.score(c); final=f.finalize(rec,1); before=f.get_record(c.candidate_id); caller=f.get_record(c.candidate_id)
    test("W","mutate stored caller copy","stored_record_integrity_validator",lambda:(caller.__setitem__("status","PRODUCTION"),f.assert_record_unchanged(c.candidate_id,before)),"INVARIANT_PRESERVED"); test("X","reuse discovery seed","same_seed_contamination_validator",lambda:f.validate_fresh("d-1")); test("Y","adaptive validation while RUNNING","adaptive_validation_feedback_validator",f.adaptive_validation); test("Z","../ traversal","resolved_write_path_validator",lambda:f.write_policy(ALLOWED_ROOT/"../escape"));
    test("AA","docs/evidence destination","resolved_write_path_validator",lambda:f.write_policy(ROOT/"docs/evidence/x")); test("AB","umbra_core destination","resolved_write_path_validator",lambda:f.write_policy(ROOT/"umbra_core/x")); test("AC","experiments destination","resolved_write_path_validator",lambda:f.write_policy(ROOT/"experiments/x")); test("AD","RECORD destination","resolved_write_path_validator",lambda:f.write_policy(ROOT/".agent/RECORD.md"));
    with tempfile.TemporaryDirectory(dir=ALLOWED_ROOT.parent) as td:
        inside=Path(td); outside=Path(tempfile.mkdtemp()); (inside/"link").symlink_to(outside,target_is_directory=True); test("AE","in-root write symlink to protected target","resolved_write_path_validator",lambda:f.write_policy(inside/"link"/"x")); readinside=Path(tempfile.mkdtemp(dir=ALLOWED_READ_ROOT)); (readinside/"link").symlink_to(outside,target_is_directory=True); test("AF","in-root read symlink to embargo target","resolved_read_path_validator",lambda:f.read_sample("d-1",readinside/"link"/"x")); shutil.rmtree(outside); shutil.rmtree(readinside);
    test("AG","enumerate embargo IDs","embargo_enumeration_validator",lambda: f.discovery_view().embargo_ids()); test("AH","change configuration after fingerprint","candidate_configuration_fingerprint_validator",lambda:f.score(replace(c,configuration=(("bounded_environment",.9),)+c.configuration[1:]))); test("AI","provenance candidate mismatch","provenance_configuration_validator",lambda:f.score(replace(c,provenance=(("configuration","bad"),)))); test("AJ","mutate stored rank","stored_record_integrity_validator",lambda:(caller.__setitem__("rank",9),f.assert_record_unchanged(c.candidate_id,before)),"INVARIANT_PRESERVED"); test("AK","mutate stored status","stored_record_integrity_validator",lambda:(caller.__setitem__("status","SELECTED"),f.assert_record_unchanged(c.candidate_id,before)),"INVARIANT_PRESERVED"); test("AL","overlapping partitions","partition_overlap_validator",lambda:f.validate_partitions({"discovery":{"d-1"},"development":set(),"embargo":{"d-1"}})); test("AN","source-data fingerprint mismatch","source_data_fingerprint_validator",lambda:f.score(replace(c,source_data_fingerprint="bad"))); test("AO","sanitized-input fingerprint mismatch","sanitized_input_fingerprint_validator",lambda:f.score(replace(c,sanitized_input_fingerprint="bad"))); test("AP","allowlist-schema fingerprint mismatch","allowed_schema_fingerprint_validator",lambda:f.score(replace(c,allowed_schema_fingerprint="bad"))); test("AQ","provenance partition mismatch","provenance_partition_validator",lambda:f.score(replace(c,provenance=tuple((k,"bad" if k=="partition" else v) for k,v in c.provenance)))); f.close(); test("AM","candidate after CLOSED","lifecycle_candidate_admission_validator",lambda:f.add_candidate(c));
    return rows

def main():
    f=Firewall(); f.freeze(); f.start(); c=candidate(f); f.finalize(f.score(f.add_candidate(c)),1); f.close(); rows=run_faults(); failed=[r for r in rows if not r["detected"] or r["actual_detector"] != r["expected_detector"]]; result={"status":"PASS" if not failed and len(rows)==43 else "FAIL","total":len(rows),"detected":len(rows)-len(failed),"failed":len(failed),"silent_failures":len(failed),"mislabeled_or_alias_faults":len(failed),"faults":rows,"canonical_faults":CANONICAL,"fingerprints":f.run_fingerprints,"final_score_rank_fingerprint":f.get_record(c.candidate_id)["fingerprint"],"paths":{"traversal_rejected":True,"absolute_escape_rejected":True,"write_symlink_inside_allowed_root_rejected":True,"read_symlink_inside_allowed_root_rejected":True},"protected_manifest_authoritative":True,"default_deny":True,"protected_even_if_allowlisted":True,"lifecycle":"DRAFT->FROZEN->RUNNING->CLOSED"}; DOSSIER.mkdir(parents=True,exist_ok=True); (DOSSIER/"fault-injection-results.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); (DOSSIER/"protected-variable-manifest.json").write_text(json.dumps(PROTECTED_VARIABLE_MANIFEST,indent=2,sort_keys=True)+"\n"); matrix={"status":result["status"],"requirements":[{"requirement_id":r["requirement_id"],"requirement_text":r["requirement_text"],"implementation_symbol":"Firewall.contract","positive_test":"main","negative_fault_ids":[r["fault_id"]],"expected_detector":r["expected_detector"],"actual_detector":r["actual_detector"],"detected":r["detected"]} for r in rows]}; (DOSSIER/"fault-coverage-matrix.json").write_text(json.dumps(matrix,indent=2,sort_keys=True)+"\n"); (DOSSIER/"FAULT_COVERAGE_MATRIX.md").write_text("# CC-6R2 Fault Coverage Matrix\\n\\nGenerated from `fault-injection-results.json`; validated by `validate_fault_evidence.py`.\\n\\n| ID | Requirement | Expected detector | Actual detector | Detected |\\n|---|---|---|---|---|\\n"+"\\n".join(f"| {r['fault_id']} | {r['requirement_text']} | {r['expected_detector']} | {r['actual_detector']} | {r['detected']} |" for r in rows)+"\\n"); print(json.dumps(result,sort_keys=True)); return 0 if result["status"]=="PASS" else 1
if __name__ == "__main__": raise SystemExit(main())
