"""D-014H3C bounded outcome gate runner.

Uses the existing current-stack D-014 organism runner without changing
production behavior. It executes only the preregistered fixed R0 population
and known R1 gate; fresh holdouts are sealed but not inspected until both pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d014.run_formal import run_case

BASELINE = "5c18693283fc48bef738bd1e0ca5fad678ce211a"
EVIDENCE_ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3c-integrated-affordance-competition-r1")
R0_SEEDS = [41241905, 79871850, 27526357, 49452783, 5366620, 3609315, 77955964, 18929722]
KNOWN_R1 = 57531938
HORIZON = 7200


def freeze_manifest(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    fresh = []
    used = set(R0_SEEDS + [KNOWN_R1])
    for regime in ("R1", "R2", "R3"):
        for index in range(2):
            raw = hashlib.sha256(f"UMBRA-D-014H3C|{BASELINE}|{regime}|{index}".encode()).digest()
            candidate = 20000000 + int.from_bytes(raw[:8], "big") % 60000000
            while candidate in used:
                candidate += 1
            used.add(candidate)
            fresh.append({"regime": regime, "index": index, "seed": candidate})
    manifest = {
        "directive": "UMBRA-D-014H3C",
        "baseline": BASELINE,
        "horizon_ticks": HORIZON,
        "fixed_r0_seeds": R0_SEEDS,
        "known_r1_seed": KNOWN_R1,
        "fresh_holdouts": fresh,
        "fresh_holdouts_sealed_before_outcomes": True,
        "selector": "experiments/research/non-production/d014h3c_shadow.py",
        "production_authority": False,
        "hidden_truth_used": False,
        "retries": 0,
        "reseeds": 0,
    }
    (root / "D014H3C_PROTOCOL_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def run_gate(root: Path, work: Path) -> dict:
    manifest = json.loads((root / "D014H3C_PROTOCOL_MANIFEST.json").read_text())
    rows = []
    for index, seed in enumerate(manifest["fixed_r0_seeds"]):
        case_work = work / f"r0-{index}"
        case_work.mkdir(parents=True, exist_ok=True)
        rows.append(run_case("R0", seed, case_work, HORIZON))
        rows[-1]["gate"] = "R0"
        rows[-1]["seed"] = seed
    r0_pass = all(row["terminal"] == "completed" and row["ticks"] == HORIZON for row in rows)
    known = None
    if r0_pass:
        known_work = work / "known-r1"
        known_work.mkdir(parents=True, exist_ok=True)
        known = run_case("R1", manifest["known_r1_seed"], known_work, HORIZON)
        known["gate"] = "KNOWN_R1"
        known["seed"] = manifest["known_r1_seed"]
    result = {
        "directive": "UMBRA-D-014H3C",
        "baseline": BASELINE,
        "r0": rows,
        "r0_pass": r0_pass,
        "known_r1": known,
        "known_r1_pass": bool(known and known["terminal"] == "completed" and known["ticks"] == HORIZON),
        "fresh_holdouts_executed": False,
        "retries": 0,
        "reseeds": 0,
        "production_authority": False,
        "formal_d014": False,
    }
    (root / "D014H3C_R0_KNOWN_R1_RESULTS.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("freeze", "gate"), required=True)
    parser.add_argument("--root", type=Path, default=EVIDENCE_ROOT)
    parser.add_argument("--work", type=Path, default=Path("/dev/shm/umbra-h3c-work"))
    args = parser.parse_args()
    if args.mode == "freeze":
        print(json.dumps(freeze_manifest(args.root), indent=2, sort_keys=True))
    else:
        print(json.dumps(run_gate(args.root, args.work), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
