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

from umbra_core.physiology import BOUNDS
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
        }


@dataclass(frozen=True)
class KnownContinuationOption:
    """Immutable source-backed option evidence, never an action ranking."""

    identity: str
    modality: PlanningModality
    owners: tuple[str, ...]
    provenance: tuple[str, ...]


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
    route_support = frame.route_experience_support.to_plain()
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
    return root, tuple(services), tuple(sorted({owner for owner, bounds in BOUNDS.items() if _owner_active(frame, owner, bounds)}))


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
            provenance = tuple(sorted({str(ref) for ref in (*tuple(raw.get("provenance") or ()), *tuple(dict(opportunity.get("future") or {}).get("provenance") or ())) if ref}))
            options.append(KnownContinuationOption(
                identity=f"known-option:{capability}:{identity}",
                modality=modality,
                owners=owners[capability],
                provenance=provenance,
            ))
    return tuple(sorted(options, key=lambda option: option.identity))


def _owner_active(frame: PlanningEvidenceFrame, owner: str, bounds: Any) -> bool:
    raw = frame.physiology_root.to_plain().get(owner)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return True
    if not bounds.in_viable(value):
        return True
    # Preventive obligation: use only the constitutional band and the
    # already-qualified autonomous drift contract.  This is a finite-horizon
    # boundary forecast, not urgency, normalization, or cross-owner scoring.
    from umbra_core.physiology import DEFAULT_DRIFT
    drift = float(DEFAULT_DRIFT.get(owner, 0.0))
    if drift < 0.0:
        remaining = value - bounds.viable_low
    elif drift > 0.0:
        remaining = bounds.viable_high - value
    else:
        return False
    if remaining <= 0.0:
        return True
    return remaining / abs(drift) <= float(MAX_CONTINUATION_DEPTH)


def _candidate_contract(candidate: Any) -> TransitionContract:
    capability = str(candidate.capability)
    # The runtime's ordinary cadence is one logical current-action interval.
    # This is the execution cadence contract, not a cost or preference.
    effects = tuple(
        {name: _hard(float(value), f"verified-outcome:{capability}:{index}:{name}") for name, value in branch.items()}
        for index, branch in enumerate(verified_outcome_effect_branches(capability))
    )
    return TransitionContract(
        semantic_identity=f"as004:candidate:{capability}:{sha256_hex(canon_json(dict(candidate.params)))}",
        duration=_hard(1.0, f"runtime-action-cadence:{capability}"),
        effect_branches=effects,
        provenance=(f"candidate:{capability}",),
    )


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
    """Apply strict O0 preservation inclusion and return only surviving candidates."""
    root, services, obligations = _frame_root_and_services(frame)
    modal_options = _frame_modal_options(frame)
    o0 = root_continuation_set(root, services, obligations=obligations, max_depth=MAX_CONTINUATION_DEPTH) if obligations else ContinuationSet(())
    witness_map = dict(o0.witnesses_by_branch)
    if not witness_map or not candidates:
        identities = tuple(str(getattr(c, "capability", "")) for c in candidates)
        # A MAY option is still a real common-root option.  It cannot grant a
        # strong continuation guarantee, but the ordinary bridge must retain
        # its candidate-neutral presence and emit a conservative classification
        # rather than collapsing the option set to empty.  Candidate effects
        # are categorical only; absent a source-backed invalidation, status is
        # PRESERVED (possible option remains possible), never a ranking signal.
        classifications: list[CandidateContinuation] = []
        for candidate in candidates:
            current = transition(root, _candidate_contract(candidate))
            status = "PRESERVED" if current.status is TransitionStatus.SUPPORTED else "UNKNOWN"
            classifications.append(CandidateContinuation(
                candidate_identity(candidate),
                tuple((option.identity, status) for option in modal_options),
                ("MAY_OPTION_NO_GUARANTEE",) if modal_options else (),
            ))
        return ContinuationElimination(
            identities, (), len(modal_options) or len(witness_map), root.material_fingerprint, tuple(classifications),
            0.0 if not modal_options else (sum(1 for row in classifications for _, value in row.status_by_witness if value == "UNKNOWN") / max(1, sum(len(row.status_by_witness) for row in classifications))),
            tuple((option.identity, option.modality.value, option.owners, ";".join(option.provenance)) for option in modal_options),
        )
    service_map = {service.service.semantic_identity: service for service in services}
    classifications: list[CandidateContinuation] = []
    for index, candidate in enumerate(candidates):
        candidate_id = candidate_identity(candidate)
        statuses: list[tuple[str, str]] = []
        for branch_key, witnesses in sorted(witness_map.items()):
            for witness in sorted(witnesses):
                statuses.append((f"{branch_key}:{witness}", _replay_witness(root, candidate, witness, service_map, obligations)))
        classifications.append(CandidateContinuation(candidate_id, tuple(statuses)))
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
    )
