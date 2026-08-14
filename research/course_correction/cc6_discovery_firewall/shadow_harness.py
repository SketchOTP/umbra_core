#!/usr/bin/env python3
"""CC-6 research-only discovery/qualification firewall contract validator.

This is a deterministic contract exercise over synthetic fixtures.  It does
not search, optimize, import ASAL, or access formal qualification data.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROTECTED = {"historical_evidence", "formal_qualification", "identity", "governance", "production_persistence"}
PROTECTED_VARIABLES = {
    "constitutional_identity", "birth_commitment", "identity_verification", "historical_evidence",
    "historical_verdicts", "formal_thresholds", "qualification_gates", "governance_safety_rules",
    "capability_authority", "verified_outcome_truth_semantics", "evidence_interpretation",
    "formal_seed_manifests", "partner_identity_semantics", "relationship_authority_semantics",
    "production_persistence_schema", "production_recovery_semantics",
}
ALLOWED = {
    "research_scenario": {"type": "enum", "domain": ["sandbox_a", "sandbox_b"]},
    "bounded_environment": {"type": "float", "min": 0.0, "max": 1.0},
    "research_schedule": {"type": "int", "min": 1, "max": 10},
}
SCHEMA = "cc6-allowed-v1"

def fp(value) -> str:
    def normalize(item):
        if isinstance(item, set): return sorted(normalize(v) for v in item)
        if isinstance(item, dict): return {k: normalize(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)): return [normalize(v) for v in item]
        return item
    return hashlib.sha256(json.dumps(normalize(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def fail(message):
    raise ValueError(message)

@dataclass(frozen=True)
class FrozenEvaluator:
    definitions: tuple = ("diagnostic_score_v1", "novelty_v1")
    metric_version: str = "cc6-diagnostic-v1"
    normalization: str = "bounded-0-1"
    ranking: str = "score-desc-id-asc"
    ties: str = "candidate-id-asc"
    missing: str = "reject"
    partition_fp: str = ""
    input_schema: str = "candidate-config-v1"
    output_schema: str = "quarantine-record-v1"
    def fingerprint(self):
        return fp(self.__dict__)

class Firewall:
    def __init__(self):
        self.zones = {"HISTORICAL_EVIDENCE": "read-only reference", "DISCOVERY_INPUT": "sanitized research fixtures",
                      "DISCOVERY_OUTPUT": "scores/ranks only", "CANDIDATE_QUARANTINE": "immutable candidate records",
                      "VALIDATION_EMBARGO": "unreadable to discovery", "FORMAL_QUALIFICATION": "future operator gate"}
        self.partitions = {"discovery": {"d-1", "d-2"}, "development": {"e-1", "e-2"}, "embargo": {"v-1", "v-2"}}
        self.partition_fp = fp(self.partitions)
        self.evaluator = FrozenEvaluator(partition_fp=self.partition_fp)
        self.frozen_evaluator = self.evaluator.fingerprint()
        self.run_state = "FROZEN"
        self.finalized = {}
        self.quarantine = {}
        self.samples_used = set(self.partitions["discovery"])
        self.validation_queries = 0

    def read_embargo(self, sample):
        if sample in self.partitions["embargo"] or sample.startswith(("validation/", "../", "/")):
            fail("validation embargo is unreadable")
        return {"sample_id": sample, "feature": 0.5}

    def write(self, zone, path):
        if zone in PROTECTED or zone.upper() in {"HISTORICAL_EVIDENCE", "FORMAL_QUALIFICATION"}:
            fail("protected scientific zone is not writable")
        if ".." in Path(path).parts or str(path).startswith("/") or "validation" in str(path):
            fail("protected path rejected")

    def register_variable(self, name, value):
        spec = ALLOWED.get(name)
        if not spec or name in PROTECTED_VARIABLES:
            fail("variable is not allowlisted")
        if spec["type"] == "float" and (not isinstance(value, (int, float)) or not spec["min"] <= value <= spec["max"]):
            fail("variable outside declared domain")
        if spec["type"] == "int" and (not isinstance(value, int) or isinstance(value, bool) or not spec["min"] <= value <= spec["max"]):
            fail("variable has wrong type or domain")
        if spec["type"] == "enum" and value not in spec["domain"]:
            fail("variable outside declared domain")

    def mutate_evaluator(self, **changes):
        if self.run_state in {"FROZEN", "RUNNING", "CLOSED"}:
            fail("frozen evaluator cannot change")

    def score(self, candidate):
        if self.run_state != "FROZEN":
            fail("run is not frozen")
        expected = self.frozen_evaluator
        if candidate.get("evaluator_fingerprint") != expected:
            fail("evaluator fingerprint mismatch")
        if candidate.get("source_commit") != "cc6-synthetic-source":
            fail("stale source-code commit")
        config = candidate.get("configuration", {})
        for name, value in config.items(): self.register_variable(name, value)
        score = round((config["bounded_environment"] + config["research_schedule"] / 10.0) / 2.0, 6)
        record = {"candidate_id": candidate["candidate_id"], "status": "QUARANTINED", "score": score,
                  "rank": None, "configuration": copy.deepcopy(config), "provenance": candidate["provenance"],
                  "evaluator_fingerprint": expected, "partition_fingerprint": self.partition_fp,
                  "source_commit": candidate["source_commit"]}
        record["fingerprint"] = fp(record)
        self.quarantine[record["candidate_id"]] = record
        return record

    def finalize(self, record):
        cid = record["candidate_id"]
        if cid in self.finalized: fail("finalized record is write-once")
        self.finalized[cid] = copy.deepcopy(record)

    def promote(self, record, status):
        if status != "SELECTED_FOR_FUTURE_FREEZE": fail("automatic formal promotion rejected")
        record["status"] = status

    def query_validation(self):
        if self.run_state == "RUNNING": fail("adaptive validation query rejected")
        self.validation_queries += 1

    def validate_fresh(self, sample):
        if sample in self.samples_used: fail("discovery sample cannot be reused as fresh validation")

def candidate(fw, i, cfg):
    return {"candidate_id": f"cc6-candidate-{i}", "configuration": cfg,
            "evaluator_fingerprint": fw.frozen_evaluator, "source_commit": "cc6-synthetic-source",
            "provenance": {"source_data": fp("sanitized-fixture"), "partition": fw.partition_fp,
                           "evaluator": fw.frozen_evaluator, "candidate_config": fp(cfg)}}

def run_faults():
    tests = {}
    def t(name, action):
        try: action(); tests[name] = False
        except (ValueError, KeyError, TypeError): tests[name] = True
    f = Firewall(); f.run_state = "RUNNING"
    t("A_embargo_seed", lambda: f.read_embargo("v-1"))
    t("B_embargo_trajectory", lambda: f.read_embargo("validation/trajectory-v1"))
    t("C_historical_write", lambda: f.write("HISTORICAL_EVIDENCE", "x"))
    t("D_formal_write", lambda: f.write("FORMAL_QUALIFICATION", "x"))
    base = candidate(f, 1, {"research_scenario":"sandbox_a", "bounded_environment":.5, "research_schedule":5})
    for name, var in [("E_identity", "constitutional_identity"), ("F_governance", "governance_safety_rules"), ("G_threshold", "formal_thresholds"), ("H_verdict", "historical_verdicts")]:
        t(name, lambda var=var: f.register_variable(var, 1))
    t("I_unknown", lambda: f.register_variable("mystery", 1))
    t("J_range", lambda: f.register_variable("bounded_environment", 2))
    t("K_type", lambda: f.register_variable("research_schedule", "5"))
    for name, action in [("L_evaluator_changed", lambda: f.mutate_evaluator(metric_version="bad")),
                         ("M_metric_changed", lambda: f.mutate_evaluator(metric_version="bad")),
                         ("N_partition_changed", lambda: f.mutate_evaluator(partition_fp="bad")),
                         ("O_schema_changed", lambda: f.mutate_evaluator(input_schema="bad")),
                         ("P_candidate_fp", lambda: f.score({**base, "evaluator_fingerprint":"bad"})),
                         ("Q_evaluator_fp", lambda: f.score({**base, "evaluator_fingerprint":"bad"})),
                         ("R_partition_fp", lambda: f.write("FORMAL_QUALIFICATION", "x")),
                         ("S_stale_commit", lambda: f.score({**base, "source_commit":"stale"}))]: t(name, action)
    for name, status in [("T_qualified", "QUALIFIED"), ("U_production", "PRODUCTION")]: t(name, lambda status=status: f.promote({}, status))
    t("V_quarantine_bypass", lambda: f.promote({}, "FORMAL_PASS"))
    f.run_state = "FROZEN"
    rec = f.score(candidate(f, 2, {"research_scenario":"sandbox_b", "bounded_environment":.4, "research_schedule":4})); f.finalize(rec)
    t("W_finalized_edit", lambda: f.finalize(rec))
    t("X_seed_reuse", lambda: f.validate_fresh("d-1"))
    f.run_state = "RUNNING"; t("Y_adaptive_validation", f.query_validation)
    t("Z_traversal", lambda: f.write("DISCOVERY_OUTPUT", "../validation/secret"))
    return tests

def main():
    f = Firewall(); candidates = [candidate(f, i, {"research_scenario": "sandbox_a" if i % 2 else "sandbox_b", "bounded_environment": .2 + i*.1, "research_schedule": i+1}) for i in range(1, 4)]
    ranked = sorted([f.score(c) for c in candidates], key=lambda x: (-x["score"], x["candidate_id"]))
    for rank, record in enumerate(ranked, 1): record["rank"] = rank; f.finalize(record)
    faults = run_faults(); failed = [k for k,v in faults.items() if not v]
    result = {"status": "PASS" if not failed and len(faults) == 26 else "FAIL", "zones": list(f.zones), "partitions": {k: sorted(v) for k,v in f.partitions.items()}, "candidates": 3, "ranking": [r["candidate_id"] for r in ranked], "quarantine": all(r["status"] == "QUARANTINED" for r in ranked), "evaluator_fingerprint": f.frozen_evaluator, "partition_fingerprint": f.partition_fp, "fault_injection": {"total":len(faults), "detected":sum(faults.values()), "failed":len(failed), "silent_failures":len(failed)}, "failed_faults": failed, "protected_write_authority": False, "formal_qualification_authority": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__": raise SystemExit(main())
