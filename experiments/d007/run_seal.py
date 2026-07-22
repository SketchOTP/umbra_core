"""Final seal for UMBRA-D-007 lived individuality."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/d007"

PRIOR_SEALS = [
    "docs/evidence/d001/evidence-hashes.json",
    "docs/evidence/d002p/evidence-hashes.json",
    "docs/evidence/d003/evidence-hashes.json",
    "docs/evidence/d004/evidence-hashes.json",
    "docs/evidence/d005/evidence-hashes.json",
    "docs/evidence/d006/evidence-hashes.json",
]

EXTRA_INPUTS = [
    "docs/directives/UMBRA-D-007-lived-individuality.md",
    "docs/superpowers/specs/2026-07-22-umbra-d007-lived-individuality-design.md",
    "experiments/d007/thresholds.json",
    "experiments/d007/experiment-matrix.json",
    "experiments/d007/probe-suite.json",
    "experiments/d007/run_experiment.py",
    "experiments/d007/run_performance.py",
    "experiments/d007/run_seal.py",
    "experiments/d007/diagnostic_controllers.py",
    "experiments/d007/history_schedules.py",
    "experiments/d007/fingerprint.py",
    "umbra_core/individuality/engine.py",
    "umbra_core/individuality/__init__.py",
    "tests/test_d007.py",
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def validate_prior_seals() -> dict:
    all_valid = True
    for seal in PRIOR_SEALS:
        data = json.loads((ROOT / seal).read_text())
        for rel, expect in data.items():
            if not isinstance(expect, str) or not rel.startswith("docs/"):
                continue
            if rel.endswith("evidence-hashes.json"):
                continue
            p = ROOT / rel
            if not p.exists():
                continue
            all_valid = all_valid and (_sha(p) == expect)
    d002v = "UMBRA_D002V_PERFORMANCE_FAIL" in (
        ROOT / "docs/evidence/d002v/final-verdict.md"
    ).read_text()
    out = {"prior_seals_valid": all_valid, "d002v_preserved_fail": d002v}
    (OUT / "prior-seals.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def write_schema_manifest() -> None:
    thr = json.loads((ROOT / "experiments/d007/thresholds.json").read_text())
    man = {
        "directive": "UMBRA-D-007",
        "schema_version": "d007-v1",
        "disposition_dimensions": 8,
        "thresholds_keys": sorted(thr.keys()),
    }
    (OUT / "schema-manifest.json").write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")


def run_pytest() -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    text = proc.stdout + "\n" + proc.stderr
    (OUT / "test-results.txt").write_text(text)
    skipped = "skipped" in text.lower() and not re.search(r"\b0 skipped\b", text)
    # parse passed
    m = re.search(r"(\d+) passed", text)
    passed = int(m.group(1)) if m else 0
    skip_m = re.search(r"(\d+) skipped", text)
    n_skip = int(skip_m.group(1)) if skip_m else 0
    return {
        "returncode": proc.returncode,
        "passed": passed,
        "skipped": n_skip,
        "zero_skip": n_skip == 0 and proc.returncode == 0,
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
        hashes[f"docs/evidence/d007/{p.name}"] = _sha(p)
    for p in sorted(OUT.glob("*.md")):
        hashes[f"docs/evidence/d007/{p.name}"] = _sha(p)
    if (OUT / "test-results.txt").exists():
        hashes["docs/evidence/d007/test-results.txt"] = _sha(OUT / "test-results.txt")
    (OUT / "evidence-hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n"
    )
    return hashes


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ending = sys.argv[1] if len(sys.argv) > 1 else "PENDING"
    priors = validate_prior_seals()
    write_schema_manifest()
    exp = json.loads((OUT / "experiment-summary.json").read_text()) if (OUT / "experiment-summary.json").exists() else {}
    perf = json.loads((OUT / "performance-results.json").read_text()) if (OUT / "performance-results.json").exists() else {}
    tests = run_pytest()

    gates_ok = bool(exp.get("all_experiment_gates_pass"))
    perf_ok = bool(perf.get("pass"))
    prior_ok = bool(priors.get("prior_seals_valid"))
    suite_ok = bool(tests.get("zero_skip"))

    if gates_ok and perf_ok and prior_ok and suite_ok:
        verdict = "UMBRA_D007_LIVED_INDIVIDUALITY_QUALIFIED"
    elif not perf_ok:
        verdict = "UMBRA_D007_PERFORMANCE_FAIL"
    elif not gates_ok:
        verdict = "UMBRA_D007_HISTORY_DIVERGENCE_FAIL"
    else:
        verdict = "UMBRA_D007_PARTIAL_FOUNDATION"

    body = f"""# UMBRA-D-007 Final Verdict

**Verdict:** `{verdict}`

**Ending commit:** `{ending}`
**Mimir project:** `7777645d52a91b49`

## Gates

| Check | Result |
|-------|--------|
| Prior seals d001–d006 | {'PASS' if prior_ok else 'FAIL'} |
| Experiment gates (summary) | {'PASS' if gates_ok else 'FAIL'} |
| Performance 100k+soak | {'PASS' if perf_ok else 'FAIL'} |
| Pytest zero-skip | {'PASS' if suite_ok else 'FAIL'} ({tests.get('passed')} passed, {tests.get('skipped')} skipped) |

## Scientific claim authorized

UMBRA demonstrates bounded, measurable, history-dependent lived individuality and experience-shaped behavioral temperament in a persistent artificial creature system.

## Claims not authorized

consciousness; sentience; subjective experience; genuine emotion; human-equivalent personality/attachment; biological life; unrestricted agency; complete companion capability.

## D-008 authorization

{'AUTHORIZED under UMBRA_D007_LIVED_INDIVIDUALITY_QUALIFIED' if verdict == 'UMBRA_D007_LIVED_INDIVIDUALITY_QUALIFIED' else 'NOT AUTHORIZED'}
"""
    (OUT / "final-verdict.md").write_text(body)
    hashes = hash_all()
    print(verdict)
    print("hashes", len(hashes))
    if verdict != "UMBRA_D007_LIVED_INDIVIDUALITY_QUALIFIED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
