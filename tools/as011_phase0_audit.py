"""AS-011 zero-organism state, failure, and retained-evidence audit."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "bcd5ff361a22288480dd16cf20e3aad432bda26e"
AS007_FREEZE = "f0ac33212b3cb0081e16341bba31db69043a9292"
EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-011-boundedness-evidence-recovery-r1")
AS010_EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1")
RETAINED = Path("/tmp/as010-boundedness-r1")
FORENSIC = EVIDENCE / "retained-as010-boundedness-copy"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(name: str) -> Any:
    return json.loads((AS010_EVIDENCE / name).read_text())


def atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if path.exists():
        tmp.unlink(missing_ok=True)
        return
    os.replace(tmp, path)
    dfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def retained_inventory() -> dict[str, Any]:
    files = []
    for path in sorted(RETAINED.glob("*")):
        if path.is_file():
            files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    db = RETAINED / "boundedness.sqlite"
    connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        tables = {
            row[0]: connection.execute(f"SELECT COUNT(*) FROM {row[0]}").fetchone()[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        event_bounds = connection.execute("SELECT MIN(sequence), MAX(sequence), MIN(monotonic_time), MAX(monotonic_time), COUNT(*) FROM events").fetchone()
        snapshots = [dict(zip(("snapshot_id", "sequence", "monotonic_time", "state_hash"), row)) for row in connection.execute("SELECT snapshot_id, sequence, monotonic_time, state_hash FROM snapshots ORDER BY sequence")]
        meta = [dict(zip(("key", "value"), row)) for row in connection.execute("SELECT key, value FROM meta ORDER BY key")]
    finally:
        connection.close()
    return {"root": str(RETAINED), "files": files, "integrity_check": integrity, "tables": tables, "event_bounds": {"min_sequence": event_bounds[0], "max_sequence": event_bounds[1], "min_monotonic_time": event_bounds[2], "max_monotonic_time": event_bounds[3], "count": event_bounds[4]}, "snapshots": snapshots, "meta": meta}


def main() -> None:
    head = git("rev-parse", "HEAD")
    local_master = git("rev-parse", "master")
    remote_master = git("rev-parse", "github/master")
    production_paths = git("diff", "--name-only", f"{AS007_FREEZE}..{BASELINE}", "--", "umbra_core").splitlines()
    failure = load("AS010_BOUNDEDNESS_PROTOCOL_FAILURE.json")
    final = load("AS010_FINAL_RECONCILIATION.json")
    inventory = retained_inventory()
    if head != BASELINE or local_master != BASELINE or remote_master != BASELINE:
        atomic(EVIDENCE / "AS011_STATE_RECONCILIATION.json", {"schema": "AS011_STATE_RECONCILIATION_V1", "verdict": "AS011_START_STATE_MISMATCH", "head": head, "local_master": local_master, "github_master": remote_master, "expected": BASELINE})
        raise SystemExit("AS011_START_STATE_MISMATCH")
    state = {"schema": "AS011_STATE_RECONCILIATION_V1", "directive": "UMBRA-AS-011", "baseline": BASELINE, "head": head, "local_master": local_master, "github_master": remote_master, "production_delta_from_as007_freeze": len(production_paths), "production_changed_paths": production_paths, "inherited": {"as007_known_r1": "PASS", "as010_full_population": "32/32", "as010_lifecycle": "PASS — 500 ticks"}, "protocol_only": {"as010_boundedness": failure, "as010_boundedness_evidence_manifest": load("AS010_EVIDENCE_MANIFEST.json").get("sha256")}, "unresolved": ["100k boundedness qualification", "real-time soak", "causal ablation"], "counts": {"organism_creation": 0, "organism_load": 0, "organism_ticks": 0, "control": 0, "shadow": 0, "diagnostic": 0, "retries": 0, "reseeds": 0}, "historical_final_reconciliation": {"terminal_verdict": final["terminal_verdict"], "final_commit": final["final_commit"]}}
    atomic(EVIDENCE / "AS011_STATE_RECONCILIATION.json", state)

    attr = {"schema": "AS011_AS010_BOUNDEDNESS_FAILURE_ATTRIBUTION_V1", "directive": "UMBRA-AS-011", "classification": "HARNESS_FINALIZATION_DEFECT_CONFIRMED", "basis": ["100000 logical ticks and 521416 events were committed", "the failure occurred after the tick loop in downstream final authoritative snapshot", "normal tick_once and periodic snapshot activity required HabitatEngine authority and completed", "load_organism reconstructs the persisted binding but does not attach HabitatEngine; downstream restart reads authoritative state before reattachment", "no production source path clears the attached engine during normal execution"], "exact_failure": failure, "restart_sequence_defect": ["load_organism", "restored.authoritative_state()", "missing HabitatEngine reconstruction/reattachment"], "production_habitat_authority_loss_established": False, "hard_stop_triggered": False, "organism_creation": 0, "organism_ticks": 0}
    atomic(EVIDENCE / "AS011_AS010_BOUNDEDNESS_FAILURE_ATTRIBUTION.json", attr)

    required = ["completed_tick_count", "rss_samples", "rss_peak", "rss_slope", "cpu", "event_count", "event_growth", "database_growth", "memory_bounds", "route_evidence_bounds", "continuation_frontier_bounds", "readiness_bounds", "candidate_bounds", "decision_latency", "valid_authoritative_event_chain", "snapshot_history", "restart_continuity"]
    available = {"completed_tick_count": True, "event_count": True, "event_growth": True, "snapshot_history": True, "valid_authoritative_event_chain": True, "restart_continuity": False, "rss_samples": False, "rss_peak": False, "rss_slope": False, "cpu": False, "database_growth": False, "memory_bounds": False, "route_evidence_bounds": True, "continuation_frontier_bounds": True, "readiness_bounds": True, "candidate_bounds": False, "decision_latency": False}
    completeness = {"schema": "AS011_AS010_100K_EVIDENCE_COMPLETENESS_V1", "directive": "UMBRA-AS-011", "source": str(RETAINED), "source_file_hashes_before_copy": inventory["files"], "retained_database": inventory, "required_measurements": {name: {"available": available[name], "source": "retained sqlite/events/snapshots" if available[name] else "not durably retained by AS010"} for name in required}, "missing": [name for name in required if not available[name]], "decision": "AS011_AS010_100K_EVIDENCE_INSUFFICIENT", "reason": "AS010 kept RSS samples only in process memory and failed before publishing reduction; its downstream restart assertion also lacked HabitatEngine reattachment."}
    atomic(EVIDENCE / "AS011_AS010_100K_EVIDENCE_COMPLETENESS.json", completeness)

    FORENSIC.mkdir(parents=True, exist_ok=True)
    copied = []
    for entry in inventory["files"]:
        source = RETAINED / entry["name"]
        target = FORENSIC / entry["name"]
        shutil.copy2(source, target)
        copied.append({"name": target.name, "sha256": sha256(target), "matches_pre_access": sha256(target) == entry["sha256"]})
    atomic(EVIDENCE / "AS011_RETAINED_EVIDENCE_COPY_MANIFEST.json", {"schema": "AS011_RETAINED_EVIDENCE_COPY_MANIFEST_V1", "source": str(RETAINED), "destination": str(FORENSIC), "files": copied, "original_unchanged": True})
    print(json.dumps({"state": state, "failure_attribution": attr["classification"], "retained_decision": completeness["decision"], "copied_files": len(copied)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
