"""D-012A1 campaign supervision and disposable dry-run tests."""
from __future__ import annotations
import json, os
from pathlib import Path
import pytest
from experiments.d012.active_runtime import ActiveRuntime
from experiments.d012.campaign_supervisor import CampaignSupervisor, freeze_hash
from experiments.d012.checkpoint_runner import recover_checkpoint, run_checkpoint
from experiments.d012.failure_codes import SupervisionError
from experiments.d012.process_identity import identity_matches, process_identity
from experiments.d012.progress_store import ProgressStore
from experiments.d012.organism_worker import organism_config
from experiments.d012.run_disposable_dry_run import run
from umbra_core.runtime import create_organism
EXP=Path(__file__).resolve().parents[1]/"experiments/d012"
def supervisor(tmp_path: Path, **kwargs) -> CampaignSupervisor:
    return CampaignSupervisor(tmp_path,"test-exec",tmp_path/"dry.sqlite",tmp_path/"evidence",freeze_hash(EXP),**kwargs)
def test_process_start_identity_rejects_pid_reuse():
    identity=process_identity(os.getpid()); assert identity and identity_matches(os.getpid(),identity); assert not identity_matches(os.getpid(),identity+"x")
def test_active_runtime_pause_resume_and_duplicate_interval():
    clock=ActiveRuntime(); clock.start(10); assert clock.stop(15)==5; clock.start(30); assert clock.stop(32)==7
    clock.start(40)
    with pytest.raises(ValueError,match="duplicate_interval"): clock.start(41)
    restored=ActiveRuntime.from_dict({"committed_seconds":7,"interval_started":None}); assert restored.committed_seconds==7
def test_progress_atomic_checksum_and_malformed_rejection(tmp_path):
    store=ProgressStore(tmp_path/"progress.json"); store.save({"x":1}); assert store.load()=={"x":1}
    (tmp_path/"progress.json").write_text("bad")
    with pytest.raises(SupervisionError,match="PROGRESS_STATE_CORRUPT"): store.load()
def test_atomic_lock_duplicate_and_stale_recovery(tmp_path):
    first=supervisor(tmp_path); first.acquire()
    with pytest.raises(SupervisionError,match="DUPLICATE_CAMPAIGN"): supervisor(tmp_path).acquire()
    lock=json.loads((tmp_path/"campaign.lock").read_text()); lock["identity"]="reused"; (tmp_path/"campaign.lock").write_text(json.dumps(lock))
    with pytest.raises(SupervisionError,match="STALE_LOCK_UNSAFE"): supervisor(tmp_path).acquire(reclaim_stale=True)
    recovered=supervisor(tmp_path); recovered.acquire(reclaim_stale=True,prior_classified=True); recovered.release(); assert list(tmp_path.glob("campaign.lock.stale.*"))
def test_launch_refusals_precede_database_mutation(tmp_path):
    wrong="0"*64
    with pytest.raises(SupervisionError,match="FREEZE_HASH_MISMATCH"): CampaignSupervisor(tmp_path,"x",tmp_path/"x.sqlite",tmp_path/"e",wrong)
    with pytest.raises(SupervisionError,match="D010_ENABLED"): supervisor(tmp_path,d010_enabled=True)
    with pytest.raises(SupervisionError,match="REAL_DEVICE_CONFIG_PROHIBITED"): supervisor(tmp_path,real_device=True)
    with pytest.raises(SupervisionError,match="NON_DISPOSABLE_DRY_RUN_DATABASE"): CampaignSupervisor(tmp_path,"x",Path("/tmp/outside-d012.sqlite"),tmp_path/"e",freeze_hash(EXP))
    with pytest.raises(SupervisionError,match="STARTING_COMMIT_MISMATCH"): CampaignSupervisor(tmp_path,"x",tmp_path/"x.sqlite",tmp_path/"e",freeze_hash(EXP),expected_starting_commit="wrong")
    assert not list(tmp_path.glob("*.sqlite"))
def test_checkpoint_atomicity_and_crash_recovery(tmp_path):
    db=tmp_path/"org.sqlite"; org=create_organism(organism_config(db)); org.run_ticks(2); org.close(); root=tmp_path/"cp"; root.mkdir()
    result=run_checkpoint(db,root,"C0"); assert result["raw_payload_count"]==0 and recover_checkpoint(root,"C0")
    with pytest.raises(SupervisionError,match="CHECKPOINT_INCOMPLETE"): run_checkpoint(db,root,"C1",fail_at="after_result")
    assert not recover_checkpoint(root,"C1"); assert list(root.glob("C1.*.quarantine"))
def test_disposable_real_runtime_dry_run_and_process_audit(tmp_path):
    result=run(tmp_path/"run"); assert result["events"]==19 and result["restarts"]==4 and result["checkpoints"]==5
    assert result["formal"] is False and result["d010_enabled"] is False and result["raw_payload_count"]==0
    assert not (tmp_path/"run/campaign.lock").exists()
    assert all(item["external_effect"]!="none" for item in result["trace"] if item["class"] in {"ENVIRONMENTAL_CHANGE","PARTNER_BEHAVIOR","BODY_CHANGE","PERCEPTION_INPUT"})
def test_harness_has_no_direct_internal_state_assignment():
    source=(EXP/"run_disposable_dry_run.py").read_text()
    for forbidden in (".phys =",".memory =",".social =",".individuality =",".identity =",".world_model ="):
        assert forbidden not in source
