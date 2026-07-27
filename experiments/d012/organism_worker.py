"""Spawn-only organism worker for the disposable D-012 campaign."""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import sys
from dataclasses import replace
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
                    if organism.submit_perception_observation(
                        envelope, self.adapter.manifest
                    ):
                        raise SupervisionError("SUPERVISOR_RECOVERY_FAILED", "duplicate")
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
        if supplied_tip is not None and supplied_tip != self.chain_tip():
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
            self.organism.run_ticks(count)
            return self.response("TICKS_COMPLETE", sequence, ticks=count)
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
    worker.log.write("worker_ready", pid=os.getpid(), process_start_identity=worker.identity)
    try:
        while not worker.stop_requested:
            connection, _ = server.accept()
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
