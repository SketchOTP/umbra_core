"""Publication-surface protection for the AS-015 one-shot formal runner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from experiments.as015 import run_qualification


def test_formal_failure_uses_a_formal_v1_artifact_name(
    monkeypatch, tmp_path: Path
) -> None:
    """A prior non-formal artifact must not mask the first formal failure."""
    manifest = {
        "schema": "AS015_SEED_MANIFEST_V1",
        "directive": "UMBRA-AS-015",
        "formal_regimes": {regime: list(range(8)) for regime in ("R0", "R1", "R2", "R3")},
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    published: list[str] = []

    monkeypatch.setattr(
        run_qualification,
        "execute",
        lambda *_args, **_kwargs: {
            "schema": "AS015_FORMAL_POPULATION_V1",
            "completed_runs": 1,
            "terminal": "AS015_FRESH_R1_FAIL",
        },
    )
    monkeypatch.setattr(run_qualification, "publish_json", lambda *_args, **_kwargs: "computed")
    monkeypatch.setattr(
        run_qualification,
        "publish",
        lambda name, _value: published.append(name) or "evidence",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_qualification",
            "--manifest",
            str(manifest_path),
            "--work",
            str(tmp_path / "formal-work"),
        ],
    )

    try:
        run_qualification.main()
    except SystemExit as failure:
        assert failure.code == 1
    else:  # pragma: no cover - formal failure must terminate the runner.
        raise AssertionError("formal failure did not stop the runner")

    assert published == ["AS015_FORMAL_POPULATION_FAILURE_V1.json"]
