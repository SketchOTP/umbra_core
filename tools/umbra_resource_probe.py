"""One bounded excluded-development P2 R0/S0 resource observation, not qualification."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import threading
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.as018.full_config import config, fingerprint
from experiments.d009.run_experiment import _habitat_state_for_scenario
from tools.as017_evidence import (StageJournal, iter_jsonl, publish_file_once,
                                 publish_json_once, reduce_certificate_linkage, stream_sha256)
from tools.as017_validate_linkage_v2 import validate_linkage_v2
from tools.umbra_baseline_audit import validate_database_copy, validate_trace_scope
from tools.umbra_life_probe import OWNERS
from tools.umbra_source_binding import capture_source_binding, verify_accepted_production
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism, load_organism, restore_habitat_engine_from_checkpoint
from umbra_core.util import current_rss_mib

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments/resource/RESOURCE_PROBE_20261001.json"


def cadence_due(tick, last_tick, now, last_time):
    return tick - last_tick >= 100 or now - last_time >= 5.0


def observed_file_size(path):
    # WAL/SHM can disappear between stat calls at a lawful connection close.
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def coverage_complete(compactions, eviction, restart, ticks, restart_tick):
    return compactions >= 5 and eviction and restart and ticks >= restart_tick + 100


def checkpoint_measurements(store):
    connection = store.conn
    epochs = [row[0] for row in connection.execute(
        "SELECT checkpoint_epoch FROM ledger_checkpoints ORDER BY checkpoint_epoch")]
    payload = connection.execute("SELECT COALESCE(SUM(length(habitat_binding_json) + "
        "COALESCE(length(habitat_checkpoint_json),0) + length(body_attachment_json)),0) "
        "FROM ledger_checkpoints").fetchone()[0]
    provenance = connection.execute("SELECT COALESCE(SUM(length(event_json)),0) FROM checkpoint_provenance").fetchone()[0]
    snapshots = connection.execute("SELECT COALESCE(SUM(length(state_json)),0) FROM snapshots WHERE protected=1").fetchone()[0]
    try:
        physical = dict(connection.execute("SELECT name, SUM(pgsize) FROM dbstat "
            "WHERE name IN ('ledger_checkpoints','checkpoint_provenance','snapshots') GROUP BY name"))
    except Exception as exc:
        physical = {"unavailable": type(exc).__name__}
    return {"epochs": epochs, "retained_checkpoint_count": len(epochs),
            "checkpoint_payload_bytes": payload, "provenance_payload_bytes": provenance,
            "protected_snapshot_payload_bytes": snapshots, "table_page_bytes": physical,
            "hot_tail_events": connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]}


class ResourceRecorder:
    """Wall sampler reads files/process only; SQLite reads stay on its owner thread.

    No RNG, preflight, policy, learning or authority writes. Checkpoint fields in
    wall samples carry an explicit owner-refresh time, never claimed current.
    """
    def __init__(self, root, database):
        self.root, self.database = root, database
        self.started = time.monotonic()
        self.tick = self.last_tick = 0
        self.last_time = self.started
        self.checkpoints = {"unavailable": "before_organism_creation"}
        self.refresh_time = self.started
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.error = None
        self.handle = (root / "resources.jsonl").open("x", encoding="utf-8")
        self.thread = threading.Thread(target=self._wall_loop, daemon=True)

    def _wall_loop(self):
        try:
            while not self.stop.wait(.05):
                with self.lock:
                    if time.monotonic() - self.last_time >= 5.0:
                        self._sample("wall_cadence")
        except Exception as exc:
            self.error = repr(exc)

    def _sample(self, reason):
        now = time.monotonic()
        sizes = {name: observed_file_size(path) for name, path in (
            ("database", self.database), ("wal", Path(str(self.database) + "-wal")),
            ("shm", Path(str(self.database) + "-shm")))}
        export = self.root / "export"
        exported = {p.name: p.stat().st_size for p in export.iterdir() if p.is_file()} if export.exists() else {}
        row = {"reason": reason, "tick": self.tick, "elapsed_seconds": now - self.started,
               "sample_gap_seconds": now - self.last_time, "rss_mib": current_rss_mib(),
               "process_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.,
               "storage_bytes": sizes, "exported_evidence_bytes": exported,
               "checkpoints": self.checkpoints,
               "checkpoint_measurement_age_seconds": now - self.refresh_time}
        self.handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        self.handle.flush()
        os.fsync(self.handle.fileno())
        self.last_time, self.last_tick = now, self.tick

    def sample(self, reason, organism=None):
        checkpoint = checkpoint_measurements(organism.store) if organism is not None else None
        with self.lock:
            if organism is not None:
                self.tick = organism.tick
                self.checkpoints = checkpoint
                self.refresh_time = time.monotonic()
            self._sample(reason)

    def after_tick(self, organism):
        with self.lock:
            self.tick = organism.tick
            due = cadence_due(self.tick, self.last_tick, time.monotonic(), self.last_time)
        if self.error:
            raise RuntimeError(f"measurement_write_failure:{self.error}")
        if due:
            self.sample("tick_or_wall_cadence", organism)

    def close(self):
        self.stop.set()
        if self.thread.ident is not None:
            self.thread.join(timeout=2)
        if self.thread.is_alive():
            raise RuntimeError("resource_recorder_did_not_stop")
        self.handle.close()
        if self.error:
            raise RuntimeError(f"measurement_write_failure:{self.error}")


def observe_maintenance(organism, recorder, lifecycle):
    # Wrap this Store instance only. Forward the identical arguments once;
    # compaction trigger, mutation, reclaim and retention stay runtime-owned.
    for name in ("compact_authoritative_prefix", "reclaim_physical_storage"):
        original = getattr(organism.store, name)
        def observed(*args, _original=original, _name=name, **kwargs):
            before = checkpoint_measurements(organism.store)["epochs"]
            recorder.sample(f"before_{_name}", organism)
            result = _original(*args, **kwargs)
            recorder.sample(f"after_{_name}", organism)
            if _name == "compact_authoritative_prefix" and result is not None:
                after = checkpoint_measurements(organism.store)["epochs"]
                lifecycle["natural_compactions"] += 1
                lifecycle["eviction_observed"] |= bool(set(before) - set(after))
            return result
        setattr(organism.store, name, observed)


def preflight(work, candidate, protocol_hash):
    protocol = json.loads(PROTOCOL.read_text())
    if stream_sha256(PROTOCOL) != protocol_hash:
        raise ValueError("protocol_hash_mismatch")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != candidate:
        raise ValueError("candidate_checkout_mismatch")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True):
        raise ValueError("execution_checkout_not_clean")
    verify_accepted_production(candidate)
    if protocol["classification"] != "EXCLUDED_DEVELOPMENT_ONLY" or protocol["hard_stop_ticks"] != 30000:
        raise ValueError("resource_protocol_mismatch")
    if work.exists():
        raise ValueError("measurement_work_path_not_fresh")
    filesystem = subprocess.check_output(
        ["findmnt", "-n", "-o", "FSTYPE", "--target", str(work.parent)], text=True).strip()
    if filesystem.startswith(("fuse", "nfs", "cifs", "smb")):
        raise ValueError("active_SQLite_requires_local_filesystem")
    database, trace = work / "life.sqlite", work / "decisions.jsonl"
    cfg = config(protocol["seed"], database, "R0")  # No ledger overrides.
    if cfg.ledger_hot_tail_event_max != 32768 or cfg.ledger_checkpoint_keep != 4:
        raise ValueError("canonical_compaction_configuration_mismatch")
    cfg.decision_trace_path, cfg.decision_trace_mode = str(trace), "compact_acceptance"
    return protocol, cfg


def run(work, candidate, protocol_hash):
    protocol, cfg = preflight(work, candidate, protocol_hash)
    work.mkdir(parents=True, exist_ok=False)
    database, trace = work / "life.sqlite", work / "decisions.jsonl"
    binding = capture_source_binding()
    publish_json_once(work / "source-binding.json", binding)
    publish_file_once(PROTOCOL, work / "protocol.json")
    journal = StageJournal(work / "stages.jsonl")
    recorder = ResourceRecorder(work, database)
    recorder.thread.start()
    report = {"schema": "UMBRA_RESOURCE_CHARACTERIZATION_V1", "classification": "DEVELOPMENT_ONLY",
              "candidate_commit": candidate, "protocol_sha256": protocol_hash, "seed": protocol["seed"],
              "configuration": fingerprint(cfg), "formal_seeds_consumed": 0,
              "formal_stages_executed": [], "failures": [], "ticks": 0,
              "machine": {"hostname": platform.node(), "platform": platform.platform(),
                          "meminfo": Path("/proc/meminfo").read_text(),
                          "cgroup_memory_max": Path("/sys/fs/cgroup/memory.max").read_text().strip()
                              if Path("/sys/fs/cgroup/memory.max").exists() else "unavailable",
                          "disk_available_bytes": os.statvfs(work).f_bavail * os.statvfs(work).f_frsize},
              "limitations": ["R0/S0 only; not every companion workload", "not 100k or S3 qualification",
                               "wall checkpoint metrics explicitly carry owner-refresh age",
                               "sampling scheduling gaps reported, not hidden", "no numerical storage ceiling established"]}
    lifecycle = {"natural_compactions": 0, "eviction_observed": False,
                 "restart_passed": False, "restart_tick": 30000}
    actions = Counter()
    organism = None
    try:
        journal.append("REGISTERED", case_id="resource-r0-s0", seed=protocol["seed"],
                       candidate=candidate, protocol_sha256=protocol_hash)
        journal.append("STARTED", case_id="resource-r0-s0", seed=protocol["seed"])
        organism = create_organism(cfg)
        identity = organism.identity.as_dict()
        report["birth_identity"] = identity
        for method in ("_ensure_development_intervention", "_ensure_memory_history",
                       "_ensure_social_history", "_ensure_individuality_history"):
            getattr(organism, method)()
        organism.embodiment.attach_habitat_engine(HabitatEngine(_habitat_state_for_scenario("S0")))
        observe_maintenance(organism, recorder, lifecycle)
        recorder.sample("birth", organism)
        while organism.tick < protocol["hard_stop_ticks"]:
            outcome = organism.tick_once()
            report["ticks"] = organism.tick
            actions[str(outcome.get("capability"))] += 1
            recorder.after_tick(organism)
            if outcome.get("no_safe_action") or organism.phys.critical_any():
                report["failures"].append("viability_boundary")
                report["failure_state"] = {"tick": organism.tick, "physiology": organism.phys.as_dict(), "outcome": outcome}
                break
            if current_rss_mib() > 180:
                report["failures"].append("existing_P2_RSS_limit_exceeded")
                break
            if lifecycle["natural_compactions"] >= 5 and not lifecycle["restart_passed"]:
                recorder.sample("before_restart", organism)
                organism.snapshot_if_due(force=True)  # Snapshot, never forced compaction.
                before = organism.authoritative_state()
                lifecycle["restart_tick"] = organism.tick
                organism.close()
                organism = None
                organism = load_organism(cfg)
                engine = restore_habitat_engine_from_checkpoint(organism)
                after = organism.authoritative_state()
                differences = [name for name in OWNERS if before[name] != after[name]]
                habitat = organism.embodiment.habitat_authority_binding
                lifecycle["restart_passed"] = not differences and habitat["state_hash"] == engine.snapshot_view().state_hash
                lifecycle["restart_owner_differences"] = differences
                lifecycle["restart_exclusions"] = ["session_id", "runtime_ready events", "wall-time anchor"]
                observe_maintenance(organism, recorder, lifecycle)
                recorder.sample("after_restart", organism)
                journal.append("RESTART_CHECKED", case_id="resource-r0-s0", **lifecycle)
                if not lifecycle["restart_passed"]:
                    report["failures"].append("restart_continuity_failure")
                    break
            if coverage_complete(lifecycle["natural_compactions"], lifecycle["eviction_observed"],
                                 lifecycle["restart_passed"], organism.tick, lifecycle["restart_tick"]):
                break
        recorder.sample("before_close", organism)
        organism.snapshot_if_due(force=True)
        organism.close()
        organism = None
        journal.append("EXECUTION_FINISHED", case_id="resource-r0-s0", ticks=report["ticks"], **lifecycle)
        recorder.sample("before_export")
        export = work / "export"
        hashes = {name: publish_file_once(source, export / name) for name, source in (
            ("life.sqlite", database), ("decisions.jsonl", trace), ("source-binding.json", work / "source-binding.json"),
            ("protocol.json", work / "protocol.json"))}
        sidecars = {}
        for suffix in ("-wal", "-shm", "-journal"):
            source = Path(str(database) + suffix)
            if source.exists():
                sidecars[suffix] = publish_file_once(source, export / source.name)
                hashes[source.name] = sidecars[suffix]
        summary = reduce_certificate_linkage(export / "decisions.jsonl", export / "linkage.jsonl")
        summary["candidate_commit"] = candidate
        hashes["linkage-summary.json"] = publish_json_once(export / "linkage-summary.json", summary)
        hashes["linkage.jsonl"] = stream_sha256(export / "linkage.jsonl")
        validation = {
            "database": validate_database_copy(export / "life.sqlite", hashes["life.sqlite"], report["ticks"],
                protocol["seed"], expected_identity=identity, sidecar_hashes=sidecars),
            "trace": validate_trace_scope(export / "decisions.jsonl", report["ticks"]),
            "linkage": validate_linkage_v2(export / "linkage-summary.json", export / "linkage.jsonl",
                export / "decisions.jsonl", candidate, expected_summary_sha256=hashes["linkage-summary.json"],
                expected_trace_sha256=hashes["decisions.jsonl"])}
        report.update(validation=validation, exported_hashes=hashes)
        if any(row["verdict"] != "PASS" for row in validation.values()):
            report["failures"].append("export_content_validation_failure")
        recorder.sample("after_export")
    except Exception as exc:
        report["failures"].append(f"infrastructure:{type(exc).__name__}:{exc}")
        journal.append("PROBE_INTERRUPTED", case_id="resource-r0-s0", ticks=report["ticks"], error=repr(exc))
    finally:
        if organism is not None:
            try:
                organism.close()
            except Exception as exc:
                report["failures"].append(f"organism_close_failed:{type(exc).__name__}:{exc}")
        try:
            recorder.close()
        except Exception as exc:
            report["failures"].append(f"measurement_finalization:{exc}")
        report.update(lifecycle=lifecycle, actions=dict(actions))
        if not coverage_complete(lifecycle["natural_compactions"], lifecycle["eviction_observed"],
                                 lifecycle["restart_passed"], report["ticks"], lifecycle["restart_tick"]):
            report["failures"].append("insufficient_lifecycle_coverage_within_hard_stop")
        after = capture_source_binding()
        if after["files"] != binding["files"]:
            report["failures"].append("source_changed_during_probe")
        report["verdict"] = "OBSERVATION_COMPLETE" if not report["failures"] else "INSUFFICIENT_OR_FAILED"
        journal.append("PROBE_FINISHED", case_id="resource-r0-s0", verdict=report["verdict"], ticks=report["ticks"])
        journal.close()
        report["journal_sha256"] = stream_sha256(work / "stages.jsonl")
        report["samples_sha256"] = stream_sha256(work / "resources.jsonl")
        rows = samples = 0
        max_rss = max_gap = 0.
        maxima = Counter()
        for row in iter_jsonl(work / "resources.jsonl"):
            rows += 1
            max_rss = max(max_rss, row["rss_mib"])
            max_gap = max(max_gap, row["sample_gap_seconds"])
            samples += int(row["sample_gap_seconds"] > 5.25)
            for key, value in row["storage_bytes"].items():
                maxima[key] = max(maxima[key], value)
        report["measurements"] = {"sample_count": rows, "max_rss_mib": max_rss,
            "max_gap_seconds": max_gap, "gaps_over_5_25_seconds": samples, "storage_peak_bytes": dict(maxima)}
        publish_json_once(work / "result.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        protocol, cfg = preflight(args.work.resolve(), args.candidate_commit, args.protocol_sha256)
        binding = capture_source_binding()
        print(json.dumps({"verdict": "PREFLIGHT_PASS", "organisms_created": 0,
                          "formal_seeds_consumed": 0, "protocol_sha256": args.protocol_sha256,
                          "configuration": fingerprint(cfg), "source_binding": binding}, sort_keys=True))
        return
    report = run(args.work.resolve(), args.candidate_commit, args.protocol_sha256)
    print(json.dumps({"verdict": report["verdict"], "ticks": report["ticks"],
                      "lifecycle": report["lifecycle"], "result": str(args.work / "result.json")}, sort_keys=True))
    raise SystemExit(0 if report["verdict"] == "OBSERVATION_COMPLETE" else 1)


if __name__ == "__main__":
    main()
