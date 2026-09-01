"""Focused pure proof for AS-003O source-backed continuation.

All fixtures are immutable owner snapshots. No test constructs an organism,
imports runtime, ticks an environment, performs learning, or executes an
action.
"""

from __future__ import annotations

import ast
from pathlib import Path

from umbra_core.hypothetical.adapters import (
    SourceOpportunity,
    SourceRoute,
    build_regulatory_service,
    capability_envelopes,
    capability_transition_contract,
    root_state_from_sources,
)
from umbra_core.hypothetical.continuation import (
    ContinuationSet,
    robust_continuation_status,
    service_transition,
    strict_continuation_superset,
)
from umbra_core.hypothetical.core import (
    BRANCH_CEILING,
    DependencyToken,
    EvidenceEnvelope,
    PhysiologyBranch,
    TransitionStatus,
)
from umbra_core.physiology import Physiology
from umbra_core.self_model.engine import CapabilitySupportEnvelope, SupportInterval, SupportSemantics


ROOT = Path(__file__).resolve().parents[1]


def hard(value: float, reference: str = "contract") -> EvidenceEnvelope:
    return EvidenceEnvelope(value, value, SupportSemantics.HARD_CONTRACT.value, (reference,))


def observed(value: float, reference: str = "observed") -> EvidenceEnvelope:
    return EvidenceEnvelope(value, value, SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value, (reference,))


def source_opportunity(*, horizon: EvidenceEnvelope | None = None, availability: TransitionStatus = TransitionStatus.SUPPORTED) -> SourceOpportunity:
    return SourceOpportunity("station", availability, horizon or observed(10, "verified-horizon"), ("world:station",), DependencyToken("opportunity", "station", "v1"))


def root(*, opportunity: SourceOpportunity | None = None):
    opportunities = {} if opportunity is None else {opportunity.identity: opportunity}
    return root_state_from_sources(root_tick=11, physiology=Physiology(energy=0.45, fatigue=0.60, integrity=0.60, stimulation=0.35), body_schema_identity="body-v1", body_schema_version=1, opportunities=opportunities)


def charge(*, opportunity: SourceOpportunity | None = None):
    opportunity = opportunity or source_opportunity()
    return build_regulatory_service(capability="CHARGE", body_schema_identity="body-v1", opportunity=opportunity, route=None, duration=hard(1, "charge-duration"), capability_support=hard(1, "stationary-capability"), body_version_token=DependencyToken("body_schema", "body-v1", "1"))


def test_exact_root_physiology_is_verified_current_observation_not_hard_contract():
    state = root()
    values = state.physiology_branches[0].values
    assert tuple(values) == ("energy", "fatigue", "integrity", "stimulation")
    assert values["energy"].minimum == values["energy"].maximum == 0.45
    assert values["energy"].semantics == SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value
    assert state.elapsed_time.semantics == SupportSemantics.HARD_CONTRACT.value


def test_root_unknown_and_source_weakening_never_promote_support():
    bad = {"energy": 0.5, "fatigue": 0.2, "integrity": 0.8}
    try:
        root_state_from_sources(root_tick=1, physiology=bad, body_schema_identity="body-v1", body_schema_version=1)
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete owner source accepted")
    unknown = EvidenceEnvelope.unknown("missing")
    assert unknown.add(hard(1)).semantics == SupportSemantics.UNKNOWN.value


def test_capability_support_preserves_probability_and_body_schema_mismatch():
    envelope = CapabilitySupportEnvelope(capability="MOVE", body_schema_id="body-v1", progress=SupportInterval(1, 2, SupportSemantics.PROBABILISTIC_SUPPORT.value), applied_step=SupportInterval(1, 1, SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value), completion=SupportInterval(3, 4, SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value))
    progress, _, completion = capability_envelopes(envelope, body_schema_identity="body-v1")
    assert progress.semantics == SupportSemantics.PROBABILISTIC_SUPPORT.value
    assert completion.categorical_supported()
    mismatch, _, _ = capability_envelopes(envelope, body_schema_identity="body-v2")
    assert mismatch.semantics == SupportSemantics.UNKNOWN.value


