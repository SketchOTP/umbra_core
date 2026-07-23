"""UMBRA-D-008 coherent embodiment profile tests."""

from __future__ import annotations

import json
from pathlib import Path

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
from umbra_core.governance import Governance
from umbra_core.persistence import Store
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
