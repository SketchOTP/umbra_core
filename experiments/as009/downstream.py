"""AS-009 post-population lifecycle, boundedness, soak, and ablation tooling."""
from __future__ import annotations

import argparse, copy, json, os, resource, time
from pathlib import Path
from typing import Any

from experiments.as009.qualification import BASELINE, SCENARIOS, partner_object
from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d014.run_formal import config as d014_config
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism, load_organism
from umbra_core.world_model import condition_to_world_model_config
from umbra_core.util import current_rss_mib

EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-009-r2-r3-habitat-authority-integrated-qualification-r1")


def cfg(seed: int, db: Path, *, route: bool = True, bounded: bool = False):
    value = d014_config(seed, db, "R0")
    value.bounded_continuation_enabled = bounded
    wc = value.world_model_config or condition_to_world_model_config("C0")
    wc.route_demand_learning_enabled = route
    value.world_model_config = wc
    return value


def cleanup(db: Path) -> None:
    for p in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm")): p.unlink(missing_ok=True)


def lifecycle(seed: int, work: Path) -> dict[str, Any]:
    db = work / "lifecycle.sqlite"; org = create_organism(cfg(seed, db)); identity = org.identity.as_dict()
    for method in ("_ensure_development_intervention", "_ensure_memory_history", "_ensure_social_history", "_ensure_individuality_history"): getattr(org, method)()
    engine = HabitatEngine(_habitat_state_for_scenario("S10")); org.embodiment.attach_habitat_engine(engine)
    engine.commit_object_creation(partner_object(), event_id=f"as009:life:create:{seed}", transaction_id=f"as009:life:create-txn:{seed}", request_id=f"as009:life:create-req:{seed}")
    org.run_ticks(300); org.snapshot_if_due(force=True); org.close()
    org = load_organism(cfg(seed, db)); engine = HabitatEngine(copy.deepcopy(engine.state)); org.embodiment.attach_habitat_engine(engine)
    restart_ok = org.identity.as_dict() == identity and len(engine.authoritative_social_entities()) == 1
    org.run_ticks(100); org.close()
    org = load_organism(cfg(seed, db)); old_body = org.embodiment_adapter.state.body_instance_id
    memory_before = org.memory.to_state(); social_before = org.social.to_state(); indiv_before = org.individuality.to_state()
    replacement = org.replace_physical_body(new_profile_id="MINIMAL_CREATURE_BODY", reason="as009_lifecycle")
    replacement_ok = (org.identity.as_dict() == identity and replacement["new_body_instance_id"] != old_body and org.embodiment.body_occupancy_view().body_instance_id == replacement["new_body_instance_id"] and org.self_model.body_binding_id == replacement["new_body_binding_id"])
    owners_preserved = org.memory.to_state() == memory_before and org.social.to_state() == social_before and org.individuality.to_state() == indiv_before
    org.snapshot_if_due(force=True); org.close(); org = load_organism(cfg(seed, db)); post_restart = org.identity.as_dict() == identity and org.embodiment_adapter.state.body_instance_id == replacement["new_body_instance_id"]
    org.embodiment_adapter.swap_profile("ABSTRACT_SHAPE_BODY", origin="AS009_LIFECYCLE_PROFILE_SWAP")
    profile_ok = org.embodiment_adapter.state.body_instance_id == replacement["new_body_instance_id"] and org.embodiment.body_occupancy_view().body_instance_id == replacement["new_body_instance_id"]
    org.run_ticks(100); org.store.validate_chain(); ticks = org.tick; org.close(); cleanup(db)
    checks = {"restart_identity_and_habitat": restart_ok, "true_body_replacement": replacement_ok, "owner_continuity": owners_preserved, "post_replacement_restart": post_restart, "compatible_profile_swap": profile_ok, "continued_after_replacement": ticks >= 200}
    return {"schema":"AS009_LIFECYCLE_RESULT_V1","directive":"UMBRA-AS-009","baseline":BASELINE,"seed":seed,"checks":checks,"pass":all(checks.values()),"ticks_after_replacement":ticks,"route_learning_source_enabled":True}


