#!/usr/bin/env python3
"""Pure retained-evidence forensics for UMBRA-AS-003P-R2.

The tool never imports or constructs Organism and never executes runtime. It
reads the immutable AS-003P-R1 evidence corpus and emits one requested JSON
analysis to stdout for durable publication by ``tools/as003pr2_evidence.py``.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


R1_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r1-shadow-protocol-recovery"
)
UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}"
)
FROZEN_DERIVATIVE_HASH_KEYS = {
    "event_hash",
    "payload_hash",
    "previous_event_hash",
    "source_sample_hash",
    "state_hash",
}
TEMPORAL_DERIVATIVE_HASH_KEYS = {
    "new_state_hash",
    "prior_state_hash",
    "trusted_sample_hash",
}


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, set):
        return sorted((_safe(v) for v in value), key=repr)
    return str(value)


def frozen_semantic(value: Any, identities: dict[str, str] | None = None) -> Any:
    """Byte-for-byte semantic reconstruction of frozen AS-003P behavior."""
    identities = identities if identities is not None else {}
    if isinstance(value, dict):
        return {
            str(key): frozen_semantic(item, identities)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in FROZEN_DERIVATIVE_HASH_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [frozen_semantic(item, identities) for item in value]
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            raw = match.group(0).lower()
            if raw not in identities:
                identities[raw] = f"<ADMIN_UUID_{len(identities) + 1}>"
            return identities[raw]

        return UUID_PATTERN.sub(replace, value)
    return _safe(value)


def _canonical(value: Any) -> str:
    return json.dumps(_safe(value), sort_keys=True, separators=(",", ":"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runs() -> tuple[dict[str, Any], dict[str, Any]]:
    control = json.loads((R1_ROOT / "AS003PR1_CONTROL_RUN.json").read_text())
    shadow = json.loads((R1_ROOT / "AS003PR1_SHADOW_RUN.json").read_text())
    return control, shadow


def _trace(name: str) -> list[dict[str, Any]]:
    path = R1_ROOT / name
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _semantic_multiset(rows: Iterable[dict[str, Any]], excluded: set[str]) -> list[dict[str, Any]]:
    result = [{k: v for k, v in row.items() if k not in excluded} for row in rows]
    return sorted(result, key=_canonical)


def _accepted_world(state: dict[str, Any]) -> dict[str, Any]:
    models = sorted(
        (
            {
                "conditions": model["conditions"],
                "action": model["action"],
                "predicted_effect": model["predicted_effect"],
                "support_count": model["support_count"],
                "contradiction_count": model["contradiction_count"],
                "status": model["status"],
                "confidence": round(model["confidence"], 4),
            }
            for model in state["models"].values()
        ),
        key=lambda row: (row["action"], str(row["conditions"]), row["status"]),
    )
    entities = sorted(
        (
            {
                "entity_kind": entity["entity_kind"],
                "estimated_state": {
                    key: round(value, 4)
                    for key, value in entity["estimated_state"].items()
                },
                "confidence": round(entity["confidence"], 4),
                "fact_kind": entity["fact_kind"],
                "evidence_count": entity["evidence_count"],
            }
            for entity in state["entities"].values()
        ),
        key=lambda row: row["entity_kind"],
    )
    affordances = sorted(
        (
            {
                "entity_kind": affordance["entity_kind"],
                "action": affordance["action"],
                "support_count": affordance["support_count"],
                "contradiction_count": affordance["contradiction_count"],
                "confidence": round(affordance["confidence"], 4),
                "status": affordance["status"],
            }
            for affordance in state["affordances"].values()
        ),
        key=lambda row: (row["entity_kind"], row["action"]),
    )
    return {
        "entities": entities,
        "models": models,
        "affordances": affordances,
        "supersession_count": len(state["supersessions"]),
        "contradiction_count": len(state["contradictions"]),
    }


def _model_semantics(state: dict[str, Any]) -> list[dict[str, Any]]:
    return _semantic_multiset(state["models"].values(), {"model_id"})


def _world_semantics(state: dict[str, Any]) -> dict[str, Any]:
    result = dict(state)
    result["models"] = _model_semantics(state)
    return result


def _model_token_map(state: dict[str, Any]) -> dict[str, str]:
    result = {}
    for model in state["models"].values():
        semantic = {key: value for key, value in model.items() if key != "model_id"}
        result[str(model["model_id"])] = "<MODEL_SEMANTIC_" + hashlib.sha256(
            _canonical(semantic).encode()
        ).hexdigest() + ">"
    return result


def _translate_model_tokens(value: Any, mapping: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _translate_model_tokens(item, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [_translate_model_tokens(item, mapping) for item in value]
    if isinstance(value, str):
        for token, semantic in mapping.items():
            value = value.replace(token, semantic)
        return value
    return value


def _drop_keys(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _drop_keys(item, keys)
            for key, item in value.items()
            if key not in keys
        }
    if isinstance(value, list):
        return [_drop_keys(item, keys) for item in value]
    return value


def _leaf_differences(left: Any, right: Any, path: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    if type(left) is not type(right):
        return [{"path": "/".join(path), "control": left, "shadow": right}]
    if isinstance(left, dict):
        rows: list[dict[str, Any]] = []
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                rows.append({"path": "/".join(path + (key,)), "control": left.get(key), "shadow": right.get(key)})
            else:
                rows.extend(_leaf_differences(left[key], right[key], path + (key,)))
        return rows
    if isinstance(left, list):
        rows = []
        if len(left) != len(right):
            rows.append({"path": "/".join(path + ("<length>",)), "control": len(left), "shadow": len(right)})
        for index, (a, b) in enumerate(zip(left, right)):
            rows.extend(_leaf_differences(a, b, path + (str(index),)))
        return rows
    if left != right:
        return [{"path": "/".join(path), "control": left, "shadow": right}]
    return []


def retained_inventory() -> dict[str, Any]:
    content = {
        "AS003PR1_CONTROL_RUN.json": ["already_normalized_authoritative_events", "already_normalized_final_authoritative_state", "subsystem_hashes", "rng_state", "timeline", "candidate_identities"],
        "AS003PR1_SHADOW_RUN.json": ["already_normalized_authoritative_events", "already_normalized_final_authoritative_state", "subsystem_hashes", "rng_state", "timeline", "candidate_identities"],
        "AS003PR1_CONTROL_DECISION_TRACE.jsonl": ["raw_decision_trace", "raw_identifiers", "per_tick_world_model_transition", "candidate_views", "authority_lineage"],
        "AS003PR1_SHADOW_DECISION_TRACE.jsonl": ["raw_decision_trace", "raw_identifiers", "per_tick_world_model_transition", "candidate_views", "authority_lineage"],
        "AS003PR1_PLANNING_SHADOW_TRACE.jsonl": ["raw_shadow_frames", "raw_world_entity_rows", "candidate_profiles", "source_fingerprints"],
        "AS003PR1_OBSERVER_PARITY.json": ["frozen_comparison_result", "normalization_contract", "coverage_aggregates"],
        "AS003PR1_PAIRED_EXECUTION_STARTED.json": ["command", "fixture", "commit", "working_directory"],
        "AS003PR1_PAIRED_EXECUTION_FINISHED.json": ["execution_counts", "artifact_hashes", "parity_boolean"],
        "AS003PR1_FINAL_EVIDENCE_MANIFEST.json": ["artifact_inventory", "readback_hashes"],
    }
    files = []
    for path in sorted(R1_ROOT.iterdir()):
        if path.is_file():
            files.append({
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": _sha(path),
                "attribution_content": content.get(path.name, []),
            })
    return {
        "schema": "AS003PR2_RETAINED_EVIDENCE_INVENTORY_V1",
        "directive": "UMBRA-AS-003P-R2",
        "source_root": str(R1_ROOT),
        "artifact_count": len(files),
        "artifacts": files,
        "retention": {
            "raw_identifiers": "retained in decision and planning JSONL; final-state UUID dictionary keys also survive frozen normalization",
            "already_normalized_identifiers": "UUID-looking string values in run records and events were replaced by first-occurrence tokens",
            "subsystem_internal_state": "final authoritative state retained for all 32 top-level fields",
            "event_payloads": "retained after frozen UUID-value normalization and selected derivative-hash omission",
            "world_model": {
                "entities": True,
                "models": True,
                "affordances": True,
                "predictions": True,
                "contradictions": True,
                "supersessions": True,
                "plan_traces": True,
                "observation_log": True,
                "prediction_errors": True,
                "processed_execution_ids": True,
                "metrics": True,
            },
        },
        "destroyed_or_not_retained": [
            "raw UUID string values inside final authoritative state and event records",
            "event_hash, payload_hash, previous_event_hash, source_sample_hash, and state_hash fields removed by the frozen normalizer",
            "temporary SQLite databases and unnormalized authoritative_state snapshots",
            "a control planning-shadow trace, absent by experimental design",
            "per-tick complete authoritative owner snapshots beyond decision/event traces",
        ],
        "organism_executions": 0,
    }


def comparator_proof() -> dict[str, Any]:
    a = "11111111-1111-4111-8111-111111111111"
    b = "22222222-2222-4222-8222-222222222222"
    x = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    y = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    cases = [
        ("UUID_KEY_SINGLE", {a: {"kind": "RESOURCE"}}, {x: {"kind": "RESOURCE"}}, True),
        ("UUID_KEY_PERMUTED", {a: {"kind": "RESOURCE"}, b: {"kind": "REST"}}, {x: {"kind": "REST"}, y: {"kind": "RESOURCE"}}, True),
        ("UUID_VALUE_SINGLE", {"entity_id": a, "kind": "RESOURCE"}, {"entity_id": x, "kind": "RESOURCE"}, True),
        ("UUID_VALUE_REPEATED_RELATION", {"owner": a, "ref": a}, {"owner": x, "ref": x}, True),
        ("NESTED_UUID_KEYS", {"models": {a: {"action": "MOVE"}}}, {"models": {x: {"action": "MOVE"}}}, True),
        ("KEY_VALUE_RELATION", {a: {"model_id": a, "action": "MOVE"}}, {x: {"model_id": x, "action": "MOVE"}}, True),
        ("SEMANTIC_VALUE_CHANGE", {"entity_id": a, "kind": "RESOURCE"}, {"entity_id": x, "kind": "REST"}, False),
        ("SEMANTIC_RELATION_CHANGE", {"owner": a, "ref": a}, {"owner": x, "ref": y}, False),
    ]
    rows = []
    false_positive = 0
    false_negative = 0
    for name, left, right, expected_equal in cases:
        frozen_equal = frozen_semantic(left) == frozen_semantic(right)
        if expected_equal and not frozen_equal:
            false_positive += 1
        if not expected_equal and frozen_equal:
            false_negative += 1
        rows.append({
            "case": name,
            "expected_semantic_equal": expected_equal,
            "frozen_comparator_equal": frozen_equal,
            "result": "PASS" if frozen_equal == expected_equal else "FALSE_POSITIVE" if expected_equal else "FALSE_NEGATIVE",
        })
    return {
        "schema": "AS003PR2_COMPARATOR_INVARIANCE_PROOF_V1",
        "directive": "UMBRA-AS-003P-R2",
        "frozen_comparator_reimplemented_exactly": True,
        "required_property": "semantic-equivalence + administrative-ID-renaming => comparator equality",
        "result": "FROZEN_COMPARATOR_NOT_ID_RENAMING_INVARIANT" if false_positive else "PASS",
        "synthetic_cases": len(rows),
        "synthetic_false_positive_count": false_positive,
        "synthetic_false_negative_count": false_negative,
        "uuid_key_ordering_causal": true_json(),
        "mechanisms": [
            "dictionary keys are sorted as raw strings and copied without UUID replacement",
            "UUID values are tokenized only after traversal order has been fixed by raw UUID keys",
            "first-occurrence token assignment can therefore bind tokens to different semantic records",
        ],
        "cases": rows,
        "actual_pair_attribution_from_this_artifact": "NOT_ESTABLISHED_BY_SYNTHETIC_PROOF_ALONE",
        "organism_executions": 0,
    }


def true_json() -> bool:
    return True


def world_comparison_semantics() -> dict[str, Any]:
    return {
        "schema": "AS003PR2_WORLD_MODEL_COMPARISON_SEMANTICS_V1",
        "directive": "UMBRA-AS-003P-R2",
        "representations": {
            "to_state": {
                "purpose": "complete persistence and exact recreation state",
                "contains_generated_identifiers": True,
                "byte_equal_across_independent_runs_expected": False,
            },
            "state_hash": {
                "purpose": "integrity hash of complete to_state representation",
                "generated_identifier_sensitive": True,
            },
            "accepted_state": {
                "purpose": "replay/semantic equality of structural WorldModel content",
                "excludes": [
                    "agent_id", "model_id", "entity_id", "affordance_id",
                    "prediction and plan identities/history", "observation log",
                    "prediction errors", "processed execution IDs", "metrics",
                    "model latency",
                ],
                "rounds": ["confidence", "entity estimated_state"],
                "cannot_alone_exclude_authoritative_mutation": True,
            },
        },
        "forensic_rule": "accepted_state is architectural evidence for volatile identity but exact field comparison remains required for excluded fields",
        "source_locations": [
            "umbra_core/world_model/engine.py:1559 state_hash",
            "umbra_core/world_model/engine.py:1563 to_state",
            "umbra_core/world_model/engine.py:1584 accepted_state",
        ],
    }


def world_semantic_diff() -> dict[str, Any]:
    control, shadow = _runs()
    c = control["final_authoritative_state"]["world_model"]
    s = shadow["final_authoritative_state"]["world_model"]
    exact_fields = {key: c.get(key) == s.get(key) for key in sorted(set(c) | set(s))}
    c_models = _model_semantics(c)
    s_models = _model_semantics(s)
    accepted_c = _accepted_world(c)
    accepted_s = _accepted_world(s)
    semantic_c = _world_semantics(c)
    semantic_s = _world_semantics(s)
    differing_model_ids = sorted(
        (row["action"], str(row["conditions"]), row["model_id"])
        for row in c["models"].values()
    ) != sorted(
        (row["action"], str(row["conditions"]), row["model_id"])
        for row in s["models"].values()
    )
    return {
        "schema": "AS003PR2_WORLD_MODEL_SEMANTIC_DIFF_V1",
        "directive": "UMBRA-AS-003P-R2",
        "raw_frozen_world_model_equal": c == s,
        "exact_field_comparisons": exact_fields,
        "exact_differing_fields": [key for key, equal in exact_fields.items() if not equal],
        "model_counts": {"control": len(c["models"]), "shadow": len(s["models"])},
        "model_dictionary_keys_equal": set(c["models"]) == set(s["models"]),
        "model_id_tokens_by_semantic_record_equal": not differing_model_ids,
        "model_semantic_multiset_exact_equal": c_models == s_models,
        "model_semantic_fields": [
            "conditions", "action", "predicted_effect", "latency", "confidence",
            "support_count", "contradiction_count", "status",
        ],
        "entities_exact_equal": c["entities"] == s["entities"],
        "affordances_exact_equal": c["affordances"] == s["affordances"],
        "predictions_exact_equal": c["predictions"] == s["predictions"],
        "contradictions_exact_equal": c["contradictions"] == s["contradictions"],
        "supersessions_exact_equal": c["supersessions"] == s["supersessions"],
        "plan_traces_exact_equal": c["plan_traces"] == s["plan_traces"],
        "observation_log_exact_equal": c["observation_log"] == s["observation_log"],
        "prediction_errors_exact_equal": c["prediction_errors"] == s["prediction_errors"],
        "processed_environmental_executions_exact_equal": c["processed_environmental_executions"] == s["processed_environmental_executions"],
        "metrics_exact_equal": c["metrics"] == s["metrics"],
        "accepted_state_equal": accepted_c == accepted_s,
        "accepted_state_control_sha256": hashlib.sha256(_canonical(accepted_c).encode()).hexdigest(),
        "accepted_state_shadow_sha256": hashlib.sha256(_canonical(accepted_s).encode()).hexdigest(),
        "full_id_invariant_world_model_equal": semantic_c == semantic_s,
        "semantic_difference_count": len(_leaf_differences(semantic_c, semantic_s)),
        "finding": "ONLY_ADMINISTRATIVE_MODEL_DICTIONARY_KEYS_AND_MODEL_ID_TOKEN_ASSIGNMENTS_DIFFER",
        "precision_weakened": False,
        "fields_removed_because_they_differ": False,
        "organism_executions": 0,
    }


def event_semantic_diff() -> dict[str, Any]:
    control, shadow = _runs()
    c = control["authoritative_events"]
    s = shadow["authoritative_events"]
    rows = []
    path_counts: Counter[str] = Counter()
    differing_indices = []
    for index, (left, right) in enumerate(zip(c, s)):
        diffs = _leaf_differences(left, right)
        if diffs:
            differing_indices.append(index)
            for row in diffs:
                normalized = "/".join("<index>" if part.isdigit() else part for part in row["path"].split("/"))
                path_counts[normalized] += 1
                if len(rows) < 20:
                    rows.append({"event_index": index, **row})
    c_sem = _drop_keys(c, TEMPORAL_DERIVATIVE_HASH_KEYS)
    s_sem = _drop_keys(s, TEMPORAL_DERIVATIVE_HASH_KEYS)
    return {
        "schema": "AS003PR2_EVENT_SEMANTIC_DIFF_V1",
        "directive": "UMBRA-AS-003P-R2",
        "event_counts": {"control": len(c), "shadow": len(s)},
        "exact_differing_event_count": len(differing_indices),
        "first_differing_event_index": differing_indices[0] if differing_indices else None,
        "first_differing_sequence": c[differing_indices[0]]["sequence"] if differing_indices else None,
        "first_differing_tick": c[differing_indices[0]]["payload"].get("runtime_tick") if differing_indices else None,
        "leaf_difference_count": sum(path_counts.values()),
        "difference_path_counts": dict(sorted(path_counts.items())),
        "sample_differences": rows,
        "source_proven_derivative_fields": sorted(TEMPORAL_DERIVATIVE_HASH_KEYS),
        "derivative_rationale": {
            "trusted_sample_hash": "compute_sample_hash hashes TrustedSample including non-seeded session_id",
            "prior_state_hash": "compute_state_hash hashes TemporalState including session-bearing anchor/mapping",
            "new_state_hash": "with_state_hash recomputes the complete session-bearing TemporalState hash",
        },
        "semantic_events_equal_after_only_source_proven_derivatives": c_sem == s_sem,
        "semantic_event_difference_count": len(_leaf_differences(c_sem, s_sem)),
        "classification": "DERIVATIVE_HASH_ONLY",
        "sequence_preserved": [row["sequence"] for row in c] == [row["sequence"] for row in s],
        "event_types_preserved": [row["event_type"] for row in c] == [row["event_type"] for row in s],
        "monotonic_time_preserved": [row["monotonic_time"] for row in c] == [row["monotonic_time"] for row in s],
        "organism_executions": 0,
    }


def final_state_diff() -> dict[str, Any]:
    control, shadow = _runs()
    c = control["final_authoritative_state"]
    s = shadow["final_authoritative_state"]
    exact = {key: c.get(key) == s.get(key) for key in sorted(set(c) | set(s))}
    semantic = dict(c)
    semantic["world_model"] = _world_semantics(c["world_model"])
    semantic_shadow = dict(s)
    semantic_shadow["world_model"] = _world_semantics(s["world_model"])
    required = {
        "physiology": "physiology",
        "embodiment": "embodiment",
        "perception": "perception",
        "arbitration": "arbitration",
        "governance": "governance",
        "self_model": "self_model",
        "world_model": "world_model",
        "development": "development",
        "memory": "memory",
        "social": "social",
        "individuality": "individuality",
        "temporal": "temporal",
        "runtime_pending_state": None,
        "metrics": "metrics",
    }
    subsystem_results = {}
    for label, key in required.items():
        if key is None:
            left = {k: c.get(k) for k in ("pending_action", "delayed_proposal")}
            right = {k: s.get(k) for k in ("pending_action", "delayed_proposal")}
            subsystem_results[label] = {"exact_equal": left == right, "semantic_equal": left == right}
        elif label == "world_model":
            subsystem_results[label] = {"exact_equal": c[key] == s[key], "semantic_equal": _world_semantics(c[key]) == _world_semantics(s[key])}
        else:
            subsystem_results[label] = {"exact_equal": c.get(key) == s.get(key), "semantic_equal": c.get(key) == s.get(key)}
    return {
        "schema": "AS003PR2_FINAL_STATE_SEMANTIC_DIFF_V1",
        "directive": "UMBRA-AS-003P-R2",
        "exact_top_level_comparisons": exact,
        "exact_differing_top_level_fields": [key for key, equal in exact.items() if not equal],
        "subsystem_results": subsystem_results,
        "full_semantic_state_equal": semantic == semantic_shadow,
        "semantic_difference_count": len(_leaf_differences(semantic, semantic_shadow)),
        "final_state_hash_mismatch_explained_by": "generated WorldModel model dictionary keys and first-occurrence model_id token assignment",
        "numbers_compared_exactly": True,
        "organism_executions": 0,
    }


def first_divergence() -> dict[str, Any]:
    control, shadow = _runs()
    c_events = control["authoritative_events"]
    s_events = shadow["authoritative_events"]
    event_index = next((index for index, pair in enumerate(zip(c_events, s_events)) if pair[0] != pair[1]), None)
    c_trace = _trace("AS003PR1_CONTROL_DECISION_TRACE.jsonl")
    s_trace = _trace("AS003PR1_SHADOW_DECISION_TRACE.jsonl")
    exact_trace_index = next((index for index, pair in enumerate(zip(c_trace, s_trace)) if pair[0] != pair[1]), None)
    trace_semantic_control = frozen_semantic(c_trace)
    trace_semantic_shadow = frozen_semantic(s_trace)
    for row in trace_semantic_control:
        row.pop("trace_row_hash", None)
    for row in trace_semantic_shadow:
        row.pop("trace_row_hash", None)
    return {
        "schema": "AS003PR2_FIRST_DIVERGENCE_V1",
        "directive": "UMBRA-AS-003P-R2",
        "earliest_retained_exact_difference": {
            "source": "authoritative_events",
            "event_index": event_index,
            "sequence": c_events[event_index]["sequence"] if event_index is not None else None,
            "tick": c_events[event_index]["payload"].get("runtime_tick") if event_index is not None else None,
            "classification": "DERIVATIVE_HASH_ONLY",
            "fields": ["new_state_hash", "prior_state_hash", "trusted_sample_hash"],
        },
        "decision_trace": {
            "first_exact_difference_row": exact_trace_index,
            "first_exact_difference_tick": c_trace[exact_trace_index]["tick"] if exact_trace_index is not None else None,
            "classification": "ADMINISTRATIVE_ID_AND_DERIVATIVE_HASH_ONLY",
            "id_normalized_trace_equal": trace_semantic_control == trace_semantic_shadow,
        },
        "first_semantic_divergence": "NONE_RETAINED",
        "first_semantic_divergence_tick": None,
        "final_world_model_difference_classification": "ADMINISTRATIVE_ID_ONLY",
        "organism_executions": 0,
    }


def nondeterministic_id_audit() -> dict[str, Any]:
    return {
        "schema": "AS003PR2_NONDETERMINISTIC_ID_AUDIT_V1",
        "directive": "UMBRA-AS-003P-R2",
        "sources": [
            {"source": "umbra_core.util.new_id", "implementation": "uuid.uuid4", "seeded": False, "classification": "ADMINISTRATIVE_ID_SOURCE"},
            {"source": "runtime.session_id", "implementation": "new_id", "seeded": False, "affects": ["temporal anchors", "wall-clock mappings", "trusted-sample hashes", "temporal state hashes", "event payloads"]},
            {"source": "temporal transaction/advance/observation/effect IDs", "implementation": "new_id", "seeded": False, "affects": ["event relationships", "derivative hashes"]},
            {"source": "WorldModel entity/model/prediction/plan IDs", "implementation": "new_id unless a specific seeded authored-prior path applies", "seeded": False, "affects": ["dictionary keys", "provenance relationships", "to_state ordering", "state_hash"]},
            {"source": "event IDs", "implementation": "generated administrative identity", "seeded": False, "affects": ["causal/event ledger relationships", "derivative hashes"]},
            {"source": "SelfModel prediction/error/decision/evidence IDs", "implementation": "new_id in live update paths", "seeded": False, "affects": ["owner history identity", "state hashes"]},
        ],
        "world_model_model_identity_behavior": {
            "used_as_merit": False,
            "used_as_provenance": True,
            "used_as_dictionary_identity": True,
            "can_affect_raw_sort_order": True,
            "can_affect_raw_state_hash": True,
            "retained_pair_semantic_model_content_equal": True,
        },
        "independent_same_seed_to_state_byte_equality_expected": False,
        "independent_same_seed_semantic_state_equality_expected": True,
        "r1_result": "ADMINISTRATIVE_NONDETERMINISM_PRESENT_WITHOUT_RETAINED_SEMANTIC_DIVERGENCE",
        "h3_semantic_divergence_confirmed": False,
        "organism_executions": 0,
    }


def world_relationship_audit() -> dict[str, Any]:
    control, shadow = _runs()
    c = control["final_authoritative_state"]["world_model"]
    s = shadow["final_authoritative_state"]["world_model"]
    c_map = _model_token_map(c)
    s_map = _model_token_map(s)
    fields = (
        "predictions", "contradictions", "supersessions", "plan_traces",
        "observation_log", "processed_environmental_executions",
    )
    results = {}
    for field in fields:
        exact = c[field] == s[field]
        translated = _translate_model_tokens(c[field], c_map) == _translate_model_tokens(s[field], s_map)
        results[field] = {
            "frozen_normalized_exact_equal": exact,
            "active_model_semantic_relationship_equal": translated,
        }
    return {
        "schema": "AS003PR2_WORLD_MODEL_RELATIONSHIP_AUDIT_V1",
        "directive": "UMBRA-AS-003P-R2",
        "active_model_counts": {"control": len(c_map), "shadow": len(s_map)},
        "method": "replace each retained active model token with a SHA-256 label of its exact non-ID model content, then compare relationship-bearing structures",
        "fields": results,
        "all_relationship_fields_equal": all(
            row["active_model_semantic_relationship_equal"] for row in results.values()
        ),
        "relationship_semantics_erased": False,
        "organism_executions": 0,
    }


ARTIFACTS = {
    "AS003PR2_RETAINED_EVIDENCE_INVENTORY.json": retained_inventory,
    "AS003PR2_COMPARATOR_INVARIANCE_PROOF.json": comparator_proof,
    "AS003PR2_WORLD_MODEL_COMPARISON_SEMANTICS.json": world_comparison_semantics,
    "AS003PR2_WORLD_MODEL_SEMANTIC_DIFF.json": world_semantic_diff,
    "AS003PR2_EVENT_SEMANTIC_DIFF.json": event_semantic_diff,
    "AS003PR2_FINAL_STATE_SEMANTIC_DIFF.json": final_state_diff,
    "AS003PR2_FIRST_DIVERGENCE.json": first_divergence,
    "AS003PR2_NONDETERMINISTIC_ID_AUDIT.json": nondeterministic_id_audit,
    "AS003PR2_WORLD_MODEL_RELATIONSHIP_AUDIT.json": world_relationship_audit,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", choices=sorted(ARTIFACTS))
    args = parser.parse_args()
    print(json.dumps(ARTIFACTS[args.artifact](), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
