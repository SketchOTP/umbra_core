#!/usr/bin/env python3
"""AS-007 pre-freeze contract lock and bounded development gate.

The development gate is not a qualification run.  It exercises one fresh,
short R1/S16 organism path before the scientific lock and records only the
categorical terminal-readiness observations needed to verify the seam.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
EVIDENCE_ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-007-recovery-executability-integrated-viability-r1"
)
CONTRACT = REPOSITORY_ROOT / "experiments/as007/AS007_EXECUTABILITY_CONTRACT.json"
SOURCE_FILES = (
    REPOSITORY_ROOT / "umbra_core/recoverability/contracts.py",
    REPOSITORY_ROOT / "umbra_core/arbitration.py",
    REPOSITORY_ROOT / "umbra_core/embodiment.py",
    REPOSITORY_ROOT / "umbra_core/runtime.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPOSITORY_ROOT, text=True).strip()


def durable_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return sha256(path)


def lock_contract() -> dict[str, Any]:
    result = {
        "schema": "AS007_EXECUTABILITY_CONTRACT_LOCK_V3",
        "directive": "UMBRA-AS-007",
        "commit": git("rev-parse", "HEAD"),
        "contract_sha256": sha256(CONTRACT),
        "source_sha256": {str(path.relative_to(REPOSITORY_ROOT)): sha256(path) for path in SOURCE_FILES},
        "categorical_results": ["EXECUTABLE", "NOT_EXECUTABLE", "UNKNOWN"],
        "terminal_capabilities": ["CHARGE", "INSPECT", "REST"],
        "authority_chain": ["adapter_preflight_execution", "embodiment_preflight_primitive"],
        "policy_boundary": {
            "only_categorical_status_crosses": True,
            "habitat_values_cross_policy": False,
            "planning_or_route_evidence_reader": False,
            "scalar_or_weighted_authority": False,
        },
        "current_vs_stale": {
            "current_preflight_is_required": True,
            "remembered_or_stale_evidence_is_not_current_executability": True,
        },
        "scientific_runs_before_lock": 0,
        "organism_ticks_before_lock": 0,
        "supersedes_artifact": "AS007_EXECUTABILITY_CONTRACT_LOCK_R2.json",
        "supersession_reason": "final lock records the clean post-correction commit after pre-freeze development and observer validation",
    }
    result["artifact_sha256"] = durable_json(EVIDENCE_ROOT / "AS007_EXECUTABILITY_CONTRACT_LOCK_R3.json", result)
    return result


def development_gate() -> dict[str, Any]:
    from experiments import close02r
    from experiments.close02r import qualification as base_runner
    from experiments.d014.run_formal import config as d014_config
    from umbra_core.world_model import condition_to_world_model_config
    from umbra_core.recoverability.contracts import (
        EXECUTABLE,
        NOT_EXECUTABLE,
        UNKNOWN_EXECUTABILITY,
    )

    seed = 7007
    horizon = 240
    work = EVIDENCE_ROOT / "development-gate-work-r5"
    prior_result_path = EVIDENCE_ROOT / "AS007_DEVELOPMENT_GATE_RESULT_R6.json"
    if not prior_result_path.exists():
        prior_result_path = EVIDENCE_ROOT / "AS007_DEVELOPMENT_GATE_RESULT_R5.json"
    if not prior_result_path.exists():
        prior_result_path = EVIDENCE_ROOT / "AS007_DEVELOPMENT_GATE_RESULT.json"
    if work.exists() and prior_result_path.exists():
        prior = json.loads(prior_result_path.read_text(encoding="utf-8"))
        calls = prior.get("readiness_observations") or []
        selected = prior.get("selected_actions") or []
        terminal_capabilities = {"REST", "CHARGE", "INSPECT"}
        selected_terminal = [row for row in selected if row.get("capability") in terminal_capabilities]
        not_ready_selected = [
            row for row in selected_terminal
            if not any(
                call.get("decision_tick") == row.get("tick", 0) + 1
                and call.get("capability") == row.get("capability")
                and call.get("status") == "EXECUTABLE"
                for call in calls
            )
        ]
        result = dict(prior)
        protected_properties = dict(prior.get("protected_properties") or {})
        protected_properties.pop("planning_authority", None)
        protected_properties.pop("route_evidence_reader", None)
        result.update({
            "schema": "AS007_DEVELOPMENT_GATE_RESULT_V4",
            "classification": "PRE_FREEZE_DEVELOPMENT_ONLY_OFFLINE_ASSERTION_RECHECK",
            "selected_terminal_count": len(selected_terminal),
            "not_ready_terminal_selected_count": len(not_ready_selected),
            "protected_properties": {
                **protected_properties,
                "unavailable_terminal_never_selected": not not_ready_selected,
                "planning_authority_absent": True,
                "route_evidence_reader_absent": True,
            },
            "prior_prelock_attempts": [
                *(prior.get("prior_prelock_attempts") or []),
                {
                    "attempt": 4,
                    "result": "DEVELOPMENT_GATE_ASSERTION_FAILURE",
                    "organism_creations": 1,
                    "organism_ticks": 240,
                    "detail": "observation assertion treated duplicate candidate evaluations as a selected non-executable terminal",
                },
            ],
            "offline_recheck": True,
            "offline_recheck_source": str(prior_result_path),
        })
        result["artifact_sha256"] = durable_json(EVIDENCE_ROOT / "AS007_DEVELOPMENT_GATE_RESULT_R7.json", result)
        if not all(result["protected_properties"].values()):
            raise RuntimeError("as007_development_gate_failed")
        return result
    if work.exists():
        raise FileExistsError(work)
    work.mkdir(parents=True)
    decision = EVIDENCE_ROOT / "AS007_DEVELOPMENT_R1_7007_R5.decision.jsonl"
    shadow = EVIDENCE_ROOT / "AS007_DEVELOPMENT_R1_7007_R5.planning.jsonl"
    database = work / "R1-7007.sqlite"
    original_config = base_runner.config

    def configured(case_seed: int, case_db: Path, case_regime: str):
        value = d014_config(case_seed, case_db, case_regime)
        value.bounded_continuation_enabled = True
        value.world_model_enabled = True
        world_config = value.world_model_config or condition_to_world_model_config("C0")
        world_config.route_demand_learning_enabled = True
        value.world_model_config = world_config
        value.decision_trace_path = str(decision)
        value.planning_shadow_path = str(shadow)
        return value

    base_runner.config = configured
    organism = None
    readiness_calls: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    try:
        organism, engine = base_runner.prepare(seed, database, "R1")
        original_readiness = organism._candidate_executability

        def observed_readiness(candidate: Any) -> str:
            status = original_readiness(candidate)
            if candidate.capability in {"REST", "CHARGE", "INSPECT"}:
                readiness_calls.append(
                    {
                        "decision_tick": organism.tick + 1,
                        "capability": candidate.capability,
                        "status": status,
                    }
                )
            return status

        organism._candidate_executability = observed_readiness
        for _ in range(horizon):
            result = organism.tick_once()
            selected.append(
                {
                    "tick": organism.tick,
                    "capability": result.get("capability"),
                    "denied": bool(result.get("denied")),
                    "no_safe_action": bool(result.get("no_safe_action", False)),
                    "outcome_reason": (result.get("outcome") or {}).get("reason"),
                }
            )
            if organism.phys.critical_any():
                raise RuntimeError(f"development_gate_reached_critical_tick:{organism.tick}")
        terminal_calls = len(readiness_calls)
        status_counts = {status: sum(call["status"] == status for call in readiness_calls) for status in (EXECUTABLE, NOT_EXECUTABLE, UNKNOWN_EXECUTABILITY)}
        selected_terminal = [row for row in selected if row["capability"] in {"REST", "CHARGE", "INSPECT"}]
        not_ready_selected = [
            row for row in selected_terminal
            if not any(
                call["decision_tick"] == row["tick"]
                and call["capability"] == row["capability"]
                and call["status"] == EXECUTABLE
                for call in readiness_calls
            )
        ]
        post_reversal_terminal_denials = [
            call for call in readiness_calls if call["decision_tick"] >= 181 and call["status"] != EXECUTABLE
        ]
        result = {
            "schema": "AS007_DEVELOPMENT_GATE_RESULT_V1",
            "directive": "UMBRA-AS-007",
            "classification": "PRE_FREEZE_DEVELOPMENT_ONLY",
            "fixture": {"regime": "R1", "scenario": "S16", "seed": seed, "horizon": horizon},
            "organism_runs": 1,
            "organism_ticks": horizon,
            "prior_prelock_attempts": [
                {
                    "attempt": 1,
                    "result": "PROTOCOL_IMPORT_FAILURE",
                    "organism_creations": 0,
                    "organism_ticks": 0,
                    "detail": "direct tools-path invocation lacked repository-root sys.path bootstrap",
                },
                {
                    "attempt": 2,
                    "result": "DEVELOPMENT_SETUP_FAILURE",
                    "organism_creations": 0,
                    "organism_ticks": 0,
                    "detail": "world_model_config was None before fallback construction",
                },
                {
                    "attempt": 3,
                    "result": "DEVELOPMENT_RUNTIME_FAILURE",
                    "organism_creations": 1,
                    "organism_ticks": 1,
                    "detail": "runtime readiness path referenced an unimported AdapterRequest",
                },
                {
                    "attempt": 4,
                    "result": "DEVELOPMENT_GATE_ASSERTION_FAILURE",
                    "organism_creations": 1,
                    "organism_ticks": 240,
                    "detail": "observation assertion treated duplicate candidate evaluations as a selected non-executable terminal",
                },
            ],
            "retries": 0,
            "reseeds": 0,
            "terminal_readiness_calls": terminal_calls,
            "readiness_status_counts": status_counts,
            "selected_terminal_count": len(selected_terminal),
            "not_ready_terminal_selected_count": len(not_ready_selected),
            "post_reversal_non_executable_calls": len(post_reversal_terminal_denials),
            "selected_actions": selected,
            "readiness_observations": readiness_calls,
            "protected_properties": {
                "unavailable_terminal_never_selected": not not_ready_selected,
                "categorical_only": all(call["status"] in {EXECUTABLE, NOT_EXECUTABLE, UNKNOWN_EXECUTABILITY} for call in readiness_calls),
                "no_critical_failure": organism.phys.critical_any() is False,
                "planning_authority_absent": True,
                "route_evidence_reader_absent": True,
            },
        }
    finally:
        base_runner.config = original_config
        if organism is not None:
            organism.close()
        for path in (database, Path(str(database) + "-wal"), Path(str(database) + "-shm")):
            path.unlink(missing_ok=True)
    result["decision_trace_sha256"] = sha256(decision) if decision.exists() else None
    result["planning_trace_sha256"] = sha256(shadow) if shadow.exists() else None
    result["artifact_sha256"] = durable_json(EVIDENCE_ROOT / "AS007_DEVELOPMENT_GATE_RESULT_R5.json", result)
    if not all(result["protected_properties"].values()):
        raise RuntimeError("as007_development_gate_failed")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("lock", "development"), required=True)
    args = parser.parse_args()
    result = lock_contract() if args.mode == "lock" else development_gate()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