def boundedness(seed: int, work: Path, ticks: int = 100_000) -> dict[str, Any]:
    db = work / "boundedness.sqlite"; org = create_organism(cfg(seed, db));
    for method in ("_ensure_development_intervention", "_ensure_memory_history", "_ensure_social_history", "_ensure_individuality_history"): getattr(org, method)()
    samples=[]; t0=time.perf_counter(); cpu0=time.process_time();
    for i in range(ticks):
        org.tick_once()
        if i == 0 or (i+1) % 5000 == 0: samples.append({"tick":i+1,"rss_mib":current_rss_mib(),"t":time.perf_counter()-t0})
    before = org.authoritative_state(); org.snapshot_if_due(force=True); org.close(); restored=load_organism(cfg(seed, db)); restart_ok=restored.authoritative_state()["identity"] == before["identity"] and restored.tick == before["tick"]; events=restored.store.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]; restored.close(); size=sum(p.stat().st_size for p in (db,Path(str(db)+"-wal"),Path(str(db)+"-shm")) if p.exists()); cleanup(db)
    rss=[x["rss_mib"] for x in samples]; elapsed=time.perf_counter()-t0; result={"schema":"AS009_BOUNDEDNESS_RESULT_V1","directive":"UMBRA-AS-009","baseline":BASELINE,"seed":seed,"ticks":ticks,"elapsed_seconds":elapsed,"cpu_seconds":time.process_time()-cpu0,"rss_p95_mib":sorted(rss)[int(.95*(len(rss)-1))],"rss_peak_mib":max(rss),"rss_samples":samples,"event_count":events,"database_bytes":size,"restart_continuity":restart_ok,"counts_bounded":events <= ticks*32,"pass":ticks==100_000 and restart_ok and events <= ticks*32}
    return result


def soak(seed: int, work: Path, seconds: float = 3600.0) -> dict[str, Any]:
    db=work/"soak.sqlite"; org=create_organism(cfg(seed,db));
    for method in ("_ensure_development_intervention", "_ensure_memory_history", "_ensure_social_history", "_ensure_individuality_history"): getattr(org, method)()
    r0=current_rss_mib(); c0=time.process_time(); t0=time.perf_counter(); ticks=org.run_realtime(seconds); elapsed=time.perf_counter()-t0; cpu=time.process_time()-c0; r1=current_rss_mib(); org.snapshot_if_due(force=True); org.store.validate_chain(); events=org.store.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]; org.close(); size=sum(p.stat().st_size for p in (db,Path(str(db)+"-wal"),Path(str(db)+"-shm")) if p.exists()); cleanup(db)
    return {"schema":"AS009_REALTIME_SOAK_RESULT_V1","directive":"UMBRA-AS-009","baseline":BASELINE,"seed":seed,"seconds_requested":seconds,"seconds_actual":elapsed,"ticks":ticks,"hz":ticks/max(elapsed,1e-9),"rss_start_mib":r0,"rss_end_mib":r1,"cpu_fraction_one_core":cpu/max(elapsed,1e-9),"event_count":events,"database_bytes":size,"pass":elapsed >= seconds*.99 and events <= ticks*32}


def ablation(seed: int, work: Path, variant: str) -> dict[str, Any]:
    db=work/f"{variant}.sqlite"; org=create_organism(cfg(seed,db,route=variant != "route_learning_disabled",bounded=variant != "continuation_disabled"));
    for method in ("_ensure_development_intervention", "_ensure_memory_history", "_ensure_social_history", "_ensure_individuality_history"): getattr(org, method)()
    readiness_calls=0
    if variant == "terminal_readiness_disabled":
        original=org._candidate_executability
        def permissive(candidate):
            nonlocal readiness_calls
            readiness_calls += 1
            if candidate.capability in {"CHARGE","REST","INSPECT"}: return "EXECUTABLE"
            return original(candidate)
        org._candidate_executability=permissive
    org.run_ticks(7200); result={"variant":variant,"seed":seed,"ticks":org.tick,"critical_violations":org.metrics["critical_violations"],"no_safe_action_ticks":org.metrics.get("no_safe_action",0),"actions":dict(org.metrics["actions"]),"readiness_calls":readiness_calls,"route_learning_enabled":variant != "route_learning_disabled","continuation_enabled":variant != "continuation_disabled"}; org.close(); cleanup(db); return result


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--mode",choices=("lifecycle","boundedness","soak","ablation"),required=True); p.add_argument("--seed",type=int,required=True); p.add_argument("--work",type=Path,required=True); p.add_argument("--seconds",type=float,default=3600); p.add_argument("--variant",default="full"); p.add_argument("--output",type=Path,required=True); a=p.parse_args(); a.work.mkdir(parents=True,exist_ok=False)
    if a.mode=="lifecycle": out=lifecycle(a.seed,a.work)
    elif a.mode=="boundedness": out=boundedness(a.seed,a.work)
    elif a.mode=="soak": out=soak(a.seed,a.work,a.seconds)
    else: out=ablation(a.seed,a.work,a.variant)
    a.output.parent.mkdir(parents=True,exist_ok=True); payload=(json.dumps(out,indent=2,sort_keys=True)+"\n").encode(); temp=a.output.with_name("."+a.output.name+".tmp"); fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o640); os.write(fd,payload); os.fsync(fd); os.close(fd); os.replace(temp,a.output); print(json.dumps(out,indent=2,sort_keys=True))


if __name__ == "__main__": main()
