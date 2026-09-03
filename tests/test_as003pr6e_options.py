from __future__ import annotations

from experiments.as003pr6e.options import (
    CandidateBranch,
    CandidateProjection,
    OptionStatus,
    SupportVariant,
    SupportedRecoveryOption,
    SupportVariantStatus,
    assess_option,
    deduplicate_options,
    known_option_precedes,
)


def option(*, demand: int = 7, evidence_id: str = "e1", provenance: tuple[str, ...] = ("p1",)) -> SupportedRecoveryOption:
    return SupportedRecoveryOption(
        root_frame_identity="root",
        active_obligation_signature=("energy",),
        body_schema_id="body",
        ordered_terminal_services=("CHARGE",),
        exact_opportunity_identities=("opp",),
        owner_coverage=("energy",),
        required_effect_semantics=(("energy", "recover"),),
        relevant_opportunity_horizons=(("opp", 8),),
        source_dependencies=("route",),
        support_variants=(SupportVariant("v", demand, 8, "body", ("route",), provenance, evidence_id, "MAY"),),
        terminal_service_semantics=(("CHARGE", "terminal"),),
        provenance=provenance,
    )


def candidate(*, horizon: int = 8, unknown: bool = False, invalidated: bool = False, body: str = "body", admissible: bool = True, signature: tuple[str, ...] = ("energy",)) -> CandidateProjection:
    return CandidateProjection(
        "candidate",
        "root",
        signature,
        admissible,
        (CandidateBranch("branch", body_schema_id=body, unknown_opportunities=("opp",) if unknown else (), invalidated_dependencies=("route",) if invalidated else (), horizon_overrides=(("opp", horizon),)),),
    )


def test_preserved_when_known_support_fits() -> None:
    assert assess_option(option(), candidate()).status is OptionStatus.PRESERVED


def test_destroyed_when_known_support_crosses_deadline() -> None:
    assert assess_option(option(), candidate(horizon=5)).status is OptionStatus.DESTROYED


def test_unknown_applicability_is_not_destruction() -> None:
    assessment = assess_option(option(), candidate(unknown=True))
    assert assessment.status is OptionStatus.UNKNOWN
    assert assessment.variants[0].status is SupportVariantStatus.UNKNOWN


def test_unknown_dependency_is_not_destruction() -> None:
    c = CandidateProjection("candidate", "root", ("energy",), True, (CandidateBranch("b", unknown_dependencies=("route",)),))
    assert assess_option(option(), c).status is OptionStatus.UNKNOWN


def test_body_schema_invalidation_destroys_known_option() -> None:
    assert assess_option(option(), candidate(body="new-body" )).status is OptionStatus.DESTROYED


def test_candidate_relation_preserve_destroy() -> None:
    a = candidate(horizon=8)
    b = candidate(horizon=5)
    assert known_option_precedes((option(),), a, b).relates


def test_candidate_relation_preserve_unknown_is_blocked() -> None:
    assert not known_option_precedes((option(),), candidate(), candidate(unknown=True)).relates


def test_candidate_relation_unknown_destroy_is_blocked() -> None:
    assert not known_option_precedes((option(),), candidate(unknown=True), candidate(horizon=5)).relates


def test_both_preserve_is_neutral() -> None:
    assert not known_option_precedes((option(),), candidate(), candidate()).relates


def test_both_destroy_is_neutral() -> None:
    assert not known_option_precedes((option(),), candidate(horizon=5), candidate(horizon=5)).relates


def test_converse_loss_blocks_a_precedence() -> None:
    assert not known_option_precedes((option(),), candidate(horizon=5), candidate()).relates


def test_duplicate_semantic_options_collapse() -> None:
    duplicate = option(evidence_id="other", provenance=("other",))
    assert len(deduplicate_options((option(), duplicate))) == 1


def test_evidence_id_renaming_does_not_change_relation() -> None:
    assert known_option_precedes((option(evidence_id="one"),), candidate(), candidate(horizon=5)).relates
    assert known_option_precedes((option(evidence_id="two"),), candidate(), candidate(horizon=5)).relates


def test_provenance_reordering_does_not_change_relation() -> None:
    assert known_option_precedes((option(provenance=("b", "a")),), candidate(), candidate(horizon=5)).relates


