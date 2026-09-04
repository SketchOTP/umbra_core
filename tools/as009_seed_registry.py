#!/usr/bin/env python3
"""Build and validate the AS-009 fresh R2/R3 seed manifest."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-009-r2-r3-habitat-authority-integrated-qualification-r1")
DIRECTIVE = "UMBRA-AS-009"
BASELINE = "f5e73ec4a3f5b677590d079d2bf2e506a699134e"
HORIZON = 7200
FORBIDDEN_EXPLICIT = {45878900, 22023239, 57531938, 16827204}


def collect(value: Any, out: set[int], path: str = "") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if "seed" in str(key).lower() and isinstance(item, int):
                out.add(item)
            if "seed" in str(key).lower() and isinstance(item, list):
                out.update(int(seed) for seed in item if isinstance(seed, int))
            collect(item, out, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            collect(item, out, f"{path}[{index}]")


def historical_seeds() -> tuple[set[int], list[str]]:
    found: set[int] = set(FORBIDDEN_EXPLICIT)
    sources: list[str] = []
    prior_registry = EVIDENCE.parent / "umbra-as-008-fresh-integrated-viability-r1" / "AS008_HISTORICAL_SEED_REGISTRY.json"
    if prior_registry.exists():
        try:
            collect(json.loads(prior_registry.read_text()), found)
            sources.append(str(prior_registry))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
    prior_manifest = EVIDENCE.parent / "umbra-as-008-fresh-integrated-viability-r1" / "AS008_FORMAL_SEED_MANIFEST.json"
    if prior_manifest.exists():
        try:
            collect(json.loads(prior_manifest.read_text()), found)
            sources.append(str(prior_manifest))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
    paths = list((ROOT / "experiments").rglob("*.json")) + list((ROOT / "docs").rglob("*.json"))
    for path in sorted(set(paths)):
        if path == EVIDENCE / "AS009_HISTORICAL_SEED_REGISTRY.json":
            continue
        try:
            value = json.loads(path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        before = len(found)
        collect(value, found)
        if len(found) != before:
            sources.append(str(path))
    return found, sources


def fresh_seed(regime: str, index: int, used: set[int]) -> int:
    digest = hashlib.sha256(f"{DIRECTIVE}|{BASELINE}|{regime}|{index}|fresh".encode()).digest()
    candidate = 10_000_000 + int.from_bytes(digest[:8], "big") % 80_000_000
    while candidate in used or candidate in FORBIDDEN_EXPLICIT:
        candidate += 1
    used.add(candidate)
    return candidate


def durable_json(path: Path, value: Any) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def build() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    historical, sources = historical_seeds()
    used = set(historical)
    seeds = {regime: [fresh_seed(regime, index, used) for index in range(8)] for regime in ("R2", "R3")}
    flat = [seed for regime in ("R2", "R3") for seed in seeds[regime]]
    registry = {
        "schema": "AS009_HISTORICAL_SEED_REGISTRY_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "seeds": sorted(historical),
        "count": len(historical),
        "source_count": len(sources),
        "explicit_forbidden": sorted(FORBIDDEN_EXPLICIT),
        "source_roots": ["repository experiments/docs JSON", "retained evidence JSON"],
    }
    manifest = {
        "schema": "AS009_FORMAL_SEED_MANIFEST_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "horizon_ticks": HORIZON,
        "runs": 16,
        "regimes": {regime: list(seeds[regime]) for regime in ("R2", "R3")},
        "seed_status": "frozen_before_formal_execution",
        "partial_as008_seed_excluded": 16827204,
    }
    proof = {
        "schema": "AS009_SEED_DISJOINTNESS_PROOF_V1",
        "historical_count": len(historical),
        "formal_count": len(flat),
        "formal_unique": len(set(flat)) == len(flat),
        "overlap": sorted(set(flat) & historical),
        "explicit_forbidden_overlap": sorted(set(flat) & FORBIDDEN_EXPLICIT),
        "status": "PASS" if len(flat) == 16 and len(set(flat)) == 16 and not (set(flat) & historical) else "FAIL",
    }
    return registry, manifest, proof


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    registry, manifest, proof = build()
    for name, value in (("AS009_HISTORICAL_SEED_REGISTRY.json", registry), ("AS009_FORMAL_SEED_MANIFEST.json", manifest), ("AS009_SEED_DISJOINTNESS_PROOF.json", proof)):
        path = args.output / name
        durable_json(path, value)
    print(json.dumps({"historical": registry["count"], "formal": manifest["runs"], "overlap": proof["overlap"], "status": proof["status"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
