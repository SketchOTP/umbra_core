"""Publish AS-014 Path A/B selection from immutable forensic artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.as014_evidence import ROOT as EVIDENCE_ROOT
from tools.as014_evidence import publish


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    attribution = EVIDENCE_ROOT / "AS014_AS013_STORAGE_ATTRIBUTION.json"
    matrix = EVIDENCE_ROOT / "AS014_EVENT_DEPENDENCY_MATRIX.json"
    data = json.loads(attribution.read_text())
    event_bytes = next(
        item["physical_bytes"]
        for item in data["physical_database"]["objects"]
        if item["name"] == "events"
    )
    total = int(data["physical_database"]["main_file_bytes"])
    publish("AS014_ROOT_CAUSE_DECISION.json", {
        "directive": "UMBRA-AS-014",
        "baseline": "a97171a2dab7c1750e2556727bce9e3648bb359a",
        "inputs": {
            "storage_attribution_sha256": sha(attribution),
            "event_dependency_matrix_sha256": sha(matrix),
        },
        "path": "PATH_B_AUTHORITATIVE_HOT_LOG_BOUNDING_REQUIRED",
        "finding": {
            "main_database_bytes": total,
            "events_table_bytes": event_bytes,
            "events_table_fraction": event_bytes / total,
            "event_rows": data["events"]["row_count"],
            "linear_lifetime_projection": data["descriptive_lifetime_projection"],
        },
        "why_path_a_is_rejected": [
            "events occupies the overwhelming physical majority of the retained database",
            "dominant event types are authoritative, not disposable diagnostics",
            "current chain validation and restart consumers require explicit replacement of the full-prefix invariant",
            "VACUUM alone only reclaims deleted pages and cannot change append-only lifetime growth",
        ],
        "selected_architecture": {
            "normal_restart": "identity + validated checkpoint + protected current snapshot + bounded absolute-sequence tail",
            "prefix_integrity": "checkpoint commits prefix sequence bounds, event count, prior checkpoint hash, terminal event hash, snapshot state hash, habitat binding/state, body attachment, schema, and epoch",
            "active_provenance": "retain or checkpoint-promote current attachment and other bounded active evidence before deletion",
            "historical_replay": "full birth replay requires verified cold archive after compaction; absence fails explicitly",
            "physical_reclamation": "controlled SQLite WAL checkpoint plus VACUUM only after valid logical checkpoint",
        },
        "policy_isolation": "ledger maintenance is not supplied to candidate generation, arbitration, Governance, physiology, motivation, or learning.",
    })


if __name__ == "__main__":
    main()
