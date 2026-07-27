"""D-012A schedule-only validator; never launches an organism."""
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
def main() -> None:
    schedule = json.loads((ROOT / "opportunity-schedule.json").read_text())
    checkpoints = json.loads((ROOT / "checkpoint-schedule.json").read_text())
    restarts = json.loads((ROOT / "restart-schedule.json").read_text())
    p0 = json.loads((ROOT / "p0-formal-config.json").read_text())
    assert schedule["active_hours"] == 72
    assert [x["hour"] for x in checkpoints["checkpoints"]] == [0, 6, 24, 48, 72]
    assert len(restarts["restarts"]) == 4
    assert all(0 <= e["hour"] <= 72 and e["window"][0] <= e["hour"] <= e["window"][1] for e in schedule["events"])
    assert all(e["class"] in {"ENVIRONMENTAL_CHANGE", "PARTNER_BEHAVIOR", "BODY_CHANGE", "PERCEPTION_INPUT", "PROCESS_EVENT", "CHECKPOINT_ONLY"} for e in schedule["events"])
    assert all(x in schedule["forbidden_direct_state_effects"] for x in ["identity", "memory", "action_selection"])
    assert p0["minimum_active_seconds"] == 1200
    assert p0["normal_stop_seconds"] == 1800
    assert p0["maximum_active_seconds"] == 3600
    assert not p0["d010_enabled"] and not p0["p1_authorized"] and not p0["p2_authorized"]
    evidence = ROOT.parents[1] / "docs/evidence/d012/p0-formal-execution-manifest.json"
    print(json.dumps({"schedule_valid": True, "formal_launched": evidence.exists(), "events": len(schedule["events"]), "adaptive_p0_valid": True}))
if __name__ == "__main__": main()
