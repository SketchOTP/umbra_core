"""Spawn, authenticate, control, and reattach a D-012 organism worker."""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .durability import atomic_write_text
from .failure_codes import SupervisionError
from .process_identity import identity_matches, process_identity
from .worker_cleanup import terminate_worker, wait_dead
from .worker_protocol import MAX_MESSAGE_BYTES, decode_message, encode_message


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(manifest, sort_keys=True))


class WorkerClient:
    def __init__(
        self,
        *,
        execution_id: str,
        generation: int,
        socket_path: Path,
        pid: int,
        identity: str,
        process: subprocess.Popen[bytes] | None,
        sequence: int = 0,
        active_runtime: float = 0.0,
        chain_tip: int | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.generation = generation
        self.socket_path = socket_path
        self.pid = pid
        self.identity = identity
        self.process = process
        self.sequence = sequence
        self.active_runtime = active_runtime
        self.chain_tip = chain_tip

    @classmethod
    def launch(
        cls,
        manifest_path: Path,
        manifest: dict[str, Any],
        *,
        timeout: float = 5.0,
    ) -> "WorkerClient":
        write_manifest(manifest_path, manifest)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "experiments.d012.organism_worker",
                "--manifest",
                str(manifest_path),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        identity = process_identity(process.pid)
        if not identity:
            process.kill()
            process.wait()
            raise SupervisionError("ORGANISM_START_FAILED", "identity")
        socket_path = Path(str(manifest["socket_path"]))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                startup_status = Path(str(manifest["startup_status_path"]))
                if startup_status.exists():
                    failure = json.loads(startup_status.read_text())
                    raise SupervisionError(
                        str(failure.get("failure_code", "ORGANISM_START_FAILED")),
                        str(failure.get("reason", "")),
                    )
                raise SupervisionError(
                    "ORGANISM_START_FAILED", f"exit:{process.returncode}"
                )
            if socket_path.exists():
                client = cls(
                    execution_id=str(manifest["execution_id"]),
                    generation=int(manifest["generation"]),
                    socket_path=socket_path,
                    pid=process.pid,
                    identity=identity,
                    process=process,
                    active_runtime=float(manifest.get("active_runtime", 0.0)),
                )
                ready = client.request("HEALTH")
                if ready["status"] != "WORKER_READY":
                    client.force_kill()
                    raise SupervisionError("ORGANISM_START_FAILED", "not_ready")
                return client
            time.sleep(0.01)
        terminate_worker(process.pid, identity, force=True)
        raise SupervisionError("ORGANISM_START_FAILED", "timeout")

    @classmethod
    def reattach(
        cls,
        *,
        execution_id: str,
        generation: int,
        socket_path: Path,
        pid: int,
        identity: str,
        sequence: int,
        active_runtime: float = 0.0,
        chain_tip: int | None = None,
    ) -> "WorkerClient":
        if not identity_matches(pid, identity) or not socket_path.exists():
            raise SupervisionError("SUPERVISOR_RECOVERY_FAILED", "worker_absent")
        client = cls(
            execution_id=execution_id,
            generation=generation,
            socket_path=socket_path,
            pid=pid,
            identity=identity,
            process=None,
            sequence=sequence,
            active_runtime=active_runtime,
            chain_tip=chain_tip,
        )
        client.request("HEALTH")
        return client

    def raw_request(self, message: dict[str, Any]) -> dict[str, Any]:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(5.0)
            connection.connect(str(self.socket_path))
            connection.sendall(encode_message(message))
            raw = b""
            while not raw.endswith(b"\n"):
                chunk = connection.recv(MAX_MESSAGE_BYTES + 1 - len(raw))
                if not chunk:
                    break
                raw += chunk
            return decode_message(raw)

    def request(self, command: str, **fields: Any) -> dict[str, Any]:
        if not identity_matches(self.pid, self.identity):
            raise SupervisionError("ORGANISM_EXIT_UNEXPECTED")
        next_sequence = self.sequence + 1
        active_runtime = float(fields.pop("active_runtime", self.active_runtime))
        response = self.raw_request(
            {
                "command": command,
                "execution_id": self.execution_id,
                "generation": self.generation,
                "sequence": next_sequence,
                "process_start_identity": self.identity,
                "active_runtime": active_runtime,
                "chain_tip": self.chain_tip,
                **fields,
            }
        )
        if response.get("status") == "WORKER_FAILED":
            code = str(response.get("failure_code", "SUPERVISOR_RECOVERY_FAILED"))
            raise SupervisionError(code, str(response.get("reason", "")))
        if response.get("execution_id") != self.execution_id:
            raise SupervisionError("IPC_EXECUTION_MISMATCH")
        if response.get("generation") != self.generation:
            raise SupervisionError("IPC_GENERATION_MISMATCH")
        if response.get("sequence") != next_sequence:
            raise SupervisionError("IPC_SEQUENCE_INVALID")
        if response.get("process_start_identity") != self.identity:
            raise SupervisionError("IPC_IDENTITY_MISMATCH")
        self.sequence = next_sequence
        self.active_runtime = float(response["active_runtime"])
        self.chain_tip = response.get("chain_tip")
        return response

    def shutdown(self, active_runtime: float) -> dict[str, Any]:
        response = self.request("SHUTDOWN", active_runtime=active_runtime)
        wait_dead(self.pid, self.identity)
        return response

    def force_kill(self) -> None:
        terminate_worker(self.pid, self.identity, force=True)

    def terminate(self) -> None:
        terminate_worker(self.pid, self.identity, force=False)


def manifest_for(
    root: Path,
    *,
    execution_id: str,
    generation: int,
    ownership_generation: int,
    freeze_manifest_hash: str,
    active_runtime: float,
    reclaim_dead: bool = False,
    **test_flags: Any,
) -> dict[str, Any]:
    return {
        "execution_id": execution_id,
        "supervisor_execution_id": execution_id,
        "root": str(root),
        "database_path": str(root / "dry-run.sqlite"),
        "ownership_path": str(root / "database-ownership.json"),
        "socket_path": str(root / f"organism-worker-{generation}.sock"),
        "worker_log": str(root / "organism-worker.log"),
        "startup_status_path": str(root / f"worker-startup-{generation}.json"),
        "generation": generation,
        "ownership_generation": ownership_generation,
        "freeze_manifest_hash": freeze_manifest_hash,
        "active_runtime": active_runtime,
        "d010_enabled": False,
        "real_device": False,
        "reclaim_dead": reclaim_dead,
        **test_flags,
    }
