"""`ReferenceRenderer` protocol — non-destructive `FrameRing` polling contract.

Renderers (`HeadlessRenderer` here; Task 9's `TkinterRenderer`) only ever read
`FrameRingEntry` objects the organism already committed. The organism never
calls into a renderer — a harness/UI loop polls the renderer independently of
`Organism.tick_once` — so renderer failure, closure, or slowdown structurally
cannot pause or block the organism.

Renderers receive a `FrameRingReader` (Task 11 Gate 8), never the live
`FrameRing`: the reader exposes only `read_latest`, so a renderer cannot
`push`/`clear` even if it stores the reference across calls.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from umbra_core.expression.frame_ring import FrameRingEntry, FrameRingReader


@runtime_checkable
class ReferenceRenderer(Protocol):
    def read_latest(self, ring: FrameRingReader) -> FrameRingEntry | None: ...

    def render(self, entry: FrameRingEntry) -> None: ...

    def set_diagnostics_visible(self, visible: bool) -> None: ...

    def close(self) -> None: ...
