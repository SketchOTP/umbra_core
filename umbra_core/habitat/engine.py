"""HabitatEngine — sole habitat authority, queries, and mutate-under-txn hooks."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Callable

from umbra_core.habitat.projection import (
    ImmutableHabitatProjection,
    project_features,
    validate_projection,
)
from umbra_core.habitat.events import (
    HABITAT_OBJECT_CREATED,
    build_habitat_event,
    build_object_visibility_event,
)
from umbra_core.habitat.state import (
    FreeLocation,
    HabitatObject,
    HabitatState,
    HeldByLocation,
    MutationRejected,
    apply_committed_object_mutation,
    canonical_serialize,
    compute_habitat_definition_hash,
    compute_object_state_hash,
    ObjectKind,
    SocialEntitySpatialState,
    with_state_hash,
)


@dataclass(frozen=True)
class Position:
    x: float
    y: float


@dataclass(frozen=True)
class BodyCollisionShape:
    radius: float


@dataclass(frozen=True)
class BodyPoseView:
    body_instance_id: str
    body_pose_version: int
    position: Position
    collision_shape: BodyCollisionShape
    attachment_generation: int


@dataclass(frozen=True)
class ReachProfile:
    reach_radius: float


@dataclass(frozen=True)
class HabitatSnapshot:
    habitat_id: str
    state_version: int
    state_hash: str
    definition_hash: str
    habitat_tick: int
    objects: dict[str, HabitatObject]
    zones: dict[str, object]


class HabitatEngine:
    """Sole habitat writer. ponytail: mutate helpers are for tests/persistence txn until Task 5."""

    def __init__(self, state: HabitatState) -> None:
        self._state = state
        self.zone_free_object_count: dict[str, int] = {}
        self.zone_held_object_count: dict[str, int] = {}
        self.hold_index: dict[str, dict[int, str]] = {}
        self.free_spatial_index: dict[str, tuple[float, float, str]] = {}
        self._last_body_poses: dict[str, BodyPoseView] = {}
        self._rebuild_indexes()

    @property
    def state(self) -> HabitatState:
        return self._state

    def _rebuild_indexes(self) -> None:
        self.zone_free_object_count = {zone_id: 0 for zone_id in self._state.zones}
        self.zone_held_object_count = {zone_id: 0 for zone_id in self._state.zones}
        self.hold_index = {}
        self.free_spatial_index = {}
        for object_id, obj in self._state.objects.items():
            if isinstance(obj.location, FreeLocation):
                zone_id = obj.location.zone_id
                self.zone_free_object_count[zone_id] = self.zone_free_object_count.get(zone_id, 0) + 1
                self.free_spatial_index[object_id] = (obj.location.x, obj.location.y, zone_id)
            elif isinstance(obj.location, HeldByLocation):
                holder = obj.location.body_instance_id
                self.hold_index.setdefault(holder, {})[obj.location.hold_slot] = object_id
        self._apply_held_zone_counts(self._last_body_poses)

    def _apply_held_zone_counts(self, body_poses: dict[str, BodyPoseView]) -> None:
        """ponytail: held zone is informational; requires holder BodyPoseView at read time."""
        for zone_id in self._state.zones:
            self.zone_held_object_count[zone_id] = 0
        for obj in self._state.objects.values():
            if not isinstance(obj.location, HeldByLocation):
                continue
            pose = body_poses.get(obj.location.body_instance_id)
            if pose is None:
                continue
            zone_id = self.zone_at(pose.position.x, pose.position.y)
            if zone_id is not None:
                self.zone_held_object_count[zone_id] = self.zone_held_object_count.get(zone_id, 0) + 1

    def get_zone(self, zone_id: str):
        return self._state.zones.get(zone_id)

    def zone_at(self, x: float, y: float) -> str | None:
        matches: list[str] = []
        for zone_id, zone in self._state.zones.items():
            b = zone.bounds
            if b.x_min <= x <= b.x_max and b.y_min <= y <= b.y_max:
                matches.append(zone_id)
        if not matches:
            return None
        return sorted(matches)[0]

    def connected_zones(self, zone_id: str) -> tuple[str, ...]:
        out: list[str] = []
        for conn in self._state.zone_connections:
            if conn.from_zone_id == zone_id:
                out.append(conn.to_zone_id)
            elif conn.to_zone_id == zone_id:
                out.append(conn.from_zone_id)
        return tuple(sorted(set(out)))

    def get_object(self, object_id: str) -> HabitatObject | None:
        return self._state.objects.get(object_id)

    def query_nearby(
        self,
        x: float,
        y: float,
        radius: float,
        *,
        free_only: bool = True,
    ) -> tuple[str, ...]:
        hits: list[tuple[float, str]] = []
        for object_id, obj in self._state.objects.items():
            if free_only and not isinstance(obj.location, FreeLocation):
                continue
            if isinstance(obj.location, FreeLocation):
                ox, oy = obj.location.x, obj.location.y
            else:
                continue
            d = math.hypot(ox - x, oy - y)
            if d <= radius + obj.collision_radius:
                hits.append((d, object_id))
        return tuple(oid for _, oid in sorted(hits))

    def check_collision(
        self,
        proposed_shape: BodyCollisionShape,
        proposed_position: Position,
        *,
        exclude_body_instance_id: str | None = None,
    ) -> bool:
        """Return True when proposed body shape overlaps a non-passable free object."""
        for object_id, obj in self._state.objects.items():
            if not isinstance(obj.location, FreeLocation):
                continue
            if obj.passable:
                continue
            ox, oy = obj.location.x, obj.location.y
            dist = math.hypot(ox - proposed_position.x, oy - proposed_position.y)
            if dist < proposed_shape.radius + obj.collision_radius:
                return True
        _ = exclude_body_instance_id
        return False

    def check_range(
        self,
        body_pose: BodyPoseView,
        reach_profile: ReachProfile,
        object_id: str,
    ) -> bool:
        obj = self.get_object(object_id)
        if obj is None:
            return False
        if isinstance(obj.location, FreeLocation):
            ox, oy = obj.location.x, obj.location.y
        elif isinstance(obj.location, HeldByLocation):
            if obj.location.body_instance_id != body_pose.body_instance_id:
                return False
            ox, oy = body_pose.position.x, body_pose.position.y
        else:
            return False
        dist = math.hypot(ox - body_pose.position.x, oy - body_pose.position.y)
        return dist <= reach_profile.reach_radius + obj.collision_radius

    def held_by(self, body_instance_id: str) -> tuple[str, ...]:
        slots = self.hold_index.get(body_instance_id, {})
        return tuple(slots[slot] for slot in sorted(slots))

    def authoritative_social_entities(self) -> tuple[HabitatObject, ...]:
        """Trusted sensing-boundary view; never pass entity_ref to policy."""
        return tuple(
            self._state.objects[object_id]
            for object_id in sorted(self._state.objects)
            if self._state.objects[object_id].object_kind == ObjectKind.SOCIAL_ENTITY
            and isinstance(self._state.objects[object_id].state, SocialEntitySpatialState)
        )

    def snapshot_view(self) -> HabitatSnapshot:
        return HabitatSnapshot(
            habitat_id=self._state.habitat_id,
            state_version=self._state.state_version,
            state_hash=self._state.state_hash,
            definition_hash=self._state.definition_hash,
            habitat_tick=self._state.habitat_tick,
            objects=dict(self._state.objects),
            zones=dict(self._state.zones),
        )

    def project(
        self,
        *,
        body_pose: BodyPoseView | None = None,
        width: float = 20.0,
        height: float = 20.0,
        blocked_cells: tuple[tuple[float, float, float], ...] = (),
        delayed_consequence_ticks: int = 0,
        misleading_correlation: bool = False,
    ) -> ImmutableHabitatProjection:
        if body_pose is not None:
            self._last_body_poses[body_pose.body_instance_id] = body_pose
            self._apply_held_zone_counts(self._last_body_poses)
        return project_features(
            self.snapshot_view(),
            body_pose=body_pose,
            width=width,
            height=height,
            blocked_cells=blocked_cells,
            delayed_consequence_ticks=delayed_consequence_ticks,
            misleading_correlation=misleading_correlation,
        )

    def validate_projection(self, projection: ImmutableHabitatProjection) -> None:
        validate_projection(projection, self.snapshot_view())

    def commit_object_mutation(
        self,
        object_id: str,
        mutate_fn: Callable[[HabitatObject], HabitatObject],
    ) -> None:
        """ponytail: production callers must use persistence transactions (Task 5)."""
        obj = self._state.objects.get(object_id)
        if obj is None:
            raise MutationRejected(f"missing_object:{object_id}")
        updated_obj = apply_committed_object_mutation(obj, mutate_fn)
        new_objects = dict(self._state.objects)
        new_objects[object_id] = updated_obj
        bumped = replace(self._state, objects=new_objects, state_version=self._state.state_version + 1)
        self._state = with_state_hash(bumped)
        self._rebuild_indexes()

    def commit_object_creation(
        self,
        obj: HabitatObject,
        *,
        event_id: str | None = None,
        transaction_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, object]:
        """Create an object through the sole habitat authority and return its ledger event."""
        if obj.object_id in self._state.objects:
            raise MutationRejected(f"duplicate_object:{obj.object_id}")
        before = self._state
        objects = dict(before.objects)
        objects[obj.object_id] = obj
        after = replace(
            before,
            objects=objects,
            definition_hash=compute_habitat_definition_hash(replace(before, objects=objects)),
            state_version=before.state_version + 1,
        )
        self._state = with_state_hash(after)
        self._rebuild_indexes()
        return build_habitat_event(
            before,
            self._state,
            HABITAT_OBJECT_CREATED,
            extra_payload={"object": canonical_serialize(obj)},
            event_id=event_id,
            transaction_id=transaction_id,
            request_id=request_id,
        )

    def commit_object_visibility(
        self,
        object_id: str,
        *,
        occluded: bool,
        event_id: str | None = None,
        transaction_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, object]:
        """Authoritatively change occlusion and return its canonical replay event."""
        obj = self._state.objects.get(object_id)
        if obj is None:
            raise MutationRejected(f"missing_object:{object_id}")
        before = self._state
        updated = replace(obj, object_version=obj.object_version + 1, occluded=bool(occluded), object_state_hash="")
        updated = replace(updated, object_state_hash=compute_object_state_hash(updated))
        objects = dict(before.objects)
        objects[object_id] = updated
        self._state = with_state_hash(replace(before, objects=objects, state_version=before.state_version + 1))
        self._rebuild_indexes()
        return build_object_visibility_event(
            before,
            self._state,
            object_id=object_id,
            event_id=event_id,
            transaction_id=transaction_id,
            request_id=request_id,
        )

    def commit_free_location(
        self,
        object_id: str,
        x: float,
        y: float,
        *,
        zone_id: str | None = None,
    ) -> None:
        """ponytail: test/persistence entry point for relocating free objects."""

        def relocate(obj: HabitatObject) -> HabitatObject:
            if not isinstance(obj.location, FreeLocation):
                raise MutationRejected("not_free_object")
            zid = zone_id or self.zone_at(x, y) or obj.location.zone_id
            return replace(obj, location=FreeLocation(x, y, zid))

        self.commit_object_mutation(object_id, relocate)
