"""UMBRA-D-008 coherent embodiment profile tests."""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
from pathlib import Path

import pytest

from experiments.d008.constrained_profile import CONSTRAINED_TEST_BODY
from experiments.d008.diagnostic_controllers import (
    RandomPresentationController,
    ScalarMoodController,
    ScriptedAnimationScheduler,
    assert_disposable_db_path,
    assert_not_production_schema,
)
from experiments.d008.hostile_renderer import HostileRenderer
from umbra_core.embodiment import Embodiment
from umbra_core.embodiment_adapters import (
    ABSTRACT_SHAPE_BODY,
    MINIMAL_CREATURE_BODY,
    BodyProfile,
    get_profile,
    profile_definition_hash,
)
from umbra_core.embodiment_adapters.adapter import (
    ADAPTER_FAILURE_CODES,
    ATTACHMENT_EVENT_TYPES,
    AdapterRequest,
    EmbodimentAdapter,
)
from umbra_core.events import AUTHORITATIVE_EVENT_TYPES
from umbra_core.expression import (
    ACTION_PHASES,
    ATTENTION_CONFIDENCE_DISPLAY_THRESHOLD,
    POSTURES,
    AttachmentView,
    AttentionView,
    ExpressionConfig,
    ExpressionConfigError,
    ExpressionEngine,
    ExpressionView,
    FrameRing,
    FrameRingEntry,
    HeadlessRenderer,
    LastOutcomeView,
    PresentationState,
    ReferenceRenderer,
    RendererCursor,
    condition_to_expression_config,
)
from umbra_core.expression.presentation_state import RESULT_ACTIVITY_STATES
from umbra_core.governance import Governance
from umbra_core.identity import ConstitutionalIdentity
from umbra_core.individuality import (
    FORBIDDEN_STATE_KEYS,
    IndividualityConfig,
    IndividualityEngine,
    VerifiedEvidence,
)
from umbra_core.persistence import PersistenceError, Store
from umbra_core.physiology import Physiology
from umbra_core.runtime import (
    OrganismConfig,
    create_organism,
    load_organism,
    maybe_migrate_d008_attachment,
    replay_from_birth,
)
from umbra_core.social import SocialEngine
from umbra_core.util import SeededRNG

from ui.reference_companion import diagnostics, habitat_view
from ui.reference_companion.tkinter_renderer import TkinterRenderer

ROOT = Path(__file__).resolve().parents[1]
THR = json.loads((ROOT / "experiments/d008/thresholds.json").read_text())
FULL_CAPABILITY_SET = frozenset(
    {
        "IDLE",
        "ORIENT",
        "MOVE",
        "APPROACH",
        "RETREAT",
        "INSPECT",
        "REST",
        "CHARGE",
        "SIGNAL_PLAY",
        "SIGNAL_ASSISTANCE",
    }
)


def test_two_production_profiles_support_full_capability_set():
    profiles = (ABSTRACT_SHAPE_BODY, MINIMAL_CREATURE_BODY)

    assert {p.profile_id for p in profiles} == set(THR["production_profile_ids"])
    assert get_profile("ABSTRACT_SHAPE_BODY") is ABSTRACT_SHAPE_BODY
    assert get_profile("MINIMAL_CREATURE_BODY") is MINIMAL_CREATURE_BODY
    for profile in profiles:
        assert profile.supported_capabilities == FULL_CAPABILITY_SET
        assert "MAINTAIN" not in profile.supported_capabilities
        assert "PRACTICE" not in profile.supported_capabilities


def test_constrained_profile_rejects_at_least_one_capability():
    assert CONSTRAINED_TEST_BODY.profile_id == "CONSTRAINED_TEST_BODY"
    assert CONSTRAINED_TEST_BODY.supported_capabilities < FULL_CAPABILITY_SET
    assert FULL_CAPABILITY_SET - CONSTRAINED_TEST_BODY.supported_capabilities
    assert (
        CONSTRAINED_TEST_BODY.physical_limits["max_step"]
        < ABSTRACT_SHAPE_BODY.physical_limits["max_step"]
    )
    assert set(CONSTRAINED_TEST_BODY.presentation_mapping) < set(
        ABSTRACT_SHAPE_BODY.presentation_mapping
    )


def test_profile_definition_hash_is_stable():
    same_profile_reordered = BodyProfile(
        profile_id=ABSTRACT_SHAPE_BODY.profile_id,
        schema_version=ABSTRACT_SHAPE_BODY.schema_version,
        supported_capabilities=frozenset(reversed(tuple(ABSTRACT_SHAPE_BODY.supported_capabilities))),
        physical_limits=dict(reversed(tuple(ABSTRACT_SHAPE_BODY.physical_limits.items()))),
        presentation_mapping=dict(reversed(tuple(ABSTRACT_SHAPE_BODY.presentation_mapping.items()))),
    )

    assert profile_definition_hash(ABSTRACT_SHAPE_BODY) == profile_definition_hash(
        same_profile_reordered
    )
    for profile in (ABSTRACT_SHAPE_BODY, MINIMAL_CREATURE_BODY):
        digest = profile_definition_hash(profile)
        assert len(digest) == 64
        assert THR["production_profile_definition_hashes"][profile.profile_id] == digest
        assert digest != "PLACEHOLDER_COMPUTE_AT_FREEZE"


# ----- EmbodimentAdapter: attach/swap + durable rejection (Task 3) -----


def _resolver(profile_id: str) -> BodyProfile:
    if profile_id == CONSTRAINED_TEST_BODY.profile_id:
        return CONSTRAINED_TEST_BODY
    return get_profile(profile_id)


def _adapter(tmp_path: Path, name: str, profile_id: str) -> tuple[EmbodimentAdapter, Store]:
    store = Store(str(tmp_path / name))
    adapter = EmbodimentAdapter(
        store=store,
        agent_id="test-agent",
        profile_resolver=_resolver,
        wall_time_fn=lambda: 0.0,
        monotonic_time_fn=lambda: 0.0,
    )
    adapter.attach(profile_id)
    return adapter, store


def test_attach_detach_swap_events_are_authoritative():
    assert ADAPTER_FAILURE_CODES == frozenset(THR["adapter_failure_codes"])
    for event_type in (
        "embodiment_body_attached",
        "embodiment_body_detached",
        "embodiment_body_profile_swapped",
    ):
        assert event_type in AUTHORITATIVE_EVENT_TYPES


def test_attach_detach_swap_lifecycle_emits_authoritative_events(tmp_path):
    adapter, store = _adapter(tmp_path, "lifecycle.sqlite", ABSTRACT_SHAPE_BODY.profile_id)
    gen1 = adapter.state.attachment_generation
    instance_id = adapter.state.body_instance_id
    assert adapter.state.attachment_status == "ATTACHED"

    adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id)
    assert adapter.state.body_instance_id == instance_id  # compatible swap retains instance
    assert adapter.state.attachment_generation == gen1 + 1
    assert adapter.state.body_profile_id == MINIMAL_CREATURE_BODY.profile_id

    adapter.detach("test_reason")
    assert adapter.state.attachment_status == "DETACHED"
    assert adapter.state.attachment_generation == gen1 + 2
    assert adapter.state.body_profile_id is None

    event_types = [e["event_type"] for e in store.iter_events()]
    assert event_types == [
        "embodiment_body_attached",
        "embodiment_body_profile_swapped",
        "embodiment_body_detached",
    ]
    store.validate_chain()
    store.close()


def test_adapter_cannot_grant_capabilities(tmp_path):
    """Governance alone admits SIGNAL_ASSISTANCE; the body profile still rejects it —
    the adapter only narrows what governance admitted, it never widens it."""
    adapter, store = _adapter(tmp_path, "grant.sqlite", CONSTRAINED_TEST_BODY.profile_id)
    embodiment = Embodiment()
    rng = SeededRNG(1)
    gov = Governance()

    proposal = gov.propose("SIGNAL_ASSISTANCE", {"tick": 1})
    decision = gov.admit(proposal, tick=1)
    assert decision.admitted

    before = embodiment.to_state()
    request = AdapterRequest(
        request_id=proposal.proposal_id,
        capability="SIGNAL_ASSISTANCE",
        params=dict(proposal.params),
        attachment_generation=adapter.state.attachment_generation,
        tick=1,
    )
    raw = adapter.execute(request, embodiment, rng)

    assert raw["ok_raw"] is False
    assert raw["failure_code"] == "UNSUPPORTED_BODY_CAPABILITY"
    assert embodiment.to_state() == before
    store.close()


def test_unsupported_body_action_fails_safely(tmp_path):
    adapter, store = _adapter(tmp_path, "unsupported.sqlite", CONSTRAINED_TEST_BODY.profile_id)
    embodiment = Embodiment()
    rng = SeededRNG(2)
    request = AdapterRequest(
        request_id="req-1",
        capability="SIGNAL_ASSISTANCE",
        params={},
        attachment_generation=adapter.state.attachment_generation,
        tick=7,
    )

    raw = adapter.execute(request, embodiment, rng)  # must never raise

    required_fields = {
        "ok_raw",
        "failure_code",
        "execution_id",
        "request_id",
        "body_instance_id",
        "body_profile_id",
        "attachment_generation",
        "capability",
        "profile_constraint",
        "tick",
    }
    assert required_fields <= set(raw)
    assert raw["ok_raw"] is False
    assert raw["failure_code"] in ADAPTER_FAILURE_CODES
    assert raw["request_id"] == "req-1"
    assert raw["capability"] == "SIGNAL_ASSISTANCE"
    assert raw["body_profile_id"] == CONSTRAINED_TEST_BODY.profile_id
    assert raw["attachment_generation"] == adapter.state.attachment_generation
    assert raw["tick"] == 7
    store.close()


def test_adapter_rejection_commits_failed_outcome_without_world_mutation(tmp_path):
    adapter, store = _adapter(tmp_path, "commit.sqlite", CONSTRAINED_TEST_BODY.profile_id)
    embodiment = Embodiment()
    rng = SeededRNG(3)
    gov = Governance()

    over_step = CONSTRAINED_TEST_BODY.physical_limits["max_step"] + 5.0
    proposal = gov.propose("MOVE", {"step": over_step, "heading": 0.0})
    decision = gov.admit(proposal, tick=1)
    assert decision.admitted

    before = embodiment.to_state()
    outcome = gov.execute_and_verify(proposal, decision, embodiment, rng, adapter=adapter, tick=1)

    assert outcome is not None
    assert outcome.verified is True
    assert outcome.success is False
    assert outcome.raw["failure_code"] == "BODY_LIMIT_REJECTED"
    assert outcome.raw["profile_constraint"]["limit"] == "max_step"
    assert embodiment.to_state() == before  # no Embodiment.execute call happened

    store.append_event(
        agent_id="test-agent",
        event_type="outcome_verified",
        monotonic_time=1.0,
        wall_time=0.0,
        payload={
            "capability": outcome.capability,
            "success": outcome.success,
            "reason": outcome.reason,
            "effects": outcome.physiology_effects,
            "verified": outcome.verified,
            "raw": outcome.raw,
        },
    )
    store.validate_chain()  # failed outcome is durable
    assert embodiment.to_state() == before  # still no world mutation after commit
    store.close()


