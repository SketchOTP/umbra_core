"""Pure source-contract probes for UMBRA-AS-003P-R6A.

The functions in this module operate on plain mappings only.  They do not
import ``umbra_core``, execute owners, consume RNG, or grant action authority.
They model what can be said conservatively from source evidence; observed
motion is never promoted to a hard future route guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Any, Mapping


class Strength(StrEnum):
    HARD_CONTRACT = "HARD_CONTRACT"
    VERIFIED_OBSERVED_SUPPORT = "VERIFIED_OBSERVED_SUPPORT"
    PROBABILISTIC_SUPPORT = "PROBABILISTIC_SUPPORT"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RouteDisposition(StrEnum):
    SUPPORTED_HARD_BOUND = "SUPPORTED_HARD_BOUND"
    SUPPORTED_OBSERVED_ENVELOPE = "SUPPORTED_OBSERVED_ENVELOPE"
    MAY_ROUTE_ENVELOPE = "MAY_ROUTE_ENVELOPE"
    UNKNOWN_ROUTE_DEMAND = "UNKNOWN_ROUTE_DEMAND"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class TimingDisposition(StrEnum):
    ONE_TICK_HARD_CONTRACT = "ONE_TICK_HARD_CONTRACT"
    SOURCE_BACKED_INTERVAL = "SOURCE_BACKED_INTERVAL"
    CAPABILITY_SPECIFIC = "CAPABILITY_SPECIFIC"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RouteDemand:
    disposition: RouteDisposition
    minimum_executions: int | None
    maximum_executions: int | None
    reason: str
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True)
class InspectOpportunity:
    status: str
    instance_id: str | None
    reason: str
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True)
class TimingResult:
    disposition: TimingDisposition
    minimum_ticks: int | None
    maximum_ticks: int | None
    reason: str


def derive_route_demand(
    *,
    distance_upper_bound: float | None,
    progress_minimum: float | None,
    distance_semantics: Strength,
    progress_semantics: Strength,
    body_schema_matches: bool,
    route_geometry_established: bool,
    remembered_opportunity: bool = False,
    route_blocked: bool = False,
    provenance: tuple[str, ...] = (),
) -> RouteDemand:
    """Assess the tempting distance/progress quotient without overclaiming.

    A quotient is a hard bound only when both geometry and motion are explicit
    hard contracts.  Existing UMBRA source fields are observed/body-relative,
    so they conservatively remain unknown for robust future scheduling.
    """
    if not body_schema_matches:
        return RouteDemand(RouteDisposition.UNKNOWN_ROUTE_DEMAND, None, None,
                           "BODY_SCHEMA_MISMATCH", provenance)
    if route_blocked:
        return RouteDemand(RouteDisposition.UNKNOWN_ROUTE_DEMAND, None, None,
                           "ROUTE_BLOCKED_OR_UNRESOLVED", provenance)
    if distance_upper_bound is None or not math.isfinite(distance_upper_bound) or distance_upper_bound < 0:
        return RouteDemand(RouteDisposition.UNKNOWN_ROUTE_DEMAND, None, None,
                           "DISTANCE_SUPPORT_MISSING", provenance)
    if progress_minimum is None or not math.isfinite(progress_minimum) or progress_minimum <= 0:
        return RouteDemand(RouteDisposition.UNKNOWN_ROUTE_DEMAND, None, None,
                           "NONPOSITIVE_PROGRESS_LOWER_BOUND", provenance)
    if remembered_opportunity and distance_semantics is not Strength.HARD_CONTRACT:
        return RouteDemand(RouteDisposition.UNKNOWN_ROUTE_DEMAND, None, None,
                           "REMEMBERED_ROUTE_NOT_GUARANTEED", provenance)
    if distance_semantics is Strength.UNKNOWN or progress_semantics is Strength.UNKNOWN:
        return RouteDemand(RouteDisposition.UNKNOWN_ROUTE_DEMAND, None, None,
                           "SOURCE_UNKNOWN", provenance)
    executions = max(0, math.ceil(distance_upper_bound / progress_minimum))
    if (
        distance_semantics is Strength.HARD_CONTRACT
        and progress_semantics is Strength.HARD_CONTRACT
        and route_geometry_established
    ):
        return RouteDemand(RouteDisposition.SUPPORTED_HARD_BOUND, executions, executions,
                           "EXPLICIT_HARD_GEOMETRY_AND_MOTION_CONTRACT", provenance)
    if route_geometry_established and progress_semantics is Strength.VERIFIED_OBSERVED_SUPPORT:
        return RouteDemand(RouteDisposition.MAY_ROUTE_ENVELOPE, None, executions,
                           "OBSERVED_PROGRESS_CANNOT_GUARANTEE_FUTURE_MINIMUM", provenance)
    return RouteDemand(RouteDisposition.UNKNOWN_ROUTE_DEMAND, None, None,
                       "TRAVERSABLE_ROUTE_OR_FUTURE_MOTION_NOT_ESTABLISHED", provenance)


def inspect_opportunity(
    *,
    instance_id: str | None,
    entity_kind: str | None,
    affordance_action: str | None,
    affordance_status: str | None,
    affordance_strength: Strength,
    body_schema_matches: bool,
    provenance: tuple[str, ...] = (),
) -> InspectOpportunity:
    """Join an actual policy-visible instance to a lawful inspect belief."""
    if not body_schema_matches:
        return InspectOpportunity("UNKNOWN", None, "BODY_SCHEMA_MISMATCH", provenance)
    if not instance_id or not entity_kind:
        return InspectOpportunity("UNKNOWN", None, "INSTANCE_REQUIRED", provenance)
    if entity_kind != "inspect" and affordance_action != "inspect":
        return InspectOpportunity("NOT_APPLICABLE", None, "NO_INSPECT_SEMANTIC", provenance)
    if affordance_action != "inspect":
        return InspectOpportunity("UNKNOWN", None, "INSPECT_AFFORDANCE_MISSING", provenance)
    if affordance_status in {"WEAKENED", "SUPERSEDED"}:
        return InspectOpportunity("UNKNOWN", instance_id, "AFFORDANCE_NOT_ACTIVE", provenance)
    if affordance_status != "ACTIVE":
        return InspectOpportunity("UNKNOWN", instance_id, "AFFORDANCE_STATUS_UNKNOWN", provenance)
    if affordance_strength is not Strength.HARD_CONTRACT and affordance_strength is not Strength.VERIFIED_OBSERVED_SUPPORT:
        return InspectOpportunity("UNKNOWN", instance_id, "AFFORDANCE_SUPPORT_INSUFFICIENT", provenance)
    return InspectOpportunity("SUPPORTED", instance_id, "INSTANCE_AND_ACTIVE_AFFORDANCE", provenance)


def terminal_timing(
    capability: str,
    *,
    explicit_contract_ticks: int | None = None,
    learned_interval: tuple[int, int] | None = None,
) -> TimingResult:
    """Resolve timing only from an explicit source, never from a point default."""
    if explicit_contract_ticks is not None and explicit_contract_ticks >= 0:
        return TimingResult(TimingDisposition.ONE_TICK_HARD_CONTRACT if explicit_contract_ticks == 1 else TimingDisposition.CAPABILITY_SPECIFIC,
                            explicit_contract_ticks, explicit_contract_ticks,
                            "EXPLICIT_TERMINAL_SERVICE_CONTRACT")
    if learned_interval is not None and 0 <= learned_interval[0] <= learned_interval[1]:
        return TimingResult(TimingDisposition.SOURCE_BACKED_INTERVAL,
                            learned_interval[0], learned_interval[1],
                            "VERIFIED_SERVICE_TIMING_INTERVAL")
    return TimingResult(TimingDisposition.UNKNOWN, None, None,
                        f"NO_SOURCE_BACKED_TIMING:{capability}")


def source_weakening_never_strengthens(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    """Small pure monotonicity check used by adversarial tests."""
    order = {
        Strength.UNKNOWN.value: 0,
        Strength.PROBABILISTIC_SUPPORT.value: 1,
        Strength.VERIFIED_OBSERVED_SUPPORT.value: 2,
        Strength.HARD_CONTRACT.value: 3,
    }
    return order.get(str(after.get("semantics")), 0) <= order.get(str(before.get("semantics")), 0)
