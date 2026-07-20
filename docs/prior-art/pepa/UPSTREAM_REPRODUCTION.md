# PEPA upstream reproduction

## Attempts (2026-07-20)

### 1. Pin public repositories

- `https://anonymous.4open.science/r/staircase_navi-B38C` → HTTP **401** `{"error":"not_connected"}`; `git clone` → repository not found.
- `https://anonymous.4open.science/r/elevator_staircase_navi-1CC5` → same.
- GitHub search (`pepa-persistent`, `staircase_navi`, `PEPA Unitree personality`, author queries) → **0** repositories.
- Hugging Face model search → **0**.

**Pin result:** no commit hash obtainable. Recorded in `docs/evidence/d000-track6/source-manifest.json`.

### 2. Install documented dependencies

Blocked — no reachable dependency manifests (requirements.txt / package.xml / etc.).

### 3. Run available tests

Blocked — no clone.

### 4. Simulation / hardware-free example

Blocked for upstream. Independent micro-world used instead (`independent_reproduction/`).

### 5. Navigation or skill module

Attempted clone/fetch of both claimed nav modules — **failed**.

### 6. Personality / reflection / goal-generation code

Only **prompt templates** on the Google Sites page (not executable). Documented under SOURCES / ARCHITECTURE_DISSECTION. No public Python package executed.

### 7. Unavailable components

Listed explicitly in source-manifest `missing_components` and `paper_only_claims`.

## Upstream verdict

```text
UPSTREAM_BLOCKED — no reachable code; genuine clone/install/execute attempts failed with HTTP 401
```

Gate 2 (upstream attempt) is **satisfied as an honest failed attempt**, not as a successful run.

## Safety

No live credentials, cloud robotics, or unrestricted external actions were used.
