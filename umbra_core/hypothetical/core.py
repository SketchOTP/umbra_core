"""Immutable, conservative hypothetical evidence composition.

The module intentionally models no search, ranking, selection, execution, or
learning.  It consumes only explicit immutable data supplied by a future
adapter and returns categorical transition evidence plus immutable successors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from umbra_core.self_model.engine import SupportSemantics
from umbra_core.util import canon_json, sha256_hex


BRANCH_CEILING = 32
MAX_PROVENANCE_REFS = 16
MAX_REASON_LENGTH = 96
_SUPPORTED_SEMANTICS = frozenset(
    {
        SupportSemantics.HARD_CONTRACT.value,
        SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value,
    }
)
_SEMANTIC_STRENGTH = {
    SupportSemantics.HARD_CONTRACT.value: 0,
    SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value: 1,
    SupportSemantics.PROBABILISTIC_SUPPORT.value: 2,
    SupportSemantics.UNKNOWN.value: 3,
}


class TransitionStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


class FrozenMap(Mapping[str, Any]):
    """Small deeply frozen mapping with deterministic iteration and equality."""

    __slots__ = ("_items", "_index")

    def __init__(self, source: Mapping[str, Any] | Iterable[tuple[str, Any]] = ()) -> None:
        items = source.items() if isinstance(source, Mapping) else source
        normalized = tuple(sorted((str(key), _freeze(value)) for key, value in items))
        self._items = normalized
        self._index = MappingProxyType(dict(normalized))

    def __getitem__(self, key: str) -> Any:
        return self._index[key]

    def __iter__(self):
        return iter(key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def items(self):  # type: ignore[override]
        return iter(self._items)

    def to_plain(self) -> dict[str, Any]:
        return {key: _plain(value) for key, value in self._items}

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FrozenMap) and self._items == other._items

    def __hash__(self) -> int:
        return hash(self._items)


def _freeze(value: Any) -> Any:
    if isinstance(value, FrozenMap):
        return value
    if isinstance(value, Mapping):
        return FrozenMap(value)
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, bool, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("hypothetical values must be finite")
        return value
    if hasattr(value, "to_canonical"):
        return value
    raise TypeError(f"mutable or unsupported hypothetical value: {type(value)!r}")


def _plain(value: Any) -> Any:
    if isinstance(value, FrozenMap):
        return value.to_plain()
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if hasattr(value, "to_canonical"):
        return value.to_canonical()
    return value


def _bounded_refs(refs: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(ref)[:MAX_REASON_LENGTH] for ref in refs}))[:MAX_PROVENANCE_REFS]


def _normalized_semantics(value: str) -> str:
    return value if value in _SEMANTIC_STRENGTH or value == SupportSemantics.NOT_APPLICABLE.value else SupportSemantics.UNKNOWN.value


def _weakest_semantics(values: Iterable[str]) -> str:
    applicable = [value for value in values if value != SupportSemantics.NOT_APPLICABLE.value]
    if not applicable:
        return SupportSemantics.NOT_APPLICABLE.value
    return max(applicable, key=lambda value: _SEMANTIC_STRENGTH[_normalized_semantics(value)])


def _outward_lower(value: float) -> float:
    return math.nextafter(value, -math.inf)


def _outward_upper(value: float) -> float:
    return math.nextafter(value, math.inf)


def _canonical_key(value: Any) -> str:
    return sha256_hex(canon_json(value.to_canonical() if hasattr(value, "to_canonical") else _plain(value)))


@dataclass(frozen=True)
class EvidenceEnvelope:
    """Finite numeric evidence interval, or an explicit unknown envelope."""

    minimum: float | None = None
    maximum: float | None = None
    semantics: str = SupportSemantics.UNKNOWN.value
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        semantics = _normalized_semantics(str(self.semantics))
        minimum = None if self.minimum is None else float(self.minimum)
        maximum = None if self.maximum is None else float(self.maximum)
        if minimum is None or maximum is None or not math.isfinite(minimum) or not math.isfinite(maximum) or minimum > maximum:
            minimum = maximum = None
            semantics = SupportSemantics.UNKNOWN.value
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)
        object.__setattr__(self, "semantics", semantics)
        object.__setattr__(self, "provenance", _bounded_refs(self.provenance))

    @classmethod
    def unknown(cls, *provenance: str) -> EvidenceEnvelope:
        return cls(semantics=SupportSemantics.UNKNOWN.value, provenance=provenance)

    def categorical_supported(self) -> bool:
        return self.semantics in _SUPPORTED_SEMANTICS and self.minimum is not None and self.maximum is not None

    def add(self, other: EvidenceEnvelope) -> EvidenceEnvelope:
        if self.minimum is None or self.maximum is None or other.minimum is None or other.maximum is None:
            return EvidenceEnvelope.unknown(*self.provenance, *other.provenance)
        return EvidenceEnvelope(
            minimum=_outward_lower(self.minimum + other.minimum),
            maximum=_outward_upper(self.maximum + other.maximum),
            semantics=_weakest_semantics((self.semantics, other.semantics)),
            provenance=(*self.provenance, *other.provenance),
        )

    def translate(self, offset: float) -> EvidenceEnvelope:
        return self.add(EvidenceEnvelope(float(offset), float(offset), SupportSemantics.HARD_CONTRACT.value))

    def scale(self, scalar: float) -> EvidenceEnvelope:
        if self.minimum is None or self.maximum is None or not math.isfinite(float(scalar)):
            return EvidenceEnvelope.unknown(*self.provenance)
        lo, hi = self.minimum * float(scalar), self.maximum * float(scalar)
        return EvidenceEnvelope(
            minimum=_outward_lower(min(lo, hi)),
            maximum=_outward_upper(max(lo, hi)),
            semantics=self.semantics,
            provenance=self.provenance,
        )

    def intersect(self, other: EvidenceEnvelope) -> EvidenceEnvelope:
        if self.minimum is None or self.maximum is None or other.minimum is None or other.maximum is None:
            return EvidenceEnvelope.unknown(*self.provenance, *other.provenance)
        minimum, maximum = max(self.minimum, other.minimum), min(self.maximum, other.maximum)
        if minimum > maximum:
            return EvidenceEnvelope.unknown(*self.provenance, *other.provenance)
        return EvidenceEnvelope(minimum, maximum, _weakest_semantics((self.semantics, other.semantics)), (*self.provenance, *other.provenance))

    def contains(self, value: float) -> bool:
        return self.minimum is not None and self.maximum is not None and self.minimum <= float(value) <= self.maximum

    def to_canonical(self) -> dict[str, Any]:
        return {"minimum": self.minimum, "maximum": self.maximum, "semantics": self.semantics, "provenance": list(self.provenance)}


@dataclass(frozen=True, order=True)
class DependencyToken:
    dependency_class: str
    identity: str
    version_or_hash: str

    def to_canonical(self) -> dict[str, str]:
        return {"class": self.dependency_class, "identity": self.identity, "version_or_hash": self.version_or_hash}


def dependency_fingerprint(tokens: Iterable[DependencyToken]) -> str:
    ordered = sorted(set(tokens))
    return sha256_hex(canon_json([token.to_canonical() for token in ordered]))


def dependency_fingerprint_matches(expected: str, tokens: Iterable[DependencyToken]) -> bool:
    return str(expected) == dependency_fingerprint(tokens)


@dataclass(frozen=True)
class PhysiologyBranch:
    """One complete correlated hypothetical physiology branch."""

    values: FrozenMap
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        values = self.values if isinstance(self.values, FrozenMap) else FrozenMap(self.values)
        if not all(isinstance(value, EvidenceEnvelope) for _, value in values.items()):
            raise TypeError("physiology branches require EvidenceEnvelope values")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "provenance", _bounded_refs(self.provenance))

    def apply(self, effects: Mapping[str, EvidenceEnvelope]) -> PhysiologyBranch:
        result = {name: value for name, value in self.values.items()}
        for name, effect in effects.items():
            existing = result.get(name)
            if existing is None:
                result[name] = EvidenceEnvelope.unknown(*effect.provenance)
            else:
                result[name] = existing.add(effect)
        return PhysiologyBranch(FrozenMap(result), self.provenance)

    def to_canonical(self) -> dict[str, Any]:
        return {"values": self.values.to_plain(), "provenance": list(self.provenance)}


@dataclass(frozen=True)
class OpportunityEvidence:
    identity: str
    availability: TransitionStatus
    persistence: EvidenceEnvelope
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "availability", TransitionStatus(self.availability))
        object.__setattr__(self, "provenance", _bounded_refs(self.provenance))

    def to_canonical(self) -> dict[str, Any]:
        return {"identity": self.identity, "availability": self.availability.value, "persistence": self.persistence.to_canonical(), "provenance": list(self.provenance)}


@dataclass(frozen=True)
class RouteEvidence:
    identity: str
    availability: TransitionStatus
    timing: EvidenceEnvelope
    capability: EvidenceEnvelope
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "availability", TransitionStatus(self.availability))
        object.__setattr__(self, "provenance", _bounded_refs(self.provenance))

    def to_canonical(self) -> dict[str, Any]:
        return {"identity": self.identity, "availability": self.availability.value, "timing": self.timing.to_canonical(), "capability": self.capability.to_canonical(), "provenance": list(self.provenance)}


@dataclass(frozen=True)
class HypotheticalState:
    root_tick: int
    elapsed_time: EvidenceEnvelope
    physiology_branches: tuple[PhysiologyBranch, ...]
    body_schema_identity: str
    opportunities: FrozenMap = field(default_factory=FrozenMap)
    routes: FrozenMap = field(default_factory=FrozenMap)
    pending_commitment: FrozenMap = field(default_factory=FrozenMap)
    provenance: tuple[str, ...] = ()
    dependencies: tuple[DependencyToken, ...] = ()
    material_fingerprint: str = ""
    depth: int = 0

    def __post_init__(self) -> None:
        branches = tuple(sorted(self.physiology_branches, key=_canonical_key))
        if not branches or len(branches) > BRANCH_CEILING or not all(isinstance(branch, PhysiologyBranch) for branch in branches):
            raise ValueError("hypothetical state requires bounded immutable physiology branches")
        opportunities = self.opportunities if isinstance(self.opportunities, FrozenMap) else FrozenMap(self.opportunities)
        routes = self.routes if isinstance(self.routes, FrozenMap) else FrozenMap(self.routes)
        pending = self.pending_commitment if isinstance(self.pending_commitment, FrozenMap) else FrozenMap(self.pending_commitment)
        if not all(isinstance(value, OpportunityEvidence) for _, value in opportunities.items()):
            raise TypeError("opportunities require OpportunityEvidence values")
        if not all(isinstance(value, RouteEvidence) for _, value in routes.items()):
            raise TypeError("routes require RouteEvidence values")
        dependencies = tuple(sorted(set(self.dependencies)))
        fingerprint = dependency_fingerprint(dependencies)
        if self.material_fingerprint and self.material_fingerprint != fingerprint:
            raise ValueError("material fingerprint does not match dependencies")
        object.__setattr__(self, "physiology_branches", branches)
        object.__setattr__(self, "opportunities", opportunities)
        object.__setattr__(self, "routes", routes)
        object.__setattr__(self, "pending_commitment", pending)
        object.__setattr__(self, "provenance", _bounded_refs(self.provenance))
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "material_fingerprint", fingerprint)
        object.__setattr__(self, "depth", int(self.depth))

    def valid_for(self, tokens: Iterable[DependencyToken]) -> bool:
        return dependency_fingerprint_matches(self.material_fingerprint, tokens)

    def to_canonical(self) -> dict[str, Any]:
        return {"root_tick": self.root_tick, "elapsed_time": self.elapsed_time.to_canonical(), "physiology_branches": [branch.to_canonical() for branch in self.physiology_branches], "body_schema_identity": self.body_schema_identity, "opportunities": self.opportunities.to_plain(), "routes": self.routes.to_plain(), "pending_commitment": self.pending_commitment.to_plain(), "provenance": list(self.provenance), "dependencies": [token.to_canonical() for token in self.dependencies], "material_fingerprint": self.material_fingerprint, "depth": self.depth}

    @property
    def semantic_identity(self) -> str:
        return sha256_hex(canon_json(self.to_canonical()))


@dataclass(frozen=True)
class RegulatoryService:
    semantic_identity: str
    owners: tuple[str, ...]
    terminal_capability: str
    opportunity_identity: str | None
    route_identity: str | None
    duration: EvidenceEnvelope
    effect_branches: tuple[FrozenMap, ...]
    body_schema_identity: str
    preconditions: tuple[EvidenceEnvelope, ...] = ()
    provenance: tuple[str, ...] = ()
    availability: TransitionStatus = TransitionStatus.UNKNOWN
    dependencies: tuple[DependencyToken, ...] = ()

    def __post_init__(self) -> None:
        branches = tuple(sorted((branch if isinstance(branch, FrozenMap) else FrozenMap(branch) for branch in self.effect_branches), key=_canonical_key))
        if not branches or len(branches) > 2:
            raise ValueError("a service must retain one or two authoritative effect branches")
        if not all(isinstance(value, EvidenceEnvelope) for branch in branches for _, value in branch.items()):
            raise TypeError("service effect branches require EvidenceEnvelope values")
        object.__setattr__(self, "owners", tuple(sorted({str(owner) for owner in self.owners})))
        object.__setattr__(self, "effect_branches", branches)
        object.__setattr__(self, "preconditions", tuple(self.preconditions))
        object.__setattr__(self, "provenance", _bounded_refs(self.provenance))
        object.__setattr__(self, "availability", TransitionStatus(self.availability))
        object.__setattr__(self, "dependencies", tuple(sorted(set(self.dependencies))))

    def to_canonical(self) -> dict[str, Any]:
        return {"semantic_identity": self.semantic_identity, "owners": list(self.owners), "terminal_capability": self.terminal_capability, "opportunity_identity": self.opportunity_identity, "route_identity": self.route_identity, "duration": self.duration.to_canonical(), "effect_branches": [branch.to_plain() for branch in self.effect_branches], "body_schema_identity": self.body_schema_identity, "preconditions": [item.to_canonical() for item in self.preconditions], "provenance": list(self.provenance), "availability": self.availability.value, "dependencies": [token.to_canonical() for token in self.dependencies]}


@dataclass(frozen=True)
class ValidatedRegulatoryService:
    service: RegulatoryService
    dependencies: tuple[DependencyToken, ...]


@dataclass(frozen=True)
class TransitionContract:
    semantic_identity: str
    duration: EvidenceEnvelope
    effect_branches: tuple[FrozenMap, ...]
    required_evidence: tuple[EvidenceEnvelope, ...] = ()
    opportunity_identity: str | None = None
    route_identity: str | None = None
    availability: TransitionStatus = TransitionStatus.SUPPORTED
    service: ValidatedRegulatoryService | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        branches = tuple(sorted((branch if isinstance(branch, FrozenMap) else FrozenMap(branch) for branch in self.effect_branches), key=_canonical_key))
        if not branches or len(branches) > 2:
            raise ValueError("transition must retain one or two effect branches")
        if not all(isinstance(value, EvidenceEnvelope) for branch in branches for _, value in branch.items()):
            raise TypeError("transition effect branches require EvidenceEnvelope values")
        object.__setattr__(self, "effect_branches", branches)
        object.__setattr__(self, "required_evidence", tuple(self.required_evidence))
        object.__setattr__(self, "availability", TransitionStatus(self.availability))
        object.__setattr__(self, "provenance", _bounded_refs(self.provenance))


@dataclass(frozen=True)
class TransitionResult:
    status: TransitionStatus
    successors: tuple[HypotheticalState, ...]
    reason: str
    provenance: tuple[str, ...] = ()
    dependencies: tuple[DependencyToken, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", TransitionStatus(self.status))
        object.__setattr__(self, "successors", tuple(self.successors))
        object.__setattr__(self, "reason", str(self.reason)[:MAX_REASON_LENGTH])
        object.__setattr__(self, "provenance", _bounded_refs(self.provenance))
        object.__setattr__(self, "dependencies", tuple(sorted(set(self.dependencies))))


def _unknown(reason: str, *provenance: str, dependencies: Iterable[DependencyToken] = ()) -> TransitionResult:
    return TransitionResult(TransitionStatus.UNKNOWN, (), reason, provenance, tuple(dependencies))


def validate_regulatory_service(service: RegulatoryService) -> TransitionResult | ValidatedRegulatoryService:
    if service.availability is TransitionStatus.UNSUPPORTED:
        return TransitionResult(TransitionStatus.UNSUPPORTED, (), "SERVICE_KNOWN_UNAVAILABLE", service.provenance, service.dependencies)
    required = (service.duration, *service.preconditions, *(value for branch in service.effect_branches for _, value in branch.items()))
    if service.availability is not TransitionStatus.SUPPORTED or not all(envelope.categorical_supported() for envelope in required):
        return _unknown("SERVICE_EVIDENCE_INSUFFICIENT", *service.provenance, dependencies=service.dependencies)
    return ValidatedRegulatoryService(service, service.dependencies)


def _availability_result(value: TransitionStatus, unknown_reason: str, unsupported_reason: str, provenance: Iterable[str], dependencies: Iterable[DependencyToken]) -> TransitionResult | None:
    if value is TransitionStatus.UNSUPPORTED:
        return TransitionResult(TransitionStatus.UNSUPPORTED, (), unsupported_reason, tuple(provenance), tuple(dependencies))
    if value is TransitionStatus.UNKNOWN:
        return _unknown(unknown_reason, *tuple(provenance), dependencies=dependencies)
    return None


def transition(state: HypotheticalState, contract: TransitionContract) -> TransitionResult:
    """Compose one explicitly supplied hypothetical transition without side effects."""
    first = _availability_result(contract.availability, "TRANSITION_AVAILABILITY_UNKNOWN", "TRANSITION_KNOWN_UNAVAILABLE", contract.provenance, state.dependencies)
    if first is not None:
        return first
    if not state.elapsed_time.categorical_supported():
        return _unknown("STATE_TIMING_UNKNOWN", *state.provenance, dependencies=state.dependencies)
    effective_opportunity = contract.opportunity_identity
    effective_route = contract.route_identity
    dependencies = state.dependencies
    if contract.service is not None:
        service = contract.service.service
        if service.body_schema_identity != state.body_schema_identity:
            return _unknown("SERVICE_BODY_SCHEMA_MISMATCH", *contract.provenance, dependencies=state.dependencies)
        if contract.duration != service.duration or contract.effect_branches != service.effect_branches:
            return _unknown("SERVICE_CONTRACT_MISMATCH", *contract.provenance, dependencies=state.dependencies)
        if effective_opportunity not in (None, service.opportunity_identity) or effective_route not in (None, service.route_identity):
            return _unknown("SERVICE_CONTRACT_MISMATCH", *contract.provenance, dependencies=state.dependencies)
        effective_opportunity = service.opportunity_identity
        effective_route = service.route_identity
        dependencies = tuple(sorted(set((*state.dependencies, *contract.service.dependencies))))
    required = (contract.duration, *contract.required_evidence, *(value for branch in contract.effect_branches for _, value in branch.items()))
    if not all(envelope.categorical_supported() for envelope in required):
        return _unknown("REQUIRED_EVIDENCE_NOT_CATEGORICAL", *contract.provenance, dependencies=state.dependencies)
    if effective_opportunity is not None:
        opportunity = state.opportunities.get(effective_opportunity)
        if opportunity is None:
            return _unknown("OPPORTUNITY_PERSISTENCE_UNKNOWN", *contract.provenance, dependencies=state.dependencies)
        result = _availability_result(opportunity.availability, "OPPORTUNITY_PERSISTENCE_UNKNOWN", "OPPORTUNITY_KNOWN_UNAVAILABLE", opportunity.provenance, state.dependencies)
        if result is not None:
            return result
        if not opportunity.persistence.categorical_supported():
            return _unknown("OPPORTUNITY_PERSISTENCE_UNKNOWN", *opportunity.provenance, dependencies=state.dependencies)
    if effective_route is not None:
        route = state.routes.get(effective_route)
        if route is None:
            return _unknown("ROUTE_SUPPORT_UNKNOWN", *contract.provenance, dependencies=state.dependencies)
        result = _availability_result(route.availability, "ROUTE_SUPPORT_UNKNOWN", "ROUTE_KNOWN_UNAVAILABLE", route.provenance, state.dependencies)
        if result is not None:
            return result
        if not route.timing.categorical_supported() or not route.capability.categorical_supported():
            return _unknown("ROUTE_SUPPORT_UNKNOWN", *route.provenance, dependencies=state.dependencies)
    total = len(state.physiology_branches) * len(contract.effect_branches)
    if total > BRANCH_CEILING:
        return _unknown("BRANCH_CEILING_EXCEEDED", *contract.provenance, dependencies=state.dependencies)
    successors = []
    for branch in state.physiology_branches:
        for effects in contract.effect_branches:
            if any(
                not branch.values.get(name, EvidenceEnvelope.unknown()).categorical_supported()
                for name, _ in effects.items()
            ):
                return _unknown("STATE_EFFECT_FIELD_UNKNOWN", *contract.provenance, dependencies=dependencies)
            successors.append(HypotheticalState(root_tick=state.root_tick, elapsed_time=state.elapsed_time.add(contract.duration), physiology_branches=(branch.apply(effects),), body_schema_identity=state.body_schema_identity, opportunities=state.opportunities, routes=state.routes, pending_commitment=state.pending_commitment, provenance=(*state.provenance, *contract.provenance), dependencies=dependencies, depth=state.depth + 1))
    return TransitionResult(TransitionStatus.SUPPORTED, tuple(successors), "SUPPORTED_TRANSITION", (*state.provenance, *contract.provenance), dependencies)
