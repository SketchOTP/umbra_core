"""Publish the unchanged A/B/C result for AS-015 legacy nodes.

The runs are intentionally read-only comparison evidence.  Final owner-level
classification is deferred until source-path tracing establishes what each
fixed trajectory did or did not exercise.
"""

from __future__ import annotations

from tools.as015_evidence import publish
from tools.as015_legacy_failure_inventory import NODES


BASELINES = {
    "A_current_as015_candidate": {
        "revision": "working tree based on b8977c6c05ad3ca89743368bbfd0fc48bb2b1ee7",
        "result": "FAIL",
    },
    "B_sealed_as014": {
        "revision": "b8977c6c05ad3ca89743368bbfd0fc48bb2b1ee7",
        "result": "FAIL",
    },
    "C_pre_as014": {
        "revision": "a97171a2dab7c1750e2556727bce9e3648bb359a",
        "result": "FAIL",
    },
}


def main() -> None:
    rows = []
    for node in NODES:
        rows.append(
            {
                "node_id": node["node_id"],
                "A_current_as015_candidate": "FAIL",
                "B_sealed_as014": "FAIL",
                "C_pre_as014": "FAIL",
                "differential_disposition": "NOT_AS015_OR_AS014_INTRODUCED",
                "classification_status": "OWNER_TRACE_REQUIRED",
            }
        )
    payload = {
        "directive": "UMBRA-AS-015",
        "job": "job-mttsspoz-87fa9cfc",
        "command": "unchanged exact seven-node pytest command in A/B/C worktrees",
        "baselines": BASELINES,
        "rows": rows,
        "conclusion": (
            "All seven assertions fail in each comparison state. The differential "
            "rules out both the AS-015 viability kernel and AS-014 persistence work "
            "as introduction points; it does not itself decide whether an inherited "
            "assertion is stale or a current owner defect."
        ),
        "execution_boundary": {
            "formal_seed_consumed": False,
            "scientific_lock_established": False,
            "retries": 0,
            "reseeds": 0,
        },
    }
    print(publish("AS015_LEGACY_BASELINE_DIFFERENTIAL.json", payload))


if __name__ == "__main__":
    main()
