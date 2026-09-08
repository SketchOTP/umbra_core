"""Durably record the returned non-formal AS-014 R3 preflight result."""

from __future__ import annotations

from tools.as014_evidence import publish


def main() -> None:
    result = {
        "schema": "AS014_R3_EXECUTABLE_PREFLIGHT_V1",
        "directive": "UMBRA-AS-014",
        "baseline": "a97171a2dab7c1750e2556727bce9e3648bb359a",
        "formal": False,
        "source": {
            "kind": "codex_process_job_returned_result",
            "job_id": "job-mtszaqtt-4cc70300",
            "command": (
                "python3 -c ... run_case('R3', 41414024, "
                "Path('/tmp/as014-r3-preflight-r4'), 3601)"
            ),
        },
        "seed": 41414024,
        "target_ticks": 3601,
        "ticks": 3601,
        "terminal": "completed",
        "critical_failure": None,
        "first_no_safe_action": None,
        "body_change_count": 1,
        "body_profile_after": "MINIMAL_CREATURE_BODY",
        "checks": {
            "r3_profile_transition_handler_executable": True,
            "body_profile_changed_once": True,
            "constitutional_identity_preserved": True,
            "full_stack_bounded_continuation": True,
            "full_stack_route_demand_learning": True,
            "no_scientific_qualification_claim": True,
        },
        "pass": True,
    }
    digest = publish("AS014_R3_EXECUTABLE_PREFLIGHT.json", result)
    print({"pass": result["pass"], "sha256": digest})


if __name__ == "__main__":
    main()
