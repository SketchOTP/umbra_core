# UMBRA-D-012B1 Remediation Report

- Exact failing mechanism reproduced: yes
- Exact source path: `umbra_core/arbitration.py`, critical energy recovery
- Downstream contract: `umbra_core/embodiment.py`, `CHARGE` range
- Red test before fix: `CHARGE` was selected at distance 1.526
- Fix: recovery `CHARGE` transition 2.2 → 1.5
- Threshold weakened: no
- Formal schedule changed: no
- Supplement S1 required: no
- Production files changed: `umbra_core/arbitration.py` only
- Remediated R0 final: tick 191, energy 0.4285, non-critical
- Remediation status: `REMEDIATED_AND_REVALIDATED`
