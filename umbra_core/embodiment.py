"""Minimal 2D habitat and body — world truth owned here; policy never sees it."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from umbra_core.util import SeededRNG, clamp, angle_diff


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
    kind: str  # rest | resource | inspect | hazard | open | novel_*
    x: float
    y: float
    radius: float = 1.2
    # World-truth affordance overrides (simulator plant only — never exposed to policy)
    chargeable: bool = True
    restable: bool = True
    inspectable: bool = True
    passable: bool = True
    occluded: bool = False


@dataclass
class Habitat:
    width: float = 20.0
    height: float = 20.0
    features: list[HabitatFeature] = field(default_factory=list)
    # D-003 world-intervention plant flags (truth — perception/governance only)
    blocked_cells: list[tuple[float, float, float]] = field(default_factory=list)  # x,y,r
    delayed_consequence_ticks: int = 0
    misleading_correlation: bool = False

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
                }
                for f in self.features
            ],
            "blocked_cells": [list(c) for c in self.blocked_cells],
            "delayed_consequence_ticks": self.delayed_consequence_ticks,
            "misleading_correlation": self.misleading_correlation,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> Habitat:
        feats = [
            HabitatFeature(
                kind=f["kind"],
                x=float(f["x"]),
                y=float(f["y"]),
                radius=float(f.get("radius", 1.2)),
                chargeable=bool(f.get("chargeable", True)),
                restable=bool(f.get("restable", True)),
                inspectable=bool(f.get("inspectable", True)),
                passable=bool(f.get("passable", True)),
                occluded=bool(f.get("occluded", False)),
            )
            for f in d.get("features", [])
        ]
        blocked = [tuple(float(x) for x in c) for c in d.get("blocked_cells", [])]
        return cls(
            width=float(d.get("width", 20.0)),
            height=float(d.get("height", 20.0)),
            features=feats,
            blocked_cells=blocked,  # type: ignore[arg-type]
            delayed_consequence_ticks=int(d.get("delayed_consequence_ticks", 0)),
            misleading_correlation=bool(d.get("misleading_correlation", False)),
        )


@dataclass
class Body:
    x: float = 5.0
    y: float = 5.0
    heading: float = 0.0
    velocity: float = 0.0
    sensor_range: float = 10.0
    movement_reliability: float = 0.95
    # D-002 physical plant params (world truth — self-model learns beliefs separately)
    movement_gain: float = 1.0
    turning_gain: float = 1.0
    actuator_delay: float = 0.0  # ticks of delay before motion applies
    body_radius: float = 0.0
    energy_cost_scale: float = 1.0

    def to_state(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "heading": self.heading,
            "velocity": self.velocity,
            "sensor_range": self.sensor_range,
            "movement_reliability": self.movement_reliability,
            "movement_gain": self.movement_gain,
            "turning_gain": self.turning_gain,
            "actuator_delay": self.actuator_delay,
            "body_radius": self.body_radius,
            "energy_cost_scale": self.energy_cost_scale,
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
    """Owns world truth + body. Exposes only observations via Perception.

    Body adapter may report observations/raw results but cannot certify
    attribution or verify outcomes (governance owns verification).
    """

    habitat: Habitat = field(default_factory=Habitat.default)
    body: Body = field(default_factory=Body)
    last_raw: dict[str, Any] = field(default_factory=dict)
    _pending_actuation: dict[str, Any] | None = field(default=None, repr=False)
    _delay_remaining: int = 0

    def world_truth(self) -> dict[str, Any]:
        """Authority-only — must not be passed to policy/arbitration."""
        return {
            "body": self.body.to_state(),
            "habitat": self.habitat.to_state(),
        }

    def apply_intervention(self, code: str) -> None:
        """D-002 body-plant interventions I0–I11 (world truth — self-model learns separately)."""
        b = self.body
        if code == "I0":
            return
        if code == "I1":
            b.movement_gain = 0.45
        elif code == "I2":
            b.turning_gain = 1.8
        elif code == "I3":
            b.actuator_delay = 2.0
        elif code == "I4":
            b.movement_reliability = 0.55
        elif code == "I5":
            b.sensor_range = 4.0
        elif code == "I6":
            b.body_radius = 1.6
        elif code == "I7":
            b.energy_cost_scale = 2.2
        elif code == "I8":
            # external displacement applied by runtime; plant unchanged
            return
        elif code == "I9":
            b.movement_reliability = 0.4
            b.movement_gain = 0.5
        elif code == "I10":
            # compatible replacement — reset to healthy defaults under new plant
            b.movement_gain = 1.0
            b.turning_gain = 1.0
            b.actuator_delay = 0.0
            b.sensor_range = 10.0
            b.movement_reliability = 0.95
            b.body_radius = 0.5
            b.energy_cost_scale = 1.0
        elif code == "I11":
            b.movement_gain = 0.55
            b.sensor_range = 5.0
            b.movement_reliability = 0.7
            b.body_radius = 0.8
            b.energy_cost_scale = 1.4
        else:
            raise ValueError(f"unknown_intervention:{code}")

    def apply_world_intervention(self, code: str) -> None:
        """D-003 environment interventions I0–I10 (habitat plant only)."""
        h = self.habitat
        if code == "I0":
            return
        if code == "I1":
            h.relocate("resource", 4.0, 16.0)
        elif code == "I2":
            h.relocate("hazard", 6.0, 6.0)
        elif code == "I3":
            # temporary occlusion — runtime clears after tick window
            feat = h.feature("inspect")
            if feat:
                feat.occluded = True
        elif code == "I4":
            h.delayed_consequence_ticks = 3
            self.body.actuator_delay = max(self.body.actuator_delay, 2.0)
        elif code == "I5":
            # misleading: resource appears near hazard (correlation trap)
            h.misleading_correlation = True
            h.relocate("resource", 14.5, 14.5)
            h.relocate("hazard", 15.0, 15.0)
        elif code == "I6":
            # affordance change: resource no longer charges
            feat = h.feature("resource")
            if feat:
                feat.chargeable = False
        elif code == "I7":
            # block a route near center
            h.blocked_cells.append((10.0, 8.0, 1.8))
            for f in h.features:
                if f.kind == "open":
                    f.passable = False
        elif code == "I8":
            # external object movement applied by runtime mid-episode
            return
        elif code == "I9":
            # novel object with familiar charge affordance
            h.features.append(
                HabitatFeature("novel_crystal", 12.0, 4.0, 1.6, chargeable=True)
            )
        elif code == "I10":
            # familiar resource now harms / no longer charges
            feat = h.feature("resource")
            if feat:
                feat.chargeable = False
                feat.kind = "resource"  # same label, changed affordance
                # treat contact like mild hazard via chargeable=False + integrity hit in execute
        else:
            raise ValueError(f"unknown_world_intervention:{code}")

    def move_feature_external(self, kind: str, x: float, y: float) -> None:
        """I8: external object relocation (not self-caused)."""
        self.habitat.relocate(kind, x, y)

    def set_occlusion(self, kind: str, occluded: bool) -> None:
        feat = self.habitat.feature(kind)
        if feat:
            feat.occluded = occluded

    def recover_from_fault(self) -> None:
        """I9 recovery — restore nominal plant after temporary fault."""
        b = self.body
        b.movement_reliability = 0.95
        b.movement_gain = 1.0

    def displace_external(self, dx: float, dy: float) -> None:
        self.body.x += dx
        self.body.y += dy
        self.clamp_body()

    def clamp_body(self) -> None:
        # Body radius shrinks effective habitat slightly (collision with walls)
        r = self.body.body_radius
        self.body.x = clamp(self.body.x, r, self.habitat.width - r)
        self.body.y = clamp(self.body.y, r, self.habitat.height - r)
        self.body.heading = (self.body.heading + math.pi) % (2 * math.pi) - math.pi

    def execute_primitive(
        self,
        capability: str,
        params: dict[str, Any],
        rng: SeededRNG,
    ) -> dict[str, Any]:
        """Execute authorized capability against world. Returns raw result (unverified)."""
        b = self.body
        # Actuator delay: queue motion and apply when delay elapses
        if b.actuator_delay >= 1.0 and capability in ("MOVE", "APPROACH", "RETREAT", "ORIENT"):
            if self._pending_actuation is None:
                self._pending_actuation = {"capability": capability, "params": dict(params)}
                self._delay_remaining = int(b.actuator_delay)
                detail = {
                    "capability": capability,
                    "params": dict(params),
                    "ok_raw": True,
                    "reason": "delayed",
                    "delayed": True,
                    "body_after": self.body.to_state(),
                }
                self.last_raw = detail
                return detail
        return self._apply_primitive(capability, params, rng)

    def tick_actuation(self, rng: SeededRNG) -> dict[str, Any] | None:
        """Advance delayed actuation; returns raw result when executed."""
        if self._pending_actuation is None:
            return None
        self._delay_remaining -= 1
        if self._delay_remaining > 0:
            return None
        pending = self._pending_actuation
        self._pending_actuation = None
        return self._apply_primitive(pending["capability"], pending["params"], rng)

    def _apply_primitive(
        self,
        capability: str,
        params: dict[str, Any],
        rng: SeededRNG,
    ) -> dict[str, Any]:
        b = self.body
        h = self.habitat
        ok = True
        reason = "ok"
        detail: dict[str, Any] = {"capability": capability, "params": dict(params)}

        if capability == "IDLE":
            b.velocity = 0.0
        elif capability == "ORIENT":
            target = float(params.get("heading", b.heading))
            if b.turning_gain != 1.0:
                b.heading = b.heading + angle_diff(target, b.heading) * b.turning_gain
            else:
                b.heading = target
            b.velocity = 0.0
            self.clamp_body()
        elif capability in ("MOVE", "APPROACH", "RETREAT"):
            step = float(params.get("step", 1.0 if capability != "RETREAT" else 1.2))
            heading = float(params.get("heading", b.heading))
            if capability == "RETREAT":
                heading = heading + math.pi
            if b.turning_gain != 1.0:
                heading = b.heading + angle_diff(heading, b.heading) * b.turning_gain
            step *= b.movement_gain
            if rng.random() > b.movement_reliability:
                ok = False
                reason = "movement_slip"
                step *= 0.3
                heading += rng.uniform(-0.4, 0.4)
            b.heading = heading
            nx = b.x + math.cos(heading) * step
            ny = b.y + math.sin(heading) * step
            # I7 blocked route
            blocked = False
            for bx, by, br in h.blocked_cells:
                if math.hypot(nx - bx, ny - by) <= br:
                    blocked = True
                    break
            if blocked:
                ok = False
                reason = "route_blocked"
                step *= 0.05
            b.x += math.cos(heading) * step
            b.y += math.sin(heading) * step
            b.velocity = step
            self.clamp_body()
            # hazard contact uses body radius
            haz, hd = h.nearest("hazard", b.x, b.y)
            if haz and hd <= haz.radius + b.body_radius * 0.5:
                detail["hazard_contact"] = True
            toward = params.get("toward")
            if toward and capability == "APPROACH":
                feat, d = h.nearest(toward if toward != "hazard" else "hazard", b.x, b.y)
                if feat and d <= feat.radius + b.body_radius * 0.3:
                    detail["arrived"] = True
        elif capability == "INSPECT":
            feat, d = h.nearest("inspect", b.x, b.y)
            if feat is None or d > feat.radius + 0.8 or not feat.inspectable:
                ok = False
                reason = "out_of_range"
            else:
                detail["inspected"] = True
                detail["object_kind"] = "inspect"
        elif capability == "REST":
            feat, d = h.nearest("rest", b.x, b.y)
            if feat is None or d > feat.radius + 0.3 or not feat.restable:
                ok = False
                reason = "not_at_rest"
            else:
                b.velocity = 0.0
                detail["rested"] = True
        elif capability == "CHARGE":
            # resource or novel chargeable kinds
            feat = None
            d = float("inf")
            for kind in ("resource", "novel_crystal"):
                f, dd = h.nearest(kind, b.x, b.y)
                if f is not None and dd < d:
                    feat, d = f, dd
            if feat is None or d > feat.radius + 0.3:
                ok = False
                reason = "not_at_resource"
            elif not feat.chargeable:
                ok = False
                reason = "affordance_denied"
                detail["false_affordance"] = True
                # I10: familiar object changed — mild integrity hit
                detail["integrity_hit"] = 0.05
            else:
                b.velocity = 0.0
                detail["charged"] = True
                detail["object_kind"] = feat.kind
        else:
            ok = False
            reason = "unknown_capability"

        detail["ok_raw"] = ok
        detail["reason"] = reason
        detail["body_after"] = self.body.to_state()
        detail["energy_cost_scale"] = b.energy_cost_scale
        # Body adapter reports only — does not certify attribution/verification
        detail["adapter_certified"] = False
        self.last_raw = detail
        return detail

    def to_state(self) -> dict[str, Any]:
        return {
            "habitat": self.habitat.to_state(),
            "body": self.body.to_state(),
            "pending_actuation": self._pending_actuation,
            "delay_remaining": self._delay_remaining,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> Embodiment:
        emb = cls(
            habitat=Habitat.from_state(d.get("habitat", {})),
            body=Body.from_state(d.get("body", {})),
        )
        emb._pending_actuation = d.get("pending_actuation")
        emb._delay_remaining = int(d.get("delay_remaining", 0))
        return emb
