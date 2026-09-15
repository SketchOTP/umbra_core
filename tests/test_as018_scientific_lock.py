"""Contract-only AS-018 lock and formal-accounting tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from experiments.as018.formal_accounting import AccountingError, FormalAccounting
from experiments.as018.qualification import validate_manifest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "experiments/as018/AS018_FORMAL_SEED_MANIFEST_V1.json"
LOCK_PATH = ROOT / "experiments/as018/AS018_SCIENTIFIC_LOCK_CONTRACT_V1.json"


def _case_ids() -> tuple[str, ...]:
    manifest = json.loads(MANIFEST_PATH.read_text())
    return tuple(
        f"{regime}-{index:02d}-{seed}"
        for regime in ("R0", "R1", "R2", "R3")
        for index, seed in enumerate(manifest["formal_regimes"][regime])
    )


def test_formal_manifest_and_lock_are_frozen_before_execution():
    manifest = json.loads(MANIFEST_PATH.read_text())
    lock = json.loads(LOCK_PATH.read_text())
    validate_manifest(manifest)
    assert lock["lock_status"] == "ESTABLISHED_BEFORE_FORMAL_ORGANISM_CREATION"
    assert lock["organism_implementation_sha"] == manifest["organism_implementation_sha"]
    assert lock["formal_execution_subject"] == manifest["formal_execution_subject"]
    assert lock["seed_contract"]["formal_seeds_consumed_at_lock"] == 0
    assert lock["lock_integrity"]["formal_organisms_created_at_lock"] == 0


def test_manifest_rejects_seed_or_subject_mutation():
    manifest = json.loads(MANIFEST_PATH.read_text())
    altered = copy.deepcopy(manifest)
    altered["formal_regimes"]["R0"][0] += 1
    with pytest.raises(RuntimeError, match="AS018_FORMAL_SEED"):
        validate_manifest(altered)
    altered = copy.deepcopy(manifest)
    altered["formal_execution_subject"] = "0" * 40
    with pytest.raises(RuntimeError, match="AS018_FORMAL_MANIFEST"):
        validate_manifest(altered)


def test_started_seed_is_consumed_even_when_interrupted():
    accounting = FormalAccounting(_case_ids())
    case_id = _case_ids()[0]
    accounting.start(case_id)
    accounting.interrupt(case_id)
    summary = accounting.summary()
    assert summary["registered_cases"] == 32
    assert summary["started_cases"] == 1
    assert summary["formal_seed_consumption"] == 1
    assert summary["population_acceptance_ready"] is False


def test_population_acceptance_requires_all_cases_finished():
    accounting = FormalAccounting(_case_ids())
    with pytest.raises(AccountingError):
        accounting.finish(_case_ids()[0])
    assert accounting.summary()["population_acceptance_ready"] is False


def test_all_case_stages_are_required_for_population_pass():
    accounting = FormalAccounting(_case_ids())
    for case_id in _case_ids():
        accounting.start(case_id)
        accounting.execution_finished(case_id)
        accounting.validation_started(case_id)
        accounting.locally_validated(case_id)
        accounting.export_verified(case_id)
        accounting.finish(case_id)
    summary = accounting.summary()
    assert summary["formal_seed_consumption"] == 32
    assert summary["accepted_cases"] == 32
    assert summary["unresolved_cases"] == []
    assert summary["population_acceptance_ready"] is True
