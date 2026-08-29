#!/usr/bin/env python3
"""Retained policy-trace analysis for UMBRA-CLOSE-02X-ATTRIB."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Callable


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def first_difference(
    x_rows: list[dict[str, Any]],
    u_rows: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any], dict[str, Any]], bool],
) -> int | None:
    for x_row, u_row in zip(x_rows, u_rows):
        if predicate(x_row, u_row):
            return int(x_row["tick"])
    return None


def analyze(x_trace: Path, u_trace: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    x_rows = rows(x_trace)
    u_rows = rows(u_trace)
    statuses: dict[str, list[int]] = defaultdict(list)
    event_status_counts: Counter[str] = Counter()
    nonrealization: Counter[str] = Counter()
    nonrealization_ticks: dict[str, list[int]] = defaultdict(list)
    not_evaluated: Counter[str] = Counter()
    not_evaluated_ticks: dict[str, list[int]] = defaultdict(list)
    fatigue_evaluated_ticks: list[int] = []
    rest_route_ticks: list[int] = []
    energy_constraints: list[dict[str, Any]] = []

    for row in x_rows:
        tick = int(row["tick"])
        fatigue_transitions: list[dict[str, Any]] = []
        for event in row.get("prospective_recoverability") or []:
            if event.get("constrained") and "energy" in event.get("constrained_dimensions", []):
                energy_transition = next(
                    transition for transition in event["transitions"]
                    if transition["dimension"] == "energy"
                )
                energy_constraints.append({
                    "tick": tick,
                    "constrained_candidate": event["candidate"],
                    "current_status": energy_transition["current_status"],
                    "projected_status": energy_transition["projected_status"],
                    "current_routes": energy_transition["current_routes"],
                    "projected_routes": energy_transition["projected_routes"],
                    "x_selected": row.get("final_candidate"),
                })
            for transition in event.get("transitions", []):
                if transition.get("dimension") == "fatigue":
                    fatigue_transitions.append(transition)
        if fatigue_transitions:
            fatigue_evaluated_ticks.append(tick)
            current_status = str(fatigue_transitions[0]["current_status"])
            assert all(str(item["current_status"]) == current_status for item in fatigue_transitions)
            statuses[current_status].append(tick)
            if any(
                route.get("opportunity") == "rest"
                for route in fatigue_transitions[0].get("current_routes", [])
            ):
                rest_route_ticks.append(tick)
            for transition in fatigue_transitions:
                status = str(transition["current_status"])
                projected = str(transition["projected_status"])
                event_status_counts[status] += 1
                if transition.get("constrained"):
                    reason = "CONSTRAINED"
                elif status == "SUPPORTED_MARGIN_EXHAUSTED":
                    reason = "CURRENT_ALREADY_EXHAUSTED"
                elif status.startswith("UNKNOWN"):
                    reason = f"CURRENT_{status}"
                elif status == "NO_KNOWN_RECOVERY_ROUTE":
                    reason = status
                elif projected.startswith("UNKNOWN"):
                    reason = f"PROJECTED_{projected}"
                elif status == projected == "SUPPORTED_MARGIN_POSITIVE":
                    reason = "POSITIVE_REMAINS_POSITIVE"
                else:
                    reason = f"{status}_TO_{projected}"
                nonrealization[reason] += 1
                nonrealization_ticks[reason].append(tick)
        else:
            context = row.get("critical_recovery_context") or {}
            active = tuple(context.get("active_recovery_needs") or [])
            fatigue = float(row["physiology"]["fatigue"])
            if active:
                reason = "ACTIVE_RECOVERY_BRANCH:" + ",".join(active)
            elif context.get("critical_vars"):
                reason = "CRITICAL_BRANCH"
            elif fatigue <= 0.2:
                reason = "FATIGUE_NOT_ABOVE_IDEAL"
            else:
                reason = "NO_PROSPECTIVE_EVENTS_OTHER"
            not_evaluated[reason] += 1
            not_evaluated_ticks[reason].append(tick)

    active_fatigue = [
        int(row["tick"]) for row in x_rows
        if "fatigue" in ((row.get("critical_recovery_context") or {}).get("active_recovery_needs") or [])
    ]
    constrained_ticks = [item["tick"] for item in energy_constraints]
    for item in energy_constraints:
        u_row = u_rows[item["tick"] - 1]
        item["u_selected"] = u_row.get("selected_candidate")
        item["u_scored_candidate_count"] = len(u_row.get("scored_candidates") or [])
        x_row = x_rows[item["tick"] - 1]
        item["x_prefilter_candidate_count"] = len(x_row.get("prospective_recoverability") or [])
        item["x_postfilter_candidate_count"] = (
            item["x_prefilter_candidate_count"]
            - sum(1 for event in x_row.get("prospective_recoverability") or [] if event.get("constrained"))
        )
        item["x_outcome"] = x_row.get("verified_outcome_linkage")
        item["u_outcome"] = (u_row.get("result") or {}).get("outcome")

    def range_rows(mapping: dict[str, list[int]], counts: Counter[str]) -> dict[str, Any]:
        return {
            key: {
                "count": int(counts[key]),
                "first_tick": min(ticks),
                "last_tick": max(ticks),
            }
            for key, ticks in sorted(mapping.items())
        }

    lifecycle = {
        "directive": "UMBRA-CLOSE-02X-ATTRIB",
        "seed": 57531938,
        "regime": "R1/S16",
        "trace_rows": len(x_rows),
        "first_preventive_attention_tick": 1,
        "first_policy_visible_rest_route_tick": min(rest_route_ticks),
        "first_supported_positive_tick": None,
        "last_supported_positive_tick": None,
        "first_supported_exhausted_tick": min(statuses["SUPPORTED_MARGIN_EXHAUSTED"]),
        "first_active_fatigue_recovery_tick": min(active_fatigue),
    "first_tick_without_supported_positive_fatigue_route": 1,
        "first_no_safe_action_tick": 923,
        "critical_fatigue_tick": 924,
        "fatigue_status_by_tick_count": {
            key: len(value) for key, value in sorted(statuses.items())
        },
        "fatigue_status_ranges": {
            key: {"first_tick": min(value), "last_tick": max(value), "ticks": len(value)}
            for key, value in sorted(statuses.items())
        },
        "finding": "Fatigue was prospectively attended from tick 1 but never had SUPPORTED_MARGIN_POSITIVE. Geometry/capability support was UNKNOWN first; when fully supported at tick 124, the route was already exhausted.",
    }
    write(output / "CLOSE02XATTRIB_FATIGUE_LIFECYCLE.json", lifecycle)

    write(output / "CLOSE02XATTRIB_NONREALIZATION.json", {
        "directive": "UMBRA-CLOSE-02X-ATTRIB",
        "fatigue_candidate_evaluations": sum(nonrealization.values()),
        "candidate_nonrealization_reasons": range_rows(nonrealization_ticks, nonrealization),
        "ticks_without_fatigue_evaluation": range_rows(not_evaluated_ticks, not_evaluated),
        "fatigue_constraints_realized": 0,
    })

    write(output / "CLOSE02XATTRIB_PASSIVE_HORIZON.json", {
        "directive": "UMBRA-CLOSE-02X-ATTRIB",
        "classification": "SUPPORTED_POSITIVE_BASELINE_NEVER_ESTABLISHED",
        "candidate_induced_positive_to_exhausted": 0,
        "passive_positive_to_exhausted": 0,
        "first_supported_state": {
            "tick": min(statuses["SUPPORTED_MARGIN_EXHAUSTED"]),
            "status": "SUPPORTED_MARGIN_EXHAUSTED",
        },
        "finding": "A passive positive-to-exhausted transition cannot be established because fatigue never had a supported-positive route. The evidence instead establishes support unavailable until the route was already exhausted.",
    })

    candidate_params_divergence = first_difference(
        x_rows, u_rows,
        lambda x, u: (x.get("final_candidate") or {}).get("params")
        != (u.get("selected_candidate") or {}).get("params"),
    )
    capability_divergence = first_difference(
        x_rows, u_rows,
        lambda x, u: (x.get("final_candidate") or {}).get("capability")
        != u.get("selected_action"),
    )
    physiology_divergence = first_difference(
        x_rows, u_rows,
        lambda x, u: x.get("physiology") != u.get("physiology_after_drift"),
    )
    outcome_divergence = first_difference(
        x_rows, u_rows,
        lambda x, u: (
            (x.get("verified_outcome_linkage") or {}).get("success"),
            (x.get("verified_outcome_linkage") or {}).get("reason"),
        ) != (
            ((u.get("result") or {}).get("outcome") or {}).get("success"),
            ((u.get("result") or {}).get("outcome") or {}).get("reason"),
        ),
    )

    def interval_metrics(source: list[dict[str, Any]], x_format: bool) -> dict[str, Any]:
        actions: Counter[str] = Counter()
        rest: Counter[str] = Counter()
        fatigue_effect = 0.0
        for row in source[568:924]:
            if x_format:
                capability = (row.get("final_candidate") or {}).get("capability")
                outcome = row.get("verified_outcome_linkage") or {}
            else:
                capability = row.get("selected_action")
                outcome = (row.get("result") or {}).get("outcome") or {}
            actions[str(capability)] += 1
            if outcome.get("capability") == "REST":
                rest["success" if outcome.get("success") else "failure"] += 1
            fatigue_effect += float((outcome.get("effects") or {}).get("fatigue", 0.0))
        return {
            "actions": dict(actions),
            "rest_successes": rest["success"],
            "rest_failures": rest["failure"],
            "cumulative_verified_fatigue_effect": fatigue_effect,
        }

    write(output / "CLOSE02XATTRIB_ENERGY_CROSS_DIMENSION.json", {
        "directive": "UMBRA-CLOSE-02X-ATTRIB",
        "energy_constraint_ticks": constrained_ticks,
        "constraints": energy_constraints,
        "causal_chain": {
            "first_energy_filter_tick": min(constrained_ticks),
            "tick_569_u_scored_candidates": energy_constraints[0]["u_scored_candidate_count"],
            "tick_569_x_postfilter_candidates": energy_constraints[0]["x_postfilter_candidate_count"],
            "stochastic_draw_rule": "one rng.gauss draw per post-filter scored candidate",
            "first_candidate_parameter_divergence": candidate_params_divergence,
            "first_outcome_divergence": outcome_divergence,
            "first_physiology_divergence": physiology_divergence,
            "first_capability_divergence": capability_divergence,
        },
        "matched_interval_569_924": {
            "x": interval_metrics(x_rows, True),
            "u": interval_metrics(u_rows, False),
            "x_fatigue_at_tick_924_before_outcome": x_rows[923]["physiology"]["fatigue"],
            "u_fatigue_at_tick_924_before_outcome": u_rows[923]["physiology_after_drift"]["fatigue"],
        },
        "classification": "SUPPORTED_CROSS_DIMENSION_LIVENESS_REGRESSION",
        "claim_boundary": "The causal chain establishes that the energy filter changed the deterministic stochastic/action trajectory and preceded materially worse fatigue regulation. It does not claim a particular unexecuted action would have rescued X.",
    })

    write(output / "CLOSE02XATTRIB_AUTHORITY_DISTINCTION.json", {
        "directive": "UMBRA-CLOSE-02X-ATTRIB",
        "x_mechanism": "NEGATIVE_OPTION_PRESERVATION_ONLY",
        "x_can_remove_candidate": True,
        "x_can_generate_candidate": False,
        "x_can_prefer_margin_improving_candidate": False,
        "existing_close02t_preventive_lane": "Existing vector urgency can admit and score already-generated regulatory actions before active recovery.",
        "missing_prospective_primitive": "No existing path lets the recoverability view positively preserve or improve a threatened route; it only vetoes a demonstrated destructive candidate.",
    })

    write(output / "CLOSE02XATTRIB_VERDICT.json", {
        "directive": "UMBRA-CLOSE-02X-ATTRIB",
        "status": "TERMINAL",
        "primary_verdict": "CLOSE02XATTRIB_CROSS_DIMENSION_LIVENESS_REGRESSION",
        "secondary_finding": "CLOSE02XATTRIB_FATIGUE_SUPPORT_UNAVAILABLE",
        "primary_basis": [
            "The first energy veto removed REST before stochastic scoring at tick 569.",
            "U scored four candidates while X scored three, shifting the seeded RNG stream even though both selected the same APPROACH action that tick.",
            "Candidate parameters diverged at 574, outcome at 577, physiology at 578, and capability at 629.",
            "From ticks 569-924 X had 11 successful and 70 failed REST outcomes versus U's 20 successful and 16 failed; X reached critical fatigue while U remained noncritical.",
        ],
        "secondary_basis": "Fatigue was attended from tick 1 but never supported-positive; support became definite only as SUPPORTED_MARGIN_EXHAUSTED at tick 124.",
        "recommendation": "REJECT_X_AS_FORWARD_PRODUCTION_CANDIDATE",
        "production_changes": 0,
        "qualification_started": False,
        "next_phase_authorized": False,
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--x-trace", type=Path, required=True)
    parser.add_argument("--u-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.x_trace, args.u_trace, args.output)


if __name__ == "__main__":
    main()
