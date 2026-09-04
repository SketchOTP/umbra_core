#!/usr/bin/env python3
"""Build the AS-008 historical seed registry and disjoint formal manifest.

This is pre-execution protocol tooling. It scans retained repository/evidence
records for seed-bearing fields and filenames, then derives AS-008 seeds from a
domain-separated hash namespace with deterministic collision resolution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

SEED_RE = re.compile(r"(?i)(?:seed(?:[_ -][a-z0-9-]+)*|organism[_ -]?basis)\D{0,48}(\d{4,10})")
FILENAME_RE = re.compile(r"(?i)(?:seed[-_])([0-9]{4,10})")
REGIMES = ("R0", "R1", "R2", "R3")


def iter_sources(repo: Path, live_root: Path) -> list[Path]:
    roots = [repo / ".agent", repo / "experiments", repo / "docs"]
    paths: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.stat().st_size <= 25_000_000:
                paths.add(path)
    # The live-evidence mount is intentionally not recursively read here: it is
    # a large remote tree. Its consumed AS-007 smoke selections are recorded
    # explicitly below, while repository-held manifests and task records are
    # scanned locally.
    return sorted(paths)


def find_seeds(paths: list[Path], repo: Path) -> tuple[set[int], dict[str, list[int]]]:
    seeds: set[int] = set()
    sources: dict[str, list[int]] = {}
    for path in paths:
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        found = {int(value) for value in SEED_RE.findall(text)}
        found.update(int(value) for value in FILENAME_RE.findall(path.name))
        if found:
            relative = str(path.relative_to(repo)) if path.is_relative_to(repo) else str(path)
            sources[relative] = sorted(found)
            seeds.update(found)
    external = {
        "/srv/.../umbra-as-007/AS007 downstream preflight": [5366620, 57531938, 76190037, 29294300],
    }
    for source, values in external.items():
        sources[source] = values
        seeds.update(values)
    return seeds, sources


def derive(baseline: str, used: set[int]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    reserved = set(used)
    for regime in REGIMES:
        result[regime] = []
        for index in range(8):
            material = f"UMBRA-AS-008|{baseline}|FORMAL|{regime}|{index}"
            candidate = 20_000 + int.from_bytes(hashlib.sha256(material.encode()).digest()[:8], "big") % 79_980_000
            while candidate in reserved:
                candidate = 20_000 + (candidate - 20_000 + 1) % 79_980_000
            reserved.add(candidate)
            result[regime].append(candidate)
    return result


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--live-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--baseline", required=True)
    args = parser.parse_args()
    paths = iter_sources(args.repo, args.live_root)
    historical, sources = find_seeds(paths, args.repo)
    formal = derive(args.baseline, historical)
    flat = [seed for values in formal.values() for seed in values]
    all_values = set(flat)
    proof = {
        "schema": "AS008_SEED_DISJOINTNESS_PROOF_V1",
        "directive": "UMBRA-AS-008",
        "baseline": args.baseline,
        "historical_seed_count": len(historical),
        "formal_seed_count": len(flat),
        "formal_unique": len(all_values) == 32,
        "formal_historical_overlap": sorted(all_values & historical),
        "historical_sources_scanned": len(paths),
        "disjoint": len(flat) == 32 and len(all_values & historical) == 0,
        "collision_resolution": "increment within 20,000..79,999,999 until unused",
    }
    registry = {
        "schema": "AS008_HISTORICAL_SEED_REGISTRY_V1",
        "directive": "UMBRA-AS-008",
        "baseline": args.baseline,
        "source_scope": [str(args.repo / ".agent"), str(args.repo / "experiments"), str(args.repo / "docs"), str(args.live_root)],
        "seed_count": len(historical),
        "seeds": sorted(historical),
        "sources": sources,
    }
    manifest = {
        "schema": "AS008_FORMAL_SEED_MANIFEST_V1",
        "directive": "UMBRA-AS-008",
        "baseline": args.baseline,
        "namespace": "UMBRA-AS-008|<baseline>|FORMAL|<regime>|<index>",
        "horizon_ticks": 7200,
        "seeds": formal,
        "runs": 32,
        "seed_status": "frozen_before_formal_execution",
    }
    write(args.evidence_root / "AS008_HISTORICAL_SEED_REGISTRY.json", registry)
    write(args.evidence_root / "AS008_FORMAL_SEED_MANIFEST.json", manifest)
    write(args.evidence_root / "AS008_SEED_DISJOINTNESS_PROOF.json", proof)
    print(json.dumps({"registry": registry, "manifest": manifest, "proof": proof}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