def test_adapter_rejection_replay_idempotent(tmp_path):
    """A crash-before-ack retry of the same rejected request must never execute the
    body, and committing its failed outcome twice must never corrupt the ledger."""
    adapter, store = _adapter(tmp_path, "idempotent.sqlite", CONSTRAINED_TEST_BODY.profile_id)
    embodiment = Embodiment()
    rng = SeededRNG(4)
    request = AdapterRequest(
        request_id="dup-req",
        capability="SIGNAL_ASSISTANCE",
        params={},
        attachment_generation=adapter.state.attachment_generation,
        tick=9,
    )

    before = embodiment.to_state()
    raw1 = adapter.execute(request, embodiment, rng)
    raw2 = adapter.execute(request, embodiment, rng)  # simulated retry after crash before ack

    assert raw1["failure_code"] == raw2["failure_code"] == "UNSUPPORTED_BODY_CAPABILITY"
    assert raw1["request_id"] == raw2["request_id"] == "dup-req"
    assert embodiment.to_state() == before  # neither attempt ever executed the body

    for raw in (raw1, raw2):
        store.append_event(
            agent_id="test-agent",
            event_type="outcome_verified",
            monotonic_time=0.0,
            wall_time=0.0,
            payload={"capability": raw["capability"], "success": False, "raw": raw},
        )
    store.validate_chain()  # duplicate durable commits never break the chain
    assert embodiment.to_state() == before  # still never executed
    store.close()


def test_body_detached_stale_generation_and_hash_mismatch_fail_closed(tmp_path):
    store = Store(str(tmp_path / "codes.sqlite"))
    adapter = EmbodimentAdapter(
        store=store,
        agent_id="test-agent",
        wall_time_fn=lambda: 0.0,
        monotonic_time_fn=lambda: 0.0,
    )
    embodiment = Embodiment()
    rng = SeededRNG(5)
    before = embodiment.to_state()

    detached_req = AdapterRequest(
        request_id="r1", capability="IDLE", params={}, attachment_generation=0, tick=1
    )
    raw_detached = adapter.execute(detached_req, embodiment, rng)
    assert raw_detached["failure_code"] == "BODY_DETACHED"

    adapter.attach(ABSTRACT_SHAPE_BODY.profile_id)

    stale_req = AdapterRequest(
        request_id="r2",
        capability="IDLE",
        params={},
        attachment_generation=adapter.state.attachment_generation - 1,
        tick=2,
    )
    raw_stale = adapter.execute(stale_req, embodiment, rng)
    assert raw_stale["failure_code"] == "STALE_ATTACHMENT_GENERATION"

    mismatched_req = AdapterRequest(
        request_id="r3",
        capability="IDLE",
        params={},
        attachment_generation=adapter.state.attachment_generation,
        tick=3,
        expected_profile_hash="deadbeef",
    )
    raw_mismatch = adapter.execute(mismatched_req, embodiment, rng)
    assert raw_mismatch["failure_code"] == "PROFILE_HASH_MISMATCH"

    assert embodiment.to_state() == before  # nothing above ever mutated the world
    store.close()


# ----- Supplement S1: adapter continuous-limit clamping (Task 4 fix) -----


def test_production_adapter_clamps_oversize_step_and_still_moves(tmp_path):
    """ABSTRACT_SHAPE_BODY.max_step=1.0; a governance-admitted MOVE requesting
    more (arbitration's real fallback candidates are 1.2/1.4/1.8 — see
    umbra_core/arbitration.py) clamps to the profile limit instead of hard-
    rejecting, and the body still actually moves."""
    adapter, store = _adapter(tmp_path, "clamp.sqlite", ABSTRACT_SHAPE_BODY.profile_id)
    embodiment = Embodiment()
    rng = SeededRNG(1)
    gov = Governance()

    max_step = ABSTRACT_SHAPE_BODY.physical_limits["max_step"]
    over_step = 1.4
    assert over_step > max_step
    proposal = gov.propose("MOVE", {"step": over_step, "heading": 0.0})
    decision = gov.admit(proposal, tick=1)
    assert decision.admitted

    before = embodiment.to_state()
    outcome = gov.execute_and_verify(proposal, decision, embodiment, rng, adapter=adapter, tick=1)

    assert outcome is not None
    assert outcome.verified is True
    assert outcome.success is True  # clamping is not a failure
    assert outcome.raw.get("failure_code") is None
    assert outcome.raw["translation_applied"] is True
    assert outcome.raw["requested_parameters"]["step"] == over_step
    assert outcome.raw["applied_parameters"]["step"] == max_step
    assert outcome.raw["translation_reason"]
    assert outcome.raw["body_profile_id"] == ABSTRACT_SHAPE_BODY.profile_id
    assert outcome.raw["profile_definition_hash"] == profile_definition_hash(ABSTRACT_SHAPE_BODY)
    assert embodiment.to_state() != before  # body actually moved (clamped distance)
    store.close()


def test_constrained_non_clampable_limit_still_hard_rejects_without_world_mutation(tmp_path):
    """CONSTRAINED_TEST_BODY marks `max_step` non-clampable — oversize step must
    still hard-reject (BODY_LIMIT_REJECTED) with zero world mutation, proving the
    hard-reject path stays exercised even though production profiles clamp."""
    assert CONSTRAINED_TEST_BODY.physical_limits.get("max_step_clampable") is False
    adapter, store = _adapter(tmp_path, "non_clampable.sqlite", CONSTRAINED_TEST_BODY.profile_id)
    embodiment = Embodiment()
    rng = SeededRNG(6)
    gov = Governance()

    over_step = CONSTRAINED_TEST_BODY.physical_limits["max_step"] + 5.0
    proposal = gov.propose("MOVE", {"step": over_step, "heading": 0.0})
    decision = gov.admit(proposal, tick=1)
    assert decision.admitted

    before = embodiment.to_state()
    outcome = gov.execute_and_verify(proposal, decision, embodiment, rng, adapter=adapter, tick=1)

    assert outcome.success is False
    assert outcome.raw["failure_code"] == "BODY_LIMIT_REJECTED"
    assert outcome.raw["profile_constraint"]["limit"] == "max_step"
    assert outcome.raw["profile_constraint"]["reason"] == "non_clampable"
    assert outcome.raw["translation_applied"] is False
    assert embodiment.to_state() == before  # no Embodiment.execute call happened
    store.close()


def test_embodiment_adapter_enabled_regression_fallback_move_steps_work(tmp_path):
    """Regression for the max_step-vs-arbitration conflict logged in Task 4
    review (.agent/CURRENT.md): with `embodiment_adapter_enabled=True` on the
    default ABSTRACT_SHAPE_BODY profile, D-001-era arbitration fallback MOVE
    steps (1.2, 1.4, 1.8 — umbra_core/arbitration.py) must succeed via clamping
    rather than being rejected on ~100% of proposals."""
    cfg = OrganismConfig(
        db_path=str(tmp_path / "regression.sqlite"),
        seed=1,
        embodiment_adapter_enabled=True,
        wall_time_fn=lambda: 0.0,
    )
    org = create_organism(cfg)
    try:
        assert org.embodiment_adapter is not None
        assert org.embodiment_adapter.state.body_profile_id == "ABSTRACT_SHAPE_BODY"
        gov = Governance()
        for fallback_step in (1.2, 1.4, 1.8):
            rng = SeededRNG(1)
            before = org.embodiment.to_state()
            proposal = gov.propose("MOVE", {"step": fallback_step, "heading": 0.0})
            decision = gov.admit(proposal, tick=1)
            outcome = gov.execute_and_verify(
                proposal, decision, org.embodiment, rng, adapter=org.embodiment_adapter, tick=1
            )
            assert outcome.success is True, f"fallback step {fallback_step} must not hard-reject"
            assert outcome.raw.get("failure_code") is None
            assert outcome.raw["translation_applied"] is True
            assert org.embodiment.to_state() != before
    finally:
        org.close()


# ----- D-007 -> D-008 attachment migration (Task 4) -----


def _create_legacy_pre_d008_db(tmp_path: Path, name: str, **config_kwargs) -> str:
    """A D-007-era organism: `embodiment_adapter_enabled=False` means
    `create_organism` never attaches a body — exactly the pre-D-008
    ledger/snapshot shape (zero `embodiment_body_*` events)."""
    db_path = str(tmp_path / name)
    cfg = OrganismConfig(
        db_path=db_path,
        embodiment_adapter_enabled=False,
        wall_time_fn=lambda: 0.0,
        **config_kwargs,
    )
    org = create_organism(cfg)
    assert not [e for e in org.store.iter_events() if e["event_type"] == "embodiment_body_attached"]
    org.close()
    return db_path


def test_embodiment_adapter_disabled_by_default_preserves_prior_behavior(tmp_path):
    """D-001..D-007 configs never set `embodiment_adapter_enabled` — the adapter
    must stay None so pre-D-008 arbitration/body behavior is unaffected."""
    org = create_organism(OrganismConfig(db_path=str(tmp_path / "default.sqlite"), seed=9))
    assert org.embodiment_adapter is None
    attach_events = [e for e in org.store.iter_events() if e["event_type"] == "embodiment_body_attached"]
    assert attach_events == []
    org.close()


def test_create_organism_attaches_default_profile_with_normal_origin(tmp_path):
    cfg = OrganismConfig(
        db_path=str(tmp_path / "fresh.sqlite"),
        seed=2,
        embodiment_adapter_enabled=True,
        wall_time_fn=lambda: 0.0,
    )
    org = create_organism(cfg)
    assert org.embodiment_adapter is not None
    assert org.embodiment_adapter.state.attachment_status == "ATTACHED"
    assert org.embodiment_adapter.state.body_profile_id == THR["default_migration_profile_id"]
    attach_events = [e for e in org.store.iter_events() if e["event_type"] == "embodiment_body_attached"]
    assert len(attach_events) == 1
    assert attach_events[0]["payload"]["origin"] == "NORMAL"
    org.close()

    # A brand-new organism is already ATTACHED — reload must never migrate it.
    org2 = load_organism(cfg)
    assert org2.embodiment_adapter.state.attachment_status == "ATTACHED"
    attach_events2 = [
        e for e in org2.store.iter_events() if e["event_type"] == "embodiment_body_attached"
    ]
    assert len(attach_events2) == 1
    org2.close()


def test_d008_migration_attaches_frozen_default_profile_once(tmp_path):
    db_path = _create_legacy_pre_d008_db(tmp_path, "legacy1.sqlite", seed=1)
    cfg = OrganismConfig(
        db_path=db_path, seed=1, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0
    )

    org = load_organism(cfg)
    try:
        assert org.embodiment_adapter is not None
        assert org.embodiment_adapter.state.attachment_status == "ATTACHED"
        assert org.embodiment_adapter.state.body_profile_id == THR["default_migration_profile_id"]
        attach_events = [
            e for e in org.store.iter_events() if e["event_type"] == "embodiment_body_attached"
        ]
        assert len(attach_events) == 1
        assert attach_events[0]["payload"]["origin"] == "D008_MIGRATION"
        assert attach_events[0]["payload"]["migrated_from_schema_version"]
        # Calling migration again on an already-attached organism is a no-op.
        assert maybe_migrate_d008_attachment(org.store, org) is False
    finally:
        org.close()


