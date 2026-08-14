#!/usr/bin/env python3
"""CC-6R3 mechanical evidence, invariants, and summary validator."""
import json
from pathlib import Path
from shadow_harness import CANONICAL

HERE=Path(__file__).resolve().parents[3]/"docs"/"course-correction"/"cc6-discovery-firewall"
REQUIRED={"fault_id","requirement_id","requirement_text","mutation","test_symbol","expected_detector","actual_detector","detection_mode","detected","execution_prevented","record_rejected","original_record_unchanged","notes"}
def main():
    evidence=json.loads((HERE/"fault-injection-results.json").read_text()); matrix=json.loads((HERE/"fault-coverage-matrix.json").read_text()); rows=evidence["faults"]; ids=[r["fault_id"] for r in rows]
    assert len(ids)==len(set(ids)), "duplicate IDs"
    assert set(CANONICAL)==set(ids), "canonical fault set mismatch"
    for fid,meaning in CANONICAL.items():
        row=next(r for r in rows if r["fault_id"]==fid); assert row["requirement_text"]==meaning, f"meaning mismatch {fid}"
    for r in rows:
        assert REQUIRED <= set(r), f"incomplete {r['fault_id']}"
        if r["detection_mode"]=="REJECTED": assert r["detected"] and r["expected_detector"]==r["actual_detector"], f"rejection mismatch {r['fault_id']}"
        else: assert r["detection_mode"]=="INVARIANT_PRESERVED" and r["detected"] and r["original_record_unchanged"] and not r["execution_prevented"] and not r["record_rejected"] and r["actual_detector"] is None, f"invariant mismatch {r['fault_id']}"
    for fid in ("AE","AF"):
        r=next(x for x in rows if x["fault_id"]==fid); assert r["lexical_inside_allowed_root"] and not r["resolved_inside_allowed_root"], fid
    for fid in ("W","AJ","AK"):
        r=next(x for x in rows if x["fault_id"]==fid); assert r["original_record_unchanged"] and r["authoritative_before_fingerprint"]==r["authoritative_after_fingerprint"] and r["authoritative_before_payload_hash"]==r["authoritative_after_payload_hash"], fid
    assert [r["requirement_id"] for r in matrix["requirements"]]==ids
    required_summary={"traversal_rejected":"Z","absolute_escape_rejected":"AR","write_symlink_inside_allowed_root_rejected":"AE","read_symlink_inside_allowed_root_rejected":"AF","protected_even_if_allowlisted":"AS"}
    for key,fid in required_summary.items(): assert (evidence["paths"][key] if key.endswith("rejected") else evidence[key]), key
    assert evidence["status"]=="PASS" and evidence["silent_failures"]==0 and all(evidence["positive_controls"].values())
    print(f"CC-6R3 evidence consistency: PASS ({len(rows)} complete records; A-AS preserved; positive controls pass)")
if __name__=="__main__": main()
