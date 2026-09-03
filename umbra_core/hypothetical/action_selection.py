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


def _owner_active(frame: PlanningEvidenceFrame, owner: str, bounds: Any) -> bool:
    raw = frame.physiology_root.to_plain().get(owner)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return True
    return not bounds.in_viable(value)


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
    o0 = root_continuation_set(root, services, obligations=obligations, max_depth=MAX_CONTINUATION_DEPTH) if obligations else ContinuationSet(())
    witness_map = dict(o0.witnesses_by_branch)
    if not witness_map or not candidates:
        identities = tuple(str(getattr(c, "capability", "")) for c in candidates)
        return ContinuationElimination(identities, (), len(witness_map), root.material_fingerprint, (), 0.0)
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
    return ContinuationElimination(survivors, tuple(sorted(set(eliminated))), len(witness_map), root.material_fingerprint, tuple(classifications), unknown / total if total else 0.0)
