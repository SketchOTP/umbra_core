"""UMBRA-D-008 coherent embodiment profile tests."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.d008.constrained_profile import CONSTRAINED_TEST_BODY
from umbra_core.embodiment_adapters import (
    ABSTRACT_SHAPE_BODY,
    MINIMAL_CREATURE_BODY,
    BodyProfile,
    get_profile,
    profile_definition_hash,
)

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
