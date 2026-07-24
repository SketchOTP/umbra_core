"""D-009 C10 — governance bypass attempt helpers (experiments only).

Every payload must be rejected by production `Governance.admit` with zero habitat
mutation when exercised through the normal admit → execute chain.
"""

from __future__ import annotations

from typing import Any

from umbra_core.governance import Governance, GovernanceState


def bypass_manipulation_proposals() -> list[tuple[str, dict[str, Any], list[str] | None]]:
    """(capability, params, requested_effects) tuples that attempt authority bypass."""
    return [
        (
            "MANIPULATE",
            {
                "target_object_id": "resource:0",
                "kind": "USE",
                "perceived_affordance_ref": "affordance:resource:use",
            },
            None,
        ),
        (
            "MANIPULATE",
            {"kind": "USE", "grants": ["MANIPULATE"]},
            ["grant_capability"],
        ),
        (
            "MANIPULATE",
            {"kind": "USE", "authority": "self"},
            ["modify_identity"],
        ),
        (
            "MANIPULATE",
            {"kind": "USE", "physiology_set": {"energy": 1.0}},
            ["modify_physiology_direct"],
        ),
    ]


def attempt_governance_bypass(
    governance: Governance | None = None,
    *,
    tick: int = 1,
) -> list[dict[str, Any]]:
    """Run bypass proposals; return per-attempt admission outcomes."""
    gov = governance or Governance(GovernanceState(bypass_enabled=True))
    outcomes: list[dict[str, Any]] = []
    for capability, params, effects in bypass_manipulation_proposals():
        proposal = gov.propose(capability, params, requested_effects=effects)
        decision = gov.admit(proposal, tick=tick)
        outcomes.append(
            {
                "admitted": decision.admitted,
                "stage_failed": decision.stage_failed,
                "reason": decision.reason,
                "params_keys": sorted(params.keys()),
            }
        )
    return outcomes
