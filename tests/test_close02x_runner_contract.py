import ast
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "experiments" / "close02x"


def test_stage_graph_is_exact_and_strict():
    manifest = json.loads((RUNNER / "CLOSE02X_STAGE_MANIFEST.json").read_text())
    assert [row["stage"] for row in manifest["stages"]] == [
        "DIAGNOSTIC_A", "DIAGNOSTIC_B", "KNOWN_R1", "R0_DEVELOPMENT",
        "R1_DEVELOPMENT", "R2_DEVELOPMENT", "R3_DEVELOPMENT",
        "AGENCY_BOUNDEDNESS", "FORMAL_R0", "FORMAL_R1", "FORMAL_R2",
        "FORMAL_R3", "REGRESSIONS",
    ]
    assert manifest["assertions"]["first_failure_stops"] is True
    assert manifest["assertions"]["retries"] == 0
    assert manifest["assertions"]["reseeds"] == 0


def test_seed_populations_are_fresh_disjoint_and_sealed():
    development = json.loads((RUNNER / "CLOSE02X_DEVELOPMENT_SEEDS.json").read_text())
    formal = json.loads((RUNNER / "CLOSE02X_FORMAL_SEEDS.json").read_text())
    dev = [seed for values in development["seeds"].values() for seed in values]
    frm = [seed for values in formal["seeds"].values() for seed in values]
    assert len(dev) == len(set(dev)) == 17
    assert len(frm) == len(set(frm)) == 32
    assert set(dev).isdisjoint(frm)
    assert {45878900, 22023239, 57531938}.isdisjoint(dev + frm)
    assert development["seed_status"] == formal["seed_status"]


def test_runner_has_no_retry_or_reseed_loop_and_known_r1_is_fixed():
    source = (RUNNER / "qualification.py").read_text()
    tree = ast.parse(source)
    assert "retry" not in {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "reseed" not in {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    manifest = json.loads((RUNNER / "CLOSE02X_STAGE_MANIFEST.json").read_text())
    assert manifest["stages"][2]["seeds"] == [57531938]


def test_unknown_neutrality_and_existing_no_safe_are_frozen_by_production_tests():
    source = (ROOT / "tests" / "test_close02x_prospective_recoverability.py").read_text()
    assert "test_unknown_support_is_neutral_in_integrated_filter" in source
    assert "test_empty_filtered_pool_uses_existing_no_safe_action_without_fallback" in source
