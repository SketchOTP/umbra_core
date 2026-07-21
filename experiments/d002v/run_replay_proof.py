"""D-002V birth vs snapshot replay proof (no soak dependency)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from umbra_core.persistence import PersistenceError
from umbra_core.runtime import OrganismConfig, create_organism, load_organism, resimulate
from umbra_core.util import sha256_hex


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/d002v" / "replay-results.json"


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        seed, ticks = 77, 100
        path = td_path / "live.sqlite"
        org = create_organism(
            OrganismConfig(db_path=str(path), seed=seed, snapshot_every=20, intervention="I1")
        )
        org.run_ticks(ticks)
        live = {
            "self_model_hash": org.self_model.state_hash(),
            "body_schema_id": org.self_model.active.body_schema_id,
            "supersessions": list(org.self_model.supersessions),
            "affordances": dict(org.self_model.active.reachable_affordances),
            "agent_id": org.identity.agent_id,
        }
        # Count diagnostic ledger rows — must not be required for reconstruction.
        pe_n = sum(1 for e in org.store.iter_events() if e["event_type"] == "prediction_error")
        attr_n = sum(1 for e in org.store.iter_events() if e["event_type"] == "self_attribution")
        org.store.validate_chain()
        org.snapshot_if_due(force=True)
        org.close()

        snap_org = load_organism(
            OrganismConfig(db_path=str(path), seed=seed, intervention="I1")
        )
        snap = {
            "self_model_hash": snap_org.self_model.state_hash(),
            "body_schema_id": snap_org.self_model.active.body_schema_id,
            "supersessions": list(snap_org.self_model.supersessions),
            "affordances": dict(snap_org.self_model.active.reachable_affordances),
            "agent_id": snap_org.identity.agent_id,
        }
        snap_org.store.validate_chain()
        snap_org.close()

        birth = resimulate(seed, ticks, str(td_path / "birth.sqlite"), intervention="I1")
        # Birth path never loaded the live DB snapshots.
        birth_match = (
            birth["self_model_hash"] == live["self_model_hash"]
            and birth["body_schema_id"] == live["body_schema_id"]
        )
        snap_match = snap == live

        # Fail-closed: gap authoritative supersede mid-chain
        path2 = td_path / "corrupt.sqlite"
        org2 = create_organism(OrganismConfig(db_path=str(path2), seed=88, intervention="I1"))
        for i in range(25):
            org2.self_model.record_dimension_evidence("movement_gain", 0.55, tick=i)
        org2.store.append_event(
            agent_id=org2.identity.agent_id,
            event_type="body_schema_supersede",
            monotonic_time=0.0,
            wall_time=0.0,
            payload={"active_schema_id": org2.self_model.active.body_schema_id},
        )
        org2.store.append_event(
            agent_id=org2.identity.agent_id,
            event_type="lifecycle",
            monotonic_time=0.0,
            wall_time=0.0,
            payload={"note": "trailer"},
        )
        seq = org2.store.conn.execute(
            "SELECT sequence FROM events WHERE event_type='body_schema_supersede' LIMIT 1"
        ).fetchone()[0]
        org2.store.conn.execute("DELETE FROM events WHERE sequence=?", (seq,))
        org2.store.conn.commit()
        corruption_raises = False
        try:
            org2.store.validate_chain()
        except PersistenceError:
            corruption_raises = True
        org2.close()

        # Snapshot self_model hash tamper
        path3 = td_path / "hashbad.sqlite"
        org3 = create_organism(OrganismConfig(db_path=str(path3), seed=89))
        org3.run_ticks(10)
        org3.snapshot_if_due(force=True)
        org3.close()
        bad = load_organism(OrganismConfig(db_path=str(path3), seed=89))
        s = bad.store.load_snapshot()
        st = s["state"]
        st["self_model"]["state_hash"] = "0" * 64
        ss = json.dumps(st, sort_keys=True, separators=(",", ":"), default=str)
        bad.store.conn.execute(
            "UPDATE snapshots SET state_json=?, state_hash=? WHERE snapshot_id=?",
            (ss, sha256_hex(ss), s["snapshot_id"]),
        )
        bad.close()
        hash_tamper_raises = False
        try:
            load_organism(OrganismConfig(db_path=str(path3), seed=89))
        except PersistenceError:
            hash_tamper_raises = True

        result = {
            "birth_replay": {
                "pass": birth_match,
                "self_model_hash": birth["self_model_hash"],
                "body_schema_id": birth["body_schema_id"],
                "relied_on_later_snapshot": False,
            },
            "snapshot_replay": {
                "pass": snap_match,
                "self_model_hash": snap["self_model_hash"],
                "body_schema_id": snap["body_schema_id"],
            },
            "identical_active_body_model_hash": live["self_model_hash"]
            == snap["self_model_hash"]
            == birth["self_model_hash"],
            "identical_supersession_history": live["supersessions"] == snap["supersessions"],
            "identical_capability_compatibility": live["affordances"] == snap["affordances"],
            "diagnostic_ledger_samples_present": {"prediction_error": pe_n, "self_attribution": attr_n},
            "corruption_missing_authoritative_fails_closed": corruption_raises,
            "corruption_snapshot_hash_fails_closed": hash_tamper_raises,
            "gate3_pass": bool(
                birth_match
                and snap_match
                and live["supersessions"] == snap["supersessions"]
                and live["affordances"] == snap["affordances"]
                and corruption_raises
                and hash_tamper_raises
            ),
        }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
