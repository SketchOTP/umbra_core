"""D-010 evidence envelope helpers — schema, hashing, stats, preflight, raw ledger."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiments.d010 import stage_a as sa

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments" / "d010"
OUT = ROOT / "docs" / "evidence" / "d010"

DIRECTIVE = "UMBRA-D-010"
AGENT_MEMORY = "D-20260724-1527-d010-task12-stage-b-freeze"
FREEZE_COMMIT: str | None = None  # Stage B Task 12 records freeze tip

REQUIRED_RESULT_FIELDS = (
    "directive",
    "agent_memory_directive",
    "software_commit",
    "generated_at",
    "thresholds_hash",
    "matrix_hash",
    "scenario_suite_hash",
    "stage_a_bundle_hash",
    "failure_code_registry_hash",
    "gate",
    "conditions",
    "scenarios",
    "seed_coverage",
    "expected_rows",
    "actual_rows",
    "missing_rows",
    "duplicate_rows",
    "metrics",
    "thresholds",
    "comparisons",
    "pass",
    "deviations",
)

RAW_ROW_FIELDS = (
    "condition",
    "scenario",
    "seed",
    "comparison_id",
    "gate",
    "software_commit",
    "thresholds_hash",
    "matrix_hash",
    "scenario_suite_hash",
    "stage_a_bundle_hash",
    "failure_code_registry_hash",
    "metrics",
    "terminal_outcome",
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def software_commit() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def git_clean() -> bool:
    out = subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--porcelain"], text=True
    ).strip()
    return out == ""


def freeze_commit_ok() -> bool:
    if not FREEZE_COMMIT:
        return False
    try:
        subprocess.check_call(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", FREEZE_COMMIT, "HEAD"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def load_frozen() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str]]:
    thr = json.loads((EXP / "thresholds.json").read_text(encoding="utf-8"))
    matrix = json.loads((EXP / "experiment-matrix.json").read_text(encoding="utf-8"))
    scen = json.loads((EXP / "scenario-suite.json").read_text(encoding="utf-8"))
    stage_payload = json.loads((EXP / "stage-a-hashes.json").read_text(encoding="utf-8"))
    hashes = {
        "thresholds_hash": file_sha256(EXP / "thresholds.json"),
        "matrix_hash": file_sha256(EXP / "experiment-matrix.json"),
        "scenario_suite_hash": file_sha256(EXP / "scenario-suite.json"),
        "stage_a_bundle_hash": str(stage_payload.get("bundle_hash", "")),
        "failure_code_registry_hash": file_sha256(EXP / "failure-code-registry.json"),
        "elapsed_contract_registry_hash": file_sha256(EXP / "elapsed-contract-registry.json"),
    }
    return thr, matrix, scen, hashes


def verify_stage_a_hashes(hashes: dict[str, str]) -> None:
    live = sa.compute_stage_a_hashes()
    sa.assert_no_placeholder_hashes(live)
    bundle = json.loads((EXP / "stage-a-hashes.json").read_text(encoding="utf-8"))
    if bundle.get("bundle_hash") != hashes["stage_a_bundle_hash"]:
        raise SystemExit("preflight_fail:stage_a_bundle_hash_mismatch")
    for key, expected in live.items():
        if file_sha256(ROOT / key) != expected:
            raise SystemExit(f"preflight_fail:stage_a_drift:{key}")


def verify_failure_codes(thr: dict[str, Any]) -> None:
    registry = json.loads((EXP / "failure-code-registry.json").read_text(encoding="utf-8"))
    known = set(registry.get("stable_failure_codes", []))
    for bucket in ("downtime_failure_codes", "elapsed_contract_failure_codes"):
        for code in thr.get(bucket, []):
            if code not in known:
                raise SystemExit(f"preflight_fail:unknown_failure_code:{code}")
    for code in thr.get("stable_failure_codes", []):
        if code not in known:
            raise SystemExit(f"preflight_fail:threshold_unknown_failure_code:{code}")


def preflight(
    thr: dict[str, Any],
    hashes: dict[str, str],
    paired_seeds: int,
    *,
    allow_smoke: bool = False,
    require_clean: bool = True,
    require_freeze: bool = False,
) -> None:
    if require_freeze and not freeze_commit_ok():
        raise SystemExit(f"preflight_fail:freeze_commit_not_ancestor:{FREEZE_COMMIT}")
    if require_clean and not git_clean():
        raise SystemExit("preflight_fail:uncommitted_source_changes")
    min_seeds = int(thr["minimum_gate_critical_paired_seeds"])
    if paired_seeds < min_seeds and not allow_smoke:
        raise SystemExit(f"preflight_fail:paired_seeds={paired_seeds}<{min_seeds}")
    verify_stage_a_hashes(hashes)
    verify_failure_codes(thr)
    sa.validate_seed_nonoverlap()
    manifest_errors = sa.validate_test_manifest_complete()
    if manifest_errors:
        raise SystemExit(f"preflight_fail:test_manifest:{manifest_errors[0]}")
    for rel in sa.STAGE_A_ARTIFACTS:
        blob = (EXP / rel).read_text(encoding="utf-8")
        if "PLACEHOLDER" in blob:
            raise SystemExit(f"preflight_fail:placeholder_in_stage_a:{rel}")


def mean(xs: list[float]) -> float:
    return float(statistics.mean(xs)) if xs else 0.0


def paired_ci(deltas: list[float], confidence: float = 0.95) -> list[float]:
    n = len(deltas)
    if n < 2:
        return [0.0, 0.0]
    m = mean(deltas)
    sd = statistics.stdev(deltas)
    z = 1.96 if confidence >= 0.95 else 1.645
    half = z * (sd / math.sqrt(n))
    return [m - half, m + half]


def effect_size_cohens_dz(deltas: list[float]) -> float:
    if len(deltas) < 2:
        return 0.0
    sd = statistics.stdev(deltas)
    if sd == 0.0:
        return 0.0
    return mean(deltas) / sd


def comparison(
    *,
    comparison_id: str,
    condition_a: str,
    condition_b: str,
    values_a: list[float],
    values_b: list[float],
    threshold: float,
    higher_is_better_for_a: bool = True,
    material_gap_min: float | None = None,
    ci_confidence: float = 0.95,
) -> dict[str, Any]:
    if len(values_a) != len(values_b):
        raise ValueError(f"paired_length_mismatch:{comparison_id}:{len(values_a)}!={len(values_b)}")
    deltas = [a - b for a, b in zip(values_a, values_b)]
    ma, mb = mean(values_a), mean(values_b)
    gap = ma - mb
    ok_a = ma >= threshold if higher_is_better_for_a else ma <= threshold
    ok_gap = True if material_gap_min is None else gap >= material_gap_min
    return {
        "comparison_id": comparison_id,
        "paired_seed_count": len(values_a),
        "condition_a": condition_a,
        "condition_b": condition_b,
        "mean_or_rate_a": ma,
        "mean_or_rate_b": mb,
        "paired_delta": gap,
        "confidence_interval": paired_ci(deltas, ci_confidence),
        "effect_size": effect_size_cohens_dz(deltas),
        "threshold": threshold,
        "material_gap_min": material_gap_min,
        "higher_is_better_for_a": higher_is_better_for_a,
        "pass": bool(ok_a and ok_gap and len(values_a) >= 100),
    }


def envelope(
    *,
    gate: int | str,
    conditions: list[str],
    scenarios: list[str],
    seed_coverage: dict[str, Any],
    expected_rows: int,
    actual_rows: int,
    metrics: dict[str, Any],
    thresholds: dict[str, Any],
    comparisons: list[dict[str, Any]],
    hashes: dict[str, str],
    commit: str,
    deviations: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    missing = max(0, expected_rows - actual_rows)
    duplicate = max(0, actual_rows - expected_rows)
    comps_ok = all(c.get("pass") for c in comparisons) if comparisons else True
    row_ok = missing == 0 and duplicate == 0 and actual_rows == expected_rows
    seeds_ok = int(seed_coverage.get("paired_seeds", 0)) >= 100
    payload = {
        "directive": DIRECTIVE,
        "agent_memory_directive": AGENT_MEMORY,
        "software_commit": commit,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds_hash": hashes["thresholds_hash"],
        "matrix_hash": hashes["matrix_hash"],
        "scenario_suite_hash": hashes["scenario_suite_hash"],
        "stage_a_bundle_hash": hashes["stage_a_bundle_hash"],
        "failure_code_registry_hash": hashes["failure_code_registry_hash"],
        "gate": gate,
        "conditions": conditions,
        "scenarios": scenarios,
        "seed_coverage": seed_coverage,
        "expected_rows": expected_rows,
        "actual_rows": actual_rows,
        "missing_rows": missing,
        "duplicate_rows": duplicate,
        "metrics": metrics,
        "thresholds": thresholds,
        "comparisons": comparisons,
        "pass": bool(comps_ok and row_ok and seeds_ok),
        "deviations": deviations or [],
    }
    if extra:
        payload.update(extra)
    if not row_ok or not seeds_ok:
        payload["pass"] = False
        if not seeds_ok:
            payload["deviations"] = list(payload["deviations"]) + ["paired_seeds_below_100"]
        if not row_ok:
            payload["deviations"] = list(payload["deviations"]) + ["row_count_mismatch"]
    return payload


def dump(name: str, payload: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    missing = [f for f in REQUIRED_RESULT_FIELDS if f not in payload]
    if missing:
        raise SystemExit(f"evidence_schema_incomplete:{name}:{missing}")
    (OUT / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def raw_row(
    *,
    condition: str,
    scenario: str,
    seed: int,
    gate: int | str,
    comparison_id: str,
    metrics: dict[str, Any],
    terminal_outcome: str,
    hashes: dict[str, str],
    commit: str,
) -> dict[str, Any]:
    row = {
        "condition": condition,
        "scenario": scenario,
        "seed": seed,
        "comparison_id": comparison_id,
        "gate": gate,
        "software_commit": commit,
        "thresholds_hash": hashes["thresholds_hash"],
        "matrix_hash": hashes["matrix_hash"],
        "scenario_suite_hash": hashes["scenario_suite_hash"],
        "stage_a_bundle_hash": hashes["stage_a_bundle_hash"],
        "failure_code_registry_hash": hashes["failure_code_registry_hash"],
        "metrics": metrics,
        "terminal_outcome": terminal_outcome,
    }
    missing = [f for f in RAW_ROW_FIELDS if f not in row]
    if missing:
        raise ValueError(f"raw_row_incomplete:{missing}")
    return row


def write_raw_ledger(rows: list[dict[str, Any]]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "raw-results.jsonl"
    lines = [json.dumps(r, sort_keys=True) for r in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path
