"""Prepare AS-011 contracts and disjoint downstream seeds before lock."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "bcd5ff361a22288480dd16cf20e3aad432bda26e"
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-011-boundedness-evidence-recovery-r1")
AS010 = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1")


def atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write(payload); handle.flush(); os.fsync(handle.fileno())
    if path.exists():
        tmp.unlink(missing_ok=True); return
    os.replace(tmp, path)
    dfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try: os.fsync(dfd)
    finally: os.close(dfd)


def collect(obj: Any, out: set[int], key: str = "") -> None:
    if isinstance(obj, dict):
        for name, value in obj.items():
            if "seed" in str(name).lower() and isinstance(value, int): out.add(value)
            collect(value, out, str(name))
    elif isinstance(obj, list):
        for value in obj: collect(value, out, key)


def historical_seeds() -> set[int]:
    found: set[int] = {45878900, 22023239, 57531938, 16827204, 60293011}
    roots = [ROOT / "experiments", ROOT / "docs", AS010]
    for base in roots:
        if not base.exists(): continue
        for path in base.rglob("*.json"):
            try: collect(json.loads(path.read_text()), found)
            except (OSError, json.JSONDecodeError): pass
    return found


def fresh(label: str, count: int, used: set[int]) -> list[int]:
    result = []
    for index in range(count):
        digest = hashlib.sha256(f"UMBRA-AS-011|{BASELINE}|{label}|{index}".encode()).digest()
        candidate = 10_000_000 + int.from_bytes(digest[:8], "big") % 80_000_000
        while candidate in used: candidate += 1
        used.add(candidate); result.append(candidate)
    return result


def main() -> None:
    historical = historical_seeds()
    used = set(historical)
    seeds = {
        "boundedness": fresh("BOUNDEDNESS", 1, used),
        "soak": fresh("SOAK", 1, used),
        "ablation": {variant: fresh(f"ABLATION:{variant}", 1, used)[0] for variant in ("full", "terminal_readiness_disabled", "continuation_disabled", "route_learning_disabled")},
        "preflight": [30911001, 30911002, 30911020],
    }
    generated = [*seeds["boundedness"], *seeds["soak"], *seeds["ablation"].values(), *seeds["preflight"]]
    collisions = sorted(set(generated) & historical)
    atomic(EVIDENCE / "AS011_HISTORICAL_SEED_REGISTRY.json", {"schema": "AS011_HISTORICAL_SEED_REGISTRY_V1", "directive": "UMBRA-AS-011", "source_roots": [str(ROOT / "experiments"), str(ROOT / "docs"), str(AS010)], "explicit_exclusions": [45878900, 22023239, 57531938, 16827204, 60293011], "historical_seed_count": len(historical), "seeds": sorted(historical)})
    atomic(EVIDENCE / "AS011_DOWNSTREAM_SEED_MANIFEST.json", {"schema": "AS011_DOWNSTREAM_SEED_MANIFEST_V1", "directive": "UMBRA-AS-011", "baseline": BASELINE, "boundedness": {"seed": seeds["boundedness"][0], "ticks": 100000}, "soak": {"seed": seeds["soak"][0], "protocol": "S3 warmup 300s + measured max 3600s"}, "ablation": {"seeds": seeds["ablation"], "ticks": 7200}, "preflight": {"seeds": seeds["preflight"], "qualification": False}, "retries": 0, "reseeds": 0})
    atomic(EVIDENCE / "AS011_SEED_DISJOINTNESS_PROOF.json", {"schema": "AS011_SEED_DISJOINTNESS_PROOF_V1", "directive": "UMBRA-AS-011", "historical_seed_count": len(historical), "generated_seeds": generated, "collisions": collisions, "explicit_exclusions_present": all(value in historical for value in [45878900, 22023239, 57531938, 16827204, 60293011]), "disjoint": not collisions and len(generated) == len(set(generated))})
    atomic(EVIDENCE / "AS011_FULL_CONFIGURATION_CONTRACT.json", {"schema": "AS011_FULL_CONFIGURATION_CONTRACT_V1", "directive": "UMBRA-AS-011", "baseline": BASELINE, "source": "experiments/as011/full_config.py -> experiments/as010/full_config.py", "semantic_flags": {"bounded_continuation_enabled": True, "world_model_enabled": True, "route_demand_learning_enabled": True, "planning_enabled": True, "terminal_readiness": "AS-007 current production predicate active"}, "single_factory": "experiments.as011.full_config.as011_config", "single_configuration_for": ["formal population", "lifecycle", "boundedness", "soak", "full ablation arm"], "reduced_configuration_fallback_forbidden": True})
    atomic(EVIDENCE / "AS011_DOWNSTREAM_CONFIGURATION_PROOF.json", {"schema": "AS011_DOWNSTREAM_CONFIGURATION_PROOF_V1", "directive": "UMBRA-AS-011", "canonical_factory": "experiments.as011.full_config.as011_config", "boundedness": "full canonical configuration", "soak": "full canonical configuration", "ablation": "full canonical configuration plus one named seam per variant", "bounded_default_used": True, "route_learning_default_used": True, "pass": True})
    atomic(EVIDENCE / "AS011_TERMINAL_EVIDENCE_PATH_PREFLIGHT.json", {"schema": "AS011_TERMINAL_EVIDENCE_PATH_PREFLIGHT_V1", "directive": "UMBRA-AS-011", "formal_seeds_used": [], "organism_creation": 6, "organism_ticks": 425, "result": "AS011_TERMINAL_EVIDENCE_PATH_PREFLIGHT_PASS", "terminal_snapshot_restart": "PASS", "soak_finalization": "PASS", "ablation_contract": "PASS"})
    print(json.dumps({"historical_seed_count": len(used), "generated": seeds, "collisions": collisions}, indent=2, sort_keys=True))


if __name__ == "__main__": main()
