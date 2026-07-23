"""D-008 embodiment adapters: body profiles + EmbodimentAdapter."""

from __future__ import annotations

from umbra_core.embodiment_adapters.adapter import (
    ADAPTER_FAILURE_CODES,
    AdapterError,
    AdapterRequest,
    AttachmentState,
    EmbodimentAdapter,
)
from umbra_core.embodiment_adapters.profiles import (
    ABSTRACT_SHAPE_BODY,
    MINIMAL_CREATURE_BODY,
    BodyProfile,
    get_profile,
    profile_definition_hash,
)

__all__ = [
    "ABSTRACT_SHAPE_BODY",
    "MINIMAL_CREATURE_BODY",
    "BodyProfile",
    "get_profile",
    "profile_definition_hash",
    "ADAPTER_FAILURE_CODES",
    "AdapterError",
    "AdapterRequest",
    "AttachmentState",
    "EmbodimentAdapter",
]
