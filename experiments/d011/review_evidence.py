"""Read-only D-011C evidence reviewer, independent of experiment execution."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    evidence = ROOT / "docs/evidence/d011"
    required = ["control-results.json", "replay-results.json", "performance-results.json", "prior-seal-validation.md"]
    checks = {name: (evidence / name).is_file() for name in required}
    controls = json.loads((evidence / "control-results.json").read_text())
    replay = json.loads((evidence / "replay-results.json").read_text())
    performance = json.loads((evidence / "performance-results.json").read_text())
    checks["controls_complete"] = all(f"C{number}" in controls for number in range(9))
    checks["raw_isolated"] = controls["C0"]["raw_durable_count"] == 0 and controls["C4"]["production_raw_rejected"]
    checks["hostile_contained"] = not controls["C5"]["adapter_memory_or_organism_reference"]
    checks["ledger_replay"] = all(replay["fail_closed"].values()) and replay["accepted_observations_reconstruct_identically"]
    checks["performance_reproducible"] = performance["result"] == "PASS" and len(performance["runs"]) == 2 and all(run["raw_payload_durable_count"] == 0 for run in performance["runs"])
    checks["prior_seals_unchanged"] = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "docs/evidence/d001", "docs/evidence/d002", "docs/evidence/d003", "docs/evidence/d004", "docs/evidence/d005", "docs/evidence/d006", "docs/evidence/d007", "docs/evidence/d008", "docs/evidence/d009", "experiments/d010", ".agent/RECORD.md"], cwd=ROOT).returncode == 0
    verdict = "APPROVE" if all(checks.values()) else "NEEDS_FIXES"
    print(json.dumps({"verdict": verdict, "checks": checks}, sort_keys=True))
    return 0 if verdict == "APPROVE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
