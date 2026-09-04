#!/usr/bin/env python3
"""AS-009 habitat-authority recovery and fresh R2/R3 qualification."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d014.run_formal import adapter_burst, config
from umbra_core.embodiment import _make_partner
from umbra_core.embodiment_adapters.profiles import MINIMAL_CREATURE_BODY
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.state import FreeLocation, make_social_entity_object
from umbra_core.runtime import create_organism, load_organism

DIRECTIVE = "UMBRA-AS-009"
BASELINE = "f5e73ec4a3f5b677590d079d2bf2e506a699134e"
HORIZON = 7200
REGIMES = ("R2", "R3")
SCENARIOS = {"R2": "S10", "R3": "S12"}
EVIDENCE_ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-009-r2-r3-habitat-authority-integrated-qualification-r1")
PARTNER_OBJECT_ID = "social:partner:d014"


def durable_json(path: Path, value: Any) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        os.write(fd, payload)
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


def partner_object() -> Any:
    partner = _make_partner("partner:d014", 6.0, 4.0, "H0", index=0)
    policy = partner.response_policy
    return make_social_entity_object(
        object_id=PARTNER_OBJECT_ID,
        entity_ref=partner.hidden_partner_id,
        location=FreeLocation(6.0, 4.0, "zone:general"),
        history_code=policy.history_code,
        motion_signature=partner.true_cues.motion_signature,
        appearance_signature=partner.true_cues.appearance_signature,
        response_timing_pattern=partner.true_cues.response_timing_pattern,
        interaction_style_cues=partner.true_cues.interaction_style_cues,
        response_mode=policy.mode,
        contingent_probability=policy.contingent_probability,
        flip_at=policy.flip_at,
        absent_windows=tuple(policy.absent_windows),
    )


def prepare(seed: int, db: Path, regime: str):
    organism = create_organism(config(seed, db, regime))
    for method in ("_ensure_development_intervention", "_ensure_memory_history", "_ensure_social_history", "_ensure_individuality_history"):
        getattr(organism, method)()
    engine = HabitatEngine(_habitat_state_for_scenario(SCENARIOS[regime]))
    organism.embodiment.attach_habitat_engine(engine)
    organism.embodiment.body.x, organism.embodiment.body.y = 4.0, 3.0
    organism.perception.perceive_habitat_objects(organism.embodiment, 1.0, organism.rng)
    return organism, engine


def reload_existing(seed: int, db: Path, regime: str, saved_habitat: Any):
    organism = load_organism(config(seed, db, regime))
    engine = HabitatEngine(copy.deepcopy(saved_habitat))
    organism.embodiment.attach_habitat_engine(engine)
    return organism, engine


def run_case(regime: str, seed: int, work: Path, horizon: int) -> dict[str, Any]:
    db = work / f"{regime}-{seed}.sqlite"
    organism, engine = prepare(seed, db, regime)
    identity = organism.identity.agent_id
    state: dict[str, Any] = {
        "organism": organism,
        "engine": engine,
        "restart_count": 0,
        "restart_identity_preserved": False,
        "partner_created": False,
        "partner_engine_count_at_creation": 0,
        "partner_occluded": False,
        "partner_reappeared": False,
        "adapter_accepts": 0,
        "body_change_count": 0,
        "body_identity_preserved": False,
        "visible_cue_ticks": 0,
        "occluded_cue_ticks": 0,
        "reappeared_cue_ticks": 0,
        "visibility_windows": {"visible": [], "occluded": [], "reappeared": []},
    }
    actions: Counter[str] = Counter()
    extrema = {"min_energy": 1.0, "max_fatigue": 0.0, "min_integrity": 1.0, "min_stimulation": 1.0}
    failure: dict[str, Any] | None = None
    first_no_safe: int | None = None
    started = time.monotonic()
    try:
        for _ in range(horizon):
            organism = state["organism"]
            tick = organism.tick + 1
            if regime == "R2" and tick == 600:
                event = state["engine"].commit_object_creation(
                    partner_object(), event_id=f"as009:create:{seed}", transaction_id=f"as009:create-txn:{seed}", request_id=f"as009:create-req:{seed}"
                )
                state["partner_created"] = True
                state["partner_engine_count_at_creation"] = len(state["engine"].authoritative_social_entities())
                state["partner_creation_event_type"] = event.get("event_type")
            if regime == "R2" and tick == 1200:
                state["adapter_accepts"] += int(adapter_burst(organism, seed, tick))
            if regime == "R2" and tick == 1800:
                saved_habitat = copy.deepcopy(state["engine"].state)
                organism.snapshot_if_due(force=True)
                organism.close()
                organism, engine = reload_existing(seed, db, regime, saved_habitat)
                state.update(organism=organism, engine=engine, restart_count=state["restart_count"] + 1, restart_identity_preserved=organism.identity.agent_id == identity)
                state["partner_present_after_restart"] = len(engine.authoritative_social_entities()) == 1
            if regime == "R2" and tick == 2400:
                state["engine"].commit_object_visibility(PARTNER_OBJECT_ID, occluded=True, event_id=f"as009:hide:{seed}", transaction_id=f"as009:hide-txn:{seed}", request_id=f"as009:hide-req:{seed}")
                state["partner_occluded"] = True
            if regime == "R2" and tick == 2600:
                state["engine"].commit_object_visibility(PARTNER_OBJECT_ID, occluded=False, event_id=f"as009:show:{seed}", transaction_id=f"as009:show-txn:{seed}", request_id=f"as009:show-req:{seed}")
                state["partner_reappeared"] = True
            if regime == "R3" and tick == 3600:
                organism.embodiment_adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id, origin="D014_R3_PREREGISTERED")
                state.update(body_change_count=1, body_profile_after=organism.embodiment_adapter.profile.profile_id, body_identity_preserved=organism.identity.agent_id == identity)
            result = organism.tick_once()
            state["engine"] = organism.embodiment._habitat_engine
            actions[str(result.get("capability"))] += 1
            extrema["min_energy"] = min(extrema["min_energy"], float(organism.phys.energy))
            extrema["max_fatigue"] = max(extrema["max_fatigue"], float(organism.phys.fatigue))
            extrema["min_integrity"] = min(extrema["min_integrity"], float(organism.phys.integrity))
            extrema["min_stimulation"] = min(extrema["min_stimulation"], float(organism.phys.stimulation))
            if regime == "R2" and state["partner_created"]:
                cue_count = len(getattr(organism.perception, "partner_cues", ()))
                if 600 <= organism.tick < 2400:
                    state["visible_cue_ticks"] += int(cue_count > 0)
                    if organism.tick in (600, 1200, 1800, 2399):
                        state["visibility_windows"]["visible"].append({"tick": organism.tick, "cue_count": cue_count})
                elif 2400 <= organism.tick < 2600:
                    state["occluded_cue_ticks"] += int(cue_count > 0)
                    if organism.tick in (2400, 2500, 2599):
                        state["visibility_windows"]["occluded"].append({"tick": organism.tick, "cue_count": cue_count})
                elif 2600 <= organism.tick < 2800:
                    state["reappeared_cue_ticks"] += int(cue_count > 0)
                    if organism.tick in (2600, 2700, 2799):
                        state["visibility_windows"]["reappeared"].append({"tick": organism.tick, "cue_count": cue_count})
            if result.get("no_safe_action") and first_no_safe is None:
                first_no_safe = organism.tick
            if organism.phys.critical_any() and failure is None:
                failure = {"tick": organism.tick, "physiology": organism.phys.as_dict(), "result": result}
                break
        completed = failure is None and state["organism"].tick >= horizon
        return {
            "directive": DIRECTIVE,
            "regime": regime,
            "scenario": SCENARIOS[regime],
            "seed": seed,
            "ticks": state["organism"].tick,
            "target_ticks": horizon,
            "terminal": "completed" if completed else "scientific_failure",
            "critical_failure": failure,
            "first_no_safe_action": first_no_safe,
            **extrema,
            "actions": dict(actions),
            "restart_count": state["restart_count"],
            "restart_identity_preserved": state["restart_identity_preserved"],
            "partner_created": state["partner_created"],
            "partner_engine_count_at_creation": state["partner_engine_count_at_creation"],
            "partner_present_after_restart": state.get("partner_present_after_restart", False),
            "partner_occluded": state["partner_occluded"],
            "partner_reappeared": state["partner_reappeared"],
            "adapter_accepts": state["adapter_accepts"],
            "visible_cue_ticks": state["visible_cue_ticks"],
            "occluded_cue_ticks": state["occluded_cue_ticks"],
            "reappeared_cue_ticks": state["reappeared_cue_ticks"],
            "visibility_windows": state["visibility_windows"],
            "body_change_count": state["body_change_count"],
            "body_profile_after": state.get("body_profile_after"),
            "body_identity_preserved": state["body_identity_preserved"],
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    finally:
        state["organism"].close()
        for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
            path.unlink(missing_ok=True)


def load_manifest(path: Path) -> dict[str, list[int]]:
    value = json.loads(path.read_text())
    if value.get("directive") != DIRECTIVE or value.get("baseline") != BASELINE or value.get("seed_status") != "frozen_before_formal_execution":
        raise SystemExit("AS009_FORMAL_SEED_MANIFEST_IDENTITY_FAIL")
    regimes = value.get("regimes")
    if not isinstance(regimes, dict) or tuple(regimes) != REGIMES or any(len(regimes[r]) != 8 for r in REGIMES):
        raise SystemExit("AS009_FORMAL_SEED_MANIFEST_SHAPE_FAIL")
    flat = [int(seed) for r in REGIMES for seed in regimes[r]]
    if len(set(flat)) != 16 or 16827204 in flat:
        raise SystemExit("AS009_FORMAL_SEED_MANIFEST_DISJOINTNESS_FAIL")
    return {r: [int(seed) for seed in regimes[r]] for r in REGIMES}


def preflight(work: Path, smoke_seeds: dict[str, int]) -> dict[str, Any]:
    rows = [run_case(regime, smoke_seeds[regime], work, 2601 if regime == "R2" else 3601) for regime in REGIMES]
    checks = {
        "r2_partner_engine_authority": rows[0]["partner_created"] and rows[0]["partner_engine_count_at_creation"] == 1 and rows[0]["partner_present_after_restart"],
        "r2_restart_identity": rows[0]["restart_count"] == 1 and rows[0]["restart_identity_preserved"],
        "r2_visibility_schedule": rows[0]["partner_occluded"] and rows[0]["partner_reappeared"],
        "r2_adapter": rows[0]["adapter_accepts"] == 1,
        "r3_profile_change": rows[1]["body_change_count"] == 1 and rows[1]["body_identity_preserved"],
        "both_completed": all(row["terminal"] == "completed" for row in rows),
    }
    return {"schema": "AS009_R2_R3_EXECUTABLE_PREFLIGHT_V1", "directive": DIRECTIVE, "smoke": True, "rows": rows, "checks": checks, "overall": "PASS" if all(checks.values()) else "FAIL"}


def execute(work: Path, output: Path, manifest_path: Path) -> dict[str, Any]:
    seeds = load_manifest(manifest_path)
    rows: list[dict[str, Any]] = []
    for regime in REGIMES:
        for index, seed in enumerate(seeds[regime]):
            row = run_case(regime, seed, work, HORIZON)
            row.update({"stage": f"FORMAL_{regime}", "seed_index": index})
            rows.append(row)
            with output.with_name("AS009_FORMAL_RUN_SUMMARIES.jsonl").open("a") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            if row["terminal"] != "completed":
                return {"schema": "AS009_FORMAL_REDUCTION_V1", "directive": DIRECTIVE, "baseline": BASELINE, "expected_runs": 16, "completed_runs": len(rows), "terminal": f"AS009_FRESH_{regime}_FAIL", "rows": rows}
    return {"schema": "AS009_FORMAL_REDUCTION_V1", "directive": DIRECTIVE, "baseline": BASELINE, "expected_runs": 16, "completed_runs": len(rows), "all_completed": True, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "execute"), required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=EVIDENCE_ROOT / "AS009_FORMAL_SEED_MANIFEST.json")
    args = parser.parse_args()
    if args.mode == "preflight":
        result = preflight(args.work, {"R2": 30991011, "R3": 30991012})
        durable_json(args.output, result)
    else:
        result = execute(args.work, args.output, args.manifest)
        durable_json(args.output, result)
        shutil.rmtree(args.work, ignore_errors=True)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
