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
    AdapterRequest,
    EmbodimentAdapter,
)
from umbra_core.events import AUTHORITATIVE_EVENT_TYPES
from umbra_core.expression import (
    ATTENTION_CONFIDENCE_DISPLAY_THRESHOLD,
    AttachmentView,
    AttentionView,
    ExpressionEngine,
    ExpressionView,
    LastOutcomeView,
    PresentationState,
)
from umbra_core.governance import Governance
from umbra_core.persistence import Store
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
            attachment_generation=1,
        ),
        embodiment_state=embodiment.to_state(),
        source_state_version=tick,
        habitat_state_version=tick,
        attention=attention if attention is not None else AttentionView(None, None),
        last_outcome=last_outcome,
        developmental_markers=developmental_markers or {},
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
