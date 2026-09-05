#!/usr/bin/env python3
"""Create historically disjoint AS-010 downstream seeds."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1")
DIRECTIVE = "UMBRA-AS-010"
BASELINE = "b5c7bb2b46e9355a8f5b658f25ebf4f1e7fea27b"


def collect(value: object, used: set[int]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if "seed" in str(key).lower():
                if isinstance(item, int):
                    used.add(item)
                elif isinstance(item, list):
                    used.update(int(x) for x in item if isinstance(x, int))
            collect(item, used)
    elif isinstance(value, list):
        for item in value:
            collect(item, used)


def durable(path: Path, value: object) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if path.exists():
        raise FileExistsError(path)
    os.replace(tmp, path)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> None:
    used: set[int] = {45878900, 22023239, 57531938, 16827204}
    sources: list[str] = []
    for path in sorted(set((ROOT / "experiments").rglob("*.json")) | set((ROOT / "docs").rglob("*.json"))):
        try:
            value = json.loads(path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        before = len(used)
        collect(value, used)
        if len(used) != before:
            sources.append(str(path))
    for path in (EVIDENCE / "AS010_HISTORICAL_SEED_REGISTRY.json", EVIDENCE / "AS010_FORMAL_SEED_MANIFEST.json"):
        if path.exists():
            collect(json.loads(path.read_text()), used)
            sources.append(str(path))

    groups: dict[str, list[int]] = {}
    counts = {"lifecycle": 1, "boundedness": 1, "soak": 1, "ablation": 4}
    for name, count in counts.items():
        values: list[int] = []
        for index in range(count):
            digest = hashlib.sha256(f"{DIRECTIVE}|{BASELINE}|downstream|{name}|{index}".encode()).digest()
            candidate = 10_000_000 + int.from_bytes(digest[:8], "big") % 80_000_000
            while candidate in used:
                candidate += 1
            used.add(candidate)
            values.append(candidate)
        groups[name] = values

    flat = [seed for values in groups.values() for seed in values]
    proof = {
        "schema": "AS010_DOWNSTREAM_SEED_DISJOINTNESS_PROOF_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "unique": len(flat) == len(set(flat)),
        "overlap_explicit": sorted(set(flat) & {45878900, 22023239, 57531938, 16827204}),
        "overlap_formal": sorted(set(flat) & {seed for values in json.loads((EVIDENCE / "AS010_FORMAL_SEED_MANIFEST.json").read_text())["regimes"].values() for seed in values}),
        "status": "PASS",
    }
    proof["status"] = "PASS" if proof["unique"] and not proof["overlap_explicit"] and not proof["overlap_formal"] else "FAIL"
    manifest = {
        "schema": "AS010_DOWNSTREAM_SEED_MANIFEST_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "seed_status": "frozen_before_downstream_execution",
        "groups": groups,
        "forbidden_explicit": [45878900, 22023239, 57531938, 16827204],
        "source_count": len(sources),
        "historical_registry": str(EVIDENCE / "AS010_HISTORICAL_SEED_REGISTRY.json"),
        "formal_manifest": str(EVIDENCE / "AS010_FORMAL_SEED_MANIFEST.json"),
    }
    durable(EVIDENCE / "AS010_DOWNSTREAM_SEED_MANIFEST.json", manifest)
    durable(EVIDENCE / "AS010_DOWNSTREAM_SEED_DISJOINTNESS_PROOF.json", proof)
    print(json.dumps({"groups": groups, "proof": proof}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