def test_d008_migration_second_load_is_noop(tmp_path):
    """No new snapshot is taken between the two loads — the second load must
    reconstruct attachment from the ledger and never re-attach a fresh
    `body_instance_id` (crash-before-snapshot idempotency)."""
    db_path = _create_legacy_pre_d008_db(tmp_path, "legacy2.sqlite", seed=1)
    cfg = OrganismConfig(
        db_path=db_path, seed=1, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0
    )

    org1 = load_organism(cfg)
    instance_id_1 = org1.embodiment_adapter.state.body_instance_id
    generation_1 = org1.embodiment_adapter.state.attachment_generation
    org1.close()

    org2 = load_organism(cfg)
    try:
        assert org2.embodiment_adapter.state.attachment_status == "ATTACHED"
        assert org2.embodiment_adapter.state.body_instance_id == instance_id_1
        assert org2.embodiment_adapter.state.attachment_generation == generation_1
        attach_events = [
            e for e in org2.store.iter_events() if e["event_type"] == "embodiment_body_attached"
        ]
        assert len(attach_events) == 1  # no duplicate attach on second load
    finally:
        org2.close()


def test_d008_migration_event_is_part_of_valid_replay_chain(tmp_path):
    """Birth replay includes the migration event as an ordinary authoritative
    event — no special-cased re-inference of attachment on replay."""
    db_path = _create_legacy_pre_d008_db(tmp_path, "legacy3.sqlite", seed=1)
    cfg = OrganismConfig(
        db_path=db_path, seed=1, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0
    )
    org = load_organism(cfg)
    org.close()

    replay = replay_from_birth(db_path)
    assert replay["chain_valid"] is True

    store = Store(db_path)
    store.validate_chain()  # migration event participates in ordinary hash chaining
    event_types = [e["event_type"] for e in store.iter_events()]
    assert "embodiment_body_attached" in event_types
    assert replay["events"] == len(event_types)
    store.close()


def test_d008_migration_does_not_reset_other_subsystems(tmp_path):
    """Migration touches only attachment — physiology, memory, social,
    individuality, and habitat are untouched (byte-identical to a load of the
    same ledger with the adapter disabled)."""
    db_path = _create_legacy_pre_d008_db(
        tmp_path,
        "legacy4.sqlite",
        seed=3,
        memory_enabled=True,
        social_enabled=True,
        individuality_enabled=True,
    )
    common = dict(
        db_path=db_path,
        seed=3,
        memory_enabled=True,
        social_enabled=True,
        individuality_enabled=True,
        wall_time_fn=lambda: 0.0,
    )

    org_no_migration = load_organism(OrganismConfig(**common, embodiment_adapter_enabled=False))
    baseline = {
        "physiology": org_no_migration.phys.to_state(),
        "habitat": org_no_migration.embodiment.habitat.to_state(),
        "body": org_no_migration.embodiment.body.to_state(),
        "memory": org_no_migration.memory.to_state(),
        "social": org_no_migration.social.to_state(),
        "individuality": org_no_migration.individuality.to_state(),
    }
    org_no_migration.close()

    org_migrated = load_organism(OrganismConfig(**common, embodiment_adapter_enabled=True))
    try:
        assert org_migrated.embodiment_adapter.state.attachment_status == "ATTACHED"
        assert org_migrated.phys.to_state() == baseline["physiology"]
        assert org_migrated.embodiment.habitat.to_state() == baseline["habitat"]
        assert org_migrated.embodiment.body.to_state() == baseline["body"]
        assert org_migrated.memory.to_state() == baseline["memory"]
        assert org_migrated.social.to_state() == baseline["social"]
        assert org_migrated.individuality.to_state() == baseline["individuality"]
    finally:
        org_migrated.close()


def test_d008_post_migration_missing_attachment_fails_closed(tmp_path):
    """Once migrated, if attachment later goes missing (e.g. detached), the
    adapter must fail closed — never fall back to unconstrained execution."""
    db_path = _create_legacy_pre_d008_db(tmp_path, "legacy5.sqlite", seed=5)
    cfg = OrganismConfig(
        db_path=db_path, seed=5, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0
    )
    org = load_organism(cfg)
    assert org.embodiment_adapter.state.attachment_status == "ATTACHED"

    org.embodiment_adapter.detach("test_missing_attachment")
    embodiment_before = org.embodiment.to_state()
    request = AdapterRequest(
        request_id="req-post-migration",
        capability="IDLE",
        params={},
        attachment_generation=org.embodiment_adapter.state.attachment_generation,
        tick=1,
    )
    raw = org.embodiment_adapter.execute(request, org.embodiment, org.rng)

    assert raw["ok_raw"] is False
    assert raw["failure_code"] == "BODY_DETACHED"
    assert org.embodiment.to_state() == embodiment_before  # no world mutation
    org.close()


# ----- PresentationState + HabitatReadModel + ExpressionEngine (Task 5) -----


def _expression_view(
    *,
    tick: int = 1,
    physiology: dict[str, float] | None = None,
    attention: AttentionView | None = None,
    last_outcome: LastOutcomeView | None = None,
    attachment_status: str = "ATTACHED",
    attachment_generation: int = 1,
    source_event_refs: tuple[str, ...] = (),
    developmental_markers: dict | None = None,
    individuality_summary: dict | None = None,
    embodiment: Embodiment | None = None,
) -> ExpressionView:
    embodiment = embodiment if embodiment is not None else Embodiment()
    return ExpressionView(
        tick=tick,
        physiology=physiology
        or {"energy": 0.7, "fatigue": 0.2, "integrity": 0.9, "stimulation": 0.5},
        attachment=AttachmentView(
            attachment_status=attachment_status,
            body_instance_id="body-1",
            body_profile_id=ABSTRACT_SHAPE_BODY.profile_id
            if attachment_status == "ATTACHED"
            else None,
            attachment_generation=attachment_generation,
        ),
        embodiment_state=embodiment.to_state(),
        source_state_version=tick,
        habitat_state_version=tick,
        attention=attention if attention is not None else AttentionView(None, None),
        last_outcome=last_outcome,
        developmental_markers=developmental_markers or {},
        individuality_summary=individuality_summary or {},
        source_event_refs=source_event_refs,
    )


def test_expression_engine_cannot_select_actions():
    """The engine has no channel to act — no execute/select_action/propose
    method, `derive` takes only a read-only view, and passing anything beyond
    that view is a hard TypeError (there is no Governance/Embodiment param)."""
    engine = ExpressionEngine()
    assert not hasattr(engine, "select_action")
    assert not hasattr(engine, "execute")
    assert not hasattr(engine, "propose")
    assert not hasattr(engine, "admit")

    sig = inspect.signature(ExpressionEngine.derive)
    assert list(sig.parameters) == ["self", "view"]

    with pytest.raises(TypeError):
        engine.derive(_expression_view(), Governance())  # type: ignore[call-arg]


def test_no_mood_or_emotion_authority_fields():
    field_names = {f.name for f in dataclasses.fields(PresentationState)}
    forbidden = ("mood", "emotion", "affect", "personality", "feeling", "wall_time", "timestamp")
    for name in field_names:
        lowered = name.lower()
        for bad in forbidden:
            assert bad not in lowered, f"forbidden authority field: {name}"


def test_physiology_is_not_modified_by_expression():
    phys = Physiology(energy=0.6, fatigue=0.3, integrity=0.9, stimulation=0.5)
    before = phys.to_state()
    engine = ExpressionEngine()

    engine.derive(_expression_view(physiology=phys.as_dict()))

    assert phys.to_state() == before


def test_fatigue_changes_visible_condition():
    low_fatigue = ExpressionEngine().derive(
        _expression_view(
            physiology={"energy": 0.7, "fatigue": 0.1, "integrity": 0.9, "stimulation": 0.5}
        )
    )
    high_fatigue = ExpressionEngine().derive(
        _expression_view(
            physiology={"energy": 0.7, "fatigue": 0.8, "integrity": 0.9, "stimulation": 0.5}
        )
    )

    assert (
        low_fatigue.presentation_state.visible_condition_channels
        != high_fatigue.presentation_state.visible_condition_channels
    )


def test_rest_changes_posture_and_activity():
    engine = ExpressionEngine()
    moved = engine.derive(
        _expression_view(
            tick=1, last_outcome=LastOutcomeView(capability="MOVE", admitted=True, success=True)
        )
    )
    assert moved.presentation_state.posture == "ACTIVE"

    rested = engine.derive(
        _expression_view(
            tick=2, last_outcome=LastOutcomeView(capability="REST", admitted=True, success=True)
        )
    )

    assert rested.presentation_state.posture == "RESTING"
    assert rested.presentation_state.rest_activity_state == "RESTING"
    assert rested.presentation_state.posture != moved.presentation_state.posture


def test_uncertain_attention_remains_ambiguous():
    below = ATTENTION_CONFIDENCE_DISPLAY_THRESHOLD - 0.1
    above = ATTENTION_CONFIDENCE_DISPLAY_THRESHOLD + 0.1

    uncertain = ExpressionEngine().derive(
        _expression_view(attention=AttentionView(target="resource", confidence=below))
    )
    certain = ExpressionEngine().derive(
        _expression_view(attention=AttentionView(target="resource", confidence=above))
    )

    assert uncertain.presentation_state.attention_target is None
    assert uncertain.presentation_state.attention_confidence == below  # raw value still passed
    assert certain.presentation_state.attention_target == "resource"


def test_denied_action_is_not_rendered_as_executed():
    """Governance denial never reaches `Embodiment.execute_primitive`, so no
    `VerifiedOutcome` exists — the presentation must not depict it as if the
    denied capability ran."""
    denied = LastOutcomeView(capability="SIGNAL_ASSISTANCE", admitted=False)

    packet = ExpressionEngine().derive(_expression_view(last_outcome=denied))

    ps = packet.presentation_state
    assert ps.active_capability is None
    assert ps.action_phase != "EXECUTED"
    assert ps.nonverbal_signal is None


def test_failed_action_renders_interruption():
    failed = LastOutcomeView(
        capability="MOVE", admitted=True, success=False, failure_code="BODY_LIMIT_REJECTED"
    )

    packet = ExpressionEngine().derive(_expression_view(last_outcome=failed))

    ps = packet.presentation_state
    assert ps.action_phase == "INTERRUPTED"
    assert ps.posture == "INTERRUPTED"


def test_detached_body_renders_empty_body_fields():
    """DETACHED never fabricates a body or replays the last pose as current
    truth (design §2 detached derivation) — habitat may still render."""
    packet = ExpressionEngine().derive(_expression_view(attachment_status="DETACHED"))

    ps = packet.presentation_state
    assert ps.attachment_status == "DETACHED"
    assert ps.position is None
    assert ps.orientation is None
    assert ps.posture is None
    assert ps.active_capability is None
    assert ps.action_phase == "UNAVAILABLE"
    assert ps.nonverbal_signal is None
    assert packet.habitat_read_model.entities  # habitat itself still renders


def test_render_packet_habitat_read_model_is_bounded_and_coherent():
    packet = ExpressionEngine().derive(_expression_view(tick=5))

    assert packet.habitat_read_model.version == packet.habitat_state_version
    assert len(packet.habitat_read_model.entities) <= THR["habitat_read_model_max_entities"]
    assert packet.source_state_version == 5
    assert packet.habitat_state_version == 5
    assert packet.body_attachment_generation == 1


# ----- FrameRing with embedded RenderPacket (Task 6) -----


