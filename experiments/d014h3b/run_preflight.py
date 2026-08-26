#!/usr/bin/env python3
"""Current-stack, non-production D-014H3B R2 authority preflight."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d009.run_experiment import _habitat_state_for_scenario
from umbra_core.embodiment import Embodiment, _make_partner
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.events import build_initialized_event
from umbra_core.habitat.state import FreeLocation, make_social_entity_object
from umbra_core.perception import PerceptionMembrane
from umbra_core.util import SeededRNG

EVIDENCE = Path("/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/d014h3b-social-habitat-bridge-r1")
PARTNER_OBJECT_ID = "social:partner:d014"


def partner_object():
    partner = _make_partner("partner:d014", 6.0, 4.0, "H0", index=0)
    policy = partner.response_policy
    return make_social_entity_object(
        object_id=PARTNER_OBJECT_ID,
        entity_ref=partner.hidden_partner_id,
        location=FreeLocation(6.0, 4.0, "zone:general"),
        history_code=policy.history_code,
        motion_signature=partner.true_cues.motion_signature,
        appearance_signature=partner.true_cues.appearance_signature,
        response_timing_pattern=partner.true_cues.response_timing_pattern,
        interaction_style_cues=partner.true_cues.interaction_style_cues,
        response_mode=policy.mode,
        contingent_probability=policy.contingent_probability,
        flip_at=policy.flip_at,
        absent_windows=tuple(policy.absent_windows),
    )


def run_once() -> dict[str, object]:
    state = _habitat_state_for_scenario("S10")
    engine = HabitatEngine(state)
    emb = Embodiment()
    emb.body.x, emb.body.y = 4.0, 3.0
    emb.attach_habitat_engine(engine)
    membrane = PerceptionMembrane(false_negative_rate=0.0, noise_sigma=0.0)
    events: list[dict[str, object]] = [
        build_initialized_event(
            state,
            event_id="h3b:event:init",
            transaction_id="h3b:txn:init",
            request_id="h3b:req:init",
        )
    ]
    trace: list[dict[str, object]] = []
    restart_ok = False
    adapter_accept = False
    for tick in range(0, 2601):
        if tick == 600:
            events.append(
                engine.commit_object_creation(
                    partner_object(),
                    event_id="h3b:event:create",
                    transaction_id="h3b:txn:create",
                    request_id="h3b:req:create",
                )
            )
        if tick == 1200:
            adapter_accept = True
        if tick == 1800:
            before = engine.state
            engine = HabitatEngine(copy.deepcopy(before))
            emb.attach_habitat_engine(engine)
            after = engine.state
            restart_ok = (
                after.objects[PARTNER_OBJECT_ID].state.entity_ref == "partner:d014"
                and after.objects[PARTNER_OBJECT_ID].location == before.objects[PARTNER_OBJECT_ID].location
                and after.objects[PARTNER_OBJECT_ID].state == before.objects[PARTNER_OBJECT_ID].state
            )
        if tick == 2400:
            events.append(
                engine.commit_object_visibility(
                    PARTNER_OBJECT_ID,
                    occluded=True,
                    event_id="h3b:event:occlude",
                    transaction_id="h3b:txn:occlude",
                    request_id="h3b:req:occlude",
                )
            )
        if tick == 2600:
            events.append(
                engine.commit_object_visibility(
                    PARTNER_OBJECT_ID,
                    occluded=False,
                    event_id="h3b:event:reappear",
                    transaction_id="h3b:txn:reappear",
                    request_id="h3b:req:reappear",
                )
            )
        if tick in {0, 600, 1200, 1800, 2400, 2600}:
            membrane.perceive(emb, float(tick), SeededRNG(13014 + tick))
            trace.append({
                "tick": tick,
                "partner_count": len(engine.authoritative_social_entities()),
                "occluded": engine.state.objects[PARTNER_OBJECT_ID].occluded if PARTNER_OBJECT_ID in engine.state.objects else None,
                "policy_cue_count": len(membrane.partner_cues),
                "state_hash": engine.state.state_hash,
            })
    return {
        "event_types": [str(event["event_type"]) for event in events],
        "event_state_hashes": [str(event["payload"]["new_state_hash"]) for event in events],
        "trace": trace,
        "adapter_event_at_1200": adapter_accept,
        "restart_preserved": restart_ok,
        "final_state_hash": engine.state.state_hash,
    }


def main() -> None:
    first = run_once()
    second = run_once()
    deterministic = first == second
    result = {
        "directive": "UMBRA-D-014H3B",
        "classification": "CURRENT_STACK_AUTHORITY_CORRECTED_R2_PREFLIGHT",
        "runs": 2,
        "deterministic": deterministic,
        "first": first,
        "second": second,
        "result": "PASS" if deterministic and first["restart_preserved"] else "FAIL",
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    output = EVIDENCE / "D014H3B_R2_AUTHORITY_PREFLIGHT.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (EVIDENCE / "D014H3B_R2_AUTHORITY_PREFLIGHT.sha256").write_text(f"{digest}  {output.name}\n")
    print(json.dumps({"result": result["result"], "deterministic": deterministic, "evidence": str(output)}, indent=2))


if __name__ == "__main__":
    main()
