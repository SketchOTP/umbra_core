#!/usr/bin/env python3
"""Seal the AS-003E bounded external prior-art boundary."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import uuid


TEXT = """# AS-003E bounded prior-art boundary

Checked August 31, 2026. This review is **REFERENCE ONLY**: it constrains the architecture question but imports no biological circuit, dependency, equation, or selection rule.

## Sources and retained principles

- Palmer and Kristan, [Contextual modulation of behavioral choice](https://pubmed.ncbi.nlm.nih.gov/21624826/) (2011). The review distinguishes environmental, internal, and ongoing-behavior context and reports that both internal and external context modulate behavioral choice. **Adopted boundary:** context can legitimately alter what behavior is expressed; this does not establish an UMBRA scalar or a priority table.
- Cisek, [Cortical mechanisms of action selection: the affordance competition hypothesis](https://pubmed.ncbi.nlm.nih.gov/17428779/) (2007). The paper frames action selection as choosing among actions currently possible and discusses concurrent specification/competition rather than a serial planner. **Adopted boundary:** candidate/affordance specification can be parallel and distinct from final selection.
- Prescott, Bryson, and Seth, [Modelling natural action selection](https://pubmed.ncbi.nlm.nih.gov/17428783/) (2007). Its framing is conflict resolution among competing behavioral alternatives, with multiple modelling approaches and social context. **Adopted boundary:** an autonomous organism has a singleness-of-action problem, but no claim that one normative global objective is required.
- Burnett et al., [Hunger-driven motivational state competition](https://pubmed.ncbi.nlm.nih.gov/27693254/) (2016). The reported experiments show hunger can suppress rival motivations in a state- and food-availability-dependent manner. **Adopted boundary:** motivational influence may be conditional on owned state and available incentives rather than permanently weighted across every action.
- Toates, [Incentive Motivation](https://doi.org/10.1017/9781009744454.005) (2026). The publisher summary states that an incentive's pull depends jointly on intrinsic properties, internal state, learned associations, and rival incentives. **Adopted boundary:** internal condition, opportunity, learned association, and competing incentives are distinct causal inputs; this does not provide a calibrated common UMBRA unit.

## Explicit non-imports

No neural circuit topology, dopamine model, reinforcement learning, model-based RL, expected utility, global reward/survival score, fixed motivational coefficient, source priority, active inference, POMDP, MPC, planner, tree search, or biological simulation is adopted. The literature does not establish a cross-system UMBRA control scale, so it cannot validate a numerical behavioral-control claim.

## Replan consequence

The reviewed material supports testing causal-role partition and context activation before any common currency. If a future common claim is proposed, its single cross-system meaning and calibration must be established from UMBRA's constitutional/verified semantics, not copied from biological labels or normalized channel values.
"""


def durable(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError("short_write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.exists():
        raise FileExistsError(path)
    os.replace(temp, path)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    durable(args.evidence_root / "AS003E_PRIOR_ART_BOUNDARY.md", TEXT.encode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
