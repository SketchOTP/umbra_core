"""Default-off AS-003P planning-shadow capture.

The sink is write-only. Its rows are never read by runtime or arbitration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from umbra_core.decision_trace import canonical_fingerprint
from umbra_core.embodiment import CAPABILITIES
from umbra_core.embodiment_adapters.profiles import profile_definition_hash

from .frame import PlanningEvidenceFrame, build_planning_evidence_frame
from .modal import profiles_for_candidate_views


class PlanningShadowSink:
    def __init__(self, path: str | None):
        self.path = path
        self._handle = None
        if path:
            destination = Path(path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            self._handle = destination.open("a", encoding="utf-8", buffering=1)

    @property
    def enabled(self) -> bool:
        return self._handle is not None

    def record(self, row: Mapping[str, Any]) -> bool:
        if self._handle is None:
            return False
        try:
            payload = json.dumps(dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            self._handle.write(payload + "\n")
            self._handle.flush()
            return True
        except Exception:
            return False

    def close(self) -> None:
        handle, self._handle = self._handle, None
        if handle is not None:
            handle.close()


def capture_runtime_frame(organism: Any) -> PlanningEvidenceFrame:
    adapter = organism.embodiment_adapter
    profile = adapter.profile if adapter is not None else None
    body_schema = organism.self_model.active if organism.self_model is not None else None
    body_schema_id = str(body_schema.body_schema_id if body_schema is not None else "legacy-body")
    body_schema_version = int(body_schema.version if body_schema is not None else 0)
    if profile is not None:
        profile_row = {
            "profile_id": profile.profile_id,
            "schema_version": profile.schema_version,
            "profile_definition_hash": profile_definition_hash(profile),
            "supported_capabilities": sorted(profile.supported_capabilities),
            "body_schema_identity": body_schema_id,
            "body_schema_version": body_schema_version,
        }
    else:
        profile_row = {
            "profile_id": "legacy-embodiment",
            "schema_version": "legacy-capability-contract",
            "profile_definition_hash": canonical_fingerprint(sorted(CAPABILITIES)),
            "supported_capabilities": sorted(CAPABILITIES),
            "body_schema_identity": body_schema_id,
            "body_schema_version": body_schema_version,
        }
    supports = {
        cap: organism.self_model.capability_support(cap)
        for cap in profile_row["supported_capabilities"]
    } if organism.self_model is not None else {}
    world = organism.world_model
    entities = [
        entity.to_dict()
        for entity in world.entities.values()
        if str(entity.entity_kind) in {"resource", "novel_crystal", "rest", "inspect"}
    ] if world is not None else []
    pending = {
        "pending_action": dict(organism._pending_action or {}),
        "delayed_proposal": dict(organism._delayed_proposal or {}),
        "pending_actuation": dict(organism.embodiment._pending_actuation or {}),
        "delay_remaining": int(organism.embodiment._delay_remaining),
    }
    source_versions = {
        "physiology": canonical_fingerprint(organism.phys.as_dict()),
        "body_profile": profile_row["profile_definition_hash"],
        "body_schema": f"{body_schema_id}:{body_schema_version}",
        "self_model": canonical_fingerprint(organism.self_model.to_state()) if organism.self_model is not None else None,
        "world_model_policy_state": canonical_fingerprint(entities),
        "world_model_route_evidence": canonical_fingerprint(world.route_evidence.to_state()) if world is not None else None,
        "world_model_affordances": canonical_fingerprint(
            {key: value.to_dict() for key, value in sorted(world.affordances.items())}
        ) if world is not None else None,
        "world_model_affordance_source_mode": canonical_fingerprint({
            "fixed_authored": bool(world.config.fixed_authored),
            "affordance_learning": bool(world.config.affordance_learning),
        }) if world is not None else None,
        "pending_execution": canonical_fingerprint(pending),
    }
    return build_planning_evidence_frame(
        organism_tick=organism.tick,
        organism_age=organism._tick_organism_age,
        monotonic_time=organism.monotonic_time,
        physiology=organism.phys.as_dict(),
        body_state=organism.embodiment.body.to_state(),
        body_profile=profile_row,
        self_model_body_schema={"body_schema_id": body_schema_id, "version": body_schema_version},
        capability_support=supports,
        world_entities=entities,
        world_object_persistence=bool(world is not None and world.config.object_persistence),
        pending_execution=pending,
        source_versions=source_versions,
        route_evidence_state=world.route_evidence.to_state() if world is not None else None,
        world_affordances=(
            {key: value.to_dict() for key, value in sorted(world.affordances.items())}
            if world is not None else None
        ),
        world_model_config=(
            {
                "fixed_authored": bool(world.config.fixed_authored),
                "affordance_learning": bool(world.config.affordance_learning),
            }
            if world is not None else None
        ),
    )


def shadow_row(frame: PlanningEvidenceFrame, views: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    profiles = profiles_for_candidate_views(frame, views)
    return {
        "schema": "AS003P_PLANNING_SHADOW_TRACE_V1",
        "tick": frame.organism_tick,
        "frame": frame.bind_candidates(views).to_canonical(),
        "candidate_profiles": list(profiles),
        "behavioral_authority": False,
        "rng_consumed": False,
        "owner_mutation": False,
    }
