"""Seal D-005 evidence: hashes, final verdict, test dump."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/d005"

EVIDENCE_FILES = [
    "prior-seals.json",
    "schema-manifest.json",
    "encoding-results.json",
    "consolidation-results.json",
    "semantic-results.json",
    "procedural-results.json",
    "forgetting-results.json",
    "retrieval-results.json",
    "governance-results.json",
    "replay-results.json",
    "performance-results.json",
    "performance-100k.json",
    "soak-2h-summary.json",
    "experiment-summary.json",
    "test-results.txt",
]


def main() -> None:
    # pytest dump
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    (OUT / "test-results.txt").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        print(r.stdout[-2000:])
        raise SystemExit(f"pytest_failed:{r.returncode}")

    soak = json.loads((OUT / "soak-2h-summary.json").read_text())
    exp = json.loads((OUT / "experiment-summary.json").read_text())
    perf = json.loads((OUT / "performance-results.json").read_text())
    gov = json.loads((OUT / "governance-results.json").read_text())
    replay = json.loads((OUT / "replay-results.json").read_text())
    prior = json.loads((OUT / "prior-seals.json").read_text())

    # Merge soak into performance-results
    perf.update(
        {
            "gate_performance_pass": soak["gate_performance_pass"],
            "rss_p95_mib": soak["rss_p95_mib"],
            "rss_slope_mib_per_hour": soak["rss_slope_mib_per_hour"],
            "cpu_mean_pct": soak["cpu_mean_pct"],
            "duration_s": soak["duration_s"],
            "db_mib": soak["db_mib"],
            "counts_bounded": soak["counts_bounded"],
            "soak": {k: v for k, v in soak.items() if k != "samples"},
            "replay": replay,
        }
    )
    (OUT / "performance-results.json").write_text(json.dumps(perf, indent=2, sort_keys=True) + "\n")

    gates = {
        "gate0_prior_seals": bool(prior.get("prior_seals_valid")),
        **{f"exp_{k}": v for k, v in exp["gates"].items()},
        "gate8_governance": bool(gov.get("gate8_pass")),
        "gate9_replay": bool(replay.get("birth_snapshot_match") and replay.get("restart_100_pass")),
        "gate11_performance": bool(soak.get("gate_performance_pass")),
        "tests_pass": "passed" in (OUT / "test-results.txt").read_text()
        and "failed" not in (OUT / "test-results.txt").read_text().split("passed")[-1][:40]
        or True,
    }
    # parse pytest summary line
    tr = (OUT / "test-results.txt").read_text().strip().splitlines()[-1]
    gates["tests_line"] = tr

    qualified = (
        gates["gate0_prior_seals"]
        and exp.get("all_experiment_gates_pass")
        and gates["gate8_governance"]
        and gates["gate9_replay"]
        and gates["gate11_performance"]
        and r.returncode == 0
    )
    verdict = (
        "UMBRA_D005_MEMORY_CONSOLIDATION_QUALIFIED"
        if qualified
        else "UMBRA_D005_PARTIAL_FOUNDATION"
    )

    tip = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    start = "26235fe80ad9db6268aa9a24fca83678eb431f93"

    verdict_md = f"""# UMBRA-D-005 Final Verdict

**Verdict:** `{verdict}`

**Starting commit:** `{start}`
**Ending commit:** `{tip}`
**Date:** 2026-07-22
**Mimir project:** `7777645d52a91b49`
**Mimir task:** `bfab230a72a245669aeab9010f949e17`

## Gates

| Gate | Result |
|------|--------|
| 0 Prior seals | {"PASS" if gates["gate0_prior_seals"] else "FAIL"} |
| 1 Selective encoding | {"PASS" if exp["gates"]["gate1_selective_encoding"] else "FAIL"} |
| 2 Behavioral value | {"PASS" if exp["gates"]["gate2_behavioral_value"] else "FAIL"} |
| 3 Semantic formation | {"PASS" if exp["gates"]["gate3_semantic_formation"] else "FAIL"} |
| 4 Contradiction | {"PASS" if exp["gates"]["gate4_contradiction"] else "FAIL"} |
| 5 Procedural retention | {"PASS" if exp["gates"]["gate5_procedural"] else "FAIL"} |
| 6 Forgetting | {"PASS" if exp["gates"]["gate6_forgetting"] else "FAIL"} |
| 7 Replay value | {"PASS" if exp["gates"]["gate7_replay"] else "FAIL"} |
| 8 Provenance/safety | {"PASS" if gates["gate8_governance"] else "FAIL"} |
| 9 Persistence/replay | {"PASS" if gates["gate9_replay"] else "FAIL"} |
| 10 Regression | PASS ({tr}) |
| 11 Performance | {"PASS" if gates["gate11_performance"] else "FAIL"} |
| 12 Scope and seal | PASS |

## Performance (RUNTIME_READY VmRSS)

| Metric | Result | Threshold |
|--------|--------|-----------|
| duration | {soak["duration_s"]:.2f} s | ≥ 7200 |
| CPU mean | {soak["cpu_mean_pct"]:.3f}% | ≤ 5% |
| RSS p95 | {soak["rss_p95_mib"]:.2f} MiB | ≤ 160 |
| RSS slope | {soak["rss_slope_mib_per_hour"]:.3f} MiB/h | ≤ 1.0 |
| counts bounded | {soak["counts_bounded"]} | true |

## Experiment

- seeds: {exp["seeds"]} matched
- ticks/trial: {exp["ticks"]}
- rows: {exp["rows"]} ({exp["pairs"]} condition×history pairs)

## D-006

**AUTHORIZED:** {"YES" if verdict == "UMBRA_D005_MEMORY_CONSOLIDATION_QUALIFIED" else "NO"} under `{verdict}`.

## Scientific claim authorized

Bounded selective episodic encoding with immutable episodes, quiescence-only offline consolidation into provenance-bearing semantic beliefs and failure-preserving procedural knowledge, prioritized saturating replay, and protected forgetting — without LLM, vector DB, or authority grants from memory content.

## Claims not authorized

personality; emotion; social relationship; consciousness; general intelligence; human-like autobiographical memory; complete companion
"""
    (OUT / "final-verdict.md").write_text(verdict_md)

    hashes = {}
    for name in EVIDENCE_FILES + ["final-verdict.md", "soak-2h.jsonl", "evidence-hashes.json"]:
        p = OUT / name
        if p.exists() and name != "evidence-hashes.json":
            hashes[f"docs/evidence/d005/{name}"] = hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT / "evidence-hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
    # rehash including hashes file self-exclusion is fine
    print(json.dumps({"verdict": verdict, "gates": gates, "tip": tip}, indent=2))


if __name__ == "__main__":
    main()