def _frame_entry(
    *,
    frame_id: int,
    tick: int | None = None,
    attachment_generation: int = 1,
    execution_id: str | None = None,
    source_event_refs: tuple[str, ...] = (),
    engine: ExpressionEngine | None = None,
) -> FrameRingEntry:
    actual_tick = tick if tick is not None else frame_id
    expression_engine = engine or ExpressionEngine()
    packet = expression_engine.derive(
        _expression_view(
            tick=actual_tick,
            attachment_generation=attachment_generation,
            source_event_refs=source_event_refs,
            last_outcome=LastOutcomeView(
                capability="MOVE", admitted=True, success=True, execution_id=execution_id
            )
            if execution_id is not None
            else None,
        )
    )
    return FrameRingEntry(
        frame_id=frame_id,
        derived_at_tick=actual_tick,
        active_execution_id=execution_id,
        render_packet=packet,
        source_event_refs=source_event_refs,
    )


def test_expression_transition_buffers_are_bounded():
    ring = FrameRing.from_thresholds()
    assert ring.capacity == THR["frame_ring_capacity"] == 64
    assert ring.retention_ticks == THR["frame_ring_retention_ticks"] == 128

    for frame_id in range(THR["frame_ring_capacity"] + 10):
        ring.push(_frame_entry(frame_id=frame_id))

    assert len(ring) == THR["frame_ring_capacity"]
    assert ring.oldest_frame_id == 10

    ring.push(_frame_entry(frame_id=500, tick=500))
    assert all(entry.derived_at_tick >= 500 - THR["frame_ring_retention_ticks"] for entry in ring)


def test_stale_expression_frames_are_rejected():
    ring = FrameRing(capacity=8, retention_ticks=128)
    ring.push(_frame_entry(frame_id=1, tick=1, attachment_generation=1, execution_id="old-exec"))
    ring.push(_frame_entry(frame_id=2, tick=2, attachment_generation=2, execution_id="old-exec"))
    ring.push(_frame_entry(frame_id=3, tick=3, attachment_generation=2, execution_id="current-exec"))

    cursor = RendererCursor(
        renderer_id="headless",
        current_tick=3,
        body_attachment_generation=2,
        source_state_version=3,
        habitat_state_version=3,
        active_execution_id="current-exec",
    )

    entry = ring.read_latest(cursor)

    assert entry is not None
    assert entry.frame_id == 3
    assert entry.active_execution_id == "current-exec"


def test_expression_frame_source_refs_are_valid():
    refs = tuple(f"event-{i}" for i in range(THR["source_event_refs_max"] + 5))
    entry = _frame_entry(frame_id=1, source_event_refs=refs)

    assert len(entry.source_event_refs) == THR["source_event_refs_max"]
    assert entry.source_event_refs == entry.render_packet.presentation_state.source_event_refs


def test_frame_ring_cursors_are_non_destructive():
    ring = FrameRing(capacity=4, retention_ticks=128)
    ring.push(_frame_entry(frame_id=1))
    ring.push(_frame_entry(frame_id=2))
    cursor_a = RendererCursor(renderer_id="headless")
    cursor_b = RendererCursor(renderer_id="tkinter")

    assert ring.read_latest(cursor_a).frame_id == 2
    assert len(ring) == 2
    assert ring.read_latest(cursor_b).frame_id == 2
    assert ring.read_latest(cursor_a) is None


def test_profile_generation_bump_invalidates_pre_swap_frames():
    ring = FrameRing(capacity=4, retention_ticks=128)
    pre_swap = _frame_entry(frame_id=1, tick=7, attachment_generation=1)
    post_swap = _frame_entry(frame_id=2, tick=8, attachment_generation=2)
    ring.push(pre_swap)
    ring.push(post_swap)

    cursor = RendererCursor(
        renderer_id="headless",
        current_tick=8,
        body_attachment_generation=2,
        source_state_version=8,
        habitat_state_version=8,
    )

    assert ring.read_latest(cursor) == post_swap
    assert cursor.last_frame_id == post_swap.frame_id


def test_frame_ring_stores_packet_habitat_without_rebuilding_at_read():
    ring = FrameRing(capacity=4, retention_ticks=128)
    entry = _frame_entry(frame_id=1, tick=1)
    stored_habitat = entry.render_packet.habitat_read_model
    ring.push(entry)

    cursor = RendererCursor(renderer_id="headless", source_state_version=1, habitat_state_version=1)
    read = ring.read_latest(cursor)

    assert read is not None
    assert read.render_packet is entry.render_packet
    assert read.render_packet.habitat_read_model is stored_habitat


# ----- HeadlessRenderer + runtime side-car wire (Task 7) -----


def _ticked_organism(tmp_path: Path, name: str, *, ticks: int, **config_kwargs):
    cfg = OrganismConfig(
        db_path=str(tmp_path / name),
        seed=1,
        embodiment_adapter_enabled=True,
        wall_time_fn=lambda: 0.0,
        **config_kwargs,
    )
    org = create_organism(cfg)
    for _ in range(ticks):
        org.tick_once()
    return org


def test_autonomous_activity_continues_without_user(tmp_path):
    """No renderer, no HeadlessRenderer, no external caller at all beyond
    `tick_once()` — autonomous ticking and frame production must not require
    a user, an observer, or anything polling the ring."""
    org = _ticked_organism(tmp_path, "autonomous.sqlite", ticks=80)
    try:
        assert org.tick == 80
        assert org.running is False  # tick_once never needs a running/observed loop
        assert len(org.frame_ring) == min(80, org.frame_ring.capacity)
        assert org.frame_ring.oldest_frame_id is not None
    finally:
        org.close()


def test_rest_and_inactivity_are_valid_visible_states(tmp_path):
    """Gate 5: rest/inactivity are legitimate, correctly-vocabularied visible
    states — never a missing/invalid frame, and never silently dropped."""
    org = _ticked_organism(tmp_path, "rest.sqlite", ticks=0)
    org.phys.fatigue = 0.9  # drives arbitration's fatigue-recovery focus toward REST
    try:
        for _ in range(60):
            org.tick_once()
        entries = list(org.frame_ring)
        assert entries
        inactivity_seen = False
        for entry in entries:
            ps = entry.render_packet.presentation_state
            assert ps.attachment_status == "ATTACHED"
            assert ps.posture in POSTURES
            assert ps.action_phase in ACTION_PHASES
            assert ps.rest_activity_state in RESULT_ACTIVITY_STATES
            if ps.action_phase == "IDLE" or ps.rest_activity_state in ("IDLE", "RESTING"):
                inactivity_seen = True
        assert inactivity_seen  # inactivity actually occurred and rendered validly
    finally:
        org.close()


def test_renderer_does_not_fake_autonomy(tmp_path):
    """A poll with no new committed frame must return `None` and render
    nothing — the renderer can never replay/duplicate a frame as if the
    organism had done something new. Gate 8: the renderer never touches the
    ring itself — this test, as the poller, owns the `RendererCursor` and
    calls `frame_ring.read_latest(cursor)` directly, handing the renderer
    only the resulting entry."""
    org = _ticked_organism(tmp_path, "no_fake.sqlite", ticks=1)
    try:
        renderer = HeadlessRenderer()
        cursor = RendererCursor(renderer_id="headless")
        first = org.frame_ring.read_latest(cursor)
        assert first is not None
        renderer.render(first)
        assert renderer.render_count == 1

        again = org.frame_ring.read_latest(cursor)
        assert again is None  # no new tick happened — nothing new to render

        org.tick_once()
        second = org.frame_ring.read_latest(cursor)
        assert second is not None
        assert second.frame_id > first.frame_id
        renderer.render(second)
        assert renderer.render_count == 2

        renderer.close()  # no-op for core
        assert org.tick == 2  # organism unaffected by renderer close
    finally:
        org.close()


def test_habitat_state_is_not_duplicated(tmp_path):
    """There is exactly one authoritative habitat (`Embodiment.habitat`); the
    expression side-car only ever projects it, never persists or maintains a
    second copy — enabling/disabling expression must not change a single
    authoritative event, and every rendered habitat entity traces straight
    back to the live habitat's own features."""
    cfg_common = dict(seed=4, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0)

    org_with_expression = create_organism(
        OrganismConfig(db_path=str(tmp_path / "dup_on.sqlite"), expression_enabled=True, **cfg_common)
    )
    org_without_expression = create_organism(
        OrganismConfig(db_path=str(tmp_path / "dup_off.sqlite"), expression_enabled=False, **cfg_common)
    )
    try:
        for _ in range(20):
            org_with_expression.tick_once()
            org_without_expression.tick_once()

        # Compare event *types* only (not payloads): body/instance ids are
        # random per organism (`new_id()`) regardless of `expression_enabled`,
        # but the count and sequence of authoritative events must be identical
        # — proving the side-car appends zero extra authoritative events.
        types_on = [e["event_type"] for e in org_with_expression.store.iter_events()]
        types_off = [e["event_type"] for e in org_without_expression.store.iter_events()]
        assert types_on == types_off

        assert len(org_with_expression.frame_ring) == 20
        assert len(org_without_expression.frame_ring) == 0  # disabled: never populated

        latest = list(org_with_expression.frame_ring)[-1]
        live_features = org_with_expression.embodiment.habitat.to_state()["features"]
        rendered_kinds = [
            ent.kind for ent in latest.render_packet.habitat_read_model.entities if ent.kind != "partner"
        ]
        assert rendered_kinds == [f["kind"] for f in live_features]
    finally:
        org_with_expression.close()
        org_without_expression.close()


def test_action_expression_alignment(tmp_path):
    """Every tick's rendered frame must faithfully reflect what `tick_once`
    actually reports for that same tick: a governed denial never shows an
    active capability, and an executed/interrupted outcome always names it."""
    org = _ticked_organism(tmp_path, "alignment.sqlite", ticks=0)
    try:
        cursor = RendererCursor(renderer_id="alignment")
        for _ in range(60):
            result = org.tick_once()
            entry = org.frame_ring.read_latest(cursor)
            assert entry is not None
            assert entry.derived_at_tick == result["tick"]
            ps = entry.render_packet.presentation_state

            if result["denied"] or not result["action_issued"]:
                assert ps.active_capability is None
                assert ps.action_phase != "EXECUTED"
            elif result["outcome"] is not None:
                outcome = result["outcome"]
                if outcome["success"]:
                    assert ps.active_capability == outcome["capability"]
                    assert ps.action_phase == "EXECUTED"
                else:
                    assert ps.active_capability == outcome["capability"]
                    assert ps.action_phase == "INTERRUPTED"
    finally:
        org.close()


def test_expression_disabled_via_config_or_c10_skips_frame_ring(tmp_path):
    """`expression_enabled=False` and the frozen C10 performance-baseline
    condition (design §4) both skip the side-car entirely — the ring stays
    empty and no `ExpressionEngine.derive` work happens."""
    org_off = create_organism(
        OrganismConfig(
            db_path=str(tmp_path / "expr_off.sqlite"),
            seed=1,
            embodiment_adapter_enabled=True,
            expression_enabled=False,
            wall_time_fn=lambda: 0.0,
        )
    )
    org_c10 = create_organism(
        OrganismConfig(
            db_path=str(tmp_path / "expr_c10.sqlite"),
            seed=1,
            embodiment_adapter_enabled=True,
            condition="C10",
            wall_time_fn=lambda: 0.0,
        )
    )
    try:
        for _ in range(10):
            org_off.tick_once()
            org_c10.tick_once()
        assert len(org_off.frame_ring) == 0
        assert len(org_c10.frame_ring) == 0
    finally:
        org_off.close()
        org_c10.close()


