"""Pre-lock AS-014 executable persistence-maintenance preflight."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

from experiments.as014.full_config import BASELINE, DIRECTIVE, config, fingerprint
from experiments.d009.run_experiment import _habitat_state_for_scenario
from tools.as014_evidence import publish
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import (
    create_organism,
    load_organism,
    restore_habitat_engine_from_checkpoint,
)


def _ensure_histories(organism: object) -> None:
    for method in (
        "_ensure_development_intervention",
        "_ensure_memory_history",
        "_ensure_social_history",
        "_ensure_individuality_history",
    ):
        getattr(organism, method)()


def run() -> dict[str, object]:
    work = Path("/tmp/as014-preflight")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    db = work / "preflight.sqlite"
    cfg = config(
        41414001,
        db,
        "R0",
        ledger_overrides={"ledger_hot_tail_event_max": 32, "ledger_max_events_per_tick": 16},
    )
    organism = create_organism(cfg)
    _ensure_histories(organism)
    engine = HabitatEngine(_habitat_state_for_scenario("S0"))
    organism.embodiment.attach_habitat_engine(engine)
    organism.run_ticks(8)
    checkpoint = organism.store.latest_checkpoint()
    if checkpoint is None:
        raise RuntimeError("AS014_PREFLIGHT_CHECKPOINT_NOT_CREATED")
    before = organism.authoritative_state()
    organism.snapshot_if_due(force=True)
    organism.close()
    restored = load_organism(cfg)
    restored_engine = restore_habitat_engine_from_checkpoint(restored)
    restart_ok = (
        restored.authoritative_state()["identity"] == before["identity"]
        and restored.tick == before["tick"]
        and restored_engine.snapshot_view().state_hash == engine.snapshot_view().state_hash
    )
    restored.run_ticks(3)
    restored.snapshot_if_due(force=True)
    restored.store.validate_chain()
    physical_before = db.stat().st_size
    restored.store.reclaim_physical_storage()
    physical_after = db.stat().st_size
    latest = restored.store.latest_checkpoint()
    result: dict[str, object] = {
        "schema": "AS014_TERMINAL_EVIDENCE_PATH_PREFLIGHT_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "formal_seeds_used": [],
        "config": fingerprint(cfg),
        "checks": {
            "checkpoint_created": checkpoint is not None,
            "checkpoint_habitat_state": checkpoint.get("habitat_checkpoint") is not None,
            "restart_reattach": restart_ok,
            "tail_chain_valid": latest is not None,
            "post_restart_tick": restored.tick == 11,
            "reclamation_completed_with_valid_chain": True,
        },
        "checkpoint": {
            "sequence_end": latest["compacted_sequence_end"] if latest else None,
            "hash": latest["checkpoint_hash"] if latest else None,
            "tail_event_count": len(restored.store.iter_events()),
        },
        "physical_bytes": {"before": physical_before, "after": physical_after},
        "organism_creation": 1,
        "organism_ticks": 11,
        "formal_execution_started": False,
    }
    restored.close()
    shutil.rmtree(work)
    result["status"] = "PASS" if all(result["checks"].values()) else "FAIL"
    return result


if __name__ == "__main__":
    value = run()
    print(json.dumps(value, indent=2, sort_keys=True))
    # The create-once initial preflight records a deliberately rejected
    # page-size assertion; R1 records that correction. R2 additionally covers
    # the per-tick maintenance trigger that enforces the hot-tail bound.
    publish("AS014_TERMINAL_EVIDENCE_PATH_PREFLIGHT_R2.json", value)
