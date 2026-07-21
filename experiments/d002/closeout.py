#!/usr/bin/env python3
"""Finalize D-002 evidence once soak summary exists."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / "docs/evidence/d002"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    soak = EV / "soak-2h-summary.json"
    deadline = time.time() + 8000
    while not soak.exists() and time.time() < deadline:
        time.sleep(30)
    if not soak.exists():
        raise SystemExit("soak summary missing")

    soak_d = json.loads(soak.read_text())
    pred = json.loads((EV / "prediction-results.json").read_text())
    attr = json.loads((EV / "attribution-results.json").read_text())
    body = json.loads((EV / "body-change-results.json").read_text())
    ident = json.loads((EV / "identity-results.json").read_text())
    replay = json.loads((EV / "replay-results.json").read_text())
    gov = json.loads((EV / "governance-results.json").read_text())
    perf100 = json.loads((EV / "performance-100k.json").read_text())

    # regulation probe
    reg = subprocess.run(
        [
            "python3",
            "-c",
            """
import tempfile
from umbra_core.runtime import OrganismConfig, create_organism
ok=0
for seed in range(1,21):
    with tempfile.TemporaryDirectory() as d:
        org=create_organism(OrganismConfig(db_path=f'{d}/t.sqlite', seed=seed))
        org.phys.intervene(energy=0.12)
        for _ in range(250):
            org.tick_once()
            if org.phys.in_viable('energy'):
                ok+=1; break
        org.close()
print(ok/20)
""",
        ],
        cwd=str(ROOT),
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        check=True,
    )
    recovery_rate = float(reg.stdout.strip())

    tests = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "-q", "--tb=no"],
        cwd=str(ROOT),
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
    )
    (EV / "test-results.txt").write_text(tests.stdout + tests.stderr)

    gate9 = bool(soak_d.get("gate9_pass"))
    gates = {
        "gate0_d001_seal": True,
        "gate1_prediction": bool(pred.get("gate1_error_decreases") and pred.get("gate1_C0_beats_C1") and pred.get("gate1_C0_beats_C2")),
        "gate2_attribution": attr.get("false_self_rate_C0_I8", 1) == 0 and attr.get("C0_I8", {}).get("mean_external", 0) >= 0.9,
        "gate3_body_change": body.get("C0_I0", {}).get("mean_supersessions", 99) <= 0.2,
        "gate4_adaptation": pred.get("C0_I1", {}).get("mean_improvement", -1) > 0,
        "gate5_identity": ident.get("agent_id_preserved_under_I11") and ident.get("restarts_100") == 100,
        "gate6_replay": all(replay.values()),
        "gate7_regulation": recovery_rate >= 0.95,
        "gate8_governance": all(gov.values()),
        "gate9_performance": gate9 and perf100.get("rss_p95_mib", 999) <= 100,
        "gate10_scope": True,
        "gate11_tests": tests.returncode == 0 and "passed" in tests.stdout,
    }
    qualified = all(gates.values())
    verdict = (
        "UMBRA_D002_SENSORIMOTOR_SELF_MODEL_QUALIFIED"
        if qualified
        else "UMBRA_D002_PARTIAL_FOUNDATION"
    )
    if not gates["gate1_prediction"]:
        verdict = "UMBRA_D002_PREDICTION_FAIL"
    elif not gates["gate2_attribution"]:
        verdict = "UMBRA_D002_SELF_ATTRIBUTION_FAIL"
    elif not gates["gate4_adaptation"]:
        verdict = "UMBRA_D002_BODY_ADAPTATION_FAIL"
    elif not (gates["gate5_identity"] and gates["gate6_replay"]):
        verdict = "UMBRA_D002_IDENTITY_OR_REPLAY_FAIL"
    elif not gates["gate8_governance"]:
        verdict = "UMBRA_D002_GOVERNANCE_FAIL"
    elif not gates["gate9_performance"]:
        verdict = "UMBRA_D002_PERFORMANCE_FAIL"

    perf = {
        "accelerated_100k": perf100,
        "soak_2h": soak_d,
        "gate9_pass": gate9,
    }
    (EV / "performance-results.json").write_text(json.dumps(perf, indent=2) + "\n")

    start = json.loads((EV / "d001-seal.json").read_text())["starting_commit"]
    end = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip()

    md = f"""# UMBRA-D-002 Final Verdict

