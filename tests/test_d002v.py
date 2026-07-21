"""UMBRA-D-002V — RSS method + self-model event authority + replay proofs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from umbra_core.events import (
    AUTHORITATIVE_EVENT_TYPES,
    DIAGNOSTIC_EVENT_TYPES,
    DIAGNOSTIC_SELF_MODEL_SAMPLE_EVERY_TICKS,
    PREDICTION_HISTORY_BOUND,
    SELF_MODEL_EVENT_AUTHORITY,
    SELF_MODEL_LEDGER_ALIASES,
    is_authoritative,
    is_diagnostic,
    self_model_authority_class,
)
from umbra_core.persistence import PersistenceError
from umbra_core.runtime import OrganismConfig, create_organism, load_organism, resimulate
from umbra_core.self_model import MAX_PREDICTION_HISTORY
from umbra_core.util import current_rss_mib, ols_slope, peak_rss_mib, sha256_hex


ROOT = Path(__file__).resolve().parents[1]
METHOD_PATH = ROOT / "docs/evidence/d002v/method-preregistration.json"

REQUIRED_SELF_MODEL_EVENTS = (
    "action_prediction",
    "prediction_error",
    "self_attribution",
    "body_change_evidence",
    "body_model_supersession",
    "capability_degradation",
    "capability_dormancy",
)


def _db(tmp_path: Path, name: str = "t.sqlite") -> str:
    return str(tmp_path / name)


def test_rss_uses_current_not_peak_memory():
    cur = current_rss_mib()
    peak = peak_rss_mib()
    assert cur > 0
    assert peak > 0
    # Allocate then free: peak may rise; current need not equal peak.
    blob = bytearray(8 * 1024 * 1024)
    blob[0] = 1
    cur2 = current_rss_mib()
    peak2 = peak_rss_mib()
    del blob
    assert peak2 >= peak
    assert cur2 >= cur
    # Metric source must be VmRSS, not ru_maxrss.
    with open(f"/proc/{__import__('os').getpid()}/status", encoding="utf-8") as f:
        status = f.read()
    assert "VmRSS:" in status
    assert "VmHWM:" in status
    # Helpers disagree on identity: peak uses ru_maxrss; current parses VmRSS.
    assert current_rss_mib.__doc__ and "VmRSS" in current_rss_mib.__doc__
    assert "ru_maxrss" in (peak_rss_mib.__doc__ or "")


def test_rss_method_is_frozen_before_run():
    method = json.loads(METHOD_PATH.read_text())
    assert method["metric"] == "current_VmRSS"
    assert method["window"] == "full_run"
    assert method["warmup_policy"].startswith("none")
    assert method["regression_method"] == "ordinary_least_squares_slope"
    assert method["sample_interval_s"] == 10
    assert method["outlier_handling"] == "none"
    assert method["pass_thresholds"]["rss_slope_mib_per_h_max"] == 1.0
    assert method["pass_thresholds"]["rss_p95_mib_max"] == 100.0
    assert method["forbidden_leak_signal"].startswith("resource.ru_maxrss")
    # Frozen before this validation suite was authored against results.
    assert method["no_post_result_metric_changes"] is True
    # Soak results (if present) must cite this method hash.
    perf = ROOT / "docs/evidence/d002v/performance-results.json"
    if perf.exists():
        import hashlib

        results = json.loads(perf.read_text())
        expect = hashlib.sha256(METHOD_PATH.read_bytes()).hexdigest()
        assert results.get("method_sha256") == expect
        assert results.get("rss_slope_method") == "full_window_ols_vmrss"


def test_full_window_rss_slope_passes():
    """D-002V Gate1 recorded FAILURE — do not waive; D-002P revalidates separately."""
    # Synthetic OLS still correct.
    hours = [i / 360.0 for i in range(0, 720)]  # 2h @ 10s
    rss = [30.0 for _ in hours]
    assert ols_slope(hours, rss) == 0.0
    rss_rise = [30.0 + h * 1.0 for h in hours]
    assert abs(ols_slope(hours, rss_rise) - 1.0) < 1e-9
    rss_leak = [30.0 + h * 1.5 for h in hours]
    assert ols_slope(hours, rss_leak) > 1.0
    perf = ROOT / "docs/evidence/d002v/performance-results.json"
    assert perf.exists(), "D-002V performance evidence must remain on record"
    results = json.loads(perf.read_text())
    assert results["duration_s"] >= 7200 * 0.99
    assert results["rss_p95_mib"] <= 100.0
    assert results["cpu_mean_pct"] <= 5.0
    assert results["crash_free"] is True
    # Preserved FAIL: full-window slope exceeded 1.0 under frozen D-002V method.
    assert results["gate1_pass"] is False
    assert results["rss_slope_mib_per_h"] > 1.0
    assert results["rss_slope_method"] == "full_window_ols_vmrss"


def test_event_types_have_authority_class():
    for name in REQUIRED_SELF_MODEL_EVENTS:
        klass = self_model_authority_class(name)
        assert klass in ("AUTHORITATIVE", "DERIVABLE", "DIAGNOSTIC")
    assert set(SELF_MODEL_EVENT_AUTHORITY) >= set(REQUIRED_SELF_MODEL_EVENTS)


def test_authoritative_self_model_events_are_not_sampled(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=31, intervention="I1"))
    org.run_ticks(120)
    events = list(org.store.iter_events())
    supersede = [e for e in events if e["event_type"] == "body_schema_supersede"]
    # Every adapted supersession must appear (authoritative — no %N skip).
    assert len(org.self_model.supersessions) == len(supersede)
    for e in events:
        if is_authoritative(e["event_type"]):
            assert e["event_type"] not in DIAGNOSTIC_EVENT_TYPES
    # Conceptual authoritative names map to unsampled ledger types.
    assert SELF_MODEL_LEDGER_ALIASES["body_model_supersession"] in AUTHORITATIVE_EVENT_TYPES
    assert self_model_authority_class("body_model_supersession") == "AUTHORITATIVE"
    assert self_model_authority_class("capability_degradation") == "AUTHORITATIVE"
    assert self_model_authority_class("capability_dormancy") == "AUTHORITATIVE"
    org.close()


def test_sampled_events_are_derivable_or_diagnostic(tmp_path):
    for name in ("prediction_error", "self_attribution"):
        assert self_model_authority_class(name) in ("DIAGNOSTIC", "DERIVABLE")
        assert name in DIAGNOSTIC_EVENT_TYPES
    assert self_model_authority_class("action_prediction") == "DERIVABLE"
    assert self_model_authority_class("body_change_evidence") == "DERIVABLE"
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=32))
    org.run_ticks(50)
    pe = [e for e in org.store.iter_events() if e["event_type"] == "prediction_error"]
    assert DIAGNOSTIC_SELF_MODEL_SAMPLE_EVERY_TICKS == 10
    assert len(org.self_model.errors) >= 1
    # Sampled ledger count is strictly below in-model error history (not every occurrence).
    assert len(pe) < len(org.self_model.errors)
    assert is_diagnostic("prediction_error")
    assert is_diagnostic("self_attribution")
    org.close()


def test_birth_replay_reconstructs_body_model(tmp_path):
    """Independent birth resimulation (no snapshot load) yields identical model hash."""
    a = resimulate(41, 80, _db(tmp_path, "birth_a.sqlite"), intervention="I1")
    b = resimulate(41, 80, _db(tmp_path, "birth_b.sqlite"), intervention="I1")
    assert a["self_model_hash"] == b["self_model_hash"]
    assert a["body_schema_id"] == b["body_schema_id"]


def test_snapshot_replay_matches_birth_replay(tmp_path):
    path = _db(tmp_path)
    org = create_organism(OrganismConfig(db_path=path, seed=42, snapshot_every=15, intervention="I1"))
    org.run_ticks(90)
    live_hash = org.self_model.state_hash()
    live_sid = org.self_model.active.body_schema_id
    live_super = list(org.self_model.supersessions)
    live_aff = dict(org.self_model.active.reachable_affordances)
    org.snapshot_if_due(force=True)
    org.close()
    # Snapshot path
    loaded = load_organism(OrganismConfig(db_path=path, seed=42, intervention="I1"))
    assert loaded.self_model.state_hash() == live_hash
    assert loaded.self_model.active.body_schema_id == live_sid
    assert loaded.self_model.supersessions == live_super
    assert loaded.self_model.active.reachable_affordances == live_aff
    loaded.close()
    # Birth path: fresh resimulation with same seed/ticks
    birth = resimulate(42, 90, _db(tmp_path, "birth.sqlite"), intervention="I1")
    assert birth["self_model_hash"] == live_hash
    assert birth["body_schema_id"] == live_sid


def test_supersession_history_matches(tmp_path):
    path = _db(tmp_path)
    org = create_organism(OrganismConfig(db_path=path, seed=43, intervention="I1"))
    org.run_ticks(100)
    expected = list(org.self_model.supersessions)
    org.snapshot_if_due(force=True)
    org.close()
    loaded = load_organism(OrganismConfig(db_path=path, seed=43, intervention="I1"))
    assert loaded.self_model.supersessions == expected
    ledger = [e["payload"] for e in loaded.store.iter_events() if e["event_type"] == "body_schema_supersede"]
    assert len(ledger) == len(expected)
    loaded.close()
    twin = resimulate(43, 100, _db(tmp_path, "twin.sqlite"), intervention="I1")
    # Twin hash implies same active+archive identity chain
    org2 = create_organism(OrganismConfig(db_path=_db(tmp_path, "twin2.sqlite"), seed=43, intervention="I1"))
    org2.run_ticks(100)
    assert org2.self_model.supersessions == expected
    assert twin["self_model_hash"] == org2.self_model.state_hash()
    org2.close()


def test_capability_compatibility_replays(tmp_path):
    path = _db(tmp_path)
    org = create_organism(OrganismConfig(db_path=path, seed=44))
    org.self_model.mark_incompatible("MOVE", "degraded")
    org.self_model.mark_incompatible("APPROACH", "dormant")
    org.run_ticks(20)
    aff = dict(org.self_model.active.reachable_affordances)
    assert aff["MOVE"] == "degraded"
    assert aff["APPROACH"] == "dormant"
    org.snapshot_if_due(force=True)
    org.close()
    loaded = load_organism(OrganismConfig(db_path=path, seed=44))
    assert loaded.self_model.active.reachable_affordances == aff
    assert loaded.self_model.capability_status("MOVE") == "degraded"
    assert loaded.self_model.capability_status("APPROACH") == "dormant"
    loaded.close()


def test_missing_authoritative_event_fails_closed(tmp_path):
    path = _db(tmp_path)
    org = create_organism(OrganismConfig(db_path=path, seed=45, intervention="I1"))
    org.run_ticks(30)
    # Force schema supersession; emit authoritative ledger row then a trailing event
    # so deletion leaves a sequence gap / chain break (not merely a shorter suffix).
    for i in range(25):
        org.self_model.record_dimension_evidence("movement_gain", 0.55, tick=i)
    assert len(org.self_model.supersessions) >= 1
    org.store.append_event(
        agent_id=org.identity.agent_id,
        event_type="body_schema_supersede",
        monotonic_time=org.monotonic_time,
        wall_time=0.0,
        payload={
            "active_schema_id": org.self_model.active.body_schema_id,
            "confidence": org.self_model.active.confidence,
        },
    )
    org.store.append_event(
        agent_id=org.identity.agent_id,
        event_type="lifecycle",
        monotonic_time=org.monotonic_time,
        wall_time=0.0,
        payload={"note": "post_supersede_marker"},
    )
    assert any(e["event_type"] == "body_schema_supersede" for e in org.store.iter_events())
    org.snapshot_if_due(force=True)
    org.close()
    store_org = load_organism(OrganismConfig(db_path=path, seed=45, intervention="I1"))
    row = store_org.store.conn.execute(
        "SELECT sequence FROM events WHERE event_type='body_schema_supersede' LIMIT 1"
    ).fetchone()
    assert row is not None
    store_org.store.conn.execute("DELETE FROM events WHERE sequence=?", (row[0],))
    store_org.store.conn.commit()
    with pytest.raises(PersistenceError):
        store_org.store.validate_chain()
    store_org.close()
    # Corrupt body model hash in snapshot fails closed on load.
    path2 = _db(tmp_path, "corrupt.sqlite")
    org2 = create_organism(OrganismConfig(db_path=path2, seed=46))
    org2.run_ticks(10)
    org2.snapshot_if_due(force=True)
    org2.close()
    bad = load_organism(OrganismConfig(db_path=path2, seed=46))
    snap = bad.store.load_snapshot()
    state = snap["state"]
    state["self_model"]["state_hash"] = "0" * 64
    state_s = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
    bad.store.conn.execute(
        "UPDATE snapshots SET state_json=?, state_hash=? WHERE snapshot_id=?",
        (state_s, sha256_hex(state_s), snap["snapshot_id"]),
    )
    bad.close()
    with pytest.raises(PersistenceError):
        load_organism(OrganismConfig(db_path=path2, seed=46))


def test_prediction_history_is_bounded(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=47))
    org.run_ticks(400)
    assert PREDICTION_HISTORY_BOUND == MAX_PREDICTION_HISTORY == 256
    assert len(org.self_model.predictions) <= PREDICTION_HISTORY_BOUND
    assert len(org.self_model.errors) <= PREDICTION_HISTORY_BOUND
    assert len(org.self_model.attributions) <= PREDICTION_HISTORY_BOUND
    org.close()
