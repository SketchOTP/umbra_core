"""`ReferenceRenderer` protocol — non-destructive `FrameRing` polling contract.

Renderers (`HeadlessRenderer` here; Task 9's `TkinterRenderer`) only ever read
`FrameRingEntry` objects the organism already committed. The organism never
calls into a renderer — a harness/UI loop polls the renderer independently of
`Organism.tick_once` — so renderer failure, closure, or slowdown structurally
cannot pause or block the organism.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from umbra_core.expression.frame_ring import FrameRing, FrameRingEntry


@runtime_checkable
class ReferenceRenderer(Protocol):
    def read_latest(self, ring: FrameRing) -> FrameRingEntry | None: ...

    def render(self, entry: FrameRingEntry) -> None: ...

    def set_diagnostics_visible(self, visible: bool) -> None: ...

    def close(self) -> None: ...
