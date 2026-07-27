"""Atomic disposable SQLite checkpoint transaction."""
from __future__ import annotations
import hashlib, json, os, sqlite3, time
from pathlib import Path
from umbra_core.persistence import Store
from .failure_codes import SupervisionError
def run_checkpoint(db_path: Path, root: Path, checkpoint_id: str, *, d010_enabled: bool = False, fail_at: str | None = None) -> dict[str, object]:
    if d010_enabled: raise SupervisionError("D010_ENABLED")
    work = root / f"{checkpoint_id}.partial.sqlite"
    final = root / f"{checkpoint_id}.sqlite"
    result_path = root / f"{checkpoint_id}.json"
    marker = root / f"{checkpoint_id}.complete"
    if fail_at == "before_copy": raise SupervisionError("CHECKPOINT_INCOMPLETE")
    source = sqlite3.connect(str(db_path)); target = sqlite3.connect(str(work))
    source.backup(target); target.close(); source.close()
    if fail_at == "during_copy": raise SupervisionError("CHECKPOINT_INCOMPLETE")
    os.replace(work, final)
    digest = hashlib.sha256(final.read_bytes()).hexdigest()
    if fail_at == "after_copy": raise SupervisionError("CHECKPOINT_INCOMPLETE")
    store = Store(final); store.validate_chain(); events = store.iter_events(); snap = store.load_snapshot(); store.close()
    raw_count = sum(json.dumps(e["payload"]).count('"raw_payload"') for e in events)
    result = {"checkpoint_id": checkpoint_id,"database_sha256":digest,"event_count":len(events),"snapshot_id":snap["snapshot_id"],"state_hash":snap["state_hash"],"raw_payload_count":raw_count,"d010_enabled":False,"completed_at":time.time()}
    tmp = result_path.with_suffix(".json.tmp"); tmp.write_text(json.dumps(result, sort_keys=True)); os.replace(tmp, result_path)
    if fail_at == "after_result": raise SupervisionError("CHECKPOINT_INCOMPLETE")
    marker.write_text(digest)
    return result
def recover_checkpoint(root: Path, checkpoint_id: str) -> bool:
    result, marker = root / f"{checkpoint_id}.json", root / f"{checkpoint_id}.complete"
    if result.exists() != marker.exists():
        for path in (root / f"{checkpoint_id}.partial.sqlite", root / f"{checkpoint_id}.sqlite", result, marker):
            if path.exists(): path.rename(path.with_suffix(path.suffix + ".quarantine"))
        return False
    return result.exists() and marker.exists()
