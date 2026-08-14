# Causal Path

1. `umbra_core/arbitration.py` computes the recovery pool from physiology.
2. Energy and stimulation both required recovery at the reproduced state.
3. A prior `recovery_focus` of `stimulation` remained sticky because the old guard only displaced a non-energy focus when energy was already below the critical bound.
4. The stimulation fallback had no suitable affordance and selected `MOVE`.
5. `MOVE` cost energy and drift crossed the `0.05` critical floor.

The D-003 world-model and governance layers did not need to be altered to explain the observed transition. The defect is upstream in recovery-focus arbitration.
