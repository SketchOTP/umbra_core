from pathlib import Path

import pytest

from tools.umbra_life_probe import run


def test_formal_seed_rejected_before_work_creation(tmp_path: Path):
    root = tmp_path / "work"
    with pytest.raises(ValueError, match="formal_seed_prohibited"):
        run(root, seed=99200001)
    assert not root.exists()


def test_current_version_restart_probe_retains_evidence(tmp_path: Path):
    root = tmp_path / "work"
    result = run(root, seed=88009998, segments=2, segment_ticks=32)
    assert result["verdict"] == "PASS", result
    assert result["ticks"] == 64
    assert len(result["restarts"]) == 1
    assert result["restarts"][0]["owner_differences"] == []
    assert result["formal_stages_executed"] == []
    assert (root / "life.sqlite").is_file()
    assert (root / "result.json").is_file()
    assert (root / "segment-01.json").is_file()


def test_existing_result_path_is_never_destroyed_or_reused(tmp_path: Path):
    root = tmp_path / "existing"
    root.mkdir()
    preserved = root / "original"
    preserved.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        run(root)
    assert preserved.read_bytes() == b"preserve"
