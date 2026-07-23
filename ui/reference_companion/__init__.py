"""Tkinter reference companion (Task 9) — the visible `ReferenceRenderer`
over the same headless presentation model as `HeadlessRenderer` (design §1:
"Tkinter visualizes authoritative state; it does not participate in
organism control, persistence, or scientific evaluation logic.").

Import rule (design §1): `umbra_core` and `experiments` MUST NOT import
`ui/`. This package may import `umbra_core.expression` — nothing here may
write back into organism state.
"""

from __future__ import annotations

from ui.reference_companion.tkinter_renderer import TkinterRenderer

__all__ = ["TkinterRenderer"]
