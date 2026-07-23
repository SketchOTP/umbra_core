"""`ReferenceRenderer` protocol — renderers never touch `FrameRing`.

Renderers (`HeadlessRenderer` here; Task 9's `TkinterRenderer`) only ever
render `FrameRingEntry` objects a caller already read from the organism's
`FrameRing`. The organism never calls into a renderer — a harness/UI loop
polls the ring itself, independently of `Organism.tick_once`, and hands the
renderer only the resulting entry — so renderer failure, closure, or
slowdown structurally cannot pause or block the organism.

Gate 8 (Task 11 finding, and its follow-up): earlier revisions handed
renderers a `FrameRingReader` wrapping the live `FrameRing` — safe against
`push`/`clear` calls, but still reachable via the reader's own `_ring`
attribute. Renderers now receive neither a `FrameRing` nor a reader at all:
`render()` takes only the already-read `FrameRingEntry`. The poll step
(`ring.read_latest(cursor)`) belongs to whatever trusted code drives the
loop, never to the renderer.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from umbra_core.expression.frame_ring import FrameRingEntry


@runtime_checkable
class ReferenceRenderer(Protocol):
    def render(self, entry: FrameRingEntry) -> None: ...

    def set_diagnostics_visible(self, visible: bool) -> None: ...

    def close(self) -> None: ...
