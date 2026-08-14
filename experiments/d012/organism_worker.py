"""Spawn-only organism worker for the disposable D-012 campaign."""
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import socket
import sys
import time
from dataclasses import asdict, replace
from math import hypot
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d012.campaign_supervisor import freeze_hash
from experiments.d012.database_ownership import acquire_ownership, release_ownership
from experiments.d012.durability import atomic_write_text
from experiments.d012.failure_codes import SupervisionError
from experiments.d012.formal_contract_v2 import (
    CONTRACT_V1,
    CONTRACT_VERSION,
    INTEGRITY_FAILURE,
    RECOVERY_FAILED,
    evaluate_episode,
    normalize_trace_row,
    validate_contract_selection,
)
from experiments.d012.process_identity import process_identity
from experiments.d012.worker_protocol import (
    BoundedLog,
    MAX_MESSAGE_BYTES,
    decode_message,
    encode_message,
    read_json,
    status_message,
    validate_command,
    validate_manifest,
)
from umbra_core.embodiment import _make_partner
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.state import FreeLocation
from umbra_core.perception_adapters import (
    AdapterManifest,
    PerceptionAdapterError,
    SyntheticPerceptionAdapter,
)
from umbra_core.runtime import OrganismConfig, create_organism, load_organism
from umbra_core.util import canon_json, sha256_hex


def organism_config(database_path: Path) -> OrganismConfig:
    return OrganismConfig(
        db_path=str(database_path),
        seed=12012,
        snapshot_every=5,
        self_model_enabled=True,
        world_model_enabled=True,
        development_enabled=True,
        memory_enabled=True,
        social_enabled=True,
        individuality_enabled=True,
        embodiment_adapter_enabled=True,
        expression_enabled=True,
        habitat_enabled=True,
        temporal_enabled=False,
    )


