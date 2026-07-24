"""Immutable, bounded habitat read model — projected once at derive time.

Design §2 / D-009 §4.4: projected once into the render packet and stored in
the ring. Renderers must not reconstruct habitat later when polling.

D-009 source of truth is `HabitatEngine.snapshot_view()` — not
`Embodiment.to_state()`. Held-object positions require a matching
`BodyPoseView` and `HELD_BY.attachment_generation`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from umbra_core.habitat.migration import feature_kind_from_object
from umbra_core.habitat.state import FreeLocation, HeldByLocation, ObjectKind, SocialEntitySpatialState

if TYPE_CHECKING:
    from umbra_core.habitat.engine import BodyPoseView, HabitatSnapshot

DEFAULT_MAX_ENTITIES = 64


@dataclass(frozen=True)
class FrozenEntity:
    kind: str
    entity_id: str
    x: float
    y: float
    radius: float = 0.0
    passable: bool = True
    occluded: bool = False
    object_id: str | None = None
    held_body_instance_id: str | None = None
    held_attachment_generation: int | None = None


@dataclass(frozen=True)
class HabitatReadModel:
    entities: tuple[FrozenEntity, ...]
    version: int
    state_hash: str = ""

    @classmethod
    def from_habitat_snapshot(
        cls,
        snapshot: HabitatSnapshot,
        *,
        body_pose: BodyPoseView | None = None,
        max_entities: int = DEFAULT_MAX_ENTITIES,
    ) -> HabitatReadModel:
        """Bounded projection from authoritative `HabitatEngine` snapshot."""
        entities: list[FrozenEntity] = []
        for object_id in sorted(snapshot.objects):
            obj = snapshot.objects[object_id]
            if isinstance(obj.location, HeldByLocation):
                if body_pose is None:
                    continue
                if obj.location.body_instance_id != body_pose.body_instance_id:
                    continue
                if obj.location.attachment_generation != body_pose.attachment_generation:
                    continue
                x, y = body_pose.position.x, body_pose.position.y
                held_body = obj.location.body_instance_id
                held_gen = obj.location.attachment_generation
            elif isinstance(obj.location, FreeLocation):
                x, y = obj.location.x, obj.location.y
                held_body = None
                held_gen = None
            else:
                continue

            if obj.object_kind == ObjectKind.SOCIAL_ENTITY and isinstance(
                obj.state, SocialEntitySpatialState
            ):
                entities.append(
                    FrozenEntity(
                        kind="partner",
                        entity_id=obj.state.entity_ref,
                        x=x,
                        y=y,
                        object_id=object_id,
                        held_body_instance_id=held_body,
                        held_attachment_generation=held_gen,
                    )
                )
                continue

            entities.append(
                FrozenEntity(
                    kind=feature_kind_from_object(obj),
                    entity_id=object_id,
                    x=x,
                    y=y,
                    radius=float(obj.collision_radius),
                    passable=bool(obj.passable),
                    occluded=bool(obj.occluded),
                    object_id=object_id,
                    held_body_instance_id=held_body,
                    held_attachment_generation=held_gen,
                )
            )
        return cls(
            entities=tuple(entities[:max_entities]),
            version=snapshot.state_version,
            state_hash=snapshot.state_hash,
        )

    @classmethod
    def from_embodiment_state(
        cls,
        embodiment_state: dict[str, Any],
        *,
        version: int,
        max_entities: int = DEFAULT_MAX_ENTITIES,
    ) -> HabitatReadModel:
        """D-008 legacy path — projects `Embodiment.to_state()["habitat"]`."""
        habitat = embodiment_state.get("habitat", {}) or {}
        entities: list[FrozenEntity] = []
        for i, feat in enumerate(habitat.get("features", [])):
            entities.append(
                FrozenEntity(
                    kind=str(feat["kind"]),
                    entity_id=f"feature:{i}:{feat['kind']}",
                    x=float(feat["x"]),
                    y=float(feat["y"]),
                    radius=float(feat.get("radius", 0.0)),
                    passable=bool(feat.get("passable", True)),
                    occluded=bool(feat.get("occluded", False)),
                    object_id=feat.get("object_id"),
                )
            )
        for partner in habitat.get("partners", []):
            entities.append(
                FrozenEntity(
                    kind="partner",
                    entity_id=str(partner["hidden_partner_id"]),
                    x=float(partner["x"]),
                    y=float(partner["y"]),
                )
            )
        state_hash = str(habitat.get("state_hash", ""))
        return cls(
            entities=tuple(entities[:max_entities]),
            version=version,
            state_hash=state_hash,
        )
