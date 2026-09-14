"""Literal AS-018 downstream readiness preflight on an excluded fixture."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

from experiments.as018.full_config import config, fingerprint
from experiments.d009.run_experiment import _habitat_state_for_scenario
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism, load_organism


def run(root: Path = Path("/tmp/as018-downstream-preflight")) -> dict[str, object]:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    db = root / "preflight.sqlite"
    cfg = config(
        81818001,
        db,
        "R0",
        ledger_overrides={"ledger_hot_tail_event_max": 32, "ledger_max_events_per_tick": 16},
    )
    organism = create_organism(cfg)
    for method in (
        "_ensure_development_intervention",
        "_ensure_memory_history",
        "_ensure_social_history",
        "_ensure_individuality_history",
    ):
        getattr(organism, method)()
    engine = HabitatEngine(_habitat_state_for_scenario("S0"))
    organism.embodiment.attach_habitat_engine(engine)
    organism.run_ticks(205)
    before = organism.authoritative_state()
    checkpoint = organism.store.latest_checkpoint()
    organism.snapshot_if_due(force=True)
    organism.close()

    restored = load_organism(cfg)
    restored_engine = HabitatEngine(copy.deepcopy(engine.state))
    restored.embodiment.attach_habitat_engine(restored_engine)
    restored.store.validate_chain()
    checks = {
        "rre_enabled": bool(cfg.recovery_reachability_enabled),
        "checkpoint_created": checkpoint is not None,
        "identity_preserved": restored.identity.agent_id == before["identity"]["agent_id"],
        "tick_preserved": restored.tick == before["tick"],
        "chain_valid": True,
        "formal_seeds_consumed": 0,
    }
    restored.close()
    result = {
        "schema": "AS018_DOWNSTREAM_PREFLIGHT_V1",
        "directive": "UMBRA-AS-018",
        "database": str(db),
        "configuration": fingerprint(cfg),
        "checks": checks,
        "status": "PASS"
        if all(value for key, value in checks.items() if key != "formal_seeds_consumed")
        and checks["formal_seeds_consumed"] == 0
        else "FAIL",
        "formal_execution_started": False,
        "formal_seeds_consumed": 0,
    }
    (root / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    shutil.rmtree(root)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
