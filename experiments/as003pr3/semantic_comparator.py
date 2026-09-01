"""Prospectively locked, owner/source-semantic observer comparator.

The comparator is research-only. It never imports UMBRA runtime code and never
constructs an organism. Administrative identities are declared by the source
contract, compared through a bijection, and never inferred from UUID shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
import json
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path(__file__).with_name("COMPARATOR_SOURCE_CONTRACT.json")
CONTRACT = json.loads(CONTRACT_PATH.read_text())
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
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, set):
        return sorted((_safe(v) for v in value), key=_json)
    if hasattr(value, "to_dict"):
        return _safe(value.to_dict())
    return str(value)


def _collect_admin_ids(value: Any, parts: tuple[str, ...], result: set[str]) -> None:
    if isinstance(value, dict):
        map_is_admin = _path(parts) in ADMIN_KEY_MAPS
        for raw_key, item in value.items():
            key = str(raw_key)
            if map_is_admin:
                result.add(key)
            if key in ADMIN_FIELDS and key not in SEMANTIC_ID_FIELDS and isinstance(item, str):
                result.add(item)
            _collect_admin_ids(item, parts + (key,), result)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _collect_admin_ids(item, parts + (str(index),), result)


def _shape(value: Any, parts: tuple[str, ...], admin_ids: set[str]) -> Any:
    """ID-renaming-independent prefilter used only to bound backtracking."""
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
    left_to_right: dict[str, str] = field(default_factory=dict)
    right_to_left: dict[str, str] = field(default_factory=dict)
    semantic_differences: list[dict[str, Any]] = field(default_factory=list)
    derivative_differences: list[dict[str, Any]] = field(default_factory=list)

    def clone(self) -> "_Context":
        return _Context(
            self.left_admin_ids,
            self.right_admin_ids,
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


def _compare_admin(left: str, right: str, parts: tuple[str, ...], ctx: _Context) -> bool:
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


def _compare_unordered_items(
    left: list[Any], right: list[Any], parts: tuple[str, ...], ctx: _Context
) -> bool:
    if len(left) != len(right):
        _difference(ctx, parts, len(left), len(right), "UNORDERED_COLLECTION_SIZE_MISMATCH")
        return False
    used: set[int] = set()

    def visit(index: int, current: _Context) -> _Context | None:
        if index == len(left):
            return current
        lshape = _shape(left[index], parts + ("*",), current.left_admin_ids)
        for right_index, candidate in enumerate(right):
            if right_index in used:
                continue
            if lshape != _shape(candidate, parts + ("*",), current.right_admin_ids):
                continue
            trial = current.clone()
            before = len(trial.semantic_differences)
            if _compare(left[index], candidate, parts + ("*",), trial):
                used.add(right_index)
                result = visit(index + 1, trial)
                if result is not None:
                    return result
                used.remove(right_index)
            elif len(trial.semantic_differences) == before:
                raise AssertionError("failed comparison did not record a difference")
        return None

    result = visit(0, ctx.clone())
    if result is None:
        _difference(ctx, parts, left, right, "UNORDERED_COLLECTION_SEMANTIC_MISMATCH")
        return False
    ctx.adopt(result)
    return True


def _compare_admin_map(
    left: dict[str, Any], right: dict[str, Any], parts: tuple[str, ...], ctx: _Context
) -> bool:
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
            if right_index in used:
                continue
            if lshape != _shape(right_value, parts + ("*",), current.right_admin_ids):
                continue
            trial = current.clone()
            if not _compare_admin(str(left_key), str(right_key), parts + ("@key",), trial):
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
            ctx.derivative_differences.append(
                {"path": _path(parts), "left": _safe(left), "right": _safe(right)}
            )
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
        ok = True
        for key in sorted(left_keys):
            ok = _compare(left[key], right[key], parts + (key,), ctx) and ok
        return ok
    if isinstance(left, (list, tuple)):
        if _path(parts) in UNORDERED_SEQUENCES:
            return _compare_unordered_items(list(left), list(right), parts, ctx)
        if len(left) != len(right):
            _difference(ctx, parts, len(left), len(right), "ORDERED_SEQUENCE_SIZE_MISMATCH")
            return False
        ok = True
        for index, (litem, ritem) in enumerate(zip(left, right)):
            ok = _compare(litem, ritem, parts + (str(index),), ctx) and ok
        return ok
    if isinstance(left, str):
        return _compare_admin(left, right, parts, ctx)
    if left != right:
        _difference(ctx, parts, left, right, "AUTHORITATIVE_VALUE_MISMATCH")
        return False
    return True


def _exact_leaf_differences(
    left: Any, right: Any, parts: tuple[str, ...] = (), *, limit: int = 200
) -> tuple[int, list[dict[str, Any]]]:
    count = 0
    rows: list[dict[str, Any]] = []

    def walk(a: Any, b: Any, p: tuple[str, ...]) -> None:
        nonlocal count
        if type(a) is not type(b):
            count += 1
            if len(rows) < limit:
                rows.append({"path": _path(p), "left": _safe(a), "right": _safe(b)})
            return
        if isinstance(a, dict):
            for key in sorted({str(k) for k in a} | {str(k) for k in b}):
                if key not in a or key not in b:
                    count += 1
                    if len(rows) < limit:
                        rows.append({"path": _path(p + (key,)), "left": _safe(a.get(key)), "right": _safe(b.get(key))})
                else:
                    walk(a[key], b[key], p + (key,))
            return
        if isinstance(a, (list, tuple)):
            if len(a) != len(b):
                count += 1
                if len(rows) < limit:
                    rows.append({"path": _path(p + ("<length>",)), "left": len(a), "right": len(b)})
            for index, (litem, ritem) in enumerate(zip(a, b)):
                walk(litem, ritem, p + (str(index),))
            return
        if a != b:
            count += 1
            if len(rows) < limit:
                rows.append({"path": _path(p), "left": _safe(a), "right": _safe(b)})

    walk(left, right, parts)
    return count, rows


def compare_values(left: Any, right: Any, *, root: str = "value") -> dict[str, Any]:
    left = _safe(left)
    right = _safe(right)
    left_ids: set[str] = set()
    right_ids: set[str] = set()
    _collect_admin_ids(left, (root,), left_ids)
    _collect_admin_ids(right, (root,), right_ids)
    ctx = _Context(left_ids, right_ids)
    semantic_equal = _compare(left, right, (root,), ctx)
    exact_count, exact_rows = _exact_leaf_differences(left, right, (root,))
    administrative = [
        {"left": left_id, "right": right_id}
        for left_id, right_id in sorted(ctx.left_to_right.items())
        if left_id != right_id
    ]
    return {
        "exact_equal": exact_count == 0,
        "exact_difference_count": exact_count,
        "exact_differences": exact_rows,
        "semantic_equal": semantic_equal and not ctx.semantic_differences,
        "semantic_difference_count": len(ctx.semantic_differences),
        "semantic_differences": ctx.semantic_differences,
        "administrative_difference_count": len(administrative),
        "administrative_differences": administrative,
        "derivative_difference_count": len(ctx.derivative_differences),
        "derivative_differences": ctx.derivative_differences,
        "administrative_bijection_size": len(ctx.left_to_right),
    }


def compare_run_records(control: dict[str, Any], shadow: dict[str, Any]) -> dict[str, Any]:
    sections = {
        "final_authoritative_state": (
            control["final_authoritative_state"], shadow["final_authoritative_state"]
        ),
        "authoritative_events": (control["authoritative_events"], shadow["authoritative_events"]),
        "timeline": (control["timeline"], shadow["timeline"]),
        "candidate_identities_by_tick": (
            control["candidate_identities_by_tick"], shadow["candidate_identities_by_tick"]
        ),
        "rng_state": (control["rng_state"], shadow["rng_state"]),
    }
    section_results = {
        name: compare_values(left, right, root=name)
        for name, (left, right) in sections.items()
    }
    left_bundle = {name: _safe(left) for name, (left, _) in sections.items()}
    right_bundle = {name: _safe(right) for name, (_, right) in sections.items()}
    left_ids: set[str] = set()
    right_ids: set[str] = set()
    _collect_admin_ids(left_bundle, (), left_ids)
    _collect_admin_ids(right_bundle, (), right_ids)
    global_context = _Context(left_ids, right_ids)
    global_equal = _compare(left_bundle, right_bundle, (), global_context)
    exact_count, exact_rows = _exact_leaf_differences(left_bundle, right_bundle)
    administrative = [
        {"left": left_id, "right": right_id}
        for left_id, right_id in sorted(global_context.left_to_right.items())
        if left_id != right_id
    ]
    per_subsystem = {
        key: compare_values(
            control["final_authoritative_state"].get(key),
            shadow["final_authoritative_state"].get(key),
            root=f"final_authoritative_state.{key}",
        )
        for key in sorted(
            set(control["final_authoritative_state"]) | set(shadow["final_authoritative_state"])
        )
    }
    semantic_differences = global_context.semantic_differences

    def prefix_equal(prefix: str) -> bool:
        return not any(
            row["path"] == prefix or row["path"].startswith(prefix + ".")
            for row in semantic_differences
        )

    return {
        "schema": "AS003PR3_SEMANTIC_OBSERVER_PARITY_V1",
        "exact_equal": exact_count == 0,
        "exact_difference_count": exact_count,
        "exact_differences": exact_rows,
        "semantic_equal": global_equal and not semantic_differences,
        "semantic_difference_count": len(semantic_differences),
        "semantic_differences": semantic_differences,
        "administrative_difference_count": len(administrative),
        "administrative_differences": administrative,
        "derivative_difference_count": len(global_context.derivative_differences),
        "derivative_differences": global_context.derivative_differences,
        "first_semantic_divergence": semantic_differences[0] if semantic_differences else None,
        "rng_equal": prefix_equal("rng_state"),
        "timeline_equal": prefix_equal("timeline"),
        "candidate_identities_equal": prefix_equal("candidate_identities_by_tick"),
        "authoritative_event_semantics_equal": prefix_equal("authoritative_events"),
        "final_authoritative_state_semantic_equal": prefix_equal("final_authoritative_state"),
        "per_subsystem": {
            key: {
                "semantic_equal": result["semantic_equal"],
                "semantic_difference_count": result["semantic_difference_count"],
                "administrative_difference_count": result["administrative_difference_count"],
                "derivative_difference_count": result["derivative_difference_count"],
            }
            for key, result in per_subsystem.items()
        },
        "section_results": section_results,
        "numeric_tolerance": None,
        "generic_uuid_detection": False,
    }
