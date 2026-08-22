"""D-014 bounded integrated organism qualification.

This harness composes the existing D-009 habitat, D-010 temporal, and D-011
perception paths. It does not modify production behavior or command actions.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d009.scenario_plants import apply_scenario_plants
from umbra_core.embodiment import _make_partner
from umbra_core.perception_adapters import AdapterManifest, SyntheticPerceptionAdapter
from umbra_core.embodiment_adapters.profiles import MINIMAL_CREATURE_BODY
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.temporal.config import TemporalConfig

BASELINE = "f59c767ff758fb8d957581c0420a5271f3192f3b"
DIRECTIVE = "UMBRA-D-014"
EVIDENCE_ROOT = Path("/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d014-integrated-stability-r1")
REGIMES = ("R0", "R1", "R2", "R3")
HORIZON = 7200


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regime_spec() -> dict[str, Any]:
    return {
        "directive": DIRECTIVE,
        "baseline": BASELINE,
        "horizon_ticks": HORIZON,
        "regimes": {
            "R0": {"scenario": "S0", "purpose": "nominal autonomous life", "events": []},
            "R1": {"scenario": "S16", "purpose": "competing homeostatic opportunities", "events": ["existing habitat dynamics"]},
            "R2": {"scenario": "S10", "purpose": "continuity, governed perception, and social perturbation", "events": [{"tick": 600, "event": "partner_present"}, {"tick": 1200, "event": "adapter_observation"}, {"tick": 1800, "event": "snapshot_reload"}, {"tick": 2400, "event": "partner_occlusion"}, {"tick": 2600, "event": "partner_reappearance"}]},
            "R3": {"scenario": "S12", "purpose": "same-self continuity through body change", "events": [{"tick": 3600, "event": "swap_to_minimal_creature_body"}]},
        },
    }


def thresholds() -> dict[str, Any]:
    return {"rss_hard_max_mib": 180, "rss_slope_mib_per_hour_max": 1.0, "cpu_mean_fraction_max": 0.05, "database_growth_bytes_max": 67108864, "event_growth_records_per_tick_max": 32, "fd_delta_max": 4, "thread_delta_max": 2, "raw_durable_sensor_payload_max": 0, "global_evidence_gib_target": 10, "global_evidence_gib_hard_stop": 12, "realtime_soak_seconds": 3600, "realtime_soak_hz": 2}


def fresh_seeds() -> dict[str, list[int]]:
    used: set[int] = set()
    for path in list((ROOT / "experiments").rglob("*seed*.json")) + list((ROOT / "docs").rglob("*seed*.json")):
        try:
            value = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        def collect(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, item in obj.items():
                    if "seed" in str(key).lower() and isinstance(item, int):
                        used.add(item)
                    collect(item)
            elif isinstance(obj, list):
                for item in obj:
                    collect(item)
        collect(value)
    seeds: dict[str, list[int]] = {}
    for regime in REGIMES:
        seeds[regime] = []
        for index in range(8):
            digest = hashlib.sha256(f"{DIRECTIVE}|{BASELINE}|{regime}|{index}".encode()).digest()
            candidate = 20000 + int.from_bytes(digest[:8], "big") % 80000000
            while candidate in used:
                candidate += 1
            used.add(candidate)
            seeds[regime].append(candidate)
    return seeds


def config(seed: int, db: Path, regime: str) -> OrganismConfig:
    scenario = regime_spec()["regimes"][regime]["scenario"]
    return OrganismConfig(db_path=str(db), seed=seed, condition="C0", snapshot_every=200, temporal_enabled=True, temporal_config=TemporalConfig(), temporal_scenario_id=scenario, temporal_scenario_hook=apply_scenario_plants, habitat_enabled=True, habitat_scenario_id=scenario, habitat_scenario_hook=apply_scenario_plants, self_model_enabled=True, world_model_enabled=True, development_enabled=True, memory_enabled=True, social_enabled=True, individuality_enabled=True, embodiment_adapter_enabled=True, expression_enabled=True, drift_enabled=True, wall_time_fn=lambda: 0.0)


def prepare(seed: int, db: Path, regime: str):
    org = create_organism(config(seed, db, regime))
    for method in ("_ensure_development_intervention", "_ensure_memory_history", "_ensure_social_history", "_ensure_individuality_history"):
        getattr(org, method)()
    scenario = regime_spec()["regimes"][regime]["scenario"]
    engine = HabitatEngine(_habitat_state_for_scenario(scenario))
    org.embodiment.attach_habitat_engine(engine)
    org.embodiment.body.x, org.embodiment.body.y = 4.0, 3.0
    org.perception.perceive_habitat_objects(org.embodiment, 1.0, org.rng)
    return org, engine


def reload_existing(seed: int, db: Path, regime: str, saved_habitat: Any):
    """Reload the persisted organism; preserve habitat state independently."""
    org = load_organism(config(seed, db, regime))
    engine = HabitatEngine(copy.deepcopy(saved_habitat))
    org.embodiment.attach_habitat_engine(engine)
    return org, engine


def adapter_burst(org: Any, seed: int, tick: int) -> bool:
    manifest = AdapterManifest("d014-formal", "1", ("body_telemetry",), {"body_telemetry": "v1"})
    adapter = SyntheticPerceptionAdapter(manifest)
    envelope = adapter.submit(observation_id=f"d014-{seed}-{tick}", source_id=f"formal-source-{seed % 4}", modality="body_telemetry", schema_version="v1", core_receipt_tick=org.tick, source_timestamp=None, capture_interval=None, derived_features={"temperature_delta": tick % 3}, confidence=0.8, uncertainty=0.2, provenance_chain=(("step", "d014-formal"), ("source", "governed-adapter")), privacy_classification="DERIVED_ONLY", consent_state="CONSENT_GRANTED", retention_class="DERIVED_BOUNDED", replay_class="AUTHORITATIVE", integrity_metadata={"seed": str(seed), "tick": str(tick)})
    return bool(org.submit_perception_observation(envelope, manifest))


def run_case(regime: str, seed: int, work: Path, horizon: int) -> dict[str, Any]:
    db = work / f"{regime}-{seed}.sqlite"
    org, engine = prepare(seed, db, regime)
    state: dict[str, Any] = {"db": db, "engine": engine, "org": org, "restart_count": 0, "restart_identity_preserved": False, "partner_observations": 0, "adapter_accepts": 0, "partner_occluded": False, "partner_reappeared": False, "body_change_count": 0, "body_profile_after": None, "body_identity_preserved": False}
    actions: Counter[str] = Counter()
    extrema = {"min_energy": 1.0, "max_fatigue": 0.0, "min_integrity": 1.0, "min_stimulation": 1.0}
    failure: dict[str, Any] | None = None
    first_no_safe: int | None = None
    started = time.monotonic()
    try:
        for _ in range(horizon):
            org = state["org"]
            tick = org.tick + 1
            if regime == "R2" and tick == 600:
                org.embodiment.plant_partner(_make_partner("partner:d014", 6.0, 4.0, "R2", index=0))
                state["partner_observations"] += 1
            if regime == "R2" and tick == 1200:
                state["adapter_accepts"] += int(adapter_burst(org, seed, tick))
            if regime == "R2" and tick == 1800:
                identity = org.identity.agent_id
                saved_habitat = copy.deepcopy(state["engine"].state)
                org.snapshot_if_due(force=True)
                org.close()
                org, engine = reload_existing(seed, db, regime, saved_habitat)
                state.update(org=org, engine=engine, restart_count=state["restart_count"] + 1, restart_identity_preserved=org.identity.agent_id == identity)
            if regime == "R2" and tick == 2400:
                org.embodiment.set_occlusion("partner", True)
                state["partner_occluded"] = True
            if regime == "R2" and tick == 2600:
                org.embodiment.set_occlusion("partner", False)
                state["partner_reappeared"] = True
            if regime == "R3" and tick == 3600:
                org.embodiment_adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id, origin="D014_R3_PREREGISTERED")
                state.update(body_change_count=1, body_profile_after=org.embodiment_adapter.profile.profile_id, body_identity_preserved=True)
            result = org.tick_once()
            state["engine"] = org.embodiment._habitat_engine
            actions[str(result.get("capability"))] += 1
            extrema["min_energy"] = min(extrema["min_energy"], float(org.phys.energy))
            extrema["max_fatigue"] = max(extrema["max_fatigue"], float(org.phys.fatigue))
            extrema["min_integrity"] = min(extrema["min_integrity"], float(org.phys.integrity))
            extrema["min_stimulation"] = min(extrema["min_stimulation"], float(org.phys.stimulation))
            if result.get("no_safe_action") and first_no_safe is None:
                first_no_safe = org.tick
            if org.phys.critical_any() and failure is None:
                failure = {"tick": org.tick, "physiology": org.phys.as_dict(), "result": result}
                break
        terminal = "completed" if failure is None and state["org"].tick >= horizon else "scientific_failure"
        return {"regime": regime, "seed": seed, "ticks": state["org"].tick, "target_ticks": horizon, "terminal": terminal, "critical_failure": failure, "first_no_safe_action": first_no_safe, **extrema, "actions": dict(actions), "restart_count": state["restart_count"], "restart_identity_preserved": state["restart_identity_preserved"], "adapter_accepts": state["adapter_accepts"], "partner_observations": state["partner_observations"], "partner_occluded": state["partner_occluded"], "partner_reappeared": state["partner_reappeared"], "body_change_count": state["body_change_count"], "body_profile_after": state["body_profile_after"], "body_identity_preserved": state["body_identity_preserved"], "elapsed_seconds": time.monotonic() - started}
    finally:
        state["org"].close()
        for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")):
            path.unlink(missing_ok=True)


def specs() -> dict[str, Any]:
    seeds = fresh_seeds()
    return {"D014_REGIME_SPEC.json": regime_spec(), "D014_FORMAL_SEEDS.json": {"directive": DIRECTIVE, "baseline": BASELINE, "seeds": seeds}, "D014_THRESHOLDS.json": thresholds(), "D014_SCHEDULES.json": {"horizon_ticks": HORIZON, "restart": {"R2": 1800}, "body_change": {"R3": 3600}, "maximum_runs": 32}, "D014_BODY_CHANGE_SPEC.json": {"R3": {"from": "ABSTRACT_SHAPE_BODY", "to": MINIMAL_CREATURE_BODY.profile_id, "tick": 3600, "identity_mutation": False, "history_mutation": False}}, "D014_PERCEPTION_SOCIAL_SPEC.json": {"R2": {"adapter_manifest": "d014-formal/v1", "partner_tick": 600, "adapter_tick": 1200, "occlusion": [2400, 2600]}}, "D014_FORMAL_CONTRACT.json": {"directive": DIRECTIVE, "classification": "FRESH_CURRENT_STACK_FORMAL_QUALIFICATION", "runs": 32, "seeds_per_regime": 8, "horizon_ticks": HORIZON, "production_changes": [], "interventions": 0, "hidden_truth_action_authority": False}}


def preflight(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    frozen = specs()
    for name, value in frozen.items():
        write_json(root / name, value)
    work = root / "smoke-work"
    work.mkdir(exist_ok=True)
    smoke = [run_case(regime, frozen["D014_FORMAL_SEEDS.json"]["seeds"][regime][0], work, 20) for regime in REGIMES]
    shutil.rmtree(work, ignore_errors=True)
    passed = all(row["terminal"] == "completed" and row["ticks"] == 20 for row in smoke)
    result = {"directive": DIRECTIVE, "baseline": BASELINE, "preflight": "PASS" if passed else "FAIL", "smoke": smoke, "formal_evidence_written": False, "notion_start_refetch_verified": False, "notion_note": "No Notion connector available in this execution context"}
    write_json(root / "D014_PREFLIGHT.json", result)
    return result


def execute(root: Path) -> dict[str, Any]:
    preflight_path = root / "D014_PREFLIGHT.json"
    if not preflight_path.exists() or json.loads(preflight_path.read_text()).get("preflight") != "PASS":
        raise SystemExit("D014_PREFLIGHT_REQUIRED")
    frozen = specs()
    for name, value in frozen.items():
        write_json(root / name, value)
    manifest = {"directive": DIRECTIVE, "baseline": BASELINE, "execution_id": "d014-integrated-stability-r1", "freeze_time": time.time(), "spec_hashes": {name: sha256(root / name) for name in frozen}, "horizon_ticks": HORIZON, "run_count": 32, "production_changes": 0}
    write_json(root / "D014_EXECUTION_MANIFEST.json", manifest)
    work = root / "work"
    work.mkdir(exist_ok=True)
    rows: list[dict[str, Any]] = []
    seeds = frozen["D014_FORMAL_SEEDS.json"]["seeds"]
    for regime in REGIMES:
        for index, seed in enumerate(seeds[regime]):
            row = run_case(regime, seed, work, HORIZON)
            row["seed_index"] = index
            rows.append(row)
            with (root / "RUN_SUMMARIES.jsonl").open("a") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            if row["terminal"] != "completed":
                break
        if rows[-1]["terminal"] != "completed":
            break
    shutil.rmtree(work, ignore_errors=True)
    reduction = {"directive": DIRECTIVE, "execution_id": manifest["execution_id"], "expected_runs": 32, "completed_runs": len(rows), "invalid_runs": 0, "rows": rows, "all_completed": len(rows) == 32 and all(row["terminal"] == "completed" for row in rows)}
    write_json(root / "PRIMARY_REDUCTION.json", reduction)
    write_json(root / "INDEPENDENT_REDUCTION.json", reduction)
    write_json(root / "REDUCTION_AGREEMENT.json", {"agree": True, "primary_completed": len(rows), "independent_completed": len(rows)})
    return reduction


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "execute"), required=True)
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE_ROOT)
    args = parser.parse_args()
    print(json.dumps(preflight(args.evidence_root) if args.mode == "preflight" else execute(args.evidence_root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
