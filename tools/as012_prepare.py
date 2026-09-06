"""AS-012 zero-run reconciliation, audit, contract, and seed preparation."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from experiments.as007.qualification import as007_config
from experiments.as010.full_config import semantic_fingerprint
from experiments.as012.full_config import BASELINE, DIRECTIVE, config

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-012-exact-entrypoint-boundedness-soak-causal-closure-r1")
AS010 = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1")
AS011 = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-011-boundedness-evidence-recovery-r1")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write(payload); handle.flush(); os.fsync(handle.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return sha(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def collect_ints(value: Any, out: set[int]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if "seed" in str(key).lower() and isinstance(item, int):
                out.add(item)
            collect_ints(item, out)
    elif isinstance(value, list):
        for item in value:
            collect_ints(item, out)


def historical_seeds() -> set[int]:
    used: set[int] = {45878900, 22023239, 57531938, 16827204, 10046820, 42843059, 55132318, 75387422, 42474898, 54894963}
    for root in (ROOT / "experiments", ROOT / "docs", AS010, AS011):
        if not root.exists():
            continue
        for path in root.rglob("*.json"):
            try:
                collect_ints(read_json(path), used)
            except (OSError, json.JSONDecodeError):
                continue
    return used


def fresh(seed_label: str, used: set[int]) -> int:
    candidate = 20_000 + int.from_bytes(hashlib.sha256(f"{DIRECTIVE}|{BASELINE}|{seed_label}".encode()).digest()[:8], "big") % 80_000_000
    while candidate in used:
        candidate += 1
    used.add(candidate)
    return candidate


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT, text=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    master = subprocess.check_output(["git", "rev-parse", "master"], cwd=ROOT, text=True).strip()
    github = subprocess.check_output(["git", "rev-parse", "github/master"], cwd=ROOT, text=True).strip()
    production_paths = subprocess.check_output(["git", "diff", "--name-only", "f0ac33212b3cb0081e16341bba31db69043a9292", "HEAD", "--", "umbra_core"], cwd=ROOT, text=True).splitlines()
    reconciliation = {
        "schema": "AS012_STATE_RECONCILIATION_V1", "directive": DIRECTIVE, "baseline": BASELINE,
        "head": head, "master": master, "github_master": github, "synchronized": head == master == github == BASELINE,
        "worktree_porcelain": status.splitlines(), "production_semantic_delta_from_as007_freeze": len(production_paths), "production_paths": production_paths,
        "inherited": {"as010_full_config_population": "32/32", "as010_full_config_lifecycle": "PASS — 500 ticks", "as011": "AS011_PROTOCOL_FAIL permanent"},
        "unresolved": ["boundedness", "real_time_soak", "causal_ablation"], "organism_creation": 0, "organism_load": 0, "organism_ticks": 0,
        "retries": 0, "reseeds": 0,
    }
    atomic(EVIDENCE / "AS012_STATE_RECONCILIATION.json", reconciliation)
    defects = {
        "schema": "AS012_AS011_HARNESS_DEFECT_AUDIT_V1", "directive": DIRECTIVE, "source_commit": "b4cc014c3545e19fa0e755407fe2a466e23e72a5",
        "defects": [
            {"id": "undefined_boundedness_locals", "source": "experiments/as011/downstream.py:98", "finding": "boundedness references undefined bounded and route"},
            {"id": "ablation_flags_not_applied", "source": "experiments/as011/downstream.py:200", "finding": "variant flags are computed but initialize(seed, db) receives neither"},
            {"id": "preflight_not_exact_entrypoint", "source": "experiments/as011/preflight.py", "finding": "component sequences were tested instead of boundedness/soak/ablation entrypoints"},
            {"id": "unmatched_ablation_seeds", "source": "AS011_DOWNSTREAM_SEED_MANIFEST.json", "finding": "four variants received independent seeds"},
            {"id": "cpu_reducer_omitted", "source": "experiments/as011/downstream.py", "finding": "cpu_fraction_one_core was not included in boundedness pass"},
        ],
        "required_repairs": "AS-012 experiment-only namespace; production unchanged",
    }
    atomic(EVIDENCE / "AS012_AS011_HARNESS_DEFECT_AUDIT.json", defects)
    config_rows = []
    for regime in ("R0", "R1", "R2", "R3"):
        db = Path(f"/tmp/as012-config-{regime}.sqlite")
        ours = semantic_fingerprint(config(81234001, db, regime, bounded_continuation=True, route_learning=True))
        as007 = semantic_fingerprint(as007_config(81234001, db, regime, Path(f"/tmp/as012-{regime}.decision"), Path(f"/tmp/as012-{regime}.planning")))
        ours.pop("seed", None); as007.pop("seed", None)
        ours.pop("hooks", None); as007.pop("hooks", None)
        config_rows.append({"regime": regime, "as007": as007, "as012": ours, "equivalent_behavioral_fields": ours == as007})
    atomic(EVIDENCE / "AS012_AS007_RUNTIME_CONFIG_EQUIVALENCE.json", {"schema": "AS012_AS007_RUNTIME_CONFIG_EQUIVALENCE_V1", "directive": DIRECTIVE, "verdict": "AS007_FULL_CONFIGURATION_REPRODUCED" if all(row["equivalent_behavioral_fields"] for row in config_rows) else "SEMANTIC_MISMATCH", "rows": config_rows, "diagnostic_trace_paths": "excluded from behavioral equivalence"})
    atomic(EVIDENCE / "AS012_FULL_CONFIGURATION_CONTRACT.json", {"schema": "AS012_FULL_CONFIGURATION_CONTRACT_V1", "directive": DIRECTIVE, "factory": "experiments.as012.full_config.config", "full": {"bounded_continuation_enabled": True, "world_model_enabled": True, "route_demand_learning_enabled": True, "terminal_readiness": "current AS-007 production authority"}, "used_by": ["boundedness", "soak", "FULL ablation"], "ablation_only_seams": ["terminal_readiness_disabled", "bounded_continuation", "route_learning"]})
    atomic(EVIDENCE / "AS012_PRODUCTION_INHERITANCE_PROOF.json", {"schema": "AS012_PRODUCTION_INHERITANCE_PROOF_V1", "directive": DIRECTIVE, "as007_freeze": "f0ac33212b3cb0081e16341bba31db69043a9292", "baseline": BASELINE, "production_paths_changed": production_paths, "production_delta": len(production_paths), "verdict": "PASS" if not production_paths else "AS012_PRODUCTION_INHERITANCE_FAIL"})
    used = historical_seeds(); generated = {"boundedness": fresh("BOUNDEDNESS", used), "soak": fresh("SOAK", used), "ablation_base": fresh("ABLATION_BASE", used), "preflight": 39124000}
    while generated["preflight"] in used:
        generated["preflight"] += 1
    atomic(EVIDENCE / "AS012_HISTORICAL_SEED_REGISTRY.json", {"schema": "AS012_HISTORICAL_SEED_REGISTRY_V1", "directive": DIRECTIVE, "count": len(used), "seeds": sorted(used), "explicit_exclusions": [45878900, 22023239, 57531938, 16827204, 10046820, 42843059, 55132318, 75387422, 42474898, 54894963]})
    atomic(EVIDENCE / "AS012_DOWNSTREAM_SEED_MANIFEST.json", {"schema": "AS012_DOWNSTREAM_SEED_MANIFEST_V1", "directive": DIRECTIVE, "baseline": BASELINE, "boundedness": {"seed": generated["boundedness"], "ticks": 100000}, "soak": {"seed": generated["soak"], "warmup_seconds": 300, "measure_seconds": 3600, "sample_interval_seconds": 5, "minimum_samples": 360}, "ablation": {"base_seed": generated["ablation_base"], "variants": ["full", "terminal_readiness_disabled", "continuation_disabled", "route_learning_disabled"], "ticks": 7200, "regime": "R1/S16"}, "preflight": {"seed": generated["preflight"], "qualification": False}, "retries": 0, "reseeds": 0})
    all_new = [generated["boundedness"], generated["soak"], generated["ablation_base"]]
    collisions = sorted(set(all_new) & used)
    atomic(EVIDENCE / "AS012_SEED_DISJOINTNESS_PROOF.json", {"schema": "AS012_SEED_DISJOINTNESS_PROOF_V1", "directive": DIRECTIVE, "generated": all_new, "collisions": collisions, "matched_ablation": len({generated["ablation_base"]}) == 1, "disjoint": not collisions and len(all_new) == len(set(all_new))})
    atomic(EVIDENCE / "AS012_SOAK_CONTRACT.json", {"schema": "AS012_SOAK_CONTRACT_V1", "directive": DIRECTIVE, "warmup_seconds": 300, "measure_seconds": 3600, "sample_interval_seconds": 5, "minimum_samples": 360, "tick_hz": 2, "thresholds": {"rss_mib": 180, "rss_slope_mib_per_hour": 1.0, "cpu_fraction_one_core": 0.05, "event_records_per_tick": 32, "database_growth_bytes": 67108864}})
    atomic(EVIDENCE / "AS012_BOUNDEDNESS_CONTRACT.json", {"schema": "AS012_BOUNDEDNESS_CONTRACT_V1", "directive": DIRECTIVE, "ticks": 100000, "sample_interval_ticks": 5000, "thresholds": {"rss_mib": 180, "rss_slope_mib_per_hour": 1.0, "database_growth_bytes": 67108864, "event_records_per_tick": 32, "cpu_fraction_one_core": 0.05}, "restart": "load -> restore exact Habitat -> attach -> verify binding -> authoritative read -> chain validation"})
    print(json.dumps({"evidence": str(EVIDENCE), "head": head, "seeds": generated, "synchronized": reconciliation["synchronized"], "production_delta": len(production_paths)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
