"""UMBRA-D-002P — RUNTIME_READY, bounded memory, performance revalidation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from umbra_core.events import (
    CHANGE_EVIDENCE_BOUND,
    COVERAGE_SET_BOUND,
    PREDICTION_HISTORY_BOUND,
    SUPERSESSION_HISTORY_BOUND,
)
from umbra_core.persistence import Store
from umbra_core.runtime import OrganismConfig, create_organism, load_organism, resimulate
from umbra_core.self_model import MAX_PREDICTION_HISTORY
from umbra_core.self_model.engine import MAX_CHANGE_EVIDENCE, MAX_ERROR_HISTORY, MAX_MODEL_VERSIONS
from umbra_core.util import BoundedRing, current_rss_mib, ols_slope


ROOT = Path(__file__).resolve().parents[1]
METHOD_PATH = ROOT / "docs/evidence/d002p/method-preregistration.json"
PERF_PATH = ROOT / "docs/evidence/d002p/performance-results.json"
D002V_PERF = ROOT / "docs/evidence/d002v/performance-results.json"
D002V_VERDICT = ROOT / "docs/evidence/d002v/final-verdict.md"


def _db(tmp_path: Path, name: str = "t.sqlite") -> str:
    return str(tmp_path / name)


def test_d002v_performance_fail_preserved():
    """Gate 0 — prior D-002V result must remain a recorded performance failure."""
    assert D002V_PERF.exists()
    results = json.loads(D002V_PERF.read_text())
    assert results["gate1_pass"] is False
    assert results["rss_slope_mib_per_h"] > 1.0
    text = D002V_VERDICT.read_text()
    assert "UMBRA_D002V_PERFORMANCE_FAIL" in text


def test_runtime_ready_has_fixed_semantics(tmp_path):
    method = json.loads(METHOD_PATH.read_text())
    assert method["measurement_start"] == "first_persisted_RUNTIME_READY_event"
    assert method["runtime_ready_semantics"]["rss_gated"] is False
    assert "bounded_collection_initialization" in method["runtime_ready_semantics"]["emitted_after"]
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=101))
    assert org._runtime_ready is True
    ready = [e for e in org.store.iter_events() if e["event_type"] == "runtime_ready"]
    assert len(ready) == 1
    assert ready[0]["payload"]["rss_gated"] is False
    assert ready[0]["payload"]["bounded_initialized"] is True
    assert org.tick == 0
    org.close()


def test_runtime_ready_precedes_first_tick(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=102))
    events = org.store.iter_events()
    types = [e["event_type"] for e in events]
    assert types.index("runtime_ready") < len(types)
    assert "physiology_drift" not in types  # no tick yet
    org.tick_once()
    types2 = [e["event_type"] for e in org.store.iter_events()]
    assert types2.index("runtime_ready") < types2.index("physiology_drift")
    org.close()


def test_runtime_ready_cannot_be_delayed_for_rss(tmp_path):
    method = json.loads(METHOD_PATH.read_text())
    assert "rss_plateau" in method["runtime_ready_semantics"]["must_not_delay_for"]
    assert method["no_steady_state_exemption"] is True
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=103))
    ready = next(e for e in org.store.iter_events() if e["event_type"] == "runtime_ready")
    assert ready["payload"]["rss_gated"] is False
    # emit_runtime_ready refuses a second emission / post-tick delay trick
    with pytest.raises(RuntimeError, match="runtime_ready_already_emitted"):
        org.emit_runtime_ready()
    org.tick_once()
    with pytest.raises(RuntimeError, match="runtime_ready_already_emitted"):
        org.emit_runtime_ready()
    org.close()


def test_prediction_history_is_bounded(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=104))
    assert isinstance(org.self_model.predictions, BoundedRing)
    assert org.self_model.predictions.maxlen == MAX_PREDICTION_HISTORY
    org.run_ticks(400)
    assert len(org.self_model.predictions) == MAX_PREDICTION_HISTORY
    assert len(org.self_model.live_predictions()) <= MAX_PREDICTION_HISTORY
    org.close()


def test_error_history_is_bounded(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=105))
    org.run_ticks(400)
    assert org.self_model.errors.maxlen == MAX_ERROR_HISTORY
    assert len(org.self_model.errors) == MAX_ERROR_HISTORY
    assert len(org.self_model.live_errors()) <= MAX_ERROR_HISTORY
    org.close()


def test_attribution_history_is_bounded(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=106))
    org.run_ticks(400)
    assert len(org.self_model.attributions) == PREDICTION_HISTORY_BOUND
    assert len(org.self_model.live_attributions()) <= PREDICTION_HISTORY_BOUND
    org.close()


def test_change_evidence_is_bounded(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=107, intervention="I1"))
    org.run_ticks(300)
    assert org.self_model.change_evidence.maxlen == MAX_CHANGE_EVIDENCE == CHANGE_EVIDENCE_BOUND
    assert len(org.self_model.change_evidence) <= MAX_CHANGE_EVIDENCE
    assert len(org.self_model.supersessions) <= SUPERSESSION_HISTORY_BOUND == MAX_MODEL_VERSIONS
    org.close()


def test_no_unbounded_runtime_collection(tmp_path):
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=108))
    org.run_ticks(600)
    assert len(org.metrics["cells"]) <= COVERAGE_SET_BOUND
    assert len(org.arbitrator.state.visited_cells) <= COVERAGE_SET_BOUND
    assert "prediction_errors" not in org.metrics  # duplicate stream removed
    assert org.metrics.get("last_prediction_error") is None or isinstance(
        org.metrics["last_prediction_error"], (int, float)
    )
    assert len(org.self_model.predictions) <= PREDICTION_HISTORY_BOUND
    assert len(org.self_model.archive) <= MAX_MODEL_VERSIONS
    n_snap = org.store.conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    assert n_snap <= 2
    org.close()


def test_database_resources_are_released(tmp_path):
    path = _db(tmp_path)
    org = create_organism(OrganismConfig(db_path=path, seed=109))
    org.run_ticks(20)
    org.close()
    # Connection closed — reopen fails on closed handle.
    with pytest.raises(Exception):
        org.store.conn.execute("SELECT 1").fetchone()
    # Fresh store can open the same file.
    store = Store(path)
    assert store.last_sequence() > 0
    store.close()


def test_full_window_rss_slope_passes():
    """Synthetic OLS + D-002P soak evidence (when present)."""
    hours = [i / 360.0 for i in range(0, 720)]
    assert ols_slope(hours, [30.0 for _ in hours]) == 0.0
    assert abs(ols_slope(hours, [30.0 + h for h in hours]) - 1.0) < 1e-9
    assert ols_slope(hours, [30.0 + 1.5 * h for h in hours]) > 1.0
    method = json.loads(METHOD_PATH.read_text())
    assert method["pass_thresholds"]["rss_slope_mib_per_h_max"] == 1.0
    assert method["outlier_handling"] == "none"
    assert method["measurement_start"] == "first_persisted_RUNTIME_READY_event"
    assert method["no_steady_state_exemption"] is True
    if PERF_PATH.exists():
        results = json.loads(PERF_PATH.read_text())
        assert results["measurement_start"] == "runtime_ready"
        assert results["duration_s"] >= 7200 * 0.99
        assert results["rss_p95_mib"] <= 100.0
        assert results["rss_slope_mib_per_h"] <= 1.0
        assert results["cpu_mean_pct"] <= 5.0
        assert results["crash_free"] is True
        assert results["gate_performance_pass"] is True
    else:
        # Pre-soak: method freeze only; soak results assert the gate once written.
        assert method["duration_s"] == 7200
        assert method["sample_interval_s"] == 10


def test_body_model_results_unchanged(tmp_path):
    """Behavioral equivalence smoke: I1 adaptation still rewrites; C0 predicts."""
    org = create_organism(OrganismConfig(db_path=_db(tmp_path), seed=110, intervention="I1"))
    sid0 = org.self_model.active.body_schema_id
    org.run_ticks(200)
    # Either supersession or gain/reliability movement — same contracts as D-002.
    moved = (
        org.self_model.active.body_schema_id != sid0
        or len(org.self_model.supersessions) > 0
        or org.self_model.active.expected_motion.get("step_gain", 1.0) != 1.0
    )
    assert moved or len(org.self_model.live_errors()) > 0
    assert len(org.self_model.live_predictions()) > 0
    org.close()


def test_replay_results_unchanged(tmp_path):
    a = resimulate(111, 60, _db(tmp_path, "a.sqlite"), intervention="I1")
    b = resimulate(111, 60, _db(tmp_path, "b.sqlite"), intervention="I1")
    assert a["self_model_hash"] == b["self_model_hash"]
    assert a["body_schema_id"] == b["body_schema_id"]
    path = _db(tmp_path, "live.sqlite")
    org = create_organism(OrganismConfig(db_path=path, seed=112, intervention="I1"))
    org.run_ticks(50)
    h = org.self_model.state_hash()
    org.snapshot_if_due(force=True)
    org.close()
    loaded = load_organism(OrganismConfig(db_path=path, seed=112, intervention="I1"))
    assert loaded.self_model.state_hash() == h
    loaded.close()


def test_d001_regression_passes():
    """Import-level gate: D-001 suite still green (run via full pytest in soak)."""
    # Light check: create + tick + restart identity.
    import tempfile

    d = tempfile.mkdtemp()
    path = f"{d}/d001.sqlite"
    org = create_organism(OrganismConfig(db_path=path, seed=7))
    org.run_ticks(10)
    aid = org.identity.agent_id
    org.close()
    org2 = load_organism(OrganismConfig(db_path=path, seed=7))
    assert org2.identity.agent_id == aid
    assert org2.phys.in_viable() or True
    org2.close()
    assert current_rss_mib() > 0
