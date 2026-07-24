"""D-008 embodiment adapters: body profiles + EmbodimentAdapter."""

from __future__ import annotations

from umbra_core.embodiment_adapters.adapter import (
    ADAPTER_FAILURE_CODES,
    ATTACHMENT_EVENT_TYPES,
    AdapterError,
    AdapterRequest,
    AttachmentState,
    EmbodimentAdapter,
    ManipulationValidationError,
    ProfileMigrationError,
    attachment_state_from_event,
)
from umbra_core.embodiment_adapters.profiles import (
    ABSTRACT_SHAPE_BODY,
    ABSTRACT_SHAPE_BODY_D009,
    MINIMAL_CREATURE_BODY,
    MINIMAL_CREATURE_BODY_D009,
    BodyProfile,
    default_migration_profile_id,
    get_d008_profile,
    get_profile,
    hold_anchor,
    hold_slot_count,
    is_d008_profile_hash,
    is_d009_profile_hash,
    maximum_held_mass_class,
    profile_definition_hash,
)

__all__ = [
    "ABSTRACT_SHAPE_BODY",
    "ABSTRACT_SHAPE_BODY_D009",
    "MINIMAL_CREATURE_BODY",
    "MINIMAL_CREATURE_BODY_D009",
    "BodyProfile",
    "get_profile",
    "get_d008_profile",
    "profile_definition_hash",
    "default_migration_profile_id",
    "hold_slot_count",
    "hold_anchor",
    "maximum_held_mass_class",
    "is_d008_profile_hash",
    "is_d009_profile_hash",
    "ADAPTER_FAILURE_CODES",
    "ATTACHMENT_EVENT_TYPES",
    "AdapterError",
    "AdapterRequest",
    "AttachmentState",
    "EmbodimentAdapter",
    "ManipulationValidationError",
    "ProfileMigrationError",
    "attachment_state_from_event",
]