def test_expression_view_is_built_from_copied_snapshots_not_live_aliases(tmp_path):
    """Task 5 review watch item, exercised at the runtime wire: the pushed
    frame must not hold a live, still-mutable reference into physiology or
    embodiment — later organism mutation must never retroactively change an
    already-pushed frame."""
    org = _ticked_organism(tmp_path, "copy_safety.sqlite", ticks=1)
    try:
        entry = list(org.frame_ring)[-1]
        channels_before = dict(entry.render_packet.presentation_state.visible_condition_channels)
        habitat_before = entry.render_packet.habitat_read_model.entities

        org.phys.energy = 0.0
        org.phys.fatigue = 1.0
        org.embodiment.habitat.features.clear()

        assert entry.render_packet.presentation_state.visible_condition_channels == channels_before
        assert entry.render_packet.habitat_read_model.entities == habitat_before
    finally:
        org.close()


# ----- Restart, replay, and body-swap continuity (Task 8) -----


def test_restart_preserves_body_position(tmp_path):
    """Gate 6/11: the authoritative body (habitat + embodiment adapter
    attachment) survives a restart byte-identically — no cosmetic frame-ring
    state is involved in body position continuity."""
    db_path = str(tmp_path / "position.sqlite")
    org = create_organism(
        OrganismConfig(db_path=db_path, seed=31, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0)
    )
    org.run_ticks(30)
    live_body = org.embodiment.body.to_state()
    live_attachment = org.embodiment_adapter.state.to_state()
    org.snapshot_if_due(force=True)
    org.close()

    loaded = load_organism(
        OrganismConfig(db_path=db_path, seed=31, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0)
    )
    assert loaded.embodiment.body.to_state() == live_body
    assert loaded.embodiment_adapter.state.to_state() == live_attachment
    loaded.close()


def test_restart_preserves_visible_condition(tmp_path):
    """Gate 6: `visible_condition_channels` is a pure function of restored
    physiology/attention — restart clears the (non-authoritative) frame ring
    and constructs a fresh `ExpressionEngine`, so a freshly derived frame
    right after restart must still show the same visible condition as one
    derived immediately before restart, from a like-new engine either way."""
    db_path = str(tmp_path / "condition.sqlite")
    org = create_organism(
        OrganismConfig(
            db_path=db_path, seed=32, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0
        )
    )
    org.run_ticks(30)

    def _channels(o) -> dict[str, float]:
        view = ExpressionView(
            tick=o.tick,
            physiology=o.phys.as_dict(),
            attachment=AttachmentView(
                attachment_status=o.embodiment_adapter.state.attachment_status,
                body_instance_id=o.embodiment_adapter.state.body_instance_id,
                body_profile_id=o.embodiment_adapter.state.body_profile_id,
                attachment_generation=o.embodiment_adapter.state.attachment_generation,
            ),
            embodiment_state=o.embodiment.to_state(),
            source_state_version=o.tick,
            habitat_state_version=o.tick,
        )
        return ExpressionEngine().derive(view).presentation_state.visible_condition_channels

    live_channels = _channels(org)
    org.snapshot_if_due(force=True)
    org.close()

    loaded = load_organism(
        OrganismConfig(
            db_path=db_path, seed=32, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0
        )
    )
    assert _channels(loaded) == live_channels
    loaded.close()


def test_interrupted_action_resolves_after_restart(tmp_path):
    """A verified-failed (INTERRUPTED) outcome is derived fresh every tick from
    the current outcome, never from carried-forward frame-ring state. Restart
    clears the non-authoritative ring and builds a fresh `ExpressionEngine`, so
    the very next real outcome is rendered on its own merits — the organism
    must never appear permanently stuck showing a pre-restart interruption."""
    db_path = str(tmp_path / "interrupted.sqlite")
    org = create_organism(
        OrganismConfig(
            db_path=db_path, seed=33, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0
        )
    )
    org.embodiment.body.movement_reliability = 0.0  # guarantee the next MOVE slips
    proposal = org.governance.propose("MOVE", {"step": 1.0, "heading": 0.0})
    decision = org.governance.admit(proposal, tick=org.tick)
    outcome = org.governance.execute_and_verify(
        proposal, decision, org.embodiment, org.rng, adapter=org.embodiment_adapter, tick=org.tick
    )
    assert outcome is not None
    assert outcome.success is False  # movement slip -> verified failure, not a crash
    org._push_expression_frame(org._outcome_to_last_outcome_view(outcome))
    pre_restart_entry = list(org.frame_ring)[-1]
    assert pre_restart_entry.render_packet.presentation_state.action_phase == "INTERRUPTED"

    org.snapshot_if_due(force=True)
    org.close()

    loaded = load_organism(
        OrganismConfig(
            db_path=db_path, seed=33, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0
        )
    )
    assert len(loaded.frame_ring) == 0  # non-authoritative ring rebuilt empty on restart
    loaded.embodiment.body.movement_reliability = 1.0  # let the next attempt actually succeed

    resolved = False
    for _ in range(80):
        result = loaded.tick_once()
        if result["outcome"] is not None and result["outcome"]["success"]:
            entry = list(loaded.frame_ring)[-1]
            assert entry.render_packet.presentation_state.action_phase == "EXECUTED"
            resolved = True
            break
    assert resolved  # the organism resumes normally, never stuck post-restart
    loaded.close()


def test_snapshot_replay_matches(tmp_path):
    """Gate 6/11: snapshot-accelerated restart reproduces the live adapter
    attachment and body state exactly (same ledger, same organism)."""
    db_path = str(tmp_path / "replay.sqlite")
    org = create_organism(
        OrganismConfig(
            db_path=db_path,
            seed=34,
            embodiment_adapter_enabled=True,
            expression_enabled=True,
            snapshot_every=10,
            wall_time_fn=lambda: 0.0,
        )
    )
    org.run_ticks(40)
    live_attachment = org.embodiment_adapter.state.to_state()
    live_body = org.embodiment.body.to_state()
    live_phys = org.phys.to_state()
    org.snapshot_if_due(force=True)
    org.close()

    loaded = load_organism(
        OrganismConfig(
            db_path=db_path,
            seed=34,
            embodiment_adapter_enabled=True,
            expression_enabled=True,
            wall_time_fn=lambda: 0.0,
        )
    )
    assert loaded.embodiment_adapter.state.to_state() == live_attachment
    assert loaded.embodiment.body.to_state() == live_body
    assert loaded.phys.to_state() == live_phys
    loaded.close()


def test_birth_replay_matches_authoritative_transitions(tmp_path):
    """Gate 11: attachment reconstructed by the real restart path
    (`load_organism`) — including a D-008 *migration* attach (not just a
    normal `create_organism` attach), then two ledger swaps — matches the
    live adapter's exact `AttachmentState` byte-for-byte. Exercises the
    actual birth/migration/restart machinery rather than re-invoking
    `attachment_state_from_event` on its own output."""
    db_path = _create_legacy_pre_d008_db(tmp_path, "transitions.sqlite", seed=35)
    cfg = OrganismConfig(
        db_path=db_path, seed=35, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0
    )

    org = load_organism(cfg)  # triggers maybe_migrate_d008_attachment
    org.embodiment_adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id)
    org.run_ticks(5)
    org.embodiment_adapter.swap_profile(ABSTRACT_SHAPE_BODY.profile_id)
    live_state = org.embodiment_adapter.state.to_state()
    attach_events = [e for e in org.store.iter_events() if e["event_type"] in ATTACHMENT_EVENT_TYPES]
    org.snapshot_if_due(force=True)
    org.close()

    assert len(attach_events) == 3  # migration attach + swap + swap
    assert attach_events[0]["payload"]["origin"] == "D008_MIGRATION"

    # Real restart path (ledger-authoritative reconstruction), not the bare helper.
    reloaded = load_organism(cfg)
    try:
        assert reloaded.embodiment_adapter.state.to_state() == live_state
    finally:
        reloaded.close()

    replay = replay_from_birth(db_path)
    assert replay["chain_valid"] is True


def test_missing_embodiment_event_fails_closed(tmp_path):
    """Gate 11: deleting the authoritative attach event breaks the same
    hash-chained ledger integrity every other D-00x authoritative event relies
    on. `load_organism` itself — not just `Store.validate_chain()` in
    isolation — must fail closed: it must never silently fall through
    `attachment_state_from_event(None)` and re-migrate a plausible-looking
    "never attached" organism out of a corrupted chain."""
    db_path = str(tmp_path / "missing_event.sqlite")
    cfg = OrganismConfig(
        db_path=db_path, seed=36, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0
    )
    org = create_organism(cfg)
    org.run_ticks(5)
    org.close()

    store = Store(db_path)
    attach_row = next(e for e in store.iter_events() if e["event_type"] == "embodiment_body_attached")
    store.conn.execute("DELETE FROM events WHERE sequence=?", (attach_row["sequence"],))
    with pytest.raises(PersistenceError):
        store.validate_chain()
    store.close()

    with pytest.raises(PersistenceError):
        load_organism(cfg)


# ----- Body-swap preserves identity/memory/relationships/individuality (Task 8) -----


def _swap_org(tmp_path: Path, name: str, seed: int = 37):
    cfg = OrganismConfig(
        db_path=str(tmp_path / name),
        seed=seed,
        embodiment_adapter_enabled=True,
        memory_enabled=True,
        social_enabled=True,
        individuality_enabled=True,
        individuality_history="H1",
        wall_time_fn=lambda: 0.0,
    )
    org = create_organism(cfg)
    org.social.recognize(
        [
            {
                "relative_position": [1.0, 0.5],
                "motion_signature": [0.2, 0.3, 0.1],
                "appearance_signature": [0.5, 0.4, 0.2],
                "response_timing_pattern": [0.3, 0.5, 0.1],
                "interaction_style_cues": [0.6, 0.3, 0.5],
                "cue_confidence": 0.7,
                "cue_uncertainty": 0.3,
                "observed_at": 1.0,
                "expires_at": 13.0,
                "source": "partner_cue",
            }
        ],
        tick=1,
    )
    org.run_ticks(15)
    return org


def test_body_profile_swap_preserves_identity(tmp_path):
    org = _swap_org(tmp_path, "swap_identity.sqlite")
    try:
        agent_id = org.identity.agent_id
        commitment = org.identity.identity_commitment
        org.embodiment_adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id)
        assert org.identity.agent_id == agent_id
        assert org.identity.identity_commitment == commitment
    finally:
        org.close()


def test_body_profile_swap_preserves_memory(tmp_path):
    org = _swap_org(tmp_path, "swap_memory.sqlite")
    try:
        before = org.memory.to_state()
        assert org.memory.episodes  # non-trivial state actually exists to preserve
        org.embodiment_adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id)
        assert org.memory.to_state() == before
    finally:
        org.close()


def test_body_profile_swap_preserves_relationships(tmp_path):
    org = _swap_org(tmp_path, "swap_relationships.sqlite")
    try:
        before = org.social.to_state()
        assert before["hypotheses"]  # non-trivial relationship state exists to preserve
        org.embodiment_adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id)
        assert org.social.to_state() == before
    finally:
        org.close()


def test_body_profile_swap_preserves_individuality(tmp_path):
    org = _swap_org(tmp_path, "swap_individuality.sqlite")
    try:
        before = org.individuality.accepted_state()
        assert before["dispositions"]  # non-trivial disposition state exists to preserve
        org.embodiment_adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id)
        assert org.individuality.accepted_state() == before
    finally:
        org.close()