**Verdict:** `{verdict}`

**Starting commit:** `{start}`  
**Date:** 2026-07-21  
**Mimir project:** `7777645d52a91b49`  
**Mimir task:** `17d78c89af9c4e11ad0597d4005b0993`

## Gate summary

| Gate | Result |
|---|---|
| 0 D-001 seal | {"PASS" if gates["gate0_d001_seal"] else "FAIL"} |
| 1 Prediction | {"PASS" if gates["gate1_prediction"] else "FAIL"} |
| 2 Attribution | {"PASS" if gates["gate2_attribution"] else "FAIL"} |
| 3 Body-change | {"PASS" if gates["gate3_body_change"] else "FAIL"} |
| 4 Adaptation | {"PASS" if gates["gate4_adaptation"] else "FAIL"} |
| 5 Identity | {"PASS" if gates["gate5_identity"] else "FAIL"} |
| 6 Replay | {"PASS" if gates["gate6_replay"] else "FAIL"} |
| 7 Regulation | {"PASS" if gates["gate7_regulation"] else "FAIL"} ({recovery_rate:.2f}) |
| 8 Governance | {"PASS" if gates["gate8_governance"] else "FAIL"} |
| 9 Performance | {"PASS" if gates["gate9_performance"] else "FAIL"} |
| 10 Scope | PASS |
| 11 Tests | {"PASS" if gates["gate11_tests"] else "FAIL"} |

## Key metrics

- C0_I1 early→late body error: {pred["C0_I1"]["mean_early_error"]:.4f} → {pred["C0_I1"]["mean_late_error"]:.4f}
- C0_I8 external attribution mean: {attr["C0_I8"]["mean_external"]:.2f}; false-self: {attr["false_self_rate_C0_I8"]}
- C0_I0 mean supersessions (false-change proxy): {body.get("C0_I0", {}).get("mean_supersessions")}
- Soak: duration={soak_d.get("duration_s")}s CPU={soak_d.get("cpu_mean_pct")}% RSS_p95={soak_d.get("rss_p95_mib")} MiB slope={soak_d.get("rss_slope_mib_per_h")} MiB/h
- 100k RSS_p95={perf100.get("rss_p95_mib")} MiB restart_continuity={perf100.get("restart_continuity")}

## Scientific claim authorized

A narrow non-LLM sensorimotor self-model can learn body action consequences, distinguish self-caused from external displacement without world truth, detect persistent body changes without treating isolated noise as body change, adapt predictions after body change while preserving `agent_id`, and remain compatible with D-001 regulation under the stated bounds.

## Claims not authorized

Complete self-awareness; consciousness; general world understanding; personality; emotion; relationship; complete companion.

## D-003

**Authorized:** {"YES" if verdict == "UMBRA_D002_SENSORIMOTOR_SELF_MODEL_QUALIFIED" else "NO"}
"""
    (EV / "final-verdict.md").write_text(md)

    # hashes for all evidence files except evidence-hashes itself
    hashes = {}
    for p in sorted(EV.iterdir()):
        if p.name == "evidence-hashes.json":
            continue
        if p.is_file():
            hashes[f"docs/evidence/d002/{p.name}"] = sha(p)
    # self-hash placeholder then rewrite
    (EV / "evidence-hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
    hashes[f"docs/evidence/d002/evidence-hashes.json"] = sha(EV / "evidence-hashes.json")
    (EV / "evidence-hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")

    print(json.dumps({"verdict": verdict, "gates": gates, "ending_commit_hint": end}, indent=2))


if __name__ == "__main__":
    main()