class Worker:
    def __init__(self, manifest: dict[str, Any]) -> None:
        self.manifest = manifest
        self.execution_id = str(manifest["execution_id"])
        self.generation = int(manifest["generation"])
        self.database_path = Path(str(manifest["database_path"]))
        self.ownership_path = Path(str(manifest["ownership_path"]))
        self.socket_path = Path(str(manifest["socket_path"]))
        self.identity = process_identity(os.getpid())
        if not self.identity:
            raise SupervisionError("ORGANISM_START_FAILED", "process_identity")
        self.log = BoundedLog(
            Path(str(manifest["worker_log"])),
            self.execution_id,
            generation=self.generation,
        )
        self.last_sequence = 0
        self.active_runtime = float(manifest.get("active_runtime", 0.0))
        self.ownership_generation = int(manifest["ownership_generation"])
        self.ownership: dict[str, Any] | None = None
        self.organism = None
        self.engine = None
        self.adapter = SyntheticPerceptionAdapter(
            AdapterManifest(
                "dry-adapter", "1", ("visual_features",), {"visual_features": "v1"}
            )
        )
        schedule_path = Path(__file__).resolve().parent / "opportunity-schedule.json"
        self.schedule = json.loads(schedule_path.read_text())["events"]
        self.running = False
        self.stop_requested = False
        self.tick_period = float(manifest.get("tick_period_seconds", 0.5))
        self.diagnostic_trace_path = (
            Path(str(manifest["diagnostic_trace_path"]))
            if manifest.get("diagnostic_trace_path")
            else None
        )
        self.formal_physiology_trace_path = (
            Path(str(manifest["formal_physiology_trace_path"]))
            if manifest.get("formal_physiology_trace_path")
            else None
        )
        self.formal_recovery_trace_path = (
            Path(str(manifest["formal_recovery_trace_path"]))
            if manifest.get("formal_recovery_trace_path")
            else None
        )
        self.formal_recovery_evaluation_trace_path = (
            Path(str(manifest["formal_recovery_evaluation_trace_path"]))
            if manifest.get("formal_recovery_evaluation_trace_path")
            else None
        )
        self.formal_failure_path = (
            Path(str(manifest["formal_failure_path"]))
            if manifest.get("formal_failure_path")
            else None
        )
        self.tick_blocked = False
        self.recovery_contract_version = str(
            manifest.get("formal_recovery_contract_version", CONTRACT_V1)
        )
        self.recovery_contract_fingerprint = manifest.get("contract_fingerprint")
        try:
            validate_contract_selection(
                self.recovery_contract_version, self.recovery_contract_fingerprint
            )
        except ValueError as exc:
            raise SupervisionError("WORKER_MANIFEST_INVALID", str(exc)) from exc
        if (
            self.recovery_contract_version == CONTRACT_VERSION
            and self.formal_recovery_evaluation_trace_path is None
        ):
            raise SupervisionError(
                "WORKER_MANIFEST_INVALID",
                "V2 evaluation trace path missing",
            )
        self.recovery_episode_rows: list[dict[str, Any]] = (
            self._load_v2_evaluator_context()
            if self.recovery_contract_version == CONTRACT_VERSION
            else []
        )

    def _load_v2_evaluator_context(self) -> list[dict[str, Any]]:
        """Reconstruct harness-only evaluator state across worker generations."""
        path = self.formal_recovery_evaluation_trace_path
        if path is None or not path.exists():
            return []
        expected = {
            "directive": self.manifest.get("directive"),
            "formal_execution_id": self.execution_id,
            "starting_commit": self.manifest.get("starting_commit"),
            "configuration_fingerprint": self.manifest.get("configuration_fingerprint"),
            "contract_version": self.recovery_contract_version,
            "contract_fingerprint": self.recovery_contract_fingerprint,
        }
        rows: list[dict[str, Any]] = []
        previous: dict[str, Any] | None = None
        initialization_seen = False
        try:
            lines = path.read_text().splitlines()
        except OSError as exc:
            raise SupervisionError("WORKER_MANIFEST_INVALID", "evaluator_trace_unreadable") from exc
        for line_number, line in enumerate(lines, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SupervisionError(
                    "WORKER_MANIFEST_INVALID", f"evaluator_trace_json:{line_number}"
                ) from exc
            if not isinstance(record, dict):
                raise SupervisionError("WORKER_MANIFEST_INVALID", "evaluator_trace_record")
            for key, value in expected.items():
                if record.get(key) != value:
                    raise SupervisionError(
                        "WORKER_MANIFEST_INVALID", f"evaluator_trace_identity:{key}"
                    )
            record_type = record.get("record_type")
            if record_type == "EVALUATOR_INIT":
                if initialization_seen or "trace_row" in record:
                    raise SupervisionError(
                        "WORKER_MANIFEST_INVALID", "evaluator_trace_init_duplicate_or_payload"
                    )
                initialization_seen = True
                continue
            if record_type not in {None, "RECOVERY_EVALUATION"}:
                raise SupervisionError(
                    "WORKER_MANIFEST_INVALID", "evaluator_trace_record_type"
                )
            raw_row = record.get("trace_row")
            if not isinstance(raw_row, dict):
                raise SupervisionError("WORKER_MANIFEST_INVALID", "evaluator_trace_row_missing")
            normalized = normalize_trace_row(raw_row, previous)
            if record.get("material_evidence_key") != normalized.get("material_evidence_key"):
                raise SupervisionError("WORKER_MANIFEST_INVALID", "evaluator_trace_materiality_mismatch")
            rows.append(normalized)
            previous = normalized
        return rows

    def acquire_and_load(self, *, reclaim_dead: bool) -> None:
        self.ownership = acquire_ownership(
            self.ownership_path,
            execution_id=self.execution_id,
            database_path=self.database_path,
            supervisor_execution_id=str(self.manifest["supervisor_execution_id"]),
            generation=self.ownership_generation,
            reclaim_dead=reclaim_dead,
        )
        if self.manifest.get("crash_after_ownership"):
            os.kill(os.getpid(), signal.SIGKILL)
        config = organism_config(self.database_path)
        new = not self.database_path.exists()
        self.organism = create_organism(config) if new else load_organism(config)
        if new:
            self.organism._ensure_development_intervention()
            self.organism._ensure_memory_history()
            self.organism._ensure_social_history()
            self.organism._ensure_individuality_history()
        self.engine = HabitatEngine(_habitat_state_for_scenario("S2"))
        if self.manifest.get("diagnostic_recovery_reachable"):
            resource = next(
                obj
                for obj in self.engine.snapshot_view().objects.values()
                if isinstance(obj.location, FreeLocation)
            )
            self.engine.commit_free_location(
                resource.object_id,
                self.organism.embodiment.body.x,
                self.organism.embodiment.body.y,
            )
        self.organism.embodiment.attach_habitat_engine(self.engine)
        self.log.write("ownership_acquired", pid=os.getpid(), ownership_generation=self.ownership_generation)

    def quiesce(self) -> None:
        if self.organism is not None:
            self.organism.snapshot_if_due(force=True)
            self.organism.close()
            self.organism = None
            self.engine = None
        if self.ownership is not None:
            release_ownership(self.ownership_path, self.ownership)
            self.ownership = None
        self.running = False
        self.log.write("quiesced", ownership_generation=self.ownership_generation)

    def resume(self) -> None:
        if self.organism is not None or self.ownership is not None:
            raise SupervisionError("OWNERSHIP_TRANSFER_INCOMPLETE", "resume_while_owned")
        self.ownership_generation += 1
        self.acquire_and_load(reclaim_dead=False)
        self.running = True

    def chain_tip(self) -> int | None:
        return None if self.organism is None else self.organism.store.last_sequence()

    def identity_id(self) -> str | None:
        return None if self.organism is None else self.organism.identity.agent_id

    def metrics(self) -> dict[str, Any]:
        if not self.running or self.organism is None or self.engine is None:
            raise SupervisionError("IPC_MESSAGE_INVALID", "worker_not_running")
        organism = self.organism
        status = Path("/proc/self/status").read_text()
        rss_kib = int(next(line.split()[1] for line in status.splitlines() if line.startswith("VmRSS:")))
        memory = organism.memory
        social = organism.social
        world = organism.world_model
        individuality = organism.individuality
        habitat = self.engine.snapshot_view()
        conn = organism.store.conn
        organism.store.validate_chain()
        event_count = int(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])
        snapshot_count = int(conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0])
        journal_count = int(
            conn.execute("SELECT COUNT(*) FROM habitat_execution_journal").fetchone()[0]
        )
        raw_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM events WHERE instr(payload, '\"raw_payload\"') > 0"
            ).fetchone()[0]
        )
        children = Path(f"/proc/{os.getpid()}/task/{os.getpid()}/children").read_text().split()
        return {
            "tick": organism.tick,
            "rss_mib": rss_kib / 1024.0,
            "cpu_seconds": time.process_time(),
            "database_bytes": sum(
                path.stat().st_size
                for path in (
                    self.database_path,
                    self.database_path.with_suffix(self.database_path.suffix + "-wal"),
                    self.database_path.with_suffix(self.database_path.suffix + "-shm"),
                )
                if path.exists()
            ),
            "event_count": event_count,
            "snapshot_count": snapshot_count,
            "file_descriptor_count": len(list(Path("/proc/self/fd").iterdir())),
            "thread_count": len(list(Path("/proc/self/task").iterdir())),
            "child_process_count": len(children),
            "perception_observation_count": len(organism.perception.adapter_observations),
            "deduplication_id_count": len(
                organism.perception.accepted_adapter_observation_ids
            ),
            "memory_count": 0
            if memory is None
            else len(memory.episodes)
            + len(memory.archived)
            + len(memory.beliefs)
            + len(memory.procedural),
            "memory_count_max": 0
            if memory is None
            else memory.config.max_active_episodic
            + memory.config.max_archived
            + memory.config.max_semantic
            + memory.config.max_procedural,
            "social_hypothesis_count": 0 if social is None else len(social.hypotheses),
            "social_hypothesis_count_max": 0
            if social is None
            else social.config.max_partner_hypotheses,
            "routine_count": 0 if social is None else len(social.routine_handles),
            "routine_count_max": 0 if social is None else social.config.max_routine_handles,
            "world_model_count": 0 if world is None else len(world.models),
            "world_model_count_max": 0 if world is None else world.config.max_models,
            "individuality_evidence_count": 0
            if individuality is None
            else len(individuality.dispositions),
            "individuality_evidence_count_max": 64,
            "habitat_object_count": len(habitat.objects),
            "habitat_object_count_max": 64,
            "habitat_journal_count": journal_count,
            "expression_frame_count": organism._frame_id_counter,
            "expression_retained_count": len(organism.frame_ring),
            "expression_retained_count_max": organism.frame_ring.capacity,
            "physiology": organism.phys.as_dict(),
            "physiology_critical": organism.phys.critical_any(),
            "formal_failure": (
                json.loads(self.formal_failure_path.read_text())
                if self.formal_failure_path is not None
                and self.formal_failure_path.exists()
                else None
            ),
            "formal_recovery_contract_version": self.recovery_contract_version,
            "contract_fingerprint": self.recovery_contract_fingerprint,
            "proposal_count": int(
                conn.execute("SELECT COUNT(*) FROM events WHERE event_type='proposal'").fetchone()[0]
            ),
            "outcome_count": int(
                conn.execute(
                    "SELECT COUNT(*) FROM events WHERE event_type='outcome_verified'"
                ).fetchone()[0]
            ),
            "durable_raw_count": raw_count,
            "accepted_state_hash": sha256_hex(canon_json(organism.authoritative_state())),
            "chain_valid": True,
        }

    def run_diagnostic_ticks(self, count: int) -> list[dict[str, Any]]:
        if self.organism is None:
            raise SupervisionError("IPC_MESSAGE_INVALID", "worker_not_running")
        organism = self.organism
        rows: list[dict[str, Any]] = []
        selections: list[dict[str, Any]] = []
        original_select = organism.arbitrator.select

        def capture_select(*args: Any, **kwargs: Any) -> Any:
            candidate = original_select(*args, **kwargs)
            phys, observations, tick = args[:3]
            selections.append(
                {
                    "candidate": asdict(candidate),
                    "urgencies": phys.vector_urgency(),
                    "observations": [dict(row) for row in observations],
                    "tick": tick,
                }
            )
            return candidate

        organism.arbitrator.select = capture_select
        try:
            for _ in range(count):
                before = organism.phys.as_dict()
                before_tick = organism.tick
                before_sequence = int(organism.store.last_sequence() or 0)
                before_body = organism.embodiment.body.to_state()
                needs_recovery = organism.phys.needs_recovery()
                critical_before = organism.phys.critical_any()
                selections.clear()
                outcome = organism.tick_once()
                events = [
                    {
                        "sequence": int(row["sequence"]),
                        "event_type": str(row["event_type"]),
                        "payload": dict(row["payload"]),
                    }
                    for row in organism.store.iter_events(from_sequence=before_sequence + 1)
                ]
                opportunities = []
                for feature in organism.embodiment.habitat.features:
                    if feature.kind not in {"resource", "rest"}:
                        continue
                    distance = hypot(
                        float(before_body["x"]) - feature.x,
                        float(before_body["y"]) - feature.y,
                    )
                    opportunities.append(
                        {
                            "kind": feature.kind,
                            "distance": distance,
                            "radius": feature.radius,
                            "chargeable": feature.chargeable,
                            "restable": feature.restable,
                            "executable": distance <= feature.radius + 0.3,
                        }
                    )
                profile = (
                    None
                    if organism.embodiment_adapter is None
                    else organism.embodiment_adapter.profile
                )
                outcome_dict = (
                    None
                    if outcome is None
                    else dict(outcome)
                    if isinstance(outcome, dict)
                    else asdict(outcome)
                )
                executed = (
                    None if outcome_dict is None else outcome_dict.get("capability")
                )
                selection = next(
                    (
                        row
                        for row in reversed(selections)
                        if row["candidate"]["capability"] == executed
                    ),
                    selections[0] if selections else {},
                )
                candidate = dict(selection.get("candidate", {}))
                rows.append(
                    {
                        "tick": organism.tick,
                        "active_runtime_seconds": organism.tick
                        * float(self.tick_period),
                        "worker_generation": self.generation,
                        "physiology_before_tick": before,
                        "energy_drift": next(
                            (
                                row["payload"]["drift"]["energy"]
                                for row in events
                                if row["event_type"] == "physiology_drift"
                            ),
                            None,
                        ),
                        "selected_candidate": candidate.get("capability"),
                        "candidate_source": (
                            "recovery_reflex"
                            if needs_recovery or critical_before
                            else candidate.get("params", {}).get(
                                "source", "endogenous_arbitration"
                            )
                        ),
                        "arbitration_scores": candidate.get("scores", {}),
                        "arbitration_total": candidate.get("total"),
                        "urgencies": selection.get("urgencies", {}),
                        "observations": selection.get("observations", []),
                        "governance": next(
                            (
                                row["payload"]
                                for row in events
                                if row["event_type"] == "proposal"
                            ),
                            None,
                        ),
                        "body_or_habitat_validation": (
                            None if outcome_dict is None else outcome_dict.get("reason")
                        ),
                        "executed_capability": (
                            None
                            if outcome_dict is None
                            else outcome_dict.get("capability")
                        ),
                        "verified_outcome": outcome_dict,
                        "physiology_effect": (
                            None
                            if outcome_dict is None
                            else outcome_dict.get(
                                "physiology_effects", outcome_dict.get("effects")
                            )
                        ),
                        "physiology_after_tick": organism.phys.as_dict(),
                        "available_recovery_affordances": opportunities,
                        "body_capability_state": {
                            "attachment_status": None
                            if organism.embodiment_adapter is None
                            else organism.embodiment_adapter.state.attachment_status,
                            "profile_id": None if profile is None else profile.profile_id,
                            "supported_capabilities": []
                            if profile is None
                            else sorted(profile.supported_capabilities),
                        },
                        "event_sequences": [
                            row["sequence"] for row in events
                        ],
                        "event_types": [row["event_type"] for row in events],
                        "critical_before_tick": critical_before,
                        "critical_after_tick": organism.phys.critical_any(),
                        "tick_advanced": organism.tick - before_tick,
                    }
                )
        finally:
            organism.arbitrator.select = original_select
        if self.diagnostic_trace_path is not None:
            atomic_write_text(
                self.diagnostic_trace_path,
                "".join(
                    json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                    for row in rows
                ),
            )
        return rows

    @staticmethod
    def _append_trace(path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as handle:
            handle.write(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())

    def _record_v2_recovery_evaluation(self, row: dict[str, Any]) -> str | None:
        previous = self.recovery_episode_rows[-1] if self.recovery_episode_rows else None
        normalized = normalize_trace_row(row, previous)
        self.recovery_episode_rows.append(normalized)
        result = evaluate_episode(self.recovery_episode_rows)
        state = result["states"][-1]
        evaluation = {
            "record_type": "RECOVERY_EVALUATION",
            "tick": normalized.get("tick"),
            "directive": self.manifest.get("directive"),
            "formal_execution_id": self.execution_id,
            "starting_commit": self.manifest.get("starting_commit"),
            "configuration_fingerprint": self.manifest.get("configuration_fingerprint"),
            "verdict_namespace": self.manifest.get("verdict_namespace"),
            "contract_version": self.recovery_contract_version,
            "contract_fingerprint": self.recovery_contract_fingerprint,
            "worker_generation": self.generation,
            "candidate": normalized.get("selected_candidate"),
            "observation_signature": normalized.get("observation_signature"),
            "material_evidence_key": normalized.get("material_evidence_key"),
            "material_evidence_changed": normalized.get("material_evidence_changed"),
            "new_evidence": normalized.get("new_evidence"),
            "corrective_context": normalized.get("corrective_action"),
            "verified_outcome": normalized.get("verified_outcome"),
            "state": state["state"],
            "episode_state": result["terminal_state"],
            "failure_reason": state["reasons"] if state["state"] in {INTEGRITY_FAILURE, RECOVERY_FAILED} else [],
            "trace_row": normalized,
        }
        self._append_trace(self.formal_recovery_evaluation_trace_path, evaluation)
        if state["state"] in {INTEGRITY_FAILURE, RECOVERY_FAILED}:
            return state["state"] + ":" + ",".join(state["reasons"])
        return None

    def run_formal_tick(self) -> None:
        if self.formal_physiology_trace_path is None:
            if self.organism is not None:
                self.organism.tick_once()
            return
        row = self.run_diagnostic_ticks(1)[0]
        self._append_trace(self.formal_physiology_trace_path, row)
        before = row["physiology_before_tick"]
        after = row["physiology_after_tick"]
        recovery = row["candidate_source"] == "recovery_reflex"
        failure: str | None = None
        values = [float(value) for value in after.values()]
        if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in values):
            failure = "invalid_physiology_value"
        elif bool(row["critical_after_tick"]) or float(after["energy"]) < 0.05:
            failure = "invalid_physiological_state"
        if recovery:
            selected = row["selected_candidate"]
            outcome = row["verified_outcome"] or {}
            verified = outcome.get("outcome", outcome)
            effect = row["physiology_effect"] or verified.get("effects") or {}
            validation = row["body_or_habitat_validation"] or verified.get("reason")
            if validation is None and bool(verified.get("success")):
                validation = "ok"
            recovery_row = {
                **row,
                "recovery_urgency": row["urgencies"],
                "generated_recovery_candidates": [selected],
                "governance_decision": row["governance"],
                "embodiment_validation": validation,
                "verified_outcome": verified,
                "action_issued": outcome.get("action_issued"),
                "verified_action": outcome.get("verified"),
                "physiology_effect": effect,
                "available_charge_or_rest_opportunity": row[
                    "available_recovery_affordances"
                ],
                "energy_before_tick": before["energy"],
                "energy_after_tick": after["energy"],
                "decline_accounted": (
                    float(after["energy"]) >= float(before["energy"])
                    or (
                        row["energy_drift"] is not None
                        and selected in {"APPROACH", "MOVE", "RETREAT", "IDLE"}
                    )
                ),
            }
            self._append_trace(self.formal_recovery_trace_path, recovery_row)
            if self.recovery_contract_version == CONTRACT_VERSION:
                failure = self._record_v2_recovery_evaluation(recovery_row)
            else:
                if selected == "CHARGE" and (
                    validation != "ok"
                    or not bool(verified.get("success"))
                ):
                    failure = "charge_selected_but_not_executable"
                elif selected == "CHARGE" and float(after["energy"]) <= float(
                    before["energy"]
                ):
                    failure = "recovery_missing_positive_energy_effect"
                elif not recovery_row["decline_accounted"]:
                    failure = "unaccounted_energy_decline_during_recovery"
                elif selected == "CHARGE" and not effect:
                    failure = "recovery_missing_verified_effect"
        if failure is not None:
            self.tick_blocked = True
            atomic_write_text(
                self.formal_failure_path,
                json.dumps(
                    {"failure": failure, "triggering_state": row},
                    sort_keys=True,
                ),
            )

    def _change_environment(self, index: int) -> bool:
        if self.engine is None:
            return False
        for obj in self.engine.snapshot_view().objects.values():
            if isinstance(obj.location, FreeLocation):
                self.engine.commit_free_location(
                    obj.object_id, obj.location.x + (index + 1) * 0.001, obj.location.y
                )
                return True
        return False

    def run_event(self, index: int) -> dict[str, Any]:
        if not self.running or self.organism is None:
            raise SupervisionError("IPC_MESSAGE_INVALID", "worker_not_running")
        if index < 0 or index >= len(self.schedule):
            raise SupervisionError("IPC_MESSAGE_INVALID", "event_index")
        event = self.schedule[index]
        organism = self.organism
        external_effect = "none"
        if event["class"] == "ENVIRONMENTAL_CHANGE":
            external_effect = (
                "habitat_opportunity_changed"
                if self._change_environment(index)
                else "opportunity_marker"
            )
        if event["class"] == "PARTNER_BEHAVIOR":
            partner = _make_partner(
                f"dry-partner-{index}",
                organism.embodiment.body.x + 0.2,
                organism.embodiment.body.y + 0.2,
                "H1" if index < 10 else "H3",
                index=index,
                ambiguous="partner-b" in event["id"],
            )
            organism.embodiment._habitat.partners.append(partner)
            external_effect = "synthetic_partner_behavior"
        organism.tick_once()
        if event["class"] == "PERCEPTION_INPUT":
            if "adapter-restart" in event["id"]:
                self.adapter = SyntheticPerceptionAdapter(self.adapter.manifest)
            observation_id = f"dry-{index}"
            source = (
                "replacement-source"
                if "source-replace" in event["id"]
                else f"source-{index}"
            )
            envelope = self.adapter.submit(
                observation_id=observation_id,
                source_id=source,
                modality="visual_features",
                schema_version="v1",
                core_receipt_tick=organism.tick,
                source_timestamp=None,
                capture_interval=None,
                derived_features={"edge_count": index},
                confidence=0.3 if "source-replace" in event["id"] else 0.6,
                uncertainty=0.7 if "source-replace" in event["id"] else 0.4,
                provenance_chain=({"step": "dry", "source": source},),
                privacy_classification="DERIVED_ONLY",
                consent_state="CONSENT_GRANTED",
                retention_class="DERIVED_BOUNDED",
                replay_class="AUTHORITATIVE",
                integrity_metadata={"dry": "true"},
            )
            perception_result = {
                "observation_id": observation_id,
                "confidence": envelope.confidence,
                "uncertainty": envelope.uncertainty,
                "provenance_chain": list(envelope.provenance_chain),
                "privacy_classification": envelope.privacy_classification,
                "duplicate_attempts": 0,
                "duplicates_suppressed": 0,
            }
            if event["id"] == "p2-adapter-restart":
                try:
                    organism.submit_perception_observation(
                        replace(envelope, consent_state="CONSENT_REVOKED"),
                        self.adapter.manifest,
                    )
                except PerceptionAdapterError:
                    pass
                external_effect = "consent_revocation_rejected"
            else:
                organism.submit_perception_observation(envelope, self.adapter.manifest)
                external_effect = "derived_observation"
                if event["id"] == "p0-duplicate":
                    for _ in range(8):
                        if organism.submit_perception_observation(
                            envelope, self.adapter.manifest
                        ):
                            raise SupervisionError(
                                "SUPERVISOR_RECOVERY_FAILED", "duplicate"
                            )
                    perception_result["duplicate_attempts"] = 8
                    perception_result["duplicates_suppressed"] = 8
                    external_effect = "duplicate_suppressed"
                if "source-replace" in event["id"]:
                    delayed = replace(
                        envelope,
                        observation_id=observation_id + "-delayed",
                        core_receipt_tick=organism.tick - 1,
                    )
                    try:
                        organism.submit_perception_observation(
                            delayed, self.adapter.manifest
                        )
                    except ValueError:
                        external_effect = (
                            "source_replaced_delayed_out_of_order_rejected"
                        )
        if event["class"] == "BODY_CHANGE" and organism.embodiment_adapter:
            profile = (
                "MINIMAL_CREATURE_BODY" if index < 15 else "ABSTRACT_SHAPE_BODY"
            )
            if index >= 15:
                organism.embodiment_adapter.detach("dry-run")
                organism.embodiment_adapter.attach(profile)
            else:
                organism.embodiment_adapter.swap_profile(profile)
            external_effect = "body_adapter_lifecycle"
        organism.snapshot_if_due(force=True)
        result = {
            "index": index,
            "event": event["id"],
            "tick": organism.tick,
            "class": event["class"],
            "external_effect": external_effect,
            "organism_id": organism.identity.agent_id,
        }
        if event["class"] == "PERCEPTION_INPUT":
            result["perception"] = perception_result
        self.log.write(
            "event_complete", index=index, schedule_event=event["id"], tick=organism.tick
        )
        return result

    def response(self, status: str, sequence: int, **extra: Any) -> dict[str, Any]:
        return status_message(
            status,
            execution_id=self.execution_id,
            generation=self.generation,
            sequence=sequence,
            process_start_identity=self.identity,
            active_runtime=self.active_runtime,
            chain_tip=self.chain_tip(),
            worker_pid=os.getpid(),
            ownership_generation=self.ownership_generation,
            organism_id=self.identity_id(),
            **extra,
        )

    def handle(self, command: dict[str, Any]) -> dict[str, Any]:
        sequence = validate_command(
            command,
            execution_id=self.execution_id,
            generation=self.generation,
            process_start_identity=self.identity,
            last_sequence=self.last_sequence,
        )
        supplied_runtime = float(command["active_runtime"])
        if supplied_runtime < self.active_runtime:
            raise SupervisionError("IPC_MESSAGE_INVALID", "active_runtime_regression")
        supplied_tip = command.get("chain_tip")
        current_tip = self.chain_tip()
        if supplied_tip is not None and (
            current_tip is None or int(current_tip) < int(supplied_tip)
        ):
            raise SupervisionError("IPC_MESSAGE_INVALID", "chain_tip_mismatch")
        self.last_sequence = sequence
        self.active_runtime = supplied_runtime
        name = command["command"]
        if name == "HEALTH":
            return self.response(
                "WORKER_RUNNING" if self.running else "WORKER_READY", sequence
            )
        if name == "START":
            self.running = True
            return self.response("WORKER_RUNNING", sequence)
        if name == "RUN_EVENT":
            result = self.run_event(int(command["event_index"]))
            return self.response("EVENT_COMPLETE", sequence, event=result)
        if name == "RUN_DIAGNOSTIC_TICKS":
            if not self.running or self.organism is None:
                raise SupervisionError("IPC_MESSAGE_INVALID", "worker_not_running")
            count = int(command.get("count", 0))
            if count < 1 or count > 100_000:
                raise SupervisionError("IPC_MESSAGE_INVALID", "diagnostic_tick_count")
            self.log.write("diagnostic_ticks_started", count=count)
            self.run_diagnostic_ticks(count)
            return self.response("TICKS_COMPLETE", sequence, ticks=count)
        if name == "METRICS":
            return self.response("METRICS", sequence, metrics=self.metrics())
        if name in {"QUIESCE", "CHECKPOINT_PREPARE"}:
            if command.get("inject_crash"):
                os.kill(os.getpid(), signal.SIGKILL)
            self.quiesce()
            return self.response(
                "CHECKPOINT_READY" if name == "CHECKPOINT_PREPARE" else "WORKER_QUIESCED",
                sequence,
            )
        if name == "RESUME":
            self.resume()
            return self.response("WORKER_RUNNING", sequence)
        if name == "SHUTDOWN":
            self.quiesce()
            self.stop_requested = True
            return self.response("WORKER_STOPPED", sequence)
        raise SupervisionError("IPC_MESSAGE_INVALID", name)


