"""Perception membrane — observations only; no world truth to policy."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from umbra_core.embodiment import Embodiment, HabitatFeature, PartnerEntity, _partner_salt
from umbra_core.util import SeededRNG, angle_diff, clamp, sha256_hex
from umbra_core.perception_adapters import AdapterManifest, ObservationEnvelope

if TYPE_CHECKING:
    from umbra_core.habitat.engine import HabitatEngine


@dataclass(frozen=True)
class ResolvedManipulationTarget:
    target_object_id: str
    target_object_version: int
    binding_hash: str


class ManipulationResolveError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ObjectAddressBinding:
    """Trusted binding — object_id must never appear in policy_view."""

    target_address_ref: str
    perception_evidence_ref: str
    perception_state_version: int
    binding_hash: str
    object_id: str
    object_version: int
    perceived_object_kind: str
    perceived_affordance_refs: tuple[str, ...]
    relative_direction: float
    estimated_distance: float


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
    # Unitful support supplied by the sensing boundary, not an error estimate.
    distance_support_upper_bound: float | None = None

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
            "distance_support_upper_bound": self.distance_support_upper_bound,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Observation:
        return cls(**d)


PARTNER_CUE_FIELDS = (
    "relative_position",
    "motion_signature",
    "appearance_signature",
    "response_timing_pattern",
    "interaction_style_cues",
    "cue_confidence",
    "cue_uncertainty",
)

# true_cues store timing in tick units; normalize before noisy clamp to [0,1]
_TIMING_CUE_SCALE = 32.0  # ponytail: max expected ticks from D-006 thresholds
# Identity-signature noise floor (see _noisy_partner_cue): below the ~0.69 antipodal
# inter-partner cue distance so distinct partners separate, above 0 so cues stay noisy.
_PARTNER_IDENTITY_NOISE_SIGMA = 0.14


@dataclass
class PerceptionMembrane:
    """Converts world truth → uncertain observations. Policy reads only this."""

    observations: list[Observation] = field(default_factory=list)
    partner_cues: list[dict[str, Any]] = field(default_factory=list)
    false_negative_rate: float = 0.08
    noise_sigma: float = 0.25
    expire_ttl: float = 12.0
    # experiment flag C6: leak exact truth (ablation — must underperform / be gated)
    leak_world_truth: bool = False
    _leaked_truth: dict[str, Any] | None = None
    object_bindings: list[ObjectAddressBinding] = field(default_factory=list)
    perception_state_version: int = 0
    adapter_observations: list[dict[str, Any]] = field(default_factory=list)
    accepted_adapter_observation_ids: list[str] = field(default_factory=list)
    rejected_adapter_observation_ids: list[str] = field(default_factory=list)

    def accept_adapter_observation(self, envelope: ObservationEnvelope, manifest: AdapterManifest) -> bool:
        """Validate before mutation; accepted envelopes contain derived data only."""
        envelope.validate(manifest)
        if envelope.observation_id in self.accepted_adapter_observation_ids:
            return False
        self.adapter_observations = (self.adapter_observations + [envelope.to_dict()])[-256:]
        self.accepted_adapter_observation_ids = (self.accepted_adapter_observation_ids + [envelope.observation_id])[-512:]
        return True

    def reject_adapter_observation(self, observation_id: str) -> None:
        if observation_id not in self.rejected_adapter_observation_ids:
            self.rejected_adapter_observation_ids = (self.rejected_adapter_observation_ids + [observation_id])[-512:]

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
                distance_support_upper_bound=(
                    float(body.sensor_range)
                    if math.isfinite(float(body.sensor_range)) and float(body.sensor_range) > 0.0
                    else None
                ),
            )
            new_obs.append(obs)

        # merge: replace same kind with fresher
        by_kind = {o.kind: o for o in self.observations}
        for o in new_obs:
            by_kind[o.kind] = o
        self.observations = list(by_kind.values())

        self.partner_cues = self._perceive_partners(embodiment, now, rng)
        self.perceive_habitat_objects(embodiment, now, rng)
        return list(self.observations)

    def perceive_habitat_objects(
        self,
        embodiment: Embodiment,
        now: float,
        rng: SeededRNG,
    ) -> list[ObjectAddressBinding]:
        """Trusted path: bind perceived habitat objects to address refs (no object_id to policy)."""
        engine = embodiment._habitat_engine
        if engine is None:
            self.object_bindings = []
            return []

        from umbra_core.habitat.migration import feature_kind_from_object
        from umbra_core.habitat.state import FreeLocation, HeldByLocation

        body = embodiment.body
        self.perception_state_version += 1
        version = self.perception_state_version
        new_bindings: list[ObjectAddressBinding] = []
        snapshot = engine.snapshot_view()

        for object_id in sorted(snapshot.objects):
            obj = snapshot.objects[object_id]
            if obj.visibility == "HIDDEN":
                continue
            if obj.occluded:
                continue
            if isinstance(obj.location, HeldByLocation):
                if obj.location.body_instance_id != embodiment._body_instance_id:
                    continue
                ox, oy = body.x, body.y
            elif isinstance(obj.location, FreeLocation):
                ox, oy = obj.location.x, obj.location.y
            else:
                continue

            dist = body.dist_to(ox, oy)
            if dist > body.sensor_range:
                continue
            if rng.random() < self.false_negative_rate:
                continue

            bearing = body.bearing_to(ox, oy)
            rel = angle_diff(bearing, body.heading)
            est_d = max(0.1, dist + rng.gauss(0.0, self.noise_sigma))
            rel_n = rel + rng.gauss(0.0, 0.15)
            kind = feature_kind_from_object(obj)
            address_ref = sha256_hex(f"addr:{kind}:{rel_n:.5f}:{est_d:.5f}")[:16]
            evidence_ref = sha256_hex(f"pe:{now:.6f}:{kind}:{rel_n:.5f}:{est_d:.5f}")[:32]
            binding_hash = sha256_hex(
                f"bind:{object_id}:{obj.object_version}:{version}"
            )
            new_bindings.append(
                ObjectAddressBinding(
                    target_address_ref=address_ref,
                    perception_evidence_ref=evidence_ref,
                    perception_state_version=version,
                    binding_hash=binding_hash,
                    object_id=object_id,
                    object_version=obj.object_version,
                    perceived_object_kind=kind,
                    perceived_affordance_refs=tuple(obj.affordance_ids),
                    relative_direction=rel_n,
                    estimated_distance=est_d,
                )
            )

        self.object_bindings = new_bindings
        return new_bindings

    def _perceive_partners(
        self,
        embodiment: Embodiment,
        now: float,
        rng: SeededRNG,
    ) -> list[dict[str, Any]]:
        body = embodiment.body
        cues: list[dict[str, Any]] = []
        for partner in embodiment.habitat.partners:
            cue = self._noisy_partner_cue(partner, body, now, rng)
            if cue is not None:
                cues.append(cue)
        return cues

    def _noisy_partner_cue(
        self,
        partner: PartnerEntity,
        body: Any,
        now: float,
        rng: SeededRNG,
    ) -> dict[str, Any] | None:
        if not partner.is_visible(now):
            return None
        d = body.dist_to(partner.x, partner.y)
        if d > body.sensor_range:
            return None
        prng = rng.fork(_partner_salt(partner.hidden_partner_id) ^ int(now * 1000))
        noise = self.noise_sigma + 0.08  # spatial (relative_position) noise
        # Identity-signature noise is deliberately smaller than the spatial noise:
        # motion/appearance/timing/interaction signatures are more stable/repeatable
        # than an instantaneous position estimate, and they must stay discriminative
        # so distinct partners do not collapse into one recognition hypothesis (and a
        # single partner does not false-split) through the real perception path. Cues
        # still always carry noise (never perfect), just below the inter-partner
        # cue-separation floor. ponytail: capped constant floor; upgrade path is a
        # per-cue-channel sigma if channels need independent reliability.
        id_noise = min(noise, _PARTNER_IDENTITY_NOISE_SIGMA)
        rel_x = (partner.x - body.x) + prng.gauss(0.0, noise)
        rel_y = (partner.y - body.y) + prng.gauss(0.0, noise)
        tc = partner.true_cues

        def noisy_vec(vec: tuple[float, ...], sigma: float = id_noise) -> list[float]:
            # ponytail: always add noise — no permanently unique perfect cues
            return [clamp(v + prng.gauss(0.0, sigma), 0.0, 1.0) for v in vec]

        def noisy_timing_vec(vec: tuple[float, ...], sigma: float = id_noise) -> list[float]:
            # true_cues in tick units; rescale to [0,1] before noise so cues stay discriminative
            return [
                clamp(v / _TIMING_CUE_SCALE + prng.gauss(0.0, sigma), 0.0, 1.0) for v in vec
            ]

        conf = clamp(1.0 - (d / body.sensor_range) * 0.5 - abs(prng.gauss(0.0, 0.05)), 0.15, 0.92)
        unc = clamp(1.0 - conf + 0.05, 0.05, 0.95)
        return {
            "relative_position": [rel_x, rel_y],
            "motion_signature": noisy_vec(tc.motion_signature),
            "appearance_signature": noisy_vec(tc.appearance_signature),
            "response_timing_pattern": noisy_timing_vec(tc.response_timing_pattern),
            "interaction_style_cues": noisy_vec(tc.interaction_style_cues),
            "cue_confidence": conf,
            "cue_uncertainty": unc,
            "observed_at": now,
            "expires_at": now + self.expire_ttl,
            "source": "partner_cue",
        }

    def policy_view(self) -> dict[str, Any]:
        """What arbitration/policy may see — never absolute world coords or partner_id."""
        view: dict[str, Any] = {
            "observations": [o.to_dict() for o in self.observations],
            "partner_cues": list(self.partner_cues),
            "manipulation_bindings": [
                {
                    "target_address_ref": b.target_address_ref,
                    "perception_evidence_ref": b.perception_evidence_ref,
                    "perception_state_version": b.perception_state_version,
                    "perceived_object_kind": b.perceived_object_kind,
                    "perceived_affordance_refs": list(b.perceived_affordance_refs),
                    "relative_direction": b.relative_direction,
                    "estimated_distance": b.estimated_distance,
                }
                for b in self.object_bindings
            ],
            "perception_state_version": self.perception_state_version,
            "adapter_observations": list(self.adapter_observations),
        }
        if self.leak_world_truth and self._leaked_truth is not None:
            view["WORLD_TRUTH_LEAK"] = self._leaked_truth
        return view

    def to_state(self) -> dict[str, Any]:
        return {
            "observations": [o.to_dict() for o in self.observations],
            "partner_cues": list(self.partner_cues),
            "false_negative_rate": self.false_negative_rate,
            "noise_sigma": self.noise_sigma,
            "expire_ttl": self.expire_ttl,
            "leak_world_truth": self.leak_world_truth,
            "perception_state_version": self.perception_state_version,
            "adapter_observations": list(self.adapter_observations),
            "accepted_adapter_observation_ids": list(self.accepted_adapter_observation_ids),
            "rejected_adapter_observation_ids": list(self.rejected_adapter_observation_ids),
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
        p.partner_cues = list(d.get("partner_cues", []))
        p.perception_state_version = int(d.get("perception_state_version", 0))
        p.adapter_observations = list(d.get("adapter_observations", []))[-256:]
        p.accepted_adapter_observation_ids = list(d.get("accepted_adapter_observation_ids", []))[-512:]
        p.rejected_adapter_observation_ids = list(d.get("rejected_adapter_observation_ids", []))[-512:]
        return p


def resolve_manipulation_address(
    *,
    target_address_ref: str,
    perception_evidence_ref: str,
    perception_state_version: int,
    bindings: list[ObjectAddressBinding],
    habitat_engine: HabitatEngine,
) -> ResolvedManipulationTarget:
    """Trusted runtime: address ref → authoritative object (never visible to policy)."""
    matches = [
        b
        for b in bindings
        if b.target_address_ref == target_address_ref
        and b.perception_evidence_ref == perception_evidence_ref
    ]
    if not matches:
        raise ManipulationResolveError("OBJECT_NOT_PERCEIVED")
    if len(matches) > 1:
        raise ManipulationResolveError("OBJECT_ADDRESS_AMBIGUOUS")
    binding = matches[0]
    if binding.perception_state_version != perception_state_version:
        raise ManipulationResolveError("OBJECT_ADDRESS_BINDING_STALE")
    obj = habitat_engine.get_object(binding.object_id)
    if obj is None:
        raise ManipulationResolveError("OBJECT_NOT_FOUND")
    if obj.object_version != binding.object_version:
        raise ManipulationResolveError("OBJECT_ADDRESS_BINDING_STALE")
    return ResolvedManipulationTarget(
        target_object_id=binding.object_id,
        target_object_version=obj.object_version,
        binding_hash=binding.binding_hash,
    )


def assert_no_world_truth(policy_input: dict[str, Any]) -> None:
    """Test/governance helper: policy bundle must not contain exact coords or partner_id."""
    bad_keys = {
        "x",
        "y",
        "habitat",
        "world_truth",
        "WORLD_TRUTH_LEAK",
        "body",
        "partner_id",
        "hidden_partner_id",
        "object_id",
        "target_object_id",
    }
    flat = set(policy_input.keys())
    if flat & bad_keys:
        # WORLD_TRUTH_LEAK only allowed under explicit ablation flag checked by caller
        if "WORLD_TRUTH_LEAK" in flat:
            return
        raise AssertionError(f"policy_saw_world_truth:{flat & bad_keys}")
