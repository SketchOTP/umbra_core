"""Prospectively locked common-root semantic comparator for AS-003P-R5.

The comparator is pure research tooling. It imports no runtime module, performs
no UUID-shape guessing, and never constructs an organism. IDs already present
in the common root compare literally; source-declared post-fork administrative
IDs may differ only under one global bijection that preserves relationships.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path(__file__).with_name("AS003PR5_PARITY_SOURCE_CONTRACT.json")
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
ADMIN_FIELDS = frozenset(CONTRACT["administrative_field_names"])
SEMANTIC_ID_FIELDS = frozenset(CONTRACT["semantic_identity_field_names"])
ADMIN_KEY_MAPS = frozenset(CONTRACT["administrative_key_maps"])
DERIVATIVE_FIELDS = frozenset(CONTRACT["derivative_field_names"])
UNORDERED_SEQUENCES = frozenset(CONTRACT["unordered_sequence_paths"])


def _path(parts: tuple[str, ...]) -> str:
    return ".".join(parts)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    if isinstance(value, set):
        return sorted((_safe(item) for item in value), key=_json)
    if hasattr(value, "to_dict"):
        return _safe(value.to_dict())
    return str(value)


def collect_declared_ids(value: Any, *, root: str = "") -> set[str]:
    """Collect source-declared identity values, never UUID-looking strings."""
    result: set[str] = set()

    def walk(item: Any, parts: tuple[str, ...]) -> None:
        if isinstance(item, dict):
            map_is_admin = _path(parts) in ADMIN_KEY_MAPS
            for raw_key, child in item.items():
                key = str(raw_key)
                if map_is_admin:
                    result.add(key)
                if (key in ADMIN_FIELDS or key in SEMANTIC_ID_FIELDS) and isinstance(child, str):
                    result.add(child)
                walk(child, parts + (key,))
        elif isinstance(item, (list, tuple)):
            for index, child in enumerate(item):
                walk(child, parts + (str(index),))

    walk(_safe(value), (root,) if root else ())
    return result


def _collect_admin_ids(
    value: Any, parts: tuple[str, ...], exact_ids: frozenset[str], result: set[str]
) -> None:
    if isinstance(value, dict):
        map_is_admin = _path(parts) in ADMIN_KEY_MAPS
        for raw_key, item in value.items():
            key = str(raw_key)
            if map_is_admin and key not in exact_ids:
                result.add(key)
            if (
                key in ADMIN_FIELDS
                and key not in SEMANTIC_ID_FIELDS
                and isinstance(item, str)
                and item not in exact_ids
            ):
                result.add(item)
            _collect_admin_ids(item, parts + (key,), exact_ids, result)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _collect_admin_ids(item, parts + (str(index),), exact_ids, result)


def _shape(value: Any, parts: tuple[str, ...], admin_ids: set[str]) -> Any:
    if isinstance(value, dict):
        if _path(parts) in ADMIN_KEY_MAPS:
            rows = [_shape(item, parts + ("*",), admin_ids) for item in value.values()]
            return {"<ADMIN_MAP>": sorted(rows, key=_json)}
        return {
            str(key): (
                "<DERIVATIVE>"
                if str(key) in DERIVATIVE_FIELDS
                else _shape(item, parts + (str(key),), admin_ids)
            )
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        rows = [_shape(item, parts + (str(index),), admin_ids) for index, item in enumerate(value)]
        if _path(parts) in UNORDERED_SEQUENCES:
            rows.sort(key=_json)
        return rows
    if isinstance(value, str) and value in admin_ids:
        return "<ADMIN_ID>"
    return _safe(value)


@dataclass
class _Context:
    left_admin_ids: set[str]
    right_admin_ids: set[str]
    exact_ids: frozenset[str]
    left_to_right: dict[str, str] = field(default_factory=dict)
    right_to_left: dict[str, str] = field(default_factory=dict)
    semantic_differences: list[dict[str, Any]] = field(default_factory=list)
    derivative_differences: list[dict[str, Any]] = field(default_factory=list)

    def clone(self) -> "_Context":
        return _Context(
            self.left_admin_ids,
            self.right_admin_ids,
            self.exact_ids,
            dict(self.left_to_right),
            dict(self.right_to_left),
            list(self.semantic_differences),
            list(self.derivative_differences),
        )

    def adopt(self, other: "_Context") -> None:
        self.left_to_right = other.left_to_right
        self.right_to_left = other.right_to_left
        self.semantic_differences = other.semantic_differences
        self.derivative_differences = other.derivative_differences


def _difference(ctx: _Context, parts: tuple[str, ...], left: Any, right: Any, reason: str) -> None:
    ctx.semantic_differences.append(
        {"path": _path(parts), "left": _safe(left), "right": _safe(right), "reason": reason}
    )


def _compare_string(left: str, right: str, parts: tuple[str, ...], ctx: _Context) -> bool:
    if left in ctx.exact_ids or right in ctx.exact_ids:
        if left != right:
            _difference(ctx, parts, left, right, "PRE_FORK_IDENTITY_MISMATCH")
            return False
        return True
    left_is = left in ctx.left_admin_ids
    right_is = right in ctx.right_admin_ids
    if left_is != right_is:
        _difference(ctx, parts, left, right, "ADMINISTRATIVE_ID_CLASS_MISMATCH")
        return False
    if not left_is:
        if left != right:
            _difference(ctx, parts, left, right, "AUTHORITATIVE_VALUE_MISMATCH")
            return False
        return True
    mapped = ctx.left_to_right.get(left)
    reverse = ctx.right_to_left.get(right)
    if mapped is not None and mapped != right:
        _difference(ctx, parts, left, right, "ADMINISTRATIVE_RELATIONSHIP_BROKEN")
        return False
    if reverse is not None and reverse != left:
        _difference(ctx, parts, left, right, "ADMINISTRATIVE_BIJECTION_BROKEN")
        return False
    ctx.left_to_right[left] = right
    ctx.right_to_left[right] = left
    return True


def _compare_unordered(left: list[Any], right: list[Any], parts: tuple[str, ...], ctx: _Context) -> bool:
    if len(left) != len(right):
        _difference(ctx, parts, len(left), len(right), "UNORDERED_COLLECTION_SIZE_MISMATCH")
        return False
    used: set[int] = set()

    def visit(index: int, current: _Context) -> _Context | None:
        if index == len(left):
            return current
        lshape = _shape(left[index], parts + ("*",), current.left_admin_ids)
        for right_index, candidate in enumerate(right):
            if right_index in used or lshape != _shape(candidate, parts + ("*",), current.right_admin_ids):
                continue
            trial = current.clone()
            if _compare(left[index], candidate, parts + ("*",), trial):
                used.add(right_index)
                result = visit(index + 1, trial)
                if result is not None:
                    return result
                used.remove(right_index)
        return None

    result = visit(0, ctx.clone())
    if result is None:
        _difference(ctx, parts, left, right, "UNORDERED_COLLECTION_SEMANTIC_MISMATCH")
        return False
    ctx.adopt(result)
    return True


def _compare_admin_map(left: dict[str, Any], right: dict[str, Any], parts: tuple[str, ...], ctx: _Context) -> bool:
    if len(left) != len(right):
        _difference(ctx, parts, len(left), len(right), "ADMINISTRATIVE_MAP_SIZE_MISMATCH")
        return False
    left_items = list(left.items())
    right_items = list(right.items())
    used: set[int] = set()

    def visit(index: int, current: _Context) -> _Context | None:
        if index == len(left_items):
            return current
        left_key, left_value = left_items[index]
        lshape = _shape(left_value, parts + ("*",), current.left_admin_ids)
        for right_index, (right_key, right_value) in enumerate(right_items):
            if right_index in used or lshape != _shape(right_value, parts + ("*",), current.right_admin_ids):
                continue
            trial = current.clone()
            if not _compare_string(str(left_key), str(right_key), parts + ("@key",), trial):
                continue
            if not _compare(left_value, right_value, parts + ("*",), trial):
                continue
            used.add(right_index)
            result = visit(index + 1, trial)
            if result is not None:
                return result
            used.remove(right_index)
        return None

    result = visit(0, ctx.clone())
    if result is None:
        _difference(ctx, parts, left, right, "ADMINISTRATIVE_MAP_RELATIONSHIP_MISMATCH")
        return False
    ctx.adopt(result)
    return True


def _compare(left: Any, right: Any, parts: tuple[str, ...], ctx: _Context) -> bool:
    if parts and parts[-1] in DERIVATIVE_FIELDS:
        if _safe(left) != _safe(right):
            ctx.derivative_differences.append({"path": _path(parts), "left": _safe(left), "right": _safe(right)})
        return True
    if type(left) is not type(right):
        _difference(ctx, parts, type(left).__name__, type(right).__name__, "TYPE_MISMATCH")
        return False
    if isinstance(left, dict):
        if _path(parts) in ADMIN_KEY_MAPS:
            return _compare_admin_map(left, right, parts, ctx)
        left_keys = {str(key) for key in left}
        right_keys = {str(key) for key in right}
        if left_keys != right_keys:
            _difference(ctx, parts, sorted(left_keys), sorted(right_keys), "FIELD_SET_MISMATCH")
            return False
        return all(_compare(left[key], right[key], parts + (key,), ctx) for key in sorted(left_keys))
    if isinstance(left, (list, tuple)):
        if _path(parts) in UNORDERED_SEQUENCES:
            return _compare_unordered(list(left), list(right), parts, ctx)
        if len(left) != len(right):
            _difference(ctx, parts, len(left), len(right), "ORDERED_SEQUENCE_SIZE_MISMATCH")
            return False
        return all(_compare(a, b, parts + (str(index),), ctx) for index, (a, b) in enumerate(zip(left, right)))
    if isinstance(left, str):
        return _compare_string(left, right, parts, ctx)
    if left != right:
        _difference(ctx, parts, left, right, "AUTHORITATIVE_VALUE_MISMATCH")
        return False
    return True


def compare_values(
    left: Any, right: Any, *, root: str = "value", pre_fork_exact_ids: set[str] | frozenset[str] = frozenset()
) -> dict[str, Any]:
    left = _safe(left)
    right = _safe(right)
    exact_ids = frozenset(pre_fork_exact_ids)
    left_ids: set[str] = set()
    right_ids: set[str] = set()
    parts = (root,) if root else ()
    _collect_admin_ids(left, parts, exact_ids, left_ids)
    _collect_admin_ids(right, parts, exact_ids, right_ids)
    ctx = _Context(left_ids, right_ids, exact_ids)
    equal = _compare(left, right, parts, ctx)
    administrative = [
        {"left": left_id, "right": right_id}
        for left_id, right_id in sorted(ctx.left_to_right.items())
        if left_id != right_id
    ]
    return {
        "schema": "AS003PR5_SEMANTIC_COMPARISON_V1",
        "semantic_equal": equal and not ctx.semantic_differences,
        "semantic_difference_count": len(ctx.semantic_differences),
        "semantic_differences": ctx.semantic_differences,
        "administrative_difference_count": len(administrative),
        "administrative_differences": administrative,
        "derivative_difference_count": len(ctx.derivative_differences),
        "derivative_differences": ctx.derivative_differences,
        "administrative_bijection_size": len(ctx.left_to_right),
        "pre_fork_exact_id_count": len(exact_ids),
    }


def compare_run_records(
    control: dict[str, Any], shadow: dict[str, Any], *, pre_fork_exact_ids: set[str] | frozenset[str]
) -> dict[str, Any]:
    sections = {
        "final_authoritative_state": (control["final_authoritative_state"], shadow["final_authoritative_state"]),
        "authoritative_events": (control["authoritative_events"], shadow["authoritative_events"]),
        "timeline": (control["timeline"], shadow["timeline"]),
        "candidate_identities_by_tick": (control["candidate_identities_by_tick"], shadow["candidate_identities_by_tick"]),
        "rng_state": (control["rng_state"], shadow["rng_state"]),
        "final_habitat_state": (control["final_habitat_state"], shadow["final_habitat_state"]),
    }
    left_bundle = {name: _safe(left) for name, (left, _) in sections.items()}
    right_bundle = {name: _safe(right) for name, (_, right) in sections.items()}
    for bundle in (left_bundle, right_bundle):
        for row in bundle["candidate_identities_by_tick"]:
            if isinstance(row.get("pool"), list):
                row["pool"] = sorted(row["pool"], key=_json)
    report = compare_values(left_bundle, right_bundle, root="", pre_fork_exact_ids=pre_fork_exact_ids)
    differences = report["semantic_differences"]

    def prefix_equal(prefix: str) -> bool:
        return not any(row["path"] == prefix or row["path"].startswith(prefix + ".") for row in differences)

    report.update(
        {
            "schema": "AS003PR5_SEMANTIC_OBSERVER_PARITY_V1",
            "first_semantic_divergence": differences[0] if differences else None,
            "rng_equal": prefix_equal("rng_state"),
            "habitat_equal": prefix_equal("final_habitat_state"),
            "timeline_equal": prefix_equal("timeline"),
            "candidate_identities_equal": prefix_equal("candidate_identities_by_tick"),
            "authoritative_event_semantics_equal": prefix_equal("authoritative_events"),
            "final_authoritative_state_semantic_equal": prefix_equal("final_authoritative_state"),
            "numeric_tolerance": None,
            "generic_uuid_detection": False,
        }
    )
    return report
