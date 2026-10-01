"""Retained, bounded DEVELOPMENT continuity probe on unchanged AS-018 semantics.

Not a formal lifecycle, 100k, S3, causal-necessity or companion qualification.
The caller's new local directory is retained, including failed/interrupted work.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.as018.full_config import config, fingerprint
from experiments.d009.run_experiment import _habitat_state_for_scenario
from tools.as017_evidence import StageJournal, iter_jsonl, publish_json_once, stream_sha256
from tools.umbra_baseline_audit import validate_database_copy, validate_trace_scope
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.physiology import BOUNDS
from umbra_core.runtime import create_organism, load_organism, restore_habitat_engine_from_checkpoint
from umbra_core.util import current_rss_mib

ROOT = Path(__file__).resolve().parents[1]
SUBJECT = "e8d048b510a477e677637b67bc0f56473cfe6540"
OWNERS = ("identity", "physiology", "memory", "social", "self_model", "world_model",
          "individuality", "development", "rng_state", "tick")


def run(root: Path, *, seed: int = 97093002, segments: int = 4, segment_ticks: int = 256) -> dict[str, Any]:
    # This narrow probe is not a generic campaign launcher. Its explicit
    # diagnostic fixtures cannot be replaced with a historical formal seed.
    if seed not in {97093002, 97093003, 97093004, 88009998}:
        raise ValueError("formal_seed_prohibited_in_development_probe")
    if not 1 <= segments <= 4 or not 1 <= segment_ticks <= 256:
        raise ValueError("bounded_development_horizon_exceeded")
    # No source mutation or imported legacy configuration rebinding.
    semantic_tree = subprocess.check_output(["git", "rev-parse", f"{SUBJECT}:umbra_core"], cwd=ROOT, text=True).strip()
    actual_tree = subprocess.check_output(["git", "rev-parse", "HEAD:umbra_core"], cwd=ROOT, text=True).strip()
    if actual_tree != semantic_tree or subprocess.check_output(
        ["git", "diff", "HEAD", "--", "umbra_core"], cwd=ROOT, text=True
    ):
        raise ValueError("accepted_production_subtree_mismatch")
    root.mkdir(parents=True, exist_ok=False)
    database, trace = root / "life.sqlite", root / "decisions.jsonl"
    cfg = config(seed, database, "R0", ledger_overrides={"ledger_hot_tail_event_max": 128})
    cfg.decision_trace_path = str(trace)
    cfg.decision_trace_mode = "compact_acceptance"
    journal = StageJournal(root / "stages.jsonl")
    samples: list[dict[str, Any]] = []
    restarts: list[dict[str, Any]] = []
    actions: Counter[str] = Counter()
    failures: list[str] = []
    started = time.monotonic()
    cpu_start = time.process_time()
    organism = None
    tick = 0
    report: dict[str, Any] = {
        "schema": "UMBRA_DEVELOPMENT_LIFE_PROBE_V1", "classification": "DEVELOPMENT_ONLY",
        "organism_subject": SUBJECT, "production_subtree": actual_tree,
        "harness_sha256": stream_sha256(Path(__file__)), "seed": seed,
        "configuration": fingerprint(cfg), "target_ticks": segments * segment_ticks,
        "formal_seeds_consumed": 0, "formal_stages_executed": [],
        "limits": {"rss_observed_ceiling_mib": 180, "hot_tail_events": 128,
                   "segments": segments, "segment_ticks": segment_ticks},
        "limitations": ["compaction threshold 128 is a development override, not canonical 32768",
                        "no long-horizon slope or real-time CPU qualification",
                        "continuity is not subsystem causal necessity or human companion acceptance"],
        "failures": failures, "restarts": restarts, "samples": samples,
    }
    try:
        journal.append("REGISTERED", case_id="development-life", seed=seed, configuration=report["configuration"])
        journal.append("STARTED", case_id="development-life", seed=seed)
        organism = create_organism(cfg)
        identity = organism.identity.as_dict()
        report["birth_identity"] = identity
        # These are the frozen configuration's environment-fixture setup, not
        # fabricated learned experience. As in the qualified population, apply
        # them before HabitatEngine becomes the sole environmental writer.
        for method in ("_ensure_development_intervention", "_ensure_memory_history",
                       "_ensure_social_history", "_ensure_individuality_history"):
            getattr(organism, method)()
        report["initial_environment_setup"] = "accepted_population_fixture_before_Habitat_attachment"
        organism.embodiment.attach_habitat_engine(HabitatEngine(_habitat_state_for_scenario("S0")))
        for segment in range(segments):
            for _ in range(segment_ticks):
                result = organism.tick_once()
                tick = organism.tick
                actions[str(result.get("capability"))] += 1
                if result.get("no_safe_action") or organism.phys.critical_any():
                    failures.append(f"viability_boundary:tick_{tick}")
                    report["first_failure_state"] = {"physiology": organism.phys.as_dict(), "result": result}
                    break
                if tick % 32 == 0:
                    phys = organism.phys.as_dict()
                    hot_count = organism.store.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                    samples.append({"tick": tick, "elapsed_seconds": time.monotonic() - started,
                                    "rss_mib": current_rss_mib(), "hot_tail_events": hot_count,
                                    "database_and_sidecar_bytes": sum(p.stat().st_size for p in
                                        (database, Path(str(database) + "-wal"), Path(str(database) + "-shm")) if p.exists()),
                                    "physiological_margins": {name: min(phys[name] - bounds.critical_low,
                                        bounds.critical_high - phys[name]) for name, bounds in BOUNDS.items()}})
                    if samples[-1]["rss_mib"] > 180:
                        failures.append(f"observed_rss_ceiling:tick_{tick}")
                        break
            organism.snapshot_if_due(force=True)
            before = organism.authoritative_state()
            checkpoint = organism.store.latest_checkpoint()
            report["checkpoint_epoch"] = checkpoint["checkpoint_epoch"] if checkpoint else 0
            memory_bounded = organism.memory.counts_bounded()
            organism.close()
            organism = None
            digest = stream_sha256(database)
            validation = validate_database_copy(database, digest, tick, seed, expected_identity=identity, max_hot_tail=128)
            publish_json_once(root / f"segment-{segment:02d}.json", {
                "tick": tick, "database_sha256_at_boundary": digest, "validation": validation,
                "memory_bounded": memory_bounded, "checkpoint_epoch": report["checkpoint_epoch"],
            })
            journal.append("SEGMENT_SEALED", case_id="development-life", tick=tick, database_sha256=digest)
            if validation["verdict"] != "PASS" or not memory_bounded:
                failures.append(f"segment_content_validation:{segment}")
            if failures or segment == segments - 1:
                break
            organism = load_organism(cfg)
            restored_engine = restore_habitat_engine_from_checkpoint(organism)
            # Runtime deliberately rejects authoritative reads before Habitat
            # reattachment. Compare owners only after fulfilling that authority.
            after = organism.authoritative_state()
            differences = [owner for owner in OWNERS if before[owner] != after[owner]]
            binding = organism.embodiment.habitat_authority_binding
            habitat_valid = binding is not None and binding["state_hash"] == restored_engine.snapshot_view().state_hash
            restart = {"boundary_tick": tick, "owner_differences": differences,
                       "habitat_binding_matches": habitat_valid,
                       "declared_comparison_exclusions": ["session_id", "runtime_ready events", "wall-time anchor"]}
            restarts.append(restart)
            journal.append("RESTART_CHECKED", case_id="development-life", **restart)
            if differences or not habitat_valid:
                failures.append(f"restart_continuity:boundary_{tick}")
                break
    except Exception as exc:
        failures.append(f"probe_exception:{type(exc).__name__}:{exc}")
        journal.append("PROBE_INTERRUPTED", case_id="development-life", tick=tick, exception_type=type(exc).__name__)
    finally:
        if organism is not None:
            organism.close()
        report.update(ticks=tick, actions=dict(actions), elapsed_seconds=time.monotonic() - started,
                      process_cpu_seconds=time.process_time() - cpu_start)
        if trace.exists():
            report["trace"] = validate_trace_scope(trace, tick)
            report["trace_sha256"] = stream_sha256(trace)
            if report["trace"]["verdict"] != "PASS":
                failures.append("trace_scope_validation")
            rre = Counter()
            try:
                for row in iter_jsonl(trace):
                    kernel = row.get("viability_kernel") or {}
                    envelope = kernel.get("recovery_reachability_envelope")
                    if isinstance(envelope, dict):
                        rre["evaluations"] += 1
                        rre["activations"] += int(envelope.get("activation") is True)
                        rre["rejections"] += len(envelope.get("rejected", []))
                    else:
                        rre["no_active_envelope"] += 1
            except (OSError, ValueError, TypeError) as exc:
                failures.append(f"trace_count_unavailable:{type(exc).__name__}:{exc}")
            report["rre_capture_counts"] = dict(rre)
        if database.exists():
            report["database_sha256"] = stream_sha256(database)
        if tick != segments * segment_ticks or len(restarts) != segments - 1:
            failures.append("probe_horizon_or_restart_count_incomplete")
        report["verdict"] = "PASS" if not failures else "FAIL"
        journal.append("PROBE_FINISHED", case_id="development-life", verdict=report["verdict"], ticks=tick)
        journal.close()
        report["journal_sha256"] = stream_sha256(root / "stages.jsonl")
        publish_json_once(root / "result.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=97093002)
    args = parser.parse_args()
    result = run(args.work, seed=args.seed)
    print(json.dumps({"verdict": result["verdict"], "ticks": result["ticks"], "restarts": len(result["restarts"])}))
    raise SystemExit(0 if result["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
