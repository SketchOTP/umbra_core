"""Bounded non-authoritative frame ring for D-008 render packets.

The ring stores complete `RenderPacket` objects. Renderers read those stored
packets only; they never rebuild habitat from current world state while reading
an older presentation frame.

Gate 8 (Task 11 finding + follow-up): a renderer must never receive this
`FrameRing` object, nor any reader wrapping it — including a wrapper whose
`push`/`clear` methods are removed, since the wrapper can still leak the live
ring through a plain attribute (e.g. `reader._ring`) that a hostile `render()`
implementation can walk to. The poll step (`FrameRing.read_latest(cursor)`)
belongs entirely to the trusted caller driving the loop (organism runtime or
UI harness); only the resulting `FrameRingEntry` — never the ring — is passed
to `ReferenceRenderer.render(entry)`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from umbra_core.expression.engine import RenderPacket

_THRESHOLDS_PATH = Path(__file__).resolve().parents[2] / "experiments" / "d008" / "thresholds.json"
_THRESHOLDS = json.loads(_THRESHOLDS_PATH.read_text())

FRAME_RING_CAPACITY = int(_THRESHOLDS["frame_ring_capacity"])
FRAME_RING_RETENTION_TICKS = int(_THRESHOLDS["frame_ring_retention_ticks"])
SOURCE_EVENT_REFS_MAX = int(_THRESHOLDS["source_event_refs_max"])


@dataclass(frozen=True)
class FrameRingEntry:
    frame_id: int
    derived_at_tick: int
    active_execution_id: str | None
    render_packet: RenderPacket
    source_event_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        packet_refs = tuple(
            self.render_packet.presentation_state.source_event_refs[:SOURCE_EVENT_REFS_MAX]
        )
        refs = tuple(self.source_event_refs[:SOURCE_EVENT_REFS_MAX])
        if packet_refs and refs != packet_refs:
            refs = packet_refs
        object.__setattr__(self, "source_event_refs", refs)


@dataclass
class RendererCursor:
    renderer_id: str
    last_frame_id: int = -1
    current_tick: int | None = None
    body_attachment_generation: int | None = None
    source_state_version: int | None = None
    habitat_state_version: int | None = None
    body_pose_version: int | None = None
    active_execution_id: str | None = None


class FrameRing:
    def __init__(self, capacity: int, retention_ticks: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if retention_ticks < 0:
            raise ValueError("retention_ticks must be non-negative")
        self.capacity = int(capacity)
        self.retention_ticks = int(retention_ticks)
        self._entries: list[FrameRingEntry] = []

    @classmethod
    def from_thresholds(cls) -> "FrameRing":
        return cls(capacity=FRAME_RING_CAPACITY, retention_ticks=FRAME_RING_RETENTION_TICKS)

    def push(self, entry: FrameRingEntry) -> None:
        self._entries.append(entry)
        self._drop_retired(entry.derived_at_tick)
        overflow = len(self._entries) - self.capacity
        if overflow > 0:
            del self._entries[:overflow]

    def read_latest(self, cursor: RendererCursor) -> FrameRingEntry | None:
        for entry in reversed(self._entries):
            if entry.frame_id <= cursor.last_frame_id:
                continue
            if self._is_valid_for_cursor(entry, cursor):
                cursor.last_frame_id = entry.frame_id
                return entry
        return None

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[FrameRingEntry]:
        return iter(tuple(self._entries))

    @property
    def oldest_frame_id(self) -> int | None:
        if not self._entries:
            return None
        return self._entries[0].frame_id

    def _drop_retired(self, current_tick: int) -> None:
        minimum_tick = current_tick - self.retention_ticks
        self._entries = [
            entry for entry in self._entries if entry.derived_at_tick >= minimum_tick
        ]

    @staticmethod
    def _packet_is_coherent(packet: RenderPacket) -> bool:
        if packet.habitat_read_model.version != packet.habitat_state_version:
            return False
        if packet.habitat_state_hash and packet.habitat_read_model.state_hash != packet.habitat_state_hash:
            return False
        if packet.organism_state_version != packet.source_state_version:
            return False
        if (
            packet.body_pose_version is not None
            and packet.presentation_state.attachment_status == "ATTACHED"
            and packet.presentation_state.position is not None
        ):
            # ponytail: body pose version is carried for held-object coherence only
            pass
        return True

    @staticmethod
    def _is_valid_for_cursor(entry: FrameRingEntry, cursor: RendererCursor) -> bool:
        packet = entry.render_packet
        if not FrameRing._packet_is_coherent(packet):
            return False
        if tuple(packet.presentation_state.source_event_refs) != entry.source_event_refs:
            return False
        if (
            cursor.body_attachment_generation is not None
            and packet.body_attachment_generation != cursor.body_attachment_generation
        ):
            return False
        if (
            cursor.source_state_version is not None
            and packet.source_state_version != cursor.source_state_version
        ):
            return False
        if (
            cursor.habitat_state_version is not None
            and packet.habitat_state_version != cursor.habitat_state_version
        ):
            return False
        if (
            cursor.body_pose_version is not None
            and packet.body_pose_version is not None
            and packet.body_pose_version != cursor.body_pose_version
        ):
            return False
        if entry.active_execution_id is not None:
            return entry.active_execution_id == cursor.active_execution_id
        return True
