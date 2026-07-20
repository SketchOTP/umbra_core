# NOTES — Track 2 lab notebook

## 2026-07-20

- Corrected MicroPsi Track 1 terminology to `INDEPENDENT_MECHANISM_REPRODUCTION`; upstream MicroPsi2 runtime was **not** executed.
- Formal env: energy + temperature; D1–D3; R0–R4; C0–C8; I0–I9.
- Causal suite seeds `{0,1,2}`, 80 steps: deprivation, satiation, competition, anticipation, autonomy, ablations, relocation — **pass**.
- Cloned Yoshida repos at pinned commits (see SOURCES). Authors warn `homeostatic_agents_pfrl` outdated.
- `deeprl_gfn` LICENSE file empty; GitHub license NOASSERTION — do not claim MIT without operator confirmation.
- Isolated venv: gym 0.22 + pfrl 0.3 + editable trp_env; `TwoResourceEnv` blocked on mujoco_py.
- Ran source-derived `homeostatic_shaped` smoke from `two_resource_env.py` without MuJoCo.
- Curiosity (P4): reference only. Multi-agent coupling: deferred Track 6.
- No production UMBRA kernel; D-001 remains blocked; Track 3 not opened by this track alone (D-000 continues).

## Scientific claim authorized (bounded)

Internal regulatory state that drifts autonomously can alter outcome values, support satiation and need competition, and motivate action without user input when paired with a drive-reduction learning signal and physiology/policy separation — under the formal tests in this track.

## Claims not authorized

Complete UMBRA motivational system; artificial emotion; personality; relationship formation; consciousness; organismhood; full Yoshida embodied runtime reproducibility on this host.
