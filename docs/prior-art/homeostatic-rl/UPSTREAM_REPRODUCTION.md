# UPSTREAM_REPRODUCTION

## B1 — homeostatic_agents_pfrl

| Step | Result |
|---|---|
| 1. Exact env reconstruction | Attempted; depends on external `trp_env_mujoco_py` / `thermal_regulation_mujoco_py` |
| 2. Isolated deps | torch present on host; **pfrl** and **mujoco_py** missing on host; venv installed gym+pfrl |
| 3. Pretrained weights | OSF link in README (`https://osf.io/mscn8/`); not downloaded (env blocked) |
| 4. Bounded training smoke | **Not run** — MuJoCo env unavailable |
| 5. Static mechanism audit | **OK** — `reward_setting` homeostatic / homeostatic_shaped / greedy documented in `main_trp.py` |

Author note (README): repository outdated; use as reference.

**Verdict:** `UPSTREAM_RUNTIME_BLOCKED` — incompatibilities preserved; not concealed by formal repro.

## B2 — deeprl_gfn

| Step | Result |
|---|---|
| 1. Exact Python 3.9 env | Host Python 3.14; torch==2.0.1 unavailable for 3.14; used modern torch in venv |
| 2. Pinned deps | gym 0.22 + pfrl 0.3 installed in `/tmp/umbra-hrrl2`; mujoco-py **not** installed (build risk / budget) |
| 3. Install included trp_env | Editable install OK (`trp_env-3.10.0+as0`) |
| 4. Deterministic CPU smoke | Package imports; `TwoResourceEnv` fails: `No module named 'mujoco_py'` |
| 5. Canonical rule comparison | `rules.py` imports OK (`get_args`); full env rule run blocked |
| 6. Visualization | Blocked on env |

**Source-derived mechanism smoke (ran):** `_homeostatic_shaped` equations from `two_resource_env.py` executed in isolation — recovery positive, overshoot negative, deprivation increases outcome value.

**Compatibility patches:** none applied to upstream trees (source-locked). Isolated venv only.

**Verdict:** Full embodied runtime blocked; faithful reward mechanism equations **executed**.

## Honest separation

| Artifact | What it proves |
|---|---|
| Formal `formal_reproduction/` | Paper-faithful causal tests |
| Yoshida equation smoke | Upstream reward definition behaves as drive reduction |
| Full MuJoCo/PFRL training | **Not demonstrated** |
