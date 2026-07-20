"""Minimal 2D habitat and body — world truth owned here; policy never sees it."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from umbra_core.util import SeededRNG, clamp


CAPABILITIES = (
    "IDLE",
    "ORIENT",
    "MOVE",
    "APPROACH",
    "RETREAT",
    "INSPECT",
    "REST",
    "CHARGE",
)


@dataclass
class HabitatFeature:
    kind: str  # rest | resource | inspect | hazard | open
    x: float
    y: float
    radius: float = 1.2


@dataclass
class Habitat:
    width: float = 20.0
    height: float = 20.0
    features: list[HabitatFeature] = field(default_factory=list)

    @classmethod
    def default(cls) -> Habitat:
        return cls(
            features=[
                HabitatFeature("rest", 2.0, 2.0, 1.8),
                HabitatFeature("resource", 17.0, 3.0, 1.8),
                HabitatFeature("inspect", 10.0, 10.0, 1.5),
                HabitatFeature("hazard", 15.0, 15.0, 1.5),
            ]
        )

    def feature(self, kind: str) -> HabitatFeature | None:
        for f in self.features:
            if f.kind == kind:
                return f
        return None

    def relocate(self, kind: str, x: float, y: float) -> None:
        f = self.feature(kind)
        if f:
            f.x = clamp(x, 0.0, self.width)
            f.y = clamp(y, 0.0, self.height)

    def nearest(self, kind: str, x: float, y: float) -> tuple[HabitatFeature | None, float]:
        best = None
        best_d = float("inf")
        for f in self.features:
            if f.kind != kind:
                continue
            d = math.hypot(f.x - x, f.y - y)
            if d < best_d:
                best, best_d = f, d
        return best, best_d

    def to_state(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "features": [
                {"kind": f.kind, "x": f.x, "y": f.y, "radius": f.radius} for f in self.features
            ],
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> Habitat:
        feats = [
            HabitatFeature(kind=f["kind"], x=float(f["x"]), y=float(f["y"]), radius=float(f.get("radius", 1.2)))
            for f in d.get("features", [])
        ]
        return cls(width=float(d.get("width", 20.0)), height=float(d.get("height", 20.0)), features=feats)


@dataclass
class Body:
    x: float = 5.0
    y: float = 5.0
    heading: float = 0.0
    velocity: float = 0.0
    sensor_range: float = 10.0
    movement_reliability: float = 0.95

    def to_state(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "heading": self.heading,
            "velocity": self.velocity,
            "sensor_range": self.sensor_range,
            "movement_reliability": self.movement_reliability,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> Body:
        return cls(**{k: float(d[k]) for k in cls.__dataclass_fields__ if k in d})

    def dist_to(self, fx: float, fy: float) -> float:
        return math.hypot(fx - self.x, fy - self.y)

    def bearing_to(self, fx: float, fy: float) -> float:
        return math.atan2(fy - self.y, fx - self.x)


@dataclass
class Embodiment:
    """Owns world truth + body. Exposes only observations via Perception."""

    habitat: Habitat = field(default_factory=Habitat.default)
    body: Body = field(default_factory=Body)
    last_raw: dict[str, Any] = field(default_factory=dict)

    def world_truth(self) -> dict[str, Any]:
        """Authority-only — must not be passed to policy/arbitration."""
        return {
            "body": self.body.to_state(),
            "habitat": self.habitat.to_state(),
        }

    def clamp_body(self) -> None:
        self.body.x = clamp(self.body.x, 0.0, self.habitat.width)
        self.body.y = clamp(self.body.y, 0.0, self.habitat.height)
        self.body.heading = (self.body.heading + math.pi) % (2 * math.pi) - math.pi

    def execute_primitive(
        self,
        capability: str,
        params: dict[str, Any],
        rng: SeededRNG,
    ) -> dict[str, Any]:
        """Execute authorized capability against world. Returns raw result (unverified)."""
        b = self.body
        h = self.habitat
        ok = True
        reason = "ok"
        detail: dict[str, Any] = {"capability": capability, "params": dict(params)}

        if capability == "IDLE":
            b.velocity = 0.0
        elif capability == "ORIENT":
            target = float(params.get("heading", b.heading))
            b.heading = target
            b.velocity = 0.0
        elif capability in ("MOVE", "APPROACH", "RETREAT"):
            step = float(params.get("step", 1.0 if capability != "RETREAT" else 1.2))
            heading = float(params.get("heading", b.heading))
            if capability == "RETREAT":
                heading = heading + math.pi
            if rng.random() > b.movement_reliability:
                ok = False
                reason = "movement_slip"
                step *= 0.3
                heading += rng.uniform(-0.4, 0.4)
            b.heading = heading
            b.x += math.cos(heading) * step
            b.y += math.sin(heading) * step
            b.velocity = step
            self.clamp_body()
            # hazard contact
            haz, hd = h.nearest("hazard", b.x, b.y)
            if haz and hd <= haz.radius:
                detail["hazard_contact"] = True
            # auto-snap success for approach when inside target radius after move
            toward = params.get("toward")
            if toward and capability == "APPROACH":
                feat, d = h.nearest(toward if toward != "hazard" else "hazard", b.x, b.y)
                if feat and d <= feat.radius:
                    detail["arrived"] = True
        elif capability == "INSPECT":
            feat, d = h.nearest("inspect", b.x, b.y)
            if feat is None or d > feat.radius + 0.8:
                ok = False
                reason = "out_of_range"
            else:
                detail["inspected"] = True
                detail["object_kind"] = "inspect"
        elif capability == "REST":
            feat, d = h.nearest("rest", b.x, b.y)
            if feat is None or d > feat.radius + 0.3:
                ok = False
                reason = "not_at_rest"
            else:
                b.velocity = 0.0
                detail["rested"] = True
        elif capability == "CHARGE":
            feat, d = h.nearest("resource", b.x, b.y)
            if feat is None or d > feat.radius + 0.3:
                ok = False
                reason = "not_at_resource"
            else:
                b.velocity = 0.0
                detail["charged"] = True
        else:
            ok = False
            reason = "unknown_capability"

        detail["ok_raw"] = ok
        detail["reason"] = reason
        detail["body_after"] = self.body.to_state()
        self.last_raw = detail
        return detail

    def to_state(self) -> dict[str, Any]:
        return {"habitat": self.habitat.to_state(), "body": self.body.to_state()}

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> Embodiment:
        return cls(
            habitat=Habitat.from_state(d.get("habitat", {})),
            body=Body.from_state(d.get("body", {})),
        )
