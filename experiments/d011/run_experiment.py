"""D-011 synthetic contract stress; intentionally contains no device integration."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from umbra_core.perception import PerceptionMembrane
from umbra_core.perception_adapters import AdapterManifest, SyntheticPerceptionAdapter
from umbra_core.util import current_rss_mib


def run(count: int = 100_000) -> dict[str, float | int]:
    manifest = AdapterManifest("d011-stress", "1", ("body_telemetry",), {"body_telemetry": "v1"})
    adapter = SyntheticPerceptionAdapter(manifest)
    membrane = PerceptionMembrane()
    started = time.monotonic()
    rss_before = current_rss_mib()
    for number in range(count):
        envelope = adapter.submit(
            observation_id=f"stress-{number}", source_id="synthetic-body", modality="body_telemetry",
            schema_version="v1", core_receipt_tick=number, source_timestamp=None,
            capture_interval=None, derived_features={"temperature_delta": number % 3},
            confidence=0.5, uncertainty=0.5,
            provenance_chain=({"step": "synthetic", "source": "stress"},),
            privacy_classification="DERIVED_ONLY", consent_state="CONSENT_GRANTED",
            retention_class="DERIVED_BOUNDED", replay_class="AUTHORITATIVE",
            integrity_metadata={"fixture": "true"},
        )
        assert membrane.accept_adapter_observation(envelope, manifest)
    elapsed = time.monotonic() - started
    return {"count": count, "accepted": len(membrane.adapter_observations), "deduplication_bound": len(membrane.accepted_adapter_observation_ids), "elapsed_seconds": elapsed, "rss_delta_mib": current_rss_mib() - rss_before}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100_000)
    print(json.dumps(run(parser.parse_args().count), sort_keys=True))
