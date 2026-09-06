"""Publish the immutable AS-012 post-lock protocol failure closeout."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-012-exact-entrypoint-boundedness-soak-causal-closure-r1")
RETAINED = EVIDENCE / "retained-as012-boundedness-run"
BASELINE = "b4cc014c3545e19fa0e755407fe2a466e23e72a5"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path: Path, value: Any) -> str:
    if path.exists():
        raise FileExistsError(path)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write(payload); handle.flush(); os.fsync(handle.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return sha(path)


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    failure = {
        "schema": "AS012_PROTOCOL_FAILURE_V1", "directive": "UMBRA-AS-012", "baseline": BASELINE,
        "terminal_verdict": "AS012_PROTOCOL_FAIL", "classification": "POST_LOCK_HARNESS_RESULT_PUBLICATION_FAILURE",
        "job_id": "job-mtpufjwp-e9d71ffb", "command": "/home/sketch/cs14n-runtime/bin/python -m experiments.as012.downstream --mode boundedness --seed 21773881 --ticks 100000 --work /tmp/as012-boundedness-r1 --output /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-012-exact-entrypoint-boundedness-soak-causal-closure-r1/AS012_BOUNDEDNESS_RESULT.json",
        "started_at": "2026-09-06T13:24:26.409Z", "completed_at": "2026-09-06T17:07:09.995Z", "exit_code": 1,
        "exception_type": "ValueError", "exception": "binary mode doesn't take an encoding argument", "source": "experiments/as012/downstream.py:331", "phase": "frozen fresh boundedness result publication",
        "organism_creation": 1, "organism_load": 1, "organism_ticks": 100000, "retry": False, "reseed": False, "result_published": False,
        "scientific_result": "NOT QUALIFIED", "retained_run": {"ticks": 100000, "last_metric_tick": 100000, "last_metric_events": 521154, "last_metric_rss_mib": 49.15234375, "journal_lines": 21, "result_artifact": "absent"},
        "stderr": "Path.open(\\\"xb\\\", encoding=\\\"utf-8\\\") in main result publication",
        "recovery": "retained journal and SQLite copied read-only for provenance; no salvage used as qualification",
    }
    atomic(EVIDENCE / "AS012_BOUNDEDNESS_PROTOCOL_FAILURE.json", failure)
    retained = {str(path.relative_to(RETAINED)): {"bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(RETAINED.iterdir()) if path.is_file()}
    recon = {
        "schema": "AS012_FINAL_RECONCILIATION_V1", "directive": "UMBRA-AS-012", "baseline": BASELINE, "final_commit": head,
        "terminal_verdict": "AS012_PROTOCOL_FAIL", "inherited_valid": {"as007_known_r1": "PASS", "as010_full_config_population": "32/32", "as010_full_config_lifecycle": "PASS — 500 ticks"},
        "as011": "AS011_PROTOCOL_FAIL permanent; exact-entrypoint and matched-ablation defects inherited and repaired only in AS012 pre-lock harness",
        "as012": {"preflight": "PASS", "protected_tests": "28 passed twice", "fresh_boundedness": "post-lock result-publication protocol failure after 100000 ticks", "real_time_soak": "NOT RUN", "causal_ablation": "NOT RUN"},
        "boundedness": {"execution_ticks": 100000, "result_reduction": "NOT PUBLISHED", "qualification": "NOT ESTABLISHED", "retained_copy": retained},
        "counts": {"organism_creation": 1, "organism_load": 1, "organism_ticks": 100000, "control": 0, "shadow": 0, "diagnostic": 0, "retries": 0, "reseeds": 0, "successor_started": False},
        "production_delta": 0, "existing_test_semantic_delta": 0, "integrated_viability": "UNQUALIFIED", "close03": "BLOCKED", "recommendation": "Architect review required; no automatic successor or rerun",
    }
    atomic(EVIDENCE / "AS012_INTEGRATED_VIABILITY_RECONCILIATION.json", recon)
    files = []
    for path in sorted(EVIDENCE.iterdir()):
        if path.name == "AS012_EVIDENCE_MANIFEST.json" or not path.is_file():
            continue
        files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)})
    for path in sorted(RETAINED.iterdir()):
        files.append({"name": str(path.relative_to(EVIDENCE)), "bytes": path.stat().st_size, "sha256": sha(path)})
    manifest = {"schema": "AS012_EVIDENCE_MANIFEST_V1", "directive": "UMBRA-AS-012", "baseline": BASELINE, "final_commit": head, "terminal_verdict": "AS012_PROTOCOL_FAIL", "files": files, "counts": recon["counts"], "production_delta": 0, "readback": "All listed artifacts were hashed after durable publication; retained boundedness files are copies and original /tmp run was not modified.", "no_retry_reseed": True}
    atomic(EVIDENCE / "AS012_EVIDENCE_MANIFEST.json", manifest)
    print(json.dumps({"final_commit": head, "terminal_verdict": "AS012_PROTOCOL_FAIL", "manifest_sha256": sha(EVIDENCE / "AS012_EVIDENCE_MANIFEST.json"), "files": len(files)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
