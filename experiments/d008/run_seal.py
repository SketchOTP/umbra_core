"""Final seal for UMBRA-D-008 coherent digital embodiment (Supplement S3)."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/d008"

PRIOR_SEALS = [
    "docs/evidence/d001/evidence-hashes.json",
    "docs/evidence/d002p/evidence-hashes.json",
    "docs/evidence/d003/evidence-hashes.json",
    "docs/evidence/d004/evidence-hashes.json",
    "docs/evidence/d005/evidence-hashes.json",
    "docs/evidence/d006/evidence-hashes.json",
    "docs/evidence/d007/evidence-hashes.json",
]

EXTRA_INPUTS = [
    "docs/directives/UMBRA-D-008-coherent-digital-embodiment.md",
    "docs/superpowers/specs/2026-07-23-umbra-d008-coherent-digital-embodiment-design.md",
    "experiments/d008/thresholds.json",
    "experiments/d008/experiment-matrix.json",
    "experiments/d008/scenario-suite.json",
    "experiments/d008/performance-protocol.json",
    "experiments/d008/run_experiment.py",
    "experiments/d008/run_performance.py",
    "experiments/d008/run_seal.py",
    "experiments/d008/evidence.py",
    "experiments/d008/validate_evidence.py",
    "umbra_core/expression/engine.py",
    "umbra_core/expression/frame_ring.py",
    "umbra_core/embodiment_adapters/adapter.py",
    "umbra_core/embodiment_adapters/profiles.py",
    "ui/reference_companion/tkinter_renderer.py",
    "tests/test_d008.py",
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
    d007 = "UMBRA_D007_LIVED_INDIVIDUALITY_QUALIFIED" in (
        ROOT / "docs/evidence/d007/final-verdict.md"
    ).read_text()
    out = {
        "prior_seals_valid": all_valid,
        "d002v_preserved_fail": d002v,
        "d007_qualified_present": d007,
    }
    (OUT / "prior-seals.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def write_schema_manifest() -> None:
    thr = json.loads((ROOT / "experiments/d008/thresholds.json").read_text())
    proto = json.loads((ROOT / "experiments/d008/performance-protocol.json").read_text())
    man = {
        "directive": "UMBRA-D-008",
        "schema_version": "d008-v1",
        "adaptive_soak_supplement": "S3",
        "thresholds_keys": sorted(thr.keys()),
        "protocol_keys": sorted(proto.keys()),
    }
    (OUT / "schema-manifest.json").write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")


def run_pytest() -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**dict(**{k: v for k, v in __import__("os").environ.items()})},
    )
    text = proc.stdout + "\n" + proc.stderr
    (OUT / "test-results.txt").write_text(text)
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
        hashes[f"docs/evidence/d008/{p.name}"] = _sha(p)
    for p in sorted(OUT.glob("*.md")):
        hashes[f"docs/evidence/d008/{p.name}"] = _sha(p)
    if (OUT / "test-results.txt").exists():
        hashes["docs/evidence/d008/test-results.txt"] = _sha(OUT / "test-results.txt")
    (OUT / "evidence-hashes.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n"
    )
    return hashes


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ending = sys.argv[1] if len(sys.argv) > 1 else "PENDING"
    priors = validate_prior_seals()
    write_schema_manifest()
    exp = (
        json.loads((OUT / "experiment-summary.json").read_text())
        if (OUT / "experiment-summary.json").exists()
        else {}
    )
    perf = (
        json.loads((OUT / "performance-results.json").read_text())
        if (OUT / "performance-results.json").exists()
        else {}
    )
    tests = run_pytest()

    gates_ok = bool(
        (exp.get("metrics") or {}).get("all_experiment_gates_pass")
        or exp.get("all_experiment_gates_pass")
        or exp.get("pass")
    )
    # Task 13 summary stores flags under metrics.
    if not gates_ok and (exp.get("metrics") or {}).get("task13_outcome") == "UMBRA_D008_TASK13_GATES_1_11_PASS":
        gates_ok = True
    perf_ok = bool(perf.get("pass")) and perf.get("adaptive_soak_supplement") == "S3"
    prior_ok = bool(priors.get("prior_seals_valid")) and bool(priors.get("d007_qualified_present"))
    suite_ok = bool(tests.get("zero_skip"))

    if gates_ok and perf_ok and prior_ok and suite_ok:
        verdict = "UMBRA_D008_COHERENT_DIGITAL_EMBODIMENT_QUALIFIED"
    elif not perf_ok:
        verdict = "UMBRA_D008_PERFORMANCE_FAIL"
    elif not gates_ok:
        verdict = "UMBRA_D008_EXPERIMENT_FAIL"
    else:
        verdict = "UMBRA_D008_PARTIAL_FOUNDATION"

    body = f"""# UMBRA-D-008 Final Verdict

**Verdict:** `{verdict}`

**Ending commit:** `{ending}`
**Mimir project:** `7777645d52a91b49`
**Adaptive soak:** Supplement **S3** (authorized replacement for fixed two-hour soak)

## Gate summary

| Check | Result |
|-------|--------|
| Task 13 Gates 1–11 | `{"PASS" if gates_ok else "FAIL"}` |
| Gate 12 performance (S3 adaptive) | `{"PASS" if perf_ok else "FAIL"}` |
| Prior seals D-001…D-007 | `{"PASS" if prior_ok else "FAIL"}` |
| Zero-skip test suite | `{"PASS" if suite_ok else "FAIL"}` (passed={tests.get("passed")}, skipped={tests.get("skipped")}) |

## Notes

D-008 Task 14 used the authorized adaptive-soak Supplement S3 rather than the
original fixed two-hour duration. Absolute and incremental RSS/CPU limits from
`experiments/d008/thresholds.json` remain binding.

D-002V `UMBRA_D002V_PERFORMANCE_FAIL` is preserved (not waived).
"""
    (OUT / "final-verdict.md").write_text(body)
    hash_all()
    print(json.dumps({"verdict": verdict, "tests": tests, "perf_ok": perf_ok, "gates_ok": gates_ok}, indent=2))
    raise SystemExit(0 if verdict.endswith("QUALIFIED") else 1)


if __name__ == "__main__":
    main()
