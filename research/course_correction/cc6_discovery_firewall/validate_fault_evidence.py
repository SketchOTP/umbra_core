#!/usr/bin/env python3
"""Mechanical CC-6R2 evidence and coverage consistency validator."""
import json
from pathlib import Path
from shadow_harness import CANONICAL

HERE = Path(__file__).resolve().parents[3] / "docs" / "course-correction" / "cc6-discovery-firewall"
REQUIRED = {"fault_id","requirement_id","requirement_text","mutation","test_symbol","expected_detector","actual_detector","detection_mode","detected","execution_prevented","record_rejected","original_record_unchanged","notes"}

def main():
    evidence = json.loads((HERE / "fault-injection-results.json").read_text())
    matrix = json.loads((HERE / "fault-coverage-matrix.json").read_text())
    rows = evidence["faults"]; ids = [r["fault_id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate fault ID"
    assert set(CANONICAL).issubset(set(ids)), "missing canonical fault"
    for fid, meaning in CANONICAL.items():
        row = next(r for r in rows if r["fault_id"] == fid)
        assert row["requirement_text"] == meaning, f"meaning mismatch: {fid}"
    for row in rows:
        assert REQUIRED <= set(row), f"incomplete record: {row['fault_id']}"
        assert row["detected"], f"undetected fault: {row['fault_id']}"
        assert row["expected_detector"] == row["actual_detector"] or row["detection_mode"] == "INVARIANT_PRESERVED", f"detector mismatch: {row['fault_id']}"
    matrix_ids = [r["requirement_id"] for r in matrix["requirements"]]
    assert matrix_ids == ids, "matrix does not match executed records"
    assert evidence["status"] == "PASS" and evidence["silent_failures"] == 0
    print(f"CC-6R2 evidence consistency: PASS ({len(rows)} complete records; A-AM preserved; extensions present)")

if __name__ == "__main__": main()
