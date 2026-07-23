"""HeadlessRenderer — the science/CI `ReferenceRenderer` (Task 9's
`TkinterRenderer` is the visible companion). Never touches `FrameRing`
itself (Gate 8): a caller polls the ring with its own `RendererCursor` and
passes this renderer only the resulting `FrameRingEntry` via `render()`.
"""

from __future__ import annotations

from umbra_core.expression.frame_ring import FrameRingEntry


class HeadlessRenderer:
    """No window, no canvas, no cosmetic motion — just the render packet."""

    def __init__(self, renderer_id: str = "headless") -> None:
        self.renderer_id = renderer_id
        self.diagnostics_visible = False
        self.last_rendered: FrameRingEntry | None = None
        self.render_count = 0
        self.last_render_error: BaseException | None = None

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
        ExpressionEngine resource — only its own bookkeeping fields."""
        return None
