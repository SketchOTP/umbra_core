"""Bounded non-authoritative frame ring for D-008 render packets.

The ring stores complete `RenderPacket` objects. Renderers read those stored
packets only; they never rebuild habitat from current world state while reading
an older presentation frame.
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

    def read_only(self) -> "FrameRingReader":
        """Read-only view for renderers (Gate 8 finding, Task 11): renderers
        must never hold the live ring's `push`/`clear`, only non-destructive
        `read_latest`/introspection."""
        return FrameRingReader(self)

    def _drop_retired(self, current_tick: int) -> None:
        minimum_tick = current_tick - self.retention_ticks
        self._entries = [
            entry for entry in self._entries if entry.derived_at_tick >= minimum_tick
        ]

    @staticmethod
    def _is_valid_for_cursor(entry: FrameRingEntry, cursor: RendererCursor) -> bool:
        packet = entry.render_packet
        if packet.habitat_read_model.version != packet.habitat_state_version:
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
        if entry.active_execution_id is not None:
            return entry.active_execution_id == cursor.active_execution_id
        return True


class FrameRingReader:
    """Read-only, non-destructive view over a `FrameRing`. This — never the
    live `FrameRing` itself — is what renderers receive (Task 11 Gate 8
    finding: renderers previously received the live ring, whose public
    `push`/`clear` a renderer implementation could store and call). Exposes
    only `read_latest` plus harmless introspection; has no `push` or
    `clear`, so even a renderer that stores this reference across calls has
    no method to call to write into the ring."""

    __slots__ = ("_ring",)

    def __init__(self, ring: FrameRing) -> None:
        self._ring = ring

    def read_latest(self, cursor: RendererCursor) -> FrameRingEntry | None:
        return self._ring.read_latest(cursor)

    def __len__(self) -> int:
        return len(self._ring)

    def __iter__(self) -> Iterator[FrameRingEntry]:
        return iter(self._ring)

    @property
    def oldest_frame_id(self) -> int | None:
        return self._ring.oldest_frame_id
