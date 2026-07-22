"""Seal UMBRA-D-006 experiment evidence (Task 12): hashes, interim verdict, test dump.

Task 12 seals experiment gates 1-9 only. Gate 12 (performance soak) is deferred to
Task 13, so this emits the interim verdict UMBRA_D006_EXPERIMENT_GATES_1_9_PASS —
NOT the final UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED. It never edits the frozen
matrix/thresholds. It hashes the current evidence files for a tamper-evident seal.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/d006"

EVIDENCE_FILES = [
    "experiment-summary.json",
    "recognition-results.json",
    "contingency-results.json",
    "history-results.json",
    "reliability-results.json",
    "satiation-results.json",
    "absence-results.json",
    "routine-results.json",
    "governance-results.json",
    "manipulation-results.json",
    "replay-results.json",
    "event-authority-results.json",
    "test-results.txt",
]


def main() -> None:
    exp = json.loads((OUT / "experiment-summary.json").read_text())

    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_d006.py", "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    (OUT / "test-results.txt").write_text(r.stdout + r.stderr)
    tests_line = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else ""
    tests_pass = r.returncode == 0

    gates = exp["gates"]
    gates_1_9_pass = bool(exp.get("all_experiment_gates_1_9_pass"))
    qualified = gates_1_9_pass and tests_pass
    verdict = (
        "UMBRA_D006_EXPERIMENT_GATES_1_9_PASS"
        if qualified
        else "UMBRA_D006_EXPERIMENT_INCOMPLETE"
    )

    try:
        tip = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except subprocess.CalledProcessError:
        tip = "unknown"

    def row(key: str, label: str) -> str:
        return f"| {label} | {'PASS' if gates.get(key) else 'FAIL'} |"

    verdict_md = f"""# UMBRA-D-006 Interim Verdict (Task 12 — experiment evidence)

**Verdict:** `{verdict}`

**Scope:** Experiment harness + evidence generation. Gates 1-9 asserted numerically
against the frozen `experiments/d006/thresholds.json`. Gate 12 (performance soak) is
deferred to Task 13; gates 10/11 (prior seals, birth/snapshot replay) are covered by
`tests/test_d006.py`. This is NOT the final directive qualification.

**Ending commit:** `{tip}`
**Date:** 2026-07-22
**Mimir project:** `7777645d52a91b49`

## Experiment gates (frozen thresholds)

| Gate | Result |
|------|--------|
{row("gate1_contingency", "1 Contingency beats frequency/timing")}
{row("gate2_history_separation", "2 History separation (pooled/no-memory worse)")}
{row("gate3_recognition", "3 Recognition: swap detected, ambiguity kept unknown (synthetic + organism real path)")}
{row("gate4_reliability_revision", "4 Reliability revision + single-anomaly preservation")}
{row("gate5_satiation", "5 Social satiation limits bids")}
{row("gate6_absence_autonomy", "6 Absence: no bids, no punishment, viability held")}
{row("gate7_routine_development", "7 Developmental routine (scripted C8 disqualified)")}
{row("gate8_provenance", "8 Relationship state has episode provenance")}
{row("gate9_authority_safety", "9 Relationship memory never grants authority; C3 isolated")}

## Key measures

- delta_C0 (H0-H1 reliability) = {exp["measures"]["delta_c0"]:.3f} (min {json.loads((ROOT / "experiments/d006/thresholds.json").read_text())["contingency_effect_size_min"]})
- history_effect = {exp["measures"]["history_effect"]:.3f}; separation C0/C2/C4 = {exp["measures"]["sep_c0"]:.3f}/{exp["measures"]["sep_c2"]:.3f}/{exp["measures"]["sep_c4"]:.3f}
- single-failure preserved = {exp["measures"]["single_failure"]["preserved"]}; viability_frac = {exp["measures"]["viability_frac"]}
- replay determinism = {exp["measures"]["replay"]}; C3 no-leak = {exp["measures"]["c3"]["c3_no_leak"]}
- Gate 3 organism real-path (embodiment→perception→recognize→tick_once, {exp["measures"]["organism_recognition"]["seeds"]} seeds): H8 distinct+swap = {exp["measures"]["organism_recognition"]["h8_distinct_and_swap_frac"]}, H8 false-merge = {exp["measures"]["organism_recognition"]["h8_false_merge_frac"]}, H9 ambiguous-not-split = {exp["measures"]["organism_recognition"]["h9_ambiguous_not_split_frac"]}

## Task 12 review Critical fix (organism-level recognition)

The Task 12 review found Gate 3 was unit-level only: `PartnerTrueCues` inter-partner
separation (~0.17) was below `PerceptionMembrane` identity-cue noise, so two distinct H8
partners collapsed into one hypothesis through the real perception path (0 swaps). Fixed by
(a) an antipodal per-index identity basis in `PartnerTrueCues.for_history` (noise-free
inter-partner cue distance ~0.69) and (b) a smaller identity-signature noise (0.14) than
spatial noise in `PerceptionMembrane`. The frozen `recognition_match_threshold` (0.55) is
unchanged. Gate 3 now requires BOTH the synthetic mechanism check AND the organism real-path
check, with an end-to-end organism regression test in `tests/test_d006.py`.

## Run

- gate-critical paired seeds: {exp["seeds_gate_critical"]}
- rows: {exp["rows"]} across cells {exp["cells"]}
- wall-clock: {exp["elapsed_s"]} s ({exp["workers"]} workers)

## Tests

- `pytest tests/test_d006.py`: {tests_line}
- Gate 12 soak remains skipped by design until Task 13 supplies performance evidence.

## Deferred

- Gate 12 performance soak (RSS/CPU bounds) → Task 13 → `docs/evidence/d006/performance-results.json`
- Final `UMBRA_D006_SOCIAL_CONTINGENCY_QUALIFIED` requires Task 13 + zero-skip sealed suite.
"""
    (OUT / "final-verdict.md").write_text(verdict_md)

    hashes = {}
    for name in EVIDENCE_FILES + ["final-verdict.md"]:
        p = OUT / name
        if p.exists():
            hashes[f"docs/evidence/d006/{name}"] = hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT / "evidence-hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")

    print(json.dumps({"verdict": verdict, "gates": gates, "tests": tests_line, "tip": tip}, indent=2))
    if not qualified:
        sys.exit(2)


if __name__ == "__main__":
    main()