# ----- Avatar/UI identifiers absent from identity + individuality (Task 8) -----


def test_avatar_identifier_absent_from_constitutional_identity(tmp_path):
    """Gate 6/7: avatar/body/UI identifiers must never enter constitutional
    identity — swapping the body must not change `agent_id` or the
    commitment hash, and no identity field names avatar/body/render/UI."""
    forbidden_substrings = ("avatar", "body_instance", "body_profile", "render", "ui_id", "display")
    field_names = {f.name for f in dataclasses.fields(ConstitutionalIdentity)}
    for name in field_names:
        lowered = name.lower()
        for bad in forbidden_substrings:
            assert bad not in lowered, f"forbidden identity field: {name}"

    org = create_organism(
        OrganismConfig(db_path=str(tmp_path / "avatar.sqlite"), seed=38, embodiment_adapter_enabled=True, wall_time_fn=lambda: 0.0)
    )
    try:
        agent_id = org.identity.agent_id
        commitment = org.identity.identity_commitment
        org.embodiment_adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id)
        assert org.identity.agent_id == agent_id
        assert org.identity.identity_commitment == commitment
    finally:
        org.close()


def test_ui_identifier_absent_from_individuality_state():
    """Gate 6/7: `IndividualityEngine` already enforces `FORBIDDEN_STATE_KEYS`
    (avatar_id, ui_component_id, screen_coordinates, animation_name, ...) on
    every `to_state()` call — this exercises that guarantee explicitly for
    D-008's avatar/UI-identifier continuity requirement."""
    assert {"avatar_id", "ui_component_id", "screen_coordinates", "animation_name"} <= FORBIDDEN_STATE_KEYS
    engine = IndividualityEngine.create("agent-ui-check", seed=1)
    state = engine.to_state()  # raises IndividualityEngineError if any forbidden key is present
    blob = json.dumps(state, default=str)
    for bad in FORBIDDEN_STATE_KEYS:
        assert bad not in blob


# ----- Tkinter reference companion (Task 9) -----


class _FakeCanvas:
    """Duck-typed stand-in for `tkinter.Canvas` — records calls only, no
    real widget and no display required. `habitat_view`/`diagnostics` only
    ever call this small subset of the real `tkinter.Canvas` API."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def delete(self, *args, **kwargs):
        self.calls.append(("delete", args, kwargs))

    def create_oval(self, *args, **kwargs):
        self.calls.append(("create_oval", args, kwargs))
        return len(self.calls)

    def create_line(self, *args, **kwargs):
        self.calls.append(("create_line", args, kwargs))
        return len(self.calls)

    def create_text(self, *args, **kwargs):
        self.calls.append(("create_text", args, kwargs))
        return len(self.calls)


def _rendered_texts(canvas: _FakeCanvas) -> list[str]:
    return [str(kwargs.get("text", "")) for name, _, kwargs in canvas.calls if name == "create_text"]


def test_experiments_and_core_never_import_ui():
    """Design §1 import rule: `umbra_core` and `experiments` must never
    import `ui/` — parsed via `ast` so this holds regardless of comments or
    string mentions, only real import statements."""
    for base_name in ("umbra_core", "experiments"):
        base = ROOT / base_name
        for path in base.rglob("*.py"):
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name.split(".")[0] != "ui", f"{path} imports ui: {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert node.module.split(".")[0] != "ui", f"{path} imports from ui: {node.module}"


def test_ui_reference_companion_only_imports_expression_from_core():
    """`ui/` may import `umbra_core.expression` (design §1); it must never
    reach into governance, persistence, runtime, or any other writable core
    module."""
    ui_root = ROOT / "ui" / "reference_companion"
    assert list(ui_root.glob("*.py"))  # package actually exists with modules
    for path in ui_root.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            for module in modules:
                if module == "umbra_core" or module.startswith("umbra_core."):
                    assert module == "umbra_core.expression" or module.startswith(
                        "umbra_core.expression."
                    ), f"{path} imports {module}"


def test_habitat_canvas_excludes_capability_phase_version_diagnostics(tmp_path):
    """Habitat canvas = shapes/orientation/posture/attention/icons only;
    capability/phase/versions belong in `diagnostics.py`, never on the
    habitat canvas (design §3: 'Not a status dashboard')."""
    org = _ticked_organism(tmp_path, "habitat_excludes.sqlite", ticks=10)
    try:
        entry = list(org.frame_ring)[-1]
        ps = entry.render_packet.presentation_state
        canvas = _FakeCanvas()
        habitat_view.render_habitat(canvas, entry.render_packet)
        rendered_text = " ".join(_rendered_texts(canvas))
        forbidden = [ps.action_phase, str(entry.render_packet.source_state_version)]
        if ps.active_capability:
            forbidden.append(ps.active_capability)
        for term in forbidden:
            assert term not in rendered_text
    finally:
        org.close()


def test_diagnostics_panel_shows_capability_phase_and_versions(tmp_path):
    """Diagnostics (optional) carry exactly the fields the habitat canvas
    must not: capability, phase, versions, source refs, condition channels."""
    org = _ticked_organism(tmp_path, "diagnostics_shows.sqlite", ticks=10)
    try:
        entry = list(org.frame_ring)[-1]
        canvas = _FakeCanvas()
        diagnostics.render_diagnostics(canvas, entry.render_packet)
        rendered_text = " ".join(_rendered_texts(canvas))
        assert "capability=" in rendered_text
        assert "phase=" in rendered_text
        assert str(entry.render_packet.source_state_version) in rendered_text
        assert str(entry.render_packet.habitat_state_version) in rendered_text
    finally:
        org.close()


def test_renderer_cannot_write_core_state(tmp_path):
    """Neither `habitat_view.render_habitat`/`diagnostics.render_diagnostics`
    nor `TkinterRenderer` itself take an organism/embodiment/adapter
    reference — the only channel in is an already-derived `RenderPacket`
    read from the frame ring — so rendering has no path to mutate
    physiology, embodiment, memory, identity, or the frame ring itself."""
    for fn in (habitat_view.render_habitat, diagnostics.render_diagnostics):
        assert list(inspect.signature(fn).parameters) == ["canvas", "packet"]

    init_params = inspect.signature(TkinterRenderer.__init__).parameters
    render_params = inspect.signature(TkinterRenderer.render).parameters
    for forbidden in (
        "organism",
        "embodiment",
        "adapter",
        "governance",
        "phys",
        "physiology",
        "store",
        "ring",
        "reader",
        "frame_ring",
    ):
        assert forbidden not in init_params
        assert forbidden not in render_params
    assert list(render_params) == ["self", "entry"]  # Gate 8: render's only channel in
    assert not hasattr(TkinterRenderer, "read_latest")
    assert not hasattr(TkinterRenderer, "poll_and_render")
    assert not hasattr(TkinterRenderer, "schedule")

    org = _ticked_organism(tmp_path, "no_write.sqlite", ticks=10)
    try:
        entry = list(org.frame_ring)[-1]
        embodiment_before = org.embodiment.to_state()
        phys_before = org.phys.to_state()
        ring_len_before = len(org.frame_ring)

        canvas = _FakeCanvas()
        habitat_view.render_habitat(canvas, entry.render_packet)
        diagnostics.render_diagnostics(canvas, entry.render_packet)

        assert org.embodiment.to_state() == embodiment_before
        assert org.phys.to_state() == phys_before
        assert len(org.frame_ring) == ring_len_before
        assert canvas.calls  # actually drew something, not a no-op stub
    finally:
        org.close()


def test_two_body_profiles_render_same_organism(tmp_path):
    """Design §1: production body profiles may differ in geometry/posture
    mapping but must not materially prevent rendering continuity for the
    same organism — swapping profile must not raise, blank the body layer,
    or change which organism is being visualized."""
    org = _ticked_organism(tmp_path, "two_profiles.sqlite", ticks=5)
    try:
        assert org.embodiment_adapter.state.body_profile_id == ABSTRACT_SHAPE_BODY.profile_id
        entry_a = list(org.frame_ring)[-1]
        body_instance_id = entry_a.render_packet.presentation_state.body_instance_id
        canvas_a = _FakeCanvas()
        habitat_view.render_habitat(canvas_a, entry_a.render_packet)
        diagnostics.render_diagnostics(canvas_a, entry_a.render_packet)
        assert canvas_a.calls

        org.embodiment_adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id)
        for _ in range(5):
            org.tick_once()
        entry_b = list(org.frame_ring)[-1]
        assert entry_b.render_packet.presentation_state.body_profile_id == MINIMAL_CREATURE_BODY.profile_id
        assert entry_b.render_packet.presentation_state.body_instance_id == body_instance_id  # same organism/body

        canvas_b = _FakeCanvas()
        habitat_view.render_habitat(canvas_b, entry_b.render_packet)
        diagnostics.render_diagnostics(canvas_b, entry_b.render_packet)
        assert canvas_b.calls
    finally:
        org.close()


def _real_tkinter_renderer(**kwargs) -> TkinterRenderer:
    tk = pytest.importorskip("tkinter")
    try:
        return TkinterRenderer(**kwargs)
    except tk.TclError as exc:
        pytest.skip(f"no Tk display available: {exc}")


def test_reference_interface_runs_without_diagnostics(tmp_path):
    """The full `ReferenceRenderer` contract (render/set_diagnostics_visible/
    close) must work correctly with diagnostics off by default — diagnostics
    are optional and removable without changing the inhabited-world canvas
    or organism behavior (design §3). Gate 8: this test, as the poller, owns
    the `RendererCursor` and calls `frame_ring.read_latest(cursor)` directly
    — the renderer itself never touches the ring. Only this test needs a
    real Tk display; it skips honestly when unavailable rather than faking a
    soak (formal soak requires a real Canvas — brief note)."""
    org = _ticked_organism(tmp_path, "tk_no_diag.sqlite", ticks=3)
    renderer = _real_tkinter_renderer()
    cursor = RendererCursor(renderer_id="tkinter")
    try:
        assert renderer.diagnostics_visible is False

        entry = org.frame_ring.read_latest(cursor)
        assert entry is not None
        renderer.render(entry)
        assert renderer.render_count == 1
        assert renderer.last_render_error is None
        assert org.frame_ring.read_latest(cursor) is None  # non-destructive, no new frame yet

        renderer.set_diagnostics_visible(True)
        assert renderer.diagnostics_visible is True
        org.tick_once()
        entry2 = org.frame_ring.read_latest(cursor)
        assert entry2 is not None
        renderer.render(entry2)
        assert renderer.render_count == 2
        assert renderer.last_render_error is None

        renderer.close()
        renderer.close()  # idempotent
        assert org.tick == 4  # organism unaffected by renderer close
    finally:
        renderer.close()
        org.close()


def test_tkinter_renderer_close_leaves_organism_running(tmp_path):
    """`close()` destroys only window resources — the organism, adapter, and
    `ExpressionEngine` keep running untouched. Gate 8: closing the renderer
    has no bearing on the ring/cursor at all (the renderer never held
    either) — a closed renderer's `render()` simply becomes a no-op."""
    org = _ticked_organism(tmp_path, "tk_close.sqlite", ticks=1)
    renderer = _real_tkinter_renderer(renderer_id="closing-tk")
    cursor = RendererCursor(renderer_id="closing-tk")
    try:
        entry = org.frame_ring.read_latest(cursor)
        assert entry is not None
        renderer.render(entry)
        assert renderer.render_count == 1

        renderer.close()
        renderer.render(entry)  # closed renderer: render() is a no-op, never raises
        assert renderer.render_count == 1  # did not re-render after close

        for _ in range(5):
            org.tick_once()
        assert org.tick == 6
        assert len(org.frame_ring) > 0  # organism/expression side-car kept running
    finally:
        renderer.close()
        org.close()


