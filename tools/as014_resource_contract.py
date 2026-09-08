"""Publish the AS-014 resource-contract reconstruction from frozen sources."""

from __future__ import annotations

from pathlib import Path

from tools.as014_evidence import publish


ROOT = Path(__file__).resolve().parents[1]


def _sha(path: str) -> str:
    import hashlib

    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main() -> None:
    sources = {
        name: {"path": name, "sha256": _sha(name)}
        for name in (
            "experiments/d009/run_performance.py",
            "experiments/d009/thresholds.json",
            "experiments/d009/performance-protocol.json",
            "experiments/as013/downstream.py",
            "umbra_core/persistence.py",
        )
    }
    accelerated = {
        "contract": "D009_ACCELERATED_100K",
        "measures": [
            "elapsed_s",
            "cpu_s via time.process_time",
            "cpu_frac_of_one_core",
            "rss_p95_mib",
            "frame_ring occupancy",
            "habitat boundedness",
            "attachment monotonicity",
            "restart continuity",
        ],
        "frozen_pass_predicate": [
            "bounded",
            "restart_ok",
            "minimum tick count",
            "rss_p95_mib <= rss_p95_mib_max",
        ],
        "cpu_mean_frac_max_used_in_predicate": False,
        "conclusion": "ACCELERATED_CPU_SCOPE_MISMATCH_CONFIRMED",
        "successor_rule": "Accelerated qualification reports CPU and throughput; the 0.05 one-core ceiling is enforced only by the real-time S3 contract.",
    }
    storage = {
        "field": "habitat_event_storage_growth_limit_bytes",
        "frozen_value_bytes": 67_108_864,
        "source_scope": "D009 habitat/event-storage resource contract",
        "not_lawful_scope": "universal total SQLite main+WAL+SHM size or growth ceiling",
        "implementation_finding": {
            "Store.event_storage_budget": "optional count-of-events guard, not a byte quota",
            "current_hot_ledger": "append-only events table; snapshot pruning retains two snapshots and does not bound events",
        },
        "conclusion": "STORAGE_THRESHOLD_SCOPE_CONFIRMED",
        "successor_rule": "AS-014 uses structural bounded-hot-storage acceptance: fixed tail, bounded checkpoints/snapshots/auxiliary tables, and physical reclamation. It does not retrospectively change AS-013.",
    }
    common = {
        "directive": "UMBRA-AS-014",
        "baseline": "a97171a2dab7c1750e2556727bce9e3648bb359a",
        "predecessor": "AS013_LONG_HORIZON_BOUNDEDNESS_FAIL",
        "sources": sources,
        "historical_integrity": "AS-013 remains failed under its frozen combined CPU and total-database-growth predicate. These scope findings govern only AS-014 successor contracts.",
    }
    publish("AS014_RESOURCE_CONTRACT_RECONSTRUCTION.json", {**common, "accelerated_100k": accelerated, "realtime_s3": {
        "warmup_seconds": 300,
        "measure_seconds": 3600,
        "tick_hz": 2,
        "sample_interval_seconds": 5,
        "minimum_measured_samples": 360,
        "cpu_mean_fraction_max": 0.05,
        "cpu_is_acceptance_predicate": True,
    }})
    publish("AS014_STORAGE_THRESHOLD_SCOPE.json", {**common, "storage": storage})


if __name__ == "__main__":
    main()
