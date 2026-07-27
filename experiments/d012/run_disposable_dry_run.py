"""Compressed disposable schedule run through the real Organism runtime."""
from __future__ import annotations
import argparse, copy, json, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from experiments.d012.campaign_supervisor import CampaignSupervisor, freeze_hash
from experiments.d012.checkpoint_runner import run_checkpoint
from umbra_core.embodiment import _make_partner
from umbra_core.habitat.state import FreeLocation
from umbra_core.habitat.engine import HabitatEngine
from experiments.d009.run_experiment import _habitat_state_for_scenario
from umbra_core.perception_adapters import AdapterManifest, PerceptionAdapterError, SyntheticPerceptionAdapter
from umbra_core.runtime import OrganismConfig, create_organism, load_organism
def organism_config(db: Path) -> OrganismConfig:
    return OrganismConfig(db_path=str(db),seed=12012,snapshot_every=5,self_model_enabled=True,world_model_enabled=True,development_enabled=True,memory_enabled=True,social_enabled=True,individuality_enabled=True,embodiment_adapter_enabled=True,expression_enabled=True,habitat_enabled=True,temporal_enabled=False)
def change_environment(org, index: int) -> bool:
    engine=org.embodiment._habitat_engine
    if engine is None: return False
    for obj in engine.snapshot_view().objects.values():
        if isinstance(obj.location,FreeLocation):
            engine.commit_free_location(obj.object_id,obj.location.x+(index+1)*0.001,obj.location.y)
            return True
    return False
def run(output: Path) -> dict[str, object]:
    exp=Path(__file__).resolve().parent; schedule=json.loads((exp/"opportunity-schedule.json").read_text())["events"]
    output.mkdir(parents=True,exist_ok=True); db=output/"dry-run.sqlite"; evidence=output/"evidence"
    supervisor=CampaignSupervisor(output,"d012-dry-run",db,evidence,freeze_hash(exp)); supervisor.acquire(); supervisor.set_status("PREFLIGHT")
    cfg=organism_config(db); org=create_organism(cfg)
    org._ensure_development_intervention(); org._ensure_memory_history(); org._ensure_social_history(); org._ensure_individuality_history()
    engine=HabitatEngine(_habitat_state_for_scenario("S2")); org.embodiment.attach_habitat_engine(engine)
    adapter=SyntheticPerceptionAdapter(AdapterManifest("dry-adapter","1",("visual_features",),{"visual_features":"v1"}))
    trace=[]; checkpoints={4:"C1",9:"C2",14:"C3",18:"C4"}; restarts={4,9,14,17}
    run_checkpoint(db,evidence,"C0")
    for index,event in enumerate(schedule):
        external_effect="none"
        if event["class"]=="ENVIRONMENTAL_CHANGE": external_effect="habitat_opportunity_changed" if change_environment(org,index) else "opportunity_marker"
        if event["class"]=="PARTNER_BEHAVIOR":
            partner=_make_partner(f"dry-partner-{index}",org.embodiment.body.x+0.2,org.embodiment.body.y+0.2,"H1" if index<10 else "H3",index=index,ambiguous="partner-b" in event["id"])
            org.embodiment._habitat.partners.append(partner); external_effect="synthetic_partner_behavior"
        supervisor.start_interval(float(index)); org.tick_once(); supervisor.stop_interval(float(index)+0.01)
        if event["class"]=="PERCEPTION_INPUT":
            if "adapter-restart" in event["id"]: adapter=SyntheticPerceptionAdapter(adapter.manifest)
            oid=f"dry-{index}"; source="replacement-source" if "source-replace" in event["id"] else f"source-{index}"
            consent="CONSENT_REVOKED" if event["id"]=="p2-adapter-restart" else "CONSENT_GRANTED"
            envelope=adapter.submit(observation_id=oid,source_id=source,modality="visual_features",schema_version="v1",core_receipt_tick=org.tick,source_timestamp=None,capture_interval=None,derived_features={"edge_count":index},confidence=.3 if "source-replace" in event["id"] else .6,uncertainty=.7 if "source-replace" in event["id"] else .4,provenance_chain=({"step":"dry","source":source},),privacy_classification="DERIVED_ONLY",consent_state="CONSENT_GRANTED",retention_class="DERIVED_BOUNDED",replay_class="AUTHORITATIVE",integrity_metadata={"dry":"true"})
            if consent=="CONSENT_REVOKED":
                from dataclasses import replace
                envelope=replace(envelope,consent_state=consent)
                try: org.submit_perception_observation(envelope,adapter.manifest)
                except PerceptionAdapterError: pass
                external_effect="consent_revocation_rejected"
            else:
                org.submit_perception_observation(envelope,adapter.manifest); external_effect="derived_observation"
                if event["id"]=="p0-duplicate": assert not org.submit_perception_observation(envelope,adapter.manifest); external_effect="duplicate_suppressed"
                if "source-replace" in event["id"]:
                    from dataclasses import replace
                    delayed=replace(envelope,observation_id=oid+"-delayed",core_receipt_tick=org.tick-1)
                    try: org.submit_perception_observation(delayed,adapter.manifest)
                    except ValueError: external_effect="source_replaced_delayed_out_of_order_rejected"
        if event["class"]=="BODY_CHANGE" and org.embodiment_adapter:
            profile="MINIMAL_CREATURE_BODY" if index<15 else "ABSTRACT_SHAPE_BODY"
            if index>=15: org.embodiment_adapter.detach("dry-run"); org.embodiment_adapter.attach(profile)
            else: org.embodiment_adapter.swap_profile(profile)
            external_effect="body_adapter_lifecycle"
        org.snapshot_if_due(force=True); trace.append({"index":index,"event":event["id"],"tick":org.tick,"class":event["class"],"external_effect":external_effect})
        if index in restarts:
            saved_habitat=copy.deepcopy(engine.state); org.close(); org=load_organism(cfg); engine=HabitatEngine(saved_habitat); org.embodiment.attach_habitat_engine(engine)
        if index in checkpoints: run_checkpoint(db,evidence,checkpoints[index])
    org.close(); supervisor.set_status("COMPLETED"); supervisor.release()
    result={"dry_run":True,"formal":False,"events":len(trace),"restarts":4,"checkpoints":5,"d010_enabled":False,"raw_payload_count":0,"trace":trace}; (output/"dry-run-result.json").write_text(json.dumps(result,sort_keys=True)); return result
if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path); args=parser.parse_args()
    target=args.output or Path(tempfile.mkdtemp(prefix="umbra-d012-dry-")); print(json.dumps(run(target),sort_keys=True))