# ----- Nonverbal signals + individuality presentation (Task 10) -----


def test_signal_play_is_visibly_expressed():
    """A verified `SIGNAL_PLAY` outcome must render as a distinct nonverbal
    icon + interacting posture — never silently folded into a generic
    ACTIVE/MOVE presentation (design Gate 9)."""
    outcome = LastOutcomeView(
        capability="SIGNAL_PLAY", admitted=True, success=True, target="partner-1"
    )
    packet = ExpressionEngine().derive(_expression_view(last_outcome=outcome))
    ps = packet.presentation_state

    assert ps.nonverbal_signal == "SIGNAL_PLAY"
    assert ps.posture == "INTERACTING"
    assert ps.action_phase == "EXECUTED"
    assert ps.interaction_target == "partner-1"


def test_signal_assistance_is_visibly_expressed():
    outcome = LastOutcomeView(
        capability="SIGNAL_ASSISTANCE", admitted=True, success=True, target="partner-2"
    )
    packet = ExpressionEngine().derive(_expression_view(last_outcome=outcome))
    ps = packet.presentation_state

    assert ps.nonverbal_signal == "SIGNAL_ASSISTANCE"
    assert ps.posture == "INTERACTING"
    assert ps.interaction_target == "partner-2"


def test_signal_does_not_directly_change_relationship():
    """`ExpressionEngine.derive` never receives a `Social`/relationship
    reference (design ownership table: ExpressionEngine cannot write core
    state) — deriving a SIGNAL_PLAY frame must leave an independent
    `SocialEngine`'s state byte-identical."""
    social = SocialEngine.create("agent-1")
    before = social.to_state()

    outcome = LastOutcomeView(
        capability="SIGNAL_PLAY", admitted=True, success=True, target="partner-1"
    )
    ExpressionEngine().derive(_expression_view(last_outcome=outcome))

    assert social.to_state() == before
    sig = inspect.signature(ExpressionEngine.derive)
    assert "social" not in sig.parameters and "relationship" not in sig.parameters


def _disposition_summary(**values: float) -> dict:
    vec = {dim: 0.0 for dim in IndividualityEngine.create("a").disposition_vector()}
    vec.update(values)
    return {"disposition_vector": vec}


def test_individuality_history_changes_visible_behavior():
    """Two organisms with identical physiology and the same executed action
    but different history-shaped dispositions (D-007) must present visibly
    differently — individuality is not decoration, but it stays a bounded
    nudge on existing channels, never a new capability or posture."""
    outcome = LastOutcomeView(capability="MOVE", admitted=True, success=True)
    neutral = ExpressionEngine().derive(
        _expression_view(last_outcome=outcome, individuality_summary=_disposition_summary())
    )
    shaped = ExpressionEngine().derive(
        _expression_view(
            last_outcome=outcome,
            individuality_summary=_disposition_summary(
                persistence_after_failure=0.8, recovery_pacing=0.8, stimulation_tolerance=0.8
            ),
        )
    )

    assert (
        neutral.presentation_state.visible_condition_channels
        != shaped.presentation_state.visible_condition_channels
    )
    # Same action still visibly the same action — individuality shades, does not author.
    assert neutral.presentation_state.posture == shaped.presentation_state.posture
    assert neutral.presentation_state.active_capability == shaped.presentation_state.active_capability


def test_renderer_does_not_create_authored_personality():
    """Individuality/habit/routine influence on presentation must stay a
    small bounded nudge on the frozen 9 condition channels — it must never
    add a new `PresentationState` field, change which capability/posture is
    depicted, or swing a channel outside [0, 1] or past its declared bound."""
    field_names = {f.name for f in dataclasses.fields(PresentationState)}
    forbidden = ("personality", "mood", "emotion", "affect", "temperament_profile")
    for name in field_names:
        for bad in forbidden:
            assert bad not in name.lower()

    outcome = LastOutcomeView(capability="MOVE", admitted=True, success=True)
    baseline = ExpressionEngine().derive(_expression_view(last_outcome=outcome))
    extreme = ExpressionEngine().derive(
        _expression_view(
            last_outcome=outcome,
            individuality_summary={
                "disposition_vector": {
                    dim: 1.0 for dim in IndividualityEngine.create("a").disposition_vector()
                },
                "habit_active": True,
                "routine_active": True,
            },
        )
    )

    assert baseline.presentation_state.posture == extreme.presentation_state.posture
    assert baseline.presentation_state.active_capability == extreme.presentation_state.active_capability
    assert baseline.presentation_state.nonverbal_signal == extreme.presentation_state.nonverbal_signal
    for key, base_val in baseline.presentation_state.visible_condition_channels.items():
        shaped_val = extreme.presentation_state.visible_condition_channels[key]
        assert 0.0 <= shaped_val <= 1.0
        assert abs(shaped_val - base_val) <= 0.30 + 1e-9


def test_learned_habit_is_visibly_expressed():
    """A learned individual habit (bounded D-005 procedural pattern, surfaced
    read-only via `individuality_summary["habit_active"]`) visibly shows as a
    steadier, quicker-settling transition compared to unfamiliar action."""
    outcome = LastOutcomeView(capability="MOVE", admitted=True, success=True)
    without_habit = ExpressionEngine().derive(_expression_view(last_outcome=outcome))
    with_habit = ExpressionEngine().derive(
        _expression_view(last_outcome=outcome, individuality_summary={"habit_active": True})
    )

    assert (
        with_habit.presentation_state.visible_condition_channels["transition_speed"]
        > without_habit.presentation_state.visible_condition_channels["transition_speed"]
    )


def test_shared_routine_is_visibly_expressed():
    """A partner-scoped shared routine (D-006 `social_routine` procedural
    promotion, surfaced read-only via `individuality_summary["routine_active"]`)
    visibly shows as sustained attentional persistence, distinct from an
    isolated habit."""
    outcome = LastOutcomeView(capability="SIGNAL_PLAY", admitted=True, success=True, target="p-1")
    without_routine = ExpressionEngine().derive(_expression_view(last_outcome=outcome))
    with_routine = ExpressionEngine().derive(
        _expression_view(last_outcome=outcome, individuality_summary={"routine_active": True})
    )

    assert (
        with_routine.presentation_state.visible_condition_channels["attentional_persistence"]
        > without_routine.presentation_state.visible_condition_channels["attentional_persistence"]
    )
    # Habit and routine are independent signals — routine alone must not move transition_speed.
    assert (
        with_routine.presentation_state.visible_condition_channels["transition_speed"]
        == without_routine.presentation_state.visible_condition_channels["transition_speed"]
    )


def test_recovery_restores_visible_activity():
    """`CHARGE` visibly presents as RECOVERING; once a subsequent action
    executes, the presentation must visibly resume ACTIVE — recovery is a
    passing visible state, not a sticky one (design: `CHARGE` presents
    maintenance/recovery)."""
    engine = ExpressionEngine()
    charging = engine.derive(
        _expression_view(
            tick=1, last_outcome=LastOutcomeView(capability="CHARGE", admitted=True, success=True)
        )
    )
    assert charging.presentation_state.posture == "RECOVERING"
    assert charging.presentation_state.rest_activity_state == "RECOVERING"

    resumed = engine.derive(
        _expression_view(
            tick=2, last_outcome=LastOutcomeView(capability="MOVE", admitted=True, success=True)
        )
    )
    assert resumed.presentation_state.posture == "ACTIVE"
    assert resumed.presentation_state.rest_activity_state == "ACTIVE"
    assert resumed.presentation_state.posture != charging.presentation_state.posture


def test_orientation_matches_selected_target():
    """`orientation` passes through the already-computed body heading
    (`Embodiment` owns turning physics toward a target — design §1); the
    presentation must reflect exactly that heading and name the same target
    the organism actually approached/oriented toward, never a re-derived or
    invented one."""
    embodiment = Embodiment()
    embodiment.body.heading = 1.25  # radians — as if ORIENT already turned to face the target
    outcome = LastOutcomeView(capability="ORIENT", admitted=True, success=True, target="resource-7")

    packet = ExpressionEngine().derive(_expression_view(last_outcome=outcome, embodiment=embodiment))
    ps = packet.presentation_state

    assert ps.orientation == pytest.approx(1.25)
    assert ps.interaction_target == "resource-7"


def test_cosmetic_motion_is_non_authoritative():
    """Cosmetic secondary motion belongs solely to the renderer (design §1
    ownership table: 'Renderer: ... cosmetic motion (local wall time)').
    `ExpressionEngine` must derive a deterministic, wall-clock-free semantic
    presentation — repeated derivation from an unchanged view yields an
    identical `PresentationState`, and the engine module never touches
    `time`/`random` to fabricate motion of its own."""
    import umbra_core.expression.engine as engine_mod

    src = inspect.getsource(engine_mod)
    assert "time.time" not in src
    assert "random." not in src

    outcome = LastOutcomeView(capability="INSPECT", admitted=True, success=True)
    view = _expression_view(tick=1, last_outcome=outcome)
    first = ExpressionEngine().derive(view)
    second = ExpressionEngine().derive(view)

    assert first.presentation_state == second.presentation_state


def test_live_organism_populates_individuality_summary_via_push_expression_frame(tmp_path):
    """Task 10 finding fix: `Organism._push_expression_frame` must populate
    `ExpressionView.individuality_summary` from the organism's own live
    `IndividualityEngine` — not leave the field empty on the runtime path
    (previously only exercised via a manually built `ExpressionView`). Drives
    two real organism ticks (`individuality_enabled` + `expression_enabled`,
    `modifiers_affect_arbitration=False` so disposition differences cannot
    change which action is chosen) and asserts the rendered visible condition
    channels differ once the organisms' own dispositions differ."""

    def _make(name: str):
        cfg = OrganismConfig(
            db_path=str(tmp_path / name),
            seed=11,
            individuality_enabled=True,
            individuality_config=IndividualityConfig(modifiers_affect_arbitration=False),
            expression_enabled=True,
            wall_time_fn=lambda: 0.0,
        )
        return create_organism(cfg)

    neutral = _make("neutral.sqlite")
    shaped = _make("shaped.sqlite")
    try:
        # H0 (default individuality_history) plants `learning_context =
        # "safe_explore"` — exactly the scope `_finish_outcome` already learns
        # in every tick. Seed strong, repeated *verified* evidence there via
        # the same public `observe_verified` the runtime itself calls, so
        # `shaped`'s real `disposition_vector()` differs from `neutral`'s
        # zeroed one before either organism ticks.
        for i in range(25):
            for dim in ("persistence_after_failure", "recovery_pacing", "stimulation_tolerance"):
                shaped.individuality.observe_verified(
                    VerifiedEvidence(
                        evidence_id=f"seed-{dim}-{i}",
                        tick=0,
                        source_system="outcome",
                        dimension=dim,
                        context_scope="safe_explore",
                        signed_outcome=1.0,
                        from_episode=True,
                    )
                )
        assert shaped.individuality.disposition_vector("safe_explore") != neutral.individuality.disposition_vector(
            "safe_explore"
        )

        neutral.tick_once()
        shaped.tick_once()

        neutral_channels = list(neutral.frame_ring)[
            -1
        ].render_packet.presentation_state.visible_condition_channels
        shaped_channels = list(shaped.frame_ring)[-1].render_packet.presentation_state.visible_condition_channels
        assert neutral_channels != shaped_channels
    finally:
        neutral.close()
        shaped.close()


