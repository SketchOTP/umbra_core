"""C3-only scalar affection ablation — experiments/d006/ only; not production.

Must not be imported by `umbra_core` or introduce production schemas.
"""

from __future__ import annotations

from dataclasses import dataclass

from umbra_core.util import clamp


@dataclass
class AffectionController:
    """Isolated scalar affection meter for C3 exploratory experiments."""

    affection: float = 0.0

    def observe_interaction(self, *, positive: bool, delta: float = 0.1) -> float:
        signed = delta if positive else -delta
        self.affection = clamp(self.affection + signed)
        return self.affection

    def proposal_bias(self) -> float:
        return self.affection
