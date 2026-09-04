"""AS-010 full-configuration R0-R3 population runner.

R0/R1 use the established D-014 regime loop with its configuration binding
replaced by the AS-010 factory. R2/R3 use the already repaired HabitatEngine
authority loop, likewise with only its configuration binding replaced.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

from experiments.as010.full_config import as010_config
from experiments.d014 import run_formal as d014
from experiments.as009 import qualification as as009

DIRECTIVE = "UMBRA-AS-010"
BASELINE = "b5c7bb2b46e9355a8f5b658f25ebf4f1e7fea27b"
HORIZON = 7200
REGIMES = ("R0", "R1", "R2", "R3")


def durable_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if path.exists():
        raise FileExistsError(path)
    os.replace(tmp, path)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _with_config(module: Any, call: Any, regime: str, seed: int, work: Path, horizon: int) -> dict[str, Any]:
    original = module.config
    module.config = lambda case_seed, case_db, case_regime: as010_config(case_seed, case_db, case_regime)
    try:
        row = call(regime, seed, work, horizon)
    finally:
        module.config = original
    row.update({"directive": DIRECTIVE, "baseline": BASELINE, "configuration": "AS010_FULL"})
    return row


def run_case(regime: str, seed: int, work: Path, horizon: int = HORIZON) -> dict[str, Any]:
    if regime in ("R0", "R1"):
        return _with_config(d014, d014.run_case, regime, seed, work, horizon)
    return _with_config(as009, as009.run_case, regime, seed, work, horizon)


def execute(manifest: Path, work: Path, output: Path) -> dict[str, Any]:
    value = json.loads(manifest.read_text())
    if value.get("directive") != DIRECTIVE or value.get("baseline") != BASELINE:
        raise SystemExit("AS010_FORMAL_MANIFEST_IDENTITY_FAIL")
    regimes = value.get("regimes")
    if tuple(regimes) != REGIMES or any(len(regimes[r]) != 8 for r in REGIMES):
        raise SystemExit("AS010_FORMAL_MANIFEST_SHAPE_FAIL")
    work.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, Any]] = []
    try:
        for regime in REGIMES:
            for index, seed in enumerate(regimes[regime]):
                row = run_case(regime, int(seed), work, HORIZON)
                row.update({"stage": f"FORMAL_{regime}", "seed_index": index})
                rows.append(row)
                with output.with_name("AS010_FORMAL_RUN_SUMMARIES.jsonl").open("a") as handle:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                if row.get("terminal") != "completed":
                    result = {"schema": "AS010_FORMAL_POPULATION_V1", "directive": DIRECTIVE, "baseline": BASELINE, "expected_runs": 32, "completed_runs": len(rows), "terminal": f"AS010_FRESH_{regime}_FAIL", "rows": rows}
                    durable_json(output, result)
                    return result
        result = {"schema": "AS010_FORMAL_POPULATION_V1", "directive": DIRECTIVE, "baseline": BASELINE, "expected_runs": 32, "completed_runs": len(rows), "all_completed": True, "rows": rows}
        durable_json(output, result)
        return result
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.manifest, args.work, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
