"""Pure CLOSE-02V recovery-contract shadow.

This module is diagnostic/test scoped. It does not execute actions, mutate
organism state, consume organism RNG, or persist state.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from umbra_core.arbitration import Candidate

REMEMBERED_FACT_KIND = "REMEMBERED_ESTIMATE"
MEMORY_SOURCE = "world_model_memory"
CONTACT_CAPABILITIES = frozenset({"REST", "CHARGE", "INSPECT", "MANIPULATE"})


def interaction_evidence_class(observation: Mapping[str, Any]) -> str:
    """Classify policy-visible interaction evidence without hidden truth."""
    if (
        observation.get("fact_kind") == REMEMBERED_FACT_KIND
        or observation.get("source") == MEMORY_SOURCE
    ):
        return REMEMBERED_FACT_KIND
    return "CURRENT_OBSERVATION"


def contact_interaction_is_justified(
    candidate: Candidate, observation: Mapping[str, Any]
) -> bool:
    """Remembered geometry guides navigation, never proves contact."""
    if candidate.capability not in CONTACT_CAPABILITIES:
        return False
    return interaction_evidence_class(observation) == "CURRENT_OBSERVATION"


def build_reacquisition_candidate(observation: Mapping[str, Any]) -> Candidate:
    """Build the existing bounded homing shape for a remembered landmark."""
    nominal_distance = float(observation.get("estimated_distance", 1.5))
    return Candidate(
        "APPROACH",
        {
            "heading_delta": float(observation.get("relative_direction", 0.0)),
            "step": min(1.5, max(0.5, nominal_distance)),
            "toward": str(observation["kind"]),
            "source": "active_reacquisition",
            "strategy": "direct_homing",
            "fact_kind": REMEMBERED_FACT_KIND,
        },
    )


def adjudicate_initial_recovery(
    chosen: Candidate,
    alternatives: Sequence[Candidate],
    *,
    immediately_safe: Callable[[Candidate], bool],
    contract_admissible: Callable[[Candidate], bool],
) -> Candidate | None:
    """Purely filter an initial choice before commit; preserve caller ranking."""
    for candidate in (chosen, *alternatives):
        if immediately_safe(candidate) and contract_admissible(candidate):
            return candidate
    return None
