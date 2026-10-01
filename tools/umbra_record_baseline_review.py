"""Publish measured baseline/continuity evidence without upgrading its scope."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.as017_evidence import publish_file_once, publish_json_once, stream_sha256
from tools.umbra_baseline_audit import bounded_json
import umbra_core.runtime

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()
    evidence = ROOT / "docs/evidence/continuity-20260930"
    life_root = Path("/home/sketch/Projects/umbra-life-evidence-20260930-v4")
    job_path = Path("/home/sketch/.codex/process-jobs/jobs/job-mu3l6lrx-ddb17f3a.json")
    job = bounded_json(job_path)
    baseline_path = args.audit or evidence / "P0_RETROSPECTIVE_AUDIT.json"
    baseline = bounded_json(baseline_path)
    life = bounded_json(life_root / "result.json")
    copies = [life_root / "result.json", *(life_root / f"segment-{index:02d}.json" for index in range(4))]
    for source in copies:
        destination = evidence / ("life-" + source.name)
        if not destination.exists():
            publish_file_once(source, destination)
        elif stream_sha256(destination) != stream_sha256(source):
            raise ValueError("retained_probe_copy_mismatch")
    tests = []
    for filename in ("target-tests.xml", "protected-tests.xml", "final-target-tests.xml",
                     "bounded-final-target-tests.xml", "sealed-target-tests.xml",
                     "publication-target-tests.xml", "publication-protected-tests.xml"):
        path = evidence / filename
        suites = ET.parse(path).getroot()
        tests.append({"file": filename, "sha256": stream_sha256(path),
                      **{key: sum(int(suite.get(key, 0)) for suite in suites.findall("testsuite"))
                         for key in ("tests", "failures", "errors", "skipped")}})
    executed_source = evidence / "life-probe-executed-source.py"
    if stream_sha256(executed_source) != life["harness_sha256"]:
        raise ValueError("executed_source_snapshot_hash_mismatch")
    tree = subprocess.check_output(["git", "rev-parse", "HEAD:umbra_core"], cwd=ROOT, text=True).strip()
    organism_tree = subprocess.check_output(["git", "rev-parse", "e8d048b510a477e677637b67bc0f56473cfe6540:umbra_core"], cwd=ROOT, text=True).strip()
    if tree != organism_tree or subprocess.check_output(["git", "diff", "HEAD", "--", "umbra_core"], cwd=ROOT, text=True):
        raise ValueError("semantic_freeze_changed")
    log_path = Path(job["logs"]["stdout"])
    observed_stdout = bounded_json(log_path)
    inventory = [{"path": str(path), "bytes": path.stat().st_size,
                  "sha256": stream_sha256(path), "mtime_ns": path.stat().st_mtime_ns}
                 for path in (job_path, log_path, Path(job["logs"]["stderr"]), *sorted(life_root.iterdir()))
                 if path.is_file()]
    failures = [row for row in tests if row["failures"] or row["errors"]]
    payload = {
        "schema": "UMBRA_BASELINE_LIFE_COMPANION_REVIEW_V1", "verdict": "PARTIAL",
        "starting_commit": "7284f41d6129e623cadbd70cff35a8229f62795e",
        "organism_semantic_subject": "e8d048b510a477e677637b67bc0f56473cfe6540",
        "production_subtree": tree, "production_delta": False,
        "formal_p0": {"job_id": job["id"], "exit_code": job["exitCode"],
                       "started_at": job["startedAt"], "completed_at": job["completedAt"],
                       "surviving_stdout": observed_stdout, "independent_audit": baseline["verdict"],
                       "independent_audit_sha256": stream_sha256(baseline_path),
                       "case_artifacts_recovered": 0, "case_validation_unavailable": 32,
                       "reported_consumed_seeds_reserved_against_reuse": list(range(99200001, 99200033)),
                       "historical_scientific_verdict_rewritten": False},
        "search_scope": [
            "local /home/sketch, /tmp, /mnt, /media, /srv/ATLAS (bounded read-only scans; unavailable paths not inferred)",
            "local Projects/Documents and /mnt/windows-n through depth six",
            "atlas-laptop retained /srv/ATLAS/.../UMBRA-CORE/evidence recursively; remote Projects/.codex/tmp through depth five",
            "exact retained launch conversation and CPJ metadata/logs; no external/private backup recovery performed"],
        "acceptance_gaps": [
            {"finding": "snapshot/payload/checkpoint cryptographic validation omitted by frozen shape validator",
             "evidence": "three disposable corruption controls pass old check and fail new check", "disposition": "source-proven; new copy-only audit; historical exposure unknown"},
            {"finding": "trace row count/monotonicity does not establish exact tick coverage",
             "disposition": "new audit checks exact 1..7200 with duplicate/missing controls"},
            {"finding": "RRE enabled flag is not RRE evidence validation",
             "disposition": "new audit validates active-kernel RRE categories/authority/schema; no numerical prediction claim"},
            {"finding": "configuration seed equality is not full frozen configuration binding",
             "disposition": "new audit compares resolved regime configuration to frozen configuration"},
            {"finding": "aggregate counts are insufficient for durable per-case/artifact reconciliation",
             "disposition": "new audit enforces individual ordered starts, exact seed bindings, artifacts and hashes"},
            {"finding": "complete trace-to-committed-outcome correspondence needs retained authority evidence",
             "disposition": "NOT DEMONSTRATED; unavailable historical databases/traces/archives cannot be reconstructed"}],
        "life_probe": {"verdict": life["verdict"], "ticks": life["ticks"], "restarts": life["restarts"],
                       "checkpoint_epoch": life["checkpoint_epoch"], "rre": life["rre_capture_counts"],
                       "observed_rss_max_mib": max(row["rss_mib"] for row in life["samples"]),
                       "sampled_hot_tail_max": max(row["hot_tail_events"] for row in life["samples"]),
                       "executed_harness_sha256": life["harness_sha256"],
                       "scope": "1024-tick DEVELOPMENT continuity/compaction, not sustained-life qualification",
                       "relationship_exposure": "none in S0 probe; empty-state continuity is not relationship causality",
                       "limitations": life["limitations"]},
        "probe_attempts": [
            {"work": "/home/sketch/Projects/umbra-life-evidence-20260930", "outcome": "StageJournal keyword interface error before organism creation", "completed_ticks": 0},
            {"work": "/home/sketch/Projects/umbra-life-evidence-20260930-v2", "outcome": "environment fixture setup after sole-authority Habitat attachment; first tick interrupted", "completed_trace_rows": 0, "organism_created": True},
            {"work": "/home/sketch/Projects/umbra-life-evidence-20260930-v3", "outcome": "authoritative read before restart Habitat reattachment; harness error", "completed_trace_rows": 256},
            {"work": str(life_root), "outcome": life["verdict"], "completed_trace_rows": life["ticks"]}],
        "targeted_tests": tests, "new_target_failures": failures,
        "regression_scope": "target/protected checks only; historical accepted full suite 1422 passed / 4 skipped / 9 inherited, unwaived; complete suite not rerun here",
        "environment": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                        "executable": sys.executable, "runtime_import_origin": umbra_core.runtime.__file__,
                        "packages": {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}},
        "source_fingerprints": {str(path.relative_to(ROOT)): stream_sha256(path) for path in
            [ROOT / "tools/umbra_baseline_audit.py", ROOT / "tools/umbra_life_probe.py", Path(__file__),
             ROOT / "tests/test_umbra_baseline_audit.py", ROOT / "tests/test_umbra_life_probe.py",
             ROOT / "docs/qualification/BASELINE_LIFE_COMPANION_PROTOCOL_V1.md"]},
        "artifact_inventory": inventory,
        "readiness": {"baseline": "BLOCKED_MISSING_ORIGINAL_CASE_EVIDENCE",
                      "sustained_life": "DEVELOPMENT_CONTINUITY_ONLY; P1-P3 not qualified",
                      "full_core_causality": "SCOPED_MODULE_TESTS_ONLY; P4 not qualified",
                      "companion": "PROSPECTIVE_PROTOCOL_PROPOSED; human sessions not run",
                      "reusable_release": "NOT_QUALIFIED; packaging must not fabricate acceptance"},
        "formal_stages_started_this_task": [], "formal_seeds_consumed_this_task": 0,
        "owner_or_architect_decisions": ["provide original P0 archive if available; otherwise disposition unverifiable reported P0 before any new formal generation",
                                          "prospectively review life/causal/companion criteria and provide owner participation"],
    }
    digest = publish_json_once(args.output, payload)
    print(json.dumps({"verdict": payload["verdict"], "sha256": digest, "new_target_failures": len(failures)}))


if __name__ == "__main__":
    main()
