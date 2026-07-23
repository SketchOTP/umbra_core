"""TkinterRenderer — the visible reference-companion `ReferenceRenderer`
(design §3), sitting over the same headless `FrameRing`/`RenderPacket`
presentation model as `umbra_core.expression.headless_renderer.HeadlessRenderer`.
It only ever reads `FrameRingEntry` objects the organism already committed
via `read_latest`; it holds no reference to the organism, adapter, or
`ExpressionEngine`, so it structurally cannot write core state.

`tkinter` is imported lazily inside `__init__` — never at module import
time — so importing this module (e.g. for the import-isolation test, or for
`habitat_view`/`diagnostics` unit tests using a fake canvas double) never
requires a real Tk installation or display. Only constructing an instance
does.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from ui.reference_companion import diagnostics, habitat_view
from umbra_core.expression.frame_ring import FrameRingEntry, FrameRingReader, RendererCursor

if TYPE_CHECKING:
    import tkinter as tk

HABITAT_CANVAS_SIZE = (480, 480)
DIAGNOSTICS_CANVAS_SIZE = (480, 160)
DEFAULT_POLL_INTERVAL_MS = 66  # renderer-local cadence; never tied to organism tick rate


class TkinterRenderer:
    """`close()` unregisters this renderer's cursor, destroys only the
    window resources it created, and leaves the organism, adapter,
    `ExpressionEngine`, and any other renderer (e.g. `HeadlessRenderer`)
    completely untouched and running.

    Thread-safety: the organism is expected to tick on a thread other than
    the Tk main thread (Tkinter itself is not thread-safe). `ring_lock` is
    exposed so a driving harness wraps `Organism.tick_once()` in the same
    lock this renderer uses around `FrameRing.read_latest` calls — an
    explicit thread-safe handoff boundary without adding any locking to
    `FrameRing` itself.
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
        self._cursor: RendererCursor | None = RendererCursor(renderer_id=renderer_id)
        self.ring_lock = threading.Lock()

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

    def read_latest(self, ring: FrameRingReader) -> FrameRingEntry | None:
        if self._closed or self._cursor is None:
            return None
        with self.ring_lock:
            return ring.read_latest(self._cursor)

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

    def poll_and_render(self, ring: FrameRingReader) -> FrameRingEntry | None:
        """One non-blocking poll step, suitable for a Tk `after()`-scheduled
        loop. Never calls into the organism — only `read_latest`/`render` on
        frames it already committed."""
        entry = self.read_latest(ring)
        if entry is not None:
            self.render(entry)
        return entry

    def schedule(self, ring: FrameRingReader, *, interval_ms: int = DEFAULT_POLL_INTERVAL_MS) -> None:
        """Schedules recurring polling on the Tk main loop. Cadence is
        renderer-local wall time and independent of organism ticks."""
        if self._closed:
            return
        self.poll_and_render(ring)
        self.root.after(interval_ms, lambda: self.schedule(ring, interval_ms=interval_ms))

    def close(self) -> None:
        """Idempotent. Unregisters the frame cursor and destroys only the
        window resources this renderer created — the organism, adapter,
        `ExpressionEngine`, and `HeadlessRenderer` keep running untouched."""
        if self._closed:
            return
        self._closed = True
        self._cursor = None
        self.habitat_canvas.destroy()
        self.diagnostics_canvas.destroy()
        if self._owns_root:
            self.root.destroy()
