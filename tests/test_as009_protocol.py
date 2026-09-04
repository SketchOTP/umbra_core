from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "experiments/as009/qualification.py"


def test_as009_uses_habitat_authority_for_partner_creation_and_visibility():
    source = HARNESS.read_text()
    assert "make_social_entity_object" in source
    assert "commit_object_creation" in source
    assert "commit_object_visibility" in source
    assert "set_occlusion" not in source
    assert "plant_partner" not in source


def test_as009_keeps_historical_harnesses_immutable():
    assert (ROOT / "experiments/d014/run_formal.py").exists()
    assert (ROOT / "experiments/as008/qualification.py").exists()


def test_as009_keeps_r2_schedule_and_r3_schedule():
    source = HARNESS.read_text()
    assert 'tick == 600' in source
    assert 'tick == 1200' in source
    assert 'tick == 1800' in source
    assert 'tick == 2400' in source
    assert 'tick == 2600' in source
    assert 'tick == 3600' in source
    assert 'HORIZON = 7200' in source


def test_as009_does_not_add_policy_authority():
    source = HARNESS.read_text()
    assert "Arbitrator" not in source
    assert "select(" not in source
    assert "candidate_generation" not in source
