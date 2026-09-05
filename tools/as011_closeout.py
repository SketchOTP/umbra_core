"""Publish the AS-011 post-lock protocol-failure closeout."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-011-boundedness-evidence-recovery-r1")
BASELINE = "bcd5ff361a22288480dd16cf20e3aad432bda26e"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write((json.dumps(value, indent=2, sort_keys=True) + "\n").encode()); handle.flush(); os.fsync(handle.fileno())
    if path.exists(): tmp.unlink(missing_ok=True); return
    os.replace(tmp, path)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    head = git("rev-parse", "HEAD")
    failure = {"schema": "AS011_BOUNDEDNESS_PROTOCOL_FAILURE_V1", "directive": "UMBRA-AS-011", "baseline": BASELINE, "terminal_verdict": "AS011_PROTOCOL_FAIL", "classification": "POST_LOCK_HARNESS_PROTOCOL_FAILURE", "job_id": "job-mtogx0pk-4c4dc451", "command": "/home/sketch/cs14n-runtime/bin/python -m experiments.as011.downstream --mode boundedness --seed 10046820 --work /tmp/as011-boundedness-r1 --output /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-011-boundedness-evidence-recovery-r1/AS011_BOUNDEDNESS_RESULT.json", "working_directory": str(ROOT), "started_at": "2026-09-05T14:18:20.539Z", "completed_at": "2026-09-05T14:18:20.730Z", "exit_code": 1, "exception_type": "NameError", "exception": "name 'bounded' is not defined", "source": "experiments/as011/downstream.py:98", "phase": "frozen fresh boundedness invocation", "pre_lock": False, "organism_creation": 0, "organism_load": 0, "organism_ticks": 0, "retry": False, "reseed": False, "result_published": False, "stderr": "Traceback: boundedness() called initialize(seed, db, bounded=bounded, route_learning=route); NameError before initialize returned."}
    atomic(EVIDENCE / "AS011_BOUNDEDNESS_PROTOCOL_FAILURE.json", failure)
    reconciliation = {"schema": "AS011_FINAL_RECONCILIATION_V1", "directive": "UMBRA-AS-011", "baseline": BASELINE, "final_commit": head, "terminal_verdict": "AS011_PROTOCOL_FAIL", "inherited_valid": {"as007_known_r1": "500/500 and 3500/3500", "as007_known_r1_s16": "7200/7200", "as010_full_config_population": "32/32", "as010_full_config_lifecycle": "PASS — 500 ticks"}, "as010_retained_boundedness": "real 100000 ticks / 521416 events, not qualified; retained evidence insufficient", "as011": {"phase0": "PASS", "config_equivalence": "PASS", "terminal_evidence_preflight": "PASS", "protected_tests": "27/27 twice", "fresh_boundedness": "post-lock protocol failure before organism creation", "real_time_soak": "NOT RUN", "causal_ablation": "NOT RUN"}, "counts": {"organism_creation": 0, "organism_load": 0, "organism_ticks": 0, "control": 0, "shadow": 0, "diagnostic": 0, "retries": 0, "reseeds": 0, "successor_started": False}, "production_delta": 0, "existing_test_semantic_delta": 0, "integrated_viability": "UNQUALIFIED", "close03": "BLOCKED", "recommendation": "No successor automatically started; Architect review required before any future repair or rerun."}
    atomic(EVIDENCE / "AS011_FINAL_RECONCILIATION.json", reconciliation)
    files = []
    for path in sorted(EVIDENCE.rglob("*")):
        if path.is_file() and path.name != "AS011_EVIDENCE_MANIFEST.json":
            files.append({"path": str(path.relative_to(EVIDENCE)), "bytes": path.stat().st_size, "sha256": sha(path)})
    manifest = {"schema": "AS011_EVIDENCE_MANIFEST_V1", "directive": "UMBRA-AS-011", "baseline": BASELINE, "final_commit": head, "terminal_verdict": "AS011_PROTOCOL_FAIL", "files": files, "counts": reconciliation["counts"], "production_delta": 0, "readback": "Each listed file hashed after durable publication; historical AS-010 root untouched."}
    atomic(EVIDENCE / "AS011_EVIDENCE_MANIFEST.json", manifest)
    print(json.dumps({"final_commit": head, "terminal_verdict": "AS011_PROTOCOL_FAIL", "manifest_sha256": sha(EVIDENCE / "AS011_EVIDENCE_MANIFEST.json"), "files": len(files)}, indent=2, sort_keys=True))


if __name__ == "__main__": main()
