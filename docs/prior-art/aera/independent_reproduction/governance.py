"""Governance + homeostasis boundaries for Track 5."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from models import ModelStore


class Authority(Enum):
    NONE = "none"
    OPERATOR = "operator"
    POLICY = "policy"


@dataclass(frozen=True)
class Proposal:
    action: str
    source_model_id: str | None
    rationale: str


@dataclass
class Physiology:
    """Track-2-style homeostatic urgency (read-only to planner)."""

    energy: float = 0.7

    @property
    def urgency(self) -> float:
        # Higher when energy low
        return max(0.0, 1.0 - self.energy)


class GovernanceGate:
    """Learned models may propose; they cannot authorize effects."""

    def __init__(self):
        self.authorized: list[tuple[str, Authority]] = []
        self.rejected: list[str] = []

    def propose_from_model(self, store: ModelStore, action: str, model_id: str | None) -> Proposal:
        return Proposal(action=action, source_model_id=model_id, rationale="model_proposal")

    def authorize(self, proposal: Proposal, authority: Authority) -> bool:
        if authority is Authority.NONE:
            self.rejected.append(proposal.action)
            return False
        # Models never grant authority
        if proposal.source_model_id is not None and authority is Authority.NONE:
            self.rejected.append(proposal.action)
            return False
        self.authorized.append((proposal.action, authority))
        return True

    def model_grants_authority(self, store: ModelStore, model_id: str) -> bool:
        """Invariant: always False — models have no authority channel."""
        _ = store, model_id
        return False


def homeostasis_priority(phys: Physiology, base: float = 0.5) -> float:
    """Urgency may prioritize goals; must not rewrite models or dictate actions."""
    return base + phys.urgency


def homeostasis_cannot_rewrite(store: ModelStore, phys: Physiology) -> None:
    """Assert boundary: calling priority helper does not mutate models."""
    before = store.dump()
    _ = homeostasis_priority(phys)
    after = store.dump()
    assert before == after
