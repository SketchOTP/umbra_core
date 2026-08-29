import ast
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNNER_DIR = ROOT / "experiments" / "close02vr"


def test_known_r1_is_fixed_and_not_loaded_from_development_manifest():
    source = (RUNNER_DIR / "qualification.py").read_text()
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "KNOWN_R1_SEED" in names
    assert 'development["known_R1"]' not in source


def test_stage_manifest_is_complete_and_ordered():
    manifest = json.loads((RUNNER_DIR / "CLOSE02VR_STAGE_MANIFEST.json").read_text())
    stages = manifest["stages"]
    assert [stage["stage"] for stage in stages] == [
        "DIAGNOSTIC_A", "DIAGNOSTIC_B", "KNOWN_R1", "R0_DEVELOPMENT",
        "R1_DEVELOPMENT", "R2_DEVELOPMENT", "R3_DEVELOPMENT",
        "AGENCY_BOUNDEDNESS", "FORMAL_R0", "FORMAL_R1", "FORMAL_R2", "FORMAL_R3",
    ]
    assert stages[2]["seed_source"] == "fixed_constant"
    assert stages[2]["seeds"] == [57531938]
    assert stages[3]["prerequisite"] == "KNOWN_R1_PASS"
    assert stages[8]["prerequisite"] == "AGENCY_BOUNDEDNESS_PASS"


def test_fresh_manifest_has_no_known_r1_population_key():
    seeds = json.loads((RUNNER_DIR / "CLOSE02VR_DEVELOPMENT_SEEDS.json").read_text())
    assert "known_R1" not in seeds["seeds"]
    assert seeds["known_r1_is_fixed_diagnostic_not_population_member"] is True
