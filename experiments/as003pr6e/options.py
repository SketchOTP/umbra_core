"""Pure known-recovery-option preservation relation for AS-003P-R6E.

This module is deliberately detached from ``umbra_core`` and from the frozen R6
L2 implementation. It models only immutable source-backed option identities,
candidate consequences, three-valued status, and the resulting partial relation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class SupportVariantStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


class OptionStatus(str, Enum):
    PRESERVED = "PRESERVED"
    DESTROYED = "DESTROYED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SupportVariant:
    """One observed support realization for a semantic recovery option."""

    variant_id: str
    observed_total_demand: int
    opportunity_horizon: int
    body_schema_id: str
    source_dependencies: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    evidence_id: str = ""
    confidence: str = ""

    def __post_init__(self) -> None:
        if self.observed_total_demand < 0:
            raise ValueError("negative observed demand")
        if self.opportunity_horizon < 0:
            raise ValueError("negative opportunity horizon")


@dataclass(frozen=True)
class SupportedRecoveryOption:
    """A semantic service strategy, with one or more empirical support variants."""

    root_frame_identity: str
    active_obligation_signature: tuple[str, ...]
    body_schema_id: str
    ordered_terminal_services: tuple[str, ...]
    exact_opportunity_identities: tuple[str, ...]
    owner_coverage: tuple[str, ...]
    required_effect_semantics: tuple[tuple[str, str], ...]
    relevant_opportunity_horizons: tuple[tuple[str, int], ...]
    source_dependencies: tuple[str, ...]
    support_variants: tuple[SupportVariant, ...]
    terminal_service_semantics: tuple[tuple[str, str], ...] = ()
    provenance: tuple[str, ...] = ()

    @property
    def semantic_identity(self) -> tuple[object, ...]:
        """Identity excluding evidence IDs, confidence, provenance, and samples."""
        return (
            self.root_frame_identity,
            self.active_obligation_signature,
            self.body_schema_id,
            self.ordered_terminal_services,
            self.exact_opportunity_identities,
            tuple(sorted(self.owner_coverage)),
            self.required_effect_semantics,
            self.relevant_opportunity_horizons,
            tuple(sorted(self.source_dependencies)),
            self.terminal_service_semantics,
        )


@dataclass(frozen=True)
class CandidateBranch:
    branch_id: str
    elapsed_ticks: int = 0
    body_schema_id: str | None = None
    invalidated_dependencies: tuple[str, ...] = ()
    unknown_dependencies: tuple[str, ...] = ()
    unknown_opportunities: tuple[str, ...] = ()
    horizon_overrides: tuple[tuple[str, int], ...] = ()
    supported: bool = True

    def __post_init__(self) -> None:
        if self.elapsed_ticks < 0:
            raise ValueError("negative candidate elapsed ticks")

    def horizon_for(self, opportunity: str, default: int) -> int | None:
        if opportunity in self.unknown_opportunities:
            return None
        for key, horizon in self.horizon_overrides:
            if key == opportunity:
                return horizon
        return default


@dataclass(frozen=True)
class CandidateProjection:
    candidate_id: str
    root_frame_identity: str
    residual_obligation_signature: tuple[str, ...]
    ordinary_hard_admissible: bool
    branches: tuple[CandidateBranch, ...]


@dataclass(frozen=True)
class VariantAssessment:
    variant_id: str
    branch_statuses: tuple[tuple[str, SupportVariantStatus, str], ...]
    status: SupportVariantStatus


@dataclass(frozen=True)
class OptionAssessment:
    option_identity: tuple[object, ...]
    status: OptionStatus
    variants: tuple[VariantAssessment, ...]


@dataclass(frozen=True)
class RelationResult:
    relates: bool
    reason: str
    option_pairs: tuple[tuple[tuple[object, ...], OptionStatus, OptionStatus], ...]
    strict_option_identities: tuple[tuple[object, ...], ...] = ()


def deduplicate_options(options: Iterable[SupportedRecoveryOption]) -> tuple[SupportedRecoveryOption, ...]:
    """Collapse semantic duplicates without using evidence volume or confidence."""
    result: list[SupportedRecoveryOption] = []
    seen: set[tuple[object, ...]] = set()
    for option in options:
        identity = option.semantic_identity
        if identity not in seen:
            seen.add(identity)
            result.append(option)
    return tuple(result)


def assess_variant(option: SupportedRecoveryOption, variant: SupportVariant, branch: CandidateBranch) -> tuple[SupportVariantStatus, str]:
    if not branch.supported:
        return SupportVariantStatus.INFEASIBLE, "UNSUPPORTED_CANDIDATE_BRANCH"
    if branch.body_schema_id is not None and branch.body_schema_id != option.body_schema_id:
        return SupportVariantStatus.INFEASIBLE, "BODY_SCHEMA_INVALIDATED"
    if set(variant.source_dependencies) & set(branch.invalidated_dependencies):
        return SupportVariantStatus.INFEASIBLE, "SOURCE_DEPENDENCY_INVALIDATED"
    if set(variant.source_dependencies) & set(branch.unknown_dependencies):
        return SupportVariantStatus.UNKNOWN, "SOURCE_DEPENDENCY_UNKNOWN"
    total_demand = variant.observed_total_demand + branch.elapsed_ticks
    for opportunity, default_horizon in option.relevant_opportunity_horizons:
        horizon = branch.horizon_for(opportunity, default_horizon)
        if horizon is None:
            return SupportVariantStatus.UNKNOWN, "OPPORTUNITY_APPLICABILITY_UNKNOWN"
        if total_demand > horizon:
            return SupportVariantStatus.INFEASIBLE, "KNOWN_SUPPORT_EXCEEDS_REMAINING_HORIZON"
    return SupportVariantStatus.FEASIBLE, "KNOWN_SUPPORT_REMAINS_FEASIBLE"


def assess_option(option: SupportedRecoveryOption, candidate: CandidateProjection) -> OptionAssessment:
    variant_assessments: list[VariantAssessment] = []
    for variant in option.support_variants:
        branch_results = tuple(
            (branch.branch_id, *assess_variant(option, variant, branch))
            for branch in candidate.branches
        )
        statuses = tuple(result[1] for result in branch_results)
        if statuses and all(status is SupportVariantStatus.FEASIBLE for status in statuses):
            variant_status = SupportVariantStatus.FEASIBLE
        elif any(status is SupportVariantStatus.INFEASIBLE for status in statuses):
            variant_status = SupportVariantStatus.INFEASIBLE
        else:
            variant_status = SupportVariantStatus.UNKNOWN
        variant_assessments.append(VariantAssessment(variant.variant_id, branch_results, variant_status))

    if any(variant.status is SupportVariantStatus.FEASIBLE for variant in variant_assessments):
        status = OptionStatus.PRESERVED
    elif variant_assessments and all(variant.status is SupportVariantStatus.INFEASIBLE for variant in variant_assessments):
        status = OptionStatus.DESTROYED
    else:
        status = OptionStatus.UNKNOWN
    return OptionAssessment(option.semantic_identity, status, tuple(variant_assessments))


def assess_options(options: Iterable[SupportedRecoveryOption], candidate: CandidateProjection) -> tuple[OptionAssessment, ...]:
    return tuple(assess_option(option, candidate) for option in deduplicate_options(options))


def known_option_precedes(
    options: Iterable[SupportedRecoveryOption],
    candidate_a: CandidateProjection,
    candidate_b: CandidateProjection,
) -> RelationResult:
    """Evaluate strict known-option preservation with a common root option set."""
    root_options = deduplicate_options(options)
    if not root_options:
        return RelationResult(False, "ROOT_OPTION_SET_EMPTY", ())
    if candidate_a.root_frame_identity != candidate_b.root_frame_identity:
        return RelationResult(False, "ROOT_FRAME_MISMATCH", ())
    if candidate_a.residual_obligation_signature != candidate_b.residual_obligation_signature:
        return RelationResult(False, "INCOMPARABLE_OBLIGATION_SIGNATURE", ())
    if not candidate_a.ordinary_hard_admissible or not candidate_b.ordinary_hard_admissible:
        return RelationResult(False, "HARD_AUTHORITY_PREEMPTED", ())

    statuses_a = {assessment.option_identity: assessment for assessment in assess_options(root_options, candidate_a)}
    statuses_b = {assessment.option_identity: assessment for assessment in assess_options(root_options, candidate_b)}
    pairs = tuple(
        (identity, statuses_a[identity].status, statuses_b[identity].status)
        for identity in statuses_a
    )
    strict: list[tuple[object, ...]] = []
    for identity, status_a, status_b in pairs:
        if status_a is OptionStatus.PRESERVED and status_b is OptionStatus.DESTROYED:
            strict.append(identity)
            continue
        if status_a is status_b:
            continue
        return RelationResult(False, _blocked_reason(status_a, status_b), pairs)
    if not strict:
        return RelationResult(False, "NO_STRICT_KNOWN_OPTION_PRESERVATION", pairs)
    return RelationResult(True, "KNOWN_OPTION_PRESERVATION", pairs, tuple(strict))


def _blocked_reason(status_a: OptionStatus, status_b: OptionStatus) -> str:
    if status_a is OptionStatus.UNKNOWN or status_b is OptionStatus.UNKNOWN:
        return "ASYMMETRIC_UNKNOWN"
    if status_a is OptionStatus.DESTROYED and status_b is OptionStatus.PRESERVED:
        return "CONVERSE_OPTION_LOSS"
    return "UNALLOWED_STATUS_PAIR"
