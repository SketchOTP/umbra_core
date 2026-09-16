#!/usr/bin/env python3
"""Register fresh AS-018 Lock V2 seeds after a binary-safe local scan."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "experiments/as018/AS018_FORMAL_SEED_MANIFEST_V2.json"
DISJOINTNESS_PATH = ROOT / "experiments/as018/AS018_FORMAL_SEED_DISJOINTNESS_V2.json"
SEED_START = 99200001
REGIMES = ("R0", "R1", "R2", "R3")
SCENARIOS = {"R0": "S0", "R1": "S16", "R2": "S10", "R3": "S12"}
ORGANISM = "e8d048b510a477e677637b67bc0f56473cfe6540"
EXECUTION_SUBJECT = "HARNESS_COMMIT_FILLED_AT_REGISTRATION"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def scan_paths() -> list[Path]:
    roots = [ROOT / name for name in (".agent", "experiments", "tools", "docs/evidence", "evidence")]
    paths: list[Path] = []
    excluded = {MANIFEST_PATH.resolve(), DISJOINTNESS_PATH.resolve(), Path(__file__).resolve()}
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.resolve() in excluded:
                continue
            if ".git" in path.parts:
                continue
            paths.append(path)
    return sorted(set(paths))


def scan_seeds(path: Path, seeds: list[int]) -> list[int]:
    tokens = b"|".join(re.escape(str(seed).encode()) for seed in seeds)
    pattern = re.compile(rb"(?<![0-9])(?:" + tokens + rb")(?![0-9])")
    found: set[int] = set()
    overlap = 16
    tail = b""
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            data = tail + chunk
            for match in pattern.finditer(data):
                found.add(int(match.group()))
            tail = data[-overlap:]
    return sorted(found)


def build() -> tuple[dict, dict]:
    seeds = list(range(SEED_START, SEED_START + 32))
    paths = scan_paths()
    collisions = {
        str(path.relative_to(ROOT)): scan_seeds(path, seeds)
        for path in paths
    }
    collisions = {path: values for path, values in collisions.items() if values}
    manifest = {
        "schema": "AS018_FORMAL_SEED_MANIFEST_V2",
        "directive": "UMBRA-AS-018",
        "classification": "fresh_formal_population_lock_v2",
        "seed_status": "frozen_before_formal_execution",
        "superseded_manifest": "experiments/as018/AS018_FORMAL_SEED_MANIFEST_V1.json",
        "superseded_manifest_sha256": sha256(ROOT / "experiments/as018/AS018_FORMAL_SEED_MANIFEST_V1.json"),
        "organism_implementation_sha": ORGANISM,
        "formal_execution_subject": EXECUTION_SUBJECT,
        "source_baseline": ORGANISM,
        "formal_regimes": {
            regime: seeds[index * 8 : (index + 1) * 8]
            for index, regime in enumerate(REGIMES)
        },
        "regime_scenarios": SCENARIOS,
        "allocation": "mechanical sequential allocation from the first locally disjoint seed at 99200001",
        "organisms_per_regime": 8,
        "ticks_per_organism": 7200,
        "total_organisms": 32,
        "total_ticks": 230400,
        "retries": 0,
        "reseeds": 0,
        "substitutions": 0,
        "formal_seeds_consumed": 0,
    }
    disjointness = {
        "schema": "AS018_FORMAL_SEED_DISJOINTNESS_V2",
        "directive": "UMBRA-AS-018",
        "classification": "fresh_formal_population_disjointness_proof_lock_v2",
        "manifest": str(MANIFEST_PATH.relative_to(ROOT)),
        "candidate_range": [SEED_START, SEED_START + 31],
        "manifest_seed_count": len(seeds),
        "manifest_unique_seed_count": len(set(seeds)),
        "explicit_exclusions": [
            "all AS-018 Lock V1 formal seeds 99100001-99100032, including consumed 99100001",
            "AS-018 V1 protocol closeout and all AS-018 development manifests",
            "all AS-017 formal, development, diagnostic, reproduction, ablation, and performance seeds",
            "AS-015 and AS-016 population seeds and all discoverable historical formal seeds",
        ],
        "scan_scope": {
            "roots": [".agent", "experiments", "tools", "docs/evidence", "evidence"],
            "method": "binary-safe bounded exact-token scan of every accessible non-.git file, excluding this generator and the two outputs",
            "scanned_file_count": len(paths),
            "candidate_exact_collision_files": sorted(collisions),
            "candidate_exact_collision_count": sum(len(values) for values in collisions.values()),
            "candidate_tokens_scanned": len(seeds),
        },
        "collisions": collisions,
        "formal_seed_consumption": 0,
        "retries": 0,
        "reseeds": 0,
        "substitutions": 0,
        "result": "PASS" if not collisions else "FAIL",
        "qualification_status": "registered_before_observation" if not collisions else "not_registered",
        "limitation": "Only the local repository and accessible retained evidence were scanned; external host-only seed registries remain unavailable and universal disjointness is not claimed.",
    }
    if collisions:
        raise RuntimeError("AS018_FORMAL_V2_SEED_COLLISION")
    manifest["formal_execution_subject"] = sys.argv[1] if len(sys.argv) > 1 else EXECUTION_SUBJECT
    return manifest, disjointness


def write_once(path: Path, value: dict) -> None:
    encoded = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    if path.exists() and path.read_bytes() != encoded:
        raise RuntimeError(f"AS018_FORMAL_V2_CREATE_ONCE_MISMATCH:{path.name}")
    if not path.exists():
        path.write_bytes(encoded)
    if path.read_bytes() != encoded:
        raise RuntimeError(f"AS018_FORMAL_V2_READBACK_INVALID:{path.name}")


if __name__ == "__main__":
    manifest, disjointness = build()
    write_once(MANIFEST_PATH, manifest)
    disjointness["manifest_sha256"] = sha256(MANIFEST_PATH)
    write_once(DISJOINTNESS_PATH, disjointness)
    print(json.dumps({
        "manifest": str(MANIFEST_PATH),
        "manifest_sha256": sha256(MANIFEST_PATH),
        "disjointness": str(DISJOINTNESS_PATH),
        "disjointness_sha256": sha256(DISJOINTNESS_PATH),
        "candidate_range": [SEED_START, SEED_START + 31],
        "scanned_file_count": disjointness["scan_scope"]["scanned_file_count"],
        "collisions": disjointness["collisions"],
        "formal_seeds_consumed": 0,
        "status": disjointness["result"],
    }, sort_keys=True))
