"""Body profiles for D-008 embodiment adapters."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from umbra_core.embodiment import CAPABILITIES

BODY_PROFILE_SCHEMA_VERSION = "d008.body-profile.v1"


@dataclass(frozen=True)
class BodyProfile:
    profile_id: str
    schema_version: str
    supported_capabilities: frozenset[str]
    physical_limits: dict[str, float]
    presentation_mapping: dict[str, Any]


def _canonical_value(value: Any) -> Any:
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, tuple):
        return [_canonical_value(item) for item in value]
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical_value(value[key]) for key in sorted(value)}
    return value


def profile_definition_hash(profile: BodyProfile) -> str:
    """SHA-256 of profile definition JSON with sorted keys and stable set order."""
    payload = json.dumps(
        _canonical_value(asdict(profile)),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


FULL_CAPABILITY_SET = frozenset(CAPABILITIES)

ABSTRACT_SHAPE_BODY = BodyProfile(
    profile_id="ABSTRACT_SHAPE_BODY",
    schema_version=BODY_PROFILE_SCHEMA_VERSION,
    supported_capabilities=FULL_CAPABILITY_SET,
    physical_limits={
        "max_step": 1.0,
        "turn_rate": 90.0,
        "attention_radius": 6.0,
    },
    presentation_mapping={
        "geometry": "abstract_shape",
        "posture_map": {
            "active": "upright",
            "rest": "low",
            "charge": "docked",
        },
        "signal_icons": {
            "SIGNAL_PLAY": "spark",
            "SIGNAL_ASSISTANCE": "beacon",
        },
    },
)

MINIMAL_CREATURE_BODY = BodyProfile(
    profile_id="MINIMAL_CREATURE_BODY",
    schema_version=BODY_PROFILE_SCHEMA_VERSION,
    supported_capabilities=FULL_CAPABILITY_SET,
    physical_limits={
        "max_step": 0.8,
        "turn_rate": 75.0,
        "attention_radius": 5.0,
    },
    presentation_mapping={
        "geometry": "minimal_creature",
        "posture_map": {
            "active": "standing",
            "rest": "curled",
            "charge": "nesting",
        },
        "signal_icons": {
            "SIGNAL_PLAY": "tail_wag",
            "SIGNAL_ASSISTANCE": "alert_chirp",
        },
    },
)

_PROFILES = {
    ABSTRACT_SHAPE_BODY.profile_id: ABSTRACT_SHAPE_BODY,
    MINIMAL_CREATURE_BODY.profile_id: MINIMAL_CREATURE_BODY,
}


def get_profile(profile_id: str) -> BodyProfile:
    return _PROFILES[profile_id]
