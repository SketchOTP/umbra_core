"""Immutable, bounded habitat read model — projected once at derive time.

Design §2: "The habitat read model is projected once at derive time into the
packet and stored in the ring. Renderers must not reconstruct habitat later
when polling." This module only builds the projection; storing it inside a
bounded frame ring is Task 6.

Source of truth is `Embodiment.to_state()` — this module never invents
entities and never mutates the embodiment it reads from.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True)
class HabitatReadModel:
    entities: tuple[FrozenEntity, ...]
    version: int

    @classmethod
    def from_embodiment_state(
        cls,
        embodiment_state: dict[str, Any],
        *,
        version: int,
        max_entities: int = DEFAULT_MAX_ENTITIES,
    ) -> HabitatReadModel:
        """Bounded, order-stable projection: habitat features first, then
        partners. Never invents an entity absent from `embodiment_state` —
        an entity that disappears from world truth disappears from the view."""
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
        return cls(entities=tuple(entities[:max_entities]), version=version)
