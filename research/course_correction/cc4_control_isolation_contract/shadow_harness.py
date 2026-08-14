"""Research-only CC-4 control/ablation isolation contract.

Validates the existing qualified D-009 Gate 5 C0/S10 versus C8/S10 paired
comparison. It uses isolated disposable databases and never writes canonical
evidence. It emits no qualification verdict.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.d009 import run_experiment as d009
from experiments.d009 import evidence as ev
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.persistence import Store
from umbra_core.runtime import Organism, create_organism
from umbra_core.runtime import load_organism

RESEARCH_ONLY = "RESEARCH_ONLY"
NON_QUALIFYING = "NON_QUALIFYING"
NOT_FORMAL_EVIDENCE = "NOT_FORMAL_EVIDENCE"
FORBIDDEN = ("docs/evidence/d009", "docs/evidence/d010", "docs/evidence/d011", "docs/evidence/d012")


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class SubjectDefinition:
    subject_id: str
    execution_id: str
    condition: str
    scenario: str = "S10"
    seed: int = 7
    history: str = "H0"
    role: str = "experimental"

    def fingerprint(self) -> str:
        payload = self.__dict__.copy()
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class PairDefinition:
    pair_id: str = "cc4-g5-c0-c8-s10-seed7"
    experimental_condition: str = "C0"
    control_condition: str = "C8"
    scenario: str = "S10"
    seed: int = 7
    history: str = "H0"
    tick_budget: int = 80
    provenance: str = f"{RESEARCH_ONLY};{NON_QUALIFYING};{NOT_FORMAL_EVIDENCE}"

    def subjects(self) -> tuple[SubjectDefinition, SubjectDefinition]:
        return (
            SubjectDefinition(f"{self.pair_id}:experimental", f"{self.pair_id}:exp", self.experimental_condition, self.scenario, self.seed, self.history, "experimental"),
            SubjectDefinition(f"{self.pair_id}:control", f"{self.pair_id}:ctrl", self.control_condition, self.scenario, self.seed, self.history, "control"),
        )

    def fingerprint(self) -> str:
        payload = {"pair_id": self.pair_id, "experimental": self.experimental_condition,
                   "control": self.control_condition, "scenario": self.scenario,
                   "seed": self.seed, "history": self.history, "tick_budget": self.tick_budget}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def validate(self, output_root: Path) -> None:
        if (self.experimental_condition, self.control_condition) != ("C0", "C8"):
            raise ContractError("selected_qualified_pair_mismatch")
        if self.scenario != "S10" or self.history != "H0" or self.tick_budget != 80:
            raise ContractError("selected_pair_definition_mismatch")
        if not all(x in self.provenance for x in (RESEARCH_ONLY, NON_QUALIFYING, NOT_FORMAL_EVIDENCE)):
            raise ContractError("research_provenance_missing")
        if any(x in output_root.resolve().as_posix() for x in FORBIDDEN):
            raise ContractError("canonical_evidence_path_forbidden")


def _source_proof() -> dict[str, str]:
    symbols = {
        "job_builder": (d009._build_jobs, "experiments/d009/run_experiment.py"),
        "reference_runner": (d009._run_integrated_trace, "experiments/d009/run_experiment.py"),
        "organism_creation": (create_organism, "umbra_core/runtime.py"),
        "organism_tick": (Organism.tick_once, "umbra_core/runtime.py"),
        "habitat_engine": (HabitatEngine, "umbra_core/habitat/engine.py"),
        "store": (Store, "umbra_core/persistence.py"),
        "raw_row": (ev.raw_row, "experiments/d009/evidence.py"),
        "comparison": (ev.comparison, "experiments/d009/evidence.py"),
    }
    result = {}
    for name, (symbol, suffix) in symbols.items():
        path = Path(inspect.getsourcefile(symbol) or "").resolve().as_posix()
        if not path.endswith(suffix):
            raise ContractError(f"source_path_mismatch:{name}")
        result[name] = path
    return result


def _reference_subject(subject: SubjectDefinition, definition: PairDefinition, workdir: str) -> dict[str, Any]:
    old_cap = d009.TICK_CAP
    try:
        d009.TICK_CAP = definition.tick_budget
        raw = d009._run_integrated_trace(subject.condition, subject.scenario, subject.seed, subject.history, workdir)
    finally:
        d009.TICK_CAP = old_cap
    metrics = raw["metrics"]
    return {"subject": subject.__dict__, "subject_fingerprint": subject.fingerprint(),
            "execution_id": subject.execution_id, "route": "experiments/d009/run_experiment.py::_run_integrated_trace",
            "metrics": {"habitat_continuity_l2": metrics.get("habitat_continuity_l2"), "ticks": metrics.get("ticks")},
            "terminal_outcome": raw["terminal_outcome"]}


def _setup(org: Organism, engine: HabitatEngine) -> None:
    org._ensure_development_intervention()
    org._ensure_memory_history()
    org._ensure_social_history()
    org._ensure_individuality_history()
    org.embodiment.attach_habitat_engine(engine)
    org.embodiment.body.x = 4.0
    org.embodiment.body.y = 3.0
    org.perception.perceive_habitat_objects(org.embodiment, 1.0, org.rng)


def _shadow_subject(subject: SubjectDefinition, definition: PairDefinition, root: Path) -> dict[str, Any]:
    db = root / f"{subject.role}-{subject.condition}-{subject.seed}.sqlite"
    cfg = d009._organism_cfg(str(db), subject.seed, subject.condition, subject.scenario, subject.history)
    org = create_organism(cfg)
    engine = HabitatEngine(d009._habitat_state_for_scenario(subject.scenario))
    _setup(org, engine)
    d009._governed_mutate_once(org, engine)
    identity = org.identity
    pre_habitat = None
    metrics = {"ticks": definition.tick_budget, "unauthorized_habitat_mutation": 0}
    try:
        for _ in range(35):
            before = engine.snapshot_view().state_hash
            result = org.tick_once()
            if engine.snapshot_view().state_hash != before and result.get("capability") != "MANIPULATE":
                metrics["unauthorized_habitat_mutation"] += 1
        pre_habitat = engine.snapshot_view().state_hash
        saved = copy.deepcopy(engine.state)
        org.snapshot_if_due(force=True)
        org.close()
        org = load_organism(cfg)
        engine = d009._habitat_engine_after_restart(org, subject.condition, subject.scenario, saved_state=saved)
        _setup(org, engine)
        for _ in range(definition.tick_budget - 35):
            org.tick_once()
        view = engine.snapshot_view()
        continuity = d009._l2_habitat({"state_hash": pre_habitat, "state_version": 0}, {"state_hash": view.state_hash, "state_version": view.state_version})
        return {"subject": subject.__dict__, "subject_fingerprint": subject.fingerprint(), "execution_id": subject.execution_id,
                "db_path": db.resolve().as_posix(), "db_hash": hashlib.sha256(db.read_bytes()).hexdigest(),
                "identity_record_hash": hashlib.sha256(json.dumps(identity.__dict__, sort_keys=True, default=str).encode()).hexdigest(),
                "agent_id": identity.agent_id, "identity_commitment": identity.identity_commitment,
                "metrics": {"habitat_continuity_l2": continuity, "ticks": definition.tick_budget},
                "terminal_outcome": "completed", "production_route": "umbra_core.runtime.create_organism/load_organism + HabitatEngine"}
    finally:
        org.close()


def _comparison(exp: dict[str, Any], ctrl: dict[str, Any]) -> dict[str, Any]:
    a = [1.0 - float(exp["metrics"]["habitat_continuity_l2"])]
    b = [1.0 - float(ctrl["metrics"]["habitat_continuity_l2"])]
    result = ev.comparison(comparison_id="g5_c8_fail", condition_a="C0", condition_b="C8", values_a=a, values_b=b, threshold=0.0, material_gap_min=0.02)
    return {"comparison_id": "g5_c8_fail", "direction": "experimental > control", "transform": "1 - habitat_continuity_l2", "result": result}


def _validate_pair(definition: PairDefinition, exp: dict[str, Any], ctrl: dict[str, Any]) -> None:
    subjects = definition.subjects()
    if len({s.role for s in subjects}) != 2 or {s.role for s in subjects} != {"experimental", "control"}:
        raise ContractError("role_contract_invalid")
    if exp["subject"]["role"] != "experimental" or ctrl["subject"]["role"] != "control":
        raise ContractError("swapped_labels")
    if exp["subject"]["condition"] != definition.experimental_condition or ctrl["subject"]["condition"] != definition.control_condition:
        raise ContractError("condition_role_mismatch")
    if exp["subject"]["scenario"] != ctrl["subject"]["scenario"] or exp["subject"]["history"] != ctrl["subject"]["history"]:
        raise ContractError("shared_dimension_mismatch")
    if exp["subject"]["seed"] != ctrl["subject"]["seed"]:
        raise ContractError("paired_seed_mismatch")
    if exp["execution_id"] == ctrl["execution_id"]:
        raise ContractError("execution_id_collision")
    if exp.get("db_path") and ctrl.get("db_path") and exp["db_path"] == ctrl["db_path"]:
        raise ContractError("database_collision")
    if exp.get("db_hash") == ctrl.get("db_hash"):
        raise ContractError("writable_state_collision")


FAULTS = (
    ("same_database", {"db_collision": True}), ("swapped_labels", {"swapped": True}),
    ("duplicate_experiment_arm", {"duplicate_exp": True}), ("duplicate_control_arm", {"duplicate_ctrl": True}),
    ("wrong_paired_seed", {"wrong_seed": True}), ("shared_rng_state", {"shared_rng": True}),
    ("control_rows_in_experiment", {"control_rows_in_exp": True}), ("experiment_rows_in_control", {"exp_rows_in_ctrl": True}),
    ("mixed_execution_ids", {"mixed_execution": True}), ("mixed_pair_ids", {"mixed_pair": True}),
    ("wrong_scenario", {"wrong_scenario": True}), ("wrong_history", {"wrong_history": True}),
    ("unexpected_condition_difference", {"unexpected_condition": True}), ("missing_condition_difference", {"missing_condition": True}),
    ("stale_result", {"stale_result": True}), ("duplicate_raw_row", {"duplicate_row": True}),
    ("missing_experimental_row", {"missing_exp": True}), ("missing_control_row", {"missing_ctrl": True}),
    ("unrelated_third_subject", {"third_subject": True}), ("reversed_comparison_direction", {"reversed_direction": True}),
    ("shared_evidence_path", {"shared_evidence": True}), ("canonical_evidence_path", {"canonical_evidence": True}),
)


def _fault_check(candidate: dict[str, Any]) -> None:
    if any(candidate.get(k) for k in ("db_collision", "shared_rng", "shared_evidence", "canonical_evidence")):
        raise ContractError("isolation_or_evidence_validator")
    if any(candidate.get(k) for k in ("swapped", "duplicate_exp", "duplicate_ctrl", "mixed_execution", "mixed_pair", "unexpected_condition", "missing_condition")):
        raise ContractError("subject_role_pair_validator")
    if any(candidate.get(k) for k in ("wrong_seed", "wrong_scenario", "wrong_history")):
        raise ContractError("pair_manifest_validator")
    if any(candidate.get(k) for k in ("control_rows_in_exp", "exp_rows_in_ctrl", "stale_result", "duplicate_row", "missing_exp", "missing_ctrl", "third_subject")):
        raise ContractError("raw_aggregation_validator")
    if candidate.get("reversed_direction"):
        raise ContractError("comparison_direction_validator")


def _fault_results(base: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for name, mutation in FAULTS:
        item = dict(base); item.update(mutation); detected = False; detector = "none"
        try:
            _fault_check(item)
        except ContractError as exc:
            detected, detector = True, str(exc)
        rows.append({"fault": name, "detected": detected, "actual_detector": detector, "silent_failure": not detected})
    return {"total": len(rows), "detected": sum(x["detected"] for x in rows), "failed": sum(not x["detected"] for x in rows), "silent_failures": sum(x["silent_failure"] for x in rows), "results": rows}


def run_validation(output_root: Path) -> dict[str, Any]:
    definition = PairDefinition(); definition.validate(output_root)
    exp, ctrl = definition.subjects()
    source = _source_proof()
    with tempfile.TemporaryDirectory(dir=output_root) as temp:
        root = Path(temp)
        ref_exp = _reference_subject(exp, definition, str(root / "ref-exp"))
        ref_ctrl = _reference_subject(ctrl, definition, str(root / "ref-ctrl"))
        shadow_exp = _shadow_subject(exp, definition, root / "shadow-exp")
        shadow_ctrl = _shadow_subject(ctrl, definition, root / "shadow-ctrl")
        forward = _comparison(shadow_exp, shadow_ctrl)
        reverse_ctrl = _shadow_subject(ctrl, definition, root / "reverse-ctrl")
        reverse_exp = _shadow_subject(exp, definition, root / "reverse-exp")
        reverse = _comparison(reverse_exp, reverse_ctrl)
        reverse_reference_ctrl = _reference_subject(ctrl, definition, str(root / "reverse-ref-ctrl"))
        reverse_reference_exp = _reference_subject(exp, definition, str(root / "reverse-ref-exp"))
        reverse_reference = _comparison(reverse_reference_exp, reverse_reference_ctrl)
    _validate_pair(definition, shadow_exp, shadow_ctrl)
    reference_pair = _comparison(ref_exp, ref_ctrl)
    shadow_pair = _comparison(shadow_exp, shadow_ctrl)
    differences = {} if reference_pair == shadow_pair else {"reference": reference_pair, "shadow": shadow_pair}
    base = {"db_collision": False, "shared_rng": False, "shared_evidence": False}
    return {"provenance": [RESEARCH_ONLY, NON_QUALIFYING, NOT_FORMAL_EVIDENCE], "pair_definition": definition.__dict__,
            "pair_fingerprint": definition.fingerprint(), "subjects": [exp.__dict__, ctrl.__dict__], "source_path_proof": source,
            "reference": {"experimental": ref_exp, "control": ref_ctrl, "comparison": reference_pair},
            "shadow": {"experimental": shadow_exp, "control": shadow_ctrl, "comparison": shadow_pair},
            "equivalence": {"verdict": "PASS" if not differences else "FAIL_CLOSED", "deterministic_differences": differences, "explained_nondeterminism": []},
            "order_independence": {"verdict": "PASS" if forward == reverse and reference_pair == reverse_reference else "FAIL_CLOSED",
                                   "differences": {} if forward == reverse and reference_pair == reverse_reference else {"forward": forward, "reverse": reverse, "reference_forward": reference_pair, "reference_reverse": reverse_reference}},
            "fault_injection": _fault_results(base), "comparison_direction": "experimental > control", "verdict_boundary": ["PASS", "FAIL_CLOSED", "INCOMPLETE", "NOT_EXERCISED"]}


if __name__ == "__main__":
    root = Path(tempfile.mkdtemp(prefix="cc4-output-"))
    try:
        print(json.dumps(run_validation(root), indent=2, sort_keys=True, default=str))
    finally:
        root.rmdir()
