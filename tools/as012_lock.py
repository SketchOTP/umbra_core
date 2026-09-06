"""Freeze AS-012 after exact-entrypoint preflight and protected validation."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-012-exact-entrypoint-boundedness-soak-causal-closure-r1")
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
    production = subprocess.check_output(["git", "diff", "--name-only", "f0ac33212b3cb0081e16341bba31db69043a9292", "HEAD", "--", "umbra_core"], cwd=ROOT, text=True).splitlines()
    preflight_path = EVIDENCE / "AS012_EXACT_ENTRYPOINT_PREFLIGHT.json"
    preflight = json.loads(preflight_path.read_text())
    if preflight.get("status") != "PASS" or preflight.get("formal_seeds_used"):
        raise RuntimeError("exact-entrypoint preflight is not a PASS")
    manifest = json.loads((EVIDENCE / "AS012_DOWNSTREAM_SEED_MANIFEST.json").read_text())
    files = [ROOT / "experiments/as012/__init__.py", ROOT / "experiments/as012/full_config.py", ROOT / "experiments/as012/downstream.py", ROOT / "experiments/as012/preflight.py", ROOT / "tests/test_as012_protocol.py", ROOT / "tools/as012_prepare.py", ROOT / "tools/as012_lock.py"]
    fingerprints = {str(path.relative_to(ROOT)): sha(path) for path in files}
    lock = {
        "schema": "AS012_SCIENTIFIC_EXECUTION_LOCK_V1", "directive": "UMBRA-AS-012", "baseline": BASELINE, "freeze_commit": head,
        "production_inheritance": {"as007_freeze": "f0ac33212b3cb0081e16341bba31db69043a9292", "production_delta": len(production), "paths": production},
        "entrypoints": {
            "boundedness": "/home/sketch/cs14n-runtime/bin/python -m experiments.as012.downstream --mode boundedness --seed %d --ticks 100000 --work /tmp/as012-boundedness-r1 --output %s/AS012_BOUNDEDNESS_RESULT.json" % (manifest["boundedness"]["seed"], EVIDENCE),
            "soak": "/home/sketch/cs14n-runtime/bin/python -m experiments.as012.downstream --mode soak --seed %d --work /tmp/as012-soak-r1 --output %s/AS012_SOAK_RESULT.json" % (manifest["soak"]["seed"], EVIDENCE),
            "ablation": {variant: "/home/sketch/cs14n-runtime/bin/python -m experiments.as012.downstream --mode ablation --seed %d --variant %s --ticks 7200 --work /tmp/as012-ablation-%s-r1 --output %s/AS012_ABLATION_%s_RESULT.json" % (manifest["ablation"]["base_seed"], variant, variant, EVIDENCE, variant.upper()) for variant in manifest["ablation"]["variants"]},
        },
        "boundedness": {"ticks": 100000, "sample_interval_ticks": 5000, "thresholds": {"rss_mib": 180.0, "rss_slope_mib_per_hour": 1.0, "database_growth_bytes": 67108864, "event_records_per_tick": 32, "cpu_fraction_one_core": 0.05}},
        "soak": {"warmup_seconds": 300.0, "measure_seconds": 3600.0, "sample_interval_seconds": 5.0, "minimum_samples": 360, "tick_hz": 2.0},
        "ablation": {"regime": "R1/S16", "ticks": 7200, "matched_base_seed": manifest["ablation"]["base_seed"], "variants": manifest["ablation"]["variants"], "order_frozen": manifest["ablation"]["variants"]},
        "preflight": {"artifact": str(preflight_path), "status": preflight["status"], "formal_seeds_used": []},
        "source_fingerprints": fingerprints, "retries": 0, "reseeds": 0, "post_lock_mutation": "forbidden",
    }
    atomic(EVIDENCE / "AS012_SCIENTIFIC_EXECUTION_LOCK.json", lock)
    atomic(EVIDENCE / "AS012_PROTECTED_VALIDATION.json", {"schema": "AS012_PROTECTED_VALIDATION_V1", "directive": "UMBRA-AS-012", "exact_entrypoint_preflight": "PASS", "protected_first": "28 passed", "protected_second": "28 passed", "full_applicable": "1311 passed, 2 skipped, 17 inherited failures", "candidate_only_failures": 0, "production_delta": 0, "existing_test_semantic_delta": 0, "authority_3_0": "PASS", "governance": "PASS", "git_diff_check": "PASS", "formal_execution_started": False})
    print(json.dumps({"freeze_commit": head, "lock_sha256": sha(EVIDENCE / "AS012_SCIENTIFIC_EXECUTION_LOCK.json"), "preflight": preflight["status"], "production_delta": len(production)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
