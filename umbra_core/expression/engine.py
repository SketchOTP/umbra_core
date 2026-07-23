"""ExpressionEngine — derives a coherent, body-neutral `RenderPacket` from a
read-only `ExpressionView` every tick, including no-action ticks.

Ownership (design §1 table): the engine derives semantic presentation,
transition intent, source refs, and condition channels. It cannot select
actions, cannot write core state (physiology/memory/identity/relationships),
and does not own canvas interpolation (that is the renderer's job, Task 9).
`ExpressionView` therefore carries no mutator methods and no reference to
`Governance`/`Embodiment`/`Physiology` objects that could be written through —
only plain, already-read data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from umbra_core.expression.habitat_read_model import HabitatReadModel
from umbra_core.expression.presentation_state import PresentationState
from umbra_core.util import clamp

_THRESHOLDS_PATH = Path(__file__).resolve().parents[2] / "experiments" / "d008" / "thresholds.json"


def _load_thresholds() -> dict[str, Any]:
    return json.loads(_THRESHOLDS_PATH.read_text())


_THRESHOLDS = _load_thresholds()
ATTENTION_CONFIDENCE_DISPLAY_THRESHOLD = float(
    _THRESHOLDS["attention_confidence_display_threshold"]
)
HABITAT_READ_MODEL_MAX_ENTITIES = int(_THRESHOLDS["habitat_read_model_max_entities"])
SOURCE_EVENT_REFS_MAX = int(_THRESHOLDS["source_event_refs_max"])
DEFAULT_TRANSITION_DURATION_TICKS_HINT = 4

SIGNAL_CAPABILITIES = frozenset({"SIGNAL_PLAY", "SIGNAL_ASSISTANCE"})

# Capability -> (posture, locomotion_state, rest_activity_state) for a
# successfully executed (verified, admitted) outcome. Never invents a
# capability the organism did not actually run.
_CAPABILITY_PRESENTATION: dict[str, tuple[str, str, str]] = {
    "IDLE": ("NEUTRAL", "STATIONARY", "IDLE"),
    "ORIENT": ("ACTIVE", "TURNING", "ACTIVE"),
    "MOVE": ("ACTIVE", "MOVING", "ACTIVE"),
    "APPROACH": ("ACTIVE", "MOVING", "ACTIVE"),
    "RETREAT": ("ACTIVE", "MOVING", "ACTIVE"),
    "INSPECT": ("OBSERVING", "STATIONARY", "ACTIVE"),
    "REST": ("RESTING", "STATIONARY", "RESTING"),
    "CHARGE": ("RECOVERING", "STATIONARY", "RECOVERING"),
    "SIGNAL_PLAY": ("INTERACTING", "STATIONARY", "ACTIVE"),
    "SIGNAL_ASSISTANCE": ("INTERACTING", "STATIONARY", "ACTIVE"),
}


@dataclass(frozen=True)
class LastOutcomeView:
    """A read-only summary of the last governance-verified outcome this tick,
    or `None` on the `ExpressionView` when no proposal reached verification
    (e.g. governance denied the proposal at admission — never executed)."""

    capability: str
    admitted: bool = True  # False = governance denied before any execution
    success: bool | None = None
    reason: str | None = None
    failure_code: str | None = None
    execution_id: str | None = None
    target: str | None = None


@dataclass(frozen=True)
class AttentionView:
    target: str | None
    confidence: float | None


@dataclass(frozen=True)
class AttachmentView:
    attachment_status: str  # ATTACHED | DETACHED
    body_instance_id: str | None
    body_profile_id: str | None
    attachment_generation: int


@dataclass(frozen=True)
class ExpressionView:
    """Read-only bundle handed to `ExpressionEngine.derive`. No mutator
    methods and no live references to organism subsystems — every field is
    already-extracted data, so the engine has no path to write back."""

    tick: int
    physiology: dict[str, float]
    attachment: AttachmentView
    embodiment_state: dict[str, Any]
    source_state_version: int
    habitat_state_version: int
    attention: AttentionView = field(default_factory=lambda: AttentionView(None, None))
    last_outcome: LastOutcomeView | None = None
    individuality_summary: dict[str, Any] = field(default_factory=dict)
    developmental_markers: dict[str, Any] = field(default_factory=dict)
    source_event_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class RenderPacket:
    presentation_state: PresentationState
    habitat_read_model: HabitatReadModel
    source_state_version: int
    habitat_state_version: int
    body_attachment_generation: int


def _visible_condition_channels(
    physiology: dict[str, float], attention_confidence: float | None
) -> dict[str, float]:
    """Pure function of already-read physiology/attention — never mutates
    either. Nine channels named in design §2; deliberately no mood/emotion
    channel (fatigue/energy/integrity/stimulation only)."""
    energy = clamp(float(physiology.get("energy", 0.0)))
    fatigue = clamp(float(physiology.get("fatigue", 0.0)))
    integrity = clamp(float(physiology.get("integrity", 0.0)))
    stimulation = clamp(float(physiology.get("stimulation", 0.0)))
    return {
        "speed": clamp(1.0 - 0.7 * fatigue - 0.3 * (1.0 - energy)),
        "persistence": energy,
        "compression": fatigue,
        "rest_frequency": fatigue,
        "orientation_stability": integrity,
        "transition_speed": clamp(1.0 - fatigue),
        "maintenance_condition": integrity,
        "activity_intensity": stimulation,
        "attentional_persistence": clamp(attention_confidence) if attention_confidence is not None else 0.0,
    }


class ExpressionEngine:
    """Derives `RenderPacket` from `ExpressionView`. Has no `execute`,
    `select_action`, or any method taking `Governance`/`Embodiment` — it
    cannot select actions or write core state (see
    `test_expression_engine_cannot_select_actions`)."""

    def __init__(self) -> None:
        self._last_presentation: PresentationState | None = None

    def derive(self, view: ExpressionView) -> RenderPacket:
        presentation = self._derive_presentation(view)
        self._last_presentation = presentation
        habitat_read_model = HabitatReadModel.from_embodiment_state(
            view.embodiment_state,
            version=view.habitat_state_version,
            max_entities=HABITAT_READ_MODEL_MAX_ENTITIES,
        )
        return RenderPacket(
            presentation_state=presentation,
            habitat_read_model=habitat_read_model,
            source_state_version=view.source_state_version,
            habitat_state_version=view.habitat_state_version,
            body_attachment_generation=view.attachment.attachment_generation,
        )

    def _derive_presentation(self, view: ExpressionView) -> PresentationState:
        prior = self._last_presentation
        prior_posture = prior.posture if prior is not None else None

        if view.attachment.attachment_status != "ATTACHED":
            return PresentationState(
                body_instance_id=view.attachment.body_instance_id,
                body_profile_id=None,
                attachment_status="DETACHED",
                position=None,
                orientation=None,
                locomotion_state=None,
                posture=None,
                attention_target=self._displayed_attention_target(view.attention),
                attention_confidence=view.attention.confidence,
                active_capability=None,
                action_phase="UNAVAILABLE",
                interaction_target=None,
                rest_activity_state=None,
                visible_condition_channels=_visible_condition_channels(
                    view.physiology, view.attention.confidence
                ),
                developmental_markers=dict(view.developmental_markers),
                nonverbal_signal=None,
                previous_posture=prior_posture,
                target_posture=None,
                transition_kind="DETACHED",
                transition_started_tick=None,
                transition_source_state_version=None,
                transition_duration_ticks_hint=None,
                source_event_refs=tuple(view.source_event_refs[:SOURCE_EVENT_REFS_MAX]),
            )

        body = (view.embodiment_state.get("body") or {}) if view.embodiment_state else {}
        position = (
            (float(body["x"]), float(body["y"])) if "x" in body and "y" in body else None
        )
        orientation = float(body["heading"]) if "heading" in body else None

        active_capability: str | None
        action_phase: str
        posture: str
        locomotion_state: str
        rest_activity_state: str
        interaction_target: str | None
        nonverbal_signal: str | None

        outcome = view.last_outcome
        if outcome is None or not outcome.admitted:
            # No verified execution happened this tick (including a governed
            # denial) — never rendered as if something executed.
            active_capability = None
            action_phase = "IDLE"
            posture = prior_posture or "NEUTRAL"
            locomotion_state = "STATIONARY"
            rest_activity_state = "IDLE"
            interaction_target = None
            nonverbal_signal = None
        elif outcome.success:
            posture, locomotion_state, rest_activity_state = _CAPABILITY_PRESENTATION.get(
                outcome.capability, ("ACTIVE", "STATIONARY", "ACTIVE")
            )
            active_capability = outcome.capability
            action_phase = "EXECUTED"
            interaction_target = outcome.target
            nonverbal_signal = outcome.capability if outcome.capability in SIGNAL_CAPABILITIES else None
        else:
            # Admitted and executed but verified as failed (adapter rejection,
            # movement slip, etc.) — visibly an interruption, not a success.
            active_capability = outcome.capability
            action_phase = "INTERRUPTED"
            posture = "INTERRUPTED"
            locomotion_state = "STATIONARY"
            rest_activity_state = "ACTIVE"
            interaction_target = outcome.target
            nonverbal_signal = None

        if posture == prior_posture or prior_posture is None:
            transition_kind = "STEADY"
            transition_started_tick = (
                prior.transition_started_tick if prior is not None else view.tick
            )
            transition_source_state_version = (
                prior.transition_source_state_version
                if prior is not None
                else view.source_state_version
            )
        else:
            transition_kind = "POSTURE_CHANGE"
            transition_started_tick = view.tick
            transition_source_state_version = view.source_state_version

        return PresentationState(
            body_instance_id=view.attachment.body_instance_id,
            body_profile_id=view.attachment.body_profile_id,
            attachment_status="ATTACHED",
            position=position,
            orientation=orientation,
            locomotion_state=locomotion_state,
            posture=posture,
            attention_target=self._displayed_attention_target(view.attention),
            attention_confidence=view.attention.confidence,
            active_capability=active_capability,
            action_phase=action_phase,
            interaction_target=interaction_target,
            rest_activity_state=rest_activity_state,
            visible_condition_channels=_visible_condition_channels(
                view.physiology, view.attention.confidence
            ),
            developmental_markers=dict(view.developmental_markers),
            nonverbal_signal=nonverbal_signal,
            previous_posture=prior_posture,
            target_posture=posture,
            transition_kind=transition_kind,
            transition_started_tick=transition_started_tick,
            transition_source_state_version=transition_source_state_version,
            transition_duration_ticks_hint=DEFAULT_TRANSITION_DURATION_TICKS_HINT,
            source_event_refs=tuple(view.source_event_refs[:SOURCE_EVENT_REFS_MAX]),
        )

    @staticmethod
    def _displayed_attention_target(attention: AttentionView) -> str | None:
        """Below the frozen display-confidence threshold, the target stays
        ambiguous — never named — even though the raw confidence value is
        still passed through for diagnostics."""
        if attention.confidence is None or attention.confidence < ATTENTION_CONFIDENCE_DISPLAY_THRESHOLD:
            return None
        return attention.target
