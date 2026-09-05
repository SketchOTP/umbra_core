"""Non-formal AS-011 downstream intervention and finalization preflight."""
from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path

from experiments.as011.downstream import _disable_terminal_readiness, initialize, restore_with_habitat
from experiments.as011.full_config import fingerprint, as011_config


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="as011-preflight-"))
    rows = []
    try:
        db = root / "terminal.sqlite"
        org, engine = initialize(30911001, db)
        for _ in range(420):
            org.tick_once()
        before = org.authoritative_state()
        habitat = copy.deepcopy(engine.state)
        org.snapshot_if_due(force=True)
        org.store.validate_chain()
        org.close()
        restored, restored_engine = restore_with_habitat(30911001, db, habitat)
        after = restored.authoritative_state()
        restored.tick_once()
        restored.snapshot_if_due(force=True)
        restored.store.validate_chain()
        rows.append({"path": "terminal_snapshot_restart", "ticks_before": before["tick"], "ticks_after": after["tick"], "restart_binding": restored.embodiment.habitat_authority_binding, "pass": before["identity"] == after["identity"] and before["tick"] == after["tick"] and restored_engine.snapshot_view().habitat_id == "habitat:sample"})
        restored.close()

        soak_db = root / "soak.sqlite"
        soak_org, soak_engine = initialize(30911002, soak_db)
        soak_org.run_realtime(2.0)
        soak_org.store.validate_chain()
        rows.append({"path": "soak_terminal_snapshot", "ticks": soak_org.tick, "pass": soak_org.tick > 0 and soak_org.embodiment._habitat_engine is soak_engine})
        soak_org.close()

        cfg_rows = []
        for index, variant in enumerate(("full", "terminal_readiness_disabled", "continuation_disabled", "route_learning_disabled")):
            bounded = variant != "continuation_disabled"; route = variant != "route_learning_disabled"
            config = as011_config(30911010 + index, root / f"{variant}-config.sqlite", "R0", bounded=bounded, route_learning=route)
            cfg_rows.append({"variant": variant, "fingerprint": fingerprint(config), "named_config_differences": {"bounded_continuation_enabled": bounded, "route_demand_learning_enabled": route}, "terminal_readiness_seam": variant == "terminal_readiness_disabled"})
        org, _ = initialize(30911020, root / "readiness.sqlite")
        original = org._candidate_executability
        seam = _disable_terminal_readiness(org)
        readiness_distinct = org._candidate_executability is not original and seam["count"] == 0
        org.close()
        full_fp = copy.deepcopy(cfg_rows[0]["fingerprint"])
        readiness_fp = copy.deepcopy(cfg_rows[1]["fingerprint"])
        full_fp["seed"] = readiness_fp["seed"] = "IGNORED_RUN_SEED"
        rows.append({"path": "ablation_contract", "configurations": cfg_rows, "terminal_readiness_seam_distinct": readiness_distinct, "pass": readiness_distinct and full_fp == readiness_fp})
        result = {"schema": "AS011_TERMINAL_EVIDENCE_PATH_PREFLIGHT_V1", "directive": "UMBRA-AS-011", "formal_seeds_used": [], "rows": rows, "organism_creation": 6, "organism_ticks": 421 + rows[1]["ticks"], "status": "PASS" if all(row["pass"] for row in rows) else "FAIL"}
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            tmp = args.output.with_name(f".{args.output.name}.{os.getpid()}.tmp")
            with tmp.open("xb") as handle:
                handle.write(rendered.encode()); handle.flush(); os.fsync(handle.fileno())
            if args.output.exists():
                tmp.unlink(missing_ok=True)
            else:
                os.replace(tmp, args.output)
        print(rendered, end="")
    finally:
        for path in sorted(root.glob("*")):
            for sidecar in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
                sidecar.unlink(missing_ok=True)
        root.rmdir()


if __name__ == "__main__":
    main()
