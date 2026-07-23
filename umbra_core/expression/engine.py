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

_EXPRESSION_DIAGNOSTIC_ONLY_CONDITIONS = frozenset({"C1", "C2", "C3", "C7", "C8"})


class ExpressionConfigError(Exception):
    """Raised when a diagnostic-only condition (C1/C2/C3/C7/C8 — isolated
    under `experiments/d008/`) is asked for a production `ExpressionConfig`."""


@dataclass
class ExpressionConfig:
    """Ablation switches for D-008 conditions C4/C5/C6 (see
    `condition_to_expression_config`). C1/C2/C3/C7/C8 never build this —
    they are isolated experiments-only diagnostic controllers/test doubles
    (`experiments/d008/diagnostic_controllers.py`,
    `experiments/d008/hostile_renderer.py`). C9 (frames temporally shuffled)
    and C10 (expression fully disabled) need no engine-level switch: C9 is
    harness-level frame reordering applied to already-derived frames, and
    C10 is enforced by `Organism._expression_active()` before the engine is
    ever called (same pattern as D-007's C9 shuffle / C2-C3 guard)."""

    ignore_actions: bool = False  # C4 — actions execute; presentation ignores them
    ignore_individuality: bool = False  # C5 — presentation ignores learned individuality
    ignore_physiology: bool = False  # C6 — presentation ignores physiology


def condition_to_expression_config(condition: str) -> ExpressionConfig:
    """Map an ablation condition label to a production `ExpressionConfig`.
    Raises for C1/C2/C3/C7/C8 — those must never share this production
    schema (mirrors `condition_to_individuality_config`'s C2/C3 guard)."""
    if condition in _EXPRESSION_DIAGNOSTIC_ONLY_CONDITIONS:
        raise ExpressionConfigError(
            f"{condition}_is_experiments_only_diagnostic_not_production_schema"
        )
    cfg = ExpressionConfig()
    if condition == "C4":
        cfg.ignore_actions = True
    elif condition == "C5":
        cfg.ignore_individuality = True
    elif condition == "C6":
        cfg.ignore_physiology = True
    return cfg

# Bounded, non-authoritative nudges only (Task 10). `individuality_summary` is
# a read-only bag the caller may populate from D-007 `IndividualityEngine.
# disposition_vector()` plus D-005/D-006 learned-pattern flags; ExpressionEngine
# never reaches into those engines itself and never lets these nudges swing a
# channel outside [0, 1] or change which capability/posture is depicted —
# individuality shades existing physiology-driven channels, it does not author
# a personality of its own (see `test_renderer_does_not_create_authored_personality`).
INDIVIDUALITY_CHANNEL_BIAS_MAX = 0.15
HABIT_ROUTINE_CHANNEL_BIAS = 0.10

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
    physiology: dict[str, float],
    attention_confidence: float | None,
    individuality_summary: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Pure function of already-read physiology/attention/individuality-summary
    — never mutates any of them. Nine channels named in design §2; physiology
    remains the dominant signal, with individuality/habit/routine contributing
    only small, bounded (`INDIVIDUALITY_CHANNEL_BIAS_MAX` /
    `HABIT_ROUTINE_CHANNEL_BIAS`) history-shaped nudges — deliberately no
    mood/emotion channel."""
    energy = clamp(float(physiology.get("energy", 0.0)))
    fatigue = clamp(float(physiology.get("fatigue", 0.0)))
    integrity = clamp(float(physiology.get("integrity", 0.0)))
    stimulation = clamp(float(physiology.get("stimulation", 0.0)))
    attention = clamp(attention_confidence) if attention_confidence is not None else 0.0

    summary = individuality_summary or {}
    disposition = summary.get("disposition_vector") or {}
    persistence_bias = INDIVIDUALITY_CHANNEL_BIAS_MAX * float(
        disposition.get("persistence_after_failure", 0.0)
    )
    recovery_bias = INDIVIDUALITY_CHANNEL_BIAS_MAX * float(disposition.get("recovery_pacing", 0.0))
    activity_bias = INDIVIDUALITY_CHANNEL_BIAS_MAX * float(
        disposition.get("stimulation_tolerance", 0.0)
    )
    habit_bias = HABIT_ROUTINE_CHANNEL_BIAS if summary.get("habit_active") else 0.0
    routine_bias = HABIT_ROUTINE_CHANNEL_BIAS if summary.get("routine_active") else 0.0

    return {
        "speed": clamp(1.0 - 0.7 * fatigue - 0.3 * (1.0 - energy)),
        "persistence": clamp(energy + persistence_bias),
        "compression": fatigue,
        "rest_frequency": clamp(fatigue - recovery_bias),
        "orientation_stability": integrity,
        "transition_speed": clamp(1.0 - fatigue + habit_bias),
        "maintenance_condition": integrity,
        "activity_intensity": clamp(stimulation + activity_bias),
        "attentional_persistence": clamp(attention + routine_bias),
    }


class ExpressionEngine:
    """Derives `RenderPacket` from `ExpressionView`. Has no `execute`,
    `select_action`, or any method taking `Governance`/`Embodiment` — it
    cannot select actions or write core state (see
    `test_expression_engine_cannot_select_actions`)."""

    def __init__(self, config: ExpressionConfig | None = None) -> None:
        self.config = config or ExpressionConfig()
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

    def _effective_physiology(self, view: ExpressionView) -> dict[str, float]:
        """C6 (design §4) — presentation ignores physiology: channels fall
        back to an empty reading (all-neutral defaults inside
        `_visible_condition_channels`) instead of the organism's actual
        energy/fatigue/integrity/stimulation."""
        return {} if self.config.ignore_physiology else view.physiology

    def _effective_individuality_summary(self, view: ExpressionView) -> dict[str, Any]:
        """C5 (design §4) — presentation ignores learned individuality."""
        return {} if self.config.ignore_individuality else view.individuality_summary

    def _derive_presentation(self, view: ExpressionView) -> PresentationState:
        prior = self._last_presentation
        prior_posture = prior.posture if prior is not None else None
        physiology = self._effective_physiology(view)
        individuality_summary = self._effective_individuality_summary(view)

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
                    physiology, view.attention.confidence, individuality_summary
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

        # C4 (design §4) — actions execute (Embodiment/Governance are
        # untouched by this flag), but presentation is forced through the
        # same "nothing happened" branch as a real no-outcome tick, so
        # visible posture/active_capability never reflects what the
        # organism actually did.
        outcome = None if self.config.ignore_actions else view.last_outcome
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
                physiology, view.attention.confidence, individuality_summary
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
