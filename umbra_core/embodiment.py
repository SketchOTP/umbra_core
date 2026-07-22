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
    "SIGNAL_PLAY",
    "SIGNAL_ASSISTANCE",
)


# Identity-basis parameters for PartnerTrueCues.for_history. Amplitude 0.40 keeps
# 0.5 ± amp inside [0.10, 0.90], leaving headroom for perception noise without
# clamp-saturating the true cue. 9 direct cue dims: motion(3)+appearance(3)+
# interaction(3); timing is excluded (it is /32-rescaled and shared across partners).
_IDENT_AMPLITUDE = 0.40
_AMBIGUOUS_IDENT_AMPLITUDE = 0.02
_IDENT_DIMS = 9
# Fixed +/-1 base direction; index 0 and 1 (the only multi-partner histories, H8/H9)
# are made antipodal so their noise-free cue distance (~0.69) clears the recognition
# threshold (0.55) with wide margin. Higher indices rotate the phase (unused today).
_IDENT_BASE = (1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0)


def _identity_offsets(index: int, amplitude: float) -> list[float]:
    """Per-index offset vector over the 9 direct cue dims. Even/odd indices flip the
    base direction (antipodal 0 vs 1) for maximal separation; index//2 adds a phase
    rotation so any further partners stay distinct. Fixed per-dim magnitude keeps the
    inter-partner distance above the perception-noise floor instead of swamped by it."""
    sign = 1.0 if index % 2 == 0 else -1.0
    rot = index // 2
    return [
        amplitude * sign * _IDENT_BASE[d] * math.cos(math.pi * rot * (d + 1) / _IDENT_DIMS)
        for d in range(_IDENT_DIMS)
    ]


def _band(offset: float, tilt: float) -> float:
    """Center a cue dim at 0.5 (+ history tilt) and apply the identity offset,
    kept strictly inside (0,1) so both separation and noise survive the [0,1] clamp."""
    return clamp(0.5 + tilt + offset, 0.02, 0.98)


@dataclass
class PartnerTrueCues:
    motion_signature: tuple[float, ...]
    appearance_signature: tuple[float, ...]
    response_timing_pattern: tuple[float, ...]
    interaction_style_cues: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "motion_signature": list(self.motion_signature),
            "appearance_signature": list(self.appearance_signature),
            "response_timing_pattern": list(self.response_timing_pattern),
            "interaction_style_cues": list(self.interaction_style_cues),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PartnerTrueCues:
        return cls(
            motion_signature=tuple(float(x) for x in d["motion_signature"]),
            appearance_signature=tuple(float(x) for x in d["appearance_signature"]),
            response_timing_pattern=tuple(float(x) for x in d["response_timing_pattern"]),
            interaction_style_cues=tuple(float(x) for x in d["interaction_style_cues"]),
        )

    @classmethod
    def for_history(cls, history_code: str, *, index: int = 0, ambiguous: bool = False) -> PartnerTrueCues:
        h = int(history_code[1:]) if history_code[1:].isdigit() else 0
        # Identity separation lives in a near-orthogonal, index-keyed basis spread
        # across the 9 direct cue dims (motion/appearance/interaction). The old ~0.17
        # scalar salt was smaller than PerceptionMembrane noise (sigma≈0.33), so two
        # distinct partners collapsed into one hypothesis through the real perception
        # path. A full-amplitude orthogonal basis keeps inter-partner cue distance
        # above the noise floor. Ambiguous histories (H9) deliberately keep a tiny
        # amplitude so partners genuinely collapse/contest and stay UNKNOWN.
        # (response_timing_pattern stays tick-scaled and index-independent; it is
        # rescaled by /32 in perception, so identity separation would be swamped there.)
        amp = _AMBIGUOUS_IDENT_AMPLITUDE if ambiguous else _IDENT_AMPLITUDE
        off = _identity_offsets(index, amp)
        hb = (h % 7) * 0.02  # mild per-history tilt so single-partner histories differ
        return cls(
            motion_signature=(_band(off[0], hb), _band(off[1], hb), _band(off[2], hb)),
            appearance_signature=(_band(off[3], hb), _band(off[4], hb), _band(off[5], hb)),
            response_timing_pattern=(2.0 + h * 0.2, 5.0, 1.0),
            interaction_style_cues=(_band(off[6], hb), _band(off[7], hb), _band(off[8], hb)),
        )


