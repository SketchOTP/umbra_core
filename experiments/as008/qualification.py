"""AS-008 runner with a seed-complete preflight before organism creation."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d014.run_formal import run_case as _run_case

DIRECTIVE = "UMBRA-AS-008"
BASELINE = "3e0fd74a37376dbb659ffb41d3d7d922f0a338bc"
HORIZON = 7200
REGIMES = ("R0", "R1", "R2", "R3")
EVIDENCE_ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-008-fresh-integrated-viability-r1")
HISTORICAL = EVIDENCE_ROOT / "AS008_HISTORICAL_SEED_REGISTRY.json"
FORMAL = EVIDENCE_ROOT / "AS008_FORMAL_SEED_MANIFEST.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def validate_seed_contract() -> dict[str, Any]:
    registry = load_json(HISTORICAL)
    manifest = load_json(FORMAL)
    historical = {int(seed) for seed in registry["seeds"]}
    seeds = manifest.get("seeds")
    if set(manifest) < {"directive", "baseline", "horizon_ticks", "runs", "seeds", "seed_status"}:
        raise ValueError("AS008_FORMAL_SEED_MANIFEST_INCOMPLETE")
    if manifest["directive"] != DIRECTIVE or manifest["baseline"] != BASELINE:
        raise ValueError("AS008_FORMAL_SEED_MANIFEST_IDENTITY_FAIL")
    if manifest["horizon_ticks"] != HORIZON or manifest["runs"] != 32:
        raise ValueError("AS008_FORMAL_SEED_MANIFEST_SHAPE_FAIL")
    if manifest["seed_status"] != "frozen_before_formal_execution":
        raise ValueError("AS008_FORMAL_SEED_MANIFEST_NOT_FROZEN")
    if not isinstance(seeds, dict) or tuple(seeds) != REGIMES:
        raise ValueError("AS008_REGIME_MAPPING_FAIL")
    flat = [int(seed) for regime in REGIMES for seed in seeds[regime]]
    if any(len(seeds[regime]) != 8 for regime in REGIMES):
        raise ValueError("AS008_FORMAL_SEED_COUNT_FAIL")
    if len(flat) != 32 or len(set(flat)) != 32:
        raise ValueError("AS008_FORMAL_SEED_DUPLICATE")
    overlap = sorted(set(flat) & historical)
    if overlap:
        raise ValueError(f"AS008_HISTORICAL_SEED_OVERLAP:{overlap}")
    return {
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "horizon_ticks": HORIZON,
        "formal_runs": 32,
        "regimes": {regime: list(map(int, seeds[regime])) for regime in REGIMES},
        "historical_seed_count": len(historical),
        "formal_seed_count": len(flat),
        "unique": True,
        "historical_overlap": [],
        "formal_manifest_sha256": sha256(FORMAL),
        "historical_registry_sha256": sha256(HISTORICAL),
    }


def preflight(output: Path) -> dict[str, Any]:
    result = {
        "schema": "AS008_DOWNSTREAM_PREFLIGHT_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "organism_creation": 0,
        "organism_ticks": 0,
        "formal_execution_started": False,
        "smoke_execution_started": False,
        "seed_source": "AS008_FORMAL_SEED_MANIFEST.json",
        "fallback_seed_sources": [],
        "status": "PASS",
    }
    result.update(validate_seed_contract())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def execute(work: Path, output: Path) -> dict[str, Any]:
    preflight_path = output.with_name("AS008_DOWNSTREAM_PREFLIGHT.json")
    preflight_result = load_json(preflight_path)
    if preflight_result.get("status") != "PASS" or preflight_result.get("organism_creation") != 0:
        raise SystemExit("AS008_DOWNSTREAM_PREFLIGHT_REQUIRED")
    contract = validate_seed_contract()
    rows: list[dict[str, Any]] = []
    started = time.time()
    seeds = contract["regimes"]
    for regime in REGIMES:
        for index, seed in enumerate(seeds[regime]):
            row = _run_case(regime, seed, work, HORIZON)
            row.update({"directive": DIRECTIVE, "stage": f"FORMAL_{regime}", "seed_index": index})
            rows.append(row)
            with (output.with_name("AS008_FORMAL_RUN_SUMMARIES.jsonl")).open("a") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            if row.get("terminal") != "completed":
                return {"schema": "AS008_FORMAL_REDUCTION_V1", "directive": DIRECTIVE, "baseline": BASELINE, "expected_runs": 32, "completed_runs": len(rows), "terminal": f"AS008_FRESH_{regime}_FAIL", "rows": rows, "started_at": started, "ended_at": time.time()}
    return {"schema": "AS008_FORMAL_REDUCTION_V1", "directive": DIRECTIVE, "baseline": BASELINE, "expected_runs": 32, "completed_runs": len(rows), "all_completed": True, "rows": rows, "started_at": started, "ended_at": time.time()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "execute"), required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "preflight":
        print(json.dumps(preflight(args.output), indent=2, sort_keys=True))
    else:
        result = execute(args.work, args.output)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        shutil.rmtree(args.work, ignore_errors=True)
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
