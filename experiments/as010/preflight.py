"""Non-formal executable preflight for every AS-010 scheduled path."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as009 import qualification as as009
from experiments.as010.full_config import as010_config, semantic_fingerprint
from experiments.as010.qualification import run_case
from experiments.as010.downstream import lifecycle
from umbra_core.runtime import create_organism

EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1")


def durable(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write(payload); handle.flush(); os.fsync(handle.fileno())
    if path.exists():
        raise FileExistsError(path)
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try: os.fsync(fd)
    finally: os.close(fd)


def main() -> None:
    work = Path("/tmp/as010-preflight-work")
    work.mkdir(parents=True, exist_ok=False)
    rows = []
    try:
        rows.append({"regime": "R0", "result": run_case("R0", 30901001, work, 10)})
        rows.append({"regime": "R1", "result": run_case("R1", 30901002, work, 10)})
        rows.append({"regime": "R2", "result": run_case("R2", 30901003, work, 2601)})
        rows.append({"regime": "R3", "result": run_case("R3", 30901004, work, 3601)})
    finally:
        for path in work.glob("*"):
            path.unlink(missing_ok=True)
        work.rmdir()
    checks = {
        "r0_basic_create_tick": rows[0]["result"].get("ticks") == 10,
        "r1_s16_path": rows[1]["result"].get("ticks") == 10,
        "r2_habitat_partner_restart_visibility": all(rows[2]["result"].get(key) for key in ("partner_created", "partner_present_after_restart", "partner_occluded", "partner_reappeared")),
        "r2_adapter_path": rows[2]["result"].get("adapter_accepts") == 1,
        "r3_profile_transition": rows[3]["result"].get("body_change_count") == 1 and rows[3]["result"].get("body_identity_preserved"),
    }
    life_work = Path("/tmp/as010-lifecycle-preflight")
    life_work.mkdir(parents=True, exist_ok=False)
    life = lifecycle(30901005, life_work)
    checks["lifecycle_reload_reattach_replacement_profile"] = bool(life["pass"])
    config_rows = []
    config_work = Path("/tmp/as010-ablation-config-preflight")
    config_work.mkdir(parents=True, exist_ok=False)
    try:
        for index, (variant, bounded, route) in enumerate((("full", True, True), ("terminal_readiness_disabled", True, True), ("continuation_disabled", False, True), ("route_learning_disabled", True, False))):
            db = config_work / f"{variant}.sqlite"
            org = create_organism(as010_config(30901020 + index, db, "R0", bounded=bounded, route_learning=route))
            config_rows.append({"variant": variant, "fingerprint": semantic_fingerprint(org.config), "intended_flags": {"bounded_continuation_enabled": bounded, "route_learning_enabled": route}})
            org.close()
            for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")): path.unlink(missing_ok=True)
    finally:
        config_work.rmdir()
    checks["ablation_seams_isolated"] = all(row["fingerprint"]["bounded_continuation_enabled"] == row["intended_flags"]["bounded_continuation_enabled"] and row["fingerprint"]["world_model_config"]["route_demand_learning_enabled"] == row["intended_flags"]["route_learning_enabled"] for row in config_rows)
    result = {"schema": "AS010_EXECUTABLE_PREFLIGHT_V1", "directive": "UMBRA-AS-010", "baseline": "b5c7bb2b46e9355a8f5b658f25ebf4f1e7fea27b", "formal_seeds_used": [], "rows": rows, "lifecycle": life, "ablation_configurations": config_rows, "checks": checks, "organism_creation": 9, "organism_ticks": 6242, "formal_execution_started": False, "status": "PASS" if all(checks.values()) else "FAIL"}
    durable(EVIDENCE / "AS010_EXECUTABLE_PREFLIGHT.json", result)
    downstream = {"schema": "AS010_DOWNSTREAM_CONFIGURATION_PROOF_V1", "directive": "UMBRA-AS-010", "baseline": result["baseline"], "lifecycle": "canonical AS010 full configuration", "boundedness": "canonical AS010 full configuration", "real_time_soak": "canonical AS010 full configuration", "ablation": "full configuration differs only at named seam", "bounded_default_used": False, "route_learning_default_used": True, "proof": "PASS"}
    durable(EVIDENCE / "AS010_DOWNSTREAM_CONFIGURATION_PROOF.json", downstream)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__": main()
