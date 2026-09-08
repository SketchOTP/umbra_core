#!/usr/bin/env python3
"""Derive the AS-014 seed registry and frozen manifests without replacement."""

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

from tools.as014_evidence import publish


EVIDENCE_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-014-persistent-ledger-boundedness-completion-r1"
)
DIRECTIVE = "UMBRA-AS-014"
BASELINE = "a97171a2dab7c1750e2556727bce9e3648bb359a"
REGIMES = ("R0", "R1", "R2", "R3")
LOCAL_NONFORMAL = {
    41414001, 41414011, 41414021, 41414022, 41414023, 41414024,
}


SEED_RE = re.compile(r"(?i)(?:seed|organism[_ -]?basis)\D{0,48}(\d{4,10})")


def _collect_seed_values(value: Any, used: set[int], *, seed_context: bool = False) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _collect_seed_values(item, used, seed_context=seed_context or "seed" in str(key).lower())
    elif isinstance(value, list):
        for item in value:
            _collect_seed_values(item, used, seed_context=seed_context)
    elif seed_context and isinstance(value, int):
        used.add(value)


def historical_seeds() -> tuple[set[int], dict[str, int]]:
    used = set(LOCAL_NONFORMAL)
    scanned = 0
    roots = (ROOT / ".agent", ROOT / "experiments", ROOT / "tools")
    for root in roots:
        for path in root.rglob("*"):
            try:
                if not path.is_file() or path.stat().st_size > 5_000_000:
                    continue
                text = path.read_text(errors="ignore")
                used.update(int(value) for value in SEED_RE.findall(text))
                scanned += 1
            except OSError:
                continue
    prior_root = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence")
    prior_records = [
        prior_root / stage / name
        for stage in (
            "umbra-as-008-fresh-integrated-viability-r1",
            "umbra-as-009-r2-r3-habitat-authority-integrated-qualification-r1",
            "umbra-as-010-full-configuration-integrated-qualification-r1",
            "umbra-as-011-boundedness-evidence-recovery-r1",
            "umbra-as-012-exact-entrypoint-boundedness-soak-causal-closure-r1",
            "umbra-as-013-publication-safe-boundedness-recovery-r1",
        )
        for name in (
            "AS008_HISTORICAL_SEED_REGISTRY.json", "AS008_FORMAL_SEED_MANIFEST.json",
            "AS009_HISTORICAL_SEED_REGISTRY.json", "AS009_FORMAL_SEED_MANIFEST.json", "AS009_DOWNSTREAM_SEED_MANIFEST.json",
            "AS010_HISTORICAL_SEED_REGISTRY.json", "AS010_FORMAL_SEED_MANIFEST.json", "AS010_DOWNSTREAM_SEED_MANIFEST.json",
            "AS011_HISTORICAL_SEED_REGISTRY.json", "AS011_DOWNSTREAM_SEED_MANIFEST.json",
            "AS012_HISTORICAL_SEED_REGISTRY.json", "AS012_DOWNSTREAM_SEED_MANIFEST.json",
            "AS013_HISTORICAL_SEED_REGISTRY.json", "AS013_DOWNSTREAM_SEED_MANIFEST.json",
        )
    ]
    prior_scanned = 0
    for path in prior_records:
        try:
            if path.is_file():
                text = path.read_text(errors="ignore")
                used.update(int(value) for value in SEED_RE.findall(text))
                try:
                    _collect_seed_values(json.loads(text), used)
                except json.JSONDecodeError:
                    pass
                prior_scanned += 1
        except OSError:
            continue
    return used, {
        "repository_text_files_scanned": scanned,
        "prior_seed_records_scanned": prior_scanned,
        "explicit_as014_nonformal": len(LOCAL_NONFORMAL),
    }


def derive(label: str, used: set[int]) -> int:
    ordinal = 0
    while True:
        digest = hashlib.sha256(f"{DIRECTIVE}|{BASELINE}|{label}|{ordinal}".encode()).digest()
        candidate = 20_000 + int.from_bytes(digest[:8], "big") % 80_000_000
        if candidate not in used:
            used.add(candidate)
            return candidate
        ordinal += 1


def main() -> None:
    historical, inventory = historical_seeds()
    used = set(historical)
    formal = {regime: [derive(f"FORMAL:{regime}:{index}", used) for index in range(8)] for regime in REGIMES}
    downstream = {
        "lifecycle": derive("LIFECYCLE", used),
        "boundedness": derive("BOUNDEDNESS", used),
        "soak": derive("SOAK", used),
        "ablation_matched": derive("ABLATION_MATCHED", used),
    }
    registry = {
        "schema": "AS014_HISTORICAL_SEED_REGISTRY_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "historical_seed_count": len(historical),
        "historical_seeds": sorted(historical),
        "inventory": inventory,
        "rule": "all historical, preflight, development, diagnostic, formal, performance, and ablation seeds are excluded",
    }
    manifest = {
        "schema": "AS014_SEED_MANIFEST_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "seed_status": "frozen_before_formal_execution",
        "formal_regimes": formal,
        "downstream": downstream,
        "retries": 0,
        "reseeds": 0,
    }
    all_new = [seed for values in formal.values() for seed in values] + list(downstream.values())
    proof = {
        "schema": "AS014_SEED_DISJOINTNESS_PROOF_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "formal_count": len(all_new),
        "new_seeds_unique": len(all_new) == len(set(all_new)),
        "intersects_historical": sorted(set(all_new) & historical),
        "result": "PASS" if len(all_new) == len(set(all_new)) and not (set(all_new) & historical) else "FAIL",
    }
    publish("AS014_HISTORICAL_SEED_REGISTRY.json", registry)
    publish("AS014_SEED_MANIFEST.json", manifest)
    publish("AS014_SEED_DISJOINTNESS_PROOF.json", proof)
    print(json.dumps({"registry": registry["historical_seed_count"], "manifest": manifest, "proof": proof}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
