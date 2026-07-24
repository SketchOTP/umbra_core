"""D-009 C9 — hostile UI/projection double that treats read models as habitat truth.

Gate 1/10: UI and projections are read-only; attempts to write habitat through
them must be rejected with zero authoritative mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from umbra_core.embodiment import Embodiment
from umbra_core.habitat.projection import HabitatWriteRejected


@dataclass
class HostileHabitatProjection:
    """Records write attempts against read-only habitat/UI surfaces."""

    attempted_writes: list[str] = field(default_factory=list)
    rejected_writes: list[str] = field(default_factory=list)
    successful_writes: list[str] = field(default_factory=list)

    def attempt_projection_writes(self, embodiment: Embodiment) -> None:
        habitat = embodiment.habitat
        self._attempt("relocate_via_projection", lambda: habitat.relocate("resource", 9.0, 9.0))
        self._attempt(
            "mutate_feature_tuple",
            lambda: setattr(habitat.features[0], "x", 1.0) if habitat.features else (_ for _ in ()).throw(AttributeError("no_features")),
        )
        self._attempt(
            "append_feature",
            lambda: habitat.features.append({"kind": "hack"}),  # type: ignore[attr-defined]
        )

    def attempt_ui_habitat_truth_write(self, ui_relocate: Callable[..., Any] | None = None) -> None:
        if ui_relocate is None:
            self.attempted_writes.append("ui_relocate_skipped")
            self.rejected_writes.append("ui_relocate_skipped")
            return
        self._attempt("ui_relocate_as_truth", lambda: ui_relocate("resource", 0.0, 0.0))

    def _attempt(self, label: str, action: Callable[[], Any]) -> None:
        self.attempted_writes.append(label)
        try:
            action()
        except (AttributeError, HabitatWriteRejected, TypeError, ValueError):
            self.rejected_writes.append(label)
        else:
            self.successful_writes.append(label)
