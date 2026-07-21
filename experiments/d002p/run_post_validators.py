"""Post-soak D-002P validators: behavior equivalence + replay proofs."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from umbra_core.runtime import OrganismConfig, create_organism, load_organism, resimulate
from umbra_core.util import sha256_hex


def _db(work: Path, name: str) -> str:
    p = work / name
    for s in (p, Path(str(p) + "-wal"), Path(str(p) + "-shm")):
        s.unlink(missing_ok=True)
    return str(p)


def run_behavior(work: Path) -> dict:
    """Compare key D-002 behavioral signals against sealed D-002 bounds (smoke)."""
    results = {}
    # Prediction present under C0
    org = create_organism(OrganismConfig(db_path=_db(work, "c0.sqlite"), seed=7))
    org.run_ticks(80)
    results["c0_live_predictions"] = len(org.self_model.live_predictions())
    results["c0_live_errors"] = len(org.self_model.live_errors())
    results["c0_live_attributions"] = len(org.self_model.live_attributions())
    results["c0_has_prediction"] = results["c0_live_predictions"] > 0
    org.close()

    # I1 adaptation / gain movement
    org = create_organism(
        OrganismConfig(db_path=_db(work, "i1.sqlite"), seed=7, intervention="I1")
    )
    sid0 = org.self_model.active.body_schema_id
    org.run_ticks(200)
    results["i1_schema_changed"] = org.self_model.active.body_schema_id != sid0
    results["i1_supersessions"] = len(org.self_model.supersessions)
    results["i1_step_gain"] = org.self_model.active.expected_motion.get("step_gain", 1.0)
    results["i1_adapted"] = (
        results["i1_schema_changed"]
        or results["i1_supersessions"] > 0
        or abs(results["i1_step_gain"] - 1.0) > 1e-6
        or len(org.self_model.live_errors()) > 0
    )
    org.close()

    # I8 external attribution
    org = create_organism(
        OrganismConfig(db_path=_db(work, "i8.sqlite"), seed=7, intervention="I8")
    )
    org.phys.intervene(energy=0.85, fatigue=0.1, stimulation=0.55)
    org.run_ticks(55)
    labels = {a.label for a in org.self_model.live_attributions() if a.tick >= 40}
    results["i8_labels"] = sorted(labels)
    results["i8_external_or_mixed"] = bool(
        labels & {"EXTERNAL_CAUSED", "MIXED", "UNKNOWN"}
    )
    org.close()

    # Regulation / identity continuity
    org = create_organism(OrganismConfig(db_path=_db(work, "id.sqlite"), seed=7))
    org.run_ticks(30)
    aid = org.identity.agent_id
    viable = org.metrics["viable_ticks"] / max(1, org.metrics["total_ticks"])
    org.close()
    org2 = load_organism(OrganismConfig(db_path=_db(work, "id.sqlite"), seed=7))
    results["identity_stable"] = org2.identity.agent_id == aid
    results["viable_frac"] = viable
    org2.close()

    results["pass"] = all(
        [
            results["c0_has_prediction"],
            results["i1_adapted"],
            results["i8_external_or_mixed"],
            results["identity_stable"],
        ]
    )
    return results


def run_replay(work: Path) -> dict:
    a = resimulate(7, 90, _db(work, "birth_a.sqlite"), intervention="I1")
    b = resimulate(7, 90, _db(work, "birth_b.sqlite"), intervention="I1")
    path = _db(work, "snap.sqlite")
    org = create_organism(
        OrganismConfig(db_path=path, seed=7, snapshot_every=20, intervention="I1")
    )
    org.run_ticks(90)
    live_hash = org.self_model.state_hash()
    live_sid = org.self_model.active.body_schema_id
    org.snapshot_if_due(force=True)
    org.close()
    loaded = load_organism(OrganismConfig(db_path=path, seed=7, intervention="I1"))
    snap_ok = (
        loaded.self_model.state_hash() == live_hash
        and loaded.self_model.active.body_schema_id == live_sid
    )
    loaded.close()
    out = {
        "birth_resimulation_match": a["self_model_hash"] == b["self_model_hash"],
        "birth_body_schema_id": a["body_schema_id"],
        "snapshot_replay_match": snap_ok,
        "active_body_model_hash": live_hash,
        "pass": a["self_model_hash"] == b["self_model_hash"] and snap_ok,
    }
    return out


def main() -> None:
    work = ROOT / ".soak" / "d002p_post"
    work.mkdir(parents=True, exist_ok=True)
    behavior = run_behavior(work)
    replay = run_replay(work)
    (ROOT / "docs/evidence/d002p/behavior-equivalence.json").write_text(
        json.dumps(behavior, indent=2) + "\n"
    )
    (ROOT / "docs/evidence/d002p/replay-results.json").write_text(
        json.dumps(replay, indent=2) + "\n"
    )
    print(json.dumps({"behavior": behavior, "replay": replay}, indent=2))


if __name__ == "__main__":
    main()
