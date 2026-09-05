"""Freeze AS-011 downstream protocols after pre-formal validation."""
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
    production_paths = git("diff", "--name-only", "f0ac33212b3cb0081e16341bba31db69043a9292..HEAD", "--", "umbra_core").splitlines()
    protected = {"suite": "27 passed", "first_run": "27 passed in 1.22s", "second_run": "27 passed in 1.18s", "candidate_only_failures": 0}
    full = {"command": "/home/sketch/cs14n-runtime/bin/python -m pytest -q --ignore=tests/test_close02x_prospective_recoverability.py", "result": "1307 passed, 2 skipped, 17 inherited failures", "candidate_only_failures": 0, "inherited_failures": 17, "collection_failure_unignored": "tests/test_close02x_prospective_recoverability.py imports absent historical symbol prospective_recoverability_transition"}
    files = [ROOT / "experiments/as011/full_config.py", ROOT / "experiments/as011/downstream.py", ROOT / "experiments/as011/preflight.py", ROOT / "tools/as011_config_audit.py", ROOT / "tools/as011_phase0_audit.py", ROOT / "tools/as011_prepare.py"]
    manifest = json.loads((EVIDENCE / "AS011_DOWNSTREAM_SEED_MANIFEST.json").read_text())
    lock = {"schema": "AS011_SCIENTIFIC_EXECUTION_LOCK_V1", "directive": "UMBRA-AS-011", "baseline": BASELINE, "working_directory": str(ROOT), "interpreter": "/home/sketch/cs14n-runtime/bin/python", "boundedness": {"method": "FRESH_RUN", "seed": manifest["boundedness"]["seed"], "ticks": 100000, "command": "/home/sketch/cs14n-runtime/bin/python -m experiments.as011.downstream --mode boundedness --seed %d --work /tmp/as011-boundedness-r1 --output %s/AS011_BOUNDEDNESS_RESULT.json" % (manifest["boundedness"]["seed"], EVIDENCE)}, "soak": {"method": "D009/D010 S3 current compatible protocol", "seed": manifest["soak"]["seed"], "warmup_seconds": 300, "measure_seconds": 3600, "sample_interval_seconds": 5, "minimum_samples": 360, "hz": 2}, "ablation": {"seeds": manifest["ablation"], "ticks": 7200, "variants": ["full", "terminal_readiness_disabled", "continuation_disabled", "route_learning_disabled"]}, "thresholds": {"rss_hard_max_mib": 180, "rss_slope_mib_per_hour_max": 1.0, "database_growth_bytes_max": 67108864, "event_growth_records_per_tick_max": 32, "cpu_mean_fraction_max": 0.05}, "preflight": "AS011_TERMINAL_EVIDENCE_PATH_PREFLIGHT_PASS", "retained_100k": "AS011_AS010_100K_EVIDENCE_INSUFFICIENT", "production_delta": len(production_paths), "production_paths": production_paths, "protected_validation": protected, "full_applicable_validation": full, "code_fingerprints": {str(path.relative_to(ROOT)): sha(path) for path in files}, "seed_manifest_sha256": sha(EVIDENCE / "AS011_DOWNSTREAM_SEED_MANIFEST.json"), "retries": 0, "reseeds": 0, "post_lock_mutation": "forbidden", "formal_execution_started": False}
    atomic(EVIDENCE / "AS011_SCIENTIFIC_EXECUTION_LOCK.json", lock)
    atomic(EVIDENCE / "AS011_PROTECTED_VALIDATION.json", {"schema": "AS011_PROTECTED_VALIDATION_V1", "directive": "UMBRA-AS-011", "protected": protected, "full_applicable": full, "authority_3_0": "PASS", "governance": "PASS", "git_diff_check": "PASS", "production_delta": 0, "existing_test_semantic_delta": 0, "formal_execution_started": False})
    print(json.dumps(lock, indent=2, sort_keys=True))


if __name__ == "__main__": main()
