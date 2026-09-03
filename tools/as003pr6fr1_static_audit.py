"""Republish R6F's static feasibility gates under the fresh R6F-R1 root."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from experiments.as003pr6f.feasibility import static_feasibility_report


ROOT = Path(
    "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/"
    "umbra-as-003p-r6f-r1-common-root-option"
)


def publish(name: str, value: object) -> str:
    ROOT.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    target = ROOT / name
    fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=ROOT)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        directory_fd = os.open(ROOT, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    readback = target.read_bytes()
    if readback != payload:
        raise RuntimeError(f"readback_mismatch:{name}")
    return hashlib.sha256(readback).hexdigest()


def main() -> None:
    report = static_feasibility_report()
    report.update(
        {
            "directive": "UMBRA-AS-003P-R6F-R1",
            "baseline": "e5af166e86e85a5937d25b579f9256768bbd3d30",
            "inherited_protocol_seed": 18482,
            "inherited_scenario": "S0",
            "organism_runs": 0,
            "ticks": 0,
            "production_change": 0,
            "existing_test_semantic_delta": 0,
            "qualification_boundary": "static prerequisites only; no organism observation",
        }
    )
    natural = {"schema": "AS003PR6FR1_NATURAL_LOSS_FEASIBILITY_AUDIT_V1", **report["natural_loss"]}
    route = {"schema": "AS003PR6FR1_ROUTE_APPLICABILITY_AUDIT_V1", **report["route_applicability"]}
    result = {
        "schema": "AS003PR6FR1_STATIC_FEASIBILITY_RESULT_V1",
        "directive": "UMBRA-AS-003P-R6F-R1",
        "baseline": report["baseline"],
        "phase_b": {"status": "PASS_STATIC_FEASIBILITY", "report": report["natural_loss"]},
        "phase_c": {"status": "PASS_STATIC_APPLICABILITY", "report": report["route_applicability"]},
        "organism_runs": 0,
        "ticks": 0,
    }
    hashes = {
        "natural": publish("AS003PR6FR1_NATURAL_LOSS_FEASIBILITY_AUDIT.json", natural),
        "route": publish("AS003PR6FR1_ROUTE_APPLICABILITY_AUDIT.json", route),
        "result": publish("AS003PR6FR1_STATIC_FEASIBILITY_RESULT.json", result),
    }
    print(json.dumps(hashes, sort_keys=True))


if __name__ == "__main__":
    main()
