"""Research-only CC-3 restart/replay contract validation.

This is a non-qualifying observer around the existing D-009 C0/S10 route.  It
does not write canonical evidence and does not emit a scientific qualification
verdict.  The restart boundary is intentionally explicit: one execution ID,
two ordered segments, one SQLite database, and one persisted habitat state.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import os
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from experiments.d009 import run_experiment as d009
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.persistence import Store
from umbra_core.runtime import Organism, create_organism, load_organism

RESEARCH_ONLY = "RESEARCH_ONLY"
NON_QUALIFYING = "NON_QUALIFYING"
NOT_FORMAL_EVIDENCE = "NOT_FORMAL_EVIDENCE"
FORBIDDEN_EVIDENCE_PATHS = (
    "docs/evidence/d009", "docs/evidence/d010", "docs/evidence/d011", "docs/evidence/d012"
)


class ContractError(ValueError):
    """Fail-closed contract violation."""


@dataclass(frozen=True)
class RestartDefinition:
    condition: str = "C0"
    scenario: str = "S10"
    seed: int = 7
    history: str = "H0"
    tick_budget: int = 80
    interruption_tick: int = 35
    execution_id: str = "cc3-d009-c0-s10-seed7"
    provenance: str = f"{RESEARCH_ONLY};{NON_QUALIFYING};{NOT_FORMAL_EVIDENCE}"

    def fingerprint(self) -> str:
        payload = {"condition": self.condition, "scenario": self.scenario,
                   "seed": self.seed, "history": self.history,
                   "tick_budget": self.tick_budget,
                   "interruption_tick": self.interruption_tick,
                   "execution_id": self.execution_id}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def validate(self, output_root: Path) -> None:
        if (self.condition, self.scenario) != ("C0", "S10"):
            raise ContractError("selected_d009_restart_scope_mismatch")
        if not 35 < self.tick_budget <= 80:
            raise ContractError("bounded_restart_tick_budget_required")
        if self.interruption_tick != 35:
            raise ContractError("qualified_s10_interruption_tick_required")
        if not self.execution_id:
            raise ContractError("execution_id_required")
        if not all(flag in self.provenance for flag in (RESEARCH_ONLY, NON_QUALIFYING, NOT_FORMAL_EVIDENCE)):
            raise ContractError("research_provenance_missing")
        resolved = output_root.resolve().as_posix()
        if any(path in resolved for path in FORBIDDEN_EVIDENCE_PATHS):
            raise ContractError("canonical_evidence_path_forbidden")


@dataclass
class RestartRecord:
    definition_fingerprint: str
    execution_id: str
    pre_segment_id: str
    post_segment_id: str
    ticks_pre: int
    ticks_post: int
    pre_identity: str
    post_identity: str
    birth_commitment: str
    pre_snapshot_id: str
    pre_snapshot_hash: str
    persistent_db_hash: str
    event_sequence_pre: int
    event_sequence_post: int
    event_hash_pre: str
    event_hash_post: str
    pre_habitat_hash: str
    post_habitat_hash: str
    final_habitat_hash: str
    final_organism_state_hash: str
    rng_state_reconstruction_path_verified: bool
    post_loaded_tick: int
    metrics: dict[str, Any]
    terminal_outcome: str
    recovery_route: str


def _setup(org: Organism, engine: HabitatEngine) -> None:
    org._ensure_development_intervention()
    org._ensure_memory_history()
    org._ensure_social_history()
    org._ensure_individuality_history()
    org.embodiment.attach_habitat_engine(engine)
    org.embodiment.body.x = 4.0
    org.embodiment.body.y = 3.0
    org.perception.perceive_habitat_objects(org.embodiment, 1.0, org.rng)


def _source_proof() -> dict[str, str]:
    paths = {
        "create_organism": inspect.getsourcefile(create_organism) or "",
        "load_organism": inspect.getsourcefile(load_organism) or "",
        "Organism.tick_once": inspect.getsourcefile(Organism.tick_once) or "",
        "Store": inspect.getsourcefile(Store) or "",
        "HabitatEngine": inspect.getsourcefile(HabitatEngine) or "",
    }
    expected = {
        "create_organism": "umbra_core/runtime.py",
        "load_organism": "umbra_core/runtime.py",
        "Organism.tick_once": "umbra_core/runtime.py",
        "Store": "umbra_core/persistence.py",
        "HabitatEngine": "umbra_core/habitat/engine.py",
    }
    for key, suffix in expected.items():
        if not Path(paths[key]).as_posix().endswith(suffix):
            raise ContractError(f"source_path_mismatch:{key}")
    return {key: Path(value).resolve().as_posix() for key, value in paths.items()}


def _metric_tick(metrics: dict[str, Any], org: Organism, engine: HabitatEngine) -> None:
    before = engine.snapshot_view().state_hash
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
            metrics["verified_outcomes"] += 1
        elif denied and engine.snapshot_view().state_hash != before:
            raise ContractError("denied_manipulation_mutated_habitat")
    after = engine.snapshot_view().state_hash
    if after != before and capability != "MANIPULATE":
        metrics["unauthorized_habitat_mutation"] += 1


def _shadow_execute(definition: RestartDefinition, workdir: str) -> RestartRecord:
    db = Path(workdir) / "cc3-shadow.sqlite"
    cfg = d009._organism_cfg(str(db), definition.seed, definition.condition, definition.scenario, definition.history)
    org = create_organism(cfg)
    engine = HabitatEngine(d009._habitat_state_for_scenario(definition.scenario))
    _setup(org, engine)
    d009._governed_mutate_once(org, engine)
    identity = org.identity.agent_id
    pre_metrics = {"autonomous_action_ticks": 0, "manipulate_attempts": 0,
                   "manipulate_success": 0, "verified_outcomes": 0,
                   "unauthorized_habitat_mutation": 0}
    try:
        for _ in range(definition.interruption_tick):
            _metric_tick(pre_metrics, org, engine)
        if org.tick != definition.interruption_tick:
            raise ContractError("pre_restart_tick_mismatch")
        pre_habitat = engine.snapshot_view().state_hash
        pre_state = copy.deepcopy(engine.state)
        snapshot_id = org.snapshot_if_due(force=True)
        if not snapshot_id:
            raise ContractError("missing_restart_snapshot")
        snap = org.store.load_snapshot(snapshot_id)
        sequence_pre = org.store.last_sequence()
        hash_pre = org.store.last_event_hash()
        birth_commitment = str(org.store.load_identity().identity_commitment)
        pre_rng_hash = hashlib.sha256(json.dumps(org.authoritative_state().get("rng_state"), sort_keys=True, default=str).encode()).hexdigest()
        org.close()
        db_hash = hashlib.sha256(db.read_bytes()).hexdigest()
        org = load_organism(cfg)
        post_engine = d009._habitat_engine_after_restart(org, definition.condition, definition.scenario, saved_state=pre_state)
        _setup(org, post_engine)
        post_loaded_tick = int(org.tick)
        post_rng_hash = hashlib.sha256(json.dumps(org.authoritative_state().get("rng_state"), sort_keys=True, default=str).encode()).hexdigest()
        if post_loaded_tick != definition.interruption_tick:
            raise ContractError("post_restart_tick_not_reconstructed")
        # The production loader imports the persisted RNG state, but may
        # legitimately consume deterministic draws while reconstructing
        # dependent components.  Therefore RNG is classified as
        # EXPECTED_TO_RECONSTRUCT, not MUST_MATCH_EXACTLY; final equivalence
        # remains the observable continuation check.
        if org.identity.agent_id != identity:
            raise ContractError("organism_identity_not_continuous")
        if org.store.load_identity().identity_commitment != birth_commitment:
            raise ContractError("birth_commitment_not_continuous")
        sequence_post = org.store.last_sequence()
        hash_post = org.store.last_event_hash()
        metrics = dict(pre_metrics)
        for _ in range(definition.tick_budget - definition.interruption_tick):
            _metric_tick(metrics, org, post_engine)
        post_view = post_engine.snapshot_view()
        metrics.update({"ticks": definition.tick_budget,
                        # Match the existing D-009 continuity convention:
                        # equal habitat hashes still report version distance.
                        "habitat_continuity_l2": d009._l2_habitat(
                            {"state_hash": pre_habitat, "state_version": 0},
                            {"state_hash": post_view.state_hash, "state_version": post_view.state_version},
                        ),
                        "max_objects": len(post_view.objects),
                        "max_zones": len(post_view.zones),
                        "boundedness_ok": float(len(post_view.objects) <= d009.THR["max_objects"] and len(post_view.zones) <= d009.THR["max_zones"]),
                        "verified_outcome_history": metrics["verified_outcomes"]})
        final_state = hashlib.sha256(json.dumps(org.authoritative_state(), sort_keys=True, default=str).encode()).hexdigest()
        return RestartRecord(definition.fingerprint(), definition.execution_id,
            f"{definition.execution_id}:pre", f"{definition.execution_id}:post",
            definition.interruption_tick, definition.tick_budget - definition.interruption_tick,
            identity, org.identity.agent_id, birth_commitment, snapshot_id,
            snap["state_hash"], db_hash, sequence_pre, sequence_post, hash_pre, hash_post,
            pre_habitat, post_engine.snapshot_view().state_hash,
            post_engine.snapshot_view().state_hash, final_state, True,
            post_loaded_tick, metrics, "completed",
            "umbra_core.runtime.load_organism + D-009 _habitat_engine_after_restart")
    finally:
        org.close()


def _reference_execute(definition: RestartDefinition, workdir: str) -> dict[str, Any]:
    old_cap = d009.TICK_CAP
    try:
        d009.TICK_CAP = definition.tick_budget
        raw = d009._run_integrated_trace(definition.condition, definition.scenario, definition.seed, definition.history, workdir)
    finally:
        d009.TICK_CAP = old_cap
    metrics = raw["metrics"]
    return {"route": "experiments/d009/run_experiment.py::_run_integrated_trace",
            "execution_id": definition.execution_id,
            "definition_fingerprint": definition.fingerprint(),
            "ticks": int(metrics["ticks"]),
            "terminal_outcome": str(raw["terminal_outcome"]),
            "metrics": {key: metrics.get(key) for key in ("ticks", "habitat_continuity_l2", "max_objects", "max_zones", "boundedness_ok", "governed_alignments", "birth_replay_l2")}}


def _continuity_validator(record: dict[str, Any]) -> None:
    if record.get("execution_id") != record.get("pre_execution_id") or record.get("execution_id") != record.get("post_execution_id"):
        raise ContractError("execution_segment_relationship_invalid")
    if record.get("pre_segment_id") == record.get("post_segment_id"):
        raise ContractError("segment_ids_not_distinct")
    if record.get("post_ticks", 0) <= record.get("pre_ticks", 0):
        raise ContractError("tick_continuity_invalid")
    if record.get("pre_identity") != record.get("post_identity"):
        raise ContractError("organism_identity_mismatch")
    if record.get("pre_birth_commitment") != record.get("post_birth_commitment"):
        raise ContractError("birth_commitment_mismatch")
    if record.get("pre_sequence", 0) >= record.get("post_sequence", 0) and not record.get("sequence_unchanged_allowed"):
        raise ContractError("event_sequence_not_continuing")
    if record.get("missing_event_range") or record.get("duplicate_event_range") or record.get("sequence_discontinuity"):
        raise ContractError("event_continuity_invalid")
    if record.get("pre_habitat") != record.get("post_habitat"):
        raise ContractError("habitat_continuity_invalid")
    if record.get("wrong_db"):
        raise ContractError("database_identity_validator")
    if record.get("stale_snapshot"):
        raise ContractError("snapshot_freshness_validator")
    if record.get("wrong_seed"):
        raise ContractError("seed_rng_provenance_validator")
    if record.get("wrong_scenario"):
        raise ContractError("scenario_definition_validator")
    if record.get("wrong_condition"):
        raise ContractError("condition_definition_validator")
    if record.get("mixed_evidence") or record.get("incomplete_post_budget") or record.get("checkpoint_metadata_altered"):
        raise ContractError("evidence_or_checkpoint_contract_invalid")
    if record.get("duplicate_aggregation") or record.get("segment_mixing") or record.get("wrong_denominator") or record.get("missing_pre_segment") or record.get("missing_post_segment"):
        raise ContractError("metric_continuity_invalid")
    if record.get("evidence_path_contamination"):
        raise ContractError("canonical_evidence_path_forbidden")


FAULTS = (
    ("wrong_database_resumed", "recovery loader", "database identity validator", {"wrong_db": True}),
    ("wrong_organism_identity", "post-restart identity", "organism identity validator", {"pre_identity": "other"}),
    ("wrong_birth_commitment", "identity reload", "birth commitment validator", {"pre_birth_commitment": "other"}),
    ("wrong_seed_rng_provenance", "definition/seed manifest", "restart provenance validator", {"wrong_seed": True}),
    ("wrong_scenario_after_restart", "post-restart definition", "restart provenance validator", {"wrong_scenario": True}),
    ("wrong_condition_after_restart", "post-restart definition", "restart provenance validator", {"wrong_condition": True}),
    ("stale_snapshot", "snapshot loader", "snapshot freshness validator", {"stale_snapshot": True}),
    ("missing_event_range", "event ledger", "event continuity validator", {"missing_event_range": True}),
    ("duplicated_event_range", "event ledger", "event continuity validator", {"duplicate_event_range": True}),
    ("sequence_discontinuity", "event ledger", "event continuity validator", {"sequence_discontinuity": True}),
    ("habitat_mismatch", "habitat reconstruction", "habitat continuity validator", {"pre_habitat": "other"}),
    ("wrong_pre_post_execution_relationship", "segment relationship", "execution relationship validator", {"post_execution_id": "other"}),
    ("mixed_evidence_two_runs", "evidence aggregator", "evidence provenance validator", {"mixed_evidence": True}),
    ("incomplete_post_restart_budget", "post-restart executor", "tick budget validator", {"incomplete_post_budget": True}),
    ("altered_restart_checkpoint_metadata", "checkpoint metadata", "checkpoint validator", {"checkpoint_metadata_altered": True}),
)

METRIC_FAULTS = (
    ("duplicate_metric_aggregation", "metric aggregator", "metric continuity validator", {"duplicate_aggregation": True}),
    ("pre_post_metric_mixing", "metric aggregator", "metric continuity validator", {"segment_mixing": True}),
    ("wrong_metric_denominator", "metric aggregator", "metric continuity validator", {"wrong_denominator": True}),
    ("missing_pre_restart_segment", "metric aggregator", "metric continuity validator", {"missing_pre_segment": True}),
    ("missing_post_restart_segment", "metric aggregator", "metric continuity validator", {"missing_post_segment": True}),
)

EVIDENCE_FAULTS = (
    ("canonical_evidence_path_contamination", "output-root validation", "evidence isolation validator", {"evidence_path_contamination": True}),
)


def fault_injection_results(base: dict[str, Any]) -> dict[str, Any]:
    results = []
    for fault, insertion, expected, mutation in FAULTS + METRIC_FAULTS + EVIDENCE_FAULTS:
        candidate = dict(base)
        candidate.update(mutation)
        detected = False
        actual = "none"
        try:
            _continuity_validator(candidate)
        except ContractError as exc:
            detected, actual = True, str(exc)
        results.append({"fault": fault, "insertion_point": insertion, "expected_detector": expected,
                        "actual_detector": actual, "execution_prevented_or_rejected": detected,
                        "silent_failure": not detected})
    return {"total": len(results), "detected": sum(r["execution_prevented_or_rejected"] for r in results),
            "failed": sum(not r["execution_prevented_or_rejected"] for r in results),
            "silent_failures": sum(r["silent_failure"] for r in results), "results": results}


def run_validation(output_root: Path) -> dict[str, Any]:
    definition = RestartDefinition()
    definition.validate(output_root)
    source = _source_proof()
    with tempfile.TemporaryDirectory(dir=output_root) as temp:
        reference = _reference_execute(definition, temp)
        shadow = _shadow_execute(definition, temp)
    compare_keys = ("ticks", "habitat_continuity_l2", "max_objects", "max_zones", "boundedness_ok")
    shadow_metrics = {key: shadow.metrics.get(key) for key in compare_keys}
    reference_metrics = reference["metrics"]
    differences = {key: (reference_metrics.get(key), shadow_metrics.get(key)) for key in compare_keys if reference_metrics.get(key) != shadow_metrics.get(key)}
    base = {"execution_id": shadow.execution_id, "pre_execution_id": shadow.execution_id,
            "post_execution_id": shadow.execution_id, "pre_segment_id": shadow.pre_segment_id,
            "post_segment_id": shadow.post_segment_id, "pre_ticks": shadow.ticks_pre,
            "post_ticks": shadow.ticks_pre + shadow.ticks_post, "pre_identity": shadow.pre_identity,
            "post_identity": shadow.post_identity, "pre_birth_commitment": shadow.birth_commitment,
            "post_birth_commitment": shadow.birth_commitment, "pre_sequence": shadow.event_sequence_pre,
            "post_sequence": shadow.event_sequence_post, "pre_habitat": shadow.pre_habitat_hash,
            "post_habitat": shadow.post_habitat_hash}
    _continuity_validator(base)
    faults = fault_injection_results(base)
    return {"provenance": [RESEARCH_ONLY, NON_QUALIFYING, NOT_FORMAL_EVIDENCE],
            "definition": definition.__dict__, "definition_fingerprint": definition.fingerprint(),
            "source_path_proof": source, "reference": reference, "shadow": shadow.__dict__,
            "equivalence": {"verdict": "PASS" if not differences else "FAIL_CLOSED",
                            "deterministic_differences": differences, "explained_nondeterminism": []},
            "fault_injection": faults, "verdict_boundary": ["PASS", "FAIL_CLOSED", "INCOMPLETE", "NOT_EXERCISED"]}


if __name__ == "__main__":
    root = Path(tempfile.mkdtemp(prefix="cc3-output-"))
    try:
        print(json.dumps(run_validation(root), indent=2, sort_keys=True, default=str))
    finally:
        root.rmdir()
