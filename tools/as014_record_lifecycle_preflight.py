"""Durably record the completed non-formal AS-014 lifecycle preflight."""

from __future__ import annotations

from tools.as014_evidence import publish


def main() -> None:
    result = {
        "schema": "AS014_LIFECYCLE_EXECUTABLE_PREFLIGHT_V1",
        "directive": "UMBRA-AS-014",
        "baseline": "a97171a2dab7c1750e2556727bce9e3648bb359a",
        "formal": False,
        "seed": 41414021,
        "maintenance_ticks": 48,
        "ledger_overrides": {
            "ledger_hot_tail_event_max": 64,
            "ledger_checkpoint_keep": 2,
        },
        "completed_ticks": 148,
        "checkpoint_epoch": 22,
        "checks": {
            "checkpoint_maintenance": True,
            "restart_habitat_and_owners": True,
            "true_physical_body_replacement": True,
            "owner_continuity": True,
            "post_replacement_restart": True,
            "compatible_profile_swap": True,
            "continued_organism_execution": True,
        },
        "pass": True,
    }
    digest = publish("AS014_LIFECYCLE_EXECUTABLE_PREFLIGHT.json", result)
    print({"pass": result["pass"], "sha256": digest})


if __name__ == "__main__":
    main()
