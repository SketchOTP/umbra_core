"""D-010 C10 — governance bypass attempt helpers for WAIT (experiments only)."""

from __future__ import annotations

from typing import Any

from umbra_core.governance import Governance, GovernanceState


def bypass_wait_proposals() -> list[tuple[str, dict[str, Any], list[str] | None]]:
    return [
        (
            "WAIT",
            {
                "recurrence_id": "rec:bypass",
                "window_start": 1.0,
                "window_end": 5.0,
                "authority": "self",
            },
            None,
        ),
        (
            "WAIT",
            {"recurrence_id": "rec:bypass", "grants": ["WAIT"]},
            ["grant_capability"],
        ),
        (
            "WAIT",
            {"recurrence_id": "rec:bypass", "physiology_set": {"energy": 1.0}},
            ["modify_physiology_direct"],
        ),
    ]


def attempt_wait_governance_bypass(
    governance: Governance | None = None,
    *,
    tick: int = 1,
) -> list[dict[str, Any]]:
    gov = governance or Governance(GovernanceState(bypass_enabled=True))
    outcomes: list[dict[str, Any]] = []
    for capability, params, effects in bypass_wait_proposals():
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