@dataclass
class PartnerResponsePolicy:
    """Stub response policy for social history plants H0–H10 (SocialEngine comes later)."""

    history_code: str
    mode: str = "contingent"
    contingent_probability: float = 0.85
    flip_at: float | None = None
    absent_windows: list[tuple[float, float]] = field(default_factory=list)

    def should_respond(self, signal: str, now: float, rng: SeededRNG) -> bool:
        if self.mode == "noncontingent":
            return rng.random() < 0.5
        if self.mode == "unreliable":
            return rng.random() < 0.3
        if self.mode == "assistance":
            return signal == "SIGNAL_ASSISTANCE" and rng.random() < 0.9
        if self.mode == "interference":
            return signal in ("SIGNAL_PLAY", "SIGNAL_ASSISTANCE") and rng.random() < 0.7
        if self.mode == "flip":
            p = 0.85 if (self.flip_at is None or now < self.flip_at) else 0.25
            return signal in ("SIGNAL_PLAY", "SIGNAL_ASSISTANCE") and rng.random() < p
        if self.mode == "flip_up":
            p = 0.25 if (self.flip_at is None or now < self.flip_at) else 0.85
            return signal in ("SIGNAL_PLAY", "SIGNAL_ASSISTANCE") and rng.random() < p
        if self.mode == "routine":
            return signal == "SIGNAL_PLAY" and rng.random() < 0.9
        # contingent default
        return signal in ("SIGNAL_PLAY", "SIGNAL_ASSISTANCE") and rng.random() < self.contingent_probability

    def response_delay_ticks(self, now: float, rng: SeededRNG) -> int:
        if self.mode == "routine":
            return 3
        return max(1, int(rng.uniform(1.0, 6.0)))


def response_policy_for_history(history_code: str) -> PartnerResponsePolicy:
    """Factory for H0–H10 partner response policies (evaluator/experiment plant)."""
    modes: dict[str, tuple[str, dict[str, Any]]] = {
        "H0": ("contingent", {}),
        "H1": ("noncontingent", {}),
        "H2": ("unreliable", {}),
        "H3": ("assistance", {}),
        "H4": ("interference", {}),
        "H5": ("flip", {"flip_at": 50.0}),
        "H6": ("flip_up", {"flip_at": 50.0}),
        "H7": ("contingent", {"absent_windows": [(20.0, 40.0)]}),
        "H8": ("contingent", {}),
        "H9": ("contingent", {}),
        "H10": ("routine", {}),
    }
    if history_code not in modes:
        raise ValueError(f"unknown_social_history:{history_code}")
    mode, extra = modes[history_code]
    return PartnerResponsePolicy(history_code=history_code, mode=mode, **extra)


