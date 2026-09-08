"""Non-formal executable checks for AS-014's R2 authority interventions.

This deliberately calls the actual current-stack intervention APIs without
spending a formal population seed or a multi-thousand-tick organism run.
"""

from __future__ import annotations

import copy
import shutil
from pathlib import Path
from typing import Any

from experiments.as009.qualification import PARTNER_OBJECT_ID, partner_object
from experiments.as014.full_config import BASELINE, DIRECTIVE, config, fingerprint
from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d014.run_formal import adapter_burst
from tools.as014_evidence import publish
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism, load_organism


PREFLIGHT_SEED = 41_414_023
PREFLIGHT_LEDGER = {
    "ledger_hot_tail_event_max": 64,
    "ledger_checkpoint_keep": 2,
}


def _ensure_histories(organism: Any) -> None:
    for method in (
        "_ensure_development_intervention",
        "_ensure_memory_history",
        "_ensure_social_history",
        "_ensure_individuality_history",
    ):
        getattr(organism, method)()


def run(work: Path) -> dict[str, Any]:
    """Exercise R2 creation, adapter, restart, occlusion, and reappearance."""
    if work.exists():
        raise FileExistsError(f"preflight_work_exists:{work}")
    work.mkdir(parents=True)
    db = work / "r2-interventions.sqlite"
    organism = create_organism(
        config(PREFLIGHT_SEED, db, "R2", ledger_overrides=PREFLIGHT_LEDGER)
    )
    _ensure_histories(organism)
    engine = HabitatEngine(_habitat_state_for_scenario("S10"))
    organism.embodiment.attach_habitat_engine(engine)
    organism.embodiment.body.x, organism.embodiment.body.y = 4.0, 3.0
    identity = organism.identity.agent_id
    try:
        created = engine.commit_object_creation(
            partner_object(),
            event_id=f"as014:preflight:create:{PREFLIGHT_SEED}",
            transaction_id=f"as014:preflight:create-txn:{PREFLIGHT_SEED}",
            request_id=f"as014:preflight:create-req:{PREFLIGHT_SEED}",
        )
        adapter_accepted = bool(adapter_burst(organism, PREFLIGHT_SEED, 1200))
        # Cross a normal runtime path before snapshot/restart; the event values
        # are non-formal, while the handlers above retain their R2 schedule IDs.
        organism.run_ticks(12)
        saved_habitat = copy.deepcopy(engine.state)
        organism.snapshot_if_due(force=True)
        organism.close()
        organism = load_organism(
            config(PREFLIGHT_SEED, db, "R2", ledger_overrides=PREFLIGHT_LEDGER)
        )
        engine = HabitatEngine(saved_habitat)
        organism.embodiment.attach_habitat_engine(engine)
        binding = organism.embodiment.habitat_authority_binding
        social_after_restart = engine.authoritative_social_entities()
        restarted = (
            organism.identity.agent_id == identity
            and binding is not None
            and binding["state_hash"] == engine.snapshot_view().state_hash
            and len(social_after_restart) == 1
        )
        hidden = engine.commit_object_visibility(
            PARTNER_OBJECT_ID,
            occluded=True,
            event_id=f"as014:preflight:hide:{PREFLIGHT_SEED}",
            transaction_id=f"as014:preflight:hide-txn:{PREFLIGHT_SEED}",
            request_id=f"as014:preflight:hide-req:{PREFLIGHT_SEED}",
        )
        hidden_state = engine.get_object(PARTNER_OBJECT_ID)
        shown = engine.commit_object_visibility(
            PARTNER_OBJECT_ID,
            occluded=False,
            event_id=f"as014:preflight:show:{PREFLIGHT_SEED}",
            transaction_id=f"as014:preflight:show-txn:{PREFLIGHT_SEED}",
            request_id=f"as014:preflight:show-req:{PREFLIGHT_SEED}",
        )
        shown_state = engine.get_object(PARTNER_OBJECT_ID)
        result = {
            "schema": "AS014_R2_INTERVENTION_PREFLIGHT_V1",
            "directive": DIRECTIVE,
            "baseline": BASELINE,
            "formal": False,
            "seed": PREFLIGHT_SEED,
            "configuration": fingerprint(organism.config),
            "checks": {
                "authoritative_partner_creation": (
                    created.get("event_type") == "habitat_object_created"
                    and len(engine.authoritative_social_entities()) == 1
                ),
                "adapter_submission": adapter_accepted,
                "restart_with_habitat_reattachment": restarted,
                "authoritative_occlusion": (
                    hidden.get("event_type") == "habitat_object_visibility_changed"
                    and hidden_state is not None
                    and hidden_state.occluded
                ),
                "authoritative_reappearance": (
                    shown.get("event_type") == "habitat_object_visibility_changed"
                    and shown_state is not None
                    and not shown_state.occluded
                ),
                "no_legacy_habitat_write": organism.embodiment._habitat_engine is engine,
            },
            "ticks": organism.tick,
        }
        result["pass"] = all(result["checks"].values())
        return result
    finally:
        organism.close()


def main() -> None:
    work = Path("/tmp/as014-r2-intervention-preflight-r1")
    # The work area is deliberately disposable, never scientific evidence.
    shutil.rmtree(work, ignore_errors=True)
    result = run(work)
    digest = publish("AS014_R2_AUTHORITY_INTERVENTION_PREFLIGHT.json", result)
    print({"pass": result["pass"], "sha256": digest, "ticks": result["ticks"]})


if __name__ == "__main__":
    main()
