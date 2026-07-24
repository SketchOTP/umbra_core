"""Task 13 evidence envelope helpers — schema, hashing, stats, preflight, raw ledger."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments" / "d009"
OUT = ROOT / "docs" / "evidence" / "d009"

DIRECTIVE = "UMBRA-D-009"
AGENT_MEMORY = "D-20260724-task13-d009-experiment-harness"
FREEZE_COMMIT = "4e6c769f916fb7e8d0ca9ce42ddd0462c8654f3b"

REQUIRED_RESULT_FIELDS = (
    "directive",
    "agent_memory_directive",
    "software_commit",
    "generated_at",
    "thresholds_hash",
    "matrix_hash",
    "scenario_suite_hash",
    "habitat_definition_hash",
    "affordance_definition_hashes",
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
    "individuality_history",
    "comparison_id",
    "gate",
    "software_commit",
    "thresholds_hash",
    "matrix_hash",
    "scenario_suite_hash",
    "habitat_definition_hash",
    "affordance_definition_hashes",
    "profile_definition_hashes",
    "metrics",
    "terminal_outcome",
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def software_commit() -> str:
    return (
        subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True)
        .strip()
    )


def git_clean() -> bool:
    out = subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--porcelain"], text=True
    ).strip()
    return out == ""


def freeze_commit_ok() -> bool:
    """HEAD must contain the Stage B freeze commit unmodified."""
    try:
        subprocess.check_call(
            [
                "git",
                "-C",
                str(ROOT),
                "merge-base",
                "--is-ancestor",
                FREEZE_COMMIT,
                "HEAD",
            ],
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
    habitat_def = json.loads((EXP / "habitat-definition.json").read_text(encoding="utf-8"))
    hashes = {
        "thresholds_hash": file_sha256(EXP / "thresholds.json"),
        "matrix_hash": file_sha256(EXP / "experiment-matrix.json"),
        "scenario_suite_hash": file_sha256(EXP / "scenario-suite.json"),
        "habitat_definition_hash": thr.get("habitat_definition_hash", ""),
        "affordance_definition_hashes": thr.get("affordance_definition_hashes", {}),
        "profile_definition_hashes": thr.get("d009_production_profile_definition_hashes", {}),
        "habitat_definition_hash_expected": habitat_def.get("definition_hash"),
    }
    return thr, matrix, scen, hashes


def verify_definition_hashes(thr: dict[str, Any], hashes: dict[str, str]) -> None:
    if hashes["habitat_definition_hash"] != thr.get("habitat_definition_hash"):
        raise SystemExit("preflight_fail:habitat_definition_hash_mismatch")
    if hashes["habitat_definition_hash_expected"] != thr.get("habitat_definition_hash"):
        raise SystemExit("preflight_fail:habitat_definition_file_hash_mismatch")
    for hid, hval in thr.get("d009_production_profile_definition_hashes", {}).items():
        if "PLACEHOLDER" in str(hval):
            raise SystemExit(f"preflight_fail:unresolved_placeholder:{hid}")
    for hid, hval in thr.get("d008_production_profile_definition_hashes", {}).items():
        if "PLACEHOLDER" in str(hval):
            raise SystemExit(f"preflight_fail:unresolved_placeholder:d008:{hid}")
    aff = thr.get("affordance_definition_hashes", {})
    for aid, hval in aff.items():
        if "PLACEHOLDER" in str(hval):
            raise SystemExit(f"preflight_fail:unresolved_placeholder:{aid}")


def preflight(
    thr: dict[str, Any],
    hashes: dict[str, str],
    paired_seeds: int,
    *,
    allow_smoke: bool = False,
    require_clean: bool = True,
) -> None:
    """Fail closed before any pass evidence is written."""
    if not freeze_commit_ok():
        raise SystemExit(f"preflight_fail:freeze_commit_not_ancestor:{FREEZE_COMMIT}")
    if require_clean and not git_clean():
        raise SystemExit("preflight_fail:uncommitted_source_changes")
    min_seeds = int(thr["minimum_gate_critical_paired_seeds"])
    if paired_seeds < min_seeds and not allow_smoke:
        raise SystemExit(f"preflight_fail:paired_seeds={paired_seeds}<{min_seeds}")
    verify_definition_hashes(thr, hashes)
    live = {
        "thresholds_hash": file_sha256(EXP / "thresholds.json"),
        "matrix_hash": file_sha256(EXP / "experiment-matrix.json"),
        "scenario_suite_hash": file_sha256(EXP / "scenario-suite.json"),
    }
    for key in ("thresholds_hash", "matrix_hash", "scenario_suite_hash"):
        if live[key] != hashes[key]:
            raise SystemExit(f"preflight_fail:frozen_hash_drift:{key}")
    # Refuse unknown failure codes in thresholds manifest.
    known = set(thr.get("stable_failure_codes", []))
    for bucket in ("adapter_failure_codes", "habitat_failure_codes"):
        for code in thr.get(bucket, []):
            if code not in known:
                raise SystemExit(f"preflight_fail:unknown_failure_code:{code}")


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
        "habitat_definition_hash": hashes["habitat_definition_hash"],
        "affordance_definition_hashes": hashes["affordance_definition_hashes"],
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
    if payload.get("pass") and int(payload.get("seed_coverage", {}).get("paired_seeds", 0)) < 100:
        raise SystemExit(f"refuse_pass_below_100_seeds:{name}")
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
    individuality_history: str = "H0",
) -> dict[str, Any]:
    row = {
        "condition": condition,
        "scenario": scenario,
        "seed": seed,
        "individuality_history": individuality_history,
        "comparison_id": comparison_id,
        "gate": gate,
        "software_commit": commit,
        "thresholds_hash": hashes["thresholds_hash"],
        "matrix_hash": hashes["matrix_hash"],
        "scenario_suite_hash": hashes["scenario_suite_hash"],
        "habitat_definition_hash": hashes["habitat_definition_hash"],
        "affordance_definition_hashes": hashes["affordance_definition_hashes"],
        "profile_definition_hashes": hashes["profile_definition_hashes"],
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


def write_seed_manifest(
    *,
    cells: list[dict[str, Any]],
    hashes: dict[str, str],
    commit: str,
) -> dict[str, Any]:
    manifest = {
        "version": 1,
        "directive": DIRECTIVE,
        "frozen_before_execution": True,
        "template": False,
        "minimum_gate_critical_paired_seeds": 100,
        "paired_seed_range": [1, 100000],
        "freeze_commit_sha": FREEZE_COMMIT,
        "software_commit": commit,
        "thresholds_hash": hashes["thresholds_hash"],
        "matrix_hash": hashes["matrix_hash"],
        "scenario_suite_hash": hashes["scenario_suite_hash"],
        "habitat_definition_hash": hashes["habitat_definition_hash"],
        "affordance_definition_hashes": hashes["affordance_definition_hashes"],
        "profile_migration_hashes": json.loads(
            (EXP / "thresholds.json").read_text(encoding="utf-8")
        ).get("profile_migration_hashes", {}),
        "cells": cells,
    }
    (OUT / "seed-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
