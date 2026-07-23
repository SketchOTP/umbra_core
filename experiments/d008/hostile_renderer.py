"""D-008 C7 — hostile renderer test double.

Implements the same shape as `ReferenceRenderer`
(`umbra_core.expression.renderer`) but every `render()` call attempts a
battery of prohibited writes using only the channel a real renderer gets: a
`FrameRing` to poll plus the `FrameRingEntry`/`RenderPacket` objects it
returns. `HostileRenderer` is never constructed with, and never receives, a
live `Organism`/`Embodiment`/`Physiology`/`Governance` reference — Gate 8's
claim ("C7 detected/rejected") is that *this* channel alone grants no write
authority, not that some other privileged access was denied to a test
double that never had it.

Attempted writes are recorded in `attempted_writes`/`rejected_writes`/
`successful_writes` so a test can assert none of the ordinary field-mutation
attempts on the derived presentation succeeded.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Callable

from umbra_core.expression.frame_ring import FrameRingEntry, FrameRingReader, RendererCursor


@dataclass
class HostileRenderer:
    renderer_id: str = "hostile"
    attempted_writes: list[str] = field(default_factory=list)
    rejected_writes: list[str] = field(default_factory=list)
    successful_writes: list[str] = field(default_factory=list)
    _cursor: RendererCursor = field(init=False, repr=False)
    _ring: FrameRingReader | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self._cursor = RendererCursor(renderer_id=self.renderer_id)

    def read_latest(self, ring: FrameRingReader) -> FrameRingEntry | None:
        # A hostile implementation stores the reader across calls, hoping to
        # find a write method on it later from `render()` (Gate 8 finding).
        self._ring = ring
        return ring.read_latest(self._cursor)

    def render(self, entry: FrameRingEntry) -> None:
        """Attempts ordinary attribute writes on every object reachable from
        an entry a real renderer would legitimately hold — no reflection
        tricks (`object.__setattr__` bypass), just what a careless or
        malicious `render()` implementation would actually try."""
        ps = entry.render_packet.presentation_state
        self._attempt("mutate_presentation_posture", lambda: setattr(ps, "posture", "HACKED"))
        self._attempt(
            "mutate_presentation_active_capability",
            lambda: setattr(ps, "active_capability", "MOVE"),
        )
        self._attempt(
            "mutate_presentation_attention_confidence",
            lambda: setattr(ps, "attention_confidence", 1.0),
        )
        self._attempt(
            "mutate_habitat_read_model_version",
            lambda: setattr(entry.render_packet.habitat_read_model, "version", -1),
        )
        self._attempt(
            "mutate_render_packet_state_version",
            lambda: setattr(entry.render_packet, "source_state_version", -1),
        )
        self._attempt("mutate_frame_ring_entry_id", lambda: setattr(entry, "frame_id", -1))
        self._attempt(
            "mutate_visible_condition_channel",
            lambda: ps.visible_condition_channels.__setitem__("persistence", 999.0),
        )
        self._attempt(
            "mutate_developmental_marker",
            lambda: ps.developmental_markers.__setitem__("hacked", True),
        )
        self._attempt("push_via_held_ring_reference", lambda: self._ring.push(entry))
        self._attempt("clear_via_held_ring_reference", lambda: self._ring.clear())

    def set_diagnostics_visible(self, visible: bool) -> None:
        return None

    def close(self) -> None:
        return None

    def _attempt(self, label: str, action: Callable[[], None]) -> None:
        self.attempted_writes.append(label)
        try:
            action()
        except (AttributeError, dataclasses.FrozenInstanceError, TypeError):
            self.rejected_writes.append(label)
        else:
            self.successful_writes.append(label)
