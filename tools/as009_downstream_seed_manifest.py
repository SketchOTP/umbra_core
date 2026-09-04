#!/usr/bin/env python3
"""Create the post-population AS-009 seed manifest without reusing any prior seed."""
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


def collect(value: Any, out: set[int]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if "seed" in str(key).lower():
                if isinstance(item, int): out.add(item)
                if isinstance(item, list): out.update(int(x) for x in item if isinstance(x, int))
            collect(item, out)
    elif isinstance(value, list):
        for item in value: collect(item, out)


def main() -> None:
    used: set[int] = {45878900, 22023239, 57531938, 16827204}
    sources: list[str] = []
    for path in sorted(set((ROOT / "experiments").rglob("*.json")) | set((ROOT / "docs").rglob("*.json"))):
        try: value = json.loads(path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError): continue
        before = len(used); collect(value, used)
        if len(used) != before: sources.append(str(path))
    registry = EVIDENCE / "AS009_HISTORICAL_SEED_REGISTRY.json"
    formal = EVIDENCE / "AS009_FORMAL_SEED_MANIFEST.json"
    for path in (registry, formal):
        if path.exists():
            collect(json.loads(path.read_text()), used)
    groups = {"lifecycle": 9001, "boundedness": 9002, "soak": 9003, "ablation": 9004}
    seeds: dict[str, list[int]] = {}
    for name, count in (("lifecycle", 1), ("boundedness", 1), ("soak", 1), ("ablation", 4)):
        values = []
        for index in range(count):
            digest = hashlib.sha256(f"{DIRECTIVE}|{BASELINE}|downstream|{name}|{index}".encode()).digest()
            candidate = 10_000_000 + int.from_bytes(digest[:8], "big") % 80_000_000
            while candidate in used: candidate += 1
            used.add(candidate); values.append(candidate)
        seeds[name] = values
    manifest = {
        "schema": "AS009_DOWNSTREAM_SEED_MANIFEST_V1", "directive": DIRECTIVE, "baseline": BASELINE,
        "seed_status": "frozen_before_downstream_execution", "groups": seeds,
        "forbidden_explicit": [45878900, 22023239, 57531938, 16827204],
        "historical_registry": str(registry), "formal_manifest": str(formal),
    }
    flat = [x for values in seeds.values() for x in values]
    proof = {"schema": "AS009_DOWNSTREAM_SEED_DISJOINTNESS_PROOF_V1", "unique": len(flat) == len(set(flat)), "overlap_explicit": sorted(set(flat) & {45878900,22023239,57531938,16827204}), "status": "PASS" if len(flat) == len(set(flat)) and not (set(flat) & {45878900,22023239,57531938,16827204}) else "FAIL"}
    for name, value in (("AS009_DOWNSTREAM_SEED_MANIFEST.json", manifest), ("AS009_DOWNSTREAM_SEED_DISJOINTNESS_PROOF.json", proof)):
        path = EVIDENCE / name; path.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
        try: os.write(fd, payload); os.fsync(fd)
        finally: os.close(fd)
        os.replace(temp, path)
        dfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try: os.fsync(dfd)
        finally: os.close(dfd)
    print(json.dumps({"groups": seeds, "status": proof["status"]}, indent=2, sort_keys=True))


if __name__ == "__main__": main()
