"""Pure CLOSE-02U contract proof; no organism or production state mutation."""

from __future__ import annotations

from math import isfinite

from umbra_core.world_model.engine import CAPABILITY_TO_AFFORDANCE


# These are the existing authored interaction conventions, not a new need
# priority table: the runtime already derives the same target kinds when it
# completes verified outcomes.
VERIFIED_RECOVERY_TARGET_KINDS = {
    "CHARGE": frozenset(("resource", "novel_crystal")),
    "REST": frozenset(("rest",)),
}


def qualifies_verified_recovery_landmark(
    *, action: str, entity_kind: str | None, observations: list[dict], outcome: dict
) -> bool:
    """Pure eligibility predicate for a verified recovery landmark."""
    if action not in VERIFIED_RECOVERY_TARGET_KINDS:
        return False
    if entity_kind not in VERIFIED_RECOVERY_TARGET_KINDS[action]:
        return False
    if not bool(outcome.get("success")) or not bool(outcome.get("verified")):
        return False
    return any(
        str(row.get("kind")) == entity_kind
        and row.get("source") != "world_model_memory"
        and row.get("fact_kind") != "REMEMBERED_ESTIMATE"
        and row.get("distance_support_upper_bound") is not None
        and isfinite(float(row["distance_support_upper_bound"]))
        and float(row["distance_support_upper_bound"]) >= 0.0
        for row in observations
    )


def proof_cases() -> dict[str, bool]:
    direct_rest = [{
        "kind": "rest", "source": "sensor", "fact_kind": "CURRENT_OBSERVATION",
        "distance_support_upper_bound": 4.0,
    }]
    direct_resource = [{
        "kind": "resource", "source": "sensor", "fact_kind": "CURRENT_OBSERVATION",
        "distance_support_upper_bound": 4.0,
    }]
    good = {"success": True, "verified": True}
    failed = {"success": False, "verified": True}
    denied = {"success": False, "verified": False}
    memory_rest = [{**direct_rest[0], "source": "world_model_memory", "fact_kind": "REMEMBERED_ESTIMATE"}]
    unsupported = [{"kind": "rest", "source": "sensor", "fact_kind": "CURRENT_OBSERVATION"}]
    return {
        "direct_charge": qualifies_verified_recovery_landmark(
            action="CHARGE", entity_kind="resource", observations=direct_resource, outcome=good
        ),
        "direct_rest": qualifies_verified_recovery_landmark(
            action="REST", entity_kind="rest", observations=direct_rest, outcome=good
        ),
        "failed_rest": not qualifies_verified_recovery_landmark(
            action="REST", entity_kind="rest", observations=direct_rest, outcome=failed
        ),
        "denied_rest": not qualifies_verified_recovery_landmark(
            action="REST", entity_kind="rest", observations=direct_rest, outcome=denied
        ),
        "memory_not_direct": not qualifies_verified_recovery_landmark(
            action="REST", entity_kind="rest", observations=memory_rest, outcome=good
        ),
        "unsupported_not_direct": not qualifies_verified_recovery_landmark(
            action="REST", entity_kind="rest", observations=unsupported, outcome=good
        ),
        "unrelated_kind_rejected": not qualifies_verified_recovery_landmark(
            action="REST", entity_kind="resource", observations=direct_rest, outcome=good
        ),
        "unknown_action_rejected": not qualifies_verified_recovery_landmark(
            action="MOVE", entity_kind="rest", observations=direct_rest, outcome=good
        ),
        "existing_affordance_mapping_present": CAPABILITY_TO_AFFORDANCE["REST"] == "rest_near",
    }


if __name__ == "__main__":
    result = proof_cases()
    assert all(result.values()), result
    print(result)
