"""Read-only physical and logical attribution for the retained AS-013 ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from tools.as014_evidence import publish
from umbra_core.events import is_authoritative, is_diagnostic


BASELINE = "a97171a2dab7c1750e2556727bce9e3648bb359a"
DEFAULT_DB = (
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-014-persistent-ledger-boundedness-completion-r1/forensic/"
    "as013-boundedness.sqlite"
)
AS013_SHA256 = "19e99be48bf3f0c395b5bbc0f7d6d9eacb457f9f1cd364665a53f40ed24c02f8"
AS013_TICKS = 100_000
AS013_HZ = 2.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * p)
    return int(ordered[index])


def subsystem(event_type: str) -> str:
    if event_type.startswith("habitat_"):
        return "Habitat"
    if event_type.startswith("social_"):
        return "Social"
    if event_type.startswith("individuality_"):
        return "Individuality"
    if event_type.startswith("temporal_") or event_type == "orchestration_tick_committed":
        return "Temporal"
    if event_type.startswith("perception_"):
        return "Perception"
    if event_type.startswith("embodiment_") or event_type == "body_schema_supersede":
        return "Embodiment/SelfModel"
    if event_type.startswith("world_model_"):
        return "WorldModel"
    if event_type.startswith("memory_"):
        return "Memory"
    if event_type in {"physiology_drift", "organism_effect_applied"}:
        return "Physiology"
    if event_type in {"proposal", "denial", "outcome_verified"}:
        return "Governed execution"
    return "Runtime/other"


def authority(event_type: str) -> str:
    if is_authoritative(event_type):
        return "AUTHORITATIVE"
    if is_diagnostic(event_type):
        return "DIAGNOSTIC"
    return "UNDECLARED_IN_EVENTS_POLICY"


def sqlite_uri(path: Path) -> str:
    return f"file:{path.resolve()}?mode=ro&immutable=1"


def analyze(path: Path) -> dict[str, Any]:
    actual_hash = sha256_file(path)
    if actual_hash != AS013_SHA256:
        raise RuntimeError(f"forensic_copy_hash_mismatch:{actual_hash}")
    conn = sqlite3.connect(sqlite_uri(path), uri=True)
    conn.row_factory = sqlite3.Row
    try:
        integrity = [str(row[0]) for row in conn.execute("PRAGMA integrity_check")]
        page_size = int(conn.execute("PRAGMA page_size").fetchone()[0])
        page_count = int(conn.execute("PRAGMA page_count").fetchone()[0])
        freelist_count = int(conn.execute("PRAGMA freelist_count").fetchone()[0])
        journal_mode = str(conn.execute("PRAGMA journal_mode").fetchone()[0])
        auto_vacuum = int(conn.execute("PRAGMA auto_vacuum").fetchone()[0])
        schema_rows = conn.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE type IN ('table','index') ORDER BY type, name"
        ).fetchall()
        object_bytes: dict[str, int] = defaultdict(int)
        for row in conn.execute("SELECT name, SUM(pgsize) AS bytes FROM dbstat GROUP BY name"):
            object_bytes[str(row["name"])] = int(row["bytes"] or 0)
        schema: list[dict[str, Any]] = []
        for row in schema_rows:
            name = str(row["name"])
            entry = {
                "type": str(row["type"]),
                "name": name,
                "table": str(row["tbl_name"]),
                "physical_bytes": object_bytes.get(name, 0),
            }
            if row["type"] == "table" and name != "sqlite_sequence":
                entry["row_count"] = int(conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0])
            schema.append(entry)

        stats: dict[str, list[int]] = defaultdict(list)
        counts: Counter[str] = Counter()
        totals: Counter[str] = Counter()
        for row in conn.execute("SELECT event_type, length(payload) AS payload_bytes FROM events"):
            kind = str(row["event_type"])
            payload_bytes = int(row["payload_bytes"] or 0)
            counts[kind] += 1
            totals[kind] += payload_bytes
            stats[kind].append(payload_bytes)
        event_rows: list[dict[str, Any]] = []
        all_payload = sum(totals.values())
        total_events = sum(counts.values())
        for kind in sorted(counts):
            values = stats[kind]
            event_rows.append(
                {
                    "event_type": kind,
                    "subsystem": subsystem(kind),
                    "authority_class": authority(kind),
                    "row_count": counts[kind],
                    "payload_bytes": totals[kind],
                    "mean_payload_bytes": totals[kind] / counts[kind],
                    "p50_payload_bytes": percentile(values, 0.50),
                    "p95_payload_bytes": percentile(values, 0.95),
                    "event_row_percentage": (counts[kind] / total_events) if total_events else 0.0,
                    "event_payload_percentage": (totals[kind] / all_payload) if all_payload else 0.0,
                }
            )
        by_count = sorted(event_rows, key=lambda item: (-item["row_count"], item["event_type"]))[:20]
        by_payload = sorted(event_rows, key=lambda item: (-item["payload_bytes"], item["event_type"]))[:20]
        classes: dict[str, dict[str, int]] = defaultdict(lambda: {"events": 0, "payload_bytes": 0})
        subsystems: dict[str, dict[str, int]] = defaultdict(lambda: {"events": 0, "payload_bytes": 0})
        for event in event_rows:
            classes[event["authority_class"]]["events"] += int(event["row_count"])
            classes[event["authority_class"]]["payload_bytes"] += int(event["payload_bytes"])
            subsystems[event["subsystem"]]["events"] += int(event["row_count"])
            subsystems[event["subsystem"]]["payload_bytes"] += int(event["payload_bytes"])
        file_size = path.stat().st_size
        bytes_per_tick = file_size / AS013_TICKS
        events_per_tick = total_events / AS013_TICKS
        seconds_per_day = 24 * 60 * 60
        projection = {
            "basis": "AS013 accelerated execution: descriptive only, not a threshold",
            "ticks_per_day_at_2hz": AS013_HZ * seconds_per_day,
            "estimated_hot_bytes_per_day": bytes_per_tick * AS013_HZ * seconds_per_day,
            "estimated_hot_bytes_per_week": bytes_per_tick * AS013_HZ * seconds_per_day * 7,
            "estimated_hot_bytes_per_30_day_month": bytes_per_tick * AS013_HZ * seconds_per_day * 30,
            "estimated_hot_bytes_per_365_day_year": bytes_per_tick * AS013_HZ * seconds_per_day * 365,
            "events_per_tick": events_per_tick,
            "bytes_per_tick": bytes_per_tick,
            "bytes_per_event": file_size / total_events if total_events else 0.0,
        }
        return {
            "schema": "AS014_AS013_STORAGE_ATTRIBUTION_V1",
            "directive": "UMBRA-AS-014",
            "baseline": BASELINE,
            "retained_source": {
                "source_generation": "AS-013",
                "forensic_copy": str(path),
                "sha256": actual_hash,
                "bytes": file_size,
                "read_only_uri": sqlite_uri(path),
                "integrity_check": integrity,
            },
            "physical_database": {
                "main_file_bytes": file_size,
                "wal_bytes": Path(str(path) + "-wal").stat().st_size if Path(str(path) + "-wal").exists() else 0,
                "shm_bytes": Path(str(path) + "-shm").stat().st_size if Path(str(path) + "-shm").exists() else 0,
                "page_size": page_size,
                "page_count": page_count,
                "freelist_count": freelist_count,
                "freelist_bytes": freelist_count * page_size,
                "journal_mode": journal_mode,
                "auto_vacuum": auto_vacuum,
                "objects": schema,
                "unattributed_dbstat_bytes": file_size - sum(object_bytes.values()),
            },
            "events": {
                "row_count": total_events,
                "payload_bytes": all_payload,
                "by_event_type": event_rows,
                "top_20_by_row_count": by_count,
                "top_20_by_payload_bytes": by_payload,
                "by_authority_class": dict(sorted(classes.items())),
                "by_subsystem": dict(sorted(subsystems.items())),
            },
            "descriptive_lifetime_projection": projection,
            "conclusion": "PENDING_ROOT_CAUSE_DECISION",
        }
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path(DEFAULT_DB))
    parser.add_argument("--output", default="AS014_AS013_STORAGE_ATTRIBUTION.json")
    args = parser.parse_args()
    result = analyze(args.db)
    digest = publish(args.output, result)
    print(json.dumps({"artifact": args.output, "sha256": digest}, sort_keys=True))


if __name__ == "__main__":
    main()
