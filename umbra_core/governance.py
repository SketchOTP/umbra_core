"""Capability governance — proposal → admit → policy → contract → safety → exec → verify."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from umbra_core.embodiment import CAPABILITIES, Embodiment
from umbra_core.embodiment_adapters.adapter import AdapterRequest, EmbodimentAdapter
from umbra_core.physiology import OUTCOME_EFFECTS, Physiology
from umbra_core.util import SeededRNG, new_id
from umbra_core.wait_execution import (
    MAXIMUM_WAIT_TICKS,
    WaitJournal,
    wait_deadline_age_tick,
)

WAIT_CAPABILITY = "WAIT"
PREAUTHORIZED = frozenset((*CAPABILITIES, "MANIPULATE", WAIT_CAPABILITY))


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
class WaitAdmissionContext:
    effective_age_ticks: int
    expectation_status: str
    wait_journal: WaitJournal | None = None
    suppress_on_reject: bool = True
    suppress_duration_ticks: int = 8


def _validate_wait_admission(
    proposal: Proposal,
    *,
    tick: int | None,
    wait_context: WaitAdmissionContext | None,
) -> GovernanceDecision | None:
    params = proposal.params
    required = (
        "recurrence_id",
        "window_start",
        "window_end",
        "maximum_wait_ticks",
        "expectation_version",
    )
    missing = [key for key in required if key not in params]
    if missing:
        return GovernanceDecision(
            False,
            "contract",
            f"wait_params_missing:{missing}",
            proposal.proposal_id,
            proposal.capability,
        )
    if wait_context is None:
        return GovernanceDecision(
            False,
            "policy",
            "wait_context_required",
            proposal.proposal_id,
            proposal.capability,
        )
    if wait_context.expectation_status != "ACTIVE":
        return GovernanceDecision(
            False,
            "policy",
            "wait_requires_active_expectation",
            proposal.proposal_id,
            proposal.capability,
        )
    effective_age = wait_context.effective_age_ticks
    window_start = float(params["window_start"])
    window_end = float(params["window_end"])
    if not (window_start <= effective_age <= window_end):
        return GovernanceDecision(
            False,
            "policy",
            "wait_outside_open_window",
            proposal.proposal_id,
            proposal.capability,
        )
    journal = wait_context.wait_journal
    if journal is not None and journal.is_suppressed(
        str(params["recurrence_id"]),
        int(params["expectation_version"]),
        effective_age,
    ):
        return GovernanceDecision(
            False,
            "policy",
            "wait_suppressed",
            proposal.proposal_id,
            proposal.capability,
        )
    max_wait = int(params.get("maximum_wait_ticks", MAXIMUM_WAIT_TICKS))
    expected_deadline = wait_deadline_age_tick(
        started_age_tick=effective_age,
        window_end=window_end,
        maximum_wait_ticks=max_wait,
    )
    if tick is not None and tick != effective_age:
        _ = tick
    params_deadline = params.get("wait_deadline")
    if params_deadline is not None and int(params_deadline) != expected_deadline:
        return GovernanceDecision(
            False,
            "contract",
            "wait_deadline_mismatch",
            proposal.proposal_id,
            proposal.capability,
        )
    return None


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

    def admit(
        self,
        proposal: Proposal,
        *,
        tick: int | None = None,
        wait_context: WaitAdmissionContext | None = None,
    ) -> GovernanceDecision:
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

        if proposal.capability == WAIT_CAPABILITY:
            wait_dec = _validate_wait_admission(
                proposal,
                tick=tick,
                wait_context=wait_context,
            )
            if wait_dec is not None:
                self.state.denials += 1
                if (
                    wait_context is not None
                    and wait_context.suppress_on_reject
                    and wait_context.wait_journal is not None
                    and wait_dec.reason in {
                        "wait_outside_open_window",
                        "wait_requires_active_expectation",
                        "wait_suppressed",
                    }
                ):
                    params = proposal.params
                    wait_context.wait_journal.record_suppression(
                        recurrence_id=str(params.get("recurrence_id", "")),
                        expectation_version=int(params.get("expectation_version", 0)),
                        terminal_reason=wait_dec.reason,
                        suppressed_until_age_tick=(
                            wait_context.effective_age_ticks
                            + wait_context.suppress_duration_ticks
                        ),
                        governance_decision_id=proposal.proposal_id,
                    )
                self.last_decision = wait_dec
                return wait_dec

        # runtime safety — refuse self-modifying authority params
        unsafe_keys = set(proposal.params.keys()) & {
            "agent_id",
            "identity_commitment",
            "grants",
            "authority",
            "physiology_set",
            "target_object_id",
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
        adapter: EmbodimentAdapter | None = None,
        tick: int = 0,
    ) -> VerifiedOutcome | None:
        if not decision.admitted:
            return None

        if proposal.capability == WAIT_CAPABILITY:
            return VerifiedOutcome(
                outcome_id=new_id(),
                capability=WAIT_CAPABILITY,
                success=True,
                reason="wait_admitted",
                physiology_effects={},
                raw={
                    "ok_raw": True,
                    "reason": "wait_admitted",
                    "capability": WAIT_CAPABILITY,
                    "params": dict(proposal.params),
                },
                verified=True,
            )

        params = dict(proposal.params)
        if resolve_params:
            params = resolve_params(params)

        if adapter is not None:
            request = AdapterRequest(
                request_id=proposal.proposal_id,
                capability=proposal.capability,
                params=params,
                attachment_generation=adapter.state.attachment_generation,
                tick=tick,
            )
            raw = adapter.execute(request, embodiment, rng)
        else:
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

    def verify_manipulation_outcome(
        self,
        request: Any,
        *,
        success: bool,
        failure_code: str | None,
        physiology_effects: dict[str, float] | None = None,
        applied_parameters: Any = None,
        transaction_id: str | None = None,
    ) -> VerifiedOutcome:
        """Verify MANIPULATE outcome — records execution/request correlation in raw."""
        from dataclasses import asdict

        raw: dict[str, Any] = {
            "ok_raw": success,
            "execution_id": request.execution_id,
            "request_id": request.request_id,
            "target_object_id": request.target_object_id,
            "affordance_id": request.affordance_id,
            "body_instance_id": request.body_instance_id,
            "body_profile_id": request.body_profile_id,
            "attachment_generation": request.attachment_generation,
            "capability": request.capability,
        }
        if applied_parameters is not None:
            raw["requested_parameters"] = asdict(request.parameters)
            raw["applied_parameters"] = asdict(applied_parameters)
        if transaction_id is not None:
            raw["transaction_id"] = transaction_id
        reason = "manipulation_committed" if success else str(failure_code or "manipulation_failed")
        self.state.verified_outcomes += 1
        return VerifiedOutcome(
            outcome_id=new_id(),
            capability=request.capability,
            success=success,
            reason=reason,
            physiology_effects=dict(physiology_effects or {}),
            raw=raw,
            verified=True,
        )

    def execute_manipulation(
        self,
        proposal: Proposal,
        decision: GovernanceDecision,
        *,
        habitat_engine: Any,
        affordance_engine: Any,
        adapter: EmbodimentAdapter,
        embodiment: Embodiment,
        bindings: list[Any],
        store: Any,
        phys: Physiology,
        agent_id: str,
        tick: int,
        monotonic_time: float,
        wall_time: float,
    ) -> VerifiedOutcome | None:
        """Full MANIPULATE path: resolve → adapter → affordance → journal commit."""
        from umbra_core.embodiment_adapters.adapter import ManipulationValidationError
        from umbra_core.habitat.execution_journal import commit_manipulation_transaction
        from umbra_core.habitat_affordances.engine import (
            ActivateParameters,
            ManipulationRequest,
            PickUpParameters,
            UseParameters,
            definition_hash,
        )
        from umbra_core.perception import ManipulationResolveError, resolve_manipulation_address
        from umbra_core.util import new_id

        if not decision.admitted:
            return None

        params = dict(proposal.params)
        target_address_ref = str(params.get("target_address_ref", ""))
        perception_evidence_ref = str(params.get("perception_evidence_ref", ""))
        perception_state_version = int(params.get("perception_state_version", -1))
        affordance_id = str(params.get("perceived_affordance_ref", ""))
        raw_parameters = dict(params.get("parameters") or {})

        def _fail(code: str) -> VerifiedOutcome:
            self.state.verified_outcomes += 1
            return VerifiedOutcome(
                outcome_id=new_id(),
                capability="MANIPULATE",
                success=False,
                reason=code,
                physiology_effects={},
                raw={"ok_raw": False, "failure_code": code, "capability": "MANIPULATE"},
                verified=True,
            )

        try:
            resolved = resolve_manipulation_address(
                target_address_ref=target_address_ref,
                perception_evidence_ref=perception_evidence_ref,
                perception_state_version=perception_state_version,
                bindings=bindings,
                habitat_engine=habitat_engine,
            )
        except ManipulationResolveError as exc:
            return _fail(exc.code)

        kind = str(raw_parameters.get("kind", "USE"))
        if kind == "PICK_UP":
            manipulation_params = PickUpParameters(hold_slot=int(raw_parameters.get("hold_slot", 0)))
        elif kind == "ACTIVATE":
            manipulation_params = ActivateParameters()
        else:
            manipulation_params = UseParameters()

        expected_profile_hash = params.get("expected_profile_hash")
        try:
            adapter_validated = adapter.validate_manipulation(
                capability="MANIPULATE",
                parameters=manipulation_params,
                attachment_generation=adapter.state.attachment_generation,
                body_instance_id=adapter.state.body_instance_id,
                embodiment=embodiment,
                expected_profile_hash=expected_profile_hash,
            )
        except ManipulationValidationError as exc:
            return _fail(exc.failure_code)

        snapshot = habitat_engine.snapshot_view()
        obj = snapshot.objects[resolved.target_object_id]
        defn = affordance_engine.get_definition(affordance_id)
        if defn is None:
            return _fail("AFFORDANCE_NOT_SUPPORTED")

        in_range = habitat_engine.check_range(
            adapter_validated.body_pose_view,
            adapter_validated.reach_profile,
            resolved.target_object_id,
        )
        request = ManipulationRequest(
            request_id=proposal.proposal_id,
            execution_id=new_id(),
            capability="MANIPULATE",
            target_object_id=resolved.target_object_id,
            affordance_id=affordance_id,
            expected_habitat_version=snapshot.state_version,
            expected_habitat_state_hash=snapshot.state_hash,
            target_object_version=resolved.target_object_version,
            target_object_definition_version=obj.definition_version,
            target_object_definition_hash=obj.definition_hash,
            affordance_definition_version=defn.definition_version,
            affordance_definition_hash=definition_hash(defn),
            body_instance_id=adapter.state.body_instance_id,
            body_profile_id=adapter.state.body_profile_id,
            attachment_generation=adapter.state.attachment_generation,
            parameters=manipulation_params,
        )
        validation = affordance_engine.validate(
            request,
            snapshot,
            adapter_validated,
            in_range=in_range,
        )
        if not validation.allowed:
            commit = commit_manipulation_transaction(
                store,
                self,
                habitat_engine,
                phys,
                request,
                validation,
                agent_id=agent_id,
                prepared_tick=tick,
                monotonic_time=monotonic_time,
                wall_time=wall_time,
            )
            return commit.outcome

        commit = commit_manipulation_transaction(
            store,
            self,
            habitat_engine,
            phys,
            request,
            validation,
            agent_id=agent_id,
            prepared_tick=tick,
            monotonic_time=monotonic_time,
            wall_time=wall_time,
        )
        return commit.outcome

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
