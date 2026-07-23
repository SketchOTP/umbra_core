"""D-008 C7 — hostile renderer test double.

Implements the exact same shape as `ReferenceRenderer`
(`umbra_core.expression.renderer`): `render(entry)`, `set_diagnostics_visible`,
`close`. `HostileRenderer` is never constructed with, and never receives, a
live `Organism`/`Embodiment`/`Physiology`/`Governance` reference — Gate 8's
claim ("C7 detected/rejected") is that the channel a real renderer actually
gets grants no write authority, not that some other privileged access was
denied to a test double that never had it.

Gate 8 follow-up finding: an earlier revision handed renderers a
`FrameRingReader` wrapping the live `FrameRing`; even with `push`/`clear`
removed from the reader's own surface, the reader still leaked the live ring
through a plain `_ring` attribute a stored reference could walk to. The fix
removes the ring/reader channel entirely — no `ReferenceRenderer` method
(including `render`) accepts a ring or reader argument, so `HostileRenderer`
has structurally nothing ring-shaped to receive or store. What remains
attackable is the `FrameRingEntry`/`RenderPacket` it legitimately reads via
`render()`; every attempted write there is recorded in
`attempted_writes`/`rejected_writes`/`successful_writes` so a test can assert
none of the ordinary field-mutation attempts on the derived presentation
succeeded.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Callable

from umbra_core.expression.frame_ring import FrameRingEntry


@dataclass
class HostileRenderer:
    renderer_id: str = "hostile"
    attempted_writes: list[str] = field(default_factory=list)
    rejected_writes: list[str] = field(default_factory=list)
    successful_writes: list[str] = field(default_factory=list)

    def render(self, entry: FrameRingEntry) -> None:
        """Attempts ordinary attribute writes on every object reachable from
        an entry a real renderer would legitimately hold — no reflection
        tricks (`object.__setattr__` bypass), just what a careless or
        malicious `render()` implementation would actually try. `entry` is
        the only parameter this method (or any `ReferenceRenderer` method)
        ever receives — there is no ring/reader argument anywhere to also
        attempt a push/clear through (Gate 8 follow-up)."""
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
