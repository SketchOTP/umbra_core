"""Diagnostics overlay — capability, phase, versions, source refs, and
condition channels only (design §3). Optional and removable without
changing the inhabited-world canvas or organism behavior — see
`habitat_view.py`, which must never show this content instead.

Duck-typed against a canvas-like object exactly like `habitat_view`; imports
no `tkinter`, so it stays unit-testable without a real display.
"""

from __future__ import annotations

from typing import Any, Protocol

from umbra_core.expression.engine import RenderPacket

LINE_HEIGHT_PX = 16.0
LEFT_MARGIN_PX = 8.0
TOP_MARGIN_PX = 8.0


class CanvasLike(Protocol):
    def delete(self, tag: str) -> None: ...
    def create_text(self, *args: Any, **kwargs: Any) -> Any: ...


def render_diagnostics(canvas: CanvasLike, packet: RenderPacket) -> None:
    canvas.delete("all")
    for i, line in enumerate(_diagnostic_lines(packet)):
        canvas.create_text(
            LEFT_MARGIN_PX,
            TOP_MARGIN_PX + i * LINE_HEIGHT_PX,
            text=line,
            anchor="nw",
            fill="#000000",
            tags=("diagnostic_line",),
        )


def _diagnostic_lines(packet: RenderPacket) -> list[str]:
    ps = packet.presentation_state
    channels = ", ".join(f"{k}={v:.2f}" for k, v in sorted(ps.visible_condition_channels.items()))
    return [
        f"capability={ps.active_capability}  phase={ps.action_phase}",
        f"posture={ps.posture}  transition={ps.transition_kind}",
        f"source_state_version={packet.source_state_version}  "
        f"habitat_state_version={packet.habitat_state_version}",
        f"body_attachment_generation={packet.body_attachment_generation}",
        f"attention_target={ps.attention_target}  attention_confidence={ps.attention_confidence}",
        f"source_event_refs={len(ps.source_event_refs)}",
        f"channels: {channels}",
    ]