@dataclass
class PartnerEntity:
    hidden_partner_id: str
    x: float
    y: float
    true_cues: PartnerTrueCues
    response_policy: PartnerResponsePolicy
    active: bool = True

    def is_visible(self, now: float) -> bool:
        if not self.active:
            return False
        for start, end in self.response_policy.absent_windows:
            if start <= now < end:
                return False
        return True

    def to_state(self) -> dict[str, Any]:
        return {
            "hidden_partner_id": self.hidden_partner_id,
            "x": self.x,
            "y": self.y,
            "true_cues": self.true_cues.to_dict(),
            "response_policy": {
                "history_code": self.response_policy.history_code,
                "mode": self.response_policy.mode,
                "contingent_probability": self.response_policy.contingent_probability,
                "flip_at": self.response_policy.flip_at,
                "absent_windows": [list(w) for w in self.response_policy.absent_windows],
            },
            "active": self.active,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> PartnerEntity:
        rp = d["response_policy"]
        windows = [tuple(float(x) for x in w) for w in rp.get("absent_windows", [])]
        policy = PartnerResponsePolicy(
            history_code=str(rp["history_code"]),
            mode=str(rp.get("mode", "contingent")),
            contingent_probability=float(rp.get("contingent_probability", 0.85)),
            flip_at=float(rp["flip_at"]) if rp.get("flip_at") is not None else None,
            absent_windows=windows,  # type: ignore[arg-type]
        )
        return cls(
            hidden_partner_id=str(d["hidden_partner_id"]),
            x=float(d["x"]),
            y=float(d["y"]),
            true_cues=PartnerTrueCues.from_dict(d["true_cues"]),
            response_policy=policy,
            active=bool(d.get("active", True)),
        )


def _partner_salt(partner_id: str) -> int:
    return sum(ord(c) for c in partner_id) & 0xFFFFFFFF


def _make_partner(
    partner_id: str,
    x: float,
    y: float,
    history_code: str,
    *,
    index: int = 0,
    ambiguous: bool = False,
    policy: PartnerResponsePolicy | None = None,
) -> PartnerEntity:
    return PartnerEntity(
        hidden_partner_id=partner_id,
        x=x,
        y=y,
        true_cues=PartnerTrueCues.for_history(history_code, index=index, ambiguous=ambiguous),
        response_policy=policy or response_policy_for_history(history_code),
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
    partners: list[PartnerEntity] = field(default_factory=list)
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
            "partners": [p.to_state() for p in self.partners],
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
        partners = [PartnerEntity.from_state(p) for p in d.get("partners", [])]
        return cls(
            width=float(d.get("width", 20.0)),
            height=float(d.get("height", 20.0)),
            features=feats,
            blocked_cells=blocked,  # type: ignore[arg-type]
            delayed_consequence_ticks=int(d.get("delayed_consequence_ticks", 0)),
            misleading_correlation=bool(d.get("misleading_correlation", False)),
            partners=partners,
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

    def apply_development_intervention(self, code: str) -> dict[str, Any]:
        """D-004 practice-environment plant (habitat/body truth — not policy-visible as truth)."""
        h = self.habitat
        tags: dict[str, Any] = {"code": code}
        if code == "I0":
            tags["stable"] = True
            # Ambient distractors present in stable world — LP should ignore; ablations waste effort
            tags["impossible"] = True
            tags["noisy_distractor"] = True
            h.features.append(
                HabitatFeature("impossible_node", 8.0, 18.0, 1.2, chargeable=False)
            )
            h.features.append(
                HabitatFeature("noise_blink", 5.0, 12.0, 1.0, inspectable=True)
            )
        elif code == "I1":
            tags["hard_mix"] = True
            # Add a distant hard-to-reach charge target (same affordance, higher difficulty)
            if h.feature("resource") is None:
                h.features.append(HabitatFeature("resource", 17.0, 3.0, 1.8))
            h.features.append(
                HabitatFeature("resource", 1.0, 18.0, 1.2, chargeable=True)
            )
        elif code == "I2":
            tags["impossible"] = True
            # Non-chargeable decoy — practice toward it never succeeds as charge
            h.features.append(
                HabitatFeature("impossible_node", 8.0, 18.0, 1.2, chargeable=False)
            )
        elif code == "I3":
            tags["noisy_distractor"] = True
            h.features.append(
                HabitatFeature("noise_blink", 5.0, 12.0, 1.0, inspectable=True)
            )
        elif code == "I4":
            tags["mastered_seed"] = True
        elif code == "I5":
            tags["degrade_at"] = 80
        elif code == "I6":
            tags["body_change_at"] = 60
            self.body.movement_gain = 0.55
            self.body.movement_reliability = 0.55
        elif code == "I7":
            tags["env_change_at"] = 70
            feat = h.feature("resource")
            if feat:
                feat.chargeable = False
        elif code == "I8":
            tags["resource_scarce"] = True
            # Shrink / remove easy resource access
            feat = h.feature("resource")
            if feat:
                feat.radius = 0.6
                h.relocate("resource", 19.0, 19.0)
        elif code == "I9":
            tags["no_user"] = True
        elif code == "I10":
            tags["novel_familiar"] = True
            h.features.append(
                HabitatFeature("novel_crystal", 12.0, 4.0, 1.6, chargeable=True)
            )
        else:
            raise ValueError(f"unknown_development_intervention:{code}")
        return tags

    def apply_memory_history(self, code: str) -> dict[str, Any]:
        """D-005 history plant H0–H9 (habitat/body truth — not narrative)."""
        h = self.habitat
        tags: dict[str, Any] = {"code": code, "rule_tag": "default", "body_compatibility": 1.0}
        if code == "H0":
            tags["repeated_success"] = True
            tags["force_consolidate_every"] = 12
        elif code == "H1":
            tags["repeated_fail"] = True
            feat = h.feature("resource")
            if feat:
                feat.chargeable = False
            tags["force_consolidate_every"] = 12
        elif code == "H2":
            tags["conflicting"] = True
            tags["rule_flip_at"] = 40
            tags["force_consolidate_every"] = 10
        elif code == "H3":
            tags["rare_high"] = True
            # Strong hazard near start — rare consequential contact
            h.features.append(HabitatFeature("hazard", 10.5, 10.5, 2.5))
            tags["force_consolidate_every"] = 15
        elif code == "H4":
            tags["frequent_low"] = True
            tags["force_consolidate_every"] = 8
            tags["force_low_value_every"] = 2
        elif code == "H5":
            tags["rule_change"] = True
            tags["rule_flip_at"] = 50
            tags["force_consolidate_every"] = 10
        elif code == "H6":
            tags["body_incompatible"] = True
            tags["body_change_at"] = 45
            tags["force_consolidate_every"] = 12
        elif code == "H7":
            tags["skill_degrade"] = True
            tags["skill_degrade_at"] = 55
            tags["force_consolidate_every"] = 10
        elif code == "H8":
            tags["misleading"] = True
            h.features.append(
                HabitatFeature("spurious_blink", 6.0, 14.0, 1.0, inspectable=True)
            )
            tags["force_consolidate_every"] = 12
        elif code == "H9":
            tags["unobserved"] = True
            tags["force_consolidate_every"] = 20
        else:
            raise ValueError(f"unknown_memory_history:{code}")
        return tags

    def apply_social_history(self, code: str) -> dict[str, Any]:
        """D-006 social history plant H0–H10 (habitat partner truth — not policy-visible)."""
        h = self.habitat
        tags: dict[str, Any] = {"code": code}
        partners: list[PartnerEntity] = []
        if code == "H0":
            partners.append(_make_partner("p-h0", 12.0, 8.0, code))
        elif code == "H1":
            partners.append(_make_partner("p-h1", 12.0, 8.0, code))
        elif code == "H2":
            partners.append(_make_partner("p-h2", 12.0, 8.0, code))
        elif code == "H3":
            partners.append(_make_partner("p-h3", 12.0, 8.0, code))
        elif code == "H4":
            partners.append(_make_partner("p-h4", 12.0, 8.0, code))
        elif code == "H5":
            partners.append(_make_partner("p-h5", 12.0, 8.0, code))
        elif code == "H6":
            partners.append(_make_partner("p-h6", 12.0, 8.0, code))
        elif code == "H7":
            partners.append(_make_partner("p-h7", 12.0, 8.0, code))
        elif code == "H8":
            partners.append(_make_partner("p-h8-a", 11.0, 8.0, code, index=0))
            partners.append(_make_partner("p-h8-b", 13.0, 7.0, code, index=1))
            tags["swap_at"] = 80.0
        elif code == "H9":
            partners.append(_make_partner("p-h9-a", 11.5, 8.0, code, index=0, ambiguous=True))
            partners.append(_make_partner("p-h9-b", 12.5, 8.0, code, index=1, ambiguous=True))
            tags["ambiguous_cues"] = True
        elif code == "H10":
            partners.append(_make_partner("p-h10", 12.0, 8.0, code))
            tags["routine_training"] = True
        else:
            raise ValueError(f"unknown_social_history:{code}")
        h.partners = partners
        return tags

    def apply_individuality_history(self, code: str) -> dict[str, Any]:
        """D-007 individuality history plant H0–H12.

        Alters opportunities and verified-consequence contexts only.
        Never sets personality labels or forces internal disposition values.
        """
        h = self.habitat
        tags: dict[str, Any] = {
            "code": code,
            "learning_context": "default",
            "arbitration_context": "default",
        }
        if code == "H0":
            tags["learning_context"] = "safe_explore"
            tags["arbitration_context"] = "safe_explore"
        elif code == "H1":
            tags["learning_context"] = "safe_explore"
            tags["arbitration_context"] = "safe_explore"
            tags["explore_rewarding"] = True
            # Extra inspectable novelty that charges successfully
            h.features.append(
                HabitatFeature("novel_crystal", 14.0, 12.0, 1.2, chargeable=True, inspectable=True)
            )
        elif code == "H2":
            tags["learning_context"] = "uncertain_hazard"
            tags["arbitration_context"] = "uncertain_hazard"
            tags["explore_punishing"] = True
            h.features.append(HabitatFeature("hazard", 11.0, 11.0, 2.0))
            # Spurious inspect that looks novel but is near hazard
            h.features.append(
                HabitatFeature("novel_crystal", 10.5, 10.5, 1.0, inspectable=True)
            )
        elif code == "H3":
            tags["learning_context"] = "solvable_task"
            tags["arbitration_context"] = "solvable_task"
            tags["persistence_rewarded"] = True
            h.features.append(
                HabitatFeature("inspect", 13.0, 9.0, 1.0, inspectable=True, chargeable=True)
            )
        elif code == "H4":
            tags["learning_context"] = "solvable_task"
            tags["arbitration_context"] = "solvable_task"
            tags["persistence_futile"] = True
            # Non-chargeable inspect — effort unproductive
            h.features.append(
                HabitatFeature("inspect", 13.0, 9.0, 1.0, inspectable=True, chargeable=False)
            )
            feat = h.feature("resource")
            if feat:
                feat.chargeable = False
        elif code == "H5":
            tags["learning_context"] = "high_stim"
            tags["arbitration_context"] = "high_stim"
            tags["stim_rewarding"] = True
            h.features.append(
                HabitatFeature("inspect", 8.0, 14.0, 1.5, inspectable=True)
            )
            h.features.append(
                HabitatFeature("inspect", 15.0, 8.0, 1.5, inspectable=True)
            )
        elif code == "H6":
            tags["learning_context"] = "post_stim_recovery"
            tags["arbitration_context"] = "high_stim"
            tags["stim_overstimulating"] = True
            tags["force_context"] = "post_stim_recovery"
            h.features.append(
                HabitatFeature("inspect", 9.0, 9.0, 2.5, inspectable=True)
            )
        elif code == "H7":
            tags["learning_context"] = "object_family_a"
            tags["arbitration_context"] = "object_family_a"
            tags["force_context"] = "object_family_a"
            tags["specialization"] = "A"
            # Use inspectable chargeable target — policy sees inspect/novel, learning uses family A
            h.features.append(
                HabitatFeature("inspect", 12.0, 14.0, 1.2, inspectable=True, chargeable=True)
            )
        elif code == "H8":
            tags["learning_context"] = "object_family_b"
            tags["arbitration_context"] = "object_family_b"
            tags["force_context"] = "object_family_b"
            tags["specialization"] = "B"
            h.features.append(
                HabitatFeature(
                    "novel_crystal", 14.0, 12.0, 1.2, inspectable=True, chargeable=True
                )
            )
        elif code == "H9":
            tags["learning_context"] = "play_context"
            tags["arbitration_context"] = "play_context"
            tags["social_reliable"] = True
            # Reuse social partner plant for reliable play
            self.apply_social_history("H0")
        elif code == "H10":
            tags["learning_context"] = "play_context"
            tags["arbitration_context"] = "play_context"
            tags["social_unreliable"] = True
            self.apply_social_history("H2")
        elif code == "H11":
            tags["learning_context"] = "routine_window"
            tags["arbitration_context"] = "diurnal_phase"
            tags["timing_phase"] = True
            tags["force_context"] = "routine_window"
        elif code == "H12":
            tags["learning_context"] = "safe_explore"
            tags["arbitration_context"] = "safe_explore"
            tags["reversal"] = True
            tags["rule_flip_at"] = 80
            h.features.append(
                HabitatFeature("novel_crystal", 14.0, 12.0, 1.2, chargeable=True, inspectable=True)
            )
        else:
            raise ValueError(f"unknown_individuality_history:{code}")
        return tags

    def hidden_partner_truth_for_eval(self) -> list[dict[str, Any]]:
        """Evaluator-only accessor — never pass to policy, SocialEngine, or arbitration."""
        return [
            {
                "partner_id": p.hidden_partner_id,
                "x": p.x,
                "y": p.y,
                "history": p.response_policy.history_code,
                "true_cues": p.true_cues.to_dict(),
            }
            for p in self.habitat.partners
        ]

    def plant_partner(self, partner: PartnerEntity) -> None:
        self.habitat.partners.append(partner)

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
            toward = params.get("toward", "inspect")
            kind = toward if toward in ("inspect", "noise_blink") else "inspect"
            feat, d = h.nearest(kind, b.x, b.y)
            if feat is None or d > feat.radius + 0.8 or not feat.inspectable:
                ok = False
                reason = "out_of_range"
            elif kind == "noise_blink":
                # Irreducible stochastic distractor — ~50% regardless of skill
                ok = rng.random() < 0.5
                reason = "ok" if ok else "noise_fail"
                detail["object_kind"] = "noise_blink"
                detail["irreducible_noise"] = True
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
        elif capability in ("SIGNAL_PLAY", "SIGNAL_ASSISTANCE"):
            b.velocity = 0.0
            detail["environmental_event"] = {
                "kind": "social_signal",
                "signal": capability,
                "tick": int(params.get("tick", 0)),
            }
        elif capability == "CHARGE":
            # resource or novel chargeable kinds (impossible_node never charges)
            toward = params.get("toward")
            if toward == "impossible_node":
                ok = False
                reason = "impossible_target"
                detail["object_kind"] = "impossible_node"
            else:
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
