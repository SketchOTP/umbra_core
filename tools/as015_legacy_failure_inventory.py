"""Publish the frozen AS-015 pre-lock legacy-failure inventory.

This records the exact protected nodes before any owner-suite repair or test
replacement.  It deliberately contains no organism execution.
"""

from __future__ import annotations

import platform
import sys

from tools.as015_evidence import publish


NODES = (
    {
        "node_id": "tests/test_d003.py::test_contradiction_weakens_obsolete_model",
        "owner": "D-003 WorldModel",
        "assertion": "contradictory verified evidence weakens an obsolete CHARGE model or affordance",
    },
    {
        "node_id": "tests/test_d003.py::test_false_affordance_is_revised",
        "owner": "D-003 WorldModel",
        "assertion": "a charge_from affordance exists and is revised after an intervention",
    },
    {
        "node_id": "tests/test_d003.py::test_changed_affordance_adaptation",
        "owner": "D-003 WorldModel",
        "assertion": "changed charge affordance produces contradiction, weakening, or supersession",
    },
    {
        "node_id": "tests/test_d006.py::test_full_tick_recognizes_proposes_governs_and_opens_pending",
        "owner": "D-006 social",
        "assertion": "a fixed ten-tick live trajectory creates social_pending_created",
    },
    {
        "node_id": "tests/test_d009.py::test_manipulation_candidates_compete_in_arbitration",
        "owner": "D-009 manipulation",
        "assertion": "MANIPULATE wins a single fixed direct-arbitration selector root",
    },
    {
        "node_id": "tests/test_d010.py::test_all_production_runtime_tick_uses_are_classified",
        "owner": "D-010 temporal inventory",
        "assertion": "the line-number keyed runtime tick inventory has no stale or unclassified sites",
    },
    {
        "node_id": "tests/test_d010.py::test_expression_adaptive_trim_on_rss_growth",
        "owner": "D-010 performance",
        "assertion": "a simulated 0.5 MiB RSS increase causes exactly one later native-arena trim call",
    },
)


def main() -> None:
    payload = {
        "directive": "UMBRA-AS-015",
        "phase": "pre-lock legacy regression attribution",
        "baseline": "b8977c6c05ad3ca89743368bbfd0fc48bb2b1ee7",
        "command": "python -m pytest -q <the seven node IDs in nodes>",
        "environment": {
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "nodes": NODES,
        "observed_result": {
            "failed": 7,
            "passed": 0,
            "first_run": "job-mttsgek4-d80e93d5",
            "targeted_confirmation": "job-mttskegg-fd2cefe3",
        },
        "integrity": {
            "formal_seed_consumed": False,
            "scientific_lock_established": False,
            "organism_execution_performed_by_this_inventory": 0,
            "next_required_step": "A/B/C unchanged-baseline differential before repair",
        },
    }
    print(publish("AS015_LEGACY_FAILURE_INVENTORY.json", payload))


if __name__ == "__main__":
    main()
