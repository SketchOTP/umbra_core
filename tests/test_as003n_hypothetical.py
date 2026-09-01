"""Focused pure proof suite for the AS-003N hypothetical substrate.

This module uses constructed immutable data only.  It does not instantiate an
organism, tick runtime, or enter Embodiment/environment execution.
"""

from __future__ import annotations

import ast
from pathlib import Path

from umbra_core.hypothetical import (
    BRANCH_CEILING,
    DependencyToken,
    EvidenceEnvelope,
    HypotheticalState,
    OpportunityEvidence,
    PhysiologyBranch,
    RegulatoryService,
    RouteEvidence,
    TransitionContract,
    TransitionStatus,
    dependency_fingerprint,
    dependency_fingerprint_matches,
    transition,
    validate_regulatory_service,
)
from umbra_core.self_model.engine import SupportSemantics


ROOT = Path(__file__).resolve().parents[1]


def supported(low: float, high: float | None = None, ref: str = "verified") -> EvidenceEnvelope:
    return EvidenceEnvelope(low, low if high is None else high, SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value, (ref,))


def hard(low: float, high: float | None = None, ref: str = "contract") -> EvidenceEnvelope:
    return EvidenceEnvelope(low, low if high is None else high, SupportSemantics.HARD_CONTRACT.value, (ref,))


def state(*, branches: tuple[PhysiologyBranch, ...] | None = None, opportunities=None, routes=None, tokens=None) -> HypotheticalState:
    return HypotheticalState(
        root_tick=7,
        elapsed_time=hard(0),
        physiology_branches=branches or (PhysiologyBranch({"energy": hard(0.5), "fatigue": hard(0.2), "integrity": hard(0.9)}),),
        body_schema_identity="body-v1",
        opportunities=opportunities or {},
        routes=routes or {},
        pending_commitment={"mode": "none"},
        provenance=("root",),
        dependencies=tokens or (DependencyToken("physiology_root", "organism", "p1"),),
    )


def contract(*, effects=None, duration=None, **kwargs) -> TransitionContract:
    return TransitionContract(
        semantic_identity="service:unit",
        duration=duration or hard(1),
        effect_branches=effects or ({"energy": hard(0.1)},),
        provenance=("contract",),
        **kwargs,
    )


def test_deep_immutability_and_canonical_identity_are_stable():
    nested = {"nested": {"item": ["a", "b"]}}
    original = state()
    candidate = HypotheticalState(
        root_tick=original.root_tick,
        elapsed_time=original.elapsed_time,
        physiology_branches=original.physiology_branches,
        body_schema_identity=original.body_schema_identity,
        pending_commitment=nested,
        dependencies=original.dependencies,
    )
    nested["nested"]["item"].append("mutated")
    assert candidate.pending_commitment["nested"]["item"] == ("a", "b")
    try:
        candidate.pending_commitment["new"] = "no"  # type: ignore[index]
    except TypeError:
        pass
    else:
        raise AssertionError("frozen mapping accepted a mutation")
    assert candidate.semantic_identity == HypotheticalState(
        root_tick=7, elapsed_time=hard(0), physiology_branches=original.physiology_branches,
        body_schema_identity="body-v1", pending_commitment={"nested": {"item": ["a", "b"]}}, dependencies=original.dependencies,
    ).semantic_identity


def test_envelopes_are_immutable_conservative_and_never_upgrade_support():
    observed = supported(1.0, 2.0)
    total = observed.add(hard(2.0, 3.0))
    assert total.minimum <= 3.0 and total.maximum >= 5.0
    assert total.semantics == SupportSemantics.VERIFIED_OBSERVED_SUPPORT.value
    scaled = observed.scale(-2.0)
    assert scaled.minimum <= -4.0 and scaled.maximum >= -2.0
    unknown = EvidenceEnvelope.unknown("missing")
    assert unknown.add(hard(1)).semantics == SupportSemantics.UNKNOWN.value
    assert observed.intersect(hard(1.5, 2.5)).contains(1.5)
    assert observed.provenance == ("verified",)


def test_unknown_probabilistic_and_known_impossible_transitions_are_categorical():
    assert transition(state(), contract(required_evidence=(EvidenceEnvelope.unknown(),))).status is TransitionStatus.UNKNOWN
    probabilistic = EvidenceEnvelope(1, 1, SupportSemantics.PROBABILISTIC_SUPPORT.value)
    assert transition(state(), contract(required_evidence=(probabilistic,))).status is TransitionStatus.UNKNOWN
    assert transition(state(), contract(availability=TransitionStatus.UNSUPPORTED)).status is TransitionStatus.UNSUPPORTED
    no_time = HypotheticalState(root_tick=7, elapsed_time=EvidenceEnvelope.unknown(), physiology_branches=state().physiology_branches, body_schema_identity="body-v1", dependencies=state().dependencies)
    assert transition(no_time, contract()).reason == "STATE_TIMING_UNKNOWN"
    missing_energy = state(branches=(PhysiologyBranch({"energy": EvidenceEnvelope.unknown()}),))
    assert transition(missing_energy, contract()).reason == "STATE_EFFECT_FIELD_UNKNOWN"


def test_not_applicable_fields_do_not_block_unrelated_effects():
    result = transition(state(), contract(effects=({"energy": hard(0.1)},)))
    assert result.status is TransitionStatus.SUPPORTED
    assert result.successors[0].physiology_branches[0].values["energy"].contains(0.6)


