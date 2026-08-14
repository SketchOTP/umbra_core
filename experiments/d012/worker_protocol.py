"""Bounded D-012 worker IPC and log records."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .failure_codes import SupervisionError

COMMANDS = frozenset({
    "START", "HEALTH", "RUN_EVENT", "QUIESCE", "RESUME",
    "CHECKPOINT_PREPARE", "SHUTDOWN", "RUN_DIAGNOSTIC_TICKS", "METRICS",
})
STATUSES = frozenset({
    "WORKER_READY", "WORKER_RUNNING", "WORKER_QUIESCED",
    "CHECKPOINT_READY", "WORKER_STOPPED", "WORKER_FAILED",
    "EVENT_COMPLETE", "TICKS_COMPLETE", "METRICS",
})
MAX_MESSAGE_BYTES = 16_384
MAX_LOG_BYTES = 65_536
MAX_LOG_FILES = 2


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SupervisionError("WORKER_MANIFEST_INVALID", str(exc)) from exc
    if not isinstance(value, dict):
        raise SupervisionError("WORKER_MANIFEST_INVALID", "not_object")
    return value


def validate_manifest(data: dict[str, Any]) -> dict[str, Any]:
    required = {
        "execution_id", "supervisor_execution_id", "root", "database_path",
        "ownership_path", "socket_path", "worker_log", "startup_status_path", "generation",
        "ownership_generation", "freeze_manifest_hash",
    }
    if required - data.keys():
        raise SupervisionError(
            "WORKER_MANIFEST_INVALID",
            "missing:" + ",".join(sorted(required - data.keys())),
        )
    if not isinstance(data["generation"], int) or data["generation"] < 1:
        raise SupervisionError("WORKER_MANIFEST_INVALID", "generation")
    root = Path(str(data["root"])).resolve()
    for key in ("database_path", "ownership_path", "socket_path", "worker_log", "startup_status_path"):
        path = Path(str(data[key])).resolve()
        if root not in path.parents:
            raise SupervisionError("WORKER_MANIFEST_INVALID", key)
    if data.get("diagnostic_trace_path"):
        path = Path(str(data["diagnostic_trace_path"])).resolve()
        if root not in path.parents:
            raise SupervisionError("WORKER_MANIFEST_INVALID", "diagnostic_trace_path")
    for key in (
        "formal_physiology_trace_path",
        "formal_recovery_trace_path",
        "formal_recovery_evaluation_trace_path",
        "formal_failure_path",
    ):
        if data.get(key):
            path = Path(str(data[key])).resolve()
            if root not in path.parents:
                raise SupervisionError("WORKER_MANIFEST_INVALID", key)
    formal_paths = [
        bool(data.get(key))
        for key in (
            "formal_physiology_trace_path",
            "formal_recovery_trace_path",
            "formal_recovery_evaluation_trace_path",
            "formal_failure_path",
        )
    ]
    if any(formal_paths) and not all(formal_paths):
        raise SupervisionError("WORKER_MANIFEST_INVALID", "formal_trace_paths")
    if data.get("diagnostic_recovery_reachable") and not data.get(
        "diagnostic_trace_path"
    ):
        raise SupervisionError(
            "WORKER_MANIFEST_INVALID", "diagnostic_recovery_reachable"
        )
    if data.get("d010_enabled"):
        raise SupervisionError("D010_ENABLED")
    if data.get("real_device"):
        raise SupervisionError("REAL_DEVICE_CONFIG_PROHIBITED")
    return data


def encode_message(message: dict[str, Any]) -> bytes:
    raw = (json.dumps(message, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(raw) > MAX_MESSAGE_BYTES or b'"raw_payload"' in raw:
        raise SupervisionError("IPC_MESSAGE_INVALID", "bounds_or_raw_payload")
    return raw


def decode_message(raw: bytes) -> dict[str, Any]:
    if not raw or len(raw) > MAX_MESSAGE_BYTES or b"raw_payload" in raw:
        raise SupervisionError("IPC_MESSAGE_INVALID", "bounds_or_raw_payload")
    try:
        message = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SupervisionError("IPC_MESSAGE_INVALID", str(exc)) from exc
    if not isinstance(message, dict):
        raise SupervisionError("IPC_MESSAGE_INVALID", "not_object")
    return message


def validate_command(
    message: dict[str, Any],
    *,
    execution_id: str,
    generation: int,
    process_start_identity: str,
    last_sequence: int,
) -> int:
    if message.get("execution_id") != execution_id:
        raise SupervisionError("IPC_EXECUTION_MISMATCH")
    if message.get("generation") != generation:
        raise SupervisionError("IPC_GENERATION_MISMATCH")
    if message.get("process_start_identity") != process_start_identity:
        raise SupervisionError("IPC_IDENTITY_MISMATCH")
    if not isinstance(message.get("active_runtime"), (int, float)):
        raise SupervisionError("IPC_MESSAGE_INVALID", "active_runtime")
    sequence = message.get("sequence")
    if not isinstance(sequence, int) or sequence != last_sequence + 1:
        raise SupervisionError("IPC_SEQUENCE_INVALID")
    if message.get("command") not in COMMANDS:
        raise SupervisionError("IPC_MESSAGE_INVALID", "command")
    return sequence


def status_message(
    status: str,
    *,
    execution_id: str,
    generation: int,
    sequence: int,
    process_start_identity: str,
    active_runtime: float,
    chain_tip: int | None,
    **extra: Any,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(status)
    return {
        "status": status,
        "execution_id": execution_id,
        "generation": generation,
        "sequence": sequence,
        "process_start_identity": process_start_identity,
        "active_runtime": active_runtime,
        "chain_tip": chain_tip,
        **extra,
    }


class BoundedLog:
    def __init__(
        self,
        path: Path,
        execution_id: str,
        *,
        generation: int | None = None,
        max_bytes: int = MAX_LOG_BYTES,
        max_files: int = MAX_LOG_FILES,
    ) -> None:
        self.path = path
        self.execution_id = execution_id
        self.generation = generation
        self.max_bytes = max_bytes
        self.max_files = max_files
        path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, **fields: Any) -> None:
        record = {"execution_id": self.execution_id, "event": event, **fields}
        if self.generation is not None:
            record["worker_generation"] = self.generation
        raw = encode_message(record)
        if self.path.exists() and self.path.stat().st_size + len(raw) > self.max_bytes:
            oldest = self.path.with_suffix(self.path.suffix + f".{self.max_files}")
            if oldest.exists():
                oldest.unlink()
            for index in range(self.max_files - 1, 0, -1):
                source = self.path if index == 1 else self.path.with_suffix(
                    self.path.suffix + f".{index - 1}"
                )
                if source.exists():
                    os.replace(source, self.path.with_suffix(self.path.suffix + f".{index}"))
        with self.path.open("ab") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