def test_current_opportunity_does_not_become_future_persistence():
    current_only = source_opportunity(horizon=EvidenceEnvelope.unknown("current-observation-only"))
    service = charge(opportunity=current_only)
    assert service.construction_status is TransitionStatus.UNKNOWN
    assert service.reason in {"SOURCE_EVIDENCE_INSUFFICIENT", "SERVICE_EVIDENCE_INSUFFICIENT"}
    assert robust_continuation_status(root(opportunity=current_only), capability_transition_contract("ORIENT", duration=hard(1)), (service,)).status is TransitionStatus.UNKNOWN


def test_explicit_horizon_is_consumed_against_hypothetical_elapsed_time():
    short = source_opportunity(horizon=observed(1, "valid-through-root-plus-one"))
    service = charge(opportunity=short)
    current = capability_transition_contract("ORIENT", duration=hard(1))
    proof = robust_continuation_status(root(opportunity=short), current, (service,))
    assert proof.status is TransitionStatus.UNKNOWN
    assert "OPPORTUNITY_HORIZON_INSUFFICIENT" in proof.unknown_reasons


def test_current_branches_require_a_service_witness_for_every_branch():
    opportunity = source_opportunity()
    proof = robust_continuation_status(root(opportunity=opportunity), capability_transition_contract("ORIENT", duration=hard(1)), (charge(opportunity=opportunity),))
    assert proof.status is TransitionStatus.SUPPORTED
    assert len(proof.witnesses) == 2  # ORIENT preserves success and delayed branches.
    assert proof.max_active_paths <= BRANCH_CEILING


def test_no_services_is_known_unsupported_not_a_favorable_branch_claim():
    proof = robust_continuation_status(root(), capability_transition_contract("ORIENT", duration=hard(1)), ())
    assert proof.status is TransitionStatus.UNSUPPORTED
    assert proof.reason == "BRANCH_HAS_NO_SUPPORTED_CONTINUATION"


def test_unknown_service_branch_prevents_cherry_picked_supported_result():
    opportunity = source_opportunity(horizon=EvidenceEnvelope.unknown("missing-horizon"))
    proof = robust_continuation_status(root(opportunity=opportunity), capability_transition_contract("ORIENT", duration=hard(1)), (charge(opportunity=opportunity),))
    assert proof.status is TransitionStatus.UNKNOWN
    assert not proof.witnesses


def test_rest_remains_one_coupled_service_for_fatigue_and_integrity():
    opportunity = source_opportunity()
    rest = build_regulatory_service(capability="REST", body_schema_identity="body-v1", opportunity=opportunity, route=None, duration=hard(1), capability_support=hard(1), body_version_token=DependencyToken("body_schema", "body-v1", "1"))
    assert rest.service.owners == ("fatigue", "integrity")
    assert all({"fatigue", "integrity"}.issubset(set(branch)) for branch in rest.service.effect_branches)


def test_charge_rest_and_inspect_are_the_only_justified_service_shapes():
    opportunity = source_opportunity()
    for capability, owners in (("CHARGE", ("energy",)), ("REST", ("fatigue", "integrity")), ("INSPECT", ("stimulation",))):
        built = build_regulatory_service(capability=capability, body_schema_identity="body-v1", opportunity=opportunity, route=None, duration=hard(1), capability_support=hard(1), body_version_token=DependencyToken("body_schema", "body-v1", "1"))
        assert built.service.owners == owners
    try:
        build_regulatory_service(capability="MOVE", body_schema_identity="body-v1", opportunity=opportunity, route=None, duration=hard(1), capability_support=hard(1), body_version_token=DependencyToken("body_schema", "body-v1", "1"))
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported drive-shaped service accepted")


def test_route_evidence_requires_supported_timing_and_capability():
    opportunity = source_opportunity()
    route = SourceRoute("route", TransitionStatus.SUPPORTED, EvidenceEnvelope.unknown("timing"), hard(1), ("route",), DependencyToken("route", "route", "v1"))
    built = build_regulatory_service(capability="CHARGE", body_schema_identity="body-v1", opportunity=opportunity, route=route, duration=hard(1), capability_support=hard(1), body_version_token=DependencyToken("body_schema", "body-v1", "1"))
    assert built.construction_status is TransitionStatus.UNKNOWN


def test_capability_transition_preserves_correlated_effect_branches_and_separate_drift():
    transition = capability_transition_contract("REST", duration=hard(1))
    assert len(transition.effect_branches) == 2
    assert all(set(branch) == {"energy", "fatigue", "integrity", "stimulation"} for branch in transition.effect_branches)
    assert any("physiology-contract:drift:energy" in effect.provenance for effect in transition.effect_branches[0].values())


