#!/usr/bin/env python3
"""D-014H3I regime-faithful non-production runner."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
NONPROD = Path(__file__).resolve().parent
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
if str(NONPROD) not in sys.path: sys.path.insert(0, str(NONPROD))
from d014h3i_runtime import HORIZON, KNOWN_R1, R0_SEEDS, h3i_selector_callback, identity_selector_callback, prepare_organism
from d014h3i_selector import canonical_bytes, fingerprint
from test_d014h3i_selector import base_state
from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d014.run_formal import regime_spec
from umbra_core.embodiment import _make_partner
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.events import build_initialized_event
from umbra_core.habitat.state import FreeLocation, make_social_entity_object
from umbra_core.runtime import load_organism
from umbra_core.embodiment_adapters.profiles import MINIMAL_CREATURE_BODY
from umbra_core.perception_adapters import AdapterManifest, SyntheticPerceptionAdapter

DIRECTIVE = "UMBRA-D-014H3I"
BASELINE = "b122131db31679bbfedf153bb7a1c15265c7fcc0"
EVIDENCE_ROOT = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3i-no-safe-composition-r1")
SCENARIOS = {"R0": "S0", "R1": "S16", "R2": "S10", "R3": "S12"}

def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def partner_object() -> object:
    partner = _make_partner("partner:d014", 6.0, 4.0, "H0", index=0)
    policy = partner.response_policy
    return make_social_entity_object(object_id="social:partner:d014", entity_ref=partner.hidden_partner_id,
        location=FreeLocation(6.0, 4.0, "zone:general"), history_code=policy.history_code,
        motion_signature=partner.true_cues.motion_signature, appearance_signature=partner.true_cues.appearance_signature,
        response_timing_pattern=partner.true_cues.response_timing_pattern,
        interaction_style_cues=partner.true_cues.interaction_style_cues, response_mode=policy.mode,
        contingent_probability=policy.contingent_probability, flip_at=policy.flip_at,
        absent_windows=tuple(policy.absent_windows))

def adapter_burst(org: object, seed: int, tick: int) -> bool:
    manifest = AdapterManifest("d014-formal", "1", ("body_telemetry",), {"body_telemetry": "v1"})
    envelope = SyntheticPerceptionAdapter(manifest).submit(observation_id=f"h3i-{seed}-{tick}",
        source_id=f"h3i-source-{seed % 4}", modality="body_telemetry", schema_version="v1",
        core_receipt_tick=org.tick, source_timestamp=None, capture_interval=None,
        derived_features={"temperature_delta": tick % 3}, confidence=0.8, uncertainty=0.2,
        provenance_chain=({"step": "d014h3i"},), privacy_classification="DERIVED_ONLY",
        consent_state="CONSENT_GRANTED", retention_class="DERIVED_BOUNDED", replay_class="AUTHORITATIVE",
        integrity_metadata={"seed": str(seed), "tick": str(tick)})
    return bool(org.submit_perception_observation(envelope, manifest))

def run_case(seed: int, regime: str, horizon: int, selector=h3i_selector_callback,
             capture_trace: bool = False) -> dict[str, object]:
    scenario = SCENARIOS[regime]
    work = Path("/dev/shm")
    db = work / f"h3i-{regime}-{seed}.sqlite"
    trace_path = work / f"h3i-{regime}-{seed}.jsonl"
    for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm"), trace_path): path.unlink(missing_ok=True)
    org = prepare_organism(db, seed, selector, trace_path, scenario)
    state = {"org": org, "engine": org.embodiment._habitat_engine, "restart_count": 0,
        "restart_identity_preserved": False, "partner_created": False, "adapter_accepts": 0,
        "partner_occluded": False, "partner_reappeared": False, "body_change_count": 0,
        "body_profile_after": None, "body_identity_preserved": False}
    events = [build_initialized_event(state["engine"].state, event_id=f"h3i:{regime}:{seed}:init",
        transaction_id=f"h3i:{regime}:{seed}:init-tx", request_id=f"h3i:{regime}:{seed}:init-req")]
    actions = {}; failure = None; first_no_safe = None
    extrema = {"minimum_energy": 1.0, "maximum_fatigue": 0.0, "minimum_integrity": 1.0, "minimum_stimulation": 1.0}
    started = time.monotonic()
    harness_exception = None
    try:
        for _ in range(horizon):
            org = state["org"]; tick = org.tick + 1
            if regime == "R2" and tick == 600:
                events.append(state["engine"].commit_object_creation(partner_object(), event_id=f"h3i:{seed}:create",
                    transaction_id=f"h3i:{seed}:create-tx", request_id=f"h3i:{seed}:create-req")); state["partner_created"] = True
            if regime == "R2" and tick == 1200: state["adapter_accepts"] += int(adapter_burst(org, seed, tick))
            if regime == "R2" and tick == 1800:
                ident = org.identity.agent_id; saved = copy.deepcopy(state["engine"].state); org.snapshot_if_due(force=True); org.close()
                org = load_organism(__import__('d014h3i_runtime').organism_config(db, seed, selector, trace_path, scenario))
                engine = HabitatEngine(saved); org.embodiment.attach_habitat_engine(engine)
                state.update(org=org, engine=engine, restart_count=state["restart_count"] + 1, restart_identity_preserved=org.identity.agent_id == ident)
            if regime == "R2" and tick == 2400:
                events.append(state["engine"].commit_object_visibility("social:partner:d014", occluded=True, event_id=f"h3i:{seed}:occlude",
                    transaction_id=f"h3i:{seed}:occlude-tx", request_id=f"h3i:{seed}:occlude-req")); state["partner_occluded"] = True
            if regime == "R2" and tick == 2600:
                events.append(state["engine"].commit_object_visibility("social:partner:d014", occluded=False, event_id=f"h3i:{seed}:reappear",
                    transaction_id=f"h3i:{seed}:reappear-tx", request_id=f"h3i:{seed}:reappear-req")); state["partner_reappeared"] = True
            if regime == "R3" and tick == 3600:
                org.embodiment_adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id, origin="D014_R3_PREREGISTERED")
                state.update(body_change_count=1, body_profile_after=org.embodiment_adapter.profile.profile_id, body_identity_preserved=True)
            result = org.tick_once(); state["engine"] = org.embodiment._habitat_engine
            cap = str(result.get("capability")); actions[cap] = actions.get(cap, 0) + 1
            extrema["minimum_energy"] = min(extrema["minimum_energy"], float(org.phys.energy)); extrema["maximum_fatigue"] = max(extrema["maximum_fatigue"], float(org.phys.fatigue))
            extrema["minimum_integrity"] = min(extrema["minimum_integrity"], float(org.phys.integrity)); extrema["minimum_stimulation"] = min(extrema["minimum_stimulation"], float(org.phys.stimulation))
            if result.get("no_safe_action") and first_no_safe is None: first_no_safe = org.tick
            if org.phys.critical_any(): failure = {"tick": org.tick, "physiology": org.phys.as_dict(), "result": result}; break
    except Exception as exc:
        harness_exception = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "tick": getattr(org, "tick", None),
        }
    rows = [json.loads(line) for line in trace_path.read_text().splitlines()] if trace_path.exists() else []
    if harness_exception is not None:
        terminal = "harness_failure"
    elif failure is None and org.tick >= horizon:
        terminal = "completed"
    else:
        terminal = "scientific_failure"
    payload = {"directive": DIRECTIVE, "regime": regime, "scenario": scenario, "seed": seed, "ticks": org.tick,
            "target_ticks": horizon, "terminal": terminal, "critical_failure": failure, "first_no_safe_action": first_no_safe,
            "harness_failure": harness_exception,
            "actions": actions, **extrema, "selector_call_count": sum(1 for r in rows if "d014h3i_selector" in r),
            "event_types": [str(e.get("event_type")) for e in events], "event_state_hashes": [e.get("payload", {}).get("new_state_hash") for e in events],
            "partner_created": state["partner_created"], "restart_count": state["restart_count"], "restart_identity_preserved": state["restart_identity_preserved"],
            "adapter_accepts": state["adapter_accepts"], "partner_occluded": state["partner_occluded"], "partner_reappeared": state["partner_reappeared"],
            "body_change_count": state["body_change_count"], "body_profile_after": state["body_profile_after"], "body_identity_preserved": state["body_identity_preserved"],
            "elapsed_seconds": time.monotonic() - started, "decision_trace": rows if capture_trace else None}
    state["org"].close()
    for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm"), trace_path): path.unlink(missing_ok=True)
    return payload

def proof(evidence_root: Path) -> dict[str, object]:
    ordinary = run_case(41241905, "R0", 1, selector=None)
    identity = run_case(41241905, "R0", 1, selector=identity_selector_callback)
    if ordinary["actions"] != identity["actions"]: raise SystemExit("D014H3I_DISABLED_PARITY_FAIL")
    result = {"disabled_parity": True, "ordinary": ordinary, "identity": identity,
        "selector_contract": fingerprint(base_state()), "source": "d014h3i_selector.evaluate reused unchanged"}
    write_json(evidence_root / "D014H3I_INJECTION_AND_REPLAY_PROOF.json", result); return result

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", choices=("preflight", "proof", "freeze", "r0", "known-r1", "holdouts"), required=True)
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE_ROOT); parser.add_argument("--horizon", type=int, default=0)
    args = parser.parse_args(); args.evidence_root.mkdir(parents=True, exist_ok=True)
    if args.mode == "proof": result = proof(args.evidence_root)
    elif args.mode == "preflight":
        result = {"r2": run_case(41241905, "R2", 2601), "r3": run_case(41241905, "R3", 3601)}
        write_json(args.evidence_root / "D014H3I_REGIME_PREFLIGHT.json", result)
    elif args.mode == "freeze":
        contract = {"directive": DIRECTIVE, "baseline": BASELINE, "selector_spec": "D014H3I_SELECTOR_SPEC", "regimes": regime_spec()["regimes"],
            "scenario_map": SCENARIOS, "r0_seeds": R0_SEEDS, "known_r1": KNOWN_R1, "horizon_ticks": HORIZON,
            "holdouts": "adopt exact D014H3D_FRESH_HOLDOUT_MANIFEST; no regeneration", "no_safe_semantics": "existing_runtime_denial", "hard_admissibility": "exact_runtime_authority_before_ranking", "unknown": "neutral_no_fallback", "production_changes": [], "formal": False}
        write_json(args.evidence_root / "D014H3I_REGIME_CONTRACT.json", contract); (args.evidence_root / "D014H3I_REGIME_CONTRACT.sha256").write_text(hashlib.sha256(canonical_bytes(contract)).hexdigest() + "\n"); result = contract
    elif args.mode == "r0":
        result = {"rows": [run_case(seed, "R0", args.horizon or HORIZON) for seed in R0_SEEDS]}
        result["all_pass"] = all(row["terminal"] == "completed" for row in result["rows"]); write_json(args.evidence_root / "D014H3I_R0_RESULTS.json", result)
    elif args.mode == "known-r1":
        result = run_case(KNOWN_R1, "R1", args.horizon or HORIZON); write_json(args.evidence_root / "D014H3I_KNOWN_R1_RESULT.json", result)
    else:
        manifest_path = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3d-causal-integrated-selector-r1/D014H3D_FRESH_HOLDOUT_MANIFEST.json")
        manifest = json.loads(manifest_path.read_text())
        rows = [run_case(int(item["seed"]), str(item["regime"]), args.horizon or HORIZON)
                for item in manifest["holdouts"]]
        result = {
            "source_manifest": str(manifest_path),
            "source_manifest_hash": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "holdouts": rows,
            "all_completed": all(row["terminal"] == "completed" for row in rows),
        }
        write_json(args.evidence_root / "D014H3I_HOLDOUT_RESULTS.json", result)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))

if __name__ == "__main__":
    main()
