#!/usr/bin/env python3
"""Offline-only AS-003D attribution over sealed AS-003C competition traces.

The tool never imports runtime or production arbitration.  It reads retained JSONL
traces, reconstructs the frozen views, and writes only immutable derivative
evidence through fsync + atomic rename.  Its ablations are explanatory probes,
not replacement-selection rules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import uuid


SUPPORTED = "SUPPORTED"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"
BLOCKER_CLASSES = (
    "WORSE_IN_SUPPORTED_CHANNEL",
    "UNKNOWN_BLOCK",
    "ONE_SIDED_NOT_APPLICABLE_BLOCK",
    "NO_STRICT_SUPPORTED_IMPROVEMENT",
    "MULTIPLE_BLOCKERS",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def durable_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError("short_write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.exists():
        raise FileExistsError(path)
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def durable_json(path: Path, value: Any) -> None:
    durable_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def family(channel: str) -> str:
    if channel.startswith("physiology."):
        return "physiology"
    if channel.startswith("body."):
        return "SelfModel"
    if channel.startswith("world."):
        return "WorldModel"
    if channel.startswith("temporal."):
        return "temporal"
    if channel.startswith("individuality."):
        return "individuality"
    if channel.startswith(("continuity.", "context.")):
        return "continuity/context"
    if channel.startswith("option."):
        return "option/recoverability"
    if channel.startswith(("development.", "habit.", "memory.", "social.")):
        return "development/habit/memory/social"
    return "other"


def evidence(view: dict[str, Any], key: str) -> dict[str, Any]:
    return view["channels"].get(key, {"status": NOT_APPLICABLE, "order": None, "provenance": []})


def channel_pairs(
    a: dict[str, Any], b: dict[str, Any], *, include: Iterable[str] | None = None,
    ignore_unknown: bool = False, ignore_one_sided: bool = False, include_details: bool = False,
) -> dict[str, Any]:
    keys = sorted(set(a["channels"]) | set(b["channels"]))
    if include is not None:
        allowed = set(include)
        keys = [key for key in keys if key in allowed]
    strict: list[str] = []
    worse: list[str] = []
    unknown: list[str] = []
    one_sided: list[str] = []
    details: list[dict[str, Any]] = []
    production_blocked: list[str] = []
    first_production: dict[str, Any] | None = None
    production_strict: list[str] = []
    for key in keys:
        av = evidence(a, key)
        bv = evidence(b, key)
        ast, bst = av["status"], bv["status"]
        detail = {"channel": key, "family": family(key), "a_status": ast, "b_status": bst} if include_details else None
        if ast == NOT_APPLICABLE and bst == NOT_APPLICABLE:
            if detail is not None:
                detail["relation"] = "BOTH_NOT_APPLICABLE"
        elif ast == NOT_APPLICABLE or bst == NOT_APPLICABLE:
            if detail is not None:
                detail["relation"] = "ONE_SIDED_NOT_APPLICABLE"
            one_sided.append(key)
            if not ignore_one_sided:
                production_blocked.append(key)
        elif ast != SUPPORTED or bst != SUPPORTED:
            if detail is not None:
                detail["relation"] = "UNKNOWN_OR_UNSUPPORTED"
            unknown.append(key)
            if not ignore_unknown:
                production_blocked.append(key)
        else:
            ao, bo = float(av["order"]), float(bv["order"])
            if detail is not None:
                detail["a_order"] = ao
                detail["b_order"] = bo
            if ao < bo:
                if detail is not None:
                    detail["relation"] = "A_WORSE"
                worse.append(key)
                if first_production is None:
                    first_production = {"reason": "worse_in_supported_channel", "channel": key}
            elif ao > bo:
                if detail is not None:
                    detail["relation"] = "A_STRICTLY_BETTER"
                strict.append(key)
                if first_production is None:
                    production_strict.append(key)
            else:
                if detail is not None:
                    detail["relation"] = "EQUAL_SUPPORTED"
        if detail is not None:
            details.append(detail)
    if first_production is None and production_blocked:
        first_production = {
            "reason": "unknown_or_inapplicable_blocks_elimination",
            "channels": production_blocked,
        }
    elif first_production is None and not production_strict:
        first_production = {"reason": "no_strict_supported_improvement", "channels": []}
    elif first_production is None:
        first_production = {"reason": "supported_no_worse_everywhere_and_strictly_better", "channels": production_strict}
    categories = []
    if worse:
        categories.append("WORSE_IN_SUPPORTED_CHANNEL")
    if unknown:
        categories.append("UNKNOWN_BLOCK")
    if one_sided:
        categories.append("ONE_SIDED_NOT_APPLICABLE_BLOCK")
    if not categories and not strict:
        categories.append("NO_STRICT_SUPPORTED_IMPROVEMENT")
    classification = categories[0] if len(categories) == 1 else "MULTIPLE_BLOCKERS"
    return {
        "strict_channels": strict,
        "production_strict_channels": production_strict,
        "worse_channels": worse,
        "unknown_channels": unknown,
        "one_sided_not_applicable_channels": one_sided,
        "channel_details": details if include_details else None,
        "blocker_categories": categories,
        "classification": classification,
        "production_first_blocker": first_production,
        "production_passed": first_production["reason"] == "supported_no_worse_everywhere_and_strictly_better",
    }


def merge_counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def percent(numerator: int, denominator: int) -> float:
    return round((100.0 * numerator / denominator) if denominator else 0.0, 6)


def retained_decisions(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    trace_info: dict[str, Any] = {}
    for label in ("DIAGNOSTIC_A", "DIAGNOSTIC_B"):
        path = root / label / f"{label}.decision-trace.jsonl"
        trace_hash = sha256(path)
        rows = 0
        qualifying = 0
        with path.open() as handle:
            for row_number, line in enumerate(handle, start=1):
                rows += 1
                row = json.loads(line)
                competition = row.get("distributed_competition") or {}
                if competition.get("admissible_candidate_count", 0) <= 1:
                    continue
                if row.get("critical_recovery_context", {}).get("active_recovery_needs"):
                    continue
                qualifying += 1
                decisions.append({
                    "diagnostic": label,
                    "trace_path": str(path),
                    "trace_sha256": trace_hash,
                    "line": row_number,
                    "tick": row["tick"],
                    "active_tick": row["active_ticks"],
                    "trace_row_hash": row.get("trace_row_hash"),
                    "selected_identity": competition["selected_identity"],
                    "stochastic_only_full_pool_shadow_winner": competition["stochastic_only_full_pool_shadow_winner"],
                    "views": competition["views"],
                    "production_attempts": competition["attempts"],
                    "production_summary": {
                        key: competition[key]
                        for key in (
                            "admissible_candidate_count", "applicable_channel_count",
                            "pairwise_dominance_count", "eliminated_candidate_count",
                            "frontier_size", "frontier_equals_full_pool",
                            "frontier_full_pool_ratio", "stochastic_resolution_required",
                            "distributed_changed_winner", "frontier_identities",
                            "dominated_identities",
                        )
                    },
                })
        trace_info[label] = {
            "path": str(path), "sha256": trace_hash, "row_count": rows,
            "qualifying_decision_count": qualifying,
        }
    return decisions, trace_info


def all_pairs(decision: dict[str, Any]) -> list[dict[str, Any]]:
    by_identity = {view["identity"]: view for view in decision["views"]}
    retained_attempts = {
        (attempt["dominator"], attempt["target"]): attempt
        for attempt in decision["production_attempts"]
    }
    pairs = []
    for a_id in sorted(by_identity):
        for b_id in sorted(by_identity):
            if a_id == b_id:
                continue
            explanation = channel_pairs(by_identity[a_id], by_identity[b_id])
            retained = retained_attempts[(a_id, b_id)]
            retained_shape = {
                "passed": retained["passed"],
                "reason": retained["reason"],
                "strict_channels": retained["strict_channels"],
                "blocking_channels": retained["blocking_channels"],
            }
            reconstructed_shape = {
                "passed": explanation["production_passed"],
                "reason": explanation["production_first_blocker"]["reason"],
                "strict_channels": explanation["production_strict_channels"],
                "blocking_channels": (
                    [explanation["production_first_blocker"]["channel"]]
                    if explanation["production_first_blocker"]["reason"] == "worse_in_supported_channel"
                    else explanation["production_first_blocker"].get("channels", [])
                ),
            }
            pairs.append({
                "dominator": a_id,
                "target": b_id,
                "retained_production_attempt": retained_shape,
                "reconstructed_production_attempt": reconstructed_shape,
                "reconstruction_matches_retained": retained_shape == reconstructed_shape,
                **explanation,
            })
    return pairs


def projected_relations(decisions: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    pair_count = pass_count = decision_with_pass = 0
    for decision in decisions:
        views = decision["views"]
        all_keys = sorted({key for view in views for key in view["channels"]})
        include: list[str] | None = None
        ignore_unknown = ignore_one_sided = False
        if mode == "physiology_only":
            include = [key for key in all_keys if family(key) == "physiology"]
        elif mode == "universally_shared_supported_only":
            include = [
                key for key in all_keys
                if all(evidence(view, key)["status"] == SUPPORTED for view in views)
            ]
        elif mode.startswith("remove_"):
            removed = mode.removeprefix("remove_")
            include = [key for key in all_keys if family(key) != removed]
        elif mode == "exclude_unknown_analysis_only":
            ignore_unknown = True
        elif mode == "isolate_one_sided_applicability":
            include = [
                key for key in all_keys
                if any(evidence(view, key)["status"] == NOT_APPLICABLE for view in views)
                and any(evidence(view, key)["status"] != NOT_APPLICABLE for view in views)
            ]
            ignore_unknown = True
        seen_pass = False
        for a in views:
            for b in views:
                if a["identity"] == b["identity"]:
                    continue
                pair_count += 1
                explanation = channel_pairs(a, b, include=include, ignore_unknown=ignore_unknown, ignore_one_sided=ignore_one_sided)
                if explanation["production_passed"]:
                    pass_count += 1
                    seen_pass = True
        decision_with_pass += int(seen_pass)
    return {
        "mode": mode,
        "analysis_only_not_replacement_rule": True,
        "ordered_pair_count": pair_count,
        "supported_dominance_relations_under_projection": pass_count,
        "decisions_with_at_least_one_relation_under_projection": decision_with_pass,
        "relation_rate_percent": percent(pass_count, pair_count),
        "decision_rate_percent": percent(decision_with_pass, len(decisions)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--start-commit", required=True)
    args = parser.parse_args()
    decisions, trace_info = retained_decisions(args.source_root)
    if len(decisions) != 2647:
        raise RuntimeError(f"unexpected_qualifying_decision_count:{len(decisions)}")

    all_pair_records: list[dict[str, Any]] = []
    blocker_class_counts: Counter[str] = Counter()
    blocker_channel_counts: Counter[str] = Counter()
    blocker_family_counts: Counter[str] = Counter()
    first_reason_counts: Counter[str] = Counter()
    first_family_counts: Counter[str] = Counter()
    taxonomy_flags: Counter[str] = Counter()
    taxonomy_exclusive: Counter[str] = Counter()
    homeostatic = Counter()
    decision_stochastic_causes = Counter()
    channel_rows: dict[str, Counter[str]] = defaultdict(Counter)
    channel_pair_rows: dict[str, Counter[str]] = defaultdict(Counter)
    family_rows: dict[str, Counter[str]] = defaultdict(Counter)
    reconstruction_mismatches: list[dict[str, Any]] = []

    dataset_rows = []
    for decision_number, decision in enumerate(decisions, start=1):
        views = decision["views"]
        dataset_rows.append({
            key: decision[key] for key in (
                "diagnostic", "trace_path", "trace_sha256", "line", "tick", "active_tick",
                "trace_row_hash", "selected_identity", "stochastic_only_full_pool_shadow_winner",
                "production_summary",
            )
        })
        dataset_rows[-1]["candidate_identities"] = [view["identity"] for view in decision["views"]]
        dataset_rows[-1]["candidate_view_sha256"] = hashlib.sha256(
            json.dumps(decision["views"], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        dataset_rows[-1]["full_views_retained_at_trace_locator"] = {
            "path": decision["trace_path"], "line": decision["line"], "trace_row_hash": decision["trace_row_hash"],
        }
        all_keys = sorted({key for view in views for key in view["channels"]})
        for key in all_keys:
            fam = family(key)
            family_rows[fam]["channel_occurrences"] += 1
            for view in views:
                status = evidence(view, key)["status"]
                channel_rows[key]["candidates_total"] += 1
                channel_rows[key][f"status_{status}"] += 1
                family_rows[fam]["candidates_total"] += 1
                family_rows[fam][f"status_{status}"] += 1
        pairs = all_pairs(decision)
        flags = {"epistemic": False, "semantic": False, "motivational": False}
        for pair in pairs:
            pair["decision_number"] = decision_number
            pair["diagnostic"] = decision["diagnostic"]
            pair["tick"] = decision["tick"]
            pair["active_tick"] = decision["active_tick"]
            all_pair_records.append(pair)
            blocker_class_counts[pair["classification"]] += 1
            for channel in pair["worse_channels"] + pair["unknown_channels"] + pair["one_sided_not_applicable_channels"]:
                blocker_channel_counts[channel] += 1
                blocker_family_counts[family(channel)] += 1
            first = pair["production_first_blocker"]
            first_reason_counts[first["reason"]] += 1
            if "channel" in first:
                first_family_counts[family(first["channel"])] += 1
            elif first.get("channels"):
                first_family_counts[family(first["channels"][0])] += 1
            if pair["unknown_channels"]:
                flags["epistemic"] = True
            if pair["one_sided_not_applicable_channels"]:
                flags["semantic"] = True
            if pair["worse_channels"] and pair["strict_channels"]:
                flags["motivational"] = True
            if not pair["reconstruction_matches_retained"]:
                reconstruction_mismatches.append({
                    "decision_number": decision_number, "dominator": pair["dominator"], "target": pair["target"],
                    "retained": pair["retained_production_attempt"], "reconstructed": pair["reconstructed_production_attempt"],
                })
        enabled = [name for name, enabled in flags.items() if enabled]
        for name in enabled:
            taxonomy_flags[name] += 1
        taxonomy_exclusive["+".join(enabled) if enabled else "none"] += 1
        if decision["production_summary"]["stochastic_resolution_required"]:
            decision_stochastic_causes["stochastic_resolution_required"] += 1
            for name in enabled:
                decision_stochastic_causes[f"co_present_{name}"] += 1
        for index, a in enumerate(views):
            for b in views[index + 1:]:
                phys_keys = [key for key in set(a["channels"]) | set(b["channels"]) if family(key) == "physiology"]
                directions = []
                for key in phys_keys:
                    ao = evidence(a, key).get("order")
                    bo = evidence(b, key).get("order")
                    if ao is None or bo is None:
                        continue
                    directions.append((key, float(ao) - float(bo)))
                better = [key for key, delta in directions if delta > 0]
                worse = [key for key, delta in directions if delta < 0]
                homeostatic["unordered_pairs"] += 1
                if better and worse:
                    homeostatic["genuine_physiology_tradeoff_pairs"] += 1
                if not worse and better:
                    homeostatic["a_physiology_no_worse_strict_better"] += 1
                if not better and worse:
                    homeostatic["b_physiology_no_worse_strict_better"] += 1
                if not better and not worse:
                    homeostatic["physiology_equal_pairs"] += 1
        for a in views:
            for b in views:
                if a["identity"] == b["identity"]:
                    continue
                for key in all_keys:
                    av, bv = evidence(a, key), evidence(b, key)
                    fam = family(key)
                    channel_pair_rows[key]["ordered_pairs_total"] += 1
                    family_rows[fam]["ordered_pairs_total"] += 1
                    if av["status"] == SUPPORTED and bv["status"] == SUPPORTED:
                        channel_pair_rows[key]["shared_supported_pairs"] += 1
                        family_rows[fam]["shared_supported_pairs"] += 1
                        if av["order"] != bv["order"]:
                            channel_pair_rows[key]["discriminatory_pairs"] += 1
                            family_rows[fam]["discriminatory_pairs"] += 1
                            if float(av["order"]) > float(bv["order"]):
                                channel_pair_rows[key]["strict_better_occurrences"] += 1
                                family_rows[fam]["strict_better_occurrences"] += 1
                            else:
                                channel_pair_rows[key]["strict_worse_occurrences"] += 1
                                family_rows[fam]["strict_worse_occurrences"] += 1
                    if (av["status"] == NOT_APPLICABLE) != (bv["status"] == NOT_APPLICABLE):
                        channel_pair_rows[key]["one_sided_applicability_pairs"] += 1
                        family_rows[fam]["one_sided_applicability_pairs"] += 1

    if reconstruction_mismatches:
        raise RuntimeError(f"production_attempt_reconstruction_mismatch:{len(reconstruction_mismatches)}")
    total_pairs = len(all_pair_records)
    channel_coverage = {}
    for key in sorted(channel_rows):
        counts = channel_rows[key]
        pair_counts = channel_pair_rows[key]
        channel_coverage[key] = {
            "family": family(key),
            "candidate_occurrences": counts["candidates_total"],
            "supported_count": counts[f"status_{SUPPORTED}"],
            "unknown_count": counts[f"status_{UNKNOWN}"],
            "not_applicable_count": counts[f"status_{NOT_APPLICABLE}"],
            "supported_rate_percent": percent(counts[f"status_{SUPPORTED}"], counts["candidates_total"]),
            "unknown_rate_percent": percent(counts[f"status_{UNKNOWN}"], counts["candidates_total"]),
            "not_applicable_rate_percent": percent(counts[f"status_{NOT_APPLICABLE}"], counts["candidates_total"]),
            "pairwise_shared_support_rate_percent": percent(pair_counts["shared_supported_pairs"], pair_counts["ordered_pairs_total"]),
            "one_sided_applicability_rate_percent": percent(pair_counts["one_sided_applicability_pairs"], pair_counts["ordered_pairs_total"]),
            "discriminatory_rate_percent": percent(pair_counts["discriminatory_pairs"], pair_counts["ordered_pairs_total"]),
            "strict_better_occurrences": pair_counts["strict_better_occurrences"],
            "strict_worse_occurrences": pair_counts["strict_worse_occurrences"],
        }
    family_coverage = {}
    for fam in sorted(family_rows):
        counts = family_rows[fam]
        family_coverage[fam] = {
            "channel_occurrences": counts["channel_occurrences"],
            "candidate_occurrences": counts["candidates_total"],
            "supported_rate_percent": percent(counts[f"status_{SUPPORTED}"], counts["candidates_total"]),
            "unknown_rate_percent": percent(counts[f"status_{UNKNOWN}"], counts["candidates_total"]),
            "not_applicable_rate_percent": percent(counts[f"status_{NOT_APPLICABLE}"], counts["candidates_total"]),
            "pairwise_shared_support_rate_percent": percent(counts["shared_supported_pairs"], counts["ordered_pairs_total"]),
            "one_sided_applicability_rate_percent": percent(counts["one_sided_applicability_pairs"], counts["ordered_pairs_total"]),
            "discriminatory_rate_percent": percent(counts["discriminatory_pairs"], counts["ordered_pairs_total"]),
            "strict_better_occurrences": counts["strict_better_occurrences"],
            "strict_worse_occurrences": counts["strict_worse_occurrences"],
        }

    source_hashes = {label: info["sha256"] for label, info in trace_info.items()}
    common = {
        "schema": "AS003D_OFFLINE_FROZEN_TRACE_ANALYSIS_V1",
        "generated_at": utc_now(),
        "start_commit": args.start_commit,
        "source_trace_info": trace_info,
        "qualifying_decision_count": len(decisions),
        "ordered_pair_count": total_pairs,
        "organism_runs": 0,
        "diagnostic_reruns": 0,
        "production_changes": 0,
        "source_trace_sha256": source_hashes,
    }
    outputs = {
        "AS003D_FROZEN_COMPETITION_DATASET_INDEX.json": {
            **common,
            "recovery_method": "retained JSONL read only; every row includes frozen views, selected identity, and trace locator",
            "decisions": dataset_rows,
        },
        "AS003D_PAIRWISE_BLOCKER_DECOMPOSITION.json": {
            **common,
            "production_attempt_reconstruction": "PASS",
            "reconstruction_mismatch_count": 0,
            "blocker_class_counts": merge_counter_dict(blocker_class_counts),
            "blocker_class_rates_percent": {key: percent(value, total_pairs) for key, value in sorted(blocker_class_counts.items())},
            "blocker_channel_counts": merge_counter_dict(blocker_channel_counts),
            "blocker_family_counts": merge_counter_dict(blocker_family_counts),
            "production_first_reason_counts": merge_counter_dict(first_reason_counts),
            "production_first_family_counts": merge_counter_dict(first_family_counts),
            "ordered_pair_explanations": all_pair_records,
        },
        "AS003D_CHANNEL_COVERAGE_ANALYSIS.json": {
            **common,
            "channel_families": family_coverage,
            "channels": channel_coverage,
            "learned_model_reaches_comparison": {
                "SelfModel": family_coverage.get("SelfModel", {}),
                "WorldModel": family_coverage.get("WorldModel", {}),
                "interpretation_boundary": "counts show reachability/support only; they do not establish forward selection influence under saturated V1",
            },
        },
        "AS003D_HOMEOSTATIC_TRADEOFF_ANALYSIS.json": {
            **common,
            "homeostatic_pair_counts": merge_counter_dict(homeostatic),
            "rates_percent": {key: percent(value, homeostatic["unordered_pairs"]) for key, value in sorted(homeostatic.items()) if key != "unordered_pairs"},
            "method": "compares each independent retained physiology channel without arithmetic aggregation",
        },
        "AS003D_INCOMPARABILITY_TAXONOMY.json": {
            **common,
            "definitions": {
                "epistemic": "at least one UNKNOWN/non-supported non-NOT_APPLICABLE retained channel blocks an ordered relation",
                "semantic": "at least one channel is NOT_APPLICABLE for exactly one candidate",
                "motivational": "the proposed dominator is strictly better in at least one supported channel and worse in another",
            },
            "decision_counts_with_flag": merge_counter_dict(taxonomy_flags),
            "decision_rates_percent_with_flag": {key: percent(value, len(decisions)) for key, value in sorted(taxonomy_flags.items())},
            "decision_exclusive_combinations": merge_counter_dict(taxonomy_exclusive),
            "note": "flags may co-occur within a decision because different candidate pairs can be blocked for different reasons",
        },
        "AS003D_CAUSAL_ABLATION_MATRIX.json": {
            **common,
            "analysis_only": True,
            "projections": [
                projected_relations(decisions, mode)
                for mode in (
                    "physiology_only", "universally_shared_supported_only", "remove_SelfModel",
                    "remove_WorldModel", "remove_temporal", "remove_individuality",
                    "remove_continuity/context", "remove_option/recoverability",
                    "exclude_unknown_analysis_only", "isolate_one_sided_applicability",
                )
            ],
        },
        "AS003D_STOCHASTIC_RESOLUTION_AUDIT.json": {
            **common,
            "stochastic_resolution_decision_count": decision_stochastic_causes["stochastic_resolution_required"],
            "stochastic_resolution_rate_percent": percent(decision_stochastic_causes["stochastic_resolution_required"], len(decisions)),
            "co_present_incomparability_flags": merge_counter_dict(decision_stochastic_causes),
            "distributed_changed_winner_count": sum(int(d["production_summary"]["distributed_changed_winner"]) for d in decisions),
            "interpretation_boundary": "the audit reports retained causes of an unresolved frontier; it does not infer a replacement rule from candidate-local stochasticity",
        },
    }
    for name, payload in outputs.items():
        durable_json(args.evidence_root / name, payload)
    manifest = {
        "schema": "AS003D_INTERIM_DERIVATIVE_EVIDENCE_MANIFEST_V1",
        "generated_at": utc_now(),
        "source_trace_sha256": source_hashes,
        "files": {name: sha256(args.evidence_root / name) for name in sorted(outputs)},
        "readback_sha256_verified": True,
        "durability": "atomic rename + file fsync + directory fsync",
    }
    durable_json(args.evidence_root / "AS003D_INTERIM_DERIVATIVE_EVIDENCE_MANIFEST.json", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
