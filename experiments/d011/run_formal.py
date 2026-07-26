"""Frozen D-011C C0 performance execution against the real SQLite intake path."""

from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from umbra_core.perception_adapters import AdapterManifest, SyntheticPerceptionAdapter
from umbra_core.runtime import OrganismConfig, create_organism
from umbra_core.util import current_rss_mib


def _raw_count(value: object) -> int:
    forbidden = {"raw", "raw_payload", "image", "video", "audio", "frame", "samples", "bytes", "base64", "location_trace"}
    if isinstance(value, dict):
        return sum(key.lower() in forbidden for key in value) + sum(_raw_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(_raw_count(item) for item in value)
    return 0


def run(count: int, seed: int) -> dict[str, float | int | bool]:
    with tempfile.TemporaryDirectory(prefix="umbra-d011c-") as directory:
        db_path = str(Path(directory) / "formal.db")
        manifest = AdapterManifest("d011c", "1", ("body_telemetry",), {"body_telemetry": "v1"})
        adapter = SyntheticPerceptionAdapter(manifest)
        org = create_organism(OrganismConfig(db_path=db_path, seed=seed))
        rss_before = current_rss_mib()
        cpu_before = time.process_time()
        started = time.monotonic()
        for number in range(count):
            envelope = adapter.submit(
                observation_id=f"{seed}-{number}", source_id=f"source-{seed % 2}", modality="body_telemetry",
                schema_version="v1", core_receipt_tick=org.tick, source_timestamp=None, capture_interval=None,
                derived_features={"temperature_delta": number % 3}, confidence=0.5, uncertainty=0.5,
                provenance_chain=({"step": "synthetic", "source": "formal"},), privacy_classification="DERIVED_ONLY",
                consent_state="CONSENT_GRANTED", retention_class="DERIVED_BOUNDED", replay_class="AUTHORITATIVE",
                integrity_metadata={"seed": str(seed)},
            )
            assert org.submit_perception_observation(envelope, manifest)
        wall = time.monotonic() - started
        cpu = time.process_time() - cpu_before
        raw_count = sum(
            _raw_count(json.loads(row[0]))
            for row in org.store.conn.execute("SELECT payload FROM events")
        )
        db_growth = os.path.getsize(db_path)
        result = {
            "seed": seed, "count": count, "elapsed_seconds": wall, "cpu_fraction": cpu / wall if wall else 0.0,
            "current_rss_mib": current_rss_mib(), "rss_delta_mib": current_rss_mib() - rss_before,
            "database_growth_bytes": db_growth, "accepted_observation_throughput": count / wall if wall else 0.0,
            "deduplication_state_bound": len(org.perception.accepted_adapter_observation_ids),
            "adapter_state_bound": len(org.perception.adapter_observations),
            "provenance_storage_growth": org.store.conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = 'perception_adapter_observation_accepted'"
            ).fetchone()[0],
            "raw_payload_durable_count": raw_count,
        }
        org.close()
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=101)
    print(json.dumps(run(parser.parse_args().count, parser.parse_args().seed), sort_keys=True))
