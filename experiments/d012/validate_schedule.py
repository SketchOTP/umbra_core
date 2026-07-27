"""D-012A schedule-only validator; never launches an organism."""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
def main() -> None:
    schedule = json.loads((ROOT / "opportunity-schedule.json").read_text())
    checkpoints = json.loads((ROOT / "checkpoint-schedule.json").read_text())
    restarts = json.loads((ROOT / "restart-schedule.json").read_text())
    assert schedule["active_hours"] == 72
    assert [x["hour"] for x in checkpoints["checkpoints"]] == [0, 6, 24, 48, 72]
    assert len(restarts["restarts"]) == 4
    assert all(0 <= e["hour"] <= 72 and e["window"][0] <= e["hour"] <= e["window"][1] for e in schedule["events"])
    assert all(e["class"] in {"ENVIRONMENTAL_CHANGE", "PARTNER_BEHAVIOR", "BODY_CHANGE", "PERCEPTION_INPUT", "PROCESS_EVENT", "CHECKPOINT_ONLY"} for e in schedule["events"])
    assert all(x in schedule["forbidden_direct_state_effects"] for x in ["identity", "memory", "action_selection"])
    print(json.dumps({"schedule_valid": True, "formal_launched": False, "events": len(schedule["events"])}))
if __name__ == "__main__": main()