def test_confidence_is_not_authority() -> None:
    first = option()
    second = SupportedRecoveryOption(**{**first.__dict__, "support_variants": (SupportVariant("v2", 7, 8, "body", ("route",), (), "e2", "MUST"),)})
    assert known_option_precedes((first,), candidate(), candidate(horizon=5)).relates
    assert known_option_precedes((second,), candidate(), candidate(horizon=5)).relates


def test_duration_difference_without_feasibility_change_is_neutral() -> None:
    short = option(demand=6)
    long = option(demand=7)
    assert known_option_precedes((short,), candidate(), candidate()).reason == "NO_STRICT_KNOWN_OPTION_PRESERVATION"
    assert known_option_precedes((long,), candidate(), candidate()).reason == "NO_STRICT_KNOWN_OPTION_PRESERVATION"


def test_duration_crossing_deadline_can_destroy() -> None:
    assert known_option_precedes((option(demand=7),), candidate(), candidate(horizon=5)).relates


def test_duplicate_samples_are_support_variants_not_options() -> None:
    base = option()
    duplicate_sample = SupportVariant("v2", 7, 8, "body", ("route",), ("later",), "e2", "MAY")
    richer = SupportedRecoveryOption(**{**base.__dict__, "support_variants": (base.support_variants[0], duplicate_sample)})
    assert len(deduplicate_options((base, richer))) == 1


def test_different_semantic_options_remain_distinct_without_count_authority() -> None:
    other = SupportedRecoveryOption(**{**option().__dict__, "exact_opportunity_identities": ("other",)})
    assert option().semantic_identity != other.semantic_identity
    assert len(deduplicate_options((option(), other))) == 2


def test_two_options_one_common_preserved_and_one_lost_can_relate() -> None:
    o1 = option()
    o2 = SupportedRecoveryOption(**{**o1.__dict__, "exact_opportunity_identities": ("other",), "relevant_opportunity_horizons": (("other", 8),), "support_variants": (SupportVariant("v2", 7, 8, "body", ("route",)),)})
    a = CandidateProjection("a", "root", ("energy",), True, (CandidateBranch("a", horizon_overrides=(("opp", 8), ("other", 8))),))
    b = CandidateProjection("b", "root", ("energy",), True, (CandidateBranch("b", horizon_overrides=(("opp", 5), ("other", 8))),))
    assert known_option_precedes((o1, o2), a, b).relates


def test_crossing_options_block_relation() -> None:
    o1 = option()
    o2 = SupportedRecoveryOption(**{**o1.__dict__, "exact_opportunity_identities": ("other",), "relevant_opportunity_horizons": (("other", 8),), "support_variants": (SupportVariant("v2", 7, 8, "body", ("route",)),)})
    a = CandidateProjection("a", "root", ("energy",), True, (CandidateBranch("a", horizon_overrides=(("opp", 8), ("other", 5))),))
    b = CandidateProjection("b", "root", ("energy",), True, (CandidateBranch("b", horizon_overrides=(("opp", 5), ("other", 8))),))
    assert not known_option_precedes((o1, o2), a, b).relates


def test_empty_root_set_is_not_precedence() -> None:
    assert not known_option_precedes((), candidate(), candidate()).relates


def test_obligation_mismatch_is_incomparable() -> None:
    assert not known_option_precedes((option(),), candidate(), candidate(signature=("fatigue",))).relates


def test_hard_invalid_candidate_is_preempted() -> None:
    result = known_option_precedes((option(),), candidate(admissible=False), candidate(horizon=5))
    assert result.reason == "HARD_AUTHORITY_PREEMPTED"


def test_candidate_branch_permutation_does_not_change_preservation() -> None:
    branches = (CandidateBranch("b1", horizon_overrides=(("opp", 8),)), CandidateBranch("b2", horizon_overrides=(("opp", 8),)))
    a = CandidateProjection("a", "root", ("energy",), True, branches)
    b = CandidateProjection("b", "root", ("energy",), True, tuple(reversed(branches)))
    assert assess_option(option(), a).status is OptionStatus.PRESERVED
    assert assess_option(option(), b).status is OptionStatus.PRESERVED


def test_physical_branch_failure_requires_all_variants_to_be_lost() -> None:
    two = SupportedRecoveryOption(**{**option().__dict__, "support_variants": (option().support_variants[0], SupportVariant("v2", 4, 8, "body", ("route",)))})
    assert assess_option(two, candidate(horizon=5)).status is OptionStatus.PRESERVED
