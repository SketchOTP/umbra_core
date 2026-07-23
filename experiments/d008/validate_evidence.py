#!/usr/bin/env python3
"""Independent Task 13 evidence validator.

Reloads all docs/evidence/d008/*.json result files and checks schema, coverage,
row integrity, frozen hashes, recomputed numeric gate pass, and absence of
Task 14 / QUALIFIED claims. Exits nonzero on any failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from experiments.d008 import evidence as ev

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "evidence" / "d008"

REQUIRED_FILES = (
    "action-expression-results.json",
    "condition-expression-results.json",
    "attention-results.json",
    "individuality-expression-results.json",
    "autonomy-results.json",
    "habitat-continuity-results.json",
    "body-independence-results.json",
    "governance-results.json",
    "nonverbal-signal-results.json",
    "no-scripted-personality-results.json",
    "replay-results.json",
    "render-coherence-results.json",
    "regression-results.json",
    "experiment-summary.json",
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

FORBIDDEN_SUBSTRINGS = (
    "UMBRA_D008_COHERENT_DIGITAL_EMBODIMENT_QUALIFIED",
    "TASK 14 AUTHORIZED: YES",
    "UMBRA_D008_QUALIFIED",
)


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _recompute_comparison_pass(c: dict[str, Any]) -> bool:
    """Recompute pass from means/threshold/gap when material_gap_min present."""
    ma = float(c["mean_or_rate_a"])
    mb = float(c["mean_or_rate_b"])
    thr = float(c["threshold"])
    higher = True
    # Heuristic: if condition_b is zero_tolerance / baseline_zero / min_* and
    # threshold is small with a < b expected for rates-to-beat-zero, check stored
    # higher_is_better via material_gap or explicit field.
    if "higher_is_better_for_a" in c:
        higher = bool(c["higher_is_better_for_a"])
    elif c.get("condition_b") in {
        "zero_tolerance",
        "baseline_zero",
        "zero_writes",
    }:
        higher = False
    ok_a = ma >= thr if higher else ma <= thr
    gap_min = c.get("material_gap_min")
    ok_gap = True if gap_min is None else (ma - mb) >= float(gap_min)
    seeds_ok = int(c["paired_seed_count"]) >= 100
    # Absolute-zero render keys: any positive mean fails regardless of CI.
    if c.get("condition_b") == "zero_tolerance" and ma > 0:
        return False
    return bool(ok_a and ok_gap and seeds_ok)


def validate_file(path: Path, hashes: dict[str, str], thr: dict[str, Any]) -> None:
    data = json.loads(path.read_text())
    text = path.read_text()
    for bad in FORBIDDEN_SUBSTRINGS:
        if bad in text:
            _fail(f"{path.name}: forbidden claim {bad}")

    missing = [f for f in ev.REQUIRED_RESULT_FIELDS if f not in data]
    if missing:
        _fail(f"{path.name}: missing schema fields {missing}")

    for hk in ("thresholds_hash", "matrix_hash", "scenario_suite_hash"):
        if data.get(hk) != hashes[hk]:
            _fail(f"{path.name}: frozen hash mismatch {hk}")

    if data["expected_rows"] != data["actual_rows"]:
        _fail(f"{path.name}: expected_rows!=actual_rows")
    if data["missing_rows"] != 0 or data["duplicate_rows"] != 0:
        _fail(f"{path.name}: missing/duplicate rows nonzero")

    seed_cov = data["seed_coverage"]
    gate = data["gate"]
    if gate != "regression":
        if int(seed_cov.get("paired_seeds", 0)) < int(thr["minimum_gate_critical_paired_seeds"]):
            _fail(f"{path.name}: paired_seeds below minimum")

    comps = data.get("comparisons") or []
    for c in comps:
        for f in COMPARISON_FIELDS:
            if f not in c:
                _fail(f"{path.name}: comparison missing {f}")
        if gate != "regression" and int(c["paired_seed_count"]) < 100:
            _fail(f"{path.name}: comparison paired_seed_count < 100")
        # Recompute numeric pass for non-regression comparisons with enough info.
        if gate != "regression" and "mean_or_rate_a" in c:
            recomputed = _recompute_comparison_pass(c)
            if bool(c["pass"]) != recomputed and gate != "summary":
                # Allow extra strictness already applied in harness (e.g. g4 C5 < C0).
                if bool(c["pass"]) and not recomputed:
                    _fail(f"{path.name}: comparison {c.get('comparison_id')} pass true but recompute false")
                if not bool(c["pass"]) and recomputed:
                    # Harness may add extra constraints — OK if file-level still fails.
                    pass

    if data.get("pass") is True:
        if gate != "regression" and int(seed_cov.get("paired_seeds", 0)) < 100:
            _fail(f"{path.name}: pass:true with paired_seeds < 100")
        if any(not c.get("pass") for c in comps):
            _fail(f"{path.name}: file pass:true but a comparison failed")

    # Render coherence absolute zeros
    if path.name == "render-coherence-results.json":
        m = data["metrics"]
        for k in (
            "accepted_generation_mismatch",
            "accepted_state_version_mismatch",
            "accepted_incoherent_habitat_packet",
            "obsolete_execution_rendered_as_current",
        ):
            if int(m.get(k, -1)) != 0:
                _fail(f"{path.name}: {k} != 0")
            if data.get("pass") and int(m.get(k, -1)) != 0:
                _fail(f"{path.name}: pass with nonzero {k}")


def main() -> None:
    thr, _matrix, _scen, hashes = ev.load_frozen()
    if not OUT.is_dir():
        _fail(f"missing evidence dir {OUT}")
    for name in REQUIRED_FILES:
        p = OUT / name
        if not p.exists():
            _fail(f"missing evidence file {name}")
        validate_file(p, hashes, thr)

    summary = json.loads((OUT / "experiment-summary.json").read_text())
    metrics = summary.get("metrics") or {}
    if metrics.get("task13_outcome") == "UMBRA_D008_COHERENT_DIGITAL_EMBODIMENT_QUALIFIED":
        _fail("summary claims final QUALIFIED")
    # All gate files that claim pass must agree with summary when summary passes.
    if summary.get("pass"):
        for name in REQUIRED_FILES:
            if name == "experiment-summary.json":
                continue
            data = json.loads((OUT / name).read_text())
            if not data.get("pass"):
                _fail(f"summary pass but {name} failed")

    print("OK: Task 13 evidence validator passed")
    print(json.dumps({"files": len(REQUIRED_FILES), "hashes": hashes}, indent=2))


if __name__ == "__main__":
    main()
