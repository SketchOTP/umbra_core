"""Habitat canvas rendering — shapes, orientation, posture, attention, and
nonverbal icons only (design §3: "Habitat canvas: geometry, orientation,
posture, attention markers (only above frozen confidence), nonverbal icons,
environment. Not a status dashboard."). Capability, phase, versions, source
refs, and condition channels are `diagnostics.py`'s job, never this
module's — see `tests/test_d008.py::test_habitat_canvas_excludes_capability_phase_version_diagnostics`.

D-009: held-object overlays render only when `held_attachment_generation`
matches `packet.body_attachment_generation`. Positions come solely from the
frozen `HabitatReadModel` in the packet — never invented or interpolated.

Draws onto any canvas-like object exposing the small `tkinter.Canvas`
drawing subset used below (`delete`, `create_oval`, `create_line`,
`create_text`). This module never imports `tkinter` itself, so it stays
fully unit-testable with a fake canvas double and never needs a real
display. Reads only `RenderPacket` fields (never live organism/embodiment
state) and calls no organism/embodiment/adapter method — it has no channel
to write core state.
"""

from __future__ import annotations

import math
from typing import Any, Protocol

from umbra_core.expression.engine import RenderPacket
from umbra_core.expression.habitat_read_model import FrozenEntity

# World-unit -> canvas-pixel projection. Matches the default habitat's
# roughly 0-20 unit extent (`Embodiment.Habitat.default`) onto
# `tkinter_renderer.HABITAT_CANVAS_SIZE`, with world y increasing upward.
PIXELS_PER_UNIT = 18.0
CANVAS_ORIGIN = (40.0, 440.0)

BODY_RADIUS_PX = 14.0
ORIENTATION_LENGTH_PX = 22.0
ATTENTION_MARKER_RADIUS_PX = 20.0
HELD_OVERLAY_OFFSET_PX = 18.0

_ENTITY_COLORS = {
    "rest": "#3a7bd5",
    "resource": "#4caf50",
    "hazard": "#e53935",
    "inspect": "#8e24aa",
    "partner": "#ffb300",
    "portable": "#ff9800",
}
_DEFAULT_ENTITY_COLOR = "#607d8b"
_HELD_OVERLAY_OUTLINE = "#ffb74d"

_POSTURE_COLORS = {
    "NEUTRAL": "#90a4ae",
    "ACTIVE": "#26a69a",
    "OBSERVING": "#5c6bc0",
    "RESTING": "#8d6e63",
    "RECOVERING": "#7e57c2",
    "WITHDRAWN": "#546e7a",
    "INTERACTING": "#ffb300",
    "INTERRUPTED": "#ef5350",
}
_DEFAULT_POSTURE_COLOR = "#cfd8dc"

_NONVERBAL_ICONS = {
    "SIGNAL_PLAY": "\u2726",  # spark
    "SIGNAL_ASSISTANCE": "\u25ce",  # beacon
}
_DEFAULT_ICON = "\u2022"


class CanvasLike(Protocol):
    def delete(self, tag: str) -> None: ...
    def create_oval(self, *args: Any, **kwargs: Any) -> Any: ...
    def create_line(self, *args: Any, **kwargs: Any) -> Any: ...
    def create_text(self, *args: Any, **kwargs: Any) -> Any: ...


def _to_canvas_xy(x: float, y: float) -> tuple[float, float]:
    ox, oy = CANVAS_ORIGIN
    return ox + x * PIXELS_PER_UNIT, oy - y * PIXELS_PER_UNIT


def _entity_visible(packet: RenderPacket, entity: FrozenEntity) -> bool:
    if entity.held_attachment_generation is not None:
        return entity.held_attachment_generation == packet.body_attachment_generation
    return True


def render_habitat(canvas: CanvasLike, packet: RenderPacket) -> None:
    """Redraws the full habitat frame from `packet` only — habitat comes
    from `packet.habitat_read_model`, never re-projected from live world
    state at render time (design §3)."""
    canvas.delete("all")
    _draw_entities(canvas, packet)
    _draw_body(canvas, packet)


def _draw_entities(canvas: CanvasLike, packet: RenderPacket) -> None:
    for entity in packet.habitat_read_model.entities:
        if not _entity_visible(packet, entity):
            continue
        cx, cy = _to_canvas_xy(entity.x, entity.y)
        if entity.held_attachment_generation is not None:
            cx += HELD_OVERLAY_OFFSET_PX
            cy -= HELD_OVERLAY_OFFSET_PX * 0.5
        radius_px = max(entity.radius, 0.3) * PIXELS_PER_UNIT
        color = _ENTITY_COLORS.get(entity.kind, _DEFAULT_ENTITY_COLOR)
        outline = _HELD_OVERLAY_OUTLINE if entity.held_attachment_generation is not None else ""
        if not entity.occluded and outline == "":
            outline = "#000000"
        canvas.create_oval(
            cx - radius_px,
            cy - radius_px,
            cx + radius_px,
            cy + radius_px,
            fill=color,
            outline=outline,
            width=2 if entity.held_attachment_generation is not None else 1,
            tags=("entity", entity.kind, "held_overlay" if entity.held_attachment_generation else "free_entity"),
        )


def _draw_body(canvas: CanvasLike, packet: RenderPacket) -> None:
    ps = packet.presentation_state
    if ps.position is None:
        return  # DETACHED: no body layer; habitat above still rendered
    if ps.action_phase == "INTERRUPTED":
        # Failed execution — body shows interruption, never success motion/icon
        pass
    cx, cy = _to_canvas_xy(*ps.position)
    color = _POSTURE_COLORS.get(ps.posture or "", _DEFAULT_POSTURE_COLOR)
    canvas.create_oval(
        cx - BODY_RADIUS_PX,
        cy - BODY_RADIUS_PX,
        cx + BODY_RADIUS_PX,
        cy + BODY_RADIUS_PX,
        fill=color,
        outline="#000000",
        tags=("body",),
    )
    if ps.orientation is not None:
        angle = math.radians(ps.orientation)
        end_x = cx + ORIENTATION_LENGTH_PX * math.sin(angle)
        end_y = cy - ORIENTATION_LENGTH_PX * math.cos(angle)
        canvas.create_line(cx, cy, end_x, end_y, fill="#000000", width=2, tags=("orientation",))
    if ps.attention_target is not None:
        r = ATTENTION_MARKER_RADIUS_PX
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#ffee58", width=2, tags=("attention",))
    if ps.nonverbal_signal is not None and ps.action_phase == "EXECUTED":
        icon = _NONVERBAL_ICONS.get(ps.nonverbal_signal, _DEFAULT_ICON)
        canvas.create_text(
            cx, cy - BODY_RADIUS_PX - 10, text=icon, fill="#ffee58", tags=("nonverbal_icon",)
        )
