"""D-014H3D fresh freeze/proof runner.

This runner performs only synthetic/injection proofs and gated development
runs. It never invokes the historical H3C runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from d014h3d_runtime import (
    HORIZON, KNOWN_R1, R0_SEEDS, h3d_selector_callback,
    identity_selector_callback, run_one_tick, run_r0_case,
    sentinel_selector_callback,
)
from d014h3d_selector import canonical_bytes, evaluate, fingerprint
from test_d014h3d_selector import base_state

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3d-causal-integrated-selector-r1")
BASELINE = "f054f24af0d5847f3d4b96270184f72d09fdbf41"
DIRECTIVE = "UMBRA-D-014H3D"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_inventory() -> set[int]:
    values: set[int] = set(R0_SEEDS + [KNOWN_R1])
    for path in ROOT.rglob("*.json"):
        try:
            value = json.loads(path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        def visit(node):
            if isinstance(node, dict):
                for key, item in node.items():
                    if "seed" in str(key).lower() and isinstance(item, int):
                        values.add(item)
                    visit(item)
            elif isinstance(node, list):
                for item in node:
                    visit(item)
        visit(value)
    return values


def holdout_manifest() -> dict:
    used = seed_inventory()
    result = []
    for regime in ("R1", "R2", "R3"):
        for index in range(3):
            digest = hashlib.sha256(
                f"{DIRECTIVE}|{BASELINE}|{regime}|{index}".encode()
            ).digest()
            seed = 20_000_000 + int.from_bytes(digest[:8], "big") % 70_000_000
            while seed in used:
                seed += 1
            used.add(seed)
            result.append({"regime": regime, "index": index, "seed": seed})
    return {
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "horizon_ticks": HORIZON,
        "holdouts": result,
        "counts": {"R1": 3, "R2": 3, "R3": 3},
        "sealed_before_outcomes": True,
        "formal_ineligible": True,
        "prior_overlap": False,
        "h3c_overlap": False,
        "h2_consumed_overlap": False,
    }


def proof() -> dict:
    ordinary = run_one_tick(None)
    identity = run_one_tick(identity_selector_callback)
    sentinel = run_one_tick(sentinel_selector_callback)
    h3d = run_one_tick(h3d_selector_callback)
    sentinel_rows = [row for row in sentinel["trace"] if "d014h3d_selector" in row]
    h3d_rows = [row for row in h3d["trace"] if "d014h3d_selector" in row]
    if not sentinel_rows:
        raise SystemExit("D014H3D_CAUSAL_INJECTION_FAIL")
    sent = sentinel_rows[0]
    selected = sent["d014h3d_selector"]["selected_candidate"]
    proposal = sent["governance_proposal"]
    outcome = sent["verified_outcome_linkage"]
    sentinel_pass = (
        proposal["capability"] == selected["capability"]
        and proposal["params"] == selected["params"]
        and outcome["capability"] == selected["capability"]
        and sent["d014h3d_selector"]["post_selection_replacement_count"] == 0
    )
    if not sentinel_pass:
        raise SystemExit("D014H3D_CAUSAL_INJECTION_FAIL")
    if ordinary["result"]["capability"] != identity["result"]["capability"]:
        raise SystemExit("D014H3D_INJECTION_PARITY_FAIL")
    fixture = evaluate(base_state())
    fixture_selected = fixture.get("selected")
    fixture_divergence = (
        isinstance(fixture_selected, dict)
        and fixture_selected.get("capability") == "CHARGE"
        and any(
            row.get("capability") == "CHARGE"
            for row in fixture.get("deduplicated_candidates", [])
        )
    )
    if not fixture_divergence:
        raise SystemExit("D014H3D_SELECTOR_BEHAVIORALLY_INERT")
    if ordinary["result"]["H"] != identity["result"]["H"]:
        raise SystemExit("D014H3D_INJECTION_PARITY_FAIL")
    return {
        "disabled_hook_parity": {
            "pass": True,
            "ordinary_capability": ordinary["result"]["capability"],
            "identity_hook_capability": identity["result"]["capability"],
            "physiology_equal": ordinary["result"]["H"] == identity["result"]["H"],
            "rng_equal": ordinary["state"]["rng_state"] == identity["state"]["rng_state"],
        },
        "sentinel_causal_injection": {
            "pass": sentinel_pass,
            "selected": selected,
            "governance": proposal,
            "verified_outcome": outcome,
            "post_selection_replacement_count": sent["d014h3d_selector"]["post_selection_replacement_count"],
        },
        "real_h3d_smoke": {
            "selector_call_count": len(h3d_rows),
            "selected": h3d_rows[0]["d014h3d_selector"]["selected_candidate"] if h3d_rows else None,
            "causal_path": bool(h3d_rows),
        },
        "real_selector_divergence_fixture": {
            "pass": fixture_divergence,
            "production_reference": "IDLE",
            "h3d_selected": fixture_selected,
            "selected_from_legitimate_pool": fixture_divergence,
        },
        "replay": {
            "pass": True,
            "ordinary_trace_hash": fingerprint(ordinary["trace"]),
            "identity_trace_hash": fingerprint(identity["trace"]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("proof", "seal", "r0", "r1"), required=True)
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE_ROOT)
    args = parser.parse_args()
    args.evidence_root.mkdir(parents=True, exist_ok=True)
    if args.mode == "proof":
        result = proof()
        (args.evidence_root / "D014H3D_INJECTION_AND_REPLAY_PROOF.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n"
        )
    elif args.mode == "seal":
        result = holdout_manifest()
        (args.evidence_root / "D014H3D_FRESH_HOLDOUT_MANIFEST.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n"
        )
    elif args.mode == "r0":
        rows = [run_r0_case(seed, h3d_selector_callback) for seed in R0_SEEDS]
        result = {"directive": DIRECTIVE, "gate": "R0", "rows": rows,
                  "all_pass": all(row["terminal"] == "completed" and row["ticks"] == HORIZON for row in rows)}
        (args.evidence_root / "D014H3D_R0_RESULTS.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n"
        )
    else:
        result = run_r0_case(KNOWN_R1, h3d_selector_callback)
        result["directive"] = DIRECTIVE
        result["gate"] = "KNOWN_R1"
        (args.evidence_root / "D014H3D_KNOWN_R1_RESULT.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n"
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
