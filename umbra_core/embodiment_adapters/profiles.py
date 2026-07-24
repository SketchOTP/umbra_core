"""Body profiles for D-008 embodiment adapters and D-009 MANIPULATE extensions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from umbra_core.embodiment import CAPABILITIES

_THRESHOLDS_PATH = Path(__file__).resolve().parents[2] / "experiments" / "d008" / "thresholds.json"

BODY_PROFILE_SCHEMA_VERSION_D008 = "d008.body-profile.v1"
BODY_PROFILE_SCHEMA_VERSION = "d009.body-profile.v1"

MASS_CLASS_ORDER = {"LIGHT": 0, "MEDIUM": 1, "HEAVY": 2}


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
D009_CAPABILITY_SET = frozenset((*CAPABILITIES, "MANIPULATE"))


def _default_manipulation_mapping() -> dict[str, Any]:
    return {
        "hold_slot_count": 1,
        "maximum_held_mass_class": "LIGHT",
        "hold_anchor": {"x": 0.4, "y": 0.2},
    }


def d009_profile_from_d008(profile: BodyProfile) -> BodyProfile:
    """Compatible D-009 profile version — same profile_id, MANIPULATE + hold fields."""
    presentation = dict(profile.presentation_mapping)
    presentation["manipulation"] = _default_manipulation_mapping()
    return BodyProfile(
        profile_id=profile.profile_id,
        schema_version=BODY_PROFILE_SCHEMA_VERSION,
        supported_capabilities=D009_CAPABILITY_SET,
        physical_limits=dict(profile.physical_limits),
        presentation_mapping=presentation,
    )


# Sealed D-008 production profiles — hashes frozen in experiments/d008/thresholds.json.
ABSTRACT_SHAPE_BODY = BodyProfile(
    profile_id="ABSTRACT_SHAPE_BODY",
    schema_version=BODY_PROFILE_SCHEMA_VERSION_D008,
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
    schema_version=BODY_PROFILE_SCHEMA_VERSION_D008,
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

ABSTRACT_SHAPE_BODY_D009 = d009_profile_from_d008(ABSTRACT_SHAPE_BODY)
MINIMAL_CREATURE_BODY_D009 = d009_profile_from_d008(MINIMAL_CREATURE_BODY)

_D008_PROFILES = {
    ABSTRACT_SHAPE_BODY.profile_id: ABSTRACT_SHAPE_BODY,
    MINIMAL_CREATURE_BODY.profile_id: MINIMAL_CREATURE_BODY,
}

_D009_PROFILES = {
    ABSTRACT_SHAPE_BODY.profile_id: ABSTRACT_SHAPE_BODY_D009,
    MINIMAL_CREATURE_BODY.profile_id: MINIMAL_CREATURE_BODY_D009,
}


def get_d008_profile(profile_id: str) -> BodyProfile:
    return _D008_PROFILES[profile_id]


def get_profile(profile_id: str) -> BodyProfile:
    return _D009_PROFILES[profile_id]


def is_d008_profile_hash(profile_id: str, digest: str) -> bool:
    return profile_definition_hash(get_d008_profile(profile_id)) == digest


def is_d009_profile_hash(profile_id: str, digest: str) -> bool:
    return profile_definition_hash(get_profile(profile_id)) == digest


def profile_manipulation_fields(profile: BodyProfile) -> dict[str, Any]:
    return dict(profile.presentation_mapping.get("manipulation") or {})


def hold_slot_count(profile: BodyProfile) -> int:
    return int(profile_manipulation_fields(profile).get("hold_slot_count", 0))


def maximum_held_mass_class(profile: BodyProfile) -> str | None:
    value = profile_manipulation_fields(profile).get("maximum_held_mass_class")
    return str(value) if value is not None else None


def hold_anchor(profile: BodyProfile) -> dict[str, float]:
    raw = profile_manipulation_fields(profile).get("hold_anchor") or {}
    return {"x": float(raw.get("x", 0.0)), "y": float(raw.get("y", 0.0))}


def mass_class_supported(object_mass: str, maximum_held: str) -> bool:
    return MASS_CLASS_ORDER.get(object_mass, 99) <= MASS_CLASS_ORDER.get(maximum_held, -1)


def default_migration_profile_id() -> str:
    """Frozen D-007→D-008 migration default from `experiments/d008/thresholds.json`."""
    return str(json.loads(_THRESHOLDS_PATH.read_text())["default_migration_profile_id"])
