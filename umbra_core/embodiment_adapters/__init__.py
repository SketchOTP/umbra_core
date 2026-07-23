"""D-008 embodiment adapters: body profiles + EmbodimentAdapter."""

from __future__ import annotations

from umbra_core.embodiment_adapters.adapter import (
    ADAPTER_FAILURE_CODES,
    ATTACHMENT_EVENT_TYPES,
    AdapterError,
    AdapterRequest,
    AttachmentState,
    EmbodimentAdapter,
    attachment_state_from_event,
)
from umbra_core.embodiment_adapters.profiles import (
    ABSTRACT_SHAPE_BODY,
    MINIMAL_CREATURE_BODY,
    BodyProfile,
    default_migration_profile_id,
    get_profile,
    profile_definition_hash,
)

__all__ = [
    "ABSTRACT_SHAPE_BODY",
    "MINIMAL_CREATURE_BODY",
    "BodyProfile",
    "get_profile",
    "profile_definition_hash",
    "default_migration_profile_id",
    "ADAPTER_FAILURE_CODES",
    "ATTACHMENT_EVENT_TYPES",
    "AdapterError",
    "AdapterRequest",
    "AttachmentState",
    "EmbodimentAdapter",
    "attachment_state_from_event",
]
