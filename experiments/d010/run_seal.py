"""Seal harness for UMBRA-D-010 (Task 14 / Supplement S3 Gate 13)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d010 import stage_a as sa

OUT = ROOT / "docs/evidence/d010"

PRIOR_SEALS = [
    "docs/evidence/d001/evidence-hashes.json",
    "docs/evidence/d009/evidence-hashes.json",
]

EXTRA_INPUTS = [
    "docs/directives/UMBRA-D-010-temporal-continuity.md",
    "docs/superpowers/specs/2026-07-24-umbra-d010-temporal-continuity-design.md",
    "experiments/d010/thresholds.json",
    "experiments/d010/experiment-matrix.json",
    "experiments/d010/scenario-suite.json",
    "experiments/d010/performance-protocol.json",
    "experiments/d010/test-manifest.json",
    "experiments/d010/stage-a-hashes.json",
    "experiments/d010/run_experiment.py",
    "experiments/d010/run_performance.py",
    "experiments/d010/run_seal.py",
    "experiments/d010/evidence.py",
    "experiments/d010/validate_evidence.py",
    "tests/test_d010.py",
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def validate_prior_seals() -> dict:
    all_valid = True
    for seal in PRIOR_SEALS:
        path = ROOT / seal
        if not path.is_file():
            all_valid = False
            continue
        data = json.loads(path.read_text())
        for rel, expect in data.items():
            if not isinstance(expect, str) or not rel.startswith("docs/"):
                continue
            if rel.endswith("evidence-hashes.json"):
                continue
            p = ROOT / rel
            if p.is_file() and _sha(p) != expect:
                all_valid = False
    d009_qualified = False
    d009_verdict = ROOT / "docs/evidence/d009/final-verdict.md"
    if d009_verdict.is_file():
        d009_qualified = "UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED" in d009_verdict.read_text()
    out = {
        "prior_seals_valid": all_valid,
        "d009_qualified_present": d009_qualified,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "prior-seals.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def validate_stage_a() -> dict:
    errors = sa.validate_test_manifest_complete()
    try:
        sa.validate_seed_nonoverlap()
    except ValueError as exc:
        errors.append(str(exc))
    hashes = sa.compute_stage_a_hashes()
    try:
        sa.assert_no_placeholder_hashes(hashes)
    except ValueError as exc:
        errors.append(str(exc))
    return {"stage_a_ok": not errors, "errors": errors}


def _collect_pytest_ids() -> set[str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_d010.py", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    text = proc.stdout + "\n" + proc.stderr
    return set(re.findall(r"::(test_[a-zA-Z0-9_]+)", text))


def run_pytest(*, contract_only: bool) -> dict:
    manifest = sa.load_test_manifest()
    required = set(sa.required_test_ids(manifest))
    collected = _collect_pytest_ids()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_d010.py",
            "-q",
            "--tb=no",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    text = proc.stdout + "\n" + proc.stderr
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "test-results.txt").write_text(text)
    m = re.search(r"(\d+) passed", text)
    passed = int(m.group(1)) if m else 0
    skip_m = re.search(r"(\d+) skipped", text)
    n_skip = int(skip_m.group(1)) if skip_m else 0
    missing_required = sorted(required - collected)
    unknown_collected = sorted(collected - required)
    manifest_ok = (
        proc.returncode == 0
        and n_skip == 0
        and not missing_required
        and not unknown_collected
        and len(collected) >= len(required)
    )
    return {
        "returncode": proc.returncode,
        "passed": passed,
        "skipped": n_skip,
        "required_count": len(required),
        "collected_count": len(collected),
        "executed_required_count": len(required & collected),
        "missing_required": missing_required,
        "unknown_collected": unknown_collected[:8],
        "manifest_ok": manifest_ok,
        "zero_skip": manifest_ok,
        "contract_only": contract_only,
        "output_tail": text[-2000:],
    }


def _load_json(name: str) -> dict:
    path = OUT / name
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _gates_ok(*, formal: dict, exp: dict) -> bool:
    if formal.get("gates_1_12_pass"):
        return True
    if formal.get("outcome") == "UMBRA_D010_TASK13_GATES_1_12_PASS":
        return True
    metrics = exp.get("metrics") or {}
    if metrics.get("all_experiment_gates_pass") or exp.get("all_experiment_gates_pass"):
        return True
    if metrics.get("task13_outcome") == "UMBRA_D010_TASK13_GATES_1_12_PASS":
        return True
    return bool(exp.get("pass"))


def _perf_ok(perf: dict) -> bool:
    if not perf:
        return False
    if perf.get("pre_freeze"):
        return False
    if perf.get("smoke_scaled"):
        return False
    return bool(perf.get("pass")) and perf.get("adaptive_soak_supplement") == "S3"


def _qualification_verdict(
    *,
    gates_ok: bool,
    perf_ok: bool,
    prior_ok: bool,
    suite_ok: bool,
) -> str:
    if gates_ok and perf_ok and prior_ok and suite_ok:
        return "UMBRA_D010_TEMPORAL_CONTINUITY_QUALIFIED"
    if not perf_ok:
        return "UMBRA_D010_PERFORMANCE_FAIL"
    if not gates_ok:
        return "UMBRA_D010_PARTIAL_FOUNDATION"
    return "UMBRA_D010_PARTIAL_FOUNDATION"


def hash_all() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for rel in EXTRA_INPUTS:
        p = ROOT / rel
        if p.exists():
            hashes[rel] = _sha(p)
    for p in sorted(OUT.glob("*.json")):
        if p.name == "evidence-hashes.json":
            continue
        hashes[f"docs/evidence/d010/{p.name}"] = _sha(p)
    if (OUT / "test-results.txt").exists():
        hashes["docs/evidence/d010/test-results.txt"] = _sha(OUT / "test-results.txt")
    if (OUT / "final-verdict.md").exists():
        hashes["docs/evidence/d010/final-verdict.md"] = _sha(OUT / "final-verdict.md")
    (OUT / "evidence-hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return hashes


def main() -> None:
    parser = argparse.ArgumentParser(description="UMBRA-D-010 seal harness")
    parser.add_argument(
        "--contract-only",
        action="store_true",
        help="Validate Stage A manifests and pytest only (pre-freeze contract)",
    )
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    ending = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] != "--contract-only" else "PENDING"
    priors = validate_prior_seals()
    stage = validate_stage_a()
    tests = run_pytest(contract_only=args.contract_only)

    if args.contract_only:
        contract_ok = bool(stage["stage_a_ok"]) and bool(tests.get("manifest_ok"))
        verdict = (
            "UMBRA_D010_PRE_FREEZE_HARNESS_CONTRACT_PASS"
            if contract_ok
            else "UMBRA_D010_PRE_FREEZE_HARNESS_CONTRACT_FAIL"
        )
        body = f"""# UMBRA-D-010 Pre-freeze Harness Verdict

