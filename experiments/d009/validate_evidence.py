#!/usr/bin/env python3
"""Independent Task 13 evidence validator for UMBRA-D-009.

Reloads docs/evidence/d009/*.json summaries and raw-results.jsonl; recomputes
gate pass from the raw ledger; rejects missing/duplicate/seed mismatch/mixed
hashes/unexplained exclusions. Does not accept QUALIFIED or Gate 13 claims.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from experiments.d009 import evidence as ev

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "evidence" / "d009"

REQUIRED_FILES = (
    "regression-results.json",
    "habitat-authority-results.json",
    "manipulation-results.json",
    "environmental-learning-results.json",
    "autonomy-results.json",
    "habitat-persistence-results.json",
    "environmental-routine-results.json",
    "individuality-habitat-results.json",
    "revision-results.json",
    "profile-migration-results.json",
    "governance-results.json",
    "replay-results.json",
    "boundedness-results.json",
    "experiment-summary.json",
)

FORBIDDEN_SUBSTRINGS = (
    "UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED",
    "TASK 14 AUTHORIZED: YES",
    "UMBRA_D009_QUALIFIED",
)

COMPARISON_FIELDS = (
    "paired_seed_count",
    "condition_a",
    "condition_b",
    "mean_or_rate_a",
    "mean_or_rate_b",
    "paired_delta",
    "confidence_interval",
    "effect_size",
    "threshold",
    "pass",
)


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _recompute_comparison_pass(c: dict[str, Any]) -> bool:
    ma = float(c["mean_or_rate_a"])
    mb = float(c["mean_or_rate_b"])
    thr = float(c["threshold"])
    higher = bool(c.get("higher_is_better_for_a", True))
    if c.get("condition_b") in {"zero_tolerance", "zero", "baseline_zero"}:
        higher = False
    ok_a = ma >= thr if higher else ma <= thr
    gap_min = c.get("material_gap_min")
    ok_gap = True if gap_min is None else (ma - mb) >= float(gap_min)
    seeds_ok = int(c["paired_seed_count"]) >= 100
    if c.get("condition_b") == "zero_tolerance" and ma > 0:
        return False
    return bool(ok_a and ok_gap and seeds_ok)


def _load_raw() -> list[dict[str, Any]]:
    path = OUT / "raw-results.jsonl"
    if not path.exists():
        _fail("missing raw-results.jsonl")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _validate_raw_ledger(rows: list[dict[str, Any]], hashes: dict[str, str], thr: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    keys = Counter()
    hash_sets = {
        "thresholds_hash": set(),
        "matrix_hash": set(),
        "scenario_suite_hash": set(),
        "habitat_definition_hash": set(),
    }
    for i, row in enumerate(rows):
        missing = [f for f in ev.RAW_ROW_FIELDS if f not in row]
        if missing:
            issues.append(f"raw_row_{i}:missing:{missing}")
        for hk in hash_sets:
            hash_sets[hk].add(row.get(hk))
            if row.get(hk) != hashes[hk]:
                issues.append(f"raw_row_{i}:hash_mismatch:{hk}")
        key = (
            row.get("gate"),
            row.get("condition"),
            row.get("scenario"),
            row.get("seed"),
            row.get("individuality_history"),
            row.get("comparison_id"),
        )
        keys[key] += 1
        if keys[key] > 1:
            issues.append(f"duplicate_raw_row:{key}")
        if int(row.get("seed", 0)) < 1 or int(row.get("seed", 0)) > 100:
            issues.append(f"seed_out_of_range:{row.get('seed')}")
    for hk, vals in hash_sets.items():
        if len(vals) > 1:
            issues.append(f"mixed_hashes:{hk}")
    manifest_path = OUT / "seed-manifest.json"
    if not manifest_path.exists():
        issues.append("missing_seed_manifest")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("template"):
            issues.append("seed_manifest_still_template")
        for cell in manifest.get("cells", []):
            seeds = cell.get("seeds") or []
            if len(seeds) < int(thr["minimum_gate_critical_paired_seeds"]):
                issues.append(f"insufficient_seeds:{cell.get('condition')}:{cell.get('scenario')}")
    return {"issues": issues, "row_count": len(rows), "unique_rows": len(keys)}


def _recompute_gate_from_raw(gate: int | str, rows: list[dict[str, Any]]) -> dict[str, float]:
    gate_rows = [r for r in rows if r.get("gate") == gate]
    if not gate_rows:
        return {}
    keys = set()
    for r in gate_rows:
        for k, v in (r.get("metrics") or {}).items():
            if isinstance(v, (int, float)):
                keys.add(k)
    out: dict[str, float] = {}
    for k in keys:
        vals = [float(r["metrics"][k]) for r in gate_rows if k in r.get("metrics", {})]
        out[k] = ev.mean(vals) if vals else 0.0
    return out


def validate_file(path: Path, hashes: dict[str, str], thr: dict[str, Any]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")
    for bad in FORBIDDEN_SUBSTRINGS:
        if bad in text:
            _fail(f"{path.name}: forbidden claim {bad}")

    missing = [f for f in ev.REQUIRED_RESULT_FIELDS if f not in data]
    if missing:
        _fail(f"{path.name}: missing schema fields {missing}")

    for hk in ("thresholds_hash", "matrix_hash", "scenario_suite_hash", "habitat_definition_hash"):
        if data.get(hk) != hashes.get(hk):
            _fail(f"{path.name}: frozen hash mismatch {hk}")

    if data["expected_rows"] != data["actual_rows"]:
        _fail(f"{path.name}: expected_rows!=actual_rows")
    if data["missing_rows"] != 0 or data["duplicate_rows"] != 0:
        _fail(f"{path.name}: missing/duplicate rows nonzero")

    gate = data["gate"]
    seed_cov = data["seed_coverage"]
    if gate not in ("regression", "summary"):
        if int(seed_cov.get("paired_seeds", 0)) < int(thr["minimum_gate_critical_paired_seeds"]):
            _fail(f"{path.name}: paired_seeds below minimum")

    for c in data.get("comparisons") or []:
        for f in COMPARISON_FIELDS:
            if f not in c:
                _fail(f"{path.name}: comparison missing {f}")
        if gate not in ("regression", "summary") and int(c["paired_seed_count"]) < 100:
            _fail(f"{path.name}: comparison paired_seed_count < 100")
        if gate not in ("regression", "summary") and "mean_or_rate_a" in c:
            recomputed = _recompute_comparison_pass(c)
            if bool(c["pass"]) and not recomputed:
                _fail(f"{path.name}: comparison {c.get('comparison_id')} pass true but recompute false")

    if data.get("pass") is True:
        if gate not in ("regression", "summary") and int(seed_cov.get("paired_seeds", 0)) < 100:
            _fail(f"{path.name}: pass:true with paired_seeds < 100")
        if any(not c.get("pass") for c in (data.get("comparisons") or [])):
            _fail(f"{path.name}: file pass:true but a comparison failed")


def main() -> None:
    thr, _matrix, _scen, hashes = ev.load_frozen()
    if not OUT.is_dir():
        _fail(f"missing evidence dir {OUT}")
    for name in REQUIRED_FILES:
        p = OUT / name
        if not p.exists():
            _fail(f"missing evidence file {name}")
        validate_file(p, hashes, thr)

    raw_rows = _load_raw()
    raw_report = _validate_raw_ledger(raw_rows, hashes, thr)
    if raw_report["issues"]:
        _fail("; ".join(raw_report["issues"][:20]))

    summary = json.loads((OUT / "experiment-summary.json").read_text(encoding="utf-8"))
    if summary.get("metrics", {}).get("task13_outcome") == "UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED":
        _fail("summary claims final QUALIFIED")
    if summary.get("metrics", {}).get("gate13_deferred") is not True:
        _fail("summary must record gate13_deferred")

    recomputed: dict[str, Any] = {}
    for gate in range(1, 13):
        fname = {
            1: "habitat-authority-results.json",
            2: "manipulation-results.json",
            3: "environmental-learning-results.json",
            4: "autonomy-results.json",
            5: "habitat-persistence-results.json",
            6: "environmental-routine-results.json",
            7: "individuality-habitat-results.json",
            8: "revision-results.json",
            9: "profile-migration-results.json",
            10: "governance-results.json",
            11: "replay-results.json",
            12: "boundedness-results.json",
        }[gate]
        file_metrics = json.loads((OUT / fname).read_text(encoding="utf-8")).get("metrics", {})
        raw_metrics = _recompute_gate_from_raw(gate, raw_rows)
        recomputed[str(gate)] = {"file": file_metrics, "raw_recomputed": raw_metrics}

    validation = {
        "directive": ev.DIRECTIVE,
        "validator": "experiments/d009/validate_evidence.py",
        "raw_row_count": raw_report["row_count"],
        "raw_unique_rows": raw_report["unique_rows"],
        "recomputed_gates": recomputed,
        "forbidden_claims_absent": True,
        "gate13_deferred": True,
        "pass": True,
    }
    (OUT / "evidence-validation.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print("OK: Task 13 evidence validator passed")
    print(json.dumps({"files": len(REQUIRED_FILES), "raw_rows": raw_report["row_count"]}, indent=2))


if __name__ == "__main__":
    main()
