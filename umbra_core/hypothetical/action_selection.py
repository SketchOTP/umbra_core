"""AS-004 bounded continuation authority adapter.

This module is the only bridge from the already qualified planning frame to
ordinary candidate elimination.  It builds O0 from the frame before candidate
inspection, uses the immutable transition substrate for every hypothetical
step, and returns only a strict preservation relation.  It has no execution,
learning, persistence, or candidate-generation authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable, Mapping, Sequence

from umbra_core.physiology import BOUNDS, DEFAULT_DRIFT
from umbra_core.physiology import verified_outcome_effect_branches
from umbra_core.self_model.engine import SupportSemantics
from umbra_core.util import canon_json, sha256_hex

from .adapters import SourceOpportunity, SourceRoute, build_regulatory_service, root_state_from_sources
from .continuation import MAX_CONTINUATION_DEPTH, ContinuationSet, _obligations_complete, root_continuation_set, service_transition
from .core import DependencyToken, EvidenceEnvelope, HypotheticalState, TransitionContract, TransitionStatus, transition
from .frame import PlanningEvidenceFrame
from .frame import PlanningModality


@dataclass(frozen=True)
class CandidateContinuation:
    candidate_identity: str
    status_by_witness: tuple[tuple[str, str], ...]
    unknown_reasons: tuple[str, ...] = ()

    def status(self, witness: str) -> str:
        return dict(self.status_by_witness).get(witness, "UNKNOWN")


@dataclass(frozen=True)
class ContinuationElimination:
    survivors: tuple[str, ...]
    eliminated: tuple[tuple[str, str, str], ...]
    root_size: int
    root_fingerprint: str
    classifications: tuple[CandidateContinuation, ...]
    unknown_rate: float
    modal_options: tuple[tuple[str, str, tuple[str, ...], str], ...] = ()
    modal_option_details: tuple[dict[str, Any], ...] = ()

    def to_canonical(self) -> dict[str, Any]:
        return {
            "survivor_count": len(self.survivors),
            "survivors": list(self.survivors),
            "eliminated": [list(row) for row in self.eliminated],
            "root_size": self.root_size,
            "root_fingerprint": self.root_fingerprint,
            "classifications": [
                {"candidate": row.candidate_identity, "status_by_witness": [list(item) for item in row.status_by_witness], "unknown_reasons": list(row.unknown_reasons)}
                for row in self.classifications
            ],
            "unknown_rate": self.unknown_rate,
            "modal_options": [
                {"identity": identity, "modality": modality, "owners": list(owners), "provenance": provenance}
                for identity, modality, owners, provenance in self.modal_options
            ],
            "modal_option_details": [dict(item) for item in self.modal_option_details],
        }


@dataclass(frozen=True)
class KnownContinuationOption:
    """One exact source-backed MAY continuation, never an action ranking."""

    identity: str
    opportunity_identity: str
    opportunity_kind: str
    body_schema_identity: str
    route_evidence_identity: str
    ordered_route_control_pattern: tuple[tuple[str, bool], ...]
    terminal_capability: str
    observed_demand_ticks: int
    source_horizon: EvidenceEnvelope
    modality: PlanningModality
    owners: tuple[str, ...]
    provenance: tuple[str, ...]

    def to_canonical(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "opportunity_identity": self.opportunity_identity,
            "opportunity_kind": self.opportunity_kind,
            "body_schema_identity": self.body_schema_identity,
            "route_evidence_identity": self.route_evidence_identity,
            "ordered_route_control_pattern": [list(item) for item in self.ordered_route_control_pattern],
            "terminal_capability": self.terminal_capability,
            "observed_demand_ticks": self.observed_demand_ticks,
            "source_horizon": self.source_horizon.to_canonical(),
            "modality": self.modality.value,
            "owners": list(self.owners),
            "provenance": list(self.provenance),
        }


def candidate_identity(candidate: Any) -> str:
    """Stable semantic identity for one candidate in the relation trace."""
    return f"{getattr(candidate, 'capability', '')}:{sha256_hex(canon_json(dict(getattr(candidate, 'params', {}))))}"


def _observed(value: float, reference: str) -> EvidenceEnvelope:
    return EvidenceEnvelope(value, value, SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value, (reference,))


def _hard(value: float, reference: str) -> EvidenceEnvelope:
    return EvidenceEnvelope(value, value, SupportSemantics.HARD_CONTRACT.value, (reference,))


def _unknown(reference: str) -> EvidenceEnvelope:
    return EvidenceEnvelope.unknown(reference)


def _fact_modality(row: Mapping[str, Any]) -> str:
    return str(row.get("modality", "UNKNOWN"))


def _frame_root_and_services(frame: PlanningEvidenceFrame) -> tuple[HypotheticalState, tuple[Any, ...], tuple[str, ...]]:
    body = frame.body.to_plain()
    body_identity = str(body.get("body_schema_identity") or "")
    body_version = str(body.get("body_schema_version", ""))
    route_support = frame.route_experience_support.to_plain()
    if not body_identity:
        # V2 frames retain the exact body schema on each route witness even
        # when a legacy body-profile projection omits it at the frame level.
        schemas = {
            str(witness.get("body_schema_id", ""))
            for raw in route_support.values()
            for witness in tuple(dict(raw).get("value", {}).get("witnesses", ()) or ())
            if witness.get("body_schema_id")
        }
        if len(schemas) == 1:
            body_identity = next(iter(schemas))
    if not body_identity:
        return root_state_from_sources(
            root_tick=frame.organism_tick,
            physiology=frame.physiology_root.to_plain(),
            body_schema_identity="unknown",
            body_schema_version="unknown",
        ), (), ()

    opportunities: dict[str, SourceOpportunity] = {}
    for identity, raw in sorted(frame.opportunities.to_plain().items()):
        future = dict(raw.get("future") or {})
        modality = _fact_modality(future)
        horizon = future.get("valid_through_ticks")
        persistence = (
            _hard(float(horizon), f"frame:opportunity:{identity}:persistence")
            if modality == "MUST" and horizon is not None
            else _unknown(f"frame:opportunity:{identity}:future-persistence:{modality}")
        )
        availability = TransitionStatus.SUPPORTED if modality in {"MUST", "MAY"} else TransitionStatus.UNKNOWN
        opportunities[str(identity)] = SourceOpportunity(
            str(identity), availability, persistence,
            tuple(str(ref) for ref in future.get("provenance", ())),
            DependencyToken("opportunity", str(identity), str(frame.source_versions.to_plain().get("world_model_policy_state", "unknown"))),
        )

    root = root_state_from_sources(
        root_tick=frame.organism_tick,
        physiology=frame.physiology_root.to_plain(),
        body_schema_identity=body_identity,
        body_schema_version=body_version,
        opportunities=opportunities,
        pending_commitment=frame.pending_execution.to_plain(),
        additional_dependencies=(DependencyToken("frame", "planning", frame.material_fingerprint),),
    )

    services: list[Any] = []
    capability_map = frame.constitutional_capabilities.to_plain()
    for identity, raw in sorted(route_support.items()):
        if identity not in opportunities:
            continue
        fact = dict(raw)
        # R6C stores the payload under the immutable ModalFact ``value``
        # field.  Do not flatten that structure or silently lose the route
        # witnesses at the source-to-substrate boundary.
        payload = dict(fact.get("value") or {})
        witnesses = tuple(payload.get("witnesses") or ())
        for witness in witnesses:
            terminal = str(witness.get("terminal_capability", ""))
            observed_ticks = witness.get("observed_episode_ticks")
            if terminal not in {"CHARGE", "REST", "INSPECT"} or observed_ticks is None:
                continue
            cap_fact = dict(capability_map.get(terminal) or {})
            cap = _hard(1.0, f"frame:capability:{terminal}") if _fact_modality(cap_fact) == "MUST" else _unknown(f"frame:capability:{terminal}")
            duration = _observed(float(observed_ticks), f"route-experience:{witness.get('route_evidence_id', 'unknown')}:duration")
            route = SourceRoute(
                identity=str(witness.get("route_evidence_id", "")),
                availability=TransitionStatus.SUPPORTED,
                timing=duration,
                capability=_observed(1.0, f"route-experience:{witness.get('route_evidence_id', 'unknown')}:capability"),
                provenance=tuple(str(ref) for ref in witness.get("provenance", ())),
                token=DependencyToken("route", str(witness.get("route_evidence_id", "")), frame.material_fingerprint),
            )
            services.append(build_regulatory_service(
                capability=terminal,
                body_schema_identity=body_identity,
                opportunity=opportunities[str(identity)],
                route=route,
                duration=duration,
                capability_support=cap,
                body_version_token=DependencyToken("body_schema", body_identity, body_version),
            ))
    # Preventive obligations are derived from exact option demand, not from
    # the hypothetical recursion-depth ceiling.  MAY remains MAY; this only
    # identifies owners whose viable-boundary time is already within demand.
    options = _frame_modal_options(frame)
    obligations = {
        owner
        for option in options
        for owner in option.owners
        if _owner_active(frame, owner, BOUNDS[owner], option.observed_demand_ticks)
    }
    return root, tuple(services), tuple(sorted(obligations))


def _frame_modal_options(frame: PlanningEvidenceFrame) -> tuple[KnownContinuationOption, ...]:
    """Expose possible source-backed options separately from strict O0.

    MAY route/persistence evidence is intentionally not upgraded to a
    categorical continuation guarantee.  It is retained as an immutable
    option fact so the shadow/diagnostic trace can show that planning evidence
    was present without granting the ordinary path a false guarantee.
    """
    opportunities = frame.opportunities.to_plain()
    routes = frame.route_experience_support.to_plain()
    capabilities = frame.constitutional_capabilities.to_plain()
    owners = {"CHARGE": ("energy",), "REST": ("fatigue", "integrity"), "INSPECT": ("stimulation",)}
    kinds = {"CHARGE": {"resource", "novel_crystal"}, "REST": {"rest"}, "INSPECT": {"inspect"}}
    options: list[KnownContinuationOption] = []
    for identity, raw in sorted(routes.items()):
        payload = dict(raw.get("value") or {})
        witnesses = tuple(payload.get("witnesses") or ())
        route_modality = PlanningModality(str(raw.get("modality", PlanningModality.UNKNOWN.value)))
        if not witnesses or route_modality in {PlanningModality.UNKNOWN, PlanningModality.UNSUPPORTED}:
            continue
        opportunity = opportunities.get(identity) or {}
        opportunity_modality = PlanningModality(str(dict(opportunity.get("future") or {}).get("modality", PlanningModality.UNKNOWN.value)))
        for capability, allowed_kinds in kinds.items():
            if str(opportunity.get("kind", "")) not in allowed_kinds:
                continue
            capability_modality = PlanningModality(str(dict(capabilities.get(capability) or {}).get("modality", PlanningModality.UNKNOWN.value)))
            if capability_modality is PlanningModality.UNSUPPORTED or opportunity_modality is PlanningModality.UNSUPPORTED:
                continue
            modality = PlanningModality.MAY
            if capability_modality is PlanningModality.MUST and opportunity_modality is PlanningModality.MUST and route_modality is PlanningModality.MUST:
                modality = PlanningModality.MUST
            future = dict(opportunity.get("future") or {})
            horizon = future.get("valid_through_ticks")
            if horizon is None or int(horizon) < 0:
                source_horizon = EvidenceEnvelope.unknown(f"opportunity:{identity}:source-horizon")
            elif opportunity_modality is PlanningModality.MUST:
                source_horizon = _hard(float(horizon), f"opportunity:{identity}:source-horizon")
            elif opportunity_modality is PlanningModality.MAY:
                source_horizon = _observed(float(horizon), f"opportunity:{identity}:source-horizon")
            else:
                source_horizon = EvidenceEnvelope.unknown(f"opportunity:{identity}:source-horizon")
            for witness in witnesses:
                demand = witness.get("observed_episode_ticks")
                if demand is None or int(demand) <= 0:
                    continue
                pattern = tuple(
                    (str(step.get("capability", "")), bool(step.get("translational_movement", False)))
                    for step in tuple(witness.get("ordered_control_steps") or ())
                )
                route_identity = str(witness.get("route_evidence_id", ""))
                semantic_key = {
                    "opportunity_identity": str(identity),
                    "opportunity_kind": str(opportunity.get("kind", "")),
                    "body_schema_identity": str(witness.get("body_schema_id") or frame.body.to_plain().get("body_schema_identity", "")),
                    "pattern": [list(item) for item in pattern],
                    "terminal_capability": capability,
                    "observed_demand_ticks": int(demand),
                }
                option_identity = f"known-option:{capability}:{sha256_hex(canon_json(semantic_key))}"
                provenance = tuple(sorted({
                    str(ref)
                    for ref in (
                        *tuple(raw.get("provenance") or ()),
                        *tuple(future.get("provenance") or ()),
                        *tuple(witness.get("provenance") or ()),
                    )
                    if ref
                }))
                options.append(KnownContinuationOption(
                    identity=option_identity,
                    opportunity_identity=str(identity),
                    opportunity_kind=str(opportunity.get("kind", "")),
                    body_schema_identity=str(witness.get("body_schema_id") or frame.body.to_plain().get("body_schema_identity", "")),
                    route_evidence_identity=route_identity,
                    ordered_route_control_pattern=pattern,
                    terminal_capability=capability,
                    observed_demand_ticks=int(demand),
                    source_horizon=source_horizon,
                    modality=modality,
                    owners=owners[capability],
                    provenance=provenance,
                ))
    return tuple(sorted(options, key=lambda option: option.identity))


def _owner_active(frame: PlanningEvidenceFrame, owner: str, bounds: Any, required_demand: int | None = None) -> bool:
    raw = frame.physiology_root.to_plain().get(owner)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return True
    if not bounds.in_viable(value):
        return True
    # Preventive obligation: use only the constitutional band, autonomous
    # drift, and exact known option demand.  This is binary feasibility, never
    # urgency, normalization, cross-owner arithmetic, or ranking.
    drift = float(DEFAULT_DRIFT.get(owner, 0.0))
    if drift < 0.0:
        remaining = value - bounds.viable_low
    elif drift > 0.0:
        remaining = bounds.viable_high - value
    else:
        return False
    if remaining <= 0.0:
        return True
    if required_demand is None:
        return False
    return remaining / abs(drift) <= float(required_demand)


def _candidate_contract(candidate: Any) -> TransitionContract:
    capability = str(candidate.capability)
    # The runtime's ordinary cadence is one logical current-action interval.
    # This is the execution cadence contract, not a cost or preference.
    effects = []
    for index, branch in enumerate(verified_outcome_effect_branches(capability)):
        branch_effects = {
            name: _hard(float(value), f"verified-outcome:{capability}:{index}:{name}")
            for name, value in branch.items()
        }
        for name, drift in DEFAULT_DRIFT.items():
            branch_effects[name] = branch_effects.get(name, _hard(0.0, f"verified-outcome:{capability}:{index}:{name}")).add(
                _hard(float(drift), f"autonomous-drift:{name}")
            )
        effects.append(branch_effects)
    return TransitionContract(
        semantic_identity=f"as004:candidate:{capability}:{sha256_hex(canon_json(dict(candidate.params)))}",
        duration=_hard(1.0, f"runtime-action-cadence:{capability}"),
        effect_branches=tuple(effects),
        provenance=(f"candidate:{capability}",),
    )


def _weak_option_branch_status(state: HypotheticalState, option: KnownContinuationOption) -> tuple[str, tuple[str, ...]]:
    """Classify one exact known option after one immediate candidate branch."""
    if option.body_schema_identity != state.body_schema_identity:
        return "UNKNOWN", ("OPTION_BODY_SCHEMA_MISMATCH",)
    opportunity = state.opportunities.get(option.opportunity_identity)
    if opportunity is None or opportunity.availability is not TransitionStatus.SUPPORTED:
        return "UNKNOWN", ("OPTION_OPPORTUNITY_UNKNOWN",)
    if not option.source_horizon.categorical_supported() or not state.elapsed_time.categorical_supported():
        return "UNKNOWN", ("OPTION_SOURCE_HORIZON_UNKNOWN",)
    elapsed = float(state.elapsed_time.maximum or 0.0)
    horizon = float(option.source_horizon.minimum or 0.0)
    demand = int(option.observed_demand_ticks)
    # The observed route demand includes its terminal action and is consumed
    # after the current action.  A known finite root horizon that no longer
    # accommodates that witness is a categorical loss of this exact option;
    # an absent/uncertain horizon was handled above as UNKNOWN.
    if elapsed + demand > horizon + 1e-12:
        return "DESTROYED", ("OPTION_SOURCE_HORIZON_EXHAUSTED",)
    branch = state.physiology_branches[0]
    reasons: list[str] = []
    for owner in option.owners:
        envelope = branch.values.get(owner)
        if envelope is None or not envelope.categorical_supported():
            return "UNKNOWN", (f"OPTION_{owner.upper()}_STATE_UNKNOWN",)
        bounds = BOUNDS[owner]
        minimum = float(envelope.minimum or 0.0)
        maximum = float(envelope.maximum or 0.0)
        if maximum < bounds.viable_low or minimum > bounds.viable_high:
            reasons.append(f"OPTION_{owner.upper()}_OUTSIDE_VIABLE_BAND")
            continue
        if minimum < bounds.viable_low or maximum > bounds.viable_high:
            return "UNKNOWN", (f"OPTION_{owner.upper()}_VIABLE_BOUNDARY_UNKNOWN",)
        drift = float(DEFAULT_DRIFT.get(owner, 0.0))
        if drift < 0.0:
            distance = minimum - bounds.viable_low
        elif drift > 0.0:
            distance = bounds.viable_high - maximum
        else:
            distance = float("inf")
        if distance <= 0.0 or (drift and distance + 1e-9 < abs(drift) * demand):
            reasons.append(f"OPTION_{owner.upper()}_SLACK_EXHAUSTED")
    if reasons:
        return "DESTROYED", tuple(sorted(set(reasons)))
    return "PRESERVED", ()


def _weak_option_status(root: HypotheticalState, candidate: Any, option: KnownContinuationOption) -> tuple[str, tuple[str, ...]]:
    """Apply universal supported immediate branches to one MAY option."""
    current = transition(root, _candidate_contract(candidate))
    if current.status is not TransitionStatus.SUPPORTED:
        return "UNKNOWN", (f"CURRENT_CANDIDATE_{current.reason}",)
    statuses: list[str] = []
    reasons: set[str] = set()
    for branch in current.successors:
        status, branch_reasons = _weak_option_branch_status(branch, option)
        statuses.append(status)
        reasons.update(branch_reasons)
    if statuses and all(status == "PRESERVED" for status in statuses):
        return "PRESERVED", tuple(sorted(reasons))
    if statuses and all(status == "DESTROYED" for status in statuses):
        return "DESTROYED", tuple(sorted(reasons))
    return "UNKNOWN", tuple(sorted(reasons or {"OPTION_BRANCH_OUTCOME_MIXED"}))


def _modal_option_detail(frame: PlanningEvidenceFrame, option: KnownContinuationOption) -> dict[str, Any]:
    values = frame.physiology_root.to_plain()
    slack: dict[str, float | None] = {}
    for owner in option.owners:
        try:
            value = float(values[owner])
        except (KeyError, TypeError, ValueError):
            slack[owner] = None
            continue
        bounds = BOUNDS[owner]
        if not bounds.in_viable(value):
            slack[owner] = 0.0
            continue
        drift = float(DEFAULT_DRIFT.get(owner, 0.0))
        slack[owner] = None if drift == 0.0 else (value - bounds.viable_low if drift < 0 else bounds.viable_high - value) / abs(drift) - option.observed_demand_ticks
    return {**option.to_canonical(), "recovery_slack": slack}


def _replay_witness(root: HypotheticalState, candidate: Any, witness: str, services: Mapping[str, Any], obligations: Sequence[str]) -> str:
    current = transition(root, _candidate_contract(candidate))
    if current.status is not TransitionStatus.SUPPORTED:
        return "UNKNOWN"
    try:
        node = json.loads(witness)
    except (TypeError, ValueError):
        return "UNKNOWN"

    def replay_branch(state: HypotheticalState, current_node: Mapping[str, Any]) -> TransitionStatus:
        if current_node.get("kind") == "complete":
            return _obligations_complete(state, obligations)
        if current_node.get("kind") != "service":
            return TransitionStatus.UNKNOWN
        service = services.get(str(current_node.get("service", "")))
        if service is None:
            return TransitionStatus.UNKNOWN
        result = service_transition(state, service)
        if result.status is not TransitionStatus.SUPPORTED:
            return result.status
        children = tuple(current_node.get("children") or ())
        if len(children) != len(result.successors) or len(result.successors) > 32:
            return TransitionStatus.UNKNOWN
        statuses: list[TransitionStatus] = []
        for child, child_node in zip(result.successors, children):
            served = _obligations_complete(child, service.service.owners)
            if served is not TransitionStatus.SUPPORTED:
                statuses.append(served)
            else:
                statuses.append(replay_branch(child, child_node))
        if all(status is TransitionStatus.SUPPORTED for status in statuses):
            return TransitionStatus.SUPPORTED
        if any(status is TransitionStatus.UNKNOWN for status in statuses):
            return TransitionStatus.UNKNOWN
        return TransitionStatus.UNSUPPORTED

    branch_statuses = tuple(replay_branch(branch, node) for branch in current.successors)
    if all(status is TransitionStatus.SUPPORTED for status in branch_statuses):
        return "PRESERVED"
    if any(status is TransitionStatus.UNKNOWN for status in branch_statuses):
        return "UNKNOWN"
    return "DESTROYED"


def eliminate_by_continuation(frame: PlanningEvidenceFrame, candidates: Sequence[Any]) -> ContinuationElimination:
    """Apply strict and weak option preservation without ranking candidates."""
    root, services, obligations = _frame_root_and_services(frame)
    modal_options = _frame_modal_options(frame)
    o0 = root_continuation_set(root, services, obligations=obligations, max_depth=MAX_CONTINUATION_DEPTH) if obligations else ContinuationSet(())
    witness_map = dict(o0.witnesses_by_branch)
    if not candidates:
        identities = tuple(str(getattr(c, "capability", "")) for c in candidates)
        return ContinuationElimination(
            identities, (), len(modal_options) or len(witness_map), root.material_fingerprint, (), 0.0,
            tuple((option.identity, option.modality.value, option.owners, ";".join(option.provenance)) for option in modal_options),
            tuple(_modal_option_detail(frame, option) for option in modal_options),
        )
    service_map = {service.service.semantic_identity: service for service in services}
    classifications: list[CandidateContinuation] = []
    for candidate in candidates:
        candidate_id = candidate_identity(candidate)
        statuses: list[tuple[str, str]] = []
        reasons: set[str] = set()
        for branch_key, witnesses in sorted(witness_map.items()):
            for witness in sorted(witnesses):
                statuses.append((f"{branch_key}:{witness}", _replay_witness(root, candidate, witness, service_map, obligations)))
        for option in modal_options:
            status, option_reasons = _weak_option_status(root, candidate, option)
            statuses.append((option.identity, status))
            reasons.update(option_reasons)
        classifications.append(CandidateContinuation(candidate_id, tuple(statuses), tuple(sorted(reasons))))
    eliminated: list[tuple[str, str, str]] = []
    eliminated_ids: set[str] = set()
    for left in classifications:
        left_map = dict(left.status_by_witness)
        for right in classifications:
            if left is right:
                continue
            right_map = dict(right.status_by_witness)
            keys = set(left_map) & set(right_map)
            positive = any(left_map[key] == "PRESERVED" and right_map[key] == "DESTROYED" for key in keys)
            converse = any(right_map[key] == "PRESERVED" and left_map[key] == "DESTROYED" for key in keys)
            unknown = any("UNKNOWN" in {left_map[key], right_map[key]} for key in keys)
            if positive and not converse and not unknown:
                eliminated.append((right.candidate_identity, left.candidate_identity, "STRICT_CONTINUATION_PRESERVATION"))
                eliminated_ids.add(right.candidate_identity)
    survivors = tuple(
        candidate_identity(candidate)
        for index, candidate in enumerate(candidates)
        if candidate_identity(candidate) not in eliminated_ids
    )
    total = sum(len(item.status_by_witness) for item in classifications)
    unknown = sum(1 for item in classifications for _, value in item.status_by_witness if value == "UNKNOWN")
    return ContinuationElimination(
        survivors, tuple(sorted(set(eliminated)),), len(modal_options) or len(witness_map), root.material_fingerprint,
        tuple(classifications), unknown / total if total else 0.0,
        tuple((option.identity, option.modality.value, option.owners, ";".join(option.provenance)) for option in modal_options),
        tuple(_modal_option_detail(frame, option) for option in modal_options),
    )
