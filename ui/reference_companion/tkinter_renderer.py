"""TkinterRenderer — the visible reference-companion `ReferenceRenderer`
(design §3), sitting over the same headless `FrameRing`/`RenderPacket`
presentation model as `umbra_core.expression.headless_renderer.HeadlessRenderer`.
It only ever renders `FrameRingEntry` objects a caller already read from the
organism's `FrameRing`; it holds no reference to the organism, adapter, or
`ExpressionEngine`, so it structurally cannot write core state.

Gate 8 follow-up: this renderer has no `FrameRing`/reader-typed parameter
anywhere (not even to poll on its own behalf, per §1 module note in
`umbra_core.expression.renderer`) — a driving harness owns the ring, owns a
`RendererCursor`, calls `FrameRing.read_latest(cursor)` itself, and passes
only the resulting entry to `render()`.

`tkinter` is imported lazily inside `__init__` — never at module import
time — so importing this module (e.g. for the import-isolation test, or for
`habitat_view`/`diagnostics` unit tests using a fake canvas double) never
requires a real Tk installation or display. Only constructing an instance
does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ui.reference_companion import diagnostics, habitat_view
from umbra_core.expression.frame_ring import FrameRingEntry

if TYPE_CHECKING:
    import tkinter as tk

HABITAT_CANVAS_SIZE = (480, 480)
DIAGNOSTICS_CANVAS_SIZE = (480, 160)


class TkinterRenderer:
    """`close()` destroys only the window resources this renderer created
    and leaves the organism, adapter, `ExpressionEngine`, and any other
    renderer (e.g. `HeadlessRenderer`) completely untouched and running.
    """

    def __init__(
        self,
        *,
        renderer_id: str = "tkinter",
        diagnostics_visible: bool = False,
        master: "tk.Misc | None" = None,
    ) -> None:
        import tkinter as tk  # local import: see module docstring

        self._tk = tk
        self._closed = False
        self.renderer_id = renderer_id

        self._owns_root = master is None
        self.root: Any = master if master is not None else tk.Tk()
        if self._owns_root:
            self.root.title("UMBRA Reference Companion")

        width, height = HABITAT_CANVAS_SIZE
        self.habitat_canvas = tk.Canvas(self.root, width=width, height=height, bg="#101418", highlightthickness=0)
        self.habitat_canvas.pack(side="top", fill="both", expand=True)

        diag_width, diag_height = DIAGNOSTICS_CANVAS_SIZE
        self.diagnostics_canvas = tk.Canvas(
            self.root, width=diag_width, height=diag_height, bg="#ffffff", highlightthickness=0
        )

        self.diagnostics_visible = False
        self.last_rendered: FrameRingEntry | None = None
        self.render_count = 0
        self.last_render_error: BaseException | None = None

        self.set_diagnostics_visible(diagnostics_visible)

    def render(self, entry: FrameRingEntry) -> None:
        """Contains failures locally (design §3) — a rendering exception
        never propagates into a caller loop that might also be driving the
        organism."""
        if self._closed:
            return
        try:
            habitat_view.render_habitat(self.habitat_canvas, entry.render_packet)
            if self.diagnostics_visible:
                diagnostics.render_diagnostics(self.diagnostics_canvas, entry.render_packet)
            self.last_rendered = entry
            self.render_count += 1
            self.last_render_error = None
        except Exception as exc:  # pragma: no cover - defensive containment
            self.last_render_error = exc

    def set_diagnostics_visible(self, visible: bool) -> None:
        self.diagnostics_visible = bool(visible)
        if self._closed:
            return
        if self.diagnostics_visible:
            self.diagnostics_canvas.pack(side="bottom", fill="x")
        else:
            self.diagnostics_canvas.pack_forget()

    def close(self) -> None:
        """Idempotent. Destroys only the window resources this renderer
        created — the organism, adapter, `ExpressionEngine`, and
        `HeadlessRenderer` keep running untouched."""
        if self._closed:
            return
        self._closed = True
        self.habitat_canvas.destroy()
        self.diagnostics_canvas.destroy()
        if self._owns_root:
            self.root.destroy()
