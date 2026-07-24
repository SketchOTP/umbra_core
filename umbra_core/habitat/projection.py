"""Deeply immutable HabitatFeature compatibility projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from umbra_core.habitat.migration import feature_kind_from_object
from umbra_core.habitat.state import (
    FreeLocation,
    HabitatObject,
    HeldByLocation,
    ObjectKind,
    SocialEntitySpatialState,
)

if TYPE_CHECKING:
    from umbra_core.habitat.engine import BodyPoseView, HabitatSnapshot


class ProjectionMismatchError(Exception):
    """Projection version/hash does not match authoritative HabitatEngine snapshot."""


class HabitatWriteRejected(Exception):
    """Attempted write through read-only habitat projection."""


@dataclass(frozen=True)
class ImmutableHabitatFeature:
    kind: str
    x: float
    y: float
    radius: float
    chargeable: bool
    restable: bool
    inspectable: bool
    passable: bool
    occluded: bool
    object_id: str
    source_state_version: int
    source_object_version: int
    source_state_hash: str


@dataclass(frozen=True)
class ImmutablePartnerView:
    hidden_partner_id: str
    x: float
    y: float


@dataclass(frozen=True)
class ImmutableHabitatProjection:
    width: float
    height: float
    features: tuple[ImmutableHabitatFeature, ...]
    partners: tuple[ImmutablePartnerView, ...]
    blocked_cells: tuple[tuple[float, float, float], ...]
    delayed_consequence_ticks: int
    misleading_correlation: bool
    state_version: int
    state_hash: str
    habitat_id: str


def _feature_flags_for_object(obj: HabitatObject) -> tuple[bool, bool, bool]:
    chargeable = obj.object_kind in {ObjectKind.RESOURCE, ObjectKind.CHARGE_STATION, ObjectKind.PORTABLE_OBJECT}
    restable = obj.object_kind == ObjectKind.REST_STATION
    inspectable = obj.object_kind in {
        ObjectKind.INSPECTABLE,
        ObjectKind.ACTIVATABLE_OBJECT,
        ObjectKind.PORTABLE_OBJECT,
    }
    return chargeable, restable, inspectable


def _project_object(
    obj: HabitatObject,
    *,
    state_version: int,
    state_hash: str,
    body_pose: BodyPoseView | None,
) -> ImmutableHabitatFeature | ImmutablePartnerView | None:
    if isinstance(obj.location, HeldByLocation):
        if body_pose is None:
            return None
        x, y = body_pose.position.x, body_pose.position.y
        zone_id = obj.location.body_instance_id  # informational only for held
        _ = zone_id
    elif isinstance(obj.location, FreeLocation):
        x, y = obj.location.x, obj.location.y
    else:
        return None

    if obj.object_kind == ObjectKind.SOCIAL_ENTITY and isinstance(obj.state, SocialEntitySpatialState):
        return ImmutablePartnerView(hidden_partner_id=obj.state.entity_ref, x=x, y=y)

    chargeable, restable, inspectable = _feature_flags_for_object(obj)
    return ImmutableHabitatFeature(
        kind=feature_kind_from_object(obj),
        x=x,
        y=y,
        radius=obj.collision_radius,
        chargeable=chargeable,
        restable=restable,
        inspectable=inspectable,
        passable=obj.passable,
        occluded=obj.occluded,
        object_id=obj.object_id,
        source_state_version=state_version,
        source_object_version=obj.object_version,
        source_state_hash=state_hash,
    )


def project_features(
    snapshot: HabitatSnapshot,
    *,
    body_pose: BodyPoseView | None = None,
    width: float = 20.0,
    height: float = 20.0,
    blocked_cells: tuple[tuple[float, float, float], ...] = (),
    delayed_consequence_ticks: int = 0,
    misleading_correlation: bool = False,
) -> ImmutableHabitatProjection:
    """Project authoritative snapshot into legacy HabitatFeature-shaped views."""
    features: list[ImmutableHabitatFeature] = []
    partners: list[ImmutablePartnerView] = []
    for object_id in sorted(snapshot.objects):
        obj = snapshot.objects[object_id]
        projected = _project_object(
            obj,
            state_version=snapshot.state_version,
            state_hash=snapshot.state_hash,
            body_pose=body_pose,
        )
        if projected is None:
            continue
        if isinstance(projected, ImmutablePartnerView):
            partners.append(projected)
        else:
            features.append(projected)
    return ImmutableHabitatProjection(
        width=width,
        height=height,
        features=tuple(features),
        partners=tuple(partners),
        blocked_cells=blocked_cells,
        delayed_consequence_ticks=delayed_consequence_ticks,
        misleading_correlation=misleading_correlation,
        state_version=snapshot.state_version,
        state_hash=snapshot.state_hash,
        habitat_id=snapshot.habitat_id,
    )


def validate_projection(
    projection: ImmutableHabitatProjection,
    snapshot: HabitatSnapshot,
) -> None:
    """Fail closed when projection does not match authoritative snapshot."""
    if projection.state_version != snapshot.state_version:
        raise ProjectionMismatchError("state_version_mismatch")
    if projection.state_hash != snapshot.state_hash:
        raise ProjectionMismatchError("state_hash_mismatch")


class HabitatProjectionFacade:
    """Read-only Embodiment.habitat facade backed by HabitatEngine projection."""

    def __init__(self, projection: ImmutableHabitatProjection) -> None:
        self._projection = projection

    @property
    def width(self) -> float:
        return self._projection.width

    @property
    def height(self) -> float:
        return self._projection.height

    @property
    def features(self) -> tuple[ImmutableHabitatFeature, ...]:
        return self._projection.features

    @property
    def partners(self) -> tuple[ImmutablePartnerView, ...]:
        return self._projection.partners

    @property
    def blocked_cells(self) -> tuple[tuple[float, float, float], ...]:
        return self._projection.blocked_cells

    @property
    def delayed_consequence_ticks(self) -> int:
        return self._projection.delayed_consequence_ticks

    @property
    def misleading_correlation(self) -> bool:
        return self._projection.misleading_correlation

    def feature(self, kind: str) -> ImmutableHabitatFeature | None:
        for feat in self._projection.features:
            if feat.kind == kind:
                return feat
        return None

    def nearest(self, kind: str, x: float, y: float) -> tuple[ImmutableHabitatFeature | None, float]:
        import math

        best = None
        best_d = float("inf")
        for feat in self._projection.features:
            if feat.kind != kind:
                continue
            d = math.hypot(feat.x - x, feat.y - y)
            if d < best_d:
                best, best_d = feat, d
        return best, best_d

    def relocate(self, kind: str, x: float, y: float) -> None:
        raise HabitatWriteRejected("habitat_projection_is_read_only")

    def to_state(self) -> dict[str, object]:
        return {
            "width": self._projection.width,
            "height": self._projection.height,
            "features": [
                {
                    "kind": f.kind,
                    "x": f.x,
                    "y": f.y,
                    "radius": f.radius,
                    "chargeable": f.chargeable,
                    "restable": f.restable,
                    "inspectable": f.inspectable,
                    "passable": f.passable,
                    "occluded": f.occluded,
                    "object_id": f.object_id,
                    "source_state_version": f.source_state_version,
                    "source_object_version": f.source_object_version,
                    "source_state_hash": f.source_state_hash,
                }
                for f in self._projection.features
            ],
            "blocked_cells": [list(c) for c in self._projection.blocked_cells],
            "delayed_consequence_ticks": self._projection.delayed_consequence_ticks,
            "misleading_correlation": self._projection.misleading_correlation,
            "partners": [
                {"hidden_partner_id": p.hidden_partner_id, "x": p.x, "y": p.y}
                for p in self._projection.partners
            ],
            "state_version": self._projection.state_version,
            "state_hash": self._projection.state_hash,
            "habitat_id": self._projection.habitat_id,
        }
