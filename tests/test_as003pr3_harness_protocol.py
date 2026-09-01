from __future__ import annotations

import ast
import hashlib
import inspect
from pathlib import Path

from experiments.as003p import shadow_diagnostic as frozen
from experiments.as003pr3 import shadow_diagnostic as r3


ROOT = Path(__file__).parents[1]


def test_fixture_seed_horizon_and_scientific_module_are_frozen():
    assert r3.SEED == frozen.SEED == 45878900
    assert r3.HORIZON == frozen.HORIZON == 500
    assert r3.frozen.fixture is frozen.fixture
    assert r3.COMMAND == "/usr/bin/python3 -m experiments.as003pr3.shadow_diagnostic"


def test_raw_leg_preserves_frozen_prepare_tick_and_trace_contract():
    source = inspect.getsource(r3.run_one_raw)
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    attrs = [node.func.attr for node in calls if isinstance(node.func, ast.Attribute)]
    assert attrs.count("prepare") == 1
    assert attrs.count("tick_once") == 1
    assert 'frozen.fixture.prepare(SEED, db, "R0")' in source
    assert "for _ in range(HORIZON)" in source
    assert "cfg.decision_trace_path" in source
    assert "cfg.planning_shadow_path" in source
    assert "_normalized_state" not in source
    assert "_normalized_events" not in source
    assert "_semantic_runtime_value" not in source


def test_main_contains_exactly_one_control_and_one_shadow_leg():
    source = inspect.getsource(r3.main)
    assert source.count("run_one_raw(shadow=False") == 1
    assert source.count("run_one_raw(shadow=True") == 1
    assert '"retries": 0' in source
    assert '"reseeds": 0' in source
    assert "while " not in source


def test_raw_evidence_and_frozen_comparator_decide_parity():
    source = inspect.getsource(r3.main)
    assert "AS003PR3_CONTROL_RUN_RAW.json" in source
    assert "AS003PR3_SHADOW_RUN_RAW.json" in source
    assert "compare_run_records(control, shadow)" in source
    assert 'if not parity["semantic_equal"]' in source


def test_frozen_comparator_source_hash():
    path = ROOT / "experiments/as003pr3/semantic_comparator.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "596ab86f41523ea16dde44693b5aa7a702f0514fc38c18717aa0070c1590da66"
    )
