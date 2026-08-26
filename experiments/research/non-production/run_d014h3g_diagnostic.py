#!/usr/bin/env python3
"""D-014H3G bounded reproduction of the H3F unsafe-selector stop."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
NONPROD = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(NONPROD) not in sys.path:
    sys.path.insert(0, str(NONPROD))

from d014h3d_selector import evaluate, fingerprint
from d014h3f_runtime import h3f_selector_callback, prepare_organism
from umbra_core.arbitration import Candidate
from umbra_core.governance import authority_effect_branches

SEED = 41241905
SCENARIO = "S0"
MAX_TICKS = 7200
EVIDENCE_ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3g-candidate-safety-selector-r1")
OUTPUT = EVIDENCE_ROOT / "D014H3G_H3F_DIAGNOSTIC_REPRODUCTION.json"
SCRATCH = Path("/dev/shm/d014h3g-h3f-diagnostic")
TRACE = SCRATCH / "decision.jsonl"
DB = SCRATCH / "organism.sqlite"

_ACTIVE_ORG: Any | None = None


def _cleanup() -> None:
    for path in (DB, Path(str(DB) + "-wal"), Path(str(DB) + "-shm"), TRACE):
        path.unlink(missing_ok=True)


def _write(value: object) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def _candidate_key(capability: str, params: dict[str, Any]) -> str:
    return fingerprint({"capability": capability, "params": params})


def _candidate_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "capability": str(row.get("capability")),
        "params": copy.deepcopy(row.get("params") or {}),
        "candidate_key": _candidate_key(str(row.get("capability")), dict(row.get("params") or {})),
        "source_name": row.get("source_name"),
        "source": row.get("source"),
        "candidate_before": copy.deepcopy(row.get("candidate_before")),
        "candidate_emitted": copy.deepcopy(row.get("candidate_emitted")),
        "candidate_after": copy.deepcopy(row.get("candidate_after")),
        "changed": row.get("changed"),
        "reason": row.get("reason"),
    }


def diagnostic_selector(context: dict[str, Any]) -> dict[str, Any]:
    org = _ACTIVE_ORG
    if org is None:
        raise RuntimeError("d014h3g_missing_active_organism")

    runtime_module = __import__("d014h3f_runtime")
    state = runtime_module.selector_input(context)
    selector_result = evaluate(state)
    selected = selector_result.get("selected")

    actual_pool = [
        _candidate_row(row)
        for row in context.get("candidate_pool", [])
        if isinstance(row, dict) and row.get("capability")
    ]
    exact = {}
    for row in actual_pool:
        candidate = Candidate(row["capability"], dict(row["params"]))
        branches = tuple(
            dict(branch)
            for branch in authority_effect_branches(
                candidate,
                org.embodiment,
                org.embodiment_adapter,
                resolve_params=org._resolve_params,
            )
        )
        exact[row["candidate_key"]] = {
            "candidate": row,
            "authority_effect_branches_exact": list(branches),
            "immediate_authority_safe": not org.arbitrator._introduces_critical_boundary(
                candidate, org.phys, effect_branches=branches
            ),
        }

    selected_row = copy.deepcopy(selected) if isinstance(selected, dict) else None
    selected_key = (
        _candidate_key(str(selected_row["capability"]), dict(selected_row.get("params") or {}))
        if selected_row else None
    )
    selected_exact = exact.get(selected_key) if selected_key else None
    capability_branches = context.get("effect_branches", {})
    capability_selected = (
        capability_branches.get(str(selected_row["capability"]), [])
        if selected_row else []
    )
    capability_safe = (
        not org.arbitrator._introduces_critical_boundary(
            Candidate(str(selected_row["capability"]), dict(selected_row.get("params") or {})),
            org.phys,
            effect_branches=tuple(dict(branch) for branch in capability_selected),
        )
        if selected_row else None
    )

    if selected_exact and selected_exact["immediate_authority_safe"] is False:
        envelope = {
            "directive": "UMBRA-D-014H3G",
            "diagnostic_kind": "H3F_EXCEPTION_REPRODUCTION",
            "baseline": "2be05c7f661abb1c4d8505eb932d74eadc30114b",
            "seed": SEED,
            "scenario": SCENARIO,
            "tick": org.tick,
            "organism_age": context.get("organism_age"),
            "active_ticks": context.get("active_ticks"),
            "physiology": copy.deepcopy(context.get("physiology")),
            "current_serial_candidate": copy.deepcopy(context.get("current_candidate")),
            "actual_proposal_pool": actual_pool,
            "candidate_transitions": copy.deepcopy(context.get("candidate_transitions")),
            "h3f_capability_keyed_effect_branches": copy.deepcopy(capability_branches),
            "exact_candidate_specific_authority": exact,
            "prospective_selector_input": state,
            "prospective_selector_result": selector_result,
            "route_envelope_by_candidate": {
                str(item.get("candidate_key")): copy.deepcopy(item.get("route"))
                for item in selector_result.get("annotated_candidates", [])
            },
            "ordinary_evidence_by_candidate": {
                str(item.get("candidate_key")): copy.deepcopy(item.get("ordinary_evidence"))
                for item in selector_result.get("annotated_candidates", [])
            },
            "selected_candidate": selected_row,
            "selected_candidate_feasibility": selected_row.get("feasibility") if selected_row else None,
            "selected_candidate_capability_keyed_branch_input": capability_selected,
            "selected_candidate_exact_authority_branch": selected_exact,
            "selected_candidate_capability_keyed_immediate_safe": capability_safe,
            "selected_candidate_exact_immediate_safe": selected_exact["immediate_authority_safe"],
            "authoritative_introduces_critical_boundary": True,
            "final_safety_transition_lineage": {
                "h3f_post_selection_assertion": "d014h3d_selector_selected_unsafe_candidate",
                "runtime_action": "raise_before_governance",
            },
            "root_cause_candidates": {
                "candidate_effect_branch_key_collision": capability_selected != selected_exact["authority_effect_branches_exact"],
                "known_hard_constraint_not_applied_preselection": selected_exact["immediate_authority_safe"] is False,
                "prospective_unknown_selected_but_authority_known_unsafe": (
                    selected_row is not None and selected_row.get("feasibility") == "UNKNOWN"
                ),
                "body_capability_constraint_mismatch": False,
            },
            "hidden_truth_used": False,
            "selector_behavior_changed": False,
        }
        _write(envelope)

    return h3f_selector_callback(context)


def main() -> int:
    _cleanup()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    org = None
    global _ACTIVE_ORG
    try:
        org = prepare_organism(DB, SEED, diagnostic_selector, TRACE, SCENARIO)
        _ACTIVE_ORG = org
        for _ in range(MAX_TICKS):
            org.tick_once()
        result = {
            "directive": "UMBRA-D-014H3G",
            "verdict": "D014H3G_DIAGNOSTIC_EXCEPTION_NOT_REPRODUCED",
            "seed": SEED,
            "ticks": org.tick,
            "exception": None,
            "diagnostic_artifact": str(OUTPUT),
        }
        _write(result)
        return 0
    except Exception as exc:
        result = {
            "directive": "UMBRA-D-014H3G",
            "verdict": "D014H3G_DIAGNOSTIC_EXCEPTION_REPRODUCED",
            "seed": SEED,
            "ticks": getattr(org, "tick", None),
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "diagnostic_artifact": str(OUTPUT),
        }
        if not OUTPUT.exists():
            _write(result)
        else:
            envelope = json.loads(OUTPUT.read_text())
            envelope["terminal_exception"] = result
            _write(envelope)
        return 1
    finally:
        if org is not None:
            org.close()
        _ACTIVE_ORG = None
        _cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