# --- Task 11: isolated ablations C1-C10 ---


def test_condition_to_expression_config_maps_c4_c5_c6():
    assert condition_to_expression_config("C0") == ExpressionConfig()
    assert condition_to_expression_config("C4") == ExpressionConfig(ignore_actions=True)
    assert condition_to_expression_config("C5") == ExpressionConfig(ignore_individuality=True)
    assert condition_to_expression_config("C6") == ExpressionConfig(ignore_physiology=True)
    # C9 (shuffled frames) and C10 (fully disabled via _expression_active) need
    # no engine-level switch — same pattern as D-007's C9 harness-level shuffle.
    assert condition_to_expression_config("C9") == ExpressionConfig()
    assert condition_to_expression_config("C10") == ExpressionConfig()


@pytest.mark.parametrize("condition", ["C1", "C2", "C3", "C7", "C8"])
def test_condition_to_expression_config_rejects_diagnostic_only_conditions(condition):
    with pytest.raises(ExpressionConfigError):
        condition_to_expression_config(condition)


def test_scripted_animation_condition_is_isolated():
    """C1: scripted animation scheduler never shares the production
    `condition_to_expression_config` schema and never reads organism state —
    it only advances a fixed schedule by call count."""
    with pytest.raises(ExpressionConfigError):
        condition_to_expression_config("C1")
    ctrl = ScriptedAnimationScheduler()
    labels = [ctrl.advance() for _ in range(len(ctrl.schedule) + 2)]
    assert labels[0] == labels[len(ctrl.schedule)]  # deterministic wrap, no core input
    assert_not_production_schema(ctrl)
    with pytest.raises(TypeError):
        assert_not_production_schema(object())


def test_random_expression_condition_is_isolated():
    """C2: presentation drawn from a seeded RNG only — deterministic by seed,
    with no causal link to action/physiology/attention/individuality."""
    with pytest.raises(ExpressionConfigError):
        condition_to_expression_config("C2")
    a = RandomPresentationController(seed=7)
    b = RandomPresentationController(seed=7)
    assert [a.advance() for _ in range(10)] == [b.advance() for _ in range(10)]
    c = RandomPresentationController(seed=8)
    assert [RandomPresentationController(seed=7).advance() for _ in range(10)] != [
        c.advance() for _ in range(10)
    ]


def test_scalar_mood_controller_is_isolated():
    """C3: a single externally-poked scalar maps directly to a canned label —
    never derived from real physiology or action history."""
    with pytest.raises(ExpressionConfigError):
        condition_to_expression_config("C3")
    ctrl = ScalarMoodController(mood=0.9)
    assert ctrl.render() == "ACTIVE"
    ctrl.mood = 0.5
    assert ctrl.render() == "NEUTRAL"
    ctrl.mood = 0.1
    assert ctrl.render() == "RESTING"


def test_ignore_actions_condition_hides_executed_capability():
    """C4: actions execute (untouched by this presentation-only flag) but
    the engine renders every tick as if no outcome existed at all."""
    outcome = LastOutcomeView(capability="MOVE", admitted=True, success=True, execution_id="e1")
    view = _expression_view(tick=1, last_outcome=outcome)

    baseline = ExpressionEngine().derive(view).presentation_state
    assert baseline.active_capability == "MOVE"
    assert baseline.action_phase == "EXECUTED"

    ablated = ExpressionEngine(config=condition_to_expression_config("C4")).derive(view).presentation_state
    assert ablated.active_capability is None
    assert ablated.action_phase == "IDLE"


def test_ignore_individuality_condition_removes_bias():
    """C5: presentation ignores learned individuality — the bounded
    disposition-shaped channel bias disappears while the physiology-driven
    baseline stays intact."""
    summary = {
        "disposition_vector": {
            "persistence_after_failure": 1.0,
            "recovery_pacing": 1.0,
            "stimulation_tolerance": 1.0,
        }
    }
    view = _expression_view(tick=1, individuality_summary=summary)

    baseline = ExpressionEngine().derive(view).presentation_state.visible_condition_channels
    ablated = (
        ExpressionEngine(config=condition_to_expression_config("C5"))
        .derive(view)
        .presentation_state.visible_condition_channels
    )
    assert baseline["persistence"] != ablated["persistence"]
    assert baseline["activity_intensity"] != ablated["activity_intensity"]


def test_ignore_physiology_condition_flattens_channels():
    """C6: presentation ignores physiology — two views with wildly different
    energy/fatigue/integrity/stimulation render identical channels once
    ablated, while the un-ablated baseline visibly differs."""
    hungry = _expression_view(
        tick=1, physiology={"energy": 0.1, "fatigue": 0.9, "integrity": 0.2, "stimulation": 0.1}
    )
    rested = _expression_view(
        tick=1, physiology={"energy": 0.9, "fatigue": 0.1, "integrity": 0.9, "stimulation": 0.9}
    )

    ablated_hungry = (
        ExpressionEngine(config=condition_to_expression_config("C6"))
        .derive(hungry)
        .presentation_state.visible_condition_channels
    )
    ablated_rested = (
        ExpressionEngine(config=condition_to_expression_config("C6"))
        .derive(rested)
        .presentation_state.visible_condition_channels
    )
    assert ablated_hungry == ablated_rested

    baseline_hungry = ExpressionEngine().derive(hungry).presentation_state.visible_condition_channels
    baseline_rested = ExpressionEngine().derive(rested).presentation_state.visible_condition_channels
    assert baseline_hungry != baseline_rested


def test_expression_config_override_wires_into_live_organism(tmp_path):
    """`OrganismConfig.expression_config` (Task 11) reaches the organism's
    real `ExpressionEngine` — actions keep executing normally (C4 never
    touches Embodiment/Governance), only the rendered presentation is blind
    to them."""
    org = _ticked_organism(
        tmp_path,
        "c4_wired.sqlite",
        ticks=0,
        expression_config=condition_to_expression_config("C4"),
    )
    try:
        assert org.expression_engine.config.ignore_actions is True
        executed_for_real = False
        for _ in range(40):
            result = org.tick_once()
            entry = list(org.frame_ring)[-1]
            ps = entry.render_packet.presentation_state
            assert ps.active_capability is None
            assert ps.action_phase != "EXECUTED"
            outcome = result.get("outcome")
            if outcome and outcome.get("success"):
                executed_for_real = True
        assert executed_for_real  # actions really ran despite blind presentation
    finally:
        org.close()


def test_hostile_renderer_write_attempts_are_rejected(tmp_path):
    """C7 (Gate 8): a hostile renderer implementing the exact same
    `ReferenceRenderer` shape as `HeadlessRenderer` — never constructed with
    an Organism/Embodiment/Physiology/Governance reference — cannot mutate
    the derived presentation it reads and cannot touch organism core state.
    Gate 8 follow-up: `render` takes only `entry` (no ring/reader parameter
    anywhere), so the hostile renderer has no channel to receive or store a
    live `FrameRing` in the first place — no `_ring` attribute exists after
    a real read+render cycle."""
    init_params = inspect.signature(HostileRenderer).parameters
    render_params = inspect.signature(HostileRenderer.render).parameters
    for forbidden in (
        "organism",
        "embodiment",
        "adapter",
        "governance",
        "phys",
        "physiology",
        "store",
        "ring",
        "reader",
        "frame_ring",
    ):
        assert forbidden not in init_params
        assert forbidden not in render_params
    assert list(render_params) == ["self", "entry"]  # the only channel in

    org = _ticked_organism(tmp_path, "hostile.sqlite", ticks=10)
    try:
        hostile = HostileRenderer()
        embodiment_before = org.embodiment.to_state()
        phys_before = org.phys.to_state()
        ring_len_before = len(org.frame_ring)

        cursor = RendererCursor(renderer_id="hostile")
        entry = org.frame_ring.read_latest(cursor)
        assert entry is not None
        hostile.render(entry)

        assert hostile.attempted_writes
        assert hostile.successful_writes == []
        assert set(hostile.rejected_writes) == set(hostile.attempted_writes)
        assert "mutate_visible_condition_channel" in hostile.rejected_writes
        assert "mutate_developmental_marker" in hostile.rejected_writes
        # No path to push a forged frame into the organism's ring exists at
        # all: no stored ring/reader reference, no ring-shaped attribute.
        assert not hasattr(hostile, "_ring")
        assert not hasattr(hostile, "ring")

        assert org.embodiment.to_state() == embodiment_before
        assert org.phys.to_state() == phys_before
        assert len(org.frame_ring) == ring_len_before
    finally:
        org.close()


def test_reference_renderer_protocol_has_no_ring_channel():
    """Gate 8 follow-up: neither the `ReferenceRenderer` protocol nor any
    concrete renderer has a method that accepts a `FrameRing`/reader
    argument — `render` takes only the already-read `FrameRingEntry`, so no
    conforming renderer can be handed the live ring at all (not even a
    read-only wrapper, closing the `reader._ring` leak the prior revision
    left open)."""
    for renderer_cls in (HeadlessRenderer, HostileRenderer, TkinterRenderer):
        params = inspect.signature(renderer_cls.render).parameters
        assert list(params) == ["self", "entry"]
        assert not hasattr(renderer_cls, "read_latest")
        assert not hasattr(renderer_cls, "poll_from")

    protocol_params = inspect.signature(ReferenceRenderer.render).parameters
    assert list(protocol_params) == ["self", "entry"]
    assert not hasattr(ReferenceRenderer, "read_latest")


def test_presentation_state_nested_mappings_are_frozen(tmp_path):
    """Gate 8: `visible_condition_channels`/`developmental_markers` are
    frozen at construction — in-place mutation raises, and does not affect
    the ring's stored truth or the next read."""
    org = _ticked_organism(tmp_path, "nested_frozen.sqlite", ticks=1)
    try:
        entry = list(org.frame_ring)[-1]
        ps = entry.render_packet.presentation_state
        with pytest.raises(TypeError):
            ps.visible_condition_channels["persistence"] = 999.0
        with pytest.raises(TypeError):
            ps.developmental_markers["hacked"] = True

        channels_before = dict(ps.visible_condition_channels)
        org.tick_once()
        next_entry = list(org.frame_ring)[-1]
        assert next_entry.render_packet.presentation_state.visible_condition_channels != {
            "persistence": 999.0
        }
        assert dict(ps.visible_condition_channels) == channels_before
    finally:
        org.close()


def test_c8_disposable_db_guard_accepts_tmp_and_scratch_paths(tmp_path):
    assert_disposable_db_path(tmp_path / "c8_scratch.sqlite")
    assert_disposable_db_path(ROOT / "experiments" / "d008" / "c8_scratch.sqlite")


def test_c8_disposable_db_guard_rejects_production_paths():
    for bad in (
        ROOT / "docs" / "evidence" / "d008" / "organism.sqlite",
        ROOT / ".agent" / "organism.sqlite",
        ROOT / "umbra_core" / "organism.sqlite",
    ):
        with pytest.raises(ValueError):
            assert_disposable_db_path(bad)
