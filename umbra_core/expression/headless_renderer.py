"""HeadlessRenderer — the science/CI `ReferenceRenderer` (Task 9's
`TkinterRenderer` is the visible companion). Polls a `FrameRing`
non-destructively through its own `RendererCursor`: a poll with no new valid
frame returns `None` and renders nothing, so this renderer can never fake
continued autonomy when the organism produced no new frame.
"""

from __future__ import annotations

from umbra_core.expression.frame_ring import FrameRing, FrameRingEntry, RendererCursor


class HeadlessRenderer:
    """No window, no canvas, no cosmetic motion — just the render packet."""

    def __init__(self, renderer_id: str = "headless") -> None:
        self._cursor = RendererCursor(renderer_id=renderer_id)
        self.diagnostics_visible = False
        self.last_rendered: FrameRingEntry | None = None
        self.render_count = 0
        self.last_render_error: BaseException | None = None

    def read_latest(self, ring: FrameRing) -> FrameRingEntry | None:
        return ring.read_latest(self._cursor)

    def render(self, entry: FrameRingEntry) -> None:
        """Contains failures locally (design §3) — never propagates into a
        caller loop that also drives the organism."""
        try:
            self.last_rendered = entry
            self.render_count += 1
            self.last_render_error = None
        except Exception as exc:  # pragma: no cover - defensive containment
            self.last_render_error = exc

    def set_diagnostics_visible(self, visible: bool) -> None:
        self.diagnostics_visible = bool(visible)

    def close(self) -> None:
        """No-op for core: this renderer owns no organism, adapter, or
        ExpressionEngine resource — only its own cursor/local state."""
        return None
