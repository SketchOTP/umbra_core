#!/usr/bin/env python3
"""Derive AS-016 formal and downstream seeds before scientific lock."""

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

from tools.as016_evidence import publish


DIRECTIVE = "UMBRA-AS-016"
BASELINE = "17859e03143b2278e612efeb3e96684f830b741f"
REGIMES = ("R0", "R1", "R2", "R3")
DEVELOPMENT = {
    41616011, 41616012, 41616013, 41616014,
    41616021, 41616022, 41616023, 41616024,
    41616031, 41616032, 41616033, 41616034,
}
EXPLICIT = {1995954, 32550454, 57531938, 45878900, 22023239, 16827204}
SEED_RE = re.compile(r"(?i)(?:seed|organism[_ -]?basis)\D{0,48}(\d{4,10})")
EVIDENCE_ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence")


def _collect(value: Any, found: set[int], *, seed_context: bool = False) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _collect(item, found, seed_context=seed_context or "seed" in str(key).lower())
    elif isinstance(value, list):
        for item in value:
            _collect(item, found, seed_context=seed_context)
    elif seed_context and isinstance(value, int):
        found.add(value)


def _historical() -> tuple[set[int], dict[str, Any]]:
    found = set(DEVELOPMENT) | set(EXPLICIT)
    repository_files = 0
    for directory in (ROOT / ".agent", ROOT / "experiments", ROOT / "tools"):
        for path in directory.rglob("*"):
            try:
                if not path.is_file() or path.stat().st_size > 5_000_000:
                    continue
                found.update(int(value) for value in SEED_RE.findall(path.read_text(errors="ignore")))
                repository_files += 1
            except OSError:
                continue
    evidence_files = 0
    for path in EVIDENCE_ROOT.glob("umbra-*/**/*SEED*.json"):
        try:
            if path.stat().st_size > 5_000_000:
                continue
            content = path.read_text(errors="ignore")
            found.update(int(value) for value in SEED_RE.findall(content))
            _collect(json.loads(content), found)
            evidence_files += 1
        except (OSError, json.JSONDecodeError):
            continue
    return found, {
        "repository_files_scanned": repository_files,
        "evidence_seed_records_scanned": evidence_files,
        "as016_development_exclusions": sorted(DEVELOPMENT),
        "explicit_exclusions": sorted(EXPLICIT),
    }


def _derive(label: str, reserved: set[int]) -> int:
    ordinal = 0
    while True:
        digest = hashlib.sha256(f"{DIRECTIVE}|{BASELINE}|{label}|{ordinal}".encode()).digest()
        candidate = 20_000 + int.from_bytes(digest[:8], "big") % 80_000_000
        if candidate not in reserved:
            reserved.add(candidate)
            return candidate
        ordinal += 1


def main() -> None:
    historical, inventory = _historical()
    reserved = set(historical)
    formal = {
        regime: [_derive(f"FORMAL:{regime}:{index}", reserved) for index in range(8)]
        for regime in REGIMES
    }
    downstream = {
        "lifecycle": _derive("LIFECYCLE", reserved),
        "boundedness": _derive("BOUNDEDNESS", reserved),
        "soak": _derive("SOAK", reserved),
        "ablation_matched": _derive("ABLATION_MATCHED", reserved),
    }
    new_seeds = [seed for values in formal.values() for seed in values] + list(downstream.values())
    registry = {
        "schema": "AS016_HISTORICAL_SEED_REGISTRY_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "historical_seed_count": len(historical),
        "historical_seeds": sorted(historical),
        "inventory": inventory,
        "rule": "all historical, formal, diagnostic, smoke, development, performance, and ablation seeds are excluded",
    }
    manifest = {
        "schema": "AS016_SEED_MANIFEST_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "seed_status": "frozen_before_formal_execution",
        "formal_regimes": formal,
        "downstream": downstream,
        "retries": 0,
        "reseeds": 0,
    }
    proof = {
        "schema": "AS016_SEED_DISJOINTNESS_PROOF_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "new_seed_count": len(new_seeds),
        "unique": len(new_seeds) == len(set(new_seeds)),
        "historical_intersection": sorted(set(new_seeds) & historical),
        "explicit_intersection": sorted(set(new_seeds) & EXPLICIT),
        "result": "PASS" if len(new_seeds) == len(set(new_seeds)) and not (set(new_seeds) & historical) else "FAIL",
    }
    publish("AS016_HISTORICAL_SEED_REGISTRY.json", registry)
    publish("AS016_SEED_MANIFEST.json", manifest)
    publish("AS016_SEED_DISJOINTNESS_PROOF.json", proof)
    print(json.dumps({"manifest": manifest, "proof": proof}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
