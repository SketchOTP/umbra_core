"""Prospective AS-010 seed registry and disjointness proof."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "b5c7bb2b46e9355a8f5b658f25ebf4f1e7fea27b"
DIRECTIVE = "UMBRA-AS-010"
REGIMES = ("R0", "R1", "R2", "R3")
EXPLICIT = {45878900, 22023239, 57531938, 16827204}
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1")


def collect(value: Any, out: set[int]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if "seed" in str(key).lower() and isinstance(item, int):
                out.add(int(item))
            collect(item, out)
    elif isinstance(value, list):
        for item in value:
            collect(item, out)


def historical() -> set[int]:
    used = set(EXPLICIT)
    for root in (ROOT / "experiments", ROOT / "docs", ROOT / ".agent"):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.stat().st_size > 5_000_000:
                continue
            try:
                raw = path.read_text(errors="ignore")
            except OSError:
                continue
            try:
                collect(json.loads(raw), used)
            except json.JSONDecodeError:
                pass
            for match in re.finditer(r"(?i)seed[^0-9]{0,24}([0-9]{3,12})", raw):
                used.add(int(match.group(1)))
    return used


def build() -> tuple[dict[str, list[int]], set[int]]:
    used = historical()
    regimes: dict[str, list[int]] = {}
    for regime in REGIMES:
        regimes[regime] = []
        for index in range(8):
            digest = hashlib.sha256(f"{DIRECTIVE}|{BASELINE}|{regime}|{index}".encode()).digest()
            candidate = 10_000_000 + int.from_bytes(digest[:8], "big") % 80_000_000
            while candidate in used:
                candidate += 1
            used.add(candidate)
            regimes[regime].append(candidate)
    return regimes, used


def main() -> None:
    regimes, used = build()
    flat = [seed for values in regimes.values() for seed in values]
    registry = {"schema": "AS010_HISTORICAL_SEED_REGISTRY_V1", "directive": DIRECTIVE, "baseline": BASELINE, "seeds": sorted(used), "explicit_exclusions": sorted(EXPLICIT), "source_roots": ["experiments", "docs", ".agent"]}
    manifest = {"schema": "AS010_FORMAL_SEED_MANIFEST_V1", "directive": DIRECTIVE, "baseline": BASELINE, "horizon_ticks": 7200, "runs": 32, "seed_status": "frozen_before_formal_execution", "regimes": regimes, "retries": 0, "reseeds": 0}
    proof = {"schema": "AS010_SEED_DISJOINTNESS_PROOF_V1", "directive": DIRECTIVE, "baseline": BASELINE, "historical_seed_count": len(used) - 32, "formal_seed_count": len(flat), "unique_formal": len(flat) == len(set(flat)), "overlap": sorted(set(flat) & (used - set(flat))), "explicit_overlap": sorted(set(flat) & EXPLICIT), "status": "PASS" if len(flat) == 32 and len(set(flat)) == 32 else "FAIL"}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name, value in (("AS010_HISTORICAL_SEED_REGISTRY.json", registry), ("AS010_FORMAL_SEED_MANIFEST.json", manifest), ("AS010_SEED_DISJOINTNESS_PROOF.json", proof)):
        path = EVIDENCE / name
        if path.exists():
            raise FileExistsError(path)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"manifest": manifest, "proof": proof}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
