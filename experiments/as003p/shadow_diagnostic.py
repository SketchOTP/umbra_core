#!/usr/bin/env python3
"""One-shot AS-003P control/shadow observer-effect qualification.

Exactly one control and one shadow execution use the existing CLOSE-02R R0/S0
Diagnostic-A fixture (seed 45878900, horizon 500). Evidence destinations are
create-once. This runner contains no retry or reseed path.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any

import experiments.close02r.qualification as fixture


ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-modal-planning-frame-r1")
SEED = 45878900
HORIZON = 500
UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}"
)
DERIVATIVE_HASH_KEYS = {
    "event_hash",
    "payload_hash",
    "previous_event_hash",
    "source_sample_hash",
    "state_hash",
}


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if value == value and value not in (float("inf"), float("-inf")) else str(value)
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, set):
        return sorted((_safe(v) for v in value), key=repr)
    if hasattr(value, "to_dict"):
        return _safe(value.to_dict())
    return str(value)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(_safe(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _publish(name: str, data: bytes) -> str:
    ROOT.mkdir(parents=True, exist_ok=True)
    destination = ROOT / name
    if destination.exists():
        raise FileExistsError(f"AS003P one-shot evidence already exists: {destination}")
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=ROOT)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        directory_fd = os.open(ROOT, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    readback = destination.read_bytes()
    if readback != data:
        raise RuntimeError("evidence readback mismatch")
    return hashlib.sha256(readback).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(_safe(value), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _trace_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _semantic_runtime_value(value: Any, identities: dict[str, str] | None = None) -> Any:
    """Normalize administrative UUIDs while preserving their equality relations.

    Independent fixture instances mint UUIDs and ledger hashes outside the seeded
    organism RNG. They are not behavioral semantics. First-occurrence tokens retain
    relationship structure; only hashes derived from those administrative values are
    omitted. All actual owner fields remain in the comparison.
    """
    identities = identities if identities is not None else {}
    if isinstance(value, dict):
        return {
            str(key): _semantic_runtime_value(item, identities)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in DERIVATIVE_HASH_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_semantic_runtime_value(item, identities) for item in value]
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            raw = match.group(0).lower()
            if raw not in identities:
                identities[raw] = f"<ADMIN_UUID_{len(identities) + 1}>"
            return identities[raw]

        return UUID_PATTERN.sub(replace, value)
    return _safe(value)


def _normalized_state(state: dict[str, Any]) -> dict[str, Any]:
    result = _semantic_runtime_value(state)
    metrics = dict(result.get("metrics") or {})
    if isinstance(metrics.get("cells"), list):
        metrics["cells"] = sorted(metrics["cells"])
    result["metrics"] = metrics
    return _safe(result)


def _normalized_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    identities: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    for event in events:
        rows.append(
            _semantic_runtime_value(
                {
                    "sequence": event["sequence"],
                    "event_type": event["event_type"],
                    "schema_version": event["schema_version"],
                    "monotonic_time": event["monotonic_time"],
                    "wall_time": event["wall_time"],
                    "causal_parent_ids": event["causal_parent_ids"],
                    "payload": event["payload"],
                },
                identities,
            )
        )
    return rows


def run_one(*, shadow: bool, work: Path) -> tuple[dict[str, Any], bytes, bytes | None]:
    work.mkdir(parents=True, exist_ok=False)
    label = "SHADOW" if shadow else "CONTROL"
    decision_trace = work / f"{label}.decision-trace.jsonl"
    planning_trace = work / f"{label}.planning-shadow.jsonl"
    original_config = fixture.config

    def config(seed: int, db: Path, regime: str):
        cfg = original_config(seed, db, regime)
        cfg.decision_trace_path = str(decision_trace)
        cfg.planning_shadow_path = str(planning_trace) if shadow else None
        return cfg

    fixture.config = config
    db = work / f"{label}.sqlite"
    organism = None
    timeline: list[dict[str, Any]] = []
    try:
        organism, _ = fixture.prepare(SEED, db, "R0")
        for _ in range(HORIZON):
            result = organism.tick_once()
            timeline.append({
                "tick": organism.tick,
                "capability": result.get("capability"),
                "denied": result.get("denied"),
                "action_issued": result.get("action_issued"),
                "no_safe_action": result.get("no_safe_action", False),
                "physiology": organism.phys.as_dict(),
                "outcome": result.get("outcome"),
            })
        events = list(organism.store.iter_events())
        final_state = _normalized_state(organism.authoritative_state())
        rng_state = organism.rng.export_state()
        subsystem_hashes = {
            key: _digest(final_state.get(key))
            for key in ("physiology", "embodiment", "arbitration", "governance", "self_model", "world_model", "development", "memory", "social", "individuality", "temporal")
        }
        record = {
            "schema": "AS003P_NONFORMAL_EXECUTION_RECORD_V1",
            "identity": label,
            "regime": "R0",
            "scenario": "S0",
            "seed": SEED,
            "horizon": HORIZON,
            "shadow_enabled": shadow,
            "timeline": _semantic_runtime_value(timeline),
            "authoritative_events": _normalized_events(events),
            "final_authoritative_state": final_state,
            "final_authoritative_state_hash": _digest(final_state),
            "rng_state": rng_state,
            "rng_state_hash": _digest(rng_state),
            "subsystem_hashes": subsystem_hashes,
            "retries": 0,
            "reseeds": 0,
            "formal": False,
        }
    finally:
        fixture.config = original_config
        if organism is not None:
            organism.close()
    decision_bytes = decision_trace.read_bytes()
    planning_bytes = planning_trace.read_bytes() if shadow else None
    rows = _trace_rows(decision_trace)
    record["decision_trace_rows"] = len(rows)
    record["decision_trace_hash"] = hashlib.sha256(decision_bytes).hexdigest()
    record["candidate_identities_by_tick"] = _semantic_runtime_value([
        {
            "tick": row.get("tick"),
            "pool": sorted(view.get("identity") for view in (row.get("distributed_competition") or {}).get("views", []) if view.get("identity")),
            "selected": (row.get("distributed_competition") or {}).get("selected_identity"),
            "governance": row.get("governance_decision"),
            "verified_outcome": row.get("verified_outcome_linkage"),
        }
        for row in rows
    ])
    return record, decision_bytes, planning_bytes


def shadow_coverage(planning_bytes: bytes) -> dict[str, Any]:
    rows = [json.loads(line) for line in planning_bytes.decode().splitlines() if line.strip()]
    complete = [row for row in rows if "frame" in row and "candidate_profiles" in row]
    classes: dict[str, int] = {}
    frames_with_distinctions = 0
    for row in complete:
        tick_classes = []
        for candidate in row.get("candidate_profiles", []):
            cls = candidate["profile"]["classification"]
            classes[cls] = classes.get(cls, 0) + 1
            tick_classes.append(cls)
        if len(set(tick_classes)) > 1:
            frames_with_distinctions += 1
    opportunity_modalities: dict[str, int] = {}
    for row in complete:
        for opportunity in (row["frame"].get("opportunities") or {}).values():
            for scope in ("current", "future"):
                modality = f"{scope}:{opportunity.get(scope, {}).get('modality')}"
                opportunity_modalities[modality] = opportunity_modalities.get(modality, 0) + 1
    return {
        "frames_attempted": len(rows),
        "frames_complete": len(complete),
        "frames_incomplete": len(rows) - len(complete),
        "capture_errors": [row.get("capture_error") or row.get("evaluation_error") for row in rows if row.get("capture_error") or row.get("evaluation_error")],
        "candidate_profile_counts": dict(sorted(classes.items())),
        "frames_with_candidate_profile_distinctions": frames_with_distinctions,
        "opportunity_modalities": dict(sorted(opportunity_modalities.items())),
    }


def main() -> None:
    required = [
        "AS003P_PAIRED_EXECUTION_STARTED.json", "AS003P_PAIRED_EXECUTION_FINISHED.json",
        "AS003P_CONTROL_RUN.json", "AS003P_SHADOW_RUN.json", "AS003P_CONTROL_DECISION_TRACE.jsonl",
        "AS003P_SHADOW_DECISION_TRACE.jsonl", "AS003P_PLANNING_SHADOW_TRACE.jsonl", "AS003P_OBSERVER_PARITY.json",
    ]
    existing = [name for name in required if (ROOT / name).exists()]
    if existing:
        raise FileExistsError(f"AS003P one-shot pair already executed: {existing}")
    started_at = time.time()
    git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    start_record = {
        "schema": "AS003P_PAIRED_EXECUTION_STARTED_V1",
        "command": "python3 experiments/as003p/shadow_diagnostic.py",
        "working_directory": str(Path.cwd()),
        "git_commit": git_commit,
        "fixture": {"regime": "R0", "scenario": "S0", "seed": SEED, "horizon": HORIZON},
        "control_authorized": 1,
        "shadow_authorized": 1,
        "retries_authorized": 0,
        "reseeds_authorized": 0,
        "formal": False,
        "started_unix": started_at,
    }
    digests = {
        "AS003P_PAIRED_EXECUTION_STARTED.json": _publish(
            "AS003P_PAIRED_EXECUTION_STARTED.json", _json_bytes(start_record)
        )
    }
    work = Path(tempfile.mkdtemp(prefix="umbra-as003p-pair-"))
    try:
        control, control_trace, _ = run_one(shadow=False, work=work / "control")
        digests["AS003P_CONTROL_RUN.json"] = _publish("AS003P_CONTROL_RUN.json", _json_bytes(control))
        digests["AS003P_CONTROL_DECISION_TRACE.jsonl"] = _publish(
            "AS003P_CONTROL_DECISION_TRACE.jsonl", control_trace
        )

        shadow, shadow_trace, planning_trace = run_one(shadow=True, work=work / "shadow")
        assert planning_trace is not None
        digests["AS003P_SHADOW_RUN.json"] = _publish("AS003P_SHADOW_RUN.json", _json_bytes(shadow))
        digests["AS003P_SHADOW_DECISION_TRACE.jsonl"] = _publish(
            "AS003P_SHADOW_DECISION_TRACE.jsonl", shadow_trace
        )
        digests["AS003P_PLANNING_SHADOW_TRACE.jsonl"] = _publish(
            "AS003P_PLANNING_SHADOW_TRACE.jsonl", planning_trace
        )

        semantic_fields = [
            "timeline", "authoritative_events", "final_authoritative_state_hash", "rng_state_hash",
            "subsystem_hashes", "candidate_identities_by_tick",
        ]
        comparisons = {field: control[field] == shadow[field] for field in semantic_fields}
        parity = {
            "schema": "AS003P_OBSERVER_PARITY_V1",
            "fixture": {"regime": "R0", "scenario": "S0", "seed": SEED, "horizon": HORIZON},
            "normalization": {
                "administrative_uuid_relations": "first-occurrence canonical tokens",
                "excluded_derivatives": sorted(DERIVATIVE_HASH_KEYS),
                "owner_state_fields_excluded": [],
            },
            "comparisons": comparisons,
            "exact_authoritative_parity": all(comparisons.values()),
            "control_final_state_hash": control["final_authoritative_state_hash"],
            "shadow_final_state_hash": shadow["final_authoritative_state_hash"],
            "control_rng_hash": control["rng_state_hash"],
            "shadow_rng_hash": shadow["rng_state_hash"],
            "coverage": shadow_coverage(planning_trace),
            "control_executions": 1,
            "shadow_executions": 1,
            "retries": 0,
            "reseeds": 0,
            "formal": False,
            "verdict_if_false": "AS003P_OBSERVER_EFFECT_FAIL",
        }
        digests["AS003P_OBSERVER_PARITY.json"] = _publish(
            "AS003P_OBSERVER_PARITY.json", _json_bytes(parity)
        )
        finished = {
            "schema": "AS003P_PAIRED_EXECUTION_FINISHED_V1",
            "git_commit": git_commit,
            "started_unix": started_at,
            "finished_unix": time.time(),
            "control_executions": 1,
            "shadow_executions": 1,
            "retries": 0,
            "reseeds": 0,
            "exact_authoritative_parity": parity["exact_authoritative_parity"],
            "artifact_sha256": dict(sorted(digests.items())),
        }
        digests["AS003P_PAIRED_EXECUTION_FINISHED.json"] = _publish(
            "AS003P_PAIRED_EXECUTION_FINISHED.json", _json_bytes(finished)
        )
        print(json.dumps({"parity": parity, "digests": digests}, sort_keys=True))
        if not parity["exact_authoritative_parity"]:
            raise SystemExit(2)
    except BaseException as exc:
        if not (ROOT / "AS003P_EXECUTION_EXCEPTION.json").exists():
            _publish(
                "AS003P_EXECUTION_EXCEPTION.json",
                _json_bytes({
                    "schema": "AS003P_EXECUTION_EXCEPTION_V1",
                    "git_commit": git_commit,
                    "started_unix": started_at,
                    "failed_unix": time.time(),
                    "exception_type": type(exc).__name__,
                    "exception": str(exc),
                    "no_retry_authorized": True,
                }),
            )
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
