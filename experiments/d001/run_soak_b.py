#!/usr/bin/env python3
"""Start Run B soak from the current HEAD (retention v1). No code changes after start."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from umbra_core.events import AUTHORITATIVE_EVENT_TYPES
from umbra_core.runtime import OrganismConfig, create_organism

EVIDENCE = Path("docs/evidence/d001")
DB = Path("/home/sketch/Projects/UMBRA-CORE/.soak/run_b.sqlite")
JSONL = EVIDENCE / "soak-run-b.jsonl"
SUMMARY = EVIDENCE / "soak-run-b-summary.json"
PROVENANCE = EVIDENCE / "soak-run-b-provenance.json"


def rss() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if DB.exists() or Path(str(DB) + "-wal").exists():
        raise SystemExit(f"refusing to overwrite existing Run B DB: {DB}")
    DB.parent.mkdir(parents=True, exist_ok=True)

    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
    if dirty:
        raise SystemExit(f"worktree not clean; commit before Run B:\n{dirty}")

    config = {
        "db_path": str(DB),
        "seed": 99,
        "hz": 2.0,
        "snapshot_every": 7200,
        "hours": 6.0,
        "retention_policy_version": "v1_authoritative_every_tick",
    }
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    provenance = {
        "run_id": "B",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "configuration": config,
        "configuration_hash_sha256": config_hash,
        "runtime_source_sha256": {
            "umbra_core/runtime.py": sha256_file(Path("umbra_core/runtime.py")),
            "umbra_core/events.py": sha256_file(Path("umbra_core/events.py")),
            "umbra_core/persistence.py": sha256_file(Path("umbra_core/persistence.py")),
        },
        "retention_policy_version": "v1_authoritative_every_tick",
        "authoritative_event_types": sorted(AUTHORITATIVE_EVENT_TYPES),
        "pid": os.getpid(),
        "database_path": str(DB),
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    PROVENANCE.write_text(json.dumps(provenance, indent=2))

    hours = 6.0
    period = 0.5
    cfg = OrganismConfig(
        db_path=str(DB),
        seed=99,
        hz=2.0,
        snapshot_every=7200,
    )
    org = create_organism(cfg)
    end = time.monotonic() + hours * 3600
    t0 = time.monotonic()
    c0 = time.process_time()
    r0 = rss()
    n = 0
    last_log = t0
    with JSONL.open("w") as f:
        while time.monotonic() < end:
            t_tick = time.monotonic()
            org.tick_once()
            n += 1
            sleep = period - (time.monotonic() - t_tick)
            if sleep > 0:
                time.sleep(sleep)
            now = time.monotonic()
            if now - last_log >= 300 or n % 3600 == 0:
                row = {
                    "elapsed_sec": now - t0,
                    "ticks": n,
                    "rss_mib": rss(),
                    "cpu_sec": time.process_time() - c0,
                    "H": org.phys.as_dict(),
                }
                f.write(json.dumps(row) + "\n")
                f.flush()
                last_log = now
    org.snapshot_if_due(force=True)
    summary = {
        "hours": hours,
        "ticks": n,
        "elapsed_sec": time.monotonic() - t0,
        "cpu_sec": time.process_time() - c0,
        "rss_start_mib": r0,
        "rss_end_mib": rss(),
        "cpu_fraction": (time.process_time() - c0) / max(1e-9, time.monotonic() - t0),
        "agent_id": org.identity.agent_id,
        "commit": commit,
        "retention_policy_version": "v1_authoritative_every_tick",
        "configuration_hash_sha256": config_hash,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2))
    org.close()
    print("SOAK_B_DONE", summary)


if __name__ == "__main__":
    main()
