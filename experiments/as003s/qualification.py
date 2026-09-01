"""One bounded, zero-tick AS-003S lifecycle qualification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.util import canon_json, sha256_hex


def _hash(value: object) -> str:
    return sha256_hex(canon_json(value))


def run(db_path: Path) -> dict[str, object]:
    if db_path.exists():
        raise FileExistsError(f"qualification database must be fresh: {db_path}")
    cfg = OrganismConfig(
        db_path=str(db_path),
        seed=3003,
        drift_enabled=False,
        embodiment_adapter_enabled=True,
        memory_enabled=True,
        social_enabled=True,
        individuality_enabled=True,
        wall_time_fn=lambda: 1_800_000_000.0,
    )
    organism = create_organism(cfg)
    identity_before = organism.identity.as_dict()
    adapter_before = organism.embodiment_adapter.state.to_state()
    binding_before = organism.self_model.body_binding_id
    schema_before = organism.self_model.active.body_schema_id
    owner_hashes_before = {
        "memory": _hash(organism.memory.to_state()),
        "social": _hash(organism.social.to_state()),
        "individuality": _hash(organism.individuality.to_state()),
    }

    replacement = organism.replace_physical_body(
        new_profile_id="MINIMAL_CREATURE_BODY",
        reason="as003s_bounded_lifecycle_qualification",
    )
    identity_after = organism.identity.as_dict()
    occupancy = organism.embodiment.body_occupancy_view()
    owner_hashes_after = {
        "memory": _hash(organism.memory.to_state()),
        "social": _hash(organism.social.to_state()),
        "individuality": _hash(organism.individuality.to_state()),
    }
    assert identity_after == identity_before
    assert replacement["new_body_instance_id"] != replacement["old_body_instance_id"]
    assert organism.embodiment_adapter.state.body_instance_id == occupancy.body_instance_id
    assert organism.embodiment_adapter.state.attachment_generation == occupancy.attachment_generation
    assert organism.self_model.body_binding_id == replacement["new_body_binding_id"]
    assert organism.self_model.active.body_schema_id == replacement["new_body_schema_id"]
    assert owner_hashes_after == owner_hashes_before
    organism.close()

    restored = load_organism(cfg)
    restart = {
        "identity_equal": restored.identity.as_dict() == identity_before,
        "body_instance_id": restored.embodiment_adapter.state.body_instance_id,
        "attachment_generation": restored.embodiment_adapter.state.attachment_generation,
        "body_binding_id": restored.self_model.body_binding_id,
        "body_schema_id": restored.self_model.active.body_schema_id,
        "profile_id": restored.embodiment_adapter.state.body_profile_id,
        "occupancy_equal": (
            restored.embodiment_adapter.state.body_instance_id
            == restored.embodiment.body_occupancy_view().body_instance_id
            and restored.embodiment_adapter.state.attachment_generation
            == restored.embodiment.body_occupancy_view().attachment_generation
        ),
        "owner_hashes_equal": {
            "memory": _hash(restored.memory.to_state()) == owner_hashes_before["memory"],
            "social": _hash(restored.social.to_state()) == owner_hashes_before["social"],
            "individuality": (
                _hash(restored.individuality.to_state())
                == owner_hashes_before["individuality"]
            ),
        },
    }
    assert restart["identity_equal"]
    assert restart["body_instance_id"] == replacement["new_body_instance_id"]
    assert restart["attachment_generation"] == replacement["new_generation"]
    assert restart["body_binding_id"] == replacement["new_body_binding_id"]
    assert restart["body_schema_id"] == replacement["new_body_schema_id"]
    assert restart["occupancy_equal"]
    assert all(restart["owner_hashes_equal"].values())

    body_before_swap = restored.embodiment_adapter.state.body_instance_id
    generation_before_swap = restored.embodiment_adapter.state.attachment_generation
    restored.embodiment_adapter.swap_profile("ABSTRACT_SHAPE_BODY", origin="AS003S_QUALIFICATION")
    profile_swap = {
        "body_instance_id_stable": (
            restored.embodiment_adapter.state.body_instance_id == body_before_swap
        ),
        "generation_before": generation_before_swap,
        "generation_after": restored.embodiment_adapter.state.attachment_generation,
        "profile_after": restored.embodiment_adapter.state.body_profile_id,
        "occupancy_equal": (
            restored.embodiment_adapter.state.body_instance_id
            == restored.embodiment.body_occupancy_view().body_instance_id
            and restored.embodiment_adapter.state.attachment_generation
            == restored.embodiment.body_occupancy_view().attachment_generation
        ),
    }
    assert profile_swap["body_instance_id_stable"]
    assert profile_swap["generation_after"] == generation_before_swap + 1
    assert profile_swap["occupancy_equal"]
    replacement_event_count = len(
        [
            event
            for event in restored.store.iter_events()
            if event["event_type"] == "embodiment_body_replaced"
        ]
    )
    restored.store.validate_chain()
    restored.close()

    return {
        "schema": "as003s.bounded-lifecycle-qualification.v1",
        "verdict": "PASS",
        "organism_creations": 1,
        "restart_loads": 1,
        "organism_ticks": 0,
        "identity_before": identity_before,
        "identity_after": identity_after,
        "adapter_before": adapter_before,
        "old_body_binding_id": binding_before,
        "old_body_schema_id": schema_before,
        "replacement": replacement,
        "owner_hashes_preserved": owner_hashes_after == owner_hashes_before,
        "restart": restart,
        "profile_swap": profile_swap,
        "replacement_event_count": replacement_event_count,
        "event_chain_valid": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.db_path), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
