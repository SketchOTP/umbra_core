"""Pure bounded modal continuation profiles for AS-003P.

Modal labels describe source strength only. They are never compared as values,
used to rank candidates, or returned to action selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from umbra_core.physiology import verified_outcome_effect_branches
from umbra_core.self_model.engine import SupportSemantics

from .adapters import capability_transition_contract, root_state_from_sources
from .core import BRANCH_CEILING, EvidenceEnvelope, FrozenMap, TransitionContract, TransitionStatus, transition
from .frame import PlanningEvidenceFrame, PlanningModality


class ContinuationClass(str, Enum):
    STRONG_MUST = "STRONG_MUST_CONTINUATION"
    STRONG_MAY = "STRONG_MAY_CONTINUATION"
    WEAK_MAY = "WEAK_MAY_CONTINUATION"
    NO_CONTINUATION = "NO_CONTINUATION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ModalService:
    identity: str
    capability: str
    owners: tuple[str, ...]
    opportunity_identity: str
    requirements: tuple[PlanningModality, ...]
    contract: TransitionContract
    allowed_branch_indexes: tuple[int, ...] | None = None

    @property
    def modality(self) -> PlanningModality:
        if PlanningModality.UNSUPPORTED in self.requirements:
            return PlanningModality.UNSUPPORTED
        if PlanningModality.UNKNOWN in self.requirements:
            return PlanningModality.UNKNOWN
        if PlanningModality.MAY in self.requirements:
            return PlanningModality.MAY
        return PlanningModality.MUST


@dataclass(frozen=True)
class ModalContinuationProfile:
    classification: ContinuationClass
    reason: str
    branch_witnesses: tuple[tuple[int, str, str], ...] = ()
    branch_results: tuple[str, ...] = ()
    max_active_paths: int = 0

    def to_canonical(self) -> dict[str, Any]:
        return {
            "classification": self.classification.value,
            "reason": self.reason,
            "branch_witnesses": [list(row) for row in self.branch_witnesses],
            "branch_results": list(self.branch_results),
            "max_active_paths": self.max_active_paths,
        }


@dataclass(frozen=True)
class PhysicalFrontierBound:
    status: TransitionStatus
    active_paths: int
    reason: str


def physical_frontier_bound(branch_counts: Iterable[int]) -> PhysicalFrontierBound:
    """Prove the locked global physical-path ceiling without expanding paths."""
    active_paths = 1
    for count in branch_counts:
        count = int(count)
        if count < 1 or count > 2:
            return PhysicalFrontierBound(TransitionStatus.UNKNOWN, active_paths, "INVALID_PHYSICAL_BRANCH_COUNT")
        active_paths *= count
        if active_paths > BRANCH_CEILING:
            return PhysicalFrontierBound(TransitionStatus.UNKNOWN, active_paths, "BRANCH_FRONTIER_EXCEEDED")
    return PhysicalFrontierBound(TransitionStatus.SUPPORTED, active_paths, "BRANCH_FRONTIER_WITHIN_BOUND")


def _hard_duration(ticks: int, capability: str) -> EvidenceEnvelope:
    return EvidenceEnvelope(float(ticks), float(ticks), SupportSemantics.HARD_CONTRACT.value, (f"runtime-timing:{capability}",))


def _modality(row: Mapping[str, Any] | None) -> PlanningModality:
    if not row:
        return PlanningModality.UNKNOWN
    return PlanningModality(str(row.get("modality", PlanningModality.UNKNOWN.value)))


def modal_services_from_frame(frame: PlanningEvidenceFrame) -> tuple[ModalService, ...]:
    capability_map = frame.constitutional_capabilities.to_plain()
    opportunity_map = frame.opportunities.to_plain()
    route_map = frame.route_support.to_plain()
    timing_map = frame.service_timing.to_plain()
    owners = {"CHARGE": ("energy",), "REST": ("fatigue", "integrity"), "INSPECT": ("stimulation",)}
    kinds = {"CHARGE": {"resource", "novel_crystal"}, "REST": {"rest"}, "INSPECT": {"inspect"}}
    services: list[ModalService] = []
    for opportunity_identity, opportunity in sorted(opportunity_map.items()):
        kind = str(opportunity.get("kind", ""))
        for capability in ("CHARGE", "REST", "INSPECT"):
            if kind not in kinds[capability]:
                continue
            capability_modality = _modality(capability_map.get(capability))
            opportunity_modality = _modality(opportunity.get("future"))
            route_modality = _modality(route_map.get(opportunity_identity))
            timing_modality = _modality(timing_map.get(capability))
            completion = int(dict(timing_map.get(capability, {}).get("value") or {}).get("completion_ticks", 0))
            contract = capability_transition_contract(capability, duration=_hard_duration(completion, capability))
            services.append(ModalService(
                identity=f"modal-service:{capability}:{opportunity_identity}",
                capability=capability,
                owners=owners[capability],
                opportunity_identity=opportunity_identity,
                requirements=(capability_modality, opportunity_modality, route_modality, timing_modality),
                contract=contract,
            ))
    return tuple(services)


def candidate_contract(capability: str, completion_ticks: int = 0) -> TransitionContract:
    return capability_transition_contract(str(capability), duration=_hard_duration(completion_ticks, str(capability)))


def _root(frame: PlanningEvidenceFrame):
    return root_state_from_sources(
        root_tick=frame.organism_age,
        physiology=frame.physiology_root.to_plain(),
        body_schema_identity=str(frame.body.to_plain().get("body_schema_identity", "unknown")),
        body_schema_version=str(frame.body.to_plain().get("body_schema_version", "unknown")),
        pending_commitment=frame.pending_execution.to_plain(),
    )


def modal_continuation_profile(
    frame: PlanningEvidenceFrame,
    current_candidate: TransitionContract,
    services: Iterable[ModalService],
) -> ModalContinuationProfile:
    if any(bool(value) for value in frame.pending_execution.to_plain().values() if value not in (None, False, 0, {}, [])):
        return ModalContinuationProfile(ContinuationClass.UNKNOWN, "PENDING_EXECUTION_CONSTRAINS_FRESH_ACTION")
    current = transition(_root(frame), current_candidate)
    if current.status is not TransitionStatus.SUPPORTED:
        return ModalContinuationProfile(ContinuationClass.UNKNOWN, f"CURRENT_{current.reason}", max_active_paths=len(current.successors))
    available = tuple(services)
    max_paths = len(current.successors)
    branch_results: list[str] = []
    witnesses: list[tuple[int, str, str]] = []
    for index, branch in enumerate(current.successors):
        best: tuple[PlanningModality, str] | None = None
        unknown = False
        for service in available:
            if service.allowed_branch_indexes is not None and index not in service.allowed_branch_indexes:
                continue
            modality = service.modality
            if modality is PlanningModality.UNKNOWN:
                unknown = True
                continue
            if modality is PlanningModality.UNSUPPORTED:
                continue
            result = transition(branch, service.contract)
            frontier = physical_frontier_bound((len(current.successors), max(1, len(result.successors))))
            max_paths = max(max_paths, frontier.active_paths)
            if frontier.status is not TransitionStatus.SUPPORTED:
                return ModalContinuationProfile(ContinuationClass.UNKNOWN, frontier.reason, max_active_paths=max_paths)
            if result.status is TransitionStatus.SUPPORTED:
                if best is None or (best[0] is PlanningModality.MAY and modality is PlanningModality.MUST):
                    best = (modality, service.identity)
        if best is not None:
            branch_results.append(best[0].value)
            witnesses.append((index, best[1], best[0].value))
        elif unknown:
            branch_results.append(PlanningModality.UNKNOWN.value)
        else:
            branch_results.append(PlanningModality.UNSUPPORTED.value)
    result_set = set(branch_results)
    if result_set == {PlanningModality.MUST.value}:
        classification, reason = ContinuationClass.STRONG_MUST, "ALL_BRANCHES_HAVE_MUST_WITNESS"
    elif result_set.issubset({PlanningModality.MUST.value, PlanningModality.MAY.value}) and PlanningModality.MAY.value in result_set:
        classification, reason = ContinuationClass.STRONG_MAY, "ALL_BRANCHES_HAVE_MODAL_WITNESS"
    elif PlanningModality.UNKNOWN.value in result_set:
        classification, reason = ContinuationClass.UNKNOWN, "BRANCH_EVIDENCE_UNKNOWN"
    elif result_set & {PlanningModality.MUST.value, PlanningModality.MAY.value}:
        classification, reason = ContinuationClass.WEAK_MAY, "ONLY_SOME_BRANCHES_HAVE_WITNESS"
    else:
        classification, reason = ContinuationClass.NO_CONTINUATION, "NO_BRANCH_HAS_WITNESS"
    return ModalContinuationProfile(classification, reason, tuple(witnesses), tuple(branch_results), max_paths)


def profiles_for_candidate_views(
    frame: PlanningEvidenceFrame,
    views: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    bound = frame.bind_candidates(views)
    services = modal_services_from_frame(bound)
    rows = []
    timings = bound.service_timing.to_plain()
    for view in sorted(views, key=lambda row: str(row.get("identity", ""))):
        capability = str(view.get("capability", ""))
        completion = int(dict(timings.get(capability, {}).get("value") or {}).get("completion_ticks", 0))
        profile = modal_continuation_profile(bound, candidate_contract(capability, completion), services)
        rows.append({
            "candidate_identity": str(view.get("identity", "")),
            "capability": capability,
            "profile": profile.to_canonical(),
            "frame_fingerprint": bound.material_fingerprint,
            "candidate_frame_identity": bound.candidate_frame_identity,
        })
    return tuple(rows)
