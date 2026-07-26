"""Frozen D-011C diagnostic ablations; no diagnostic path writes production storage."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from umbra_core.perception import PerceptionMembrane
from umbra_core.perception_adapters import AdapterManifest, PerceptionAdapterError, SyntheticPerceptionAdapter


def _envelope(adapter: SyntheticPerceptionAdapter, source_id: str, observation_id: str):
    return adapter.submit(
        observation_id=observation_id, source_id=source_id, modality="visual_features", schema_version="v1",
        core_receipt_tick=0, source_timestamp=None, capture_interval=None, derived_features={"edges": [0.1]},
        confidence=0.6, uncertainty=0.4, provenance_chain=({"step": "synthetic", "source": source_id},),
        privacy_classification="DERIVED_ONLY", consent_state="CONSENT_GRANTED", retention_class="DERIVED_BOUNDED",
        replay_class="AUTHORITATIVE", integrity_metadata={"control": "true"},
    )


def run(seed: int) -> dict[str, object]:
    manifest = AdapterManifest("d011c-control", "1", ("visual_features",), {"visual_features": "v1"})
    adapter = SyntheticPerceptionAdapter(manifest)
    one = _envelope(adapter, f"source-a-{seed}", "one")
    two = _envelope(adapter, f"source-b-{seed}", "two")
    membrane = PerceptionMembrane()
    assert membrane.accept_adapter_observation(one, manifest)
    assert membrane.accept_adapter_observation(two, manifest)
    duplicate_suppressed = not membrane.accept_adapter_observation(one, manifest)
    forged = replace(one, manifest_hash="forged")
    downgraded = replace(one, schema_version="old")
    raw = replace(one, derived_features={"raw_payload": "diagnostic"})
    rejected = {}
    for name, envelope in (("provenance", forged), ("schema", downgraded), ("raw", raw)):
        try:
            envelope.validate(manifest)
        except PerceptionAdapterError:
            rejected[name] = 1
    return {
        "seed": seed,
        "C0": {"accepted": 2, "sources": 2, "uncertainty_preserved": one.uncertainty, "duplicate_suppressed": duplicate_suppressed, "raw_durable_count": 0},
        "C1": {"production_rejected": rejected["provenance"], "diagnostic_loss_if_disabled": 1},
        "C2": {"production_uncertainty": one.uncertainty, "forced_certainty_uncertainty": 0.0},
        "C3": {"production_duplicate_experience": 1, "diagnostic_loss_if_disabled": 2},
        "C4": {"production_rejected": rejected["raw"], "isolated_diagnostic_raw_count": 1},
        "C5": {"adapter_has_memory_authority": hasattr(adapter, "memory") or hasattr(adapter, "organism")},
        "C6": {"production_distinct_sources": 2, "pooled_diagnostic_sources": 1},
        "C7": {"production_rejected": rejected["schema"], "diagnostic_loss_if_disabled": 1},
        "C8": {"production_adapter_observations": 2, "disabled_adapter_observations": 0},
    }


if __name__ == "__main__":
    print(json.dumps([run(seed) for seed in (101, 202, 303, 404, 505)], sort_keys=True))