def test_fingerprint_invalidation_is_material_but_not_unrelated_state():
    state = root()
    assert state.valid_for(state.dependencies)
    changed = tuple(token if token.dependency_class != "body_schema" else DependencyToken("body_schema", token.identity, "2") for token in state.dependencies)
    assert not state.valid_for(changed)
    assert state.valid_for((*state.dependencies, DependencyToken("unrelated", "journal", "1"))) is False


def test_pending_commitment_is_snapshot_data_and_not_fresh_action_authority():
    state = root_state_from_sources(root_tick=1, physiology=Physiology(), body_schema_identity="body-v1", body_schema_version=1, pending_commitment={"execution_id": "pending-1", "fresh_action_allowed": False})
    assert state.pending_commitment["fresh_action_allowed"] is False
    assert state.pending_commitment["execution_id"] == "pending-1"


def test_global_frontier_overflow_is_unknown_without_pruning():
    state = root()
    branches = tuple(PhysiologyBranch(state.physiology_branches[0].values, (f"branch:{index}",)) for index in range(BRANCH_CEILING))
    overflow_state = type(state)(root_tick=state.root_tick, elapsed_time=state.elapsed_time, physiology_branches=branches, body_schema_identity=state.body_schema_identity, opportunities=state.opportunities, routes=state.routes, pending_commitment=state.pending_commitment, dependencies=state.dependencies)
    two_branch = capability_transition_contract("ORIENT", duration=hard(1))
    proof = robust_continuation_status(overflow_state, two_branch, ())
    assert proof.status is TransitionStatus.UNKNOWN
    assert proof.reason == "BRANCH_FRONTIER_EXCEEDED"


def test_exact_32_path_ceiling_is_not_an_operational_pruning_frontier():
    state = root()
    branches = tuple(PhysiologyBranch(state.physiology_branches[0].values, (f"branch:{index}",)) for index in range(16))
    at_limit = type(state)(root_tick=state.root_tick, elapsed_time=state.elapsed_time, physiology_branches=branches, body_schema_identity=state.body_schema_identity, opportunities=state.opportunities, routes=state.routes, pending_commitment=state.pending_commitment, dependencies=state.dependencies)
    result = robust_continuation_status(at_limit, capability_transition_contract("ORIENT", duration=hard(1)), ())
    assert result.status is TransitionStatus.UNSUPPORTED
    assert result.max_active_paths == BRANCH_CEILING


def test_exact_continuation_set_inclusion_requires_matching_branch_identity():
    broad = ContinuationSet.from_mapping({"branch-a": ("charge", "rest"), "branch-b": ("charge",)})
    narrow = ContinuationSet.from_mapping({"branch-a": ("charge",), "branch-b": ("charge",)})
    crossing = ContinuationSet.from_mapping({"branch-a": ("rest",), "branch-b": ("charge",)})
    ambiguous = ContinuationSet.from_mapping({"different": ("charge",)})
    assert strict_continuation_superset(broad, narrow) is TransitionStatus.SUPPORTED
    assert strict_continuation_superset(crossing, narrow) is TransitionStatus.UNSUPPORTED
    assert strict_continuation_superset(broad, ambiguous) is TransitionStatus.UNKNOWN


def test_source_or_provenance_renaming_does_not_change_semantics_when_facts_match():
    left = source_opportunity(horizon=observed(10, "a"))
    right = SourceOpportunity("station", TransitionStatus.SUPPORTED, observed(10, "b"), ("renamed",), DependencyToken("opportunity", "station", "v1"))
    assert left.evidence().availability is right.evidence().availability
    assert left.evidence().persistence.minimum == right.evidence().persistence.minimum


def test_static_firewall_and_zero_live_callsites():
    modules = [ROOT / "umbra_core" / "hypothetical" / "adapters.py", ROOT / "umbra_core" / "hypothetical" / "continuation.py"]
    prohibited = ("umbra_core.runtime", "umbra_core.arbitration", "umbra_core.governance", "umbra_core.embodiment", "umbra_core.persistence")
    for module in modules:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        assert not any(name.startswith(prohibited) for name in imports)
    existing = [path for path in (ROOT / "umbra_core").rglob("*.py") if "hypothetical" not in path.parts]
    assert all("umbra_core.hypothetical.adapters" not in path.read_text(encoding="utf-8") and "umbra_core.hypothetical.continuation" not in path.read_text(encoding="utf-8") for path in existing)
