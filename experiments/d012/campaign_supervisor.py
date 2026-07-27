"""Single-owner disposable D-012 campaign supervisor."""
from __future__ import annotations
import hashlib, json, os, subprocess, time
from pathlib import Path
from .active_runtime import ActiveRuntime
from .durability import fsync_directory
from .failure_codes import SupervisionError
from .process_identity import identity_matches, process_identity
from .progress_store import ProgressStore
from .worker_protocol import BoundedLog
STATUSES = {"CREATED","PREFLIGHT","RUNNING","CHECKPOINTING","RESTARTING","PAUSED_INFRASTRUCTURE","COMPLETED","FAILED_SCIENTIFIC","FAILED_INFRASTRUCTURE","ABORTED_SAFETY"}
def freeze_hash(root: Path) -> str:
    names = ["opportunity-schedule.json","intervention-schedule.json","checkpoint-schedule.json","restart-schedule.json","body-change-schedule.json","perception-schedule.json","active-runtime-policy.json","failure-classification.json","thresholds.json","experiment-matrix.json","performance-protocol.json","replay-protocol.json","corruption-protocol.json"]
    h = hashlib.sha256()
    for name in names: h.update(name.encode()); h.update((root / name).read_bytes())
    return h.hexdigest()
class CampaignSupervisor:
    def __init__(self, root: Path, execution_id: str, database_path: Path, evidence_root: Path, expected_freeze_hash: str, *, d010_enabled: bool=False, real_device: bool=False, expected_starting_commit: str | None=None) -> None:
        if d010_enabled: raise SupervisionError("D010_ENABLED")
        if real_device: raise SupervisionError("REAL_DEVICE_CONFIG_PROHIBITED")
        root, database_path, evidence_root = root.resolve(), database_path.resolve(), evidence_root.resolve()
        if root not in database_path.parents: raise SupervisionError("NON_DISPOSABLE_DRY_RUN_DATABASE")
        if root not in evidence_root.parents and evidence_root != root: raise SupervisionError("EVIDENCE_PATH_INVALID")
        actual = freeze_hash(Path(__file__).resolve().parent)
        if actual != expected_freeze_hash: raise SupervisionError("FREEZE_HASH_MISMATCH")
        current_commit=subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip()
        if expected_starting_commit is not None and current_commit != expected_starting_commit: raise SupervisionError("STARTING_COMMIT_MISMATCH")
        self.root, self.execution_id, self.database_path, self.evidence_root = root, execution_id, database_path, evidence_root
        self.lock_path, self.progress = root / "campaign.lock", ProgressStore(root / "progress.json")
        self.log = BoundedLog(root / "supervisor.log", execution_id)
        self.runtime = ActiveRuntime(); self.state = self._state("CREATED", actual)
    def _state(self, status: str, freeze: str) -> dict[str, object]:
        now=time.time(); pid=os.getpid(); identity=process_identity(pid)
        return {"formal_execution_id":self.execution_id,"freeze_manifest_hash":freeze,"starting_commit":subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(),"database_path":str(self.database_path),"organism_pid":None,"organism_process_start_identity":None,"supervisor_pid":pid,"supervisor_process_start_identity":identity,"active_runtime_seconds":0.0,"wall_clock_started_at":now,"last_heartbeat_at":now,"last_completed_schedule_event":None,"last_completed_checkpoint":None,"pending_restart":None,"campaign_status":status,"termination_reason":None,"evidence_root":str(self.evidence_root)}
    def acquire(self, *, reclaim_stale: bool=False, prior_classified: bool=False) -> None:
        self.root.mkdir(parents=True, exist_ok=True); self.evidence_root.mkdir(parents=True, exist_ok=True)
        try:
            fd=os.open(self.lock_path, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
        except FileExistsError:
            old=json.loads(self.lock_path.read_text()); alive=identity_matches(int(old["pid"]), str(old["identity"]))
            if alive: raise SupervisionError("DUPLICATE_CAMPAIGN")
            if not reclaim_stale or not prior_classified: raise SupervisionError("STALE_LOCK_UNSAFE")
            self.lock_path.rename(self.root / f"campaign.lock.stale.{int(time.time())}"); return self.acquire()
        with os.fdopen(fd,"w") as handle:
            json.dump({"execution_id":self.execution_id,"pid":os.getpid(),"identity":process_identity(os.getpid()),"database":str(self.database_path)},handle,sort_keys=True)
            handle.flush(); os.fsync(handle.fileno())
        fsync_directory(self.root)
        self.progress.save(self.state)
        self.log.write("campaign_acquired", supervisor_pid=os.getpid())
    def set_status(self, status: str) -> None:
        if status not in STATUSES: raise ValueError(status)
        self.state["campaign_status"]=status; self.progress.save(self.state)
    def start_interval(self, now: float) -> None: self.runtime.start(now)
    def stop_interval(self, now: float) -> None:
        self.state["active_runtime_seconds"]=self.runtime.stop(now); self.progress.save(self.state)
    def heartbeat(self) -> None:
        self.state["last_heartbeat_at"]=time.time(); self.progress.save(self.state)
    def attach_worker(self, pid: int, identity: str, generation: int) -> None:
        if pid == os.getpid() or identity == self.state["supervisor_process_start_identity"]:
            raise SupervisionError("PID_IDENTITY_MISMATCH")
        if not identity_matches(pid, identity):
            raise SupervisionError("PID_IDENTITY_MISMATCH")
        self.state["organism_pid"]=pid
        self.state["organism_process_start_identity"]=identity
        self.state["worker_generation"]=generation
        self.progress.save(self.state)
        self.log.write("worker_attached", worker_pid=pid, worker_generation=generation)
    def complete_event(self, event_id: str) -> None:
        self.state["last_completed_schedule_event"]=event_id
        self.progress.save(self.state)
    def complete_checkpoint(self, checkpoint_id: str) -> None:
        self.state["last_completed_checkpoint"]=checkpoint_id
        self.progress.save(self.state)
    def record_worker_status(self, status: dict[str, object]) -> None:
        if status.get("process_start_identity") != self.state["organism_process_start_identity"]:
            raise SupervisionError("IPC_IDENTITY_MISMATCH")
        self.state["worker_ipc_sequence"]=status["sequence"]
        self.state["worker_chain_tip"]=status.get("chain_tip")
        self.state["worker_generation"]=status["generation"]
        self.progress.save(self.state)
    def recover(self) -> None:
        state=self.progress.load()
        pid=int(state["supervisor_pid"]); identity=str(state["supervisor_process_start_identity"])
        if pid != os.getpid() and identity_matches(pid,identity): raise SupervisionError("DUPLICATE_CAMPAIGN")
        self.state=state; self.runtime=ActiveRuntime(float(state["active_runtime_seconds"]),None)
    def recover_after_crash(self, *, prior_classified: bool) -> dict[str, object]:
        if not prior_classified:
            raise SupervisionError("STALE_LOCK_UNSAFE")
        state=self.progress.load()
        old_pid=int(state["supervisor_pid"])
        old_identity=str(state["supervisor_process_start_identity"])
        if identity_matches(old_pid,old_identity):
            raise SupervisionError("DUPLICATE_CAMPAIGN")
        worker_pid=int(state["organism_pid"])
        worker_identity=str(state["organism_process_start_identity"])
        if not identity_matches(worker_pid,worker_identity):
            raise SupervisionError("SUPERVISOR_RECOVERY_FAILED","worker_absent")
        try: lock=json.loads(self.lock_path.read_text())
        except (OSError,json.JSONDecodeError) as exc:
            raise SupervisionError("SUPERVISOR_RECOVERY_FAILED","lock") from exc
        if lock.get("execution_id") != self.execution_id or lock.get("database") != str(self.database_path):
            raise SupervisionError("SUPERVISOR_RECOVERY_FAILED","lock_binding")
        self.lock_path.rename(self.root / f"campaign.lock.stale.{int(time.time_ns())}")
        fd=os.open(self.lock_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        pid=os.getpid(); identity=process_identity(pid)
        with os.fdopen(fd,"w") as handle:
            json.dump({"execution_id":self.execution_id,"pid":pid,"identity":identity,"database":str(self.database_path)},handle,sort_keys=True)
            handle.flush(); os.fsync(handle.fileno())
        fsync_directory(self.root)
        state["supervisor_pid"]=pid
        state["supervisor_process_start_identity"]=identity
        state["last_heartbeat_at"]=time.time()
        self.state=state
        self.runtime=ActiveRuntime(float(state["active_runtime_seconds"]),None)
        self.progress.save(self.state)
        self.log.write("supervisor_recovered",previous_supervisor_pid=old_pid,worker_pid=worker_pid)
        return state
    def release(self) -> None:
        self.log.write("campaign_released", status=self.state["campaign_status"])
        if self.lock_path.exists():
            lock=json.loads(self.lock_path.read_text())
            if lock.get("execution_id") != self.execution_id or lock.get("pid") != os.getpid():
                raise SupervisionError("SUPERVISOR_RECOVERY_FAILED","lock_not_owned")
            self.lock_path.unlink()
            fsync_directory(self.root)
