"""Constrained D-008 body profile for negative adapter tests."""

from __future__ import annotations

from umbra_core.embodiment_adapters import BodyProfile
from umbra_core.embodiment_adapters.profiles import (
    ABSTRACT_SHAPE_BODY,
    BODY_PROFILE_SCHEMA_VERSION,
)

CONSTRAINED_TEST_BODY = BodyProfile(
    profile_id="CONSTRAINED_TEST_BODY",
    schema_version=BODY_PROFILE_SCHEMA_VERSION,
    supported_capabilities=frozenset(
        cap
        for cap in ABSTRACT_SHAPE_BODY.supported_capabilities
        if cap != "SIGNAL_ASSISTANCE"
    ),
    physical_limits={
        "max_step": 0.4,
        "turn_rate": 60.0,
        "attention_radius": 4.0,
    },
    presentation_mapping={
        "geometry": "constrained_shape",
        "posture_map": {
            "active": "compact",
            "rest": "low",
            "charge": "docked",
        },
    },
)
