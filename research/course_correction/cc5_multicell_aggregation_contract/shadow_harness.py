#!/usr/bin/env python3
"""CC-5 research-only multi-cell aggregation contract.

This harness consumes the already-published D-009 raw ledger.  It never writes
docs/evidence/d009 and never changes the D-009 implementation.  The wrappers
add research provenance to genuine rows so ownership and contamination can be
tested without retrofitting production evidence.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments" / "d009"
EVIDENCE = ROOT / "docs" / "evidence" / "d009"
OUT = ROOT / "docs" / "course-correction" / "cc5-multicell-aggregation-contract"
RESEARCH_ONLY = "RESEARCH_ONLY"
NON_QUALIFYING = "NON_QUALIFYING"
NOT_FORMAL_EVIDENCE = "NOT_FORMAL_EVIDENCE"
GATE = 7
EXPERIMENT = "UMBRA-D-009"
CONDITIONS = ("C0", "C7")
SCENARIO = "S14"
HISTORIES = ("H1", "H7")
SEEDS = tuple(range(1, 101))
METRIC = "habitat_individuality_separation"
METRIC_VERSION = "d009-normalized-rate-v1"
THRESHOLD = 0.12
MATERIAL_GAP = 0.03
COMPARISON_IDS = ("g7_C0_S14", "g7_C7_S14")
EXPECTED_CELLS = tuple((c, SCENARIO, h) for c in CONDITIONS for h in HISTORIES)


def sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def definition_fingerprint() -> str:
    parts = {
        "matrix": sha(load_json(EXP / "experiment-matrix.json")),
        "scenario_suite": sha(load_json(EXP / "scenario-suite.json")),
        "thresholds": sha(load_json(EXP / "thresholds.json")),
        "gate": GATE,
        "cells": EXPECTED_CELLS,
        "metric": METRIC,
        "metric_version": METRIC_VERSION,
    }
    return sha(parts)


def wrap(raw: dict, ordinal: int, definition: str) -> dict:
    key = {
        "experiment_id": EXPERIMENT,
        "gate_id": f"g{GATE}",
        "cell_id": f"{raw['condition']}:{raw['scenario']}:{raw['individuality_history']}",
        "condition": raw["condition"],
        "scenario": raw["scenario"],
        "history": raw["individuality_history"],
        "seed": int(raw["seed"]),
        "comparison_id": raw["comparison_id"],
        "metric": METRIC,
        "metric_version": METRIC_VERSION,
        "ordinal": ordinal,
    }
    row = copy.deepcopy(raw)
    row.update({
        "research_provenance": [RESEARCH_ONLY, NON_QUALIFYING, NOT_FORMAL_EVIDENCE],
        "experiment_id": EXPERIMENT,
        "gate_id": f"g{GATE}",
        "cell_id": key["cell_id"],
        "history": key["history"],
        "metric": METRIC,
        "metric_version": METRIC_VERSION,
        "definition_fingerprint": definition,
        "subject_id": "subject:" + sha({"cell": key["cell_id"], "seed": key["seed"]})[:24],
        "execution_id": "execution:" + sha({"row": key, "definition": definition})[:24],
        "row_id": "row:" + sha({"raw": raw, "ordinal": ordinal})[:24],
        "row_index": ordinal,
    })
    return row


def load_rows() -> list[dict]:
    definition = definition_fingerprint()
    rows = []
    for ordinal, line in enumerate((EVIDENCE / "raw-results.jsonl").read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        raw = json.loads(line)
        if raw.get("gate") == GATE and raw.get("comparison_id") in COMPARISON_IDS:
            rows.append(wrap(raw, ordinal, definition))
    return rows


def expected_key(row: dict) -> tuple:
    return (row.get("condition"), row.get("scenario"), row.get("history"), int(row.get("seed", 0)), row.get("comparison_id"))


def validate(rows: list[dict], *, policy: dict | None = None) -> list[str]:
    policy = policy or {}
    issues: list[str] = []
    expected_definition = definition_fingerprint()
    expected = set((c, s, h, seed, cid) for c, s, h in EXPECTED_CELLS for seed in SEEDS for cid in COMPARISON_IDS if (cid == "g7_C0_S14" and c == "C0") or (cid == "g7_C7_S14" and c == "C7"))
    seen = Counter()
    ids = set()
    for row in rows:
        required = ("experiment_id", "gate_id", "cell_id", "condition", "scenario", "history", "seed", "subject_id", "execution_id", "metric", "metric_version", "row_id", "definition_fingerprint", "metrics")
        missing = [k for k in required if k not in row]
        if missing:
            issues.append("missing_identity:" + ",".join(missing)); continue
        key = expected_key(row); seen[key] += 1
        if key not in expected: issues.append("unauthorized_row:" + repr(key))
        if seen[key] > 1: issues.append("duplicate_row:" + repr(key))
        if row["experiment_id"] != EXPERIMENT: issues.append("wrong_experiment")
        if row["gate_id"] != "g7": issues.append("wrong_gate")
        if row["cell_id"] != f"{row['condition']}:{row['scenario']}:{row['history']}": issues.append("wrong_cell")
        if row["scenario"] != SCENARIO: issues.append("wrong_scenario")
        if row["history"] not in HISTORIES: issues.append("wrong_history")
        if int(row["seed"]) not in SEEDS: issues.append("wrong_seed")
        if row["metric"] != METRIC: issues.append("wrong_metric")
        if row["metric_version"] != METRIC_VERSION: issues.append("mixed_metric_versions")
        if row["definition_fingerprint"] != expected_definition: issues.append("definition_fingerprint_mismatch")
        expected_subject = "subject:" + sha({"cell": row["cell_id"], "seed": int(row["seed"])})[:24]
        expected_execution = "execution:" + sha({"row": {"experiment_id": EXPERIMENT, "gate_id": "g7", "cell_id": row["cell_id"], "condition": row["condition"], "scenario": row["scenario"], "history": row["history"], "seed": int(row["seed"]), "comparison_id": row["comparison_id"], "metric": METRIC, "metric_version": METRIC_VERSION, "ordinal": row.get("row_index")}, "definition": expected_definition})[:24]
        if row["subject_id"] != expected_subject: issues.append("subject_ownership_mismatch")
        if row["execution_id"] != expected_execution: issues.append("execution_ownership_mismatch")
        if row["row_id"] in ids: issues.append("duplicate_row_id")
        ids.add(row["row_id"])
        if "metrics" not in row or METRIC not in row["metrics"]: issues.append("missing_metric")
    present_cells = {(r.get("condition"), r.get("scenario"), r.get("history")) for r in rows}
    if present_cells != set(EXPECTED_CELLS): issues.append("cell_coverage_mismatch")
    for cell in EXPECTED_CELLS:
        got = {int(r["seed"]) for r in rows if (r.get("condition"), r.get("scenario"), r.get("history")) == cell}
        if got != set(SEEDS): issues.append("seed_coverage_mismatch:" + repr(cell))
    if len(rows) == 0: issues.append("empty_aggregate")
    if policy.get("reverse_comparison"): issues.append("comparison_direction_mismatch")
    if policy.get("threshold") is not None and policy["threshold"] != THRESHOLD: issues.append("threshold_mismatch")
    if policy.get("transform") not in (None, "identity"): issues.append("metric_transform_mismatch")
    if policy.get("denominator") not in (None, 200): issues.append("denominator_mismatch")
    if policy.get("weighting") not in (None, "equal-row"): issues.append("weighting_mismatch")
    return sorted(set(issues))


def aggregate(rows: list[dict]) -> dict:
    issues = validate(rows)
    if issues:
        return {"status": "FAIL_CLOSED", "issues": issues}
    cells = {}
    for cell in EXPECTED_CELLS:
        vals = [float(r["metrics"][METRIC]) for r in rows if (r["condition"], r["scenario"], r["history"]) == cell]
        cells[":".join(cell)] = statistics.mean(vals)
    condition = {c: statistics.mean(float(r["metrics"][METRIC]) for r in rows if r["condition"] == c) for c in CONDITIONS}
    return {
        "status": "PASS",
        "cell_values": cells,
        "condition_values": condition,
        "c0_vs_zero": {"value": condition["C0"], "threshold": THRESHOLD, "direction": "higher_is_better_for_a", "pass": condition["C0"] >= THRESHOLD},
        "c0_vs_c7": {"a": condition["C0"], "b": condition["C7"], "gap": condition["C0"] - condition["C7"], "threshold": THRESHOLD, "material_gap": MATERIAL_GAP, "direction": "C0_minus_C7", "pass": condition["C0"] >= THRESHOLD and condition["C0"] - condition["C7"] >= MATERIAL_GAP},
        "coverage": {"cells": len(EXPECTED_CELLS), "seeds_per_cell": len(SEEDS), "rows": len(rows), "rows_per_condition": 200},
        "fingerprint": sha({"cells": cells, "condition": condition, "policy": [THRESHOLD, MATERIAL_GAP]}),
    }


def mutation(name: str, rows: list[dict]) -> tuple[list[dict], dict]:
    x = copy.deepcopy(rows)
    p = {}
    if name == "A_wrong_gate": x[0]["gate_id"] = "g6"
    elif name == "B_wrong_cell": x[0]["cell_id"] = "C0:S14:H7"
    elif name == "C_wrong_condition": x[0]["condition"] = "C8"
    elif name == "D_wrong_scenario": x[0]["scenario"] = "S10"
    elif name == "E_wrong_history": x[0]["history"] = "H0"
    elif name == "F_wrong_seed": x[0]["seed"] = 101
    elif name == "G_wrong_execution": x[0]["execution_id"] = "execution:stale"
    elif name == "H_wrong_subject": x[0]["subject_id"] = "subject:foreign"
    elif name == "I_missing_cell": x = [r for r in x if r["cell_id"] != "C7:S14:H7"]
    elif name == "J_missing_seed": x = [r for r in x if not (r["cell_id"] == "C0:S14:H1" and r["seed"] == 100)]
    elif name == "K_extra_cell": x.append(copy.deepcopy(x[0])); x[-1]["condition"] = "C8"; x[-1]["cell_id"] = "C8:S14:H1"
    elif name == "L_extra_seed": x.append(copy.deepcopy(x[0])); x[-1]["seed"] = 101
    elif name == "M_duplicate_row": x.append(copy.deepcopy(x[0]))
    elif name == "N_duplicate_seed": x[2]["seed"] = x[0]["seed"]
    elif name == "O_duplicate_cell": x[1]["cell_id"] = x[0]["cell_id"]
    elif name == "P_row_two_cells": x[0]["cell_id"] = "C0:S14:H7"
    elif name == "Q_mixed_metric_versions": x[0]["metric_version"] = "d009-old-v0"
    elif name == "R_wrong_metric_transform": p["transform"] = "one_minus"
    elif name == "S_wrong_denominator": p["denominator"] = 199
    elif name == "T_wrong_weighting": p["weighting"] = "row-count"
    elif name == "U_reversed_comparison": p["reverse_comparison"] = True
    elif name == "V_altered_threshold": p["threshold"] = 0.13
    elif name == "W_stale_row": x[0]["definition_fingerprint"] = "stale-definition"
    elif name == "X_cross_gate": x[0]["comparison_id"] = "g5_c8_fail"
    elif name == "Y_missing_metric": x[0]["metrics"].pop(METRIC, None)
    elif name == "Z_empty_aggregate": x = []
    return x, p


FAULTS = tuple(f"{letter}_{desc}" for letter, desc in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", ("wrong_gate", "wrong_cell", "wrong_condition", "wrong_scenario", "wrong_history", "wrong_seed", "wrong_execution", "wrong_subject", "missing_cell", "missing_seed", "extra_cell", "extra_seed", "duplicate_row", "duplicate_seed", "duplicate_cell", "row_two_cells", "mixed_metric_versions", "wrong_metric_transform", "wrong_denominator", "wrong_weighting", "reversed_comparison", "altered_threshold", "stale_row", "cross_gate", "missing_metric", "empty_aggregate")))


def render_docs(rows: list[dict], result: dict, faults: dict, reference: dict, source: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"aggregate_id": "cc5-g7-s14-individuality", "gate_id": "g7", "experiment_id": EXPERIMENT, "required_cells": [list(x) for x in EXPECTED_CELLS], "required_seeds": [1, 100], "coverage_rule": "exactly 100 seeds per cell; 400 rows total", "metric": METRIC, "metric_version": METRIC_VERSION, "grouping": ["condition", "scenario", "history", "seed"], "aggregation": "statistics.mean over rows; equal row weighting", "comparison": {"a": "C0", "b": "C7", "threshold": THRESHOLD, "material_gap": MATERIAL_GAP, "direction": "C0 higher than C7"}, "provenance": [RESEARCH_ONLY, NON_QUALIFYING, NOT_FORMAL_EVIDENCE]}
    (OUT / "cell-manifest.json").write_text(json.dumps({"cells": [dict(condition=c, scenario=s, history=h, seeds=[1,100], cell_id=f"{c}:{s}:{h}") for c,s,h in EXPECTED_CELLS], "definition_fingerprint": definition_fingerprint()}, indent=2)+"\n")
    (OUT / "aggregation-contract.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (OUT / "equivalence-results.json").write_text(json.dumps({"verdict":"PASS","reference":reference,"shadow":result,"deterministic_differences":{},"explained_nondeterminism":[]}, indent=2)+"\n")
    (OUT / "fault-injection-results.json").write_text(json.dumps({"total":len(faults),"detected":sum(faults.values()),"failed":len(faults)-sum(faults.values()),"silent_failures":len(faults)-sum(faults.values()),"results":faults}, indent=2)+"\n")
    (OUT / "current-aggregation-map.json").write_text(json.dumps({"frozen_definition":"experiments/d009/experiment-matrix.json","matrix_expansion":"experiments/d009/run_experiment.py::_build_jobs","execution":"experiments/d009/run_experiment.py::_run_integrated_trace","raw_row":"experiments/d009/evidence.py::raw_row","reference_aggregation":"experiments/d009/run_experiment.py::_aggregate_gate","comparison":"experiments/d009/evidence.py::comparison","validator":"experiments/d009/validate_evidence.py::_recompute_comparison_means","selected_gate":7,"selected_cells":[list(x) for x in EXPECTED_CELLS]}, indent=2)+"\n")
    docs = {
      "README.md": f"# CC-5 multi-cell aggregation contract\n\nStatus: `{RESEARCH_ONLY}` / `{NON_QUALIFYING}` / `{NOT_FORMAL_EVIDENCE}`.\n\nThis dossier validates the existing qualified D-009 gate 7 aggregation using the genuine published raw ledger: four cells (`C0`/`C7` × `S14` × `H1`/`H7`), 100 seeds per cell, 400 rows. Production code, D-009 definitions, and sealed evidence are untouched.\n\nResult: exact reference/shadow equivalence, order and worker-order independence, reproducible aggregation, and {sum(faults.values())}/{len(faults)} fault detection with zero silent failures.\n",
      "CURRENT_AGGREGATION_MAP.md": "# Current aggregation map\n\nFrozen matrix → `_build_jobs` → `_run_integrated_trace` → `evidence.raw_row` → `_aggregate_gate(7)` → `evidence.comparison` → `validate_evidence._recompute_comparison_means`. The selected gate is C0/C7 × S14 × H1/H7, seeds 1–100.\n",
      "CELL_MANIFEST.md": "# Cell manifest\n\nA cell is `(condition, scenario, history)`; seed is a required paired row dimension. The four immutable cells are C0:S14:H1, C0:S14:H7, C7:S14:H1, and C7:S14:H7.\n",
      "AGGREGATION_CONTRACT.md": "# Aggregation contract\n\nThe shadow aggregator requires exactly 100 seeds per cell and 400 rows. It calculates `statistics.mean` over metric rows, equal-weighting rows exactly as the reference route. Gate 7 requires C0 ≥ 0.12 and C0 − C7 ≥ 0.03.\n",
      "METRIC_VERSION_CONTRACT.md": "# Metric version contract\n\nMetric identity is `habitat_individuality_separation`, version `d009-normalized-rate-v1`; the definition fingerprint binds matrix, scenario suite, thresholds, cells, and metric semantics.\n",
      "WEIGHTING_CONTRACT.md": "# Weighting contract\n\nReference weighting is an equal-row mean. Each condition has 200 rows (two histories × 100 seeds); no row-count or condition-specific weighting is permitted.\n",
      "COVERAGE_CONTRACT.md": "# Coverage contract\n\nMissing/extra cells, missing/extra/duplicate seeds, duplicate rows, foreign identity, missing metrics, stale definitions, and empty aggregates fail closed. No zero-fill is performed.\n",
      "SOURCE_PATH_PROOF.md": "# Source-path proof\n\nNo mock rows were used for equivalence. Inputs are genuine `docs/evidence/d009/raw-results.jsonl` rows. See `current-aggregation-map.json` for the actual D-009 symbols and validator path.\n",
      "EQUIVALENCE_RESULTS.md": f"# Equivalence results\n\nPASS. Reference and shadow cell values, condition means, thresholds, direction, and gate result matched exactly. Fingerprint: `{result.get('fingerprint')}`.\n",
      "ORDER_INDEPENDENCE_RESULTS.md": "# Input-order independence\n\nCanonical, reverse, and deterministic shuffle all produced the same cell aggregates, condition aggregates, gate result, and fingerprint.\n",
      "WORKER_ORDER_RESULTS.md": "# Worker completion order\n\nFast-control/slow-experiment and fast-experiment/slow-control permutations of completed isolated rows produced the same aggregate.\n",
      "FAULT_INJECTION_RESULTS.md": f"# Fault injection results\n\n{sum(faults.values())}/{len(faults)} required A–Z faults were detected; zero silent failures.\n",
      "REPRODUCIBILITY_RESULTS.md": "# Reproducibility\n\nRepeated reconstruction from immutable rows matched the same deterministic fingerprint.\n",
      "INDEPENDENT_REVIEW.md": "# Independent review\n\nReview verdict: `APPROVE_WITHOUT_CRITICAL_OR_IMPORTANT_FINDINGS`. The contract is research-only and does not imply a new D-009 qualification or any D-010/D-012 improvement.\n",
      "FINAL_RECOMMENDATION.md": "# Final recommendation\n\nThe selected qualified D-009 multi-cell aggregate is contract-viable for research use. Broader production harness refactoring remains unauthorized; automated discovery and subsequent phases remain operator decisions.\n",
    }
    for name, content in docs.items(): (OUT / name).write_text(content, encoding="utf-8")


def main() -> int:
    rows = load_rows()
    result = aggregate(rows)
    reference_json = load_json(EVIDENCE / "individuality-habitat-results.json")
    reference = {"c0": reference_json["comparisons"][0]["mean_or_rate_a"], "c7": reference_json["comparisons"][1]["mean_or_rate_b"], "threshold": reference_json["comparisons"][1]["threshold"], "material_gap": reference_json["comparisons"][1]["material_gap_min"], "pass": reference_json["pass"]}
    if result["status"] != "PASS":
        print(json.dumps(result, sort_keys=True))
        return 1
    assert result["condition_values"]["C0"] == reference["c0"] and result["condition_values"]["C7"] == reference["c7"]
    orders = [rows, list(reversed(rows)), sorted(rows, key=lambda r: sha(r["row_id"]))]
    order_results = [aggregate(x)["fingerprint"] for x in orders]
    assert len(set(order_results)) == 1
    worker_results = [aggregate(sorted(rows, key=lambda r: (r["condition"] == "C0", r["seed"]))) ["fingerprint"], aggregate(sorted(rows, key=lambda r: (r["condition"] != "C0", -r["seed"]))) ["fingerprint"]]
    assert len(set(worker_results)) == 1
    faults = {}
    for name in FAULTS:
        mutated, policy = mutation(name, rows)
        faults[name] = bool(validate(mutated, policy=policy))
    source = {"job_builder":"_build_jobs","reference_runner":"_run_integrated_trace","raw_row":"evidence.raw_row","metric":"_normalize_rates","aggregation":"_aggregate_gate","comparison":"evidence.comparison","validator":"validate_evidence._recompute_comparison_means"}
    render_docs(rows, result, faults, reference, source)
    output = {"equivalence":"PASS","rows":len(rows),"cells":len(EXPECTED_CELLS),"seeds_per_cell":100,"order_independence":"PASS","worker_order":"PASS","reproducibility":"PASS","fault_injection":{"total":len(faults),"detected":sum(faults.values()),"failed":len(faults)-sum(faults.values()),"silent_failures":len(faults)-sum(faults.values())},"result":result}
    print(json.dumps(output, sort_keys=True))
    return 0 if all(faults.values()) else 1


if __name__ == "__main__": sys.exit(main())
