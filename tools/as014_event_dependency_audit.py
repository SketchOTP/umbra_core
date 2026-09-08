"""Static, source-cited AS-014 event dependency classification."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tools.as014_evidence import publish


ROOT = Path(__file__).resolve().parents[1]


def digest(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main() -> None:
    rows = [
        {
            "record_group": "identity",
            "classification": ["REQUIRED_FOR_CURRENT_LIVE_STATE"],
            "current_consumer": "Store.load_identity",
            "compaction_disposition": "retain identity row unchanged",
        },
        {
            "record_group": "event hash prefix",
            "classification": ["REQUIRED_FOR_CURRENT_AUTHORITY_PROVENANCE", "DERIVABLE_FROM_CHECKPOINT"],
            "current_consumer": "Store.validate_chain, append_event, ledger_tip",
            "compaction_disposition": "replace removed prefix verification with checkpoint terminal hash, sequence bounds, prior checkpoint hash, and checkpoint hash; retain absolute tail sequences",
        },
        {
            "record_group": "embodiment attachment/replacement events",
            "classification": ["REQUIRED_FOR_CURRENT_LIVE_STATE", "REQUIRED_FOR_CURRENT_AUTHORITY_PROVENANCE"],
            "current_consumer": "load_organism, body replacement, D008/D009 migration",
            "compaction_disposition": "promote latest canonical attachment event and attachment state into checkpoint provenance; last_event_of_types must consult it when the event is compacted",
        },
        {
            "record_group": "outcome_verified referenced by active learned state",
            "classification": ["REQUIRED_FOR_CURRENT_AUTHORITY_PROVENANCE"],
            "current_consumer": "SelfModel/WorldModel route evidence and Habitat execution recovery",
            "compaction_disposition": "retain pending-transaction evidence in tail; checkpoint a bounded canonical provenance copy for active references",
        },
        {
            "record_group": "prepared Habitat execution and journal",
            "classification": ["REQUIRED_FOR_PENDING_TRANSACTION_RECOVERY"],
            "current_consumer": "habitat.execution_journal recovery",
            "compaction_disposition": "never compact while a prepared execution exists; retain journal rows and referenced tail evidence until terminal",
        },
        {
            "record_group": "habitat mutation/event history",
            "classification": ["REQUIRED_FOR_CURRENT_LIVE_STATE", "REQUIRED_ONLY_FOR_FULL_HISTORICAL_REPLAY"],
            "current_consumer": "HabitatEngine reattachment and legacy migration fallback replay",
            "compaction_disposition": "checkpoint committed Habitat identity/version/state hash plus an authoritative Habitat checkpoint state supplied by the owner; normal live recovery uses it, while birth replay requires archive availability",
        },
        {
            "record_group": "physiology, proposal, orchestration, prediction, and disposition events",
            "classification": ["REQUIRED_ONLY_FOR_FULL_HISTORICAL_REPLAY", "DERIVABLE_FROM_CHECKPOINT"],
            "current_consumer": "diagnostics/replay; current runtime state is materialized in snapshots",
            "compaction_disposition": "compact after a validated checkpoint; no policy reader may receive maintenance state",
        },
        {
            "record_group": "social evidence and hypothesis provenance tables",
            "classification": ["REQUIRED_FOR_CURRENT_AUTHORITY_PROVENANCE"],
            "current_consumer": "SocialEngine persistence tables",
            "compaction_disposition": "retain bounded active rows and snapshot state; do not delete because their source events were compacted",
        },
        {
            "record_group": "snapshots",
            "classification": ["REQUIRED_FOR_CURRENT_LIVE_STATE"],
            "current_consumer": "load_organism",
            "compaction_disposition": "protect checkpoint-bound snapshots; keep normal snapshots bounded separately",
        },
        {
            "record_group": "full replay-from-birth",
            "classification": ["REQUIRED_ONLY_FOR_FULL_HISTORICAL_REPLAY"],
            "current_consumer": "replay_from_birth and historical diagnostics",
            "compaction_disposition": "after hot-prefix compaction, fail explicitly unless a verified optional cold archive covering the missing prefix is available",
        },
    ]
    sources = {
        path: digest(path)
        for path in (
            "umbra_core/persistence.py",
            "umbra_core/runtime.py",
            "umbra_core/habitat/execution_journal.py",
            "umbra_core/world_model/route_evidence.py",
        )
    }
    publish("AS014_EVENT_DEPENDENCY_MATRIX.json", {
        "directive": "UMBRA-AS-014",
        "baseline": "a97171a2dab7c1750e2556727bce9e3648bb359a",
        "method": "static call-graph and persistence-schema audit before any event removal",
        "source_sha256": sources,
        "rows": rows,
        "decision": "AUTHORITATIVE_HOT_LOG_BOUNDING_REQUIRES_CHECKPOINT_PLUS_TAIL_AND_ACTIVE_PROVENANCE_PROMOTION",
        "prohibited": [
            "delete events then vacuum without a checkpoint",
            "renumber retained event sequences",
            "discard current attachment or active outcome provenance",
            "silently claim full birth replay after missing-prefix compaction",
        ],
    })


if __name__ == "__main__":
    main()
