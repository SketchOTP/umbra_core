"""Pre-freeze seal harness for UMBRA-D-010 (Task 11 / Task 14)."""

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
    out = {"prior_seals_valid": all_valid, "pre_freeze": True}
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


def run_pytest() -> dict:
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
        "output_tail": text[-2000:],
    }


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
    (OUT / "evidence-hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return hashes


def main() -> None:
    parser = argparse.ArgumentParser(description="UMBRA-D-010 seal harness (pre-freeze)")
    parser.add_argument("--contract-only", action="store_true", help="Validate manifests and pytest only")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    priors = validate_prior_seals()
    stage = validate_stage_a()
    tests = run_pytest()
    perf = (
        json.loads((OUT / "performance-results.json").read_text())
        if (OUT / "performance-results.json").exists()
        else {}
    )
    exp = (
        json.loads((OUT / "experiment-summary.json").read_text())
        if (OUT / "experiment-summary.json").exists()
        else {}
    )
    contract_ok = bool(stage["stage_a_ok"]) and bool(tests.get("manifest_ok"))
    perf_contract = bool(perf.get("pre_freeze")) or not perf
    verdict = "UMBRA_D010_PRE_FREEZE_HARNESS_CONTRACT_PASS" if contract_ok else "UMBRA_D010_PRE_FREEZE_HARNESS_CONTRACT_FAIL"
    body = f"""# UMBRA-D-010 Pre-freeze Harness Verdict

**Verdict:** `{verdict}`

**Stage:** Task 11 pre-freeze (not Stage B qualified)

| Check | Result |
|-------|--------|
| Stage A artifacts | `{"PASS" if stage["stage_a_ok"] else "FAIL"}` |
| Test manifest + pytest | `{"PASS" if tests.get("zero_skip") else "FAIL"}` (passed={tests.get("passed")}, skipped={tests.get("skipped")}) |
| Prior seals present | `{"PASS" if priors.get("prior_seals_valid") else "PARTIAL"}` |
| Formal experiment evidence | `{"PRESENT" if exp else "NOT_RUN"}` |
| Performance evidence | `{"PRESENT" if perf else "NOT_RUN"}` |

No QUALIFIED claim is made at this stage.
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
    if args.contract_only:
        raise SystemExit(0 if contract_ok else 1)
    raise SystemExit(0 if contract_ok and perf_contract else 1)


if __name__ == "__main__":
    main()
