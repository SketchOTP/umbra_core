"""Perception membrane — observations only; no world truth to policy."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from umbra_core.embodiment import Embodiment, HabitatFeature
from umbra_core.util import SeededRNG, angle_diff, clamp, sha256_hex


@dataclass
class Observation:
    observation_id: str
    kind: str
    relative_direction: float
    estimated_distance: float
    confidence: float
    uncertainty: float
    observed_at: float
    expires_at: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "kind": self.kind,
            "relative_direction": self.relative_direction,
            "estimated_distance": self.estimated_distance,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Observation:
        return cls(**d)


@dataclass
class PerceptionMembrane:
    """Converts world truth → uncertain observations. Policy reads only this."""

    observations: list[Observation] = field(default_factory=list)
    false_negative_rate: float = 0.08
    noise_sigma: float = 0.25
    expire_ttl: float = 12.0
    # experiment flag C6: leak exact truth (ablation — must underperform / be gated)
    leak_world_truth: bool = False
    _leaked_truth: dict[str, Any] | None = None

    def clear_expired(self, now: float) -> None:
        self.observations = [o for o in self.observations if o.expires_at > now]

    def perceive(
        self,
        embodiment: Embodiment,
        now: float,
        rng: SeededRNG,
    ) -> list[Observation]:
        self.clear_expired(now)
        body = embodiment.body
        new_obs: list[Observation] = []

        if self.leak_world_truth:
            # Ablation C6 — exact coordinates (forbidden in normal operation)
            self._leaked_truth = embodiment.world_truth()
        else:
            self._leaked_truth = None

        for feat in embodiment.habitat.features:
            if feat.occluded:
                continue
            d = body.dist_to(feat.x, feat.y)
            if d > body.sensor_range:
                continue
            # false negative
            if rng.random() < self.false_negative_rate:
                continue
            bearing = body.bearing_to(feat.x, feat.y)
            rel = angle_diff(bearing, body.heading)
            est_d = max(0.1, d + rng.gauss(0.0, self.noise_sigma))
            # noise on direction
            rel_n = rel + rng.gauss(0.0, 0.15)
            conf = clamp(1.0 - (d / body.sensor_range) * 0.6 - abs(rng.gauss(0, 0.05)))
            unc = clamp(1.0 - conf)
            oid = sha256_hex(f"obs:{now:.6f}:{feat.kind}:{est_d:.5f}:{rel_n:.5f}")[:32]
            oid = f"{oid[:8]}-{oid[8:12]}-{oid[12:16]}-{oid[16:20]}-{oid[20:32]}"
            obs = Observation(
                observation_id=oid,
                kind=feat.kind,
                relative_direction=rel_n,
                estimated_distance=est_d,
                confidence=conf,
                uncertainty=unc,
                observed_at=now,
                expires_at=now + self.expire_ttl,
                source="sensor",
            )
            new_obs.append(obs)

        # merge: replace same kind with fresher
        by_kind = {o.kind: o for o in self.observations}
        for o in new_obs:
            by_kind[o.kind] = o
        self.observations = list(by_kind.values())
        return list(self.observations)

    def policy_view(self) -> dict[str, Any]:
        """What arbitration/policy may see — never absolute world coords."""
        view: dict[str, Any] = {
            "observations": [o.to_dict() for o in self.observations],
        }
        if self.leak_world_truth and self._leaked_truth is not None:
            view["WORLD_TRUTH_LEAK"] = self._leaked_truth
        return view

    def to_state(self) -> dict[str, Any]:
        return {
            "observations": [o.to_dict() for o in self.observations],
            "false_negative_rate": self.false_negative_rate,
            "noise_sigma": self.noise_sigma,
            "expire_ttl": self.expire_ttl,
            "leak_world_truth": self.leak_world_truth,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> PerceptionMembrane:
        p = cls(
            false_negative_rate=float(d.get("false_negative_rate", 0.12)),
            noise_sigma=float(d.get("noise_sigma", 0.35)),
            expire_ttl=float(d.get("expire_ttl", 8.0)),
            leak_world_truth=bool(d.get("leak_world_truth", False)),
        )
        p.observations = [Observation.from_dict(o) for o in d.get("observations", [])]
        return p


def assert_no_world_truth(policy_input: dict[str, Any]) -> None:
    """Test/governance helper: policy bundle must not contain exact coords."""
    bad_keys = {"x", "y", "habitat", "world_truth", "WORLD_TRUTH_LEAK", "body"}
    flat = set(policy_input.keys())
    if flat & bad_keys:
        # WORLD_TRUTH_LEAK only allowed under explicit ablation flag checked by caller
        if "WORLD_TRUTH_LEAK" in flat:
            return
        raise AssertionError(f"policy_saw_world_truth:{flat & bad_keys}")
