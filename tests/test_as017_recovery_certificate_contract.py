from __future__ import annotations

from umbra_core.arbitration import Candidate
from umbra_core.recoverability.contracts import EXECUTABLE
from umbra_core.recoverability.viability import (
    ASSESSMENT_ALLOWED,
    ASSESSMENT_DENIED,
    ASSESSMENT_UNKNOWN,
    CERTIFICATE_PROVEN,
    CandidateAssessment,
    RecoveryAssessmentContext,
    assess_candidate,
    certify_candidate_recovery,
)


def _context() -> RecoveryAssessmentContext:
    return RecoveryAssessmentContext(
        "root:1", {"energy": 0.20, "fatigue": 0.20, "integrity": 0.90, "stimulation": 0.55},
        "observation:1", "body:1", "governance:1", "model:1",
    )


def _assess(candidate: Candidate, *, eligible: bool | None = True, params=None, branches=({"energy": 0.8},)):
    return assess_candidate(
        context=_context(), candidate=candidate,
        execution_params_for=lambda _ctx, _candidate: params if params is not None else candidate.params,
        eligible_for=lambda _ctx, _candidate: eligible,
        compositional_admissible_for=lambda _ctx, _candidate, _branches: True,
        executability_for=lambda _ctx, _candidate: EXECUTABLE,
        governance_precondition_for=lambda _ctx, _candidate: True,
        effect_branches_for=lambda _ctx, _candidate: branches,
    )


def test_physically_executable_but_self_model_forbidden_action_cannot_certify() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    assessment = _assess(charge, eligible=False)
    assert assessment.status == ASSESSMENT_DENIED
    certificate = certify_candidate_recovery(
        context=_context(), first_candidate=charge,
        assessments={assessment.candidate_identity: assessment},
    )
    assert certificate.status != CERTIFICATE_PROVEN


def test_certificate_binds_exact_first_candidate_and_parameters() -> None:
    near = Candidate("CHARGE", {"toward": "resource", "mode": "near"})
    far = Candidate("CHARGE", {"toward": "resource", "mode": "far"})
    near_assessment = _assess(near)
    far_assessment = _assess(far)
    assert near_assessment.candidate_identity != far_assessment.candidate_identity
    certificate = certify_candidate_recovery(
        context=_context(), first_candidate=near,
        assessments={far_assessment.candidate_identity: far_assessment},
    )
    assert certificate.status != CERTIFICATE_PROVEN


def test_unknown_assumption_is_not_relabelled_as_safe_or_impossible() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    assessment = _assess(charge, eligible=None)
    assert assessment.status == ASSESSMENT_UNKNOWN


def test_translated_execution_params_are_assessed_without_rewriting_requested_identity() -> None:
    approach = Candidate("APPROACH", {"heading_delta": 0.5, "toward": "resource"})
    assessment = _assess(approach, params={"heading": 1.5, "toward": "resource"})
    assert assessment.status == ASSESSMENT_ALLOWED
    assert assessment.requested_params["heading_delta"] == 0.5
    assert assessment.execution_params["heading"] == 1.5


def _two_step_context() -> RecoveryAssessmentContext:
    return RecoveryAssessmentContext(
        "root:two-step", {"energy": 0.15, "fatigue": 0.20, "integrity": 0.90, "stimulation": 0.55},
        "observation:1", "body:1", "governance:1", "model:1",
    )


def _two_step_assessment(candidate: Candidate, context: RecoveryAssessmentContext | None = None) -> CandidateAssessment:
    return assess_candidate(
        context=context or _two_step_context(), candidate=candidate,
        execution_params_for=lambda _ctx, value: value.params,
        eligible_for=lambda _ctx, _candidate: True,
        compositional_admissible_for=lambda _ctx, _candidate, _branches: True,
        executability_for=lambda _ctx, _candidate: EXECUTABLE,
        governance_precondition_for=lambda _ctx, _candidate: True,
        effect_branches_for=lambda _ctx, _candidate: ({"energy": 0.10},),
    )


def test_denied_second_action_cannot_be_certified_as_proven() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    first = _two_step_assessment(charge)
    calls: list[str] = []

    def denied(context: RecoveryAssessmentContext, _state, _candidate) -> CandidateAssessment:
        calls.append(context.root_id)
        return CandidateAssessment(context.root_id, first.candidate_identity, charge.params, charge.params,
                                   ASSESSMENT_DENIED, ("successor_denied",), (), None)

    certificate = certify_candidate_recovery(
        context=_two_step_context(), first_candidate=charge,
        assessments={first.candidate_identity: first}, successor_assessment_for=denied,
    )
    assert calls == ["root:two-step:successor:1:0"]
    assert certificate.status != CERTIFICATE_PROVEN
    assert certificate.search_budget_status == "SUCCESSOR_DENIED"


def test_missing_successor_authority_cannot_be_certified_as_proven() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    first = _two_step_assessment(charge)
    certificate = certify_candidate_recovery(
        context=_two_step_context(), first_candidate=charge,
        assessments={first.candidate_identity: first},
    )
    assert certificate.status != CERTIFICATE_PROVEN
    assert certificate.search_budget_status == "SUCCESSOR_CONTEXT_REQUIRED"


def test_supported_repeated_action_is_certified_only_after_each_successor_assessment() -> None:
    charge = Candidate("CHARGE", {"toward": "resource"})
    first = _two_step_assessment(charge)
    contexts: list[RecoveryAssessmentContext] = []

    def supported(context: RecoveryAssessmentContext, _state, candidate: Candidate) -> CandidateAssessment:
        contexts.append(context)
        return _two_step_assessment(candidate, context)

    certificate = certify_candidate_recovery(
        context=_two_step_context(), first_candidate=charge,
        assessments={first.candidate_identity: first}, successor_assessment_for=supported,
    )
    assert certificate.status == CERTIFICATE_PROVEN
    assert certificate.witness == (first.candidate_identity, first.candidate_identity)
    assert [context.root_id for context in contexts] == ["root:two-step:successor:1:0"]
