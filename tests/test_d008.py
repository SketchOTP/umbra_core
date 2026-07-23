"""UMBRA-D-008 coherent embodiment profile tests."""

from __future__ import annotations

import dataclasses
import inspect
import json
from pathlib import Path

import pytest

from experiments.d008.constrained_profile import CONSTRAINED_TEST_BODY
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
    ExpressionEngine,
    ExpressionView,
    FrameRing,
    FrameRingEntry,
    HeadlessRenderer,
    LastOutcomeView,
    PresentationState,
    RendererCursor,
)
from umbra_core.expression.presentation_state import RESULT_ACTIVITY_STATES
from umbra_core.governance import Governance
from umbra_core.identity import ConstitutionalIdentity
from umbra_core.individuality import FORBIDDEN_STATE_KEYS, IndividualityEngine
from umbra_core.persistence import PersistenceError, Store
from umbra_core.physiology import Physiology
from umbra_core.runtime import (
    OrganismConfig,
    create_organism,
    load_organism,
    maybe_migrate_d008_attachment,
    replay_from_birth,
)
from umbra_core.util import SeededRNG

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
) -> ExpressionView:
    embodiment = Embodiment()
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
    organism had done something new."""
    org = _ticked_organism(tmp_path, "no_fake.sqlite", ticks=1)
    try:
        renderer = HeadlessRenderer()
        first = renderer.read_latest(org.frame_ring)
        assert first is not None
        renderer.render(first)
        assert renderer.render_count == 1

        again = renderer.read_latest(org.frame_ring)
        assert again is None  # no new tick happened — nothing new to render

        org.tick_once()
        second = renderer.read_latest(org.frame_ring)
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