**Verdict:** `{verdict}`

**Stage:** contract-only (Stage A + test manifest; no qualification claim)

| Check | Result |
|-------|--------|
| Stage A artifacts | `{"PASS" if stage["stage_a_ok"] else "FAIL"}` |
| Test manifest + pytest | `{"PASS" if tests.get("zero_skip") else "FAIL"}` (passed={tests.get("passed")}, skipped={tests.get("skipped")}) |
| Prior seals present | `{"PASS" if priors.get("prior_seals_valid") else "PARTIAL"}` |

No QUALIFIED claim is made in contract-only mode.
"""
        (OUT / "final-verdict.md").write_text(body)
        hash_all()
        print(
            json.dumps(
                {
                    "verdict": verdict,
                    "contract_ok": contract_ok,
                    "tests": tests,
                    "stage": stage,
                    "pre_freeze": True,
                },
                indent=2,
            )
        )
        raise SystemExit(0 if contract_ok else 1)

    formal = _load_json("formal-run-outcome.json")
    exp = _load_json("experiment-summary.json")
    perf = _load_json("performance-results.json")

    gates_ok = _gates_ok(formal=formal, exp=exp)
    perf_ok = _perf_ok(perf)
    prior_ok = bool(priors.get("prior_seals_valid")) and bool(priors.get("d009_qualified_present"))
    suite_ok = bool(tests.get("zero_skip"))
    verdict = _qualification_verdict(
        gates_ok=gates_ok,
        perf_ok=perf_ok,
        prior_ok=prior_ok,
        suite_ok=suite_ok,
    )

    body = f"""# UMBRA-D-010 Final Verdict

**Verdict:** `{verdict}`

**Ending commit:** `{ending}`
**Mimir project:** `7777645d52a91b49`
**Adaptive soak:** Supplement **S3** (authorized replacement for fixed two-hour soak)

## Gate summary

| Check | Result |
|-------|--------|
| Task 13 Gates 1–12 | `{"PASS" if gates_ok else "FAIL"}` |
| Gate 13 performance (S3 adaptive) | `{"PASS" if perf_ok else "FAIL"}` |
| Prior seals D-001 + D-009 | `{"PASS" if prior_ok else "FAIL"}` |
| Zero-skip test suite | `{"PASS" if suite_ok else "FAIL"}` (passed={tests.get("passed")}, skipped={tests.get("skipped")}) |

## Evidence surfaces

| Surface | Present |
|---------|---------|
| formal-run-outcome.json | `{"yes" if formal else "no"}` |
| experiment-summary.json | `{"yes" if exp else "no"}` |
| performance-results.json | `{"yes" if perf else "no"}` |

D-010 Task 14 uses authorized adaptive-soak Supplement S3. Absolute and incremental
RSS/CPU limits from `experiments/d010/thresholds.json` remain binding.

D-009 `UMBRA_D009_PERSISTENT_HABITAT_AGENCY_QUALIFIED` prerequisite required.
"""
    (OUT / "final-verdict.md").write_text(body)
    hash_all()
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_ok": gates_ok,
                "perf_ok": perf_ok,
                "prior_ok": prior_ok,
                "suite_ok": suite_ok,
                "tests": tests,
            },
            indent=2,
        )
    )
    raise SystemExit(0 if verdict.endswith("QUALIFIED") else 1)


if __name__ == "__main__":
    main()