def test_correlated_effect_branches_are_retained_and_order_invariant():
    rest = ({"energy": hard(0.01), "fatigue": hard(-0.08), "integrity": hard(0.05)}, {"energy": hard(-0.003), "fatigue": hard(0.002), "integrity": hard(0.0)})
    left = transition(state(), contract(effects=rest))
    right = transition(state(), contract(effects=tuple(reversed(rest))))
    assert left.status is right.status is TransitionStatus.SUPPORTED
    assert tuple(item.semantic_identity for item in left.successors) == tuple(item.semantic_identity for item in right.successors)
    first = left.successors[0].physiology_branches[0].values
    assert first["energy"].minimum != first["fatigue"].minimum


def test_branch_ceiling_overflow_returns_unknown_without_pruning_or_sampling():
    branches = tuple(
        PhysiologyBranch({"energy": hard(0.5 + index * 0.0001)}) for index in range(BRANCH_CEILING)
    )
    result = transition(state(branches=branches), contract(effects=({"energy": hard(0.1)}, {"energy": hard(-0.1)})))
    assert result.status is TransitionStatus.UNKNOWN
    assert result.reason == "BRANCH_CEILING_EXCEEDED"
    assert result.successors == ()


def test_multistep_composition_is_deterministic_and_unknown_is_sticky():
    first = transition(state(), contract(effects=({"energy": hard(0.1)},)))
    second = transition(first.successors[0], contract(effects=({"fatigue": hard(-0.1)},)))
    repeat = transition(first.successors[0], contract(effects=({"fatigue": hard(-0.1)},)))
    assert second.status is repeat.status is TransitionStatus.SUPPORTED
    assert second.successors[0].semantic_identity == repeat.successors[0].semantic_identity
    assert transition(first.successors[0], contract(required_evidence=(EvidenceEnvelope.unknown(),))).status is TransitionStatus.UNKNOWN


def test_opportunity_route_and_timing_uncertainty_block_supported_continuation():
    unknown_opportunity = OpportunityEvidence("charge", TransitionStatus.SUPPORTED, EvidenceEnvelope.unknown())
    assert transition(state(opportunities={"charge": unknown_opportunity}), contract(opportunity_identity="charge")).reason == "OPPORTUNITY_PERSISTENCE_UNKNOWN"
    route = RouteEvidence("r", TransitionStatus.SUPPORTED, EvidenceEnvelope.unknown(), hard(1))
    assert transition(state(routes={"r": route}), contract(route_identity="r")).reason == "ROUTE_SUPPORT_UNKNOWN"
    assert transition(state(), contract(duration=EvidenceEnvelope.unknown())).status is TransitionStatus.UNKNOWN


def test_validated_regulatory_service_is_non_executable_and_retains_coupled_effect():
    service = RegulatoryService(
        semantic_identity="rest:body-v1",
        owners=("fatigue", "integrity"),
        terminal_capability="REST",
        opportunity_identity="rest-zone",
        route_identity=None,
        duration=supported(1, 2),
        effect_branches=({"fatigue": supported(-0.08), "integrity": supported(0.055)},),
        body_schema_identity="body-v1",
        preconditions=(hard(1),),
        availability=TransitionStatus.SUPPORTED,
    )
    validated = validate_regulatory_service(service)
    assert not isinstance(validated, type(transition(state(), contract())))
    assert validated.service.owners == ("fatigue", "integrity")  # type: ignore[union-attr]
    rest_zone = OpportunityEvidence("rest-zone", TransitionStatus.SUPPORTED, hard(1))
    result = transition(state(opportunities={"rest-zone": rest_zone}), contract(service=validated, effects=service.effect_branches, duration=service.duration))  # type: ignore[arg-type]
    assert result.status is TransitionStatus.SUPPORTED
    values = result.successors[0].physiology_branches[0].values
    assert values["fatigue"].contains(0.12) and values["integrity"].contains(0.955)


def test_dependency_fingerprint_is_order_independent_and_material_changes_invalidate():
    tokens = (DependencyToken("physiology_root", "o", "p1"), DependencyToken("body_schema", "b", "v1"))
    fingerprint = dependency_fingerprint(tokens)
    assert fingerprint == dependency_fingerprint(reversed(tokens))
    assert dependency_fingerprint_matches(fingerprint, reversed(tokens))
    assert not dependency_fingerprint_matches(fingerprint, (*tokens[:-1], DependencyToken("body_schema", "b", "v2")))
    assert state(tokens=tokens).valid_for(reversed(tokens))


def test_firewall_and_live_callsite_static_proof():
    module = ROOT / "umbra_core" / "hypothetical" / "core.py"
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not any(name.startswith(("umbra_core.runtime", "umbra_core.governance", "umbra_core.embodiment", "umbra_core.persistence")) for name in imported)
    forbidden_calls = {"set_var", "apply_outcome_effects", "observe_outcome", "tick_once", "execute", "random"}
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in forbidden_calls for node in ast.walk(tree))
    existing = [path for path in (ROOT / "umbra_core").rglob("*.py") if "hypothetical" not in path.parts]
    assert all("umbra_core.hypothetical" not in path.read_text(encoding="utf-8") for path in existing)
