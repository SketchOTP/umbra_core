#!/usr/bin/env python3
"""Derive AS-015 seed records before any formal organism is created."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.as015_evidence import publish


DIRECTIVE = "UMBRA-AS-015"
BASELINE = "b8977c6c05ad3ca89743368bbfd0fc48bb2b1ee7"
REGIMES = ("R0", "R1", "R2", "R3")
# Population and literal-CLI preflights are development-only and are excluded
# prospectively from every AS-015 formal namespace.
NONFORMAL = {
    41515001, 41515002, 41515003, 41515004, 41515005, 41515006,
    41515011, 41515012, 41515013, 41515014, 41515015,
}
EXPLICIT = {32550454, 57531938, 45878900, 22023239, 16827204}
SEED_RE = re.compile(r"(?i)(?:seed|organism[_ -]?basis)\D{0,48}(\d{4,10})")


def collect(value: Any, values: set[int], *, seed_context: bool = False) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            collect(item, values, seed_context=seed_context or "seed" in str(key).lower())
    elif isinstance(value, list):
        for item in value:
            collect(item, values, seed_context=seed_context)
    elif seed_context and isinstance(value, int):
        values.add(value)


def historical() -> tuple[set[int], dict[str, int]]:
    values = set(NONFORMAL) | set(EXPLICIT)
    scanned = 0
    for root in (ROOT / ".agent", ROOT / "experiments", ROOT / "tools"):
        for path in root.rglob("*"):
            try:
                if not path.is_file() or path.stat().st_size > 5_000_000:
                    continue
                content = path.read_text(errors="ignore")
                values.update(int(item) for item in SEED_RE.findall(content))
                scanned += 1
            except OSError:
                continue
    evidence_root = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence")
    evidence_scanned = 0
    for path in evidence_root.glob("umbra-*/**/*SEED*.json"):
        try:
            if path.stat().st_size > 5_000_000:
                continue
            content = path.read_text(errors="ignore")
            values.update(int(item) for item in SEED_RE.findall(content))
            collect(json.loads(content), values)
            evidence_scanned += 1
        except (OSError, json.JSONDecodeError):
            continue
    return values, {
        "repository_files_scanned": scanned,
        "evidence_seed_records_scanned": evidence_scanned,
        "as015_nonformal_exclusions": sorted(NONFORMAL),
        "explicit_exclusions": sorted(EXPLICIT),
    }


def derive(label: str, values: set[int]) -> int:
    ordinal = 0
    while True:
        digest = hashlib.sha256(f"{DIRECTIVE}|{BASELINE}|{label}|{ordinal}".encode()).digest()
        result = 20_000 + int.from_bytes(digest[:8], "big") % 80_000_000
        if result not in values:
            values.add(result)
            return result
        ordinal += 1


def main() -> None:
    used, inventory = historical()
    generated = set(used)
    formal = {regime: [derive(f"FORMAL:{regime}:{index}", generated) for index in range(8)] for regime in REGIMES}
    downstream = {
        "lifecycle": derive("LIFECYCLE", generated),
        "boundedness": derive("BOUNDEDNESS", generated),
        "soak": derive("SOAK", generated),
        "ablation_matched": derive("ABLATION_MATCHED", generated),
    }
    new_values = [seed for seeds in formal.values() for seed in seeds] + list(downstream.values())
    registry = {
        "schema": "AS015_HISTORICAL_SEED_REGISTRY_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "historical_seed_count": len(used),
        "historical_seeds": sorted(used),
        "inventory": inventory,
        "rule": "all historical, formal, diagnostic, smoke, development, performance, and ablation seeds are excluded",
    }
    manifest = {
        "schema": "AS015_SEED_MANIFEST_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "seed_status": "frozen_before_formal_execution",
        "formal_regimes": formal,
        "downstream": downstream,
        "retries": 0,
        "reseeds": 0,
    }
    proof = {
        "schema": "AS015_SEED_DISJOINTNESS_PROOF_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "new_seed_count": len(new_values),
        "unique": len(new_values) == len(set(new_values)),
        "historical_intersection": sorted(set(new_values) & used),
        "explicit_intersection": sorted(set(new_values) & EXPLICIT),
        "result": "PASS" if len(new_values) == len(set(new_values)) and not (set(new_values) & used) else "FAIL",
    }
    publish("AS015_HISTORICAL_SEED_REGISTRY.json", registry)
    publish("AS015_SEED_MANIFEST.json", manifest)
    publish("AS015_SEED_DISJOINTNESS_PROOF.json", proof)
    print(json.dumps({"manifest": manifest, "proof": proof}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
