"""Capability governance — proposal → admit → policy → contract → safety → exec → verify."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from umbra_core.embodiment import CAPABILITIES, Embodiment
from umbra_core.physiology import OUTCOME_EFFECTS, Physiology
from umbra_core.util import SeededRNG, new_id


# Effects capabilities may request but never apply themselves.
FORBIDDEN_CAPABILITY_EFFECTS = frozenset(
    {
        "modify_identity",
        "modify_authority",
        "modify_physiology_direct",
        "rewrite_events",
        "grant_capability",
        "revoke_capability",
    }
)

PREAUTHORIZED = frozenset(CAPABILITIES)

SIGNAL_CAPABILITIES = frozenset({"SIGNAL_PLAY", "SIGNAL_ASSISTANCE"})
# ponytail: frozen default matches experiments/d006/thresholds.json signal_cooldown_ticks
SIGNAL_COOLDOWN_TICKS_DEFAULT = 6


@dataclass
class Proposal:
    proposal_id: str
    capability: str
    params: dict[str, Any]
    requested_effects: list[str] = field(default_factory=list)


@dataclass
class GovernanceDecision:
    admitted: bool
    stage_failed: str | None
    reason: str
    proposal_id: str
    capability: str


@dataclass
class VerifiedOutcome:
    outcome_id: str
    capability: str
    success: bool
    reason: str
    physiology_effects: dict[str, float]
    raw: dict[str, Any]
    verified: bool


@dataclass
class GovernanceState:
    grants: set[str] = field(default_factory=lambda: set(PREAUTHORIZED))
    denials: int = 0
    admissions: int = 0
    bypass_attempts: int = 0
    verified_outcomes: int = 0
    # ablation C5
    bypass_enabled: bool = False
    last_signal_tick: int = -10_000
    signal_cooldown_ticks: int = SIGNAL_COOLDOWN_TICKS_DEFAULT

    def to_state(self) -> dict[str, Any]:
        return {
            "grants": sorted(self.grants),
            "denials": self.denials,
            "admissions": self.admissions,
            "bypass_attempts": self.bypass_attempts,
            "verified_outcomes": self.verified_outcomes,
            "bypass_enabled": self.bypass_enabled,
            "last_signal_tick": self.last_signal_tick,
            "signal_cooldown_ticks": self.signal_cooldown_ticks,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> GovernanceState:
        return cls(
            grants=set(d.get("grants", list(PREAUTHORIZED))),
            denials=int(d.get("denials", 0)),
            admissions=int(d.get("admissions", 0)),
            bypass_attempts=int(d.get("bypass_attempts", 0)),
            verified_outcomes=int(d.get("verified_outcomes", 0)),
            bypass_enabled=bool(d.get("bypass_enabled", False)),
            last_signal_tick=int(d.get("last_signal_tick", -10_000)),
            signal_cooldown_ticks=int(
                d.get("signal_cooldown_ticks", SIGNAL_COOLDOWN_TICKS_DEFAULT)
            ),
        )


class Governance:
    def __init__(self, state: GovernanceState | None = None):
        self.state = state or GovernanceState()
        self.last_decision: GovernanceDecision | None = None
        self._execute_hook: Callable[..., dict[str, Any]] | None = None

    def propose(self, capability: str, params: dict[str, Any], requested_effects: list[str] | None = None) -> Proposal:
        return Proposal(
            proposal_id=new_id(),
            capability=capability,
            params=dict(params),
            requested_effects=list(requested_effects or []),
        )

    def admit(self, proposal: Proposal, *, tick: int | None = None) -> GovernanceDecision:
        # C5 bypass attempt tracking
        if self.state.bypass_enabled:
            self.state.bypass_attempts += 1
            # bypass attempts still fail closed for forbidden effects / unknown caps
            pass

        if proposal.capability not in self.state.grants:
            self.state.denials += 1
            dec = GovernanceDecision(
                False, "capability_admission", "unknown_or_ungranted_capability", proposal.proposal_id, proposal.capability
            )
            self.last_decision = dec
            return dec

        for eff in proposal.requested_effects:
            if eff in FORBIDDEN_CAPABILITY_EFFECTS:
                self.state.denials += 1
                self.state.bypass_attempts += 1
                dec = GovernanceDecision(
                    False, "capability_admission", f"forbidden_effect:{eff}", proposal.proposal_id, proposal.capability
                )
                self.last_decision = dec
                return dec

        # policy stage: low-risk preauth only for known primitives
        if proposal.capability not in PREAUTHORIZED:
            self.state.denials += 1
            dec = GovernanceDecision(False, "policy", "not_preauthorized", proposal.proposal_id, proposal.capability)
            self.last_decision = dec
            return dec

        if proposal.capability in SIGNAL_CAPABILITIES and tick is not None:
            elapsed = tick - self.state.last_signal_tick
            if elapsed < self.state.signal_cooldown_ticks:
                self.state.denials += 1
                dec = GovernanceDecision(
                    False,
                    "policy",
                    "signal_cooldown",
                    proposal.proposal_id,
                    proposal.capability,
                )
                self.last_decision = dec
                return dec

        # contract validation
        if not isinstance(proposal.params, dict):
            self.state.denials += 1
            dec = GovernanceDecision(False, "contract", "params_not_dict", proposal.proposal_id, proposal.capability)
            self.last_decision = dec
            return dec

        # runtime safety — refuse self-modifying authority params
        unsafe_keys = set(proposal.params.keys()) & {
            "agent_id",
            "identity_commitment",
            "grants",
            "authority",
            "physiology_set",
        }
        if unsafe_keys:
            self.state.denials += 1
            self.state.bypass_attempts += 1
            dec = GovernanceDecision(
                False, "runtime_safety", f"unsafe_params:{sorted(unsafe_keys)}", proposal.proposal_id, proposal.capability
            )
            self.last_decision = dec
            return dec

        # C5: even with bypass_enabled, we do NOT skip the chain — we record attempt and continue admit
        self.state.admissions += 1
        if proposal.capability in SIGNAL_CAPABILITIES and tick is not None:
            self.state.last_signal_tick = tick
        dec = GovernanceDecision(True, None, "admitted", proposal.proposal_id, proposal.capability)
        self.last_decision = dec
        return dec

    def execute_and_verify(
        self,
        proposal: Proposal,
        decision: GovernanceDecision,
        embodiment: Embodiment,
        rng: SeededRNG,
        *,
        resolve_params: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> VerifiedOutcome | None:
        if not decision.admitted:
            return None

        params = dict(proposal.params)
        if resolve_params:
            params = resolve_params(params)

        raw = embodiment.execute_primitive(proposal.capability, params, rng)
        return self.verify_outcome(proposal.capability, raw)

    def verify_outcome(self, capability: str, raw: dict[str, Any]) -> VerifiedOutcome:
        """Independent verification — capability cannot self-certify."""
        success = bool(raw.get("ok_raw")) and raw.get("reason") not in (
            "unknown_capability",
            "out_of_range",
            "not_at_rest",
            "not_at_resource",
            "delayed",
            "affordance_denied",
            "route_blocked",
        )
        # movement_slip still "executed" but failed quality
        if raw.get("reason") == "movement_slip":
            success = False
        if raw.get("reason") == "delayed" or raw.get("delayed"):
            success = False

        effects: dict[str, float] = {}
        if raw.get("reason") == "delayed" or raw.get("delayed"):
            effects = {}
        elif success:
            effects = dict(OUTCOME_EFFECTS.get(capability, {}))
            if raw.get("hazard_contact"):
                for k, v in OUTCOME_EFFECTS["HAZARD_HIT"].items():
                    effects[k] = effects.get(k, 0.0) + v
        else:
            if capability in ("MOVE", "APPROACH", "RETREAT"):
                effects = dict(OUTCOME_EFFECTS["FAILED_MOVE"])
            else:
                # failed rest/charge still costs a little effort
                effects = {"energy": -0.003, "fatigue": 0.002}
            if raw.get("integrity_hit"):
                effects["integrity"] = effects.get("integrity", 0.0) - float(
                    raw["integrity_hit"]
                )

        scale = float(raw.get("energy_cost_scale", 1.0))
        if scale != 1.0 and "energy" in effects and effects["energy"] < 0:
            effects["energy"] = effects["energy"] * scale

        # Strip any forged physiology_set from raw — never accept as outcome
        if "physiology_set" in raw:
            self.state.bypass_attempts += 1
            success = False
            effects = {}

        self.state.verified_outcomes += 1
        return VerifiedOutcome(
            outcome_id=new_id(),
            capability=capability,
            success=success,
            reason=str(raw.get("reason", "unknown")),
            physiology_effects=effects,
            raw={k: v for k, v in raw.items() if k != "physiology_set"},
            verified=True,
        )

    def apply_physiology(self, phys: Physiology, outcome: VerifiedOutcome) -> None:
        """Physiology owner applies verified effects — governance does not write H directly from policy."""
        if not outcome.verified:
            return
        effects = dict(outcome.physiology_effects)
        # desperate locomotion: seeking rest/charge while depleted shouldn't deepen fatigue trap
        if outcome.capability in ("MOVE", "APPROACH", "RETREAT") and phys.fatigue > 0.65:
            effects["fatigue"] = min(0.0, effects.get("fatigue", 0.0))
        if outcome.capability in ("MOVE", "APPROACH") and phys.energy < 0.2:
            effects["energy"] = max(-0.002, effects.get("energy", 0.0))
        phys.apply_outcome_effects(effects)
