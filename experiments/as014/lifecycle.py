"""AS-014 whole-life checkpoint/compaction continuity qualification."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from experiments.as009.qualification import partner_object
from experiments.as014.full_config import BASELINE, DIRECTIVE, config, fingerprint
from experiments.d009.run_experiment import _habitat_state_for_scenario
from umbra_core.embodiment_adapters.profiles import MINIMAL_CREATURE_BODY
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism, load_organism, restore_habitat_engine_from_checkpoint


def _ensure_histories(organism: Any) -> None:
    for method in (
        "_ensure_development_intervention",
        "_ensure_memory_history",
        "_ensure_social_history",
        "_ensure_individuality_history",
    ):
        getattr(organism, method)()


def _restore(seed: int, db: Path) -> tuple[Any, HabitatEngine]:
    organism = load_organism(config(seed, db, "R2"))
    engine = restore_habitat_engine_from_checkpoint(organism)
    binding = organism.embodiment.habitat_authority_binding
    view = engine.snapshot_view()
    if binding is None or binding["state_hash"] != view.state_hash:
        raise RuntimeError("AS014_LIFECYCLE_HABITAT_BINDING_INVALID")
    return organism, engine


def _checkpoint_cycle(organism: Any, minimum_ticks: int = 7200) -> None:
    organism.run_ticks(minimum_ticks)
    checkpoint = organism.store.latest_checkpoint()
    if checkpoint is None:
        raise RuntimeError("AS014_LIFECYCLE_MAINTENANCE_NOT_REACHED")
    organism.store.validate_chain()


def lifecycle(seed: int, work: Path) -> dict[str, Any]:
    db = work / "lifecycle.sqlite"
    organism = create_organism(config(seed, db, "R2"))
    _ensure_histories(organism)
    engine = HabitatEngine(_habitat_state_for_scenario("S10"))
    organism.embodiment.attach_habitat_engine(engine)
    identity = organism.identity.as_dict()
    engine.commit_object_creation(
        partner_object(),
        event_id=f"as014:lifecycle:create:{seed}",
        transaction_id=f"as014:lifecycle:create-txn:{seed}",
        request_id=f"as014:lifecycle:create-req:{seed}",
    )
    _checkpoint_cycle(organism)
    memory_before = copy.deepcopy(organism.memory.to_state())
    social_before = copy.deepcopy(organism.social.to_state())
    individuality_before = copy.deepcopy(organism.individuality.to_state())
    organism.snapshot_if_due(force=True)
    organism.close()

    organism, engine = _restore(seed, db)
    first_restart = (
        organism.identity.as_dict() == identity
        and len(engine.authoritative_social_entities()) == 1
        and organism.memory.to_state() == memory_before
        and organism.social.to_state() == social_before
        and organism.individuality.to_state() == individuality_before
    )
    old_body = organism.embodiment_adapter.state.body_instance_id
    replacement = organism.replace_physical_body(
        new_profile_id=MINIMAL_CREATURE_BODY.profile_id,
        reason="as014_lifecycle_true_replacement",
    )
    replacement_ok = (
        replacement["new_body_instance_id"] != old_body
        and organism.identity.as_dict() == identity
        and organism.self_model.body_binding_id == replacement["new_body_binding_id"]
        and organism.embodiment.body_occupancy_view().body_instance_id == replacement["new_body_instance_id"]
    )
    owners_preserved = (
        organism.memory.to_state() == memory_before
        and organism.social.to_state() == social_before
        and organism.individuality.to_state() == individuality_before
    )
    organism.snapshot_if_due(force=True)
    organism.close()

    organism, engine = _restore(seed, db)
    post_replacement_restart = (
        organism.identity.as_dict() == identity
        and organism.embodiment_adapter.state.body_instance_id == replacement["new_body_instance_id"]
        and organism.embodiment.habitat_authority_binding["state_hash"] == engine.snapshot_view().state_hash
    )
    organism.embodiment_adapter.swap_profile("ABSTRACT_SHAPE_BODY", origin="AS014_LIFECYCLE_PROFILE_SWAP")
    profile_ok = (
        organism.embodiment_adapter.state.body_instance_id == replacement["new_body_instance_id"]
        and organism.embodiment.body_occupancy_view().body_instance_id == replacement["new_body_instance_id"]
    )
    organism.run_ticks(100)
    organism.snapshot_if_due(force=True)
    organism.store.validate_chain()
    checkpoint = organism.store.latest_checkpoint()
    result = {
        "schema": "AS014_LIFECYCLE_RESULT_V1",
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "seed": seed,
        "ticks": organism.tick,
        "configuration": fingerprint(organism.config),
        "checkpoint_epoch": checkpoint["checkpoint_epoch"] if checkpoint else 0,
        "checks": {
            "checkpoint_maintenance": checkpoint is not None,
            "restart_habitat_and_owners": first_restart,
            "true_physical_body_replacement": replacement_ok,
            "owner_continuity": owners_preserved,
            "post_replacement_restart": post_replacement_restart,
            "compatible_profile_swap": profile_ok,
            "continued_organism_execution": organism.tick >= 7300,
        },
    }
    organism.close()
    result["pass"] = all(result["checks"].values())
    return result


__all__ = ["lifecycle"]
