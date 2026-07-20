# FORMAL_MODEL — Keramati–Gutkin style reference

Independent mechanism reproduction under `formal_reproduction/`.  
Not a production UMBRA kernel. Not the Yoshida MuJoCo runtime.

## Internal state

\[
H_t = (e_t, \tau_t) \in [0,1]^2
\]

- Ideal: \(e^\* = 0.70\), \(\tau^\* = 0.50\)
- Viable intervals: energy \([0.35, 0.85]\), temperature \([0.30, 0.70]\)
- Critical bounds: \(\{0, 1\}\)
- Autonomous drift: \(e_{t+1} \leftarrow e_t + \delta_e\) even under `STAY` / observer absence
- Ambient temperature pull from warm/cool regions
- Policy **cannot** assign \(H\); only drift, time, authenticated outcomes, or experimental `intervene`

## Drives

| ID | Formula |
|---|---|
| D1 | \(\|e-e^\*\| + \|\tau-\tau^\*\|\) |
| D2 | \(\sqrt{(e-e^\*)^2 + (\tau-\tau^\*)^2}\) |
| D3 | \((e-e^\*)^2 + (\tau-\tau^\*)^2\) (nonlinear / overshoot-sensitive) |

Default comparison drive: **D3**.

## Rewards

| ID | Definition | Role |
|---|---|---|
| R0 | Fixed external event table | Non-homeostatic control |
| R1 | \(-D(H_{t+1})\) | Negative drive |
| R2 | \(D(H_t) - D(H_{t+1})\) | Keramati–Gutkin drive reduction |
| R3 | Sparse survival (+1 / −10 critical) | Terminal control |
| R4 | Hard-coded max-deficit action | **Negative control** (not UMBRA candidate) |

## Environment

4×3 grid: food, warm, cool, neutral. Actions: `N S E W STAY CONSUME`.  
Forbidden: `GO_EAT`, `GO_WARM`, `GO_COOL`.

## Policies (conditions)

C0 random … C8 novelty — see `experiment.py`.

## Anticipation (formal)

Forward projection of energy under drift + travel + food delay.  
This is a **minimal anticipatory regulator**, not a full continuous-time HRRL learner. Ceiling noted in code (`ponytail`).
