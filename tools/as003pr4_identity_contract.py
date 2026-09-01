#!/usr/bin/env python3
"""Pure AS-003P-R4 owner-scoped body-name equivalence proof.

This tool deliberately imports no UMBRA runtime modules.  It compares static
synthetic records only and therefore cannot create or tick an organism.
"""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any


BODY_REFERENCE_FIELDS = frozenset(
    {
        "body_instance_id",
        "new_body_instance_id",
        "held_body_instance_id",
        "actor_body_instance_id",
    }
)


def _body_mapping(left: dict[str, Any], right: dict[str, Any]) -> dict[str, str] | None:
    left_entities = {row["role"]: row["id"] for row in left["body_entities"]}
    right_entities = {row["role"]: row["id"] for row in right["body_entities"]}
    if set(left_entities) != set(right_entities):
        return None
    mapping = {left_entities[role]: right_entities[role] for role in left_entities}
    if len(mapping) != len(left_entities) or len(set(mapping.values())) != len(mapping):
        return None
    return mapping


def _rename(value: Any, mapping: dict[str, str], key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {k: _rename(v, mapping, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_rename(item, mapping, key) for item in value]
    if key in BODY_REFERENCE_FIELDS and isinstance(value, str):
        return mapping.get(value, value)
    return value


def alpha_equivalent(left: dict[str, Any], right: dict[str, Any]) -> bool:
    mapping = _body_mapping(left, right)
    if mapping is None:
        return False
    renamed = _rename(deepcopy(left), mapping)
    renamed["body_entities"] = deepcopy(right["body_entities"])
    return renamed == right


def _record(
    body_id: str,
    *,
    generation: int = 1,
    profile: str = "ABSTRACT_SHAPE_BODY",
    status: str = "ATTACHED",
    held_ref: str | None = None,
    pose_ref: str | None = None,
    request_ref: str | None = None,
    event_type: str = "embodiment_body_attached",
) -> dict[str, Any]:
    held_ref = body_id if held_ref is None else held_ref
    pose_ref = body_id if pose_ref is None else pose_ref
    request_ref = body_id if request_ref is None else request_ref
    return {
        "agent_id": "agent:constitutional",
        "body_entities": [{"role": "current-attached-body", "id": body_id}],
        "attachment": {
            "body_instance_id": body_id,
            "attachment_generation": generation,
            "body_profile_id": profile,
            "attachment_status": status,
        },
        "event": {
            "event_type": event_type,
            "new_body_instance_id": body_id,
            "new_generation": generation,
            "new_profile_id": profile,
        },
        "held_object": {
            "body_instance_id": held_ref,
            "attachment_generation": generation,
            "hold_slot": 0,
        },
        "body_pose": {
            "body_instance_id": pose_ref,
            "attachment_generation": generation,
        },
        "manipulation_request": {
            "body_instance_id": request_ref,
            "attachment_generation": generation,
        },
    }


def cases() -> list[dict[str, Any]]:
    a = "body:left"
    b = "body:right"
    rows: list[dict[str, Any]] = []

    def add(name: str, left: dict[str, Any], right: dict[str, Any], expected: bool) -> None:
        actual = alpha_equivalent(left, right)
        rows.append({"name": name, "expected": expected, "actual": actual, "pass": actual == expected})

    add("one_body_renamed_everywhere", _record(a), _record(b), True)
    add("event_and_final_adapter_renamed_together", _record(a), _record(b), True)
    add("held_object_reference_renamed_consistently", _record(a), _record(b), True)
    add("one_reference_left_stale", _record(a), _record(b, held_ref=a), False)

    left_two = _record(a)
    left_two["body_entities"].append({"role": "retired-body", "id": "body:left-old"})
    right_collapsed = _record(b)
    right_collapsed["body_entities"].append({"role": "retired-body", "id": b})
    add("two_bodies_collapsed_to_one", left_two, right_collapsed, False)

    split = _record(b)
    split["body_entities"].append({"role": "duplicate-current-reference", "id": "body:right-split"})
    add("one_body_split_into_two", _record(a), split, False)
    add("profile_differs", _record(a), _record(b, profile="MINIMAL_CREATURE_BODY"), False)
    add("attachment_generation_differs", _record(a), _record(b, generation=2), False)
    add(
        "detach_event_relationship_differs",
        _record(a),
        _record(b, status="DETACHED", event_type="embodiment_body_detached"),
        False,
    )
    add("manipulation_request_wrong_body", _record(a), _record(b, request_ref="body:unmapped"), False)
    add("same_body_after_restart", _record(a), _record(a), True)

    replacement = _record(b)
    replacement["body_entities"] = [{"role": "replacement-body", "id": b}]
    add("genuinely_different_body_replacement", _record(a), replacement, False)
    return rows


def main() -> None:
    rows = cases()
    result = {
        "schema": "AS003PR4_BODY_NAME_EQUIVALENCE_PROOF_V1",
        "pure_static_only": True,
        "production_imports": 0,
        "organism_constructions": 0,
        "organism_ticks": 0,
        "body_reference_fields": sorted(BODY_REFERENCE_FIELDS),
        "cases": rows,
        "case_count": len(rows),
        "positive_case_count": sum(1 for row in rows if row["expected"]),
        "negative_case_count": sum(1 for row in rows if not row["expected"]),
        "passed_case_count": sum(1 for row in rows if row["pass"]),
        "result": "PASS" if all(row["pass"] for row in rows) else "FAIL",
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
