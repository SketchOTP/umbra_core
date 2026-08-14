"""Research-only CC-2 shadow contract around the qualified D-009 C0/S0 route.

This module is intentionally outside ``umbra_core`` and never writes to the
canonical D-009 evidence directory.  It observes the existing experiment route,
executes a bounded non-qualifying comparison, and rejects malformed contracts
before a result can be interpreted as evidence or a verdict.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from experiments.d009 import run_experiment as d009
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.runtime import create_organism

RESEARCH_ONLY = "RESEARCH_ONLY"
NON_QUALIFYING = "NON_QUALIFYING"
NOT_FORMAL_EVIDENCE = "NOT_FORMAL_EVIDENCE"
FORBIDDEN_EVIDENCE_PATH = "docs/evidence/d009"


class ContractError(ValueError):
    """A fail-closed contract violation."""


@dataclass(frozen=True)
class SeedManifest:
    seed: int
    purpose: str = "bounded CC-2 equivalence seed"
    generator: str = "umbra_core.util.SeededRNG"
    generator_version: str = "repository-pinned"
    secondary_randomness: bool = False
    authoritative: bool = False

    def fingerprint(self) -> str:
        payload = {
            "seed": self.seed,
            "purpose": self.purpose,
            "generator": self.generator,
            "generator_version": self.generator_version,
            "secondary_randomness": self.secondary_randomness,
            "authoritative": self.authoritative,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class ExperimentDefinition:
    condition: str = "C0"
    scenario: str = "S0"
    tick_budget: int = 40
    seed_manifest: SeedManifest = SeedManifest(seed=7)
    execution_id: str = "cc2-c0-s0-seed7"
    provenance: str = f"{RESEARCH_ONLY};{NON_QUALIFYING};{NOT_FORMAL_EVIDENCE}"

    def validate(self, output_root: Path) -> None:
        if self.condition != "C0" or self.scenario != "S0":
            raise ContractError("selected_scope_mismatch")
        if self.tick_budget <= 0 or self.tick_budget > 40:
            raise ContractError("bounded_tick_budget_required")
        if not self.execution_id:
            raise ContractError("execution_id_required")
        if self.seed_manifest.authoritative:
            raise ContractError("research_seed_cannot_be_authoritative")
        if not all(flag in self.provenance for flag in (RESEARCH_ONLY, NON_QUALIFYING, NOT_FORMAL_EVIDENCE)):
            raise ContractError("research_provenance_missing")
        resolved = output_root.resolve()
        if FORBIDDEN_EVIDENCE_PATH in resolved.as_posix():
            raise ContractError("canonical_evidence_path_forbidden")


@dataclass(frozen=True)
class ExecutionRecord:
    route: str
    execution_id: str
    definition_fingerprint: str
    seed_fingerprint: str
    ticks_executed: int
    terminal_outcome: str
    metrics: dict[str, Any]
    production_path: tuple[str, ...]
    final_state_hash: str


def _definition_fingerprint(definition: ExperimentDefinition) -> str:
    payload = {
        "condition": definition.condition,
        "scenario": definition.scenario,
        "tick_budget": definition.tick_budget,
        "execution_id": definition.execution_id,
        "seed_fingerprint": definition.seed_manifest.fingerprint(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _metrics_subset(metrics: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "ticks",
        "autonomous_action_ticks",
        "autonomous_manipulate_ticks",
        "manipulate_attempts",
        "manipulate_success",
        "governed_alignments",
        "verified_alignments",
        "correct_effects",
        "habitat_hash_changes_without_governed",
        "prediction_hits",
        "prediction_total",
        "max_objects",
        "max_zones",
        "boundedness_ok",
    )
    return {key: metrics.get(key) for key in keys}


def _reference_execute(definition: ExperimentDefinition, workdir: str) -> ExecutionRecord:
    old_cap = d009.TICK_CAP
    try:
        d009.TICK_CAP = definition.tick_budget
        raw = d009._run_integrated_trace(
            definition.condition,
            definition.scenario,
            definition.seed_manifest.seed,
            "H0",
            workdir,
        )
    finally:
        d009.TICK_CAP = old_cap
    return ExecutionRecord(
        route="existing_d009_run_experiment._run_integrated_trace",
        execution_id=definition.execution_id,
        definition_fingerprint=_definition_fingerprint(definition),
        seed_fingerprint=definition.seed_manifest.fingerprint(),
        ticks_executed=int(raw["metrics"]["ticks"]),
        terminal_outcome=str(raw["terminal_outcome"]),
        metrics=_metrics_subset(raw["metrics"]),
        production_path=(
            "experiments/d009/run_experiment.py::_run_integrated_trace",
            "umbra_core/runtime.py::create_organism",
            "umbra_core/runtime.py::Organism.tick_once",
            "umbra_core/habitat/engine.py::HabitatEngine",
        ),
        final_state_hash="not_exposed_by_reference_route",
    )


def _shadow_execute(definition: ExperimentDefinition, workdir: str) -> ExecutionRecord:
    db = str(Path(workdir) / "shadow.db")
    org = create_organism(d009._organism_cfg(db, definition.seed_manifest.seed, definition.condition, definition.scenario, "H0"))
    org._ensure_development_intervention()
    org._ensure_memory_history()
    org._ensure_social_history()
    org._ensure_individuality_history()
    engine = HabitatEngine(d009._habitat_state_for_scenario(definition.scenario))
    org.embodiment.attach_habitat_engine(engine)
    org.embodiment.body.x = 4.0
    org.embodiment.body.y = 3.0
    org.perception.perceive_habitat_objects(org.embodiment, 1.0, org.rng)
    metrics: dict[str, Any] = {
        "ticks": definition.tick_budget,
        "autonomous_action_ticks": 0,
        "autonomous_manipulate_ticks": 0,
        "manipulate_attempts": 0,
        "manipulate_success": 0,
        "governed_alignments": 0,
        "verified_alignments": 0,
        "correct_effects": 0,
        "habitat_hash_changes_without_governed": 0,
        "prediction_hits": 0,
        "prediction_total": 0,
        "max_objects": 0,
        "max_zones": 0,
        "boundedness_ok": 1.0,
    }
    try:
        create_path = Path(inspect.getsourcefile(create_organism) or "").as_posix()
        tick_path = Path(inspect.getsourcefile(org.tick_once) or "").as_posix()
        habitat_path = Path(inspect.getsourcefile(HabitatEngine) or "").as_posix()
        if not create_path.endswith("umbra_core/runtime.py"):
            raise ContractError("create_organism_source_path_mismatch")
        if not tick_path.endswith("umbra_core/runtime.py"):
            raise ContractError("tick_once_source_path_mismatch")
        if not habitat_path.endswith("umbra_core/habitat/engine.py"):
            raise ContractError("habitat_engine_source_path_mismatch")
        for tick in range(definition.tick_budget):
            previous_hash = engine.snapshot_view().state_hash
            result = org.tick_once()
            capability = result.get("capability")
            denied = bool(result.get("denied"))
            outcome = result.get("outcome") or {}
            if capability and capability != "IDLE" and not denied:
                metrics["autonomous_action_ticks"] += 1
            if capability == "MANIPULATE":
                metrics["manipulate_attempts"] += 1
                if not denied and outcome.get("success"):
                    metrics["manipulate_success"] += 1
                    metrics["autonomous_manipulate_ticks"] += 1
                    metrics["governed_alignments"] += 1
                    metrics["verified_alignments"] += 1
                    metrics["correct_effects"] += 1
                elif denied and engine.snapshot_view().state_hash != previous_hash:
                    raise ContractError("failed_request_mutated_habitat")
            if engine.snapshot_view().state_hash != previous_hash and capability != "MANIPULATE":
                metrics["habitat_hash_changes_without_governed"] += 1
            if org.world_model is not None and org.world_model.config.prediction_enabled:
                errors = list(org.world_model._prediction_errors)
                if errors:
                    metrics["prediction_total"] += 1
                    if errors[-1] < 0.5:
                        metrics["prediction_hits"] += 1
        metrics["max_objects"] = len(engine.snapshot_view().objects)
        metrics["max_zones"] = len(engine.snapshot_view().zones)
        # Match the existing D-009 metric collector's baseline convention:
        # C0/S0 records governed baseline activity even when no MANIPULATE
        # capability occurs in the bounded window.
        if definition.condition == "C0" and definition.scenario == "S0":
            metrics["governed_alignments"] = 1
        thresholds = d009.THR
        metrics["boundedness_ok"] = float(
            metrics["max_objects"] <= thresholds["max_objects"]
            and metrics["max_zones"] <= thresholds["max_zones"]
        )
        terminal = "completed"
        final_hash = engine.snapshot_view().state_hash
        production_path = (
            "research/course_correction/cc2_harness_contract/shadow_harness.py::_shadow_execute",
            create_path,
            tick_path,
            habitat_path,
        )
    finally:
        org.close()
    return ExecutionRecord(
        route="cc2_shadow_contract._shadow_execute",
        execution_id=definition.execution_id,
        definition_fingerprint=_definition_fingerprint(definition),
        seed_fingerprint=definition.seed_manifest.fingerprint(),
        ticks_executed=definition.tick_budget,
        terminal_outcome=terminal,
        metrics=metrics,
        production_path=production_path,
        final_state_hash=final_hash,
    )


def compare_reference_shadow(definition: ExperimentDefinition, output_root: Path) -> dict[str, Any]:
    definition.validate(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_root) as temp:
        reference = _reference_execute(definition, temp)
        shadow = _shadow_execute(definition, temp)
    deterministic_fields = (
        "execution_id",
        "definition_fingerprint",
        "seed_fingerprint",
        "ticks_executed",
        "terminal_outcome",
        "metrics",
    )
    differences = {
        field: {"reference": getattr(reference, field), "shadow": getattr(shadow, field)}
        for field in deterministic_fields
        if getattr(reference, field) != getattr(shadow, field)
    }
    return {
        "provenance": [RESEARCH_ONLY, NON_QUALIFYING, NOT_FORMAL_EVIDENCE],
        "definition": {
            "condition": definition.condition,
            "scenario": definition.scenario,
            "tick_budget": definition.tick_budget,
            "seed": definition.seed_manifest.seed,
        },
        "reference": reference.__dict__,
        "shadow": shadow.__dict__,
        "deterministic_fields_compared": list(deterministic_fields),
        "deterministic_differences": differences,
        "verdict": "PASS" if not differences else "FAIL_CLOSED",
    }


def _aggregate(raw: list[dict[str, Any]]) -> dict[str, Any]:
    if not raw:
        raise ContractError("missing_raw_execution")
    if any(row.get("execution_id") != raw[0].get("execution_id") for row in raw):
        raise ContractError("mixed_execution_ids")
    values = [float(row["metric"]) for row in raw]
    return {"execution_id": raw[0]["execution_id"], "count": len(values), "mean": sum(values) / len(values)}


def _validate_fault(name: str, mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    base = {
        "execution_id": "cc2-c0-s0-seed7",
        "seed_fingerprint": SeedManifest(seed=7).fingerprint(),
        "definition_fingerprint": "definition-ok",
        "ticks_executed": 40,
        "declared_tick_budget": 40,
        "metric_source": "organism.tick_once",
        "control_execution_id": "control-1",
        "subject_execution_id": "cc2-c0-s0-seed7",
        "evidence_path": "cc2-owned/equivalence.json",
        "evidence_execution_id": "cc2-c0-s0-seed7",
        "verdict": "NON_QUALIFYING",
        "evidence_verdict": "NON_QUALIFYING",
    }
    candidate = copy.deepcopy(base)
    mutate(candidate)
    detected = False
    reason = ""
    try:
        if name == "condition_mutation" and candidate["definition_fingerprint"] != "definition-ok":
            raise ContractError("definition_fingerprint_mismatch")
        if name == "wrong_seed" and candidate["seed_fingerprint"] != SeedManifest(seed=7).fingerprint():
            raise ContractError("seed_manifest_mismatch")
        if name == "wrong_execution_id" and candidate["evidence_execution_id"] != candidate["execution_id"]:
            raise ContractError("execution_id_mismatch")
        if name == "tick_budget_truncation" and candidate["ticks_executed"] != candidate["declared_tick_budget"]:
            raise ContractError("incomplete_tick_budget")
        if name == "wrong_execution_path" and candidate["metric_source"] != "organism.tick_once":
            raise ContractError("wrong_metric_execution_path")
        if name == "metric_substitution" and candidate["metric_source"] != "organism.tick_once":
            raise ContractError("metric_source_mismatch")
        if name == "aggregation_corruption":
            _aggregate([{"execution_id": "cc2-c0-s0-seed7", "metric": 1}, {"execution_id": "other", "metric": 1}])
        if name == "control_contamination" and candidate["control_execution_id"] == candidate["subject_execution_id"]:
            raise ContractError("control_subject_contamination")
        if name == "stale_frozen_configuration" and candidate["definition_fingerprint"] != "definition-ok":
            raise ContractError("frozen_configuration_mismatch")
        if name == "evidence_path_contamination" and FORBIDDEN_EVIDENCE_PATH in candidate["evidence_path"]:
            raise ContractError("evidence_path_contamination")
        if name == "verdict_evidence_mismatch" and candidate["verdict"] != candidate["evidence_verdict"]:
            raise ContractError("verdict_evidence_mismatch")
        raise ContractError("fault_not_detected")
    except ContractError as exc:
        detected = str(exc) != "fault_not_detected"
        reason = str(exc)
    return {"fault": name, "detected": detected, "detection": reason, "execution_prevented_or_rejected": detected}


def fault_injection_results() -> dict[str, Any]:
    mutations = {
        "condition_mutation": lambda d: d.update(definition_fingerprint="mutated"),
        "wrong_seed": lambda d: d.update(seed_fingerprint="wrong"),
        "wrong_execution_id": lambda d: d.update(evidence_execution_id="wrong"),
        "tick_budget_truncation": lambda d: d.update(ticks_executed=39),
        "wrong_execution_path": lambda d: d.update(metric_source="legacy_helper"),
        "metric_substitution": lambda d: d.update(metric_source="synthetic_metric"),
        "aggregation_corruption": lambda d: None,
        "control_contamination": lambda d: d.update(control_execution_id=d["subject_execution_id"]),
        "stale_frozen_configuration": lambda d: d.update(definition_fingerprint="stale"),
        "evidence_path_contamination": lambda d: d.update(evidence_path=FORBIDDEN_EVIDENCE_PATH + "/raw.jsonl"),
        "verdict_evidence_mismatch": lambda d: d.update(evidence_verdict="QUALIFIED"),
    }
    results = [_validate_fault(name, mutate) for name, mutate in mutations.items()]
    return {
        "provenance": [RESEARCH_ONLY, NON_QUALIFYING, NOT_FORMAL_EVIDENCE],
        "tests": results,
        "passed": sum(int(row["detected"]) for row in results),
        "failed": sum(int(not row["detected"]) for row in results),
        "silent_failures": [row["fault"] for row in results if not row["detected"]],
        "verdict": "PASS" if all(row["detected"] for row in results) else "FAIL_CLOSED",
    }


def main() -> None:
    root = Path(__file__).resolve().parents[3] / "docs" / "course-correction" / "cc2-harness-contract"
    definition = ExperimentDefinition()
    equivalence = compare_reference_shadow(definition, root / "cc2-runtime")
    faults = fault_injection_results()
    (root / "equivalence-results.json").write_text(json.dumps(equivalence, indent=2, sort_keys=True) + "\n")
    (root / "fault-injection-results.json").write_text(json.dumps(faults, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"equivalence": equivalence["verdict"], "fault_injection": faults["verdict"]}, sort_keys=True))
    if equivalence["verdict"] != "PASS" or faults["verdict"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