def serve(manifest_path: Path) -> int:
    manifest = validate_manifest(read_json(manifest_path))
    expected = str(manifest["freeze_manifest_hash"])
    if freeze_hash(Path(__file__).resolve().parent) != expected:
        raise SupervisionError("FREEZE_HASH_MISMATCH")
    if manifest.get("crash_before_ready"):
        os.kill(os.getpid(), signal.SIGKILL)
    worker = Worker(manifest)
    worker.acquire_and_load(reclaim_dead=bool(manifest.get("reclaim_dead")))
    if worker.socket_path.exists():
        worker.socket_path.unlink()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(worker.socket_path))
    os.chmod(worker.socket_path, 0o600)
    server.listen(1)
    server.settimeout(worker.tick_period)
    worker.log.write("worker_ready", pid=os.getpid(), process_start_identity=worker.identity)
    try:
        while not worker.stop_requested:
            try:
                connection, _ = server.accept()
            except TimeoutError:
                if worker.running and worker.organism is not None:
                    if not worker.tick_blocked:
                        worker.run_formal_tick()
                continue
            with connection:
                raw = b""
                while not raw.endswith(b"\n"):
                    chunk = connection.recv(MAX_MESSAGE_BYTES + 1 - len(raw))
                    if not chunk:
                        break
                    raw += chunk
                    if len(raw) > MAX_MESSAGE_BYTES:
                        break
                try:
                    response = worker.handle(decode_message(raw))
                except SupervisionError as exc:
                    response = worker.response(
                        "WORKER_FAILED",
                        int(worker.last_sequence),
                        failure_code=exc.code,
                        reason=str(exc),
                    )
                except Exception as exc:
                    worker.log.write(
                        "worker_error", error_type=type(exc).__name__, reason=str(exc)
                    )
                    response = worker.response(
                        "WORKER_FAILED",
                        int(worker.last_sequence),
                        failure_code="SUPERVISOR_RECOVERY_FAILED",
                        reason=f"{type(exc).__name__}:{exc}",
                    )
                connection.sendall(encode_message(response))
    finally:
        server.close()
        if worker.socket_path.exists():
            worker.socket_path.unlink()
        if worker.organism is not None or worker.ownership is not None:
            worker.quiesce()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        return serve(args.manifest)
    except SupervisionError as exc:
        try:
            manifest = json.loads(args.manifest.read_text())
            status_path = Path(str(manifest["startup_status_path"]))
            atomic_write_text(status_path, json.dumps(
                {"failure_code": exc.code, "reason": str(exc)}, sort_keys=True
            ))
        except (OSError, KeyError, json.JSONDecodeError):
            pass
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
