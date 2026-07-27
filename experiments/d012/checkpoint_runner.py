"""Atomic disposable SQLite checkpoint transaction."""
from __future__ import annotations
import hashlib, json, os, sqlite3, time
from pathlib import Path
from umbra_core.persistence import Store
from .database_ownership import assert_quiescent
from .durability import atomic_write_text, fsync_directory
from .failure_codes import SupervisionError
def run_checkpoint(db_path: Path, root: Path, checkpoint_id: str, *, ownership_path: Path | None = None, d010_enabled: bool = False, fail_at: str | None = None) -> dict[str, object]:
    if d010_enabled: raise SupervisionError("D010_ENABLED")
    if ownership_path is not None: assert_quiescent(ownership_path)
    root.mkdir(parents=True, exist_ok=True)
    work = root / f"{checkpoint_id}.partial.sqlite"
    final = root / f"{checkpoint_id}.sqlite"
    result_path = root / f"{checkpoint_id}.json"
    marker = root / f"{checkpoint_id}.complete"
    if any(path.exists() for path in (work, final, result_path, marker)):
        raise SupervisionError("CHECKPOINT_INCOMPLETE","checkpoint_identity_exists")
    if fail_at == "before_copy": raise SupervisionError("CHECKPOINT_INCOMPLETE")
    source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True); target = sqlite3.connect(str(work))
    source.backup(target); target.close(); source.close()
    if fail_at == "during_copy": raise SupervisionError("CHECKPOINT_INCOMPLETE")
    os.replace(work, final)
    with final.open("rb") as handle: os.fsync(handle.fileno())
    fsync_directory(root)
    if fail_at == "after_copy_before_hash": raise SupervisionError("CHECKPOINT_INCOMPLETE")
    digest = hashlib.sha256(final.read_bytes()).hexdigest()
    if fail_at in {"after_copy","after_hash_before_result"}: raise SupervisionError("CHECKPOINT_INCOMPLETE")
    store = Store(final); store.validate_chain(); events = store.iter_events(); snap = store.load_snapshot(); store.close()
    raw_count = sum(json.dumps(e["payload"]).count('"raw_payload"') for e in events)
    result = {"checkpoint_id": checkpoint_id,"database_sha256":digest,"event_count":len(events),"snapshot_id":snap["snapshot_id"],"state_hash":snap["state_hash"],"raw_payload_count":raw_count,"d010_enabled":False,"completed_at":time.time()}
    atomic_write_text(result_path, json.dumps(result, sort_keys=True))
    if fail_at == "after_result": raise SupervisionError("CHECKPOINT_INCOMPLETE")
    atomic_write_text(marker, digest)
    return result
def recover_checkpoint(root: Path, checkpoint_id: str) -> bool:
    result, marker = root / f"{checkpoint_id}.json", root / f"{checkpoint_id}.complete"
    partial, database = root / f"{checkpoint_id}.partial.sqlite", root / f"{checkpoint_id}.sqlite"
    if result.exists() and marker.exists():
        return database.exists() and marker.read_text() == hashlib.sha256(database.read_bytes()).hexdigest()
    for path in (partial, database, result, marker):
        if path.exists(): path.rename(path.with_suffix(path.suffix + ".quarantine"))
    return False
