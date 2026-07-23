"""PresentationState — derived, body-neutral nonverbal presentation (design §2).

Never authoritative, never snapshotted, never mood/emotion/personality bearing,
and never wall-clock stamped (transitions are keyed by organism tick /
`source_state_version`, not `time.time()`). ExpressionEngine is the only
writer; everything else treats it as a read-only render input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

# Postures are purely descriptive presentation labels — never a command, mood,
# or emotion. Ordering matches design §2.
POSTURES = frozenset(
    {
        "NEUTRAL",
        "ACTIVE",
        "OBSERVING",
        "RESTING",
        "RECOVERING",
        "WITHDRAWN",
        "INTERACTING",
        "INTERRUPTED",
    }
)

# Presentation-only action-phase labels. UNAVAILABLE is reserved for DETACHED.
ACTION_PHASES = frozenset({"UNAVAILABLE", "IDLE", "EXECUTED", "INTERRUPTED"})

RESULT_ACTIVITY_STATES = frozenset({"IDLE", "ACTIVE", "RESTING", "RECOVERING"})


@dataclass(frozen=True)
class PresentationState:
    """Fields per design §2. Deliberately excludes any mood/emotion/personality
    field and any wall-clock field — see `test_no_mood_or_emotion_authority_fields`.

    Frozen (Task 11, Gate 8/C7): `ExpressionEngine` always constructs a brand
    new instance per tick rather than mutating an existing one, and the same
    object a renderer reads back out of the frame ring is also the engine's
    own `_last_presentation` bookkeeping reference — without freezing, a
    renderer that merely assigns a field it read (e.g. `posture = "HACKED"`)
    would silently corrupt the organism's own next-tick transition state.
    Freezing closes that ordinary-assignment vector (see
    `experiments/d008/hostile_renderer.py`)."""

    body_instance_id: str | None
    body_profile_id: str | None
    attachment_status: str

    position: tuple[float, float] | None
    orientation: float | None
    locomotion_state: str | None
    posture: str | None  # null when DETACHED; else one of POSTURES

    attention_target: str | None
    attention_confidence: float | None

    active_capability: str | None  # null when DETACHED
    action_phase: str  # UNAVAILABLE when DETACHED
    interaction_target: str | None
    rest_activity_state: str | None

    visible_condition_channels: Mapping[str, float]
    developmental_markers: Mapping[str, Any]
    nonverbal_signal: str | None  # null when DETACHED

    previous_posture: str | None
    target_posture: str | None
    transition_kind: str
    transition_started_tick: int | None
    transition_source_state_version: int | None
    transition_duration_ticks_hint: int | None

    source_event_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        # Gate 8/C7 (Task 11): freeze both nested mappings to a defensive
        # copy wrapped in `MappingProxyType` so no caller — including a
        # renderer holding this same frozen instance — can silently mutate
        # a channel/marker in place; only top-level reassignment was blocked
        # by `frozen=True`, not in-place dict mutation.
        object.__setattr__(
            self,
            "visible_condition_channels",
            MappingProxyType(dict(self.visible_condition_channels)),
        )
        object.__setattr__(
            self,
            "developmental_markers",
            MappingProxyType(dict(self.developmental_markers)),
        )
